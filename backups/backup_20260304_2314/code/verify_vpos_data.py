
import psycopg2
import os
import sys
from dotenv import load_dotenv

# Configurar salida para soportar utf-8
sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "admin")

try:
    print("Conectando DB...")
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    cur = conn.cursor()
    
    # 1. Conteo total
    cur.execute("SELECT COUNT(*) FROM raw_virtualpos")
    total = cur.fetchone()[0]
    print(f"Total registros en raw_virtualpos: {total}")
    
    # 2. Rango de fechas
    cur.execute("SELECT MIN(transaction_date), MAX(transaction_date) FROM raw_virtualpos")
    min_date, max_date = cur.fetchone()
    print(f"Fecha Inicio: {min_date}")
    print(f"Fecha Fin: {max_date}")
    
    # 3. Muestra de 5 registros recientes
    print("\nÚltimos 5 registros insertados:")
    cur.execute("SELECT vpos_code, amount, transaction_date, card_type FROM raw_virtualpos ORDER BY transaction_date DESC LIMIT 5")
    rows = cur.fetchall()
    for r in rows:
        print(f" - {r}")
        
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error verificación: {e}")
