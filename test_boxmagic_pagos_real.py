
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def check_pagos_real():
    load_dotenv()
    USER = os.getenv('BOXMAGIC_USER')
    PASS = os.getenv('BOXMAGIC_PASS')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            print("Login...")
            await page.goto("https://auth.boxmagic.cl/login")
            await page.get_by_placeholder("Correo").fill(USER)
            await page.get_by_placeholder("Contraseña").fill(PASS)
            await page.locator("button[type='submit']").click()
            
            print("Waiting for redirect...")
            await page.wait_for_selector('text="Panel de administración"', timeout=30000)
            await page.get_by_text("Panel de administración").click(force=True)
            
            print("Waiting for boxmagic.cl dashboard...")
            await page.wait_for_function("() => window.location.hostname === 'boxmagic.cl'", timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            print("Navigating directly to reportes_pagos...")
            await page.goto("https://boxmagic.cl/reportes/reportes_pagos")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
            print("Screenshotting pag...")
            await page.screenshot(path="reports_pagos_real.png", full_page=True)
            
            print("Dumping HTML...")
            with open("reports_pagos_real.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
                
        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="error_pagos_real.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(check_pagos_real())
