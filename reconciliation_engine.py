import os
import pandas as pd
import argparse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def get_engine():
    load_dotenv()
    db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    return create_engine(db_url)

def run_reconciliation(target_month=1, target_year=2026):
    print(f"--- Running SAP-Style Reconciliation Engine for {target_month}/{target_year} ---")
    engine = get_engine()
    
    # Define start and end dates
    start_date = f"{target_year}-{target_month:02d}-01"
    end_date = f"{target_year}-{target_month:02d}-31" 
    
    sedes = ["Campanario", "Marina"]
    
    for sede in sedes:
        print(f"\nProcessing Branch: {sede}...")
        with engine.begin() as conn:
            # Create a new reconciliation result tracking record
            res = conn.execute(text("""
                INSERT INTO reconciliation_results (reconciliation_date, sede, status)
                VALUES (:rd, :sede, 'RUNNING')
                ON CONFLICT (reconciliation_date, sede) DO UPDATE SET status = 'RUNNING'
                RETURNING id
            """), {'rd': start_date, 'sede': sede}).fetchone()
            
            recon_id = res[0]
            
            # 1. Summarize BoxMagic (Verdad Comercial)
            bm_sums = conn.execute(text("""
                SELECT 
                    COALESCE(SUM(monto), 0) as total,
                    COALESCE(SUM(CASE WHEN tipo_pago = 'webpay' THEN monto ELSE 0 END), 0) as webpay,
                    COALESCE(SUM(CASE WHEN tipo_pago = 'transferencia' THEN monto ELSE 0 END), 0) as transferencia,
                    COALESCE(SUM(CASE WHEN tipo_pago = 'efectivo' THEN monto ELSE 0 END), 0) as efectivo
                FROM raw_boxmagic_pagos
                WHERE (LOWER(sede) = LOWER(:sede) OR (LOWER(:sede) = 'campanario' AND (sede IS NULL OR sede = 'Current Sede')))
                AND fecha_pago >= :start AND fecha_pago <= :end
            """), {'sede': sede, 'start': start_date, 'end': end_date}).fetchone()
            
            # 2. Summarize VirtualPOS (Verdad Transaccional VPOS)
            # VPOS status can be 'pagado' or 'Aprobada'. In our ETL it came as 'pagado'.
            vpos_sums = conn.execute(text("""
                SELECT COALESCE(SUM(total), 0) as vpos_total
                FROM raw_virtualpos
                WHERE transaction_date >= :start AND transaction_date <= :end 
                AND (status = 'Aprobada' OR status = 'pagado' OR status = 'Aceptado')
            """), {'start': start_date, 'end': end_date}).fetchone()
            
            # Update results
            conn.execute(text("""
                UPDATE reconciliation_results SET 
                    bm_total = :bmt,
                    bm_webpay = :bmw,
                    bm_transferencia = :bmtf,
                    bm_efectivo = :bme,
                    vpos_total = :vpt,
                    discrepancy_webpay = :bmw - :vpt,
                    status = 'COMPLETED'
                WHERE id = :id
            """), {
                'id': recon_id,
                'bmt': bm_sums[0] or 0,
                'bmw': bm_sums[1] or 0,
                'bmtf': bm_sums[2] or 0,
                'bmw': bm_sums[1] or 0, # Double check mapping
                'bme': bm_sums[3] or 0,
                'vpt': (vpos_sums[0] or 0) if sede == "Campanario" else 0, # Asumimos VPOS principal en Campanario si no hay campo sede
            })
            
            print(f"   - BoxMagic Total: ${bm_sums[0]:,.0f}")
            print(f"   - BoxMagic Webpay vs VPOS: ${bm_sums[1]:,.0f} vs ${vpos_sums[0]:,.0f}")
            print(f"   - BoxMagic Transferencias (Alerta Typos): ${bm_sums[2]:,.0f}")
            
            # DETAILED ANOMALY DETECTION
            conn.execute(text("DELETE FROM reconciliation_anomalies WHERE reconciliation_id = :id"), {'id': recon_id})
            
            # Flag transferencias for manual bank check
            transferencias = conn.execute(text("""
                SELECT bm_pago_id, cliente, monto, fecha_pago 
                FROM raw_boxmagic_pagos
                WHERE (LOWER(sede) = LOWER(:sd) OR (LOWER(:sd) = 'campanario' AND (sede IS NULL OR sede = 'Current Sede')))
                AND tipo_pago = 'transferencia' AND fecha_pago >= :start AND fecha_pago <= :end
            """), {'sd': sede, 'start': start_date, 'end': end_date}).fetchall()
            
            for t in transferencias:
                bm_id, cliente, monto, fecha = t
                conn.execute(text("""
                    INSERT INTO reconciliation_anomalies 
                    (reconciliation_id, anomaly_type, bm_pago_id, cliente, monto_esperado, notas)
                    VALUES (:rid, 'TRANSFER_PENDING_BANK', :bmid, :clk, :mo, :not)
                """), {
                    'rid': recon_id, 'bmid': bm_id, 'clk': cliente, 'mo': monto,
                    'not': f"Transferencia de {cliente} por ${monto:,.0f} el {fecha} requiere validación BCI."
                })
            
    print(f"SUCCESS: Cuadratura para {sede} completada. Anomalías registradas.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", type=int)
    parser.add_argument("--year", type=int)
    args = parser.parse_args()
    
    run_reconciliation(target_month=args.month, target_year=args.year)
