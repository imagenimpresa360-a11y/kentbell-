
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating to https://auth.boxmagic.cl/login/")
        await page.goto("https://auth.boxmagic.cl/login/", wait_until="networkidle")
        
        print("\n--- INPUTS ---")
        inputs = await page.locator("input").all()
        for i, inp in enumerate(inputs):
            print(f"Input {i}: {await inp.evaluate('el => el.outerHTML')}")
            
        print("\n--- BUTTONS ---")
        buttons = await page.locator("button, input[type='submit'], div[role='button']").all()
        for i, btn in enumerate(buttons):
            print(f"Button {i}: {await btn.evaluate('el => el.outerHTML')}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
