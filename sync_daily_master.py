
import subprocess
import os
import sys
import argparse
from datetime import datetime

def run_script(script_name, args=[]):
    print(f"\n>>> EJECUTANDO: {script_name} {' '.join(map(str, args))} ...")
    try:
        # Usamos el mismo ejecutable de python que este script
        result = subprocess.run([sys.executable, script_name] + list(map(str, args)), 
                                capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        
        # Expert Fix: Safe printing for Windows console
        try:
            print(result.stdout)
        except UnicodeEncodeError:
            print(result.stdout.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))
            
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: en {script_name}:")
        print(e.stdout)
        print(e.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Sincronizador Maestro ERP")
    parser.add_argument("--month", type=int, help="Mes a sincronizar (1-12)")
    parser.add_argument("--year", type=int, help="Año a sincronizar (YYYY)")
    args_parsed = parser.parse_args()

    start_time = datetime.now()
    
    target_month = args_parsed.month if args_parsed.month else start_time.month
    target_year = args_parsed.year if args_parsed.year else start_time.year

    print("="*60)
    print(f"Sincronización Maestra ERP - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Objetivo: {target_month}/{target_year}")
    print("="*60)
    
    # Argumentos para los scripts hijos
    child_args = ["--month", str(target_month), "--year", str(target_year)]
    
    # 1. BoxMagic Pagos (La Verdad Comercial)
    bm_ok = run_script("process_bm_pagos.py", child_args)
    
    # 2. VirtualPOS (La Verdad Transaccional Tarjetas)
    # VirtualPOS toma archivos locales, pero podemos pasarle el filtro de mes si lo ajustamos
    vpos_ok = run_script("process_vpos_csv.py")
    
    # 3. Lioren DTE (La Verdad Tributaria)
    lioren_ok = run_script("process_lioren_dte.py", child_args)
    
    # 4. Motor de Cuadratura (Cruzar todo)
    recon_ok = run_script("reconciliation_engine.py", child_args)
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "="*60)
    print(f"Sincronización Finalizada en {duration.total_seconds():.1f} segundos.")
    print(f"Estado Final: {'ÉXITO' if all([bm_ok, vpos_ok, recon_ok]) else 'CON ADVERTENCIAS'}")
    print("="*60)

if __name__ == "__main__":
    main()
