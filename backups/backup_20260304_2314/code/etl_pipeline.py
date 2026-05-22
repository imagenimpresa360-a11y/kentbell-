
import os
import pandas as pd
import uuid
from db_utils import DatabaseManager

# Configuration
EXCEL_PATH = r"C:\Users\DELL\Desktop\Agente kent-bell\Lista_Recuperacion_Campanario_Unicos_Ago_Nov_2025.xlsx"
ACTIVE_CSV = r"C:\Users\DELL\Desktop\Agente kent-bell\alumnos activos enero 29012026.csv"
DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads", "boxmagic")

class BoxMagicLoader:
    def __init__(self):
        self.db = DatabaseManager()

    def run(self):
        print("Starting ETL Pipeline...")
        self.db.connect()
        try:
            # 1. Update Schema (Idempotent)
            print("[1/3] Updating Database Schema...")
            self.db.execute_script("schema.sql")
            
            # 2. Process Inactive Users
            print("[2/3] Processing Inactive Users Excel...")
            self.process_inactive_users()

            # 3. Process Active Students
            print("[3/3] Processing Active Students CSV...")
            self.process_active_students()
            
            print("ETL Pipeline Completed Successfully.")
            
        except Exception as e:
            print(f"ETL Failed: {e}")
        finally:
            self.db.close()

    def process_inactive_users(self):
        if not os.path.exists(EXCEL_PATH):
            print(f"Skipping: File not found {EXCEL_PATH}")
            return

        # Load Excel
        try:
            df = pd.read_excel(EXCEL_PATH)
            print(f"   Loaded {len(df)} rows from Excel.")
            
            # Prepare Batch ID
            batch_id = str(uuid.uuid4())
            
            # Insert Loop
            count = 0
            for _, row in df.iterrows():
                # Map Excel columns to DB columns
                try:
                    client = row.get('Cliente')
                    email = row.get('Email')
                    last_pay = row.get('Último Pago')
                    plan = row.get('Plan')
                    amount = row.get('Monto')
                    
                    # Simple cleanup
                    if pd.isna(client): client = None
                    else: client = str(client).strip()
                    
                    if pd.isna(email): email = None
                    else: email = str(email).strip()
                    
                    if pd.isna(amount): amount = 0
                    else: 
                         if isinstance(amount, str):
                             amount = float(amount.replace('$','').replace('.','').strip())
                    
                    query = """
                        INSERT INTO raw_boxmagic_users 
                        (import_batch_id, client_name, email, last_payment_date, plan_name, amount)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    self.db.execute_query(query, (batch_id, client, email, last_pay, plan, amount))
                    count += 1
                except Exception as e:
                    print(f"   Error inserting row {count}: {e}")
            
            print(f"   Inserted {count} records into raw_boxmagic_users.")
        except Exception as e:
            print(f"   Error reading Excel: {e}")

    def process_active_students(self):
        if not os.path.exists(ACTIVE_CSV):
            print(f"Skipping: File not found {ACTIVE_CSV}")
            return

        import re
        batch_id = str(uuid.uuid4())
        
        count = 0
        try:
            with open(ACTIVE_CSV, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for line in lines[1:]: # Skip header
                # 1. Extract Email
                email_match = re.search(r'[\w\.-]+@[\w\.-]+', line)
                if not email_match:
                    continue
                email = email_match.group(0)
                
                # 2. Extract Name (Left of email)
                parts = line.split(email)
                raw_name = parts[0]
                # Cleanup: Remove numbers appearing at start (index), quotes, commas
                name = ''.join([c for c in raw_name if not c.isdigit()]).replace('"', '').replace(',', ' ').strip()
                
                # 3. Status (Simple check)
                status = "activo" if "activo" in line.lower() else "inactivo"
                
                # 4. Plan (Best effort: text after email)
                plan_part = parts[1] if len(parts) > 1 else ""
                plan = plan_part[:100].replace('"', '').replace('activo', '').replace(',', '').strip()

                try:
                    query = """
                        INSERT INTO raw_active_students 
                        (import_batch_id, full_name, email, status, plan_name)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    self.db.execute_query(query, (batch_id, name, email, status, plan))
                    count += 1
                except Exception as e:
                    pass # Silently skip malformed lines in this rapid iteration

            print(f"   Inserted {count} active students.")
            
        except Exception as e:
            print(f"   Error processing active csv: {e}")

if __name__ == "__main__":
    loader = BoxMagicLoader()
    loader.run()
