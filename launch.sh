#!/bin/bash
# Larj Launcher for Linux/Mac (development/testing only)
# Note: Larj is primarily designed for Windows

echo "========================================"
echo "Larj - Windows Desktop Efficiency Tool"
echo "========================================"
echo ""

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "[OK] Python 3 found"
echo ""

# Check if dependencies are installed
echo "Checking dependencies..."
python3 -c "import PyQt5" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[WARN] PyQt5 not found, installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies"
        exit 1
    fi
fi

echo "[OK] Dependencies installed"
echo ""

# Warning for non-Windows platforms
if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
    echo "[WARN] Larj is designed for Windows"
    echo "Some features may not work on this platform"
    echo ""
fi

# Launch Larj
echo "Starting Larj..."
echo ""
python3 main.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Larj failed to start"
    echo "Check logs/ directory for error details"
fi
