import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

new_categories = [
    ('Servicios Básicos (Agua/Luz/Internet)', 'Pagos de servicios básicos de las sedes.'),
    ('Mantenimiento Equipos e Infraestructura', 'Reparación de máquinas, discos, barras, y arreglos del local.'),
    ('Software y Plataformas', 'Suscripciones como BoxMagic, VirtualPOS, hosting, dominios.'),
    ('Impuestos, Patentes y Contabilidad', 'Pago de IVA, patentes municipales, honorarios contables.'),
    ('Marketing y Publicidad', 'Gastos en Meta Ads, Google Ads, impresiones y merchandising.'),
]

with engine.begin() as conn:
    for name, desc in new_categories:
         conn.execute(text("""
            INSERT INTO expense_categories (name, description)
            VALUES (:name, :desc)
            ON CONFLICT (name) DO NOTHING
         """), {"name": name, "desc": desc})
    print("Categorías añadidas.")
