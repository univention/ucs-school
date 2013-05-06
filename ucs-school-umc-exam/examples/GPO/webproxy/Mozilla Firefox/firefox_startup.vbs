' FirefoxADM 0.5.9.3
' 2004/2005/2008/2009 Mark Sammons
' URL Security check code by Michael Morandi, 2005
' Delete Private Data Cookies, Delete Private Data Offline Websites, Delete Private Data Passwords, Show SSL Domain Icon,
' Use Download Directory, Replace Certificates for all User Profiles code by Florian Baenziger, 2009
' Suppression of Firefox update page by Nathan Przybyszewski, 2009
' Support for Wow6432 and updated file locations by Arvid Requate <requate@univention.de>, 2013
' See http://kb.mozillazine.org/Locking_preferences
' And http://mike.kaply.com/2012/08/01/major-change-setting-default-preferences-for-firefox-14/

' create shell instance
set WshShell = WScript.CreateObject("WScript.Shell")

' create file object instances
set fso = CreateObject("Scripting.FileSystemObject")

' variables I'll be needing later
Const ForReading = 1, ForWriting = 2, ForAppending = 8
Dim FirefoxProfilePath, FirefoxPrefCallsFile, FirefoxProfileFolder, FirefoxProfiles
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

If Not fso.FolderExists(FirefoxFilePath) Then
	MsgBox("firefox_startup.vbs: Firefox directory not found: " & FirefoxFilePath)
	WScript.Quit
End If

' set paths
MozillaCfgFile = FirefoxFilePath & "\mozilla.cfg"
'' If the defaults\pref does not work any more see also http://mike.kaply.com/2012/08/01/major-change-setting-default-preferences-for-firefox-14/
DefaultsPreferencesDirectory = FirefoxFilePath & "\defaults\pref"
LocalSettingsFile = DefaultsPreferencesDirectory & "\local-settings.js"
' probably legacy paths:
FirefoxPrefCallsFile = FirefoxFilePath & "\defaults\autoconfig\prefcalls.js"
FirefoxAllJsFile = FirefoxFilePath & "\greprefs\all.js"
FirefoxXpinstallJsFile = FirefoxFilePath & "\greprefs\xpinstall.js"
FirefoxBrowserconfigPropertiesFile = FirefoxFilePath & "\browserconfig.properties"

If Not fso.FolderExists(DefaultsPreferencesDirectory) Then
	fso.CreateFolder(DefaultsPreferencesDirectory)
End If

' check for the Netscape locking file
if fso.FileExists(MozillaCfgFile) then
	' do nothing
else
	' create locking file
	Set MozillaCfgFileSet = fso.OpenTextFile(MozillaCfgFile, ForWriting, True)
  	MozillaCfgFileSet.Write("//")
	MozillaCfgFileSet.Close
end if

RemoveMozillaCfgFileInclude()

' insert mozilla.cfg locking include
Set LocalSettingsFileSet = fso.OpenTextFile(LocalSettingsFile, ForAppending, True)
LocalSettingsFileSet.Write(vbCrLf & "pref(" & chr(34) & "general.config.obscure_value" & chr(34) & "," & 0 & ");")
LocalSettingsFileSet.Write(vbCrLf & "pref(" & chr(34) & "general.config.filename" & chr(34) & "," & chr(34) & "mozilla.cfg" & chr(34) & ");")
LocalSettingsFileSet.Close


'  ------------------
'  Begin the Settings
'  ------------------


' homepage setting
if FirefoxUseIEKey <> "1" then 
	HomePageTypeKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxHomepageType")
	HomePageKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxHomepage")
	HomePagePageKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxHomepagePage")
end if
if HomePageKey <> "" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.startup.homepage")
	if HomePageTypeKey = "default" then
		SetDefaultHomePage(HomePageKey)
	else
		set HomePageSet = AppendPrefsToMozillaCfgFile("browser.startup.homepage", chr(34) & HomePageKey & chr(34))
	end if
end if
if HomePagePageKey <> "" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.startup.page")
	if HomePageTypeKey = "default" then
		set HomePagePageSet = AppendDefaultToMozillaCfgFile("browser.startup.page", HomePagePageKey)
	else
		set HomePagePageSet = AppendPrefsToMozillaCfgFile("browser.startup.page", HomePagePageKey)
	end if
end if


' Automatic Image Resizing
ImageResizeTypeKey = WshShell.regread("HKLM\Software\Policies\Firefox\ImageResizeType")
ImageResizeKey = WshShell.regread("HKLM\Software\Policies\Firefox\ImageResize")
if ImageResizeKey <> "" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.enable_automatic_image_resizing")
	if ImageResizeTypeKey = "default" then
		RemovePrefFromLocalConfig("browser.enable_automatic_image_resizing")
		if ImageResizeKey = "0" then
			set SearchEngineSet = AppendDefaultToMozillaCfgFile("browser.enable_automatic_image_resizing", "false")
		else
			set SearchEngineSet = AppendDefaultToMozillaCfgFile("browser.enable_automatic_image_resizing", "true")
		end if
	else
		if ImageResizeKey = "0" then
			set SearchEngineSet = AppendPrefsToMozillaCfgFile("browser.enable_automatic_image_resizing", "false")
		else
			set SearchEngineSet = AppendPrefsToMozillaCfgFile("browser.enable_automatic_image_resizing", "true")
		end if
	end if
end if
		

' Proxy Settings
FirefoxProxyType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxProxyType")
ProxyKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxProxy")
ProxyURLKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxAutoProxyURL")
HTTPKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxManualHTTP")
HTTPPortKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxManualHTTPPort")
SSLKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxManualSSL")
SSLPortKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxManualSSLPort")
FTPKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxManualFTP")
FTPPortKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxManualFTPPort")
GopherKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxManualGopher")
GopherPortKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxManualGopherPort")
SOCKSKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxManualSOCKS")
SOCKSPortKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxManualSOCKSPort")
ProxyExceptionsKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxProxyExceptions")
if ProxyKey <> "" then
	SOCKSVersionKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxManualSOCKSVersion")
	removeCurrentPrefsFromFile("network.proxy.type")
	removeCurrentPrefsFromFile("network.proxy.autoconfig_url")
	removeCurrentPrefsFromFile("network.proxy.http")
	removeCurrentPrefsFromFile("network.proxy.http_port")
	removeCurrentPrefsFromFile("network.proxy.ssl")
	removeCurrentPrefsFromFile("network.proxy.ssl_port")
	removeCurrentPrefsFromFile("network.proxy.ftp")
	removeCurrentPrefsFromFile("network.proxy.ftp_port")
	removeCurrentPrefsFromFile("network.proxy.gopher")
	removeCurrentPrefsFromFile("network.proxy.gopher_port")
	removeCurrentPrefsFromFile("network.proxy.socks")
	removeCurrentPrefsFromFile("network.proxy.socks_port")
	removeCurrentPrefsFromFile("network.proxy.socks_version")
	removeCurrentPrefsFromFile("network.proxy.no_proxies_on")
	if FirefoxProxyType = "default" then
		RemovePrefFromAllJs("network.proxy.type")
		RemovePrefFromAllJs("network.proxy.autoconfig_url")
		RemovePrefFromAllJs("network.proxy.http")
		RemovePrefFromAllJs("network.proxy.http_port")
		RemovePrefFromAllJs("network.proxy.ssl")
		RemovePrefFromAllJs("network.proxy.ssl_port")
		RemovePrefFromAllJs("network.proxy.ftp")
		RemovePrefFromAllJs("network.proxy.ftp_port")
		RemovePrefFromAllJs("network.proxy.gopher")
		RemovePrefFromAllJs("network.proxy.gopher_port")
		RemovePrefFromAllJs("network.proxy.socks_port")
		RemovePrefFromAllJs("network.proxy.socks_version")
		RemovePrefFromAllJs("network.proxy.no_proxies_on")
		if ProxyURLKey <> "" then
			set ProxyURLSet = AppendDefaultToMozillaCfgFile("network.proxy.autoconfig_url", chr(34) & ProxyURLKey & chr(34))
		end if
		if HTTPKey <> "" then
			set HTTPSet = AppendDefaultToMozillaCfgFile("network.proxy.http", chr(34) & HTTPKey & chr(34))
			HTTPSet = AppendDefaultToMozillaCfgFile("network.proxy.http_port", HTTPPortKey)
		end if
		if SSLKey <> "" then
			set SSLSet = AppendDefaultToMozillaCfgFile("network.proxy.ssl", chr(34) & SSLKey & chr(34))
			SSLSet = AppendDefaultToMozillaCfgFile("network.proxy.ssl_port", SSLPortKey)
		end if
		if FTPKey <> "" then
			set FTPSet = AppendDefaultToMozillaCfgFile("network.proxy.ftp", chr(34) & FTPKey & chr(34))
			FTPSet = AppendDefaultToMozillaCfgFile("network.proxy.ftp_port", FTPPortKey)
		end if
		if GopherKey <> "" then
			set GopherSet = AppendDefaultToMozillaCfgFile("network.proxy.gopher", chr(34) & GopherKey & chr(34))
			GopherSet = AppendDefaultToMozillaCfgFile("network.proxy.gopher_port", GopherPortKey)
		end if
		if SOCKSKey <> "" then
			set SOCKSSet = AppendDefaultToMozillaCfgFile("network.proxy.socks", chr(34) & SOCKSKey & chr(34))
			SOCKSSet = AppendDefaultToMozillaCfgFile("network.proxy.socks_port", SOCKSPortKey)
			SOCKSSet = AppendDefaultToMozillaCfgFile("network.proxy.socks_version", SOCKSVersionKey)
		end if
		if ProxyExceptionsKey <> "localhost, 127.0.0.1" or ProxyExceptions <> "" then
			set ExceptionsSet = AppendDefaultToMozillaCfgFile("network.proxy.no_proxies_on", chr(34) & ProxyExceptionsKey & chr(34))
		Elseif ProxyExceptionsKey = "localhost, 127.0.0.1" then
			set ExceptionsSet = AppendDefaultToMozillaCfgFile("network.proxy.no_proxies_on", chr(34) & ProxyExceptionsKey & chr(34))
		end if
		set ProxySet = AppendDefaultToMozillaCfgFile("network.proxy.type", ProxyKey)
	else
		if ProxyURLKey <> "" then
			set ProxyURLSet = AppendPrefsToMozillaCfgFile("network.proxy.autoconfig_url", chr(34) & ProxyURLKey & chr(34))
		end if
		if HTTPKey <> "" then
			set HTTPSet = AppendPrefsToMozillaCfgFile("network.proxy.http", chr(34) & HTTPKey & chr(34))
			HTTPSet = AppendPrefsToMozillaCfgFile("network.proxy.http_port", HTTPPortKey)
		end if
		if SSLKey <> "" then
			set SSLSet = AppendPrefsToMozillaCfgFile("network.proxy.ssl", chr(34) & SSLKey & chr(34))
			SSLSet = AppendPrefsToMozillaCfgFile("network.proxy.ssl_port", SSLPortKey)
		end if
		if FTPKey <> "" then
			set FTPSet = AppendPrefsToMozillaCfgFile("network.proxy.ftp", chr(34) & FTPKey & chr(34))
			FTPSet = AppendPrefsToMozillaCfgFile("network.proxy.ftp_port", FTPPortKey)
		end if
		if GopherKey <> "" then
			set GopherSet = AppendPrefsToMozillaCfgFile("network.proxy.gopher", chr(34) & GopherKey & chr(34))
			GopherSet = AppendPrefsToMozillaCfgFile("network.proxy.gopher_port", GopherPortKey)
		end if
		if SOCKSKey <> "" then
			set SOCKSSet = AppendPrefsToMozillaCfgFile("network.proxy.socks", chr(34) & SOCKSKey & chr(34))
			SOCKSSet = AppendPrefsToMozillaCfgFile("network.proxy.socks_port", SOCKSPortKey)
			SOCKSSet = AppendPrefsToMozillaCfgFile("network.proxy.socks_version", SOCKSVersionKey)
		end if
		if ProxyExceptionsKey <> "localhost, 127.0.0.1" or ProxyExceptions <> "" then
			set ExceptionsSet = AppendPrefsToMozillaCfgFile("network.proxy.no_proxies_on", chr(34) & ProxyExceptionsKey & chr(34))
		Elseif ProxyExceptionsKey = "localhost, 127.0.0.1" then
			set ExceptionsSet = AppendPrefsToMozillaCfgFile("network.proxy.no_proxies_on", chr(34) & ProxyExceptionsKey & chr(34))
		end if
		set ProxySet = AppendPrefsToMozillaCfgFile("network.proxy.type", ProxyKey)
	end if
end if


' Cache
FirefoxCacheType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCacheType")
FirefoxCacheKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCacheSize")
FirefoxCacheSSLKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCacheSSL")
if FirefoxCacheKey <> "" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.cache.disk.capacity")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.cache.disk_cache_ssl")
	if FirefoxCacheType = "default" then
		RemovePrefFromAllJs("browser.cache.disk.capacity")
		RemovePrefFromLocalSettingsFile("browser.cache.disk.capacity")
		RemovePrefFromAllJs("browser.cache.disk_cache_ssl")
		set CacheSet = AppendDefaultToMozillaCfgFile("browser.cache.disk.capacity", FirefoxCacheKey)
		if FirefoxCacheSSLKey = "1" then
			set CacheSSLSet = AppendDefaultToMozillaCfgFile("browser.cache.disk_cache_ssl", "true")
		else
			set CacheSSLSet = AppendDefaultToMozillaCfgFile("browser.cache.disk_cache_ssl", "false")
		end if
	else
		set CacheSet = AppendPrefsToMozillaCfgFile("browser.cache.disk.capacity", FirefoxCacheKey)
		if FirefoxCacheSSLKey = "1" then
			set CacheSSLSet = AppendPrefsToMozillaCfgFile("browser.cache.disk_cache_ssl", "true")
		else
			set CacheSSLSet = AppendPrefsToMozillaCfgFile("browser.cache.disk_cache_ssl", "false")
		end if
	end if
end if


' Check Default Browser
FirefoxCheckDefaultType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCheckDefaultType")
FirefoxCheckDefaultKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCheckDefault")
if FirefoxCheckDefaultKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.shell.checkDefaultBrowser")
	if FirefoxCheckDefaultType = "default" then
		RemovePrefFromLocalSettingsFile("browser.shell.checkDefaultBrowser")
		set DefaultSet = AppendDefaultToMozillaCfgFile("browser.shell.checkDefaultBrowser", "false")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("browser.shell.checkDefaultBrowser", "false")
	end if
Elseif FirefoxCheckDefaultKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.shell.checkDefaultBrowser")
	if FirefoxCheckDefaultType = "default" then
		RemovePrefFromLocalSettingsFile("browser.shell.checkDefaultBrowser")
		set DefaultSet = AppendDefaultToMozillaCfgFile("browser.shell.checkDefaultBrowser", "true")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("browser.shell.checkDefaultBrowser", "true")
	end if
end if


' Disable XPI Installations?
FirefoxXPIStateType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxXPIStateType")
FirefoxXPIStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxXPIState")
if FirefoxXPIStateKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("xpinstall.enabled")
	if FirefoxXPIStateType = "default" then
		RemovePrefFromXpinstallJs("xpinstall.enabled")
		set XPISet = AppendDefaultToMozillaCfgFile("xpinstall.enabled", "false")
	else
		set XPISet = AppendPrefsToMozillaCfgFile("xpinstall.enabled", "false")
	end if
Elseif FirefoxXPIStateKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("xpinstall.enabled")
	if FirefoxXPIStateType = "default" then
		RemovePrefFromXpinstallJs("xpinstall.enabled")
		set XPISet = AppendDefaultToMozillaCfgFile("xpinstall.enabled", "true")
	else
		set XPISet = AppendPrefsToMozillaCfgFile("xpinstall.enabled", "true")
	end if
end if


' update Firefox
FirefoxUpdateStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxUpdateState")
If FirefoxUpdateStateKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("app.update.autoUpdateEnabled")
	RemoveCurrentPrefsFromMozillaCfgFile("app.update.enabled")
	set UpdateSet1 = AppendPrefsToMozillaCfgFile("app.update.autoUpdateEnabled", "true")
	set UpdateSet2 = AppendPrefsToMozillaCfgFile("app.update.enabled", "true")
ElseIf FirefoxUpdateStateKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("app.update.autoUpdateEnabled")
	RemoveCurrentPrefsFromMozillaCfgFile("app.update.enabled")
	set UpdateSet1 = AppendPrefsToMozillaCfgFile("app.update.autoUpdateEnabled", "false")
	set UpdateSet2 = AppendPrefsToMozillaCfgFile("app.update.enabled", "false")
end if


' update Firefox's extensions
FirefoxExtUpdateStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxExtUpdateState")
If FirefoxExtUpdateStateKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("extensions.update.autoUpdateEnabled")
	RemoveCurrentPrefsFromMozillaCfgFile("extensions.update.enabled")
	set UpdateXtSet1 = AppendPrefsToMozillaCfgFile("extensions.update.autoUpdateEnabled", "true")
	set UpdateXtSet2 = AppendPrefsToMozillaCfgFile("extensions.update.enabled", "true")
ElseIf FirefoxExtUpdateStateKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("extensions.update.autoUpdate")
	RemoveCurrentPrefsFromMozillaCfgFile("extensions.update.enabled")
	set UpdateXtSet1 = AppendPrefsToMozillaCfgFile("extensions.update.autoUpdateEnabled", "false")
	set UpdateXtSet2 = AppendPrefsToMozillaCfgFile("extensions.update.enabled", "false")
end if


' update Firefox's search engines
FirefoxSearchUpdateStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxSearchUpdateState")
If FirefoxSearchUpdateStateKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.search.update")
	set UpdateSearchSet = AppendPrefsToMozillaCfgFile("browser.search.update", "true")
ElseIf FirefoxSearchUpdateStateKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.search.update")
	set UpdateSearchSet = AppendPrefsToMozillaCfgFile("browser.search.update", "false")
end if


' Disable Java?
FirefoxJavaStateType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxJavaStateType")
FirefoxJavaStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxJavaState")
If FirefoxJavaStateKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.enable_java")
	If FirefoxJavaStateType = "default" then
		RemovePrefFromAllJs("security.enable_java")
		set JavaStateSet = AppendDefaultToMozillaCfgFile("security.enable_java", "true")
	Else
		set JavaStateSet = AppendPrefsToMozillaCfgFile("security.enable_java", "true")
	end if
ElseIf FirefoxJavaStateKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.enable_java")
	If FirefoxJavaStateType = "default" then
		RemovePrefFromAllJs("security.enable_java")
		set JavaStateSet = AppendDefaultToMozillaCfgFile("security.enable_java", "false")
	Else
		set JavaStateSet = AppendPrefsToMozillaCfgFile("security.enable_java", "false")
	end if
end if


' Disable Javascript?
FirefoxJavascriptStateType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxJavascriptStateType")
FirefoxJavascriptStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxJavascriptState")
If FirefoxJavascriptStateKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("javascript.enabled")
	If FirefoxJavascriptStateType = "default" then
		RemovePrefFromAllJs("javascript.enabled")
		set JavascriptStateSet = AppendDefaultToMozillaCfgFile("javascript.enabled", "true")
	Else
		set JavascriptStateSet = AppendPrefsToMozillaCfgFile("javascript.enabled", "true")
	end if
ElseIf FirefoxJavascriptStateKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("javascript.enabled")
	If FirefoxJavascriptStateType = "default" then
		RemovePrefFromAllJs("javascript.enabled")
		set JavascriptStateSet = AppendDefaultToMozillaCfgFile("javascript.enabled", "false")
	Else
		set JavascriptStateSet = AppendPrefsToMozillaCfgFile("javascript.enabled", "false")
	end if
end if


' Disable SSL 2/3 & TLS?
FirefoxSSLStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxSSLState")
If FirefoxSSLStateKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.enable_ssl2")
	RemoveCurrentPrefsFromMozillaCfgFile("security.enable_ssl3")
	RemoveCurrentPrefsFromMozillaCfgFile("security.enable_tls")
	set SSLStateSet = AppendPrefsToMozillaCfgFile("security.enable_ssl2", "true")
	set SSLStateSet = AppendPrefsToMozillaCfgFile("security.enable_ssl3", "true")
	set SSLStateSet = AppendPrefsToMozillaCfgFile("security.enable_tls", "true")
Elseif FirefoxSSLStateKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.enable_ssl2")
	RemoveCurrentPrefsFromMozillaCfgFile("security.enable_ssl3")
	RemoveCurrentPrefsFromMozillaCfgFile("security.enable_tls")
	set SSLStateSet = AppendPrefsToMozillaCfgFile("security.enable_ssl2", "false")
	set SSLStateSet = AppendPrefsToMozillaCfgFile("security.enable_ssl3", "false")
	set SSLStateSet = AppendPrefsToMozillaCfgFile("security.enable_tls", "false")	
end if


' Disable IDNs?
FirefoxIDNStateType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxIDNStateType")
FirefoxIDNStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxIDNState")
if FirefoxIDNStateKey <> "" then
	if FirefoxIDNStateType = "default" then
		If FirefoxIDNStateKey = "1" then
			RemoveCurrentPrefsFromMozillaCfgFile("network.enableIDN")
			set IDNStateSet = AppendDefaultToMozillaCfgFile("network.enableIDN", "true")
		ElseIf FirefoxIDNStateKey = "0" then
			RemoveCurrentPrefsFromMozillaCfgFile("network.enableIDN")
			set IDNStateSet = AppendDefaultToMozillaCfgFile("network.enableIDN", "false")
		end if
	else
		If FirefoxIDNStateKey = "1" then
			RemoveCurrentPrefsFromMozillaCfgFile("network.enableIDN")
			set IDNStateSet = AppendPrefsToMozillaCfgFile("network.enableIDN", "true")
		ElseIf FirefoxIDNStateKey = "0" then
			RemoveCurrentPrefsFromMozillaCfgFile("network.enableIDN")
			set IDNStateSet = AppendPrefsToMozillaCfgFile("network.enableIDN", "false")
		end if
	end if
end if

' Disable Password Remembering?
FirefoxPasswordRememberKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxPasswordRememberState")
If FirefoxPasswordRememberKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("signon.rememberSignons")
	set PasswordRememberStateSet = AppendPrefsToMozillaCfgFile("signon.rememberSignons", "true")
ElseIf FirefoxPasswordRememberKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("signon.rememberSignons")
	set PasswordRememberStateSet = AppendPrefsToMozillaCfgFile("signon.rememberSignons", "false")
end if


' Enable Type Ahead Find
FirefoxTypeAheadFindTypeKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTypeAheadFindType")
FirefoxTypeAheadFindKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTypeAheadFindState")
if FirefoxTypeAheadFindKey <> "" then
	if FirefoxTypeAheadFindTypeKey = "default" then
		If FirefoxTypeAheadFindKey = "1" then
			RemoveCurrentPrefsFromMozillaCfgFile("accessibility.typeaheadfind")
			RemovePrefFromLocalSettingsFile("accessibility.typeaheadfind")
			set FirefoxTypeAheadFindSet = AppendDefaultToMozillaCfgFile("accessibility.typeaheadfind", "true")
		ElseIf FirefoxTypeAheadFindKey = "0" then
			RemoveCurrentPrefsFromMozillaCfgFile("accessibility.typeaheadfind")
			RemovePrefFromLocalSettingsFile("accessibility.typeaheadfind")
			set FirefoxTypeAheadFindSet = AppendDefaultToMozillaCfgFile("accessibility.typeaheadfind", "false")
		end if
	else
		If FirefoxTypeAheadFindKey = "1" then
			RemoveCurrentPrefsFromMozillaCfgFile("accessibility.typeaheadfind")
			set FirefoxTypeAheadFindSet = AppendPrefsToMozillaCfgFile("accessibility.typeaheadfind", "true")
		ElseIf FirefoxTypeAheadFindKey = "0" then
			RemoveCurrentPrefsFromMozillaCfgFile("accessibility.typeaheadfind")
			set FirefoxTypeAheadFindSet = AppendPrefsToMozillaCfgFile("accessibility.typeaheadfind", "false")
		end if
	end if
end if


' Disable Prefetching
FirefoxPrefetchStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxPrefetchState")
If FirefoxPrefetchStateKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("network.prefetch-next")
	set FirefoxPrefetchState = AppendPrefsToMozillaCfgFile("network.prefetch-next", "true")
ElseIf FirefoxPrefetchStateKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("network.prefetch-next")
	set FirefoxPrefetchState = AppendPrefsToMozillaCfgFile("network.prefetch-next", "false")
end if


' Enable/Disable URL security check
FirefoxSecurityCheckLoadUriKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxSecurityCheckLoadUri")
If FirefoxSecurityCheckLoadUriKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.checkloaduri")
	set FirefoxSecurityCheckLoadUriSet = AppendPrefsToMozillaCfgFile("security.checkloaduri", "false")
ElseIf FirefoxSecurityCheckLoadUriKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.checkloaduri")
	set FirefoxSecurityCheckLoadUriSet = AppendPrefsToMozillaCfgFile("security.checkloaduri", "true")
end if


' Trusted & Delegated Authentication white list
FirefoxTrustedAuthKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTrustedAuth")
FirefoxDelegatedAuthKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDelegatedAuth")
If FirefoxTrustedAuthKey <> "" or FirefoxDelegatedAuthKey <> "" then
	RemoveCurrentPrefsFromMozillaCfgFile("network.negotiate-auth.trusted-uris")
	RemoveCurrentPrefsFromMozillaCfgFile("network.negotiate-auth.delegation-uris")
	set FirefoxTrustedAuthSet = AppendPrefsToMozillaCfgFile("network.negotiate-auth.trusted-uris", chr(34) & FirefoxTrustedAuthKey & chr(34))
	set FirefoxDelegatedAuthSet = AppendPrefsToMozillaCfgFile("network.negotiate-auth.delegation-uris", chr(34) & FirefoxDelegatedAuthKey & chr(34))
end if


' Trusted NTLM white list
FirefoxTrustedNTLMKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTrustedNTLM")
If FirefoxTrustedNTLMKey <> "" then
	RemoveCurrentPrefsFromMozillaCfgFile("network.automatic-ntlm-auth.trusted-uris")
	RemoveCurrentPrefsFromMozillaCfgFile("network.ntlm.send-lm-response")
	set FirefoxTrustedAuthSet = AppendPrefsToMozillaCfgFile("network.automatic-ntlm-auth.trusted-uris", chr(34) & FirefoxTrustedNTLMKey & chr(34))
	set FirefoxTrustedAuthSet = AppendPrefsToMozillaCfgFile("Network.ntlm.send-lm-response", "true")
end if


' Browse with Caret
FirefoxCaretKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCaret")
If FirefoxCaretKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("accessibility.browsewithcaret")
	set FirefoxCaretSet = AppendPrefsToMozillaCfgFile("accessibility.browsewithcaret", "true")
ElseIf FirefoxCaretKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("accessibility.browsewithcaret")
	set FirefoxCaretSet = AppendPrefsToMozillaCfgFile("accessibility.browsewithcaret", "false")
end if


' Cookie Handling
FirefoxCookieType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCookieBehaviourType")
FirefoxCookieKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCookieBehaviour")
If FirefoxCookieKey <> "" then
	If FirefoxCookieType = "default" then
		RemovePrefFromAllJs("network.cookie.cookieBehavior")
		RemovePrefFromLocalSettingsFile("network.cookie.cookieBehavior")
		set FirefoxCookieBehaviourKey = AppendDefaultToMozillaCfgFile("network.cookie.cookieBehavior", FirefoxCookieKey)
	else
		RemoveCurrentPrefsFromMozillaCfgFile("network.cookie.cookieBehavior")
		set FirefoxCookieBehaviourKey = AppendPrefsToMozillaCfgFile("network.cookie.cookieBehavior", FirefoxCookieKey)
	end if
end if


' Set Bookmarks Location
FirefoxBookmarksLocationKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxBookmarks")
If FirefoxBookmarksLocationKey <> "" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.bookmarks.file")
	set FirefoxBookmarksKey = AppendPrefsToMozillaCfgFile("browser.bookmarks.file", chr(34) & FirefoxBookmarksLocationKey & "\\bookmarks.html" & chr(34))
end if


' Tabs Behaviour
FirefoxTabType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTabType")
If FirefoxTabType = "locked" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.link.open_external")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.link.open_newwindow")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.tabs.loadInBackground")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.tabs.warnOnClose")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.tabs.warnOnOpen")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.tabs.autoHide")
	FirefoxTabNewPage = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTabNewPage")
	If FirefoxTabNewPage = "Window" then
		set FirefoxTabNewPageKey = AppendPrefsToMozillaCfgFile("browser.link.open_external", 2)
		set FirefoxTabNewPageKey2 = AppendPrefsToMozillaCfgFile("browser.link.open_newwindow", 2)
	Else
		set FirefoxTabNewPageKey = AppendPrefsToMozillaCfgFile("browser.link.open_external", 3)
		set FirefoxTabNewPageKey2 = AppendPrefsToMozillaCfgFile("browser.link.open_newwindow", 3)
	end if
	FirefoxTabCloseWarn = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTabCloseWarn")
	set FirefoxTabCloseWarnKey = AppendPrefsToMozillaCfgFile("browser.tabs.warnOnClose", FirefoxTabCloseWarn)
	FirefoxTabOpenWarn = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTabOpenWarn")
	set FirefoxTabOpenWarnKey = AppendPrefsToMozillaCfgFile("browser.tabs.warnOnOpen", FirefoxTabOpenWarn)
	FirefoxTabShowBar = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTabShowBar")
	set FirefoxTabShowBarKey = AppendPrefsToMozillaCfgFile("browser.tabs.autoHide", FirefoxTabShowBar)
	FirefoxTabBackground = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTabBackground")
	set FirefoxTabBackgroundKey = AppendPrefsToMozillaCfgFile("browser.tabs.loadInBackground", FirefoxTabBackground)
ElseIf FirefoxTabType = "default" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.link.open_external")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.link.open_newwindow")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.tabs.loadInBackground")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.tabs.warnOnClose")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.tabs.warnOnOpen")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.tabs.autoHide")
	RemovePrefFromLocalSettingsFile("browser.link.open_external")
	RemovePrefFromLocalSettingsFile("browser.link.open_newwindow")
	RemovePrefFromLocalSettingsFile("browser.tabs.loadInBackground")
	RemovePrefFromLocalSettingsFile("browser.tabs.warnOnClose")
	RemovePrefFromLocalSettingsFile("browser.tabs.warnOnOpen")
	RemovePrefFromLocalSettingsFile("browser.tabs.autoHide")
	RemovePrefFromAllJs("browser.tabs.warnOnClose")
	RemovePrefFromAllJs("browser.tabs.warnOnOpen")
	RemovePrefFromAllJs("browser.tabs.autoHide")
	FirefoxTabNewPage = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTabNewPage")
	If FirefoxTabNewPage = "Window" then
		set FirefoxTabNewPageKey = AppendDefaultToMozillaCfgFile("browser.link.open_external", 2)
		set FirefoxTabNewPageKey2 = AppendDefaultToMozillaCfgFile("browser.link.open_newwindow", 2)
	Else
		set FirefoxTabNewPageKey = AppendDefaultToMozillaCfgFile("browser.link.open_external", 3)
		set FirefoxTabNewPageKey2 = AppendDefaultToMozillaCfgFile("browser.link.open_newwindow", 3)
	end if
	FirefoxTabCloseWarn = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTabCloseWarn")
	set FirefoxTabCloseWarnKey = AppendDefaultToMozillaCfgFile("browser.tabs.warnOnClose", FirefoxTabCloseWarn)
	FirefoxTabOpenWarn = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTabOpenWarn")
	set FirefoxTabOpenWarnKey = AppendDefaultToMozillaCfgFile("browser.tabs.warnOnOpen", FirefoxTabOpenWarn)
	FirefoxTabShowBar = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTabShowBar")
	set FirefoxTabShowBarKey = AppendDefaultToMozillaCfgFile("browser.tabs.autoHide", FirefoxTabShowBar)
	FirefoxTabBackground = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTabBackground")
	set FirefoxTabBackgroundKey = AppendDefaultToMozillaCfgFile("browser.tabs.loadInBackground", FirefoxTabBackground)
end if		


' History
FirefoxHistoryType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxHistoryType")
If FirefoxHistoryType = "locked" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.history_expire_days")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.history_expire_days_min")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.history_expire_days.mirror")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.formfill.enable")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.download.manager.retention")
	FirefoxHistoryPage = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxHistoryDays")
	set FirefoxHistoryPageKey = AppendPrefsToMozillaCfgFile("browser.history_expire_days", FirefoxHistoryPage)
	set FirefoxHistoryPage2Key = AppendPrefsToMozillaCfgFile("browser.history_expire_days.mirror", FirefoxHistoryPage)
	set FirefoxHistoryPage3Key = AppendPrefsToMozillaCfgFile("browser.history_expire_days_min", FirefoxHistoryPage)
	FirefoxHistoryPage = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxHistoryForms")
	set FirefoxHistoryPageKey = AppendPrefsToMozillaCfgFile("browser.formfill.enable", FirefoxHistoryPage)
	FirefoxHistoryPage = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxHistoryDownloads")
	set FirefoxHistoryPageKey = AppendPrefsToMozillaCfgFile("browser.download.manager.retention", FirefoxHistoryPage)
ElseIf FirefoxHistoryType = "default" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.history_expire_days")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.history_expire_days_min")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.history_expire_days.mirror")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.formfill.enable")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.download.manager.retention")
	RemovePrefFromAllJs("browser.history_expire_days")
	RemovePrefFromLocalSettingsFile("browser.history_expire_days")
	RemovePrefFromLocalSettingsFile("browser.history_expire_days_min")
	RemovePrefFromLocalSettingsFile("browser.formfill.enable")
	RemovePrefFromLocalSettingsFile("browser.download.manager.retention")
	FirefoxHistoryPage = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxHistoryDays")
	set FirefoxHistoryPageKey = AppendDefaultToMozillaCfgFile("browser.history_expire_days", FirefoxHistoryPage)
	set FirefoxHistoryPage2Key = AppendDefaultToMozillaCfgFile("browser.history_expire_days.mirror", FirefoxHistoryPage)
	set FirefoxHistoryPage3Key = AppendDefaultToMozillaCfgFile("browser.history_expire_days_min", FirefoxHistoryPage)
	FirefoxHistoryPage = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxHistoryForms")
	set FirefoxHistoryPageKey = AppendDefaultToMozillaCfgFile("browser.formfill.enable", FirefoxHistoryPage)
	FirefoxHistoryPage = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxHistoryDownloads")
	set FirefoxHistoryPageKey = AppendDefaultToMozillaCfgFile("browser.download.manager.retention", FirefoxHistoryPage)
end if


' Private Data
FirefoxDataType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDataType")
If FirefoxDataType = "locked" then
	RemoveCurrentPrefsFromMozillaCfgFile("privacy.sanitize.sanitizeOnShutdown")
	RemoveCurrentPrefsFromMozillaCfgFile("privacy.sanitize.promptOnSanitize")
	FirefoxDataClear = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDataClear")
	set FirefoxDataClearKey = AppendPrefsToMozillaCfgFile("privacy.sanitize.sanitizeOnShutdown", FirefoxDataClear)
	FirefoxDataPrompt = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDataPrompt")
	set FirefoxDataClearKey = AppendPrefsToMozillaCfgFile("privacy.sanitize.promptOnSanitize", FirefoxDataPrompt)
ElseIf FirefoxDataType = "default" then
	RemoveCurrentPrefsFromMozillaCfgFile("privacy.sanitize.sanitizeOnShutdown")
	RemoveCurrentPrefsFromMozillaCfgFile("privacy.sanitize.promptOnSanitize")
	RemovePrefFromLocalSettingsFile("privacy.sanitize.sanitizeOnShutdown")
	RemovePrefFromLocalSettingsFile("privacy.sanitize.promptOnSanitize")
	FirefoxDataClear = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDataClear")
	set FirefoxDataClearKey = AppendDefaultToMozillaCfgFile("privacy.sanitize.sanitizeOnShutdown", FirefoxDataClear)
	FirefoxDataPrompt = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDataPrompt")
	set FirefoxDataClearKey = AppendDefaultToMozillaCfgFile("privacy.sanitize.promptOnSanitize", FirefoxDataPrompt)
end if


' Browsing Options
FirefoxBrowsingType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxBrowsingType")
If FirefoxBrowsingType = "locked" then
	RemoveCurrentPrefsFromMozillaCfgFile("general.autoScroll")
	RemoveCurrentPrefsFromMozillaCfgFile("general.smoothScroll")
	RemoveCurrentPrefsFromMozillaCfgFile("layout.spellcheckDefault")
	FirefoxAutoScroll = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxAutoScroll")
	set FirefoxAutoScrollKey = AppendPrefsToMozillaCfgFile("general.autoScroll", FirefoxAutoScroll)
	FirefoxSmoothScroll = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxSmoothScroll")
	set FirefoxSmoothScrollKey = AppendPrefsToMozillaCfgFile("general.smoothScroll", FirefoxSmoothScroll)
	FirefoxCheckSpell = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCheckSpell")
	set FirefoxCheckSpellKey = AppendPrefsToMozillaCfgFile("layout.spellcheckDefault", FirefoxCheckSpell)
ElseIf FirefoxBrowsingType = "default" then
	RemoveCurrentPrefsFromMozillaCfgFile("general.autoScroll")
	RemoveCurrentPrefsFromMozillaCfgFile("general.smoothScroll")
	RemoveCurrentPrefsFromMozillaCfgFile("layout.spellcheckDefault")
	RemovePrefFromLocalSettingsFile("general.autoScroll")
	RemovePrefFromLocalSettingsFile("general.smoothScroll")
	RemovePrefFromLocalSettingsFile("layout.spellcheckDefault")
	FirefoxAutoScroll = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxAutoScroll")
	set FirefoxAutoScrollKey = AppendDefaultToMozillaCfgFile("general.autoScroll", FirefoxAutoScroll)
	FirefoxSmoothScroll = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxSmoothScroll")
	set FirefoxSmoothScrollKey = AppendDefaultToMozillaCfgFile("general.smoothScroll", FirefoxSmoothScroll)
	FirefoxCheckSpell = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCheckSpell")
	set FirefoxCheckSpellKey = AppendDefaultToMozillaCfgFile("layout.spellcheckDefault", FirefoxCheckSpell)
end if


' Save Form Data
FirefoxSaveFormDataType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxSaveFormDataType")
FirefoxSaveFormDataKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxSaveFormData")
if FirefoxSaveFormDataKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.formfill.enable")
	if FirefoxSaveFormDataType = "default" then
		RemovePrefFromLocalSettingsFile("browser.formfill.enable")
		set DefaultSet = AppendDefaultToMozillaCfgFile("browser.formfill.enable", "false")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("browser.formfill.enable", "false")
	end if
Elseif FirefoxSaveFormDataKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.formfill.enable")
	if FirefoxSaveFormDataType = "default" then
		RemovePrefFromLocalSettingsFile("browser.formfill.enable")
		set DefaultSet = AppendDefaultToMozillaCfgFile("browser.formfill.enable", "true")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("browser.formfill.enable", "true")
	end if
end if


' Delete Private Data Cookies
FirefoxDelPrivDataCookiesType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDelPrivDataCookiesType")
FirefoxDelPrivDataCookiesKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDelPrivDataCookies")
if FirefoxDelPrivDataCookiesKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("privacy.item.cookies")
	if FirefoxDelPrivDataCookiesType = "default" then
		RemovePrefFromLocalSettingsFile("privacy.item.cookies")
		set DefaultSet = AppendDefaultToMozillaCfgFile("privacy.item.cookies", "false")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("privacy.item.cookies", "false")
	end if
Elseif FirefoxDelPrivDataCookiesKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("privacy.item.cookies")
	if FirefoxDelPrivDataCookiesType = "default" then
		RemovePrefFromLocalSettingsFile("privacy.item.cookies")
		set DefaultSet = AppendDefaultToMozillaCfgFile("privacy.item.cookies", "true")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("privacy.item.cookies", "true")
	end if
end if


' Delete Private Data Offline Websites
FirefoxDelPrivDataOfflineWebsitesType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDelPrivDataOfflineWebsitesType")
FirefoxDelPrivDataOfflineWebsitesKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDelPrivDataOfflineWebsites")
if FirefoxDelPrivDataOfflineWebsitesKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("privacy.item.offlineApps")
	if FirefoxDelPrivDataOfflineWebsitesType = "default" then
		RemovePrefFromLocalSettingsFile("privacy.item.offlineApps")
		set DefaultSet = AppendDefaultToMozillaCfgFile("privacy.item.offlineApps", "false")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("privacy.item.offlineApps", "false")
	end if
Elseif FirefoxDelPrivDataOfflineWebsitesKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("privacy.item.offlineApps")
	if FirefoxDelPrivDataOfflineWebsitesType = "default" then
		RemovePrefFromLocalSettingsFile("privacy.item.offlineApps")
		set DefaultSet = AppendDefaultToMozillaCfgFile("privacy.item.offlineApps", "true")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("privacy.item.offlineApps", "true")
	end if
end if


' Delete Private Data Passwords
FirefoxDelPrivDataPasswordsType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDelPrivDataPasswordsType")
FirefoxDelPrivDataPasswordsKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDelPrivDataPasswords")
if FirefoxDelPrivDataPasswordsKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("privacy.item.passwords")
	if FirefoxDelPrivDataPasswordsType = "default" then
		RemovePrefFromLocalSettingsFile("privacy.item.passwords")
		set DefaultSet = AppendDefaultToMozillaCfgFile("privacy.item.passwords", "false")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("privacy.item.passwords", "false")
	end if
Elseif FirefoxDelPrivDataPasswordsKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("privacy.item.passwords")
	if FirefoxDelPrivDataPasswordsType = "default" then
		RemovePrefFromLocalSettingsFile("privacy.item.passwords")
		set DefaultSet = AppendDefaultToMozillaCfgFile("privacy.item.passwords", "true")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("privacy.item.passwords", "true")
	end if
end if


' Show SSL Domain Icon
FirefoxShowSSLDomainIconType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxShowSSLDomainIconType")
FirefoxShowSSLDomainIconKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxShowSSLDomainIcon")
if FirefoxShowSSLDomainIconKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.identity.ssl_domain_display")
	if FirefoxShowSSLDomainIconType = "default" then
		RemovePrefFromLocalSettingsFile("browser.identity.ssl_domain_display")
		set DefaultSet = AppendDefaultToMozillaCfgFile("browser.identity.ssl_domain_display", "0")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("browser.identity.ssl_domain_display", "0")
	end if
Elseif FirefoxShowSSLDomainIconKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.identity.ssl_domain_display")
	if FirefoxShowSSLDomainIconType = "default" then
		RemovePrefFromLocalSettingsFile("browser.identity.ssl_domain_display")
		set DefaultSet = AppendDefaultToMozillaCfgFile("browser.identity.ssl_domain_display", "1")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("browser.identity.ssl_domain_display", "1")
	end if
end if


' Use Download Directory
FirefoxUseDownloadDirType = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxUseDownloadDirType")
FirefoxUseDownloadDirKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxUseDownloadDir")
if FirefoxUseDownloadDirKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.download.useDownloadDir")
	if FirefoxUseDownloadDirType = "default" then
		RemovePrefFromLocalSettingsFile("browser.download.useDownloadDir")
		set DefaultSet = AppendDefaultToMozillaCfgFile("browser.download.useDownloadDir", "false")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("browser.download.useDownloadDir", "false")
	end if
Elseif FirefoxUseDownloadDirKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.download.useDownloadDir")
	if FirefoxUseDownloadDirType = "default" then
		RemovePrefFromLocalSettingsFile("browser.download.useDownloadDir")
		set DefaultSet = AppendDefaultToMozillaCfgFile("browser.download.useDownloadDir", "true")
	else
		set DefaultSet = AppendPrefsToMozillaCfgFile("browser.download.useDownloadDir", "true")
	end if
end if


' Replace Certificates for all User Profiles
FirefoxCertificatesLocationKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCertificateLocation")
if FirefoxCertificatesLocationKey <> "" then
	FirefoxMandatoryCertificatesKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxMandatoryCertificates")
	if (FirefoxMandatoryCertificatesKey = "Merge" OR FirefoxMandatoryCertificatesKey = "Replace") then
		set EnVar = Wshshell.environment("Process")
		DocSettingsPath = Left(EnVar("ALLUSERSPROFILE"),Len(EnVar("ALLUSERSPROFILE"))-9)
		Set objFolder = fso.GetFolder(DocSettingsPath)
		Set colSubfolders = objFolder.Subfolders
		for each objSubfolder in colSubfolders
			if (objFSO.FolderExists(DocSettingsPath&objSubfolder.Name)) then
				if (objFSO.FolderExists(DocSettingsPath&objSubfolder.Name&"\Application Data")) then
					if (objFSO.FolderExists(DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla")) then
						if (objFSO.FolderExists(DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla\Firefox")) then
							if (objFSO.FolderExists(DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla\Firefox\Profiles")) then
								Set objFolderProf = fso.GetFolder(DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla\Firefox\Profiles")
								Set colSubfoldersProf = objFolderProf.Subfolders
								For Each objSubfolderProf in colSubfoldersProf
									if FirefoxMandatoryCertificatesKey = "Merge" then
										if fso.FileExists(DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla\Firefox\Profiles\"&objSubfolderProf.Name & "\cert8.db") = false then
											if fso.FileExists(FirefoxCertificatesLocationKey & "\cert8.db") then
												fso.CopyFile FirefoxCertificatesLocationKey & "\cert8.db", DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla\Firefox\Profiles\"&objSubfolderProf.Name & "\cert8.db"
											end if
										end if
										if fso.FileExists(DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla\Firefox\Profiles\"&objSubfolderProf.Name & "\key3.db") = false then
											if fso.FileExists(FirefoxCertificatesLocationKey & "\key3.db") then
												fso.CopyFile FirefoxCertificatesLocationKey & "\key3.db", DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla\Firefox\Profiles\"&objSubfolderProf.Name & "\key3.db"
											end if
										end if
										if fso.FileExists(DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla\Firefox\Profiles\"&objSubfolderProf.Name & "\secmod.db") = false then
											if fso.FileExists(FirefoxCertificatesLocationKey & "\secmod.db") then
												fso.CopyFile FirefoxCertificatesLocationKey & "\secmod.db", DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla\Firefox\Profiles\"&objSubfolderProf.Name & "\secmod.db"
											end if
										end if
									else
										if fso.FileExists(FirefoxCertificatesLocationKey & "\cert8.db") then
											fso.CopyFile FirefoxCertificatesLocationKey & "\cert8.db", DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla\Firefox\Profiles\"&objSubfolderProf.Name & "\cert8.db"
										end if
										if fso.FileExists(FirefoxCertificatesLocationKey & "\key3.db") then
											fso.CopyFile FirefoxCertificatesLocationKey & "\key3.db", DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla\Firefox\Profiles\"&objSubfolderProf.Name & "\key3.db"
										end if
										if fso.FileExists(FirefoxCertificatesLocationKey & "\secmod.db") then
											fso.CopyFile FirefoxCertificatesLocationKey & "\secmod.db", DocSettingsPath&objSubfolder.Name&"\Application Data\Mozilla\Firefox\Profiles\"&objSubfolderProf.Name & "\secmod.db"
										end if
									end if
								next
							end if
						end if
					end if
				end if
			end if
		next
	end if
end if


' Suppress Update Message
FirefoxSupressUpdatePageKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxSupressUpdatePage")
If FirefoxSupressUpdatePageKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("startup.homepage_override_url")
	RemoveCurrentPrefsFromMozillaCfgFile("startup.homepage_welcome_url")
	set FirefoxSupressUpdateKey = AppendPrefsToMozillaCfgFile("startup.homepage_override_url", chr(34) & chr(34))
	set FirefoxSupressUpdateKey = AppendPrefsToMozillaCfgFile("startup.homepage_welcome_url", chr(34) & chr(34))
ElseIf FirefoxSupressUpdatePage = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("startup.homepage_override_url")
	RemoveCurrentPrefsFromMozillaCfgFile("startup.homepage_welcome_url")
end if


' Disable IPv6
FirefoxDisableIPv6Key = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDisableIPv6")
If FirefoxDisableIPv6Key = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("network.dns.disableIPv6")
	set DisableIPv6Key = AppendPrefsToMozillaCfgFile("network.dns.disableIPv6", "true")
end if


' Display Warning Messages
FirefoxWarningEnteringSecureKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxWarningEnteringSecure")
If FirefoxWarningEnteringSecureKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.warn_entering_secure")
	set WarningEnteringSecureKey = AppendPrefsToMozillaCfgFile("security.warn_entering_secure", "true")
ElseIf FirefoxWarningEnteringSecureKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.warn_entering_secure")
	set WarningEnteringSecureKey = AppendPrefsToMozillaCfgFile("security.warn_entering_secure", "false")
end if
FirefoxWarningEnteringWeakKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxWarningEnteringWeak")
If FirefoxWarningEnteringWeakKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.warn_entering_weak")
	set WarningEnteringWeakKey = AppendPrefsToMozillaCfgFile("security.warn_entering_weak", "true")
ElseIf FirefoxWarningEnteringWeakKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.warn_entering_weak")
	set WarningEnteringWeakKey = AppendPrefsToMozillaCfgFile("security.warn_entering_weak", "false")
end if
FirefoxWarningLeavingSecureKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxWarningLeavingSecure")
If FirefoxWarningLeavingSecureKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.warn_leaving_secure")
	set WarningLeavingSecureKey = AppendPrefsToMozillaCfgFile("security.warn_leaving_secure", "true")
ElseIf FirefoxWarningLeavingSecureKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.warn_leaving_secure")
	set WarningLeavingSecureKey = AppendPrefsToMozillaCfgFile("security.warn_leaving_secure", "false")
end if
FirefoxWarningSubmitInsecureKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxWarningSubmitInsecure")
If FirefoxWarningSubmitInsecureKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.warn_submit_insecure")
	set WarningSubmitInsecureKey = AppendPrefsToMozillaCfgFile("security.warn_submit_insecure", "true")
ElseIf FirefoxWarningSubmitInsecureKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.warn_submit_insecure")
	set WarningSubmitInsecureKey = AppendPrefsToMozillaCfgFile("security.warn_submit_insecure", "false")
end if
FirefoxWarningViewingMixedKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxWarningViewingMixed")
If FirefoxWarningViewingMixedKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.warn_viewing_mixed")
	set WarningViewingMixedKey = AppendPrefsToMozillaCfgFile("security.warn_viewing_mixed", "true")
ElseIf FirefoxWarningViewingMixedKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("security.warn_viewing_mixed")
	set WarningViewingMixedKey = AppendPrefsToMozillaCfgFile("security.warn_viewing_mixed", "false")
end if


' Phishing Protection
FirefoxPhishProtectKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxPhishProtect")
If FirefoxPhishProtectKey = "1" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.safebrowsing.enabled")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.safebrowsing.malware.enabled")
	set PhishProtectKey = AppendPrefsToMozillaCfgFile("browser.safebrowsing.enabled", "true")
	set MalwareProtectKey = AppendPrefsToMozillaCfgFile("browser.safebrowsing.malware.enabled", "true")
ElseIf FirefoxPhishProtectKey = "0" then
	RemoveCurrentPrefsFromMozillaCfgFile("browser.safebrowsing.enabled")
	RemoveCurrentPrefsFromMozillaCfgFile("browser.safebrowsing.malware.enabled")
	set PhishProtectKey = AppendPrefsToMozillaCfgFile("browser.safebrowsing.enabled", "false")
	set MalwareProtectKey = AppendPrefsToMozillaCfgFile("browser.safebrowsing.malware.enabled", "false")
end if


' TODO:  More settings!


Function RemoveCurrentPrefsFromMozillaCfgFile(removeSetting)
	if fso.FileExists(MozillaCfgFile) then
		Set ParseMozillaCfgFile = fso.OpenTextFile(MozillaCfgFile, ForReading)

		' Get file content into an array:
		Dim aContents
		aContents = Split(ParseMozillaCfgFile.ReadAll, vbCrLf)

		ParseMozillaCfgFile.Close
		set ParseMozillaCfgFile = Nothing

		' Parse Back In to mozilla.cfg file

		Dim aContentsNew
		aContentsNew = Filter(aContents, chr(34) & removeSetting & chr(34), False, vbTextCompare)

		' Overwrite the old file with the new file,
		Set ParseOutMozillaCfgFile = fso.OpenTextFile(MozillaCfgFile, ForWriting)
		ParseOutMozillaCfgFile.Write Join(aContentsNew, vbCrLf)
		ParseOutMozillaCfgFile.Close
	else
		RemoveCurrentPrefsFromPrefCallsFile(removeSetting)
	end if
End Function

Function RemoveCurrentPrefsFromPrefCallsFile(removeSetting)
	if fso.FileExists(FirefoxPrefCallsFile) then
		Set ParsePrefCallsFile = fso.OpenTextFile(FirefoxPrefCallsFile, ForReading)

		' Get file content into an array:
		Dim aContents
		aContents = Split(ParsePrefCallsFile.ReadAll, vbCrLf)

		ParsePrefCallsFile.Close
		set ParsePrefCallsFile = Nothing

		' Parse Back In to PrefCalls.js file

		Dim aContentsNew
		aContentsNew = Filter(aContents, chr(34) & removeSetting & chr(34), False, vbTextCompare)

		' Overwrite the old file with the new file,
		Set ParseOutPrefCallsFile = fso.OpenTextFile(FirefoxPrefCallsFile, ForWriting)
		ParseOutPrefCallsFile.Write Join(aContentsNew, vbCrLf)
		ParseOutPrefCallsFile.Close
	end if
End Function

Function RemovePrefFromAllJs(removeSetting)
	if fso.FileExists(FirefoxAllJsFile) then
		Set ParsePrefsFile = fso.OpenTextFile(FirefoxAllJsFile, ForReading)

		' Get file content into an array:
		Dim aContents
		aContents = Split(ParsePrefsFile.ReadAll, vbCrLf)

		ParsePrefsFile.Close
		set ParsePrefsFile = Nothing

		' Parse Back In to all.js file

		Dim aContentsNew
		aContentsNew = Filter(aContents, chr(34) & removeSetting & chr(34), False, vbTextCompare)

		' Overwrite the old file with the new file,
		Set ParseOutPrefsFile = fso.OpenTextFile(FirefoxAllJsFile, ForWriting)
		ParseOutPrefsFile.Write Join(aContentsNew, vbCrLf)
		ParseOutPrefsFile.Close
	end if
End Function

Function RemovePrefFromLocalSettingsFile(removeSetting)
	if fso.FileExists(LocalSettingsFile) then
		Set ParsePrefsFile = fso.OpenTextFile(LocalSettingsFile, ForReading)

		' Get file content into an array:
		Dim aContents
		aContents = Split(ParsePrefsFile.ReadAll, vbCrLf)

		ParsePrefsFile.Close
		set ParsePrefsFile = Nothing

		' Parse Back In to all.js file

		Dim aContentsNew
		aContentsNew = Filter(aContents, chr(34) & removeSetting & chr(34), False, vbTextCompare)

		' Overwrite the old file with the new file,
		Set ParseOutPrefsFile = fso.OpenTextFile(LocalSettingsFile, ForWriting)
		ParseOutPrefsFile.Write Join(aContentsNew, vbCrLf)
		ParseOutPrefsFile.Close
	end if
End Function

Function RemovePrefFromXpinstallJs(removeSetting)
	if fso.FileExists(FirefoxXpinstallJsFile) then
		Set ParsePrefsFile = fso.OpenTextFile(FirefoxXpinstallJsFile, ForReading)

		' Get file content into an array:
		Dim aContents
		aContents = Split(ParsePrefsFile.ReadAll, vbCrLf)

		ParsePrefsFile.Close
		set ParsePrefsFile = Nothing

		' Parse Back In to all.js file

		Dim aContentsNew
		aContentsNew = Filter(aContents, chr(34) & removeSetting & chr(34), False, vbTextCompare)

		' Overwrite the old file with the new file,
		Set ParseOutPrefsFile = fso.OpenTextFile(FirefoxXpinstallJsFile, ForWriting)
		ParseOutPrefsFile.Write Join(aContentsNew, vbCrLf)
		ParseOutPrefsFile.Close
	end if
End Function

Function SetDefaultHomePage(homepage)
	Set ParseOutPrefsFile = fso.OpenTextFile(FirefoxBrowserconfigPropertiesFile, ForWriting)
	ParseOutPrefsFile.WriteLine("browser.startup.homepage=" & homepage)
	ParseOutPrefsFile.WriteLine("browser.startup.homepage_reset=" & homepage)
	ParseOutPrefsFile.Close
End Function

Function AppendPrefsToMozillaCfgFile(writeKey, writeData)
	set PrefsFile = fso.OpenTextFile(MozillaCfgFile,ForAppending)
	PrefsFile.Write (vbCrLf & "lockPref(" & chr(34) & writeKey & chr(34) & ", " & writeData & ");")
	PrefsFile.Close
End Function

Function AppendDefaultToMozillaCfgFile(writeKey, writeData)
	set PrefsFile = fso.OpenTextFile(MozillaCfgFile,ForAppending)
	PrefsFile.Write (vbCrLf & "defaultPref(" & chr(34) & writeKey & chr(34) & ", " & writeData & ");")
	PrefsFile.Close
End Function

Function RemoveMozillaCfgFileInclude()
	if fso.FileExists(LocalSettingsFile) then
		Set ParsePrefsFile = fso.OpenTextFile(LocalSettingsFile, ForReading)

		' Get file content into an array:
		Dim aContents
		aContents = Split(ParsePrefsFile.ReadAll, vbCrLf)

		ParsePrefsFile.Close
		set ParsePrefsFile = Nothing

		' Parse Back In to local-settings.js file

		Dim aContentsNew
		aContentsNew = Filter(aContents, chr(34) & "general.config.filename" & chr(34), False, vbTextCompare)

		' Overwrite the old file with the new file,
		Set ParseOutPrefsFile = fso.OpenTextFile(LocalSettingsFile, ForWriting)
		ParseOutPrefsFile.Write Join(aContentsNew, vbCrLf)
		ParseOutPrefsFile.Close
	end if
End Function
