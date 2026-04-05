@echo off
setlocal

if not exist .venv (
    echo [setup] Creating Python virtual environment...
    py -m venv .venv
)

call .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt

python app.py

endlocal
