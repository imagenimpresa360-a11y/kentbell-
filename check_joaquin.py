import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

print("--- Estado de Joaquin en el Ledger ---")
df = pd.read_sql("SELECT description, due_date, status, amount_due, sede FROM expense_ledger WHERE description LIKE '%JOAQUIN%'", engine)
print(df)
