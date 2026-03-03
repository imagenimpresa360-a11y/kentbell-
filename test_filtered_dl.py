
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def get_excel_btn():
    load_dotenv()
    USER = os.getenv('LIOREN_USER')
    PASS = os.getenv('LIOREN_PASS')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            print("Login...")
            await page.goto("https://www.lioren.cl/login")
            await page.locator('input[name="email"]').fill(USER)
            await page.locator('input[name="password"]').fill(PASS)
            await page.get_by_role("button", name="INICIAR SESIÓN").click()
            
            await page.wait_for_selector('a:has-text("SELECCIONAR")', timeout=30000)
            async with page.expect_navigation():
                await page.locator('a:has-text("SELECCIONAR")').click()
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
            print("Going direct to filtered Boleta Exenta...")
            # Inside the same session, navigate to the exact URL hash!
            target_url = "https://cl.lioren.enterprises/empresas/the-boos-box-spa#/boletaexenta?fecha0=2026-01-01&fecha1=2026-01-31&rpp=50&orderby=fecha&direction=desc&page=1"
            await page.goto(target_url)
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
            print("Screenshot after filtering nav:")
            await page.screenshot(path="lioren_filtered.png")
            
            # Find the header toolbar buttons
            print("Finding buttons...")
            btnsHTML = await page.evaluate('''
                () => {
                    let toolbar = document.querySelector('md-toolbar');
                    if(toolbar) {
                        return toolbar.innerHTML;
                    }
                    return "No toolbar found";
                }
            ''')
            with open("lioren_toolbar.html", "w", encoding="utf-8") as f:
                f.write(btnsHTML)
            print("Saved lioren_toolbar.html")
            
            # Let's try to click a button that has a download/excel icon specifically.
            try:
                # md-icon often has 'get_app', 'file_download', 'grid_on', 'insert_drive_file'
                print("Clicking export button... evaluating JS...")
                await page.evaluate('''
                    () => {
                        let btns = Array.from(document.querySelectorAll('button'));
                        let exportBtn = btns.find(b => b.innerHTML.includes('get_app') || b.innerHTML.includes('file_download') || b.innerHTML.includes('explicit') || b.innerHTML.includes('insert_drive_file') || b.innerHTML.includes('md-svg-icon="excel"'));
                        if(exportBtn) exportBtn.click();
                        else {
                            // in Lioren, the excel icon might literally be just an svg or text 'Excel' somewhere hidden.
                            let top_right_btns = document.querySelectorAll('.md-toolbar-tools button');
                            if(top_right_btns.length > 0) {
                                // Usually the leftmost of the 3 is export
                                top_right_btns[0].click();
                            }
                        }
                    }
                ''')
                print("Triggered export click. Waiting...")
                
            except Exception as e:
                print("JS click failed:", e)

            # Let's wait to see if download triggers
            try:
                # Start waiting for download before the click? No we already clicked.
                pass
            except Exception as e:
                pass
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(get_excel_btn())
