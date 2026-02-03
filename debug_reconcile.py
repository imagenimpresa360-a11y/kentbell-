import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

print("--- Gastos Pendientes en Ledger ---")
df = pd.read_sql("SELECT uuid, description, due_date, amount_due, status FROM expense_ledger WHERE status = 'PENDING_PAYMENT' ORDER BY due_date DESC", engine)
print(df)

print("\n--- Remuneraciones de Coaches ---")
df_c = pd.read_sql("SELECT id, month, year, total_honorarios, status, expense_uuid FROM coach_remunerations", engine)
print(df_c)
