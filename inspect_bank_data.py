import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')

try:
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cur = conn.cursor()
    cur.execute("SELECT bank_date, description, amount, created_at FROM raw_bank ORDER BY created_at DESC LIMIT 50")
    rows = cur.fetchall()
    
    print(f"Total registros encontrados: {len(rows)}")
    print("-" * 50)
    for r in rows:
        print(f"Fecha Mov: {r[0]} | Desc: {r[1]} | Monto: {r[2]} | Cargado el: {r[3]}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
