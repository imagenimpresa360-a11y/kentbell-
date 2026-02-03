import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

def migration():
    try:
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME
        )
        cur = conn.cursor()
        
        # 1. Corrección de SEDE: Rellenar con 'General' donde sea NULL
        print("Actualizando datos de sedes faltantes...")
        cur.execute("UPDATE consolidated_incomes SET sede = 'General' WHERE sede IS NULL;")
        cur.execute("UPDATE expense_ledger SET sede = 'General' WHERE sede IS NULL;")
        
        # 2. Módulo de Coaches (Entrenadores)
        print("Creando tablas para gestión de Coaches...")
        
        # Tabla de Perfiles de Coaches
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coaches (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                rut VARCHAR(20) UNIQUE,
                base_rate NUMERIC(12, 2) DEFAULT 7000,
                default_sede VARCHAR(50) DEFAULT 'General',
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Tabla de Seguimiento de Horas y Honorarios
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coach_remunerations (
                id SERIAL PRIMARY KEY,
                coach_id INTEGER REFERENCES coaches(id),
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                hours_worked NUMERIC(6, 2) DEFAULT 0,
                hourly_rate NUMERIC(12, 2),
                total_honorarios NUMERIC(12, 2),
                status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, INVOICED, PAID
                sii_folio INTEGER,
                sede VARCHAR(50),
                expense_uuid UUID REFERENCES expense_ledger(uuid),
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(coach_id, month, year, sede)
            );
        """)
        
        # 3. Seed inicial de Coaches (basado en la imagen enviada por el usuario)
        coaches_seed = [
            ('JOAQUIN', 7000, 'Marina'),
            ('GABY', 7000, 'Marina'),
            ('NICOLAS', 9000, 'Marina'),
            ('CRISTIAN', 7000, 'Marina'),
            ('GERALDINE', 7000, 'Marina'),
            ('RODRIGO', 7000, 'Marina'),
            ('DAPHNE', 7000, 'Marina'),
            ('JAVIERA', 7000, 'Marina')
        ]
        
        for name, rate, sede in coaches_seed:
            cur.execute("""
                INSERT INTO coaches (name, base_rate, default_sede)
                VALUES (%s, %s, %s)
                ON CONFLICT (rut) DO NOTHING;
            """, (name, rate, sede))

        conn.commit()
        print("✅ Migración y configuración de Coaches completada.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error en migración: {e}")

if __name__ == "__main__":
    migration()
