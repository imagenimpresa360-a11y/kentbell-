
import os
import sys
import logging
from datetime import datetime

# Asegurar que el directorio raíz está en el path
sys.path.append(os.getcwd())

try:
    from etl_manager import ETLManager
except ImportError:
    print("❌ Error: No se pudo importar ETLManager. Asegúrate de correr este script en la raíz del proyecto.")
    sys.exit(1)

# Configurar logs para ejecución headless
LOG_DIR = os.path.join(os.getcwd(), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_file = os.path.join(LOG_DIR, f"daily_sync_{datetime.now().strftime('%Y%m%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("HeadlessSync")

def main():
    logger.info("============== INICIANDO SINCRONIZACIÓN DIARIA (HEADLESS) ==============")
    startTime = datetime.now()
    
    manager = ETLManager()
    success, results = manager.run_full_sync()
    
    endTime = datetime.now()
    duration = endTime - startTime
    
    logger.info(f"Sincronización finalizada en {duration.total_seconds():.1f} segundos.")
    logger.info(f"Estatus Global: {'✅ ÉXITO' if success else '❌ FALLO'}")
    
    logger.info("Detalle por módulo:")
    for mod, res in results.items():
        logger.info(f"  - {mod.capitalize()}: {res}")
        
    logger.info("========================================================================")

if __name__ == "__main__":
    main()
