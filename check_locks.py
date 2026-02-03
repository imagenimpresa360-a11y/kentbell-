
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_locks():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS")
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT pid, usename, pg_blocking_pid(pid) as blocked_by, 
            query as blocked_query
            FROM pg_stat_activity
            WHERE pg_blocking_pid(pid) != 0;
        """)
        rows = cur.fetchall()
        if rows:
            print("❌ BLECKING DETECTED:")
            for r in rows:
                print(r)
        else:
            print("✅ No blocks detected.")
            
        cur.execute("SELECT count(*) FROM raw_boxmagic")
        print(f"Rows in raw_boxmagic: {cur.fetchone()[0]}")
        
    except Exception as e:
        print(f"Error checking locks: {e}")

if __name__ == "__main__":
    check_locks()
