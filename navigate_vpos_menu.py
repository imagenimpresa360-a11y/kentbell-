"""
VirtualPOS Menu Navigator
Navega por todas las opciones del menú lateral para encontrar reportes
"""
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv('VIRTUALPOS_URL')
USER = os.getenv('VIRTUALPOS_USER')
PASS = os.getenv('VIRTUALPOS_PASS')

async def login_virtualpos(page):
    """Realiza login en VirtualPOS"""
    await page.goto(URL, timeout=90000, wait_until='domcontentloaded')
    await asyncio.sleep(3)
    
    link = page.get_by_role("link", name="Acceso clientes")
    if await link.count() > 0:
        await link.first.click()
        await asyncio.sleep(3)
    
    await page.locator('input[type="email"]').fill(USER)
    await page.locator('input[type="password"]').fill(PASS)
    await page.keyboard.press('Enter')
    await asyncio.sleep(8)

async def explore_menu():
    print("=" * 70)
    print("VIRTUALPOS - NAVEGADOR DE MENÚ")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        
        page = await context.new_page()
        
        try:
            print("\n[1/3] Realizando login...")
            await login_virtualpos(page)
            print("      ✓ Login completado")
            
            print("\n[2/3] Explorando opciones del menú lateral...")
            
            # El menú lateral parece estar en un nav o aside
            # Vamos a buscar todos los enlaces clickeables del menú
            menu_selectors = [
                'nav a',
                'aside a', 
                '[role="navigation"] a',
                '.sidebar a',
                '.menu a'
            ]
            
            all_menu_items = []
            
            for selector in menu_selectors:
                try:
                    items = await page.locator(selector).all()
                    for item in items:
                        if await item.is_visible():
                            text = await item.inner_text()
                            href = await item.get_attribute('href')
                            if text.strip():
                                all_menu_items.append((text.strip(), href, item))
                except:
                    pass
            
            # Eliminar duplicados
            unique_items = {}
            for text, href, item in all_menu_items:
                if text not in unique_items:
                    unique_items[text] = (href, item)
            
            print(f"\n      Encontradas {len(unique_items)} opciones únicas:")
            print("      " + "-" * 60)
            
            for i, (text, (href, _)) in enumerate(unique_items.items()):
                print(f"      [{i}] {text[:40]:<40} → {href}")
            
            # Navegar por cada opción y capturar
            print("\n[3/3] Navegando por cada opción...")
            
            for i, (text, (href, item)) in enumerate(unique_items.items()):
                if i > 10:  # Limitar a 10 para no saturar
                    break
                
                try:
                    print(f"\n      [{i}] Navegando a: {text}")
                    
                    # Hacer clic
                    await item.click()
                    await asyncio.sleep(3)
                    
                    # Capturar screenshot
                    filename = f"vpos_menu_{i}_{text[:20].replace(' ', '_').replace('/', '_')}.png"
                    await page.screenshot(path=filename)
                    
                    # Buscar botones de exportación
                    export_keywords = ["Exportar", "Descargar", "Excel", "CSV", "PDF"]
                    found_export = False
                    
                    for keyword in export_keywords:
                        buttons = page.get_by_role("button", name=keyword)
                        if await buttons.count() > 0:
                            print(f"         ✓ Encontrado botón: {keyword}")
                            found_export = True
                    
                    if found_export:
                        print(f"         🎯 OPCIÓN PROMETEDORA: {text}")
                        # Guardar HTML de esta página
                        html = await page.content()
                        with open(f"vpos_export_option_{i}.html", 'w', encoding='utf-8') as f:
                            f.write(html)
                    
                except Exception as e:
                    print(f"         ⚠ Error: {e}")
            
            print("\n" + "=" * 70)
            print("Exploración completada. Revisa los screenshots generados.")
            print("=" * 70)
            
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(explore_menu())
