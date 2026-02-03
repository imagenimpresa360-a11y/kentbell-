
import os
import psycopg2
import pandas as pd
import json
from dotenv import load_dotenv

load_dotenv()

def inspect_raw():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT", 5432)
        )
        
        df = pd.read_sql("SELECT raw_data FROM raw_boxmagic WHERE source_hint = 'Marina' LIMIT 5", conn)
        for idx, row in df.iterrows():
            print(f"Row {idx}: {row['raw_data']}")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_raw()
