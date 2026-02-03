
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_schema():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS")
        )
        cur = conn.cursor()
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'expense_ledger'")
        rows = cur.fetchall()
        print("Columns in expense_ledger:")
        for r in rows:
            print(f"- {r[0]} ({r[1]})")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
