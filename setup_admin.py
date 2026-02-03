import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

def setup_admin_features():
    try:
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME
        )
        cur = conn.cursor()
        print("Conectado a la base de datos...")
        
        # 1. Tabla de configuración administrativa
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key VARCHAR(50) PRIMARY KEY,
                value VARCHAR(255),
                label VARCHAR(100),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # 2. Datos base para alertas
        settings = [
            ('cert_digital_vence', '2026-08-15', 'Vencimiento Certificado Digital'),
            ('folios_alerta_min', '100', 'Mínimo Folios (Alerta)'),
            ('folios_actuales', '450', 'Cantidad de Folios Disponibles')
        ]
        
        for key, val, lbl in settings:
            cur.execute("""
                INSERT INTO system_settings (key, value, label) 
                VALUES (%s, %s, %s) 
                ON CONFLICT (key) DO NOTHING
            """, (key, val, lbl))
        
        # 3. Soporte en expense_ledger
        cur.execute("ALTER TABLE expense_ledger ADD COLUMN IF NOT EXISTS is_critical BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE expense_ledger ADD COLUMN IF NOT EXISTS retention_amount NUMERIC(12, 2) DEFAULT 0;")
        cur.execute("ALTER TABLE expense_ledger ADD COLUMN IF NOT EXISTS source_sii_folio INTEGER;")
        
        # 4. Marcar crítios
        keywords = ['Aguas', 'Andinas', 'Enel', 'VTR', 'Movistar', 'Internet', 'Luz', 'Agua']
        for kw in keywords:
            cur.execute("UPDATE expense_ledger SET is_critical = TRUE WHERE description ILIKE %s", (f'%{kw}%',))
            
        conn.commit()
        print("✅ Configuración completada.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    setup_admin_features()
