
import pandas as pd
import os

FILES = [
    r"c:\Users\DELL\Desktop\Agente kent-bell\downloads\boxmagic\BoxMagic marina (13).csv",
    r"c:\Users\DELL\Desktop\Agente kent-bell\downloads\boxmagic\reporte de ventas campanario 29012026.csv"
]

def main():
    print("=== INSPECTING NEW SALES FILES ===\n")
    for fpath in FILES:
        if os.path.exists(fpath):
            print(f"File: {os.path.basename(fpath)}")
            try:
                # Try reading with default (comma) then semicolon
                try:
                    df = pd.read_csv(fpath, nrows=3)
                except:
                    df = pd.read_csv(fpath, sep=';', nrows=3)
                
                print(f"Columns: {list(df.columns)}")
                print(df.to_string())
                print("-" * 50)
            except Exception as e:
                print(f"Error reading: {e}")
        else:
            print(f"NOT FOUND: {fpath}")

if __name__ == "__main__":
    main()
