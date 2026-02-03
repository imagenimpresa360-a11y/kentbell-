
from db_utils import DatabaseManager

def main():
    db = DatabaseManager()
    db.connect()
    
    print("=== VERIFICATION: STATISTICS MENU ===")
    
    # 1. Monthly Stats
    print("\n[A] View: view_inactive_users_stats")
    try:
        rows = db.fetch_all("SELECT * FROM view_inactive_users_stats")
        if not rows:
            print("   No data found.")
        for r in rows:
            print(f"   {r['month_year']}: Users={r['total_leaked_users']}, Loss=${r['estimated_revenue_loss']}, TopChurnPlan='{r['most_common_plan_churned']}'")
    except Exception as e:
        print(f"Error querying view: {e}")

    # 2. Recuperation List Sample
    print("\n[B] View: view_recuperation_list (Top 5 Recent)")
    try:
        rows = db.fetch_all("SELECT * FROM view_recuperation_list LIMIT 5")
        for r in rows:
            print(f"   {r['client_name']} ({r['email']}) - Inactive since {r['last_payment_date']} ({r['days_inactive']} days)")
    except Exception as e:
         print(f"Error querying detailed view: {e}")

    db.close()

if __name__ == "__main__":
    main()
