"""Установка одной командой: одноразовая ссылка /i/{token} отдаёт короткий скрипт.

Скрипт скачивает архив установщика, кладёт его в постоянную папку пользователя
(рядом остаются вспомогательные файлы Codex) и запускает с ключом в переменной
AIMARKET_SETUP_KEY — ключ не попадает ни в историю команд, ни на диск.
"""

import secrets

from app.billing import BillingError, describe_key
from app.db import pool
from app.settings_store import public_base_url
from app.web_auth import key_hash

TOKEN_TTL_SEC = 15 * 60

# Совпадает со списком в installer/build.py.
APPS = {
    "codex": "Codex",
    "claude-code": "Claude Code",
    "claude-desktop": "Claude Desktop",
    "opencode": "OpenCode",
    "hermes": "Hermes",
    "grok-build": "Grok Build",
    "cursor": "Cursor",
}
SYSTEMS = {"windows", "macos", "linux"}
ACTIONS = {"setup", "setup-reserve", "restore"}


class InstallError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def create_install_command(user_id: int, app: str, system: str, action: str) -> dict:
    if app not in APPS or system not in SYSTEMS or action not in ACTIONS:
        raise InstallError("unknown")
    if app == "claude-desktop" and system == "linux":
        raise InstallError("unknown")
    base = public_base_url()
    if not base:
        raise InstallError("no-site")
    _user_key(user_id)
    token = secrets.token_urlsafe(18)
    with pool.connection() as conn:
        conn.execute("DELETE FROM install_tokens WHERE expires_at < NOW()")
        conn.execute(
            """
            INSERT INTO install_tokens (token_hash, user_id, app, os, action, expires_at)
            VALUES (%s, %s, %s, %s, %s, NOW() + make_interval(secs => %s))
            """,
            (key_hash(token), user_id, app, system, action, TOKEN_TTL_SEC),
        )
    url = f"{base}/i/{token}"
    if system == "windows":
        command = f'powershell -NoProfile -ExecutionPolicy Bypass -NoExit -Command "irm {url} | iex"'
    else:
        command = f"bash <(curl -fsSL {url})"
    return {"command": command, "expires_in": TOKEN_TTL_SEC}


def bootstrap_script(token: str) -> tuple[str, str] | None:
    """Возвращает (система, текст скрипта) или None, если ссылка неизвестна или истекла."""
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT user_id, app, os, action FROM install_tokens
            WHERE token_hash = %s AND expires_at > NOW()
            """,
            (key_hash(token),),
        ).fetchone()
    if row is None:
        return None
    app, system, action = str(row["app"]), str(row["os"]), str(row["action"])
    try:
        key = "" if action == "restore" else _user_key(int(row["user_id"]))
    except InstallError:
        return None
    base = public_base_url()
    if system == "windows":
        return system, _windows(base, app, action, key)
    return system, _unix(base, app, system, action, key)


def _user_key(user_id: int) -> str:
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT k.secret, u.blocked_at
            FROM users u
            LEFT JOIN api_keys k ON k.user_id = u.id AND k.revoked_at IS NULL AND k.upstream_id IS NOT NULL
            WHERE u.id = %s
            """,
            (user_id,),
        ).fetchone()
    if row is None or row["blocked_at"] is not None:
        raise InstallError("blocked")
    secret = str(row["secret"] or "")
    if secret:
        return secret
    try:
        secret = str(describe_key(user_id).get("secret") or "")
    except BillingError as exc:
        raise InstallError(exc.code) from exc
    if not secret:
        raise InstallError("no-key")
    return secret


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _windows(base: str, app: str, action: str, key: str) -> str:
    if app == "claude-desktop":
        script, args = "setup-aimarket-claude-desktop.ps1", f"-Action {action}"
    else:
        script, args = "setup-aimarket.ps1", f"-App {app} -Action {action}"
    folder = _ps_quote("aimarket\\setup\\" + app)
    title = _ps_quote(f"aimarket: {APPS[app]} setup")
    zip_url = _ps_quote(f"{base}/downloads/setup/aimarket-{app}-windows.zip")
    return f"""& {{
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$dir = Join-Path $env:LOCALAPPDATA {folder}
Write-Host {title}
if (Test-Path -LiteralPath $dir) {{ Remove-Item -LiteralPath $dir -Recurse -Force }}
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$zip = Join-Path $dir 'setup.zip'
Invoke-WebRequest -UseBasicParsing -Uri {zip_url} -OutFile $zip
Expand-Archive -LiteralPath $zip -DestinationPath $dir -Force
Remove-Item -LiteralPath $zip -Force
$env:AIMARKET_SETUP_KEY = {_ps_quote(key)}
try {{
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $dir {_ps_quote(script)}) {args}
}} finally {{
    Remove-Item Env:AIMARKET_SETUP_KEY -ErrorAction SilentlyContinue
}}
}}
"""


def _unix(base: str, app: str, system: str, action: str, key: str) -> str:
    if system == "linux":
        url = _sh_quote(f"{base}/downloads/setup/setup-aimarket-{app}.sh")
        fetch = f'curl -fsSL {url} -o "$dir/setup-aimarket.sh"'
        script, args = "setup-aimarket.sh", f"--app {app} --action {action}"
    else:
        url = _sh_quote(f"{base}/downloads/setup/aimarket-{app}-macos.zip")
        fetch = (
            f'curl -fsSL {url} -o "$dir/setup.zip"\n'
            'unzip -q -o "$dir/setup.zip" -d "$dir"\n'
            'rm -f "$dir/setup.zip"'
        )
        if app == "claude-desktop":
            script, args = "setup-aimarket-claude-desktop.sh", f"--action {action}"
        else:
            script, args = "setup-aimarket.sh", f"--app {app} --action {action}"
    title = _sh_quote(f"aimarket: {APPS[app]} setup")
    return f"""#!/usr/bin/env bash
set -euo pipefail
dir="$HOME/.aimarket/setup/{app}"
printf '%s\\n' {title}
rm -rf "$dir"
mkdir -p "$dir"
{fetch}
AIMARKET_SETUP_KEY={_sh_quote(key)} bash "$dir/{script}" {args}
"""
