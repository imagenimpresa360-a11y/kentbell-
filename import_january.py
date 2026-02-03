
import pandas as pd
import uuid
import re
from db_utils import DatabaseManager

FILES = [
    r"c:\Users\DELL\Desktop\Agente kent-bell\downloads\boxmagic\BoxMagic marina (13).csv",
    r"c:\Users\DELL\Desktop\Agente kent-bell\downloads\boxmagic\reporte de ventas campanario 29012026.csv"
]

def parse_and_load():
    db = DatabaseManager()
    db.connect()
    print("=== IMPORTING JANUARY 2026 SALES ===")
    
    # CLEANUP: Remove entries from previous run of this script (identified by JSON structure)
    print("Cleaning up previous import attempts...")
    db.execute_query("DELETE FROM raw_boxmagic WHERE raw_data::text LIKE '%raw_line%'")
    
    batch_id = str(uuid.uuid4())
    total_inserted = 0
    total_inserted = 0
    
    for fpath in FILES:
        print(f"Processing: {fpath}")
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Skip header (heuristic: starts with "Cliente" or similar, or just try to parse)
            # Actually, let's look at the data structure from previous inspection:
            # It seems like: "Name,Email,Plan,Date,Date,Method,Amount,User"
            
            for line in lines:
                # regex to capture money: "\$ \d+"
                money_match = re.search(r'\$ ?(\d+)', line)
                if not money_match:
                    continue # Skip lines without money (headers/empty)
                
                amount = float(money_match.group(1))
                
                # Extract Date (dd/mm/yyyy)
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', line)
                date_str = date_match.group(1) if date_match else "2026-01-01"
                
                # Extract Plan (heuristic: text between "activo"," and ",")
                # Or just grab the longest quoted string that looks like a plan
                # Looking at "FUNCIONAL / CF C 16 CLASES", it's usually quoted.
                # Let's try simple split by comma if quote handling is hard
                
                # Robust approach: Text containing typical plan keywords?
                # Best effort: Split by " and look for known structure
                parts = line.split('"')
                # Usually parts: [..., "Active", "PLAN NAME", "Date", ...]
                
                plan_name = "Unknown Plan"
                # Find the part that looks like a plan (contains / or CLASES or PLAN)
                for p in parts:
                    if ('/' in p or 'CLASES' in p or 'PLAN' in p) and len(p) < 100:
                        plan_name = p.strip()
                        break
                
                # User Name (usually first quoted field?)
                user_name = parts[1] if len(parts) > 1 else "Unknown"

                # print(f"Found: {date_str} | ${amount} | {plan_name}")
                
                # INSERT
                import json
                # Determine source hint from filename
                source_hint = "Marina" if "marina" in fpath.lower() else ("Campanario" if "campanario" in fpath.lower() else "General")
                
                query = """
                    INSERT INTO raw_boxmagic 
                    (import_batch_id, bm_user_id, plan_name, amount, created_at, payment_status, raw_data)
                    VALUES (%s, %s, %s, %s, TO_DATE(%s, 'DD/MM/YYYY'), 'activo', %s)
                """
                db.execute_query(query, (batch_id, user_name, plan_name, amount, date_str, json.dumps({"raw_line": line.strip(), "source_hint": source_hint})))
                total_inserted += 1
                
        except Exception as e:
            print(f"Error processing file: {e}")

    print(f"✅ Successfully inserted {total_inserted} new sales records.")
    db.close()

if __name__ == "__main__":
    parse_and_load()
