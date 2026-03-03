
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def explore_lioren_login():
    load_dotenv()
    USER = os.getenv('LIOREN_USER')
    PASS = os.getenv('LIOREN_PASS')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Intentamos Linux por si hubiera algún bloqueo de bot por Windows
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            print("Going to lioren.cl...")
            await page.goto("https://lioren.cl", wait_until="networkidle")
            await page.screenshot(path="lioren_home.png")
            print("Home captured.")
            
            # Busquemos el botón de 'Iniciar Sesión' o similar
            login_link = page.get_by_role("link", name="Ingresar")
            if await login_link.count() > 0:
                await login_link.first.click()
            else:
                login_btn = page.get_by_role("link", name="Iniciar sesión")
                if await login_btn.count() > 0:
                    await login_btn.first.click()
                else:
                    print("Could not find login link, trying direct URL redirection...")
                    await page.goto("https://www.lioren.cl/login", wait_until="networkidle")

            await asyncio.sleep(5)
            await page.screenshot(path="lioren_login_page.png")
            print("Login page captured.")
            
            # List placeholders to be sure
            inputs = await page.locator("input").all()
            for inp in inputs:
                p_text = await inp.get_attribute("placeholder")
                t_text = await inp.get_attribute("type")
                v_text = await inp.get_attribute("name")
                print(f"Input: name={v_text}, type={t_text}, placeholder={p_text}")

        except Exception as e:
            print(f"Failed: {e}")
            await page.screenshot(path="lioren_error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(explore_lioren_login())
