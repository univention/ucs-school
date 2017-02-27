Set WshShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")
strLinkPath = WshShell.SpecialFolders("Desktop") & "\Univention Management Console.URL"
If Not objFSO.FileExists(strLinkPath) Then
    Set oUrlLink = WshShell.CreateShortcut(strLinkPath)
    oUrlLink.TargetPath = "{umc_link}"
    oUrlLink.Save
    set objFile = objFSO.OpenTextFile(strLinkPath, 8, True)
    objFile.WriteLine("IconFile=\\{hostname}.{domainname}\netlogon\user\univention-management-console.ico")
    objFile.WriteLine("IconIndex=0")
    objFile.Close
End If
