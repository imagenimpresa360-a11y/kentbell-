
import asyncio
import os
from playwright.async_api import async_playwright

DEBUG_DIR = os.path.join(os.getcwd(), "downloads", "boxmagic_debug")
os.makedirs(DEBUG_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Try the URL from .env
        url = "https://auth.boxmagic.cl/"
        print(f"Navigating to {url}...")
        
        try:
            await page.goto(url, timeout=60000)
            print("Page loaded.")
            
            # Save HTML
            content = await page.content()
            html_path = os.path.join(DEBUG_DIR, "login_page.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"HTML saved to {html_path}")
            
            # Save Screenshot
            png_path = os.path.join(DEBUG_DIR, "login_page.png")
            await page.screenshot(path=png_path)
            print(f"Screenshot saved to {png_path}")
            
            # Print simple analysis
            inputs = await page.locator("input").count()
            print(f"Found {inputs} input fields.")
            
            for i in range(inputs):
                el = page.locator("input").nth(i)
                name = await el.get_attribute("name")
                id_attr = await el.get_attribute("id")
                type_attr = await el.get_attribute("type")
                placeholder = await el.get_attribute("placeholder")
                print(f"Input {i}: name='{name}', id='{id_attr}', type='{type_attr}', placeholder='{placeholder}'")
                
        except Exception as e:
            print(f"Error: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
