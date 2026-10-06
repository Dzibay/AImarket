<#
Safely configures Claude Desktop's managed 3P inference profile for aimarket.

This intentionally does not touch Claude account, chat, IndexedDB, Local Storage,
or Claude Code session files. Before setup and restore it copies the known local
history stores to a user-private safety-backup directory unless explicitly skipped.
#>

[CmdletBinding()]
param(
    [ValidateSet("en", "ru")]
    [string]$Lang = "",
    [ValidateSet("", "setup", "setup-reserve", "restore")]
    [string]$Action = "",
    [string]$ApiKey = "",
    [string]$Endpoint = "https://router.cheap",
    [switch]$SkipEndpointTest,
    [switch]$SkipHistoryBackup,
    [switch]$DryRun,
    [string]$NormalConfigDirectory = "",
    [string]$ThreePConfigDirectory = "",
    [string]$BackupDirectory = "",
    [string[]]$HistoryDataDirectories = @()
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$script:ProfileId = "7c532ace-9355-4acb-a881-3bcf5d893c41"
$script:ProfileName = "aimarket"
$script:ScriptVersion = "1.4"
$script:NetworkPhase = $false
$script:PreferredModels = @(
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-opus-4-8",
    "claude-haiku-4-5",
    "claude-fable-5",
    "claude-mythos-5",
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-opus-4-6"
)

if ([string]::IsNullOrWhiteSpace($Lang)) {
    $Lang = if ([Globalization.CultureInfo]::CurrentUICulture.TwoLetterISOLanguageName -eq "ru") { "ru" } else { "en" }
}

$script:RussianMessagesJson = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(
    "eyJ0aXRsZSI6ItCd0LDRgdGC0YDQvtC50LrQsCBDbGF1ZGUgRGVza3RvcCDQtNC70Y8gcm91dGVyLmNoZWFwIiwiY2hvb3NlIjoi0JLRi9Cx0LXRgNC40YLQtSDQtNC10LnRgdGC0LLQuNC1OiIsInNldHVwIjoi0J3QsNGB0YLRgNC+0LjRgtGMIENsYXVkZSBEZXNrdG9wINC00LvRjyByb3V0ZXIuY2hlYXAiLCJyZXN0b3JlIjoi0JLQtdGA0L3Rg9GC0Ywg0L/RgNC10LTRi9C00YPRidC40Lkv0L7RhNC40YbQuNCw0LvRjNC90YvQuSDQv9GA0L7RhNC40LvRjCBDbGF1ZGUgRGVza3RvcCIsImV4aXQiOiLQktGL0LnRgtC4IiwiaW52YWxpZCI6ItCd0LXQstC10YDQvdGL0Lkg0LLRi9Cx0L7RgC4iLCJjbG9zZSI6ItCf0L7Qu9C90L7RgdGC0YzRjiDQt9Cw0LrRgNC+0LnRgtC1IENsYXVkZSBEZXNrdG9wINC4INC30LDQv9GD0YHRgtC40YLQtSDRgdC60YDQuNC/0YIg0YHQvdC+0LLQsC4g0J/RgNC40LvQvtC20LXQvdC40LUg0LTQvtC70LbQvdC+INCx0YvRgtGMINC30LDQutGA0YvRgtC+LCDRh9GC0L7QsdGLINC40YHRgtC+0YDQuNGPINC4INC90LDRgdGC0YDQvtC50LrQuCDQvtGB0YLQsNCy0LDQu9C40YHRjCDRhtC10LvRi9C80LguIiwia2V5Ijoi0JLRgdGC0LDQstGM0YLQtSBBUEkt0LrQu9GO0Ycgcm91dGVyLmNoZWFwICjQstCy0L7QtCDRgdC60YDRi9GCKSIsInRlc3RpbmciOiLQn9GA0L7QstC10YDRj9GOIEFudGhyb3BpYy3RgdC+0LLQvNC10YHRgtC40LzRi9C5INGI0LvRjtC3IiwiYmFja3VwIjoi0KHQvtC30LTQsNGOINGA0LXQt9C10YDQstC90YPRjiDQutC+0L/QuNGOINC90LDRgdGC0YDQvtC10Log0Lgg0LvQvtC60LDQu9GM0L3QvtC5INC40YHRgtC+0YDQuNC4L9GB0LXRgdGB0LjQuSBDbGF1ZGUgRGVza3RvcCIsImJhY2t1cERvbmUiOiLQoNC10LfQtdGA0LLQvdCw0Y8g0LrQvtC/0LjRjzoge3BhdGh9IiwiYmFja3VwU2tpcHBlZCI6ItCa0L7Qv9C40YDQvtCy0LDQvdC40LUg0LvQvtC60LDQu9GM0L3QvtC5INC40YHRgtC+0YDQuNC4L9GB0LXRgdGB0LjQuSDRj9Cy0L3QviDQv9GA0L7Qv9GD0YnQtdC90L47INGE0LDQudC70Ysg0LrQvtC90YTQuNCz0YPRgNCw0YbQuNC4INCy0YHRkSDRgNCw0LLQvdC+INCx0YPQtNGD0YIg0YHQvtGF0YDQsNC90LXQvdGLLiIsIm5vSGlzdG9yeSI6ItCb0L7QutCw0LvRjNC90YvQtSDRhdGA0LDQvdC40LvQuNGJ0LAg0LjRgdGC0L7RgNC40Lgv0YHQtdGB0YHQuNC5IENsYXVkZSDQvdC1INC90LDQudC00LXQvdGLLiDQmtC+0L3RhNC40LPRg9GA0LDRhtC40Y8g0LLRgdGRINGA0LDQstC90L4g0LHRg9C00LXRgiDRgdC+0YXRgNCw0L3QtdC90LAuIiwiY29uZmlndXJpbmciOiLQl9Cw0L/QuNGB0YvQstCw0Y4g0YPQv9GA0LDQstC70Y/QtdC80YvQuSAzUC3Qv9GA0L7RhNC40LvRjCBDbGF1ZGUgRGVza3RvcCIsInJlc3RvcmluZyI6ItCj0LTQsNC70Y/RjiDRgtC+0LvRjNC60L4g0L/RgNC+0YTQuNC70Ywgcm91dGVyLmNoZWFwINC4INCy0L7Qt9Cy0YDQsNGJ0LDRjiDQv9GA0LXQtNGL0LTRg9GJ0LjQuSDQstGL0LHQvtGAIiwiZG9uZSI6ItCT0L7RgtC+0LLQvi4g0KXRgNCw0L3QuNC70LjRidCwINGH0LDRgtC+0LIg0Lgg0YHQtdGB0YHQuNC5INC90LUg0LjQt9C80LXQvdGP0LvQuNGB0YwuINCf0L7Qu9C90L7RgdGC0YzRjiDQt9Cw0LrRgNC+0LnRgtC1INC4INGB0L3QvtCy0LAg0L7RgtC60YDQvtC50YLQtSBDbGF1ZGUgRGVza3RvcC4iLCJyZXN0b3JlZCI6ItCS0L7RgdGB0YLQsNC90L7QstC70LXQvdC+LiDQpdGA0LDQvdC40LvQuNGJ0LAg0YfQsNGC0L7QsiDQuCDRgdC10YHRgdC40Lkg0L3QtSDQuNC30LzQtdC90Y/Qu9C40YHRjC4g0J/QvtC70L3QvtGB0YLRjNGOINC30LDQutGA0L7QudGC0LUg0Lgg0YHQvdC+0LLQsCDQvtGC0LrRgNC+0LnRgtC1IENsYXVkZSBEZXNrdG9wLiIsIm5vdGhpbmciOiLQn9GA0L7RhNC40LvRjCByb3V0ZXIuY2hlYXAg0LTQu9GPIENsYXVkZSBEZXNrdG9wINC90LUg0YPRgdGC0LDQvdC+0LLQu9C10L07INC90LjRh9C10LPQviDQvdC1INC40LfQvNC10L3QtdC90L4uIiwicGxhaW50ZXh0IjoiQ2xhdWRlIERlc2t0b3Ag0YLRgNC10LHRg9C10YIg0YXRgNCw0L3QuNGC0Ywg0LrQu9GO0Ycg0YjQu9GO0LfQsCDQsiDQu9C+0LrQsNC70YzQvdC+0Lwg0L/RgNC+0YTQuNC70LUuINCf0YDQvtGE0LjQu9GMINC4INGA0LXQt9C10YDQstC90YvQtSDQutC+0L/QuNC4INC90LDRhdC+0LTRj9GC0YHRjyDQstC90YPRgtGA0Lgg0LLQsNGI0LXQuSDRg9GH0ZHRgtC90L7QuSDQt9Cw0L/QuNGB0Lgg0J7QoS4iLCJtb2RlbHMiOiLQnNC+0LTQtdC70LggQ2xhdWRlIERlc2t0b3A6IHttb2RlbHN9IiwiZHJ5UnVuIjoi0J/RgNC+0LLQtdGA0L7Rh9C90YvQuSDQt9Cw0L/Rg9GB0Lo6INGE0LDQudC70Ysg0L3QtSDQuNC30LzQtdC90LXQvdGLLiIsImJhY2t1cFNwYWNlIjoi0J3QtdC00L7RgdGC0LDRgtC+0YfQvdC+INGB0LLQvtCx0L7QtNC90L7Qs9C+INC80LXRgdGC0LAg0LTQu9GPINGA0LXQt9C10YDQstC90L7QuSDQutC+0L/QuNC4LiDQndGD0LbQvdC+INC/0YDQuNC80LXRgNC90L4ge3JlcXVpcmVkfSDQnNC40JEsINC00L7RgdGC0YPQv9C90L4ge2F2YWlsYWJsZX0g0JzQuNCRLiJ9"
)) | ConvertFrom-Json
$script:RussianInvalidKeyMessage = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(
    "QVBJLdC60LvRjtGHINCy0LLQtdC00ZHQvSDQvdC10LrQvtGA0YDQtdC60YLQvdC+LiDQntC9INC00L7Qu9C20LXQvSDQvdCw0YfQuNC90LDRgtGM0YHRjyDRgSBzay0uINCf0L7Qv9GA0L7QsdGD0LnRgtC1INC10YnRkSDRgNCw0Lcu"
))
$script:RussianMessagesJson | Add-Member -NotePropertyName invalidKey -NotePropertyValue $script:RussianInvalidKeyMessage -Force
$script:RussianMessagesJson | Add-Member -NotePropertyName historyNotice -NotePropertyValue ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(
    "0J7RhNC40YbQuNCw0LvRjNC90YvQtSDRh9Cw0YLRiyBDbGF1ZGUg0YXRgNCw0L3Rj9GC0YHRjyDQsiDQsNC60LrQsNGD0L3RgtC1IEFudGhyb3BpYywg0LAg0YfQsNGC0Ysg0YHRgtC+0YDQvtC90L3QtdCz0L4g0L/RgNC+0LLQsNC50LTQtdGA0LAg4oCUINC70L7QutCw0LvRjNC90L4g0LIg0L7RgtC00LXQu9GM0L3QvtC8INC/0YDQvtGE0LjQu9C1LiDQndCw0LTRkdC20L3QviDQvtCx0YrQtdC00LjQvdC40YLRjCDQuNGFINC90LXQu9GM0LfRjy4g0KfRgtC+0LHRiyDRgdC90L7QstCwINGD0LLQuNC00LXRgtGMINC+0YTQuNGG0LjQsNC70YzQvdGL0LUg0YfQsNGC0YssINCy0YvQsdC10YDQuNGC0LUg0LLRhdC+0LQgQW50aHJvcGljINC40LvQuCDQstGL0L/QvtC70L3QuNGC0LUg0JLQvtGB0YHRgtCw0L3QvtCy0LvQtdC90LjQtS4="
))) -Force
$script:RussianMessagesJson | Add-Member -NotePropertyName setupReserve -NotePropertyValue "Настроить Claude Desktop через резервный endpoint" -Force
$script:RussianMessagesJson | Add-Member -NotePropertyName networkHint -NotePropertyValue "Если соединение обрывается (ECONNRESET, тайм-ауты), повторите настройку с запасным адресом: на странице подключения откройте «Если соединение обрывается» или запустите установщик с -Action setup-reserve. Если не помогло, попробуйте VPN, который не рвёт потоковые соединения." -Force
$script:RussianMessagesJson | Add-Member -NotePropertyName runningPrompt -NotePropertyValue "Claude Desktop сейчас открыт, его нужно закрыть на время настройки. Enter — закрыть Claude Desktop, n — отмена" -Force
$script:RussianMessagesJson | Add-Member -NotePropertyName closing -NotePropertyValue "Закрываю Claude Desktop" -Force
$script:RussianMessagesJson | Add-Member -NotePropertyName clipboardKey -NotePropertyValue "В буфере обмена найден ключ" -Force
$script:RussianMessagesJson | Add-Member -NotePropertyName clipboardPrompt -NotePropertyValue "Нажмите Enter, чтобы использовать его, или вставьте другой ключ (ввод скрыт)" -Force
$script:RussianMessagesJson | Add-Member -NotePropertyName setupKey -NotePropertyValue "Использую ключ из ссылки установки" -Force

$script:Messages = @{
    en = @{
        title = "aimarket Claude Desktop setup"
        choose = "Choose action:"
        setup = "Configure Claude Desktop for aimarket"
        setupReserve = "Configure Claude Desktop with the reserve endpoint"
        networkHint = "If the connection drops (ECONNRESET, timeouts), rerun setup with the reserve endpoint: open 'If the connection drops' on the setup page, or run the installer with -Action setup-reserve. If that does not help, use a VPN that does not reset streaming connections."
        runningPrompt = "Claude Desktop is running and must be closed during setup. Press Enter to close it, or n to cancel"
        closing = "Closing Claude Desktop"
        clipboardKey = "Found a key in the clipboard"
        clipboardPrompt = "Press Enter to use it, or paste another key (input is hidden)"
        setupKey = "Using the key from the setup link"
        restore = "Restore the previously active/official Claude Desktop profile"
        exit = "Exit"
        invalid = "Invalid choice."
        close = "Fully quit Claude Desktop and run this script again. It must be closed so chat storage and configuration stay consistent."
        key = "Paste aimarket API key (input is hidden)"
        invalidKey = "API key is invalid. It must start with sk-. Please try again."
        testing = "Testing the Anthropic-compatible gateway"
        backup = "Creating a safety backup of Claude Desktop configuration and local chat/session state"
        backupDone = "Safety backup: {path}"
        backupSkipped = "Local chat/session backup was explicitly skipped; configuration files are still backed up."
        noHistory = "No local Claude chat/session stores were found. Configuration backup will still be created."
        configuring = "Writing the managed Claude Desktop 3P profile"
        restoring = "Removing only the aimarket profile and restoring the previous selection"
        done = "Configured. Existing chat/session stores were not modified. Fully quit and reopen Claude Desktop."
        restored = "Restored. Existing chat/session stores were not modified. Fully quit and reopen Claude Desktop."
        historyNotice = "Standard Claude chats are stored in your Anthropic account, while third-party-provider chats are stored locally in a separate profile. They cannot be merged reliably. Choose Anthropic sign-in, or run Restore, to see your official chats again."
        nothing = "The aimarket Claude Desktop profile is not installed; nothing was changed."
        plaintext = "Claude Desktop requires the gateway key in its local profile. The profile and backups are stored inside your user account."
        models = "Claude Desktop models: {models}"
        dryRun = "Dry run: no files were changed."
        backupSpace = "Not enough free space for the safety backup. Required approximately {required} MiB, available {available} MiB."
    }
    ru = $script:RussianMessagesJson
}

function T {
    param([string]$Key, [hashtable]$Values = @{})
    $language = $script:Messages[$Lang]
    $text = if ($language -is [hashtable]) { [string]$language[$Key] } else { [string]$language.$Key }
    foreach ($name in $Values.Keys) { $text = $text.Replace("{$name}", [string]$Values[$name]) }
    return $text
}

function Info { param([string]$Text) Write-Host "[INFO] $Text" -ForegroundColor Cyan }
function Ok { param([string]$Text) Write-Host "[OK] $Text" -ForegroundColor Green }
function Warn { param([string]$Text) Write-Host "[WARN] $Text" -ForegroundColor Yellow }

function Convert-SecureStringToText {
    param([Security.SecureString]$Value)
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}

function Test-ApiKeyFormat {
    param([AllowEmptyString()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return $false }
    return $Value.Trim().StartsWith("sk-", [StringComparison]::Ordinal)
}

function Test-CanPromptForApiKey {
    return [Environment]::UserInteractive -and -not [Console]::IsInputRedirected
}

function Get-ValidApiKey {
    param([AllowEmptyString()][string]$Value)
    $candidate = if ($null -eq $Value) { "" } else { $Value.Trim() }
    $setupKey = [Environment]::GetEnvironmentVariable("AIMARKET_SETUP_KEY", "Process")
    if ([string]::IsNullOrWhiteSpace($candidate) -and -not [string]::IsNullOrWhiteSpace($setupKey)) {
        [Environment]::SetEnvironmentVariable("AIMARKET_SETUP_KEY", $null, "Process")
        $candidate = $setupKey.Trim()
        Ok (T "setupKey")
    }
    if ([string]::IsNullOrWhiteSpace($candidate) -and (Test-CanPromptForApiKey)) {
        $clipboard = ""
        try { $clipboard = ([string](Get-Clipboard -Raw -ErrorAction Stop)) -replace "\s", "" } catch {}
        if ($clipboard -cmatch '^sk-[A-Za-z0-9_-]{16,200}$') {
            Write-Host "$(T "clipboardKey"): $($clipboard.Substring(0, 6))...$($clipboard.Substring($clipboard.Length - 4))"
            $entered = (Convert-SecureStringToText (Read-Host (T "clipboardPrompt") -AsSecureString)).Trim()
            $candidate = if ([string]::IsNullOrWhiteSpace($entered)) { $clipboard } else { $entered }
        }
    }
    if (Test-ApiKeyFormat $candidate) { return $candidate }
    if (-not (Test-CanPromptForApiKey)) { throw (T "invalidKey") }
    if (-not [string]::IsNullOrWhiteSpace($candidate)) { Warn (T "invalidKey") }
    while ($true) {
        $candidate = (Convert-SecureStringToText (Read-Host (T "key") -AsSecureString)).Trim()
        if (Test-ApiKeyFormat $candidate) { return $candidate }
        Warn (T "invalidKey")
    }
}

function Normalize-Endpoint {
    param([string]$Value)
    $candidate = $Value.Trim().TrimEnd("/")
    if ($candidate.EndsWith("/v1", [StringComparison]::OrdinalIgnoreCase)) {
        $candidate = $candidate.Substring(0, $candidate.Length - 3).TrimEnd("/")
    }
    $uri = $null
    if (-not [Uri]::TryCreate($candidate, [UriKind]::Absolute, [ref]$uri) -or $uri.Scheme -ne "https") {
        throw "Endpoint must be an absolute HTTPS URL."
    }
    if (-not [string]::IsNullOrEmpty($uri.Query) -or -not [string]::IsNullOrEmpty($uri.Fragment)) {
        throw "Endpoint must not contain a query string or fragment."
    }
    return $candidate
}

function Join-Endpoint {
    param([string]$Base, [string]$Path)
    return $Base.TrimEnd("/") + "/" + $Path.TrimStart("/")
}

function Invoke-ClaudeDesktopHttp {
    param(
        [ValidateSet("GET", "POST")][string]$Method,
        [string]$Url,
        [string]$Key,
        [AllowNull()][string]$Body = $null,
        [int]$TimeoutSeconds = 30
    )
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    Add-Type -AssemblyName System.Net.Http -ErrorAction Stop
    $client = [System.Net.Http.HttpClient]::new()
    $client.Timeout = [TimeSpan]::FromSeconds($TimeoutSeconds)
    $request = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::new($Method), $Url)
    try {
        [void]$request.Headers.TryAddWithoutValidation("Authorization", "Bearer $Key")
        [void]$request.Headers.TryAddWithoutValidation("anthropic-version", "2023-06-01")
        [void]$request.Headers.TryAddWithoutValidation("Accept-Language", $Lang)
        [void]$request.Headers.TryAddWithoutValidation("User-Agent", "aimarket-claude-desktop-setup/$($script:ScriptVersion)")
        if ($Method -eq "POST" -and $null -ne $Body) {
            $request.Content = [System.Net.Http.StringContent]::new($Body, [Text.Encoding]::UTF8, "application/json")
        }
        $response = $client.SendAsync($request).GetAwaiter().GetResult()
        try {
            $text = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            return [pscustomobject]@{
                Ok = [bool]$response.IsSuccessStatusCode
                StatusCode = [int]$response.StatusCode
                Body = [string]$text
            }
        } finally { $response.Dispose() }
    } finally {
        $request.Dispose()
        $client.Dispose()
    }
}

function Get-ClaudeDesktopHttpErrorMessage {
    param([AllowEmptyString()][string]$Body)
    if ([string]::IsNullOrWhiteSpace($Body)) { return "" }
    try {
        $json = $Body | ConvertFrom-Json
        if ($json.PSObject.Properties["error"] -and $null -ne $json.error -and
            $json.error.PSObject.Properties["message"]) {
            return [string]$json.error.message
        }
        if ($json.PSObject.Properties["message"]) { return [string]$json.message }
    } catch {}
    $clean = $Body.Trim()
    if ($clean.Length -gt 500) { return $clean.Substring(0, 500) + "..." }
    return $clean
}

function Assert-ClaudeDesktopHttpOk {
    param([object]$Response, [string]$Label)
    if ($Response.Ok) { return }
    $message = Get-ClaudeDesktopHttpErrorMessage $Response.Body
    $suffix = if ([string]::IsNullOrWhiteSpace($message)) { "" } else { " $message" }
    throw "$Label failed: HTTP $($Response.StatusCode)$suffix"
}

function Get-ClaudeDesktopProcesses {
    # Результат разворачивается в поток, поэтому на месте вызова всегда @(...):
    # иначе при единственном процессе вернётся объект без .Count (StrictMode).
    Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ProcessName -eq "Claude" -or $_.ProcessName -like "Claude Helper*"
    }
}

function Assert-ClaudeDesktopClosed {
    $running = @(Get-ClaudeDesktopProcesses)
    if ($running.Count -eq 0) { return }
    if ($DryRun -or -not (Test-CanPromptForApiKey)) { throw (T "close") }
    $answer = (Read-Host (T "runningPrompt")).Trim()
    if ($answer -match '^(n|no|\u043d|\u043d\u0435\u0442)$') { throw (T "close") }
    Info (T "closing")
    foreach ($process in $running) {
        try { if ($process.MainWindowHandle -ne [IntPtr]::Zero) { [void]$process.CloseMainWindow() } } catch {}
    }
    for ($i = 0; $i -lt 10; $i++) {
        if (@(Get-ClaudeDesktopProcesses).Count -eq 0) { return }
        Start-Sleep -Seconds 1
    }
    # Claude Desktop keeps running in the tray after its window closes.
    @(Get-ClaudeDesktopProcesses) | Stop-Process -ErrorAction SilentlyContinue
    for ($i = 0; $i -lt 10; $i++) {
        if (@(Get-ClaudeDesktopProcesses).Count -eq 0) { return }
        Start-Sleep -Seconds 1
    }
    throw (T "close")
}

function Read-JsonObject {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return [pscustomobject]@{} }
    try { $value = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json }
    catch { throw "Invalid JSON in $Path. $($_.Exception.Message)" }
    if ($null -eq $value -or $value -is [array] -or $null -eq $value.PSObject) {
        throw "Expected a JSON object in $Path."
    }
    return $value
}

function Set-JsonProperty {
    param([object]$Object, [string]$Name, [object]$Value)
    $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value -Force
}

function Remove-JsonProperty {
    param([object]$Object, [string]$Name)
    if ($Object.PSObject.Properties[$Name]) { $Object.PSObject.Properties.Remove($Name) }
}

function Write-JsonAtomic {
    param([string]$Path, [object]$Value)
    $directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $temporary = Join-Path $directory ("." + [IO.Path]::GetFileName($Path) + ".tmp-" + [guid]::NewGuid().ToString("N"))
    $json = ($Value | ConvertTo-Json -Depth 100) + "`r`n"
    [IO.File]::WriteAllText($temporary, $json, [Text.UTF8Encoding]::new($false))
    try {
        if (Test-Path -LiteralPath $Path) {
            try { [IO.File]::Replace($temporary, $Path, $null) }
            catch { Move-Item -LiteralPath $temporary -Destination $Path -Force }
        } else {
            Move-Item -LiteralPath $temporary -Destination $Path
        }
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
}

function Get-ManagedPaths {
    $normal = New-Object System.Collections.Generic.List[string]
    $normalRoots = New-Object System.Collections.Generic.List[string]
    if (-not [string]::IsNullOrWhiteSpace($NormalConfigDirectory)) {
        $normalRoots.Add($NormalConfigDirectory)
        $normal.Add((Join-Path $NormalConfigDirectory "claude_desktop_config.json"))
    } else {
        $localRoot = Join-Path $env:LOCALAPPDATA "Claude"
        $normalRoots.Add($localRoot)
        $normal.Add((Join-Path $localRoot "claude_desktop_config.json"))
        $legacyRoot = Join-Path $env:APPDATA "Claude"
        if (Test-Path -LiteralPath $legacyRoot) {
            $normalRoots.Add($legacyRoot)
            $normal.Add((Join-Path $legacyRoot "claude_desktop_config.json"))
        }
    }

    $threepRoot = if ([string]::IsNullOrWhiteSpace($ThreePConfigDirectory)) {
        Join-Path $env:LOCALAPPDATA "Claude-3p"
    } else { $ThreePConfigDirectory }
    $configLibrary = Join-Path $threepRoot "configLibrary"
    $backupRoot = if ([string]::IsNullOrWhiteSpace($BackupDirectory)) {
        Join-Path $env:LOCALAPPDATA "aimarket\claude-desktop-backups"
    } else { $BackupDirectory }

    return [pscustomobject]@{
        NormalConfigs = @($normal | Select-Object -Unique)
        NormalRoots = @($normalRoots | Select-Object -Unique)
        ThreePRoot = $threepRoot
        ThreePConfig = Join-Path $threepRoot "claude_desktop_config.json"
        Meta = Join-Path $configLibrary "_meta.json"
        Profile = Join-Path $configLibrary "$($script:ProfileId).json"
        BackupRoot = $backupRoot
        State = Join-Path $backupRoot "switch-state.json"
    }
}

function Assert-ManagedPathsAreFiles {
    param([object]$Paths)
    $managed = @($Paths.NormalConfigs) + @($Paths.ThreePConfig, $Paths.Meta, $Paths.Profile, $Paths.State)
    foreach ($path in @($managed | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $path -PathType Container) {
            throw "Expected a configuration file but found a directory: $path"
        }
    }
}

function Get-FileSnapshots {
    param([string[]]$Paths)
    return @($Paths | Select-Object -Unique | ForEach-Object {
        [pscustomobject]@{
            Path = $_
            Existed = Test-Path -LiteralPath $_ -PathType Leaf
            Bytes = if (Test-Path -LiteralPath $_ -PathType Leaf) { [IO.File]::ReadAllBytes($_) } else { $null }
        }
    })
}

function Restore-FileSnapshots {
    param([object[]]$Snapshots)
    foreach ($snapshot in $Snapshots) {
        if ($snapshot.Existed) {
            $directory = Split-Path -Parent $snapshot.Path
            New-Item -ItemType Directory -Path $directory -Force | Out-Null
            [IO.File]::WriteAllBytes($snapshot.Path, $snapshot.Bytes)
        } elseif (Test-Path -LiteralPath $snapshot.Path -PathType Leaf) {
            Remove-Item -LiteralPath $snapshot.Path -Force
        }
    }
}

function ConvertTo-ExtendedLengthPath {
    param([string]$Path)
    $fullPath = [IO.Path]::GetFullPath($Path)
    if ($fullPath.StartsWith("\\?\", [StringComparison]::Ordinal)) { return $fullPath }
    if ($fullPath.StartsWith("\\", [StringComparison]::Ordinal)) { return "\\?\UNC\" + $fullPath.Substring(2) }
    return "\\?\" + $fullPath
}

function Get-HistorySources {
    param([object]$Paths)
    $historyPaths = New-Object System.Collections.Generic.List[string]
    if ($HistoryDataDirectories.Count -gt 0) {
        foreach ($path in $HistoryDataDirectories) {
            if (Test-Path -LiteralPath $path) { $historyPaths.Add((Resolve-Path -LiteralPath $path).Path) }
        }
        return @($historyPaths | Select-Object -Unique)
    }

    $roots = New-Object System.Collections.Generic.List[string]
    foreach ($root in @($Paths.NormalRoots) + @($Paths.ThreePRoot)) {
        if (Test-Path -LiteralPath $root) { $roots.Add($root) }
    }
    $packages = Join-Path $env:LOCALAPPDATA "Packages"
    if (Test-Path -LiteralPath $packages) {
        foreach ($package in @(Get-ChildItem -LiteralPath $packages -Directory -Filter "Claude_*" -ErrorAction SilentlyContinue)) {
            foreach ($relativeRoot in @("LocalCache\Roaming\Claude", "LocalCache\Roaming\Claude-3p")) {
                $root = Join-Path $package.FullName $relativeRoot
                if (Test-Path -LiteralPath $root) { $roots.Add($root) }
            }
        }
    }

    foreach ($root in @($roots | Select-Object -Unique)) {
        foreach ($relative in @("IndexedDB", "Local Storage", "Session Storage", "local-agent-mode-sessions", "Partitions", "WebStorage", "databases", "Service Worker", "shared_proto_db")) {
            $candidate = Join-Path $root $relative
            if (Test-Path -LiteralPath $candidate) { $historyPaths.Add($candidate) }
        }
        foreach ($relative in @("Network\Cookies", "Network\Cookies-journal", "Local State", "Preferences")) {
            $candidate = Join-Path $root $relative
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { $historyPaths.Add($candidate) }
        }
    }

    $claudeProjects = Join-Path $env:USERPROFILE ".claude\projects"
    if (Test-Path -LiteralPath $claudeProjects) { $historyPaths.Add($claudeProjects) }
    return @($historyPaths | Select-Object -Unique)
}

function Get-PathByteCount {
    param([string]$Path)
    $extendedPath = ConvertTo-ExtendedLengthPath $Path
    if ([IO.File]::Exists($extendedPath)) { return [long]([IO.FileInfo]::new($extendedPath)).Length }
    if (-not [IO.Directory]::Exists($extendedPath)) { throw "Safety backup source no longer exists: $Path" }

    $sum = [long]0
    foreach ($file in [IO.Directory]::EnumerateFiles($extendedPath, "*", [IO.SearchOption]::AllDirectories)) {
        $sum += [long]([IO.FileInfo]::new($file)).Length
    }
    return $sum
}

function Copy-SafetyBackupPath {
    param([string]$Source, [string]$Destination)
    $sourceFullPath = [IO.Path]::GetFullPath($Source)
    $destinationFullPath = [IO.Path]::GetFullPath($Destination)
    $extendedSource = ConvertTo-ExtendedLengthPath $sourceFullPath
    $extendedDestination = ConvertTo-ExtendedLengthPath $destinationFullPath

    if ([IO.File]::Exists($extendedSource)) {
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($extendedDestination)) | Out-Null
        [IO.File]::Copy($extendedSource, $extendedDestination, $true)
        return
    }
    if (-not [IO.Directory]::Exists($extendedSource)) { throw "Safety backup source no longer exists: $Source" }

    [IO.Directory]::CreateDirectory($extendedDestination) | Out-Null
    $robocopy = Get-Command "robocopy.exe" -CommandType Application -ErrorAction Stop
    $copyOutput = @(& $robocopy.Source $sourceFullPath $destinationFullPath "/E" "/COPY:DAT" "/DCOPY:DAT" "/R:2" "/W:1" "/XJ" "/NFL" "/NDL" "/NJH" "/NJS" "/NP" 2>&1 | ForEach-Object { [string]$_ })
    $exitCode = $LASTEXITCODE
    $global:LASTEXITCODE = 0
    if ($exitCode -ge 8) {
        $details = @($copyOutput | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 12) -join [Environment]::NewLine
        $message = "Safety backup copy failed with robocopy exit code $exitCode."
        if ($details) { $message += [Environment]::NewLine + $details }
        throw $message
    }
}

function New-SafetyBackup {
    param([string]$ActionName, [object]$Paths)
    Info (T "backup")
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
    $destination = Join-Path $Paths.BackupRoot "$stamp-$ActionName"
    if ($SkipHistoryBackup) { $history = @() }
    else { $history = @(Get-HistorySources $Paths) }
    if ($SkipHistoryBackup) { Warn (T "backupSkipped") }
    elseif ($history.Count -eq 0) { Info (T "noHistory") }

    $historyBytes = [long]0
    foreach ($source in $history) { $historyBytes += Get-PathByteCount $source }
    if (-not $DryRun) {
        $root = [IO.Path]::GetPathRoot([IO.Path]::GetFullPath($Paths.BackupRoot))
        $drive = [IO.DriveInfo]::new($root)
        $required = $historyBytes + 64MB
        if ($drive.AvailableFreeSpace -lt $required) {
            throw (T "backupSpace" @{ required = [math]::Ceiling($required / 1MB); available = [math]::Floor($drive.AvailableFreeSpace / 1MB) })
        }
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
    }

    $configPaths = @($Paths.NormalConfigs) + @($Paths.ThreePConfig, $Paths.Meta, $Paths.Profile, $Paths.State)
    $manifestEntries = New-Object System.Collections.Generic.List[object]
    $index = 0
    foreach ($path in @($configPaths | Select-Object -Unique)) {
        $index++
        $exists = Test-Path -LiteralPath $path -PathType Leaf
        $backupName = "config\{0:D2}-{1}" -f $index, [IO.Path]::GetFileName($path)
        if ($exists -and -not $DryRun) {
            $target = Join-Path $destination $backupName
            New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
            Copy-SafetyBackupPath $path $target
        }
        $manifestEntries.Add([pscustomobject]@{ source = $path; existed = $exists; backup = if ($exists) { $backupName } else { $null } })
    }

    $historyIndex = 0
    foreach ($source in $history) {
        $historyIndex++
        $safeName = ([IO.Path]::GetFileName($source) -replace '[^A-Za-z0-9._-]', '_')
        if ([string]::IsNullOrWhiteSpace($safeName)) { $safeName = "state" }
        $relative = "history\{0:D2}-{1}" -f $historyIndex, $safeName
        if (-not $DryRun) {
            $target = Join-Path $destination $relative
            New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
            Copy-SafetyBackupPath $source $target
        }
        $manifestEntries.Add([pscustomobject]@{ source = $source; existed = $true; backup = $relative; bytes = Get-PathByteCount $source })
    }

    if (-not $DryRun) {
        $manifest = [ordered]@{
            version = $script:ScriptVersion
            action = $ActionName
            created_at = [DateTime]::UtcNow.ToString("o")
            history_bytes = $historyBytes
            entries = $manifestEntries.ToArray()
        }
        Write-JsonAtomic (Join-Path $destination "manifest.json") $manifest
    }
    Ok (T "backupDone" @{ path = $destination })
    return $destination
}

function Get-ClaudeDesktopModels {
    param([string]$Key)
    if ($SkipEndpointTest) { return @($script:PreferredModels) }
    Info (T "testing")
    $catalogResponse = Invoke-ClaudeDesktopHttp -Method GET -Url (Join-Endpoint $Endpoint "v1/models") -Key $Key -TimeoutSeconds 30
    Assert-ClaudeDesktopHttpOk $catalogResponse "GET /v1/models"
    try { $catalog = $catalogResponse.Body | ConvertFrom-Json }
    catch { throw "GET /v1/models returned invalid JSON. $($_.Exception.Message)" }
    $available = @($catalog.data | ForEach-Object { [string]$_.id } | Where-Object {
        $_ -match '(?i)^(anthropic/)?claude-(sonnet|opus|haiku|fable|mythos)-[a-z0-9][a-z0-9._-]*$'
    } | Select-Object -Unique)
    if ($available.Count -eq 0) { throw "This key has no Claude Desktop-compatible models in GET /v1/models." }

    $ordered = New-Object System.Collections.Generic.List[string]
    foreach ($model in $script:PreferredModels) { if ($available -contains $model) { $ordered.Add($model) } }
    foreach ($model in @($available | Sort-Object)) { if (-not $ordered.Contains($model)) { $ordered.Add($model) } }

    $body = @{ model = $ordered[0]; max_tokens = 8; messages = @(@{ role = "user"; content = "Reply with OK." }) } | ConvertTo-Json -Depth 6 -Compress
    $messageResponse = Invoke-ClaudeDesktopHttp -Method POST -Url (Join-Endpoint $Endpoint "v1/messages") -Key $Key -Body $body -TimeoutSeconds 90
    Assert-ClaudeDesktopHttpOk $messageResponse "POST /v1/messages"
    return @($ordered)
}

function Test-LegacyDeploymentModeManaged {
    param([object]$State)
    return $State.PSObject.Properties["profile_id"] -and
           [string]$State.profile_id -eq $script:ProfileId -and
           -not $State.PSObject.Properties["script_version"]
}

function Remove-LegacyDeploymentMode {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return }
    $config = Read-JsonObject $Path
    if ($config.PSObject.Properties["deploymentMode"] -and [string]$config.deploymentMode -eq "3p") {
        Remove-JsonProperty $config "deploymentMode"
        Write-JsonAtomic $Path $config
    }
}

function Get-MetaEntries {
    param([object]$Meta)
    if (-not $Meta.PSObject.Properties["entries"] -or $null -eq $Meta.entries) { return @() }
    return @($Meta.entries)
}

function Test-MetaContainsId {
    param([object[]]$Entries, [string]$Id)
    return @($Entries | Where-Object { $_.PSObject.Properties["id"] -and [string]$_.id -eq $Id }).Count -gt 0
}

function Install-Profile {
    param([string]$Key, [string[]]$Models, [object]$Paths)
    Info (T "configuring")
    Warn (T "plaintext")
    $meta = Read-JsonObject $Paths.Meta
    $state = Read-JsonObject $Paths.State
    $currentApplied = if ($meta.PSObject.Properties["appliedId"]) { [string]$meta.appliedId } else { "" }
    $previousApplied = if ($currentApplied -and $currentApplied -ne $script:ProfileId) {
        $currentApplied
    } elseif ($state.PSObject.Properties["previousAppliedId"]) {
        [string]$state.previousAppliedId
    } else { "" }

    $entries = @(Get-MetaEntries $meta | Where-Object {
        -not ($_.PSObject.Properties["id"] -and [string]$_.id -eq $script:ProfileId)
    })
    $entries += [pscustomobject][ordered]@{ id = $script:ProfileId; name = $script:ProfileName }
    Set-JsonProperty $meta "entries" ([object[]]$entries)
    Set-JsonProperty $meta "appliedId" $script:ProfileId

    $profile = [ordered]@{
        coworkEgressAllowedHosts = @("*")
        inferenceGatewayApiKey = $Key
        inferenceGatewayAuthScheme = "bearer"
        inferenceGatewayBaseUrl = $Endpoint
        inferenceModels = @($Models)
        inferenceProvider = "gateway"
    }
    $switchState = [ordered]@{
        profile_id = $script:ProfileId
        script_version = $script:ScriptVersion
        previousAppliedId = $previousApplied
        installed_at = [DateTime]::UtcNow.ToString("o")
    }

    $managed = @($Paths.NormalConfigs) + @($Paths.ThreePConfig, $Paths.Meta, $Paths.Profile, $Paths.State)
    $snapshots = Get-FileSnapshots $managed
    try {
        if (Test-LegacyDeploymentModeManaged $state) {
            foreach ($path in $Paths.NormalConfigs) { Remove-LegacyDeploymentMode $path }
            Remove-LegacyDeploymentMode $Paths.ThreePConfig
        }
        Write-JsonAtomic $Paths.Profile $profile
        Write-JsonAtomic $Paths.Meta $meta
        Write-JsonAtomic $Paths.State $switchState
    } catch {
        Restore-FileSnapshots $snapshots
        throw
    }
}

function Uninstall-Profile {
    param([object]$Paths)
    $meta = Read-JsonObject $Paths.Meta
    $state = Read-JsonObject $Paths.State
    $entriesBefore = @(Get-MetaEntries $meta)
    $hasEntry = Test-MetaContainsId $entriesBefore $script:ProfileId
    $hasProfile = Test-Path -LiteralPath $Paths.Profile -PathType Leaf
    $hasState = Test-Path -LiteralPath $Paths.State -PathType Leaf
    if (-not $hasEntry -and -not $hasProfile -and -not $hasState) {
        Info (T "nothing")
        return $false
    }

    Info (T "restoring")
    $currentApplied = if ($meta.PSObject.Properties["appliedId"]) { [string]$meta.appliedId } else { "" }
    $entries = @($entriesBefore | Where-Object {
        -not ($_.PSObject.Properties["id"] -and [string]$_.id -eq $script:ProfileId)
    })
    $targetApplied = ""
    if ($currentApplied -and $currentApplied -ne $script:ProfileId -and (Test-MetaContainsId $entries $currentApplied)) {
        $targetApplied = $currentApplied
    } elseif ($state.PSObject.Properties["previousAppliedId"] -and
              (Test-MetaContainsId $entries ([string]$state.previousAppliedId))) {
        $targetApplied = [string]$state.previousAppliedId
    } elseif ($entries.Count -gt 0 -and $entries[0].PSObject.Properties["id"]) {
        $targetApplied = [string]$entries[0].id
    }

    Set-JsonProperty $meta "entries" ([object[]]$entries)
    if ($targetApplied) { Set-JsonProperty $meta "appliedId" $targetApplied }
    else { Remove-JsonProperty $meta "appliedId" }
    $managed = @($Paths.NormalConfigs) + @($Paths.ThreePConfig, $Paths.Meta, $Paths.Profile, $Paths.State)
    $snapshots = Get-FileSnapshots $managed
    try {
        Write-JsonAtomic $Paths.Meta $meta
        if (Test-Path -LiteralPath $Paths.Profile -PathType Leaf) { Remove-Item -LiteralPath $Paths.Profile -Force }
        if (Test-LegacyDeploymentModeManaged $state) {
            foreach ($path in $Paths.NormalConfigs) { Remove-LegacyDeploymentMode $path }
            Remove-LegacyDeploymentMode $Paths.ThreePConfig
        }
        if (Test-Path -LiteralPath $Paths.State -PathType Leaf) { Remove-Item -LiteralPath $Paths.State -Force }
    } catch {
        Restore-FileSnapshots $snapshots
        throw
    }
    return $true
}

try {
    $Endpoint = Normalize-Endpoint $Endpoint
    Write-Host ""
    Write-Host (T "title") -ForegroundColor White
    Write-Host ""
    if ([string]::IsNullOrWhiteSpace($Action)) { $Action = "setup" }

    Assert-ClaudeDesktopClosed
    $paths = Get-ManagedPaths
    Assert-ManagedPathsAreFiles $paths

    if ($Action -eq "setup" -or $Action -eq "setup-reserve") {
        if ($Action -eq "setup-reserve") { $Endpoint = "https://direct.router-cheap.com" }
        $ApiKey = Get-ValidApiKey $ApiKey
        $script:NetworkPhase = $true
        $models = @(Get-ClaudeDesktopModels $ApiKey)
        $script:NetworkPhase = $false
        Ok (T "models" @{ models = ($models -join ", ") })
        [void](New-SafetyBackup "setup" $paths)
        if ($DryRun) { Info (T "dryRun") }
        else { Install-Profile $ApiKey $models $paths; Warn (T "historyNotice"); Ok (T "done") }
    } else {
        $meta = Read-JsonObject $paths.Meta
        $installed = (Test-Path -LiteralPath $paths.Profile -PathType Leaf) -or
                     (Test-Path -LiteralPath $paths.State -PathType Leaf) -or
                     (Test-MetaContainsId (Get-MetaEntries $meta) $script:ProfileId)
        if (-not $installed) { Info (T "nothing"); exit 0 }
        [void](New-SafetyBackup "restore" $paths)
        if ($DryRun) { Info (T "dryRun") }
        elseif (Uninstall-Profile $paths) { Warn (T "historyNotice"); Ok (T "restored") }
    }
} catch {
    Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red
    if ($script:NetworkPhase) { Warn (T "networkHint") }
    if ($_.ScriptStackTrace) { Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray }
    exit 1
}
