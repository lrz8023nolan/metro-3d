@echo off
rem metro-3d - one-click build + open the city index (Windows)
rem Requires Python 3.10+ in PATH. Docs: docs/usage.zh-CN.md
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
  pause
  exit /b 1
)
echo Building all cities under cities\ ...
python scripts\build.py --all
if errorlevel 1 (
  echo.
  echo [ERROR] Build failed. See the messages above.
  pause
  exit /b 1
)
echo Done. Opening dist\index.html ...
start "" "dist\index.html"
