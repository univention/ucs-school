dim quotaThreshold: quotaThreshold = 0.9
dim ldapsearchBaseDN : ldapsearchBaseDN = "dc=schule,dc=bremen,dc=de"



Dim objFSO, objDrive, username, quotaLimit, quotaUsed

Set WshShell = WScript.CreateObject("WScript.Shell") 
username = WshShell.ExpandEnvironmentStrings("%USERNAME%")
dim tmpdir : tmpdir = WshShell.ExpandEnvironmentStrings("%TMP%")
if tmpdir = "" Then
  tmpdir = WshShell.ExpandEnvironmentStrings("%TEMP%")
end if

dim LOGONSERVER
set shell = createobject("wscript.shell") 
LOGONSERVER = mid(shell.Environment("PROCESS")("LOGONSERVER"),3) 

Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objDrive = objFSO.GetDrive("\\" & LOGONSERVER & "\" & username )

quotaLimit = objDrive.TotalSize / 1024 / 1024
quotaUsed = (objDrive.TotalSize - objDrive.AvailableSpace) / 1024 / 1024
ratio = quotaUsed / quotaLimit

if (CSng(quotaThreshold) > CSng(ratio)) Then
  wscript.quit
end if

quotaLimit = Round(quotaLimit * 100)/100
quotaUsed = Round(quotaUsed * 100)/100

dim ldapsearchCmd : ldapsearchCmd = "ldapsearch.exe -x -LLL -h " & LOGONSERVER

dim userattrs: userattrs = RunExternalCmd(ldapsearchCmd & " -b " & ldapsearchBaseDN & " uid=" & username)
dim attrlist : attrlist = GetAttribute(userattrs,"cn")

for each name in attrlist
	realname = name
    next

Set file = objFSO.GetFile( "\\" & LOGONSERVER & "\netlogon\wichtig.gif")
file.Copy ( tmpdir & "\wichtig.gif")
set file = nothing

Set file = objFSO.GetFile( "\\" & LOGONSERVER & "\netlogon\clipboard.gif")
file.Copy ( tmpdir & "\clipboard.gif")
set file = nothing
set fso = nothing


cssstyle = "<html>" &_
"  <head>" &_
"    <style type=""text/css"">" &_
"<!-- " &_
"body, html{color:#000000; }" &_
"td{font-family: helvetica, impact, sans-serif;text-align:center}" &_
"h1{margin:15px 0;text-align:center;}" &_
" -->" &_
"</style>" &_
"  </head>" &_
"<body></body>" &_
"</html>"	

htmlbody = "<html>" &_
"  <head>" &_
"  </head>" &_
"  <body>" &_
"   <center>" &_
"    <table border=0 width=""80%"" bgcolor=""#A0A0A0"" cellspacing=5>" &_
"      <tr><td width=""20%""><img src=""TMPDIR/wichtig.gif"" width=""180"" height=""180"" alt=""wichtig""></td>" &_
"         <td valign=center><h1>Vorsicht, Speicherplatz bald &uuml;berschritten!</h1>" &_
"            REALNAME, dein eingetragener Speicherplatz hat sein Limit fast erreicht." &_
"         </td>" &_
"      </tr>" &_
"      <tr>" &_
"         <td width=""20%"">&nbsp;</td>" &_
"         <td><table bgcolor=#C0C0C0 border=0 cellspacing=8>" &_
"               <tr><td width=80 rowspan=2><img src=""TMPDIR/clipboard.gif"" width=""45"" height=""90"" alt=""clipboard""></td>" &_
"                   <td><b>Eingetragenes Limit:</b></td><td><b>QUOTALIMIT MB</b></td></tr>" &_
"               <tr><td><b>Momentan verwendet:</b></td><td><b>QUOTAUSED MB</b></td></tr>" &_
"             </table>" &_
"         </td>" &_
"      </tr>" &_
"	  <tr>" &_
"        <td width=""20%"">&nbsp;</td>" &_
"        <td valign=center>Um weitere Daten speichern zu k&ouml;nnen, solltest du nicht mehr ben&ouml;tigte Dateien l&ouml;schen.<br>&nbsp;<br>" &_
"		Erkundige dich bei deinem zust&auml;ndigen Fachlehrer, welche Dateien nicht mehr ben&ouml;tigt werden.</td>" &_
"	  </tr>" &_
"	  <tr>" &_
"        <td width=""20%"">&nbsp;</td>" &_
"        <td><hr></td>" &_
"	  </tr>" &_
"	  <tr>" &_
"        <td width=""20%"">&nbsp;</td>" &_
"        <td valign=center>Eine Erh&ouml;hung des Speichervolumens kann beim IT-Verantwortlichen eurer Schule beantragt werden." &_
"		  Informiere dazu deinen Fachlehrer.</td>" &_
"	  </tr>" &_
"	  <tr>" &_
"        <td width=""20%"">&nbsp;</td>" &_
"		<td><form action=""0"">" &_
"			<input type=""button"" value=""OK"" onclick=""javascript:window.close()"">" &_
"		</form></td>" &_
"	  </tr>" &_
"    </table>" &_
"   </center>" &_
"  </body>" &_
"</html>"

htmlbody = Replace(htmlbody, "REALNAME", realname)
htmlbody = Replace(htmlbody, "QUOTALIMIT", quotaLimit)
htmlbody = Replace(htmlbody, "QUOTAUSED", quotaUsed)
htmlbody = Replace(htmlbody, "TMPDIR", tmpdir)

Dim oIE, n
Set oIE = WScript.CreateObject("InternetExplorer.Application", "IEApp_")
With oIE
 .Navigate ("JavaScript:'" & cssstyle & "';" )
 .Visible = True
 .Toolbar = True
 .Statusbar = True
 .Fullscreen = True
 Do
 Loop While oIE.ReadyState<>4
.document.body.innerHTML = htmlbody
 WScript.Sleep(1800000)
End With
oIE.Quit
wscript.quit

		
Sub IEApp_onQuit ()
  WScript.Quit
End Sub


Function GetAttribute(ByVal attrlist, attrname)
  dim outval : outval = ""
  dim lines : lines = split(attrlist, vbCrLf)
  for each line in lines
     'wscript.echo "LINE: " & line
     if left(line, len(attrname) + 2) = attrname & ": " Then
        if len(outval) > 0 Then
	   outval = outval & vbCrLf
	End If
	outval = outval & mid(line, len(attrname)+3)
     End If
     next
  GetAttribute = split(outval, vbCrLf)
End Function
		

Function RunExternalCmd (ByVal cmd)
   Dim outp: outp = ""
   Dim sh: Set sh = CreateObject("WScript.Shell")
   Dim wsx: Set wsx = Sh.Exec(cmd)
   If wsx.ProcessID = 0 And wsx.Status = 1 Then
      ' (The Win98 version of VBScript does not detect WshShell.Exec errors)
      Err.Raise vbObjectError,,"WshShell.Exec failed."
   End If
   Do
      Dim Status: Status = wsx.Status
      outp = outp & wsx.StdOut.ReadAll() & wsx.StdErr.ReadAll()
      If Status <> 0 Then Exit Do
      WScript.Sleep 10
   Loop
   RunExternalCmd = outp
End Function

