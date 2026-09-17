param(
    [int]$Port = 8787,
    [ValidateSet("token", "cache")]
    [string]$Mode = "token",
    [decimal]$Budget = 0,
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
$headroomCmd = Get-Command headroom -ErrorAction Stop
$headroomExe = $headroomCmd.Source

if (-not $WorkspaceDir) { $WorkspaceDir = Join-Path $repoRoot ".headroom" }
if (-not $ConfigDir) { $ConfigDir = Join-Path $WorkspaceDir "config" }

$logDir = Join-Path $WorkspaceDir "logs"
New-Item -ItemType Directory -Force -Path $WorkspaceDir, $ConfigDir, $logDir | Out-Null

$env:HEADROOM_WORKSPACE_DIR = $WorkspaceDir
$env:HEADROOM_CONFIG_DIR = $ConfigDir
if ($KompressBackend) { $env:HEADROOM_KOMPRESS_BACKEND = $KompressBackend }
if ($DisableStickyBeta) { $env:HEADROOM_BETA_HEADER_STICKY = "disabled" }

$args = @(
    "proxy",
    "--host", "127.0.0.1",
    "--port", $Port,
    "--mode", $Mode,
    "--memory",
    "--memory-project-root", $repoRoot,
    "--log-file", (Join-Path $logDir "proxy.jsonl")
)

if ($Budget -gt 0) { $args += @("--budget", $Budget) }
if ($NoOptimize) { $args += "--no-optimize" }
if ($NoCache) { $args += "--no-cache" }
if ($NoRateLimit) { $args += "--no-rate-limit" }
if ($Stateless) { $args += "--stateless" }

Push-Location $repoRoot
try { & $headroomExe @args }
finally { Pop-Location }
