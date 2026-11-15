@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 (
  echo ERROR: The timer folder cannot be opened.
  pause
  exit /b 1
)
where node.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: Node.js was not found. Install Node.js 20 or newer before Sunday service.
  echo This launcher needs Node.js, but does NOT need an internet connection during use.
  pause
  exit /b 1
)
if not exist "server.mjs" goto missing_files
if not exist "assets\welcome.png" goto missing_files
if not exist "assets\background-clean.png" goto missing_files
if not exist "scripts\launch-local.mjs" goto missing_files

echo UBF Koeln Projector Timer - local offline launch
echo Keep this window open while using the projector.
echo Open the display with the button in the controller, then move it to the projector.
echo.
node "scripts\launch-local.mjs"
if errorlevel 1 (
  echo.
  echo Timer stopped with an error. Read the message above.
  pause
  exit /b 1
)
exit /b 0

:missing_files
echo ERROR: Required timer files are missing.
echo Extract the WHOLE ZIP before running Start-Timer.cmd.
pause
exit /b 1
