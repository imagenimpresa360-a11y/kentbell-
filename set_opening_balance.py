import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

def set_balance():
    try:
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME
        )
        cur = conn.cursor()
        
        # Saldo Final al 30/12/2025 según Excel
        opening_balance = 2075089
        
        cur.execute("""
            INSERT INTO system_settings (key, value, label) 
            VALUES ('bank_opening_balance_2026', %s, 'Saldo Inicial Banco 2026') 
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (str(opening_balance),))
        
        conn.commit()
        print(f"✅ Saldo inicial 2026 fijado en: ${opening_balance:,.0f}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    set_balance()
