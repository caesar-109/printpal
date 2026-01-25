@echo off
echo ========================================
echo Building PrintAgent.exe Prototype
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.11+
    pause
    exit /b 1
)

echo Step 1: Creating virtual environment...
if exist venv (
    echo Virtual environment already exists, skipping...
) else (
    python -m venv venv
)

echo.
echo Step 2: Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Step 3: Installing dependencies...
pip install --upgrade pip
pip install -r requirements_print_agent.txt

echo.
echo Step 4: Building EXE with PyInstaller...
echo Note: Using --console to show printing progress window
pyinstaller --onefile --console --name PrintAgent --clean print_agent.py

echo.
echo ========================================
if exist dist\PrintAgent.exe (
    echo SUCCESS! EXE built successfully!
    echo Location: dist\PrintAgent.exe
    echo.
    echo You can now test the application.
) else (
    echo ERROR: Build failed! Check errors above.
)
echo ========================================
echo.
pause
