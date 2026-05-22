
import pandas as pd
import re
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de base de datos
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

# Constantes de Precios 2026
NUEVOS_PRECIOS = {1: 7000, 4: 27000, 8: 39900, 10: 42900, 12: 45900, 16: 51900, 20: 55900, 24: 59900}

def extract_classes(plan_name):
    if not plan_name:
        return None
    # Buscar patrones como "16 CLASES", "12 CL", "4 CL", "1 CLASE"
    match = re.search(r'(\d+)\s*(?:CLASES|CLASE|CL)', plan_name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def generate_recovery_list():
    print("🚀 Iniciando Proceso de Generación de Campaña de Recuperación...")
    
    try:
        with engine.connect() as conn:
            # 1. Obtener todos los registros de inactivos
            query_inactive = "SELECT client_name, email, plan_name, last_payment_date, amount FROM raw_boxmagic_users WHERE email IS NOT NULL;"
            df_inactive = pd.read_sql(text(query_inactive), conn)
            
            # 2. Obtener todos los registros de activos (incluso los mal parseados)
            query_active = "SELECT email FROM raw_active_students;"
            df_active = pd.read_sql(text(query_active), conn)
            
        if df_inactive.empty:
            print("ERROR: No hay datos de inactivos para procesar.")
            return

        # 3. De-duplicar Inactivos (obtener el último registro por email)
        df_inactive['last_payment_date'] = pd.to_datetime(df_inactive['last_payment_date'])
        df_inactive = df_inactive.sort_values('last_payment_date', ascending=False)
        df_prospects = df_inactive.drop_duplicates(subset=['email'], keep='first').copy()
        
        print(f"📊 Prospectos únicos en base histórica: {len(df_prospects)}")

        # 4. Matching robusto contra Activos
        # El problema es que en 'raw_active_students', el email puede contener el apellido pegado
        # Estilo: 'Canalesjuan.canales1989@gmail.com' contra 'juan.canales1989@gmail.com'
        active_list_raw = [str(e).lower().strip() for e in df_active['email'].tolist() if e]
        
        def is_recovered(email):
            email_lower = str(email).lower().strip()
            for active_raw in active_list_raw:
                if email_lower in active_raw:
                    return True
            return False
            
        df_prospects['recuperado'] = df_prospects['email'].apply(is_recovered)
        
        # Filtrar solo los NO recuperados
        df_target = df_prospects[~df_prospects['recuperado']].copy()
        
        recovered_count = len(df_prospects) - len(df_target)
        print(f"SUCCESS: Alumnos ya recuperados (omitiendo): {recovered_count}")
        print(f"🎯 Prospectos reales a contactar: {len(df_target)}")

        # 5. Calcular métricas finales y precios
        df_target['dias_inactivo'] = (pd.Timestamp.now().tz_localize(None) - df_target['last_payment_date'].dt.tz_localize(None)).dt.days
        df_target['n_clases'] = df_target['plan_name'].apply(extract_classes)
        df_target['precio_sugerido_2026'] = df_target['n_clases'].map(NUEVOS_PRECIOS)
        
        # Dar formato final
        df_final = df_target[[
            'client_name', 
            'email', 
            'plan_name', 
            'last_payment_date', 
            'dias_inactivo',
            'n_clases',
            'amount', 
            'precio_sugerido_2026'
        ]].copy()
        
        df_final.columns = [
            'Nombre Cliente', 
            'Email', 
            'Último Plan 2025', 
            'Fecha Último Pago', 
            'Días Inactivo',
            'Suscripción (Clases)',
            'Monto Pagado 2025', 
            'Precio Sugerido 2026'
        ]

        # 6. Exportar
        filename = "Campaña_Recuperacion_Alumnos_2026.xlsx"
        filepath = os.path.join(os.getcwd(), filename)
        df_final.to_excel(filepath, index=False)
        
        print(f"SUCCESS: ÉXITO: Campaña generada en {filepath}")
        return filepath

    except Exception as e:
        print(f"ERROR: Error crítico: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    generate_recovery_list()
