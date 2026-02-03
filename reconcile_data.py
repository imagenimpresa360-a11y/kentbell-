import psycopg2
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "admin")

def reconcile():
    print("="*60)
    print("CONCILIACIÓN DE INGRESOS (TAX & COMMISSIONS MODE)")
    print("="*60)
    
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    cur = conn.cursor()
    
    try:
        # 1. Limpiar tabla consolidada
        cur.execute("TRUNCATE consolidated_incomes CASCADE")
        
        # 2. Cargar datos
        print("📥 Cargando datos...")
        
        # BoxMagic: Incluimos 'activo' y 'congelado' ya que ambos representan ingresos monetarios reales
        cur.execute("SELECT id, bm_user_id, plan_name, amount, created_at, source_hint FROM raw_boxmagic WHERE payment_status IN ('activo', 'congelado')")
        df_bm = pd.DataFrame(cur.fetchall(), columns=['id', 'user', 'plan', 'amount', 'date', 'source_hint'])
        df_bm['date'] = pd.to_datetime(df_bm['date']).dt.tz_localize(None)
        
        # VirtualPOS
        cur.execute("SELECT id, vpos_code, amount, transaction_date FROM raw_virtualpos")
        df_vpos = pd.DataFrame(cur.fetchall(), columns=['id', 'code', 'amount', 'date'])
        df_vpos['date'] = pd.to_datetime(df_vpos['date']).dt.tz_localize(None)
        
        # Bank
        cur.execute("SELECT id, bank_date, amount, description FROM raw_bank WHERE amount > 0")
        df_bank = pd.DataFrame(cur.fetchall(), columns=['id', 'date', 'amount', 'desc'])
        df_bank['date'] = pd.to_datetime(df_bank['date']).dt.tz_localize(None)
        
        # 3. Matching
        print("\n🔍 Procesando Match y Tasas...")
        
        unmatched_vpos = df_vpos.copy()
        unmatched_bank = df_bank.copy()
        
        insert_sql = """
            INSERT INTO consolidated_incomes 
            (transaction_date, amount_expected, amount_received, amount_banked, 
             source_bm_id, source_vpos_id, source_bank_id, 
             status, net_income, iva_debit, commission_amount, sede)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        for _, bm in df_bm.iterrows():
            bruto = float(bm['amount'])
            # REGLA EXENTO: El Neto es igual al Bruto, IVA es 0
            neto = bruto
            iva = 0
            
            # Match con VPOS
            vpos_candidates = unmatched_vpos[unmatched_vpos['amount'] == bruto].copy()
            vpos_id = None
            
            if not vpos_candidates.empty:
                vpos_candidates['diff'] = (vpos_candidates['date'] - bm['date']).dt.days.abs()
                best_vpos = vpos_candidates[vpos_candidates['diff'] <= 5].sort_values('diff')
                
                if not best_vpos.empty:
                    v_match = best_vpos.iloc[0]
                    vpos_id = str(v_match['id'])
                    unmatched_vpos = unmatched_vpos.drop(v_match.name)
            
            # Match con Banco (Abono)
            bank_id = None
            bank_amount = bruto
            comision = 0
            
            # El banco recibe Bruto - Comisión. Estimemos comisión ~2-3.5%
            bank_min = bruto * 0.94
            bank_candidates = unmatched_bank[
                (unmatched_bank['amount'] >= bank_min) & 
                (unmatched_bank['amount'] <= (bruto + 10))
            ].copy()
            
            if not bank_candidates.empty:
                bank_candidates['diff'] = (bank_candidates['date'] - bm['date']).dt.days.abs()
                best_bank = bank_candidates[bank_candidates['diff'] <= 7].sort_values('diff')
                
                if not best_bank.empty:
                    b_match = best_bank.iloc[0]
                    bank_id = str(b_match['id'])
                    bank_amount = float(b_match['amount'])
                    comision = bruto - bank_amount
                    unmatched_bank = unmatched_bank.drop(b_match.name)
            
            status = 'MATCH_FULL' if (vpos_id and bank_id) else ('MATCH_PARTIAL' if vpos_id else 'PENDING_DEPOSIT')
            
            # Lógica de Sede Optimizada (Expert Style)
            plan = str(bm['plan']).strip()
            sede = bm['source_hint'] or 'General'
            
            # Si el hint es General, intentamos rescatar por nombre de plan (Legacy Support)
            if sede == 'General':
                plan_upper = plan.upper()
                if 'MARINA' in plan_upper or 'CF M' in plan_upper or ' M ' in plan_upper:
                    sede = 'Marina'
                elif 'CAMPANARIO' in plan_upper or 'CF C' in plan_upper or ' C ' in plan_upper:
                    sede = 'Campanario'

            # 3. Reglas Específicas
            # (generic remain General)

            cur.execute(insert_sql, (
                bm['date'], bruto, bruto, bank_amount,
                str(bm['id']), vpos_id, bank_id,
                status, neto, iva, comision, sede
            ))
                
        conn.commit()
        print("\n✅ Conciliación impositiva completada.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    reconcile()
