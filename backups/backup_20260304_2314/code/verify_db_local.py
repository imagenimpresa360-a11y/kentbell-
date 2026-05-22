import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

query = text("""
    SELECT sede, TO_CHAR(fecha_pago, 'YYYY-MM') as mes, COUNT(*) 
    FROM raw_boxmagic_pagos 
    WHERE fecha_pago BETWEEN '2026-01-01' AND '2026-02-28'
    GROUP BY sede, mes 
    ORDER BY mes
""")

try:
    with engine.connect() as conn:
        print("--- CONTEO DE REGISTROS EN DATABASE (ENE-FEB 2026) ---")
        res = conn.execute(query)
        rows = res.mappings().all()
        if not rows:
            print("No se encontraron registros.")
        else:
            for row in rows:
                print(f"Sede: {row['sede']} | Mes: {row['mes']} | Registros: {row['count']}")
except Exception as e:
    print(f"Error: {e}")
