import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("--- Remuneraciones ---")
    df = pd.read_sql(text("SELECT id, status, sede, expense_uuid FROM coach_remunerations WHERE coach_id = 4"), conn)
    print(df.to_string())

    print("\n--- Ledger ---")
    df_l = pd.read_sql(text("SELECT uuid, status, sede, description FROM expense_ledger WHERE description LIKE '%CRISTIAN%'"), conn)
    print(df_l.to_string())
