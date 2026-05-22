
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def explore_menus():
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
            
            # Use javascript to click the sidebar items directly
            print("Clicking Boleta Exenta via js...")
            await page.evaluate('''
                () => {
                    let items = Array.from(document.querySelectorAll('span, a, div, li, button'));
                    let be = items.find(el => el.textContent && el.textContent.trim() === 'Boleta Exenta');
                    if (be) be.click();
                }
            ''')
            
            print("Waiting network idle...")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(10)
            await page.screenshot(path="lioren_boletas_view.png")
            print("Boletas view taken")

            # Check for Excel button
            print("Checking Excel buttons...")
            await page.evaluate('''
                () => {
                    let b = Array.from(document.querySelectorAll('button'));
                    let ex = b.find(el => el.innerText.includes('Excel') || el.className.includes('excel'));
                    if (ex) { console.log('Found excel btn'); }
                }
            ''')
            # Extract HTML body to analyze
            html = await page.content()
            with open("lioren_boletas_html.txt", "w", encoding="utf-8") as f:
                f.write(html)

            # Try clicking Sucursales
            print("Clicking Sucursales via js...")
            await page.evaluate('''
                () => {
                    let items = Array.from(document.querySelectorAll('span, a, div, li, button'));
                    let t = items.find(el => el.textContent && el.textContent.trim() === 'Sucursales');
                    if (t) t.click();
                }
            ''')
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(8)
            await page.screenshot(path="lioren_sucursales_view.png")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(explore_menus())
