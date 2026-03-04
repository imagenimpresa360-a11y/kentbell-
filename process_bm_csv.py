
import os
import pandas as pd
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuración DB
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "admin")

# Ruta del archivo
DOWNLOAD_OUTPUT_DIR = os.path.join(os.getcwd(), "downloads", "boxmagic")

import json
import csv
from io import StringIO

def parse_bm_csv_content(content):
    """Robustly parse BoxMagic CSV/Excel export using Pandas engine."""
    if not content:
        return pd.DataFrame()
    
    try:
        # Intentar leer con detección automática de separador
        try:
            df = pd.read_csv(StringIO(content), sep=None, engine='python')
        except:
            # Fallback a ; si falla la detección
            df = pd.read_csv(StringIO(content), sep=';', engine='python')
        
        # Normalizar columnas (strip whitespace y borrar :)
        df.columns = [str(c).replace(':', '').strip() for c in df.columns]
        
        # Verificar si cargó todo en una columna (fallo de separador)
        if len(df.columns) == 1 and ';' in df.columns[0]:
             # Si el header tiene ; significa que leyó mal. Reintentar forzando ;
             df = pd.read_csv(StringIO(content), sep=';', engine='python')
             df.columns = [str(c).replace(':', '').strip() for c in df.columns]

        return df

    except Exception as e:
        print(f"Error parseando CSV: {e}")
        return pd.DataFrame()

def process_bm_dataframe(df, sede_hint="General"):
    """
    Ingests a BoxMagic dataframe into the DB with a forced sede hint.
    Returns (inserted_count, error_count)
    """
    if df.empty:
        return 0, 0

    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        
        # Normalize DataFrame columns to lowercase for mapping
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        # Expert check: Is this a summary file?
        required_cols_found = any('cliente' in c or 'alumno' in c for c in df.columns) and \
                              any('monto' in c or 'valor' in c or 'precio' in c for c in df.columns)
        
        if not required_cols_found:
            print(f"      ⏩ Skipping: File doesn't appear to be a transactional report (Cols: {list(df.columns)})")
            return 0, 0
        
        # Map roughly
        col_map = {
            'n°': 'id',
            'no.': 'id',
            'cliente': 'user',
            'alumno': 'user',
            'plan': 'plan',
            'monto': 'amount',
            'valor': 'amount',
            'fecha de pago': 'date',
            'fecha pago': 'date',
            'fecha': 'date', # Only if no other specific date match
            'estado': 'status',
            'estatus': 'status'
        }
        
        # Rename columns that match
        new_cols = {}
        mapped_targets = set()
        
        # Sort keys by length desc to match longest first (specific over generic)
        sorted_keys = sorted(col_map.keys(), key=len, reverse=True)
        
        for c in df.columns:
            for k in sorted_keys:
                if k in c:
                    # Avoid mapping "Fecha de Inicio" if we already have "date" or if we want specific
                    # Hack: if c contains "inicio" or "vencimiento" and k is just "fecha", skip
                    if k == 'fecha' and ('inicio' in c or 'vencimiento' in c or 'fin' in c):
                        continue
                        
                    # Check if target already mapped? No, we might have multiple source cols but we shouldn't map them to same target if it creates duplicates we care about.
                    # Actually, if we map 'fecha de pago' to 'date', we are good.
                    new_cols[c] = col_map[k]
                    break
        
        df.rename(columns=new_cols, inplace=True)
        
        # Remove duplicate columns if any (keep first)
        df = df.loc[:, ~df.columns.duplicated()]
        
        inserted = 0
        errors = 0
        
        inserted = 0
        errors = 0
        
        # 1. Fetch Closed Periods to Cache
        cur.execute("SELECT period_key FROM accounting_periods WHERE status = 'CLOSED'")
        closed_periods = {row[0] for row in cur.fetchall()} # Set of 'YYYY-MM'
        
        for idx, row in df.iterrows():
            try:
                bm_id = str(row.get('id', ''))
                
                # Robust amount cleaning for CLP ($15.000 or 15.000,00)
                monto_str = str(row.get('amount', '0')).replace('$', '').strip()
                if ',' in monto_str and '.' in monto_str:
                    # Case 15.000,00 -> remove dot, replace comma with dot
                    monto_str = monto_str.replace('.', '').replace(',', '.')
                elif ',' in monto_str:
                    # Case 15000,00 or 1.500 (if comma is thousand?) 
                    # Usually in CL comma is decimal.
                    monto_str = monto_str.replace(',', '.')
                else:
                    # Case 15.000 -> remove dot
                    monto_str = monto_str.replace('.', '')
                
                amount = float(monto_str) if monto_str else 0
                
                date_str = str(row.get('date', '')).strip()
                created_at = None
                # Expert: Extra formats for better coverage
                for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
                    try:
                        created_at = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                if not created_at or created_at.year < 2000:
                    print(f"      WARN: Fecha no reconocida: {date_str}")
                    # If date invalid, we can't check period, so we might insert or fail.
                    # Default to fail? Or let DB handle it. Database 'created_at' is timestamp.
                else:
                    # CHECK PERIOD LOCK
                    period_key = created_at.strftime("%Y-%m")
                    if period_key in closed_periods:
                        raise ValueError(f"⛔ PERIODO CERRADO: No se pueden cargar datos para {period_key}. Desbloquea el periodo primero.")
                
                plan = row.get('plan', '')
                raw_status = str(row.get('status', '')).lower().strip()
                
                # Normalize status for reconciliation
                # If status is empty but we have a valid amount and date, treat as active?
                # User says "upload sales report", usually implies completed sales.
                # BoxMagic 'Estado' can be 'Pagado', 'Pendiente', etc.
                if not raw_status or any(x in raw_status for x in ['pag', 'exit', 'aprob', 'confirm', 'ok', 'act']):
                    status = 'activo'
                else:
                    status = raw_status # 'pendiente', 'fallido', etc.
                user = row.get('user', '')
                
                row_data = row.to_dict()
                # Sanitize for JSON (fill NaNs)
                for k, v in row_data.items():
                    if pd.isna(v):
                        row_data[k] = ""
                row_data['source_hint'] = sede_hint

                # Identificador único para evitar duplicados si se sube el mismo archivo varias veces
                # Usamos una combinación de user, plan, monto y fecha como "huella" en raw_data si no hay ID único real estable
                
                cur.execute("""
                    INSERT INTO raw_boxmagic 
                    (bm_user_id, plan_name, amount, payment_status, created_at, raw_data, source_hint)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (f"{user} [{bm_id}]", plan, amount, status, created_at, json.dumps(row_data), sede_hint))
                
                inserted += 1
                
            except Exception as e_row:
                print(f"      Error fila {idx}: {e_row}")
                conn.rollback() # Reset transaction state to allow continuing
                errors += 1
        
        conn.commit()
        cur.close()
        conn.close()
        return inserted, errors

    except Exception as e:
        print(f"ERROR: DB BoxMagic: {e}")
        return 0, 0

def process_boxmagic():
    # Buscar todos los CSVs en la carpeta (Lógica original)
    files = [f for f in os.listdir(DOWNLOAD_OUTPUT_DIR) if f.endswith('.csv')]
    if not files:
        print(f"ERROR: No se encontraron CSVs en {DOWNLOAD_OUTPUT_DIR}")
        return

    print(f"FILE: Archivos encontrados: {files}")

    # Limpiar tabla UNA SOLA VEZ antes de cargar todo (Solo en modo automàtico)
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        print("   WARNING: Truncando tabla raw_boxmagic para carga limpia...")
        cur.execute("TRUNCATE raw_boxmagic RESTART IDENTITY")
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error truncando: {e}")

    total_inserted = 0
    for filename in files:
        csv_path = os.path.join(DOWNLOAD_OUTPUT_DIR, filename)
        print(f"\n   >>> Procesando: {filename}")
        
        content = ""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f: content = f.read()
        except:
            with open(csv_path, 'r', encoding='latin-1') as f: content = f.read()
        
        df = parse_bm_csv_content(content)
        
        fname_lower = filename.lower()
        sede_hint = "Marina" if "marina" in fname_lower else ("Campanario" if "campanario" in fname_lower else "General")
        
        ins, err = process_bm_dataframe(df, sede_hint)
        total_inserted += ins
        print(f"      OK: Insertados: {ins} | Errores: {err}")

    print(f"\nSUCCESS: TOTAL IMPORTADO: {total_inserted} registros de {len(files)} archivos.")


if __name__ == "__main__":
    process_boxmagic()



if __name__ == "__main__":
    process_boxmagic()
