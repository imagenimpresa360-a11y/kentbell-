
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_sums():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASS", "admin")
        )
        cur = conn.cursor()
        
        print("--- SUMAS MARINA ---")
        cur.execute("SELECT SUM(amount) FROM raw_boxmagic WHERE source_hint = 'Marina'")
        raw_sum = cur.fetchone()[0] or 0
        print(f"Raw BoxMagic Sum (Marina): {raw_sum}")
        
        cur.execute("SELECT SUM(net_income) FROM consolidated_incomes WHERE sede = 'Marina'")
        cons_sum = cur.fetchone()[0] or 0
        print(f"Consolidated Sum (Marina): {cons_sum}")
        
        print("\n--- DETALLE POR FECHA (RAW) ---")
        cur.execute("SELECT created_at, SUM(amount) FROM raw_boxmagic WHERE source_hint = 'Marina' GROUP BY created_at ORDER BY created_at")
        for row in cur.fetchall():
            print(f"Fecha: {row[0]} | Suma: {row[1]}")
            
        print("\n--- POSIBLES DIFERENCIAS (Anio distinto a 2026?) ---")
        cur.execute("SELECT created_at, amount, plan_name FROM raw_boxmagic WHERE source_hint = 'Marina' AND EXTRACT(YEAR FROM created_at) != 2026")
        for row in cur.fetchall():
            print(f"FUERA DE 2026 -> Fecha: {row[0]} | Monto: {row[1]} | Plan: {row[2]}")

        # Check for non-Active statuses if any
        cur.execute("SELECT payment_status, SUM(amount) FROM raw_boxmagic WHERE source_hint = 'Marina' GROUP BY payment_status")
        print("\n--- POR ESTADO ---")
        for row in cur.fetchall():
            print(f"Estado: {row[0]} | Suma: {row[1]}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_sums()
