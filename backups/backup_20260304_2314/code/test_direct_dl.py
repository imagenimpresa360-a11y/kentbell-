
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def direct_dl_fix():
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
            
            print("Going direct to Boleta Exenta with January 2026 date range...")
            target_url = "https://cl.lioren.enterprises/empresas/the-boos-box-spa#/boletaexenta?fecha0=2026-01-01&fecha1=2026-01-31&rpp=50&orderby=fecha&direction=desc&page=1"
            await page.goto(target_url)
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
            print("Screenshot after direct nav:")
            await page.screenshot(path="lioren_direct.png")
            
            print("Searching for excel export button...")
            excel_btn = page.locator('button, a, span').filter(has_text="Excel")
            count = await excel_btn.count()
            print(f"Excel buttons found: {count}")
            
            if count > 0:
                print("Downloading...")
                async with page.expect_download(timeout=60000) as dl_info:
                    await excel_btn.first.click()
                dl = await dl_info.value
                path = "jan_campanario.xlsx"
                await dl.save_as(path)
                print(f"Saved: {path}")
            else:
                print("No excel button found with text Excel. I will inspect HTML.")
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(direct_dl_fix())
