import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text

def render_financial_dashboard(engine, sel_year, sede_filter):
    """
    Renders a premium financial dashboard for the Kent Bell system.
    """
    
    # --- STYLE INJECTION (GLASSMORPISM) ---
    st.markdown("""
    <style>
        .metric-card {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 20px;
            padding: 1.5rem;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
            margin-bottom: 1rem;
        }
        .metric-label {
            font-size: 0.8rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 800;
            color: #0f172a;
        }
        .metric-delta {
            font-size: 0.9rem;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- DATA FETCHING ---
    try:
        where_sede_ledger = ""
        where_sede_raw = ""
        if sede_filter == "Marina":
            where_sede_ledger = "AND sede = 'Marina'"
            where_sede_raw = "AND source_hint = 'Marina'"
        elif sede_filter == "Campanario":
            where_sede_ledger = "AND sede = 'Campanario'"
            where_sede_raw = "AND source_hint = 'Campanario'"

        # A. Income Data
        q_inc = f"""
            SELECT 
                COALESCE(SUM(amount_expected), 0) as bruto,
                COALESCE(SUM(commission_amount), 0) as comisiones,
                COALESCE(SUM(net_income), 0) as neto_comercial
            FROM consolidated_incomes
            WHERE EXTRACT(YEAR FROM transaction_date) = {sel_year}
            {where_sede_ledger}
        """
        
        # B. Expense Data
        q_exp = f"""
            SELECT COALESCE(SUM(amount_due), 0) as total_bruto,
                   COALESCE(SUM(amount_paid), 0) as total_pagado
            FROM expense_ledger
            WHERE EXTRACT(YEAR FROM due_date) = {sel_year}
            {where_sede_ledger}
        """
        
        with engine.connect() as conn:
            income_summary = pd.read_sql(text(q_inc), conn).iloc[0]
            expense_summary = pd.read_sql(text(q_exp), conn).iloc[0]
            
            # Monthly flow
            q_flow = f"""
                WITH monthly_inc AS (
                    SELECT EXTRACT(MONTH FROM transaction_date) as mes, SUM(amount_expected) as income
                    FROM consolidated_incomes
                    WHERE EXTRACT(YEAR FROM transaction_date) = {sel_year} {where_sede_ledger}
                    GROUP BY 1
                ), monthly_exp AS (
                    SELECT EXTRACT(MONTH FROM due_date) as mes, SUM(amount_due) as expense
                    FROM expense_ledger
                    WHERE EXTRACT(YEAR FROM due_date) = {sel_year} {where_sede_ledger}
                    GROUP BY 1
                )
                SELECT 
                    m.mes,
                    COALESCE(i.income, 0) as ingresos,
                    COALESCE(e.expense, 0) as egresos
                FROM (SELECT generate_series(1,12) as mes) m
                LEFT JOIN monthly_inc i ON m.mes = i.mes
                LEFT JOIN monthly_exp e ON m.mes = e.mes
                ORDER BY m.mes
            """
            df_flow = pd.read_sql(text(q_flow), conn)
            
            # Expense by Category
            q_cat = f"""
                SELECT c.name, SUM(l.amount_due) as total
                FROM expense_ledger l
                JOIN expense_categories c ON l.category_id = c.id
                WHERE EXTRACT(YEAR FROM l.due_date) = {sel_year} {where_sede_ledger}
                GROUP BY 1 ORDER BY 2 DESC
            """
            df_cat = pd.read_sql(text(q_cat), conn)

        # --- KPI CALCULATIONS ---
        total_income = float(income_summary['bruto'])
        total_commissions = float(income_summary['comisiones'])
        net_commercial = float(income_summary['neto_comercial'])
        total_expenses = float(expense_summary['total_bruto'])
        ebitda = net_commercial - total_expenses
        margin_perc = (ebitda / net_commercial * 100) if net_commercial > 0 else 0

        # --- UI: HEADER KPIs ---
        st.markdown(f"### 🚀 Rendimiento Financiero: {sede_filter}")
        
        k1, k2, k3, k4 = st.columns(4)
        
        with k1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Ingreso Bruto</div>
                <div class="metric-value">${total_income:,.0f}</div>
                <div class="metric-delta" style="color: #ef4444;">-${total_commissions:,.0f} Comis.</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k2:
            st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid #10b981;">
                <div class="metric-label">Margen Comercial</div>
                <div class="metric-value">${net_commercial:,.0f}</div>
                <div class="metric-delta" style="color: #64748b;">Ingreso Neto Ops</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k3:
            st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid #ef4444;">
                <div class="metric-label">Gastos Totales</div>
                <div class="metric-value">${total_expenses:,.0f}</div>
                <div class="metric-delta" style="color: #64748b;">OpEx Real</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k4:
            ebitda_color = "#10b981" if ebitda >= 0 else "#ef4444"
            st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid {ebitda_color};">
                <div class="metric-label">EBITDA Estimado</div>
                <div class="metric-value" style="color: {ebitda_color};">${ebitda:,.0f}</div>
                <div class="metric-delta" style="color: {ebitda_color};">{margin_perc:.1f}% Margen</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # --- CHART ROW 1: CASH FLOW & EXPENSES ---
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.markdown("#### 💰 Flujo de Caja Mensual")
            df_flow['Mes'] = df_flow['mes'].apply(lambda x: {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}[x])
            
            fig_flow = go.Figure()
            fig_flow.add_trace(go.Bar(
                x=df_flow['Mes'], y=df_flow['ingresos'],
                name='Ingresos', marker_color='#10b981',
                opacity=0.8, borderwidth=0,
                marker_line_width=0
            ))
            fig_flow.add_trace(go.Bar(
                x=df_flow['Mes'], y=df_flow['egresos'],
                name='Egresos', marker_color='#ef4444',
                opacity=0.8, borderwidth=0,
                marker_line_width=0
            ))
            
            fig_flow.update_layout(
                barmode='group',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=30, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
                font=dict(family="Outfit", size=12)
            )
            st.plotly_chart(fig_flow, use_container_width=True)

        with c2:
            st.markdown("#### 📋 Mix de Gastos")
            if not df_cat.empty:
                fig_pie = px.pie(
                    df_cat, values='total', names='name',
                    hole=0.6,
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_pie.update_layout(
                    margin=dict(l=0, r=0, t=30, b=0),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent')
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Sin datos de gastos registrados.")

        # --- CHART ROW 2: COMPARATIVA & PROYECCIÓN ---
        st.markdown("---")
        st.markdown("#### 📊 Insights Estratégicos")
        
        i1, i2 = st.columns(2)
        
        with i1:
            # Distribution by source
            q_source = f"""
                SELECT COALESCE(source_hint, 'Otros') as fuente, SUM(amount) as total
                FROM raw_boxmagic
                WHERE EXTRACT(YEAR FROM created_at) = {sel_year}
                {where_sede_raw}
                GROUP BY 1 ORDER BY 2 DESC
            """
            with engine.connect() as conn:
                df_source = pd.read_sql(text(q_source), conn)
            
            st.markdown("**Ingresos por Sub-Fuente (BoxMagic)**")
            if not df_source.empty:
                fig_source = px.bar(df_source, x='total', y='fuente', orientation='h',
                                   color='fuente', color_discrete_sequence=px.colors.qualitative.Safe)
                fig_source.update_layout(showlegend=False, xaxis_title=None, yaxis_title=None,
                                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_source, use_container_width=True)
            else:
                st.info("No hay datos de fuentes disponibles.")

        with i2:
            # Sede comparison (if holding)
            if sede_filter == "Holding (Todas)":
                st.markdown("**Efectividad Marina vs Campanario**")
                q_sede_cmp = f"""
                    SELECT sede, SUM(amount_expected) as income
                    FROM consolidated_incomes
                    WHERE EXTRACT(YEAR FROM transaction_date) = {sel_year}
                    AND sede IN ('Marina', 'Campanario')
                    GROUP BY 1
                """
                with engine.connect() as conn:
                    df_sede_cmp = pd.read_sql(text(q_sede_cmp), conn)
                
                if not df_sede_cmp.empty:
                    fig_cmp = px.funnel(df_sede_cmp, y='sede', x='income', color='sede')
                    fig_cmp.update_layout(showlegend=False, 
                                         plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_cmp, use_container_width=True)
                else:
                    st.info("Datos insuficientes para comparar sedes.")
            else:
                # Show status of reconciliation for the selected sede
                st.markdown(f"**Estatus de Conciliación ({sede_filter})**")
                q_status = f"""
                    SELECT status, COUNT(*) as qt
                    FROM consolidated_incomes
                    WHERE EXTRACT(YEAR FROM transaction_date) = {sel_year} {where_sede_ledger}
                    GROUP BY 1
                """
                with engine.connect() as conn:
                    df_status = pd.read_sql(text(q_status), conn)
                
                if not df_status.empty:
                    fig_status = px.pie(df_status, values='qt', names='status', hole=0.4,
                                       color_discrete_map={'MATCH_FULL': '#10b981', 'MATCH_PARTIAL': '#3b82f6', 'PENDING_DEPOSIT': '#f59e0b'})
                    st.plotly_chart(fig_status, use_container_width=True)
                else:
                    st.info("Sin datos de conciliación.")

    except Exception as e:
        st.error(f"Error crítico en el Dashboard Financiero: {e}")
        st.exception(e)
