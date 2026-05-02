@echo off
title MCA Extraction Engine
cd /d "%~dp0"

echo ===================================================
echo           MCA EXTRACTION ENGINE
echo ===================================================
echo.
:: VPN AUTOMATIC DETECTION
echo $connected = $false > "%temp%\vpncheck.ps1"
echo try { >> "%temp%\vpncheck.ps1"
echo     $vpn = Get-VpnConnection -ErrorAction SilentlyContinue ^| Where-Object { $_.ConnectionStatus -eq 'Connected' } >> "%temp%\vpncheck.ps1"
echo     if ($vpn) { $connected = $true } >> "%temp%\vpncheck.ps1"
echo } catch {} >> "%temp%\vpncheck.ps1"
echo $vpnKeywords = 'Proton^|WireGuard^|TUN^|TAP' >> "%temp%\vpncheck.ps1"
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

echo Starting engine...
echo (Please keep this window open while using the app)
echo.

:: Check and install requirements
echo Checking dependencies (this may take a minute on the very first run)...
python -m pip install -r "%~dp0requirements.txt" --quiet --disable-pip-version-check

:: Open browser with a slight delay
start /b cmd /c "timeout /t 5 /nobreak >nul && start http://localhost:8000"

:: Start the python app
python api.py

pause
