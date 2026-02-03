"""
VirtualPOS Dashboard Explorer
Explora el dashboard de VirtualPOS para identificar opciones de reportes y exportación
"""
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv('VIRTUALPOS_URL')
USER = os.getenv('VIRTUALPOS_USER')
PASS = os.getenv('VIRTUALPOS_PASS')

async def explore_virtualpos_dashboard():
    print("=" * 70)
    print("VIRTUALPOS - EXPLORADOR DE DASHBOARD")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible para exploración
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        
        page = await context.new_page()
        
        try:
            # Login
            print("\n[1/4] Realizando login...")
            await page.goto(URL, timeout=90000, wait_until='domcontentloaded')
            print("      ✓ Página inicial cargada")
            
            # Esperar y hacer clic en "Acceso clientes"
            await asyncio.sleep(3)
            link = page.get_by_role("link", name="Acceso clientes")
            if await link.count() > 0:
                await link.first.click()
                print("      ✓ Clic en 'Acceso clientes'")
                
                # Esperar página de login con timeout más largo
                try:
                    await page.wait_for_load_state('domcontentloaded', timeout=60000)
                except:
                    print("      ⚠ Timeout en carga, continuando...")
                
                await asyncio.sleep(2)
                print("      ✓ Página de login cargada")
            
            # Llenar credenciales
            await page.locator('input[type="email"]').fill(USER)
            await page.locator('input[type="password"]').fill(PASS)
            await page.keyboard.press('Enter')
            print("      ✓ Credenciales enviadas")
            
            # Esperar carga del dashboard (sin networkidle)
            await asyncio.sleep(8)
            print("      ✓ Dashboard cargado")
            
            # Capturar dashboard
            await page.screenshot(path='vpos_dashboard_full.png', full_page=True)
            print("\n[2/4] Screenshot del dashboard guardado")
            
            # Analizar menú lateral
            print("\n[3/4] Analizando opciones del menú...")
            
            # Buscar elementos del menú
            menu_items = await page.locator('nav a, aside a, [role="navigation"] a').all()
            
            print(f"\n      Encontrados {len(menu_items)} elementos de navegación:")
            print("      " + "-" * 60)
            
            for i, item in enumerate(menu_items[:20]):  # Limitar a 20 para no saturar
                try:
                    text = await item.inner_text()
                    href = await item.get_attribute('href')
                    is_visible = await item.is_visible()
                    
                    if text and is_visible:
                        print(f"      [{i}] {text.strip()[:40]:<40} → {href}")
                except:
                    pass
            
            # Buscar palabras clave relacionadas con reportes
            print("\n[4/4] Buscando opciones de reportes/exportación...")
            keywords = ["Reporte", "Informe", "Exportar", "Descargar", "Excel", "CSV", "Transacciones", "Ventas"]
            
            body_text = await page.inner_text('body')
            
            found_keywords = []
            for keyword in keywords:
                if keyword.lower() in body_text.lower():
                    found_keywords.append(keyword)
            
            if found_keywords:
                print(f"      ✓ Palabras clave encontradas: {', '.join(found_keywords)}")
            else:
                print("      ⚠ No se encontraron palabras clave obvias")
            
            # Guardar HTML completo
            html = await page.content()
            with open('vpos_dashboard.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("\n      ✓ HTML del dashboard guardado: vpos_dashboard.html")
            
            # Intentar encontrar enlaces específicos
            print("\n[ANÁLISIS DETALLADO] Buscando enlaces de reportes...")
            
            # Buscar por texto
            for keyword in ["Reporte", "Informe", "Transacciones", "Ventas", "Exportar"]:
                links = page.get_by_role("link", name=keyword)
                count = await links.count()
                if count > 0:
                    print(f"      ✓ Encontrado enlace con '{keyword}' ({count} coincidencias)")
                    for i in range(min(count, 3)):
                        try:
                            text = await links.nth(i).inner_text()
                            href = await links.nth(i).get_attribute('href')
                            print(f"         → {text.strip()} | {href}")
                        except:
                            pass
            
            # Mantener navegador abierto para inspección manual
            print("\n" + "=" * 70)
            print("NAVEGADOR ABIERTO - Inspecciona manualmente el dashboard")
            print("Busca opciones de reportes, transacciones o exportación")
            print("El navegador se cerrará en 30 segundos...")
            print("=" * 70)
            
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path='vpos_error_exploration.png')
            
        finally:
            await browser.close()
            print("\n✓ Exploración finalizada")

if __name__ == "__main__":
    asyncio.run(explore_virtualpos_dashboard())
