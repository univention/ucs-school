' FirefoxADM Logout 0.4
' 2004/2005 Mark Sammons

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

on error resume next 

set EnVar = Wshshell.environment("Process")
FirefoxProfilePath = EnVar("appdata") & "\Mozilla\Firefox\Profiles"


' Do this:  For Each Dir within Firefox's profile, check for prefs.js, then remove setting
		
if fso.FolderExists(FirefoxProfilePath) then
	' Get the folders within profile and store to array
	set FirefoxProfileFolder = fso.GetFolder(FirefoxProfilePath)
	set FirefoxProfiles = FirefoxProfileFolder.SubFolders

	' Now the Pass...

	For Each FirefoxFolder in FirefoxProfiles
		FirefoxPrefsFile = FirefoxProfilePath & "\" & FirefoxFolder.Name & "\prefs.js"

		' if its there!
		if fso.FileExists(FirefoxPrefsFile) then

			' SET FROM ADMINISTRATIVE TEMPLATES
			' regread in from HKCU\Software\Policies\Firefox\<settings>


			' homepage setting
			HomePageKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxHomepage")
			if HomePageKey <> "" then
				RemoveCurrentPrefsFromFile("browser.startup.homepage")
			end if


			' Automatic Image Resizing
			ImageResizeKey = WshShell.regread("HKCU\Software\Policies\Firefox\ImageResize")
			if ImageResizeKey <> "" then
				RemoveCurrentPrefsFromFile("browser.enable_automatic_image_resizing")
			end if
		

			' Proxy Settings
			ProxyKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxProxy")
			if ProxyKey <> "" then
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
			end if


			' Cache
			FirefoxCacheKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxCacheSize")
			if FirefoxCacheKey <> "" then
				RemoveCurrentPrefsFromFile("browser.cache.disk.capacity")
			end if


			' Check Default Browser
			FirefoxCheckDefaultKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxCheckDefault")
			if FirefoxCheckDefaultKey <> "" then
				RemoveCurrentPrefsFromFile("browser.shell.checkDefaultBrowser")
			end if


			' Disable XPI Installations?
			FirefoxXPIStateKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxXPIState")
			if FirefoxXPIStateKey <> "" then
				RemoveCurrentPrefsFromFile("xpinstall.dialog.confirm")
				RemoveCurrentPrefsFromFile("xpinstall.enabled")
				RemoveCurrentPrefsFromFile("xpinstall.dialog.progress.chrome")
				RemoveCurrentPrefsFromFile("xpinstall.dialog.progress.skin")
				RemoveCurrentPrefsFromFile("xpinstall.dialog.progress.type.chrome")
				RemoveCurrentPrefsFromFile("xpinstall.dialog.progress.type.skin")
			end if


			' Download Folder
			FirefoxDownloadLocationKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxDownloadType")
			if FirefoxDownloadLocationKey <> "" then
				RemoveCurrentPrefsFromFile("browser.download.defaultFolder")
				RemoveCurrentPrefsFromFile("browser.download.dir")
			end if


			FirefoxTypeAheadFindKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxTypeAheadFindState")
			If FirefoxTypeAheadFindKey <> "" then
				RemoveCurrentPrefsFromFile("accessibility.typeaheadfind")
			end if


			FirefoxLocalCacheKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxCacheLocal")
			If FirefoxLocalCacheKey <> "" then
				RemoveCurrentPrefsFromFile("browser.cache.disk.parent_directory")
			end if


			FirefoxCaretKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxCaret")
			If FirefoxCaretKey <> "" then
				RemoveCurrentPrefsFromFile("accessibility.browsewithcaret")
			end if


			'
			' locked settings
			'

			HomePageKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxHomepage")
			HomePageTypeKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxHomepageType")
			if HomePageKey <> "" and HomePageTypeKey <> "default" then
				RemoveCurrentPrefsFromFile("browser.startup.homepage")
			end if


			ImageResizeKey = WshShell.regread("HKLM\Software\Policies\Firefox\ImageResize")
			if ImageResizeKey <> "" then
				RemoveCurrentPrefsFromFile("browser.enable_automatic_image_resizing")
			end if


			ProxyKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxProxy")
			ProxyTypeKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxProxyType")
			if ProxyKey <> "" and ProxyTypeKey <> "default" then
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
			end if


			FirefoxCacheKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCacheSize")
			FirefoxCacheTypeKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCacheType")
			if FirefoxCacheKey <> "" and FirefoxCacheTypeKey <> "default" then
				RemoveCurrentPrefsFromFile("browser.cache.disk.capacity")
				RemoveCurrentPrefsFromFile("browser.cache.disk_cache_ssl")
			end if


			FirefoxCheckDefaultKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCheckDefault")
			if FirefoxCheckDefaultKey <> "" then
				RemoveCurrentPrefsFromFile("browser.shell.checkDefaultBrowser")
			end if


			FirefoxXPIStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxXPIState")
			if FirefoxXPIStateKey <> "" then
				RemoveCurrentPrefsFromFile("xpinstall.enabled")
			end if


			FirefoxUpdateStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxUpdateState")
			If FirefoxUpdateStateKey <> "" then
				RemoveCurrentPrefsFromFile("app.update.autoUpdateEnabled")
				RemoveCurrentPrefsFromFile("app.update.enabled")
			end if


			FirefoxExtUpdateStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxExtUpdateState")
			If FirefoxExtUpdateStateKey <> "" then
				RemoveCurrentPrefsFromFile("extensions.update.autoUpdate")
				RemoveCurrentPrefsFromFile("extensions.update.enabled")
			end if


			FirefoxJavaStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxJavaState")
			If FirefoxJavaStateKey = "1" then
				RemoveCurrentPrefsFromFile("security.enable_java")
			end if


			FirefoxJavascriptStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxJavascriptState")
			If FirefoxJavascriptStateKey = "1" then
				RemoveCurrentPrefsFromFile("javascript.enabled")
			end if


			FirefoxSSLStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxSSLState")
			If FirefoxSSLStateKey <> "" then
				RemoveCurrentPrefsFromFile("security.enable_ssl2")
				RemoveCurrentPrefsFromFile("security.enable_ssl3")
				RemoveCurrentPrefsFromFile("security.enable_tls")
			end if


			FirefoxIDNStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxIDNState")
			If FirefoxIDNStateKey <> "" then
				RemoveCurrentPrefsFromFile("network.enableIDN")
			end if


			FirefoxPasswordRememberKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxPasswordRememberState")
			If FirefoxPasswordRememberKey <> "" then
				RemoveCurrentPrefsFromFile("signon.rememberSignons")
			end if


			FirefoxTypeAheadFindKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTypeAheadFindState")
			If FirefoxTypeAheadFindKey <> "" then
				RemoveCurrentPrefsFromFile("accessibility.typeaheadfind")
			end if


			FirefoxPrefetchStateKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxPrefetchState")
			If FirefoxPrefetchStateKey <> "" then
				RemoveCurrentPrefsFromFile("network.prefetch-next")
			end if


			FirefoxSecurityCheckLoadUriKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxSecurityCheckLoadUri")
			If FirefoxSecurityCheckLoadUriKey <> "" then
				RemoveCurrentPrefsFromFile("security.checkloaduri")
			end if


			FirefoxTrustedAuthKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxTrustedAuth")
			FirefoxDelegatedAuthKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxDelegatedAuth")
			If FirefoxTrustedAuthKey <> "" or FirefoxDelegatedAuthKey <> "" then
				RemoveCurrentPrefsFromFile("network.negotiate-auth.trusted-uris")
				RemoveCurrentPrefsFromFile("network.negotiate-auth.delegation-uris")
			end if


			FirefoxCaretKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCaret")
			If FirefoxCaretKey <> "" then
				RemoveCurrentPrefsFromFile("accessibility.browsewithcaret")
			end if


			FirefoxCookieKey = WshShell.regread("HKLM\Software\Policies\Firefox\FirefoxCookieBehaviour")
			If FirefoxCookieKey <> "" then
				RemoveCurrentPrefsFromFile("network.cookie.cookieBehavior")
			end if

		end if
	next
end if


Function RemoveCurrentPrefsFromFile(removeSetting)
	Set ParsePrefsFile = fso.OpenTextFile(FirefoxPrefsFile, ForReading)

	' Get file content into an array:
	Dim aContents
	aContents = Split(ParsePrefsFile.ReadAll, vbCrLf)

	ParsePrefsFile.Close
	set ParsePrefsFile = Nothing

	' Parse Back In to Prefs.js file

	Dim aContentsNew
	aContentsNew = Filter(aContents, chr(34) & removeSetting & chr(34), False, vbTextCompare)

	' Overwrite the old file with the new file,
  	Set ParseOutPrefsFile = fso.OpenTextFile(FirefoxPrefsFile, ForWriting)
  	ParseOutPrefsFile.Write Join(aContentsNew, vbCrLf)
    	ParseOutPrefsFile.Close
End Function

Function AppendPrefsToFile(writeKey, writeData)
	set PrefsFile = fso.OpenTextFile(FirefoxPrefsFile,ForAppending)
	PrefsFile.Write ("user_pref(" & chr(34) & writeKey & chr(34) & ", " & writeData & ");" & vbNewLine)
	PrefsFile.Close
End Function