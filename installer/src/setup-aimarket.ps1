<#
aimarket setup helper for Codex, Claude Code, OpenCode, Hermes, Grok Build, Cursor, and Factory Droid.
This file intentionally keeps source strings ASCII-only. Localized text is loaded
from setup-aimarket.en.json or setup-aimarket.ru.json as UTF-8.
#>

[CmdletBinding()]
param(
    [ValidateSet("", "en", "ru")]
    [string]$Lang = "",
    [ValidateSet("", "codex", "claude-code", "opencode", "hermes", "grok-build", "cursor", "droid")]
    [string]$App = "",
    [ValidateSet("", "setup", "setup-reserve", "restore")]
    [string]$Action = "",
    [string]$ApiKey = "",
    [string]$Endpoint = "https://router.cheap/v1",
    [string]$AnthropicEndpoint = "https://router.cheap",
    [string]$TelemetryEndpoint = "https://router.cheap/api/setup-events",
    [string]$Model = "gpt-6-astra",
    [string]$ClaudeModel = "claude-opus-5",
    [string]$GrokModel = "grok-4.5",
    [ValidateSet("none", "minimal", "low", "medium", "high", "xhigh", "max")]
    [string]$HermesReasoningEffort = "medium",
    [switch]$SkipEndpointTest,
    [switch]$InstallCodexIfMissing,
    [switch]$SkipLiveModelTest,
    [switch]$SkipCodexRuntimeTest,
    [switch]$AllowMissingModel,
    [switch]$RestartCodex,
    [switch]$NoRestartCodex,
    [switch]$ChooseModel,
    [switch]$DryRun
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Lang)) {
    $Lang = if ([Globalization.CultureInfo]::CurrentUICulture.TwoLetterISOLanguageName -eq "ru") { "ru" } else { "en" }
}
# Windows PowerShell can leave native output on the ASCII encoder even after the
# console code page changes. Use the code page that can represent the selected
# locale, and keep the native-command encoder in sync with the console host.
$script:SetupOutputEncoding = if ($Lang -eq "ru") {
    [System.Text.Encoding]::GetEncoding(1251)
} else {
    [System.Text.UTF8Encoding]::new($false)
}
[Console]::OutputEncoding = $script:SetupOutputEncoding
$global:OutputEncoding = $script:SetupOutputEncoding
Add-Type -AssemblyName System.Net.Http

$script:SetupScriptVersion = "2.14"
$script:RestartCodexEffective = -not $NoRestartCodex
$script:SetupTelemetryStep = ""
$script:SetupTelemetrySessionId = ""
$script:SetupTelemetryStartedAt = $null
$script:SetupLastProbeMethod = ""
$script:SetupLastProbePath = ""
$script:SetupLastProbeStatus = ""
$script:SetupModelsProbeStatus = ""
$script:SetupResponsesProbeStatus = ""
$script:CodexRuntimeProbeStatus = ""
$script:CodexRuntimeProbeExitCode = ""
$script:ModelExplicit = $PSBoundParameters.ContainsKey("Model")
$script:HermesReasoningEffortExplicit = $PSBoundParameters.ContainsKey("HermesReasoningEffort")
$script:OpenAIModels = @()
$script:ClaudeModels = @()
$script:OpenAIModelCatalogVerified = $false
$script:ClaudeModelCatalogVerified = $false
$script:OpenAIModelCandidates = @(
	"gpt-6-astra",
	"gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "claude-opus-5",
    "claude-sonnet-5",
    "grok-4.6",
    "grok-4.7",
    "grok-4.5",
    "gpt-5.4",
    "gpt-5",
    "gpt-5-mini",
    "gpt-4.1",
    "gpt-4o",
    "claude-sonnet-4-5",
    "claude-opus-4-5",
    "claude-3-5-sonnet-latest",
    "claude-3-7-sonnet-latest"
)
$script:ClaudeModelCandidates = @(
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-sonnet-4-5",
    "claude-opus-4-5",
    "claude-3-5-sonnet-latest",
    "claude-3-7-sonnet-latest",
    "claude-3-opus-latest"
)

$script:Messages = @{
    title = "aimarket app setup"
    selectApp = "Select application:"
    selectAction = "Select action for {app}:"
    configure = "Configure {app} for aimarket"
    configureReserve = "Configure {app} with the reserve endpoint"
    networkHint = "If the connection drops (ECONNRESET, timeouts), rerun setup with the reserve endpoint: open 'If the connection drops' on the setup page, or run the installer with -Action setup-reserve. If that does not help, use a VPN that does not reset streaming connections."
    clipboardKeyFound = "Found a key in the clipboard"
    clipboardKeyPrompt = "Press Enter to use it, or paste another key (input is hidden)"
    setupKeyUsing = "Using the key from the setup link"
    appRunningPrompt = "{app} is running and must be closed during setup. Save your open files. Press Enter to close {app}, or n to cancel"
    appClosing = "Closing {app}"
    appStillRunning = "{app} did not close. Quit it manually, including the tray icon, and run setup again."
    appInsideTerminal = "Setup is running inside {app}'s built-in terminal, but {app} must be closed during setup. Open a regular PowerShell window and run the command there."
    doneApp = "Done. Restart {app} and send a test request."
    restoredApp = "Done. Restart {app}."
    failedSupport = "Setup did not finish. If the error repeats, contact support and include diagnostic code {session}."
    restore = "Restore official/default {app} endpoint"
    exit = "Exit"
    choice = "Enter number"
    badChoice = "Invalid choice."
    pasteKey = "Paste aimarket API key (input is hidden)"
    savedKeyFound = "Found saved API key"
    savedKeyPrompt = "Press Enter to use it, or paste a new API key (input is hidden)"
    savedKeyUsing = "Using saved API key"
    invalidKey = "API key is invalid. It must start with sk-. Please try again."
    endpoint = "Endpoint"
    model = "Model"
    selectDefaultModel = "Choose the default model for {app}:"
    selectDefaultModelHint = "Enter only the model number. Press Enter to keep {model}."
    selectedDefaultModel = "Default model selected"
    invalidModelChoice = "Invalid input. Enter a number from the list, for example 1."
    key = "Key"
    testing = "Testing aimarket key"
    writing = "Writing configuration"
    codexHistoryNotice = 'Codex has no supported cross-provider session-copy command. The setup keeps session files and indexes intact. Please ask Codex: review the optional last-7-day metadata migration dry-run before applying it. To run it, close Codex and execute python "$PSScriptRoot\codex-history-migrate.py" --source-provider <current-provider> --target-provider <new-provider> --days 7 --dry-run, then repeat with --yes. A rollback backup is created automatically; use --rollback <backup-directory> to restore. This reclassifies metadata only and encrypted reasoning may not resume.'
    done = "Done. A bare standalone Codex was restarted automatically; if setup warned about Desktop/IDE, close it and start it again before testing."
    restored = "Restored. A bare standalone Codex was restarted automatically; if setup warned about Desktop/IDE, close it and start it again before testing."
    restoreNotNeeded = "Restore is not needed for this app. To stop using aimarket, remove the custom provider/config in the app settings."
    cursorClosed = "Close Cursor completely (including its tray/background process), then run the setup again. This protects Cursor's settings and chat database."
    cursorNotFound = "Cursor's local storage or bundled SQLite runtime was not found. Install/update Cursor, start it once, close it completely, and run setup again."
    cursorConfigured = "Cursor's OpenAI key, Base URL, and available compatible models were updated. Existing chats, workspaces, and unrelated settings were not changed."
    cursorRestored = "Cursor's previous OpenAI key, Base URL, and model visibility settings were restored. Existing chats were not changed."
    cursorNotManaged = "No managed Cursor setup for aimarket was found; nothing was changed."
    cursorOtherOwner = "Cursor is currently managed by {owner}. Restore it with that service's setup script so its active configuration is not overwritten."
    cursorLimit = "Cursor limitation: Override OpenAI Base URL is global and does not reroute Claude/Anthropic models. Cursor can also bypass a custom OpenAI Base URL for image attachments in some versions. Use Codex, OpenCode, or Hermes when images must be sent through aimarket; use GPT/Grok models in Cursor for text-only normal-context work."
    telemetry = "Sending a safe setup event to aimarket (app, OS, action, result; the API key is used only in the Authorization header to identify your account)."
    telemetrySession = "Diagnostic session ID: {session}. Keep this ID with the setup time when reporting a Codex problem; it links the started, success, and failed events without exposing the API key."
    telemetryFailed = "Setup event could not be sent. Continuing without telemetry."
    probeNonFatal = "{label} failed with a temporary HTTP {status}. Configuration will still be written; test the app after restart."
    probeTimeout = "The model check timed out or was canceled. Configuration will still be written; test the app after restart."
    claudeLoginPreserved = "Your saved official Claude Code login was left intact. Gateway variables take priority while configured; after Restore and a restart, Claude Code can use the saved official login again."
    claudeLoginRestore = "Gateway variables were removed. Restart Claude Code; the saved official login can be used again without signing in again unless it has expired or was removed separately."
    claudeCachePolicyConfigured = "Cache-priority policy enabled: full-context Agent(fork) is denied while ordinary subagents remain available."
    claudeCachePolicyRestored = "The Agent(fork) deny rule added by this setup was removed. Pre-existing user rules were preserved."
    claudeModelAccessHint = "Claude Code uses Claude models. Open Routing and enable 'Automatic balance conversion' to pay for them from the active balance, or manually convert the balance to Claude."
    crossFamilyAccessHint = "Open Routing and enable 'Cross-family access' to convert balance automatically for this request, or convert it manually in 'Model balance'."
    modelProbeRetry = "Model {model} is listed, but its live request failed for this key. Trying the next available model."
    modelFallbackSelected = "Confirmed available default model"
    modelCatalogLimited = "Only models from the confirmed usable {family} family were added to the configuration."
    codexPickerHint = "Codex uses {model} as the configured default. A custom provider does not need to expose a separate model picker; restart Codex to load the new configuration."
    modelEndpointHint = "The selected model or its provider does not support the API endpoint required by this app. Rerun setup with another available model (PowerShell: -Model MODEL; macOS/Linux: --model MODEL)."
    transientServerHint = "This is usually a temporary gateway or provider error. Setup retried once automatically; wait a minute and run it again if the error persists."
    pressEnter = "Press Enter to close"
    grokCommand = "Use the secure launcher 'grok-aimarket'. It selects Grok 4.5 and loads the API key only into the Grok child process."
    grokMissing = "Grok Build CLI was not found. Install the official CLI first from https://x.ai/news/grok-build-cli, then run this setup again."
    hermesEnvPath = "Hermes active credentials file"
    hermesProtocol = "Hermes API mode"
    hermesReasoning = "Hermes reasoning effort"
    hermesLegacyCleaned = "Removed obsolete managed credentials from the legacy Hermes path"
    hermesTransportFixed = "Applied the Hermes Windows streaming compatibility fix."
    hermesTransportCurrent = "Hermes Windows streaming compatibility fix is already installed."
    hermesReasoningSessionFixed = "Applied the Hermes Desktop session reasoning compatibility fix."
    hermesReasoningSessionCurrent = "Hermes Desktop session reasoning is already handled correctly."
    hermesRuntimeTesting = "Testing the configured connection through Hermes"
    hermesRuntimeOk = "Hermes received a model response successfully."
    droidConfigured = "Factory Droid custom model was updated. Restart Droid before testing."
    droidConfigHint = "Droid uses the local Factory settings file and keeps the API key in AIMARKET_API_KEY, never in settings.json."
}

function Load-Messages {
    $path = Join-Path $PSScriptRoot "setup-aimarket.$Lang.json"
    if (Test-Path -LiteralPath $path) {
        $loaded = Get-Content -Raw -Encoding UTF8 -LiteralPath $path | ConvertFrom-Json
        foreach ($property in $loaded.PSObject.Properties) {
            $script:Messages[$property.Name] = [string]$property.Value
        }
    }
}

function T {
    param([string]$Key, [hashtable]$Vars = @{})
    $value = if ($script:Messages.ContainsKey($Key)) { $script:Messages[$Key] } else { $Key }
    foreach ($name in $Vars.Keys) {
        $value = $value.Replace("{$name}", [string]$Vars[$name])
    }
    return $value
}

function Ok { param([string]$Text) Write-Host "[OK] $Text" -ForegroundColor Green }
function Warn { param([string]$Text) Write-Host "[WARN] $Text" -ForegroundColor Yellow }
function Fail { param([string]$Text) Write-Host "[FAIL] $Text" -ForegroundColor Red; exit 1 }
function Section { param([string]$Text) Write-Host ""; Write-Host "== $Text ==" }

function Set-SetupTelemetryStep {
    param([string]$Step)
    $script:SetupTelemetryStep = $Step
}

function Limit-SetupTelemetryText {
    param([string]$Text, [int]$MaxLength = 2000)
    if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
    $clean = $Text.Trim() -replace "[`r`n`t]+", " "
    if ($MaxLength -gt 3 -and $clean.Length -gt $MaxLength) {
        return $clean.Substring(0, $MaxLength - 3) + "..."
    }
    if ($MaxLength -gt 0 -and $clean.Length -gt $MaxLength) {
        return $clean.Substring(0, $MaxLength)
    }
    return $clean
}

trap {
    Fail $_.Exception.Message
}

function ConvertFrom-SecureStringPlainText {
    param([securestring]$SecureValue)
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally {
        if ($bstr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    }
}

function Mask-Key {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return "<empty>" }
    $trimmed = $Value.Trim()
    if ($trimmed.Length -le 12) { return $trimmed.Substring(0, [Math]::Min(4, $trimmed.Length)) + "..." }
    return $trimmed.Substring(0, 7) + "..." + $trimmed.Substring($trimmed.Length - 4)
}

function Get-EnvironmentCandidate {
    param([string]$Name)
    foreach ($scope in @("Process", "User")) {
        $value = [Environment]::GetEnvironmentVariable($Name, $scope)
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return [pscustomobject]@{ Name = $Name; Scope = $scope; Value = $value.Trim() }
        }
    }
    return $null
}

function Format-EnvironmentSource {
    param([object]$Candidate)
    if ($Candidate.PSObject.Properties["Source"] -and -not [string]::IsNullOrWhiteSpace([string]$Candidate.Source)) {
        return [string]$Candidate.Source
    }
    $scope = if ($Candidate.Scope -eq "User") { "user" } else { "current process" }
    return "$scope environment variable $($Candidate.Name)"
}

function Test-EnvironmentUrlMatches {
    param([string]$Name, [string]$ExpectedUrl)
    $candidate = Get-EnvironmentCandidate $Name
    if ($null -eq $candidate) { return $false }
    $actual = $candidate.Value.Trim().TrimEnd("/")
    $expected = $ExpectedUrl.Trim().TrimEnd("/")
    return [string]::Equals($actual, $expected, [StringComparison]::OrdinalIgnoreCase)
}

function Get-SavedApiKeyCandidate {
    foreach ($name in @("AIMARKET_API_KEY", "AIMARKET_OPENCODE_API_KEY")) {
        $candidate = Get-EnvironmentCandidate $name
        if ($null -ne $candidate) { return $candidate }
    }
    if ($App -eq "hermes") {
        $candidate = Get-HermesSavedApiKeyCandidate
        if ($null -ne $candidate) { return $candidate }
    }
    if (Test-EnvironmentUrlMatches "ANTHROPIC_BASE_URL" $AnthropicEndpoint) {
        $candidate = Get-EnvironmentCandidate "ANTHROPIC_AUTH_TOKEN"
        if ($null -ne $candidate) { return $candidate }
    }
    if (Test-EnvironmentUrlMatches "OPENAI_BASE_URL" $Endpoint) {
        $candidate = Get-EnvironmentCandidate "OPENAI_API_KEY"
        if ($null -ne $candidate) { return $candidate }
    }
    return $null
}

function Read-ApiKeySecret {
    param([string]$Prompt)
    $secure = Read-Host $Prompt -AsSecureString
    return (ConvertFrom-SecureStringPlainText $secure).Trim()
}

function Test-ApiKeyFormat {
    param([AllowEmptyString()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return $false }
    return $Value.Trim().StartsWith("sk-", [StringComparison]::Ordinal)
}

function Test-CanPromptForApiKey {
    return [Environment]::UserInteractive -and -not [Console]::IsInputRedirected
}

function Read-ValidApiKeySecret {
    param([string]$Prompt)
    while ($true) {
        $entered = Read-ApiKeySecret $Prompt
        if (Test-ApiKeyFormat $entered) { return $entered.Trim() }
        Warn (T "invalidKey")
        $Prompt = T "pasteKey"
    }
}

function Get-ClipboardApiKey {
    try { $value = [string](Get-Clipboard -Raw -ErrorAction Stop) } catch { return "" }
    if ([string]::IsNullOrWhiteSpace($value)) { return "" }
    $value = $value -replace "\s", ""
    if ($value -cmatch '^sk-[A-Za-z0-9_-]{16,200}$') { return $value }
    return ""
}

function Get-PlainApiKey {
    $setupKey = [Environment]::GetEnvironmentVariable("AIMARKET_SETUP_KEY", "Process")
    if ([string]::IsNullOrWhiteSpace($ApiKey) -and -not [string]::IsNullOrWhiteSpace($setupKey)) {
        [Environment]::SetEnvironmentVariable("AIMARKET_SETUP_KEY", $null, "Process")
        $script:ApiKey = $setupKey.Trim()
        Ok "$(T "setupKeyUsing"): $(Mask-Key $script:ApiKey)"
    }
    if ([string]::IsNullOrWhiteSpace($ApiKey) -and (Test-CanPromptForApiKey)) {
        $clipboardKey = Get-ClipboardApiKey
        if (-not [string]::IsNullOrWhiteSpace($clipboardKey)) {
            Write-Host "$(T "clipboardKeyFound"): $(Mask-Key $clipboardKey)"
            $entered = Read-ApiKeySecret (T "clipboardKeyPrompt")
            if ([string]::IsNullOrWhiteSpace($entered)) { return $clipboardKey }
            if (Test-ApiKeyFormat $entered) { return $entered.Trim() }
            Warn (T "invalidKey")
            return Read-ValidApiKeySecret (T "pasteKey")
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
        $provided = $ApiKey.Trim()
        if (Test-ApiKeyFormat $provided) { return $provided }
        if (-not (Test-CanPromptForApiKey)) { throw (T "invalidKey") }
        Warn (T "invalidKey")
        return Read-ValidApiKeySecret (T "pasteKey")
    }
    $candidate = Get-SavedApiKeyCandidate
    if ($null -ne $candidate) {
        $source = Format-EnvironmentSource $candidate
        Warn "$(T "savedKeyFound") ($source): $(Mask-Key $candidate.Value)"
        if (Test-CanPromptForApiKey) {
            $entered = Read-ApiKeySecret (T "savedKeyPrompt")
            if (-not [string]::IsNullOrWhiteSpace($entered)) {
                if (Test-ApiKeyFormat $entered) { return $entered.Trim() }
                Warn (T "invalidKey")
                return Read-ValidApiKeySecret (T "pasteKey")
            }
            if (-not (Test-ApiKeyFormat $candidate.Value)) {
                Warn (T "invalidKey")
                return Read-ValidApiKeySecret (T "pasteKey")
            }
        } elseif (-not (Test-ApiKeyFormat $candidate.Value)) {
            throw (T "invalidKey")
        }
        Ok "$(T "savedKeyUsing") ($source)."
        return $candidate.Value.Trim()
    }
    if (-not (Test-CanPromptForApiKey)) { throw (T "invalidKey") }
    return Read-ValidApiKeySecret (T "pasteKey")
}

function Normalize-OpenAIBaseUrl {
    param([string]$Value)
    $url = $Value.Trim().TrimEnd("/")
    if ($url -match "/(chat/completions|responses)$") {
        throw "Use the base URL https://router.cheap/v1, not a full endpoint path."
    }
    if (-not ($url -match "^https?://")) { throw "Endpoint must start with http:// or https://." }
    if (-not $url.EndsWith("/v1")) { $url = "$url/v1" }
    [void][Uri]$url
    return $url
}

function Normalize-AnthropicBaseUrl {
    param([string]$Value)
    $url = $Value.Trim().TrimEnd("/")
    if ($url.EndsWith("/v1")) { $url = $url.Substring(0, $url.Length - 3).TrimEnd("/") }
    if (-not ($url -match "^https?://")) { throw "Endpoint must start with http:// or https://." }
    [void][Uri]$url
    return $url
}

function Join-UrlPath {
    param([string]$BaseUrl, [string]$Path)
    return $BaseUrl.TrimEnd("/") + "/" + $Path.TrimStart("/")
}

function Invoke-RouterHttp {
    param(
        [ValidateSet("GET", "POST")] [string]$Method,
        [string]$Url,
        [string]$BearerToken,
        [object]$Body = $null,
        [hashtable]$Headers = @{}
    )
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $client = [System.Net.Http.HttpClient]::new()
    $client.Timeout = [TimeSpan]::FromSeconds(60)
    try {
        for ($attempt = 1; $attempt -le 2; $attempt++) {
            $request = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::new($Method), $Url)
            [void]$request.Headers.TryAddWithoutValidation("Authorization", "Bearer $BearerToken")
            [void]$request.Headers.TryAddWithoutValidation("User-Agent", "aimarket-setup/$($script:SetupScriptVersion)")
            foreach ($key in $Headers.Keys) {
                [void]$request.Headers.TryAddWithoutValidation($key, [string]$Headers[$key])
            }
            if ($null -ne $Body) {
                $json = $Body | ConvertTo-Json -Depth 20 -Compress
                $request.Content = [System.Net.Http.StringContent]::new($json, [Text.Encoding]::UTF8, "application/json")
            }
            try {
                $response = $client.SendAsync($request).GetAwaiter().GetResult()
                $text = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
                $result = [pscustomobject]@{ Ok = [bool]$response.IsSuccessStatusCode; StatusCode = [int]$response.StatusCode; Body = [string]$text }
                try {
                    $uri = [Uri]$Url
                    $script:SetupLastProbeMethod = $Method
                    $script:SetupLastProbePath = $uri.AbsolutePath
                    $script:SetupLastProbeStatus = [string]$result.StatusCode
                    if ($uri.AbsolutePath -match '/models/?$') { $script:SetupModelsProbeStatus = [string]$result.StatusCode }
                    elseif ($uri.AbsolutePath -match '/responses/?$') { $script:SetupResponsesProbeStatus = [string]$result.StatusCode }
                } catch { }
                $response.Dispose()
                $transient = $result.StatusCode -eq 429 -or ($result.StatusCode -ge 500 -and $result.StatusCode -le 599)
                if ($result.Ok -or -not $transient -or $attempt -eq 2) { return $result }
            }
            catch {
                $message = if ([string]::IsNullOrWhiteSpace($_.Exception.Message)) { "request timed out or was canceled" } else { $_.Exception.Message }
                try {
                    $uri = [Uri]$Url
                    $script:SetupLastProbeMethod = $Method
                    $script:SetupLastProbePath = $uri.AbsolutePath
                    $script:SetupLastProbeStatus = "0"
                    if ($uri.AbsolutePath -match '/models/?$') { $script:SetupModelsProbeStatus = "0" }
                    elseif ($uri.AbsolutePath -match '/responses/?$') { $script:SetupResponsesProbeStatus = "0" }
                } catch { }
                return [pscustomobject]@{ Ok = $false; StatusCode = 0; Body = $message; TransportError = $true }
            }
            finally { $request.Dispose() }
            Start-Sleep -Seconds 1
        }
    }
    finally { $client.Dispose() }
}

function Test-TransientProbeResponse {
    param($Response)
    if ($null -eq $Response) { return $true }
    $status = [int]$Response.StatusCode
    return $status -eq 0 -or $status -eq 408 -or $status -eq 429 -or ($status -ge 500 -and $status -le 599)
}

function Warn-NonFatalProbeFailure {
    param($Response, [string]$Label)
    $status = if ($null -eq $Response) { 0 } else { [int]$Response.StatusCode }
    if ($status -eq 0) {
        Warn (T "probeTimeout")
        return
    }
    Warn (T "probeNonFatal" @{ status = $status; label = $Label })
}

function Send-SetupTelemetry {
    param(
        [string]$Key,
        [string]$AppName,
        [string]$ActionName,
        [string]$Result,
        [string]$ErrorMessage = "",
        [string]$ErrorStep = "",
        [string]$ErrorFunction = "",
        [int]$ErrorLine = 0,
        [int]$ExitCode = 0
    )
    if ([string]::IsNullOrWhiteSpace($TelemetryEndpoint) -or [string]::IsNullOrWhiteSpace($Key)) { return }
    if ($DryRun) { return }
    if ($Result -eq "started") { Warn (T "telemetry") }
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        $client = [System.Net.Http.HttpClient]::new()
        $client.Timeout = [TimeSpan]::FromSeconds(10)
        try {
            $request = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::new("POST"), $TelemetryEndpoint)
            [void]$request.Headers.TryAddWithoutValidation("Authorization", "Bearer $Key")
            [void]$request.Headers.TryAddWithoutValidation("User-Agent", "aimarket-setup/$($script:SetupScriptVersion)")
            $body = @{
                app = $AppName
                os = "windows"
                action = $ActionName
                result = $Result
                script_version = $script:SetupScriptVersion
                script_language = $Lang
                dry_run = [bool]$DryRun
            }
            if (-not [string]::IsNullOrWhiteSpace($script:SetupTelemetrySessionId)) {
                $body["session_id"] = $script:SetupTelemetrySessionId
            }
            if ($Result -ne "started" -and $null -ne $script:SetupTelemetryStartedAt) {
                $durationMs = [int64]([DateTimeOffset]::UtcNow - $script:SetupTelemetryStartedAt).TotalMilliseconds
                if ($durationMs -gt 0) { $body["duration_ms"] = $durationMs }
            }
            if ($AppName -eq "codex") {
                $diagnostics = Get-CodexSetupDiagnostics -RequestedEndpoint $Endpoint -RequestedModel $script:Model -EnvironmentKey "AIMARKET_API_KEY"
                if ($diagnostics.Count -gt 0) { $body["diagnostics"] = $diagnostics }
            }
            if ($Result -eq "failed") {
                $limitedError = Limit-SetupTelemetryText $ErrorMessage 2000
                $limitedStep = Limit-SetupTelemetryText $ErrorStep 120
                $limitedFunction = Limit-SetupTelemetryText $ErrorFunction 120
                if (-not [string]::IsNullOrWhiteSpace($limitedError)) { $body["error_message"] = $limitedError }
                if (-not [string]::IsNullOrWhiteSpace($limitedStep)) { $body["error_step"] = $limitedStep.ToLowerInvariant() }
                if (-not [string]::IsNullOrWhiteSpace($limitedFunction)) { $body["error_function"] = $limitedFunction.ToLowerInvariant() }
                if ($ErrorLine -gt 0) { $body["error_line"] = $ErrorLine }
                if ($ExitCode -ne 0) { $body["exit_code"] = $ExitCode }
            }
            $json = $body | ConvertTo-Json -Depth 10 -Compress
            $request.Content = [System.Net.Http.StringContent]::new($json, [Text.Encoding]::UTF8, "application/json")
            $response = $client.SendAsync($request).GetAwaiter().GetResult()
            if (-not $response.IsSuccessStatusCode) { Warn (T "telemetryFailed") }
        }
        finally { $client.Dispose() }
    } catch {
        Warn (T "telemetryFailed")
    }
}

function Get-ErrorMessage {
    param([string]$Body)
    if ([string]::IsNullOrWhiteSpace($Body)) { return "" }
    try {
        $json = $Body | ConvertFrom-Json
        if ($json.error -and $json.error.message) { return [string]$json.error.message }
        if ($json.message) { return [string]$json.message }
    } catch {}
    $clean = $Body.Trim()
    if ($clean.Length -gt 500) { return $clean.Substring(0, 500) + "..." }
    return $clean
}

function Assert-HttpOk {
    param($Response, [string]$Label)
    if ($null -eq $Response) {
        throw "$Label failed: no HTTP response was returned by the setup helper."
    }
    $responseProperties = @($Response.PSObject.Properties | ForEach-Object { $_.Name })
    if ($responseProperties -notcontains "Ok" -or
        $responseProperties -notcontains "StatusCode" -or
        $responseProperties -notcontains "Body") {
        throw "$Label failed: setup helper returned an invalid HTTP response object."
    }
    if (-not $Response.Ok) {
        $message = Get-ErrorMessage $Response.Body
        $advice = ""
        if ($Response.StatusCode -eq 403 -and $message -match "(?i)(credit wallet|quota insufficient|model/family|not available for (GPT|Claude))") {
            $advice = T "crossFamilyAccessHint"
        } elseif ($Response.StatusCode -ge 500 -and $message -match "(?i)(not implemented|unsupported|does not support)") {
            $advice = T "modelEndpointHint"
        } elseif ($Response.StatusCode -ge 500 -and $Response.StatusCode -le 599) {
            $advice = T "transientServerHint"
        }
        $suffix = if ([string]::IsNullOrWhiteSpace($advice)) { "" } else { " $advice" }
        throw "$Label failed: HTTP $($Response.StatusCode) $message$suffix"
    }
}

function Get-ModelIdsFromBody {
    param([string]$Body)
    if ([string]::IsNullOrWhiteSpace($Body)) { return @() }
    try {
        $json = $Body | ConvertFrom-Json
    } catch {
        return @()
    }
    $items = @()
    if ($json -is [array]) {
        $items = @($json)
    } elseif ($json.PSObject.Properties["data"] -and $null -ne $json.data) {
        $items = @($json.data)
    } elseif ($json.PSObject.Properties["models"] -and $null -ne $json.models) {
        $items = @($json.models)
    }
    $seen = @{}
    $ids = New-Object System.Collections.Generic.List[string]
    foreach ($item in $items) {
        $value = ""
        if ($item -is [string]) {
            $value = $item
        } elseif ($null -ne $item) {
            if ($item.PSObject.Properties["id"] -and $null -ne $item.id) {
                $value = [string]$item.id
            } elseif ($item.PSObject.Properties["name"] -and $null -ne $item.name) {
                $value = [string]$item.name
            }
        }
        if ([string]::IsNullOrWhiteSpace($value)) { continue }
        if ($value.StartsWith("models/")) { $value = $value.Substring(7) }
        if (-not $seen.ContainsKey($value)) {
            $seen[$value] = $true
            $ids.Add($value)
        }
    }
    return $ids.ToArray()
}

function Test-SetupChatModel {
    param([string]$ModelName)
    $lower = $ModelName.ToLowerInvariant()
    foreach ($needle in @("embedding", "embed", "rerank", "whisper", "tts", "audio", "speech", "transcrib", "moderation", "image", "dall-e", "midjourney", "suno")) {
        if ($lower.Contains($needle)) { return $false }
    }
    return $true
}

function Test-ModelSupportsImageInput {
    param([string]$ModelName)
    if ([string]::IsNullOrWhiteSpace($ModelName)) { return $false }
    $lower = $ModelName.Trim().ToLowerInvariant()
    if ($lower -match '^kimi-k3(?:$|[-_.:])') { return $true }
    if ($lower -match '^deepseek-v4-flash-vision-exp(?:$|[-_.:])') { return $true }
    if ($lower -match '^claude-(?:.+)$') { return $true }
    if ($lower -match '^grok-4\.(?:5|6|7)(?:$|[-_.:])') { return $true }
	if ($lower -match '^gpt-(?:5|6-astra)(?:$|[-_.:])') { return $true }
    if ($lower -match '^gpt-4(?:o|\.1)(?:$|[-_.:])') { return $true }
    if ($lower -match '^o1(?:$|[-_.:])' -and $lower -notmatch '^o1-mini(?:$|[-_.:])') { return $true }
    if ($lower -match '^o3(?:$|[-_.:])' -and $lower -notmatch '^o3-mini(?:$|[-_.:])') { return $true }
    if ($lower -match '^o4-mini(?:$|[-_.:])') { return $true }
    return $false
}

function Test-ModelFamily {
    param([string]$ModelName, [string]$Family = "any")
    if ($Family -eq "any") { return $true }
    $lower = $ModelName.ToLowerInvariant()
    switch ($Family) {
        "claude" { return $lower.Contains("claude") }
        "responses" { return $lower.StartsWith("gpt-") -or $lower -match '^o[0-9]' }
        default { return $true }
    }
}

function Select-AvailableModel {
    param([string]$Preferred, [string[]]$Models, [string[]]$Candidates, [string]$Family = "any")
    if (($Models -contains $Preferred) -and (Test-SetupChatModel $Preferred) -and (Test-ModelFamily $Preferred $Family)) {
        return $Preferred
    }
    foreach ($candidate in $Candidates) {
        if (($Models -contains $candidate) -and (Test-SetupChatModel $candidate) -and (Test-ModelFamily $candidate $Family)) {
            return $candidate
        }
    }
    foreach ($candidate in $Models) {
        if ((Test-SetupChatModel $candidate) -and (Test-ModelFamily $candidate $Family)) {
            return $candidate
        }
    }
    return ""
}

function Get-ModelPreview {
    param([string[]]$Models, [int]$Max = 8)
    $preview = @($Models | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -First $Max)
    if ($preview.Count -eq 0) { return "<none>" }
    return ($preview -join ", ")
}

function Get-AvailableChatModels {
    $source = if ($script:OpenAIModels.Count -gt 0) { @($script:OpenAIModels) } else { @($script:Model) }
    $seen = @{}
    $models = New-Object System.Collections.Generic.List[string]
    foreach ($name in $source) {
        if ([string]::IsNullOrWhiteSpace($name)) { continue }
        if (-not (Test-SetupChatModel $name)) { continue }
        if (-not $seen.ContainsKey($name)) {
            $seen[$name] = $true
            $models.Add($name)
        }
    }
    return $models.ToArray()
}

function Get-RankedChatModels {
    $source = @(Get-AvailableChatModels)
    $seen = @{}
    $models = New-Object System.Collections.Generic.List[string]
    foreach ($name in $script:OpenAIModelCandidates) {
        if (($source -contains $name) -and (Test-SetupChatModel $name) -and -not $seen.ContainsKey($name)) {
            $seen[$name] = $true
            $models.Add($name)
        }
    }
    foreach ($name in $source) {
        if ([string]::IsNullOrWhiteSpace($name)) { continue }
        if (-not (Test-SetupChatModel $name)) { continue }
        if (-not $seen.ContainsKey($name)) {
            $seen[$name] = $true
            $models.Add($name)
        }
    }
    return $models.ToArray()
}

function Get-ModelFamily {
    param([string]$ModelName)
    $lower = $ModelName.Trim().ToLowerInvariant()
    if ($lower.StartsWith("claude-")) { return "claude" }
    if ($lower.StartsWith("grok-")) { return "grok" }
    if ($lower.StartsWith("gpt-") -or $lower -match '^o[0-9]') { return "gpt" }
    return $lower
}

function Get-ModelProbeCandidates {
    param([switch]$Responses)
    $seen = @{}
    $candidates = New-Object System.Collections.Generic.List[string]
    foreach ($candidate in @($script:Model) + @(Get-RankedChatModels)) {
        if ([string]::IsNullOrWhiteSpace($candidate) -or $seen.ContainsKey($candidate)) { continue }
        if ($App -eq "grok-build" -and $candidate -ne $script:Model) { continue }
        if ($App -eq "cursor" -and -not (Test-CursorCompatibleModel $candidate)) { continue }
        # Codex accepts only GPT/o models on Responses. Grok Build also uses
        # Responses, but its selected Grok model must be probed instead.
        if ($Responses -and $App -ne "grok-build" -and -not (Test-ModelFamily $candidate "responses")) { continue }
        $seen[$candidate] = $true
        $candidates.Add($candidate)
    }
    return $candidates.ToArray()
}

function Test-ModelAccessFailure {
    param($Response)
    if ($null -eq $Response -or $Response.StatusCode -ne 403) { return $false }
    $message = (Get-ErrorMessage $Response.Body).ToLowerInvariant()
    return $message -match "(model|family|credit wallet|quota|disabled|access)"
}

function Test-RetryableModelProbeFailure {
    param($Response)
    if ($null -eq $Response -or $Response.StatusCode -notin @(400, 403, 404)) { return $false }
    $message = (Get-ErrorMessage $Response.Body).ToLowerInvariant()
    return $message -match "(model|family|disabled|unsupported|unknown|not available|not found)"
}

function Limit-OpenAIModelsToFamily {
    param([string]$ModelName)
    $family = Get-ModelFamily $ModelName
    $filtered = @($script:OpenAIModels | Where-Object { (Get-ModelFamily $_) -eq $family })
    if ($filtered.Count -gt 0) { $script:OpenAIModels = $filtered }
}

function Complete-ModelProbe {
    param([string]$InitialModel, [string]$SelectedModel, [bool]$AccessLimited)
    $script:Model = $SelectedModel
    if ($SelectedModel -eq $InitialModel) { return }
    Warn "$(T "modelFallbackSelected"): $SelectedModel"
    if ($AccessLimited) {
        Limit-OpenAIModelsToFamily $SelectedModel
        Warn (T "modelCatalogLimited" @{ family = (Get-ModelFamily $SelectedModel) })
        Warn (T "crossFamilyAccessHint")
    }
}

function Get-OpenAIModels {
    param([string]$OpenAIEndpoint, [string]$Key)
    if ($script:OpenAIModels.Count -gt 0 -or $SkipEndpointTest) { return }
    Set-SetupTelemetryStep "model_discovery"
    $models = Invoke-RouterHttp -Method GET -Url (Join-UrlPath $OpenAIEndpoint "models") -BearerToken $Key
    if (Test-TransientProbeResponse $models) {
        Warn-NonFatalProbeFailure $models "GET /v1/models"
        $script:OpenAIModelCatalogVerified = $false
        $script:OpenAIModels = @($script:Model)
        return
    }
    Assert-HttpOk $models "GET /v1/models"
    $script:OpenAIModels = @(Get-ModelIdsFromBody $models.Body)
    $script:OpenAIModelCatalogVerified = $true
    if ($script:OpenAIModels.Count -eq 0) {
        throw "No OpenAI-compatible models are available for this key."
    }
}

function Get-ClaudeModels {
    param([string]$AnthropicBase, [string]$Key)
    if ($script:ClaudeModels.Count -gt 0 -or $SkipEndpointTest) { return }
    Set-SetupTelemetryStep "model_discovery"
    $headers = @{ "x-api-key" = $Key; "anthropic-version" = "2023-06-01" }
    $models = Invoke-RouterHttp -Method GET -Url (Join-UrlPath $AnthropicBase "v1/models") -BearerToken $Key -Headers $headers
    if (Test-TransientProbeResponse $models) {
        Warn-NonFatalProbeFailure $models "GET /v1/models"
        $script:ClaudeModelCatalogVerified = $false
        $script:ClaudeModels = @($script:ClaudeModel)
        return
    }
    Assert-HttpOk $models "GET /v1/models"
    $script:ClaudeModels = @(Get-ModelIdsFromBody $models.Body)
    $script:ClaudeModelCatalogVerified = $true
    if ($script:ClaudeModels.Count -eq 0) {
        throw "No Anthropic-compatible models are available for this key."
    }
}

function Ensure-OpenAIModel {
    param([string]$OpenAIEndpoint, [string]$Key)
    if ($SkipEndpointTest) { return }
    Get-OpenAIModels -OpenAIEndpoint $OpenAIEndpoint -Key $Key
    $selected = Select-AvailableModel -Preferred $script:Model -Models $script:OpenAIModels -Candidates $script:OpenAIModelCandidates -Family "any"
    if ([string]::IsNullOrWhiteSpace($selected)) {
        throw "No chat model suitable for app setup is available for this key. Available models: $(Get-ModelPreview $script:OpenAIModels)"
    }
    if ($selected -ne $script:Model) {
        Warn "Model '$($script:Model)' is not available for this key; using '$selected'. Available models: $(Get-ModelPreview $script:OpenAIModels)"
        $script:Model = $selected
    }
}

function Ensure-CodexModel {
    param([string]$OpenAIEndpoint, [string]$Key)
    if ($SkipEndpointTest) { return }
    Get-OpenAIModels -OpenAIEndpoint $OpenAIEndpoint -Key $Key
    $selected = Select-AvailableModel -Preferred $script:Model -Models $script:OpenAIModels -Candidates $script:OpenAIModelCandidates -Family "responses"
    if ([string]::IsNullOrWhiteSpace($selected)) {
        if ($AllowMissingModel) {
            Warn "Model '$($script:Model)' is not listed as Responses-compatible for this key; keeping it because -AllowMissingModel was supplied."
            return
        }
        throw "No GPT/Responses-compatible model is available for this key. Available models: $(Get-ModelPreview $script:OpenAIModels)"
    }
    if ($selected -ne $script:Model) {
        Warn "Model '$($script:Model)' is not available for Codex Responses; using '$selected'. Available models: $(Get-ModelPreview $script:OpenAIModels)"
        $script:Model = $selected
    }
}

function Ensure-ClaudeModel {
    param([string]$AnthropicBase, [string]$Key)
    if ($SkipEndpointTest) { return }
    Get-ClaudeModels -AnthropicBase $AnthropicBase -Key $Key
    $selected = Select-AvailableModel -Preferred $script:ClaudeModel -Models $script:ClaudeModels -Candidates $script:ClaudeModelCandidates -Family "claude"
    if ([string]::IsNullOrWhiteSpace($selected)) {
        throw "No Claude model is available for this key. Available models: $(Get-ModelPreview $script:ClaudeModels). $(T "claudeModelAccessHint")"
    }
    if ($selected -ne $script:ClaudeModel) {
        Warn "Claude model '$($script:ClaudeModel)' is not available for this key; using '$selected'. Available models: $(Get-ModelPreview $script:ClaudeModels)"
        $script:ClaudeModel = $selected
    }
}

function Ensure-GrokModel {
    param([string]$OpenAIEndpoint, [string]$Key)
    $script:Model = $GrokModel
    if ($SkipEndpointTest) { return }
    Get-OpenAIModels -OpenAIEndpoint $OpenAIEndpoint -Key $Key
    if ($script:OpenAIModels -notcontains $GrokModel) {
        throw "Model '$GrokModel' is not available for this key. Available models: $(Get-ModelPreview $script:OpenAIModels). $(T "crossFamilyAccessHint")"
    }
}

function Test-CursorCompatibleModel {
    param([string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) { return $false }
    $lower = $Name.Trim().ToLowerInvariant()
    return -not ($lower.StartsWith("claude-") -or $lower.StartsWith("gemini-"))
}

function Ensure-CursorModel {
    if (Test-CursorCompatibleModel $script:Model) { return }
    $source = if ($script:OpenAIModels.Count -gt 0) { @($script:OpenAIModels) } else { @($script:OpenAIModelCandidates) }
    $compatible = @($source | Where-Object { (Test-SetupChatModel $_) -and (Test-CursorCompatibleModel $_) })
    $selected = Select-AvailableModel -Preferred "gpt-6-astra" -Models $compatible -Candidates $script:OpenAIModelCandidates -Family "any"
    if ([string]::IsNullOrWhiteSpace($selected)) {
        throw "Cursor's OpenAI Base URL override cannot route Claude/Anthropic models, and no compatible GPT/Grok model is available for this key."
    }
    Warn "Model '$($script:Model)' cannot use Cursor's OpenAI Base URL override; using '$selected'."
    $script:Model = $selected
}

function Select-DefaultOpenAIModelInteractive {
    param([string]$AppName)
    if ($AppName -notin @("hermes", "cursor", "droid")) { return }
    if (-not $ChooseModel) { return }
    if ($SkipEndpointTest -or $script:ModelExplicit -or [Console]::IsInputRedirected) { return }

    $models = @(Get-RankedChatModels)
    if ($AppName -eq "cursor") {
        $models = @($models | Where-Object { Test-CursorCompatibleModel $_ })
    }
    if ($models.Count -eq 0) { return }
    if ($models.Count -eq 1) {
        $script:Model = $models[0]
        return
    }

    $default = Select-AvailableModel -Preferred $script:Model -Models $models -Candidates $script:OpenAIModelCandidates -Family "any"
    if ([string]::IsNullOrWhiteSpace($default)) { $default = $models[0] }
    $label = Get-AppLabel $AppName
    Set-SetupTelemetryStep "model_choice"

    while ($true) {
        Section (T "selectDefaultModel" @{ app = $label })
        for ($i = 0; $i -lt $models.Count; $i++) {
            $suffix = if ($models[$i] -eq $default) { " (recommended)" } else { "" }
            Write-Host "$($i + 1)) $($models[$i])$suffix"
        }
        Write-Host (T "selectDefaultModelHint" @{ model = $default })
        $raw = (Read-Host (T "choice")).Trim()
        if ([string]::IsNullOrWhiteSpace($raw)) {
            $script:Model = $default
            break
        }

        $n = 0
        if ([int]::TryParse($raw, [ref]$n) -and $n -ge 1 -and $n -le $models.Count) {
            $script:Model = $models[$n - 1]
            break
        }

        Warn (T "invalidModelChoice")
    }

    Ok "$(T "selectedDefaultModel"): $script:Model"
}

function Prepare-SetupModel {
    param([string]$AppName, [string]$Key, [string]$OpenAIEndpoint, [string]$AnthropicBase)
    if ($AppName -eq "codex") {
        Ensure-CodexModel -OpenAIEndpoint $OpenAIEndpoint -Key $Key
        return
    }
    if ($AppName -eq "claude-code") {
        return
    }
    if ($AppName -eq "grok-build") {
        Ensure-GrokModel -OpenAIEndpoint $OpenAIEndpoint -Key $Key
    } else {
        Ensure-OpenAIModel -OpenAIEndpoint $OpenAIEndpoint -Key $Key
        if ($AppName -eq "cursor") { Ensure-CursorModel }
    }
}

function Test-OpenAIKey {
    param([string]$OpenAIEndpoint, [string]$Key, [string]$ModelName, [switch]$Responses)
    if ($SkipEndpointTest) { Warn "Endpoint test skipped."; return }
    Set-SetupTelemetryStep "endpoint_test"
    Section (T "testing")
    Ensure-OpenAIModel -OpenAIEndpoint $OpenAIEndpoint -Key $Key
    if ($script:OpenAIModelCatalogVerified) { Ok "GET /v1/models" }
    if ($SkipLiveModelTest) {
        Warn "Skipped live model test. /v1/models auth passed, but model execution was not tested."
        return
    }
    $path = if ($Responses) { "responses" } else { "chat/completions" }
    $initialModel = $script:Model
    $accessLimited = $false
    $lastResponse = $null
    $candidates = @(Get-ModelProbeCandidates -Responses:$Responses)
    if ($candidates.Count -eq 0) {
        $endpointName = if ($Responses) { "Responses" } else { "Chat Completions" }
        throw "No model candidates are available for $endpointName endpoint testing. Verify that the selected model is listed by /v1/models."
    }
    foreach ($candidate in $candidates) {
        if ($Responses) {
            $body = @{ model = $candidate; input = "Reply with OK."; max_output_tokens = 8; stream = $false }
        } else {
            $body = @{ model = $candidate; messages = @(@{ role = "user"; content = "Reply with OK." }); max_tokens = 8; stream = $false }
        }
        $lastResponse = Invoke-RouterHttp -Method POST -Url (Join-UrlPath $OpenAIEndpoint $path) -BearerToken $Key -Body $body
        if (Test-TransientProbeResponse $lastResponse) {
            Warn-NonFatalProbeFailure $lastResponse "POST /v1/$path"
            return
        }
        if ($lastResponse.Ok) {
            Complete-ModelProbe -InitialModel $initialModel -SelectedModel $candidate -AccessLimited $accessLimited
            Ok "POST /v1/$path"
            return
        }
        if (Test-ModelAccessFailure $lastResponse) { $accessLimited = $true }
        if ((Test-RetryableModelProbeFailure $lastResponse) -and $App -ne "grok-build") {
            Warn (T "modelProbeRetry" @{ model = $candidate })
            continue
        }
        Assert-HttpOk $lastResponse "POST /v1/$path"
    }
    Assert-HttpOk $lastResponse "POST /v1/$path"
}

function Test-AnthropicKey {
    param([string]$AnthropicBase, [string]$Key, [string]$ModelName)
    if ($SkipEndpointTest) { Warn "Endpoint test skipped."; return }
    Set-SetupTelemetryStep "endpoint_test"
    Section (T "testing")
    Ensure-ClaudeModel -AnthropicBase $AnthropicBase -Key $Key
    $ModelName = $script:ClaudeModel
    if ($script:ClaudeModelCatalogVerified) { Ok "GET /v1/models" }
    $body = @{ model = $ModelName; max_tokens = 8; messages = @(@{ role = "user"; content = "Reply with OK." }) }
    $headers = @{ "x-api-key" = $Key; "anthropic-version" = "2023-06-01" }
    $live = Invoke-RouterHttp -Method POST -Url (Join-UrlPath $AnthropicBase "v1/messages") -BearerToken $Key -Body $body -Headers $headers
    if (Test-TransientProbeResponse $live) {
        Warn-NonFatalProbeFailure $live "POST /v1/messages"
        return
    }
    Assert-HttpOk $live "POST /v1/messages"
    Ok "POST /v1/messages"
}

function Backup-File {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) {
        $backup = "$Path.aimarket-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        if (-not $DryRun) {
            Copy-Item -LiteralPath $Path -Destination $backup
            Ok "Backup: $backup"
        } else {
            Ok "Would create backup: $backup"
        }
    }
}

function Save-TextUtf8NoBom {
    param([string]$Path, [string]$Text)
    if ($DryRun) { Write-Host (Protect-SetupPreviewText $Text); return }
    $directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $temporary = Join-Path $directory ("." + [IO.Path]::GetFileName($Path) + ".tmp-" + [guid]::NewGuid().ToString("N"))
    $replaceBackup = "$temporary.replace-backup"
    try {
        [IO.File]::WriteAllText($temporary, $Text, [Text.UTF8Encoding]::new($false))
        if (Test-Path -LiteralPath $Path) {
            [IO.File]::Replace($temporary, $Path, $replaceBackup)
        } else {
            [IO.File]::Move($temporary, $Path)
        }
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
        if (Test-Path -LiteralPath $replaceBackup) { Remove-Item -LiteralPath $replaceBackup -Force }
    }
}

function Protect-SetupPreviewText {
    param([string]$Text)
    if ([string]::IsNullOrEmpty($Text)) { return $Text }
    # Dry-run output may contain preserved third-party config. Never print
    # credential-like TOML values even when they were already on disk.
    return ($Text -replace '(?im)^(\s*(?:api[_-]?key|access[_-]?token|auth[_-]?token|experimental_bearer_token|secret|password)\s*=\s*)(.+)$', '$1"[REDACTED]"')
}

function ConvertTo-TomlString { param([string]$Value) return '"' + $Value.Replace('\', '\\').Replace('"', '\"') + '"' }

function Remove-TomlTable {
    param([string[]]$Lines, [string]$TableName)
    $result = New-Object System.Collections.Generic.List[string]
    $pattern = "^\s*\[$([regex]::Escape($TableName))\]\s*(?:#.*)?$"
    $i = 0
    while ($i -lt $Lines.Count) {
        if ($Lines[$i] -match $pattern) {
            $i++
            while ($i -lt $Lines.Count -and $Lines[$i] -notmatch "^\s*\[") { $i++ }
            continue
        }
        $result.Add($Lines[$i])
        $i++
    }
    return $result.ToArray()
}

function Remove-TomlTableTree {
    param([string[]]$Lines, [string]$TableName)
    $result = New-Object System.Collections.Generic.List[string]
    $escaped = [regex]::Escape($TableName)
    $pattern = "^\s*\[$escaped(?:\.[^\]]+)?\]\s*(?:#.*)?$"
    $skip = $false
    foreach ($line in $Lines) {
        if ($line -match $pattern) {
            $skip = $true
            continue
        }
        if ($skip -and $line -match "^\s*\[") { $skip = $false }
        if (-not $skip) { $result.Add($line) }
    }
    return $result.ToArray()
}

function Repair-CodexProviderTables {
    param([string[]]$Lines)
    $out = New-Object System.Collections.Generic.List[string]
    $reserved = @("openai", "ollama", "lmstudio")
    $i = 0
    while ($i -lt $Lines.Count) {
        $line = $Lines[$i]
        if ($line -match "^\s*\[model_providers\.([A-Za-z0-9_-]+)\]\s*(?:#.*)?$") {
            $providerId = [string]$Matches[1]
            $section = New-Object System.Collections.Generic.List[string]
            $section.Add($line)
            $i++
            while ($i -lt $Lines.Count -and $Lines[$i] -notmatch "^\s*\[") {
                $section.Add($Lines[$i])
                $i++
            }
            if ($reserved -contains $providerId.ToLowerInvariant()) { continue }
            $hasName = $false
            $nameIndex = -1
            for ($j = 1; $j -lt $section.Count; $j++) {
                if ($section[$j] -match "^\s*name\s*=") {
                    $hasName = $true
                    $nameIndex = $j
                    break
                }
            }
            if ($hasName -and (($section[$nameIndex] -match '^\s*name\s*=\s*"\s*"\s*(?:#.*)?$') -or ($section[$nameIndex] -match "^\s*name\s*=\s*'\s*'\s*(?:#.*)?$"))) {
                $indent = ($section[$nameIndex] -replace "^(\s*).*$", '$1')
                $section[$nameIndex] = "${indent}name = $(ConvertTo-TomlString $providerId)"
            } elseif (-not $hasName) {
                $section.Insert(1, "name = $(ConvertTo-TomlString $providerId)")
            }
            foreach ($item in $section) { $out.Add($item) }
            continue
        }
        $out.Add($line)
        $i++
    }
    return $out.ToArray()
}

function Get-CodexHome {
    $homeDir = [Environment]::GetEnvironmentVariable("CODEX_HOME", "Process")
    if ([string]::IsNullOrWhiteSpace($homeDir)) { $homeDir = [Environment]::GetEnvironmentVariable("CODEX_HOME", "User") }
    if ([string]::IsNullOrWhiteSpace($homeDir)) { $homeDir = Join-Path $env:USERPROFILE ".codex" }
    return [IO.Path]::GetFullPath($homeDir)
}

function Get-CodexConfigPath {
    return Join-Path (Get-CodexHome) "config.toml"
}

function Get-CodexProfileFiles {
    $codexHomePath = Get-CodexHome
    if (-not (Test-Path -LiteralPath $codexHomePath)) { return @() }
    return @(Get-ChildItem -LiteralPath $codexHomePath -Filter "*.config.toml" -File -ErrorAction SilentlyContinue)
}

function Install-CodexIfMissing {
    param([switch]$DryRun)
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($null -ne $winget) {
        if ($DryRun) {
            Warn "DryRun: would run 'winget install Codex -s msstore'."
        }
        else {
            Warn "Codex command was not found. Trying Microsoft Store install through winget..."
            & winget install Codex -s msstore --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0 -and $null -ne (Get-Command codex -ErrorAction SilentlyContinue)) { return }
            Warn "winget did not make codex available in PATH; trying official standalone installer."
        }
    }
    else {
        Warn "winget was not found; trying official standalone installer."
    }
    if ($DryRun) {
        Warn "DryRun: would run official installer from https://chatgpt.com/codex/install.ps1."
        return
    }
    $previousNonInteractive = $env:CODEX_NON_INTERACTIVE
    try {
        $env:CODEX_NON_INTERACTIVE = "1"
        Invoke-Expression (Invoke-RestMethod -Uri "https://chatgpt.com/codex/install.ps1")
    }
    finally {
        if ($null -eq $previousNonInteractive) { Remove-Item Env:CODEX_NON_INTERACTIVE -ErrorAction SilentlyContinue }
        else { $env:CODEX_NON_INTERACTIVE = $previousNonInteractive }
    }
}

function Get-RunningCodexProcesses {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { return @() }
    try {
        return @(Get-CimInstance Win32_Process -Filter "Name = 'codex.exe'" -ErrorAction Stop | ForEach-Object {
            [pscustomobject]@{ Id = [int]$_.ProcessId; CommandLine = [string]$_.CommandLine; ExecutablePath = [string]$_.ExecutablePath }
        })
    } catch {
        return @()
    }
}

function Stop-CodexForSetup {
    $script:CodexRestartState = @()
    $running = @(Get-RunningCodexProcesses)
    if ($running.Count -eq 0) { return }
    if (-not $script:RestartCodexEffective) {
        Warn "Codex is already running. Its process will not see the new API-key environment variable until it is fully restarted. Close Codex and rerun setup, or omit -NoRestartCodex to let setup restart a bare standalone CLI."
        return
    }
    if ($DryRun) {
        Warn "DryRun: would close and relaunch $($running.Count) standalone Codex process(es)."
        return
    }
    foreach ($item in $running) {
        $commandLine = $item.CommandLine.Trim()
        if ([string]::IsNullOrWhiteSpace($item.ExecutablePath) -or $commandLine -notmatch '^\s*(?:"[^"]+"|\S+)\s*$') {
            $message = "Codex Desktop/IDE/app-server or a CLI with arguments is running. Close it fully and rerun setup so it can receive the new API-key environment. Setup cannot safely reconfigure an already-running Codex process."
            if ($script:RestartCodexEffective) { throw $message }
            Warn "$message (continuing because -NoRestartCodex was requested.)"
            return
        }
    }
    foreach ($item in $running) {
        $process = Get-Process -Id $item.Id -ErrorAction SilentlyContinue
        if ($null -eq $process) { continue }
        $script:CodexRestartState += [pscustomobject]@{ ExecutablePath = $item.ExecutablePath }
        [void]$process.CloseMainWindow()
        if (-not $process.WaitForExit(5000)) {
            Stop-Process -Id $item.Id -Force -ErrorAction Stop
        }
    }
    Write-Ok "Closed running standalone Codex process(es) before changing configuration."
}

function Start-CodexAfterSetup {
    $restartState = @($script:CodexRestartState)
    if ($DryRun -or $restartState.Count -eq 0) { return }
    foreach ($item in $restartState) {
        try {
            Start-Process -FilePath $item.ExecutablePath | Out-Null
        } catch {
            Warn "Codex was configured, but could not be relaunched automatically. Start it manually from the usual shortcut."
        }
    }
    $script:CodexRestartState = @()
    Write-Ok "Relaunched Codex after configuration."
}

function Write-CodexAuthDiagnostics {
    param([string]$Provider, [string]$EnvironmentKey, [string]$ConfigPath)
    $processPresent = -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($EnvironmentKey, "Process"))
    $userPresent = -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($EnvironmentKey, "User"))
    if (-not $processPresent -or -not $userPresent) {
        throw "Provider auth diagnostic failed: $EnvironmentKey is not present in both the current process and the user environment."
    }
    Ok "Codex auth: provider '$Provider' uses env_key '$EnvironmentKey' (present in process and user environment)."
    $profiles = @(Get-CodexProfileFiles)
    if ($profiles.Count -gt 0) {
        $names = (($profiles | Select-Object -ExpandProperty Name) -join ", ")
        Warn "Found named Codex profile file(s): $names. A profile selected with 'codex --profile <name>' can override model/model_provider from $ConfigPath; verify the selected profile after restart."
    }
}

function Invoke-CodexRuntimeProbe {
    param([string]$ModelName)
    if ($SkipCodexRuntimeTest) {
        $script:CodexRuntimeProbeStatus = "skipped"
        Warn "Codex runtime probe skipped by request."
        return
    }
    $command = Get-Command codex -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $command -or [string]::IsNullOrWhiteSpace($command.Source)) {
        $script:CodexRuntimeProbeStatus = "codex-missing"
        Warn "Codex runtime probe skipped because the codex command is not available."
        return
    }
    try {
        $help = (& $command.Source exec --help 2>&1 | Out-String)
        if ($help -notmatch "(?m)--ephemeral\b") {
            $script:CodexRuntimeProbeStatus = "unsupported"
            Warn "Codex runtime probe skipped because this Codex version has no --ephemeral mode."
            return
        }
    } catch {
        $script:CodexRuntimeProbeStatus = "help-failed"
        Warn "Codex runtime probe could not inspect the installed Codex CLI."
        return
    }

    Set-SetupTelemetryStep "codex_runtime_probe"
    $temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("aimarket-codex-probe-" + [guid]::NewGuid().ToString("N"))
    $stdoutPath = Join-Path $temporaryRoot "stdout.log"
    $stderrPath = Join-Path $temporaryRoot "stderr.log"
    $argumentList = 'exec --ephemeral --sandbox read-only --skip-git-repo-check --json -m "' + ($ModelName -replace '"', '\"') + '" "Reply with exactly OK."'
    $process = $null
    try {
        New-Item -ItemType Directory -Path $temporaryRoot -Force | Out-Null
        $process = Start-Process -FilePath $command.Source -ArgumentList $argumentList -WorkingDirectory $env:TEMP -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru
        if (-not $process.WaitForExit(90000)) {
            try { $process.Kill() } catch { }
            $script:CodexRuntimeProbeStatus = "timeout"
            $script:CodexRuntimeProbeExitCode = "124"
            Warn "Codex runtime probe timed out after 90 seconds."
            return
        }
        $script:CodexRuntimeProbeExitCode = [string]$process.ExitCode
        $output = ""
        if (Test-Path -LiteralPath $stdoutPath) { $output += Get-Content -Raw -LiteralPath $stdoutPath }
        if (Test-Path -LiteralPath $stderrPath) { $output += "`n" + (Get-Content -Raw -LiteralPath $stderrPath) }
        if ($process.ExitCode -eq 0) {
            $script:CodexRuntimeProbeStatus = "passed"
            Ok "Codex runtime probe passed: the CLI completed through the configured provider."
        } elseif ($output -match "(?i)api\.openai\.com") {
            $script:CodexRuntimeProbeStatus = "wrong-provider-openai"
            Warn "Codex runtime probe reached api.openai.com instead of aimarket. Check --profile, -c model_provider, CODEX_HOME, or a stale app-server."
        } elseif ($output -match "(?i)(401|unauthorized|invalid[_ -]?api[_ -]?key)") {
            $script:CodexRuntimeProbeStatus = "failed-401"
            Warn "Codex runtime probe received an authorization failure. The configured key/provider was not accepted."
        } else {
            $script:CodexRuntimeProbeStatus = "failed"
            Warn "Codex runtime probe failed (exit $($process.ExitCode)); setup configuration was still written."
        }
    } catch {
        $script:CodexRuntimeProbeStatus = "launch-failed"
        Warn "Codex runtime probe could not be launched; setup configuration was still written."
    } finally {
        if ($null -ne $process -and -not $process.HasExited) { try { $process.Kill() } catch { } }
        if (Test-Path -LiteralPath $temporaryRoot) { Remove-Item -LiteralPath $temporaryRoot -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

function Get-CodexTomlSetting {
    param(
        [string[]]$Lines,
        [string]$TableName,
        [string]$Key
    )
    $inTable = [string]::IsNullOrWhiteSpace($TableName)
    foreach ($line in $Lines) {
        if ($line -match '^\s*\[') {
            $inTable = $line -match ("^\s*\[" + [regex]::Escape($TableName) + "\]\s*(?:#.*)?$")
            continue
        }
        if (-not $inTable) { continue }
        $settingPattern = '^\s*' + [regex]::Escape($Key) + '\s*=\s*(?:"([^"]*)"|''([^'']*)''|([^\s#]+))\s*(?:#.*)?$'
        if ($line -match $settingPattern) {
            if ($null -ne $Matches[1]) { return [string]$Matches[1] }
            if ($null -ne $Matches[2]) { return [string]$Matches[2] }
            return [string]$Matches[3]
        }
    }
    return $null
}

function Assert-CodexProviderConfiguration {
    param(
        [string]$ConfigPath,
        [string]$Provider,
        [string]$BaseUrl,
        [string]$EnvironmentKey,
        [string]$ModelName
    )
    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        throw "Codex configuration was not written: $ConfigPath"
    }
    $lines = @((Get-Content -Raw -LiteralPath $ConfigPath) -replace "`r`n", "`n" -replace "`r", "`n" -split "`n")
    $rootProvider = Get-CodexTomlSetting -Lines $lines -TableName "" -Key "model_provider"
    $rootModel = Get-CodexTomlSetting -Lines $lines -TableName "" -Key "model"
    $providerName = Get-CodexTomlSetting -Lines $lines -TableName "model_providers.$Provider" -Key "name"
    $providerBase = Get-CodexTomlSetting -Lines $lines -TableName "model_providers.$Provider" -Key "base_url"
    $providerEnv = Get-CodexTomlSetting -Lines $lines -TableName "model_providers.$Provider" -Key "env_key"
    $providerAuth = Get-CodexTomlSetting -Lines $lines -TableName "model_providers.$Provider" -Key "requires_openai_auth"
    $providerWire = Get-CodexTomlSetting -Lines $lines -TableName "model_providers.$Provider" -Key "wire_api"
    if ($rootProvider -ne $Provider -or $rootModel -ne $ModelName -or
        [string]::IsNullOrWhiteSpace($providerName) -or $providerBase -ne $BaseUrl -or
        $providerEnv -ne $EnvironmentKey -or $providerAuth -ne "false" -or $providerWire -ne "responses") {
        throw "Codex configuration verification failed at $ConfigPath. Expected model_provider='$Provider', model='$ModelName', base_url='$BaseUrl', env_key='$EnvironmentKey', requires_openai_auth=false, wire_api=responses."
    }
    Ok "Codex configuration verified: $ConfigPath (provider '$Provider', endpoint '$BaseUrl')."
    Warn "If Codex later reports URL https://api.openai.com/v1/responses, that invocation did not use provider '$Provider' (usually a --profile/CLI override or an already-running Desktop/IDE app-server)."

    foreach ($profile in @(Get-CodexProfileFiles)) {
        $profileLines = @((Get-Content -Raw -LiteralPath $profile.FullName) -replace "`r`n", "`n" -replace "`r", "`n" -split "`n")
        $profileProvider = Get-CodexTomlSetting -Lines $profileLines -TableName "" -Key "model_provider"
        if (-not [string]::IsNullOrWhiteSpace($profileProvider) -and $profileProvider -ne $Provider) {
            Warn "Profile '$($profile.Name)' selects provider '$profileProvider' and overrides the aimarket default when used with 'codex --profile'."
        }
    }
}

function Get-CodexSetupDiagnostics {
    param([string]$RequestedEndpoint, [string]$RequestedModel, [string]$EnvironmentKey)
    $result = [ordered]@{ schema = "1" }
    try {
        $processHome = [Environment]::GetEnvironmentVariable("CODEX_HOME", "Process")
        $userHome = [Environment]::GetEnvironmentVariable("CODEX_HOME", "User")
        $result.codex_home_source = if (-not [string]::IsNullOrWhiteSpace($processHome)) { "process" } elseif (-not [string]::IsNullOrWhiteSpace($userHome)) { "user" } else { "default" }
        $homePath = Get-CodexHome
        try {
            $homeBytes = [Text.UTF8Encoding]::new($false).GetBytes($homePath.ToLowerInvariant())
            $homeHash = [Security.Cryptography.SHA256]::Create().ComputeHash($homeBytes)
            $result.codex_home_sha256 = ([BitConverter]::ToString($homeHash) -replace "-", "").ToLowerInvariant()
        } catch { }
        $command = Get-Command codex -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            try { $version = (& $command.Source --version 2>$null | Select-Object -First 1); if ($version) { $result.codex_version = ([string]$version).Trim() } } catch { }
        }
        $configPath = Get-CodexConfigPath
        $result.config_exists = ([bool](Test-Path -LiteralPath $configPath -PathType Leaf)).ToString().ToLowerInvariant()
        if (Test-Path -LiteralPath $configPath -PathType Leaf) {
            try { $result.config_sha256 = (Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash.ToLowerInvariant() } catch { }
            try {
                $lines = @((Get-Content -Raw -LiteralPath $configPath) -replace "`r`n", "`n" -replace "`r", "`n" -split "`n")
                $result.config_model = [string](Get-CodexTomlSetting -Lines $lines -TableName "" -Key "model")
                $result.config_model_provider = [string](Get-CodexTomlSetting -Lines $lines -TableName "" -Key "model_provider")
                $provider = if ($result.config_model_provider) { [string]$result.config_model_provider } else { "aimarket" }
                $result.provider_name = [string](Get-CodexTomlSetting -Lines $lines -TableName "model_providers.$provider" -Key "name")
                $base = [string](Get-CodexTomlSetting -Lines $lines -TableName "model_providers.$provider" -Key "base_url")
                if ($base) { try { $uri = [Uri]$base; $result.provider_base_host = $uri.Host; $result.provider_base_path = $uri.AbsolutePath } catch { } }
                $result.provider_env_key = [string](Get-CodexTomlSetting -Lines $lines -TableName "model_providers.$provider" -Key "env_key")
                $result.provider_requires_openai_auth = [string](Get-CodexTomlSetting -Lines $lines -TableName "model_providers.$provider" -Key "requires_openai_auth")
                $result.provider_wire_api = [string](Get-CodexTomlSetting -Lines $lines -TableName "model_providers.$provider" -Key "wire_api")
            } catch { }
        }
        $profiles = @(Get-CodexProfileFiles)
        $result.profiles_count = [string]$profiles.Count
        $otherProviders = New-Object System.Collections.Generic.List[string]
        foreach ($profile in $profiles) {
            try {
                $profileLines = @((Get-Content -Raw -LiteralPath $profile.FullName) -replace "`r`n", "`n" -replace "`r", "`n" -split "`n")
                $profileProvider = [string](Get-CodexTomlSetting -Lines $profileLines -TableName "" -Key "model_provider")
                if ($profileProvider -and $otherProviders -notcontains $profileProvider) { $otherProviders.Add($profileProvider) }
            } catch { }
        }
        $result.profiles_other_provider_count = [string](@($otherProviders | Where-Object { $_ -ne "aimarket" -and $_ -ne "routercheap" }).Count)
        if ($otherProviders.Count -gt 0) { $result.profiles_provider_ids = ($otherProviders -join ",") }
        $result.api_key_process_present = (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($EnvironmentKey, "Process"))).ToString().ToLowerInvariant()
        $result.api_key_user_present = (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($EnvironmentKey, "User"))).ToString().ToLowerInvariant()
        $result.openai_api_key_process_present = (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "Process"))).ToString().ToLowerInvariant()
        $result.openai_base_url_process_present = (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("OPENAI_BASE_URL", "Process"))).ToString().ToLowerInvariant()
        $result.codex_profile_process_present = (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("CODEX_PROFILE", "Process"))).ToString().ToLowerInvariant()
        $running = @(Get-RunningCodexProcesses)
        if ($running.Count -eq 0) { $result.codex_process_state = "none" }
        else {
            $bare = @($running | Where-Object { $_.CommandLine.Trim() -match '^\s*(?:"[^"]+"|\S+)\s*$' }).Count
            $withArgs = $running.Count - $bare
            $result.codex_process_state = if ($bare -gt 0 -and $withArgs -gt 0) { "bare+args" } elseif ($withArgs -gt 0) { "args" } else { "bare" }
        }
        try { $requestedUri = [Uri]$RequestedEndpoint; $result.requested_endpoint_host = $requestedUri.Host; $result.requested_endpoint_path = $requestedUri.AbsolutePath } catch { }
        $result.requested_model = $RequestedModel
        if ($script:SetupLastProbeMethod) { $result.last_probe_method = $script:SetupLastProbeMethod }
        if ($script:SetupLastProbePath) { $result.last_probe_path = $script:SetupLastProbePath }
        if ($script:SetupLastProbeStatus) { $result.last_probe_status = $script:SetupLastProbeStatus }
        if ($script:SetupModelsProbeStatus) { $result.models_probe_status = $script:SetupModelsProbeStatus }
        if ($script:SetupResponsesProbeStatus) { $result.responses_probe_status = $script:SetupResponsesProbeStatus }
        if ($script:CodexRuntimeProbeStatus) { $result.codex_runtime_probe_status = $script:CodexRuntimeProbeStatus }
        if ($script:CodexRuntimeProbeExitCode) { $result.codex_runtime_probe_exit_code = $script:CodexRuntimeProbeExitCode }
    } catch { }
    return $result
}

function Get-CodexImageToolRoot {
    return Join-Path (Get-CodexHome) "aimarket-image-tool"
}

function Install-CodexImageTool {
    param([string]$OpenAIEndpoint)
    $root = Get-CodexImageToolRoot
    $serverPath = Join-Path $root "server.ps1"
    $skillPath = Join-Path (Get-CodexHome) "skills\aimarket-imagegen\SKILL.md"
    $otherRoot = Join-Path (Get-CodexHome) "relayfast-image-tool"
    $otherSkill = Join-Path (Get-CodexHome) "skills\relayfast-imagegen"
    $base = $OpenAIEndpoint.TrimEnd("/")
    $assetsBase = $base.Substring(0, $base.Length - 3).TrimEnd("/") + "/downloads/setup/codex-image-tool"
    $assets = @(
        [pscustomobject]@{ Name = "server.ps1"; Url = "$assetsBase/server.ps1"; Path = $serverPath; Sha256 = "7299C4CAF2B1BCF835771FD104E0BEC41B3B0D57C1F5F2807FED72D84A0E5F36" },
        [pscustomobject]@{ Name = "SKILL.md"; Url = "$assetsBase/SKILL.md"; Path = $skillPath; Sha256 = "5AA800BD3EFC637EC012B39E90839949F3DED6FA8844CB6798E905B5FF14950C" }
    )
    foreach ($asset in $assets) {
        if ($DryRun) { Ok "Would install Codex image component: $($asset.Path)"; continue }
        $temporary = Join-Path ([IO.Path]::GetTempPath()) ("aimarket-image-tool-" + [guid]::NewGuid().ToString("N"))
        try {
            $localAsset = Join-Path $PSScriptRoot "codex-image-tool\$($asset.Name)"
            if (Test-Path -LiteralPath $localAsset) {
                Copy-Item -LiteralPath $localAsset -Destination $temporary
            } else {
                Invoke-WebRequest -UseBasicParsing -Uri $asset.Url -OutFile $temporary -TimeoutSec 120
            }
            $actual = (Get-FileHash -LiteralPath $temporary -Algorithm SHA256).Hash.ToUpperInvariant()
            if ($actual -ne $asset.Sha256) { throw "Codex image component checksum mismatch for $($asset.Url)" }
            $directory = Split-Path -Parent $asset.Path
            New-Item -ItemType Directory -Path $directory -Force | Out-Null
            Move-Item -LiteralPath $temporary -Destination $asset.Path -Force
        } finally {
            if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
        }
    }
    if (-not $DryRun) {
        foreach ($managedPath in @($otherRoot, $otherSkill, (Join-Path (Get-CodexHome) "codexrodeo-image-tool"), (Join-Path (Get-CodexHome) "skills\codexrodeo-imagegen"))) {
            if (Test-Path -LiteralPath $managedPath) { Remove-Item -LiteralPath $managedPath -Recurse -Force }
        }
    }
    return $serverPath
}

function Remove-CodexImageTool {
    foreach ($managedPath in @((Get-CodexImageToolRoot), (Join-Path (Get-CodexHome) "skills\aimarket-imagegen"))) {
        if ($DryRun) { Ok "Would remove managed Codex image component: $managedPath" }
        elseif (Test-Path -LiteralPath $managedPath) { Remove-Item -LiteralPath $managedPath -Recurse -Force }
    }
}

# Codex session files and SQLite state are intentionally never rewritten when the
# active model provider changes. Codex owns provider-bound resume metadata.

function Update-CodexConfigText {
    param([string]$ExistingText, [string]$Provider, [string]$BaseUrl, [string]$EnvironmentKey, [string]$ModelName, [string]$ImageToolPath)
    $lines = @()
    if (-not [string]::IsNullOrEmpty($ExistingText)) {
        $normalized = $ExistingText -replace "`r`n", "`n" -replace "`r", "`n"
        $lines = @($normalized -split "`n", -1)
        if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -eq "") { $lines = $lines[0..($lines.Count - 2)] }
    }
    $firstTableForRoot = -1
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match "^\s*\[") { $firstTableForRoot = $i; break } }
    if ($firstTableForRoot -lt 0) { $firstTableForRoot = $lines.Count }
    $rootInline = if ($firstTableForRoot -gt 0) { @($lines[0..($firstTableForRoot - 1)] | Where-Object { $_ -match "^\s*model_providers\s*=" }) } else { @() }
    if (@($rootInline).Count -gt 0) {
        Write-WarnLine "Removed a legacy inline model_providers map from the generated Codex config; the original is kept in the timestamped backup."
        $rootPrefix = if ($firstTableForRoot -gt 0) { @($lines[0..($firstTableForRoot - 1)] | Where-Object { $_ -notmatch "^\s*model_providers\s*=" }) } else { @() }
        $tail = if ($firstTableForRoot -lt $lines.Count) { @($lines[$firstTableForRoot..($lines.Count - 1)]) } else { @() }
        $lines = @($rootPrefix + $tail)
    }
    foreach ($reservedProvider in @("openai", "ollama", "lmstudio")) {
        $lines = @(Remove-TomlTableTree -Lines $lines -TableName "model_providers.$reservedProvider")
    }
    $lines = @(Repair-CodexProviderTables -Lines $lines)
    $lines = @(Remove-TomlTableTree -Lines $lines -TableName "model_providers.$Provider")
    $lines = @(Remove-TomlTable -Lines $lines -TableName "mcp_servers.aimarket_image")
    $lines = @(Remove-TomlTable -Lines $lines -TableName "mcp_servers.routercheap_image")
    $lines = @(Remove-TomlTable -Lines $lines -TableName "mcp_servers.relayfast_image")
    $lines = @(Remove-TomlTable -Lines $lines -TableName "mcp_servers.codexrodeo_image")
    $firstTable = -1
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match "^\s*\[") { $firstTable = $i; break } }
    if ($firstTable -lt 0) { $root = $lines; $rest = @() }
    elseif ($firstTable -eq 0) { $root = @(); $rest = $lines }
    else { $root = $lines[0..($firstTable - 1)]; $rest = $lines[$firstTable..($lines.Count - 1)] }
    $root = @($root | Where-Object { $_ -notmatch "^\s*model\s*=" -and $_ -notmatch "^\s*model_provider\s*=" })
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($line in $root) { $out.Add($line) }
    if ($out.Count -gt 0 -and $out[$out.Count - 1].Trim() -ne "") { $out.Add("") }
    $out.Add("model = $(ConvertTo-TomlString $ModelName)")
    $out.Add("model_provider = $(ConvertTo-TomlString $Provider)")
    if ($rest.Count -gt 0) { $out.Add(""); foreach ($line in $rest) { $out.Add($line) } }
    if ($out.Count -gt 0 -and $out[$out.Count - 1].Trim() -ne "") { $out.Add("") }
    $out.Add("[model_providers.$Provider]")
    $out.Add('name = "aimarket"')
    $out.Add("base_url = $(ConvertTo-TomlString $BaseUrl)")
    $out.Add("env_key = $(ConvertTo-TomlString $EnvironmentKey)")
    $out.Add('requires_openai_auth = false')
    $out.Add('wire_api = "responses"')
    $out.Add("")
    $out.Add("[mcp_servers.aimarket_image]")
    $out.Add('command = "powershell"')
    $out.Add(('args = ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", {0}]' -f (ConvertTo-TomlString $ImageToolPath)))
    $out.Add(('env_vars = [{0}]' -f (ConvertTo-TomlString $EnvironmentKey)))
    $out.Add(('env = {{ CODEX_HOME = {0}, ROUTER_IMAGE_BASE_URL = {1}, ROUTER_IMAGE_API_KEY_ENV = {2}, ROUTER_IMAGE_MODEL = "gpt-image-2", ROUTER_IMAGE_BRAND = "aimarket" }}' -f (ConvertTo-TomlString (Get-CodexHome)), (ConvertTo-TomlString $BaseUrl), (ConvertTo-TomlString $EnvironmentKey)))
    $out.Add('startup_timeout_sec = 20')
    $out.Add('tool_timeout_sec = 900')
    $out.Add('enabled = true')
    $out.Add('required = false')
    $out.Add('default_tools_approval_mode = "approve"')
    return ($out.ToArray() -join "`r`n") + "`r`n"
}

function Restore-CodexConfigText {
    param([string]$ExistingText)
    $normalized = $ExistingText -replace "`r`n", "`n" -replace "`r", "`n"
    $lines = @($normalized -split "`n", -1)
    $lines = @(Remove-TomlTable -Lines $lines -TableName "model_providers.aimarket")
    $lines = @(Remove-TomlTable -Lines $lines -TableName "model_providers.routercheap")
    $lines = @(Remove-TomlTable -Lines $lines -TableName "mcp_servers.aimarket_image")
    $lines = @(Remove-TomlTable -Lines $lines -TableName "mcp_servers.routercheap_image")
    $firstTable = -1
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match "^\s*\[") { $firstTable = $i; break } }
    if ($firstTable -lt 0) { $root = $lines; $rest = @() }
    elseif ($firstTable -eq 0) { $root = @(); $rest = $lines }
    else { $root = $lines[0..($firstTable - 1)]; $rest = $lines[$firstTable..($lines.Count - 1)] }
    $root = @($root | Where-Object { $_ -notmatch "^\s*model_provider\s*=" })
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($line in $root) { $out.Add($line) }
    if ($out.Count -gt 0 -and $out[$out.Count - 1].Trim() -ne "") { $out.Add("") }
    $out.Add('model_provider = "openai"')
    if ($rest.Count -gt 0) { $out.Add(""); foreach ($line in $rest) { $out.Add($line) } }
    return ($out.ToArray() -join "`r`n").TrimEnd() + "`r`n"
}

function Setup-Codex {
    param([string]$Key, [string]$OpenAIEndpoint)
    Test-OpenAIKey -OpenAIEndpoint $OpenAIEndpoint -Key $Key -ModelName $Model -Responses
    Section (T "writing")
    Stop-CodexForSetup
    try {
        Set-SetupTelemetryStep "write_environment"
        if (-not $DryRun) {
            [Environment]::SetEnvironmentVariable("AIMARKET_API_KEY", $Key, "User")
            Set-Item Env:AIMARKET_API_KEY $Key
        } else {
            Ok "Would set AIMARKET_API_KEY for the current Windows user."
        }
        Set-SetupTelemetryStep "write_codex_config"
        $imageToolPath = Install-CodexImageTool $OpenAIEndpoint
        $path = Get-CodexConfigPath
        $existing = if (Test-Path -LiteralPath $path) { Get-Content -Raw -LiteralPath $path } else { "" }
        Backup-File $path
        Save-TextUtf8NoBom $path (Update-CodexConfigText $existing "aimarket" $OpenAIEndpoint "AIMARKET_API_KEY" $Model $imageToolPath)
        if ($DryRun) {
            Warn "DryRun: Codex configuration was not written; provider verification will run after a real setup."
        } else {
            Assert-CodexProviderConfiguration -ConfigPath $path -Provider "aimarket" -BaseUrl $OpenAIEndpoint -EnvironmentKey "AIMARKET_API_KEY" -ModelName $Model
        }
        Write-CodexAuthDiagnostics -Provider "aimarket" -EnvironmentKey "AIMARKET_API_KEY" -ConfigPath $path
        if (-not $DryRun) { Invoke-CodexRuntimeProbe -ModelName $Model }
        Warn (T "codexPickerHint" @{ model = $Model })
        Warn (T "codexHistoryNotice")
    } finally {
        Start-CodexAfterSetup
    }
}

function Restore-Codex {
    $path = Get-CodexConfigPath
    $existing = if (Test-Path -LiteralPath $path) { Get-Content -Raw -LiteralPath $path } else { "" }
    Stop-CodexForSetup
    try {
        Backup-File $path
        Save-TextUtf8NoBom $path (Restore-CodexConfigText $existing)
        Remove-CodexImageTool
        Warn (T "codexHistoryNotice")
    } finally {
        Start-CodexAfterSetup
    }
}

function Get-GrokExecutable {
    $command = Get-Command grok -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $command -and -not [string]::IsNullOrWhiteSpace($command.Source)) {
        return $command.Source
    }
    $official = Join-Path $env:USERPROFILE ".grok\bin\grok.exe"
    if (Test-Path -LiteralPath $official) { return $official }
    return ""
}

function Get-GrokHome {
    $homeDir = [Environment]::GetEnvironmentVariable("GROK_HOME", "Process")
    if ([string]::IsNullOrWhiteSpace($homeDir)) { $homeDir = [Environment]::GetEnvironmentVariable("GROK_HOME", "User") }
    if ([string]::IsNullOrWhiteSpace($homeDir)) { $homeDir = Join-Path $env:USERPROFILE ".grok" }
    return [IO.Path]::GetFullPath($homeDir)
}

function Update-GrokConfigText {
    param([string]$ExistingText, [string]$Alias, [string]$ModelName, [string]$BaseUrl, [string]$EnvironmentKey)
    $lines = @()
    if (-not [string]::IsNullOrEmpty($ExistingText)) {
        $normalized = $ExistingText -replace "`r`n", "`n" -replace "`r", "`n"
        $lines = @($normalized -split "`n", -1)
        if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -eq "") { $lines = $lines[0..($lines.Count - 2)] }
    }
    $lines = @(Remove-TomlTable -Lines $lines -TableName "model.$Alias")
    $lines = @(Remove-TomlTable -Lines $lines -TableName "model.routercheap-grok-4-5")
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($line in $lines) { $out.Add($line) }
    while ($out.Count -gt 0 -and [string]::IsNullOrWhiteSpace($out[$out.Count - 1])) { $out.RemoveAt($out.Count - 1) }
    if ($out.Count -gt 0) { $out.Add("") }
    $out.Add("[model.$Alias]")
    $out.Add("model = $(ConvertTo-TomlString $ModelName)")
    $out.Add("base_url = $(ConvertTo-TomlString $BaseUrl)")
    $out.Add('name = "Grok 4.5 via aimarket"')
    $out.Add('description = "Grok 4.5 through the aimarket OpenAI-compatible Responses API"')
    $out.Add("env_key = $(ConvertTo-TomlString $EnvironmentKey)")
    $out.Add('api_backend = "responses"')
    $out.Add('context_window = 500000')
    $out.Add('supports_reasoning_effort = true')
    $out.Add('reasoning_effort = "high"')
    $out.Add('stream_tool_calls = true')
    $out.Add('supports_backend_search = false')
    return ($out.ToArray() -join "`r`n") + "`r`n"
}

function Restore-GrokConfigText {
    param([string]$ExistingText, [string]$Alias)
    if ([string]::IsNullOrEmpty($ExistingText)) { return "" }
    $normalized = $ExistingText -replace "`r`n", "`n" -replace "`r", "`n"
    $lines = @($normalized -split "`n", -1)
    $lines = @(Remove-TomlTable -Lines $lines -TableName "model.$Alias")
    $lines = @(Remove-TomlTable -Lines $lines -TableName "model.routercheap-grok-4-5")
    return (($lines -join "`r`n").TrimEnd() + "`r`n")
}

function Test-GrokConfigText {
    param([string]$GrokExecutable, [string]$ConfigText, [string]$Key, [string]$EnvironmentKey)
    $validationHome = Join-Path ([IO.Path]::GetTempPath()) ("aimarket-grok-validate-" + [guid]::NewGuid().ToString("N"))
    $oldHome = [Environment]::GetEnvironmentVariable("GROK_HOME", "Process")
    $oldKey = [Environment]::GetEnvironmentVariable($EnvironmentKey, "Process")
    $oldUpdater = [Environment]::GetEnvironmentVariable("GROK_DISABLE_AUTOUPDATER", "Process")
    try {
        New-Item -ItemType Directory -Path $validationHome -Force | Out-Null
        [IO.File]::WriteAllText((Join-Path $validationHome "config.toml"), $ConfigText, [Text.UTF8Encoding]::new($false))
        [Environment]::SetEnvironmentVariable("GROK_HOME", $validationHome, "Process")
        [Environment]::SetEnvironmentVariable($EnvironmentKey, $Key, "Process")
        [Environment]::SetEnvironmentVariable("GROK_DISABLE_AUTOUPDATER", "1", "Process")
        $output = & $GrokExecutable inspect --json 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Grok rejected the generated config: $($output -join ' ')" }
        $json = ($output -join "`n") | ConvertFrom-Json
        if ($null -eq $json) { throw "Grok inspect returned invalid JSON." }
    } finally {
        [Environment]::SetEnvironmentVariable("GROK_HOME", $oldHome, "Process")
        [Environment]::SetEnvironmentVariable($EnvironmentKey, $oldKey, "Process")
        [Environment]::SetEnvironmentVariable("GROK_DISABLE_AUTOUPDATER", $oldUpdater, "Process")
        if (Test-Path -LiteralPath $validationHome) { Remove-Item -LiteralPath $validationHome -Recurse -Force }
    }
}

function Protect-GrokApiKey {
    param([string]$Key)
    Add-Type -AssemblyName System.Security
    $plain = [Text.UTF8Encoding]::new($false).GetBytes($Key)
    try {
        $protected = [Security.Cryptography.ProtectedData]::Protect($plain, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
        try { return [Convert]::ToBase64String($protected) }
        finally { [Array]::Clear($protected, 0, $protected.Length) }
    } finally {
        [Array]::Clear($plain, 0, $plain.Length)
    }
}

function Add-GrokLauncherPath {
    param([string]$Directory)
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    $parts = @($current -split ";" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($parts | Where-Object { $_.TrimEnd('\') -ieq $Directory.TrimEnd('\') }) { return }
    $updated = if ([string]::IsNullOrWhiteSpace($current)) { $Directory } else { "$Directory;$current" }
    [Environment]::SetEnvironmentVariable("Path", $updated, "User")
    if (-not (($env:Path -split ";") | Where-Object { $_.TrimEnd('\') -ieq $Directory.TrimEnd('\') })) {
        $env:Path = "$Directory;$env:Path"
    }
}

function Setup-GrokBuild {
    param([string]$Key, [string]$OpenAIEndpoint)
    $script:Model = $GrokModel
    Test-OpenAIKey -OpenAIEndpoint $OpenAIEndpoint -Key $Key -ModelName $GrokModel -Responses
    Section (T "writing")

    Set-SetupTelemetryStep "find_grok_cli"
    $grokExecutable = Get-GrokExecutable
    if ([string]::IsNullOrWhiteSpace($grokExecutable)) { throw (T "grokMissing") }
    $grokHome = Get-GrokHome
    $configPath = Join-Path $grokHome "config.toml"
    $credentialsPath = Join-Path $grokHome "credentials\aimarket-api-key.dpapi"
    $launcherDirectory = Join-Path $env:USERPROFILE ".grok\bin"
    $launcherPs1 = Join-Path $launcherDirectory "grok-aimarket.ps1"
    $launcherCmd = Join-Path $launcherDirectory "grok-aimarket.cmd"
    $alias = "aimarket-grok-4-5"
    $environmentKey = "AIMARKET_GROK_API_KEY"
    $existing = if (Test-Path -LiteralPath $configPath) { Get-Content -Raw -LiteralPath $configPath } else { "" }
    $newConfig = Update-GrokConfigText -ExistingText $existing -Alias $alias -ModelName $GrokModel -BaseUrl $OpenAIEndpoint -EnvironmentKey $environmentKey

    Set-SetupTelemetryStep "validate_grok_config"
    Test-GrokConfigText -GrokExecutable $grokExecutable -ConfigText $newConfig -Key $Key -EnvironmentKey $environmentKey
    Set-SetupTelemetryStep "write_grok_config"
    Backup-File $configPath

    if ($DryRun) {
        Ok "Would store the API key with Windows DPAPI for the current user: $credentialsPath"
        Ok "Would install secure launcher: $launcherCmd"
        Write-Host $newConfig
        return
    }

    $escapedHome = $grokHome.Replace("'", "''")
    $escapedCredential = $credentialsPath.Replace("'", "''")
    $escapedExecutable = $grokExecutable.Replace("'", "''")
    $launcherTemplate = @'
$ErrorActionPreference = "Stop"
$grokHome = '__GROK_HOME__'
$credentialPath = '__CREDENTIAL_PATH__'
$grokExecutable = '__GROK_EXECUTABLE__'
if (-not (Test-Path -LiteralPath $credentialPath)) { throw "aimarket Grok credential is missing. Run setup again." }
Add-Type -AssemblyName System.Security
$encrypted = [Convert]::FromBase64String((Get-Content -Raw -LiteralPath $credentialPath).Trim())
$plain = [Security.Cryptography.ProtectedData]::Unprotect($encrypted, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
$previousHome = [Environment]::GetEnvironmentVariable("GROK_HOME", "Process")
$previousKey = [Environment]::GetEnvironmentVariable("AIMARKET_GROK_API_KEY", "Process")
try {
    $env:GROK_HOME = $grokHome
    $env:AIMARKET_GROK_API_KEY = [Text.UTF8Encoding]::new($false).GetString($plain)
    & $grokExecutable -m aimarket-grok-4-5 @args
    exit $LASTEXITCODE
} finally {
    [Environment]::SetEnvironmentVariable("GROK_HOME", $previousHome, "Process")
    [Environment]::SetEnvironmentVariable("AIMARKET_GROK_API_KEY", $previousKey, "Process")
    [Array]::Clear($plain, 0, $plain.Length)
    [Array]::Clear($encrypted, 0, $encrypted.Length)
}
'@
    $launcherText = $launcherTemplate.Replace("__GROK_HOME__", $escapedHome).Replace("__CREDENTIAL_PATH__", $escapedCredential).Replace("__GROK_EXECUTABLE__", $escapedExecutable)
    $cmdText = "@echo off`r`npowershell.exe -NoProfile -ExecutionPolicy Bypass -File `"%~dp0grok-aimarket.ps1`" %*`r`nexit /b %ERRORLEVEL%`r`n"

    Save-TextUtf8NoBom $credentialsPath ((Protect-GrokApiKey $Key) + "`r`n")
    Save-TextUtf8NoBom $launcherPs1 ($launcherText.TrimStart() + "`r`n")
    Save-TextUtf8NoBom $launcherCmd $cmdText
    Save-TextUtf8NoBom $configPath $newConfig
    Add-GrokLauncherPath $launcherDirectory
    Ok "Grok config validated with 'grok inspect'."
    Ok (T "grokCommand")
}

function Restore-GrokBuild {
    $grokHome = Get-GrokHome
    $configPath = Join-Path $grokHome "config.toml"
    if (Test-Path -LiteralPath $configPath) {
        $existing = Get-Content -Raw -LiteralPath $configPath
        $restored = Restore-GrokConfigText -ExistingText $existing -Alias "aimarket-grok-4-5"
        Backup-File $configPath
        if ([string]::IsNullOrWhiteSpace($restored)) {
            if (-not $DryRun) { Remove-Item -LiteralPath $configPath -Force }
        } else {
            Save-TextUtf8NoBom $configPath $restored
        }
    }
    foreach ($path in @(
        (Join-Path $grokHome "credentials\aimarket-api-key.dpapi"),
        (Join-Path $env:USERPROFILE ".grok\bin\grok-aimarket.ps1"),
        (Join-Path $env:USERPROFILE ".grok\bin\grok-aimarket.cmd"),
        (Join-Path $env:USERPROFILE ".grok\bin\grok-routercheap.ps1"),
        (Join-Path $env:USERPROFILE ".grok\bin\grok-routercheap.cmd")
    )) {
        if (Test-Path -LiteralPath $path) {
            if ($DryRun) { Ok "Would remove: $path" } else { Remove-Item -LiteralPath $path -Force }
        }
    }
}

function Get-ClaudeSettingsPath { return Join-Path $env:USERPROFILE ".claude\settings.json" }
function Get-ClaudeCachePolicyStatePath { return Join-Path $env:USERPROFILE ".aimarket\claude-code-cache-policy.json" }

function Read-JsonObject {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) {
        $raw = Get-Content -Raw -Encoding UTF8 -LiteralPath $Path
        if (-not [string]::IsNullOrWhiteSpace($raw)) { return $raw | ConvertFrom-Json }
    }
    return [pscustomobject]@{}
}

function Ensure-PropertyObject {
    param($Object, [string]$Name)
    if (-not $Object.PSObject.Properties[$Name] -or $null -eq $Object.$Name) {
        $Object | Add-Member -NotePropertyName $Name -NotePropertyValue ([pscustomobject]@{}) -Force
    }
}

function Save-JsonObject {
    param([string]$Path, $Object)
    Save-TextUtf8NoBom $Path (($Object | ConvertTo-Json -Depth 20) + "`r`n")
}

function Test-ClaudeForkDenyManaged {
    $path = Get-ClaudeCachePolicyStatePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
    $state = Read-JsonObject $path
    return $state.PSObject.Properties["agent_fork_deny_added"] -and
           [bool]$state.agent_fork_deny_added
}

function Save-ClaudeForkDenyState {
    $state = [ordered]@{
        version = 1
        agent_fork_deny_added = $true
    }
    Save-JsonObject (Get-ClaudeCachePolicyStatePath) $state
}

function Remove-ClaudeForkDenyState {
    $path = Get-ClaudeCachePolicyStatePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return }
    if ($DryRun) {
        Ok "Would remove: $path"
    } else {
        Remove-Item -LiteralPath $path -Force
    }
}

function Add-ClaudeForkDenyRule {
    param($Settings)
    Ensure-PropertyObject $Settings "permissions"
    if ($Settings.permissions -isnot [pscustomobject] -and $Settings.permissions -isnot [hashtable]) {
        throw "Claude Code settings permissions must be a JSON object."
    }

    $deny = @()
    if ($Settings.permissions.PSObject.Properties["deny"] -and $null -ne $Settings.permissions.deny) {
        if ($Settings.permissions.deny -is [string] -or $Settings.permissions.deny -isnot [System.Collections.IEnumerable]) {
            throw "Claude Code settings permissions.deny must be a JSON array."
        }
        $deny = @($Settings.permissions.deny)
        foreach ($entry in $deny) {
            if ($entry -isnot [string]) { throw "Claude Code settings permissions.deny must contain only strings." }
            if ($entry -ceq "Agent(fork)") { return $false }
        }
    }

    $Settings.permissions | Add-Member -NotePropertyName "deny" -NotePropertyValue @($deny + "Agent(fork)") -Force
    return $true
}

function Remove-ClaudeForkDenyRule {
    param($Settings)
    if (-not $Settings.PSObject.Properties["permissions"] -or $null -eq $Settings.permissions -or
        -not $Settings.permissions.PSObject.Properties["deny"] -or $null -eq $Settings.permissions.deny) {
        return $false
    }

    $remaining = [System.Collections.Generic.List[object]]::new()
    $removed = $false
    foreach ($entry in @($Settings.permissions.deny)) {
        if (-not $removed -and $entry -is [string] -and $entry -ceq "Agent(fork)") {
            $removed = $true
            continue
        }
        $remaining.Add($entry)
    }
    if (-not $removed) { return $false }

    if ($remaining.Count -eq 0) {
        $Settings.permissions.PSObject.Properties.Remove("deny")
    } else {
        $Settings.permissions | Add-Member -NotePropertyName "deny" -NotePropertyValue @($remaining.ToArray()) -Force
    }
    if (@($Settings.permissions.PSObject.Properties).Count -eq 0) {
        $Settings.PSObject.Properties.Remove("permissions")
    }
    return $true
}

function Setup-ClaudeCode {
    param([string]$Key, [string]$Base)
    Section (T "writing")
    Set-SetupTelemetryStep "write_environment"
    if (-not $DryRun) {
        [Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", $Base, "User")
        [Environment]::SetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", $Key, "User")
        [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $null, "User")
        [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $null, "Process")
    } else {
        Ok "Would set ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN and remove conflicting ANTHROPIC_API_KEY for the current Windows user."
    }
    Set-SetupTelemetryStep "read_claude_settings"
    $path = Get-ClaudeSettingsPath
    $settings = Read-JsonObject $path
    Ensure-PropertyObject $settings "env"
    if ($settings.env.PSObject.Properties["ANTHROPIC_API_KEY"]) {
        $settings.env.PSObject.Properties.Remove("ANTHROPIC_API_KEY")
    }
    $settings.env | Add-Member -NotePropertyName "ANTHROPIC_BASE_URL" -NotePropertyValue $Base -Force
    $settings.env | Add-Member -NotePropertyName "ANTHROPIC_AUTH_TOKEN" -NotePropertyValue $Key -Force
    $settings.env | Add-Member -NotePropertyName "ANTHROPIC_MODEL" -NotePropertyValue $ClaudeModel -Force
    $forkDenyManaged = Test-ClaudeForkDenyManaged
    if ((Add-ClaudeForkDenyRule $settings) -or $forkDenyManaged) {
        Save-ClaudeForkDenyState
    }
    Set-SetupTelemetryStep "write_claude_settings"
    Backup-File $path
    Save-JsonObject $path $settings
    Ok (T "claudeCachePolicyConfigured")
    Warn (T "claudeLoginPreserved")
}

function Restore-ClaudeCode {
    if (-not $DryRun) {
        [Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", $null, "User")
        [Environment]::SetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", $null, "User")
    } else {
        Ok "Would remove ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN from the current Windows user."
    }
    $path = Get-ClaudeSettingsPath
    $settings = Read-JsonObject $path
    $forkDenyManaged = Test-ClaudeForkDenyManaged
    $settingsChanged = $false
    if ($settings.PSObject.Properties["env"] -and $settings.env) {
        foreach ($name in @("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL")) {
            if ($settings.env.PSObject.Properties[$name]) {
                $settings.env.PSObject.Properties.Remove($name)
                $settingsChanged = $true
            }
        }
    }
    if ($forkDenyManaged -and (Remove-ClaudeForkDenyRule $settings)) {
        $settingsChanged = $true
    }
    if ($settingsChanged) {
        Backup-File $path
        Save-JsonObject $path $settings
    }
    if ($forkDenyManaged) {
        Remove-ClaudeForkDenyState
        Ok (T "claudeCachePolicyRestored")
    }
    Warn (T "claudeLoginRestore")
}

function Get-OpenCodeRouterConfigPath {
    return Join-Path $env:USERPROFILE ".config\opencode\aimarket.json"
}

function Get-DroidConfigPath {
    return Join-Path $env:USERPROFILE ".factory\settings.json"
}

function Get-DroidDisplayName {
    param([string]$ModelName)
    $normalized = $ModelName.Trim().ToLowerInvariant()
    switch ($normalized) {
        "gpt-6-astra" { return "aimarket GPT-6 Astra" }
        "gpt-5.6-sol" { return "aimarket GPT 5.6 Sol" }
        "gpt-5.6-terra" { return "aimarket GPT 5.6 Terra" }
        "gpt-5.6-luna" { return "aimarket GPT 5.6 Luna" }
        "gpt-5.5" { return "aimarket GPT 5.5" }
        default { return "aimarket $ModelName" }
    }
}

function Update-DroidSettings {
    param([string]$Path, [string]$OpenAIEndpoint, [string]$ModelName)
    $settings = Read-JsonObject $Path
    if ($null -eq $settings -or $settings -is [array] -or $settings -is [string]) {
        throw "Factory Droid settings root must be a JSON object."
    }

    $existingModels = @()
    if ($settings.PSObject.Properties["customModels"] -and $null -ne $settings.customModels) {
        if ($settings.customModels -isnot [array]) {
            throw "Factory Droid settings customModels must be a JSON array."
        }
        $existingModels = @($settings.customModels)
    }

    $managed = [pscustomobject][ordered]@{
        model = $ModelName
        displayName = Get-DroidDisplayName $ModelName
        baseUrl = $OpenAIEndpoint
        apiKey = '${AIMARKET_API_KEY}'
        provider = "generic-chat-completion-api"
        maxOutputTokens = 16384
    }
    $managedHosts = @("router.cheap", "direct.router-cheap.com")
    $updated = New-Object System.Collections.Generic.List[object]
    $found = $false
    foreach ($item in $existingModels) {
        if ($null -eq $item -or $item -is [array] -or $item -is [string]) {
            throw "Factory Droid settings customModels must contain JSON objects."
        }
        $itemModel = if ($item.PSObject.Properties["model"] -and $null -ne $item.model) { [string]$item.model } else { "" }
        $itemBaseUrl = if ($item.PSObject.Properties["baseUrl"] -and $null -ne $item.baseUrl) { [string]$item.baseUrl } else { "" }
        $itemProvider = if ($item.PSObject.Properties["provider"] -and $null -ne $item.provider) { [string]$item.provider } else { "" }
        $itemApiKey = if ($item.PSObject.Properties["apiKey"] -and $null -ne $item.apiKey) { [string]$item.apiKey } else { "" }
        $itemHost = ""
        try { $itemHost = ([Uri]$itemBaseUrl).Host.ToLowerInvariant() } catch { }
        $isManagedRouterModel = $itemProvider -eq "generic-chat-completion-api" -and
            $itemApiKey -eq '${AIMARKET_API_KEY}' -and
            ($managedHosts -contains $itemHost -or [string]::Equals($itemBaseUrl.TrimEnd('/'), $OpenAIEndpoint.TrimEnd('/'), [StringComparison]::OrdinalIgnoreCase))
        if ([string]::Equals($itemModel.Trim(), $ModelName.Trim(), [StringComparison]::Ordinal) -or $isManagedRouterModel) {
            if (-not $found) {
                $updated.Add($managed)
                $found = $true
            }
            continue
        }
        $updated.Add($item)
    }
    if (-not $found) { $updated.Add($managed) }
    $settings | Add-Member -NotePropertyName "customModels" -NotePropertyValue @($updated.ToArray()) -Force
    return $settings
}

function Setup-Droid {
    param([string]$Key, [string]$OpenAIEndpoint)
    Test-OpenAIKey -OpenAIEndpoint $OpenAIEndpoint -Key $Key -ModelName $Model
    Section (T "writing")
    Set-SetupTelemetryStep "write_environment"
    if (-not $DryRun) {
        [Environment]::SetEnvironmentVariable("AIMARKET_API_KEY", $Key, "User")
        Set-Item Env:AIMARKET_API_KEY $Key
    } else {
        Ok "Would set AIMARKET_API_KEY for the current Windows user."
    }
    Set-SetupTelemetryStep "write_droid_config"
    $path = Get-DroidConfigPath
    $settings = Update-DroidSettings -Path $path -OpenAIEndpoint $OpenAIEndpoint -ModelName $Model
    Backup-File $path
    Save-JsonObject $path $settings
    if ($DryRun) {
        Ok "DryRun: Factory Droid settings were not written."
    }
    Ok (T "droidConfigured")
    Warn (T "droidConfigHint")
}

function Get-OpenCodeModelsMap {
    $map = [ordered]@{}
    foreach ($name in @(Get-AvailableChatModels)) {
        $map[$name] = Get-OpenCodeModelConfig $name
    }
    if ($map.Count -eq 0) {
        $map[$script:Model] = Get-OpenCodeModelConfig $script:Model
    }
    return $map
}

function Get-OpenCodeEffortVariants {
    param([string[]]$Efforts, [string]$OptionName)
    $variants = [ordered]@{}
    foreach ($effort in $Efforts) {
        $variants[$effort] = [ordered]@{ $OptionName = $effort }
    }
    return $variants
}

function Get-OpenCodeReasoningProfile {
    param([string]$Name)
    $lower = $Name.Trim().ToLowerInvariant()
    if ($lower -match '^kimi-k3(?:$|[-_.:])') {
        return [ordered]@{
            default = "max"
            efforts = @("low", "high", "max")
        }
    }
    if ($lower -match '^deepseek-v[4-9](?:$|[-_.:])' -or $lower -match '^deepseek-reasoner(?:$|[-_.:])') {
        return [ordered]@{
            default = "medium"
            efforts = @("low", "medium", "high", "xhigh")
        }
    }
    if ($lower -match '^(?:glm|gemini|gemma|learnlm)(?:[-_.:]|$)') {
        return [ordered]@{
            default = "medium"
            efforts = @("low", "medium", "high")
        }
    }
    return $null
}

function Get-ManagedModelContextLength {
    param([string]$Name)
    $lower = $Name.Trim().ToLowerInvariant()
    if ($lower -match '^gpt-5\.(?:4|5)(?:$|[-_.:])') { return 272000 }
	if ($lower -match '^gpt-5\.6(?:$|[-_.:])') { return 372000 }
	if ($lower -match '^gpt-6-astra(?:$|[-_.:])') { return 1050000 }
    if ($lower -match '^claude-haiku-4-5(?:$|[-_.:])') { return 200000 }
    if ($lower -match '^claude-(?:sonnet-5|sonnet-4-6|opus-4-6|opus-4-7|opus-4-8|opus-5|fable-5|mythos-5)(?:$|[-_.:])') { return 1000000 }
    if ($lower -match '^grok-4\.(?:5|6|7)(?:$|[-_.:])') { return 500000 }
    if ($lower -match '^kimi-k3(?:$|[-_.:])') { return 1048576 }
    if ($lower -match '^kimi-k2\.(?:6|7)(?:$|[-_.:])') { return 256000 }
    if ($lower -match '^gemini-3\.(?:1-pro-preview|5-flash|6-flash|7-flash)(?:$|[-_.:])') { return 1048576 }
    if ($lower -match '^deepseek-v4-(?:flash|pro)(?:$|[-_.:])' -or $lower -match '^deepseek-v4\.1-flash(?:$|[-_.:])') { return 1000000 }
    if ($lower -match '^glm-5\.1(?:$|[-_.:])') { return 200000 }
    if ($lower -match '^glm-5\.(?:2|3)(?:$|[-_.:])') { return 1000000 }
    if ($lower -match '^(?:hy3|hy4)(?:$|[-_.:])') { return 256000 }
    if ($lower -match '^mimo-v2\.5(?:$|[-_.:])') { return 1000000 }
    if ($lower -match '^minimax-m3(?:$|[-_.:])') { return 1000000 }
    return 0
}

function Get-OpenCodeModelConfig {
    param([string]$Name)
    $config = [ordered]@{ name = $Name }
    $lower = $Name.ToLowerInvariant()
    $contextLength = Get-ManagedModelContextLength $Name
    if ($contextLength -gt 0) {
        # OpenCode currently caps generated output at 32K even when a model
        # advertises more, so 128K here reserves its full runtime allowance
        # without changing the product's operational context window.
        $config.limit = [ordered]@{ context = $contextLength; output = 128000 }
    }
    if (Test-ModelSupportsImageInput $Name) {
        # OpenCode uses modalities (not the legacy attachment flag) for its
        # client-side capability gate. Without it, image parts are discarded
        # before an OpenAI-compatible request is built.
        $config.attachment = $true
        $config.modalities = [ordered]@{ input = @("text", "image"); output = @("text") }
    }

    if ($lower.StartsWith("claude-")) {
        $config.provider = [ordered]@{ npm = "@ai-sdk/anthropic" }
        $config.tool_call = $true

        if ($lower.StartsWith("claude-sonnet-5") -or $lower.StartsWith("claude-opus-5") -or
            $lower.StartsWith("claude-fable-5") -or $lower.StartsWith("claude-mythos-5")) {
            $config.reasoning = $true
            $config.interleaved = $true
            $config.options = [ordered]@{ effort = "high" }
            $config.variants = Get-OpenCodeEffortVariants @("low", "medium", "high", "xhigh", "max") "effort"
        } elseif ($lower.StartsWith("claude-opus-4-8") -or $lower.StartsWith("claude-opus-4-7")) {
            $config.reasoning = $true
            $config.interleaved = $true
            $config.options = [ordered]@{ thinking = [ordered]@{ type = "adaptive" }; effort = "high" }
            $config.variants = Get-OpenCodeEffortVariants @("low", "medium", "high", "xhigh", "max") "effort"
        } elseif ($lower.StartsWith("claude-opus-4-6") -or $lower.StartsWith("claude-sonnet-4-6")) {
            $config.reasoning = $true
            $config.interleaved = $true
            $config.options = [ordered]@{ thinking = [ordered]@{ type = "adaptive" }; effort = "high" }
            $config.variants = Get-OpenCodeEffortVariants @("low", "medium", "high", "max") "effort"
        } elseif ($lower.StartsWith("claude-opus-4-5")) {
            $config.options = [ordered]@{ effort = "high" }
            $config.variants = Get-OpenCodeEffortVariants @("low", "medium", "high") "effort"
        }
        return $config
    }

    if ($lower -match '^grok-4\.5(?:$|[-_.:])') {
        $config.reasoning = $true
        $config.tool_call = $true
        $config.temperature = $false
        $config.options = [ordered]@{ reasoningEffort = "high" }
        $config.variants = Get-OpenCodeEffortVariants @("low", "medium", "high") "reasoningEffort"
        return $config
    }

    if ($lower -match '^grok-4\.6(?:$|[-_.:])') {
        $config.reasoning = $true
        $config.tool_call = $true
        $config.temperature = $false
        $config.options = [ordered]@{ reasoningEffort = "high" }
        $config.variants = Get-OpenCodeEffortVariants @("low", "medium", "high", "xhigh") "reasoningEffort"
        return $config
    }

    if ($lower -match '^grok-4\.7(?:$|[-_.:])') {
        $config.reasoning = $true
        $config.tool_call = $true
        $config.temperature = $false
        $config.options = [ordered]@{ reasoningEffort = "high" }
        $config.variants = Get-OpenCodeEffortVariants @("low", "medium", "high", "xhigh") "reasoningEffort"
        return $config
    }

    if ($lower -match '^kimi-k2\.6(?:$|[-_.:])') {
        $config.reasoning = $true
        $config.tool_call = $true
        $config.temperature = $false
        $config.options = [ordered]@{ thinking = [ordered]@{ type = "enabled" } }
        $config.variants = [ordered]@{
            enabled = [ordered]@{ thinking = [ordered]@{ type = "enabled" } }
            disabled = [ordered]@{ thinking = [ordered]@{ type = "disabled" } }
        }
        return $config
    }

    if ($lower -match '^kimi-k2\.7(?:-code)?(?:$|[-_.:])') {
        $config.reasoning = $true
        $config.tool_call = $true
        $config.temperature = $false
        $config.options = [ordered]@{ thinking = [ordered]@{ type = "enabled"; keep = "all" } }
        return $config
    }

    if ($lower -match '^minimax-m3(?:$|[-_.:])') {
        $config.reasoning = $true
        $config.tool_call = $true
        $config.temperature = $false
        $config.options = [ordered]@{ thinking = [ordered]@{ type = "adaptive" } }
        $config.variants = [ordered]@{
            adaptive = [ordered]@{ thinking = [ordered]@{ type = "adaptive" } }
            disabled = [ordered]@{ thinking = [ordered]@{ type = "disabled" } }
        }
        return $config
    }

    $reasoningProfile = Get-OpenCodeReasoningProfile $Name
    if ($null -ne $reasoningProfile) {
        $config.reasoning = $true
        $config.tool_call = $true
        $config.temperature = $false
        $config.options = [ordered]@{ reasoningEffort = $reasoningProfile.default }
        $config.variants = Get-OpenCodeEffortVariants $reasoningProfile.efforts "reasoningEffort"
        return $config
    }

	if ($lower.StartsWith("gpt-5") -or $lower.StartsWith("gpt-6-astra") -or $lower -match '^o[1-9](?:-|$)') {
        $config.provider = [ordered]@{ npm = "@ai-sdk/openai" }
        $config.tool_call = $true
    }
	if ($lower.StartsWith("gpt-5.6") -or $lower.StartsWith("gpt-6-astra")) {
        $config.reasoning = $true
        $config.temperature = $false
        $config.options = [ordered]@{
            reasoningEffort = "medium"
            reasoningSummary = "auto"
            include = @("reasoning.encrypted_content")
        }
        $config.variants = Get-OpenCodeEffortVariants @("none", "low", "medium", "high", "xhigh", "max") "reasoningEffort"
    } elseif ($lower.StartsWith("gpt-5.5") -or $lower.StartsWith("gpt-5.4")) {
        $config.reasoning = $true
        $config.temperature = $false
        $config.options = [ordered]@{
            reasoningEffort = "medium"
            reasoningSummary = "auto"
            include = @("reasoning.encrypted_content")
        }
        $config.variants = Get-OpenCodeEffortVariants @("none", "low", "medium", "high", "xhigh") "reasoningEffort"
    }
    return $config
}

function Merge-OpenCodeConfig {
    param([string]$Path, [string]$OpenAIEndpoint)
    $obj = Read-JsonObject $Path
    Ensure-PropertyObject $obj "provider"
    $managedProvider = [pscustomobject]@{
        npm = "@ai-sdk/openai-compatible"
        name = "aimarket"
        options = [pscustomobject]@{
            baseURL = $OpenAIEndpoint
            apiKey = "{env:AIMARKET_OPENCODE_API_KEY}"
        }
        models = [pscustomobject](Get-OpenCodeModelsMap)
    }
    $obj.provider | Add-Member -NotePropertyName "aimarket" -NotePropertyValue $managedProvider -Force
    $obj | Add-Member -NotePropertyName '$schema' -NotePropertyValue "https://opencode.ai/config.json" -Force

    $currentModel = if ($obj.PSObject.Properties["model"]) { [string]$obj.model } else { "" }
    if ([string]::IsNullOrWhiteSpace($currentModel) -or $currentModel.StartsWith("aimarket/", [StringComparison]::OrdinalIgnoreCase)) {
        $obj | Add-Member -NotePropertyName "model" -NotePropertyValue "aimarket/$Model" -Force
    }

    if ($obj.PSObject.Properties["enabled_providers"] -and $null -ne $obj.enabled_providers) {
        $providers = @($obj.enabled_providers | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        if ($providers.Count -eq 1 -and $providers[0] -eq "aimarket") {
            $obj.PSObject.Properties.Remove("enabled_providers")
        } else {
            if ($providers -notcontains "aimarket") { $providers += "aimarket" }
            $obj.enabled_providers = @($providers | Select-Object -Unique)
        }
    }
    return $obj
}

function Setup-OpenCode {
    param([string]$Key, [string]$OpenAIEndpoint)
    Test-CodingAgentKey -Key $Key -OpenAIEndpoint $OpenAIEndpoint
    Section (T "writing")
    Set-SetupTelemetryStep "write_environment"
    $path = Get-OpenCodeRouterConfigPath
    if (-not $DryRun) {
        $oldManagedKey = [Environment]::GetEnvironmentVariable("AIMARKET_OPENCODE_API_KEY", "User")
        if (-not [string]::IsNullOrWhiteSpace($oldManagedKey) -and
            [Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User") -eq $oldManagedKey) {
            [Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $null, "User")
        }
        [Environment]::SetEnvironmentVariable("AIMARKET_OPENCODE_API_KEY", $Key, "User")
        [Environment]::SetEnvironmentVariable("OPENCODE_CONFIG", $path, "User")
    } else {
        Ok "Would set AIMARKET_OPENCODE_API_KEY and OPENCODE_CONFIG for the current Windows user."
    }
    Set-SetupTelemetryStep "write_opencode_config"
    $obj = Merge-OpenCodeConfig -Path $path -OpenAIEndpoint $OpenAIEndpoint
    Backup-File $path
    Save-JsonObject $path $obj
}

function Restore-OpenCode {
    $path = Get-OpenCodeRouterConfigPath
    $markedKey = [Environment]::GetEnvironmentVariable("AIMARKET_OPENCODE_API_KEY", "User")
    if (([Environment]::GetEnvironmentVariable("OPENCODE_CONFIG", "User") -eq $path) -and -not $DryRun) {
        [Environment]::SetEnvironmentVariable("OPENCODE_CONFIG", $null, "User")
    } elseif ($DryRun) {
        Ok "Would remove OPENCODE_CONFIG if it points to aimarket.json."
    }
    if (-not $DryRun) {
        if (-not [string]::IsNullOrWhiteSpace($markedKey) -and [Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User") -eq $markedKey) {
            [Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $null, "User")
        }
        [Environment]::SetEnvironmentVariable("AIMARKET_OPENCODE_API_KEY", $null, "User")
    } else {
        Ok "Would remove OPENAI_API_KEY only if it matches the aimarket key saved by this script."
    }
    if (Test-Path -LiteralPath $path) {
        Backup-File $path
        if (-not $DryRun) { Remove-Item -LiteralPath $path -Force }
    }
}

function Remove-MarkedBlock {
    param([string]$Text, [string]$Begin, [string]$End)
    $pattern = "(?ms)^$([regex]::Escape($Begin)).*?^$([regex]::Escape($End))\r?\n?"
    return [regex]::Replace($Text, $pattern, "")
}

function Get-HermesApiMode {
    param([string]$ModelName)
    $normalized = $ModelName.Trim().ToLowerInvariant()
    if ($normalized.StartsWith("claude-")) { return "anthropic_messages" }
    if ($normalized.StartsWith("gpt-")) { return "codex_responses" }
    return "chat_completions"
}

function Get-HermesManagedProviderName {
    param([string]$ModelName)
    $normalized = $ModelName.Trim().ToLowerInvariant()
    if ($normalized.StartsWith("claude-")) { return "aimarket-anthropic" }
    if ($normalized.StartsWith("gpt-") -or $normalized -match '^o[1-9](?:-|$)') { return "aimarket" }
    return "aimarket-compatible"
}

function Get-HermesPythonCandidates {
    param([object]$HermesCommand)
    if ($null -eq $HermesCommand -or [string]::IsNullOrWhiteSpace($HermesCommand.Source)) { return @() }

    $bin = Split-Path -Parent $HermesCommand.Source
    $roots = New-Object System.Collections.Generic.List[string]
    # Current Windows installers expose only launchers in HERMES_HOME/bin.
    # Their interpreter remains inside the sibling hermes-agent checkout.
    if ((Split-Path -Leaf $bin) -eq "bin") {
        $roots.Add((Join-Path (Split-Path -Parent $bin) "hermes-agent"))
    }
    $current = $bin
    for ($i = 0; $i -lt 3 -and -not [string]::IsNullOrWhiteSpace($current); $i++) {
        if (-not ($roots -contains $current)) { $roots.Add($current) }
        $parent = Split-Path -Parent $current
        if ([string]::Equals($parent, $current, [StringComparison]::OrdinalIgnoreCase)) { break }
        $current = $parent
    }

    $candidates = New-Object System.Collections.Generic.List[string]
    foreach ($root in $roots) {
        foreach ($relative in @(
            "python.exe", "python3.exe", "python", "python3", "python.cmd",
            "Scripts\python.exe", "bin\python.exe",
            "venv\Scripts\python.exe", "venv\Scripts\python.cmd", "venv\bin\python3",
            ".venv\Scripts\python.exe", ".venv\Scripts\python.cmd", ".venv\bin\python3",
            "env\Scripts\python.exe", "env\bin\python3",
            "python\python.exe", "python\bin\python3"
        )) {
            $candidate = Join-Path $root $relative
            if (-not ($candidates -contains $candidate)) { $candidates.Add($candidate) }
        }
    }
    return @($candidates)
}

function Get-HermesPythonPath {
    param([object]$HermesCommand)
    foreach ($candidate in @(Get-HermesPythonCandidates $HermesCommand)) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    return ""
}

function Get-HermesRunAgentPath {
    param([object]$HermesCommand)
    $python = Get-HermesPythonPath $HermesCommand
    if ([string]::IsNullOrWhiteSpace($python)) {
        throw "Hermes' Python runtime was not found for $($HermesCommand.Source). Checked the launcher directory and adjacent virtual-environment layouts."
    }
    $probe = "import importlib.util; spec = importlib.util.find_spec('run_agent'); print(spec.origin if spec and spec.origin else '')"
    $output = @(& $python -c $probe 2>$null)
    if ($LASTEXITCODE -ne 0) { throw "Hermes' run_agent module could not be located." }
    $lines = @($output | ForEach-Object { ([string]$_).Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($lines.Count -eq 0) { throw "Hermes' run_agent module could not be located." }
    $path = Convert-HermesPathForHost ([string]$lines[-1])
    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or [IO.Path]::GetFileName($path) -ne "run_agent.py") {
        throw "Hermes returned an unexpected run_agent module path."
    }
    return [IO.Path]::GetFullPath($path)
}

function Assert-HermesSetupRuntime {
    param([object]$HermesCommand)
    [void](Get-HermesRunAgentPath $HermesCommand)
    $python = Get-HermesPythonPath $HermesCommand
    $probe = "from hermes_cli.config import fast_safe_load; from utils import atomic_yaml_write"
    & $python -c $probe 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Hermes' Python runtime is missing the configuration helpers. Repair/update Hermes and rerun setup; configuration files were not changed."
    }
}

function Get-HermesTuiGatewayServerPath {
    param([object]$HermesCommand)
    $runAgentPath = Get-HermesRunAgentPath $HermesCommand
    $path = Join-Path (Split-Path -Parent $runAgentPath) "tui_gateway\server.py"
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Hermes' tui_gateway.server module could not be located next to run_agent.py."
    }
    return [IO.Path]::GetFullPath($path)
}

function Update-HermesReasoningSessionFix {
    param(
        [object]$HermesCommand,
        [switch]$Restore
    )

    $path = Get-HermesTuiGatewayServerPath $HermesCommand
    $text = Get-Content -Raw -Encoding UTF8 -LiteralPath $path
    $begin = "            # aimarket Hermes session reasoning fix begin"
    $end = "            # aimarket Hermes session reasoning fix end"
    $withoutManagedBlock = Remove-MarkedBlock $text $begin $end
    $newline = if ($text.Contains("`r`n")) { "`r`n" } else { "`n" }
    $agentLine = '            if session and session.get("agent") is not None:'
    $legacyLine = '            _write_config_key("agent.reasoning_effort", arg)'

    if ($Restore) {
        if ($withoutManagedBlock -ceq $text) { return }
        $agentIndex = $withoutManagedBlock.IndexOf($agentLine, [StringComparison]::Ordinal)
        if ($agentIndex -lt 0) {
            throw "The managed Hermes session reasoning fix could not be restored safely."
        }
        $candidate = $withoutManagedBlock.Insert($agentIndex, $legacyLine + $newline)
    } else {
        if ($withoutManagedBlock -cne $text) {
            Ok (T "hermesReasoningSessionCurrent")
            return
        }
        if ($text.Contains('session["create_reasoning_override"] = parsed')) {
            Ok (T "hermesReasoningSessionCurrent")
            return
        }

        $legacy = $legacyLine + $newline + $agentLine
        $legacyIndex = $text.IndexOf($legacy, [StringComparison]::Ordinal)
        if ($legacyIndex -lt 0) {
            throw "This Hermes version has an unsupported Desktop reasoning layout. Update Hermes and run setup again."
        }
        $block = @(
            $begin
            '            scope = str(params.get("scope") or "").strip().lower()'
            '            if scope == "global" or session is None:'
            '                _write_config_key("agent.reasoning_effort", arg)'
            '                if session is not None:'
            '                    session.pop("create_reasoning_override", None)'
            '            else:'
            '                session["create_reasoning_override"] = parsed'
            $end
        ) -join $newline
        $candidate = $text.Remove($legacyIndex, $legacy.Length).Insert($legacyIndex, $block + $newline + $agentLine)
    }

    $python = Get-HermesPythonPath $HermesCommand
    $temporary = Join-Path (Split-Path -Parent $path) (".server.aimarket-validate-" + [guid]::NewGuid().ToString("N") + ".py")
    try {
        Save-TextUtf8NoBom $temporary $candidate
        $compileProbe = "import pathlib, sys; compile(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'), sys.argv[1], 'exec')"
        & $python -c $compileProbe $temporary | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "The Hermes Desktop session reasoning fix did not pass Python syntax validation." }
        Backup-File $path
        Save-TextUtf8NoBom $path $candidate
    } finally {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }

    if (-not $Restore) { Ok (T "hermesReasoningSessionFixed") }
}

function Update-HermesWindowsTransportFix {
    param(
        [object]$HermesCommand,
        [switch]$Restore
    )
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { return }

    $path = Get-HermesRunAgentPath $HermesCommand
    $text = Get-Content -Raw -Encoding UTF8 -LiteralPath $path
    $begin = "        # aimarket Windows transport fix begin"
    $end = "        # aimarket Windows transport fix end"
    $withoutManagedBlock = Remove-MarkedBlock $text $begin $end

    if ($Restore) {
        if ($withoutManagedBlock -ceq $text) { return }
        $candidate = $withoutManagedBlock
    } else {
        if ($withoutManagedBlock -cne $text) {
            Ok (T "hermesTransportCurrent")
            return
        }

        $functionMatch = [regex]::Match(
            $text,
            '(?m)^    def _build_keepalive_http_client\(base_url: str = ""[^\r\n]*\) -> Any:\r?$'
        )
        if (-not $functionMatch.Success) {
            throw "This Hermes version has an unsupported HTTP transport layout. Update Hermes and run setup again."
        }
        $afterSignature = $functionMatch.Index + $functionMatch.Length
        $nextFunction = [regex]::Match($text.Substring($afterSignature), '(?m)^    def ')
        $functionEnd = if ($nextFunction.Success) { $afterSignature + $nextFunction.Index } else { $text.Length }
        $functionText = $text.Substring($functionMatch.Index, $functionEnd - $functionMatch.Index)
        $tryMatch = [regex]::Match($functionText, '(?m)^        try:\r?$')
        if (-not $tryMatch.Success) {
            throw "This Hermes version has an unsupported HTTP transport layout. Update Hermes and run setup again."
        }

        $newline = if ($text.Contains("`r`n")) { "`r`n" } else { "`n" }
        $block = @(
            $begin
            "        # Hermes can abort native Windows SSE requests when it injects a custom"
            "        # httpx transport. Let the OpenAI SDK use its default for aimarket."
            '        if os.name == "nt" and base_url_host_matches(str(base_url or ""), "router.cheap"):'
            "            return None"
            $end
        ) -join $newline
        $insertAt = $functionMatch.Index + $tryMatch.Index
        $candidate = $text.Insert($insertAt, $block + $newline)
    }

    $python = Get-HermesPythonPath $HermesCommand
    $temporary = Join-Path (Split-Path -Parent $path) (".run_agent.aimarket-validate-" + [guid]::NewGuid().ToString("N") + ".py")
    try {
        Save-TextUtf8NoBom $temporary $candidate
        $compileProbe = "import pathlib, sys; compile(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'), sys.argv[1], 'exec')"
        & $python -c $compileProbe $temporary | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "The Hermes Windows transport fix did not pass Python syntax validation." }
        Backup-File $path
        Save-TextUtf8NoBom $path $candidate
    } finally {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }

    if (-not $Restore) { Ok (T "hermesTransportFixed") }
}

function Stop-HermesRuntimeTestProcess {
    param([Diagnostics.Process]$Process)
    if ($null -eq $Process -or $Process.HasExited) { return }

    try {
        $taskKill = Join-Path $env:SystemRoot "System32\taskkill.exe"
        if (Test-Path -LiteralPath $taskKill -PathType Leaf) {
            & $taskKill "/PID" ([string]$Process.Id) "/T" "/F" 2>$null | Out-Null
        }
    } catch { }
    if (-not $Process.HasExited) {
        try { $Process.Kill() } catch { }
    }
    try { [void]$Process.WaitForExit(5000) } catch { }
}

function Test-HermesRuntime {
    param([object]$HermesCommand)
    if ($SkipEndpointTest -or $DryRun -or [Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { return }

    Section (T "hermesRuntimeTesting")
    Set-SetupTelemetryStep "test_hermes_runtime"
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $HermesCommand.Source
    $start.Arguments = 'chat -q "Reply with exactly: OK" -Q --max-turns 1 --ignore-rules --source setup'
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    # Hermes prints the one-shot response before its shutdown cleanup runs.
    # Keep the pipes unbuffered so a stuck cleanup cannot hide a valid answer.
    $start.EnvironmentVariables["PYTHONUNBUFFERED"] = "1"
    $start.EnvironmentVariables["HERMES_EXIT_WATCHDOG_S"] = "2"
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    $responseSeen = $false
    $timedOut = $false
    try {
        if (-not $process.Start()) { throw "Hermes could not be started for its connection test." }

        $stdoutTask = $process.StandardOutput.ReadLineAsync()
        $stderrTask = $process.StandardError.ReadLineAsync()
        $deadline = [DateTime]::UtcNow.AddSeconds(90)
        while ($true) {
            $activity = $false
            if ($null -ne $stdoutTask -and $stdoutTask.IsCompleted) {
                $line = $stdoutTask.GetAwaiter().GetResult()
                if ($null -eq $line) {
                    $stdoutTask = $null
                } else {
                    $activity = $true
                    if ([string]::Equals($line.Trim(), "OK", [StringComparison]::OrdinalIgnoreCase)) {
                        $responseSeen = $true
                    }
                    $stdoutTask = $process.StandardOutput.ReadLineAsync()
                }
            }
            if ($null -ne $stderrTask -and $stderrTask.IsCompleted) {
                $line = $stderrTask.GetAwaiter().GetResult()
                if ($null -eq $line) {
                    $stderrTask = $null
                } else {
                    $activity = $true
                    $stderrTask = $process.StandardError.ReadLineAsync()
                }
            }
            if ($responseSeen) { break }
            if ($process.HasExited -and $null -eq $stdoutTask -and $null -eq $stderrTask) { break }
            if ([DateTime]::UtcNow -ge $deadline) {
                $timedOut = $true
                break
            }
            if (-not $activity) { Start-Sleep -Milliseconds 50 }
        }

        if (-not $responseSeen) {
            Stop-HermesRuntimeTestProcess $process
            if ($timedOut) {
                throw "Hermes did not return its connection test response within 90 seconds."
            }
            throw "Hermes could not receive a model response after configuration. Close Hermes completely and run setup again."
        }

        # Hermes 0.18.x can leave Windows cleanup threads alive after the model
        # response is already complete. The response is the connectivity proof;
        # do not turn a cleanup-only hang into a false setup failure.
        if (-not $process.WaitForExit(5000)) {
            Stop-HermesRuntimeTestProcess $process
        }
    } finally {
        Stop-HermesRuntimeTestProcess $process
        $process.Dispose()
    }
    Ok (T "hermesRuntimeOk")
}

function Update-HermesManagedProviders {
    param(
        [object]$HermesCommand,
        [string]$OpenAIEndpoint,
        [switch]$Restore
    )
    $python = Get-HermesPythonPath $HermesCommand
    if ([string]::IsNullOrWhiteSpace($python)) {
        throw "Hermes' Python runtime was not found for $($HermesCommand.Source). Checked the launcher directory and adjacent virtual-environment layouts."
    }
    $configOutput = @(& $HermesCommand.Source config path 2>$null)
    if ($LASTEXITCODE -ne 0) { throw "Hermes did not return its active config path." }
    $configLines = @($configOutput | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
    if ($configLines.Count -eq 0) { throw "Hermes returned an empty config path." }
    $configPath = [string]$configLines[-1]
    $configPath = Convert-HermesPathForHost $configPath
    if ([string]::IsNullOrWhiteSpace($configPath)) { throw "Hermes returned an empty config path." }

    $managed = [ordered]@{}
    if (-not $Restore) {
        $groups = [ordered]@{
            "aimarket" = [ordered]@{ name = "aimarket (GPT / Responses)"; transport = "codex_responses"; models = [ordered]@{} }
            "aimarket-anthropic" = [ordered]@{ name = "aimarket (Claude / Messages)"; transport = "anthropic_messages"; models = [ordered]@{} }
            "aimarket-compatible" = [ordered]@{ name = "aimarket (OpenAI compatible)"; transport = "chat_completions"; models = [ordered]@{} }
        }
        $models = @(Get-AvailableChatModels)
        if ($models.Count -eq 0) { $models = @($Model) }
        foreach ($modelName in $models) {
            $providerName = Get-HermesManagedProviderName $modelName
            $contextLength = Get-ManagedModelContextLength $modelName
            $modelConfig = [ordered]@{}
            if ($contextLength -gt 0) { $modelConfig.context_length = $contextLength }
            if (Test-ModelSupportsImageInput $modelName) { $modelConfig.supports_vision = $true }
            $groups[$providerName].models[$modelName] = $modelConfig
        }
        foreach ($providerName in $groups.Keys) {
            $group = $groups[$providerName]
            if ($group.models.Count -eq 0) { continue }
            $defaultModel = if ($group.models.Contains($Model)) { $Model } else { [string]@($group.models.Keys)[0] }
            $managed[$providerName] = [ordered]@{
                name = $group.name
                base_url = $OpenAIEndpoint
                key_env = "AIMARKET_API_KEY"
                default_model = $defaultModel
                transport = $group.transport
                models = $group.models
            }
        }
    }

    $payloadPath = [IO.Path]::GetTempFileName()
    $helperPath = [IO.Path]::GetTempFileName() + ".py"
    try {
        $payload = [ordered]@{
            config_path = $configPath
            managed = $managed
            remove = if ($Restore) {
                @("aimarket", "aimarket-anthropic", "aimarket-compatible")
            } else {
                @("aimarket", "aimarket-anthropic", "aimarket-compatible", "relayfast", "relayfast-anthropic", "relayfast-compatible")
            }
        } | ConvertTo-Json -Depth 20 -Compress
        Save-TextUtf8NoBom $payloadPath $payload
        $helper = @'
import json
import sys
from pathlib import Path

from hermes_cli.config import fast_safe_load
from utils import atomic_yaml_write

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
path = Path(payload["config_path"])
config = {}
if path.exists():
    with path.open("r", encoding="utf-8") as handle:
        config = fast_safe_load(handle) or {}
if not isinstance(config, dict):
    raise TypeError("Hermes config root must be a mapping")
providers = config.get("providers")
if providers is None:
    providers = {}
if not isinstance(providers, dict):
    raise TypeError("Hermes config 'providers' must be a mapping")
for name in payload["remove"]:
    providers.pop(name, None)
providers.update(payload["managed"])
if providers:
    config["providers"] = providers
else:
    config.pop("providers", None)
path.parent.mkdir(parents=True, exist_ok=True)
atomic_yaml_write(path, config, sort_keys=False)
'@
        Save-TextUtf8NoBom $helperPath $helper
        Backup-File $configPath
        & $python $helperPath $payloadPath | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Hermes rejected the managed provider catalog." }
    } finally {
        Remove-Item -LiteralPath $payloadPath, $helperPath -Force -ErrorAction SilentlyContinue
    }
}

function Convert-HermesPathForHost {
    param([string]$Path)
    $candidate = $Path.Trim().Trim('"')
    if ([string]::IsNullOrWhiteSpace($candidate)) { return "" }
    return [Environment]::ExpandEnvironmentVariables($candidate)
}

function Get-HermesLegacyEnvPath {
    $profileHome = if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) { $env:USERPROFILE } else { $HOME }
    return Join-Path (Join-Path $profileHome ".hermes") ".env"
}

function Get-HermesEnvPath {
    param([object]$HermesCommand = $null)
    if ($null -eq $HermesCommand) { $HermesCommand = Get-Command hermes -ErrorAction SilentlyContinue }
    if ($null -ne $HermesCommand) {
        $output = @(& $HermesCommand.Source config env-path 2>$null)
        if ($LASTEXITCODE -eq 0) {
            $candidate = @($output | ForEach-Object { ([string]$_).Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 1)
            if ($candidate.Count -gt 0) {
                $resolved = Convert-HermesPathForHost $candidate[0]
                if (-not [string]::IsNullOrWhiteSpace($resolved)) { return $resolved }
            }
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($env:HERMES_HOME)) {
        return Join-Path $env:HERMES_HOME ".env"
    }
    if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT -and -not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        return Join-Path (Join-Path $env:LOCALAPPDATA "hermes") ".env"
    }
    return Get-HermesLegacyEnvPath
}

function Test-HermesPathEqual {
    param([string]$Left, [string]$Right)
    try {
        $leftPath = [IO.Path]::GetFullPath($Left).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
        $rightPath = [IO.Path]::GetFullPath($Right).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    } catch {
        $leftPath = $Left.Trim()
        $rightPath = $Right.Trim()
    }
    $comparison = if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) { [StringComparison]::OrdinalIgnoreCase } else { [StringComparison]::Ordinal }
    return [string]::Equals($leftPath, $rightPath, $comparison)
}

function Get-DotEnvValue {
    param([string]$Path, [string]$Name)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return "" }
    $value = ""
    $pattern = "^\s*$([regex]::Escape($Name))\s*=\s*(.*)$"
    foreach ($line in @(Get-Content -LiteralPath $Path)) {
        if ($line -match $pattern) {
            $value = $Matches[1].Trim()
            if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }
    }
    return $value
}

function Get-HermesSavedApiKeyCandidate {
    $paths = New-Object System.Collections.Generic.List[string]
    foreach ($candidate in @((Get-HermesEnvPath), (Get-HermesLegacyEnvPath))) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        if (-not ($paths | Where-Object { Test-HermesPathEqual $_ $candidate })) { $paths.Add($candidate) }
    }
    foreach ($path in $paths) {
        $baseUrl = (Get-DotEnvValue -Path $path -Name "AIMARKET_BASE_URL").Trim().TrimEnd("/")
        if ([string]::IsNullOrWhiteSpace($baseUrl)) { $baseUrl = (Get-DotEnvValue -Path $path -Name "OPENAI_BASE_URL").Trim().TrimEnd("/") }
        if (-not [string]::Equals($baseUrl, $Endpoint.Trim().TrimEnd("/"), [StringComparison]::OrdinalIgnoreCase)) { continue }
        foreach ($keyName in @("AIMARKET_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")) {
            $value = (Get-DotEnvValue -Path $path -Name $keyName).Trim()
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                return [pscustomobject]@{ Name = $keyName; Scope = "Hermes"; Value = $value; Source = "Hermes credentials file $path" }
            }
        }
    }
    return $null
}

function Remove-HermesManagedBlocksAtPath {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return }
    $existing = Get-Content -Raw -LiteralPath $Path
    $clean = Remove-MarkedBlock $existing "# aimarket setup begin" "# aimarket setup end"
    $clean = Remove-MarkedBlock $clean "# relayfast setup begin" "# relayfast setup end"
    if ($clean -ceq $existing) { return }
    Backup-File $Path
    Save-TextUtf8NoBom $Path $clean
}

function Test-CodingAgentKey {
    param([string]$Key, [string]$OpenAIEndpoint)
    if ($SkipEndpointTest) { Warn "Endpoint test skipped."; return }
    Set-SetupTelemetryStep "endpoint_test"
    Section (T "testing")
    Get-OpenAIModels -OpenAIEndpoint $OpenAIEndpoint -Key $Key
    if ($script:OpenAIModelCatalogVerified) { Ok "GET /v1/models" }
    $initialModel = $script:Model
    $accessLimited = $false
    $lastResponse = $null
    $lastPath = ""
    foreach ($candidate in @(Get-ModelProbeCandidates)) {
        $apiMode = Get-HermesApiMode $candidate
        if ($apiMode -eq "anthropic_messages") {
            $lastPath = "messages"
            $headers = @{ "x-api-key" = $Key; "anthropic-version" = "2023-06-01" }
            $body = @{ model = $candidate; max_tokens = 8; messages = @(@{ role = "user"; content = "Reply with OK." }) }
            $lastResponse = Invoke-RouterHttp -Method POST -Url (Join-UrlPath $AnthropicEndpoint "v1/messages") -BearerToken $Key -Body $body -Headers $headers
        } elseif ($apiMode -eq "codex_responses") {
            $lastPath = "responses"
            $body = @{ model = $candidate; input = "Reply with OK."; max_output_tokens = 8; stream = $false }
            $lastResponse = Invoke-RouterHttp -Method POST -Url (Join-UrlPath $OpenAIEndpoint "responses") -BearerToken $Key -Body $body
        } else {
            $lastPath = "chat/completions"
            $body = @{ model = $candidate; messages = @(@{ role = "user"; content = "Reply with OK." }); max_tokens = 8; stream = $false }
            $lastResponse = Invoke-RouterHttp -Method POST -Url (Join-UrlPath $OpenAIEndpoint "chat/completions") -BearerToken $Key -Body $body
        }
        if (Test-TransientProbeResponse $lastResponse) {
            Warn-NonFatalProbeFailure $lastResponse "POST /v1/$lastPath"
            return
        }
        if ($lastResponse.Ok) {
            Complete-ModelProbe -InitialModel $initialModel -SelectedModel $candidate -AccessLimited $accessLimited
            Ok "POST /v1/$lastPath"
            return
        }
        if (Test-ModelAccessFailure $lastResponse) { $accessLimited = $true }
        if (Test-RetryableModelProbeFailure $lastResponse) {
            Warn (T "modelProbeRetry" @{ model = $candidate })
            continue
        }
        Assert-HttpOk $lastResponse "POST /v1/$lastPath"
    }
    Assert-HttpOk $lastResponse "POST /v1/$lastPath"
}

function Get-HermesSupportedReasoningEfforts {
    param([string]$ModelName)
    $lower = $ModelName.Trim().ToLowerInvariant()
    if ($lower -match '^grok-4\.5(?:$|[-_.:])') {
        return @("low", "medium", "high")
    }
    if ($lower -match '^grok-4\.6(?:$|[-_.:])') {
        return @("low", "medium", "high", "xhigh")
    }

    if ($lower -match '^grok-4\.7(?:$|[-_.:])') {
        return @("low", "medium", "high", "xhigh")
    }
    if ($lower -match '^deepseek-v[4-9](?:$|[-_.:])' -or $lower -match '^deepseek-reasoner(?:$|[-_.:])') {
        return @("none", "minimal", "low", "medium", "high", "xhigh")
    }
    if ($lower -match '^kimi-k3(?:$|[-_.:])') {
        return @("low", "high", "max")
    }
    if ($lower -match '^kimi-k2\.(?:6|7)(?:$|[-_.:])' -or $lower -match '^minimax-m3(?:$|[-_.:])') {
        return @()
    }
    if ($lower -match '^(?:glm|gemini|gemma|learnlm)(?:[-_.:]|$)') {
        return @("low", "medium", "high")
    }
    return @("none", "minimal", "low", "medium", "high", "xhigh")
}

function Get-HermesEffectiveReasoningEffort {
    param([string]$ModelName, [string]$Effort)
    $lower = $ModelName.Trim().ToLowerInvariant()
    if ($lower -match '^kimi-k3(?:$|[-_.:])' -and -not $script:HermesReasoningEffortExplicit -and $Effort -eq "medium") {
        return "max"
    }
    if ($lower -match '^kimi-k2\.(?:6|7)(?:$|[-_.:])' -or $lower -match '^minimax-m3(?:$|[-_.:])') {
        return ""
    }
    return $Effort
}

function Assert-HermesReasoningEffortSupported {
    param([string]$ModelName, [string]$Effort)
    $supported = @(Get-HermesSupportedReasoningEfforts $ModelName)
    if ($Effort -notin $supported) {
        throw "Hermes reasoning effort '$Effort' is not supported by $ModelName. Choose one of: $($supported -join ', ')."
    }
}

function Setup-Hermes {
    param([string]$Key, [string]$OpenAIEndpoint)
    Test-CodingAgentKey -Key $Key -OpenAIEndpoint $OpenAIEndpoint
    $effectiveReasoningEffort = Get-HermesEffectiveReasoningEffort -ModelName $Model -Effort $HermesReasoningEffort
    if (-not [string]::IsNullOrWhiteSpace($effectiveReasoningEffort)) {
        Assert-HermesReasoningEffortSupported -ModelName $Model -Effort $effectiveReasoningEffort
    }
    Section (T "writing")
    Set-SetupTelemetryStep "write_hermes_config"
    $hermes = Get-Command hermes -ErrorAction SilentlyContinue
    if ($null -ne $hermes -and -not $DryRun) {
        Set-SetupTelemetryStep "check_hermes_runtime"
        Assert-HermesSetupRuntime $hermes
    }
    $path = Get-HermesEnvPath -HermesCommand $hermes
    $legacyPath = Get-HermesLegacyEnvPath
    $apiMode = Get-HermesApiMode $Model
    $keyName = "AIMARKET_API_KEY"
    $providerName = Get-HermesManagedProviderName $Model
    $providerId = "custom:$providerName"
    $begin = "# aimarket setup begin"
    $end = "# aimarket setup end"
    $existing = if (Test-Path -LiteralPath $path) { Get-Content -Raw -LiteralPath $path } else { "" }
    $clean = Remove-MarkedBlock $existing $begin $end
    $clean = Remove-MarkedBlock $clean "# relayfast setup begin" "# relayfast setup end"
    $block = @(
        $begin
        "$keyName=$Key"
        "AIMARKET_BASE_URL=$OpenAIEndpoint"
        "HERMES_MODEL=$Model"
        $end
        ""
    ) -join "`r`n"
    Backup-File $path
    Save-TextUtf8NoBom $path ($clean.TrimEnd() + "`r`n" + $block)
    if (-not (Test-HermesPathEqual $path $legacyPath)) {
        Remove-HermesManagedBlocksAtPath $legacyPath
        Ok "$(T "hermesLegacyCleaned"): $legacyPath"
    }
    if ($null -ne $hermes -and -not $DryRun) {
        Update-HermesManagedProviders -HermesCommand $hermes -OpenAIEndpoint $OpenAIEndpoint
        Update-HermesReasoningSessionFix -HermesCommand $hermes
        $settings = @(
            @("model.provider", $providerId),
            @("model.default", $Model),
            @("model.base_url", $OpenAIEndpoint),
            @("model.api_mode", $apiMode)
        )
        if (-not [string]::IsNullOrWhiteSpace($effectiveReasoningEffort)) {
            $settings += ,@("agent.reasoning_effort", $effectiveReasoningEffort)
        }
        foreach ($setting in $settings) {
            & $hermes.Source config set $setting[0] $setting[1] | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "Hermes rejected config setting $($setting[0])." }
        }
        if ($apiMode -eq "codex_responses") {
            Update-HermesWindowsTransportFix -HermesCommand $hermes
            Test-HermesRuntime -HermesCommand $hermes
        }
        $verifiedPath = Get-HermesEnvPath -HermesCommand $hermes
        if (-not (Test-HermesPathEqual $path $verifiedPath)) { throw "Hermes active credentials path changed during setup: $verifiedPath" }
        if (-not [string]::Equals((Get-DotEnvValue -Path $verifiedPath -Name $keyName), $Key, [StringComparison]::Ordinal)) {
            throw "Hermes active credentials file does not contain the configured aimarket API key."
        }
    } elseif ($null -eq $hermes) {
        Warn "hermes command was not found. Install Hermes and rerun setup so the model-specific API mode can be applied."
    } elseif ($DryRun) {
        Ok "Would configure Hermes custom provider with model.api_mode=$apiMode and agent.reasoning_effort=$effectiveReasoningEffort."
        Ok "Would validate or patch Hermes Desktop session-scoped reasoning selection."
        if ($apiMode -eq "codex_responses" -and [Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
            Ok "Would apply and validate the Hermes Windows streaming compatibility fix."
        }
    }
    Ok "$(T "hermesEnvPath"): $path"
    Ok "$(T "hermesProtocol"): $apiMode"
    $supportedEfforts = @(Get-HermesSupportedReasoningEfforts $Model)
    $displayReasoningEffort = if ([string]::IsNullOrWhiteSpace($effectiveReasoningEffort)) { "native-thinking" } else { $effectiveReasoningEffort }
    Ok "$(T "hermesReasoning"): $displayReasoningEffort (/reasoning $($supportedEfforts -join '|'))"
}

function Restore-Hermes {
    $hermes = Get-Command hermes -ErrorAction SilentlyContinue
    $path = Get-HermesEnvPath -HermesCommand $hermes
    $legacyPath = Get-HermesLegacyEnvPath
    Remove-HermesManagedBlocksAtPath $path
    if (-not (Test-HermesPathEqual $path $legacyPath)) {
        Remove-HermesManagedBlocksAtPath $legacyPath
    }
    if ($null -ne $hermes -and -not $DryRun) {
        Update-HermesManagedProviders -HermesCommand $hermes -OpenAIEndpoint $Endpoint -Restore
        Update-HermesReasoningSessionFix -HermesCommand $hermes -Restore
        Update-HermesWindowsTransportFix -HermesCommand $hermes -Restore
        & $hermes.Source config set model.provider auto | Out-Null
        & $hermes.Source config set model.base_url "" | Out-Null
        & $hermes.Source config set model.api_mode "" | Out-Null
    }
}

function Get-CursorStorageInfo {
    $databasePath = if (-not [string]::IsNullOrWhiteSpace($env:APPDATA)) {
        Join-Path $env:APPDATA "Cursor\User\globalStorage\state.vscdb"
    } else { "" }
    $roots = New-Object System.Collections.Generic.List[string]
    foreach ($base in @($env:LOCALAPPDATA, $env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not [string]::IsNullOrWhiteSpace($base)) {
            $roots.Add((Join-Path $base "Programs\cursor\resources\app"))
            $roots.Add((Join-Path $base "Cursor\resources\app"))
        }
    }
    foreach ($root in $roots) {
        $nodePath = Join-Path $root "resources\helpers\node.exe"
        $modulePath = Join-Path $root "node_modules\@vscode\sqlite3"
        if ((Test-Path -LiteralPath $databasePath -PathType Leaf) -and
            (Test-Path -LiteralPath $nodePath -PathType Leaf) -and
            (Test-Path -LiteralPath $modulePath -PathType Container)) {
            return [pscustomobject]@{
                DatabasePath = $databasePath
                NodePath = $nodePath
                SqliteModulePath = $modulePath
            }
        }
    }
    throw (T "cursorNotFound")
}

function Assert-CursorClosed {
    if ($null -ne (Get-Process -Name "Cursor" -ErrorAction SilentlyContinue | Select-Object -First 1)) {
        throw (T "cursorClosed")
    }
}

function Close-CursorForSetup {
    $running = @(Get-Process -Name "Cursor" -ErrorAction SilentlyContinue)
    if ($running.Count -eq 0) { return }
    if (-not [string]::IsNullOrWhiteSpace($env:CURSOR_TRACE_ID) -or $env:TERM_PROGRAM -eq "vscode") {
        throw (T "appInsideTerminal" @{ app = "Cursor" })
    }
    if (-not (Test-CanPromptForApiKey)) { throw (T "cursorClosed") }
    $answer = (Read-Host (T "appRunningPrompt" @{ app = "Cursor" })).Trim()
    if ($answer -match '^(n|no|\u043d|\u043d\u0435\u0442)$') { throw (T "cursorClosed") }
    Ok (T "appClosing" @{ app = "Cursor" })
    foreach ($process in $running) {
        try { if ($process.MainWindowHandle -ne [IntPtr]::Zero) { [void]$process.CloseMainWindow() } } catch {}
    }
    for ($i = 0; $i -lt 20; $i++) {
        if ($null -eq (Get-Process -Name "Cursor" -ErrorAction SilentlyContinue | Select-Object -First 1)) { return }
        Start-Sleep -Seconds 1
    }
    throw (T "appStillRunning" @{ app = "Cursor" })
}

function Backup-CursorDatabase {
    param([object]$Info)
    $backupDirectory = "$($Info.DatabasePath).aimarket-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
    if ($DryRun) {
        Ok "Would create Cursor database backup: $backupDirectory"
        return
    }
    New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
    foreach ($path in @($Info.DatabasePath, "$($Info.DatabasePath)-wal", "$($Info.DatabasePath)-shm")) {
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Copy-Item -LiteralPath $path -Destination (Join-Path $backupDirectory ([IO.Path]::GetFileName($path)))
        }
    }
    Ok "Cursor database backup: $backupDirectory"
}

function Get-CursorManagedModels {
    $source = @(Get-AvailableChatModels)
    if ($source.Count -eq 0) { $source = @($script:Model) }
    $seen = @{}
    $models = New-Object System.Collections.Generic.List[string]
    foreach ($name in $source) {
        if (-not (Test-CursorCompatibleModel $name)) { continue }
        if (-not $seen.ContainsKey($name)) {
            $seen[$name] = $true
            $models.Add($name)
        }
    }
    if ((Test-CursorCompatibleModel $script:Model) -and -not $seen.ContainsKey($script:Model)) {
        $models.Add($script:Model)
    }
    return $models.ToArray()
}

function Invoke-CursorStorageUpdate {
    param(
        [ValidateSet("setup", "restore")]
        [string]$Mode,
        [string]$Key = "",
        [string]$OpenAIEndpoint = ""
    )
    Assert-CursorClosed
    $info = Get-CursorStorageInfo
    Backup-CursorDatabase $info
    if ($DryRun) {
        return [pscustomobject]@{ status = if ($Mode -eq "setup") { "configured" } else { "restored" }; modelCount = 0 }
    }

    $helperPath = [IO.Path]::GetTempFileName() + ".js"
    $modelsPath = [IO.Path]::GetTempFileName()
    $previousKey = [Environment]::GetEnvironmentVariable("AIMARKET_CURSOR_SETUP_KEY", "Process")
    try {
        $models = if ($Mode -eq "setup") { @(Get-CursorManagedModels) } else { @() }
        Save-TextUtf8NoBom $modelsPath (ConvertTo-Json -InputObject @($models) -Compress)
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

function clone(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

function capture(object, property) {
  return Object.prototype.hasOwnProperty.call(object, property)
    ? { exists: true, value: clone(object[property]) }
    : { exists: false };
}

function restoreProperty(object, property, snapshot) {
  if (snapshot && snapshot.exists) object[property] = clone(snapshot.value);
  else delete object[property];
}

function stringArray(value, label) {
  if (value === undefined) return [];
  if (!Array.isArray(value) || !value.every(item => typeof item === "string")) {
    throw new TypeError(`Cursor setting '${label}' must be an array of strings`);
  }
  return [...value];
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

    if (action === "restore") {
      if (!state) {
        await run(database, "COMMIT");
        transaction = false;
        process.stdout.write(JSON.stringify({ status: "not-managed" }));
        return;
      }
      if (state.owner !== owner && state.owner !== "routercheap") {
        await run(database, "COMMIT");
        transaction = false;
        process.stdout.write(JSON.stringify({ status: "other-owner", owner: state.owner }));
        return;
      }
      const original = state.original;
      restoreProperty(application, "openAIBaseUrl", original.application.openAIBaseUrl);
      restoreProperty(application, "useOpenAIKey", original.application.useOpenAIKey);
      if (original.application.aiSettingsExists) {
        if (!application.aiSettings || typeof application.aiSettings !== "object" || Array.isArray(application.aiSettings)) application.aiSettings = {};
        restoreProperty(application.aiSettings, "userAddedModels", original.application.userAddedModels);
        restoreProperty(application.aiSettings, "modelOverrideEnabled", original.application.modelOverrideEnabled);
        restoreProperty(application.aiSettings, "modelOverrideDisabled", original.application.modelOverrideDisabled);
      } else {
        delete application.aiSettings;
      }
      await upsert(database, applicationKey, JSON.stringify(application));
      if (original.apiKey.exists) await upsert(database, apiKeyStorageKey, original.apiKey.value);
      else await run(database, "DELETE FROM ItemTable WHERE key = ?", [apiKeyStorageKey]);
      await run(database, "DELETE FROM ItemTable WHERE key = ?", [setupStateKey]);
      await run(database, "COMMIT");
      transaction = false;
      process.stdout.write(JSON.stringify({ status: "restored" }));
      return;
    }

    if (action !== "setup") throw new Error(`Unknown Cursor setup action '${action}'`);
    const apiKey = process.env.AIMARKET_CURSOR_SETUP_KEY || "";
    if (!apiKey.startsWith("sk-")) throw new Error("Cursor setup API key is missing or malformed");
    const models = JSON.parse(fs.readFileSync(modelsPath, "utf8"));
    if (!Array.isArray(models) || models.length === 0 || !models.every(item => typeof item === "string" && item.trim())) {
      throw new TypeError("Cursor setup model catalog is empty or malformed");
    }
    const uniqueModels = [...new Set(models.map(item => item.trim()))];
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
    const added = stringArray(application.aiSettings.userAddedModels, "aiSettings.userAddedModels").filter(value => keep(value, originalAdded));
    const enabled = stringArray(application.aiSettings.modelOverrideEnabled, "aiSettings.modelOverrideEnabled").filter(value => keep(value, originalEnabled));
    const disabled = stringArray(application.aiSettings.modelOverrideDisabled, "aiSettings.modelOverrideDisabled").filter(value => !currentManaged.has(value));
    for (const model of uniqueModels) {
      if (!added.includes(model)) added.push(model);
      if (!enabled.includes(model)) enabled.push(model);
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
    if (transaction) {
      try { await run(database, "ROLLBACK"); } catch (_) {}
    }
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
        Save-TextUtf8NoBom $helperPath $helper
        if ($Mode -eq "setup") {
            [Environment]::SetEnvironmentVariable("AIMARKET_CURSOR_SETUP_KEY", $Key, "Process")
        } else {
            [Environment]::SetEnvironmentVariable("AIMARKET_CURSOR_SETUP_KEY", $null, "Process")
        }
        $endpointArgument = if ([string]::IsNullOrWhiteSpace($OpenAIEndpoint)) { "https://router.cheap/v1" } else { $OpenAIEndpoint }
        $output = @(& $info.NodePath $helperPath $info.SqliteModulePath $info.DatabasePath $Mode $endpointArgument "aimarket" $modelsPath 2>&1)
        if ($LASTEXITCODE -ne 0) {
            throw "Cursor settings update failed: $($output -join [Environment]::NewLine)"
        }
        $outputLines = @($output | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
        if ($outputLines.Count -eq 0) { throw "Cursor settings update returned no result." }
        $json = [string]$outputLines[-1]
        return ($json | ConvertFrom-Json)
    } finally {
        [Environment]::SetEnvironmentVariable("AIMARKET_CURSOR_SETUP_KEY", $previousKey, "Process")
        Remove-Item -LiteralPath $helperPath, $modelsPath -Force -ErrorAction SilentlyContinue
    }
}

function Setup-Cursor {
    param([string]$Key, [string]$OpenAIEndpoint)
    Test-OpenAIKey -OpenAIEndpoint $OpenAIEndpoint -Key $Key -ModelName $Model
    Set-SetupTelemetryStep "write_cursor_config"
    Section (T "writing")
    $result = Invoke-CursorStorageUpdate -Mode "setup" -Key $Key -OpenAIEndpoint $OpenAIEndpoint
    Ok (T "cursorConfigured")
    Warn (T "cursorLimit")
}

function Restore-Cursor {
    $result = Invoke-CursorStorageUpdate -Mode "restore"
    switch ([string]$result.status) {
        "restored" { Ok (T "cursorRestored") }
        "not-managed" { Warn (T "cursorNotManaged") }
        "other-owner" { Warn (T "cursorOtherOwner" @{ owner = [string]$result.owner }) }
        default { throw "Unexpected Cursor restore result '$($result.status)'." }
    }
}

function Choose-App {
    $items = @(
        @{ id = "codex"; label = "Codex" },
        @{ id = "claude-code"; label = "Claude Code" },
        @{ id = "opencode"; label = "OpenCode" },
        @{ id = "hermes"; label = "Hermes" },
        @{ id = "grok-build"; label = "Grok Build" },
        @{ id = "cursor"; label = "Cursor" },
        @{ id = "droid"; label = "Factory Droid" }
    )
    Section (T "selectApp")
    for ($i = 0; $i -lt $items.Count; $i++) { Write-Host "$($i + 1). $($items[$i].label)" }
    Write-Host "$($items.Count + 1). $(T "exit")"
    $raw = Read-Host (T "choice")
    $n = 0
    if (-not [int]::TryParse($raw, [ref]$n)) { Fail (T "badChoice") }
    if ($n -eq $items.Count + 1) { exit 0 }
    if ($n -lt 1 -or $n -gt $items.Count) { Fail (T "badChoice") }
    return $items[$n - 1].id
}

function Choose-Action {
    param([string]$AppName)
    $label = Get-AppLabel $AppName
    Section (T "selectAction" @{ app = $label })
    Write-Host "1. $(T "configure" @{ app = $label })"
    if (Supports-Restore $AppName) {
        Write-Host "2. $(T "restore" @{ app = $label })"
        Write-Host "3. $(T "configureReserve" @{ app = $label })"
        Write-Host "4. $(T "exit")"
    } else {
        Write-Host "2. $(T "exit")"
        Write-Host "3. $(T "configureReserve" @{ app = $label })"
    }
    $raw = Read-Host (T "choice")
    if (Supports-Restore $AppName) {
        switch ($raw) {
            "1" { return "setup" }
            "2" { return "restore" }
            "3" { return "setup-reserve" }
            "4" { exit 0 }
            default { Fail (T "badChoice") }
        }
    } else {
        switch ($raw) {
            "1" { return "setup" }
            "2" { exit 0 }
            "3" { return "setup-reserve" }
            default { Fail (T "badChoice") }
        }
    }
}

function Supports-Restore {
    param([string]$AppName)
    return $AppName -notin @("opencode", "droid")
}

function Set-ReserveEndpoints {
    $script:Endpoint = "https://direct.router-cheap.com/v1"
    $script:AnthropicEndpoint = "https://direct.router-cheap.com"
}

function Get-AppLabel {
    param([string]$AppName)
    switch ($AppName) {
        "codex" { "Codex" }
        "claude-code" { "Claude Code" }
        "opencode" { "OpenCode" }
        "hermes" { "Hermes" }
        "grok-build" { "Grok Build" }
        "cursor" { "Cursor" }
        "droid" { "Factory Droid" }
        default { $AppName }
    }
}

Load-Messages
$Endpoint = Normalize-OpenAIBaseUrl $Endpoint
$AnthropicEndpoint = Normalize-AnthropicBaseUrl $AnthropicEndpoint
Section (T "title")

if ([string]::IsNullOrWhiteSpace($App)) {
    $App = Choose-App
    if ([string]::IsNullOrWhiteSpace($Action)) { $Action = Choose-Action $App }
}
if ([string]::IsNullOrWhiteSpace($Action)) { $Action = "setup" }

if ($Action -eq "setup-reserve") { Set-ReserveEndpoints }
$Endpoint = Normalize-OpenAIBaseUrl $Endpoint
$AnthropicEndpoint = Normalize-AnthropicBaseUrl $AnthropicEndpoint

if ($Action -eq "restore" -and -not (Supports-Restore $App)) {
    Fail (T "restoreNotNeeded")
}

if ($App -eq "cursor" -and -not $DryRun) { Close-CursorForSetup }

if ($Action -eq "setup" -or $Action -eq "setup-reserve") {
    $key = Get-PlainApiKey
    if ([string]::IsNullOrWhiteSpace($key)) { Fail "API key is empty." }
    $script:SetupTelemetrySessionId = [guid]::NewGuid().ToString("N")
    $script:SetupTelemetryStartedAt = [DateTimeOffset]::UtcNow
    Set-SetupTelemetryStep "setup"
    Send-SetupTelemetry -Key $key -AppName $App -ActionName "setup" -Result "started"
    try {
        if ($App -eq "codex" -and $null -eq (Get-Command codex -ErrorAction SilentlyContinue) -and $InstallCodexIfMissing) {
            Install-CodexIfMissing -DryRun:$DryRun
        }
        Prepare-SetupModel -AppName $App -Key $key -OpenAIEndpoint $Endpoint -AnthropicBase $AnthropicEndpoint
        Select-DefaultOpenAIModelInteractive -AppName $App
        Ok "$(T "endpoint"): $(if ($App -eq "claude-code") { $AnthropicEndpoint } else { $Endpoint })"
        Ok "$(T "model"): $(if ($App -eq "claude-code") { $ClaudeModel } elseif ($App -eq "grok-build") { $GrokModel } else { $Model })"
        Ok "$(T "key"): $(Mask-Key $key)"
        switch ($App) {
            "codex" { Setup-Codex $key $Endpoint }
            "claude-code" { Setup-ClaudeCode $key $AnthropicEndpoint }
            "opencode" { Setup-OpenCode $key $Endpoint }
            "hermes" { Setup-Hermes $key $Endpoint }
            "grok-build" { Setup-GrokBuild $key $Endpoint }
            "cursor" { Setup-Cursor $key $Endpoint }
            "droid" { Setup-Droid $key $Endpoint }
        }
        Send-SetupTelemetry -Key $key -AppName $App -ActionName "setup" -Result "success"
    } catch {
        $errorFunction = if ($null -ne $_.InvocationInfo.MyCommand) { [string]$_.InvocationInfo.MyCommand.Name } else { "" }
        $errorLine = [int]$_.InvocationInfo.ScriptLineNumber
        Send-SetupTelemetry -Key $key -AppName $App -ActionName "setup" -Result "failed" -ErrorMessage $_.Exception.Message -ErrorStep $script:SetupTelemetryStep -ErrorFunction $errorFunction -ErrorLine $errorLine -ExitCode 1
        Write-Host ""
        Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red
        Warn (T "networkHint")
        Warn (T "failedSupport" @{ session = $script:SetupTelemetrySessionId })
        exit 1
    }
    if ($App -eq "codex") { Ok (T "done") } else { Ok (T "doneApp" @{ app = (Get-AppLabel $App) }) }
} else {
    switch ($App) {
        "codex" { Restore-Codex }
        "claude-code" { Restore-ClaudeCode }
        "opencode" { Restore-OpenCode }
        "hermes" { Restore-Hermes }
        "grok-build" { Restore-GrokBuild }
        "cursor" { Restore-Cursor }
    }
    if ($App -eq "codex") { Ok (T "restored") } else { Ok (T "restoredApp" @{ app = (Get-AppLabel $App) }) }
}
