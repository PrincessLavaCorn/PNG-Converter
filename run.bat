@echo off
title Universal PNG Converter
cd /d "%~dp0"

echo [1/2] Checking Python dependencies...
python -c "import PIL, pillow_heif, PySide6" >nul 2>&1
if %errorlevel% NEQ 0 (
    echo Installing missing requirements (Pillow, pillow-heif, PySide6)...
    pip install -r requirements.txt
    if %errorlevel% NEQ 0 (
        echo Failed to install dependencies. Please run 'pip install -r requirements.txt' manually.
        pause
        exit /b %errorlevel%
    )
)

echo [2/2] Launching Universal PNG Converter...
python png_converter.py
if %errorlevel% NEQ 0 (
    pause
)
