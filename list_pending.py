import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("--- Todos los Gastos Pendientes ---")
    df = pd.read_sql(text("SELECT due_date, description, amount_due, sede, status FROM expense_ledger WHERE status = 'PENDING_PAYMENT' ORDER BY description"), conn)
    print(df.to_string())
