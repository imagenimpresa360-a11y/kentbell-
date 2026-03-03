
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def consultar_download():
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
            
            print("Expanding Boleta Exenta...")
            await page.get_by_label('Boleta Exenta').nth(0).click()
            await asyncio.sleep(2)
                    
            print("Clicking Consultar documentos natively...")
            items = page.locator('md-list-item, button').filter(has_text="Consultar documentos")
            count = await items.count()
            for i in range(count):
                if await items.nth(i).is_visible():
                    await items.nth(i).click()
                    break
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
            # Now we are in the Boleta view.
            print("URL:", page.url)
            await page.screenshot(path="lioren_boletas_view.png")
            
            print("Extracting toolbar HTML to find filter/export buttons...")
            toolbar_html = await page.evaluate('''
                () => {
                    // Try to get the green toolbar
                    let toolbars = Array.from(document.querySelectorAll('md-toolbar'));
                    if(toolbars.length > 1) return toolbars[1].outerHTML; // Usually the second one is the view toolbar
                    else if (toolbars.length === 1) return toolbars[0].outerHTML;
                    return "No toolbar";
                }
            ''')
            with open("lioren_boleta_toolbar.html", "w", encoding="utf-8") as f:
                f.write(toolbar_html)
                
            print("Clicking ALL funnel or filter icons to open filter panel...")
            # Usually md-icon for filter is 'filter_list' or 'funnel'
            await page.evaluate('''
                () => {
                    let icons = Array.from(document.querySelectorAll('md-icon'));
                    let filterIcon = icons.find(i => i.innerHTML.includes('filter_list') || i.innerHTML.includes('funnel') || i.className.includes('filter'));
                    if(filterIcon && filterIcon.closest('button')) {
                        filterIcon.closest('button').click();
                    } else {
                        // try just the last button in the secondary toolbar
                        let toolbars = document.querySelectorAll('md-toolbar');
                        if (toolbars.length > 1) {
                            let btns = toolbars[1].querySelectorAll('button');
                            if(btns.length > 0) btns[btns.length-1].click(); // last button is usually filter
                        }
                    }
                }
            ''')
            
            await asyncio.sleep(3)
            await page.screenshot(path="lioren_filter_panel.png")
            
            # Now let's try to fill the filter if it appeared!
            # It usually opens an md-sidenav or something with inputs name="fecha0", name="fecha1"
            print("Trying to fill filters for Jan 2026...")
            await page.evaluate('''
                () => {
                    let i0 = document.querySelector('input[ng-model*="fecha0"], input[name="fecha0"], input[aria-label*="Fecha inicial"]');
                    let i1 = document.querySelector('input[ng-model*="fecha1"], input[name="fecha1"], input[aria-label*="Fecha final"]');
                    if(i0) { i0.value = '2026-01-01'; i0.dispatchEvent(new Event('input', {bubbles: true})); i0.dispatchEvent(new Event('change', {bubbles: true})); }
                    if(i1) { i1.value = '2026-01-31'; i1.dispatchEvent(new Event('input', {bubbles: true})); i1.dispatchEvent(new Event('change', {bubbles: true})); }
                    
                    // Click search/refresh button inside the filter panel
                    let findBtn = Array.from(document.querySelectorAll('md-sidenav button, md-dialog button, .filter-panel button')).find(b => b.textContent.toLowerCase().includes('buscar') || b.textContent.toLowerCase().includes('filtrar') || b.innerHTML.includes('search'));
                    if(findBtn) findBtn.click();
                }
            ''')
            
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            await page.screenshot(path="lioren_filtered_jan.png")
            
            # Now let's find the EXCEL button!
            print("Attempting to click Excel button...")
            try:
                # Based on the toolbar, it's the first of the right-aligned icons in the second toolbar.
                # Specifically, looks like an md-icon containing 'excel' or 'grid_on' or 'explicit'.
                async with page.expect_download(timeout=10000) as dl_info:
                    await page.evaluate('''
                        () => {
                            let toolbars = document.querySelectorAll('md-toolbar');
                            if (toolbars.length > 1) {
                                let btns = toolbars[1].querySelectorAll('button');
                                if(btns.length > 0) {
                                    // Usually the first of these 3 icons is export
                                    // Let's see if one explicitly says export or excel
                                    let exp = Array.from(btns).find(b => b.outerHTML.includes('excel') || b.outerHTML.includes('export') || b.outerHTML.includes('grid_on') || b.outerHTML.includes('file_download'));
                                    if(exp) exp.click();
                                    else btns[0].click(); // fallback to first button
                                }
                            }
                        }
                    ''')
                dl = await dl_info.value
                path = "jan_campanario.xlsx"
                await dl.save_as(path)
                print(f"Saved: {path}")
            except Exception as e:
                print("Download failed:", e)

            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(consultar_download())
