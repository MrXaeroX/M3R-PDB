@echo off
::------------------------------------------------------------------------------
:: Our copyright message will be here.
::------------------------------------------------------------------------------
setlocal
set project_dir=%~dp0
set pause_on_exit=0
echo %cmdcmdline% | find /i "%~0" >nul
if not errorlevel 1 set pause_on_exit=1
set PYTHONDONTWRITEBYTECODE=1

:: Defer control.
python "%project_dir%\m3rpdb.py" %*
if _%pause_on_exit%_==_1_ pause
