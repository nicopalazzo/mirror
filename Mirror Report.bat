@echo off
rem Opens your latest Mirror report in the browser. No questions after the first run. Nothing is sent anywhere.
setlocal
cd /d "%~dp0"

set "TEST=0"
if "%~1"=="--test" set "TEST=1"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto nopython

if "%TEST%"=="1" goto testmode

%PY% mirror.py report --open
goto end


:testmode
%PY% mirror.py report --yes
exit /b %errorlevel%

:nopython
echo Mirror needs Python 3.8 or newer, and I could not find it.
echo Install it from https://www.python.org/downloads/ and double-click this file again.

:end
if not "%TEST%"=="1" pause
