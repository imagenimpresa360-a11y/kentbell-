import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('etl_process.log')
    ]
)
logger = logging.getLogger('ETLManager')

# Import core processing functions
try:
    from process_bm_csv import process_boxmagic
    from process_vpos_csv import process_vpos_csv, get_latest_vpos_csv
    from process_bank_bci import process_bci_statement
    from reconcile_data import reconcile
    from reconcile_bank_expenses import reconcile_bank_expenses
    from process_lioren import process_lioren_sales, process_lioren_purchases
    from process_active_students import process_latest_active_file
except ImportError as e:
    logger.error(f"Error importing processing modules: {e}")
    # We might be running from different contexts, adjust path if needed
    sys.path.append(os.getcwd())
    from process_bm_csv import process_boxmagic
    from process_vpos_csv import process_vpos_csv, get_latest_vpos_csv
    from process_bank_bci import process_bci_statement
    from reconcile_data import reconcile
    from reconcile_bank_expenses import reconcile_bank_expenses
    from process_lioren import process_lioren_sales, process_lioren_purchases
    from process_active_students import process_latest_active_file

load_dotenv()

class ETLManager:
    def __init__(self):
        load_dotenv()
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            db_user = os.getenv('DB_USER', os.getenv('PGUSER', 'postgres'))
            db_pass = os.getenv('DB_PASS', os.getenv('PGPASSWORD', 'password'))
            db_host = os.getenv('DB_HOST', os.getenv('PGHOST', 'localhost'))
            db_port = os.getenv('DB_PORT', os.getenv('PGPORT', '5432'))
            db_name = os.getenv('DB_NAME', os.getenv('PGDATABASE', 'railway'))
            db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
            
        self.db_url = db_url
        self.engine = create_engine(self.db_url)
        self.status = "IDLE"

    def run_full_sync(self):
        """Orchestrates a full data synchronization and reconciliation."""
        start_time = datetime.now()
        logger.info("🚀 Starting Full ETL Sync...")
        self.status = "RUNNING"
        
        results = {
            "boxmagic": "Pending",
            "virtualpos": "Pending",
            "bank": "Pending",
            "lioren": "Pending",
            "students": "Pending",
            "reconciliation": "Pending"
        }

        try:
            # 0. Process Active Students
            logger.info("--- Phase 0: Processing Active Students ---")
            try:
                count, msg = process_latest_active_file()
                results["students"] = msg
            except Exception as e:
                results["students"] = f"Error: {e}"
            # 1. Process BoxMagic (Income)
            logger.info("--- Phase 1: Processing BoxMagic ---")
            try:
                process_boxmagic()
                results["boxmagic"] = "Success"
            except Exception as e:
                logger.error(f"BoxMagic processing failed: {e}")
                results["boxmagic"] = f"Error: {e}"

            # 2. Process VirtualPOS (Payments)
            logger.info("--- Phase 2: Processing VirtualPOS ---")
            try:
                vpos_csv = get_latest_vpos_csv()
                if vpos_csv:
                    process_vpos_csv(vpos_csv)
                    results["virtualpos"] = "Success"
                else:
                    results["virtualpos"] = "No new file found"
            except Exception as e:
                logger.error(f"VirtualPOS processing failed: {e}")
                results["virtualpos"] = f"Error: {e}"

            # 3. Process Bank (BCI)
            logger.info("--- Phase 3: Processing Bank Statements ---")
            try:
                # Find latest bank file in downloads/bank
                bank_dir = os.path.join(os.getcwd(), "downloads", "bank")
                if os.path.exists(bank_dir):
                    bank_files = [os.path.join(bank_dir, f) for f in os.listdir(bank_dir) if f.endswith('.xlsx')]
                    if bank_files:
                        latest_bank = max(bank_files, key=os.path.getctime)
                        process_bci_statement(latest_bank)
                        results["bank"] = "Success"
                    else:
                        results["bank"] = "No new file found"
                else:
                    results["bank"] = "Bank directory not found"
            except Exception as e:
                logger.error(f"Bank processing failed: {e}")
                results["bank"] = f"Error: {e}"

            # 4. Process Lioren (Sales & Purchases)
            logger.info("--- Phase 4: Processing Lioren ---")
            try:
                lioren_dir = os.path.join(os.getcwd(), "downloads", "lioren")
                if os.path.exists(lioren_dir):
                    # Attempt to process all xlsx in the directory
                    l_files = [os.path.join(lioren_dir, f) for f in os.listdir(lioren_dir) if f.endswith('.xlsx')]
                    if l_files:
                        for lf in l_files:
                            if "Boletas" in lf or "Ventas" in lf:
                                process_lioren_sales(lf)
                            elif "Recibidos" in lf or "Compras" in lf:
                                process_lioren_purchases(lf)
                        results["lioren"] = f"Processed {len(l_files)} files"
                    else:
                        results["lioren"] = "No files found"
                else:
                    results["lioren"] = "Directory not found"
            except Exception as e:
                logger.error(f"Lioren processing failed: {e}")
                results["lioren"] = f"Error: {e}"

            # 5. Run Reconciliation (Centralized Income)
            logger.info("--- Phase 5: Running Income Reconciliation ---")
            try:
                reconcile()
                results["reconciliation"] = "Success"
            except Exception as e:
                logger.error(f"Incomes reconciliation failed: {e}")
                results["reconciliation"] = f"Reconciliation Error: {e}"

            # 6. Run Bank vs Expenses Reconciliation
            logger.info("--- Phase 6: Running Bank vs Expenses Reconciliation ---")
            try:
                reconcile_bank_expenses()
            except Exception as e:
                logger.warn(f"Bank/Expenses reconciliation failed: {e}")

            self.status = "COMPLETED"
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"SUCCESS: Full ETL Sync Completed in {duration.total_seconds():.2f}s")
            
            self._log_sync_status("ETL_LAST_RUN", results, duration.total_seconds())

        except Exception as e:
            self.status = "FAILED"
            logger.critical(f"Critical failure in ETL Manager: {e}")
            self._log_sync_status("ETL_LAST_RUN", {"error": str(e)}, 0)

        return results

    def _log_sync_status(self, key, results, duration):
        """Records the sync outcome in the system_settings table."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        summary = {
            "timestamp": now_str,
            "duration_seconds": duration,
            "results": results,
            "status": self.status
        }
        
        import json
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO system_settings (key, value, label) 
                    VALUES (:k, :v, :l)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """), {"k": key, "v": json.dumps(summary), "l": "ETL Activity Log"})
                
                # Update main last sync date for backward compatibility
                conn.execute(text("""
                    INSERT INTO system_settings (key, value, label) 
                    VALUES ('LAST_SYNC_DATE', :v, 'Sync Principal')
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """), {"k": 'LAST_SYNC_DATE', "v": now_str})
        except Exception as e:
            logger.error(f"Failed to log sync status to DB: {e}")

if __name__ == "__main__":
    manager = ETLManager()
    manager.run_full_sync()
