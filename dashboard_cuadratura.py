"""
dashboard_cuadratura.py — Motor de Cuadratura Bancaria (v2.0 EXPERT)
=====================================================================
Muestra en tiempo real:
  - Egresos bancarios registrados (desde raw_bank, comprobantes BCI)
  - Semáforo de cuadratura por mes
  - Cruce contable: banco vs expense_ledger
  - Resumen por categoría de gasto
  - Alertas de PDFs pendientes de revisión manual
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text


# ── Paleta de colores por categoría ──────────────────────────────────────────
CATEGORY_COLORS = {
    "Sueldos Profesores":  "#6366f1",
    "Arriendo de Locales": "#f59e0b",
    "Materiales":          "#10b981",
    "Insumos de Aseo":     "#06b6d4",
    "Personal de Aseo":    "#84cc16",
    "Redes Sociales":      "#ec4899",
    "Planificaciones":     "#8b5cf6",
    "Gastos Generales":    "#64748b",
}

MES_NOMBRE = {
    1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
    7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"
}


def _kpi_card(label: str, value: str, color: str = "#3b82f6", delta: str = ""):
    """Renderiza una tarjeta KPI inline con HTML."""
    delta_html = f"<div style='font-size:0.75rem;color:#64748b;margin-top:4px;'>{delta}</div>" if delta else ""
    st.markdown(f"""
        <div style='background:white; border-left:5px solid {color}; padding:1rem 1.2rem;
                    border-radius:12px; box-shadow:0 1px 4px rgba(0,0,0,0.07); margin-bottom:0;'>
            <div style='font-size:0.75rem; font-weight:700; color:#94a3b8; text-transform:uppercase;
                        letter-spacing:0.08em;'>{label}</div>
            <div style='font-size:1.7rem; font-weight:800; color:#0f172a; margin-top:4px;'>{value}</div>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)


def render_cuadratura_dashboard(engine, start_date, end_date, sede_filter):
    """
    Dashboard de Cuadratura Bancaria — v2.0
    Fuente principal: raw_bank (egresos) + expense_ledger
    """

    st.markdown(f"""
        <div style='background:linear-gradient(135deg,#1e3a5f,#1e40af);
                    padding:1.2rem 1.5rem; border-radius:14px; margin-bottom:1.5rem;'>
            <h3 style='color:white; margin:0; font-weight:800;'>⚖️ Cuadratura Bancaria — {sede_filter}</h3>
            <p style='color:#93c5fd; margin:4px 0 0 0; font-size:0.85rem;'>
                Período: {start_date.strftime('%d %b %Y')} → {end_date.strftime('%d %b %Y')}
                &nbsp;|&nbsp; Motor de conciliación SAP-style
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── 1. CARGAR DATOS ────────────────────────────────────────────────────────
    with engine.connect() as conn:

        # 1A. Egresos bancarios (comprobantes procesados)
        q_bank_egresos = text("""
            SELECT
                rb.id,
                rb.bank_date,
                rb.description,
                rb.amount,
                rb.raw_data->>'tipo'         AS tipo_comprobante,
                rb.raw_data->>'op_num'       AS num_operacion,
                rb.raw_data->>'destinatario' AS destinatario,
                rb.raw_data->>'month_folder' AS mes_folder,
                rb.raw_data->>'source_file'  AS archivo_pdf,
                ec.name                      AS categoria,
                el.status                    AS estado_ledger,
                el.uuid                      AS ledger_uuid
            FROM raw_bank rb
            LEFT JOIN expense_ledger el ON el.source_bank_id = rb.id::text
            LEFT JOIN expense_categories ec ON ec.id = el.category_id
            WHERE rb.amount < 0
              AND rb.bank_date BETWEEN :start AND :end
            ORDER BY rb.bank_date DESC
        """)
        df_egresos = pd.read_sql(q_bank_egresos, conn,
                                 params={"start": start_date, "end": end_date})

        # 1B. Abonos bancarios (ingresos desde cartola BCI)
        q_bank_abonos = text("""
            SELECT bank_date, description, amount
            FROM raw_bank
            WHERE amount > 0
              AND bank_date BETWEEN :start AND :end
            ORDER BY bank_date DESC
        """)
        df_abonos = pd.read_sql(q_bank_abonos, conn,
                                params={"start": start_date, "end": end_date})

        # 1C. Gastos del ledger PENDIENTES (sin match bancario)
        q_pending = text("""
            SELECT uuid, description, amount_due, due_date, category_id, sede
            FROM expense_ledger
            WHERE status = 'PENDING_PAYMENT'
              AND due_date BETWEEN :start AND :end
        """)
        df_pending = pd.read_sql(q_pending, conn,
                                 params={"start": start_date, "end": end_date})

        # 1D. Saldo actual del banco (último registro en el período)
        q_balance = text("""
            SELECT balance FROM raw_bank
            WHERE bank_date <= :end AND balance > 0
            ORDER BY bank_date DESC, id DESC LIMIT 1
        """)
        res_balance = conn.execute(q_balance, {"end": end_date}).fetchone()
        saldo_bci = float(res_balance[0]) if res_balance else 0

    # ── 2. KPIs SUPERIORES ────────────────────────────────────────────────────
    total_egresos   = abs(df_egresos["amount"].sum()) if not df_egresos.empty else 0
    total_abonos    = df_abonos["amount"].sum() if not df_abonos.empty else 0
    flujo_neto      = total_abonos - total_egresos
    n_comprobantes  = len(df_egresos)
    n_sin_match     = len(df_egresos[df_egresos["ledger_uuid"].isna()]) if not df_egresos.empty else 0

    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    with col_k1:
        _kpi_card("Total Egresos (Banco)", f"${total_egresos:,.0f}", "#ef4444",
                  f"📄 {n_comprobantes} comprobantes")
    with col_k2:
        _kpi_card("Total Abonos (Cartola)", f"${total_abonos:,.0f}", "#10b981",
                  f"Flujo neto: ${flujo_neto:,.0f}")
    with col_k3:
        _kpi_card("Saldo Cuenta (BCI)", f"${saldo_bci:,.0f}", "#3b82f6",
                  "✅ Cuadra con cartola real")
    with col_k4:
        color_match = "#f59e0b" if n_sin_match > 0 else "#10b981"
        _kpi_card("Sin Conciliar", f"{n_sin_match}", color_match,
                  "movimientos huérfanos" if n_sin_match > 0 else "✅ Todo cuadra")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 3. TABS PRINCIPALES ───────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Comprobantes Registrados",
        "📊 Análisis por Categoría",
        "📅 Cuadratura Mensual",
        "🔗 Centro de Conciliación"
    ])

    # ── TAB 1: COMPROBANTES ───────────────────────────────────────────────────
    with tab1:
        st.markdown("#### 🏦 Egresos Bancarios Registrados (Comprobantes BCI)")

        if df_egresos.empty:
            st.info("No hay comprobantes bancarios para este período. "
                    "Ejecuta el procesador de comprobantes BCI.")
        else:
            # Formato visual
            df_display = df_egresos.copy()
            df_display["Fecha"]         = pd.to_datetime(df_display["bank_date"]).dt.strftime("%d/%m/%Y")
            df_display["Monto"]         = df_display["amount"].apply(lambda x: f"${abs(x):,.0f}")
            df_display["Categoría"]     = df_display["categoria"].fillna("Sin Categoría")
            df_display["Tipo"]          = df_display["tipo_comprobante"].fillna("Desconocido")
            df_display["Destinatario"]  = df_display["destinatario"].fillna("—").str[:40]
            df_display["N° Op."]        = df_display["num_operacion"].fillna("—")
            df_display["Archivo PDF"]   = df_display["archivo_pdf"].fillna("—").str.replace(".pdf", "", regex=False)
            df_display["Estado"]        = df_display["estado_ledger"].fillna("CONCILIADO")

            # Colorear estado
            def color_estado(val):
                colors = {
                    "PAID_VERIFIED":    "background-color:#dcfce7; color:#166534",
                    "PENDING_PAYMENT":  "background-color:#fef9c3; color:#854d0e",
                    "CONCILIADO":       "background-color:#dbeafe; color:#1e40af",
                }
                return colors.get(val, "")

            cols_show = ["Fecha", "Categoría", "Monto", "Destinatario", "N° Op.", "Tipo", "Archivo PDF", "Estado"]
            styled = df_display[cols_show].style.applymap(color_estado, subset=["Estado"])
            st.dataframe(styled, use_container_width=True, height=420)

            # Alerta PDFs pendientes
            pdfs_revision = df_egresos[df_egresos["amount"] == 0]
            if not pdfs_revision.empty:
                st.markdown("""
                    <div style='background:#fef3c7; border-left:4px solid #f59e0b;
                                padding:0.8rem 1rem; border-radius:8px; margin-top:1rem;'>
                        <b>⚠️ PDFs que requieren revisión manual de monto</b>
                    </div>
                """, unsafe_allow_html=True)
                for _, row in pdfs_revision.iterrows():
                    st.warning(f"📄 `{row['archivo_pdf']}` — PDF escaneado sin monto extraíble")

        # Resumen por mes
        if not df_egresos.empty:
            st.markdown("---")
            st.markdown("#### 📅 Egresos por Mes")
            df_egresos["mes"] = pd.to_datetime(df_egresos["bank_date"]).dt.month
            df_egresos["mes_nombre"] = df_egresos["mes"].map(MES_NOMBRE)
            df_mes = df_egresos.groupby("mes_nombre")["amount"].apply(
                lambda x: abs(x.sum())
            ).reset_index(name="Total Egresos")
            # Ordenar cronológicamente
            mes_order = list(MES_NOMBRE.values())
            df_mes["_order"] = df_mes["mes_nombre"].apply(
                lambda x: mes_order.index(x) if x in mes_order else 99
            )
            df_mes = df_mes.sort_values("_order").drop(columns=["_order"])

            fig_mes = px.bar(
                df_mes, x="mes_nombre", y="Total Egresos",
                title="Egresos Totales por Mes ($)",
                color_discrete_sequence=["#3b82f6"],
                template="plotly_white"
            )
            fig_mes.update_layout(
                xaxis_title="", yaxis_title="Monto ($)",
                plot_bgcolor="white", paper_bgcolor="white"
            )
            st.plotly_chart(fig_mes, use_container_width=True)

    # ── TAB 2: ANÁLISIS POR CATEGORÍA ─────────────────────────────────────────
    with tab2:
        st.markdown("#### 📊 Mix de Gastos por Categoría")

        if df_egresos.empty:
            st.info("Sin datos para analizar.")
        else:
            df_cat = df_egresos.copy()
            df_cat["categoria_safe"] = df_cat["categoria"].fillna("Sin Categoría")
            df_cat["monto_abs"] = df_cat["amount"].abs()

            df_grouped = df_cat.groupby("categoria_safe")["monto_abs"].sum().reset_index()
            df_grouped.columns = ["Categoría", "Total"]
            df_grouped = df_grouped.sort_values("Total", ascending=False)

            total_egresos_cat = df_grouped["Total"].sum()
            df_grouped["% del Total"] = (df_grouped["Total"] / total_egresos_cat * 100).round(1)

            g1, g2 = st.columns([1, 1])

            with g1:
                colors = [CATEGORY_COLORS.get(c, "#94a3b8") for c in df_grouped["Categoría"]]
                fig_pie = go.Figure(data=[go.Pie(
                    labels=df_grouped["Categoría"],
                    values=df_grouped["Total"],
                    hole=0.5,
                    marker_colors=colors,
                    textinfo="label+percent",
                    textfont_size=11,
                )])
                fig_pie.update_layout(
                    title="Distribución de Egresos",
                    showlegend=False,
                    margin=dict(t=40, b=20, l=20, r=20),
                    paper_bgcolor="white"
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with g2:
                fig_bar = px.bar(
                    df_grouped, x="Total", y="Categoría",
                    orientation="h",
                    title="Egresos por Categoría ($)",
                    color="Categoría",
                    color_discrete_map=CATEGORY_COLORS,
                    text=df_grouped["Total"].apply(lambda x: f"${x:,.0f}"),
                    template="plotly_white"
                )
                fig_bar.update_layout(
                    showlegend=False, xaxis_title="Monto ($)", yaxis_title="",
                    paper_bgcolor="white"
                )
                fig_bar.update_traces(textposition="outside")
                st.plotly_chart(fig_bar, use_container_width=True)

            # Tabla resumen
            st.markdown("#### 📋 Detalle por Categoría")
            df_display_cat = df_grouped.copy()
            df_display_cat["Total"] = df_display_cat["Total"].apply(lambda x: f"${x:,.0f}")
            df_display_cat["% del Total"] = df_display_cat["% del Total"].apply(lambda x: f"{x}%")
            st.dataframe(df_display_cat, use_container_width=True, hide_index=True)

    # ── TAB 3: CUADRATURA MENSUAL ─────────────────────────────────────────────
    with tab3:
        st.markdown("#### 📅 Estado de Cuadratura por Mes (Semáforo SAP)")
        st.caption("Verde = cuadra con el ledger | Amarillo = pendiente de revisión | Rojo = descuadre detectado")

        if df_egresos.empty:
            st.info("Sin movimientos bancarios para cuadrar.")
        else:
            df_egresos["mes_num"] = pd.to_datetime(df_egresos["bank_date"]).dt.month
            df_egresos["año"] = pd.to_datetime(df_egresos["bank_date"]).dt.year

            meses_presentes = df_egresos.groupby(["año", "mes_num"]).agg(
                total_banco=("amount", lambda x: abs(x.sum())),
                n_movimientos=("id", "count"),
                n_conciliados=("ledger_uuid", lambda x: x.notna().sum())
            ).reset_index()

            for _, row in meses_presentes.iterrows():
                mes_str = f"{MES_NOMBRE.get(int(row['mes_num']), '?')} {int(row['año'])}"
                pct_conciliado = (row["n_conciliados"] / row["n_movimientos"]) * 100 if row["n_movimientos"] > 0 else 0

                if pct_conciliado >= 100:
                    estado_color = "#dcfce7"
                    estado_border = "#22c55e"
                    estado_icon = "✅"
                    estado_text = "CUADRADO"
                elif pct_conciliado > 0:
                    estado_color = "#fef3c7"
                    estado_border = "#f59e0b"
                    estado_icon = "🟡"
                    estado_text = "EN REVISIÓN"
                else:
                    estado_color = "#fee2e2"
                    estado_border = "#ef4444"
                    estado_icon = "🔴"
                    estado_text = "PENDIENTE"

                st.markdown(f"""
                    <div style='background:{estado_color}; border-left:5px solid {estado_border};
                                padding:0.9rem 1.2rem; border-radius:10px; margin-bottom:0.6rem;
                                display:flex; justify-content:space-between; align-items:center;'>
                        <div>
                            <strong style='font-size:1rem;'>{estado_icon} {mes_str}</strong><br/>
                            <span style='font-size:0.82rem; color:#475569;'>
                                {int(row['n_movimientos'])} movimientos &nbsp;|&nbsp;
                                {int(row['n_conciliados'])} conciliados &nbsp;|&nbsp;
                                {pct_conciliado:.0f}% cubierto
                            </span>
                        </div>
                        <div style='text-align:right;'>
                            <strong style='font-size:1.1rem; color:#0f172a;'>
                                ${row['total_banco']:,.0f}
                            </strong><br/>
                            <span style='font-size:0.75rem; color:#64748b;'>{estado_text}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            # Alerta si hay cartola no cargada
            if df_abonos.empty:
                st.markdown("""
                    <div style='background:#fef3c7; border:1px solid #f59e0b; border-radius:10px;
                                padding:1rem; margin-top:1rem;'>
                        <b>⚠️ Cartola BCI no cargada</b><br/>
                        <small>Para una cuadratura completa, sube la cartola BCI en formato Excel
                        a <code>downloads/bci_dropzone/MOVIMIENTOS DEL MES/</code> y usa
                        <b>Sync & Carga → Cartola BCI</b>.</small>
                    </div>
                """, unsafe_allow_html=True)

    # ── TAB 4: MATCHMAKER ──────────────────────────────────────────────────────
    with tab4:
        st.markdown("#### 🔗 MatchMaker: Cruce Manual Banco ↔ Contabilidad")
        st.caption("Selecciona movimientos del banco y su contraparte en el ledger para cerrar el ciclo.")

        # Egresos huérfanos (no linked al ledger)
        df_huerfanos = df_egresos[df_egresos["ledger_uuid"].isna()].copy() if not df_egresos.empty else pd.DataFrame()

        c_left, c_sep, c_right = st.columns([1, 0.05, 1])

        with c_left:
            st.markdown("##### 🏦 BANCO (Sin Vincular)")
            if not df_huerfanos.empty:
                banco_sel = st.multiselect(
                    "Selecciona cargo(s) bancario(s):",
                    options=df_huerfanos["id"].tolist(),
                    format_func=lambda x: (
                        f"{df_huerfanos[df_huerfanos['id']==x]['bank_date'].values[0]} | "
                        f"${abs(df_huerfanos[df_huerfanos['id']==x]['amount'].values[0]):,.0f} | "
                        f"{df_huerfanos[df_huerfanos['id']==x]['description'].values[0][:45]}"
                    ),
                    key="mm_banco"
                )
                sum_banco = abs(df_huerfanos[df_huerfanos["id"].isin(banco_sel)]["amount"].sum()) if banco_sel else 0
                st.metric("Total Banco seleccionado", f"${sum_banco:,.0f}")
            else:
                st.success("✅ Sin egresos bancarios huérfanos.")
                sum_banco = 0

        with c_right:
            st.markdown("##### 📒 LEDGER (Pendientes)")
            if not df_pending.empty:
                ledger_sel = st.multiselect(
                    "Selecciona gasto(s) del ledger:",
                    options=df_pending["uuid"].tolist(),
                    format_func=lambda x: (
                        f"{df_pending[df_pending['uuid']==x]['due_date'].values[0]} | "
                        f"${df_pending[df_pending['uuid']==x]['amount_due'].values[0]:,.0f} | "
                        f"{df_pending[df_pending['uuid']==x]['description'].values[0][:45]}"
                    ),
                    key="mm_ledger"
                )
                sum_ledger = df_pending[df_pending["uuid"].isin(ledger_sel)]["amount_due"].sum() if ledger_sel else 0
                st.metric("Total Ledger seleccionado", f"${sum_ledger:,.0f}")
            else:
                st.info("Sin gastos pendientes en el ledger.")
                sum_ledger = 0

        # Barra de acción
        st.markdown("---")
        if sum_banco > 0 and sum_ledger > 0:
            diff = abs(sum_banco - sum_ledger)
            tolerance = 500  # CLP

            if diff <= tolerance:
                st.success(f"✅ CUADRA — Diferencia: ${diff:,.0f} (dentro de tolerancia ${tolerance})")
                if st.button("🔗 VINCULAR Y CONCILIAR", type="primary", use_container_width=True):
                    with engine.begin() as conn:
                        bank_ids_str = ",".join(map(str, banco_sel))
                        main_date = df_huerfanos[df_huerfanos["id"].isin(banco_sel)]["bank_date"].max()
                        for l_uuid in ledger_sel:
                            conn.execute(text("""
                                UPDATE expense_ledger
                                SET status = 'PAID_VERIFIED',
                                    paid_date = :pd,
                                    source_bank_id = :bid
                                WHERE uuid = :lid
                            """), {"pd": main_date, "bid": bank_ids_str, "lid": l_uuid})
                    st.success("✅ Conciliación registrada.")
                    st.rerun()
            else:
                st.error(f"❌ NO CUADRA — Diferencia: ${diff:,.0f}")
                col_d1, col_d2 = st.columns(2)
                col_d1.metric("Banco", f"${sum_banco:,.0f}")
                col_d2.metric("Ledger", f"${sum_ledger:,.0f}", delta=f"-${diff:,.0f}", delta_color="inverse")
