
import psycopg2
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "admin")

def check_type():
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    cur = conn.cursor()
    cur.execute("SELECT raw_data FROM raw_boxmagic WHERE raw_data::text LIKE '%raw_line%' LIMIT 1")
    row = cur.fetchone()
    if row:
        val = row[0]
        print(f"Type from DB (New Record): {type(val)}")
        print(f"Value: {val}")
    else:
        print("No new records found.")
    
    # Check DataFrame behavior
    cur.execute("SELECT raw_data FROM raw_boxmagic WHERE raw_data IS NOT NULL LIMIT 1")
    df = pd.DataFrame(cur.fetchall(), columns=['raw_data'])
    df_val = df.iloc[0]['raw_data']
    print(f"Type from DF: {type(df_val)}")
    print(f"DF Value: {df_val}")
    
    conn.close()

if __name__ == "__main__":
    check_type()
