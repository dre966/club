#!/usr/bin/env python3
"""
Hostel Registration System - Single-file Runner
Run: python run.py
This script handles everything: dependency check, database setup, and app launch.
"""

import sys
import subprocess
import os
from pathlib import Path

def check_python():
    """Verify Python version."""
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8+ required. Current:", sys.version)
        return False
    print(f"[OK] Python {sys.version.split()[0]}")
    return True

def install_deps():
    """Install requirements.txt if needed."""
    req_file = Path(__file__).parent / "requirements.txt"
    if not req_file.exists():
        print("[FAIL] requirements.txt not found")
        return False
    
    try:
        import mysql.connector
        print("[OK] mysql-connector-python already installed")
        return True
    except ImportError:
        print("Installing dependencies...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[FAIL] Failed to install dependencies:\n{result.stderr}")
            return False
        print("[OK] Dependencies installed")
        return True

def setup_database():
    """Run init_database.sql against MySQL."""
    sql_file = Path(__file__).parent / "init_database.sql"
    if not sql_file.exists():
        print("[FAIL] init_database.sql not found")
        return False
    
    print("Setting up databases...")
    # Try without password first, then prompt if needed
    for pwd in ["", None]:
        cmd = ["mysql", "-u", "root"]
        if pwd is not None:
            cmd += [f"-p{pwd}"] if pwd else []
        cmd += ["<", str(sql_file)]
        
        # Use shell=True for input redirection on Windows
        result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("[OK] Databases created/verified")
            return True
        if pwd is None:  # tried without password, now try prompting
            print("MySQL root password required. Enter it now (input hidden):")
            import getpass
            pwd = getpass.getpass("Password: ")
    
    print(f"[FAIL] Database setup failed:\n{result.stderr}")
    print("\nManual fix: Run this in MySQL Workbench or CLI:")
    print(f"  mysql -u root -p < {sql_file}")
    return False

def launch_app():
    """Launch the hostel registration app."""
    app_file = Path(__file__).parent / "hostel_registration.py"
    if not app_file.exists():
        print("[FAIL] hostel_registration.py not found")
        return False
    
    print("[OK] Starting Hostel Registration App...")
    print("     (Close the app window to exit)")
    try:
        # Use Popen so we don't block and can show the message
        proc = subprocess.Popen([sys.executable, str(app_file)])
        proc.wait()
    except KeyboardInterrupt:
        print("\nApp closed by user.")
    except subprocess.CalledProcessError as e:
        print(f"App error: {e}")
        return False
    return True

def main():
    print("=" * 55)
    print("  Hostel Registration System - One-Click Runner")
    print("=" * 55)
    print()
    
    steps = [
        ("Checking Python", check_python),
        ("Installing dependencies", install_deps),
        ("Setting up databases", setup_database),
    ]
    
    for name, func in steps:
        print(f"\n[{name}]")
        if not func():
            print(f"\n✗ Setup failed at: {name}")
            input("\nPress Enter to exit...")
            return 1
    
    print("\n" + "=" * 55)
    launch_app()
    return 0

if __name__ == "__main__":
    sys.exit(main())