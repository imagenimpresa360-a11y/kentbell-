import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def clean_database():
    load_dotenv()
    db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    engine = create_engine(db_url)
    
    with engine.begin() as conn:
        print("Borrando registros operativos...")
        conn.execute(text("TRUNCATE TABLE raw_boxmagic_pagos CASCADE;"))
        conn.execute(text("TRUNCATE TABLE raw_virtualpos CASCADE;"))
        conn.execute(text("TRUNCATE TABLE raw_lioren_sales CASCADE;"))
        conn.execute(text("TRUNCATE TABLE reconciliation_results CASCADE;"))
        conn.execute(text("TRUNCATE TABLE reconciliation_anomalies CASCADE;"))
        # We also might want to clean the other old raw ones just in case
        conn.execute(text("TRUNCATE TABLE raw_boxmagic CASCADE;"))
        conn.execute(text("TRUNCATE TABLE consolidated_incomes CASCADE;"))
        
        print("SUCCESS: Base de datos completamente limpia y lista para la prueba en limpio.")

if __name__ == "__main__":
    clean_database()
