
from db_utils import DatabaseManager

def main():
    db = DatabaseManager()
    db.connect()
    
    print("=== Checking BoxMagic Plans ===")
    try:
        rows = db.fetch_all("SELECT DISTINCT plan_name FROM raw_boxmagic LIMIT 50")
        for r in rows:
            print(f"   Plan: '{r['plan_name']}'")
    except Exception as e:
        print(f"   Error: {e}")

    db.close()

if __name__ == "__main__":
    main()
