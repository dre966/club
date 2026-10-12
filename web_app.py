#!/usr/bin/env python3
"""
Cybersecurity Club Registration - Web App (FastAPI + Jinja2)
Deploy to Railway: connects to same Railway MySQL
Run locally: python web_app.py
Access: http://localhost:8000
"""

import os
import json
import re
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
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
PROGRAMME_FILTER = ""  # "" = all students
APP_TITLE = "Cybersecurity Club Registration"


# ---------- Database ----------
def get_conn():
    return mysql.connector.connect(**DB_CONFIG, ssl_disabled=True)


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{REG_DB}`")
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS `{REG_DB}`.`cybersecurity_registrations` (
            `id` VARCHAR(255) PRIMARY KEY,
            `formReferenceNo` VARCHAR(255),
            `fullName` VARCHAR(255),
            `email` VARCHAR(255),
            `programme` VARCHAR(255),
            `phoneNumber` VARCHAR(50),
            `year_level` VARCHAR(50),
            `tshirt_paid` BOOLEAN DEFAULT FALSE,
            `registeredAt` DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    # Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fullName ON `cybersecurity_registrations`(`fullName`)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_year ON `cybersecurity_registrations`(`year_level`)")
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
    cur.execute(f"""
        SELECT a.id, a.formReferenceNo, a.fullName, a.email, a.programme,
               a.phoneNumber, a.hallName, a.affiliatedHallName,
               r.year_level, r.phoneNumber AS regPhone, r.tshirt_paid, r.registeredAt
        FROM `{SOURCE_DB}`.`admitted_students` a
        LEFT JOIN `{REG_DB}`.`cybersecurity_registrations` r ON r.id = a.id
        WHERE {' AND '.join(where)}
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
               r.year_level, r.phoneNumber AS regPhone, r.tshirt_paid, r.registeredAt
        FROM `{SOURCE_DB}`.`admitted_students` a
        LEFT JOIN `{REG_DB}`.`cybersecurity_registrations` r ON r.id = a.id
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
        INSERT INTO `{REG_DB}`.`cybersecurity_registrations`
        (id, formReferenceNo, fullName, email, programme, phoneNumber, year_level, tshirt_paid, registeredAt)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            phoneNumber = VALUES(phoneNumber),
            year_level = VALUES(year_level),
            tshirt_paid = VALUES(tshirt_paid),
            registeredAt = VALUES(registeredAt)
    """, (rec["id"], rec["formReferenceNo"], rec["fullName"], rec["email"],
          rec["programme"], rec["phoneNumber"], rec["year_level"], rec["tshirt_paid"], rec["registeredAt"]))
    conn.commit()
    cur.close()
    conn.close()


# ---------- FastAPI App ----------
app = FastAPI(title=APP_TITLE)

# Templates
templates = Jinja2Templates(directory="templates")

# Static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# Initialize DB on startup
@app.on_event("startup")
async def startup():
    try:
        init_db()
        print("Database initialized")
    except Error as e:
        print(f"DB init error: {e}")


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
    year_level: str = Form(...),
    phone: str = Form(""),
    tshirt_paid: bool = Form(False)
):
    student = get_student(student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    
    if not year_level.strip():
        return templates.TemplateResponse("detail.html", {
            "request": request,
            "student": student,
            "error": "Year/Level is required",
            "app_title": APP_TITLE
        })
    
    rec = {
        "id": student["id"],
        "formReferenceNo": student["formReferenceNo"],
        "fullName": student["fullName"],
        "email": student["email"],
        "programme": student["programme"],
        "phoneNumber": phone or student["regPhone"] or student["phoneNumber"] or "",
        "year_level": year_level.strip(),
        "tshirt_paid": tshirt_paid,
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
    cur.execute(f"SELECT COUNT(*) as total FROM `{REG_DB}`.`cybersecurity_registrations`")
    total = cur.fetchone()["total"]
    cur.execute(f"SELECT COUNT(*) as paid FROM `{REG_DB}`.`cybersecurity_registrations` WHERE tshirt_paid = 1")
    paid = cur.fetchone()["paid"]
    cur.execute(f"SELECT year_level, COUNT(*) as cnt FROM `{REG_DB}`.`cybersecurity_registrations` GROUP BY year_level")
    by_year = {row["year_level"]: row["cnt"] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return {"total_registered": total, "tshirt_paid": paid, "by_year": by_year}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)