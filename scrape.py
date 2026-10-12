import os
import requests
import mysql.connector
from mysql.connector import Error

# 1. Setup Database Configuration
db_config = {
    'host': 'localhost',      # Change this if your database is hosted elsewhere
    'user': 'root',           # Replace with your MySQL username
    'password': '',           # Replace with your MySQL password
    'database': 'umatdb'      # Replace with your database name (create this DB first in MySQL!)
}

# 2. Create the images directory if it doesn't exist
IMG_DIR = "imgs"
os.makedirs(IMG_DIR, exist_ok=True)

try:
    # Connect to MySQL
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Create table using MySQL syntax
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admitted_students (
        id VARCHAR(255) PRIMARY KEY,
        formReferenceNo VARCHAR(255),
        fullName VARCHAR(255),
        email VARCHAR(255),
        phoneNumber VARCHAR(50),
        programme VARCHAR(255),
        admittedDate VARCHAR(255),
        affiliatedHallName VARCHAR(255),
        hallName VARCHAR(255),
        campus VARCHAR(255),
        status VARCHAR(50)
    )
    ''')
    conn.commit()

    # 3. Setup API Request Variables
    url = "https://apply.umat.edu.gh/api/admitted-applicants" 
    params = {
        "searchText": "",
        "pageSize": 500,
        "sortBy": "admittedDate",
        "sortOrder": "asc"
    }

    curr_page = 1
    max_pages = 1

    # 4. Loop Through Pages
    while curr_page <= max_pages:
        params["page"] = curr_page
        print(f"Fetching data for page {curr_page}...")
        
        # Fetch Data
        res = requests.get(url, params=params)
        res.raise_for_status() 
        
        data = res.json().get("data", {})
        students = data.get("items", [])
        
        if not students:
            print("No more items found. Exiting loop.")
            break
            
        if curr_page == 1:
            max_pages = data.get("totalPages", 1)

        # 5. Process Students and Images
        student_records = []
        
        for s in students:
            ref_no = s.get("formReferenceNo")
            img_url = s.get("profileImageUrl")
            
            # Prepare data tuple for MySQL batch insert
            student_records.append((
                s.get("id"),
                ref_no,
                s.get("fullName"),
                s.get("email"),
                s.get("phoneNumber"),
                s.get("programme"),
                s.get("campus"),
                s.get("admittedDate"),
                s.get("affiliatedHallName"),
                s.get("hallName"),
                s.get("status")
            ))
            
            # Download the image
            if img_url:
                try:
                    # stream=True is best for downloading files
                    # timeout=10 prevents the script from hanging on a bad image link
                    img_res = requests.get(img_url, stream=True, timeout=10)
                    
                    if img_res.status_code == 200:
                        # Save the image using the formReferenceNo as the filename
                        file_path = os.path.join(IMG_DIR, f"{ref_no}.jpg")
                        
                        with open(file_path, 'wb') as f:
                            for chunk in img_res.iter_content(1024):
                                f.write(chunk)
                except Exception as img_err:
                    print(f"  [!] Failed to download image for {ref_no}: {img_err}")

        # 6. Execute Batch Insert for MySQL
        insert_query = '''
        INSERT IGNORE INTO admitted_students 
        (id, formReferenceNo, fullName, email, phoneNumber, programme, campus, admittedDate, affiliatedHallName, hallName, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        
        cursor.executemany(insert_query, student_records)
        conn.commit()
        
        print(f"Successfully processed page {curr_page}. Inserted {cursor.rowcount} new records and downloaded images.")
        
        curr_page += 1

except Error as e:
    print(f"Database Error: {e}")
except requests.exceptions.RequestException as e:
    print(f"Network error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    # 7. Clean up connections securely
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
        print("MySQL connection safely closed.")