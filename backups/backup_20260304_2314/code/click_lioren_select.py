
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def click_lioren_select():
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
            print("Selection link found. Clicking...")
            
            async with page.expect_navigation():
                await page.locator('a:has-text("SELECCIONAR")').first.click()
            
            print("Navigated. Current URL:", page.url)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            await page.screenshot(path="lioren_dashboard_navigated.png")
            
            # Print links again
            links = await page.locator('a').all()
            for link in links:
                t = await link.inner_text()
                h = await link.get_attribute('href')
                if t and len(t.strip()) > 3:
                    print(f"L: {t.strip()} -> {h}")

        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="lioren_nav_err.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(click_lioren_select())
