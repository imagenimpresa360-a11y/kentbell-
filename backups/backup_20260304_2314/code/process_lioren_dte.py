
import asyncio
import os
import pandas as pd
import argparse
from playwright.async_api import async_playwright
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def get_engine():
    load_dotenv()
    db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    return create_engine(db_url)

async def sync_lioren_boletas(target_month=None, target_year=None):
    load_dotenv()
    LIOREN_USER = os.getenv('LIOREN_USER')
    LIOREN_PASS = os.getenv('LIOREN_PASS')
    
    now = datetime.now()
    if not target_month: target_month = now.month
    if not target_year: target_year = now.year
    
    start_date = f"{target_year}-{target_month:02d}-01"
    end_date = f"{target_year}-{target_month:02d}-31" # Lioren accepts 31 even for Feb
    
    # Campanario Company ID we found earlier is typically selected by default or we can just download whatever is in the dashboard.
    # For now, we will just download the default company.
    
    excel_path = f"tmp_lioren_boletas_{target_month}_{target_year}.xlsx"
    if os.path.exists(excel_path):
        os.remove(excel_path)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        page.set_default_timeout(60000)
        
        try:
            print("Login Lioren...")
            await page.goto("https://www.lioren.cl/login")
            await page.fill('input[name="email"]', LIOREN_USER)
            await page.fill('input[name="password"]', LIOREN_PASS)
            await page.locator('button:has-text("INICIAR SESIÓN")').click(timeout=60000)
            await page.wait_for_load_state('networkidle')
            
            # Click SELECCIONAR on Campanario
            # For simplicity, we just look for SELECCIONAR
            print("Selecting company...")
            await page.evaluate("""() => {
                let btns = document.querySelectorAll('a');
                for(let b of btns) {
                    if(b.textContent.includes('SELECCIONAR')) {
                        b.click();
                        return;
                    }
                }
            }""")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            print("Navigating to Boleta Exenta view...")
            direct_url = f"https://cl.lioren.enterprises/s/#/comprobantes/emitidos?rpp=50&fecha_desde={start_date}&fecha_hasta={end_date}&tipo_documento=41"
            await page.goto(direct_url)
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(6)
            
            print("Clicking ALL funnel or filter icons to open filter panel...")
            await page.evaluate('''
                () => {
                    let icons = Array.from(document.querySelectorAll('md-icon'));
                    let filterIcon = icons.find(i => i.innerHTML.includes('filter_list') || i.innerHTML.includes('funnel') || i.className.includes('filter'));
                    if(filterIcon && filterIcon.closest('button')) {
                        filterIcon.closest('button').click();
                    } else {
                        let toolbars = document.querySelectorAll('md-toolbar');
                        if (toolbars.length > 1) {
                            let btns = toolbars[1].querySelectorAll('button');
                            if(btns.length > 0) btns[btns.length-1].click(); 
                        }
                    }
                }
            ''')
            await asyncio.sleep(3)
            
            print("Trying to fill filters...")
            await page.evaluate(f'''
                () => {{
                    let i0 = document.querySelector('input[ng-model*="fecha0"], input[name="fecha0"], input[aria-label*="Fecha inicial"]');
                    let i1 = document.querySelector('input[ng-model*="fecha1"], input[name="fecha1"], input[aria-label*="Fecha final"]');
                    if(i0) {{ i0.value = '{start_date}'; i0.dispatchEvent(new Event('input', {{bubbles: true}})); i0.dispatchEvent(new Event('change', {{bubbles: true}})); }}
                    if(i1) {{ i1.value = '{end_date}'; i1.dispatchEvent(new Event('input', {{bubbles: true}})); i1.dispatchEvent(new Event('change', {{bubbles: true}})); }}
                    
                    let findBtn = Array.from(document.querySelectorAll('md-sidenav button, md-dialog button, .filter-panel button')).find(b => b.textContent.toLowerCase().includes('buscar') || b.textContent.toLowerCase().includes('filtrar') || b.innerHTML.includes('search'));
                    if(findBtn) findBtn.click();
                }}
            ''')
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)

            print("Attempting to click EXCEL download...")
            # Save HTML for debugging if it fails
            html = await page.content()
            with open("lioren_debug.html", "w", encoding="utf-8") as f:
                f.write(html)
            
            # Final strategy: Wait for the specific excel icon element in the toolbar
            print("      Waiting for Excel icon selector...")
            try:
                # Selector for the Excel icon/button found in the HTML structure
                excel_selector = 'button md-icon:has-text("file_download"), button:has(md-icon:has-text("file_download")), button[aria-label="Descargar a Excel"]'
                await page.wait_for_selector(excel_selector, timeout=10000)
                
                async with page.expect_download(timeout=60000) as dl_info:
                    await page.locator(excel_selector).first.click(timeout=60000)
                    dl = await dl_info.value
                    await dl.save_as(excel_path)
                    print(f"SUCCESS: Downloaded to {excel_path}")
                    return 1
            except Exception as e_dl:
                print(f"      Selector strategy failed: {e_dl}. Trying legacy JS fallback...")
                # Try to click the Excel button using Javascript with more selectors
                clicked = await page.evaluate("""() => {
                    let icons = Array.from(document.querySelectorAll('md-icon'));
                    let excelIcon = icons.find(i => i.innerHTML.includes('file_download') || i.innerHTML.includes('get_app'));
                    if (excelIcon && excelIcon.closest('button')) {
                        excelIcon.closest('button').click();
                        return true;
                    }
                    let excelBtn = document.querySelector('button[aria-label*="Excel"], button[aria-label*="Exportar"]');
                    if (excelBtn) { excelBtn.click(); return true; }
                    return false;
                }""")
                
                if clicked:
                    async with page.expect_download(timeout=60000) as dl_info:
                        dl = await dl_info.value
                        await dl.save_as(excel_path)
                        print(f"SUCCESS: Downloaded to {excel_path} (JS Fallback)")
                        return 1
                else:
                    print("Could not find the Excel button on screen.")
                    return 0
            
            if clicked:
                print("Clicked Excel, waiting for download...")
                async with page.expect_download(timeout=60000) as dl_info:
                    dl = await dl_info.value
                    await dl.save_as(excel_path)
                    print(f"SUCCESS: Downloaded to {excel_path}")
            else:
                print("Could not find the Excel button on screen.")
                return 0

        except Exception as e:
            print(f"Error extracting Lioren: {e}")
            await page.screenshot(path="error_lioren_sync.png")
            return 0
        finally:
            await browser.close()
            
    # Step 2: Ingest Excel
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path, engine="openpyxl")
            if df.empty:
                print("Excel is empty.")
                return 0
                
            inserted = 0
            engine = get_engine()
            with engine.begin() as conn:
                for _, row in df.iterrows():
                    folio = row.get('Folio')
                    if pd.isna(folio): continue
                    
                    monto = float(row.get('Total', 0))
                    fecha_str = str(row.get('Fecha', ''))
                    
                    # Ensure formatting
                    if isinstance(row.get('Fecha'), datetime):
                        fecha = row.get('Fecha').date()
                    else:
                        try:
                            fecha = datetime.strptime(fecha_str.split()[0], '%Y-%m-%d').date()
                        except:
                            fecha = None

                    # Use raw_lioren_sales
                    # Unique constraint could be Folio + doc_type (41 is Boleta Exenta)
                    # For safety, let's just insert if not exists
                    query = text("""
                        INSERT INTO raw_lioren_sales 
                        (folio, total_amount, emission_date, doc_type, source_hint)
                        VALUES (:f, :m, :fd, 'BOLETA_EXENTA', 'Campanario')
                        ON CONFLICT DO NOTHING; 
                    """)
                    # Wait, our schema does NOT have a unique constraint on folio yet inside raw_lioren_sales.
                    # We'll just do a select first or add unique constraint.
                    exists = conn.execute(text("SELECT id FROM raw_lioren_sales WHERE folio = :f AND doc_type = 'BOLETA_EXENTA'"), {'f': int(folio)}).fetchone()
                    if not exists:
                        conn.execute(text("""
                            INSERT INTO raw_lioren_sales 
                            (folio, total_amount, emission_date, doc_type, source_hint)
                            VALUES (:f, :m, :fd, 'BOLETA_EXENTA', 'Campanario')
                        """), {'f': int(folio), 'm': monto, 'fd': fecha})
                        inserted += 1
                        
            print(f"SUCCESS: Lioren Sync Complete. Inserted {inserted} new Boletas Exentas.")
            return inserted
            
        except Exception as e:
            print(f"Error processing Excel: {e}")
            return 0
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", type=int)
    parser.add_argument("--year", type=int)
    args = parser.parse_args()
    
    asyncio.run(sync_lioren_boletas(target_month=args.month, target_year=args.year))
