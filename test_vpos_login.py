import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# VirtualPOS Credentials
URL = os.getenv('VIRTUALPOS_URL')
USER = os.getenv('VIRTUALPOS_USER')
PASS = os.getenv('VIRTUALPOS_PASS')

async def main():
    print(f"--- INICIANDO ANÁLISIS DE VIRTUALPOS ---")
    print(f"URL: {URL}")
    print(f"Usuario: {USER}")
    print(f"Contraseña: {'*' * len(PASS)}")
    
    async with async_playwright() as p:
        # Lanzar navegador visible para análisis inicial
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        
        page = await context.new_page()
        
        try:
            print(f"\n1. Navegando a {URL}...")
            await page.goto(URL, timeout=90000, wait_until='domcontentloaded')
            print("   ✓ Página cargada (DOM)")
            
            # Esperar un poco más para recursos
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
                print("   ✓ Página completamente cargada")
            except:
                print("   ⚠ Timeout en networkidle, continuando...")
            
            # Capturar página inicial
            await page.screenshot(path='debug_vpos_step1_initial.png')
            print("   ✓ Screenshot guardado: debug_vpos_step1_initial.png")
            
            # Guardar HTML
            html_content = await page.content()
            with open('debug_vpos_step1_initial.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print("   ✓ HTML guardado: debug_vpos_step1_initial.html")
            
            # Analizar texto visible
            body_text = await page.inner_text('body')
            print(f"\n2. Texto visible en la página:")
            print("=" * 60)
            print(body_text[:500])
            print("=" * 60)
            
            # Buscar botón de "Acceso clientes" o "Iniciar sesión"
            print("\n3. Buscando botón de acceso a clientes...")
            access_keywords = ["Acceso clientes", "Iniciar sesión", "Login", "Ingresar", "Acceder"]
            
            clicked_access = False
            for keyword in access_keywords:
                try:
                    # Buscar enlaces o botones
                    link = page.get_by_role("link", name=keyword)
                    if await link.count() > 0:
                        print(f"   ✓ Enlace encontrado: '{keyword}'")
                        await link.first.click()
                        clicked_access = True
                        break
                    
                    button = page.get_by_role("button", name=keyword)
                    if await button.count() > 0:
                        print(f"   ✓ Botón encontrado: '{keyword}'")
                        await button.first.click()
                        clicked_access = True
                        break
                except:
                    pass
            
            if clicked_access:
                print("   ✓ Navegando a página de login...")
                await page.wait_for_load_state('networkidle', timeout=30000)
                await page.screenshot(path='debug_vpos_step2_login_page.png')
                
                html_login = await page.content()
                with open('debug_vpos_step2_login_page.html', 'w', encoding='utf-8') as f:
                    f.write(html_login)
            
            # Buscar campos de login
            print("\n4. Buscando campos de login...")
            
            # Intentar encontrar campos de email/usuario
            email_selectors = [
                'input[type="email"]',
                'input[type="text"][name*="user"]',
                'input[type="text"][name*="email"]',
                'input[name="username"]',
                'input[name="email"]',
                'input#email',
                'input#username'
            ]
            
            email_field = None
            for selector in email_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        email_field = selector
                        print(f"   ✓ Campo de email encontrado: {selector}")
                        break
                except:
                    pass
            
            # Intentar encontrar campos de contraseña
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input#password'
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        password_field = selector
                        print(f"   ✓ Campo de contraseña encontrado: {selector}")
                        break
                except:
                    pass
            
            # Buscar botón de login
            print("\n5. Buscando botón de login...")
            button_keywords = ["Ingresar", "Login", "Entrar", "Iniciar", "Acceder"]
            
            for keyword in button_keywords:
                try:
                    buttons = page.get_by_role("button", name=keyword)
                    if await buttons.count() > 0:
                        print(f"   ✓ Botón encontrado con texto: '{keyword}'")
                except:
                    pass
            
            # Si encontramos los campos, intentar login
            if email_field and password_field:
                print(f"\n6. Intentando login automático...")
                
                await page.locator(email_field).fill(USER)
                print(f"   ✓ Email ingresado")
                
                await page.locator(password_field).fill(PASS)
                print(f"   ✓ Contraseña ingresada")
                
                # Capturar antes de hacer clic
                await page.screenshot(path='debug_vpos_step2_before_submit.png')
                
                # Intentar submit (Enter o botón)
                await page.keyboard.press('Enter')
                print(f"   ✓ Enter presionado")
                
                # Esperar navegación
                await page.wait_for_load_state('networkidle', timeout=30000)
                
                # Capturar resultado
                await page.screenshot(path='debug_vpos_step3_after_login.png')
                print("   ✓ Screenshot post-login guardado")
                
                # Guardar HTML post-login
                html_post = await page.content()
                with open('debug_vpos_step3_after_login.html', 'w', encoding='utf-8') as f:
                    f.write(html_post)
                
                print(f"\n7. Resultado:")
                print(f"   URL actual: {page.url}")
                print(f"   Título: {await page.title()}")
                
                if "login" in page.url.lower():
                    print("   ⚠ ADVERTENCIA: Aún en página de login - credenciales incorrectas o CAPTCHA")
                else:
                    print("   ✓ LOGIN EXITOSO - Fuera de la página de login")
                
            else:
                print("\n⚠ No se pudieron identificar los campos de login automáticamente")
                print("   Por favor revisa los screenshots manualmente")
            
            # Mantener navegador abierto 10 segundos para inspección manual
            print("\n8. Manteniendo navegador abierto 10 segundos para inspección...")
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            await page.screenshot(path='debug_vpos_error.png')
            
        finally:
            await browser.close()
            print("\n--- ANÁLISIS FINALIZADO ---")

if __name__ == "__main__":
    asyncio.run(main())
