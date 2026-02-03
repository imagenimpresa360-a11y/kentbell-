import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("--- Todas las Remuneraciones de Cristian ---")
    df = pd.read_sql(text("SELECT r.*, c.name FROM coach_remunerations r JOIN coaches c ON r.coach_id = c.id WHERE c.name LIKE '%CRISTIAN%'"), conn)
    print(df)

    print("\n--- Todos los Egresos en Ledger que digan CRISTIAN ---")
    df_l = pd.read_sql(text("SELECT * FROM expense_ledger WHERE description LIKE '%CRISTIAN%'"), conn)
    print(df_l)
