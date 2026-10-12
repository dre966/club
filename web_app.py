#!/usr/bin/env python3
"""
Cybersecurity Club Registration - Web App (FastAPI + Jinja2)
Deploy to Railway: connects to same Railway MySQL
Run locally: python web_app.py
Access: http://localhost:8000
"""

import os
import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import mysql.connector
from mysql.connector import Error


# ---------- Config ----------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "iriguchi.proxy.rlwy.net"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "qusAYhbZUedrXZWMTbtNXNtFoddixXvT"),
    "port": int(os.getenv("DB_PORT", "36817")),
}
SOURCE_DB = os.getenv("SOURCE_DB", "railway")
REG_DB = os.getenv("REG_DB", "railway")
UNIFIED_TABLE = "registration_rectification"
PROGRAMME_FILTER = ""  # "" = all students
APP_TITLE = "Hostel & Cyber Club Registration"


# ---------- Database ----------
def get_conn():
    return mysql.connector.connect(**DB_CONFIG, ssl_disabled=True)


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    # Table already created by create_unified.py - just verify
    cur.execute(f"SHOW TABLES LIKE '{UNIFIED_TABLE}'")
    if not cur.fetchone():
        print(f"Warning: {UNIFIED_TABLE} not found")
    conn.commit()
    cur.close()
    conn.close()


def search_students(text: str):
    text = text.strip()
    where = []
    params = []
    if PROGRAMME_FILTER:
        where.append("a.programme LIKE %s")
        params.append(f"%{PROGRAMME_FILTER}%")

    for t in text.split():
        like = f"%{t}%"
        digits = re.sub(r"[\s\-+]", "", t)
        if digits.isdigit() and digits.startswith("233"):
            digits = "0" + digits[3:]
        where.append("(a.fullName LIKE %s OR a.formReferenceNo LIKE %s OR a.phoneNumber LIKE %s OR a.email LIKE %s)")
        params += [like, like, f"%{digits}%", like]

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    where_clause = " AND ".join(where) if where else "1=1"
    cur.execute(f"""
        SELECT a.id, a.formReferenceNo, a.fullName, a.email, a.programme,
               a.phoneNumber, a.hallName, a.affiliatedHallName,
               r.hostel, r.souvenir_paid, r.source,
               r.phoneNumber AS regPhone,
               COALESCE(r.hostel, a.hallName, a.affiliatedHallName) AS regHostel,
               r.registeredAt
        FROM `{SOURCE_DB}`.`admitted_students` a
        LEFT JOIN `{REG_DB}`.`{UNIFIED_TABLE}` r ON r.id = a.id
        WHERE {where_clause}
        ORDER BY (a.formReferenceNo = %s) DESC,
                 (a.fullName LIKE %s) DESC,
                 a.fullName
        LIMIT 100
    """, params + [text, f"{text}%"])
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_student(student_id: str):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(f"""
        SELECT a.id, a.formReferenceNo, a.fullName, a.email, a.programme,
               a.phoneNumber, a.hallName, a.affiliatedHallName,
               r.hostel, r.souvenir_paid, r.source,
               r.phoneNumber AS regPhone,
               COALESCE(r.hostel, a.hallName, a.affiliatedHallName) AS regHostel,
               r.registeredAt
        FROM `{SOURCE_DB}`.`admitted_students` a
        LEFT JOIN `{REG_DB}`.`{UNIFIED_TABLE}` r ON r.id = a.id
        WHERE a.id = %s
    """, (student_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def save_registration(rec: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO `{REG_DB}`.`{UNIFIED_TABLE}`
        (id, formReferenceNo, fullName, email, programme, phoneNumber,
         hostel, souvenir_paid, registeredAt, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            phoneNumber = VALUES(phoneNumber),
            hostel = VALUES(hostel),
            souvenir_paid = VALUES(souvenir_paid),
            registeredAt = VALUES(registeredAt)
    """, (rec["id"], rec["formReferenceNo"], rec["fullName"], rec["email"],
          rec["programme"], rec["phoneNumber"],
          rec.get("hostel"), rec.get("souvenir_paid", False),
          rec["registeredAt"], rec.get("source", "web")))
    conn.commit()
    cur.close()
    conn.close()


# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        print("Database initialized")
    except Error as e:
        print(f"DB init error: {e}")
    yield


# ---------- FastAPI App ----------
app = FastAPI(title=APP_TITLE, lifespan=lifespan)

# Templates - disable cache to avoid Jinja2 cache key issues
templates = Jinja2Templates(directory="templates")
# Disable template cache to prevent "unhashable type: dict" error
templates.env.cache = {}

# Static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, q: str = ""):
    students = search_students(q) if q else []
    return templates.TemplateResponse("index.html", {
        "request": request,
        "students": students,
        "query": q,
        "count": len(students),
        "app_title": APP_TITLE
    })


@app.get("/student/{student_id}", response_class=HTMLResponse)
async def student_detail(request: Request, student_id: str):
    student = get_student(student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    return templates.TemplateResponse("detail.html", {
        "request": request,
        "student": student,
        "app_title": APP_TITLE
    })


@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    student_id: str = Form(...),
    hostel: str = Form(""),
    phone: str = Form(""),
    souvenir: bool = Form(False)
):
    student = get_student(student_id)
    if not student:
        raise HTTPException(404, "Student not found")

    if not hostel.strip() and not souvenir:
        return templates.TemplateResponse("detail.html", {
            "request": request,
            "student": student,
            "error": "Enter hostel or check Souvenir",
            "app_title": APP_TITLE
        })

    rec = {
        "id": student["id"],
        "formReferenceNo": student["formReferenceNo"],
        "fullName": student["fullName"],
        "email": student["email"],
        "programme": student["programme"],
        "phoneNumber": phone or student["regPhone"] or student["phoneNumber"] or "",
        "hostel": hostel.strip(),
        "souvenir_paid": souvenir,
        "source": "both" if (hostel and souvenir) else ("hostel" if hostel else "cyber_club"),
        "registeredAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        save_registration(rec)
    except Error as e:
        return templates.TemplateResponse("detail.html", {
            "request": request,
            "student": student,
            "error": f"Database error: {e}",
            "app_title": APP_TITLE
        })

    return RedirectResponse(url=f"/student/{student_id}?saved=1", status_code=303)


@app.get("/api/stats")
async def stats():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(f"SELECT COUNT(*) as total FROM `{REG_DB}`.`{UNIFIED_TABLE}`")
    total = cur.fetchone()["total"]
    cur.execute(f"SELECT COUNT(*) as hostel FROM `{REG_DB}`.`{UNIFIED_TABLE}` WHERE hostel IS NOT NULL AND hostel != ''")
    hostel = cur.fetchone()["hostel"]
    cur.execute(f"SELECT COUNT(*) as souvenirs FROM `{REG_DB}`.`{UNIFIED_TABLE}` WHERE souvenir_paid = 1")
    souvenirs = cur.fetchone()["souvenirs"]
    cur.close()
    conn.close()
    return {"total_registered": total, "hostel": hostel, "souvenir_paid": souvenirs}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)