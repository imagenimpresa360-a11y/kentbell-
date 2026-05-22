
import streamlit as st
import pandas as pd
import plotly.express as px
from db_utils import DatabaseManager

# Page Config
st.set_page_config(page_title="CrossFit Control Dashboard", layout="wide", page_icon="🏋️")

# Database Connection
@st.cache_resource
def get_db_connection():
    db = DatabaseManager()
    db.connect()
    return db

db = get_db_connection()

# Sidebar
st.sidebar.title("Navegación")
option = st.sidebar.radio("Ir a:", ["Dashboard General", "Estadísticas (Alumnos)", "Configuración"])

st.sidebar.markdown("---")
st.sidebar.success("Sistema Conectado a PostgreSQL")

# --- PAGE: ESTADÍSTICAS ---
if option == "Estadísticas (Alumnos)":
    st.title("📊 Estadísticas de Alumnos Inactivos")
    st.markdown("Análisis de usuarios fugados y oportunidades de recuperación.")

    # Fetch KPI Data
    try:
        kpi_df = pd.DataFrame(db.fetch_all("SELECT * FROM view_inactive_users_stats"))
        if not kpi_df.empty:
            # Aggregate KPIs
            total_loss = kpi_df['estimated_revenue_loss'].sum()
            total_users = kpi_df['total_leaked_users'].sum()
            top_churn_plan = kpi_df['most_common_plan_churned'].iloc[0]

            # Display KPIs
            col1, col2, col3 = st.columns(3)
            col1.metric("Ingresos Perdidos (Est.)", f"${total_loss:,.0f}")
            col2.metric("Total Usuarios Inactivos", f"{total_users}")
            col3.metric("Plan con Mayor Fuga", top_churn_plan)
            
            st.divider()

            # Charts
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("Evolución de Fuga por Mes")
                fig_bar = px.bar(kpi_df, x='month_year', y='total_leaked_users', 
                                 title="Usuarios Inactivos por Mes",
                                 labels={'month_year': 'Mes', 'total_leaked_users': 'Usuarios'})
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_chart2:
                st.subheader("Ingresos Perdidos por Mes")
                fig_line = px.line(kpi_df, x='month_year', y='estimated_revenue_loss', 
                                   title="Tendencia de Pérdida Financiera", markers=True,
                                   labels={'month_year': 'Mes', 'estimated_revenue_loss': 'Monto ($)'})
                st.plotly_chart(fig_line, use_container_width=True)

    except Exception as e:
        st.error(f"Error cargando KPIs: {e}")

    # Detail Table
    st.subheader("📋 Lista de Recuperación (Top Prioridad)")
    try:
        detail_df = pd.DataFrame(db.fetch_all("SELECT * FROM view_recuperation_list"))
        if not detail_df.empty:
            st.dataframe(
                detail_df.style.background_gradient(subset=['amount'], cmap='Reds'),
                use_container_width=True
            )
        else:
            st.info("No hay datos detallados disponibles.")
    except Exception as e:
        st.error(f"Error cargando detalles: {e}")

# --- PAGE: DASHBOARD ---
elif option == "Dashboard General":
    st.title("🚀 Panel de Control General")
    st.info("Módulos de Ingresos y Egresos en construcción...")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Estado de Conectores")
        st.success("SUCCESS: BoxMagic (Activo)")
        st.warning("WARN:️ VirtualPOS (En proceso)")
        st.success("SUCCESS: PostgreSQL (Conectado)")
    
    with col2:
        st.subheader("Acciones Rápidas")
        if st.button("🔄 Ejecutar Sincronización Diaria"):
            st.toast("Iniciando sincronización... (Simulado)")

# --- PAGE: CONFIG ---
elif option == "Configuración":
    st.title("⚙️ Configuración del Sistema")
    st.code("DB_HOST=localhost\nDB_NAME=crossfit_control", language="bash")
