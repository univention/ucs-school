reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\DomainCache" /v SCHULE
if errorlevel 1 echo nicht in Domäne SCHULE
if errorlevel 1 goto :eof
REM Oben wurde geprüft, ob der PC bereits in der Domäne Schule ist und falls nicht abgebrochen. Dies soll verhindern, dass das Post-Deploy gestört wird.
echo boot cmd auf dc gestartet
if "%1"=="" echo kein Parameter (dc)
if "%1"=="" echo boot cmd auf dc gestartet ohne Parameter >> c:\boot.cmd.log
if not "%1"=="" echo Parameter ist "%1"
REM Hier wird für diese Datei die Variable dctemp nutzbar gemacht. Sie ist wenn verfügbar der 1. Aufrufparameter und anderenfalls wird sie aus dem Computernamen gebildet.
Set dctemp=%1
if "%dctemp%"=="" Set dctemp=dc%COMPUTERNAME:~2,3%
echo dctemp ist "%dctemp%"
echo Systemvaiable dcname ist "%dcname%"
REM Wenn das Skript ohne Parameter gestartet wurde, dann wird die boot.cmd durch die bootclient.cmd ersetzt. Dies soll auch das logging vereinheitlichen.
if "%1"=="" if exist \\dc%COMPUTERNAME:~2,3%\config\scripts\bootclient.cmd copy /Y \\dc%COMPUTERNAME:~2,3%\config\scripts\bootclient.cmd "C:\WINDOWS\system32\GroupPolicy\Machine\Scripts\Startup\boot.cmd" >> c:\boot.cmd.log
REM Die weiteren Skripte werden mit dem gültigen DC-Namen als Parameter gestartet.
net user Lehrer Sf22reS3
echo starte swassign.cmd
call \\%dctemp%\config\scripts\swassign.cmd %dctemp%
echo starte boots3.cmd
call \\%dctemp%\config\scripts\boots3.cmd %dctemp%
echo starte sophos.cmd
call \\%dctemp%\config\scripts\sophos.cmd %dctemp%
echo boot.cmd beendet
