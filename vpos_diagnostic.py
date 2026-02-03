
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

async def diagnostic():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://comercios.virtualpos.cl/login"
        print(f"Navigating to {url}...")
        
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(5)
        
        # Guardar estado actual
        await page.screenshot(path='diagnostic_login.png')
        content = await page.content()
        with open('diagnostic_login.html', 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("Diagnostic info saved: diagnostic_login.png and diagnostic_login.html")
        
        # Listar todos los inputs
        inputs = await page.locator('input').all()
        print(f"Found {len(inputs)} input elements:")
        for i, input_loc in enumerate(inputs):
            placeholder = await input_loc.get_attribute('placeholder') or "N/A"
            type_attr = await input_loc.get_attribute('type') or "N/A"
            id_attr = await input_loc.get_attribute('id') or "N/A"
            print(f"  [{i}] ID: {id_attr}, Type: {type_attr}, Placeholder: {placeholder}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(diagnostic())
