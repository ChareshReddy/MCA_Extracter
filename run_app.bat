@echo off
:: Set directory to where the batch file is located
cd /d "%~dp0"

echo ===================================================
echo           APP LAUNCHER: BACKEND ^& FRONTEND
echo ===================================================

:: VPN AUTOMATIC DETECTION
echo $connected = $false > "%temp%\vpncheck.ps1"
echo try { >> "%temp%\vpncheck.ps1"
echo     $vpn = Get-VpnConnection -ErrorAction SilentlyContinue ^| Where-Object { $_.ConnectionStatus -eq 'Connected' } >> "%temp%\vpncheck.ps1"
echo     if ($vpn) { $connected = $true } >> "%temp%\vpncheck.ps1"
echo } catch {} >> "%temp%\vpncheck.ps1"
echo $vpnKeywords = 'VPN^|TAP^|TUN^|WireGuard^|PANGP^|Cisco^|AnyConnect^|Pulse^|Fortinet^|Proton^|Express^|Nord^|Surfshark^|CyberGhost^|Windscribe^|PIA^|TunnelBear^|Mullvad^|Hide.me^|Vypr^|TorGuard^|IVPN' >> "%temp%\vpncheck.ps1"
echo try { >> "%temp%\vpncheck.ps1"
echo     $adapters = Get-NetAdapter -ErrorAction SilentlyContinue ^| Where-Object { $_.Status -eq 'Up' -and ($_.InterfaceDescription -match $vpnKeywords -or $_.Name -match $vpnKeywords) } >> "%temp%\vpncheck.ps1"
echo     if ($adapters) { $connected = $true } >> "%temp%\vpncheck.ps1"
echo } catch {} >> "%temp%\vpncheck.ps1"
echo if ($connected) { exit 0 } else { exit 1 } >> "%temp%\vpncheck.ps1"

powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%temp%\vpncheck.ps1"
if %errorlevel% neq 0 (
    echo Set objArgs = WScript.Arguments > "%temp%\vpnwarn.vbs"
    echo MsgBox "NO SECURE VPN CONNECTION DETECTED!" ^& vbCrLf ^& vbCrLf ^& "The extraction engine requires an active VPN connection to run. Please connect to your VPN client and try again.", 48, "VPN Required" >> "%temp%\vpnwarn.vbs"
    cscript //nologo "%temp%\vpnwarn.vbs"
    del "%temp%\vpnwarn.vbs"
    del "%temp%\vpncheck.ps1"
    exit /b
)
del "%temp%\vpncheck.ps1"

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)


:: 3. Open Browser (with a 5-second delay to let the server start)
start /b cmd /c "timeout /t 5 /nobreak >nul && start http://localhost:8000"

:: 4. Start Application
:: We run this directly. When run via VBScript (hidden), this stays hidden.
python api.py

exit /b
