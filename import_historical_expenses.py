import os
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

def import_historical_expenses(file_path):
    try:
        print(f"Leyendo consolidado de egresos: {file_path}")
        df = pd.read_excel(file_path)
        
        # Filtramos solo 2025 y que tengan montos
        df = df[(df['Año'] == 2025) & (df['Egresos_totales'] > 0)]
        
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME
        )
        cur = conn.cursor()
        
        # Obtenemos el ID de una categoría base para el histórico
        cur.execute("SELECT id FROM expense_categories WHERE name = 'Administración' LIMIT 1")
        res = cur.fetchone()
        if not res:
            cur.execute("SELECT id FROM expense_categories LIMIT 1")
            res = cur.fetchone()
        cat_id = res[0]
        
        records_added = 0
        for _, row in df.iterrows():
            bruto = float(row['Egresos_totales'])
            neto = round(bruto / 1.19)
            iva = bruto - neto
            fecha = row['Fecha']
            
            query = """
                INSERT INTO expense_ledger 
                (description, category_id, amount_due, amount_paid, net_amount, iva_amount, 
                 due_date, paid_date, status, sede)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(query, (
                "Consolidado Histórico 2025", cat_id, bruto, bruto, neto, iva,
                fecha, fecha, 'PAID_VERIFIED', 'General'
            ))
            records_added += 1
            
        conn.commit()
        print(f"Se han importado {records_added} meses de gastos históricos 2025.")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error importando egresos: {e}")
        return False

if __name__ == "__main__":
    file_path = 'CONSOLIDADO  EGRESOS 2SEDES.xlsx'
    import_historical_expenses(file_path)
