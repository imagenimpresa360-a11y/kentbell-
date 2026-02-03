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

def update_sync_date(key):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO system_settings (key, value, label) 
            VALUES (:k, :v, :l)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """), {"k": key, "v": now_str, "l": "Sincronización"})

# Cargar variables de entorno
load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

# URL de conexión
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

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
    
    /* Premium Metric Cards */
    div[data-testid="metric-container"] {
        background-color: #ffffff; 
        border: 1px solid #e2e8f0; 
        padding: 20px; 
        border-radius: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        color: #0f172a !important;
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

    # --- SIMULADOR DE ROLES (FASE 1) ---
    st.markdown("### 👤 Simulación de Perfil")
    user_role = st.selectbox("Rol Activo", ["Admin", "Luis (Ops)", "Finanzas", "Cobranza"])
    st.info(f"Viendo como: **{user_role}**")
    st.markdown("---")
    
    # available_years = [2026, 2025, 2024]
    # sel_year = st.selectbox("📅 Año Fiscal", available_years, index=0)
    # Usuario solicitó eliminar selector. Fijamos 2026 por defecto para mantener lógica.
    sel_year = 2026
    
    # ppm_rate = st.sidebar.number_input("📊 Tasa PPM (%)", value=0.25, step=0.01, help="Tasa P115 1ra Categoría (0.25%)")
    ppm_rate = 0.25
    
    st.markdown("---")
    
    # Definir menú según rol
    if user_role == "Luis (Ops)":
        menu_options = [
            "💸 Registrar Egresos",
            "🏃‍♂️ Gestión de Coaches",
            "📑 Reportes Legales"
        ]
    elif user_role == "Finanzas":
        menu_options = [
            "📊 Dashboard General (P&L)",
            "🏦 Dashboard Banco",
            "📥 Sync & Carga",
            "📑 Reportes Legales",
            "🚨 Alertas & Control"
        ]
    elif user_role == "Cobranza":
        menu_options = [
             "📉 Alumnos Inactivos",
             "📈 Dashboard BoxMagic",
             "💳 Dashboard VirtualPOS"
        ]
    else: # Admin - Ve todo
        menu_options = [
            "📊 Dashboard General (P&L)",
            "📈 Dashboard BoxMagic", 
            "💳 Dashboard VirtualPOS",
            "🧾 Dashboard Lioren",
            "🏦 Dashboard Banco",
            "🏃‍♂️ Gestión de Coaches",
            "📉 Alumnos Inactivos",
            "🚨 Alertas & Control",
            "💸 Registrar Egresos", 
            "📥 Sync & Carga",
            "📑 Reportes Legales"
        ]

    page = st.radio("🏠 MENÚ EXPERTO", menu_options)
    
    st.markdown("---")
    st.markdown("<div style='text-align: center; font-size: 0.8rem; opacity: 0.6;'>v3.2.1 SENIOR | Enterprise Hub</div>", unsafe_allow_html=True)

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
                Fiscal {sel_year} | <span style="color: #3b82f6;">v3.5.0 EXECUTIVE</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
with h_col2:
    try:
        st.image("logo_the_boos.jpg", width=120)
    except:
        st.write("LOGO")

# --- LÓGICA DE PÁGINAS ---

# 1. DASHBOARD
# 1. DASHBOARD GENERAL (P&L)
# 1. DASHBOARD GENERAL (P&L)
if page == "📊 Dashboard General (P&L)":
    # st.info("ℹ️ Vista Ejecutiva simplificada para toma de decisiones rápida.")
    
    # --- DATA FETCHING ---
    try:
        # A. VENTAS BOXMAGIC
        # Filtramos por año actual
        q_bm = f"""
            SELECT COALESCE(source_hint, 'General') as sede, SUM(amount) as total, COUNT(*) as qt
            FROM raw_boxmagic 
            WHERE EXTRACT(YEAR FROM created_at) = {sel_year} 
              AND payment_status IN ('activo', 'congelado')
            GROUP BY 1
        """
        with engine.connect() as conn:
            df_bm = pd.read_sql(text(q_bm), conn)
        
        val_bm_marina = df_bm[df_bm['sede'] == 'Marina']['total'].sum()
        qt_bm_marina = df_bm[df_bm['sede'] == 'Marina']['qt'].sum()
        
        val_bm_campanario = df_bm[df_bm['sede'] == 'Campanario']['total'].sum()
        qt_bm_campanario = df_bm[df_bm['sede'] == 'Campanario']['qt'].sum()
        
        val_bm_total = df_bm['total'].sum()
        qt_bm_total = df_bm['qt'].sum()
        
        # B. COSTOS OPERATIVOS (Net_Amount from expense_ledger)
        q_exp = f"""
            SELECT COALESCE(sede, 'General') as sede, SUM(net_amount) as total
            FROM expense_ledger
            WHERE EXTRACT(YEAR FROM due_date) = {sel_year}
            GROUP BY 1
        """
        df_exp = pd.read_sql(q_exp, engine)
        
        cost_marina = df_exp[df_exp['sede'] == 'Marina']['total'].sum()
        cost_campanario = df_exp[df_exp['sede'] == 'Campanario']['total'].sum()
        cost_general = df_exp[df_exp['sede'] == 'General']['total'].sum() # Gastos centrales
        cost_total = df_exp['total'].sum()
        
        # C. MARGENES
        margen_marina = val_bm_marina - cost_marina
        margen_campanario = val_bm_campanario - cost_campanario
        
        # Consolidado: Ventas Totales (BM) vs Costos Totales (Incluye General)
        # Nota: Si hay otros ingresos (VPOS, Banco directo no conciliado), se podrían sumar aquí.
        # Por ahora obedecemos "indicador consolidado de ventas, costos y margen".
        # Si agregamos VPOS, el número será mayor que la suma de las dos sedes si VPOS no tiene sede.
        
        margen_total = val_bm_total - cost_total

        # --- UI LAYOUT (3 FILAS) ---
        
        st.markdown("### ⚓ Sede MARINA")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Ventas BoxMagic", f"${val_bm_marina:,.0f}")
        m2.metric("Costos Operativos", f"${cost_marina:,.0f}")
        m3.metric("N° Reg. Ventas", f"{int(qt_bm_marina)}")
        m4.metric("Margen Operacional", f"${margen_marina:,.0f}", delta_color="normal" if margen_marina > 0 else "inverse")
        st.markdown("---")

        st.markdown("### ⛪ Sede CAMPANARIO")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ventas BoxMagic", f"${val_bm_campanario:,.0f}")
        c2.metric("Costos Operativos", f"${cost_campanario:,.0f}")
        c3.metric("N° Reg. Ventas", f"{int(qt_bm_campanario)}")
        c4.metric("Margen Operacional", f"${margen_campanario:,.0f}", delta_color="normal" if margen_campanario > 0 else "inverse")
        st.markdown("---")

        st.markdown("### 🌎 CONSOLIDADO HOLDING")
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Ventas Totales (Holding)", f"${val_bm_total:,.0f}")
        h2.metric("Costos Totales (Inc. Centrales)", f"${cost_total:,.0f}")
        h3.metric("Total Reg. Ventas", f"{int(qt_bm_total)}")
        h4.metric("EBITDA / Margen Final", f"${margen_total:,.0f}", delta_color="normal" if margen_total > 0 else "inverse")

    except Exception as e:
        st.error(f"Error cargando dashboard ejecutivo: {e}")

# 1.2 DASHBOARD BOXMAGIC (Expert Commercial View)
elif page == "📈 Dashboard BoxMagic":
    st.info("🎯 **Expert Analytics**: Este panel analiza la performance comercial de BoxMagic. Cuantifica los ingresos brutos y netos por sede y plan.")
    
    try:
        # Query matching my updated ingestion logic (using raw_data hint)
        query_bm = f"""
            SELECT 
                amount as monto, 
                created_at as fecha, 
                plan_name, 
                COALESCE(source_hint, 'General') as sede
            FROM raw_boxmagic 
            WHERE EXTRACT(YEAR FROM created_at) = {sel_year}
        """
        df_bm = pd.read_sql(query_bm, engine)
        
        if df_bm.empty:
            st.warning("⚠️ No hay datos cargados en 'raw_boxmagic'. Por favor, sube las planillas en la sección **Sync & Carga**.")
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

    except Exception as e: st.error(f"Error en analítica BoxMagic: {e}")

# 1.3 DASHBOARD VIRTUALPOS (Banking Flow)
elif page == "💳 Dashboard VirtualPOS":
    st.info("🏦 **Cash Flow Audit**: Este tablero cuantifica depósitos y transferencias procesadas vía VirtualPOS.")
    try:
        query_v = f"SELECT transaction_date as fecha, amount as monto, vpos_code FROM raw_virtualpos WHERE EXTRACT(YEAR FROM transaction_date) = {sel_year}"
        df_v = pd.read_sql(query_v, engine)
        if df_v.empty:
            st.warning("No hay flujos de VirtualPOS detectados para este año.")
        else:
            v1, v2 = st.columns(2)
            v1.metric("Total Transaccionado", f"${df_v['monto'].sum():,.0f}")
            v2.metric("Volumen de Operaciones", len(df_v))
            
            st.markdown("---")
            df_v['fecha'] = pd.to_datetime(df_v['fecha'])
            df_line = df_v.groupby('fecha')['monto'].sum().reset_index()
            fig_v = px.line(df_line, x='fecha', y='monto', title="Flujo de Abonos por Fecha", markers=True)
            st.plotly_chart(fig_v, use_container_width=True)
            st.dataframe(df_v, use_container_width=True)
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
            
            st.success("✅ Nota: Todas las boletas registradas operan bajo régimen **Exento de IVA**.")
            
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
                        st.success("✅ Todo conciliado en Banco.")
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
                        st.success(f"✅ MATCH CONFIRMADO (Dif: ${diff})")
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
                        st.error(f"⚠️ NO CUADRA: Diferencia de ${diff:,.0f}")

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
    show_help("Ingreso de Honorarios", """
        **Flujo de Registro:**
        1. Indica el coach y el mes que trabajó.
        2. Ingresa el total de horas. El sistema calculará el monto según su tarifa base.
        3. **Folio SII**: Puedes dejarlo en 0 si aún no te envía la boleta. Cámbialo después en la pestaña 'Historial'.
        
        *Ejemplo: Joaquin trabajó 40 horas en Marina. Registras, el sistema crea la deuda, y cuando le transfieras los $280.000, usas el módulo de Caja & Banco.*
    """)
    
    tabs = st.tabs(["💰 Registro de Honorarios", "📊 Historial y Deudas", "👤 Configuración Coaches"])
    
    with tabs[0]:
        st.markdown("### Registrar Horas Mensuales")
        df_c = pd.read_sql("SELECT id, name, base_rate, default_sede FROM coaches WHERE active = TRUE", engine)
        
        with st.form("honorarios_form", clear_on_submit=True):
            r1c1, r1c2, r1c3 = st.columns(3)
            with r1c1:
                coach_sel = st.selectbox("Coach", options=df_c['name'].tolist())
                coach_id = int(df_c[df_c['name'] == coach_sel]['id'].values[0])
                base_rate = float(df_c[df_c['name'] == coach_sel]['base_rate'].values[0])
            with r1c2:
                mes = st.selectbox("Mes", range(1, 13), index=datetime.now().month - 1)
            with r1c3:
                anio = st.number_input("Año", value=sel_year)
            
            r2c1, r2c2, r2c3 = st.columns(3)
            with r2c1:
                horas = st.number_input("Horas Trabajadas", min_value=0.0, step=0.5)
            with r2c2:
                tarifa = st.number_input("Tarifa por Hora ($)", value=base_rate)
            with r2c3:
                sede_c = st.selectbox("Sede de Imputación", ["Marina", "Campanario", "General"])
            
            if st.form_submit_button("✅ Calcular y Guardar Honorario"):
                total = horas * tarifa
                due_date = f"{anio}-{mes:02d}-01" # Fecha estimada de pago
                
                with engine.begin() as conn:
                    # 1. Crear/Actualizar en el libro de egresos primero (para tener el UUID)
                    res = conn.execute(text("""
                        INSERT INTO expense_ledger (description, amount_due, due_date, category_id, sede, status)
                        VALUES (:d, :a, :f, (SELECT id FROM expense_categories WHERE name = 'Sueldos Profesores' LIMIT 1), :s, 'PENDING_PAYMENT')
                        ON CONFLICT DO NOTHING 
                        RETURNING uuid
                    """), {"d": f"Honorarios {coach_sel} - {mes}/{anio}", "a": total, "f": due_date, "s": sede_c})
                    
                    row = res.fetchone()
                    e_uuid = row[0] if row else None
                    
                    # 2. Guardar en remuneraciones vinculando el UUID del egreso
                    conn.execute(text("""
                        INSERT INTO coach_remunerations (coach_id, month, year, hours_worked, hourly_rate, total_honorarios, sede, status, expense_uuid)
                        VALUES (:cid, :m, :y, :h, :r, :t, :s, 'PENDING', :euuid)
                        ON CONFLICT (coach_id, month, year, sede) DO UPDATE SET 
                            hours_worked = EXCLUDED.hours_worked, 
                            total_honorarios = EXCLUDED.total_honorarios,
                            hourly_rate = EXCLUDED.hourly_rate,
                            expense_uuid = COALESCE(coach_remunerations.expense_uuid, EXCLUDED.expense_uuid)
                    """), {"cid": coach_id, "m": mes, "y": anio, "h": horas, "r": tarifa, "t": total, "s": sede_c, "euuid": e_uuid})
                    
                    # 3. Si ya existía el registro, actualizamos el monto en el ledger también
                    if not row:
                        conn.execute(text("""
                            UPDATE expense_ledger SET amount_due = :a 
                            WHERE uuid = (SELECT expense_uuid FROM coach_remunerations WHERE coach_id = :cid AND month = :m AND year = :y AND sede = :s)
                        """), {"a": total, "cid": coach_id, "m": mes, "y": anio, "s": sede_c})

                st.success(f"Honorario registrado para {coach_sel}: ${total:,.0f}. Reflejado en Dashboard.")

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
        st.subheader("✅ Alumnos Recuperados (Cruce con Activos)")
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
        Este panel monitorea la salud administrativa de tu box.
        - **Certificado Digital**: Fecha de vencimiento para facturación SII.
        - **Folios**: Cantidad de boletas disponibles en Lioren.
        - **Cuentas Críticas**: Gastos marcados como prioritarios (Arriendo, Luz) que vencen pronto.
    """)
    st.markdown("<h1>🚨 Centro de Control & Alertas</h1>", unsafe_allow_html=True)
    df_set = pd.read_sql("SELECT key, value, label FROM system_settings", engine)
    settings = {r['key']: r['value'] for _, r in df_set.iterrows()}
    
    col1, col2, col3 = st.columns(3)
    with col1:
        vence = datetime.strptime(settings.get('cert_digital_vence', '2026-01-01'), '%Y-%m-%d')
        days = (vence - datetime.now()).days
        st.metric("Certificado Digital", vence.strftime('%d/%b'), delta=f"{days} días restantes")
    with col2:
        actual = int(settings.get('folios_actuales', 0))
        st.metric("Folios SII (Disponibles)", actual, delta="-15 esta semana", delta_color="inverse")
    with col3:
        # BUG FIXED: Usando uuid en lugar de id
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
                        st.success(f"✅ CUADRE PERFECTO: ${total_bank:,.0f}")
                    else:
                        st.error(f"⚠️ DIFERENCIA: ${diff:,.0f}")
            
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
            st.success("✅ No quedan movimientos bancarios por conciliar.")

# 6. REGISTRAR EGRESOS
elif page == "💸 Registrar Egresos":
    show_help("Registro Manual de Egresos", """
        Usa esto para facturas, boletas de servicios o compras con caja chica.
        - **Sede**: Vital para saber cuánto gasta Marina vs Campanario.
        - **Gasto Crítico**: Si se activa, aparecerá en el panel de alertas si no se paga a tiempo.
    """)
    st.markdown("<h1>💸 Gestión Integral de Egresos</h1>", unsafe_allow_html=True)
    
    if user_role == "Luis (Ops)":
        st.success("🔒 **Modo Operativo:** Registrando gastos como **PENDIENTE DE PAGO**. La Tesorería aprobará el egreso.")
    
    st.info("💡 **Tip Pro:** Para dividir una factura en varias sedes, registra el mismo N° de Folio varias veces con montos parciales y sedes distintas.")
    
    with st.form("new_exp", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            f = st.date_input("Fecha Documento", datetime.now())
            m = st.number_input("Monto Bruto ($)", min_value=0)
            fol = st.number_input("N° Folio / Factura", min_value=0, step=1)
        with col2:
            p = st.text_input("Proveedor / Profesional")
            c = st.selectbox("Cuenta Contable", pd.read_sql("SELECT name FROM expense_categories", engine)['name'].tolist())
            sd = st.selectbox("Sede", ["Marina", "Campanario", "General"])
        with col3:
            is_f = st.checkbox("¿Es Factura con IVA?", value=True)
            is_c = st.checkbox("¿Gasto Crítico?")
            st.write("") # Spacer
            submit = st.form_submit_button("📁 REGISTRAR EGRESO")
        
        if submit:
            neto = round(m / 1.19) if is_f else m
            iva = m - neto
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO expense_ledger 
                    (description, amount_due, net_amount, iva_amount, due_date, status, is_critical, sede, source_sii_folio) 
                    VALUES (:d, :a, :n, :i, :f, 'PENDING_PAYMENT', :c, :s, :fol)
                """), 
                {"d": f"{p}", "a": m, "n": neto, "i": iva, "f": f, "c": is_c, "s": sd, "fol": fol if fol > 0 else None})
            st.success(f"Gasto registrado: {p} por ${m:,.0f} (Sede: {sd})")

    st.markdown("---")
    st.subheader("📋 Egresos Recientes")
    df_recent = pd.read_sql("SELECT uuid, due_date as fecha, description as proveedor, source_sii_folio as folio, amount_due as monto, sede, status FROM expense_ledger ORDER BY created_at DESC LIMIT 10", engine)
    st.dataframe(df_recent, use_container_width=True)

    if user_role == "Admin":
        with st.expander("🗑️ Eliminar Gasto (Admin)"):
            st.warning("⚠️ Esta acción es irreversible. Eliminará el gasto del Dashboard y cualquier vínculo con Coaches.")
        
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
                        st.error(f"❌ Error crítico de base de datos: {e}")
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
                    st.success(f"✅ Marina: {ins} registros cargados.")
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
                    st.success(f"✅ Campanario: {ins} registros cargados.")
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
                st.success(f"✅ VirtualPOS: {ins} nuevos, {skp} duplicados omitidos.")
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
                    st.success(f"✅ Ventas integradas: {result} registros procesados.")
                    # st.rerun() # Omitimos rerun inmediato para que el usuario vea el mensaje de éxito
                else:
                    st.error(f"❌ Error al procesar: {result}")
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
                    st.success(f"✅ {msg}")
                    # st.rerun()
                else:
                    st.error(f"❌ Error: {msg}")
                    
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
elif page == "Históricos Finanzas":
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

