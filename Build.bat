@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -m nuitka ^
  --mode=standalone ^
  --windows-console-mode=attach ^
  --include-module=pystray._win32 ^
  --include-data-files=icon.png=icon.png ^
  --output-dir=dist ^
  --assume-yes-for-downloads ^
  SendPerformance.py
exit /b %errorlevel%
