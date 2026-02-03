
from db_utils import DatabaseManager

def main():
    db = DatabaseManager()
    db.connect()
    
    print("=== Checking Sede Values ===")
    
    print("\n1. Table: consolidated_incomes")
    try:
        rows = db.fetch_all("SELECT DISTINCT sede FROM consolidated_incomes")
        print(f"   Found {len(rows)} distinct values:")
        for r in rows:
            val = r['sede']
            print(f"   - '{val}' (Type: {type(val)})")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n2. Table: expense_ledger")
    try:
        rows = db.fetch_all("SELECT DISTINCT sede FROM expense_ledger")
        print(f"   Found {len(rows)} distinct values:")
        for r in rows:
            val = r['sede']
            print(f"   - '{val}' (Type: {type(val)})")
    except Exception as e:
        print(f"   Error: {e}")

    db.close()

if __name__ == "__main__":
    main()
