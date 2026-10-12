<# 
.SYNOPSIS
    Hostel Registration System - Setup and Run Script (PowerShell)
.DESCRIPTION
    This script installs dependencies, sets up databases, and runs the registration app.
    Run with: powershell -ExecutionPolicy Bypass -File run_hostel_registration.ps1
#>

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Hostel Registration System - Setup & Run (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[1/4] Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://python.org" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# Install dependencies
Write-Host "[2/4] Installing Python dependencies..." -ForegroundColor Yellow
try {
    pip install -r requirements.txt
    Write-Host "Dependencies installed successfully." -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# Set up databases
Write-Host "[3/4] Setting up databases..." -ForegroundColor Yellow
Write-Host "This requires MySQL server running with root access (no password by default)." -ForegroundColor Gray
Write-Host "If your MySQL root has a password, edit this file and add `-p'yourpassword'` to the mysql command." -ForegroundColor Gray
Write-Host ""

try {
    mysql -u root -e "SOURCE init_database.sql"
    Write-Host "Databases set up successfully." -ForegroundColor Green
} catch {
    Write-Host "WARNING: Database setup may have failed." -ForegroundColor Yellow
    Write-Host "Make sure MySQL is running and root has no password (or edit the script)." -ForegroundColor Yellow
    Write-Host "You can also run init_database.sql manually in MySQL Workbench or CLI." -ForegroundColor Yellow
}
Write-Host ""

# Check if hostel_registration.py exists
if (-not (Test-Path "hostel_registration.py")) {
    Write-Host "ERROR: hostel_registration.py not found in current directory" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[4/4] Starting Hostel Registration App..." -ForegroundColor Green
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "App is starting... Close this window to stop the app." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

python hostel_registration.py

Write-Host ""
Write-Host "App closed." -ForegroundColor Cyan
Read-Host "Press Enter to exit"