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
python -m pip install pyinstaller
python -m pip install pillow

if exist dist\ReVork.exe (
    del /f /q dist\ReVork.exe
)

if exist ReVork.exe (
    del /f /q ReVork.exe
)

python -m PyInstaller --noconfirm --clean --onefile --windowed --name ReVork --icon static\logo.png --add-data "static\logo.png;static" native_app.py

if exist dist\ReVork.exe (
    copy /y dist\ReVork.exe ReVork.exe >nul
    echo [done] Built dist\ReVork.exe and ReVork.exe
) else (
    echo [error] EXE build failed.
    exit /b 1
)

endlocal
