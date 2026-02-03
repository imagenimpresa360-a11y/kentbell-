
from db_utils import DatabaseManager

def main():
    db = DatabaseManager()
    db.connect()
    
    print("=== Analyzing 'General' Revenue Sources ===")
    
    # query to get source plans for records marked as General
    # We join with raw_boxmagic to get the original plan name
    query = """
        SELECT 
            b.plan_name, 
            COUNT(*) as count, 
            SUM(c.net_income) as total 
        FROM consolidated_incomes c
        JOIN raw_boxmagic b ON c.source_bm_id = CAST(b.id AS VARCHAR)
        WHERE c.sede = 'General'
        GROUP BY b.plan_name
        ORDER BY total DESC
    """
    
    try:
        rows = db.fetch_all(query)
        for r in rows:
            print(f"Plan: '{r['plan_name']}' | Count: {r['count']} | Total: ${r['total']:,.0f}")
            
    except Exception as e:
        print(f"Error: {e}")

    db.close()

if __name__ == "__main__":
    main()
