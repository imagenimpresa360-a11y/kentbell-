
@echo off
echo.
echo ==========================================
echo LANZADOR SINCRONIZACION MAESTRA ERP
echo ==========================================
echo.
echo Entrando al directorio del proyecto...
cd /d "c:\Users\DELL\Desktop\ERP The Boos Box"

echo Ejecutando sincronizacion...
python sync_daily_master.py

echo.
echo Sincronizacion completada.
pause
