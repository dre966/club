import getpass
import requests
import mysql.connector, requests
from mysql.connector import Error

BASE_URL = "https://student.umat.edu.gh"
LOGIN_URL = f"{BASE_URL}/api/auth/login"
REG_URL = f"{BASE_URL}/api/registration"
SURVEY_URL = f"{BASE_URL}/api/assessment"

STUDENT_NO = "9015298625"
SCORE = 5  # a perfect score
QUESTIONS = list(range(1, 24)) #assuuming everyone answers 23 questions

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9,es;q=0.8",
    "content-type": "application/json",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}

class StudentNotReported(Exception):
    """Custom Exception for when a student didnt report"""

class LoginFailed(Exception):
    """Explains what it does"""

def get_reference_numbers():
    """Gets Reference Number From My Local Database"""
    try:
        connection = mysql.connector.connect(
            host='localhost',          
            database='umatdb',         
            user='root',     
            password=''   
        )
        if connection.is_connected():
            cursor = connection.cursor()
            query = 'select * from admitted_students;'
            cursor.execute(query)
            records = cursor.fetchall()            
            return records
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("\nMySQL connection is closed.")


def check_if_user_exists(session: requests.Session, user):
    r = session.post(
        REG_URL,
        headers={**HEADERS, "referer": f"{BASE_URL}/"},
        json={"action":"getCourses"}
    )
    if r.status_code == 200 and len(r.json()["data"]) != 0:
        return
    raise StudentNotReported(f"{user} did not report")


def login(session:requests.Session, username, password, user):
    r = session.post(
        LOGIN_URL,
        headers={**HEADERS, "referer": f"{BASE_URL}/"},
        json={"username": username, "password": password},
    )
    if r.status_code == 200:
        print("Found ", user)
        print("Checking If user actually reported")
        check_if_user_exists(session, user)
        return r.json()
    raise LoginFailed(f"{username}, {user} Failed....Moving On")
    

def get_my_courses(session:requests.Session):
    r = session.post(
        REG_URL,
        headers={**HEADERS, "referer": f"{BASE_URL}/course-assessment"},
        json={"action": "getCourses"},
    )
    r.raise_for_status()
    res = r.json()
    if not res.get("isSuccessful"):
        raise RuntimeError(f"couldn't get courses: {res.get('message')}")

    courses = res["data"]
    print(f"got {len(courses)} courses")
    for c in courses:
        print(f"  {c['code']} - {c['name']}")

    return [c["courseId"] for c in courses]


def make_payload(course_ids):
    return {
        "action": "submitSurveyResponses",
        "payload": [
            {
                "studentNumber": STUDENT_NO,
                "courseId": cid,
                "remarks": "",
                "data": [{"questionId": q, "score": SCORE} for q in QUESTIONS],
            }
            for cid in course_ids
        ],
    }


def submit(session, course_ids):
    r = session.post(
        SURVEY_URL,
        headers={**HEADERS, "referer": f"{BASE_URL}/course-assessment"},
        json=make_payload(course_ids),
    )
    r.raise_for_status()
    return r.json()




# start a session and reuse keys
records = get_reference_numbers()
for row in records:
    print("\n\n--------------------------------------------") #make each print look nice
    ref = row[1]
    user = row[2]
    with requests.Session() as s:
        try:
            login(s, ref, ref,user)
            print()
            courses = get_my_courses(s)
            print()
            result = submit(s, courses)
            print(result)
        except Exception as e:
            print(f"Error: {type(e)}\nmsg: {e}.....skipping....")
            continue

       