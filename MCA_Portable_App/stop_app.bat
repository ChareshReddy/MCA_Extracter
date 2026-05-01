@echo off
title Stop MCA Engine
echo ===================================================
echo           MCA EXTRACTION ENGINE - SHUTDOWN
echo ===================================================
echo.
echo Force stopping all background scraper processes...
taskkill /F /IM python.exe /T >nul 2>&1
echo.
echo Server successfully stopped!
echo You can now close this window.
pause
