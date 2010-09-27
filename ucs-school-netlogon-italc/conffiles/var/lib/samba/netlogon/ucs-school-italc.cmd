@%@BCWARNING=REM   @%@
REM ---
REM script copys teachers/systems iTALC public key to windows system to enable remote logins
echo Copying iTALC public key to local system
@!@
print 'copy /Y "%s" "%s"' % ( configRegistry.get('samba/netlogonscript/italc/key/public/serverpath', '%LOGONSERVER%\netlogon\italc\italc-key.pub'),
							  configRegistry.get('samba/netlogonscript/italc/key/public/localpath', 'C:\\Programme\\iTALC\\keys\\public\\teacher\\key') )
@!@
echo iTALC public key is installed and becomes active on next system reboot
