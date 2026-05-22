
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def click_boleta():
    load_dotenv()
    USER = os.getenv('LIOREN_USER')
    PASS = os.getenv('LIOREN_PASS')
    
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
            await page.goto("https://www.lioren.cl/login")
            await page.locator('input[name="email"]').fill(USER)
            await page.locator('input[name="password"]').fill(PASS)
            await page.get_by_role("button", name="INICIAR SESIÓN").click()
            
            await page.wait_for_selector('a:has-text("SELECCIONAR")', timeout=30000)
            async with page.expect_navigation():
                await page.locator('a:has-text("SELECCIONAR")').click()
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
            print("Clicking Boleta Exenta button...")
            btn = page.locator('button[aria-label="Boleta Exenta"]')
            if await btn.count() > 0:
                print(f"Found {await btn.count()} buttons with aria-label='Boleta Exenta'")
                await btn.first.click()
            else:
                print("Button not found! Let's try button:has-text('Boleta Exenta')")
                text_btn = page.locator('button', has_text='Boleta Exenta')
                if await text_btn.count() > 0:
                    await text_btn.first.click()
                else:
                    print("Still not found.")
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            print("URL after click:", page.url)
            
            # Check for Excel download buttons inside the view
            await page.screenshot(path="lioren_boletas_real.png")
            print("Saved lioren_boletas_real.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(click_boleta())
