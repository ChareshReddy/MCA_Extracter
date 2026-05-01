@echo off
cd /d "%~dp0"

echo ===================================================
echo           STOPPING APPLICATION PROCESSES
echo ===================================================

echo.
echo Stopping Python backend processes...
taskkill /F /IM python.exe /T 2>nul
if %errorlevel% equ 0 (
    echo [SUCCESS] Python processes terminated.
) else (
    echo [INFO] No running python processes found.
)

echo.
echo Stopping Node.js/Frontend processes...
taskkill /F /IM node.exe /T 2>nul
if %errorlevel% equ 0 (
    echo [SUCCESS] Node.js processes terminated.
) else (
    echo [INFO] No running node processes found.
)

echo.
echo ===================================================
echo Application stopped successfully.
echo ===================================================
pause
