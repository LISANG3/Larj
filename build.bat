@echo off
setlocal
chcp 65001 >nul

echo ========================================
echo Larj Build Script
echo ========================================
echo.

REM Version source file
set "version_file=VERSION"
if not exist "%version_file%" (
    echo 0.1.0>"%version_file%"
)

set /p current_version=<"%version_file%"
for /f "tokens=* delims= " %%i in ("%current_version%") do set "current_version=%%i"
if "%current_version%"=="" set "current_version=0.1.0"

for /f "tokens=1-3 delims=." %%a in ("%current_version%") do (
    set /a major=%%a 2>nul
    set /a minor=%%b 2>nul
    set /a patch=%%c 2>nul
)
if not defined major set "major=0"
if not defined minor set "minor=1"
if not defined patch set "patch=0"

echo Current version: %major%.%minor%.%patch%
echo Select version bump type:
echo   1^) patch  ^(x.y.z -^> x.y.z+1^) [default]
echo   2^) minor  ^(x.y.z -^> x.y+1.0^)
echo   3^) major  ^(x.y.z -^> x+1.0.0^)
echo   4^) keep current version
echo   5^) manual input full version
set "bump_choice="
set /p bump_choice=Choose [1-5] (default 1): 
if "%bump_choice%"=="" set "bump_choice=1"

if "%bump_choice%"=="1" (
    set /a patch+=1
) else if "%bump_choice%"=="2" (
    set /a minor+=1
    set "patch=0"
) else if "%bump_choice%"=="3" (
    set /a major+=1
    set "minor=0"
    set "patch=0"
) else if "%bump_choice%"=="4" (
    rem keep current
) else if "%bump_choice%"=="5" (
    set "manual_version="
    set /p manual_version=Please enter version, e.g. 1.2.3: 
    if "%manual_version%"=="" (
        echo [ERROR] Manual version cannot be empty.
        pause
        exit /b 1
    )
    set "version=%manual_version%"
) else (
    echo [ERROR] Invalid choice: %bump_choice%
    pause
    exit /b 1
)

REM Basic sanitize for filename safety
if not defined version (
    set "version=%major%.%minor%.%patch%"
)
set "version=%version: =%"
set "version=%version:/=-%"
set "version=%version:\=-%"
set "version=%version::=-%"
if "%version%"=="" (
    echo [ERROR] Version cannot be empty after sanitize.
    pause
    exit /b 1
)

set "output_exe=Larj_v%version%.exe"
echo New version: %version%
echo %version%>"%version_file%"

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
if not exist "dist\Larj.exe" (
    echo [ERROR] Expected output dist\Larj.exe was not found.
    pause
    exit /b 1
)

if exist "dist\%output_exe%" del /f /q "dist\%output_exe%"
ren "dist\Larj.exe" "%output_exe%"
echo Output: dist\%output_exe%
echo.

set /p run=Run now? (y/n): 
if /i "%run%"=="y" (
    start "" "dist\%output_exe%"
)

pause
