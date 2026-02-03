import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

CATEGORIES = [
    'Arriendos',
    'Servicios Básicos',
    'Limpieza y Aseo',
    'Mantenimiento de Equipos',
    'Sueldos de Entrenadores',
    'Administración',
    'Asesores',
    'Plataforma de Gestión',
    'Plataformas de Pago/Facturación',
    'Banco (Créditos)',
    'Retiros',
    'Impuestos Mensuales (IVA)',
    'Rentas',
    'Convenios 1 y 2',
    'Convenio 3'
]

def sync_categories():
    try:
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME
        )
        cur = conn.cursor()
        
        print("Sincronizando categorías...")
        # Truncate and reset (CASCADE because ledger might reference them, though ledger is empty)
        cur.execute("TRUNCATE expense_categories CASCADE;")
        
        for cat in CATEGORIES:
            cur.execute("INSERT INTO expense_categories (name) VALUES (%s)", (cat,))
            
        conn.commit()
        print("Categorías sincronizadas con éxito.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error sincronizando categorías: {e}")

if __name__ == "__main__":
    sync_categories()
