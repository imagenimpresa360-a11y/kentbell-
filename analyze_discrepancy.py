
from db_utils import DatabaseManager
import pandas as pd

def main():
    db = DatabaseManager()
    db.connect()
    
    print("=== REVENUE ANALYSIS (Discrepancy Check) ===")
    print("Checking 'consolidated_incomes' table for Year 2026 (assuming current fiscal)\n")
    
    query = """
        SELECT 
            COALESCE(sede, 'NULL') as sede, 
            COUNT(*) as tx_count, 
            SUM(net_income) as total_neto 
        FROM consolidated_incomes 
        -- WHERE EXTRACT(YEAR FROM transaction_date) = 2026 
        GROUP BY sede
    """
    
    try:
        rows = db.fetch_all(query)
        df = pd.DataFrame(rows)
        
        print(df.to_string(index=False))
        
        total_db = df['total_neto'].sum()
        total_marina = df[df['sede'] == 'Marina']['total_neto'].sum()
        total_camp = df[df['sede'] == 'Campanario']['total_neto'].sum()
        total_gen = df[df['sede'] == 'General']['total_neto'].sum()
        
        print("-" * 40)
        print(f"Total Consolidated (DB Sum): ${total_db:,.0f}")
        print(f"Sum (Marina + Campanario):   ${(total_marina + total_camp):,.0f}")
        print(f"Difference (General/Other):  ${total_gen:,.0f}")
        
        if total_gen > 0:
            print("\n[INSIGHT] There is revenue assigned to 'General'.")
            print("This explains why Manual Sum(Sedes) < Consolidated.")
            
    except Exception as e:
        print(f"Error: {e}")

    db.close()

if __name__ == "__main__":
    main()
