@echo off
setlocal
cd /d "%~dp0"
echo UBF Koeln Timer - NUR TESTBETRIEB. Kein Sonntags-Release.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Verify-Windows-Rehearsal.ps1" -Launch
if errorlevel 1 (
  echo.
  echo PRUEFUNG ODER START FEHLGESCHLAGEN. Nicht fortfahren.
  pause
  exit /b 1
)
echo.
echo Lokaler Probestart abgeschlossen. Ergebnisse W01-W08 getrennt erfassen.
pause
