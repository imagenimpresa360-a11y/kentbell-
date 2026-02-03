import os
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from dotenv import load_dotenv
import uuid

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

def import_historical_sales(file_path):
    try:
        print(f"Leyendo histórico de ventas: {file_path}")
        df = pd.read_excel(file_path)
        
        # Filtrar solo registros con ingresos > 0
        df = df[df['Ingresos_Abonos'] > 0]
        
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME
        )
        cur = conn.cursor()
        
        # No truncamos, solo añadimos si no existen o usamos un tag especial
        # Para evitar duplicidad en re-ejecución, podríamos usar el Origen 'Histórico'
        
        records_added = 0
        for _, row in df.iterrows():
            bruto = float(row['Ingresos_Abonos'])
            neto = round(bruto / 1.19)
            iva = bruto - neto
            fecha = row['Fecha']
            sede = row['Sede']
            
            # Insertamos en consolidated_incomes
            # Usamos status 'MATCH_FULL' para histórico ya que son datos ya procesados externamente
            query = """
                INSERT INTO consolidated_incomes 
                (transaction_date, amount_expected, amount_received, amount_banked, 
                 status, net_income, iva_debit, commission_amount, sede)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(query, (
                fecha, bruto, bruto, bruto, 
                'MATCH_FULL', neto, iva, 0, sede
            ))
            records_added += 1
            
        conn.commit()
        print(f"Se han importado {records_added} registros históricos exitosamente.")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error importando histórico: {e}")
        return False

if __name__ == "__main__":
    file_path = r'C:\Users\DELL\Desktop\Agente kent-bell\downloads\historico 2020-2025\1er reporte consolidado solo ventas 2020-2025.xlsx'
    import_historical_sales(file_path)
