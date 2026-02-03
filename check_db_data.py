import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

def check_boxmagic_data():
    try:
        with engine.connect() as conn:
            # Check if there's 2025 data in raw_boxmagic
            query = text("SELECT COUNT(*) FROM raw_boxmagic")
            count = conn.execute(query).scalar()
            print(f"Total rows in raw_boxmagic: {count}")
            
            if count > 0:
                query_2025 = text("SELECT COUNT(*) FROM raw_boxmagic WHERE (raw_data->>'Fecha de pago') LIKE '%2025%'")
                count_2025 = conn.execute(query_2025).scalar()
                print(f"Rows with 2025 in 'Fecha de pago': {count_2025}")
                
                if count_2025 > 0:
                    query_sample = text("SELECT raw_data FROM raw_boxmagic WHERE (raw_data->>'Fecha de pago') LIKE '%2025%' LIMIT 5")
                    sample = conn.execute(query_sample).fetchall()
                    for s in sample:
                        print(s[0])
            else:
                print("raw_boxmagic is empty.")
                
            # Check consolidated_incomes
            query_ci = text("SELECT COUNT(*) FROM consolidated_incomes WHERE EXTRACT(YEAR FROM transaction_date) = 2025")
            count_ci = conn.execute(query_ci).scalar()
            print(f"Total rows in consolidated_incomes for 2025: {count_ci}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_boxmagic_data()
