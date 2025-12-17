@echo off
setlocal EnableExtensions

set "APP_NAME=CryptoTicker"
set "ENTRYPOINT=app\main.py"
set "DIST_DIR=dist\%APP_NAME%"
set "INTERNAL_DIR=%DIST_DIR%\_internal"
set "ENSURE_DLLS_PS1=scripts\ensure_dlls.ps1"

if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate

rem Install runtime + build deps
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
pip install -r requirements-dev.txt
if errorlevel 1 exit /b %errorlevel%

rem Clean previous build artifacts to avoid stale bootloader paths
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller --clean --noconfirm --name %APP_NAME% --windowed ^
  --runtime-hook scripts\pyi_rth_dll_search_path.py ^
  --collect-all PySide6 ^
  --collect-all shiboken6 ^
  --collect-all certifi ^
  --hidden-import truststore ^
  --hidden-import PySide6.QtCharts ^
  --hidden-import PySide6.QtWebSockets ^
  %ENTRYPOINT%
if errorlevel 1 exit /b %errorlevel%

rem Ensure all *.dll under the venv site-packages are present in dist (PyInstaller may miss some lazily-loaded DLLs)
for /f "usebackq delims=" %%I in (`python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])"`) do set "SITE_PACKAGES=%%I"
if not exist "%ENSURE_DLLS_PS1%" (
  echo Error: missing helper script "%ENSURE_DLLS_PS1%"
  exit /b 1
)
if not exist "%INTERNAL_DIR%" (
  echo Error: build output not found: "%INTERNAL_DIR%"
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%ENSURE_DLLS_PS1%" -SourceRoot "%SITE_PACKAGES%" -DestRoot "%INTERNAL_DIR%" -Pattern "*.dll"
if errorlevel 1 exit /b %errorlevel%

rem Put OpenSSL DLLs next to the EXE too (Windows loader prefers EXE directory; avoids picking up incompatible OpenSSL from PATH on other PCs)
for %%D in (libcrypto-3.dll libssl-3.dll libcrypto-3-x64.dll libssl-3-x64.dll) do (
  if exist "%INTERNAL_DIR%\\%%D" copy /y "%INTERNAL_DIR%\\%%D" "%DIST_DIR%\\%%D" >nul
)

echo.
echo Build complete. See %DIST_DIR%\%APP_NAME%.exe
for /f "usebackq delims=" %%I in (`python -c "import sys; print(f\"python{sys.version_info.major}{sys.version_info.minor}.dll\")"`) do set "PYTHON_DLL=%%I"
if exist "%INTERNAL_DIR%\%PYTHON_DLL%" (
  echo Verified: %PYTHON_DLL% packaged under _internal.
) else (
  echo Warning: %PYTHON_DLL% not found under _internal.
)
if exist "%DIST_DIR%\libcrypto-3.dll" (
  echo Verified: OpenSSL DLLs copied next to EXE.
) else (
  echo Warning: OpenSSL DLLs not present next to EXE.
)
if exist "%INTERNAL_DIR%\PySide6\plugins\platforms\qwindows.dll" (
  echo Verified: Qt platform plugin ^(qwindows.dll^) packaged.
) else (
  echo Warning: Qt platform plugin ^(qwindows.dll^) missing.
)

endlocal
