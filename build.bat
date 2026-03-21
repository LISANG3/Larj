@echo off
setlocal
chcp 65001 >nul

echo ========================================
echo Larj Build Script
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Ensure pip is available
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not available.
    pause
    exit /b 1
)

REM Check PyInstaller
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

REM Clean old artifacts
echo [STEP 1/3] Cleaning old build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM Build
echo [STEP 2/3] Building with PyInstaller...
python -m PyInstaller larj.spec --clean
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

REM Done
echo [STEP 3/3] Build completed.
echo.
echo Output: dist\Larj.exe
echo.

set /p run=Run now? (y/n): 
if /i "%run%"=="y" (
    start "" "dist\Larj.exe"
)

pause
