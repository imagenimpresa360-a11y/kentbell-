
import asyncio
import os
import pandas as pd
import argparse
from playwright.async_api import async_playwright
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import calendar
from io import StringIO
import json

# Session state file
SESSION_FILE = os.path.join(os.path.dirname(__file__), os.getenv('BM_SESSION_PATH', 'bm_session.json'))

def get_engine():
    env_path = r"c:\Users\DELL\Desktop\ERP The Boos Box\.env"
    load_dotenv(env_path)
    db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    return create_engine(db_url)

def get_month_range(month, year):
    """Returns (start_date, end_date) strings for the given month/year."""
    last_day = calendar.monthrange(year, month)[1]
    return f"01/{month:02d}/{year}", f"{last_day}/{month:02d}/{year}"

async def set_date_range(page, start_date, end_date):
    """Filter by date using direct URL parameters (most robust)."""
    # Convert DD/MM/YYYY to YYYY-MM-DD
    start_iso = "/".join(start_date.split("/")[::-1]).replace("/", "-")
    # Actually it's DD/MM/YYYY -> YYYY-MM-DD
    parts_s = start_date.split("/")
    start_iso = f"{parts_s[2]}-{parts_s[1]}-{parts_s[0]}"
    parts_e = end_date.split("/")
    end_iso = f"{parts_e[2]}-{parts_e[1]}-{parts_e[0]}"
    
    url = f"https://boxmagic.cl/reportes/reportes_pagos?fecha_desde={start_iso}&fecha_hasta={end_iso}"
    print(f"      Navigating to: {url}")
    await page.goto(url, timeout=60000)
    await page.wait_for_load_state("load")
    await asyncio.sleep(5)
    
    # Increase display length if possible
    try:
        await page.evaluate('''() => {
            let sel = document.querySelector('select[name*="_length"]');
            if(sel) { sel.value = "100"; sel.dispatchEvent(new Event('change')); }
        }''')
        await asyncio.sleep(2)
    except: pass

async def extract_pagos(page, sede, start_date, end_date):
    """Extracts the payments table for the current sede view with verification."""
    print(f"[{sede}] Extracting pagos from {start_date} to {end_date}...")
    
    target_month = int(start_date.split('/')[1])
    max_retries = 2
    
    for attempt in range(max_retries + 1):
        await set_date_range(page, start_date, end_date)
        
        # Take a debug screenshot
        await page.screenshot(path=f"debug_{sede.lower()}_{start_date.replace('/','-')}_att{attempt}.png")
        
        html_content = await page.content()
        try:
            tables = pd.read_html(StringIO(html_content))
            for df in tables:
                if 'N°' in df.columns and 'Cliente:' in df.columns:
                    if not df.empty:
                        # Verification check on first row date
                        try:
                            sample_date_str = str(df.iloc[0]['Fecha de pago'])
                            sample_date = datetime.strptime(sample_date_str, '%d/%m/%Y')
                            if sample_date.month != target_month:
                                print(f"[{sede}] WARNING: Data month {sample_date.month} != Target {target_month}. Retrying filter...")
                                continue
                        except Exception as de:
                            print(f"[{sede}] Date parse warning: {de}")
                    
                    print(f"[{sede}] Found payments table with {len(df)} rows.")
                    return df
        except Exception as e:
            print(f"[{sede}] Error parsing HTML: {e}")
            
        if attempt < max_retries:
            print(f"[{sede}] Retry {attempt+1}/{max_retries}...")
            await asyncio.sleep(5)
            
    print(f"[{sede}] Failed to extract verified data.")
    return pd.DataFrame()

async def sync_boxmagic_pagos(target_month=None, target_year=None):
    load_dotenv(r"c:\Users\DELL\Desktop\ERP The Boos Box\.env")
    USER = os.getenv('BOXMAGIC_USER')
    PASS = os.getenv('BOXMAGIC_PASS')
    
    now = datetime.now()
    if not target_month: target_month = now.month
    if not target_year: target_year = now.year
    
    start_str, end_str = get_month_range(target_month, target_year)
    print(f"Syncing BoxMagic for {start_str} to {end_str}...")
    
    engine = get_engine()
    all_dfs = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context_args = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {'width': 1920, 'height': 1080}
        }
        if os.path.exists(SESSION_FILE):
            context_args["storage_state"] = SESSION_FILE
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        page.set_default_timeout(60000)
        
        try:
            # Check if we need to login
            session_exists = os.path.exists(SESSION_FILE)
            if session_exists:
                print(f"Loading session from {SESSION_FILE}...")
                # Validating if session is still good by navigating to a protected page
                await page.goto("https://boxmagic.cl/reportes/reportes_pagos", timeout=60000)
                await asyncio.sleep(3)
                if "auth.boxmagic.cl" in page.url:
                    print("Session expired or invalid. Proceeding to login...")
                    session_exists = False
            
            if not session_exists:
                print("Login to Boxmagic...")
                await page.goto("https://auth.boxmagic.cl/login", timeout=90000)
                await page.fill('input[type="email"]', str(USER or ""))
                await page.fill('input[type="password"]', str(PASS or ""))
                await page.click("button[type='submit']")
                
                print("Login submitted. Polling for dashboard or selection...")
                # Poll for session state
                for _ in range(30):
                    await asyncio.sleep(2)
                    cur_url = page.url
                    if "boxmagic.cl" in cur_url and "auth" not in cur_url:
                        print(f"Reached dashboard domain: {cur_url}")
                        break
                    
                    # Check for intermediate selection
                    admin_btn = page.get_by_text("Panel de administración").first
                    if await admin_btn.count() > 0 and await admin_btn.is_visible():
                        print("Intermediate screen detected. Clicking Panel de administración...")
                        await admin_btn.click(force=True)
                        await asyncio.sleep(5)
                
                # Save session state
                await context.storage_state(path=SESSION_FILE)
                print(f"Session saved to {SESSION_FILE}")
            
            await page.screenshot(path="post_login.png")
            
            if "boxmagic.cl" not in page.url or "auth" in page.url:
                print("Not on dashboard domain, attempting direct navigation as fallback...")
                await page.goto("https://boxmagic.cl/reportes/reportes_pagos", timeout=60000)
            
            await page.wait_for_load_state("load")
            print(f"Final login URL: {page.url}")
            await page.screenshot(path="final_login_state.png")
            
            # --- EXTRACT DATA PER SEDE
            sedes_config = [
                ("Campanario", os.getenv('BM_SEDE_CAMPANARIO', 'R7XLbnaLV5')),
                ("Marina", os.getenv('BM_SEDE_MARINA', 'VWQDqk1489'))
            ]
            
            for sede_name, sede_id in sedes_config:
                if not sede_id:
                    print(f"Skipping {sede_name} (No ID found in .env)")
                    continue
                    
                print(f"Switching Sede to {sede_name} ({sede_id})...")
                try:
                    await page.goto(f"https://boxmagic.cl/choose_box/{sede_id}", timeout=60000)
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)
                    
                    await page.goto("https://boxmagic.cl/reportes/reportes_pagos")
                    await page.wait_for_load_state("networkidle")
                    
                    df = await extract_pagos(page, sede_name, start_str, end_str)
                    if not df.empty:
                        df['sede'] = sede_name
                        all_dfs.append(df)
                except Exception as se:
                    print(f"Error extracting data for {sede_name}: {se}")
            
        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="error_sync.png")
        finally:
            await browser.close()
            
    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        print(f"Total BoxMagic Pagos Extracted: {len(final_df)}")
        
        inserted = 0
        with engine.begin() as conn:
            for _, row in final_df.iterrows():
                bm_id = str(row['N°'])
                if not bm_id.isdigit(): continue
                
                cliente = str(row.get('Cliente:', ''))
                email = str(row.get('Email:', ''))
                estado = str(row.get('Estado:', ''))
                plan = str(row.get('Plan', ''))
                tipo_pago = str(row.get('Tipo', '')).lower()
                monto_str = str(row.get('Monto', '0')).replace('$', '').replace('.', '').strip()
                monto = float(monto_str) if monto_str.replace('.', '', 1).isdigit() else 0.0
                vendedor = str(row.get('Vendedor', ''))
                sede = str(row.get('sede', ''))
                
                try:
                    fecha_pago = datetime.strptime(str(row.get('Fecha de pago', '')), '%d/%m/%Y').date()
                except:
                    fecha_pago = None
                    
                try:
                    fecha_inicio = datetime.strptime(str(row.get('Fecha de Inicio', '')), '%d/%m/%Y').date()
                except:
                    fecha_inicio = None
                
                query = text("""
                    INSERT INTO raw_boxmagic_pagos 
                    (bm_pago_id, cliente, email, estado, plan, fecha_pago, fecha_inicio, tipo_pago, monto, vendedor, sede)
                    VALUES (:id, :clk, :em, :est, :pl, :fp, :fi, :tp, :mo, :ven, :sd)
                    ON CONFLICT (bm_pago_id) DO UPDATE SET
                    estado = EXCLUDED.estado,
                    tipo_pago = EXCLUDED.tipo_pago,
                    fecha_pago = EXCLUDED.fecha_pago
                """)
                conn.execute(query, {
                    'id': int(bm_id), 'clk': cliente, 'em': email, 'est': estado, 'pl': plan,
                    'fp': fecha_pago, 'fi': fecha_inicio, 'tp': tipo_pago, 'mo': monto, 'ven': vendedor, 'sd': sede
                })
                inserted += 1
                
        print(f"BoxMagic Sync Complete. Upserted {inserted} records.")
        # Update system settings
        try:
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO system_settings (key, value) VALUES ('last_sync_boxmagic', :v) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"), {"v": datetime.now().strftime("%Y-%m-%d %H:%M")})
        except: pass
        return inserted
    else:
        print("No data extracted.")
        return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", type=int)
    parser.add_argument("--year", type=int)
    args = parser.parse_args()
    asyncio.run(sync_boxmagic_pagos(target_month=args.month, target_year=args.year))
