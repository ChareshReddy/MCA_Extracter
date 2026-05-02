npm run build
cmd.exe /c "rmdir /s /q "..\MCA_Portable_App\frontend\dist\assets""
cmd.exe /c "xcopy /s /e /y dist "..\MCA_Portable_App\frontend\dist\""
