import os
import sys

# 1. Configurar puerto y dirección de Streamlit a través de su sistema de configuración
import streamlit.config as config

port = os.environ.get("PORT", "8080")
config.set_option("server.port", int(port))
config.set_option("server.address", "0.0.0.0")

# 2. Patch de Rutas de Starlette
# Importamos el módulo encargado de construir la aplicación Starlette en Streamlit
try:
    import streamlit.web.server.starlette.starlette_app as starlette_app
    from starlette.routing import Route
    from starlette.responses import FileResponse, Response

    original_create_routes = starlette_app.create_streamlit_routes

    def custom_create_routes(runtime):
        # Generar las rutas internas estándar de Streamlit
        routes = original_create_routes(runtime)
        
        # Handler 1: Exportación Segura de Alumnos Inactivos
        async def exportar_inactivos(request):
            token = request.query_params.get("token")
            # El token por defecto si no está en las variables de entorno de Railway
            secure_token = os.getenv("BLACK_BOX_TOKEN", "TBB_SECURE_TOKEN_2026")
            
            if not token or token != secure_token:
                return Response("Forbidden: Invalid Token", status_code=403)
                
            csv_path = "export/inactivos_latest.csv"
            if not os.path.exists(csv_path):
                return Response("File Not Found (No data generated yet)", status_code=404)
                
            return FileResponse(csv_path, media_type="text/csv", filename="inactivos_latest.csv")

        # Handler 2: Endpoint Nexus de Salud Seguro
        async def exportar_nexus(request):
            token = request.query_params.get("token")
            secure_token = os.getenv("BLACK_BOX_TOKEN", "TBB_SECURE_TOKEN_2026")
            
            if not token or token != secure_token:
                return Response("Forbidden: Invalid Token", status_code=403)
                
            nexus_path = "export/nexus.json"
            if not os.path.exists(nexus_path):
                return Response("File Not Found", status_code=404)
                
            return FileResponse(nexus_path, media_type="application/json", filename="nexus.json")

        # Inyectar rutas personalizadas antes de las rutas estándar
        # Las inyectamos arriba para evitar colisiones con el catch-all de Streamlit
        custom_routes = [
            Route("/api/cajas-negras/exportar-inactivos", exportar_inactivos, methods=["GET"]),
            Route("/api/nexus.json", exportar_nexus, methods=["GET"])
        ]
        
        return custom_routes + routes

    # Aplicar el Monkey Patch antes de que Streamlit levante el servidor
    starlette_app.create_streamlit_routes = custom_create_routes
    print("🚀 [NEXUS PROTOCOL] Monkey patch de rutas Starlette aplicado con éxito.")

except Exception as e:
    print(f"❌ [NEXUS PROTOCOL] Error aplicando parches de seguridad de Starlette: {e}", file=sys.stderr)

# 3. Lanzar Streamlit a través del bootstrap oficial
import streamlit.web.bootstrap as bootstrap
bootstrap.run("app.py", "", [], flag_options={})
