@echo off
setlocal

if exist ReVork.exe (
    echo [launch] Starting ReVork.exe...
    start "" "ReVork.exe"
    goto :EOF
)

if exist dist\ReVork.exe (
    echo [launch] Starting packaged EXE...
    start "" "dist\ReVork.exe"
    goto :EOF
)

if exist dist\ReVorkPortStudio.exe (
    echo [launch] Starting packaged EXE...
    start "" "dist\ReVorkPortStudio.exe"
    goto :EOF
)

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

python native_app.py

endlocal
