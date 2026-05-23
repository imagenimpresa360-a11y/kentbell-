import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import uuid
import json
import re

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

def load_coach_data():
    """Lee el archivo markdown de sueldos para aprender los RUTs y nombres de los coaches."""
    coaches = []
    file_path = os.path.join(os.path.dirname(__file__), 'docs', 'remuneraciones', 'sueldos_coaches.md')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '|' in line and 'Nombre Coach' not in line and '---' not in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        name = parts[1]
                        rut = parts[2].replace('.', '') # normalizar rut sin puntos
                        coaches.append({'name': name.lower(), 'rut': rut})
    return coaches

def clean_bci_number(val):
    if pd.isna(val) or str(val).strip().lower() == 'nan': return 0.0
    s = str(val).strip().replace('$', '').replace('.', '').replace(',', '')
    if not s or s == '-': return 0.0
    return float(s)

def process_detailed_statement(file_path):
    print(f"Leyendo archivo detallado: {file_path}")
    try:
        # Forzar lectura de todo como string
        df = pd.read_excel(file_path, dtype=str)
        
        # Mapeo de columnas con manejo de tildes mal formateadas
        cols_lower = {str(c).lower(): c for c in df.columns}
        
        col_fecha = next((cols_lower[c] for c in cols_lower if "fecha de transac" in c or "fecha" in c), None)
        col_glosa = next((cols_lower[c] for c in cols_lower if "glosa" in c or "descrip" in c), None)
        col_ingreso = next((cols_lower[c] for c in cols_lower if "ingreso" in c), None)
        col_egreso = next((cols_lower[c] for c in cols_lower if "egreso" in c), None)
        col_nombre = next((cols_lower[c] for c in cols_lower if "nombre" in c), None)
        col_rut = next((cols_lower[c] for c in cols_lower if "rut" in c), None)
        col_comentario = next((cols_lower[c] for c in cols_lower if "comentario" in c), None)
        col_saldo = next((cols_lower[c] for c in cols_lower if "saldo contable" in c or "saldo" in c), None)

        if not all([col_fecha, col_glosa]):
            raise ValueError("Faltan columnas de Fecha o Glosa.")

        # Obtener categorias para auto-aprendizaje
        conn = psycopg2.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME)
        cur = conn.cursor()
        
        cur.execute("SELECT id, name FROM expense_categories")
        categories = {row[1]: row[0] for row in cur.fetchall()}
        cat_sueldo_coach = categories.get('Sueldo Coach')
        
        coaches = load_coach_data()
        
        import_id = str(uuid.uuid4())
        inserted_count = 0
        categorized_count = 0
        
        print(f"Insertando {len(df)} movimientos crudos en raw_bank y auto-categorizando...")
        for _, row in df.iterrows():
            if pd.isna(row[col_fecha]) or pd.isna(row[col_glosa]):
                continue
                
            row_dict = {k: v for k, v in row.to_dict().items() if not pd.isna(v)}
            
            fecha = str(row[col_fecha]).split()[0]
            glosa = str(row.get(col_glosa, ''))
            nombre = str(row.get(col_nombre, ''))
            rut = str(row.get(col_rut, '')).replace('.', '')
            comentario = str(row.get(col_comentario, ''))
            
            ingreso = clean_bci_number(row.get(col_ingreso))
            egreso = clean_bci_number(row.get(col_egreso))
            saldo = clean_bci_number(row.get(col_saldo))
            
            monto_final = ingreso - egreso
            if monto_final == 0: continue
            
            # Auto-Aprendizaje
            assigned_category = None
            for coach in coaches:
                if (rut and coach['rut'] in rut) or (nombre and coach['name'] in nombre.lower()):
                    assigned_category = cat_sueldo_coach
                    break
            
            # Insert into raw_bank
            cur.execute("""
                INSERT INTO raw_bank (import_batch_id, raw_data, bank_date, description, amount, balance)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                import_id,
                json.dumps(row_dict, default=str),
                fecha,
                f"{glosa} | {nombre}".strip(" |"),
                monto_final,
                saldo
            ))
            raw_bank_id = cur.fetchone()[0]
            inserted_count += 1
            
            # Auto-categorize into expense_ledger if it's an expense and matched
            if monto_final < 0 and assigned_category:
                cur.execute("""
                    INSERT INTO expense_ledger (uuid, description, category_id, amount_due, amount_paid, due_date, paid_date, source_bank_id, status, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    f"Auto-generado: Pago a {nombre}",
                    assigned_category,
                    abs(monto_final),
                    abs(monto_final),
                    fecha,
                    fecha,
                    str(raw_bank_id),
                    'PAID_VERIFIED',
                    f"RUT: {rut} | Comentario: {comentario}"
                ))
                categorized_count += 1

        conn.commit()
        cur.close()
        conn.close()
        return True, f"Procesados {inserted_count} movimientos. Auto-categorizados: {categorized_count}"

    except Exception as e:
        return False, str(e)

if __name__ == '__main__':
    file_path = r'C:\ECOPROYECTOS\THEBOOSBOX\ERP The Boos Box\downloads\bci_dropzone\MOVIMIENTOS DEL MES\5.- movimientos de mayo incompleto con detalle detalle.xlsx'
    ok, msg = process_detailed_statement(file_path)
    print("Resultado:", msg)
