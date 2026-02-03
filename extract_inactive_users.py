
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# Cookie from boxmagic_downloader.py
LARAVEL_SESSION = "eyJpdiI6InFzbWhtMHA3WHJvNmFJUmlLY3NpQ0E9PSIsInZhbHVlIjoiZW5ucCtXVUhXWGtyMDE3N2lzUmpoVTZcL3Q0RFpCQ2pDdzgwMjlzbjBUYWFLeE4zXC9oNUc0cUEyeWxYM2pnSGpNK2NHZkkxbmFudUVYWUZMNm5HcTdpUT09IiwibWFjIjoiOTY3OGZiMDQzNzE1YmY0MGZkNTg3NTdjOTM3N2MzZmE0YWJmYzcxZmI0MTY1NTBiOGNlZmNmOWVmOWFhZTcwMiJ9"
DOMAIN = "boxmagic.cl"

DEBUG_DIR = os.path.join(os.getcwd(), "downloads", "boxmagic_debug")
os.makedirs(DEBUG_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 720})
        
        # Inject Cookie
        await context.add_cookies([{
            'name': 'laravel_session', 
            'value': LARAVEL_SESSION, 
            'domain': DOMAIN, 
            'path': '/'
        }])
        
        page = await context.new_page()
        
        print("1. Navigating to Dashboard with Cookie...")
        try:
            await page.goto("https://boxmagic.cl/dashboard", wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"   Goto error: {e}")

        print(f"   Current URL: {page.url}")
        
        # Check if we are at login (cookie expired)
        if "login" in page.url:
            print("   ERROR: Redirected to login. Cookie might be expired.")
            return

        print("   SUCCESS: Dashboard access confirmed (presumably).")
        
        # Save dashboard for menu analysis
        content = await page.content()
        with open("dashboard_cookie_access.html", "w", encoding="utf-8") as f:
            f.write(content)
        await page.screenshot(path=os.path.join(DEBUG_DIR, "dashboard_cookie.png"))

        # Look for "Campanario"
        print("2. Checking for 'Campanario' profile...")
        campanario = await page.get_by_text("Campanario").count()
        if campanario > 0:
            print("   'Campanario' text found on page.")
        else:
            print("   'Campanario' NOT found. Need to switch profile?")

        # Look for "Reportes" or "Alumnos"
        print("3. Dumping links to find Inactive Users report...")
        links = await page.locator("a").all()
        for link in links:
            txt = await link.inner_text()
            href = await link.get_attribute("href")
            if txt and ("Inact" in txt or "Report" in txt or "Alum" in txt):
                print(f"   Link found: '{txt}' -> {href}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
