param(
    [int]$Port = 8787,
    [ValidateSet("token", "cache")]
    [string]$Mode = "token",
    [decimal]$Budget = 0,
    [string]$ResumeId = "",
    [switch]$ResumeLast,
    [switch]$NoOptimize,
    [switch]$NoCache,
    [switch]$NoRateLimit,
    [switch]$Stateless,
    [string]$WorkspaceDir = "",
    [string]$ConfigDir = "",
    [string]$KompressBackend = "",
    [switch]$DisableStickyBeta
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$codexConfigPath = Join-Path $env:USERPROFILE ".codex\config.toml"
if (-not (Test-Path $codexConfigPath)) { throw "Codex config not found at $codexConfigPath" }

if (-not $WorkspaceDir) { $WorkspaceDir = Join-Path $repoRoot ".headroom" }
if (-not $ConfigDir) { $ConfigDir = Join-Path $WorkspaceDir "config" }

$proxyCheckUrl = "http://127.0.0.1:$Port/health"
$proxyRunning = $false
try {
    $health = Invoke-RestMethod -Uri $proxyCheckUrl -TimeoutSec 2
    $proxyRunning = $health.ready -eq $true
} catch {
    $proxyRunning = $false
}

if (-not $proxyRunning) {
    $headroomArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $repoRoot "scripts\headroom\start-headroom.ps1"),
        "-Port", $Port,
        "-Mode", $Mode,
        "-WorkspaceDir", $WorkspaceDir,
        "-ConfigDir", $ConfigDir
    )
    if ($Budget -gt 0) { $headroomArgs += @("-Budget", $Budget) }
    if ($NoOptimize) { $headroomArgs += "-NoOptimize" }
    if ($NoCache) { $headroomArgs += "-NoCache" }
    if ($NoRateLimit) { $headroomArgs += "-NoRateLimit" }
    if ($Stateless) { $headroomArgs += "-Stateless" }
    if ($KompressBackend) { $headroomArgs += @("-KompressBackend", $KompressBackend) }
    if ($DisableStickyBeta) { $headroomArgs += "-DisableStickyBeta" }
    Start-Process powershell.exe -ArgumentList $headroomArgs -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 6
}

Push-Location $repoRoot
try {
    $env:HEADROOM_WORKSPACE_DIR = $WorkspaceDir
    $env:HEADROOM_CONFIG_DIR = $ConfigDir
    $env:HEADROOM_BASE_URL = "http://127.0.0.1:$Port"
    $env:OPENAI_BASE_URL = "http://127.0.0.1:$Port/v1"
    $env:ANTHROPIC_BASE_URL = "http://127.0.0.1:$Port"
    if ($KompressBackend) { $env:HEADROOM_KOMPRESS_BACKEND = $KompressBackend }
    if ($DisableStickyBeta) { $env:HEADROOM_BETA_HEADER_STICKY = "disabled" }

    if ($ResumeLast) { codex resume --last }
    elseif ($ResumeId) { codex resume $ResumeId }
    else { codex }
}
finally { Pop-Location }
