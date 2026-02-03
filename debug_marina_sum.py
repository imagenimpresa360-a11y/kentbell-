
import pandas as pd
from process_bm_csv import parse_bm_csv_content

def calculate_manual_sum():
    path = r"C:\Users\DELL\Desktop\Agente kent-bell\downloads\boxmagic\BoxMagic  MARINA 2901206.csv"
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        df = parse_bm_csv_content(content)
        # Normalize columns
        df.columns = [c.lower() for c in df.columns]
        
        # Clean amount
        # Format: $15.000 or 15.000,00
        # We need to act exactly like the system does
        
        # 1. Total Raw CSV Sum
        df['clean_amount'] = (
            df['monto'].astype(str)
            .str.replace(r'[$.]', '', regex=True) # Remove $ and thousand separators dots
            .str.replace(',', '.')   # Replace decimal comma with dot
            .astype(float)
        )
        
        total_csv = df['clean_amount'].sum()
        print(f"Total CSV Raw Sum (All rows): ${total_csv:,.0f}")
        
        # 2. Filter year 2026
        # Parse Dates
        df['date_obj'] = pd.to_datetime(df['fecha de pago'], dayfirst=True, errors='coerce')
        df_2026 = df[df['date_obj'].dt.year == 2026].copy()
        
        total_2026 = df_2026['clean_amount'].sum()
        print(f"Total 2026 Only: ${total_2026:,.0f}")
        
        # 3. Identify dropped rows?
        # Maybe some have null status?
        print(f"Rows in CSV: {len(df)}")
        print(f"Rows 2026: {len(df_2026)}")
        
        # Check if any row has non-2026 date
        others = df[df['date_obj'].dt.year != 2026]
        if not others.empty:
            print("\nRows NOT in 2026:")
            print(others[['fecha de pago', 'monto']])
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    calculate_manual_sum()
