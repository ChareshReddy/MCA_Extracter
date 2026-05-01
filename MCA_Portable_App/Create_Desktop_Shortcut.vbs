Set WshShell = CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")

Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

Set oShellLink = WshShell.CreateShortcut(strDesktop & "\MCA Data Extracter.lnk")
oShellLink.TargetPath = currentDir & "\Launch_App.vbs"
oShellLink.WorkingDirectory = currentDir
oShellLink.WindowStyle = 1
oShellLink.Description = "Launch MCA Data Extraction Engine"
oShellLink.IconLocation = "imageres.dll, 109"
oShellLink.Save

MsgBox "Desktop shortcut created successfully!" & vbCrLf & vbCrLf & "You can now launch the MCA Data Extracter directly from your Desktop.", 64, "Shortcut Created"
