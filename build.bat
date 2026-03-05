@echo off
chcp 65001 >nul
echo ========================================
echo Larj 打包脚本
echo ========================================
echo.

REM 检查 Python 环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

REM 检查 PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [信息] 正在安装 PyInstaller...
    pip install pyinstaller
)

REM 清理旧的构建文件
echo [步骤 1/3] 清理旧的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM 开始打包
echo [步骤 2/3] 开始打包...
pyinstaller larj.spec --clean

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo [步骤 3/3] 打包完成！
echo.
echo 输出文件: dist\Larj.exe
echo.

REM 询问是否运行
set /p run="是否立即运行？(y/n): "
if /i "%run%"=="y" (
    start "" "dist\Larj.exe"
)

pause
