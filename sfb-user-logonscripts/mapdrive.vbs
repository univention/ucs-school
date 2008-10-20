'Set shares to be mapped 
 Software="\\cmgc-fp-003\software$" 
 Apps="\\cmgc-fp-001\applications" 
 'Call function for mapping drive 
 MapDrive "J:",Apps 
 MapDrive "S:",Software 

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


--------------- variante


MapDrive "H:", "\\SDDEU-APP", "\apps"





Set fso = WScript.CreateObject("Scripting.FileSystemObject")
Set WSHNetwork = WScript.CreateObject("WScript.Network")
 Set WSHShell = WScript.CreateObject("WScript.Shell")
 Set WshEnv = WshShell.Environment("Process")
 
 WinDir = WshEnv("windir")
 
 LogonServer = WshEnv("LogonServer")
 OSVer = WshEnv("OS")
 
 UserName = ""
 On Error Resume Next
 While UserName = ""
 UserName = WshNetwork.UserName
 Wend
 
 ComputerName = WshNetwork.ComputerName





Function MapDrive(Drive, Server, Share)
 
 Choice = vbNo
 ServerShare = Server & Share
 If fso.DriveExists(ServerShare) Then
 If fso.DriveExists(Drive) Then
 Set DriveObj = fso.GetDrive(Drive)
 if LCase(DriveObj.ShareName) <> LCase(ServerShare) Then
 if Not(AutoRemoveMap) And Not(Silent) Then
 Set DriveObj = fso.GetDrive(Drive)
 Message = "Drive " & ucase(Drive) & " is currently mapped to: "
 &_
 vbCRLF &_
 DriveObj.ShareName & TwoLines &_
 "Should this Drive be remapped to " &_
 Drive & ServerShare & "?" & TwoLines
 Choice = MsgBox(Message, vbYesNo + vbQuestion, BoxTitle)
 End If
 If (Choice = vbYes) or AutoRemoveMap Then
 WshNetwork.RemoveNetworkDrive Drive
 WshNetwork.MapNetworkDrive Drive, ServerShare , False
 End If
 End If
 Else
 WshNetwork.MapNetworkDrive Drive, ServerShare, False
 End If
 Else
 If Not Silent Then
 Message = "Mapping for drive " & UCase(Drive) & " to " &_
 ServerShare & " failed." & TwoLines & PleaseContact
 MsgBox Message, vbCritical, Boxtitle
 End If
 End If
 End Function