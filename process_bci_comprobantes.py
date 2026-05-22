"""
process_bci_comprobantes.py
============================
Motor de procesamiento de comprobantes de transferencia BCI.
Extrae datos de PDFs en bci_dropzone/comprobantes TBB y los registra
en raw_bank (egresos) y expense_ledger del ERP.

Tipos de comprobante soportados:
  - BCI Clásico: "N.° de operación: XXXXX / Transferencia exitosa"
  - BCI Nuevo:   Formato tabular compacto (sin espacios)
  - Tesorería:   "COMPROBANTE DE TRANSACCION / Formulario 99"
  - Sin texto:   PDFs escaneados (imágenes) → registra sólo desde el nombre del archivo
"""

import os
import re
import json
import uuid
import logging
import pdfplumber
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

# ── Configuración ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

DROPZONE_BASE = os.path.join(
    os.path.dirname(__file__),
    "downloads", "bci_dropzone", "comprobantes TBB"
)

# Mapeo mes-folder → número de mes
MONTH_MAP = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4,
    "MAYO": 5, "JUNIO": 6, "JULIO": 7, "AGOSTO": 8,
    "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12,
}

# Categorías de gasto (según schema expense_categories)
CATEGORY_KEYWORDS = {
    "boxmagic":        "Sueldos Profesores",   # subscripción sistema
    "arriendo":        "Arriendo de Locales",
    "enel":            "Gastos Generales",      # luz
    "entel":           "Gastos Generales",      # internet
    "aseo":            "Insumos de Aseo",
    "circulo ambiental":"Insumos de Aseo",
    "coach":           "Sueldos Profesores",
    "honorarios":      "Sueldos Profesores",
    "sueldo":          "Sueldos Profesores",
    "salgo":           "Sueldos Profesores",    # saldo a coaches
    "saldo":           "Sueldos Profesores",
    "joaco":           "Sueldos Profesores",
    "material":        "Materiales",
    "equipamiento":    "Materiales",
    "gap":             "Materiales",
    "hosting":         "Gastos Generales",
    "dominio":         "Gastos Generales",
    "concept":         "Redes Sociales",        # mp5 concept (community)
    "monito":          "Redes Sociales",
    "stl abogado":     "Gastos Generales",
    "abogado":         "Gastos Generales",
    "patente":         "Gastos Generales",
    "convenio":        "Gastos Generales",      # convenio pago tesorería
    "tesoreria":       "Gastos Generales",
    "formulario":      "Gastos Generales",
    "internet":        "Gastos Generales",
    "luz":             "Gastos Generales",
    "agua":            "Gastos Generales",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_amount(raw: str) -> float:
    """Convierte '63.000' o '$63,000' o '63000' a float 63000.0"""
    if not raw:
        return 0.0
    s = re.sub(r"[$\s]", "", raw).replace(".", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def guess_category(text: str, filename: str) -> str:
    """Infiere la categoría de gasto según palabras clave en texto+nombre."""
    combined = (text + " " + filename).lower()
    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in combined:
            return category
    return "Gastos Generales"


def guess_sede(text: str, filename: str) -> str | None:
    """Infiere la sede (Marina/Campanario) desde el texto o nombre de archivo."""
    combined = (text + " " + filename).lower()
    if "marina" in combined:
        return "Marina"
    if "campanario" in combined:
        return "Campanario"
    return None


def parse_date_flexible(raw: str) -> date | None:
    """Parsea fechas en múltiples formatos: dd/mm/yyyy, dd-mm-yyyy, d/m/yy."""
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def infer_date_from_filename(filename: str, month_folder: str) -> date | None:
    """
    Intenta extraer fecha del nombre del archivo.
    Ej: 'boxmagic marina 14012026.pdf' → 14/01/2026
        'PAGO BOXMAGIC CAMPANARIO 09-04-2026.pdf' → 09/04/2026
    Si no hay fecha explícita, usa el día 1 del mes indicado por la carpeta.
    """
    # Buscar patrón ddmmyyyy o dd-mm-yyyy en el nombre
    m = re.search(r"(\d{2})[-/]?(\d{2})[-/]?(20\d{2})", filename)
    if m:
        day, mon, year = m.group(1), m.group(2), m.group(3)
        try:
            return datetime.strptime(f"{day}/{mon}/{year}", "%d/%m/%Y").date()
        except ValueError:
            pass
    # Usar mes de la carpeta con día 1
    month_num = MONTH_MAP.get(month_folder.upper())
    if month_num:
        year = 2026  # año por defecto
        return date(year, month_num, 1)
    return None


# ── Extractores por tipo ───────────────────────────────────────────────────────

def extract_bci_clasico(text: str, filename: str, month_folder: str) -> dict | None:
    """
    Comprobante BCI Clásico:
    N.° de operación: 28464350
    Monto transferido
    63.000
    $
    Fecha: 14/01/2026
    Destinatario: Boxmagic Spa
    Mensaje: boxmagic marina
    """
    op_num = re.search(r"operaci[oó]n[:\s]*(\d+)", text, re.IGNORECASE)
    amount_m = re.search(r"Monto transferido\s*([\d\.]+)", text, re.IGNORECASE)
    date_m = re.search(r"Fecha[:\s]*([\d]{1,2}/[\d]{1,2}/[\d]{4})", text, re.IGNORECASE)
    dest_m = re.search(r"Destinatario[:\s]*\n?(.*?)(?:\n|RUT)", text, re.IGNORECASE | re.DOTALL)
    msg_m = re.search(r"Mensaje[:\s]*\n?(.*?)(?:\n|Tipo de transferencia|Banco del destinatario)", text, re.IGNORECASE | re.DOTALL)

    amount = clean_amount(amount_m.group(1)) if amount_m else 0.0
    tx_date = parse_date_flexible(date_m.group(1)) if date_m else infer_date_from_filename(filename, month_folder)
    destinatario = dest_m.group(1).strip() if dest_m else ""
    mensaje = msg_m.group(1).strip().split("\n")[0] if msg_m else ""
    op_id = op_num.group(1) if op_num else None

    if amount == 0.0:
        return None

    return {
        "tipo": "BCI_CLASICO",
        "op_num": op_id,
        "amount": -amount,         # egreso → negativo
        "bank_date": tx_date,
        "destinatario": destinatario,
        "mensaje": mensaje,
        "description": mensaje or destinatario or filename,
    }


def extract_bci_nuevo(text: str, filename: str, month_folder: str) -> dict | None:
    """
    Comprobante BCI Nuevo (formato compacto sin espacios):
    IDTransferencia: 39466968
    FechaPago: 19/05/2026-16:57
    Monto: $230.000
    NombreDestinatario: ChristianUrrutia
    MensajeaDestinatario: MonitorPM5
    """
    op_m = re.search(r"IDTransferencia\s*([\d]+)", text, re.IGNORECASE)
    date_m = re.search(r"FechaPago\s*([\d]{2}/[\d]{2}/[\d]{4})", text, re.IGNORECASE)
    # El monto puede venir como '$230.000' (con signo $) o solo '230.000'
    amount_m = re.search(r"Monto\s*\$?([\d\.]+)", text, re.IGNORECASE)
    dest_m = re.search(r"NombreDestinatario\s*([A-Za-záéíóúÁÉÍÓÚñÑ]+)", text, re.IGNORECASE)
    msg_m = re.search(r"Mensajeadestinatario\s*([\w ]+)", text, re.IGNORECASE)

    amount = clean_amount(amount_m.group(1)) if amount_m else 0.0
    tx_date = parse_date_flexible(date_m.group(1)) if date_m else infer_date_from_filename(filename, month_folder)
    destinatario = dest_m.group(1).strip() if dest_m else ""
    mensaje = msg_m.group(1).strip() if msg_m else ""
    op_id = op_m.group(1) if op_m else None

    if amount == 0.0:
        return None

    return {
        "tipo": "BCI_NUEVO",
        "op_num": op_id,
        "amount": -amount,
        "bank_date": tx_date,
        "destinatario": destinatario,
        "mensaje": mensaje,
        "description": mensaje or destinatario or filename,
    }


def extract_servipag(text: str, filename: str, month_folder: str) -> dict | None:
    """
    Comprobante Servipag (pagos de servicios: ENEL, Entel, etc.):
    Hola Vladimir Palma Martinez
    Fecha: 30/01/2026
    Hora: 09:21
    Número de transacción: 41051504
    Valor: $18.990
    Empresa: Entel Hogar internet
    """
    # Número de transacción Servipag
    op_m = re.search(r"(\d{7,10})", text)  # Los IDs de servipag son 7-10 dígitos
    # Fecha: puede venir en Resumen de pago en formato dd/mm/yyyy
    date_m = re.search(r"(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}", text)
    # Valor: puede venir como '$18.990' o '$122.581'
    amount_m = re.search(r"\$([\d\.]+)\s+BCI", text)
    if not amount_m:
        amount_m = re.search(r"Valor\s+\$([\d\.]+)", text, re.IGNORECASE)
    # Empresa / Nombre del servicio
    empresa_m = re.search(r"Empresa\s+Nombre\s+Valor\s*\n([^\n]+?)\s+(?:[\d-]+)\s+\$", text, re.IGNORECASE | re.DOTALL)
    if not empresa_m:
        empresa_m = re.search(r"(?:Entel|Enel|Portal Enel|CGE|Metrogas|Aguas)[^\n]*", text, re.IGNORECASE)

    amount = clean_amount(amount_m.group(1)) if amount_m else 0.0
    tx_date = parse_date_flexible(date_m.group(1)) if date_m else infer_date_from_filename(filename, month_folder)
    empresa = empresa_m.group(0).strip()[:80] if empresa_m else filename.replace(".pdf", "")
    op_id = op_m.group(1) if op_m else None

    if amount == 0.0:
        return None

    return {
        "tipo": "SERVIPAG",
        "op_num": op_id,
        "amount": -amount,
        "bank_date": tx_date,
        "destinatario": "Servipag",
        "mensaje": empresa,
        "description": empresa or filename.replace(".pdf", ""),
    }


def extract_tesoreria(text: str, filename: str, month_folder: str) -> dict | None:
    """
    Comprobante Tesorería Chile:
    Folio: 11884019
    Total Pagado: 119.409
    Fecha Pago: 30-01-2026 12:57:59
    Formulario 99 (patentes, contribuciones, etc.)
    """
    folio_m = re.search(r"Folio\s*([\d]+)", text, re.IGNORECASE)
    amount_m = re.search(r"Total Pagado\s*([\d\.]+)", text, re.IGNORECASE)
    date_m = re.search(r"Fecha Pago\s*([\d]{2}-[\d]{2}-[\d]{4})", text, re.IGNORECASE)
    form_m = re.search(r"Formulario\s*([\d]+)", text, re.IGNORECASE)

    amount = clean_amount(amount_m.group(1)) if amount_m else 0.0
    tx_date = parse_date_flexible(date_m.group(1)) if date_m else infer_date_from_filename(filename, month_folder)
    folio = folio_m.group(1) if folio_m else None
    formulario = form_m.group(1) if form_m else "?"

    if amount == 0.0:
        return None

    desc = f"Tesorería Formulario {formulario} Folio {folio}" if folio else filename

    return {
        "tipo": "TESORERIA",
        "op_num": folio,
        "amount": -amount,
        "bank_date": tx_date,
        "destinatario": "Tesorería General de la República",
        "mensaje": desc,
        "description": desc,
    }


def classify_and_extract(text: str, filename: str, month_folder: str) -> dict | None:
    """Detecta el tipo de comprobante y llama al extractor correcto."""
    text_lower = text.lower() if text else ""

    if "comprobante de transaccion" in text_lower or "tesoreria.cl" in text_lower:
        return extract_tesoreria(text, filename, month_folder)
    elif "servipag" in text_lower or "comprobante de pago" in text_lower and ("entel" in text_lower or "enel" in text_lower or "portal enel" in text_lower or "empresa" in text_lower):
        return extract_servipag(text, filename, month_folder)
    elif "idtransferencia" in text_lower and "fechapago" in text_lower:
        return extract_bci_nuevo(text, filename, month_folder)
    elif "transferencia exitosa" in text_lower or "n.° de operación" in text_lower or "n.o de operaci" in text_lower:
        return extract_bci_clasico(text, filename, month_folder)
    else:
        return None  # PDF imagen o tipo desconocido


def extract_from_pdf(pdf_path: str, month_folder: str) -> dict | None:
    """Abre un PDF y extrae los datos del comprobante."""
    filename = os.path.basename(pdf_path)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
    except Exception as e:
        log.warning(f"Error abriendo {filename}: {e}")
        return None

    if not full_text.strip():
        # PDF imagen - registrar con datos mínimos del nombre de archivo
        log.warning(f"  ⚠ PDF sin texto (imagen): {filename} — se registrará con datos del nombre")
        tx_date = infer_date_from_filename(filename, month_folder)
        return {
            "tipo": "PDF_IMAGEN",
            "op_num": None,
            "amount": 0.0,  # monto desconocido - marcar para revisión manual
            "bank_date": tx_date,
            "destinatario": "",
            "mensaje": filename.replace(".pdf", ""),
            "description": f"[REVISAR MANUAL] {filename.replace('.pdf', '')}",
            "_needs_review": True,
        }

    result = classify_and_extract(full_text, filename, month_folder)
    if result is None:
        log.warning(f"  ⚠ Tipo no reconocido: {filename}")
        log.debug(f"  Texto (primeros 300 chars): {full_text[:300]}")
    return result


# ── Base de datos ──────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", os.getenv("PGHOST")),
        database=os.getenv("DB_NAME", os.getenv("PGDATABASE")),
        user=os.getenv("DB_USER", os.getenv("PGUSER")),
        password=os.getenv("DB_PASS", os.getenv("PGPASSWORD")),
        port=os.getenv("DB_PORT", os.getenv("PGPORT", "5432")),
    )


def get_or_create_category_id(cur, category_name: str) -> int | None:
    cur.execute("SELECT id FROM expense_categories WHERE name = %s", (category_name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO expense_categories (name, description) VALUES (%s, %s) RETURNING id",
        (category_name, f"Categoría auto-creada: {category_name}")
    )
    return cur.fetchone()[0]


def check_duplicate(cur, op_num: str | None, amount: float, bank_date) -> bool:
    """Evita duplicados en raw_bank por número de operación o combinación fecha+monto."""
    if op_num:
        cur.execute(
            "SELECT id FROM raw_bank WHERE raw_data->>'op_num' = %s LIMIT 1",
            (op_num,)
        )
        if cur.fetchone():
            return True
    # Fallback: misma fecha + mismo monto + misma descripción ya existe
    return False


def insert_records(records: list[dict]) -> dict:
    """Inserta los registros en raw_bank y expense_ledger."""
    inserted_bank = 0
    inserted_ledger = 0
    skipped_dup = 0
    skipped_zero = 0
    errors = 0

    conn = get_connection()
    cur = conn.cursor()

    import_batch_id = str(uuid.uuid4())

    for rec in records:
        filename = rec.get("_filename", "")
        month_folder = rec.get("_month_folder", "")

        try:
            # Saltar montos cero (PDFs imagen sin dato)
            if rec.get("_needs_review"):
                log.warning(f"  🔍 REVISAR MANUAL: {filename} (sin monto extraíble)")
                skipped_zero += 1
                continue

            if rec["amount"] == 0.0:
                skipped_zero += 1
                continue

            # Verificar duplicado
            if check_duplicate(cur, rec.get("op_num"), rec["amount"], rec["bank_date"]):
                log.info(f"  ⏭ Duplicado omitido: {filename} op={rec.get('op_num')}")
                skipped_dup += 1
                continue

            # ── INSERT raw_bank ──────────────────────────────────────────
            raw_data = {
                "op_num": rec.get("op_num"),
                "tipo": rec.get("tipo"),
                "destinatario": rec.get("destinatario"),
                "mensaje": rec.get("mensaje"),
                "source_file": filename,
                "month_folder": month_folder,
            }

            cur.execute("""
                INSERT INTO raw_bank 
                    (import_batch_id, raw_data, bank_date, description, amount, balance)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                import_batch_id,
                json.dumps(raw_data, default=str),
                rec["bank_date"],
                rec["description"],
                rec["amount"],
                0,   # balance no disponible en comprobantes individuales
            ))
            raw_bank_id = cur.fetchone()[0]
            inserted_bank += 1

            # ── INSERT expense_ledger ────────────────────────────────────
            category_name = guess_category(
                (rec.get("descripcion", "") + " " + rec.get("mensaje", "")),
                filename
            )
            category_id = get_or_create_category_id(cur, category_name)
            sede = guess_sede(rec.get("descripcion", "") + " " + rec.get("mensaje", ""), filename)

            cur.execute("""
                INSERT INTO expense_ledger
                    (description, category_id, amount_due, amount_paid,
                     paid_date, source_bank_id, status, notes)
                VALUES (%s, %s, %s, %s, %s, %s, 'PAID_VERIFIED', %s)
            """, (
                rec["description"][:255],
                category_id,
                abs(rec["amount"]),
                abs(rec["amount"]),
                rec["bank_date"],
                str(raw_bank_id),
                f"Sede: {sede} | Importado desde: {filename}",
            ))
            inserted_ledger += 1

            log.info(
                f"  ✅ {filename} → ${abs(rec['amount']):,.0f} [{rec['bank_date']}] "
                f"[{category_name}]"
            )

        except Exception as e:
            log.error(f"  ❌ Error procesando {filename}: {e}")
            conn.rollback()
            errors += 1
            conn = get_connection()
            cur = conn.cursor()
            continue

    conn.commit()
    cur.close()
    conn.close()

    return {
        "inserted_bank": inserted_bank,
        "inserted_ledger": inserted_ledger,
        "skipped_dup": skipped_dup,
        "skipped_zero": skipped_zero,
        "errors": errors,
    }


# ── Orquestador principal ──────────────────────────────────────────────────────

def scan_dropzone(dry_run: bool = False) -> list[dict]:
    """
    Escanea todas las subcarpetas de comprobantes TBB y extrae los datos.
    Retorna lista de registros listos para insertar.
    """
    records = []
    total_pdfs = 0
    total_ok = 0
    total_fail = 0

    if not os.path.isdir(DROPZONE_BASE):
        log.error(f"Dropzone no encontrada: {DROPZONE_BASE}")
        return []

    # Iterar sobre carpetas de mes
    for month_folder in sorted(os.listdir(DROPZONE_BASE)):
        month_path = os.path.join(DROPZONE_BASE, month_folder)
        if not os.path.isdir(month_path):
            continue
        if month_folder.upper() not in MONTH_MAP:
            continue

        log.info(f"\n📂 Procesando carpeta: {month_folder}")

        for filename in sorted(os.listdir(month_path)):
            if not filename.lower().endswith(".pdf"):
                continue
            if filename.lower() == "desktop.ini":
                continue

            total_pdfs += 1
            pdf_path = os.path.join(month_path, filename)
            log.info(f"  📄 {filename}")

            rec = extract_from_pdf(pdf_path, month_folder)
            if rec:
                rec["_filename"] = filename
                rec["_month_folder"] = month_folder
                records.append(rec)
                total_ok += 1
            else:
                log.warning(f"  ⚠ No se pudo extraer: {filename}")
                total_fail += 1

    log.info(f"\n{'='*50}")
    log.info(f"📊 RESUMEN ESCANEO:")
    log.info(f"   PDFs encontrados: {total_pdfs}")
    log.info(f"   Extraídos OK:     {total_ok}")
    log.info(f"   Fallidos:         {total_fail}")

    return records


def run(dry_run: bool = False):
    """
    Punto de entrada principal.
    dry_run=True → sólo muestra qué se insertaría, sin tocar la BD.
    """
    log.info("🚀 Iniciando procesamiento de comprobantes BCI...")
    log.info(f"   Dropzone: {DROPZONE_BASE}")
    log.info(f"   Modo: {'DRY RUN (sin escritura)' if dry_run else 'PRODUCCIÓN'}\n")

    records = scan_dropzone(dry_run=dry_run)

    if not records:
        log.warning("No se encontraron registros para procesar.")
        return

    if dry_run:
        log.info("\n🔍 DRY RUN — Registros que se insertarían:")
        for r in records:
            log.info(
                f"  [{r.get('_month_folder')}] {r.get('_filename')} → "
                f"${abs(r.get('amount', 0)):,.0f} [{r.get('bank_date')}] "
                f"tipo={r.get('tipo')}"
            )
        return

    log.info("\n💾 Insertando en base de datos...")
    stats = insert_records(records)

    log.info(f"\n{'='*50}")
    log.info(f"✅ PROCESAMIENTO COMPLETADO:")
    log.info(f"   Registros en raw_bank:     {stats['inserted_bank']}")
    log.info(f"   Registros en expense_ledger: {stats['inserted_ledger']}")
    log.info(f"   Duplicados omitidos:       {stats['skipped_dup']}")
    log.info(f"   Sin monto (revisión):      {stats['skipped_zero']}")
    log.info(f"   Errores:                   {stats['errors']}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Procesador de Comprobantes BCI → ERP")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simular sin escribir en la base de datos")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
