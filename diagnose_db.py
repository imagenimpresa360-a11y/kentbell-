
import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def diagnose():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT", 5432)
        )
        
        print("--- Table: raw_boxmagic ---")
        df_bm = pd.read_sql("SELECT source_hint, COUNT(*) as count, SUM(amount) as total FROM raw_boxmagic GROUP BY source_hint", conn)
        print(df_bm)
        
        print("\n--- Table: consolidated_incomes ---")
        df_ci = pd.read_sql("SELECT sede, COUNT(*) as count, SUM(net_income) as total FROM consolidated_incomes GROUP BY sede", conn)
        print(df_ci)
        
        print("\n--- Recent raw_boxmagic rows ---")
        df_recent = pd.read_sql("SELECT created_at, plan_name, amount, source_hint FROM raw_boxmagic ORDER BY id DESC LIMIT 5", conn)
        print(df_recent)

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    diagnose()
