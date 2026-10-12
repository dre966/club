import json
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import mysql.connector
from mysql.connector import Error

# ---------- Config ----------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
}
SOURCE_DB = "umatdb"          # DB created by your scraper (admitted_students table)
REG_DB = "hostel_db"          # New DB this app creates for registered students
JSON_FILE = "registered_students.json"
PROGRAMME_FILTER = ""         # "" = all students; or e.g. "cyber" to filter by programme


# ---------- Database ----------
def get_conn():
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {REG_DB}")
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {REG_DB}.registered_students (
            id VARCHAR(255) PRIMARY KEY,
            formReferenceNo VARCHAR(255),
            fullName VARCHAR(255),
            email VARCHAR(255),
            programme VARCHAR(255),
            phoneNumber VARCHAR(50),
            hostel VARCHAR(255),
            registeredAt DATETIME
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def search_students(text):
    text = text.strip()
    where = ["(%s = '' OR a.programme LIKE %s)"]
    params = [PROGRAMME_FILTER, f"%{PROGRAMME_FILTER}%"]
    # Every word must match somewhere (name, ref no, phone, email), in any order
    for t in text.split():
        like = f"%{t}%"
        digits = re.sub(r"[\s\-+]", "", t)
        if digits.isdigit() and digits.startswith("233"):
            digits = "0" + digits[3:]          # +233 50... -> 050...
        where.append("(a.fullName LIKE %s OR a.formReferenceNo LIKE %s "
                     "OR a.phoneNumber LIKE %s OR a.email LIKE %s)")
        params += [like, like, f"%{digits}%", like]

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(f"""
        SELECT a.id, a.formReferenceNo, a.fullName, a.email, a.programme,
               a.phoneNumber, a.hallName, a.affiliatedHallName,
               r.hostel AS hostel, r.phoneNumber AS regPhone
        FROM {SOURCE_DB}.admitted_students a
        LEFT JOIN {REG_DB}.registered_students r ON r.id = a.id
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


def save_to_db(rec):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO {REG_DB}.registered_students
        (id, formReferenceNo, fullName, email, programme, phoneNumber, hostel, registeredAt)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            phoneNumber = VALUES(phoneNumber),
            hostel = VALUES(hostel),
            registeredAt = VALUES(registeredAt)
    """, (rec["id"], rec["formReferenceNo"], rec["fullName"], rec["email"],
          rec["programme"], rec["phoneNumber"], rec["hostel"], rec["registeredAt"]))
    conn.commit()
    cur.close()
    conn.close()


# ---------- JSON ----------
def save_to_json(rec):
    data = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    data = [d for d in data if d.get("id") != rec["id"]]  # replace if re-registered
    data.append(rec)
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------- UI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hostel Registration")
        self.geometry("900x560")
        self.results = {}

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Search (name / ref no / phone):").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.search_var, width=40)
        entry.pack(side="left", padx=8)
        entry.focus()
        self._job = None
        self.search_var.trace_add("write", lambda *_: self.schedule_search())
        entry.bind("<Return>", lambda e: self.do_search())
        entry.bind("<Down>", lambda e: self.focus_first_result())
        self.count_label = ttk.Label(top, text="")
        self.count_label.pack(side="left", padx=8)

        cols = ("name", "ref", "programme", "phone", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        for c, w in zip(cols, (250, 110, 250, 110, 120)):
            self.tree.heading(c, text=c.title())
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True, padx=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        form = ttk.LabelFrame(self, text="Register selected student", padding=10)
        form.pack(fill="x", padx=10, pady=10)

        self.sel_label = ttk.Label(form, text="No student selected")
        self.sel_label.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        ttk.Label(form, text="Hostel:").grid(row=1, column=0, sticky="w")
        self.hostel_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.hostel_var, width=28).grid(row=1, column=1, padx=8)

        ttk.Label(form, text="Phone (edit if different):").grid(row=1, column=2, sticky="w")
        self.phone_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.phone_var, width=20).grid(row=1, column=3, padx=8)

        ttk.Button(form, text="Register", command=self.register).grid(row=1, column=4, padx=8)

        self.selected = None
        try:
            init_db()
        except Error as e:
            messagebox.showerror("Database error", str(e))
        self.do_search()

    def schedule_search(self):
        if self._job:
            self.after_cancel(self._job)       # only the last keystroke triggers a query
        self._job = self.after(250, self.do_search)

    def focus_first_result(self):
        items = self.tree.get_children()
        if items:
            self.tree.focus_set()
            self.tree.selection_set(items[0])
            self.tree.focus(items[0])

    def do_search(self):
        self._job = None
        try:
            rows = search_students(self.search_var.get().strip())
        except Error as e:
            messagebox.showerror("Database error", str(e))
            return
        self.tree.delete(*self.tree.get_children())
        self.results = {}
        for r in rows:
            status = f"Registered: {r['hostel']}" if r["hostel"] else ""
            iid = self.tree.insert("", "end", values=(
                r["fullName"], r["formReferenceNo"], r["programme"],
                r["regPhone"] or r["phoneNumber"], status))
            self.results[iid] = r
        n = len(rows)
        self.count_label.config(text=f"{n}{'+' if n == 100 else ''} result{'s' if n != 1 else ''}")

    def on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        r = self.results[sel[0]]
        self.selected = r
        self.sel_label.config(text=f"{r['fullName']}  |  Ref: {r['formReferenceNo']}  |  {r['programme']}")
        self.phone_var.set(r["regPhone"] or r["phoneNumber"] or "")
        self.hostel_var.set(r["hostel"] or r["hallName"] or r["affiliatedHallName"] or "")

    def register(self):
        if not self.selected:
            messagebox.showwarning("No student", "Select a student first.")
            return
        hostel = self.hostel_var.get().strip()
        phone = self.phone_var.get().strip()
        if not hostel:
            messagebox.showwarning("Missing hostel", "Enter the hostel.")
            return
        r = self.selected
        if r["hostel"] and not messagebox.askyesno(
                "Already registered", f"{r['fullName']} is already in {r['hostel']}. Update?"):
            return
        rec = {
            "id": r["id"],
            "formReferenceNo": r["formReferenceNo"],
            "fullName": r["fullName"],
            "email": r["email"],
            "programme": r["programme"],
            "phoneNumber": phone,
            "hostel": hostel,
            "registeredAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            save_to_db(rec)
            save_to_json(rec)
        except Error as e:
            messagebox.showerror("Database error", str(e))
            return
        messagebox.showinfo("Saved", f"{rec['fullName']} registered in {hostel}.")
        self.selected = None
        self.sel_label.config(text="No student selected")
        self.hostel_var.set("")
        self.phone_var.set("")
        self.do_search()


if __name__ == "__main__":
    App().mainloop()