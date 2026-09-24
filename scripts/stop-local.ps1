[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

foreach ($Port in 3000, 8000) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $listener) {
        Stop-Process -Id $listener.OwningProcess -Force
        Write-Host "Stopped the local service using port $Port."
    }
}
