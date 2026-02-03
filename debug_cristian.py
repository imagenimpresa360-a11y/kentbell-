import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

def get_data():
    with engine.connect() as conn:
        print("--- Buscando Coach Cristian ---")
        q1 = text("SELECT id, name FROM coaches WHERE name LIKE '%CRISTIAN%'")
        res1 = conn.execute(q1)
        coaches = res1.fetchall()
        print(coaches)

        if coaches:
            cid = int(coaches[0][0])
            print(f"\n--- Remuneraciones de Cristian (ID: {cid}) ---")
            q2 = text("SELECT id, month, year, total_honorarios, sede, status, expense_uuid FROM coach_remunerations WHERE coach_id = :id")
            res2 = conn.execute(q2, {"id": cid})
            rems = res2.fetchall()
            for r in rems:
                print(r)
            
            uuids = [r[6] for r in rems if r[6] is not None]
            if uuids:
                print("\n--- Estado en Libro de Egresos (Ledger) ---")
                # PostgreSQL ANY expects an array, but we can also use tuple and IN
                q3 = text(f"SELECT uuid, description, amount_due, sede, status FROM expense_ledger WHERE uuid IN ({','.join([f':u{i}' for i in range(len(uuids))])})")
                params = {f"u{i}": str(u) for i, u in enumerate(uuids)}
                res3 = conn.execute(q3, params)
                ledger = res3.fetchall()
                for l in ledger:
                    print(l)

if __name__ == "__main__":
    get_data()
