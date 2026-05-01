@echo off
echo ===================================================
echo       MCA ENGINE: BUILDING STANDALONE APP
echo ===================================================
echo.
echo [1/3] Cleaning previous builds...
if exist "dist_app" rmdir /s /q "dist_app"
if exist "build" rmdir /s /q "build"
if exist "MCA_Extraction_Engine.spec" del /q "MCA_Extraction_Engine.spec"

echo.
echo [2/3] Running PyInstaller...
:: --noconsole: Hides the terminal window
:: --add-data: Includes the frontend files
:: --name: Sets the output filename
pyinstaller --noconsole ^
    --name "MCA_Extraction_Engine" ^
    --add-data "frontend/dist;frontend/dist" ^
    --add-data "requirements.txt;." ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols" ^
    --hidden-import "uvicorn.protocols.http" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "uvicorn.protocols.websockets" ^
    --hidden-import "uvicorn.protocols.websockets.auto" ^
    --hidden-import "uvicorn.lifespan" ^
    --hidden-import "uvicorn.lifespan.on" ^
    api.py

echo.
echo [3/3] Finalizing package...
:: Move the output to a cleaner folder
mkdir "dist_app"
move "dist\MCA_Extraction_Engine" "dist_app\"

:: Create empty input/output folders in the final package
mkdir "dist_app\MCA_Extraction_Engine\input"
mkdir "dist_app\MCA_Extraction_Engine\output"

echo.
echo ===================================================
echo [SUCCESS] Standalone app created in 'dist_app' folder!
echo You can send the entire 'dist_app' folder to the client.
echo They only need to run 'MCA_Extraction_Engine.exe' inside it.
echo ===================================================
pause
