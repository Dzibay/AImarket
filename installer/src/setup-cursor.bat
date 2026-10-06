@echo off
setlocal DisableDelayedExpansion
if not defined SystemRoot set "SystemRoot=C:\Windows"
set "PATH=%SystemRoot%\System32;%SystemRoot%\System32\WindowsPowerShell\v1.0;%PATH%"
chcp 65001 >nul
set "CURSOR_SETUP_FILE=%~f0"
if not exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
  echo [FAIL] PowerShell 5.1 не найден.
  pause
  exit /b 1
)
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { $path=$env:CURSOR_SETUP_FILE; if (-not (Test-Path -LiteralPath $path)) { throw ('File not found: ' + $path) }; $s=[IO.File]::ReadAllText($path,[Text.Encoding]::UTF8); $parts=$s -split '(?m)^# CURSOR_SETUP_POWERSHELL\r?$',2; if ($parts.Count -lt 2) { throw 'Installer payload missing. Re-download setup-cursor.bat.' }; & ([scriptblock]::Create($parts[1])) } catch { Write-Host ('STARTUP ERROR: ' + $_.Exception.Message); if ($_.ScriptStackTrace) { Write-Host $_.ScriptStackTrace }; exit 1 }"
set "CURSOR_SETUP_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %CURSOR_SETUP_EXIT%
# CURSOR_SETUP_POWERSHELL
#Requires -Version 5.1
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

function Fail([string]$Message) { throw $Message }
function Ok([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }
function Info([string]$Message) { Write-Host $Message }

function Mask-Key([string]$Key) {
    if ($Key.Length -le 12) { return 'sk-****' }
    return $Key.Substring(0, 7) + '...' + $Key.Substring($Key.Length - 4)
}

function Hide-Secrets([string]$Message, [string]$Key) {
    if ([string]::IsNullOrWhiteSpace($Message)) { return $Message }
    if ($Key) { $Message = $Message.Replace($Key, '[СКРЫТО]') }
    return $Message
}

function Normalize-BaseUrl([string]$Value) {
    $url = $Value.Trim().TrimEnd('/')
    if ($url -match '/(chat/completions|responses)$') {
        Fail 'Нужен Base URL вида https://host/v1, а не полный путь chat/completions.'
    }
    if ($url -notmatch '^https?://') { Fail 'Адрес должен начинаться с http:// или https://.' }
    if (-not $url.EndsWith('/v1')) { $url = "$url/v1" }
    [void][Uri]$url
    return $url
}

function Read-PromptLine([string]$Prompt) {
    if ([Console]::IsInputRedirected) {
        Fail 'Нужен интерактивный запуск: двойной щелчок в Проводнике или окно cmd/PowerShell, не пайп и не фоновый агент.'
    }
    $value = Read-Host $Prompt
    if ($null -eq $value) { return '' }
    return $value.Trim().Trim('"', "'")
}

function Read-Secret([string]$Prompt) {
    if ([Console]::IsInputRedirected) {
        Fail 'Нужен интерактивный запуск: двойной щелчок в Проводнике или окно cmd/PowerShell, не пайп и не фоновый агент.'
    }
    $secure = Read-Host $Prompt -AsSecureString
    if ($null -eq $secure) { return '' }
    $plain = (New-Object Management.Automation.PSCredential('x', $secure)).GetNetworkCredential().Password
    if ($null -eq $plain) { return '' }
    return $plain.Trim().Trim('"', "'")
}

function ConvertTo-JsonStringArray([string[]]$Values) {
    $parts = New-Object System.Collections.Generic.List[string]
    foreach ($value in @($Values)) {
        if ([string]::IsNullOrWhiteSpace($value) -or $value -match '\s') { continue }
        $parts.Add((ConvertTo-Json -InputObject ([string]$value) -Compress))
    }
    return ('[' + ($parts.ToArray() -join ',') + ']')
}

function Get-Models([string]$BaseUrl, [string]$Key) {
    if ($Key -notmatch '^sk-[A-Za-z0-9_-]{10,}$') {
        Fail 'Нужен полный ключ, начинающийся с sk-, без кавычек и Bearer.'
    }
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri ($BaseUrl.TrimEnd('/') + '/models') -Headers @{ Authorization = ('Bearer ' + $Key) } -TimeoutSec 30 -MaximumRedirection 0
    } catch [Net.WebException] {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        if ($status -eq 401 -or $status -eq 403) { return [string[]]@() }
        Fail "Проверка API не прошла (HTTP $status). Проверьте адрес, интернет и ключ."
    }
    $ids = New-Object System.Collections.Generic.List[string]
    foreach ($item in @((ConvertFrom-Json -InputObject $response.Content).data)) {
        $id = [string]$item.id
        if (-not $id -or ($id -match '\s') -or ($id -match '(?i)^(claude-|gemini-)') -or ($id -match '(?i)image')) { continue }
        $ids.Add($id)
    }
    return $ids.ToArray()
}

function Close-Cursor {
    $running = @(Get-Process -Name 'Cursor' -ErrorAction SilentlyContinue)
    if ($running.Count -eq 0) { return }
    if (-not [string]::IsNullOrWhiteSpace($env:CURSOR_TRACE_ID) -or $env:TERM_PROGRAM -eq 'vscode') {
        Fail 'Запустите этот файл не из встроенного терминала Cursor, а из Проводника или обычного PowerShell.'
    }
    $answer = (Read-Host 'Cursor сейчас открыт. Закрыть его для настройки? Enter = да, n = нет').Trim()
    if ($answer -match '^(n|no|н|нет)$') { Fail 'Закройте Cursor полностью и запустите файл снова.' }
    Info 'Закрываю Cursor...'
    foreach ($process in $running) {
        try { if ($process.MainWindowHandle -ne [IntPtr]::Zero) { [void]$process.CloseMainWindow() } } catch {}
    }
    for ($i = 0; $i -lt 20; $i++) {
        if (@(Get-Process -Name 'Cursor' -ErrorAction SilentlyContinue).Count -eq 0) { return }
        Start-Sleep -Seconds 1
    }
    Fail 'Cursor всё ещё запущен (в том числе в трее). Закройте его и повторите.'
}

function Get-CursorStorageInfo {
    $databasePath = if ($env:APPDATA) { Join-Path $env:APPDATA 'Cursor\User\globalStorage\state.vscdb' } else { '' }
    $roots = New-Object System.Collections.Generic.List[string]
    foreach ($base in @($env:LOCALAPPDATA, $env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if ([string]::IsNullOrWhiteSpace($base)) { continue }
        $roots.Add((Join-Path $base 'Programs\cursor\resources\app'))
        $roots.Add((Join-Path $base 'Cursor\resources\app'))
    }
    foreach ($root in $roots) {
        $nodePath = Join-Path $root 'resources\helpers\node.exe'
        $modulePath = Join-Path $root 'node_modules\@vscode\sqlite3'
        if ((Test-Path -LiteralPath $databasePath -PathType Leaf) -and
            (Test-Path -LiteralPath $nodePath -PathType Leaf) -and
            (Test-Path -LiteralPath $modulePath -PathType Container)) {
            return [pscustomobject]@{ DatabasePath = $databasePath; NodePath = $nodePath; SqliteModulePath = $modulePath }
        }
    }
    Fail 'Cursor не найден. Установите Cursor, один раз откройте его и закройте — затем запустите этот файл снова.'
}

function Backup-CursorDatabase($Info) {
    $backupDirectory = "$($Info.DatabasePath).setup-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
    New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
    foreach ($path in @($Info.DatabasePath, "$($Info.DatabasePath)-wal", "$($Info.DatabasePath)-shm")) {
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Copy-Item -LiteralPath $path -Destination (Join-Path $backupDirectory ([IO.Path]::GetFileName($path)))
        }
    }
    Ok "Резервная копия базы Cursor: $backupDirectory"
}

function Write-CursorConfig([string]$Key, [string]$Endpoint, [string[]]$Models) {
    if (@(Get-Process -Name 'Cursor' -ErrorAction SilentlyContinue).Count -ne 0) {
        Fail 'Cursor всё ещё запущен. Закройте его и повторите.'
    }
    $info = Get-CursorStorageInfo
    Backup-CursorDatabase $info
    $helperPath = $null
    $modelsPath = $null
    $previousKey = [Environment]::GetEnvironmentVariable('AIMARKET_CURSOR_SETUP_KEY', 'Process')
    $helperPath = [IO.Path]::GetTempFileName() + '.js'
    $modelsPath = [IO.Path]::GetTempFileName()
    try {
        $modelsJson = ConvertTo-JsonStringArray $Models
        if ($modelsJson -eq '[]') { Fail 'Список моделей для Cursor пуст.' }
        [IO.File]::WriteAllText($modelsPath, $modelsJson, [Text.UTF8Encoding]::new($false))
        $helper = @'
"use strict";
const fs = require("fs");
const sqlite3 = require(process.argv[2]);
const databasePath = process.argv[3];
const action = process.argv[4];
const endpoint = process.argv[5];
const owner = process.argv[6];
const modelsPath = process.argv[7];
const applicationKey = "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser";
const apiKeyStorageKey = "cursorAuth/openAIKey";
const setupStateKey = "cheap-router/cursorSetupState.v1";
function openDatabase() {
  return new Promise((resolve, reject) => {
    const database = new sqlite3.Database(databasePath, sqlite3.OPEN_READWRITE, error => error ? reject(error) : resolve(database));
  });
}
function get(database, sql, params = []) {
  return new Promise((resolve, reject) => database.get(sql, params, (error, row) => error ? reject(error) : resolve(row)));
}
function run(database, sql, params = []) {
  return new Promise((resolve, reject) => database.run(sql, params, function(error) {
    if (error) reject(error); else resolve({ changes: this.changes });
  }));
}
function close(database) {
  return new Promise((resolve, reject) => database.close(error => error ? reject(error) : resolve()));
}
function clone(value) { return value === undefined ? undefined : JSON.parse(JSON.stringify(value)); }
function capture(object, property) {
  return Object.prototype.hasOwnProperty.call(object, property) ? { exists: true, value: clone(object[property]) } : { exists: false };
}
function stringArray(value, label) {
  if (value === undefined) return [];
  if (!Array.isArray(value) || !value.every(item => typeof item === "string")) {
    throw new TypeError("Cursor setting '" + label + "' must be an array of strings");
  }
  return [...value];
}
function isCursorBuiltinModel(id) {
  const name = String(id).trim().toLowerCase();
  if (!name) return false;
  if (/^(claude-|gemini-|composer-|cursor-)/.test(name)) return true;
  if (/^gpt-[456]/.test(name)) return true;
  if (/^grok-\d/.test(name)) return true;
  if (/^kimi-k\d/.test(name)) return true;
  if (/^o[1-9]([.\-]|$)/.test(name)) return true;
  return false;
}
async function upsert(database, key, value) {
  const updated = await run(database, "UPDATE ItemTable SET value = ? WHERE key = ?", [value, key]);
  if (updated.changes === 0) await run(database, "INSERT INTO ItemTable(key, value) VALUES(?, ?)", [key, value]);
}
async function main() {
  const database = await openDatabase();
  let transaction = false;
  try {
    await run(database, "BEGIN IMMEDIATE");
    transaction = true;
    const applicationRow = await get(database, "SELECT value FROM ItemTable WHERE key = ?", [applicationKey]);
    if (!applicationRow) throw new Error("Cursor application settings row was not found");
    const application = JSON.parse(String(applicationRow.value));
    if (!application || typeof application !== "object" || Array.isArray(application)) {
      throw new TypeError("Cursor application settings must be a JSON object");
    }
    const stateRow = await get(database, "SELECT value FROM ItemTable WHERE key = ?", [setupStateKey]);
    let state = stateRow ? JSON.parse(String(stateRow.value)) : null;
    if (state && state.version !== 1) throw new Error("Unsupported managed Cursor setup state version");
    const apiKey = process.env.AIMARKET_CURSOR_SETUP_KEY || "";
    if (!apiKey.startsWith("sk-")) throw new Error("Cursor setup API key is missing or malformed");
    const models = JSON.parse(fs.readFileSync(modelsPath, "utf8"));
    if (!Array.isArray(models) || models.length === 0 || !models.every(item => typeof item === "string" && item.trim())) {
      throw new TypeError("Cursor setup model catalog is empty or malformed");
    }
    const uniqueModels = [...new Set(models.flatMap(item => String(item).split(/\s+/)).map(item => item.trim()).filter(item => item && !/\s/.test(item)))];
    if (uniqueModels.length === 0) throw new TypeError("Cursor setup model catalog is empty or malformed");
    const apiKeyRow = await get(database, "SELECT value FROM ItemTable WHERE key = ?", [apiKeyStorageKey]);
    const aiSettingsExists = Object.prototype.hasOwnProperty.call(application, "aiSettings");
    if (aiSettingsExists && (!application.aiSettings || typeof application.aiSettings !== "object" || Array.isArray(application.aiSettings))) {
      throw new TypeError("Cursor setting 'aiSettings' must be a JSON object");
    }
    if (!state) {
      const aiSettings = aiSettingsExists ? application.aiSettings : {};
      state = {
        version: 1,
        owner,
        managedModels: [],
        original: {
          application: {
            openAIBaseUrl: capture(application, "openAIBaseUrl"),
            useOpenAIKey: capture(application, "useOpenAIKey"),
            aiSettingsExists,
            userAddedModels: capture(aiSettings, "userAddedModels"),
            modelOverrideEnabled: capture(aiSettings, "modelOverrideEnabled"),
            modelOverrideDisabled: capture(aiSettings, "modelOverrideDisabled")
          },
          apiKey: apiKeyRow ? { exists: true, value: String(apiKeyRow.value) } : { exists: false }
        }
      };
    }
    if (!application.aiSettings || typeof application.aiSettings !== "object" || Array.isArray(application.aiSettings)) application.aiSettings = {};
    const previousManaged = new Set(Array.isArray(state.managedModels) ? state.managedModels : []);
    const currentManaged = new Set(uniqueModels);
    const originalAdded = new Set(stringArray(state.original.application.userAddedModels.exists ? state.original.application.userAddedModels.value : undefined, "managed original userAddedModels"));
    const originalEnabled = new Set(stringArray(state.original.application.modelOverrideEnabled.exists ? state.original.application.modelOverrideEnabled.value : undefined, "managed original modelOverrideEnabled"));
    const keep = (value, originals) => !previousManaged.has(value) || currentManaged.has(value) || originals.has(value);
    const added = stringArray(application.aiSettings.userAddedModels, "aiSettings.userAddedModels").filter(value => keep(value, originalAdded) && !/\s/.test(value) && !isCursorBuiltinModel(value));
    const enabled = stringArray(application.aiSettings.modelOverrideEnabled, "aiSettings.modelOverrideEnabled").filter(value => keep(value, originalEnabled) && !/\s/.test(value) && (!previousManaged.has(value) || isCursorBuiltinModel(value)));
    const disabled = stringArray(application.aiSettings.modelOverrideDisabled, "aiSettings.modelOverrideDisabled").filter(value => !currentManaged.has(value));
    for (const model of uniqueModels) {
      if (isCursorBuiltinModel(model)) {
        if (!enabled.includes(model)) enabled.push(model);
        continue;
      }
      if (!added.includes(model)) added.push(model);
    }
    application.openAIBaseUrl = endpoint;
    application.useOpenAIKey = true;
    application.aiSettings.userAddedModels = added;
    application.aiSettings.modelOverrideEnabled = enabled;
    application.aiSettings.modelOverrideDisabled = disabled;
    state.owner = owner;
    state.managedModels = uniqueModels;
    await upsert(database, applicationKey, JSON.stringify(application));
    await upsert(database, apiKeyStorageKey, apiKey);
    await upsert(database, setupStateKey, JSON.stringify(state));
    await run(database, "COMMIT");
    transaction = false;
    process.stdout.write(JSON.stringify({ status: "configured", modelCount: uniqueModels.length }));
  } catch (error) {
    if (transaction) { try { await run(database, "ROLLBACK"); } catch (_) {} }
    throw error;
  } finally {
    await close(database);
  }
}
main().catch(error => {
  process.stderr.write(String(error && error.stack ? error.stack : error));
  process.exitCode = 1;
});
'@
        [IO.File]::WriteAllText($helperPath, $helper, [Text.UTF8Encoding]::new($false))
        [Environment]::SetEnvironmentVariable('AIMARKET_CURSOR_SETUP_KEY', $Key, 'Process')
        $output = @(& $info.NodePath $helperPath $info.SqliteModulePath $info.DatabasePath 'setup' $Endpoint 'aimarket' $modelsPath 2>&1)
        if ($LASTEXITCODE -ne 0) { Fail ("Не удалось записать настройки Cursor: " + ($output -join [Environment]::NewLine)) }
        $json = [string]@($output | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })[-1]
        $result = $json | ConvertFrom-Json
        if ([string]$result.status -ne 'configured') { Fail "Неожиданный результат настройки: $($result.status)" }
        return [int]$result.modelCount
    } finally {
        [Environment]::SetEnvironmentVariable('AIMARKET_CURSOR_SETUP_KEY', $previousKey, 'Process')
        foreach ($tempPath in @($helperPath, $modelsPath)) {
            if (-not [string]::IsNullOrWhiteSpace($tempPath) -and (Test-Path -LiteralPath $tempPath)) {
                Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

$apiKey = $null
try {
    Write-Host ''
    Write-Host 'Настройка Cursor (OpenAI-compatible API)' -ForegroundColor Cyan
    Write-Host 'Скрипт спросит адрес и ключ, проверит их и пропишет в Cursor.'
    Write-Host 'Чаты не трогаются. Claude и Gemini через этот Base URL в Cursor не подключаются.'
    Write-Host ''

    $rawUrl = Read-PromptLine 'Base URL (например https://positionapi.top/v1)'
    if (-not $rawUrl) { Fail 'Адрес не введён.' }
    $endpoint = Normalize-BaseUrl $rawUrl
    Ok "Адрес: $endpoint"

    $models = New-Object System.Collections.Generic.List[string]
    while ($models.Count -eq 0) {
        $apiKey = Read-Secret 'API-ключ (ввод скрыт, начинается с sk-)'
        if (-not $apiKey) { Fail 'Ключ не введён. Настройки Cursor не изменены.' }
        if ($apiKey -notmatch '^sk-[A-Za-z0-9_-]{10,}$') {
            Write-Host 'Нужен полный ключ, начинающийся с sk-, без кавычек и Bearer.' -ForegroundColor Yellow
            continue
        }
        Write-Host 'Проверяю ключ (GET /v1/models, без платной генерации)...'
        foreach ($id in @(Get-Models $endpoint $apiKey)) { $models.Add($id) }
        if ($models.Count -eq 0) {
            Write-Host 'Ключ не принят или нет совместимых с Cursor моделей (GPT/Grok и т.п.).' -ForegroundColor Yellow
        }
    }
    Ok ("Ключ принят: " + (Mask-Key $apiKey) + ". Моделей для Cursor: " + $models.Count)

    Close-Cursor
    $count = Write-CursorConfig $apiKey $endpoint $models.ToArray()
    Ok "В Cursor записаны ключ, Base URL и $count моделей."
    Write-Host ''
    Write-Host 'Откройте Cursor и отправьте пробный запрос. Если Cursor был открыт — он уже закрыт, запустите его снова.'
} catch {
    $message = Hide-Secrets $_.Exception.Message $apiKey
    Write-Host ("ОШИБКА: " + $message) -ForegroundColor Red
    if ($_.ScriptStackTrace) { Write-Host $_.ScriptStackTrace }
    exit 1
}
exit 0
