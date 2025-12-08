@echo off
REM AI-Assistant Launcher
REM This script ensures all Python dependencies are available before running the app

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org
    pause
    exit /b 1
)

echo Installing/updating dependencies...
pip install --upgrade -q -r requirements.txt 2>nul

echo Launching AI-Assistant...
python main.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start the application
    echo Please ensure:
    echo 1. Python 3.11+ is installed
    echo 2. All requirements are installed: pip install -r requirements.txt
    echo 3. You have valid API keys in the settings
    pause
)
