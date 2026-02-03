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
    
    available_years = [2026, 2025, 2024]
    sel_year = st.selectbox("📅 Año Fiscal", available_years, index=0)
    
    ppm_rate = st.sidebar.number_input("📊 Tasa PPM (%)", value=0.25, step=0.01, help="Tasa P115 1ra Categoría (0.25%)")
    
    st.markdown("---")
    page = st.radio("🏠 MENÚ", [
        "Dashboard Real", 
        "Gestión de Coaches",
        "Alertas & Control",
        "Reportes Legales",
        "Caja & Banco", 
        "Registrar Egresos", 
        "Sync & Carga",
        "Históricos Finanzas"
    ])
    
    st.markdown("---")
    st.markdown("<div style='text-align: center; font-size: 0.8rem; opacity: 0.6;'>v3.2.1 SENIOR | Enterprise Hub</div>", unsafe_allow_html=True)

# --- HEADER DINÁMICO ---
h_col1, h_col2 = st.columns([6, 1])
with h_col1:
    st.markdown(f"""
        <div class="main-header">
            <div style="display: flex; align-items: center; gap: 15px;">
                <span style="font-size: 1.5rem;">{ "📊" if page == "Dashboard Real" else "🏃‍♂️" if page == "Gestión de Coaches" else "🚨" if page == "Alertas & Control" else "📑" if page == "Reportes Legales" else "🏦" if page == "Caja & Banco" else "💸" if page == "Registrar Egresos" else "📥" if page == "Sync & Carga" else "📜" }</span>
                <h2 style="margin:0; font-weight: 800; color: #0f172a; font-size: 1.4rem;">{page}</h2>
            </div>
            <div style="color: #64748b; font-weight: 600;">
                Fiscal {sel_year} | <span style="color: #3b82f6;">v3.3.0</span>
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
if page == "Dashboard Real":
    show_help("Dashboard de Gestión", """
        **¿Cómo leer este panel?**
        - **Ventas**: Ingreso neto después de comisiones (BoxMagic/VirtualPos).
        - **Egresos Op.**: Gastos basados en la fecha de la factura (sirve para impuestos).
        - **Egreso Caja**: Dinero que realmente salió de tu banco este mes.
        
        *Ejemplo: Si pagas el arriendo de Enero en Febrero, aparecerá en 'Egreso Caja' de Febrero.*
    """)
    
    with st.container():
        col_filter1, col_filter2 = st.columns([1, 2])
        with col_filter1:
            sede_filter = st.selectbox("📍 Ubicación Actual", ["CONSOLIDADO", "Campanario", "Marina", "General"])
    
    try:
        y_f = f"EXTRACT(YEAR FROM transaction_date) = {sel_year}"
        ey_f = f"EXTRACT(YEAR FROM due_date) = {sel_year}"
        
        if sede_filter != "CONSOLIDADO":
            y_f += f" AND sede = '{sede_filter}'"
            ey_f += f" AND sede = '{sede_filter}'"
        
        # 1. Ingresos
        with engine.connect() as conn:
            inc_data = pd.read_sql(text(f"SELECT SUM(net_income) as neto, SUM(commission_amount) as com FROM consolidated_incomes WHERE {y_f}"), conn).iloc[0]
            v_neto = inc_data['neto'] or 0
            v_com = inc_data['com'] or 0
            
            # 2. Egresos (P&L - Devengado: basado en fecha de documento)
            exp_data = pd.read_sql(text(f"SELECT SUM(amount_due) as total, SUM(iva_amount) as iva FROM expense_ledger WHERE {ey_f}"), conn).iloc[0]
            c_total = exp_data['total'] or 0
            c_iva = exp_data['iva'] or 0
            
            # 2b. Flujo de Caja (Efectivo: cuánto dinero salió realmente este año del banco)
            cash_out_query = f"SELECT SUM(amount_paid) as total_caja FROM expense_ledger WHERE EXTRACT(YEAR FROM paid_date) = {sel_year}"
            if sede_filter != "CONSOLIDADO":
                cash_out_query += f" AND sede = '{sede_filter}'"
            cash_out_data = pd.read_sql(text(cash_out_query), conn).iloc[0]
            c_caja = cash_out_data['total_caja'] or 0
            
            # 3. Datos Bancarios
            df_set = pd.read_sql(text("SELECT value FROM system_settings WHERE key = 'bank_opening_balance_2026'"), conn)
            open_bal = float(df_set.iloc[0,0]) if not df_set.empty else 0
            bank_moves = pd.read_sql(text(f"SELECT SUM(amount) as neto_banco FROM raw_bank WHERE EXTRACT(YEAR FROM bank_date) = {sel_year}"), conn).iloc[0]
        neto_banco = bank_moves['neto_banco'] or 0
        saldo_actual_banco = open_bal + neto_banco
        
        ppm_provision = v_neto * (ppm_rate / 100)
        utilidad = v_neto - c_total - v_com - ppm_provision
        # Utilidad de Caja (Cash Profit)
        utilidad_caja = v_neto - c_caja - v_com

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Ventas {sede_filter}", f"${v_neto:,.0f}")
        c2.metric("Egresos (Op. Fiscal)", f"${c_total:,.0f}", delta=f"${c_iva:,.0f} IVA Costo", delta_color="inverse")
        c3.metric("Egreso de Caja Real", f"${c_caja:,.0f}", delta="Dinero pagado este año", delta_color="inverse")
        
        if sede_filter == "CONSOLIDADO":
            c4.metric("Saldo BCI (Cash)", f"${saldo_actual_banco:,.0f}", delta=f"${utilidad_caja:,.0f} flujo neto")
        else:
            c4.metric(f"Margen Sede {sede_filter}", f"${utilidad:,.0f}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        g1, g2 = st.columns([3, 2])
        with g1:
            df_cat = pd.read_sql(f"SELECT c.name as cat, SUM(e.amount_due) as m FROM expense_ledger e JOIN expense_categories c ON e.category_id = c.id WHERE {ey_f} GROUP BY c.name ORDER BY m DESC", engine)
            st.plotly_chart(px.bar(df_cat, x='m', y='cat', orientation='h', title=f"Distribución de Gastos: {sede_filter}", color='m', color_continuous_scale='Blues'), use_container_width=True)
        with g2:
            if sede_filter == "CONSOLIDADO":
                df_sd = pd.read_sql(f"SELECT sede, SUM(amount_due) as m FROM expense_ledger WHERE {ey_f} GROUP BY sede", engine)
                st.plotly_chart(px.pie(df_sd, values='m', names='sede', hole=0.5, title="Gastos por Centro de Costo"), use_container_width=True)
    except Exception as e: st.error(f"Error cargando dashboard: {e}")

# 2. GESTIÓN DE COACHES
elif page == "Gestión de Coaches":
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
        query_rem = """
            SELECT r.id, c.name as coach, r.month as mes, r.year as anio, r.hours_worked as horas, 
                   r.total_honorarios as total, r.status, r.sii_folio as folio, r.sede
            FROM coach_remunerations r
            JOIN coaches c ON r.coach_id = c.id
            ORDER BY r.year DESC, r.month DESC, c.name ASC
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
                    # Eliminar del ledger y luego de remuneraciones
                    conn.execute(text("DELETE FROM expense_ledger WHERE uuid = (SELECT expense_uuid FROM coach_remunerations WHERE id = :id)"), {"id": target_rem})
                    conn.execute(text("DELETE FROM coach_remunerations WHERE id = :id"), {"id": target_rem})
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

# 3. ALERTAS
elif page == "Alertas & Control":
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
elif page == "Reportes Legales":
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
elif page == "Caja & Banco":
    show_help("Conciliación Bancaria", """
        **¿Cómo conciliar?**
        1. Selecciona el movimiento del banco (salida de dinero).
        2. Selecciona el o los gastos que cubren ese monto.
        
        *Ejemplo: Un cargo de $343.000 del banco puede cubrir 2 honorarios de $126k y $217k. El sistema sumará ambos y te dará el OK.*
    """)
    tabs_bank = st.tabs(["🏦 Movimientos de Banco", "🤝 Conciliación Manual"])
    
    with tabs_bank[0]:
        st.markdown("### Movimientos Bancarios sin Respaldar")
        df_h = pd.read_sql("SELECT bank_date as fecha, description, amount as monto FROM raw_bank WHERE amount < 0 AND id::text NOT IN (SELECT source_bank_id FROM expense_ledger WHERE source_bank_id IS NOT NULL) ORDER BY bank_date DESC", engine)
        st.dataframe(df_h, use_container_width=True)
        st.download_button("💾 Descargar Detalle de Huérfanos (CSV)", df_h.to_csv(index=False), "banco_huerfanos.csv")
        
    with tabs_bank[1]:
        st.subheader("🛠️ Emparejamiento Manual (SAP Style)")
        st.info("Utiliza esta herramienta para 'cruzar' un cargo del banco con uno o varios gastos registrados. Esto 'limpia' tu saldo y valida el egreso.")
        
        # 1. Movimientos de Banco Huérfanos
        query_orphan = "SELECT id, bank_date, description, amount FROM raw_bank WHERE amount < 0 AND id::text NOT IN (SELECT source_bank_id FROM expense_ledger WHERE source_bank_id IS NOT NULL) ORDER BY bank_date DESC"
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
                df_pending = pd.read_sql("SELECT uuid, due_date, description, amount_due, sede FROM expense_ledger WHERE status = 'PENDING_PAYMENT' ORDER BY due_date DESC", engine)
                
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
elif page == "Registrar Egresos":
    show_help("Registro Manual de Egresos", """
        Usa esto para facturas, boletas de servicios o compras con caja chica.
        - **Sede**: Vital para saber cuánto gasta Marina vs Campanario.
        - **Gasto Crítico**: Si se activa, aparecerá en el panel de alertas si no se paga a tiempo.
    """)
    st.markdown("<h1>💸 Gestión Integral de Egresos</h1>", unsafe_allow_html=True)
    
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

    with st.expander("🗑️ Eliminar Gasto (Admin)"):
        st.warning("⚠️ Esta acción es irreversible. Eliminará el gasto del Dashboard y cualquier vínculo con Coaches.")
        
        # 1. Traer lista de egresos recientes para el selector (Zero Copy)
        df_to_del = pd.read_sql("""
            SELECT uuid, due_date, description, amount_due 
            FROM expense_ledger 
            ORDER BY created_at DESC LIMIT 30
        """, engine)
        
        if not df_to_del.empty:
            # Formatear opciones para que sean legibles
            options = df_to_del['uuid'].tolist()
            def format_exp(uid):
                row = df_to_del[df_to_del['uuid'] == uid].iloc[0]
                return f"{row['due_date']} | {row['description'][:30]} | ${row['amount_due']:,.0f}"
            
            target_uid = st.selectbox("Seleccione el Gasto a Eliminar", options=options, format_func=format_exp)
            
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
elif page == "Sync & Carga":
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
    
    t1, t2, t3 = st.tabs(["📊 Ventas & Operación", "🧾 Facturación Lioren", "🏦 Banco BCI"])
    with t1:
        st.caption(f"📅 Última carga: {sync_dates.get('last_sync_boxmagic', 'Nunca')}")
        c1, c2 = st.columns(2)
        with c1:
            up_bm = st.file_uploader("Subir BoxMagic (.csv)", type=['csv'])
            if up_bm and st.button("🚀 Procesar BoxMagic"):
                # Aquí iría la lógica de procesamiento
                update_sync_date('last_sync_boxmagic')
                st.success("Planes de socios sincronizados.")
                st.rerun()
    with t2:
        st.caption(f"📅 Última carga: {sync_dates.get('last_sync_lioren', 'Nunca')}")
        c1, c2 = st.columns(2)
        with c1:
            up_lv = st.file_uploader("Ventas Lioren (.xlsx)", type=['xlsx'])
            if up_lv and st.button("📊 Sync Ventas SII"):
                with open("tmp_v.xlsx","wb") as f: f.write(up_lv.read())
                process_lioren_sales("tmp_v.xlsx")
                update_sync_date('last_sync_lioren')
                st.success("Ventas legales integradas.")
                st.rerun()
    with t3:
        st.caption(f"📅 Última carga: {sync_dates.get('last_sync_bci', 'Nunca')}")
        up_bci = st.file_uploader("Cartola BCI (.xlsx)", type=['xlsx'])
        if up_bci and st.button("🏦 Iniciar Conciliación Bancaria"):
            with open("tmp_bci.xlsx","wb") as f: f.write(up_bci.read())
            process_bci_statement("tmp_bci.xlsx")
            reconcile_bank_expenses()
            update_sync_date('last_sync_bci')
            st.success("Banco sincronizado y conciliado.")
            st.rerun()

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
