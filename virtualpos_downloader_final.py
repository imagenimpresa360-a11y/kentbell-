"""
VirtualPOS Downloader - FINAL
Descarga el reporte de transacciones de VirtualPOS.
Estrategia: Login directo + navegación por URL + múltiples métodos de descarga.
"""
import asyncio
import os
import csv
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

LOGIN_URL = "https://comercios.virtualpos.cl/login"
TRANSACTIONS_URL = "https://comercios.virtualpos.cl/finanzas/transacciones"
USER = os.getenv('VIRTUALPOS_USER')
PASS = os.getenv('VIRTUALPOS_PASS')
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads", "virtualpos")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def login(page):
    """Login directo al subdominio de comercios"""
    print("[1/4] Realizando login en comercios.virtualpos.cl...")
    await page.goto(LOGIN_URL, timeout=90000, wait_until='domcontentloaded')
    await asyncio.sleep(3)

    try:
        await page.wait_for_selector('input[type="email"], input[placeholder*="Email"]', timeout=20000)
    except:
        print("      ⚠ No se encontró campo de email. Capturando pantalla...")
        await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'debug_login_no_field.png'))
        return False

    # Llenar email
    email_input = page.locator('input[type="email"], input[placeholder*="Email"]').first
    await email_input.fill(USER)

    # Llenar contraseña
    pass_input = page.locator('input[type="password"], input[placeholder*="Contraseña"]').first
    await pass_input.fill(PASS)

    # Enviar
    try:
        btn = page.get_by_role("button", name="Entrar")
        if await btn.count() > 0:
            await btn.click()
        else:
            await page.keyboard.press('Enter')
    except:
        await page.keyboard.press('Enter')

    print("      Credenciales enviadas, esperando dashboard...")
    await asyncio.sleep(12)

    current_url = page.url
    if "login" in current_url.lower():
        print(f"      ❌ Sigue en login: {current_url}")
        await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'debug_login_failed.png'))
        return False

    print(f"      ✓ Login exitoso. URL: {current_url}")
    return True


async def navigate_to_transactions(page):
    """Navega a la sección de transacciones usando URL directa"""
    print("\n[2/4] Navegando a Transacciones...")

    # Estrategia 1: URL directa (la más confiable en SPAs)
    await page.goto(TRANSACTIONS_URL, wait_until='domcontentloaded')
    await asyncio.sleep(10)

    print(f"      URL actual: {page.url}")
    await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'transacciones_page.png'))

    # Verificar si llegamos
    if "transacciones" in page.url or "finanzas" in page.url:
        print("      ✓ En la sección de Transacciones (por URL)")
        return True

    # Estrategia 2: Navegación por menú (si la URL directa no funcionó)
    print("      ⚠ URL directa no funcionó, intentando navegación por menú...")

    try:
        # Ir al dashboard primero
        await page.goto("https://comercios.virtualpos.cl/dashboard", wait_until='domcontentloaded')
        await asyncio.sleep(5)

        # Buscar el item de menú "Transacciones"
        # VirtualPOS usa un menú con title o texto
        menu_selectors = [
            'a[title="Transacciones"]',
            'a[href*="transacciones"]',
            'nav a:has-text("Transacciones")',
            'aside a:has-text("Transacciones")',
            'li a:has-text("Transacciones")',
        ]

        for sel in menu_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    print(f"      Haciendo hover y clic en: {sel}")
                    await el.hover()
                    await asyncio.sleep(1)
                    await el.click()
                    await asyncio.sleep(3)

                    # Buscar submenú
                    submenu = page.locator('a[href*="/finanzas/transacciones"]').first
                    if await submenu.count() > 0 and await submenu.is_visible():
                        await submenu.click()
                        await asyncio.sleep(8)
                        print(f"      ✓ Submenú clickeado. URL: {page.url}")
                        return True
                    break
            except Exception as e:
                print(f"      ⚠ {sel}: {e}")
                continue

    except Exception as e:
        print(f"      ❌ Navegación por menú falló: {e}")

    return False


async def find_and_download(page):
    """
    Busca el botón de descarga y descarga el archivo.
    VirtualPOS usa un flujo de 2 pasos: clic Exportar → modal → clic OK → download.
    """
    print("\n[3/4] Buscando y ejecutando exportación...")

    # Guardar HTML para debug ANTES del clic
    html = await page.content()
    with open(os.path.join(DOWNLOAD_DIR, 'transacciones_debug.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print("      ✓ HTML pre-click guardado para debug")

    # --- ESTRATEGIA PRINCIPAL: Exportar → Modal → OK / Confirmar ---
    export_btn_selectors = [
        'button:has-text("Exportar")',
        'button:has-text("Descargar")',
        'button[title*="export" i]',
        'button[title*="descargar" i]',
        'a:has-text("Exportar")',
        'a:has-text("Descargar")',
    ]

    for sel in export_btn_selectors:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible():
                text = await btn.inner_text()
                print(f"      ✓ Botón encontrado: '{text.strip()}' [{sel}]")
                print("        Haciendo clic...")
                await btn.click()
                await asyncio.sleep(3)  # Dar tiempo al modal para aparecer

                # Capturar screenshot del modal
                await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'after_export_click.png'))

                # Buscar el botón de confirmación en el modal
                confirm_selectors = [
                    'button:has-text("OK")',
                    'button:has-text("Aceptar")',
                    'button:has-text("Confirmar")',
                    'button:has-text("Descargar")',
                    '.modal button.btn-primary',
                    '.modal-footer button.btn-primary',
                    '.modal-footer .btn:not(.btn-secondary)',
                    'div[role="dialog"] button.btn-primary',
                ]

                confirmed = False
                for conf_sel in confirm_selectors:
                    try:
                        conf_btn = page.locator(conf_sel).first
                        if await conf_btn.count() > 0 and await conf_btn.is_visible():
                            conf_text = await conf_btn.inner_text()
                            print(f"        ✓ Modal/confirmación encontrada: '{conf_text.strip()}' [{conf_sel}]")
                            
                            # ANALIZAR SI ES EMAIL O DESCARGA
                            modal_text = await page.locator('.modal-body, .modal').first.inner_text()
                            if "correo" in modal_text.lower() or "email" in modal_text.lower():
                                print("        📧 EXPORTACIÓN POR EMAIL DETECTADA.")
                                await conf_btn.click(force=True)
                                print("        ✓ Confirmación de envío por email completada.")
                                return "EMAIL_SENT"
                            
                            print("        Haciendo clic en confirmación y esperando descarga...")
                            # Ahora sí esperamos el evento de descarga si parece ser descarga
                            try:
                                async with page.expect_download(timeout=30000) as dl:
                                    await conf_btn.click(force=True)
                                download = await dl.value
                                filename = download.suggested_filename or \
                                           f"vpos_transacciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                                path = os.path.join(DOWNLOAD_DIR, filename)
                                await download.save_as(path)
                                print(f"      ✅ Descarga exitosa: {path}")
                                return path
                            except Exception as e_dl:
                                print(f"        ⚠ No se inició descarga tras confirmación: {e_dl}")
                                # Tal vez era email pero no detectamos el texto
                                return "CONFIRMED_BUT_NO_DOWNLOAD"
                    except Exception as e:
                        continue

                if not confirmed:
                    # El clic en Exportar quizás disparó download directo (sin modal)
                    print("        ⚠ No se encontró modal. Intentando download directo post-clic...")
                    try:
                        async with page.expect_download(timeout=20000) as dl:
                            # Re-clic por si el primero no disparó
                            await btn.click()
                        download = await dl.value
                        path = os.path.join(DOWNLOAD_DIR, download.suggested_filename or "vpos_export.csv")
                        await download.save_as(path)
                        print(f"      ✅ Descarga directa exitosa: {path}")
                        return path
                    except:
                        pass

        except Exception as e:
            print(f"      ⚠ Error con {sel}: {e}")
            continue

    # --- FALLBACK: Buscar links de exportación en el DOM ---
    print("      Buscando links de exportación en el DOM...")
    try:
        links = await page.locator('a').all()
        for link in links:
            try:
                href = await link.get_attribute('href') or ""
                text = (await link.inner_text()).strip()
                if any(k.lower() in href.lower() or k.lower() in text.lower()
                       for k in ["export", "download", "excel", "csv"]):
                    print(f"      🎯 Link potencial: href={href}, text={text}")
                    async with page.expect_download(timeout=30000) as dl:
                        await link.click()
                    download = await dl.value
                    path = os.path.join(DOWNLOAD_DIR, download.suggested_filename or "vpos_export.csv")
                    await download.save_as(path)
                    print(f"      ✅ Descarga exitosa: {path}")
                    return path
            except:
                continue
    except:
        pass

    print("      ❌ No se pudo completar ninguna descarga")
    await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'error_no_download.png'))
    return None


async def analyze_page(page):
    """Si no podemos descargar, muestra todos los botones disponibles"""
    print("\n[4/4] Análisis de botones y links en la página...")
    buttons = await page.locator('button').all()
    print(f"      Botones encontrados: {len(buttons)}")
    for btn in buttons:
        try:
            if await btn.is_visible():
                text = await btn.inner_text()
                cls = await btn.get_attribute('class') or ""
                print(f"         → [{text.strip()[:50]}] classes: {cls[:60]}")
        except:
            pass

    links = await page.locator('a').all()
    print(f"\n      Links encontrados: {len(links)}")
    for link in links:
        try:
            if await link.is_visible():
                href = await link.get_attribute('href') or ""
                text = await link.inner_text()
                if href and href != '#' and href != '/':
                    print(f"         → [{text.strip()[:40]}] → {href}")
        except:
            pass


async def run(headless=False):
    print("=" * 70)
    print("VIRTUALPOS - DESCARGA DE TRANSACCIONES (FINAL)")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1440, 'height': 900},
            accept_downloads=True
        )
        page = await context.new_page()
        result_path = None

        try:
            if not await login(page):
                print("\n❌ Fallo en login. Revisa credenciales en .env")
                return None

            nav_ok = await navigate_to_transactions(page)
            if not nav_ok:
                print("\n⚠ No se pudo navegar a Transacciones. Analizando página actual...")
                await analyze_page(page)
                return None

            result_path = await find_and_download(page)

            if not result_path:
                await analyze_page(page)

        except Exception as e:
            print(f"\n❌ ERROR GLOBAL: {e}")
            import traceback
            traceback.print_exc()
            try:
                await page.screenshot(path=os.path.join(DOWNLOAD_DIR, 'error_global.png'))
            except:
                pass
        finally:
            await asyncio.sleep(5)
            await browser.close()
            print("\n" + "=" * 70)
            if result_path:
                print(f"✅ RESULTADO: Archivo guardado en:\n   {result_path}")
            else:
                print("⚠ RESULTADO: No se descargó ningún archivo.")
                print(f"   Revisa los archivos de debug en: {DOWNLOAD_DIR}")
            print("=" * 70)

        return result_path


if __name__ == "__main__":
    # headless=False para ver el navegador y depurar
    asyncio.run(run(headless=False))
