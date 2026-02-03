
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def create_table():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS")
        )
        cur = conn.cursor()
        print("🔧 Creating table accounting_periods...")
        
        sql = """
            CREATE TABLE IF NOT EXISTS accounting_periods (
                period_key VARCHAR(7) PRIMARY KEY,  -- Format: 'YYYY-MM'
                status VARCHAR(20) DEFAULT 'OPEN',  -- 'OPEN', 'CLOSED'
                closed_at TIMESTAMP,
                closed_by VARCHAR(100),
                total_income_marina DECIMAL(15,2) DEFAULT 0,
                total_income_campanario DECIMAL(15,2) DEFAULT 0,
                total_expense_marina DECIMAL(15,2) DEFAULT 0,
                total_expense_campanario DECIMAL(15,2) DEFAULT 0,
                final_margin DECIMAL(15,2) DEFAULT 0,
                notes TEXT
            );
        """
        cur.execute(sql)
        conn.commit()
        print("✅ Table `accounting_periods` created successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_table()
