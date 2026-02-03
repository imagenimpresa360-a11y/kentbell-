import pandas as pd
import os

file_path = r"c:\Users\DELL\Desktop\Agente kent-bell\downloads\historico 2020-2025\1er reporte consolidado solo ventas 2020-2025.xlsx"

try:
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        print("Columns in Excel:")
        print(df.columns.tolist())
        print("\nFirst 5 rows:")
        print(df.head())
        
        # Check if there's a 'Sede' or 'Sucursal' column
        # and filter for 'Campanario' and '2025'
        
    else:
        print(f"File not found: {file_path}")
except Exception as e:
    print(f"Error: {e}")
