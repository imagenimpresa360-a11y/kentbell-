
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating...")
        await page.goto("https://auth.boxmagic.cl/login/", wait_until="networkidle")
        
        print("Collecting inputs...")
        inputs = await page.locator("input").all()
        
        output = []
        for i, inp in enumerate(inputs):
            outer = await inp.evaluate("el => el.outerHTML")
            visible = await inp.is_visible()
            output.append(f"Input {i}: Visible={visible}, HTML={outer}")
            
        with open("inputs_dump.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(output))
            
        print("Done. Saved to inputs_dump.txt")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
