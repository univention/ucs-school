@%@BCWARNING='# @%@

@!@
path = configRegistry.get('ucsschool/datadistribution/datadir/recipient','Unterrichtsmaterial')
dirname = path
if '/' in path:
    dirname = path.rsplit('/',1)[1]
    path = path.replace('/','\\')

print 'DIRNAME = "%s"' % dirname
print 'DIRPATH = "%s"' % path
print 'DRIVE = "%s"' % configRegistry.get('samba/homedirletter','I')
@!@

Dim WSHShell
Set WSHShell = WScript.CreateObject("WScript.Shell")
Dim MyShortcut, MyDesktop, DesktopPath
DesktopPath = WSHShell.SpecialFolders("Desktop")

Set FSO = CreateObject("scripting.filesystemobject")
If FSO.FolderExists( DRIVE & ":\" & DIRPATH ) = False Then
   Set objFolder = FSO.CreateFolder( DRIVE & ":\" & DIRPATH )
End If
If FSO.FolderExists( DRIVE & ":\" & DIRPATH ) = True Then
   Set MyShortcut = WSHShell.CreateShortcut(DesktopPath & "\" & DIRNAME & ".lnk")
   MyShortcut.TargetPath = WSHShell.ExpandEnvironmentStrings( DRIVE & ":\" & DIRPATH )
   MyShortcut.WorkingDirectory = WSHShell.ExpandEnvironmentStrings( DRIVE & ":\" & DIRPATH )
   MyShortcut.WindowStyle = 4
   MyShortcut.Save
End If
