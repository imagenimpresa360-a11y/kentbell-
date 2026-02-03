import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# Cookie from user (The Session Injection)
LARAVEL_SESSION = "eyJpdiI6InFzbWhtMHA3WHJvNmFJUmlLY3NpQ0E9PSIsInZhbHVlIjoiZW5ucCtXVUhXWGtyMDE3N2lzUmpoVTZcL3Q0RFpCQ2pDdzgwMjlzbjBUYWFLeE4zXC9oNUc0cUEyeWxYM2pnSGpNK2NHZkkxbmFudUVYWUZMNm5HcTdpUT09IiwibWFjIjoiOTY3OGZiMDQzNzE1YmY0MGZkNTg3NTdjOTM3N2MzZmE0YWJmYzcxZmI0MTY1NTBiOGNlZmNmOWVmOWFhZTcwMiJ9"
DOMAIN = "boxmagic.cl"

# Target Report URL
URL_REPORTS_V2 = "https://boxmagic.cl/reportes/v2/reportes_pagos"

async def main():
    print(f"--- STARTING BOXMAGIC REPORT ANALYSIS ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        
        # INJECT COOKIE
        print("Injecting session cookie...")
        await context.add_cookies([
            {
                'name': 'laravel_session', 
                'value': LARAVEL_SESSION, 
                'domain': DOMAIN, 
                'path': '/'
            }
        ])
        
        page = await context.new_page()
        
        try:
            print(f"Navigating to {URL_REPORTS_V2}...")
            await page.goto(URL_REPORTS_V2, timeout=60000)
            await page.wait_for_load_state('networkidle')
            
            # Check if we were redirected to login
            if "login" in page.url:
                print("FAILURE: Redirected back to login.")
                return

            print(f"SUCCESS: Reached {page.url}")
            print(f"Page Title: {await page.title()}")
            
            # Save screenshot
            await page.screenshot(path='debug_reports_v2.png')
            
            # Save HTML
            html_content = await page.content()
            with open('debug_reports_v2.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            print("Saved 'debug_reports_v2.html' and 'debug_reports_v2.png'")
            
            # Simple text analysis
            body_text = await page.inner_text('body')
            # Look for keywords
            keywords = ["Exportar", "Excel", "Descargar", "CSV", "Generar"]
            print("--- KEYWORDS FOUND ---")
            for kw in keywords:
                if kw in body_text:
                    print(f"- Found: {kw}")
            
        except Exception as e:
            print(f"ERROR: {e}")
            
        finally:
            await browser.close()
            print("--- ANALYSIS FINISHED ---")

if __name__ == "__main__":
    asyncio.run(main())
