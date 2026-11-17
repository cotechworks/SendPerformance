@echo off
setlocal
cd /d "%~dp0"
if not exist "dist" mkdir "dist"
if errorlevel 1 exit /b %errorlevel%
".venv\Scripts\python.exe" -c "from PIL import Image; image = Image.open('icon.png'); image.save('dist/SendPerformance.ico', format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]); image.close()"
if errorlevel 1 exit /b %errorlevel%
".venv\Scripts\python.exe" -m nuitka ^
  --mode=standalone ^
  --windows-icon-from-ico=dist/SendPerformance.ico ^
  --windows-console-mode=attach ^
  --include-module=pystray._win32 ^
  --enable-plugin=tk-inter ^
  --include-data-files=icon.png=icon.png ^
  --output-dir=dist ^
  --assume-yes-for-downloads ^
  SendPerformance.py
exit /b %errorlevel%
