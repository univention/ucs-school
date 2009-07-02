@echo off & setlocal
::For Windows NT 4.0 users only!!!
::Creates LNK and PIF files from the command line.
::Author: Walter Zackery
if not %1[==[ if exist %1 goto start
echo You must pass the path of a file or folder to the
echo batch file as a shortcut target.
if not %1[==[ echo %1 is not an existing file or folder
(pause & endlocal & goto:eof)
:start
(set hkey=HKEY_CURRENT_USER\Software\Microsoft\Windows)
(set hkey=%hkey%\CurrentVersion\Explorer\Shell Folders)
(set inf=rundll32 setupapi,InstallHinfSection DefaultInstall)
start/w regedit /e %temp%\#57#.tmp "%hkey%"

for /f "tokens=*" %%? in (
'dir/b/a %1? 2^>nul') do (set name=%%~nx?)

for /f "tokens=2* delims==" %%? in (
'findstr/b /i """desktop"""= %temp%\#57#.tmp') do (set d=%%?)

for /f "tokens=2* delims==" %%? in (
'findstr/b /i """programs"""= %temp%\#57#.tmp') do (set p=%%?)

(set d=%d:\\=\%) & (set p=%p:\\=\%)
if not %2[==[ if exist %~fs2\nul (set d=%~fs2)
if not %2[==[ if exist %~fs2nul (set d=%~fs2)
set x=if exist %2\nul
if not %2[==[ if not %d%==%2 %x% if "%~p2"=="\" set d=%2
echo %d%?find ":\" >nul??(set d=%d%\)
(set file=""""""%1"""""")
for /f "tokens=1 delims=:" %%? in ("%file:"=%") do set drive=%%?
(set progman=setup.ini, progman.groups,,)
echo > %temp%\#k#.inf [version]
echo >>%temp%\#k#.inf signature=$chicago$
echo >>%temp%\#k#.inf [DefaultInstall]
echo >>%temp%\#k#.inf UpdateInis=Addlink
echo >>%temp%\#k#.inf [Addlink]
echo >>%temp%\#k#.inf %progman% ""group200="}new{"""
echo >>%temp%\#k#.inf setup.ini, group200,, """%name%"",%file%
start/w %inf% 132 %temp%\#k#.inf
del %temp%\#k#.inf %temp%\#57#.tmp
move %p%\"}new{\*.*" %d% >nul 2>&1
rd %p%\}new{ 2>nul
move %p%\}new{.lnk %d%\"drive %drive%.lnk" >nul 2>&1
endlocal