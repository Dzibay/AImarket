#!/usr/bin/env python3
"""Move recent Codex session provider buckets with a backup and rollback ledger.

Codex has no supported command that copies a conversation between providers. This
utility only reclassifies existing session metadata in JSONL and state_5.sqlite;
it never copies thread IDs or transcript content. Run a dry-run first and close
Codex, Desktop, IDE integrations, and app-server before applying a migration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"[FAIL] {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def codex_home(cli_value: str | None) -> Path:
    value = cli_value or os.environ.get("CODEX_HOME")
    return Path(value).expanduser().resolve() if value else (Path.home() / ".codex").resolve()


def sqlite_home(home: Path) -> Path:
    config = home / "config.toml"
    if config.is_file():
        try:
            import tomllib

            parsed = tomllib.loads(config.read_text(encoding="utf-8-sig"))
            value = parsed.get("sqlite_home")
            if isinstance(value, str) and value.strip():
                return Path(value).expanduser().resolve()
        except Exception:
            pass
    value = os.environ.get("CODEX_SQLITE_HOME")
    return Path(value).expanduser().resolve() if value else home


def process_is_running() -> bool:
    try:
        if os.name == "nt":
            output = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq codex.exe", "/FO", "CSV", "/NH"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            return "codex.exe" in output.lower() and "no tasks" not in output.lower()
        result = subprocess.run(["pgrep", "-x", "codex"], capture_output=True, text=True)
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def session_files(home: Path) -> Iterable[Path]:
    for directory in (home / "sessions", home / "archived_sessions"):
        if directory.is_dir():
            yield from directory.rglob("*.jsonl")


def parse_timestamp(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def recent_sqlite_provider_threads(path: Path, sources: set[str], cutoff: float) -> set[str]:
    """Return source-provider threads touched in the requested time window."""
    if not path.is_file() or not sources:
        return set()
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(str(path), timeout=5)
        connection.execute("PRAGMA busy_timeout=5000")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "threads" not in tables:
            return set()
        columns = {row[1] for row in connection.execute("PRAGMA table_info(threads)")}
        if not {"id", "model_provider"}.issubset(columns):
            return set()
        marks = ",".join("?" for _ in sources)
        time_terms: list[str] = []
        time_args: list[int] = []
        if "updated_at_ms" in columns:
            time_terms.append("COALESCE(updated_at_ms, 0) >= ?")
            time_args.append(int(cutoff * 1000))
        if "updated_at" in columns:
            time_terms.append("COALESCE(updated_at, 0) >= ?")
            time_args.append(int(cutoff))
        if not time_terms:
            return set()
        query = f"SELECT id FROM threads WHERE model_provider IN ({marks}) AND ({' OR '.join(time_terms)})"
        rows = connection.execute(query, [*sorted(sources), *time_args]).fetchall()
        return {str(row[0]) for row in rows if row and isinstance(row[0], str) and row[0].strip()}
    except (OSError, sqlite3.Error):
        return set()
    finally:
        if connection is not None:
            connection.close()


def recent_provider_threads(
    home: Path,
    sources: set[str],
    cutoff: float,
    db_recent_ids: set[str] | None = None,
) -> tuple[set[str], dict[Path, os.stat_result]]:
    ids: set[str] = set()
    stats: dict[Path, os.stat_result] = {}
    for path in session_files(home):
        try:
            stat = path.stat()
        except OSError:
            continue
        file_is_recent = stat.st_mtime >= cutoff
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if '"session_meta"' not in line or '"model_provider"' not in line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if record.get("type") != "session_meta":
                        continue
                    payload = record.get("payload")
                    if not isinstance(payload, dict) or payload.get("model_provider") not in sources:
                        continue
                    thread_id = payload.get("id")
                    if (
                        isinstance(thread_id, str)
                        and thread_id.strip()
                        and (file_is_recent or (db_recent_ids is not None and thread_id in db_recent_ids))
                    ):
                        ids.add(thread_id)
                        stats[path] = stat
                        break
        except (OSError, UnicodeError):
            continue
    return ids, stats


def backup_file(path: Path, root: Path, home: Path) -> str:
    relative = path.resolve().relative_to(home.resolve())
    destination = root / "files" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    return str(destination.relative_to(root))


def atomic_replace(path: Path, data: bytes, mode: int) -> None:
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.codex-migrate-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temporary, mode & 0o777)
        except OSError:
            pass
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def rewrite_jsonl(path: Path, thread_ids: set[str], sources: set[str], target: str) -> int:
    original = path.read_bytes()
    text = original.decode("utf-8")
    changed = 0
    output: list[str] = []
    for line in text.splitlines(keepends=True):
        newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
        body = line[: -len(newline)] if newline else line
        try:
            record = json.loads(body)
        except json.JSONDecodeError:
            output.append(line)
            continue
        payload = record.get("payload") if isinstance(record, dict) else None
        if (
            isinstance(record, dict)
            and record.get("type") == "session_meta"
            and isinstance(payload, dict)
            and payload.get("id") in thread_ids
            and payload.get("model_provider") in sources
        ):
            payload["model_provider"] = target
            body = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            changed += 1
        output.append(body + newline)
    if changed:
        atomic_replace(path, "".join(output).encode("utf-8"), path.stat().st_mode)
    return changed


def backup_database(path: Path, root: Path) -> str:
    destination = root / "state" / path.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(str(path), timeout=5)
    backup = sqlite3.connect(str(destination))
    try:
        source.execute("PRAGMA busy_timeout=5000")
        source.backup(backup)
        backup.commit()
    finally:
        backup.close()
        source.close()
    return str(destination.relative_to(root))


def migrate_database(path: Path, thread_ids: set[str], sources: set[str], target: str) -> int:
    if not path.is_file() or not thread_ids:
        return 0
    connection = sqlite3.connect(str(path), timeout=5)
    try:
        connection.execute("PRAGMA busy_timeout=5000")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "threads" not in tables:
            return 0
        columns = {row[1] for row in connection.execute("PRAGMA table_info(threads)")}
        if not {"id", "model_provider"}.issubset(columns):
            return 0
        ids = sorted(thread_ids)
        source_values = sorted(sources)
        id_marks = ",".join("?" for _ in ids)
        source_marks = ",".join("?" for _ in source_values)
        query = f"SELECT COUNT(*) FROM threads WHERE id IN ({id_marks}) AND model_provider IN ({source_marks})"
        count = int(connection.execute(query, ids + source_values).fetchone()[0])
        if count == 0:
            return 0
        update = f"UPDATE threads SET model_provider = ? WHERE id IN ({id_marks}) AND model_provider IN ({source_marks})"
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(update, [target] + ids + source_values)
        connection.commit()
        return count
    finally:
        connection.close()


def require_closed() -> None:
    if process_is_running():
        fail("Codex is running. Close Codex, Desktop, IDE integrations, and app-server, then rerun.")


def rollback(backup_root: Path, home: Path) -> None:
    manifest_path = backup_root / "manifest.json"
    if not manifest_path.is_file():
        fail(f"Migration manifest not found: {manifest_path}")
    require_closed()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest.get("files", []):
        destination = home / item["path"]
        source = backup_root / item["backup"]
        if source.is_file():
            atomic_replace(destination, source.read_bytes(), source.stat().st_mode)
    db = manifest.get("database")
    if isinstance(db, dict):
        destination = Path(db["path"])
        source = backup_root / db["backup"]
        if source.is_file():
            temporary = destination.with_suffix(destination.suffix + ".rollback-tmp")
            shutil.copy2(source, temporary)
            os.replace(temporary, destination)
    print(f"[OK] Rolled back migration from {backup_root}")


def run(args: argparse.Namespace) -> None:
    home = codex_home(args.codex_home)
    if args.rollback:
        rollback(Path(args.rollback).expanduser().resolve(), home)
        return
    if args.days <= 0:
        fail("--days must be greater than zero")
    if not args.target_provider or not args.source_provider:
        fail("Specify --target-provider and at least one --source-provider")
    target = args.target_provider.strip()
    sources = {value.strip() for value in args.source_provider if value.strip() and value.strip() != target}
    if not sources:
        fail("At least one source provider must differ from the target provider")
    cutoff = time.time() - args.days * 86400
    db_path = sqlite_home(home) / "state_5.sqlite"
    db_recent_ids = recent_sqlite_provider_threads(db_path, sources, cutoff)
    ids, stats = recent_provider_threads(home, sources, cutoff, db_recent_ids)
    # A current state DB is authoritative even when an old rollout has no
    # session_meta line that can be matched back to a JSONL file.
    ids.update(db_recent_ids)
    print(f"[INFO] Codex home: {home}")
    print(f"[INFO] Source providers: {', '.join(sorted(sources))}")
    print(f"[INFO] Target provider: {target}")
    print(f"[INFO] Recent thread ids: {len(ids)}; JSONL files: {len(stats)}")
    if args.dry_run:
        return
    if not args.yes:
        fail("Dry-run completed. Re-run with --yes after reviewing the counts.")
    require_closed()
    home.mkdir(parents=True, exist_ok=True)
    lock_path = home / ".codex-history-migrate.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        fail(f"Migration lock exists: {lock_path}")
    backup_root = home / "codex-history-migrations" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest: dict[str, Any] = {"version": 1, "home": str(home), "target": target, "sources": sorted(sources), "files": []}
    try:
        os.close(lock_fd)
        changed_json = 0
        for path, before in stats.items():
            current = path.stat()
            if current.st_mtime_ns != before.st_mtime_ns or current.st_size != before.st_size:
                fail(f"Session file changed during scan: {path}")
            backup = backup_file(path, backup_root, home)
            changed = rewrite_jsonl(path, ids, sources, target)
            if changed:
                manifest["files"].append({"path": str(path.relative_to(home)), "backup": backup, "sha256": sha256(path)})
                changed_json += changed
        changed_db = 0
        if db_path.is_file():
            connection = sqlite3.connect(str(db_path), timeout=5)
            try:
                columns = {row[1] for row in connection.execute("PRAGMA table_info(threads)")} if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='threads'").fetchone() else set()
            finally:
                connection.close()
            if {"id", "model_provider"}.issubset(columns):
                db_backup = backup_database(db_path, backup_root)
                changed_db = migrate_database(db_path, ids, sources, target)
                manifest["database"] = {"path": str(db_path), "backup": db_backup}
        if changed_json or changed_db:
            backup_root.mkdir(parents=True, exist_ok=True)
            (backup_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        else:
            # Backups are created before the final row-change count is known;
            # do not leave an apparently valid migration directory for a no-op.
            shutil.rmtree(backup_root, ignore_errors=True)
        print(f"[OK] Migrated JSONL metadata lines: {changed_json}; SQLite thread rows: {changed_db}")
        if changed_json or changed_db:
            print(f"[OK] Backup and rollback ledger: {backup_root}")
        print("[WARN] Encrypted reasoning content may not resume under a different provider even when history is visible.")
    finally:
        Path(lock_path).unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate recent Codex provider-bound history safely")
    parser.add_argument("--codex-home")
    parser.add_argument("--source-provider", action="append", default=[])
    parser.add_argument("--target-provider", default="")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--rollback")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
