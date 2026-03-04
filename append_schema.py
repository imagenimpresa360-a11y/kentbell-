
import sqlite3

def append_to_schema():
    new_tables = """
-- =============================================
-- MODULE F: EXPERT RECONCILIATION ENGINE
-- =============================================

-- 1. Raw BoxMagic Pagos (Extracted from "Reporte de Pagos")
CREATE TABLE IF NOT EXISTS raw_boxmagic_pagos (
    id SERIAL PRIMARY KEY,
    import_batch_id UUID,
    
    bm_pago_id INTEGER UNIQUE NOT NULL, -- "N°" in Boxmagic Report (Prevents duplicates!)
    cliente VARCHAR(150),
    email VARCHAR(150),
    estado VARCHAR(50),
    plan VARCHAR(150),
    fecha_pago DATE,
    fecha_inicio DATE,
    tipo_pago VARCHAR(50), -- webpay, efectivo, transferencia, etc.
    monto NUMERIC(12, 2),
    vendedor VARCHAR(150),
    sede VARCHAR(50),
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Reconciliation Engine Results
CREATE TABLE IF NOT EXISTS reconciliation_results (
    id SERIAL PRIMARY KEY,
    reconciliation_date DATE NOT NULL,
    sede VARCHAR(50) NOT NULL,
    
    -- BoxMagic Totals
    bm_total NUMERIC(12, 2) DEFAULT 0,
    bm_webpay NUMERIC(12, 2) DEFAULT 0,
    bm_transferencia NUMERIC(12, 2) DEFAULT 0,
    bm_efectivo NUMERIC(12, 2) DEFAULT 0,
    
    -- Real World Totals
    vpos_total NUMERIC(12, 2) DEFAULT 0,
    bank_transfer_total NUMERIC(12, 2) DEFAULT 0,
    lioren_total NUMERIC(12, 2) DEFAULT 0,
    
    -- Discrepancies
    discrepancy_webpay NUMERIC(12, 2) DEFAULT 0, -- bm_webpay - vpos_total
    discrepancy_transferencia NUMERIC(12, 2) DEFAULT 0, -- bm_transferencia - bank_transfer_total
    
    status VARCHAR(50) DEFAULT 'PENDING', -- PERFECT_MATCH, DISCREPANCY
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure exactly one reconciliation per date per sede
    CONSTRAINT unique_recon_date_sede UNIQUE (reconciliation_date, sede)
);

-- 3. Detailed Discrepancies (Anomalies)
CREATE TABLE IF NOT EXISTS reconciliation_anomalies (
    id SERIAL PRIMARY KEY,
    reconciliation_id INTEGER REFERENCES reconciliation_results(id),
    
    anomaly_type VARCHAR(50), -- e.g., 'MISSING_IN_BANK', 'AMOUNT_MISMATCH'
    bm_pago_id INTEGER REFERENCES raw_boxmagic_pagos(bm_pago_id),
    cliente VARCHAR(150),
    monto_esperado NUMERIC(12, 2),
    monto_encontrado NUMERIC(12, 2),
    diferencia NUMERIC(12, 2),
    notas TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);
"""
    with open('schema.sql', 'a', encoding='utf-8') as f:
        f.write(new_tables)
        
    print("Schema updated.")

if __name__ == '__main__':
    append_to_schema()
