import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

new_categories = [
    ('Sueldo Coach', 'Remuneraciones de coaches.'),
    ('Administradores de Local', 'Sueldos de administración.'),
    ('Personal de Aseo', 'Sueldos de personal de limpieza.'),
    ('Retiros Socios', 'Retiros de utilidades o pagos a socios fundadores.'),
    ('Arriendo Campanario', 'Pago de alquiler de Sede Campanario.'),
    ('Arriendo Marina', 'Pago de alquiler de Sede Marina.'),
]

with engine.begin() as conn:
    for name, desc in new_categories:
         conn.execute(text("""
            INSERT INTO expense_categories (name, description)
            VALUES (:name, :desc)
            ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
         """), {"name": name, "desc": desc})
    print("Categorias actualizadas con detalle de RRHH y Sedes.")
