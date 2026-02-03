
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def apply_schema():
    conn = None
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT", 5432)
        )
        cur = conn.cursor()
        
        with open("schema.sql", "r", encoding="utf-8") as f:
            sql = f.read()
        
        print("Applying schema.sql...")
        cur.execute(sql)
        conn.commit()
        print("✅ Schema applied successfully.")
        
    except Exception as e:
        print(f"❌ Error applying schema: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    apply_schema()
