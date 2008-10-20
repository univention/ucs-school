@echo off
echo lokale boot.cmd gestartet > c:\boot.cmd.log
REM Die Systemvariable dcname kann über die NTconfig.pol gesetzt werden. Dies ist dann notwendig, wenn der dcname nicht dcNNN ist, wobei NNN die 3. bis 5. Stelle der Clientnamen ist, bspw. bei 4stelliger Schulnummer.
echo Systemvariable dcname ist "%dcname%" >> c:\boot.cmd.log
REM Wenn die Variable nicht gesetzt ist, dann wird sie (nur für dieses Skript) auf dcNNN gesetzt.
if "%dcname%"=="" SET dcname=dc%COMPUTERNAME:~2,3%
REM Hier wird die boot.cmd auf dcname aufgerufen. Als Parameter wird der gültige dc-Name mitgegeben und dies Ausgaben werden in c:\boot.cmd.log geschrieben.
if exist \\%dcname%\config\scripts\boot.cmd call \\%dcname%\config\scripts\boot.cmd %dcname% >> c:\boot.cmd.log
REM Falls obige Datei nicht existiert, wird die von dcNNN aufgerufen, bspw. wenn dcname per NTconfig.pol falsch gesetzt wurde. Als Parameter wird der gültige dc-Name mitgegeben und dies Ausgaben werden in c:\boot.cmd.log geschrieben.
if not exist \\%dcname%\config\scripts\boot.cmd if exist \\dc%COMPUTERNAME:~2,3%\config\scripts\boot.cmd call \\dc%COMPUTERNAME:~2,3%\config\scripts\boot.cmd dc%COMPUTERNAME:~2,3% >> c:\boot.cmd.log
