#!/usr/bin/env python3
"""
Export MySQL table to PDF
Usage: python sql_to_pdf.py [options]

Examples:
  python sql_to_pdf.py --table registered_students --db hostel_db
  python sql_to_pdf.py --table admitted_students --db umatdb --output students.pdf
  python sql_to_pdf.py --query "SELECT * FROM hostel_db.registered_students WHERE souvenirs_paid=1" --output paid.pdf
"""

import argparse
import sys
from pathlib import Path

try:
    import mysql.connector
    from fpdf import FPDF
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install mysql-connector-python fpdf2")
    sys.exit(1)


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
}


def fetch_data(table=None, db=None, query=None, limit=None):
    """Fetch data from MySQL."""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    if query:
        sql = query
        if limit:
            sql += f" LIMIT {limit}"
        cursor.execute(sql)
    else:
        if not table or not db:
            raise ValueError("Either --query or both --table and --db required")
        sql = f"SELECT * FROM `{db}`.`{table}`"
        if limit:
            sql += f" LIMIT {limit}"
        cursor.execute(sql)

    rows = cursor.fetchall()
    columns = cursor.column_names
    cursor.close()
    conn.close()
    return columns, rows


def create_pdf(columns, rows, output_path, title="Table Export"):
    """Generate PDF from column names and rows."""
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(5)

    # Calculate column widths
    page_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_count = len(columns)

    # Measure content widths
    pdf.set_font("Helvetica", "", 8)
    col_widths = []
    for i, col in enumerate(columns):
        max_w = pdf.get_string_width(str(col)) + 4
        for row in rows:
            val = str(row.get(col, ""))
            w = pdf.get_string_width(val) + 4
            if w > max_w:
                max_w = w
        col_widths.append(min(max_w, 80))  # Cap at 80mm

    # Scale if too wide
    total_w = sum(col_widths)
    if total_w > page_width:
        scale = page_width / total_w
        col_widths = [w * scale for w in col_widths]

    # Header
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(30, 60, 110)
    pdf.set_text_color(255, 255, 255)
    for i, col in enumerate(columns):
        pdf.cell(col_widths[i], 7, str(col)[:40], border=1, fill=True, align="C")
    pdf.ln()

    # Rows
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(0, 0, 0)
    fill = False
    for row in rows:
        # Check page break
        if pdf.get_y() > pdf.h - 20:
            pdf.add_page()
            # Re-draw header
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(30, 60, 110)
            pdf.set_text_color(255, 255, 255)
            for i, col in enumerate(columns):
                pdf.cell(col_widths[i], 7, str(col)[:40], border=1, fill=True, align="C")
            pdf.ln()
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(0, 0, 0)

        if fill:
            pdf.set_fill_color(240, 245, 250)
        else:
            pdf.set_fill_color(255, 255, 255)

        for i, col in enumerate(columns):
            val = str(row.get(col, ""))
            pdf.cell(col_widths[i], 6, val[:60], border=1, fill=True, align="L")
        pdf.ln()
        fill = not fill

    pdf.output(output_path)
    print(f"PDF saved: {output_path} ({len(rows)} rows)")


def main():
    parser = argparse.ArgumentParser(description="Export MySQL table/query to PDF")
    parser.add_argument("--table", help="Table name")
    parser.add_argument("--db", help="Database name")
    parser.add_argument("--query", help="Custom SQL query")
    parser.add_argument("--output", "-o", default="export.pdf", help="Output PDF file")
    parser.add_argument("--limit", type=int, help="Limit rows")
    parser.add_argument("--title", default="Table Export", help="PDF title")
    args = parser.parse_args()

    if not args.query and not (args.table and args.db):
        parser.error("Provide either --query OR both --table and --db")

    try:
        columns, rows = fetch_data(
            table=args.table,
            db=args.db,
            query=args.query,
            limit=args.limit
        )
        if not rows:
            print("No data found.")
            return
        create_pdf(columns, rows, args.output, args.title)
    except mysql.connector.Error as e:
        print(f"MySQL error: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()