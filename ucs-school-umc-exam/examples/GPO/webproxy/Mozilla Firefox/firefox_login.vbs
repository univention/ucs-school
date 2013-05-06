' FirefoxADM 0.4
' 2004/2005 Mark Sammons
' Internationalisation code contributed by Andrea Giorgini

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



' Do this:  For Each Dir within Firefox's profile, check for prefs.js, then write setting

' first, is there ANY profile?
' if not, create one!
if fso.FolderExists(FirefoxProfilePath) = false then
	if fsoFolderExists(EnVar("appdata") & "\Mozilla\Firefox") = false then
		if fsoFolderExists(EnVar("appdata") & "\Mozilla") = false then
			if fsoFolderExists(EnVar("appdata")) = false then
				FolderCreate = fso.CreateFolder(EnVar("appdata"))
			end if
			FolderCreate = fso.CreateFolder(EnVar("appdata") & "\Mozilla")
		end if
		FolderCreate = fso.CreateFolder(EnVar("appdata") & "\Mozilla\Firefox")
		Set FirefoxProfileIniFile = fso.CreateTextFile(Envar("appdata") & "\Mozilla\Firefox\profiles.ini")
		FirefoxProfileIniFile.WriteLine("[General]")
		FirefoxProfileIniFile.WriteLine("StartWithLastProfile=1")
		FirefoxProfileIniFile.WriteLine("")
		FirefoxProfileIniFile.WriteLine("[Profile0]")
		FirefoxProfileIniFile.WriteLine("Name=default")
		FirefoxProfileIniFile.WriteLine("IsRelative=1")
		FirefoxProfileIniFile.WriteLine("Path=Profiles/1nc1d3r.default")
		FirefoxProfileIniFile.Close
	end if
	FolderCreate = fso.CreateFolder(EnVar("appdata") & "\Mozilla\Firefox\Profiles")
	FolderCreate = fso.CreateFolder(EnVar("appdata") & "\Mozilla\Firefox\Profiles\1nc1d3r.default")
	Set FirefoxEmptyPrefsFile = fso.CreateTextFile(Envar("appdata") & "\Mozilla\Firefox\Profiles\1nc1d3r.default\prefs.js")
	FirefoxEmptyPrefsFile.Close
end if

			
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

			' Use IE's settings
			FirefoxUseIEKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxUseIESettings")
			if FirefoxUseIEKey = "1" then
				HomePageKey = WshShell.regread("HKCU\Software\Microsoft\Internet Explorer\Main\Start Page")
				If fso.FileExists(Envar("appdata") & "\Microsoft\Internet Explorer\Custom Settings\Custom0\install.ins") then

					Set IESettingFile = fso.OpenTextFile(Envar("appdata") & "\Microsoft\Internet Explorer\Custom Settings\Custom0\install.ins", ForReading)
					Do While Not IESettingFile.atEndOfStream
						ParseFileLine = IESettingFile.ReadLine
						If ParseFileLine <> "" then
							ParseSplitLine = Split(ParseFileLine,"=")
							if ParseSplitLine(0) = "Proxy_Enable" then
								' do nothing (set proxy type in later script?)
							Elseif ParseSplitLine(0) = "HTTP_Proxy_Server" then
								ParseSplitSetting = split(ParseSplitLine(1),":")
								HTTPKey = ParseSplitSetting(0)
								HTTPPortKey = ParseSplitSetting(1)
								if SameProxy = "1" then
									FTPKey = ParseSplitSetting(0)
									FTPPortKey = ParseSplitSetting(1)
									GopherKey = ParseSplitSetting(0)
									GopherPortKey = ParseSplitSetting(1)
									SSLKey = ParseSplitSetting(0)
									SSLPortKey = ParseSplitSetting(1)
									SOCKSKey = ParseSplitSetting(0)
									SOCKSPortKey = ParseSplitSetting(1)
								end if
							Elseif ParseSplitLine(0) = "FTP_Proxy_Server" and SameProxy <> "1" then
								ParseSplitSetting = split(ParseSplitLine(1),":")
								FTPKey = ParseSplitSetting(0)
								FTPPortKey = ParseSplitSetting(1)
							Elseif ParseSplitLine(0) = "Gopher_Proxy_Server" and SameProxy <> "1"  then
								ParseSplitSetting = split(ParseSplitLine(1),":")
								GopherKey = ParseSplitSetting(0)
								GopherPortKey = ParseSplitSetting(1)
							Elseif ParseSplitLine(0) = "Secure_Proxy_Server" and SameProxy <> "1"  then
								ParseSplitSetting = split(ParseSplitLine(1),":")
								SSLKey = ParseSplitSetting(0)
								SSLPortKey = ParseSplitSetting(1)
							Elseif ParseSplitLine(0) = "Socks_Proxy_Server" and SameProxy <> "1"  then
								ParseSplitSetting = split(ParseSplitLine(1),":")
								SOCKSKey = ParseSplitSetting(0)
								SOCKSPortKey = ParseSplitSetting(1)
							Elseif ParseSplitLine(0) = "Use_Same_Proxy" then
								if ParseSplitLine(1) = "1" then
									SameProxy="1"
								end if
							Elseif ParseSplitLine(0) = "Proxy_Override" then
								if ParseSplitLine(1) = "<local>" then
									ProxyExceptionsKey = "localhost, 127.0.0.1"
								Else
									ExceptionSplit = Split(ParseSplitLine(1),";")
									i = 1
									ProxyExceptionsKey = Right(ExceptionSplit(0), len(ExceptionSplit(0))-2)
									Do While ExceptionSplit(i) <> "<local>" & chr(34) or ExceptionSplit(i) = ""
										ProxyExceptionsKey = ProxyExceptionsKey + "," + ExceptionSplit(i)
										i = i + 1
									Loop
									ProxyExceptionsKey = ProxyExceptionsKey + ", localhost, 127.0.0.1"
								end if
							Elseif ParseSplitLine(0) = "AutoConfigJSURL" then
								ProxyURLKey = ParseSplitLine(1)
							End if
						End If
					Loop
					IESettingFile.Close
				end if			
			end if


			' homepage setting
			if FirefoxUseIEKey <> "1" then 
				HomePageKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxHomepage")
			end if
			if HomePageKey <> "" then
				RemoveCurrentPrefsFromFile("browser.startup.homepage")
				set HomePageSet = AppendPrefsToFile("browser.startup.homepage", chr(34) & HomePageKey & chr(34))
			end if


			' Automatic Image Resizing
			ImageResizeKey = WshShell.regread("HKCU\Software\Policies\Firefox\ImageResize")
			if ImageResizeKey <> "" then
				RemoveCurrentPrefsFromFile("browser.enable_automatic_image_resizing")
				if ImageResizeKey = "0" then
					set SearchEngineSet = AppendPrefsToFile("browser.enable_automatic_image_resizing", "false")
				else
					set SearchEngineSet = AppendPrefsToFile("browser.enable_automatic_image_resizing", "true")
				end if
			end if
		

			' Proxy Settings
			ProxyKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxProxy")
			if ProxyKey <> "" then
				if FirefoxUseIEKey <> "1" then
					ProxyURLKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxAutoProxyURL")
					HTTPKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxManualHTTP")
					HTTPPortKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxManualHTTPPort")
					SSLKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxManualSSL")
					SSLPortKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxManualSSLPort")
					FTPKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxManualFTP")
					FTPPortKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxManualFTPPort")
					GopherKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxManualGopher")
					GopherPortKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxManualGopherPort")
					SOCKSKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxManualSOCKS")
					SOCKSPortKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxManualSOCKSPort")
					ProxyExceptionsKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxProxyExceptions")
				end if
				SOCKSVersionKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxManualSOCKSVersion")
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
				if ProxyURLKey <> "" then
					set ProxyURLSet = AppendPrefsToFile("network.proxy.autoconfig_url", chr(34) & ProxyURLKey & chr(34))
				end if
				if HTTPKey <> "" then
					set HTTPSet = AppendPrefsToFile("network.proxy.http", chr(34) & HTTPKey & chr(34))
					HTTPSet = AppendPrefsToFile("network.proxy.http_port", HTTPPortKey)
				end if
				if SSLKey <> "" then
					set SSLSet = AppendPrefsToFile("network.proxy.ssl", chr(34) & SSLKey & chr(34))
					SSLSet = AppendPrefsToFile("network.proxy.ssl_port", SSLPortKey)
				end if
				if FTPKey <> "" then
					set FTPSet = AppendPrefsToFile("network.proxy.ftp", chr(34) & FTPKey & chr(34))
					FTPSet = AppendPrefsToFile("network.proxy.ftp_port", FTPPortKey)
				end if
				if GopherKey <> "" then
					set GopherSet = AppendPrefsToFile("network.proxy.gopher", chr(34) & GopherKey & chr(34))
					GopherSet = AppendPrefsToFile("network.proxy.gopher_port", GopherPortKey)
				end if
				if SOCKSKey <> "" then
					set SOCKSSet = AppendPrefsToFile("network.proxy.socks", chr(34) & SOCKSKey & chr(34))
					SOCKSSet = AppendPrefsToFile("network.proxy.socks_port", SOCKSPortKey)
					SOCKSSet = AppendPrefsToFile("network.proxy.socks_version", SOCKSVersionKey)
				end if
				if ProxyExceptionsKey <> "localhost, 127.0.0.1" or ProxyExceptions <> "" then
					set ExceptionsSet = AppendPrefsToFile("network.proxy.no_proxies_on", chr(34) & ProxyExceptionsKey & chr(34))
				end if
				set ProxySet = AppendPrefsToFile("network.proxy.type", ProxyKey)
			end if


			' Cache
			FirefoxCacheKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxCacheSize")
			if FirefoxCacheKey <> "" then
				RemoveCurrentPrefsFromFile("browser.cache.disk.capacity")
				set CacheSet = AppendPrefsToFile("browser.cache.disk.capacity", FirefoxCacheKey)
			end if


			' Check Default Browser
			FirefoxCheckDefaultKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxCheckDefault")
			if FirefoxCheckDefaultKey = "0" then
				RemoveCurrentPrefsFromFile("browser.shell.checkDefaultBrowser")
				set DefaultSet = AppendPrefsToFile("browser.shell.checkDefaultBrowser", "false")
			Elseif FirefoxCheckDefaultKey = "1" then
				RemoveCurrentPrefsFromFile("browser.shell.checkDefaultBrowser")
				set DefaultSet = AppendPrefsToFile("browser.shell.checkDefaultBrowser", "true")
			end if


			' Disable XPI Installations?
			FirefoxXPIStateKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxXPIState")
			if FirefoxXPIStateKey = "0" then
				RemoveCurrentPrefsFromFile("xpinstall.dialog.confirm")
				RemoveCurrentPrefsFromFile("xpinstall.enabled")
				RemoveCurrentPrefsFromFile("xpinstall.dialog.progress.chrome")
				RemoveCurrentPrefsFromFile("xpinstall.dialog.progress.skin")
				RemoveCurrentPrefsFromFile("xpinstall.dialog.progress.type.chrome")
				RemoveCurrentPrefsFromFile("xpinstall.dialog.progress.type.skin")
				set XPISet = AppendPrefsToFile("xpinstall.enabled", "false")
				set XPIDialog = AppendPrefsToFile("xpinstall.dialog.confirm", chr(34) & "sorry-installation-permission-denied" & chr(34))
				set XPIDialog2 = AppendPrefsToFile("xpinstall.dialog.progress.chrome", chr(34) & "sorry-installation-permission-denied" & chr(34))
				set XPIDialog3 = AppendPrefsToFile("xpinstall.dialog.progress.skin", chr(34) & "sorry-installation-permission-denied" & chr(34))
				set XPIDialog4 = AppendPrefsToFile("xpinstall.dialog.progress.type.chrome", chr(34) & "sorry-installation-permission-denied" & chr(34))
				set XPIDialog5 = AppendPrefsToFile("xpinstall.dialog.progress.type.skin", chr(34) & "sorry-installation-permission-denied" & chr(34))
			Elseif FirefoxXPIStateKey = "1" then
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
				if FirefoxDownloadLocationKey = "My Documents" then
					MyDownloadLocation = WshShell.regread("HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders\Personal")
				Elseif FirefoxDownloadLocationKey = "Desktop" then
					MyDownloadLocation = WshShell.regread("HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders\Desktop")
				Elseif FirefoxDownloadLocationKey = "Set" then
					MyDownloadLocation = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxDownloadLocation")
				Elseif FirefoxDownloadLocationKey = "Home Drive" then
					MyDownloadLocation = "%homedrive%"
				end if

				' check for environment variables
				MyDownloadLocation = Replace(MyDownloadLocation, "%homeshare%", EnVar("homeshare"), 1, -1, 1)
				MyDownloadLocation = Replace(MyDownloadLocation, "%homepath%", EnVar("homepath"), 1, -1, 1)
				MyDownloadLocation = Replace(MyDownloadLocation, "%userprofile%", EnVar("userprofile"), 1, -1, 1)
				MyDownloadLocation = Replace(MyDownloadLocation, "%username%", EnVar("username"), 1, -1, 1)
				MyDownloadLocation = Replace(MyDownloadLocation, "%homedrive%", EnVar("homedrive"), 1, -1, 1)

				DownloadLocation = Replace(MyDownloadLocation,"\","\\")

				RemoveCurrentPrefsFromFile("browser.download.defaultFolder")
				RemoveCurrentPrefsFromFile("browser.download.dir")
				set DownloadDefaultSet = AppendPrefsToFile("browser.download.defaultFolder", chr(34) & DownloadLocation & chr(34))
				set DownloadDirSet = AppendPrefsToFile("browser.download.dir", chr(34) & DownloadLocation & chr(34))
			end if


			' mandatory bookmarks location
			FirefoxBookmarksKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxMandatoryBookmarks")
			if FirefoxBookmarksKey <> "" then
				if fso.FileExists(FirefoxBookmarksKey) then
					fso.CopyFile FirefoxBookmarksKey, FirefoxProfilePath & "\" & FirefoxFolder.Name & "\bookmarks.html"
				end if
			end if


			' host permssions file
			FirefoxPermissionsFileKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxPermissionsFile")
			if FirefoxPermissionsFile <> "" then
				if fso.FileExists(FirefoxPermissionsFile) then
					fso.CopyFile FirefoxPermissionsFile, FirefoxProfilePath & "\" & FirefoxFolder.Name & "\hostperm.1"
				end if
			end if

			
			' Firefox certificates
			FirefoxCertificatesLocationKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxCertificateLocation")
			if FirefoxCertificatesLocationKey <> "" then
				FirefoxMandatoryCertificatesKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxMandatoryCertificates")
				If FirefoxMandatoryCertificatesKey = "Merge" then
					if fso.FileExists(FirefoxProfilePath & "\" & FirefoxFolder.Name & "\cert8.db") = false then
						if fso.FileExists(FirefoxCertificatesLocationKey & "\cert8.db") then
							fso.CopyFile FirefoxCertificatesLocationKey & "\cert8.db", FirefoxProfilePath & "\" & FirefoxFolder.Name & "\cert8.db"
						end if
					end if
					if fso.FileExists(FirefoxProfilePath & "\" & FirefoxFolder.Name & "\key3.db") = false then
						if fso.FileExists(FirefoxCertificatesLocationKey & "\key3.db") then
							fso.CopyFile FirefoxCertificatesLocationKey & "\key3.db", FirefoxProfilePath & "\" & FirefoxFolder.Name & "\key3.db"
						end if
					end if
					if fso.FileExists(FirefoxProfilePath & "\" & FirefoxFolder.Name & "\secmod.db") = false then
						if fso.FileExists(FirefoxCertificatesLocationKey & "\secmod.db") then
							fso.CopyFile FirefoxCertificatesLocationKey & "\secmod.db", FirefoxProfilePath & "\" & FirefoxFolder.Name & "\secmod.db"
						end if
					end if
				Else
					if fso.FileExists(FirefoxCertificatesLocationKey & "\cert8.db") then
						fso.CopyFile FirefoxCertificatesLocationKey & "\cert8.db", FirefoxProfilePath & "\" & FirefoxFolder.Name & "\cert8.db"
					end if
					if fso.FileExists(FirefoxCertificatesLocationKey & "\key3.db") then
						fso.CopyFile FirefoxCertificatesLocationKey & "\key3.db", FirefoxProfilePath & "\" & FirefoxFolder.Name & "\key3.db"
					end if
					if fso.FileExists(FirefoxCertificatesLocationKey & "\secmod.db") then
						fso.CopyFile FirefoxCertificatesLocationKey & "\secmod.db", FirefoxProfilePath & "\" & FirefoxFolder.Name & "\secmod.db"
					end if
				end if
			end if


			' popups & install sites whitelist file
			FirefoxPopupsWhitelistKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxPopupWhitelist")
			FirefoxInstallWhitelistKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxInstallWhitelist")
			if FirefoxPopupsWhitelistKey <> "" and FirefoxInstallWhitelistKey <> "" then
				set hostperm1File = fso.OpenTextFile(FirefoxProfilePath & "\" & FirefoxFolder.Name & "\hostperm.1", ForWriting)
				if FirefoxPopupsWhitelistKey <> "" and FirefoxPopupsWhitelistKey <> "NONE" then
					Dim popups
					popups = split(FirefoxPopupsWhitelistKey, ";")
					For Each popup in popups
						hostperm1File.Write ("host" & chr(9) & "popup" & chr(9) & "1" & chr(9) & popup & chr(10))
					next
				end if
				if FirefoxInstallWhitelistKey <> "" and FirefoxInstallWhitelistKey <> "NONE" then
					Dim installsites
					installsites = split(FirefoxInstallWhitelistKey, ";")
					For Each installsite in installsites
						hostperm1File.Write ("host" & chr(9) & "install" & chr(9) & "1" & chr(9) & installsite & chr(10))
					next
				end if
				hostperm1File.close
			end if

		
			' Enable Type Ahead Find
			FirefoxTypeAheadFindKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxTypeAheadFindState")
			If FirefoxTypeAheadFindKey = "1" then
				RemoveCurrentPrefsFromFile("accessibility.typeaheadfind")
				set FirefoxTypeAheadFindSet = AppendPrefsToFile("accessibility.typeaheadfind", "true")
			ElseIf FirefoxTypeAheadFindKey = "0" then
				RemoveCurrentPrefsFromFile("accessibility.typeaheadfind")
				set FirefoxTypeAheadFindSet = AppendPrefsToFile("accessibility.typeaheadfind", "false")
			end if


			' Set Cache to Local
			FirefoxLocalCacheKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxCacheLocal")
			If FirefoxLocalCacheKey = "1" then
				RemoveCurrentPrefsFromFile("browser.cache.disk.parent_directory")
				set FirefoxLocalCacheSet = AppendPrefsToFile("browser.cache.disk.parent_directory", chr(34) & EnVar("userprofile") & "\Local Settings" & chr(34))
			ElseIf FirefoxLocalCacheKey = "0" then
				RemoveCurrentPrefsFromFile("browser.cache.disk.parent_directory")
			end if


			' Browse with Caret
			FirefoxCaretKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxCaret")
			If FirefoxCaretKey = "1" then
				RemoveCurrentPrefsFromFile("accessibility.browsewithcaret")
				set FirefoxCaretSet = AppendPrefsToFile("accessibility.browsewithcaret", "true")
			ElseIf FirefoxCaretKey = "0" then
				RemoveCurrentPrefsFromFile("accessibility.browsewithcaret")
				set FirefoxCaretSet = AppendPrefsToFile("accessibility.browsewithcaret", "false")
			end if
			

			' CAPS sites
			FirefoxFileSitesKey = WshShell.regread("HKCU\Software\Policies\Firefox\FirefoxFileSites")
			if FirefoxFileSitesKey <> "" then
				AppendSitesToFile(FirefoxFileSitesKey)
			End if


			' TODO:  More settings!




	
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

Function AppendSitesToFile(sites)
	set PrefsFile = fso.OpenTextFile(FirefoxPrefsFile,ForAppending)
	PrefsFile.Write ("user_pref(" & chr(34) & "capability.policy.localfilelinks.checkloaduri.enabled" & chr(34) & ", " & chr(34) & "allAccess" & chr(34) & ");" & vbNewLine)
	PrefsFile.Write ("user_pref(" & chr(34) & "capability.policy.localfilelinks.sites" & chr(34) & ", " & chr(34) & sites & chr(34) & ");" & vbNewLine)
	PrefsFile.Write ("user_pref(" & chr(34) & "capability.policy.policynames" & chr(34) & ", " & chr(34) & "localfilelinks" & chr(34) & ");" & vbNewLine)
	PrefsFile.Close
End Function