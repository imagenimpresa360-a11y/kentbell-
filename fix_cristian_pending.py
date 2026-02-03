import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

with engine.begin() as conn:
    print("Reparando registros de Cristian para permitir conciliación manual...")
    
    # 1. Resetear el Ledger
    res1 = conn.execute(text("""
        UPDATE expense_ledger 
        SET status = 'PENDING_PAYMENT', source_bank_id = NULL, amount_paid = 0
        WHERE description LIKE '%Honorarios CRISTIAN%'
    """))
    print(f"Egresos actualizados: {res1.rowcount}")
    
    # 2. Resetear las Remuneraciones
    res2 = conn.execute(text("""
        UPDATE coach_remunerations 
        SET status = 'PENDING'
        WHERE coach_id = (SELECT id FROM coaches WHERE name LIKE '%CRISTIAN%' LIMIT 1)
    """))
    print(f"Honorarios actualizados: {res2.rowcount}")

print("✅ Operación completada. Cristian ahora debería aparecer con sus dos sedes en la Conciliación Manual.")
