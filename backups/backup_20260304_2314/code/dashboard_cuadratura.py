
import streamlit as st
import pandas as pd
from sqlalchemy import text
import plotly.express as px

def render_cuadratura_dashboard(engine, start_date, end_date, sede_filter):
    """
    Renders the Conciliation and Anomalies (Cuadratura) Dashboard.
    """
    st.markdown(f"### ⚖️ Cuadratura de Caja: {sede_filter}")
    st.caption(f"Periodo: {start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}")
    
    st.markdown("""
        <div style='background-color:#fff3e0; padding:15px; border-radius:10px; border-left: 5px solid #ff9800; margin-bottom: 20px;'>
            <strong>🔍 Motor de Cuadratura Automática</strong><br/>
            Este módulo cruza automáticamente "La Verdad Comercial" (BoxMagic) con "La Verdad Transaccional" (VPOS y Bancos).
            Destaca específicamente errores de tipeo y descuadres en transferencias.
        </div>
    """, unsafe_allow_html=True)

    with engine.connect() as conn:
        # Get Latest Reconciliation Result
        q_results = text("""
            SELECT * FROM reconciliation_results 
            WHERE sede = :sede 
            AND reconciliation_date >= :start AND reconciliation_date <= :end
            ORDER BY created_at DESC LIMIT 1
        """)
        
        result_df = pd.read_sql(q_results, conn, params={"sede": sede_filter, "start": start_date, "end": end_date})
        
        if result_df.empty:
            st.warning("No hay datos de cuadratura para este periodo. Sincronice los datos primero.")
            if st.button("🔄 Ejecutar Cuadratura Ahora"):
                # Call the script or show message
                st.info("Ejecutando Engine... (En desarrollo la llamada asíncrona)")
            return
            
        res = result_df.iloc[0]
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Informado (BoxMagic)", f"${res['bm_total']:,.0f}")
        with c2:
            st.metric("Total Webpay (VPOS Real)", f"${res['vpos_total']:,.0f}", delta=f"${res['discrepancy_webpay']:,.0f} Descuadre")
        with c3:
            st.metric("Total Transferencias (Por Validar)", f"${res['bm_transferencia']:,.0f}")
            
        st.markdown("---")
        
        # Anomalies
        q_anomalies = text("""
            SELECT anomaly_type as "Tipo", cliente as "Cliente", monto_esperado as "Monto BM", notas as "Detalle" 
            FROM reconciliation_anomalies
            WHERE reconciliation_id = :rid
        """)
        anomalies_df = pd.read_sql(q_anomalies, conn, params={'rid': int(res['id'])})
        
        st.markdown("#### 🚨 Alertas de Transferencia y Posibles Errores de Tipeo")
        st.write("El 30% de los pagos por transferencia suelen tener errores en BoxMagic al ser ingresados manualmente. Aquí listamos los que requieren revisión cruzada con el banco:")
        
        if anomalies_df.empty:
            st.success("¡Perfecto! No se detectaron anomalías en este periodo.")
        else:
            st.dataframe(anomalies_df, use_container_width=True)
            
            # Action buttons
            st.button("SUCCESS: Marcar Transferencias como Validadas en Banco")

