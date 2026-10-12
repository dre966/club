import mysql.connector, requests, json

login = "https://student.umat.edu.gh/api/auth/login"
result = "https://student.umat.edu.gh/api/result"


# {
#     "isSuccessful": true,
#     "message": "Login successful",
#     "rawResponse": {
#         "status": 200,
#         "statusText": "OK",
#         "data": {
#             "isSuccess": true,
#             "isFailure": false,
#             "error": null,
#             "message": "Login successful",
#             "code": "200",
#             "data": {
#                 "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1bmlxdWVfbmFtZSI6WyI5MDE3MzYxNzI1IiwiOTAxNzM2MTcyNSJdLCJuYW1laWQiOiIyMTRjYTUyMi1hNWZhLTQ5NzItYTNlOC1mNTIxODlhNDZkMDgiLCJlbWFpbCI6WyJscXVheWUxNzI1QHN0LnVtYXQuZWR1LmdoIiwibHF1YXllMTcyNUBzdC51bWF0LmVkdS5naCJdLCJzdWIiOiIyMTRjYTUyMi1hNWZhLTQ5NzItYTNlOC1mNTIxODlhNDZkMDgiLCJyb2xlIjoiU3R1ZGVudHMiLCJuYmYiOjE3OTE2MzA5NDIsImV4cCI6MTc5NDMwOTY0MiwiaWF0IjoxNzkxNjMxMjQyLCJpc3MiOiJ1bWF0LmVkdS5naCIsImF1ZCI6InVtYXQuYXV0aC5hcGkifQ.QUQBdrNrKHCErall7kVdKpDAa4Ne3BKsJT6J8Z6LXtQ",
#                 "expiresAt": "2026-11-10T11:20:42.5682811Z",
#                 "roles": [
#                     "Students"
#                 ]
#             }
#         }
#     },
#     "portal": "student"
# }


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
            query = "select * from admitted_students where programme like 'Bsc Cyber%';"
            cursor.execute(query)
            records = cursor.fetchall()            
            return records
    except Exception as e:
        print(f"Error while connecting to MySQL: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("\nMySQL connection is closed.")


recs = get_reference_numbers()
final_info = {}
with open("whatiwant.json", 'r') as f:
    final_info = json.load(f)
for i, v in enumerate(recs):
    id, s_id, s_name, s_email, s_ph, s_programme, s__, s__, s__, s__, s__ = v
    payload = {
    "username": s_id,
    "password": s_id
    }
    session = requests.session()
    res = session.post(login, json=payload)
    if res.status_code == 200:
        rst_res = session.get(result)
        if rst_res.status_code == 200:
            if s_id in final_info.keys():
                print(f"Skipping {s_id}: {s_name}")
            print(f"Passed for {s_name}")
            final_info[s_id] = rst_res.json()
            with open('whatiwant.json', 'w') as f:
                json.dump(final_info,f, indent=2)

        else:
            print(f"Result get failed, code{rst_res.status_code}")
    else:
        print(f"Login failed, code: {res.status_code}")


with open("cy_2025_res.json", "w") as f:
    json.dump(final_info, f)

print("done")

