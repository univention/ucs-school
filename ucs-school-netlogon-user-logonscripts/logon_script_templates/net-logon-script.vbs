Const DESKTOP = &H10&
Const FolderName = "{desktop_folder_name}"
Const HKEY_CURRENT_USER= &H80000001

Set objShell = CreateObject("Shell.Application")
Set objFolder = objShell.Namespace(DESKTOP)
Set objFolderItem = objFolder.Self
Set FileSysObj = WScript.CreateObject("Scripting.FileSystemObject")
Set WSHNetwork = WScript.CreateObject("WScript.Network")

FolderPath = objFolderItem.Path + "\" + FolderName

' Delete Folder
Set objFSO = CreateObject("Scripting.FileSystemObject")
If objFSO.FolderExists(FolderPath) Then
	objFSO.DeleteFolder(FolderPath)
End If

' Recreate Folder
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objFolder = objFSO.CreateFolder(FolderPath)

' Link to HOMEDRIVE
Set oShell = CreateObject("Wscript.Shell")
homepath = oShell.Environment("Process").Item("HOMEDRIVE") & oShell.Environment("Process").Item("HOMEPATH")

Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = FolderPath + "\{my_files_link_name}.LNK"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = homepath
oLink.IconLocation = "{my_files_link_icon}"
oLink.Save

Function SetMyShares(strPersonal)
	strKeyPath1="Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
	strKeyPath2="Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"

	strComputer = GetComputerName
	Set objReg = GetObject("winmgmts:{{impersonationLevel=impersonate}}!" & strComputer & "\root\default:StdRegProv")

	' Check if folder {myshares_name} exists
	Set fso = CreateObject("Scripting.FileSystemObject")
	If not (fso.FolderExists(strPersonal)) then
		ON ERROR RESUME NEXT
		Set f = fso.CreateFolder(strPersonal)
	End If

	intRet1= objReg.SetStringValue(HKEY_CURRENT_USER, strKeyPath1, "Personal", strPersonal)
	If intRet1 <> 0 Then
		Wscript.echo "Error: Setting Shell Folder Key Personal"
	End If

	intRet2= objReg.SetStringValue(HKEY_CURRENT_USER, strKeyPath2, "Personal", strPersonal)
	If intRet2 <> 0 Then
		Wscript.echo "Error: Setting User Shell Folder Key Personal"
	End If

	' Check if folder {mypictures_name} exists
	Set fso = CreateObject("Scripting.FileSystemObject")
	If not (fso.FolderExists(strPersonal & "\{mypictures_name}")) then
		ON ERROR RESUME NEXT
		Set f = fso.CreateFolder(strPersonal & "\{mypictures_name}")
	End If

	intRet3= objReg.SetStringValue(HKEY_CURRENT_USER, strKeyPath1, "My Pictures", strPersonal & "\{mypictures_name}")
	If intRet3 <> 0 Then
		Wscript.echo "Error: Setting Shell Folder Key Personal"
	End If

	intRet4= objReg.SetStringValue(HKEY_CURRENT_USER, strKeyPath2, "My Pictures", strPersonal & "\{mypictures_name}")
	If intRet4 <> 0 Then
		Wscript.echo "Error: Setting User Shell Folder Key Personal"
	End If
end function

Function MapDrive(Drive,Share)
	ON ERROR RESUME NEXT
	If FileSysObj.DriveExists(share)=True then
		if FileSysObj.DriveExists(Drive)=True then
			WSHNetwork.RemoveNetworkDrive Drive
		end if
	end if
	WSHNetwork.MapNetworkDrive Drive, Share
	If err.number >0 then
		msgbox "ERROR: " & err.description & vbcr & Drive & " " & share
		err.clear
	End if
end function

Function CreateDesktopIcon()
	Const HIDDEN = 2
	CONST SYSTEM = 4

	Set objShell = CreateObject("Shell.Application")
	Set FileSysObj = WScript.CreateObject("Scripting.FileSystemObject")

	DesktopIniPath = FolderPath + "\" + "desktop.ini"

	If (FileSysObj.FileExists(DesktopIniPath)) Then
		FileSysObj.DeleteFile DesktopIniPath, True
	End If

	Set DesktopIniFile = FileSysObj.CreateTextFile(DesktopIniPath, True, True)
	DesktopIniFile.WriteLine "[.ShellClassInfo]"
	DesktopIniFile.WriteLine "IconResource={desktop_folder_icon}"
	DesktopIniFile.Close

	Set objFile = FileSysObj.GetFile(DesktopIniPath)
	objFile.Attributes = objFile.Attributes OR HIDDEN
	Set objFile = FileSysObj.GetFolder(FolderPath)
	objFile.Attributes = objFile.Attributes OR SYSTEM
end function
