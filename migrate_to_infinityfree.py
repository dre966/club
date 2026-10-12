#!/usr/bin/env python3
"""
Migrate local umatdb and hostel_db to InfinityFree MySQL
"""

import mysql.connector
from mysql.connector import Error

# Local DB config
LOCAL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
}

# Railway DB config
REMOTE_CONFIG = {
    "host": "iriguchi.proxy.rlwy.net",
    "user": "root",
    "password": "qusAYhbZUedrXZWMTbtNXNtFoddixXvT",
    "database": "railway",
    "port": 36817,
}

TABLES = {
    "admitted_students": {
        "source_db": "umatdb",
        "create_sql": """
        CREATE TABLE IF NOT EXISTS `admitted_students` (
            `id` VARCHAR(255) PRIMARY KEY,
            `formReferenceNo` VARCHAR(255),
            `fullName` VARCHAR(255),
            `email` VARCHAR(255),
            `phoneNumber` VARCHAR(50),
            `programme` VARCHAR(255),
            `admittedDate` VARCHAR(255),
            `affiliatedHallName` VARCHAR(255),
            `hallName` VARCHAR(255),
            `campus` VARCHAR(255),
            `status` VARCHAR(50)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        "columns": ["id", "formReferenceNo", "fullName", "email", "phoneNumber", "programme", "admittedDate", "affiliatedHallName", "hallName", "campus", "status"]
    },
    "registered_students": {
        "source_db": "hostel_db",
        "create_sql": """
        CREATE TABLE IF NOT EXISTS `registered_students` (
            `id` VARCHAR(255) PRIMARY KEY,
            `formReferenceNo` VARCHAR(255),
            `fullName` VARCHAR(255),
            `email` VARCHAR(255),
            `programme` VARCHAR(255),
            `phoneNumber` VARCHAR(50),
            `hostel` VARCHAR(255),
            `souvenirs_paid` BOOLEAN DEFAULT FALSE,
            `registeredAt` DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        "columns": ["id", "formReferenceNo", "fullName", "email", "programme", "phoneNumber", "hostel", "souvenirs_paid", "registeredAt"]
    }
}


def get_local_conn():
    return mysql.connector.connect(**LOCAL_CONFIG)


def get_remote_conn():
    return mysql.connector.connect(**REMOTE_CONFIG, ssl_disabled=True)


def create_remote_tables():
    print("Creating tables on InfinityFree...")
    conn = get_remote_conn()
    cursor = conn.cursor()
    for table_name, info in TABLES.items():
        cursor.execute(info["create_sql"])
        print(f"  Created/verified: {table_name}")
    conn.commit()
    cursor.close()
    conn.close()


def migrate_table(table_name, info):
    print(f"\nMigrating {table_name}...")
    
    # Fetch from local
    local_conn = get_local_conn()
    local_cursor = local_conn.cursor(dictionary=True)
    local_cursor.execute(f"SELECT * FROM `{info['source_db']}`.`{table_name}`")
    rows = local_cursor.fetchall()
    local_cursor.close()
    local_conn.close()
    
    if not rows:
        print(f"  No data in local {table_name}")
        return
    
    print(f"  Found {len(rows)} rows locally")
    
    # Insert into remote
    remote_conn = get_remote_conn()
    remote_cursor = remote_conn.cursor()
    
    cols = info["columns"]
    placeholders = ", ".join(["%s"] * len(cols))
    col_list = ", ".join([f"`{c}`" for c in cols])
    insert_sql = f"INSERT IGNORE INTO `{table_name}` ({col_list}) VALUES ({placeholders})"
    
    data = []
    for row in rows:
        data.append(tuple(row.get(c) for c in cols))
    
    remote_cursor.executemany(insert_sql, data)
    remote_conn.commit()
    print(f"  Inserted {remote_cursor.rowcount} new rows")
    
    remote_cursor.close()
    remote_conn.close()


def verify_migration():
    print("\nVerifying migration...")
    remote_conn = get_remote_conn()
    remote_cursor = remote_conn.cursor()
    for table_name in TABLES:
        remote_cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        count = remote_cursor.fetchone()[0]
        print(f"  {table_name}: {count} rows on InfinityFree")
    remote_cursor.close()
    remote_conn.close()


def main():
    print("=" * 50)
    print("Migrating to InfinityFree MySQL")
    print("=" * 50)
    
    try:
        # Test connections
        print("Testing local connection...")
        get_local_conn().close()
        print("  OK")
        
        print("Testing remote connection...")
        get_remote_conn().close()
        print("  OK")
        
        # Create tables
        create_remote_tables()
        
        # Migrate data
        for table_name, info in TABLES.items():
            migrate_table(table_name, info)
        
        # Verify
        verify_migration()
        
        print("\n[OK] Migration complete!")
        
    except Error as e:
        print(f"\n[ERROR] Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())