
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()
USER = os.getenv('BOXMAGIC_USER')
PASS = os.getenv('BOXMAGIC_PASS')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating...")
        await page.goto("https://boxmagic.cl/login", wait_until="networkidle")
        
        print("Filling...")
        await page.fill("input[data-bmid='input-email-ingreso']", USER)
        await page.fill("input[data-bmid='input-password-ingreso']", PASS)
        
        print("Clicking...")
        await page.click("[data-bmid='btn-ingresar']")
        
        print("Waiting 10s...")
        await asyncio.sleep(10)
        
        print(f"Current URL: {page.url}")
        
        print("Dumping text...")
        text = await page.inner_text("body")
        with open("page_text_failure.txt", "w", encoding="utf-8") as f:
            f.write(text)
            
        print("Checking for alerts...")
        alerts = await page.locator(".alert, .error, .toast, [role='alert']").all_inner_texts()
        print(f"Alerts found: {alerts}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
