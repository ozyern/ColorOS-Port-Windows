@echo off
setlocal

set "PYTHON_CMD="
where py >nul 2>nul && set "PYTHON_CMD=py"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
    echo [error] Python was not found in PATH.
    exit /b 1
)

if not exist .venv (
    echo [setup] Creating Python virtual environment...
    %PYTHON_CMD% -m venv .venv
)

call .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt

python app.py

endlocal
