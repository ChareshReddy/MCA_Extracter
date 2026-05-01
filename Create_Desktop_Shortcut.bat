@echo off
set SCRIPT_PATH=%~dp0Launch_MCA_Engine.vbs
set SHORTCUT_NAME=MCA Extraction Engine
set DESKTOP_PATH=%USERPROFILE%\Desktop

echo Creating desktop shortcut for MCA Extraction Engine...

powershell -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%DESKTOP_PATH%\%SHORTCUT_NAME%.lnk'); $s.TargetPath = '%SCRIPT_PATH%'; $s.WorkingDirectory = '%~dp0'; $s.Save()"

if %errorlevel% equ 0 (
    echo [SUCCESS] Shortcut created on your Desktop!
) else (
    echo [ERROR] Failed to create shortcut.
)
pause
