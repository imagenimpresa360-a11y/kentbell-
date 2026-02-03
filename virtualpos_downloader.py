"""
VirtualPOS Dashboard Scraper (MVP)
Extrae datos resumidos directamente del Dashboard principal para evitar problemas de navegación SPA.
"""
import asyncio
import os
import csv
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# Configuración
URL = os.getenv('VIRTUALPOS_URL')
USER = os.getenv('VIRTUALPOS_USER')
PASS = os.getenv('VIRTUALPOS_PASS')
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads", "virtualpos")

# Crear directorio de descargas
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def login_virtualpos(page):
    """Realiza login en VirtualPOS"""
    print("[1/3] Realizando login...")
    await page.goto(URL, timeout=90000, wait_until='domcontentloaded')
    
    # Espera inicial para asegurar carga
    await asyncio.sleep(3)
    
    # Clic en "Acceso clientes"
    try:
        link = page.get_by_role("link", name="Acceso clientes")
        if await link.count() > 0:
            await link.first.click()
            await asyncio.sleep(3)
    except Exception as e:
        print(f"      ⚠ Nota: {e}")

    # Llenar credenciales
    try:
        await page.wait_for_selector('input[type="email"]', timeout=30000)
        await page.locator('input[type="email"]').fill(USER)
        await page.locator('input[type="password"]').fill(PASS)
        await page.keyboard.press('Enter')
        
        # Esperar a que desaparezca el login o cargue el dashboard
        await asyncio.sleep(10)
        print("      ✓ Login enviado")
    except Exception as e:
        print(f"      ❌ Error en login: {e}")
        return False
        
    return True

async def extract_dashboard_data(page):
    """Extrae datos visibles del dashboard"""
    print("\n[2/3] Extrayendo datos del Dashboard...")
    
    data = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Esperar a que carguen las tarjetas
        await page.wait_for_selector('.card', timeout=30000)
        
        # Extraer texto completo del body para análisis
        body_text = await page.inner_text('body')
        
        # 1. Ventas Totales del Mes
        # Buscamos patrones de texto comunes en el dashboard
        # Estructura típica: "Total enero $3.954.300"
        
        # Intentar extraer usando selectores específicos si es posible, o texto
        # Basado en la estructura vista: 
        # Tarjeta "Resumen de ventas" -> "Total [Mes]" -> Valor
        
        # Buscamos elementos que contengan el signo $
        prices = await page.locator('text=/$[\d\.]+/').all_inner_texts()
        print(f"      Precios detectados: {prices}")
        
        # Estrategia: Buscar contenedores de tarjetas
        cards = await page.locator('.card').all()
        
        for i, card in enumerate(cards):
            text = await card.inner_text()
            # Limpiar y separar por líneas
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            print(f"      Tarjeta {i} líneas: {lines}")
            
            category = "Desconocido"
            if "Resumen de ventas" in text:
                category = "Ventas"
            elif "Resumen de abonos" in text:
                category = "Abonos"
            
            if category != "Desconocido":
                # Iterar líneas para encontrar pares Etiqueta -> Valor
                # Estructura usual: [Titulo, Fecha, Monto, LabelTotal, MontoTotal]
                # Ejemplo: ['Resumen de ventas', 'Viernes, 23 de enero', '$54.900', 'Total enero', '$3.961.300']
                
                for j, line in enumerate(lines):
                    if '$' in line:
                        # Encontramos un monto, miramos la línea anterior para el concepto
                        value = line
                        label = lines[j-1] if j > 0 else "Sin etiqueta"
                        
                        # Refinar concepto
                        concept_name = f"{category} - {label}"
                        
                        # Validar si es diario o mensual basado en texto
                        if "Total" in label:
                            concept_type = "Mensual"
                        else:
                            concept_type = "Diario"
                            
                        print(f"      -> Detectado: {concept_name} ({concept_type}): {value}")
                        
                        data.append({
                            'Fecha': timestamp,
                            'Concepto': concept_name,
                            'Tipo': concept_type,
                            'Valor': value,
                            'Origen': 'Dashboard'
                        })

        # Capturar screenshot para evidencia
        await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'dashboard_evidence.png'))
        print("      ✓ Screenshot de evidencia guardado")
        
        return data

    except Exception as e:
        print(f"      ❌ Error extrayendo datos: {e}")
        return []

async def scrape_virtualpos_dashboard(headless=True):
    print("=" * 70)
    print("VIRTUALPOS - DASHBOARD SCRAPER (MVP)")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        
        page = await context.new_page()
        file_path = None
        
        try:
            if await login_virtualpos(page):
                data = await extract_dashboard_data(page)
                
                if data:
                    print("\n[3/3] Guardando datos...")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"virtualpos_summary_{timestamp}.csv"
                    file_path = os.path.join(DOWNLOAD_DIR, filename)
                    
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=['Fecha', 'Concepto', 'Tipo', 'Valor', 'Origen'])
                        writer.writeheader()
                        writer.writerows(data)
                        
                    print(f"      ✓ Archivo guardado: {filename}")
                    print(f"      ✓ Ubicación: {file_path}")
                else:
                    print("      ⚠ No se extrajeron datos para guardar")
            
        except Exception as e:
            print(f"\n❌ ERROR GLOBAL: {e}")
            await page.screenshot(path='error_vpos_scraper.png')
            
        finally:
            await browser.close()
            print("\n" + "=" * 70)
            
        return file_path

if __name__ == "__main__":
    # Ejecutar en modo visible para verificar (headless=False)
    # Cambiar a True para producción
    asyncio.run(scrape_virtualpos_dashboard(headless=False))
