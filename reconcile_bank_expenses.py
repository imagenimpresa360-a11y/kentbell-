import os
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    DB_USER = os.getenv('DB_USER', os.getenv('PGUSER', 'postgres'))
    DB_PASS = os.getenv('DB_PASS', os.getenv('PGPASSWORD', 'password'))
    DB_HOST = os.getenv('DB_HOST', os.getenv('PGHOST', 'localhost'))
    DB_PORT = os.getenv('DB_PORT', os.getenv('PGPORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', os.getenv('PGDATABASE', 'railway'))
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Manejar el protocolo postgres:// legacy si viene directo de un addon de base de datos
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Asignar variables individuales para el resto del archivo que las utiliza
DB_USER = os.getenv('DB_USER', os.getenv('PGUSER', 'postgres'))
DB_PASS = os.getenv('DB_PASS', os.getenv('PGPASSWORD', 'password'))
DB_HOST = os.getenv('DB_HOST', os.getenv('PGHOST', 'localhost'))
DB_PORT = os.getenv('DB_PORT', os.getenv('PGPORT', '5432'))
DB_NAME = os.getenv('DB_NAME', os.getenv('PGDATABASE', 'railway'))

engine = create_engine(DATABASE_URL)

def reconcile_bank_expenses():
    try:
        # 1. Load Data
        query_ledger = "SELECT * FROM expense_ledger WHERE status = 'PENDING_PAYMENT'"
        df_ledger = pd.read_sql(query_ledger, engine)
        
        # Bank output (negative amounts)
        query_bank = "SELECT * FROM raw_bank WHERE amount < 0"
        df_bank = pd.read_sql(query_bank, engine)
        
        if df_ledger.empty:
            print("No hay gastos pendientes en el ledger para conciliar.")
            return

        if df_bank.empty:
            print("No hay movimientos bancarios (egresos) para conciliar.")
            return

        matches_found = 0
        
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME
        )
        cur = conn.cursor()

        for idx, ledger_row in df_ledger.iterrows():
            # Criteria: Match amount (abs) and date proximity (±90 days to allow for long payment terms and cross-year debts)
            target_amount = -float(ledger_row['amount_due'])
            target_date = pd.to_datetime(ledger_row['due_date'])
            
            # Simple exact amount match first
            # We look for bank movements within a 90-day window after the invoice date
            bank_match = df_bank[
                (df_bank['amount'] == target_amount) & 
                ((pd.to_datetime(df_bank['bank_date']) - target_date).dt.days.between(-5, 90))
            ]
            
            if not bank_match.empty:
                # Use the first available match that hasn't been linked yet
                match_id = bank_match.iloc[0]['id']
                ledger_uuid = ledger_row['uuid']
                paid_date = bank_match.iloc[0]['bank_date']
                
                print(f"Match encontrado: {ledger_row['description']} (${ledger_row['amount_due']}) -> Banco ID {match_id}")
                
                # Update Ledger
                cur.execute("""
                    UPDATE expense_ledger 
                    SET status = 'PAID_VERIFIED', 
                        paid_date = %s,
                        amount_paid = %s,
                        source_bank_id = %s
                    WHERE uuid = %s
                """, (paid_date, ledger_row['amount_due'], str(match_id), ledger_uuid))
                
        # 2. SEGUNDA PASADA: Conciliación por Folio (Para gastos divididos entre sedes)
        # Buscamos grupos de gastos con el mismo folio cuyo total sume un movimiento bancario
        pending_folios = df_ledger[df_ledger['source_sii_folio'].notnull()]['source_sii_folio'].unique()
        
        for folio in pending_folios:
            group = df_ledger[df_ledger['source_sii_folio'] == folio]
            total_group = group['amount_due'].sum()
            target_amount = -float(total_group)
            target_date = pd.to_datetime(group['due_date'].min())
            
            # Buscamos un movimiento bancario que coincida con la suma total del folio
            bank_match = df_bank[
                (df_bank['amount'] == target_amount) & 
                ((pd.to_datetime(df_bank['bank_date']) - target_date).dt.days.between(-5, 90))
            ]
            
            if not bank_match.empty:
                match_id = bank_match.iloc[0]['id']
                paid_date = bank_match.iloc[0]['bank_date']
                
                print(f"Match GRUPAL encontrado: Folio {folio} Total ${total_group} -> Banco ID {match_id}")
                
                for _, row in group.iterrows():
                    cur.execute("""
                        UPDATE expense_ledger 
                        SET status = 'PAID_VERIFIED', 
                            paid_date = %s,
                            amount_paid = %s,
                            source_bank_id = %s
                        WHERE uuid = %s
                    """, (paid_date, row['amount_due'], str(match_id), row['uuid']))
                
                df_bank = df_bank[df_bank['id'] != match_id]
                matches_found += 1

        conn.commit()
        print(f"Reconciliación bancaria terminada. Matches realizados: {matches_found}")
        
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error en reconciliación bancaria: {e}")

if __name__ == "__main__":
    reconcile_bank_expenses()
