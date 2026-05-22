
@echo off
cd /d "C:\Users\DELL\Desktop\ERP The Boos Box"
echo [%date% %time%] Iniciando Sincronizacion ERP...
python run_daily_sync.py
echo [%date% %time%] Sincronizacion Finalizada.
pause
