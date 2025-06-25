@echo off
echo 🚀 Starting Analytics Dashboard Server...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo 📦 Please install Python from https://python.org
    pause
    exit /b 1
)

REM Check if requirements are installed
python -c "import flask, flask_cors, requests, dotenv, waitress" >nul 2>&1
if errorlevel 1 (
    echo 📦 Installing required packages for Windows...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install requirements
        echo 💡 Try: pip install flask flask-cors requests python-dotenv waitress
        pause
        exit /b 1
    )
    echo ✅ Packages installed successfully
)

REM Start the server
echo ✅ Starting server...
python start_server.py

pause
