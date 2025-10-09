@echo off
setlocal

if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate

rem Install runtime + build deps
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
pip install -r requirements-dev.txt

rem Clean previous build artifacts to avoid stale bootloader paths
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller --clean --noconfirm --name CryptoTicker --windowed ^
  --collect-all PySide6 ^
  --collect-all certifi ^
  --hidden-import truststore ^
  --hidden-import PySide6.QtCharts ^
  --hidden-import PySide6.QtWebSockets ^
  app\main.py

echo.
echo Build complete. See dist\CryptoTicker\CryptoTicker.exe
if exist dist\CryptoTicker\_internal\python313.dll (
  echo Verified: python313.dll packaged under _internal.
) else (
  echo Warning: python313.dll not found. Build likely failed. See build logs.
)

endlocal
