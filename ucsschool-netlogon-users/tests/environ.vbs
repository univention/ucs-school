'set WshShell = CreateObject("WScript.Shell")
'Use the methods of the object
'wscript.echo "Environment.item: "& WshShell.Environment.item("HOMEDRIVE")
'wscript.echo "ExpandEnvironmentStrings: "& WshShell.ExpandEnvironmentString


Set oShell = CreateObject("Wscript.Shell") 
strName = oShell.Environment("Process").Item("HOMEDRIVE") & oShell.Environment("Process").Item("HOMEPATH") 
wscript.echo strName


Const DESKTOP = &H10&
Const FolderName = "%s"

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

Set oShell = CreateObject("Wscript.Shell") 
homepath = oShell.Environment("Process").Item("HOMEDRIVE") & oShell.Environment("Process").Item("HOMEPATH")

Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = FolderPath + "\\Meine Dateien.LNK"

Set oLink = oWS.CreateShortcut(sLinkFile)

oLink.TargetPath = homepath
oLink.Save