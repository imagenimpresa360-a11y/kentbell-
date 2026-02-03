
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT", 5432)
        )
        cur = conn.cursor()
        
        # Add source_hint to raw tables if missing
        for table in ["raw_boxmagic", "raw_virtualpos", "raw_lioren_sales"]:
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND column_name = 'source_hint'")
            if not cur.fetchone():
                print(f"Adding source_hint to {table}...")
                cur.execute(f"ALTER TABLE {table} ADD COLUMN source_hint VARCHAR(50)")
        
        # Ensure consolidated_incomes has sede
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = 'consolidated_incomes' AND column_name = 'sede'")
        if not cur.fetchone():
            print(f"Adding sede to consolidated_incomes...")
            cur.execute(f"ALTER TABLE consolidated_incomes ADD COLUMN sede VARCHAR(50)")

        conn.commit()
        print("✅ Migration successful.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Migration error: {e}")

if __name__ == "__main__":
    migrate()
