
import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

async def explore():
    load_dotenv()
    USER = os.getenv('BOXMAGIC_USER')
    PASS = os.getenv('BOXMAGIC_PASS')
    
    async with async_playwright() as p:
        # Launching with a specific user agent and window size
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            print("Step 1: Login...")
            await page.goto("https://auth.boxmagic.cl/login")
            await page.get_by_placeholder("Correo").fill(USER)
            await page.get_by_placeholder("Contraseña").fill(PASS)
            await page.locator("button[type='submit']").click()
            
            print("Step 2: Waiting for redirect to Panel...")
            # Detectar el botón "Panel de administración" o esperar a que cambie de host
            await page.wait_for_selector('text="Panel de administración"', timeout=30000)
            await page.get_by_text("Panel de administración").click(force=True)
            
            print("Step 3: Waiting for boxmagic.cl...")
            await page.wait_for_function("() => window.location.hostname === 'boxmagic.cl'", timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            print(f"Current URL: {page.url}")
            await page.screenshot(path="boxmagic_dashboard.png")
            
            # 4. Investigar el menú superior para ver sedes
            print("Step 4: Analyzing top menu for branches...")
            nav_links = await page.locator('nav .nav-link').all_text_contents()
            print(f"Nav Links: {nav_links}")
            
            # Buscar el selector de sedes
            # A veces es un dropdown con el nombre de la sede actual
            sede_selector = await page.locator('.dropdown-toggle').all_text_contents()
            print(f"Dropdown toggles: {sede_selector}")
            
            # 5. Ir a Alumnos
            print("Step 5: Navigating to student list...")
            await page.goto("https://boxmagic.cl/alumnos/lista")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            await page.screenshot(path="boxmagic_alumnos.png")
            
            # Buscar filtros de sede en la lista de alumnos
            filters = await page.locator('select').all()
            for i, f in enumerate(filters):
                content = await f.inner_text()
                print(f"Filter {i} selects: {content[:100]}...")

            # Intentar encontrar "Campanario" en el DOM
            campanario_found = await page.locator('text="Campanario"').count()
            print(f"Campanario text found {campanario_found} times.")
            
            # 6. Diagnosticar por qué el bot de 2024 falló (verificar el rango de fechas en reportes)
            print("Step 6: Checking Reports page...")
            await page.goto("https://boxmagic.cl/reportes/v2/reportes_pagos")
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path="boxmagic_reports.png")
            
            print("Investigation complete.")

        except Exception as e:
            print(f"Exploration failed: {e}")
            await page.screenshot(path="exploration_error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(explore())
