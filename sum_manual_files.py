
import pandas as pd
import re
import os

FILES = [
    (r"c:\Users\DELL\Desktop\Agente kent-bell\downloads\boxmagic\BoxMagic marina (13).csv", "Marina"),
    (r"c:\Users\DELL\Desktop\Agente kent-bell\downloads\boxmagic\reporte de ventas campanario 29012026.csv", "Campanario")
]

def clean_money(val):
    if not isinstance(val, str):
        return 0
    # Extract numbers
    match = re.search(r'\$ ?([\d\.]+)', val)
    if match:
        clean = match.group(1).replace('.', '')
        return float(clean)
    return 0

def main():
    print("=== SUMAS INDIVIDUALES DE ARCHIVOS (RAW) ===")
    
    grand_total = 0
    
    for fpath, label in FILES:
        if not os.path.exists(fpath):
            print(f"❌ Archivo no encontrado: {fpath}")
            continue
            
        # Parse manually because of the messy format
        total_file = 0
        count = 0
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for line in lines:
                # Look for money pattern: $ 12.345 or $12345
                match = re.search(r'\$ ?([\d\.]+)', line)
                if match:
                    raw_num = match.group(1).replace('.', '')
                    try:
                        amount = float(raw_num)
                        total_file += amount
                        count += 1
                    except:
                        pass
            
            print(f"📂 {label} ({os.path.basename(fpath)})")
            print(f"   - Pagos detectados: {count}")
            print(f"   - Total File: ${total_file:,.0f}")
            grand_total += total_file
            print("-" * 30)

        except Exception as e:
            print(f"Error procesando {fpath}: {e}")
            
    print(f"\n💰 GRAN TOTAL (Suma de Archivos): ${grand_total:,.0f}")

if __name__ == "__main__":
    main()
