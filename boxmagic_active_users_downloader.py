
import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

async def download_alumnos():
    load_dotenv()
    USER = os.getenv('BOXMAGIC_USER')
    PASS = os.getenv('BOXMAGIC_PASS')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, accept_downloads=True)
        page = await context.new_page()
        
        try:
            print("Login...")
            await page.goto("https://auth.boxmagic.cl/login")
            await page.get_by_placeholder("Correo").fill(USER)
            await page.get_by_placeholder("Contraseña").fill(PASS)
            await page.locator("button[type='submit']").click()
            
            await page.get_by_text("Panel de administración").wait_for(state="visible", timeout=30000)
            await page.get_by_text("Panel de administración").click(force=True)
            
            await page.wait_for_function("() => window.location.hostname === 'boxmagic.cl'", timeout=60000)
            
            print("Navigating to https://boxmagic.cl/alumnos/lista...")
            await page.goto("https://boxmagic.cl/alumnos/lista")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(15)
            
            print("Executing Triple-Nested click sequence via Robust JS Promise...")
            
            async with page.expect_download(timeout=45000) as download_info:
                await page.evaluate("""() => {
                    return new Promise((resolve, reject) => {
                        const clickEl = (el, name) => {
                            if (!el) {
                                console.error(`${name} not found`);
                                return false;
                            }
                            console.log(`Clicking ${name}`);
                            el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
                            el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
                            el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                            return true;
                        };

                        // 1. Find Mi Cuenta
                        const miCuenta = Array.from(document.querySelectorAll('a.nav-link.dropdown-toggle')).find(el => el.innerText.includes('Mi cuenta'));
                        if (!clickEl(miCuenta, 'Mi Cuenta')) { reject('Mi Cuenta not found'); return; }

                        setTimeout(() => {
                            // 2. Find Funciones
                            const funciones = document.querySelector('#opciones-funciones');
                            if (!clickEl(funciones, 'Funciones')) { reject('Funciones not found'); return; }

                            setTimeout(() => {
                                // 3. Find Administra
                                const administra = document.querySelector('#funciones-administra');
                                if (!clickEl(administra, 'Administra')) { reject('Administra not found'); return; }

                                setTimeout(() => {
                                    // 4. Find Descargar
                                    const items = document.querySelectorAll('#ajustes-funciones-adicionales');
                                    let target = null;
                                    for (const item of items) {
                                        if (item.innerText.toLowerCase().includes('descargar')) {
                                            target = item;
                                            break;
                                        }
                                    }
                                    if (!clickEl(target, 'Descargar')) { reject('Descargar button not found'); return; }
                                    resolve('Sequence initiated');
                                }, 1500);
                            }, 1500);
                        }, 1500);
                    });
                }""")
            
                print("Waiting for download to finish...")
                download = await download_info.value
                target_path = "downloads/boxmagic/alumnos_activos_final.csv"
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                await download.save_as(target_path)
                print(f"SUCCESS! Saved to {target_path}")

        except Exception as e:
            print(f"Final bot (Robust JS) failed: {e}")
            await page.screenshot(path="debug_final_fail_v9.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(download_alumnos())
