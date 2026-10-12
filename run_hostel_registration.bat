@echo off
REM Hostel Registration System - Setup and Run Script
REM This script installs dependencies, sets up databases, and runs the registration app

echo ============================================================
echo Hostel Registration System - Setup & Run
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo [1/4] Python found:
python --version
echo.

REM Install dependencies
echo [2/4] Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

REM Set up databases
echo [3/4] Setting up databases...
echo This requires MySQL server running with root access (no password by default).
echo If your MySQL root has a password, edit this file and add -p"yourpassword" to the mysql command.
echo.

mysql -u root < init_database.sql
if %errorlevel% neq 0 (
    echo WARNING: Database setup may have failed.
    echo Make sure MySQL is running and root has no password (or edit the script).
    echo You can also run init_database.sql manually in MySQL Workbench or CLI.
    echo.
)

REM Check if hostel_registration.py exists
if not exist hostel_registration.py (
    echo ERROR: hostel_registration.py not found in current directory
    pause
    exit /b 1
)

echo [4/4] Starting Hostel Registration App...
echo.
echo ============================================================
echo App is starting... Close this window to stop the app.
echo ============================================================
echo.

python hostel_registration.py

echo.
echo App closed.
pause