@echo off
setlocal EnableExtensions

set "APP_NAME=CryptoTicker"
set "ENTRYPOINT=app\main.py"
set "DIST_DIR=dist\%APP_NAME%"
set "INTERNAL_DIR=%DIST_DIR%\_internal"
set "ENSURE_DLLS_PS1=scripts\ensure_dlls.ps1"

set QT_DEBUG_PLUGINS=1

if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate

python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
pip install -r requirements-dev.txt
if errorlevel 1 exit /b %errorlevel%

pyinstaller --log-level DEBUG --noconfirm --name %APP_NAME% --windowed ^
  --runtime-hook scripts\pyi_rth_dll_search_path.py ^
  --collect-all PySide6 ^
  --collect-all shiboken6 ^
  --collect-all certifi ^
  --hidden-import truststore ^
  --hidden-import PySide6.QtCharts ^
  --hidden-import PySide6.QtWebSockets ^
  %ENTRYPOINT%
if errorlevel 1 exit /b %errorlevel%

for /f "usebackq delims=" %%I in (`python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])"`) do set "SITE_PACKAGES=%%I"
if not exist "%ENSURE_DLLS_PS1%" (
  echo Warning: missing helper script "%ENSURE_DLLS_PS1%"
) else (
  if not exist "%INTERNAL_DIR%" (
    echo Warning: build output not found: "%INTERNAL_DIR%"
  ) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%ENSURE_DLLS_PS1%" -SourceRoot "%SITE_PACKAGES%" -DestRoot "%INTERNAL_DIR%" -Pattern "*.dll"
    if errorlevel 1 exit /b %errorlevel%

    for %%D in (libcrypto-3.dll libssl-3.dll libcrypto-3-x64.dll libssl-3-x64.dll) do (
      if exist "%INTERNAL_DIR%\\%%D" copy /y "%INTERNAL_DIR%\\%%D" "%DIST_DIR%\\%%D" >nul
    )
  )
)

echo Debug build complete. Check build\CryptoTicker\warn-CryptoTicker.txt for hook logs.
endlocal
