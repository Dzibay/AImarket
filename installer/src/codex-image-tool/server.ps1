[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)

function Get-ImageToolEnvironment {
    param([string]$Name, [string]$Fallback = "")
    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) { return $Fallback }
    return $value.Trim()
}

function Get-ImageToolEndpoint {
    $base = Get-ImageToolEnvironment "ROUTER_IMAGE_BASE_URL"
    if ($base -notmatch '^https?://') { throw "ROUTER_IMAGE_BASE_URL is not configured" }
    return $base.TrimEnd('/') + "/images/generations"
}

function Get-ImageToolApiKey {
    $name = Get-ImageToolEnvironment "ROUTER_IMAGE_API_KEY_ENV"
    $key = if ($name) { [Environment]::GetEnvironmentVariable($name, "Process") } else { "" }
    if ([string]::IsNullOrWhiteSpace($key)) { throw "$(if ($name) { $name } else { 'API key environment variable' }) is not available to the image tool" }
    return $key.Trim()
}

function Get-ImageToolOutput {
    param([object]$Arguments)
    $format = if ($Arguments.PSObject.Properties["output_format"] -and $Arguments.output_format) { ([string]$Arguments.output_format).Trim().ToLowerInvariant() } else { "png" }
    if ($format -notin @("png", "jpeg", "webp")) { throw "output_format must be png, jpeg, or webp" }
    $codexHome = Get-ImageToolEnvironment "CODEX_HOME" (Join-Path $env:USERPROFILE ".codex")
    $outputPath = Join-Path $codexHome ("generated_images\endpoint-image-tool\{0}.{1}" -f ([guid]::NewGuid().ToString("N")), $format)
    return [pscustomobject]@{ Format = $format; Path = $outputPath }
}

function Invoke-ImageToolGenerate {
    param([object]$Arguments)
    $prompt = if ($Arguments.PSObject.Properties["prompt"]) { ([string]$Arguments.prompt).Trim() } else { "" }
    if (-not $prompt) { throw "prompt is required" }
    $output = Get-ImageToolOutput $Arguments
    $size = if ($Arguments.PSObject.Properties["size"] -and $Arguments.size) { [string]$Arguments.size } else { "1024x1024" }
    $quality = if ($Arguments.PSObject.Properties["quality"] -and $Arguments.quality) { [string]$Arguments.quality } else { "auto" }
    $model = Get-ImageToolEnvironment "ROUTER_IMAGE_MODEL" "gpt-image-2"
    $payload = [ordered]@{ model = $model; prompt = $prompt; n = 1; size = $size; quality = $quality; output_format = $output.Format }
    $body = $payload | ConvertTo-Json -Compress
    try {
        $response = Invoke-RestMethod -Method Post -Uri (Get-ImageToolEndpoint) -Headers @{ Authorization = "Bearer $(Get-ImageToolApiKey)"; Accept = "application/json"; "User-Agent" = "codex-endpoint-image-tool/1.0" } -ContentType "application/json" -Body $body -TimeoutSec 900
    } catch {
        $message = $_.Exception.Message
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try {
                $errorBody = $_.ErrorDetails.Message | ConvertFrom-Json
                if ($errorBody.error.message) { $message = [string]$errorBody.error.message }
            } catch {}
        }
        throw $message
    }
    $item = @($response.data) | Select-Object -First 1
    if ($null -eq $item -or [string]::IsNullOrWhiteSpace([string]$item.b64_json)) { throw "image API response did not contain b64_json" }
    try { $bytes = [Convert]::FromBase64String([string]$item.b64_json) } catch { throw "image API returned invalid base64 image data" }
    if ($bytes.Length -eq 0) { throw "image API returned an empty image" }
    $directory = Split-Path -Parent $output.Path
    [IO.Directory]::CreateDirectory($directory) | Out-Null
    $temporary = Join-Path $directory (".{0}.{1}.tmp" -f ([IO.Path]::GetFileName($output.Path)), ([guid]::NewGuid().ToString("N")))
    try {
        [IO.File]::WriteAllBytes($temporary, $bytes)
        Move-Item -LiteralPath $temporary -Destination $output.Path -Force
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
    $mime = if ($output.Format -eq "jpeg") { "image/jpeg" } else { "image/$($output.Format)" }
    $brand = Get-ImageToolEnvironment "ROUTER_IMAGE_BRAND" "the configured endpoint"
    return [ordered]@{
        content = @(
            [ordered]@{ type = "text"; text = "Generated with $brand $model and saved to $($output.Path)" },
            [ordered]@{ type = "image"; data = [string]$item.b64_json; mimeType = $mime }
        )
        structuredContent = [ordered]@{
            path = $output.Path; model = $model; size = $size; quality = $quality; format = $output.Format; bytes = $bytes.Length
            revised_prompt = if ($item.PSObject.Properties["revised_prompt"]) { [string]$item.revised_prompt } else { "" }
        }
    }
}

$tool = [ordered]@{
    name = "generate_image"
    title = "Generate image"
    description = "Generate one raster image with the configured gpt-image-2 endpoint, save it under CODEX_HOME/generated_images/endpoint-image-tool, and return a preview."
    inputSchema = [ordered]@{
        type = "object"; additionalProperties = $false; required = @("prompt")
        properties = [ordered]@{
            prompt = [ordered]@{ type = "string"; minLength = 1; description = "Detailed image prompt." }
            size = [ordered]@{ type = "string"; default = "1024x1024" }
            quality = [ordered]@{ type = "string"; enum = @("auto", "low", "medium", "high"); default = "auto" }
            output_format = [ordered]@{ type = "string"; enum = @("png", "jpeg", "webp"); default = "png" }
        }
    }
    annotations = [ordered]@{ title = "Generate image"; readOnlyHint = $false; destructiveHint = $false; idempotentHint = $false; openWorldHint = $true }
}

while ($null -ne ($line = [Console]::In.ReadLine())) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try { $request = $line | ConvertFrom-Json } catch { continue }
    if (-not $request.method -or ([string]$request.method).StartsWith("notifications/")) { continue }
    try {
        switch ([string]$request.method) {
            "initialize" { $result = [ordered]@{ protocolVersion = if ($request.params.protocolVersion) { [string]$request.params.protocolVersion } else { "2025-06-18" }; capabilities = [ordered]@{ tools = [ordered]@{ listChanged = $false } }; serverInfo = [ordered]@{ name = "endpoint-image-generation"; version = "1.0.0" } } }
            "ping" { $result = [ordered]@{} }
            "tools/list" { $result = [ordered]@{ tools = @($tool) } }
            "tools/call" {
                if ([string]$request.params.name -ne "generate_image") { throw "unknown tool: $($request.params.name)" }
                $result = Invoke-ImageToolGenerate $request.params.arguments
            }
            default {
                $response = [ordered]@{ jsonrpc = "2.0"; id = $request.id; error = [ordered]@{ code = -32601; message = "method not found: $($request.method)" } }
                [Console]::Out.WriteLine(($response | ConvertTo-Json -Compress -Depth 20)); [Console]::Out.Flush(); continue
            }
        }
        $response = [ordered]@{ jsonrpc = "2.0"; id = $request.id; result = $result }
    } catch {
        if ([string]$request.method -eq "tools/call") {
            $response = [ordered]@{ jsonrpc = "2.0"; id = $request.id; result = [ordered]@{ isError = $true; content = @([ordered]@{ type = "text"; text = $_.Exception.Message }) } }
        } else {
            $response = [ordered]@{ jsonrpc = "2.0"; id = $request.id; error = [ordered]@{ code = -32603; message = $_.Exception.Message } }
        }
    }
    [Console]::Out.WriteLine(($response | ConvertTo-Json -Compress -Depth 20))
    [Console]::Out.Flush()
}
