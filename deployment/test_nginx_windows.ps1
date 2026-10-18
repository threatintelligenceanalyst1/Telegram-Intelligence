# ==============================================================================
# Helper Script to Test Nginx Locally on Windows
# ==============================================================================

param (
    [string]$Action = "start"
)

$NginxDir = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\nginxinc.nginx_Microsoft.Winget.Source_8wekyb3d8bbwe\nginx-1.31.7"
$NginxExe = "$NginxDir\nginx.exe"
$ConfigFile = "$PSScriptRoot\nginx\nginx_windows_test.conf"

if ($Action -eq "stop") {
    Write-Host "[*] Stopping local Nginx..." -ForegroundColor Yellow
    Stop-Process -Name nginx -Force -ErrorAction SilentlyContinue
    Write-Host "[+] Nginx stopped successfully." -ForegroundColor Green
    return
}

if ($Action -eq "status") {
    $proc = Get-Process nginx -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "[+] Nginx is RUNNING (PID: $($proc[0].Id))" -ForegroundColor Green
    } else {
        Write-Host "[-] Nginx is NOT running." -ForegroundColor Red
    }
    return
}

# Default: Start
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  Starting Nginx on Windows (Port 80 -> Port 8000)" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# Stop any older instance first
Stop-Process -Name nginx -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

# Start Nginx in background
Start-Process -FilePath $NginxExe -ArgumentList "-p `"$NginxDir`" -c `"$ConfigFile`"" -WindowStyle Hidden

Start-Sleep -Seconds 1
$running = Get-Process nginx -ErrorAction SilentlyContinue

if ($running) {
    Write-Host "[+] Nginx is now running on http://localhost (Port 80)!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Try these tests in your browser or terminal:" -ForegroundColor White
    Write-Host "  1. Swagger Docs:  http://localhost/docs" -ForegroundColor Yellow
    Write-Host "  2. API Stats:     curl -H `"X-API-Key: YOUR_KEY`" http://localhost/api/v1/stats" -ForegroundColor Yellow
    Write-Host "  3. Darknet IOCs:  curl -H `"X-API-Key: YOUR_KEY`" http://localhost/api/v1/iocs?limit=5" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To stop Nginx later, run:" -ForegroundColor White
    Write-Host "  .\deployment\test_nginx_windows.ps1 -Action stop" -ForegroundColor Gray
} else {
    Write-Host "[-] Failed to start Nginx. Check logs at: $NginxDir\logs\error.log" -ForegroundColor Red
}
