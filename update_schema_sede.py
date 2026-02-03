import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

def update_schema():
    try:
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME
        )
        cur = conn.cursor()
        
        print("Añadiendo campo 'sede' a tablas de gastos...")
        
        # Add sede to expense_ledger
        cur.execute("ALTER TABLE expense_ledger ADD COLUMN IF NOT EXISTS sede VARCHAR(50);")
        
        # Add sede to raw_lioren_purchases (for future automation)
        cur.execute("ALTER TABLE raw_lioren_purchases ADD COLUMN IF NOT EXISTS sede VARCHAR(50);")
        
        conn.commit()
        print("Schema actualizado con éxito.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error actualizando schema: {e}")

if __name__ == "__main__":
    update_schema()
