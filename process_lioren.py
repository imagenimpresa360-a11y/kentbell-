import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "admin")

def process_lioren_sales(file_path):
    """
    Procesa el Excel de Ventas de Lioren de forma robusta.
    Detecta columnas por nombre (folio, fecha, monto).
    """
    try:
        print(f"📦 Procesando Ventas Lioren: {file_path}")
        df = pd.read_excel(file_path)
        
        # Normalizar nombres de columnas para detección flexible
        cols = [str(c).lower().strip() for c in df.columns]
        df.columns = cols
        
        # Mapeo flexible
        folio_col = next((c for c in cols if c in ['folio', 'nro. docto', 'número', 'n°']), None)
        fecha_col = next((c for c in cols if c in ['fecha', 'fecha emisión', 'emisión', 'date']), None)
        monto_col = next((c for c in cols if c in ['monto total', 'total', 'monto', 'valor']), None)
        
        if not all([folio_col, fecha_col, monto_col]):
             raise ValueError(f"No se identificaron las columnas necesarias. Detectadas: {cols}")

        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        
        count = 0
        for _, row in df.iterrows():
            try:
                folio = int(row[folio_col])
                fecha = pd.to_datetime(row[fecha_col]).date()
                total = float(row[monto_col])
                
                # Insertar en tabla raw_lioren_sales
                cur.execute("""
                    INSERT INTO raw_lioren_sales (folio, total_amount, emission_date, doc_type, raw_data)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (folio, total, fecha, 'Boleta Exenta', row.to_json()))
                count += 1
            except:
                continue
            
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ {count} ventas integradas desde Lioren.")
        return True, count
    except Exception as e:
        print(f"❌ Error Lioren: {e}")
        return False, str(e)

def process_lioren_purchases(file_path):
    """
    Procesa el Excel de Compras/Documentos Recibidos de Lioren.
    Carga automáticamente al Libro de Egresos.
    """
    try:
        print(f"🧾 Procesando Compras Lioren (Egresos Automáticos): {file_path}")
        df = pd.read_excel(file_path)
        
        # Normalizar nombres de columnas
        cols = [str(c).lower().strip() for c in df.columns]
        df.columns = cols
        
        # Mapeo flexible
        tipo_col = next((c for c in cols if 'tipo' in c), None)
        folio_col = next((c for c in cols if c in ['folio', 'nro. docto', 'número', 'n°']), None)
        fecha_col = next((c for c in cols if 'fecha' in c or 'emisión' in c), None)
        rut_col = next((c for c in cols if 'rut' in c), None)
        razon_col = next((c for c in cols if 'razón' in c or 'empresa' in c or 'emisor' in c), None)
        total_col = next((c for c in cols if 'monto total' in c or 'total' in c or 'monto' in c), None)
        iva_col = next((c for c in cols if 'iva' in c), None)
        neto_col = next((c for c in cols if 'neto' in c), None)

        if not all([folio_col, fecha_col, rut_col, total_col]):
             raise ValueError(f"Faltan columnas críticas en el archivo de compras. Detectadas: {cols}")

        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        
        # Obtener ID de categoría por defecto
        cur.execute("SELECT id FROM expense_categories WHERE name = 'Administración' LIMIT 1")
        res = cur.fetchone()
        cat_id = res[0] if res else 1
        
        count = 0
        for _, row in df.iterrows():
            try:
                tipo = str(row[tipo_col]) if tipo_col else "Factura Electrónica"
                folio = int(row[folio_col])
                fecha = pd.to_datetime(row[fecha_col]).date()
                rut_emisor = str(row[rut_col])
                razon_social = str(row[razon_col]) if razon_col else "Proveedor Genérico"
                total = float(row[total_col])
                iva = float(row[iva_col]) if iva_col else 0
                neto = float(row[neto_col]) if neto_col else total
                
                # 1. Registrar en raw_lioren_purchases
                cur.execute("""
                    INSERT INTO raw_lioren_purchases (rut_issuer, folio, total_amount, emission_date, raw_data)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (rut_emisor, folio, total, fecha, row.to_json()))
                
                # 2. Registrar automáticamente en expense_ledger si no existe
                cur.execute("SELECT id FROM suppliers WHERE rut = %s", (rut_emisor,))
                supp_res = cur.fetchone()
                if not supp_res:
                    cur.execute("INSERT INTO suppliers (rut, name) VALUES (%s, %s) RETURNING id", (rut_emisor, razon_social))
                    supp_id = cur.fetchone()[0]
                else:
                    supp_id = supp_res[0]

                cur.execute("SELECT uuid FROM expense_ledger WHERE source_sii_folio = %s AND supplier_id = %s", (folio, supp_id))
                
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO expense_ledger (description, category_id, supplier_id, amount_due, net_amount, iva_amount, due_date, source_sii_folio, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING_PAYMENT')
                    """, (f"Lioren {tipo} {folio}: {razon_social}", cat_id, supp_id, total, neto, iva, fecha, folio))
                    count += 1
            except:
                continue
                
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ {count} nuevas facturas de compra cargadas al libro de egresos.")
        return True, count
    except Exception as e:
        print(f"❌ Error Compras: {e}")
        return False, str(e)

if __name__ == "__main__":
    # Rutas por defecto según envío del usuario
    ventas_path = r'C:\Users\DELL\Desktop\Agente kent-bell\downloads\lioren\ventas\77265501-0 - Boletas Exentas.xlsx'
    compras_path = r'C:\Users\DELL\Desktop\Agente kent-bell\downloads\lioren\compras\772655010 - Documentos Recibidos - TS20260126122330.xlsx'
    
    process_lioren_sales(ventas_path)
    process_lioren_purchases(compras_path)
