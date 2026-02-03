
-- =============================================
-- schema.sql (UPDATED v2 - IDEMPOTENT)
-- Database Schema for CrossFit Control System
-- Includes INCOME, EXPENSES and ANALYTICS
-- =============================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- MODULE A: INCOME (Plans, Sales)
-- =============================================

-- [STAGING TABLES for Income]
CREATE TABLE IF NOT EXISTS raw_boxmagic (
    id SERIAL PRIMARY KEY,
    import_batch_id UUID,
    raw_data JSONB,
    bm_user_id VARCHAR(50),
    plan_name VARCHAR(100),
    amount NUMERIC(12, 2),
    payment_status VARCHAR(50),
    source_hint VARCHAR(50), -- Marina, Campanario, etc.
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_virtualpos (
    id SERIAL PRIMARY KEY,
    import_batch_id UUID,
    raw_data JSONB,
    vpos_code VARCHAR(100),
    amount NUMERIC(12, 2),
    transaction_date TIMESTAMP,
    card_type VARCHAR(20),
    source_hint VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_lioren_sales (
    id SERIAL PRIMARY KEY,
    import_batch_id UUID,
    raw_data JSONB,
    folio INTEGER,
    total_amount NUMERIC(12, 2),
    emission_date TIMESTAMP,
    doc_type VARCHAR(20), 
    source_hint VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- MODULE B: EXPENSES (Egresos)
-- =============================================
-- Categories for P&L
CREATE TABLE IF NOT EXISTS expense_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

-- SEED DATA: Categorías (SAFE INSERT)
INSERT INTO expense_categories (name, description) VALUES
('Sueldos Profesores', 'Pago de honorarios y liquidaciones a coaches'),
('Arriendo de Locales', 'Pago mensual de alquiler de sedes'),
('Materiales', 'Equipamiento deportivo y reposición'),
('Insumos de Aseo', 'Artículos de limpieza e higiene'),
('Personal de Aseo', 'Sueldos o pagos externos servicios de aseo'),
('Redes Sociales', 'Pago a Community Manager o Publicidad'),
('Planificaciones', 'Pago a coaches por programación de entrenamientos'),
('Gastos Generales', 'Otros gastos operativos no categorizados')
ON CONFLICT (name) DO NOTHING;

-- Suppliers
CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    rut VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    category_id INTEGER REFERENCES expense_categories(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Raw Invoices Received
CREATE TABLE IF NOT EXISTS raw_lioren_purchases (
    id SERIAL PRIMARY KEY,
    import_batch_id UUID,
    raw_data JSONB,
    rut_issuer VARCHAR(20),
    folio INTEGER,
    total_amount NUMERIC(12, 2),
    emission_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Consolidated Expense Ledger
DO $$ BEGIN
    CREATE TYPE expense_status AS ENUM (
        'PLANNED',
        'PENDING_PAYMENT',
        'PAID_VERIFIED',
        'UNJUSTIFIED_OUTFLOW'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS expense_ledger (
    uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    description VARCHAR(255),
    category_id INTEGER REFERENCES expense_categories(id),
    supplier_id INTEGER REFERENCES suppliers(id),
    
    amount_due NUMERIC(12, 2) DEFAULT 0,
    amount_paid NUMERIC(12, 2) DEFAULT 0,
    
    due_date DATE,
    paid_date DATE,
    
    source_sii_folio INTEGER,
    source_bank_id VARCHAR(100),
    
    status expense_status DEFAULT 'PENDING_PAYMENT',
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- BANKING (The Bridge)
-- =============================================

CREATE TABLE IF NOT EXISTS raw_bank (
    id SERIAL PRIMARY KEY,
    import_batch_id UUID,
    raw_data JSONB,
    bank_date DATE,
    description TEXT,
    amount NUMERIC(12, 2),
    balance NUMERIC(12, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- MODULE C: INCOME CONSOLIDATION
-- =============================================

DO $$ BEGIN
    CREATE TYPE reconciliation_status AS ENUM (
        'MATCH_FULL',
        'MATCH_PARTIAL', 
        'PENDING_DEPOSIT',
        'ERROR_GHOST', 
        'ERROR_TAX',
        'ERROR_LIQUIDITY'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS consolidated_incomes (
    uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_date DATE NOT NULL,
    
    amount_expected NUMERIC(12, 2) DEFAULT 0,
    amount_received NUMERIC(12, 2) DEFAULT 0,
    amount_invoiced NUMERIC(12, 2) DEFAULT 0,
    amount_banked   NUMERIC(12, 2) DEFAULT 0,

    source_bm_id VARCHAR(100),
    source_vpos_id VARCHAR(100),
    source_lioren_folio INTEGER,
    source_bank_id VARCHAR(100),

    status reconciliation_status DEFAULT 'MATCH_PARTIAL',
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- MODULE D: ANALYTICS & STATISTICS (For Dashboard Menu)
-- =============================================

-- 1. Inactive Users Raw Data (From Excel)
CREATE TABLE IF NOT EXISTS raw_boxmagic_users (
    id SERIAL PRIMARY KEY,
    import_batch_id UUID,
    client_name VARCHAR(150),
    email VARCHAR(150),
    last_payment_date DATE,
    plan_name VARCHAR(150),
    amount NUMERIC(12, 2),
    snapshot_date DATE DEFAULT CURRENT_DATE, -- When this file was processed
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. VIEW: Statistics for 'Menú de Estadísticas'
CREATE OR REPLACE VIEW view_inactive_users_stats AS
SELECT 
    TO_CHAR(last_payment_date, 'YYYY-MM') as month_year,
    COUNT(*) as total_leaked_users,
    SUM(amount) as estimated_revenue_loss,
    MODE() WITHIN GROUP (ORDER BY plan_name) as most_common_plan_churned
FROM raw_boxmagic_users
GROUP BY TO_CHAR(last_payment_date, 'YYYY-MM')
ORDER BY month_year DESC;

-- 3. VIEW: Detail for 'Lista de Recuperación'
CREATE OR REPLACE VIEW view_recuperation_list AS
SELECT 
    client_name,
    email,
    plan_name,
    last_payment_date,
    amount,
    CURRENT_DATE - last_payment_date as days_inactive
FROM raw_boxmagic_users
WHERE email IS NOT NULL
ORDER BY last_payment_date DESC;

-- =============================================
-- MODULE E: ACTIVE STUDENTS & RECOVERY
-- =============================================

-- 1. Active Students Raw Data
CREATE TABLE IF NOT EXISTS raw_active_students (
    id SERIAL PRIMARY KEY,
    import_batch_id UUID,
    full_name VARCHAR(200),
    email VARCHAR(150),
    status VARCHAR(50),
    plan_name VARCHAR(200),
    last_payment_date DATE,
    snapshot_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. VIEW: Recovered Users (Intersection)
-- Detects users present in 'raw_boxmagic_users' (Inactive list) who also appear in 'raw_active_students'
CREATE OR REPLACE VIEW view_recovered_users AS
SELECT 
    i.client_name,
    i.email,
    i.last_payment_date as inactive_since,
    a.last_payment_date as reactivation_date,
    a.plan_name as new_plan,
    (a.last_payment_date - i.last_payment_date) as recovery_days_gap
FROM raw_boxmagic_users i
JOIN raw_active_students a ON LOWER(i.email) = LOWER(a.email)
WHERE i.email IS NOT NULL AND a.status = 'activo';

