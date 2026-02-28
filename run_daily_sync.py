
import os
import time
import subprocess
from datetime import datetime

print("============================================================")
print(f"🔄 INICIO DE SINCRONIZACIÓN DIARIA: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("============================================================")

scripts = [
    ("1. Solicitar exportación en VirtualPOS", "python virtualpos_downloader_final.py"),
    ("2. Pausa para envío de correo (15s)", "sleep 15" if os.name == 'posix' else "timeout 15 /nobreak"),
    ("3. Buscar y descargar archivo desde el correo", "python vpos_email_fetcher.py"),
    ("4. Procesar el CSV de VirtualPOS e insertar en la BD", "python process_vpos_csv.py")
]

for desc, cmd in scripts:
    print(f"\n▶ Ejecutando: {desc}")
    start = time.time()
    
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        # Use shell=True to handle the timeout command on Windows properly
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, encoding="utf-8", env=env)
        print(f"✅ Completado en {time.time() - start:.1f}s")
        print(f"|  Salida:\n{result.stdout.strip()}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error durante la ejecución ({time.time() - start:.1f}s):")
        print(f"|  Manejo de Error:\n{e.stderr.strip() if hasattr(e, 'stderr') and e.stderr else str(e)}")
        print("❗ Deteniendo sincronización por error crítico.")
        break
        
print("============================================================")
print(f"✅ FIN DE SINCRONIZACIÓN DIARIA: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("============================================================")
