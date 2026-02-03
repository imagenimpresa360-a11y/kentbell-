import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

with engine.begin() as conn:
    # Buscar remuneraciones sin UUID de gasto
    df = pd.read_sql("SELECT r.id, c.name, r.month, r.year, r.total_honorarios, r.sede FROM coach_remunerations r JOIN coaches c ON r.coach_id = c.id WHERE r.expense_uuid IS NULL", engine)
    
    for _, row in df.iterrows():
        print(f"Reparando registro {row['id']} para {row['name']}...")
        description = f"Honorarios {row['name']} - {row['month']}/{row['year']}"
        due_date = f"{row['year']}-{row['month']:02d}-01"
        
        # 1. Crear egreso en PENDING_PAYMENT para que aparezca en el conciliador
        res = conn.execute(text("""
            INSERT INTO expense_ledger (description, amount_due, due_date, category_id, sede, status)
            VALUES (:d, :a, :f, (SELECT id FROM expense_categories WHERE name = 'Sueldos Profesores' LIMIT 1), :s, 'PENDING_PAYMENT')
            RETURNING uuid
        """), {"d": description, "a": row['total_honorarios'], "f": due_date, "s": row['sede']})
        
        new_uuid = res.fetchone()[0]
        
        # 2. Vincular y volver a poner en PENDING en remuneraciones para habilitar match
        conn.execute(text("""
            UPDATE coach_remunerations 
            SET expense_uuid = :euuid, status = 'PENDING' 
            WHERE id = :id
        """), {"euuid": new_uuid, "id": row['id']})

print("✅ Reparación completada. Los gastos de Joaquín ahora deberían aparecer en el conciliador manual.")
