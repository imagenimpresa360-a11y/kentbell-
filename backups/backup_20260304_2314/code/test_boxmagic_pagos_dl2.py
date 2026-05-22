
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def evaluate_and_download2():
    load_dotenv()
    USER = os.getenv('BOXMAGIC_USER')
    PASS = os.getenv('BOXMAGIC_PASS')
    
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
            await page.goto("https://auth.boxmagic.cl/login")
            await page.get_by_placeholder("Correo").fill(USER)
            await page.get_by_placeholder("Contraseña").fill(PASS)
            await page.locator("button[type='submit']").click()
            
            print("Waiting for redirect...")
            await page.wait_for_selector('text="Panel de administración"', timeout=30000)
            await page.get_by_text("Panel de administración").click(force=True)
            
            print("Waiting for boxmagic.cl dashboard...")
            await page.wait_for_function("() => window.location.hostname === 'boxmagic.cl'", timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            print("Navigating to Reportes de pagos...")
            await page.goto("https://boxmagic.cl/reportes/reportes_pagos")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
            # Switch the date? Let's try to find reportrange
            print("Attempting to set dates to January 2026...")
            try:
                # We can also use evaluate to fully click the daterangepicker
                await page.evaluate('''() => {
                    let fp = document.querySelector('#reportrange');
                    if(fp) {
                        try{
                            $(fp).data('daterangepicker').setStartDate('01/01/2026');
                            $(fp).data('daterangepicker').setEndDate('31/01/2026');
                            let e = $.Event('apply.daterangepicker', { picker: $(fp).data('daterangepicker') });
                            $(fp).trigger(e);
                        }catch(err){console.log(err)}
                    }
                }''')
                await asyncio.sleep(1)
                filtrar_btn = page.locator('button').filter(has_text="filtrar")
                if await filtrar_btn.count() > 0:
                    filtrar_btn.first.click()
                elif await page.locator('text="filtrar"').count() > 0:
                    page.locator('text="filtrar"').first.click()
                await asyncio.sleep(4)
                print("Filter clicked.")
            except Exception as ex:
                print("Could not set date via JS:", ex)
            
            print("Attempting to click #exportar ...")
            try:
                # Exportar Excel link is id="exportar"
                export_btn = page.locator('#exportar')
                if await export_btn.count() > 0:
                    async with page.expect_download(timeout=30000) as dl_info:
                        await export_btn.first.click()
                    dl = await dl_info.value
                    path = "pagos_campanario_excel.xlsx"
                    await dl.save_as(path)
                    print(f"Saved EXCEL successfully: {path}")
                else:
                    print("#exportar not found. Trying CSV...")
                    csv_btn = page.locator('.buttons-csv')
                    if await csv_btn.count() > 0:
                        async with page.expect_download(timeout=30000) as dl_info:
                            await csv_btn.first.click()
                        dl = await dl_info.value
                        path = "pagos_campanario_table.csv"
                        await dl.save_as(path)
                        print(f"Saved CSV successfully: {path}")
                    else:
                        print("No export buttons found!")
            except Exception as dl_ex:
                print("Download failed:", dl_ex)

            await page.screenshot(path="final_pagos.png")
            
        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="error_pagos_dl.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(evaluate_and_download2())
