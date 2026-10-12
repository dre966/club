import json
import os
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

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
JSON_FILE = "cybersecurity_registrations.json"
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
            `souvenir_paid` BOOLEAN DEFAULT FALSE,
            `registeredAt` DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    conn.commit()
    cur.close()
    conn.close()


def load_all_students():
    """Load ALL students from DB once at startup. Returns list of dicts."""
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    query = f"""
        SELECT a.id, a.formReferenceNo, a.fullName, a.email, a.programme,
               a.phoneNumber, a.hallName, a.affiliatedHallName,
               r.year_level, r.phoneNumber AS regPhone, r.tshirt_paid, r.registeredAt
        FROM `{SOURCE_DB}`.`admitted_students` a
        LEFT JOIN `{REG_DB}`.`cybersecurity_registrations` r ON r.id = a.id
    """
    params = []
    if PROGRAMME_FILTER:
        query += " WHERE a.programme LIKE %s"
        params.append(f"%{PROGRAMME_FILTER}%")
    query += " ORDER BY a.fullName"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def save_registration(rec):
    """Save registration to DB and update local JSON."""
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
    save_to_json(rec)


def save_to_json(rec):
    data = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    data = [d for d in data if d.get("id") != rec["id"]]
    data.append(rec)
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------- In-memory search ----------
def search_local(students, text):
    """Fast in-memory search. Returns filtered list."""
    text = text.strip().lower()
    if not text:
        return students[:100]  # Limit display to 100 for performance
    
    words = text.split()
    results = []
    
    for s in students:
        # Build searchable text
        searchable = " ".join([
            str(s.get("fullName", "")),
            str(s.get("formReferenceNo", "")),
            str(s.get("phoneNumber", "")),
            str(s.get("regPhone", "")),
            str(s.get("email", "")),
            str(s.get("programme", "")),
        ]).lower()
        
        # Normalize phone in searchable text
        searchable = re.sub(r"[\s\-+]", "", searchable)
        searchable = re.sub(r"233(\d{9})", r"0\1", searchable)
        
        # All words must match
        if all(w in searchable for w in words):
            results.append(s)
    
    # Sort: exact ref match first, then name starts with query, then alphabetical
    query_lower = text
    results.sort(key=lambda x: (
        0 if x.get("formReferenceNo", "").lower() == query_lower else
        1 if x.get("fullName", "").lower().startswith(query_lower) else 2,
        x.get("fullName", "")
    ))
    
    return results[:100]  # Cap at 100 for UI performance


# ---------- UI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("950x600")
        self.all_students = []      # Full dataset in memory
        self.filtered_students = [] # Current search results
        self.results = {}           # Tree item -> student data
        self._loading = True
        
        # UI Setup
        self.setup_ui()
        
        # Load data in background
        self.after(100, self.load_data_async)

    def setup_ui(self):
        # Top bar
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Search Cyber Security Students (name / ref / phone / email):").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.search_var, width=50)
        entry.pack(side="left", padx=8)
        entry.focus()
        self._job = None
        self.search_var.trace_add("write", lambda *_: self.schedule_search())
        entry.bind("<Return>", lambda e: self.do_search())
        entry.bind("<Down>", lambda e: self.focus_first_result())
        self.count_label = ttk.Label(top, text="Loading...")
        self.count_label.pack(side="left", padx=8)
        
        # Progress bar for loading
        self.progress = ttk.Progressbar(top, mode="indeterminate", length=200)
        self.progress.pack(side="left", padx=8)
        self.progress.start(10)
        
        # Refresh button
        ttk.Button(top, text="↻ Refresh", command=self.refresh_data).pack(side="right", padx=8)
        
        # Results tree
        cols = ("name", "ref", "programme", "phone", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=16)
        for c, w in zip(cols, (280, 130, 280, 130, 140)):
            self.tree.heading(c, text=c.title())
            self.tree.column(c, width=w, minwidth=80)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # Registration form
        form = ttk.LabelFrame(self, text="Register selected student for Cybersecurity Club", padding=10)
        form.pack(fill="x", padx=10, pady=(0,10))
        
        self.sel_label = ttk.Label(form, text="No student selected")
        self.sel_label.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 8))
        
        ttk.Label(form, text="Year/Level:").grid(row=1, column=0, sticky="w")
        self.year_var = tk.StringVar()
        ttk.Combobox(form, textvariable=self.year_var, values=["100", "200", "300", "400", "500", "Other"], width=28).grid(row=1, column=1, padx=8)
        
        ttk.Label(form, text="Phone:").grid(row=1, column=2, sticky="w")
        self.phone_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.phone_var, width=22).grid(row=1, column=3, padx=8)
        
        self.tshirt_var = tk.BooleanVar()
        ttk.Checkbutton(form, text="T-Shirt Paid", variable=self.tshirt_var).grid(row=1, column=4, padx=8)
        
        ttk.Button(form, text="Register / Update", command=self.register).grid(row=1, column=5, padx=8)
        
        self.selected = None
        try:
            init_db()
        except Error as e:
            messagebox.showerror("Database error", str(e))

    def load_data_async(self):
        """Load all students in background thread."""
        def worker():
            try:
                students = load_all_students()
                self.after(0, lambda: self.on_data_loaded(students))
            except Error as e:
                self.after(0, lambda: self.on_load_error(e))
        
        threading.Thread(target=worker, daemon=True).start()

    def on_data_loaded(self, students):
        self.all_students = students
        self.progress.stop()
        self.progress.pack_forget()
        self._loading = False
        self.do_search()
        self.count_label.config(text=f"Loaded {len(students)} students. Ready.")

    def on_load_error(self, error):
        self.progress.stop()
        self.progress.pack_forget()
        messagebox.showerror("Load failed", f"Could not load students:\n{error}")
        self.destroy()

    def refresh_data(self):
        """Manual refresh from database."""
        self.progress.pack(side="left", padx=8)
        self.progress.start(10)
        self.count_label.config(text="Refreshing...")
        self._loading = True
        self.load_data_async()

    def schedule_search(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(150, self.do_search)

    def focus_first_result(self):
        items = self.tree.get_children()
        if items:
            self.tree.focus_set()
            self.tree.selection_set(items[0])
            self.tree.focus(items[0])

    def do_search(self):
        self._job = None
        if self._loading:
            return
        
        query = self.search_var.get().strip()
        self.filtered_students = search_local(self.all_students, query)
        
        self.tree.delete(*self.tree.get_children())
        self.results = {}
        
        for s in self.filtered_students:
            status = ""
            if s.get("hostel"):
                status = f"✓ {s['hostel']}"
                if s.get("souvenirs_paid"):
                    status += " 🎁"
            iid = self.tree.insert("", "end", values=(
                s["fullName"], s["formReferenceNo"], s["programme"],
                s.get("regPhone") or s.get("phoneNumber") or "", status))
            self.results[iid] = s
        
        n = len(self.filtered_students)
        suffix = "+" if n == 100 and query else ""
        self.count_label.config(text=f"{n}{suffix} result{'s' if n != 1 else ''}")

    def on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        s = self.results[sel[0]]
        self.selected = s
        self.sel_label.config(text=f"{s['fullName']}  |  Ref: {s['formReferenceNo']}  |  {s['programme']}")
        self.phone_var.set(s.get("regPhone") or s.get("phoneNumber") or "")
        self.year_var.set(s.get("year_level") or "")
        self.tshirt_var.set(bool(s.get("tshirt_paid", False)))

    def register(self):
        if not self.selected:
            messagebox.showwarning("No student", "Select a student first.")
            return
        year = self.year_var.get().strip()
        phone = self.phone_var.get().strip()
        tshirt_paid = self.tshirt_var.get()
        if not year:
            messagebox.showwarning("Missing year", "Select the year/level.")
            return
        
        s = self.selected
        if s.get("year_level") and not messagebox.askyesno(
                "Already registered", f"{s['fullName']} is already registered (Year {s['year_level']}). Update?"):
            return
        
        rec = {
            "id": s["id"],
            "formReferenceNo": s["formReferenceNo"],
            "fullName": s["fullName"],
            "email": s["email"],
            "programme": s["programme"],
            "phoneNumber": phone,
            "year_level": year,
            "tshirt_paid": tshirt_paid,
            "registeredAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # Save to DB (blocking but fast)
        try:
            save_registration(rec)
        except Error as e:
            messagebox.showerror("Database error", str(e))
            return
        
        # Update local cache immediately
        s["year_level"] = year
        s["regPhone"] = phone
        s["tshirt_paid"] = tshirt_paid
        s["registeredAt"] = rec["registeredAt"]
        
        # Refresh UI
        messagebox.showinfo("Saved", f"{rec['fullName']} registered for Cybersecurity Club (Year {year}).")
        self.selected = None
        self.sel_label.config(text="No student selected")
        self.year_var.set("")
        self.phone_var.set("")
        self.tshirt_var.set(False)
        self.do_search()


if __name__ == "__main__":
    App().mainloop()