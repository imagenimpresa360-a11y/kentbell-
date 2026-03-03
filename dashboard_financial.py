import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text

def render_financial_dashboard(engine, start_date, end_date, sede_filter):
    """
    Renders a premium financial dashboard for the Kent Bell system.
    """
    
    # Convert dates to string for SQL if needed, but safer to pass as parameters
    params = {
        "start": start_date,
        "end": end_date
    }
    
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
        q_inc = text(f"""
            SELECT 
                COALESCE(SUM(amount_expected), 0) as bruto,
                COALESCE(SUM(amount_expected - amount_received), 0) as comisiones, -- Asumimos diferencia como costo transaccional si no hay campo comision
                COALESCE(SUM(amount_received), 0) as neto_comercial
            FROM consolidated_incomes
            WHERE transaction_date BETWEEN :start AND :end
            {where_sede_ledger}
        """)
        
        # B. Expense Data
        q_exp = text(f"""
            SELECT COALESCE(SUM(amount_due), 0) as total_bruto,
                   COALESCE(SUM(amount_paid), 0) as total_pagado
            FROM expense_ledger
            WHERE due_date BETWEEN :start AND :end
            {where_sede_ledger}
        """)
        
        with engine.connect() as conn:
            income_summary = pd.read_sql(q_inc, conn, params=params).iloc[0]
            expense_summary = pd.read_sql(q_exp, conn, params=params).iloc[0]
            
            # Monthly flow (ajustado para mostrar solo meses en el rango)
            q_flow = text(f"""
                WITH monthly_inc AS (
                    SELECT TO_CHAR(transaction_date, 'YYYY-MM') as mes_sort, TO_CHAR(transaction_date, 'Mon') as mes, SUM(amount_expected) as income
                    FROM consolidated_incomes
                    WHERE transaction_date BETWEEN :start AND :end {where_sede_ledger}
                    GROUP BY 1, 2
                ), monthly_exp AS (
                    SELECT TO_CHAR(due_date, 'YYYY-MM') as mes_sort, TO_CHAR(due_date, 'Mon') as mes, SUM(amount_due) as expense
                    FROM expense_ledger
                    WHERE due_date BETWEEN :start AND :end {where_sede_ledger}
                    GROUP BY 1, 2
                )
                SELECT 
                    COALESCE(i.mes, e.mes) as mes,
                    COALESCE(i.income, 0) as ingresos,
                    COALESCE(e.expense, 0) as egresos,
                    COALESCE(i.mes_sort, e.mes_sort) as mes_sort
                FROM monthly_inc i
                FULL OUTER JOIN monthly_exp e ON i.mes_sort = e.mes_sort
                ORDER BY mes_sort
            """)
            df_flow = pd.read_sql(q_flow, conn, params=params)
            
            # Expense by Category
            q_cat = text(f"""
                SELECT c.name, SUM(l.amount_due) as total
                FROM expense_ledger l
                JOIN expense_categories c ON l.category_id = c.id
                WHERE l.due_date BETWEEN :start AND :end {where_sede_ledger}
                GROUP BY 1 ORDER BY 2 DESC
            """)
            df_cat = pd.read_sql(q_cat, conn, params=params)

             # C. Rentabilidad por Plan
            q_plans = text(f"""
                SELECT plan_name, SUM(amount) as total, COUNT(*) as cantidad
                FROM raw_boxmagic
                WHERE created_at BETWEEN :start AND :end {where_sede_raw}
                GROUP BY 1 ORDER BY 2 DESC LIMIT 10
            """)
            df_plans = pd.read_sql(q_plans, conn, params=params)

        # --- KPI CALCULATIONS ---
        total_income = float(income_summary['bruto'])
        total_commissions = float(income_summary['comisiones'])
        net_commercial = float(income_summary['neto_comercial'])
        total_expenses = float(expense_summary['total_bruto'])
        ebitda = net_commercial - total_expenses
        margin_perc = (ebitda / net_commercial * 100) if net_commercial > 0 else 0

        # --- UI: HEADER KPIs ---
        st.markdown(f"### 🚀 Rendimiento Financiero: {sede_filter}")
        st.caption(f"Periodo: {start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}")
        
        k1, k2, k3, k4 = st.columns(4)
        
        with k1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Ingreso Bruto</div>
                <div class="metric-value">${total_income:,.0f}</div>
                <div class="metric-delta" style="color: #64748b;">Monto Esperado</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k2:
            st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid #10b981;">
                <div class="metric-label">Ingreso Neto (Caja)</div>
                <div class="metric-value">${net_commercial:,.0f}</div>
                <div class="metric-delta" style="color: #ef4444;">-${total_commissions:,.0f} Est. Costos</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k3:
            st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid #ef4444;">
                <div class="metric-label">Gastos Totales</div>
                <div class="metric-value">${total_expenses:,.0f}</div>
                <div class="metric-delta" style="color: #64748b;">OpEx del Periodo</div>
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
            st.markdown("#### 💰 Evolución del Periodo")
            if not df_flow.empty:
                fig_flow = go.Figure()
                fig_flow.add_trace(go.Bar(
                    x=df_flow['mes'], y=df_flow['ingresos'],
                    name='Ingresos', marker_color='#10b981',
                    opacity=0.8
                ))
                fig_flow.add_trace(go.Bar(
                    x=df_flow['mes'], y=df_flow['egresos'],
                    name='Egresos', marker_color='#ef4444',
                    opacity=0.8
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
            else:
                st.info("No hay datos para el rango de fechas seleccionado.")

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
                st.info("Sin datos de gastos en este rango.")

        # --- CHART ROW 2: STRATEGIC INSIGHTS ---
        st.markdown("---")
        st.markdown("#### 📊 Insights Estratégicos")
        
        i1, i2 = st.columns(2)
        
        with i1:
            st.markdown("**🏆 Planes más Rentables (Top 10)**")
            if not df_plans.empty:
                fig_plans = px.bar(df_plans, x='total', y='plan_name', orientation='h',
                                  text_auto='.2s',
                                  color='total', color_continuous_scale='Blues')
                fig_plans.update_layout(showlegend=False, xaxis_title="Monto Total ($)", yaxis_title=None,
                                       plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                       yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_plans, use_container_width=True)
            else:
                st.info("No hay datos de planes para este periodo.")

        with i2:
             # Collection Health (Conciliation Status)
            q_status = text(f"""
                SELECT status, COUNT(*) as qt, SUM(amount_expected) as total
                FROM consolidated_incomes
                WHERE transaction_date BETWEEN :start AND :end {where_sede_ledger}
                GROUP BY 1
            """)
            with engine.connect() as conn:
                df_status = pd.read_sql(q_status, conn, params=params)
            
            st.markdown("**🛡️ Salud de Cobranza (Conciliación)**")
            if not df_status.empty:
                fig_status = px.pie(df_status, values='total', names='status', hole=0.4,
                                   color='status',
                                   color_discrete_map={
                                       'MATCH_FULL': '#10b981', 
                                       'MATCH_PARTIAL': '#3b82f6', 
                                       'PENDING_DEPOSIT': '#f59e0b',
                                       'ERROR_GHOST': '#ef4444'
                                   })
                fig_status.update_layout(margin=dict(l=0, r=0, t=30, b=0),
                                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
                st.plotly_chart(fig_status, use_container_width=True)
            else:
                st.info("Sin datos de conciliación para este periodo.")

        # --- DETALLE DE GASTOS (EXPANDER) ---
        st.markdown("---")
        with st.expander("📂 Ver Detalle de Gastos del Periodo"):
            q_detail = text(f"""
                SELECT 
                    l.due_date as fecha, 
                    c.name as categoria, 
                    l.description as descripcion, 
                    l.amount_due as monto, 
                    l.status as estado
                FROM expense_ledger l
                JOIN expense_categories c ON l.category_id = c.id
                WHERE l.due_date BETWEEN :start AND :end {where_sede_ledger}
                ORDER BY l.due_date DESC
            """)
            with engine.connect() as conn:
                df_detail = pd.read_sql(q_detail, conn, params=params)
            
            if not df_detail.empty:
                st.dataframe(df_detail, use_container_width=True)
            else:
                st.info("No se encontraron gastos registrados para este periodo.")

    except Exception as e:
        st.error(f"Error crítico en el Dashboard Financiero: {e}")
        st.exception(e)
