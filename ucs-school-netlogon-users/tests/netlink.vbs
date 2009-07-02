Const DESKTOP = &H10&
Const FolderName = "Schulordner"

Set objShell = CreateObject("Shell.Application")
Set objFolder = objShell.Namespace(DESKTOP)
Set objFolderItem = objFolder.Self

FolderPath = objFolderItem.Path + "\" + FolderName

' Delete Folder
Set objFSO = CreateObject("Scripting.FileSystemObject")
If objFSO.FolderExists(FolderPath) Then
	objFSO.DeleteFolder(FolderPath)
End If

' Recreate Folder
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objFolder = objFSO.CreateFolder(FolderPath)


Set oWS = WScript.CreateObject("WScript.Shell")

sLinkFile = FolderPath+"\MyShortcut.LNK"

Set oLink = oWS.CreateShortcut(sLinkFile)

oLink.TargetPath = "\\anton\steuwer"
' oLink.Arguments = ""
' oLink.Description = "MyProgram"
' oLink.HotKey = "ALT+CTRL+F"
' oLink.IconLocation = "C:\Program Files\MyApp\MyProgram.EXE, 2"
' oLink.WindowStyle = "1"
' oLink.WorkingDirectory = "C:\Program Files\MyApp"
oLink.Save

' Set Readonly-Flag on Folder
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objFolder = objFSO.GetFolder(FolderPath)

