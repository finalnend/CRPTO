@echo off
setlocal

set QT_DEBUG_PLUGINS=1

if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate

python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
pip install -r requirements-dev.txt

pyinstaller --log-level DEBUG --noconfirm --name CryptoTicker --windowed ^
  --collect-all PySide6 ^
  --collect-all certifi ^
  --hidden-import truststore ^
  --hidden-import PySide6.QtCharts ^
  --hidden-import PySide6.QtWebSockets ^
  app\main.py

echo Debug build complete. Check build\CryptoTicker\warn-CryptoTicker.txt for hook logs.
endlocal
