
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def consultar_documentos_js():
    load_dotenv()
    USER = os.getenv('LIOREN_USER')
    PASS = os.getenv('LIOREN_PASS')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            print("Login...")
            await page.goto("https://www.lioren.cl/login")
            await page.locator('input[name="email"]').fill(USER)
            await page.locator('input[name="password"]').fill(PASS)
            await page.get_by_role("button", name="INICIAR SESIÓN").click()
            
            await page.wait_for_selector('a:has-text("SELECCIONAR")', timeout=30000)
            async with page.expect_navigation():
                await page.locator('a:has-text("SELECCIONAR")').click()
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
            print("Expanding Boleta Exenta...")
            count = await page.get_by_label('Boleta Exenta').count()
            for i in range(count):
                try:
                    await page.get_by_label('Boleta Exenta').nth(i).click()
                    await asyncio.sleep(1)
                except Exception as ex:
                    print(f"Clicking Boleta {i} failed: {ex}")
                    
            print("Clicking Consultar documentos...")
            # there are multiple "Consultar documentos" because of Factura Exenta, Nota de Credito etc
            # use js to click the latest visible one or all of them!
            await page.evaluate('''
                () => {
                    let items = Array.from(document.querySelectorAll('button, a, p, span, div, li'));
                    let targets = items.filter(el => el.textContent && el.textContent.trim() === 'Consultar documentos');
                    targets.forEach(t => {
                        let style = window.getComputedStyle(t);
                        if (style.display !== 'none' && t.offsetHeight > 0) {
                            t.click();
                            if (t.parentElement) t.parentElement.click();
                        }
                    });
                }
            ''')
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            print("URL:", page.url)
            await page.screenshot(path="lioren_consultar.png")
            print("Screenshot taken.")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(consultar_documentos_js())
