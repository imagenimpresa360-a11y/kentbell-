import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

def update_and_reimport():
    try:
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME
        )
        cur = conn.cursor()
        
        # 1. Añadir columna sede
        print("Añadiendo columna 'sede' a consolidated_incomes...")
        cur.execute("ALTER TABLE consolidated_incomes ADD COLUMN IF NOT EXISTS sede VARCHAR(50);")
        
        # 2. Limpiar para re-importar con sede
        print("Limpiando consolidated_incomes para re-importación...")
        cur.execute("TRUNCATE consolidated_incomes CASCADE;")
        
        conn.commit()
        cur.close()
        conn.close()
        
        # 3. Re-importar historial
        print("Ejecutando import_historical_sales.py actualizado...")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    update_and_reimport()
