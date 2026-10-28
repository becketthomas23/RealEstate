[CmdletBinding()]
param(
    [switch]$NoBrowser,
    # Start without the sign-in screen (developer convenience). The default
    # enables sign-in with a demo administrator so the app behaves as deployed.
    [switch]$OpenAccess
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendRoot = Join-Path $ProjectRoot "backend"
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$BackendUrl = "http://127.0.0.1:8000/health"
$FrontendUrl = "http://127.0.0.1:3000"
$RunLogDirectory = Join-Path ([System.IO.Path]::GetTempPath()) "deal-scope"

# Demo sign-in. Override any of these in the environment before launching.
$DemoAdminEmail = if ($env:DEALSCOPE_ADMIN_EMAIL) { $env:DEALSCOPE_ADMIN_EMAIL } else { "admin@dealscope.local" }
$DemoAdminPassword = if ($env:DEALSCOPE_ADMIN_PASSWORD) { $env:DEALSCOPE_ADMIN_PASSWORD } else { "dealscope-demo" }
$DemoAdminName = if ($env:DEALSCOPE_ADMIN_NAME) { $env:DEALSCOPE_ADMIN_NAME } else { "Demo Administrator" }

New-Item -ItemType Directory -Force -Path $RunLogDirectory | Out-Null
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$BackendStdoutLog = Join-Path $RunLogDirectory "backend-$RunId.stdout.log"
$BackendStderrLog = Join-Path $RunLogDirectory "backend-$RunId.stderr.log"
$FrontendStdoutLog = Join-Path $RunLogDirectory "frontend-$RunId.stdout.log"
$FrontendStderrLog = Join-Path $RunLogDirectory "frontend-$RunId.stderr.log"

function Test-Url([string]$Url) {
    $status = & curl.exe --silent --output NUL --write-out "%{http_code}" --max-time 2 $Url
    return $LASTEXITCODE -eq 0 -and $status -eq "200"
}

function Get-StartupLog([string]$Path) {
    if (-not (Test-Path $Path)) {
        return "No log was written."
    }

    $content = Get-Content -Raw $Path
    if ([string]::IsNullOrWhiteSpace($content)) {
        return "The log is empty."
    }

    return $content.Trim()
}

function Wait-ForUrl([string]$Url, [string]$Name, [System.Diagnostics.Process]$Process, [string]$StdoutLog, [string]$StderrLog) {
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url $Url) {
            return
        }
        if ($Process.HasExited) {
            throw "$Name exited with code $($Process.ExitCode) before becoming ready at $Url.`nStandard output ($StdoutLog):`n$(Get-StartupLog $StdoutLog)`nStandard error ($StderrLog):`n$(Get-StartupLog $StderrLog)"
        }
        Start-Sleep -Seconds 1
    }
    throw "$Name did not become ready at $Url within 60 seconds. Standard output: $StdoutLog. Standard error: $StderrLog. Check the logs for the startup error."
}

function Test-PortInUse([int]$Port) {
    return $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

$Python = Join-Path $BackendRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Backend dependencies are not installed. Run 'cd backend; uv sync' once, then run this launcher again."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js/npm is required to run the frontend. Install Node.js, then run this launcher again."
}
if (-not (Test-Path (Join-Path $FrontendRoot "node_modules\next\package.json"))) {
    throw "Frontend dependencies are not installed. Run 'cd frontend; npm ci' once, then run this launcher again."
}

if (-not (Test-Url $BackendUrl)) {
    if (Test-PortInUse 8000) {
        throw "Port 8000 is already in use but the Deal Scope API is not healthy. Run .\scripts\stop-local.ps1, then try again."
    }
    if ($OpenAccess) {
        $env:APP_REQUIRE_AUTH = "false"
    } else {
        $env:APP_REQUIRE_AUTH = "true"
        if (-not $env:APP_SESSION_SECRET) {
            # A fresh secret per launch signs the session cookie; signing out
            # happens automatically when the service restarts.
            $env:APP_SESSION_SECRET = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
        }
        $env:APP_SESSION_COOKIE_SECURE = "false"
        $env:APP_ADMIN_EMAIL = $DemoAdminEmail
        $env:APP_ADMIN_PASSWORD = $DemoAdminPassword
        $env:APP_ADMIN_NAME = $DemoAdminName
    }
    # Ensure Uvicorn imports this checkout's src/ package rather than a stale
    # backend distribution that may already be installed in the virtualenv.
    $backendProcess = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "backend.api.main:app", "--app-dir", "src", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $BackendRoot -WindowStyle Hidden -RedirectStandardOutput $BackendStdoutLog -RedirectStandardError $BackendStderrLog -PassThru
    Wait-ForUrl $BackendUrl "Backend" $backendProcess $BackendStdoutLog $BackendStderrLog
}

if (-not (Test-Url $FrontendUrl)) {
    if (Test-PortInUse 3000) {
        throw "Port 3000 is already in use but the Deal Scope frontend is not healthy. Run .\scripts\stop-local.ps1, then try again."
    }
    $frontendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev -- --hostname 127.0.0.1 --port 3000" -WorkingDirectory $FrontendRoot -WindowStyle Hidden -RedirectStandardOutput $FrontendStdoutLog -RedirectStandardError $FrontendStderrLog -PassThru
    Wait-ForUrl $FrontendUrl "Frontend" $frontendProcess $FrontendStdoutLog $FrontendStderrLog
}

Write-Host "Deal Scope is ready at $FrontendUrl" -ForegroundColor Green
if (-not $OpenAccess) {
    Write-Host "Sign in with $DemoAdminEmail / $DemoAdminPassword (first launch creates this administrator; change it under Team and access)." -ForegroundColor Cyan
}
Write-Host "Demo kit: .\demo\ holds the mock offering memorandum and the Excel import for Maple Street Apartments." -ForegroundColor Gray
if (-not $NoBrowser) {
    Start-Process $FrontendUrl
}
