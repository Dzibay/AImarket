"""РЎРѕР±РёСЂР°РµС‚ СѓСЃС‚Р°РЅРѕРІС‰РёРєРё РёР· installer/src РІ backend/app/web/downloads/setup.

Р—Р°РїСѓСЃРє РёР· РєРѕСЂРЅСЏ СЂРµРїРѕР·РёС‚РѕСЂРёСЏ:  python installer/build.py

РќР° РїСЂРѕРіСЂР°РјРјСѓ Рё СЃРёСЃС‚РµРјСѓ вЂ” РѕРґРёРЅ Р°СЂС…РёРІ, СЏР·С‹Рє СЃРєСЂРёРїС‚ РѕРїСЂРµРґРµР»СЏРµС‚ СЃР°Рј РїРѕ СЃРёСЃС‚РµРјРµ:
  aimarket-{app}-windows.zip   start.cmd + PowerShell-СЃРєСЂРёРїС‚
  aimarket-{app}-macos.zip     start.command + bash-СЃРєСЂРёРїС‚
  setup-aimarket-{app}.sh      РѕРґРёРЅ С„Р°Р№Р» РґР»СЏ Linux, РїСЂРѕРіСЂР°РјРјР° РІС€РёС‚Р° РІ APP=
"""

import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT.parent / "backend" / "app" / "web" / "downloads" / "setup"

# РЎРѕРІРїР°РґР°РµС‚ СЃРѕ СЃРїРёСЃРєРѕРј РІ bot/app/guide.py Рё frontend/src/components/SetupGuide.vue.
APPS = ["codex", "claude-code", "claude-desktop", "opencode", "hermes", "grok-build", "cursor"]
NO_LINUX = {"claude-desktop"}

# Р¤РёРєСЃРёСЂРѕРІР°РЅРЅР°СЏ РґР°С‚Р° РІРЅСѓС‚СЂРё zip: РїРµСЂРµСЃР±РѕСЂРєР° Р±РµР· РїСЂР°РІРѕРє РґР°С‘С‚ С‚РѕС‚ Р¶Рµ С„Р°Р№Р» Рё С‡РёСЃС‚С‹Р№ git diff.
ZIP_DATE = (2026, 1, 1, 0, 0, 0)

CODEX_EXTRAS = [
    "codex-history-migrate.py",
    "codex-image-tool/server.mjs",
    "codex-image-tool/server.ps1",
    "codex-image-tool/server.py",
    "codex-image-tool/SKILL.md",
]

START_CMD = """@echo off
setlocal
chcp 1251 >nul 2>nul
title aimarket setup
set "SCRIPT_DIR=%~dp0"
set "PS1_SCRIPT=%SCRIPT_DIR%{script}"
if not exist "%PS1_SCRIPT%" (
  echo [FAIL] {script} not found. Extract the whole archive, then run start.cmd again.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1_SCRIPT%"{args} %*
set "SETUP_EXIT_CODE=%ERRORLEVEL%"
echo.
echo Press any key to close this window.
pause >nul
exit /b %SETUP_EXIT_CODE%
"""

START_COMMAND = """#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SH_SCRIPT="$SCRIPT_DIR/{script}"

if [[ ! -f "$SH_SCRIPT" ]]; then
  printf '[FAIL] {script} was not found. Extract the whole archive, then run start.command again.\\n' >&2
  printf '\\nPress Enter to close this window.'
  read -r _ || true
  exit 1
fi

bash "$SH_SCRIPT"{args} "$@"
SETUP_EXIT_CODE=$?

printf '\\nPress Enter to close this window.'
read -r _ || true
exit "$SETUP_EXIT_CODE"
"""


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def raw(name: str) -> bytes:
    # РЎРєСЂРёРїС‚С‹ СЃРІРµСЂСЏСЋС‚ SHA-256 СЌС‚РёС… С„Р°Р№Р»РѕРІ, Р±Р°Р№С‚С‹ РЅРµР»СЊР·СЏ РјРµРЅСЏС‚СЊ.
    return (SRC / name).read_bytes()


def encode(name: str, body: str | bytes) -> bytes:
    if isinstance(body, bytes):
        return body
    if name.endswith(".cmd"):
        return body.replace("\n", "\r\n").encode("ascii")
    if name.endswith(".ps1") and not body.isascii():
        # Windows PowerShell 5.1 С‡РёС‚Р°РµС‚ .ps1 Р±РµР· BOM РєР°Рє ANSI Рё Р»РѕРјР°РµС‚ РєРёСЂРёР»Р»РёС†Сѓ.
        return body.encode("utf-8-sig")
    return body.encode("utf-8")


def windows_files(app: str) -> dict[str, str | bytes]:
    if app == "claude-desktop":
        script = "setup-aimarket-claude-desktop.ps1"
        files = {script: text(SRC / script)}
        files["start.cmd"] = START_CMD.format(script=script, args="")
        return files
    script = "setup-aimarket.ps1"
    files = {
        script: text(SRC / script),
        "setup-aimarket.en.json": text(SRC / "setup-aimarket.en.json"),
        "setup-aimarket.ru.json": text(SRC / "setup-aimarket.ru.json"),
        "start.cmd": START_CMD.format(script=script, args=f" -App {app}"),
    }
    if app == "codex":
        files.update({name: raw(name) for name in CODEX_EXTRAS})
    return files


def macos_files(app: str) -> dict[str, str | bytes]:
    if app == "claude-desktop":
        script = "setup-aimarket-claude-desktop.sh"
        return {
            script: text(SRC / script),
            "start.command": START_COMMAND.format(script=script, args=""),
        }
    script = "setup-aimarket.sh"
    files = {
        script: text(SRC / script),
        "start.command": START_COMMAND.format(script=script, args=f" --app {app}"),
    }
    if app == "codex":
        files.update({name: raw(name) for name in CODEX_EXTRAS})
    return files


def linux_script(app: str) -> str:
    body, count = re.subn(r'^APP=""$', f'APP="{app}"', text(SRC / "setup-aimarket.sh"), count=1, flags=re.M)
    if count != 1:
        raise SystemExit('setup-aimarket.sh: СЃС‚СЂРѕРєР° APP="" РЅРµ РЅР°Р№РґРµРЅР°')
    return body


def write_zip(path: Path, files: dict[str, str | bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            executable = name.endswith((".sh", ".command"))
            info.external_attr = (0o100755 if executable else 0o100644) << 16
            info.create_system = 3
            archive.writestr(info, encode(name, files[name]))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.iterdir():
        if old.is_file() and old.suffix in {".zip", ".sh"}:
            old.unlink()
        elif old.is_dir():
            shutil.rmtree(old)
    built = []
    for app in APPS:
        for system, files in (("windows", windows_files(app)), ("macos", macos_files(app))):
            target = OUT / f"aimarket-{app}-{system}.zip"
            write_zip(target, files)
            built.append(target)
        if app not in NO_LINUX:
            target = OUT / f"setup-aimarket-{app}.sh"
            target.write_bytes(encode(target.name, linux_script(app)))
            built.append(target)
    for path in built:
        print(f"{path.relative_to(ROOT.parent)}  {path.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
