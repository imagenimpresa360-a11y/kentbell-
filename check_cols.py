
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_table(table_name):
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT", 5432)
        )
        cur = conn.cursor()
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
        cols = [r[0] for r in cur.fetchall()]
        print(f"Columns in {table_name}: {cols}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_table("consolidated_incomes")
    check_table("raw_boxmagic")
