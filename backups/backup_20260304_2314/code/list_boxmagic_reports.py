
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def list_reports():
    load_dotenv()
    USER = os.getenv('BOXMAGIC_USER')
    PASS = os.getenv('BOXMAGIC_PASS')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            print("Step 1: Login...")
            await page.goto("https://auth.boxmagic.cl/login")
            await page.get_by_placeholder("Correo").fill(USER)
            await page.get_by_placeholder("Contraseña").fill(PASS)
            await page.locator("button[type='submit']").click()
            
            await page.wait_for_selector('text="Panel de administración"', timeout=30000)
            await page.get_by_text("Panel de administración").click(force=True)
            
            await page.wait_for_function("() => window.location.hostname === 'boxmagic.cl'", timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            print("Step 2: Navigating to Reports list...")
            await page.goto("https://boxmagic.cl/reportes")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            await page.screenshot(path="boxmagic_all_reports.png")
            
            # Listar todos los links en la página de reportes
            links = await page.locator('a').all()
            for link in links:
                text = await link.inner_text()
                href = await link.get_attribute('href')
                if href and '/reportes/' in href:
                    print(f"Report: {text.strip()} -> {href}")

        except Exception as e:
            print(f"Failed: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(list_reports())
