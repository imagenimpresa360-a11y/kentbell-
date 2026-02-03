
import pandas as pd
import re
import psycopg2
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "admin")

def parse_active_line(line):
    # Regex to find email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', line)
    email = email_match.group(0) if email_match else None
    
    # Regex for status (activo/inactivo/congelado)
    status_match = re.search(r'"(activo|inactivo|congelado)"', line.lower())
    status = status_match.group(1) if status_match else "desconocido"
    
    # Extract name (everything before email, cleaning prefixes like '4 ')
    name = line.split(email)[0].strip() if email else line.split(',')[0]
    name = re.sub(r'^\d+\s+', '', name).replace('"', '').replace(',', '').strip()
    
    # Extract Plan (everything between status and next specific markers if possible)
    # This is brittle but based on provided sample
    plan = "Plan No Identificado"
    if status != "desconocido":
        parts = line.split(f'"{status}"')
        if len(parts) > 1:
            plan_part = parts[1].split(',')[1].replace('"', '').strip()
            plan = plan_part if plan_part else plan

    return {
        "full_name": name,
        "email": email,
        "status": status,
        "plan_name": plan
    }

def process_active_students_content(content, sede="General"):
    lines = content.splitlines()
    data = []
    for line in lines[1:]: # Skip header
        if not line.strip(): continue
        parsed = parse_active_line(line)
        if parsed['email']:
            data.append(parsed)
    
    df = pd.DataFrame(data)
    if df.empty:
        return 0, 0

    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        
        # Add column if not exists (defensive)
        cur.execute("ALTER TABLE raw_active_students ADD COLUMN IF NOT EXISTS sede VARCHAR(50)")
        
        # For Active Students, we usually want the latest snapshot per sede.
        print(f"Truncating raw_active_students for sede {sede}...")
        cur.execute("DELETE FROM raw_active_students WHERE sede = %s", (sede,))
        
        inserted = 0
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO raw_active_students (full_name, email, status, plan_name, sede)
                VALUES (%s, %s, %s, %s, %s)
            """, (row['full_name'], row['email'], row['status'], row['plan_name'], sede))
            inserted += 1
            
        conn.commit()
        cur.close()
        conn.close()
        return inserted, 0
    except Exception as e:
        print(f"Error processed_active_students: {e}")
        return 0, 0

if __name__ == "__main__":
    # Test with local file if exists
    FILE_PATH = r"C:\Users\DELL\Desktop\Agente kent-bell\alumnos activos enero 29012026.csv"
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            c = f.read()
        ins, err = process_active_students_content(c)
        print(f"Inserted: {ins}")
