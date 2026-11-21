@echo off
setlocal enabledelayedexpansion
title Universal PNG Converter
cd /d "%~dp0"

echo ========================================================
echo        Universal PNG Converter - Launcher
echo ========================================================
echo.

:: 1. Detect working Python interpreter
set "PYTHON_CMD="

:: Check user-specific Python installation (found on this machine)
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    "%LOCALAPPDATA%\Python\bin\python.exe" --version >nul 2>&1
    if !errorlevel! EQU 0 (
        set "PYTHON_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
    )
)

:: Check PythonCore directory directly
if not defined PYTHON_CMD (
    for /d %%D in ("%LOCALAPPDATA%\Python\pythoncore*") do (
        if exist "%%D\python.exe" (
            "%%D\python.exe" --version >nul 2>&1
            if !errorlevel! EQU 0 set "PYTHON_CMD=%%D\python.exe"
        )
    )
)

:: Check standard LocalAppData Programs Python
if not defined PYTHON_CMD (
    for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
        if exist "%%D\python.exe" (
            "%%D\python.exe" --version >nul 2>&1
            if !errorlevel! EQU 0 set "PYTHON_CMD=%%D\python.exe"
        )
    )
)

:: Check standard C:\Python
if not defined PYTHON_CMD (
    for /d %%D in ("C:\Python*") do (
        if exist "%%D\python.exe" (
            "%%D\python.exe" --version >nul 2>&1
            if !errorlevel! EQU 0 set "PYTHON_CMD=%%D\python.exe"
        )
    )
)

:: Check py launcher
if not defined PYTHON_CMD (
    py --version >nul 2>&1
    if !errorlevel! EQU 0 set "PYTHON_CMD=py"
)

:: Check standard PATH python
if not defined PYTHON_CMD (
    python --version >nul 2>&1
    if !errorlevel! EQU 0 set "PYTHON_CMD=python"
)

:: If Python is still not found, alert user and pause
if not defined PYTHON_CMD (
    echo [ERROR] No working Python 3 installation was detected.
    echo.
    echo Please make sure Python is installed and added to PATH.
    echo You can download Python at: https://www.python.org/downloads/
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo Python interpreter found:
echo %PYTHON_CMD%
echo.

:: 2. Check and install dependencies
echo [1/2] Checking required Python dependencies...
"%PYTHON_CMD%" -c "import PIL, pillow_heif, PySide6" >nul 2>&1
if !errorlevel! NEQ 0 (
    echo Installing missing requirements: Pillow, pillow-heif, PySide6...
    echo Please wait while packages are installed...
    echo.
    "%PYTHON_CMD%" -m pip install -r requirements.txt
    if !errorlevel! NEQ 0 (
        echo.
        echo [ERROR] Failed to install dependencies.
        echo Try running: "%PYTHON_CMD%" -m pip install -r requirements.txt manually.
        echo.
        pause
        exit /b 1
    )
    echo Dependencies successfully installed!
    echo.
) else (
    echo All dependencies are ready.
    echo.
)

:: 3. Launch the application
echo [2/2] Launching Universal PNG Converter...
"%PYTHON_CMD%" png_converter.py
set "EXIT_CODE=%errorlevel%"

if %EXIT_CODE% NEQ 0 (
    echo.
    echo ========================================================
    echo Application exited with code %EXIT_CODE%.
    echo If this was an unexpected crash, please check the output above.
    echo ========================================================
    pause
)
