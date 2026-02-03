
import os
import io
import pandas as pd
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuración DB
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "admin")

# Ruta del archivo (hardcoded o búsqueda dinámica)
# Buscaremos el archivo más reciente en downloads/virtualpos
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads", "virtualpos")

def get_latest_csv():
    try:
        files = [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.csv')]
        if not files:
            return None
        return max(files, key=os.path.getctime)
    except Exception as e:
        print(f"Error buscando CSV: {e}")
        return None

def process_vpos_content(content):
    """
    Process raw CSV content from VirtualPOS and insert into DB.
    Returns (inserted_count, skipped_count)
    """
    if not content:
        return 0, 0
        
    print(f"📂 Procesando contenido VirtualPOS ({len(content)} bytes)")

    try:
        # Conectar a DB
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        
        # Intentar leer con detección automática de separador
        # Primero probamos parseo estándar (coma)
        try:
            # Reemplazar posibles BOM o caracteres raros al inicio si existen
            content_clean = content.lstrip('\ufeff')
            df = pd.read_csv(io.StringIO(content_clean), sep=None, engine='python')
        except:
             # Fallback
             df = pd.DataFrame()

        # Si falló o si detectó mal (ej: todo en 1 columna por usar ; en vez de ,)
        # Check común: si hay 1 sola columna y esa columna tiene ';', entonces es ;
        if df.empty or (len(df.columns) == 1 and ';' in str(df.columns[0])):
             try:
                df = pd.read_csv(io.StringIO(content_clean), sep=';', engine='python')
             except Exception as e:
                print(f"Error parseando con ; : {e}")
                return 0, 0

        # Normalizar nombres de columnas
        # Eliminar comillas, espacios, convertir a lowercase
        df.columns = [str(c).lower().strip().replace('"', '').replace("'", "") for c in df.columns]
        
        print(f"   Columnas detectadas: {list(df.columns)}")
        
        # Mapeo de columna ID
        # VirtualPOS export usually has 'id' or 'folio' or 'código'
        # User screenshot shows file name "VirtualPos-transacciones..."
        id_col = next((c for c in df.columns if c in ['id', 'folio', 'codigo', 'n_operacion', 'operacion']), None)
        if not id_col:
            # Fallback a la primera columna si no encontramos nombre conocido
            id_col = df.columns[0]
            print(f"   ⚠ ID no identificado por nombre, usando 1ra columna: {id_col}")

        # Mapeo de Monto
        amount_col = next((c for c in df.columns if c in ['monto', 'valor', 'amount', 'total']), None)
        
        # Mapeo de Fecha
        date_col = next((c for c in df.columns if c in ['fecha', 'date', 'fecha_transaccion', 'fecha creacion']), None)
        
        inserted_count = 0
        skipped_count = 0
        
        for index, row in df.iterrows():
            try:
                vpos_id = str(row.get(id_col, ''))
                # A veces el ID viene como 1234.0 (float), limpiar
                if vpos_id.endswith('.0'): vpos_id = vpos_id[:-2]
                
                if not vpos_id or vpos_id.lower() == 'nan':
                     continue

                # Monto
                if amount_col:
                    monto_raw = row.get(amount_col, 0)
                    # Limpiar formato CLP (puntos de mil, coma decimal, o viceversa)
                    # "10.000" -> 10000. "10.000,00" -> 10000.0. "10,000" -> 10000
                    s_monto = str(monto_raw).replace('$', '').strip()
                    if ',' in s_monto and '.' in s_monto:
                         # Asumimos 10.000,00 -> 10000.00
                         s_monto = s_monto.replace('.', '').replace(',', '.')
                    elif ',' in s_monto:
                         # 10000,00 -> 10000.00? O 10,000 (US)? En Chile es decimal.
                         s_monto = s_monto.replace(',', '.')
                    else:
                         s_monto = s_monto.replace('.', '')
                    
                    try:
                        amount = float(s_monto)
                    except:
                        amount = 0
                else:
                    amount = 0
                
                # Fecha
                transaction_date = None
                if date_col:
                    fecha_str = str(row.get(date_col, '')).strip()
                    # Formatos probables
                    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
                        try:
                            transaction_date = datetime.strptime(fecha_str, fmt)
                            break
                        except:
                            continue
                
                card_type = ""
                # Buscar medio de pago
                mp_col = next((c for c in df.columns if 'medio' in c or 'tarjeta' in c or 'card' in c), None)
                if mp_col:
                    card_type = str(row.get(mp_col, ''))
                
                # Verificar duplicado
                cur.execute("SELECT id FROM raw_virtualpos WHERE vpos_code = %s", (vpos_id,))
                if cur.fetchone():
                    skipped_count += 1
                    continue
                
                row_json = row.to_json()
                
                cur.execute("""
                    INSERT INTO raw_virtualpos 
                    (vpos_code, amount, transaction_date, card_type, raw_data)
                    VALUES (%s, %s, %s, %s, %s)
                """, (vpos_id, amount, transaction_date, card_type, row_json))
                
                inserted_count += 1
                
            except Exception as e_row:
                print(f"   ⚠ Error en fila {index}: {e_row}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return inserted_count, skipped_count
        
    except Exception as e:
        print(f"❌ Error crítico procesando CSV: {e}")
        return 0, 0

def process_csv():
    csv_path = get_latest_csv()
    if not csv_path:
        print("❌ No se encontraron archivos CSV en la carpeta downloads/virtualpos")
        return

    print(f"📂 Procesando archivo: {os.path.basename(csv_path)}")
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
        
    ins, skp = process_vpos_content(content)
    
    print("\n✅ PROCESAMIENTO COMPLETADO")
    print(f"   Insertados: {ins}")
    print(f"   Omitidos (Duplicados): {skp}")

if __name__ == "__main__":
    process_csv()
