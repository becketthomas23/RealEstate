[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendRoot = Join-Path $ProjectRoot "backend"
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$BackendUrl = "http://127.0.0.1:8000/health"
$FrontendUrl = "http://localhost:3000"

function Test-Url([string]$Url) {
    $status = & curl.exe --silent --output NUL --write-out "%{http_code}" --max-time 2 $Url
    return $LASTEXITCODE -eq 0 -and $status -eq "200"
}

function Wait-ForUrl([string]$Url, [string]$Name) {
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url $Url) {
            return
        }
        Start-Sleep -Seconds 1
    }
    throw "$Name did not become ready at $Url. Check that its port is not already in use."
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

if (-not (Test-Url $BackendUrl)) {
    if (Test-PortInUse 8000) {
        throw "Port 8000 is already in use but the underwriting API is not healthy. Run .\scripts\stop-local.ps1, then try again."
    }
    Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "backend.api.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $BackendRoot -WindowStyle Hidden
    Wait-ForUrl $BackendUrl "Backend"
}

if (-not (Test-Url $FrontendUrl)) {
    if (Test-PortInUse 3000) {
        throw "Port 3000 is already in use but the frontend is not healthy. Run .\scripts\stop-local.ps1, then try again."
    }
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev -- --hostname 127.0.0.1 --port 3000" -WorkingDirectory $FrontendRoot -WindowStyle Hidden
    Wait-ForUrl $FrontendUrl "Frontend"
}

Write-Host "CRE Underwriting App is ready at $FrontendUrl" -ForegroundColor Green
if (-not $NoBrowser) {
    Start-Process $FrontendUrl
}
