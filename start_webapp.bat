@echo off
REM Oracle to SQL Server Migration - Web Application Startup Script
REM This script starts the Streamlit web interface

echo.
echo ================================================================================
echo  Oracle to SQL Server Migration - Web Application
echo ================================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [INFO] Python is installed
echo.

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Check if Streamlit is installed
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Streamlit is not installed. Installing dependencies...
    echo.
    pip install -r requirements_streamlit.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo.
    echo [SUCCESS] Dependencies installed successfully
    echo.
)

REM Check if config file exists
if not exist "config\config_enhanced.py" (
    echo [WARNING] Configuration file not found
    echo Please ensure config/config_enhanced.py exists with your API keys
    echo.
)

REM Create output directory if it doesn't exist
if not exist "output" mkdir output

REM Start Streamlit application
echo [INFO] Starting Streamlit web application...
echo [INFO] The application will open in your default browser
echo [INFO] Default URL: http://localhost:8501
echo.
echo ================================================================================
echo  Press Ctrl+C to stop the server
echo ================================================================================
echo.

streamlit run app.py

pause
