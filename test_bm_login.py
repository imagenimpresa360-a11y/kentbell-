import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# Cookie from user (The Session Injection)
LARAVEL_SESSION = "eyJpdiI6InFzbWhtMHA3WHJvNmFJUmlLY3NpQ0E9PSIsInZhbHVlIjoiZW5ucCtXVUhXWGtyMDE3N2lzUmpoVTZcL3Q0RFpCQ2pDdzgwMjlzbjBUYWFLeE4zXC9oNUc0cUEyeWxYM2pnSGpNK2NHZkkxbmFudUVYWUZMNm5HcTdpUT09IiwibWFjIjoiOTY3OGZiMDQzNzE1YmY0MGZkNTg3NTdjOTM3N2MzZmE0YWJmYzcxZmI0MTY1NTBiOGNlZmNmOWVmOWFhZTcwMiJ9"

URL_DASHBOARD = "https://boxmagic.cl/home/admin" # Direct URL to dashboard
DOMAIN = "boxmagic.cl"

async def main():
    print(f"--- STARTING SESSION INJECTION TEST ---")
    async with async_playwright() as p:
        # Launch browser with real User Agent
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Set viewport to standard desktop
            viewport={'width': 1366, 'height': 768}
        )
        
        # INJECT COOKIE
        print("Injecting 'laravel_session' cookie...")
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
            print(f"Navigating directly to {URL_DASHBOARD}...")
            await page.goto(URL_DASHBOARD, timeout=60000)
            await page.wait_for_load_state('networkidle')
            
            # Save screenshot of dashboard
            await page.screenshot(path='debug_step2_dashboard_cookie.png')
            
            title = await page.title()
            print(f"Page Title: {title}")
            print(f"Current URL: {page.url}")
            
            # Save HTML for analysis
            html_content = await page.content()
            with open('debug_dashboard_cookie.html', 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Verification
            if "login" in page.url:
                print("FAILURE: Redirected back to login. Cookie might be expired or insufficient.")
            else:
                print("SUCCESS: Access confirmed! We are in the dashboard.")
                
        except Exception as e:
            print(f"ERROR: {e}")
            await page.screenshot(path='debug_error_cookie.png')
            
        finally:
            await browser.close()
            print("--- TEST FINISHED ---")

if __name__ == "__main__":
    asyncio.run(main())
