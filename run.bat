@echo off
setlocal

if not exist .venv (
    echo Creating virtual environment...
    py -3 -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
python -m app.main

endlocal
