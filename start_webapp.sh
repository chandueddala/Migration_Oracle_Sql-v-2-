#!/bin/bash
# Oracle to SQL Server Migration - Web Application Startup Script
# This script starts the Streamlit web interface

echo ""
echo "================================================================================"
echo " Oracle to SQL Server Migration - Web Application"
echo "================================================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "[INFO] Python is installed: $(python3 --version)"
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if Streamlit is installed
if ! python3 -c "import streamlit" &> /dev/null; then
    echo "[INFO] Streamlit is not installed. Installing dependencies..."
    echo ""
    pip3 install -r requirements_streamlit.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies"
        exit 1
    fi
    echo ""
    echo "[SUCCESS] Dependencies installed successfully"
    echo ""
fi

# Check if config file exists
if [ ! -f "config/config_enhanced.py" ]; then
    echo "[WARNING] Configuration file not found"
    echo "Please ensure config/config_enhanced.py exists with your API keys"
    echo ""
fi

# Create output directory if it doesn't exist
mkdir -p output

# Start Streamlit application
echo "[INFO] Starting Streamlit web application..."
echo "[INFO] The application will open in your default browser"
echo "[INFO] Default URL: http://localhost:8501"
echo ""
echo "================================================================================"
echo " Press Ctrl+C to stop the server"
echo "================================================================================"
echo ""

streamlit run app.py
