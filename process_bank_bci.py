import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import uuid
import json

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

def process_bci_statement(file_path):
    """
    Procesa la cartola BCI buscando dinámicamente el encabezado y normalizando columnas.
    """
    try:
        print(f"Leyendo archivo: {file_path}")
        # Intentamos leer las primeras filas para encontrar el encabezado (BCI puede tenerlo hasta la fila 22)
        df_raw = pd.read_excel(file_path, header=None, nrows=45)
        
        # Buscar la fila que tiene "Fecha" y "Descripción" (o "Glosa")
        header_row_idx = None
        for idx, row in df_raw.iterrows():
            row_str = [str(val).lower() if pd.notna(val) else "" for val in row]
            if any("fecha" in s for s in row_str) and (any("descrip" in s for s in row_str) or any("glosa" in s for s in row_str)):
                header_row_idx = idx
                break
        
        if header_row_idx is None:
            raise ValueError("No se encontro la fila de encabezados (Fecha, Descripcion, Glosa, etc.) en las primeras 45 filas.")
            
        # Re-leer con el header correcto y forzando dtype=str para no perder ceros
        df = pd.read_excel(file_path, header=header_row_idx, dtype=str)
        
        # Normalizar columnas
        df.columns = [str(c).strip() for c in df.columns]
        
        # Mapeo de columnas flexible (insensible a mayusculas, minusculas y acentos)
        columns_lower = {str(c).lower(): c for c in df.columns}
        
        col_fecha = next((columns_lower[c] for c in columns_lower if "fecha" in c), None)
        col_desc = next((columns_lower[c] for c in columns_lower if "descrip" in c or "glosa" in c), None)
        col_cargo = next((columns_lower[c] for c in columns_lower if "cargo" in c or "egreso" in c), None)
        col_abono = next((columns_lower[c] for c in columns_lower if "abono" in c or "ingreso" in c), None)
        col_saldo = next((columns_lower[c] for c in columns_lower if "saldo" in c), None) # Opcional
        
        if not all([col_fecha, col_desc]):
            print(f"Columnas detectadas: {df.columns.tolist()}")
            raise ValueError("Faltan columnas esenciales: Fecha o Descripcion/Glosa.")

        # Limpieza
        df = df.dropna(subset=[col_fecha, col_desc], how='all')
        
        # Limpiar Fechas (BCI usa espacio no rompible \xa0)
        df[col_fecha] = df[col_fecha].astype(str).str.replace('\xa0', '').str.strip()
        df['bank_date'] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['bank_date'])

        # Calcular Monto Neto
        df['final_amount'] = 0.0
        
        # Helper para limpiar montos BCI (eliminar $, puntos, comas)
        # Recibe strings exactos (e.g. "343.000", "165", "19.457")
        def clean_bci_number(val):
            if pd.isna(val) or str(val).strip().lower() == 'nan': return 0.0
            s = str(val).strip().replace('$', '').replace('.', '').replace(',', '')
            if not s or s == '-': return 0.0
            return float(s)

        if col_cargo:
            vals_cargo = df[col_cargo].apply(clean_bci_number).fillna(0).abs()
            df['final_amount'] -= vals_cargo
            
        if col_abono:
             vals_abono = df[col_abono].apply(clean_bci_number).fillna(0).abs()
             df['final_amount'] += vals_abono
             
        # Si no hay cargo/abono separados, buscar columna 'Monto'
        if not col_cargo and not col_abono:
            col_monto = next((c for c in df.columns if "Monto" in c), None)
            if col_monto:
                 df['final_amount'] = df[col_monto].apply(clean_bci_number).fillna(0)
            else:
                raise ValueError("No se encontraron columnas de montos (Cargo/Abono o Monto).")

        # Database Connection
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME
        )
        cur = conn.cursor()
        
        import_id = str(uuid.uuid4())
        data_to_insert = []
        
        for _, row in df.iterrows():
            # Convert row to dict
            row_dict = row.to_dict()
            
            # Limpiar NaN/NaT para JSON (Postgres no acepta NaN en JSON válido estándar)
            for k, v in row_dict.items():
                if pd.isna(v):
                    row_dict[k] = None
            
            # Convert timestamp to string for JSON
            if 'bank_date' in row_dict and row_dict['bank_date']:
                row_dict['bank_date'] = str(row_dict['bank_date'])
                
            saldo_val = 0
            if col_saldo:
                try:
                    val_clean = str(row[col_saldo]).replace('$','').replace(',','')
                    saldo_val = float(val_clean)
                except: 
                    saldo_val = 0

            data_to_insert.append((
                import_id,
                json.dumps(row_dict, default=str),
                row['bank_date'].date(),
                row[col_desc],
                row['final_amount'],
                saldo_val
            ))

        print(f"Insertando {len(data_to_insert)} movimientos en raw_bank...")
        query = """
            INSERT INTO raw_bank (import_batch_id, raw_data, bank_date, description, amount, balance)
            VALUES %s
        """
        execute_values(cur, query, data_to_insert)
        
        conn.commit()
        cur.close()
        conn.close()
        return True, f"{len(data_to_insert)} movimientos procesados."

    except Exception as e:
        err_msg = f"Error procesando cartola BCI: {str(e)}"
        print(err_msg)
        return False, err_msg
