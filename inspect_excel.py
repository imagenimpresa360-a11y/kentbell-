
import pandas as pd
import os

FILE_PATH = r"C:\Users\DELL\Desktop\Agente kent-bell\Lista_Recuperacion_Campanario_Unicos_Ago_Nov_2025.xlsx"

def main():
    if not os.path.exists(FILE_PATH):
        print(f"File not found: {FILE_PATH}")
        return

    try:
        # Read Excel
        df = pd.read_excel(FILE_PATH)
        
        print(f"--- File Info ---")
        print(f"Rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        
        print("\n--- First 5 Rows ---")
        print(df.head().to_string())
        
        # Check for contact info
        contact_cols = [c for c in df.columns if any(x in c.lower() for x in ['mail', 'correo', 'tel', 'fon', 'celular', 'phone'])]
        print(f"\n--- Potential Contact Columns ---")
        print(contact_cols)
        
    except Exception as e:
        print(f"Error reading excel: {e}")

if __name__ == "__main__":
    main()
