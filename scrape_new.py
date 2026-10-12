import os
import sys
import requests
import mysql.connector
from mysql.connector import Error

# 1. Setup Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'umatdb'
}

# 2. Ask whether to download images (or pass --images / --no-images to skip the prompt)
if "--images" in sys.argv:
    DOWNLOAD_IMAGES = True
elif "--no-images" in sys.argv:
    DOWNLOAD_IMAGES = False
else:
    DOWNLOAD_IMAGES = input("Download student images? (y/n): ").strip().lower() in ("y", "yes")

IMG_DIR = "imgs"
if DOWNLOAD_IMAGES:
    os.makedirs(IMG_DIR, exist_ok=True)

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

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

    url = "https://apply.umat.edu.gh/api/admitted-applicants"
    params = {
        "searchText": "",
        "pageSize": 500,
        "sortBy": "admittedDate",
        "sortOrder": "asc"
    }

    curr_page = 1
    max_pages = 1
    session = requests.Session()  # reuses connections, faster than bare requests.get

    while curr_page <= max_pages:
        params["page"] = curr_page
        print(f"Fetching data for page {curr_page}...")

        res = session.get(url, params=params)
        res.raise_for_status()

        data = res.json().get("data", {})
        students = data.get("items", [])

        if not students:
            print("No more items found. Exiting loop.")
            break

        if curr_page == 1:
            max_pages = data.get("totalPages", 1)

        student_records = []
        downloaded = skipped = 0

        for s in students:
            ref_no = s.get("formReferenceNo")
            img_url = s.get("profileImageUrl")

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

            if DOWNLOAD_IMAGES and img_url:
                file_path = os.path.join(IMG_DIR, f"{ref_no}.jpg")

                # Skip images already downloaded on a previous run - verify valid image
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'rb') as f:
                            header = f.read(16)
                        # Check for JPEG (FF D8 FF), PNG (89 50 4E 47), or WebP (RIFF....WEBP)
                        if len(header) >= 3 and header[:3] == b'\xff\xd8\xff':
                            skipped += 1
                            continue
                        if len(header) >= 8 and header[:8] == b'\x89PNG\r\n\x1a\n':
                            skipped += 1
                            continue
                        if len(header) >= 12 and header[:4] == b'RIFF' and header[8:12] == b'WEBP':
                            skipped += 1
                            continue
                        # Invalid/corrupted file - will re-download
                        print(f"  [!] Corrupted image for {ref_no}, re-downloading...")
                    except Exception:
                        pass  # Unreadable - will re-download

                try:
                    img_res = session.get(img_url, stream=True, timeout=10)
                    if img_res.status_code == 200:
                        with open(file_path, 'wb') as f:
                            for chunk in img_res.iter_content(8192):
                                f.write(chunk)
                        downloaded += 1
                except Exception as img_err:
                    print(f"  [!] Failed to download image for {ref_no}: {img_err}")

        insert_query = '''
        INSERT IGNORE INTO admitted_students
        (id, formReferenceNo, fullName, email, phoneNumber, programme, campus, admittedDate, affiliatedHallName, hallName, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''

        cursor.executemany(insert_query, student_records)
        conn.commit()

        msg = f"Page {curr_page} done. Inserted {cursor.rowcount} new records."
        if DOWNLOAD_IMAGES:
            msg += f" Images: {downloaded} downloaded, {skipped} already existed."
        print(msg)

        curr_page += 1

except Error as e:
    print(f"Database Error: {e}")
except requests.exceptions.RequestException as e:
    print(f"Network error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
        print("MySQL connection safely closed.")