
from db_utils import DatabaseManager

def purge_sales():
    db = DatabaseManager()
    db.connect()
    
    print("=== PURGING SALES DATA (Preserving Costs) ===")
    
    tables_to_purge = [
        "consolidated_incomes",
        "raw_boxmagic",
        "raw_lioren_sales",
        "raw_virtualpos"
    ]
    
    try:
        # We use CASCADE just in case, but these are raw tables usually
        for table in tables_to_purge:
            print(f"Purging {table}...")
            db.execute_query(f"TRUNCATE {table} CASCADE")
        
        print("\n✅ Sales data purged successfully.")
        print("💡 Expense ledger and Coach costs were NOT affected.")
        
    except Exception as e:
        print(f"❌ Error during purge: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    purge_sales()
