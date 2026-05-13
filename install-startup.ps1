$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\LENOVO\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\bookmark-manager.lnk")
$Shortcut.TargetPath = "C:\Python314\pythonw.exe"
$Shortcut.Arguments = "C:\Users\LENOVO\Desktop\paper_writting\bookmark-manager\run.py"
$Shortcut.WorkingDirectory = "C:\Users\LENOVO\Desktop\paper_writting\bookmark-manager"
$Shortcut.WindowStyle = 7
$Shortcut.Description = "Collection Manager"
$Shortcut.Save()
Write-Host "done"
