'#
'# Warning: This file is auto-generated and might be overwritten by
'#          univention-config-registry.
'#          Please edit the files in the following directory instead:
'# Warnung: Diese Datei wurde automatisch generiert und kann durch
'#          univention-config-registry ueberschrieben werden.
'#          Bitte bearbeiten Sie an Stelle dessen die Dateien in
'#          folgendem Verzeichnis:
'#
'#       /etc/univention/templates/files/var/lib/samba/netlogon/umc-distribution.vbs
'#
'#

@!@
path = configRegistry.get('umc/datadistribution/datadir/recipient','Unterrichtsmaterial')
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
If FSO.FolderExists( DRIVE & ":\" & DIRPATH ) = True Then
   Set MyShortcut = WSHShell.CreateShortcut(DesktopPath & "\" & DIRNAME & ".lnk")
   MyShortcut.TargetPath = WSHShell.ExpandEnvironmentStrings( DRIVE & ":\" & DIRPATH )
   MyShortcut.WorkingDirectory = WSHShell.ExpandEnvironmentStrings( DRIVE & ":\" & DIRPATH )
   MyShortcut.WindowStyle = 4
   MyShortcut.Save
End If
