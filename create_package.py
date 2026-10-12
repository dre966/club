#!/usr/bin/env python3
"""
Create a distribution package for the Hostel Registration System.
Run: python create_package.py
Outputs: hostel_registration_package.zip
"""

import zipfile
import os
from pathlib import Path

# Files to include in the package
FILES_TO_INCLUDE = [
    "hostel_registration.py",
    "web_app.py",
    "init_database.sql",
    "requirements.txt",
    "run_hostel_registration.bat",
    "run_hostel_registration.ps1",
    "run.py",
    "sql_to_pdf.py",
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "README.md",
    "USB_INSTALL_GUIDE.txt",
]

# Files that are optional (include if they exist)
OPTIONAL_FILES = [
    "registered_students.json",
    "scraper.py",
    "db_config.py",
]

def create_readme():
    """Create a README.md file for the package."""
    readme_content = """# Hostel Registration System

A Python/Tkinter desktop application for registering students to hostels.

## Contents

- `hostel_registration.py` - Main application
- `init_database.sql` - Database initialization script
- `requirements.txt` - Python dependencies
- `run_hostel_registration.bat` - Windows batch file to set up and run
- `run_hostel_registration.ps1` - PowerShell script to set up and run (recommended)

## Requirements

- Python 3.8+
- MySQL Server 5.7+ or 8.0+
- mysql-connector-python (auto-installed)

## Quick Start (Windows)

### Option 1: PowerShell (Recommended)
```powershell
powershell -ExecutionPolicy Bypass -File run_hostel_registration.ps1
```

### Option 2: Batch File
Double-click `run_hostel_registration.bat` or run from cmd:
```
run_hostel_registration.bat
```

### Option 3: Manual Steps
```cmd
pip install -r requirements.txt
mysql -u root < init_database.sql
python hostel_registration.py
```

## Database Configuration

Default configuration in `hostel_registration.py`:
- **Source DB**: `umatdb` (created by scraper, contains `admitted_students` table)
- **Registration DB**: `hostel_db` (created by app, contains `registered_students` table)
- **MySQL**: localhost, user `root`, no password

To change credentials, edit the `DB_CONFIG` dictionary in `hostel_registration.py`:
```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_password_here",  # Add password if needed
}
```

## Features

- Search students by name, reference number, phone, or email
- Multi-word search (order-independent)
- Phone number format normalization (+233 ↔ 0)
- Pre-fills hostel from scraped data (hallName → affiliatedHallName)
- Saves to both MySQL and JSON backup
- Debounced search (250ms delay)
- Keyboard navigation (Down arrow to select first result)

## Search Tips

- Type multiple words: `derrick attaa` finds "Attaa Derrick"
- Search by phone: `0500263934` or `+233500263934`
- Search by email: `student@umat.edu.gh`
- Results capped at 100 (shows "100+" when capped)

## Programme Filter

By default, searches ALL programmes. To filter:
```python
PROGRAMME_FILTER = "cyber"  # Only show Cyber Security students
```

## Data Flow

1. Scraper populates `umatdb.admitted_students` with `hallName` and `affiliatedHallName`
2. Registration app reads from `umatdb.admitted_students`
3. On register: saves to `hostel_db.registered_students` + `registered_students.json`
4. Re-registering a student updates their record

## Troubleshooting

### MySQL Connection Failed
- Ensure MySQL service is running
- Check credentials in `DB_CONFIG`
- If root has password, add it to `DB_CONFIG` and update scripts

### No Students Found
- Verify scraper has run and populated `umatdb.admitted_students`
- Check `PROGRAMME_FILTER` setting
- Try empty search to see all students

### ModuleNotFoundError: mysql.connector
```cmd
pip install mysql-connector-python
```

## License

Internal use only.
"""
    return readme_content


def create_package():
    """Create the distribution zip file."""
    package_name = "hostel_registration_package.zip"
    base_dir = Path(__file__).parent
    
    with zipfile.ZipFile(package_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add required files
        for fname in FILES_TO_INCLUDE:
            fpath = base_dir / fname
            if fpath.exists():
                zf.write(fpath, fname)
                print(f"Added: {fname}")
            else:
                # Create README if it doesn't exist
                if fname == "README.md":
                    content = create_readme()
                    zf.writestr(fname, content)
                    print(f"Created: {fname}")
                else:
                    print(f"WARNING: Missing required file: {fname}")
        
        # Add templates directory
        for fpath in base_dir.glob("templates/**/*"):
            if fpath.is_file():
                rel_path = fpath.relative_to(base_dir)
                zf.write(fpath, rel_path)
                print(f"Added: {rel_path}")
        
        # Add static directory
        for fpath in base_dir.glob("static/**/*"):
            if fpath.is_file():
                rel_path = fpath.relative_to(base_dir)
                zf.write(fpath, rel_path)
                print(f"Added: {rel_path}")
        
        # Add optional files if they exist
        for fname in OPTIONAL_FILES:
            fpath = base_dir / fname
            if fpath.exists():
                zf.write(fpath, fname)
                print(f"Added (optional): {fname}")
    
    size = os.path.getsize(package_name) / 1024
    print(f"\nPackage created: {package_name} ({size:.1f} KB)")
    print("\nTo distribute: share the .zip file")
    print("Recipient extracts and runs: run_hostel_registration.ps1")


if __name__ == "__main__":
    create_package()