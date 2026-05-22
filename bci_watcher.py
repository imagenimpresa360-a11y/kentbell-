"""
BCI Dropzone Watcher - ERP The Boos Box
Monitorea una carpeta 'downloads/bci_dropzone' en búsqueda de cartolas Excel del Banco BCI.
Al detectar una cartola (incluso en subcarpetas), la procesa automáticamente con process_bank_bci.py,
inyecta los datos en la BD PostgreSQL, y archiva el archivo en 'downloads/bci_processed'.
"""

import os
import time
import shutil
from datetime import datetime
from process_bank_bci import process_bci_statement

# Configuración de Rutas
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DROPZONE_DIR = os.path.join(PROJECT_ROOT, "downloads", "bci_dropzone")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "downloads", "bci_processed")
FAILED_DIR = os.path.join(PROJECT_ROOT, "downloads", "bci_failed")

# Crear directorios si no existen
for folder in [DROPZONE_DIR, PROCESSED_DIR, FAILED_DIR]:
    os.makedirs(folder, exist_ok=True)

POLL_INTERVAL_SECONDS = 5

def check_and_process():
    excel_files = []
    
    # Buscar archivos de manera recursiva (para soportar subcarpetas como "CARTOLAS COMPLETAS")
    for root, dirs, files in os.walk(DROPZONE_DIR):
        # Evitar procesar archivos que ya están en las carpetas de salida por si acaso
        if root.startswith(PROCESSED_DIR) or root.startswith(FAILED_DIR):
            continue
            
        for file in files:
            if (file.endswith('.xlsx') or file.endswith('.xls')) and not file.startswith('~$'):
                excel_files.append(os.path.join(root, file))

    if not excel_files:
        return

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SEARCH] Detectado(s) {len(excel_files)} archivo(s) Excel en la Dropzone.")

    for file_path in excel_files:
        filename = os.path.basename(file_path)
        print(f"   [PROCESS] Procesando: {filename}...")

        # Dar un segundo para asegurar que el archivo terminó de escribirse
        time.sleep(1.5)

        # Invocar procesador de cartola BCI
        success, message = process_bci_statement(file_path)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if success:
            dest_filename = f"{timestamp}_{filename}"
            dest_path = os.path.join(PROCESSED_DIR, dest_filename)
            try:
                shutil.move(file_path, dest_path)
                print(f"   [SUCCESS] EXITO: {message}")
                print(f"   [ARCHIVE] Archivado en: downloads/bci_processed/{dest_filename}")
            except Exception as e:
                print(f"   [ERROR] Error al archivar archivo procesado: {e}")
        else:
            dest_filename = f"{timestamp}_FAILED_{filename}"
            dest_path = os.path.join(FAILED_DIR, dest_filename)
            try:
                shutil.move(file_path, dest_path)
                print(f"   [FAILED] FALLO: {message}")
                print(f"   [WARNING] Movido a fallidos: downloads/bci_failed/{dest_filename}")
            except Exception as e:
                print(f"   [ERROR] Error al mover archivo fallido: {e}")

def main():
    print("=" * 70)
    print("INICIANDO VIGILANTE DE BUZON BCI (DROPZONE RECURSIVO)")
    print(f"   Monitoreando: {DROPZONE_DIR} y sus subcarpetas")
    print(f"   Historico Procesados: {PROCESSED_DIR}")
    print(f"   Errores/Fallidos: {FAILED_DIR}")
    print(f"   Intervalo de escaneo: Cada {POLL_INTERVAL_SECONDS} segundos")
    print("=" * 70)

    try:
        while True:
            check_and_process()
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nVigilante detenido por el usuario.")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Error en el bucle principal: {e}")

if __name__ == "__main__":
    main()
