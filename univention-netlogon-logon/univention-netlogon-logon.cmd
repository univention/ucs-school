@echo off > NUL 2>&1
cls
net use x: %LOGONSERVER%\netlogonlog /persistent:no > NUL 2>&1
net use x: /d > NUL 2>&1
