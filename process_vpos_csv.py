"""
process_vpos_csv.py
Carga el CSV de VirtualPOS en la tabla raw_virtualpos de PostgreSQL.
Mapeo completo al schema v2 (todos los campos del CSV).
"""
import os
import io
import uuid
import pandas as pd
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "admin")
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads", "virtualpos")


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def get_latest_vpos_csv():
    """Devuelve el CSV de VirtualPOS más reciente en el directorio de descargas."""
    try:
        files = [
            os.path.join(DOWNLOAD_DIR, f)
            for f in os.listdir(DOWNLOAD_DIR)
            if f.lower().startswith("virtualpos-transacciones") and f.endswith(".csv")
        ]
        if not files:
            return None
        return max(files, key=os.path.getctime)
    except Exception as e:
        print(f"Error buscando CSV: {e}")
        return None


def clean_amount(value) -> float:
    """Convierte valores monetarios chilenos a float. Ej: '52.900' → 52900.0"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    s = str(value).replace("$", "").replace(" ", "").strip()
    # Formato CLP: puntos como miles, sin decimales
    if "," in s and "." in s:
        # Ej: 1.000,50 → 1000.50
        s = s.replace(".", "").replace(",", ".")
    elif "." in s and len(s.split(".")[-1]) == 3:
        # Ej: 52.900 → 52900
        s = s.replace(".", "")
    try:
        return float(s)
    except Exception:
        return 0.0


def parse_date(value):
    """Parsea fecha de VirtualPOS (ej: '20/02/2026 15:09') a datetime."""
    if not value or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def parse_date_only(value):
    """Parsea fecha sin hora (ej: '25/02/2026') a date."""
    if not value or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def clean_str(value, maxlen=None):
    """Limpia un valor string. Devuelve None si está vacío o es NaN."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).replace('"', "").replace("\t", "").strip()
    if not s:
        return None
    return s[:maxlen] if maxlen else s


# ──────────────────────────────────────────────
# Core ETL
# ──────────────────────────────────────────────

def process_vpos_csv(csv_path: str) -> tuple[int, int]:
    """
    Lee el CSV de VirtualPOS y lo inserta en raw_virtualpos.
    Devuelve (insertados, omitidos_por_duplicado).
    """
    print(f"\n📂 Archivo: {os.path.basename(csv_path)}")

    # Leer CSV (VirtualPOS usa coma como separador y comillas en los valores)
    with open(csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        raw = f.read()

    df = pd.read_csv(io.StringIO(raw), sep=",", engine="python", dtype=str)

    # Normalizar nombres de columna
    df.columns = [c.lower().strip().replace('"', "").replace(" ", "_") for c in df.columns]
    print(f"   Columnas: {list(df.columns)}")
    print(f"   Filas:    {len(df)}")

    # Conectar a PostgreSQL
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    cur = conn.cursor()

    batch_id = str(uuid.uuid4())
    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        # ── Mapeo completo ──────────────────────────────────────
        transaction_id = clean_str(row.get("id"), 50)
        if not transaction_id:
            continue

        vpos_code    = clean_str(row.get("codigo_de_autorizacion"), 100)
        amount       = clean_amount(row.get("monto"))
        tax          = clean_amount(row.get("impuesto"))
        total        = clean_amount(row.get("total"))
        commission   = clean_amount(row.get("comision"))
        net_amount   = clean_amount(row.get("total_abono"))
        status       = clean_str(row.get("estado"), 30)
        payment_method = clean_str(row.get("medio_de_pago"), 50)
        payment_type = clean_str(row.get("tipo_de_pago"), 10)

        installments_raw = row.get("num_cuotas")
        try:
            installments = int(float(installments_raw)) if installments_raw and str(installments_raw).strip() else 0
        except Exception:
            installments = 0

        client_name  = clean_str(row.get("cliente"), 150)
        client_rut   = clean_str(row.get("rut_cliente"), 20)
        email        = clean_str(row.get("email_cliente"), 150)
        phone        = clean_str(row.get("telefono_cliente"), 30)
        plan_desc    = clean_str(row.get("producto"))

        transaction_date    = parse_date(row.get("fecha"))
        authorization_date  = parse_date(row.get("fecha_autorizacion"))
        deposit_date        = parse_date_only(row.get("fecha_abono"))

        # Serialización segura: NaN → None → JSON válido
        clean_dict = {
            k: (None if (isinstance(v, float) and pd.isna(v)) else v)
            for k, v in row.to_dict().items()
        }
        raw_json = Json(clean_dict)


        # ── Detección de duplicados (ON CONFLICT DO NOTHING) ──
        try:
            cur.execute("""
                INSERT INTO raw_virtualpos (
                    import_batch_id, raw_data,
                    transaction_id, vpos_code,
                    amount, tax, total, commission, net_amount,
                    status, payment_method, payment_type, installments,
                    client_name, client_rut, email, phone,
                    plan_description,
                    transaction_date, authorization_date, deposit_date,
                    source_hint
                ) VALUES (
                    %s, %s,
                    %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s,
                    %s, %s, %s,
                    %s
                )
                ON CONFLICT (transaction_id) DO NOTHING
            """, (
                batch_id, raw_json,
                transaction_id, vpos_code,
                amount, tax, total, commission, net_amount,
                status, payment_method, payment_type, installments,
                client_name, client_rut, email, phone,
                plan_desc,
                transaction_date, authorization_date, deposit_date,
                "virtualpos"
            ))

            if cur.rowcount == 1:
                inserted += 1
            else:
                skipped += 1

        except Exception as e_row:
            print(f"   ⚠ Error fila {transaction_id}: {e_row}")

    conn.commit()
    cur.close()
    conn.close()
    return inserted, skipped


# ──────────────────────────────────────────────
# Wrapper for Streamlit UI (content string → DB)
# ──────────────────────────────────────────────

def process_vpos_content(content: str) -> tuple:
    """
    Procesa el contenido de un CSV de VirtualPOS como string (desde st.file_uploader).
    Guarda a un archivo temporal y llama al ETL principal.
    Retorna (insertados, duplicados).
    """
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv',
                                        encoding='utf-8-sig', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        ins, skp = process_vpos_csv(tmp_path)
        os.remove(tmp_path)
        return ins, skp
    except Exception as e:
        print(f"❌ Error en process_vpos_content: {e}")
        return 0, 0


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def run():
    print("=" * 60)
    print("PROCESS VPOS CSV — ETL VirtualPOS → PostgreSQL")
    print("=" * 60)

    csv_path = get_latest_vpos_csv()
    if not csv_path:
        print(f"\n❌ No se encontró ningún CSV en: {DOWNLOAD_DIR}")
        print("   Ejecutá primero: python virtualpos_downloader_final.py")
        return

    try:
        ins, skp = process_vpos_csv(csv_path)
        print(f"\n✅ ETL completado:")
        print(f"   Insertados : {ins}")
        print(f"   Duplicados : {skp}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run()
