' FirefoxADM Shutdown 0.4
' 2004/2005 Mark Sammons
' Support for Wow6432 and updated file locations by Arvid Requate <requate@univention.de>, 2013
' See http://kb.mozillazine.org/Locking_preferences
' And http://mike.kaply.com/2012/08/01/major-change-setting-default-preferences-for-firefox-14/

' create shell instance
set WshShell = WScript.CreateObject("WScript.Shell")

' create file object instances
set fso = CreateObject("Scripting.FileSystemObject")

' variables I'll be needing later
Const ForReading = 1, ForWriting = 2, ForAppending = 8
Dim FirefoxProfilePath, FirefoxPrefsFile, FirefoxProfileFolder, FirefoxProfiles
Dim FirefoxFolder, PrefsFile
Dim ParsePrefsFile, ParseOutPrefsFile
Dim FolderCreate, FirefoxProfileIniFile, FirefoxEmptyPrefsFile
' and this list needed for each feature
Dim HomePageKey, SearchEngineKey, ImageResizeKey, ProxyKey, ProxyURLKey
Dim HTTPKey, HTTPPortKey, SSLKey, SSLPortKey, FTPKey, FTPPortKey
Dim GopherKey, GopherPortKey, SOCKSKey, SOCKSPortKey, SOCKSVersionKey, ProxyExceptionsKey, ExceptionSplit
Dim FirefoxUseIEKey, IESettingFile, ParseFileLine, ParseSplitLine, ParseSplitSetting, SameProxy
Dim DefaultsPreferencesDirectory, LocalSettingsFile, MozillaCfgFile, ProgramFilesDir

on error resume next 

set EnVar = Wshshell.environment("Process")

' Files To Use
FirefoxUseRegLoc = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxUseRegLoc")
if FirefoxUseRegLoc = "yes" then
	' get location
	FirefoxVersion = WshShell.regread("HKLM\Software\Mozilla\Mozilla Firefox\CurrentVersion")

	' if can't find, try amd64
	if FirefoxVersion <> "" then
		FirefoxFilePath = WshShell.regread("HKLM\Software\Mozilla\Mozilla Firefox\" & FirefoxVersion & "\Main\Install Directory")
	else
		FirefoxVersion = WshShell.regread("HKLM\Software\Wow6432Node\Mozilla\Mozilla Firefox\CurrentVersion")
		FirefoxFilePath = WshShell.regread("HKLM\Software\Wow6432Node\Mozilla\Mozilla Firefox\" & FirefoxVersion & "\Main\Install Directory")
	end if

	' if can't find, use default
	if FirefoxFilePath = "" then
		ProgramFilesDir = EnVar("ProgramFiles(x86)")
		if ProgramFilesDir = "" then
			ProgramFilesDir = EnVar("ProgramFiles")
		end if
		FirefoxFilePath = ProgramFilesDir & "\Mozilla Firefox"
	end if
else
	ProgramFilesDir = EnVar("ProgramFiles(x86)")
	if ProgramFilesDir = "" then
		ProgramFilesDir = EnVar("ProgramFiles")
	end if
	FirefoxFilePath = ProgramFilesDir & "\Mozilla Firefox"
end if

' set paths
MozillaCfgFile = FirefoxFilePath & "\mozilla.cfg"
DefaultsPreferencesDirectory = FirefoxFilePath & "\defaults\preferences"
LocalSettingsFile = DefaultsPreferencesDirectory & "\local-settings.js"
' probably legacy:
FirfoxPrefCallsFile = FirefoxFilePath & "\defaults\autoconfig\prefcalls.js"
FirefoxAllJsFile = FirefoxFilePath & "\greprefs\all.js"
FirefoxXpinstallJsFile = FirefoxFilePath & "\greprefs\xpinstall.js"
FirefoxBrowserconfigPropertiesFile = FirefoxFilePath & "\browserconfig.properties"

Dim KeywordList
KeywordList = Array(_
"browser.startup.homepage", _
"browser.enable_automatic_image_resizing", _
"network.proxy.type", _
"network.proxy.autoconfig_url", _
"network.proxy.http", _
"network.proxy.http_port", _
"network.proxy.ssl", _
"network.proxy.ssl_port", _
"network.proxy.ftp", _
"network.proxy.ftp_port", _
"network.proxy.gopher", _
"network.proxy.gopher_port", _
"network.proxy.socks", _
"network.proxy.socks_port", _
"network.proxy.socks_version", _
"network.proxy.no_proxies_on", _
"browser.cache.disk.capacity", _
"browser.cache.disk_cache_ssl", _
"browser.shell.checkDefaultBrowser", _
"xpinstall.enabled", _
"app.update.autoUpdateEnabled", _
"app.update.enabled", _
"security.enable_java", _
"javascript.enabled", _
"security.enable_ssl2", _
"security.enable_ssl3", _
"security.enable_tls", _
"network.enableIDN", _
"extensions.update.autoUpdateEnabled", _
"extensions.update.autoUpdate", _
"extensions.update.enabled", _
"accessibility.typeaheadfind", _
"signon.rememberSignons", _
"network.prefetch-next", _
"security.checkloaduri", _
"accessibility.browsewithcaret", _
"network.cookie.cookieBehavior", _
"network.cookie.lifetimePolicy", _
"network.cookie.lifetime.days" )

' Wipe out all settings
if fso.FileExists(MozillaCfgFile) then
	RemoveCurrentPrefsFromMozillaCfgFile(KeywordList)
else
	if fso.FileExists(FirefoxPrefCallsFile) then
		RemoveCurrentPrefsFromPrefCallsFile(KeywordList)
	end if
end if

Function RemoveCurrentPrefsFromMozillaCfgFile(removeSettingList)
	Set ParseMozillaCfgFile = fso.OpenTextFile(MozillaCfgFile, ForReading)

	' Get file content into an array:
	Dim aContents
	aContents = Split(ParseMozillaCfgFile.ReadAll, vbCrLf)

	ParseMozillaCfgFile.Close
	set ParseMozillaCfgFile = Nothing

	' Parse Back In to mozilla.cfg file

	For Each removeSetting in removeSettingList
		aContents = Filter(aContents, chr(34) & removeSetting & chr(34), False, vbTextCompare)
	Next

	' Overwrite the old file with the new file,
	Set ParseOutMozillaCfgFile = fso.OpenTextFile(MozillaCfgFile, ForWriting)
	ParseOutMozillaCfgFile.Write Join(aContents, vbCrLf)
	ParseOutMozillaCfgFile.Close
End Function

Function RemoveCurrentPrefsFromPrefCallsFile(removeSettingList)
	Set ParsePrefCallsFile = fso.OpenTextFile(FirefoxPrefCallsFile, ForReading)

	' Get file content into an array:
	Dim aContents
	aContents = Split(ParsePrefCallsFile.ReadAll, vbCrLf)

	ParsePrefCallsFile.Close
	set ParsePrefCallsFile = Nothing

	' Parse Back In to PrefCalls.js file

	For Each removeSetting in removeSettingList
		aContents = Filter(aContents, chr(34) & removeSetting & chr(34), False, vbTextCompare)
	Next

	' Overwrite the old file with the new file,
	Set ParseOutPrefCallsFile = fso.OpenTextFile(FirefoxPrefCallsFile, ForWriting)
	ParseOutPrefCallsFile.Write Join(aContents, vbCrLf)
	ParseOutPrefCallsFile.Close
End Function
