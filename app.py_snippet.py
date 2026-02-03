
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
    periods_df = pd.read_sql(f"SELECT * FROM accounting_periods WHERE period_key LIKE '{sel_year}-%' ORDER BY period_key", engine)
    status_map = {row['period_key']: row for _, row in periods_df.iterrows()}
    
    # 2. Grid of Months
    months = [f"{sel_year}-{m:02d}" for m in range(1, 13)]
    
    # Check current stats to show preview
    inc_df = pd.read_sql(f"SELECT TO_CHAR(transaction_date, 'YYYY-MM') as pk, SUM(net_income) as v FROM consolidated_incomes WHERE EXTRACT(YEAR FROM transaction_date) = {sel_year} GROUP BY 1", engine)
    inc_map = dict(zip(inc_df['pk'], inc_df['v']))
    
    exp_df = pd.read_sql(f"SELECT TO_CHAR(due_date, 'YYYY-MM') as pk, SUM(amount_due) as v FROM expense_ledger WHERE EXTRACT(YEAR FROM due_date) = {sel_year} GROUP BY 1", engine)
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

