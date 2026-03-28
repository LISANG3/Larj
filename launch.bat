@echo off
REM Larj Launcher for Windows
REM This script checks dependencies and launches Larj

echo ========================================
echo Larj - Windows Desktop Efficiency Tool
echo ========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Check if dependencies are installed
echo Checking dependencies...
python -c "import PyQt5" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] PyQt5 not found, installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

echo [OK] Dependencies installed
echo.

if not exist "everything\Everything64.dll" (
    if not exist "everything\Everything32.dll" (
        echo [WARN] Everything SDK DLL not found in everything\ directory
        echo Search may not work until you place Everything64.dll or Everything32.dll.
        echo Download SDK: https://www.voidtools.com/Everything-SDK.zip
        echo.
    )
)

REM Launch Larj
echo Starting Larj...
echo.
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Larj failed to start
    echo Check logs\ directory for error details
    pause
)
