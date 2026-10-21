[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendRoot = Join-Path $ProjectRoot "backend"
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$BackendUrl = "http://127.0.0.1:8000/health"
$FrontendUrl = "http://127.0.0.1:3000"
$RunLogDirectory = Join-Path ([System.IO.Path]::GetTempPath()) "cre-underwriting"

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
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url $Url) {
            return
        }
        if ($Process.HasExited) {
            throw "$Name exited with code $($Process.ExitCode) before becoming ready at $Url.`nStandard output ($StdoutLog):`n$(Get-StartupLog $StdoutLog)`nStandard error ($StderrLog):`n$(Get-StartupLog $StderrLog)"
        }
        Start-Sleep -Seconds 1
    }
    throw "$Name did not become ready at $Url within 45 seconds. Standard output: $StdoutLog. Standard error: $StderrLog. Check the logs for the startup error."
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
        throw "Port 8000 is already in use but the underwriting API is not healthy. Run .\scripts\stop-local.ps1, then try again."
    }
    # Ensure Uvicorn imports this checkout's src/ package rather than a stale
    # backend distribution that may already be installed in the virtualenv.
    $backendProcess = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "backend.api.main:app", "--app-dir", "src", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $BackendRoot -WindowStyle Hidden -RedirectStandardOutput $BackendStdoutLog -RedirectStandardError $BackendStderrLog -PassThru
    Wait-ForUrl $BackendUrl "Backend" $backendProcess $BackendStdoutLog $BackendStderrLog
}

if (-not (Test-Url $FrontendUrl)) {
    if (Test-PortInUse 3000) {
        throw "Port 3000 is already in use but the frontend is not healthy. Run .\scripts\stop-local.ps1, then try again."
    }
    $frontendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev -- --hostname 127.0.0.1 --port 3000" -WorkingDirectory $FrontendRoot -WindowStyle Hidden -RedirectStandardOutput $FrontendStdoutLog -RedirectStandardError $FrontendStderrLog -PassThru
    Wait-ForUrl $FrontendUrl "Frontend" $frontendProcess $FrontendStdoutLog $FrontendStderrLog
}

Write-Host "CRE Underwriting App is ready at $FrontendUrl" -ForegroundColor Green
if (-not $NoBrowser) {
    Start-Process $FrontendUrl
}
