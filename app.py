import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json

# Import sub-modules
from process_bank_bci import process_bci_statement
from reconcile_bank_expenses import reconcile_bank_expenses
from reconcile_data import reconcile
from process_lioren import process_lioren_sales, process_lioren_purchases
from process_bm_csv import process_bm_dataframe, parse_bm_csv_content
from process_vpos_csv import process_vpos_content
from process_active_students import process_active_students_content
from dashboard_financial import render_financial_dashboard
from dashboard_cuadratura import render_cuadratura_dashboard
from etl_manager import ETLManager

# --- CONSTANTES DE NEGOCIO ---
NUEVOS_PRECIOS = {1:7_000, 4:27_000, 8:39_900, 10:42_900, 12:45_900, 16:51_900, 20:55_900, 24:59_900}
PRECIO_A_CLASES = {7_000:1, 27_000:4, 37_900:8, 39_900:10, 42_900:12, 49_900:16, 52_900:20, 59_900:24}

def get_delta_unit(precio):
    try:
        p_int = int(float(precio))
        n = PRECIO_A_CLASES.get(p_int)
        if n is None: return 0
        return NUEVOS_PRECIOS.get(n, p_int) - p_int
    except:
        return 0

# Configuración de página
st.set_page_config(
    page_title="Kent Bell | Strategic Hub", 
    layout="wide", 
    page_icon="🏋️‍♂️",
    initial_sidebar_state="expanded"
)

# --- FUNCIONES DE APOYO ---
def show_help(title, message):
    with st.expander(f"❓ Ayuda & Ejemplo: {title}"):
        st.markdown(message)


def is_period_closed(db_engine, date_obj):
    try:
        from datetime import datetime
        if isinstance(date_obj, str):
            p_key = date_obj[:7]
        else:
            p_key = date_obj.strftime('%Y-%m')
        with db_engine.connect() as conn:
            res = conn.execute(text("SELECT status FROM accounting_periods WHERE period_key = :pk"), {"pk": p_key}).fetchone()
            if res and res[0] == 'CLOSED':
                return True
        return False
    except:
        return False

def update_sync_date(key):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO system_settings (key, value, label) 
            VALUES (:k, :v, :l)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """), {"k": key, "v": now_str, "l": "Sincronización"})

@st.cache_data(ttl=3600)
def get_lioren_realtime_data():
    import requests
    import os
    token = os.getenv('LIOREN_API_TOKEN')
    if not token:
        return None
        
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    result = {
        "cert_vence": None,
        "folios_libres": 0
    }
    
    try:
        # 1. Obtener vencimiento del certificado
        res_emp = requests.get('https://www.lioren.cl/api/miempresa', headers=headers, timeout=5)
        if res_emp.status_code == 200:
            emp_data = res_emp.json()
            valid_to_str = emp_data.get('validto')
            if valid_to_str:
                result["cert_vence"] = valid_to_str.split(' ')[0] # YYYY-MM-DD
                
        # 2. Obtener folios libres (Boletas Exentas - 41)
        res_caf = requests.get('https://www.lioren.cl/api/cafs?tipodoc=41', headers=headers, timeout=5)
        if res_caf.status_code == 200:
            cafs = res_caf.json()
            if cafs:
                result["folios_libres"] = int(cafs[0].get('libres', 0))
                
        return result
    except Exception as e:
        print(f"Error fetching Lioren real-time data: {e}")
        return None


# Cargar variables de entorno y construir URL robusta
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    DB_USER = os.getenv('DB_USER', os.getenv('PGUSER', 'postgres'))
    DB_PASS = os.getenv('DB_PASS', os.getenv('PGPASSWORD', 'password'))
    DB_HOST = os.getenv('DB_HOST', os.getenv('PGHOST', 'localhost'))
    DB_PORT = os.getenv('DB_PORT', os.getenv('PGPORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', os.getenv('PGDATABASE', 'railway'))
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Manejar el protocolo postgres:// legacy si viene directo de un addon de base de datos
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

# Validar conexión a la base de datos de forma segura
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as db_err:
    st.markdown("""
        <div style="background-color: #fee2e2; border-left: 5px solid #ef4444; padding: 25px; border-radius: 16px; margin-bottom: 25px; border: 1px solid #fca5a5;">
            <h3 style="color: #991b1b; margin-top: 0; font-weight: 800;">🔧 Conexión de Base de Datos Requerida</h3>
            <p style="color: #7f1d1d; font-size: 1.05rem; margin-bottom: 0;">
                El sitio web del ERP se ha levantado con éxito, pero <b>no puede conectarse a la base de datos PostgreSQL</b> de tu proyecto. Esto sucede porque las credenciales de la base de datos aún no se han compartido con el servicio web en Railway.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🛠️ ¿Cómo solucionarlo en 1 minuto?")
    
    st.markdown("""
    Sigue estos sencillos pasos en tu panel de control de Railway:
    
    1. **Entra a tu proyecto en Railway** (donde ves los recuadros de *Postgres* y *thorough-respect*).
    2. Haz clic en el recuadro del servicio web **`thorough-respect`**.
    3. Ve a la pestaña **Variables** en la parte superior derecha.
    4. Haz clic en el botón **New Variable** (o *Add Variable*).
    5. Configura la variable con estos valores:
       * **Name (Nombre):** `DATABASE_URL`
       * **Value (Valor):** Escribe `${{Postgres.DATABASE_URL}}` (o haz clic en el botón **Reference** y selecciona `DATABASE_URL` de la lista de Postgres).
    6. Haz clic en **Save** (Guardar).
    
    *Una vez guardado, Railway reiniciará automáticamente el sitio web en unos segundos y este se conectará al 100% de forma segura cargando todos tus movimientos bancarios.*
    """)
    
    st.stop()

# --- LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    # MODO TESTING: Auto-login como Admin para testeo rápido
    st.session_state.logged_in = True
    st.session_state.user_role = 'Admin'

if not st.session_state.logged_in:
    st.markdown("""
    <style>
        .stApp { background-color: #0f172a; color: white; font-family: 'Outfit', sans-serif;}
        .login-box {
            background-color: #1e293b;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            max-width: 400px;
            margin: 100px auto;
            border-top: 5px solid #3b82f6;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;'>🏋️‍♂️ KENT BELL ERP</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#94a3b8; margin-bottom: 25px;'>Acceso Seguro Autorizado</p>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
        
        if submit:
            if user_input == 'admin' and pass_input == 'Imagen2026':
                st.session_state.logged_in = True
                st.session_state.user_role = 'Admin'
                st.rerun()
            elif user_input == 'luis' and pass_input == 'luis2026':
                st.session_state.logged_in = True
                st.session_state.user_role = 'Luis'
                st.rerun()
            elif user_input == 'coach' and pass_input == 'coach2026':
                st.session_state.logged_in = True
                st.session_state.user_role = 'Coach'
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- SISTEMA DE DISEÑO PREMIUM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"] { 
        font-family: 'Outfit', sans-serif; 
        color: #1e293b;
    }
    .stApp { 
        background-color: #f1f5f9; 
    }
    
    /* Constrain main content for better readability */
    .main .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Sidebar Styling - Dark & Sleek */
    section[data-testid="stSidebar"] { 
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b;
    }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        padding: 1.5rem 1rem;
    }
    section[data-testid="stSidebar"] * { color: #f8fafc !important; }
    
    /* Modern Radio (Menu) */
    div[data-testid="stSidebarNav"] { display: none; } /* Hide default nav if any */
    
    /* Custom Header Style */
    .main-header {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        padding: 1rem 1.5rem;
        border-radius: 16px;
        border: 1px solid rgba(226, 232, 240, 0.8);
        margin-bottom: 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }

    /* Input Styling - White and Clean */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: white !important;
        color: #1e293b !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        transition: all 0.2s;
    }
    .stTextInput>div>div>input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1) !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 8px 8px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        border: 1px solid #e2e8f0;
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #f8fafc;
        border-top: 3px solid #3b82f6 !important;
        font-weight: 600;
    }

    /* Buttons */
    .stButton>button {
        background: #2563eb;
        color: white;
        border-radius: 10px;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
        border: none;
        transition: all 0.2s;
        width: 100%;
    }
    .stButton>button:hover {
        background: #1d4ed8;
        transform: scale(1.02);
    }

    /* Premium Metric Cards */
    div[data-testid="metric-container"] {
        background-color: #ffffff; 
        border: 1px solid #e2e8f0; 
        padding: 24px; 
        border-radius: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border-left: 5px solid #3b82f6;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        border-left: 5px solid #2563eb;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        letter-spacing: -0.025em;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #64748b !important;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #e2e8f0;
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background-color: white !important;
        color: #3b82f6 !important;
        font-weight: 600;
    }

    /* Buttons override removed for better native contrast */
    
    /* Content Blocks */
    .glass-card {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        border: 1px solid #e2e8f0;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# --- NAVEGACIÓN ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; font-size: 2rem;'>🏋️‍♂️ KENT BELL</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # --- SISTEMA DE PERFIL ---
    st.markdown("### 👤 Mi Perfil")
    user_role = st.session_state.user_role
    st.info(f"Conectado como: **{user_role}**")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.rerun()
    st.markdown("---")

    # --- DEFINICIÓN DE MENÚS POR CATEGORÍA ---
    if user_role == 'Admin':
        menu_groups = {
            "🎯 Operación Diaria (Flujo)": ["📥 Sync & Carga", "⚖️ Cuadratura Bancaria", "💸 Registrar Egresos"],
            "🏃‍♂️ Equipo & Nómina": ["🏃‍♂️ Gestión de Coaches"],
            "📊 Dashboards (Inteligencia)": ["📊 Dashboard General (P&L)", "📈 Dashboard BoxMagic", "💳 Dashboard VirtualPOS", "🏦 Dashboard Banco", "🧾 Dashboard Lioren"],
            "🚨 Retención & Control": ["📉 Alumnos Inactivos", "🚨 Alertas & Control"],
            "🔐 Contabilidad Formal": ["📑 Reportes Legales", "🏦 Caja & Banco", "🔐 Cierre Fiscal", "Docs Históricos Finanzas"]
        }
    elif user_role == 'Luis':
        menu_groups = {
            "🎯 Operación Diaria (Flujo)": ["📥 Sync & Carga", "⚖️ Cuadratura Bancaria", "💸 Registrar Egresos"],
            "📊 Dashboards (Inteligencia)": ["🏦 Dashboard Banco"],
            "🔐 Contabilidad Formal": ["📑 Reportes Legales", "🏦 Caja & Banco", "🔐 Cierre Fiscal"]
        }
    elif user_role == 'Coach':
        menu_groups = {
            "🏃‍♂️ Equipo & Nómina": ["🏃‍♂️ Gestión de Coaches"]
        }
    else:
        menu_groups = {}

    # 1. Acordeón de Navegación (Árbol de subdirectorios)
    st.markdown("### 🧭 NAVEGACIÓN")
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = menu_groups[list(menu_groups.keys())[0]][0]

    for group, pages in menu_groups.items():
        with st.expander(group, expanded=(st.session_state.current_page in pages)):
            for p in pages:
                # Botones nativos como enlaces de navegación
                btn_type = "primary" if st.session_state.current_page == p else "secondary"
                if st.button(p, use_container_width=True, key=f"nav_{p}", type=btn_type):
                    st.session_state.current_page = p
                    st.rerun()

    page = st.session_state.current_page
    
    st.markdown("---")
    
    sel_year = datetime.now().year
    
    # Declaración global de fechas para solucionar el NameError en Dashboards
    # Como ya no se eligen en la barra lateral, se establece por defecto el año fiscal completo
    start_date = datetime(sel_year, 1, 1).date()
    end_date = datetime(sel_year, 12, 31).date()
    
    ppm_rate = 0.25

    st.markdown("<div style='text-align: center; font-size: 0.8rem; opacity: 0.6; margin-top:10px;'>v3.6.1 SENIOR | Enterprise Hub</div>", unsafe_allow_html=True)

# --- HEADER DINÁMICO ---
h_col1, h_col2 = st.columns([6, 1])
with h_col1:
    st.markdown(f"""
        <div class="main-header">
            <div style="display: flex; align-items: center; gap: 15px;">
                <span style="font-size: 1.5rem;">{ page }</span>
                <h2 style="margin:0; font-weight: 800; color: #0f172a; font-size: 1.4rem;">{page}</h2>
            </div>
            <div style="color: #64748b; font-weight: 600;">
                Fiscal {sel_year} | <span style="color: #3b82f6;">v3.6.0 EXECUTIVE</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Mostrar alerta si los datos están muy desactualizados
    with engine.connect() as conn:
        last_sync = pd.read_sql(text("SELECT value FROM system_settings WHERE key = 'last_sync_boxmagic'"), conn)
        if not last_sync.empty:
            sync_dt = datetime.strptime(last_sync.iloc[0]['value'], "%Y-%m-%d %H:%M")
            if (datetime.now() - sync_dt).days > 1:
                st.warning(f"WARN:️ Los datos de ventas no se han actualizado desde hace {(datetime.now() - sync_dt).days} días. Ve a 'Sync & Carga' para actualizar.")
with h_col2:
    try:
        st.image("logo_the_boos.jpg", width=120)
    except:
        st.write("LOGO")

# --- LÓGICA DE PÁGINAS ---

# 1. DASHBOARD
# 1. DASHBOARD GENERAL (P&L)
# 1. DASHBOARD GENERAL (P&L)
# 1. DASHBOARD GENERAL (P&L)
if page == "📊 Dashboard General (P&L)":
    # --- FILTROS DE CABECERA (ZONA EJECUTIVA) ---
    sede_filter = st.radio("🏢 Sede de Control", ["Holding (Todas)", "Marina", "Campanario"], horizontal=True)
    
    # Call the new premium dashboard
    render_financial_dashboard(engine, start_date, end_date, sede_filter)

# 1.1 CUADRATURA (Reconciliation Engine)
elif page == "⚖️ Cuadratura Bancaria":
    sede_filter = st.radio("🏢 Sede de Control", ["Campanario", "Marina"], horizontal=True)
    render_cuadratura_dashboard(engine, start_date, end_date, sede_filter)

# 1.2 DASHBOARD BOXMAGIC (Expert Commercial View)
elif page == "📈 Dashboard BoxMagic":
    st.info("🎯 **Expert Analytics**: Este panel analiza la performance comercial de BoxMagic. Cuantifica los ingresos brutos y netos por sede y plan.")
    
    try:
        # Expert Resolution: Union of historical (manual) and automated (bot) data with granular date filter
        query_bm = text("""
            SELECT amount as monto, created_at as fecha, plan_name, COALESCE(source_hint, 'General') as sede
            FROM raw_boxmagic 
            WHERE created_at::date BETWEEN :start AND :end
            UNION ALL
            SELECT monto, fecha_pago as fecha, plan as plan_name, sede
            FROM raw_boxmagic_pagos
            WHERE fecha_pago::date BETWEEN :start AND :end
        """)
        df_bm = pd.read_sql(query_bm, engine, params={"start": start_date, "end": end_date})
        
        if df_bm.empty:
            st.warning("WARN:️ No hay datos cargados en el ecosistema BoxMagic. Por favor, realiza una sincronización.")
        else:
            tabs_bm = st.tabs(["🌎 Consolidado BM", "🏖️ Marina", "🏔️ Campanario"])
            
            with tabs_bm[0]:
                st.markdown("#### Desempeño Total BoxMagic")
                m1, m2, m3 = st.columns(3)
                m1.metric("Ventas Totales", f"${df_bm['monto'].sum():,.0f}")
                m2.metric("Tickets Emitidos", len(df_bm))
                m3.metric("Ticket Promedio", f"${df_bm['monto'].mean():,.0f}")
                
                g1, g2 = st.columns(2)
                with g1:
                    fig_pie = px.pie(df_bm, values='monto', names='sede', title="Distribución por Sede", hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
                with g2:
                    df_ts = df_bm.set_index('fecha').resample('M')['monto'].sum().reset_index()
                    fig_area = px.area(df_ts, x='fecha', y='monto', title="Evolución mensual (Monto)")
                    st.plotly_chart(fig_area, use_container_width=True)
            
            for i, sede_name in enumerate(["Marina", "Campanario"]):
                with tabs_bm[i+1]:
                    sdf = df_bm[df_bm['sede'] == sede_name]
                    if sdf.empty:
                        st.info(f"Sin datos específicos para {sede_name} en {sel_year}.")
                    else:
                        st.markdown(f"#### KPI: {sede_name}")
                        k_col1, k_col2 = st.columns(2)
                        k_col1.metric(f"Ventas {sede_name}", f"${sdf['monto'].sum():,.0f}")
                        k_col2.metric("N° Planes", len(sdf))
                        
                        st.markdown("---")
                        st.markdown("**Populares / Pareto de Planes**")
                        plan_dist = sdf.groupby('plan_name')['monto'].agg(['count', 'sum']).sort_values('sum', ascending=False).head(10)
                        st.bar_chart(plan_dist['sum'])
                        st.dataframe(plan_dist, use_container_width=True)

                        st.markdown("**Detalle de Registros (Últimos 50)**")
                        # Show individual rows for transparency
                        df_show = sdf.sort_values('fecha', ascending=False).head(50).copy()
                        if 'fecha' in df_show.columns:
                            df_show['fecha'] = pd.to_datetime(df_show['fecha']).dt.strftime('%d/%m/%Y')
                        if 'monto' in df_show.columns:
                            df_show['monto'] = df_show['monto'].apply(lambda x: f"${x:,.0f}")
                        
                        st.dataframe(df_show, use_container_width=True)

    except Exception as e: st.error(f"Error en analítica BoxMagic: {e}")

# 1.3 DASHBOARD VIRTUALPOS (Banking Flow)
elif page == "💳 Dashboard VirtualPOS":
    st.info("🏦 **VirtualPOS / Transbank**: Este tablero analiza los pagos con tarjetas, comisiones retenidas y abonos netos generados.")
    try:
        query_v = f"""
            SELECT 
                transaction_date as fecha, 
                amount as monto_bruto, 
                commission as comision, 
                net_amount as monto_neto, 
                client_name as cliente, 
                plan_description as plan, 
                status as estado, 
                payment_method as medio_pago 
            FROM raw_virtualpos 
            WHERE EXTRACT(YEAR FROM transaction_date) = {sel_year}
            ORDER BY transaction_date DESC
        """
        df_v = pd.read_sql(query_v, engine)
        if df_v.empty:
            st.warning("No hay flujos de VirtualPOS detectados para este año.")
        else:
            v1, v2, v3, v4 = st.columns(4)
            total_bruto = df_v['monto_bruto'].sum()
            total_comision = df_v['comision'].sum()
            total_neto = df_v['monto_neto'].sum()
            
            v1.metric("Ventas Brutas", f"${total_bruto:,.0f}")
            v2.metric("Comisiones VPOS", f"${total_comision:,.0f}", delta=f"{(total_comision/total_bruto)*100 if total_bruto else 0:.1f}%", delta_color="inverse")
            v3.metric("Abonos Netos", f"${total_neto:,.0f}")
            v4.metric("N° Transacciones", len(df_v))
            
            st.markdown("---")
            g1, g2 = st.columns([2, 1])
            with g1:
                df_v['fecha_corta'] = pd.to_datetime(df_v['fecha']).dt.date
                df_line = df_v.groupby('fecha_corta')['monto_neto'].sum().reset_index()
                fig_v = px.line(df_line, x='fecha_corta', y='monto_neto', title="Abonos Netos Diarios ($)", markers=True)
                fig_v.update_traces(line_color='#10b981')
                st.plotly_chart(fig_v, use_container_width=True)
            with g2:
                 df_status = df_v['estado'].value_counts().reset_index()
                 df_status.columns = ['estado', 'cantidad']
                 fig_pie = px.pie(df_status, values='cantidad', names='estado', title="Estado de Transacciones", hole=0.4)
                 st.plotly_chart(fig_pie, use_container_width=True)

            st.markdown("#### Detalle de Transacciones (Últimas)")
            # Formatear el dataframe para mostrar
            df_display = df_v.drop(columns=['fecha_corta']).copy()
            df_display['monto_bruto'] = df_display['monto_bruto'].apply(lambda x: f"${x:,.0f}")
            df_display['comision'] = df_display['comision'].apply(lambda x: f"${x:,.0f}")
            df_display['monto_neto'] = df_display['monto_neto'].apply(lambda x: f"${x:,.0f}")
            df_display['fecha'] = pd.to_datetime(df_display['fecha']).dt.strftime('%d/%m/%Y %H:%M')
            st.dataframe(df_display, use_container_width=True)
    except Exception as e: st.error(f"Error VPOS: {e}")

# 1.4 DASHBOARD LIOREN (Tax/Billing)
elif page == "🧾 Dashboard Lioren":
    st.info("⚖️ **Tax Integrity**: Control de facturación y boletas emitidas (Lioren/SII).")
    try:
        query_l = f"SELECT emission_date as fecha, total_amount as total, folio FROM raw_lioren_sales WHERE EXTRACT(YEAR FROM emission_date) = {sel_year}"
        df_l = pd.read_sql(query_l, engine)
        if df_l.empty:
            st.warning("No hay boletas/facturas cargadas en la tabla 'raw_lioren_sales'.")
        else:
            total_fact = df_l['total'].sum()
            
            l1, l2, l3 = st.columns(3)
            l1.metric("Total Facturado (Exento)", f"${total_fact:,.0f}")
            l2.metric("N° Documentos", len(df_l))
            l3.metric("Ticket Promedio (Exento)", f"${(total_fact/len(df_l) if len(df_l)>0 else 0):,.0f}")
            
            st.success("SUCCESS: Nota: Todas las boletas registradas operan bajo régimen **Exento de IVA**.")
            
            st.markdown("---")
            st.markdown("**Cronología de Facturación**")
            st.line_chart(df_l.set_index('fecha')['total'])
            st.dataframe(df_l, use_container_width=True)
    except Exception as e: st.error(f"Error Lioren: {e}")
    
# 1.5 DASHBOARD BANCO
elif page == "🏦 Dashboard Banco":
    st.info("🏦 **Cash Flow Audit**: Monitoreo de movimientos bancarios reales y flujo de caja.")
    try:
        query_bank = f"SELECT bank_date as fecha, description as desc, amount as monto, balance FROM raw_bank WHERE EXTRACT(YEAR FROM bank_date) = {sel_year} ORDER BY bank_date DESC"
        with engine.connect() as conn:
            df_bank = pd.read_sql(text(query_bank), conn)
            
        if df_bank.empty:
            st.warning("No hay registros bancarios para mostrar. Por favor, sube la cartola BCI en la sección 'Sync & Carga'.")
        else:
            df_bank['fecha'] = pd.to_datetime(df_bank['fecha'])
            
            total_abonos = df_bank[df_bank['monto'] > 0]['monto'].sum()
            total_cargos = df_bank[df_bank['monto'] < 0]['monto'].sum()
            
            b1, b2, b3 = st.columns(3)
            b1.metric("Total Abonos (Ingresos)", f"${total_abonos:,.0f}")
            b2.metric("Total Cargos (Egresos)", f"${abs(total_cargos):,.0f}", delta_color="inverse")
            b3.metric("Flujo Neto", f"${(total_abonos + total_cargos):,.0f}")

            # --- CENTRO DE CONCILIACIÓN ---
            st.markdown("---")
            tabs_bank = st.tabs(["🤝 Centro de Conciliación", "📃 Cartola Completa"])

            with tabs_bank[0]:
                st.subheader("🛠️ MatchMaker: Conciliación Bancaria")
                st.markdown("""
                    <div style='background-color: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px;'>
                        <small>Este módulo conecta la <b>Realidad Bancaria</b> (Izquierda) con la <b>Contabilidad</b> (Derecha).<br>
                        Selecciona 1 movimiento del banco y su(s) contraparte(s) contable(s) para cerrar el ciclo.</small>
                    </div>
                """, unsafe_allow_html=True)

                # 1. Movimientos de Banco Huérfanos (Egresos)
                query_orphan = f"SELECT id, bank_date, description, amount FROM raw_bank WHERE amount < 0 AND EXTRACT(YEAR FROM bank_date) = {sel_year} AND id::text NOT IN (SELECT source_bank_id FROM expense_ledger WHERE source_bank_id IS NOT NULL) ORDER BY bank_date DESC"
                df_orphan = pd.read_sql(query_orphan, engine)
                
                # 2. Gastos Pendientes (Ledger)
                df_pending = pd.read_sql(f"SELECT uuid, due_date, description, amount_due, sede FROM expense_ledger WHERE status = 'PENDING_PAYMENT' AND EXTRACT(YEAR FROM due_date) = {sel_year} ORDER BY due_date DESC", engine)
                
                c_left, c_center, c_right = st.columns([1, 0.2, 1])
                
                with c_left:
                    st.markdown("##### 🏦 BANCO (Salidas Reales)")
                    if not df_orphan.empty:
                        bank_sel = st.multiselect("Selecciona Cargo Bancario", 
                                                  options=df_orphan['id'].tolist(),
                                                  format_func=lambda x: f"{df_orphan[df_orphan['id']==x]['bank_date'].values[0]} | ${-df_orphan[df_orphan['id']==x]['amount'].values[0]:,.0f} | {df_orphan[df_orphan['id']==x]['description'].values[0]}",
                                                  key="match_bank")
                        sum_bank = -df_orphan[df_orphan['id'].isin(bank_sel)]['amount'].sum() if bank_sel else 0
                        st.metric("Total Banco", f"${sum_bank:,.0f}")
                    else:
                        st.success("SUCCESS: Todo conciliado en Banco.")
                        sum_bank = 0

                with c_right:
                    st.markdown("##### 📒 CONTABILIDAD (Pendientes)")
                    if not df_pending.empty:
                        ledger_sel = st.multiselect("Selecciona Gasto(s) Registrado(s)", 
                                                    options=df_pending['uuid'].tolist(),
                                                    format_func=lambda x: f"{df_pending[df_pending['uuid']==x]['due_date'].values[0]} | ${df_pending[df_pending['uuid']==x]['amount_due'].values[0]:,.0f} | {df_pending[df_pending['uuid']==x]['description'].values[0]}",
                                                    key="match_ledger")
                        sum_ledger = df_pending[df_pending['uuid'].isin(ledger_sel)]['amount_due'].sum() if ledger_sel else 0
                        st.metric("Total Contable", f"${sum_ledger:,.0f}")
                    else:
                        st.info("No hay gastos pendientes.")
                        sum_ledger = 0

                # Action Bar
                st.markdown("---")
                diff = sum_bank - sum_ledger
                
                if sum_bank > 0 and sum_ledger > 0:
                    if abs(diff) < 50: # Tolerancia de $50 pesos
                        st.success(f"SUCCESS: MATCH CONFIRMADO (Dif: ${diff})")
                        if st.button("🔗 CONCILIAR Y PAGAR", type="primary", use_container_width=True):
                            with engine.begin() as conn:
                                # 1. Update Ledger
                                bank_ids_str = ",".join(map(str, bank_sel))
                                main_date = df_orphan[df_orphan['id'].isin(bank_sel)]['bank_date'].max()
                                
                                for l_uuid in ledger_sel:
                                    conn.execute(text("""
                                        UPDATE expense_ledger 
                                        SET status = 'PAID', 
                                            paid_date = :pd, 
                                            source_bank_id = :bid
                                        WHERE uuid = :lid
                                    """), {"pd": main_date, "bid": bank_ids_str, "lid": l_uuid})
                            st.balloons()
                            st.success("Operación Exitosa: Gastos marcados como PAGADOS y vinculados al Banco.")
                            st.rerun()
                    else:
                        st.error(f"WARN:️ NO CUADRA: Diferencia de ${diff:,.0f}")

            with tabs_bank[1]:
                # Gráfico de barras diarias
                df_daily_bank = df_bank.groupby(df_bank['fecha'].dt.date)['monto'].sum().reset_index()
                fig_bank = px.bar(df_daily_bank, x='fecha', y='monto', 
                                 title="Fluctuación de Caja Diaria ($)",
                                 color='monto', 
                                 color_continuous_scale=['red', 'gray', 'green'],
                                 template="plotly_white")
                st.plotly_chart(fig_bank, use_container_width=True)
                
                st.markdown("#### Detalle de Cartola")
                st.dataframe(df_bank.style.format({"monto": "${:,.0f}", "balance": "${:,.0f}"}), use_container_width=True)
            
    except Exception as e:
        st.error(f"Error cargando dashboard banco: {e}")

# 2. GESTIÓN DE COACHES
elif page == "🏃‍♂️ Gestión de Coaches":
    
    tabs = st.tabs(["💰 Registro de Honorarios", "📊 Historial y Deudas", "👤 Configuración Coaches"])
    
    with tabs[0]:
        df_c = pd.read_sql("SELECT id, name, base_rate, default_sede FROM coaches WHERE active = TRUE", engine)

        # ─────────────────────────────────────────────────────────────
        # 🟩 PANEL DE CONTROL MENSUAL (Filtro Interactivo)
        # Muestra qué meses del año ya tienen honorarios y filtra la grilla
        # ─────────────────────────────────────────────────────────────
        st.markdown("#### 📅 Control de Sueldos por Mes")
        try:
            df_meses = pd.read_sql(
                f"SELECT month, SUM(total_honorarios) as total FROM coach_remunerations WHERE year = {sel_year} GROUP BY month ORDER BY month",
                engine
            )
            meses_con_datos = df_meses['month'].tolist()
            nombres_mes = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
            
            mes_map = {"Todos (Año)": None}
            opciones_meses = ["Todos (Año)"]
            
            for i, nombre in enumerate(nombres_mes, 1):
                if i in meses_con_datos:
                    total_m = df_meses[df_meses['month']==i]['total'].values[0]
                    label = f"{nombre} (${total_m/1000:,.0f}k)"
                else:
                    label = nombre
                opciones_meses.append(label)
                mes_map[label] = i
                
            st.caption("Selecciona un mes para auditar la grilla de honorarios:")
            mes_seleccionado = st.radio("Filtro:", options=opciones_meses, horizontal=True, label_visibility="collapsed")
            mes_filtro_num = mes_map[mes_seleccionado]
            
        except Exception as e_mes:
            st.warning(f"No se pudo cargar el control mensual: {e_mes}")
            mes_filtro_num = None

        st.markdown("---")
        st.markdown("### Registrar Horas Mensuales")
        
        with st.form("honorarios_form", clear_on_submit=True):
            r1c1, r1c2, r1c3 = st.columns(3)
            with r1c1:
                coach_sel = st.selectbox("Coach", options=df_c['name'].tolist())
                coach_id = int(df_c[df_c['name'] == coach_sel]['id'].values[0])
                base_rate = float(df_c[df_c['name'] == coach_sel]['base_rate'].values[0])
            with r1c2:
                mes = st.selectbox("Mes", range(1, 13), index=datetime.now().month - 1,
                                   format_func=lambda x: ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"][x-1])
            with r1c3:
                anio = st.number_input("Año", value=sel_year)
            
            r2c1, r2c2, r2c3 = st.columns(3)
            with r2c1:
                horas = st.number_input("Horas Trabajadas", min_value=0.0, step=0.5)
            with r2c2:
                tarifa = st.number_input("Tarifa por Hora ($)", value=base_rate)
            with r2c3:
                sede_c = st.selectbox("Sede de Imputación", ["Marina", "Campanario", "General"])
            
            total_preview = horas * tarifa
            st.markdown(f"<div style='background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:8px 14px;font-size:1.1rem;font-weight:700;color:#166534;'>💰 Total a registrar: ${total_preview:,.0f}</div>", unsafe_allow_html=True)

            if st.form_submit_button("✅ Calcular y Guardar Honorario", use_container_width=True):
                due_date_str = f"{anio}-{mes:02d}-01"
                if is_period_closed(engine, due_date_str):
                    st.error(f"🚫 ERROR DE CIERRE FISCAL: El periodo {due_date_str[:7]} se encuentra CERRADO.")
                    st.stop()
                total = horas * tarifa
                due_date = f"{anio}-{mes:02d}-01"
                
                with engine.begin() as conn:
                    res = conn.execute(text("""
                        INSERT INTO expense_ledger (description, amount_due, due_date, category_id, sede, status)
                        VALUES (:d, :a, :f, (SELECT id FROM expense_categories WHERE name = 'Sueldos Profesores' LIMIT 1), :s, 'PENDING_PAYMENT')
                        ON CONFLICT DO NOTHING 
                        RETURNING uuid
                    """), {"d": f"Honorarios {coach_sel} - {mes}/{anio}", "a": total, "f": due_date, "s": sede_c})
                    row = res.fetchone()
                    e_uuid = row[0] if row else None
                    conn.execute(text("""
                        INSERT INTO coach_remunerations (coach_id, month, year, hours_worked, hourly_rate, total_honorarios, sede, status, expense_uuid)
                        VALUES (:cid, :m, :y, :h, :r, :t, :s, 'PENDING', :euuid)
                        ON CONFLICT (coach_id, month, year, sede) DO UPDATE SET 
                            hours_worked = EXCLUDED.hours_worked, 
                            total_honorarios = EXCLUDED.total_honorarios,
                            hourly_rate = EXCLUDED.hourly_rate,
                            expense_uuid = COALESCE(coach_remunerations.expense_uuid, EXCLUDED.expense_uuid)
                    """), {"cid": coach_id, "m": mes, "y": anio, "h": horas, "r": tarifa, "t": total, "s": sede_c, "euuid": e_uuid})
                    if not row:
                        conn.execute(text("""
                            UPDATE expense_ledger SET amount_due = :a 
                            WHERE uuid = (SELECT expense_uuid FROM coach_remunerations WHERE coach_id = :cid AND month = :m AND year = :y AND sede = :s)
                        """), {"a": total, "cid": coach_id, "m": mes, "y": anio, "s": sede_c})
                st.success(f"✅ Honorario registrado para **{coach_sel}**: **${total:,.0f}** — Mes {mes}/{anio}")
                st.rerun()

        # ─────────────────────────────────────────────────────────────
        # 🟥 GRILLA EN VIVO (círculo rojo en la foto)
        # Muestra en tiempo real los honorarios registrados este año
        # ─────────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📋 Honorarios Registrados — Vista Rápida")
        try:
            where_clause = f"r.year = {sel_year}"
            if mes_filtro_num is not None:
                where_clause += f" AND r.month = {mes_filtro_num}"
                
            df_live = pd.read_sql(f"""
                SELECT 
                    c.name as Coach,
                    TO_CHAR(TO_DATE(r.month::text, 'MM'), 'Month') as Mes,
                    r.year as Año,
                    r.hours_worked as Horas,
                    r.hourly_rate as "Tarifa/Hora",
                    r.total_honorarios as Total,
                    r.sede as Sede,
                    r.status as Estado
                FROM coach_remunerations r
                JOIN coaches c ON r.coach_id = c.id
                WHERE {where_clause}
                ORDER BY r.month DESC, c.name ASC
            """, engine)
            if df_live.empty:
                st.info("Sin registros este año. Ingresa el primer honorario con el formulario de arriba.")
            else:
                # KPI row
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Total Comprometido", f"${df_live['Total'].sum():,.0f}")
                k2.metric("N° de Registros", len(df_live))
                k3.metric("Coaches Activos", df_live['Coach'].nunique())
                pendientes = len(df_live[df_live['Estado'] == 'PENDING'])
                k4.metric("Pendientes de Pago", pendientes, delta=f"-{pendientes}" if pendientes > 0 else None, delta_color="inverse")

                # Color status
                def style_status(v):
                    if v == 'PENDING': return 'background-color:#fef9c3;color:#713f12;font-weight:600'
                    if v == 'PAID': return 'background-color:#dcfce7;color:#166534;font-weight:600'
                    return ''
                df_live['Total'] = df_live['Total'].apply(lambda x: f"${x:,.0f}")
                df_live['Tarifa/Hora'] = df_live['Tarifa/Hora'].apply(lambda x: f"${x:,.0f}")
                st.dataframe(
                    df_live.style.applymap(style_status, subset=['Estado']),
                    use_container_width=True, hide_index=True
                )
        except Exception as e_grid:
            st.error(f"Error cargando grilla: {e_grid}")

    with tabs[1]:
        st.markdown("### Estado de Pagos y Boletas")
        query_rem = f"""
            SELECT r.id, c.name as coach, r.month as mes, r.year as anio, r.hours_worked as horas, 
                   r.total_honorarios as total, r.status, r.sii_folio as folio, r.sede
            FROM coach_remunerations r
            JOIN coaches c ON r.coach_id = c.id
            WHERE r.year = {sel_year}
            ORDER BY r.month DESC, c.name ASC
        """
        df_rem = pd.read_sql(query_rem, engine)
        st.dataframe(df_rem, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📝 Modificar o Eliminar Registro")
        if not df_rem.empty:
            col_acc1, col_acc2, col_acc3 = st.columns([2, 1, 1])
            with col_acc1:
                target_rem = st.selectbox("Seleccionar Registro", options=df_rem['id'].tolist(), 
                                         format_func=lambda x: f"ID {x} - {df_rem[df_rem['id']==x]['coach'].values[0]} ({df_rem[df_rem['id']==x]['mes'].values[0]}/{df_rem[df_rem['id']==x]['anio'].values[0]})")
            curr_row = df_rem[df_rem['id'] == target_rem].iloc[0]
            
            # CHECK: ¿El registro ya está conciliado con el banco?
            is_reconciled = False
            # Consultamos el ledger para ver si tiene source_bank_id
            try:
                ledger_check = pd.read_sql(f"SELECT source_bank_id, status FROM expense_ledger WHERE uuid = '{curr_row['expense_uuid']}'", engine)
                if not ledger_check.empty:
                    if ledger_check.iloc[0]['source_bank_id'] or "PAID" in ledger_check.iloc[0]['status']:
                        is_reconciled = True
            except: pass

            if is_reconciled:
                 st.markdown("""
                    <div style='background-color: #fee2e2; border: 1px solid #ef4444; color: #991b1b; padding: 10px; border-radius: 8px;'>
                        🚨 <b>REGISTRO BLOQUEADO:</b> Este honorario ya fue pagado y conciliado con el Banco. <br>
                        Para modificarlo, un Administrador debe anular la conciliación primero.
                    </div>
                """, unsafe_allow_html=True)
                 st.text_input("Horas (Bloqueado)", value=float(curr_row['horas']), disabled=True)
                 st.text_input("Tarifa (Bloqueado)", value=float(curr_row['total']/curr_row['horas']) if curr_row['horas'] > 0 else 0.0, disabled=True)
                 st.text_input("Estado (Bloqueado)", value=curr_row['status'], disabled=True)
            else:
                with col_acc2:
                    edit_horas = st.number_input("Corregir Horas", value=float(curr_row['horas']), step=0.5)
                    edit_tarifa = st.number_input("Corregir Tarifa ($)", value=float(curr_row['total']/curr_row['horas']) if curr_row['horas'] > 0 else 0.0)
                
                with col_acc3:
                    edit_status = st.selectbox("Estado", ["PENDING", "INVOICED", "PAID"], 
                                             index=["PENDING", "INVOICED", "PAID"].index(curr_row['status']))
                    edit_folio = st.number_input("Folio SII", value=int(curr_row['folio']) if not pd.isna(curr_row['folio']) else 0)

                c_btn1, c_btn2, _ = st.columns([1, 1, 2])
                if c_btn1.button("💾 Guardar Cambios"):
                    due_date_str = f"{curr_row['anio']}-{curr_row['mes']:02d}-01"
                    if is_period_closed(engine, due_date_str):
                        st.error("🚫 El periodo está cerrado.")
                        st.stop()
                    new_total = edit_horas * edit_tarifa
                    with engine.begin() as conn:
                        # 1. Actualizar el registro administrativo
                        conn.execute(text("""
                            UPDATE coach_remunerations 
                            SET hours_worked = :h, hourly_rate = :r, total_honorarios = :t, status = :s, sii_folio = :f 
                            WHERE id = :id
                        """), {"h": edit_horas, "r": edit_tarifa, "t": new_total, "s": edit_status, "f": edit_folio, "id": target_rem})
                        
                        # 2. Sincronizar con el Ledger de Egresos para que el P&L sea exacto
                        conn.execute(text("""
                            UPDATE expense_ledger 
                            SET amount_due = :a, source_sii_folio = :f, status = :st
                            WHERE uuid = (SELECT expense_uuid FROM coach_remunerations WHERE id = :id)
                        """), {
                            "a": new_total, 
                            "f": edit_folio if edit_folio > 0 else None, 
                            "st": 'PAID_VERIFIED' if edit_status == 'PAID' else 'PENDING_PAYMENT',
                            "id": target_rem
                        })
                    st.success("Registro y Dashboard actualizados correctamente.")
                    st.rerun()
                
                if c_btn2.button("🗑️ Eliminar Registro", type="secondary"):
                    due_date_str = f"{curr_row['anio']}-{curr_row['mes']:02d}-01"
                    if is_period_closed(engine, due_date_str):
                        st.error("🚫 El periodo está cerrado.")
                        st.stop()
                    with engine.begin() as conn:
                        # PASO 1: Obtener el UUID del expense_ledger ANTES de eliminar
                        result = conn.execute(text("SELECT expense_uuid FROM coach_remunerations WHERE id = :id"), {"id": target_rem})
                        row = result.fetchone()
                        expense_uuid = row[0] if row else None
                        
                        # PASO 2: Eliminar el hijo (coach_remunerations) primero
                        conn.execute(text("DELETE FROM coach_remunerations WHERE id = :id"), {"id": target_rem})
                        
                        # PASO 3: Eliminar el padre (expense_ledger) usando el UUID capturado
                        if expense_uuid:
                            conn.execute(text("DELETE FROM expense_ledger WHERE uuid = :uuid"), {"uuid": expense_uuid})
                        
                    st.warning("Registro eliminado de todo el sistema.")
                    st.rerun()
        else:
            st.info("No hay registros para modificar.")

    with tabs[2]:
        st.markdown("### Maestro de Entrenadores")
        st.dataframe(pd.read_sql("SELECT name, rut, base_rate as tarifa_base, default_sede as sede_base, active FROM coaches", engine), use_container_width=True)
        
        with st.expander("📝 Actualizar Perfil de Coach"):
            df_edit = pd.read_sql("SELECT name, id FROM coaches ORDER BY name", engine)
            coach_to_edit = st.selectbox("Seleccionar Coach para Modificar", options=df_edit['name'].tolist())
            c_id = int(df_edit[df_edit['name'] == coach_to_edit]['id'].values[0])
            
            # Fetch current data
            coach_data = pd.read_sql(f"SELECT base_rate, default_sede, active FROM coaches WHERE id = {c_id}", engine).iloc[0]
            
            with st.form("edit_coach"):
                new_rate = st.number_input("Nueva Tarifa Base ($)", value=int(coach_data['base_rate']))
                new_sede = st.selectbox("Nueva Sede Base", ["Marina", "Campanario", "General"], index=["Marina", "Campanario", "General"].index(coach_data['default_sede']))
                is_active = st.checkbox("¿Coach Activo?", value=bool(coach_data['active']))
                
                if st.form_submit_button("Actualizar Coach"):
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE coaches SET base_rate = :t, default_sede = :s, active = :a WHERE id = :id"),
                                     {"t": new_rate, "s": new_sede, "a": is_active, "id": c_id})
                    st.success(f"Perfil de {coach_to_edit} actualizado. El nuevo valor hora es ${new_rate:,.0f}")
                    st.rerun()

        with st.expander("➕ Agregar Nuevo Coach"):
            with st.form("new_coach"):
                nc_name = st.text_input("Nombre Completo")
                nc_rut = st.text_input("RUT")
                nc_rate = st.number_input("Tarifa Base ($)", value=7000)
                nc_sede = st.selectbox("Sede Base", ["Marina", "Campanario", "General"])
                if st.form_submit_button("Guardar Coach"):
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO coaches (name, rut, base_rate, default_sede) VALUES (:n, :r, :t, :s)"),
                                     {"n": nc_name, "r": nc_rut, "t": nc_rate, "s": nc_sede})
                    st.success("Coach agregado.")
                    st.rerun()

# 2.5 ALUMNOS INACTIVOS
elif page == "📉 Alumnos Inactivos":
    show_help("Fuga de Clientes", """
        **Análisis de Retención**
        - Monitorea los usuarios que han dejado de pagar.
        - **Ingresos Perdidos**: Estimación basada en el plan que tenían.
        - **Lista de Recuperación**: Prioriza contactar a quienes se fueron recientemente.
    """)
    
    st.markdown("### 📊 KPIs de Fuga")
    try:
        # Strict year filtering for inactive students
        kpi_df = pd.read_sql(f"SELECT * FROM view_inactive_users_stats WHERE month_year LIKE '{sel_year}%'", engine)
        if not kpi_df.empty:
            total_loss = kpi_df['estimated_revenue_loss'].sum()
            total_users = kpi_df['total_leaked_users'].sum()
            # Handle empty data case safely
            top_churn_plan = kpi_df['most_common_plan_churned'].iloc[0] if len(kpi_df) > 0 else "N/A"

            k1, k2, k3 = st.columns(3)
            k1.metric("Ingresos Perdidos (Est.)", f"${total_loss:,.0f}", delta="Oportunidad Mensual", delta_color="inverse")
            k2.metric("Usuarios Inactivos", f"{total_users}", delta="Total Detectado")
            k3.metric("Plan Crítico", top_churn_plan, help="Plan con mayor tasa de abandono")
            
            st.markdown("---")
            
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("Tendencia de Fuga")
                fig_bar = px.bar(kpi_df, x='month_year', y='total_leaked_users', 
                                 title="Usuarios por Mes", color='total_leaked_users', color_continuous_scale='Reds')
                st.plotly_chart(fig_bar, use_container_width=True)
            with g2:
                st.subheader("Impacto Financiero")
                fig_line = px.line(kpi_df, x='month_year', y='estimated_revenue_loss', 
                                   title="Pérdida Estimada ($)", markers=True)
                fig_line.update_traces(line_color='#ef4444')
                st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No hay datos de inactividad cargados aún.")

        st.markdown("### 📋 Lista de Recuperación (Acción Inmediata)")
        detail_df = pd.read_sql(f"SELECT * FROM view_recuperation_list WHERE EXTRACT(YEAR FROM last_payment_date) = {sel_year}", engine)
        st.dataframe(
            detail_df.style.background_gradient(subset=['days_inactive'], cmap='Oranges'),
            use_container_width=True
        )
        
        st.markdown("---")
        st.subheader("SUCCESS: Alumnos Recuperados (Cruce con Activos)")
        st.info("Estos alumnos aparecían como inactivos, pero figuran en la lista de activos actual.")
        
        rec_df = pd.read_sql(f"SELECT * FROM view_recovered_users WHERE EXTRACT(YEAR FROM reactivation_date) = {sel_year}", engine)
        if not rec_df.empty:
            st.dataframe(
                rec_df.style.background_gradient(subset=['recovery_days_gap'], cmap='Greens'),
                use_container_width=True
            )
            st.metric("Total Recuperados", len(rec_df))
        else:
            st.warning("No se encontraron coincidencias entre la lista de inactivos y la de activos.")

    except Exception as e:
        st.error(f"Error cargando módulo: {e}")

# 3. ALERTAS
elif page == "🚨 Alertas & Control":
    show_help("Centro de Alertas", """
        Este panel monitorea la salud administrativa de tu box en tiempo real.
        - **Certificado Digital**: Fecha de vencimiento para facturación SII (Sincronizado vía API).
        - **Folios**: Cantidad de boletas disponibles en Lioren (Boletas Exentas 41).
        - **Cuentas Críticas**: Gastos marcados como prioritarios (Arriendo, Luz) que vencen pronto.
    """)
    st.markdown("<h1>🚨 Centro de Control & Alertas</h1>", unsafe_allow_html=True)
    
    # Intentar obtener datos reales de Lioren
    with st.spinner("Conectando con la API de Lioren para actualizar folios y certificado..."):
        lioren_data = get_lioren_realtime_data()
    
    # Cargar valores históricos por si falla la API o no hay internet
    df_set = pd.read_sql("SELECT key, value FROM system_settings", engine)
    settings = {r['key']: r['value'] for _, r in df_set.iterrows()}
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if lioren_data and lioren_data["cert_vence"]:
            vence_str = lioren_data["cert_vence"]
            # Guardar en caché persistente en DB
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO system_settings (key, value, label) VALUES ('cert_digital_vence', :v, 'Certificado Vence') ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"), {"v": vence_str})
        else:
            vence_str = settings.get('cert_digital_vence', '2026-01-01')
            
        vence = datetime.strptime(vence_str, '%Y-%m-%d')
        days = (vence - datetime.now()).days
        
        # Color dinámico si vence pronto
        color_flag = "normal" if days > 30 else "inverse"
        st.metric("Certificado Digital", vence.strftime('%d/%b/%Y'), delta=f"{days} días restantes", delta_color=color_flag)
        
    with col2:
        if lioren_data:
            actual = lioren_data["folios_libres"]
            # Guardar en caché persistente en DB
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO system_settings (key, value, label) VALUES ('folios_actuales', :v, 'Folios Disponibles') ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"), {"v": str(actual)})
            api_status = "Sincronizado vía API"
            api_color = "normal"
        else:
            actual = int(settings.get('folios_actuales', 0))
            api_status = "Usando caché histórica"
            api_color = "inverse"
            
        st.metric("Folios SII (Boletas Exentas)", f"{actual} libres", delta=api_status, delta_color=api_color)
        
    with col3:
        query_pend = "SELECT uuid FROM expense_ledger WHERE is_critical = TRUE AND status != 'PAID_VERIFIED'"
        pend = len(pd.read_sql(query_pend, engine))
        st.metric("Cuentas Críticas", f"{pend} Facturas", delta="PENDIENTE PAGO", delta_color="inverse")

# 4. REPORTES
elif page == "📑 Reportes Legales":
    show_help("Reportes Legales & Contables", """
        Genera los libros necesarios para tu contador o para control interno.
        - **Libro de Compras/Ventas**: Detalle legal sincronizado con Lioren.
        - **Libro Mayor**: Agrupación por cuenta contable (Sueldos, Insumos, etc.).
    """)
    # Eliminamos el H1 redundante ya que el Header Dinámico lo cubre
    rt = st.selectbox("Formato de Reporte", ["Libro de Compras", "Libro de Ventas", "Libro de Honorarios", "Cuentas Contables Consolidado", "Detalle Movimientos (Libro Mayor)"])
    
    if rt == "Libro de Compras":
        df = pd.read_sql(f"SELECT due_date as fecha, source_sii_folio as folio, description as proveedor, amount_due as total, sede FROM expense_ledger WHERE EXTRACT(YEAR FROM due_date) = {sel_year} ORDER BY fecha DESC", engine)
    elif rt == "Libro de Ventas":
        df = pd.read_sql(f"SELECT folio, emission_date as fecha, total_amount as total FROM raw_lioren_sales WHERE EXTRACT(YEAR FROM emission_date) = {sel_year} ORDER BY emission_date DESC", engine)
    elif rt == "Libro de Honorarios":
        df = pd.read_sql(f"""
            SELECT c.name as coach, r.month, r.year, r.hours_worked as horas, r.total_honorarios as monto, r.status, r.sede
            FROM coach_remunerations r JOIN coaches c ON r.coach_id = c.id 
            WHERE r.year = {sel_year} ORDER BY r.month DESC
        """, engine)
    elif rt == "Cuentas Contables Consolidado":
        df = pd.read_sql(f"""
            SELECT c.name as cuenta, COALESCE(SUM(e.amount_due), 0) as total 
            FROM expense_categories c 
            LEFT JOIN expense_ledger e ON c.id = e.category_id AND EXTRACT(YEAR FROM e.due_date) = {sel_year}
            GROUP BY c.name ORDER BY total DESC
        """, engine)
        st.info("💡 Para ver qué facturas componen estos montos, selecciona el reporte: **Detalle Movimientos (Libro Mayor)**")
    else:
        # DETALLE MOVIMIENTOS (LIBRO MAYOR)
        cat_list = pd.read_sql("SELECT name FROM expense_categories ORDER BY name", engine)['name'].tolist()
        sel_cat = st.selectbox("Seleccione Cuenta Contable a Detallar", cat_list)
        
        df = pd.read_sql(f"""
            SELECT e.due_date as fecha, e.description as detalle, e.source_sii_folio as folio, 
                   e.amount_due as bruto, e.status, e.sede
            FROM expense_ledger e
            JOIN expense_categories c ON e.category_id = c.id
            WHERE c.name = '{sel_cat}' AND EXTRACT(YEAR FROM e.due_date) = {sel_year}
            ORDER BY e.due_date DESC
        """, engine)
        
        st.markdown(f"### Detalle de: {sel_cat}")
        
    st.dataframe(df, use_container_width=True)
    st.download_button(f"💾 Exportar {rt} (CSV)", df.to_csv(index=False), f"reporte_{rt.lower().replace(' ', '_')}.csv")

# 5. CAJA & BANCO
elif page == "🏦 Caja & Banco":
    show_help("Conciliación Bancaria", """
        **¿Cómo conciliar?**
        1. Selecciona el movimiento del banco (salida de dinero).
        2. Selecciona el o los gastos que cubren ese monto.
        
        *Ejemplo: Un cargo de $343.000 del banco puede cubrir 2 honorarios de $126k y $217k. El sistema sumará ambos y te dará el OK.*
    """)
    tabs_bank = st.tabs(["🏦 Movimientos de Banco", "🤝 Conciliación Manual"])
    
    with tabs_bank[0]:
        st.markdown("### Movimientos Bancarios sin Respaldar")
        df_h = pd.read_sql(f"SELECT bank_date as fecha, description, amount as monto FROM raw_bank WHERE amount < 0 AND EXTRACT(YEAR FROM bank_date) = {sel_year} AND id::text NOT IN (SELECT source_bank_id FROM expense_ledger WHERE source_bank_id IS NOT NULL) ORDER BY bank_date DESC", engine)
        st.dataframe(df_h, use_container_width=True)
        st.download_button("💾 Descargar Detalle de Huérfanos (CSV)", df_h.to_csv(index=False), "banco_huerfanos.csv")
        
    with tabs_bank[1]:
        st.subheader("🛠️ Emparejamiento Manual (SAP Style)")
        st.info("Utiliza esta herramienta para 'cruzar' un cargo del banco con uno o varios gastos registrados. Esto 'limpia' tu saldo y valida el egreso.")
        
        # 1. Movimientos de Banco Huérfanos
        query_orphan = f"SELECT id, bank_date, description, amount FROM raw_bank WHERE amount < 0 AND EXTRACT(YEAR FROM bank_date) = {sel_year} AND id::text NOT IN (SELECT source_bank_id FROM expense_ledger WHERE source_bank_id IS NOT NULL) ORDER BY bank_date DESC"
        df_orphan = pd.read_sql(query_orphan, engine)
        
        if not df_orphan.empty:
            col_bk, col_ld = st.columns(2)
            
            with col_bk:
                st.markdown("**1. Seleccione Cargo(s) del Banco**")
                bank_matches = st.multiselect("Movimientos Bancarios (Puede elegir varios)", 
                                              options=df_orphan['id'].tolist(), 
                                              format_func=lambda x: f"{df_orphan[df_orphan['id']==x]['bank_date'].values[0]} | {df_orphan[df_orphan['id']==x]['description'].values[0][:25]}.. | ${-df_orphan[df_orphan['id']==x]['amount'].values[0]:,.0f}")
                
                total_bank = -df_orphan[df_orphan['id'].isin(bank_matches)]['amount'].sum()
                st.write(f"**Total Banco: ${total_bank:,.0f}**")
            
            with col_ld:
                st.markdown("**2. Seleccione Gasto(s) del Ledger**")
                df_pending = pd.read_sql(f"SELECT uuid, due_date, description, amount_due, sede FROM expense_ledger WHERE status = 'PENDING_PAYMENT' AND EXTRACT(YEAR FROM due_date) = {sel_year} ORDER BY due_date DESC", engine)
                
                if not df_pending.empty:
                    ledger_matches = st.multiselect("Gastos Pendientes", options=df_pending['uuid'].tolist(), 
                                                   format_func=lambda x: f"{df_pending[df_pending['uuid']==x]['due_date'].values[0]} | {df_pending[df_pending['uuid']==x]['description'].values[0][:25]}.. | ${df_pending[df_pending['uuid']==x]['amount_due'].values[0]:,.0f}")
                    
                    total_ledger = df_pending[df_pending['uuid'].isin(ledger_matches)]['amount_due'].sum()
                    st.write(f"**Total Ledger: ${total_ledger:,.0f}**")
                else:
                    total_ledger = 0
                    st.warning("No hay gastos pendientes.")

            # Área de Cuadre Central
            st.markdown("---")
            diff = total_bank - total_ledger
            c_res1, c_res2 = st.columns(2)
            
            with c_res1:
                if total_bank > 0 and total_ledger > 0:
                    if abs(diff) < 1:
                        st.success(f"SUCCESS: CUADRE PERFECTO: ${total_bank:,.0f}")
                    else:
                        st.error(f"WARN:️ DIFERENCIA: ${diff:,.0f}")
            
            with c_res2:
                if st.button("🔗 VINCULAR MOVIMIENTOS SELECCIONADOS", use_container_width=True):
                    if total_bank > 0 and total_ledger > 0 and abs(diff) < 1:
                        with engine.begin() as conn:
                            # Concatenamos los IDs bancarios para trazabilidad
                            bank_ids_str = ",".join(map(str, bank_matches))
                            main_date = df_orphan[df_orphan['id'].isin(bank_matches)]['bank_date'].max()
                            
                            for l_uuid in ledger_matches:
                                conn.execute(text("""
                                    UPDATE expense_ledger 
                                    SET status = 'PAID_VERIFIED', 
                                        paid_date = :pd, 
                                        amount_paid = amount_due,
                                        source_bank_id = :bid
                                    WHERE uuid = :lid
                                """), {"pd": main_date, "bid": bank_ids_str, "lid": l_uuid})
                        st.success("¡Conciliación M:N exitosa! El saldo ha sido saneado.")
                        st.rerun()
                    elif abs(diff) >= 1:
                        st.error("No se puede vincular: El total del banco debe coincidir con el total del ledger.")
        else:
            st.success("SUCCESS: No quedan movimientos bancarios por conciliar.")

# 6. REGISTRAR EGRESOS (MODO SAP FB60)
elif page == "💸 Registrar Egresos":
    st.markdown("""
        <style>
        .sap-header { background-color: #f1f5f9; padding: 15px; border-radius: 10px; border-left: 5px solid #3b82f6; margin-bottom: 20px; }
        .sap-section { border: 1px solid #e2e8f0; padding: 20px; border-radius: 10px; background: white; margin-bottom: 15px; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1>📁 Módulo de Gestión de Egresos</h1>", unsafe_allow_html=True)
    
    tab_control, tab_registro = st.tabs(["📋 Control de Egresos por Mes", "➕ Registrar Documento (FB60)"])
    
    with tab_control:
        st.markdown("### 📅 Libro Auxiliar de Compras & Flujo de Caja")
        st.caption("Filtra tus egresos mes a mes, audita el estado de cuadratura con la cartola del banco y detecta pendientes.")
        
        # Selector de período
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            mes_sel = st.selectbox("Seleccionar Mes de Consulta", range(1, 13), index=datetime.now().month - 1,
                                   format_func=lambda x: ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"][x-1])
        with col_m2:
            anio_sel = st.number_input("Seleccionar Año de Consulta", value=datetime.now().year, step=1)
            
        # Cargar egresos del período seleccionado
        query_month = text("""
            SELECT 
                e.uuid, 
                e.due_date as "Fecha", 
                COALESCE(s.name, e.description) as "Proveedor / Detalle",
                ec.name as "Categoría",
                e.source_sii_folio as "Folio", 
                e.amount_due as "Monto", 
                e.sede as "Sede", 
                e.status as "Estado"
            FROM expense_ledger e
            LEFT JOIN suppliers s ON e.supplier_id = s.id
            LEFT JOIN expense_categories ec ON e.category_id = ec.id
            WHERE EXTRACT(MONTH FROM e.due_date) = :month 
              AND EXTRACT(YEAR FROM e.due_date) = :year
            ORDER BY e.due_date DESC, e.created_at DESC
        """)
        
        with engine.connect() as conn:
            df_month = pd.read_sql(query_month, conn, params={"month": mes_sel, "year": anio_sel})
            
        if df_month.empty:
            months_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            st.info(f"ℹ️ No hay egresos contables registrados para {months_names[mes_sel-1]} de {anio_sel}.")
        else:
            # Calcular KPIs de Cuadratura Operativa
            total_egresos = df_month["Monto"].sum()
            total_conciliado = df_month[df_month["Estado"].isin(["PAID_VERIFIED", "PAID"])]["Monto"].sum()
            total_pendiente = total_egresos - total_conciliado
            
            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Total Egresos Registrados", f"${total_egresos:,.0f}")
            with k2:
                pct = (total_conciliado / total_egresos * 100) if total_egresos > 0 else 0
                st.metric("Total Cuadrado con Banco (BCI)", f"${total_conciliado:,.0f}", delta=f"{pct:.1f}% conciliado")
            with k3:
                st.metric("Pendiente por Cuadrar / Pagar", f"${total_pendiente:,.0f}", delta=f"-${total_pendiente:,.0f}" if total_pendiente > 0 else "✓ Todo al día", delta_color="inverse" if total_pendiente > 0 else "normal")
                
            # Preparar visualización
            df_disp = df_month.copy()
            df_disp["Fecha"] = pd.to_datetime(df_disp["Fecha"]).dt.strftime("%d/%m/%Y")
            df_disp["Monto"] = df_disp["Monto"].apply(lambda x: f"${x:,.0f}")
            df_disp["Folio"] = df_disp["Folio"].fillna("—")
            
            # Generar columnas de estado claras
            df_disp["Cuadratura"] = df_disp["Estado"].apply(lambda x: "✅ Conciliado (Flujo Cerrado)" if x in ["PAID_VERIFIED", "PAID"] else "❌ Pendiente de Match Bancario")
            df_disp["Estado"] = df_disp["Estado"].apply(lambda x: "CONCILIADO" if x in ["PAID_VERIFIED", "PAID"] else "PENDIENTE")
            
            # Formato de color para la tabla
            def color_cuadratura(val):
                if val == "CONCILIADO":
                    return "background-color:#dcfce7; color:#166534; font-weight:bold"
                return "background-color:#fee2e2; color:#991b1b; font-weight:bold"
                
            cols_show = ["Fecha", "Proveedor / Detalle", "Categoría", "Folio", "Monto", "Sede", "Cuadratura", "Estado"]
            styled_table = df_disp[cols_show].style.applymap(color_cuadratura, subset=["Estado"])
            
            st.dataframe(styled_table, use_container_width=True, height=450)
            st.info("💡 **Tip Operativo:** Para cuadrar los egresos marcados con '❌ Pendiente', dirígete al menú de **Cuadratura Bancaria** y utiliza el MatchMaker para enlazarlos con el cargo bancario real en 1 clic.")
            
    with tab_registro:
        st.markdown("<h1>📁 Registro de Documentos de Compra (FB60)</h1>", unsafe_allow_html=True)
        
        # 1. Cargar Datos Maestros
        with engine.connect() as conn:
            suppliers_df = pd.read_sql(text("SELECT id, rut, name FROM suppliers ORDER BY name"), conn)
            categories_df = pd.read_sql(text("SELECT id, name FROM expense_categories ORDER BY name"), conn)
    
        # UI de Cabecera
        st.markdown('<div class="sap-header"><b>DATOS DE CABECERA:</b> Información general del documento legal.</div>', unsafe_allow_html=True)
        
        # Session state for dynamic calc
        if 'exp_amount' not in st.session_state: st.session_state.exp_amount = 0.0
    
        with st.container():
            c1, c2, c3 = st.columns([2,2,1])
            with c1:
                doc_type = st.selectbox("Tipo de Documento", 
                    ["Factura Electrónica (IVA 19%)", "Boleta de Honorarios (Ret. 13.75%)", "Boleta / Voucher / Otros (Exento)"])
                doc_date = st.date_input("Fecha Contable / Emisión", datetime.now())
            with c2:
                # Selector de Proveedor con opción de crear uno rápido
                supplier_names = suppliers_df['name'].tolist()
                sel_supp = st.selectbox("Proveedor (Dato Maestro)", ["-- SELECCIONE O CREE NUEVO --"] + supplier_names)
                doc_folio = st.number_input("Folio Documento (N°)", min_value=1, step=1, value=1)
            with c3:
                total_amount = st.number_input("Monto Total ($)", min_value=0, step=100)
    
        st.markdown('<div class="sap-header"><b>POSICIÓN Y COSTOS:</b> Distribución contable y centros de costo.</div>', unsafe_allow_html=True)
        
        with st.container():
            d1, d2, d3 = st.columns(3)
            with d1:
                sel_cat = st.selectbox("Cuenta Contable (Categoría)", categories_df['name'].tolist())
            with d2:
                sel_sede = st.selectbox("Centro de Costo (Sede)", ["Marina", "Campanario", "General"])
            with d3:
                is_critical = st.toggle("Gasto Crítico (Bloqueante)", value=False)
    
        # Lógica de Impuestos Automática
        neto, impuesto = 0, 0
        if "Factura" in doc_type:
            neto = round(total_amount / 1.19)
            impuesto = total_amount - neto
            tax_label = "IVA (19%)"
        elif "Honorarios" in doc_type:
            # En Chile: Bruto - Retención = Liquido. Aquí asumimos total_amount es el BRUTO.
            impuesto = round(total_amount * 0.1375)
            neto = total_amount - impuesto
            tax_label = "Retención (13.75%)"
        else:
            neto = total_amount
            impuesto = 0
            tax_label = "N/A (Exento)"
    
        # Resumen de validación
        st.markdown("---")
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("Neto / Imponible", f"${neto:,.0f}")
        res_col2.metric(tax_label, f"${impuesto:,.0f}")
        res_col3.metric("Total Documento", f"${total_amount:,.0f}")
    
        if sel_supp == "-- SELECCIONE O CREE NUEVO --":
            with st.expander("➕ ALTA RÁPIDA DE PROVEEDOR"):
                with st.form("quick_supp"):
                    q_name = st.text_input("Razón Social / Nombre")
                    q_rut = st.text_input("RUT (ej: 12.345.678-9)")
                    q_cat = st.selectbox("Categoría Predeterminada", categories_df['name'].tolist())
                    if st.form_submit_button("💾 Crear y Vincular"):
                        if q_name and q_rut:
                            try:
                                # Obtener cat id
                                qc_id = int(categories_df[categories_df['name'] == q_cat]['id'].iloc[0])
                                with engine.begin() as conn:
                                    conn.execute(text("INSERT INTO suppliers (rut, name, category_id) VALUES (:r, :n, :c)"), 
                                                 {"r": q_rut, "n": q_name, "c": qc_id})
                                st.success(f"Proveedor {q_name} creado. Por favor selecciona de la lista.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning("Nombre y RUT son obligatorios.")
    
        if st.button("🏁 CONTABILIZAR DOCUMENTO (POST)", type="primary", use_container_width=True):
            if is_period_closed(engine, doc_date):
                st.error(f"🚫 ERROR DE CIERRE FISCAL: El periodo {doc_date.strftime('%Y-%m')} se encuentra CERRADO. No se pueden contabilizar documentos.")
            elif total_amount <= 0:
                st.error("El monto debe ser mayor a cero.")
            elif sel_supp == "-- SELECCIONE O CREE NUEVO --":
                st.warning("Debe seleccionar un proveedor válido.")
            else:
                try:
                    # Obtener ID del proveedor
                    supp_id = int(suppliers_df[suppliers_df['name'] == sel_supp]['id'].iloc[0])
                    cat_id = int(categories_df[categories_df['name'] == sel_cat]['id'].iloc[0])
                    
                    with engine.begin() as conn:
                        # Verificar duplicado
                        dup = conn.execute(text("SELECT uuid FROM expense_ledger WHERE supplier_id = :s AND source_sii_folio = :f"), 
                                         {"s": supp_id, "f": doc_folio}).fetchone()
                        
                        if dup:
                            st.error(f"WARN:️ Documento Duplicado: El folio {doc_folio} ya existe para este proveedor.")
                        else:
                            conn.execute(text("""
                                INSERT INTO expense_ledger 
                                (description, supplier_id, category_id, amount_due, net_amount, iva_amount, due_date, status, is_critical, sede, source_sii_folio) 
                                VALUES (:d, :sid, :cid, :a, :n, :i, :f, 'PENDING_PAYMENT', :crit, :s, :fol)
                            """), 
                            {
                                "d": f"{doc_type} {doc_folio} - {sel_cat}",
                                "sid": supp_id,
                                "cid": cat_id,
                                "a": total_amount,
                                "n": neto,
                                "i": impuesto,
                                "f": doc_date,
                                "crit": is_critical,
                                "s": sel_sede,
                                "fol": doc_folio
                            })
                            st.success(f"SUCCESS: Documento {doc_folio} contabilizado exitosamente para {sel_supp}.")
                            st.balloons()
                            st.rerun()
                except Exception as ex:
                    st.error(f"Error al contabilizar: {ex}")
    
        st.markdown("---")
        st.subheader("📋 Egresos Recientes (Audit View)")
        # Improved Query with Join for Supplier Name
        query_recent = """
            SELECT 
                e.uuid, 
                e.due_date as fecha, 
                COALESCE(s.name, e.description) as proveedor,
                e.source_sii_folio as folio, 
                e.amount_due as monto, 
                e.sede, 
                e.status 
            FROM expense_ledger e
            LEFT JOIN suppliers s ON e.supplier_id = s.id
            ORDER BY e.created_at DESC 
            LIMIT 15
        """
        df_recent = pd.read_sql(query_recent, engine)
        st.dataframe(df_recent, use_container_width=True)
    
        if user_role == "Admin":
            with st.expander("🗑️ Eliminar Gasto (Admin)"):
                st.warning("WARN:️ Esta acción es irreversible. Eliminará el gasto del Dashboard and cualquier vínculo con Coaches.")
            
            # 1. Traer lista de egresos recientes para el selector (Zero Copy)
            df_to_del = pd.read_sql("""
                SELECT uuid, due_date, description, amount_due, status 
                FROM expense_ledger 
                ORDER BY created_at DESC LIMIT 50
            """, engine)
    
            if not df_to_del.empty:
                # Formatear opciones para que sean legibles
                options = df_to_del['uuid'].tolist()
                def format_exp(uid):
                    row = df_to_del[df_to_del['uuid'] == uid].iloc[0]
                    status_icon = "🟢" if "PAID" in row['status'] else "🔴"
                    return f"{status_icon} {row['due_date']} | {row['description'][:30]} | ${row['amount_due']:,.0f}"
                
                target_uid = st.selectbox("Seleccione el Gasto a Eliminar", options=options, format_func=format_exp)
                
                # Verificar estado antes de mostrar botón
                target_status = df_to_del[df_to_del['uuid'] == target_uid]['status'].values[0]
                is_locked = "PAID" in target_status
                
                if is_locked:
                    st.error("⛔ ESTE GASTO ESTÁ CONCILIADO (PAGADO).")
                    st.markdown(f"Para mantener la integridad contable, no puede eliminar un gasto que ya cruzó con el banco. \n**Acción Requerida:** Pida a Finanzas que anule la conciliación primero.")
                else:
                    if st.button("🚀 CONFIRMAR ELIMINACIÓN DEFINITIVA"):
                        try:
                            with engine.begin() as conn:
                                # EXPERT FIX: Eliminar primero las referencias para evitar ForeignKeyViolation
                                # 1. Limpiar/Eliminar registros de remuneraciones vinculados
                                conn.execute(text("DELETE FROM coach_remunerations WHERE expense_uuid = :u"), {"u": target_uid})
                                
                                # 2. Eliminar el registro principal del ledger
                                conn.execute(text("DELETE FROM expense_ledger WHERE uuid = :u"), {"u": target_uid})
                                
                            st.success("Gasto y registros asociados eliminados correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"ERROR: Error crítico de base de datos: {e}")
            else:
                st.info("No hay egresos registrados para eliminar.")

# 7. SYNC & CARGA
elif page == "📥 Sync & Carga":
    show_help("Sincronización de Datos", """
        **Archivos requeridos:**
        - **BoxMagic**: Exportar 'Planes Vendidos' en CSV.
        - **Lioren**: Reporte de Ventas Excel (SII).
        - **Banco BCI**: Cartola histórica en Excel.
        
        El sistema detectará duplicados automáticamente. No temas subir el mismo archivo dos veces.
    """)
    
    # --- SMART SYNC SECTION (Unified ETL) ---
    st.markdown("### 🚀 Sincronización Inteligente (One-Touch Sync)")
    st.info("💡 **Expert Mode:** Busca automáticamente los archivos más recientes en el servidor/carpetas de descarga y procesa todos los conectores (BM, VPOS, BCI, Lioren) en un solo paso.")
    
    if st.button("🔄 EJECUTAR SINCRONIZACIÓN GLOBAL", type="primary", use_container_width=True):
        manager = ETLManager()
        with st.spinner("Sincronizando todas las fuentes de datos y ejecutando conciliación..."):
            res = manager.run_full_sync()
        
        # Analizar resultados para mostrar info amigable
        failed_sources = []
        success_sources = []
        for src, status in res.items():
            if "Success" in status or "Processed" in status:
                success_sources.append(src.capitalize())
            else:
                failed_sources.append((src.capitalize(), status))
                
        if success_sources:
            st.success(f"✅ **Sincronización Automática Exitosa para:** {', '.join(success_sources)}")
            
        if failed_sources:
            st.warning("⚠️ **Requiere Carga Manual:** Al estar el sistema en la nube (Railway), no tiene acceso a tu carpeta de Descargas local. Por favor, usa las pestañas de abajo para subir estos archivos:")
            for src, error in failed_sources:
                # Simplificar el mensaje de error para el usuario
                user_err = "Archivo no encontrado en el servidor" if "not found" in error.lower() or "no new file" in error.lower() else error
                st.error(f"❌ **{src}**: {user_err}")
        
        if st.button("Re-cargar Aplicación"):
            st.rerun()

    # --- ULTIMO REGISTRO DE SYNC ---
    with engine.connect() as conn:
        q_log = text("SELECT value FROM system_settings WHERE key = 'ETL_LAST_RUN'")
        log_res = conn.execute(q_log).fetchone()
        
    if log_res:
        log_data = json.loads(log_res[0])
        with st.expander(f"📜 Detalle Última Ejecución ({log_data.get('timestamp')})"):
            st.write(f"**Estado:** `{log_data.get('status')}` | **Duración:** `{log_data.get('duration_seconds', 0):.1f}s`")
            st.json(log_data.get('results', {}))

    st.markdown("---")
    
    # Consultar fechas de última sincronización
    with engine.connect() as conn:
        df_sync = pd.read_sql(text("SELECT key, value FROM system_settings WHERE key LIKE 'last_sync_%'"), conn)
    sync_dates = {row['key']: row['value'] for _, row in df_sync.iterrows()}
    
    t1, t2, t3, t4 = st.tabs(["📊 Ventas & Operación", "💳 VirtualPOS", "🧾 Facturación Lioren", "🏦 Banco BCI"])
    with t1:
        st.caption(f"📅 Última carga: {sync_dates.get('last_sync_boxmagic', 'Nunca')}")
        
        # Layout: Marina (Izquierda) | Campanario (Derecha) - Eliminado Active Students
        col_marina, col_camp = st.columns(2)
        
        with col_marina:
            st.markdown("#### ⚓ Sede MARINA")
            up_marina = st.file_uploader("BoxMagic Marina (.csv)", type=['csv'], key="bm_marina")
            if up_marina and st.button("🚀 Cargar Marina", type="primary", use_container_width=True):
                content = up_marina.getvalue().decode("utf-8", errors="ignore")
                df = parse_bm_csv_content(content)
                ins, err = process_bm_dataframe(df, "Marina")
                if ins > 0:
                    reconcile()
                    update_sync_date('last_sync_boxmagic')
                    st.success(f"SUCCESS: Marina: {ins} registros cargados.")
                else: st.error("Error en formato o archivo vacío.")

        with col_camp:
            st.markdown("#### ⛪ Sede CAMPANARIO")
            up_camp = st.file_uploader("BoxMagic Campanario (.csv)", type=['csv'], key="bm_campanario")
            if up_camp and st.button("🚀 Cargar Campanario", type="primary", use_container_width=True):
                content = up_camp.getvalue().decode("utf-8", errors="ignore")
                df = parse_bm_csv_content(content)
                ins, err = process_bm_dataframe(df, "Campanario")
                if ins > 0:
                    reconcile()
                    update_sync_date('last_sync_boxmagic')
                    st.success(f"SUCCESS: Campanario: {ins} registros cargados.")
                else: st.error("Error en formato o archivo vacío.")

    with t2:
        st.caption(f"📅 Última carga: {sync_dates.get('last_sync_vpos', 'Nunca')}")
        st.markdown("#### 💳 Cartola VirtualPOS")
        st.info("Sube el archivo CSV exportado desde el portal de Transbank/VirtualPOS ('Mis Ventas').")
        
        up_vpos = st.file_uploader("VirtualPOS (.csv)", type=['csv'], key="vpos_upload")
        if up_vpos and st.button("🚀 Cargar VirtualPOS", type="primary"):
            content = up_vpos.getvalue().decode("utf-8", errors="ignore")
            ins, skp = process_vpos_content(content)
            if ins > 0 or skp > 0:
                reconcile()
                update_sync_date('last_sync_vpos')
                st.success(f"SUCCESS: VirtualPOS: {ins} nuevos, {skp} duplicados omitidos.")
            else:
                st.error("No se pudieron procesar registros. Revisa el formato.")

    with t3:
        st.caption(f"📅 Última carga: {sync_dates.get('last_sync_lioren', 'Nunca')}")
        st.markdown("#### 🧾 Boletas de Venta (Lioren / SII)")
        st.info("Sube el archivo Excel exportado desde Lioren ('Ventas' -> 'Boletas').")
        
        up_lv = st.file_uploader("Ventas Lioren (.xlsx)", type=['xlsx'], key="lioren_sales_up")
        if up_lv:
            if st.button("📊 Sync Ventas SII", type="primary"):
                with open("tmp_v.xlsx","wb") as f: f.write(up_lv.read())
                with st.spinner("Procesando ventas legales..."):
                    success, result = process_lioren_sales("tmp_v.xlsx")
                
                if success:
                    update_sync_date('last_sync_lioren')
                    st.success(f"SUCCESS: Ventas integradas: {result} registros procesados.")
                    # st.rerun() # Omitimos rerun inmediato para que el usuario vea el mensaje de éxito
                else:
                    st.error(f"ERROR: Error al procesar: {result}")
    with t4:
        st.caption(f"📅 Última carga: {sync_dates.get('last_sync_bci', 'Nunca')}")
        
        col_up, col_manual = st.columns([2, 1])
        
        with col_up:
            st.markdown("#### 🏦 Carga Masiva (Cartola BCI)")
            st.info("Sube el archivo Excel exportado desde el portal BCI.")
            up_bci = st.file_uploader("Cartola BCI (.xlsx)", type=['xlsx'], key="bci_statement_up")
            
            if up_bci and st.button("🚀 Procesar Cartola", type="primary"):
                with open("tmp_bci.xlsx","wb") as f: f.write(up_bci.read())
                
                with st.spinner("Analizando cartola bancaria..."):
                    success, msg = process_bci_statement("tmp_bci.xlsx")
                
                if success:
                    reconcile_bank_expenses()
                    update_sync_date('last_sync_bci')
                    st.success(f"SUCCESS: {msg}")
                    # st.rerun()
                else:
                    st.error(f"ERROR: Error: {msg}")
                    
        with col_manual:
            st.markdown("#### ✍️ Ingreso Manual")
            with st.popover("Registrar Ajuste/Movimiento"):
                with st.form("manual_bank"):
                    m_f = st.date_input("Fecha")
                    m_d = st.text_input("Descripción / Motivo")
                    m_a = st.number_input("Monto ($)", step=1000, help="Positivo para abono, negativo para cargo")
                    
                    if st.form_submit_button("Guardar Movimiento"):
                        if m_d and m_a != 0:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO raw_bank (bank_date, description, amount, balance)
                                    VALUES (:f, :d, :a, 0)
                                """), {"f": m_f, "d": f"[MANUAL] {m_d}", "a": m_a})
                            st.success("Movimiento registrado.")
                            st.rerun()
                        else:
                            st.error("Datos incompletos.")

# 8. HISTÓRICOS FINANZAS
elif page == "Docs Históricos Finanzas":
    show_help("Reportes Históricos (2025 y anteriores)", """
        Este panel está diseñado para la consolidación de años pasados. 
        Muestra la evolución de costos y ventas históricas para análisis comparativos.
    """)
    
    h_years = [2025, 2024, 2023, 2022]
    sel_h_year = st.selectbox("Seleccione Año para Revisar", h_years)
    
    # KPIs Históricos
    c1, c2, c3 = st.columns(3)
    # Lógica simplificada para históricos (ejemplo)
    h_inc = pd.read_sql(f"SELECT SUM(net_income) as t FROM consolidated_incomes WHERE EXTRACT(YEAR FROM transaction_date) = {sel_h_year}", engine).iloc[0]['t'] or 0
    h_exp = pd.read_sql(f"SELECT SUM(amount_due) as t FROM expense_ledger WHERE EXTRACT(YEAR FROM due_date) = {sel_h_year}", engine).iloc[0]['t'] or 0
    
    c1.metric(f"Ventas {sel_h_year}", f"${h_inc:,.0f}")
    c2.metric(f"Gastos {sel_h_year}", f"${h_exp:,.0f}")
    c3.metric(f"EBITDA Est.", f"${(h_inc - h_exp):,.0f}")
    
    st.markdown("### 📈 Evolución Mensual")
    # Query para gráfico de barras mensual
    h_query = f"""
        SELECT TO_CHAR(transaction_date, 'MM') as mes, SUM(net_income) as monto, 'Ingresos' as tipo
        FROM consolidated_incomes WHERE EXTRACT(YEAR FROM transaction_date) = {sel_h_year}
        GROUP BY 1
        UNION ALL
        SELECT TO_CHAR(due_date, 'MM') as mes, SUM(amount_due) as monto, 'Egresos' as tipo
        FROM expense_ledger WHERE EXTRACT(YEAR FROM due_date) = {sel_h_year}
        GROUP BY 1
        ORDER BY mes
    """
    df_h = pd.read_sql(h_query, engine)
    if not df_h.empty:
        fig_h = px.bar(df_h, x="mes", y="monto", color="tipo", barmode="group",
                       title=f"Desempeño Mensual {sel_h_year}",
                       color_discrete_map={'Ingresos': '#3b82f6', 'Egresos': '#ef4444'})
        st.plotly_chart(fig_h, use_container_width=True)
    else:
        st.warning(f"No hay datos cargados para el año {sel_h_year}. Por favor, usa el módulo 'Sync & Carga' para subir los históricos.")

# 9. CIERRE FISCAL (NEW)
elif page == "🔐 Cierre Fiscal":
    show_help("Control de Cierre Mensual", """
        **Certificación de Periodo**:
        Esta herramienta permite 'Sellar' un mes contable. Una vez cerrado:
        - Nadie podrá subir ventas o gastos con fecha de ese mes.
        - Se guarda una copia estática de los resultados.
        
        *Solo cierra un mes cuando estés seguro de que toda la información está cargada.*
    """)
    
    st.markdown(f"### 🔐 Gestión de Periodos Fiscales {sel_year}")
    
    # 1. Fetch current status
    with engine.connect() as conn:
        periods_df = pd.read_sql(text(f"SELECT * FROM accounting_periods WHERE period_key LIKE '{sel_year}-%' ORDER BY period_key"), conn)
        
    status_map = {row['period_key']: row for _, row in periods_df.iterrows()}
    
    # 2. Grid of Months
    months = [f"{sel_year}-{m:02d}" for m in range(1, 13)]
    
    # Check current stats to show preview
    with engine.connect() as conn:
        inc_df = pd.read_sql(text(f"SELECT TO_CHAR(transaction_date, 'YYYY-MM') as pk, SUM(net_income) as v FROM consolidated_incomes WHERE EXTRACT(YEAR FROM transaction_date) = {sel_year} GROUP BY 1"), conn)
        inc_map = dict(zip(inc_df['pk'], inc_df['v']))
        
        exp_df = pd.read_sql(text(f"SELECT TO_CHAR(due_date, 'YYYY-MM') as pk, SUM(amount_due) as v FROM expense_ledger WHERE EXTRACT(YEAR FROM due_date) = {sel_year} GROUP BY 1"), conn)
        exp_map = dict(zip(exp_df['pk'], exp_df['v']))
    exp_map = dict(zip(exp_df['pk'], exp_df['v']))
    
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    
    for i, p_key in enumerate(months):
        p_data = status_map.get(p_key, {})
        is_closed = p_data.get('status') == 'CLOSED'
        
        curr_sales = inc_map.get(p_key, 0)
        curr_exp = exp_map.get(p_key, 0)
        margin = curr_sales - curr_exp
        
        with cols[i % 3]:
            # Card Style
            border_color = "#ef4444" if is_closed else "#10b981"
            icon = "🔒" if is_closed else "🔓"
            bg_color = "rgba(254, 202, 202, 0.1)" if is_closed else "white"
            
            st.markdown(f"""
                <div style="border: 2px solid {border_color}; border-radius: 10px; padding: 15px; background: {bg_color}; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin:0;">{p_key}</h4>
                        <span style="font-size: 1.5rem;">{icon}</span>
                    </div>
            """, unsafe_allow_html=True)
            
            st.metric("Ventas (Prelim)", f"${curr_sales:,.0f}")
            st.metric("Margen (Prelim)", f"${margin:,.0f}", delta_color="normal" if margin > 0 else "inverse")
            
            if is_closed:
                st.caption(f"Cerrado por: {p_data.get('closed_by', 'Admin')}")
                st.caption(f"Fecha: {str(p_data.get('closed_at', ''))[:10]}")
            else:
                if st.button(f"Sellar {p_key}", key=f"btn_close_{p_key}", use_container_width=True):
                    # Logic to close
                    try:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO accounting_periods (period_key, status, closed_at, closed_by, final_margin)
                                VALUES (:pk, 'CLOSED', NOW(), 'Admin', :fm)
                                ON CONFLICT (period_key) 
                                DO UPDATE SET status = 'CLOSED', closed_at = NOW(), final_margin = :fm
                            """), {"pk": p_key, "fm": margin})
                        st.success(f"Periodo {p_key} CERRADO.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error cerrando: {e}")
            
            st.markdown("</div>", unsafe_allow_html=True)

