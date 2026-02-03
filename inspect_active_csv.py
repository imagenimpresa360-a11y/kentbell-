
import pandas as pd
import os

FILE_PATH = r"C:\Users\DELL\Desktop\Agente kent-bell\alumnos activos enero 29012026.csv"

def main():
    if not os.path.exists(FILE_PATH):
        print(f"File not found: {FILE_PATH}")
        return

    try:
        # Try reading with default separator first, then ;
        try:
            df = pd.read_csv(FILE_PATH, nrows=5)
        except:
            df = pd.read_csv(FILE_PATH, sep=';', nrows=5)
            
        print(f"--- File Info ---")
        print(f"Columns: {list(df.columns)}")
        print("\n--- First 5 Rows ---")
        print(df.to_string())
        
    except Exception as e:
        print(f"Error reading CSV: {e}")

if __name__ == "__main__":
    main()
