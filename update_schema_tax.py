import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

def update_schema_tax():
    try:
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME
        )
        cur = conn.cursor()
        
        print("Actualizando schema para soporte de impuestos y comisiones...")
        
        # 1. Update expense_ledger
        cur.execute("ALTER TABLE expense_ledger ADD COLUMN IF NOT EXISTS net_amount NUMERIC(12, 2) DEFAULT 0;")
        cur.execute("ALTER TABLE expense_ledger ADD COLUMN IF NOT EXISTS iva_amount NUMERIC(12, 2) DEFAULT 0;")
        cur.execute("ALTER TABLE expense_ledger ADD COLUMN IF NOT EXISTS other_tax_amount NUMERIC(12, 2) DEFAULT 0;")
        
        # 2. Update consolidated_incomes
        cur.execute("ALTER TABLE consolidated_incomes ADD COLUMN IF NOT EXISTS commission_amount NUMERIC(12, 2) DEFAULT 0;")
        cur.execute("ALTER TABLE consolidated_incomes ADD COLUMN IF NOT EXISTS net_income NUMERIC(12, 2) DEFAULT 0;")
        cur.execute("ALTER TABLE consolidated_incomes ADD COLUMN IF NOT EXISTS iva_debit NUMERIC(12, 2) DEFAULT 0;")
        
        conn.commit()
        print("Schema actualizado con éxito.")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando schema: {e}")
        return False

if __name__ == "__main__":
    update_schema_tax()
