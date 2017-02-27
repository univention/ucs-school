Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = FolderPath + "\{share}.LNK"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "\\{server}\{share}"
oLink.IconLocation = "{other_links_icon}"
oLink.Save
