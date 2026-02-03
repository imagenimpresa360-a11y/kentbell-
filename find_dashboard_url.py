
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# Cookie from boxmagic_downloader.py
LARAVEL_SESSION = "eyJpdiI6InFzbWhtMHA3WHJvNmFJUmlLY3NpQ0E9PSIsInZhbHVlIjoiZW5ucCtXVUhXWGtyMDE3N2lzUmpoVTZcL3Q0RFpCQ2pDdzgwMjlzbjBUYWFLeE4zXC9oNUc0cUEyeWxYM2pnSGpNK2NHZkkxbmFudUVYWUZMNm5HcTdpUT09IiwibWFjIjoiOTY3OGZiMDQzNzE1YmY0MGZkNTg3NTdjOTM3N2MzZmE0YWJmYzcxZmI0MTY1NTBiOGNlZmNmOWVmOWFhZTcwMiJ9"
DOMAIN = "boxmagic.cl"

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
        
        urls_to_try = [
            "https://boxmagic.cl/",
            "https://boxmagic.cl/admin",
            "https://boxmagic.cl/admin/dashboard",
            "https://auth.boxmagic.cl/", # Might redirect back
        ]
        
        for url in urls_to_try:
            print(f"Testing {url}...")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(3) # Wait for redirects
                print(f"   -> Redirected to: {page.url}")
                title = await page.title()
                print(f"   -> Title: {title}")
                
                # Check for 404
                text = await page.inner_text("body")
                if "404" in text or "no existe" in text:
                    print("   -> Result: 404 Not Found")
                elif "login" in page.url or "Ingresa" in text:
                    print("   -> Result: Redirected to Login (Cookie failed for this path?)")
                else:
                    print("   -> Result: POSSIBLE SUCCESS")
                    # Save HTML if success
                    with open("dashboard_found.html", "w", encoding="utf-8") as f:
                        f.write(await page.content())
                    print("   -> HTML saved to dashboard_found.html")
                    break # Stop if found
                    
            except Exception as e:
                print(f"   -> Error: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
