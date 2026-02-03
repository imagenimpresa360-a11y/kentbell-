
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating...")
        await page.goto("https://auth.boxmagic.cl/login/", wait_until="networkidle")
        
        print("Collecting buttons...")
        # Get all buttons and inputs that could be buttons
        buttons = await page.locator("button, input[type='submit'], div[role='button'], a[role='button']").all()
        
        output = []
        for i, btn in enumerate(buttons):
            outer = await btn.evaluate("el => el.outerHTML")
            text = await btn.evaluate("el => el.innerText")
            visible = await btn.is_visible()
            output.append(f"Button {i}: Visible={visible}, Text='{text}', HTML={outer}")
            
        with open("buttons_dump.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(output))
            
        print("Done. Saved to buttons_dump.txt")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
