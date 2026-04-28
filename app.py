"""
DisinfoCode Interactive Dashboard — v2
Ejecutar: streamlit run app.py
"""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
from data.population import POPULATION
from data.sli_labels import label as make_label

# ── Configuración página ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="DisinfoCode · Comparativa de Plataformas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSV_PATH   = Path(__file__).parent / "output" / "metrics_raw.csv"
WAVE_ORDER = ["March 2025", "September 2025", "March 2026"]
EU_MEMBERS = [k for k in POPULATION if not k.startswith("Total")]

COLOR_SEQ  = px.colors.qualitative.Bold
COLOR_SEQ2 = px.colors.qualitative.Pastel

# ── Carga y limpieza de datos ──────────────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[df["value"].notna() & (df["value"] > 0)].copy()

    df["wave_label"] = pd.Categorical(df["wave_label"], categories=WAVE_ORDER, ordered=True)
    df["population"] = df["country"].map(POPULATION)
    df["value_per_100k"] = df.apply(
        lambda r: (r["value"] / r["population"] * 100_000)
        if pd.notna(r["population"]) and r["population"] > 0 else None,
        axis=1,
    )
    df["sli_label"] = df.apply(lambda r: make_label(r["sli_code"], r["sli_name"]), axis=1)
    return df


df_all = load_data()

platforms    = sorted(df_all["platform"].unique())
countries    = sorted(df_all["country"].unique())
chapters     = sorted(df_all["chapter"].dropna().unique())
sli_labels_all = sorted(df_all["sli_label"].unique())


def sli_opts(frame: pd.DataFrame) -> list[str]:
    return sorted(frame["sli_label"].unique())

def pick_sli(frame: pd.DataFrame, chosen: str) -> pd.DataFrame:
    return frame[frame["sli_label"] == chosen]

def apply_metric(frame: pd.DataFrame, mode: str, df_base: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Añade columna 'metric' según el modo seleccionado."""
    if mode == "% sobre Total EU":
        totals = (
            df_base[df_base["country"] == "Total EU"]
            .groupby(["wave_label", "sli_name"])["value"].sum().rename("total_eu")
        )
        frame = frame.merge(totals.reset_index(), on=["wave_label", "sli_name"], how="left")
        frame["metric"] = frame.apply(
            lambda r: r["value"] / r["total_eu"] * 100
            if pd.notna(r.get("total_eu")) and r["total_eu"] > 0 else None, axis=1
        )
        label = "% sobre Total EU"
    elif mode == "Por 100.000 habitantes":
        frame["metric"] = frame["value_per_100k"]
        label = "Por 100.000 hab."
    else:
        frame["metric"] = frame["value"]
        label = "Valor absoluto"
    return frame[frame["metric"].notna()], label


# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 Filtros globales")

    sel_waves     = st.multiselect("Ola / Wave", WAVE_ORDER, default=WAVE_ORDER)
    sel_platforms = st.multiselect("Plataforma", platforms, default=platforms)
    sel_chapters  = st.multiselect("Capítulo temático", chapters, default=chapters)

    scope = st.radio(
        "Ámbito geográfico",
        ["Solo totales EU/EEA", "Por estado miembro", "Ambos"],
    )
    if scope == "Solo totales EU/EEA":
        sel_countries = [c for c in countries if "Total" in c]
    elif scope == "Por estado miembro":
        sel_countries = st.multiselect("Países", EU_MEMBERS, default=EU_MEMBERS)
    else:
        sel_countries = countries

    metric_mode = st.radio(
        "Unidad de medida",
        ["Valor absoluto", "% sobre Total EU", "Por 100.000 habitantes"],
    )

    st.divider()
    sel_sli_filt = st.multiselect("Limitar a variables SLI", sli_labels_all)

    st.caption("Fuente: disinfocode.eu · Población: REST Countries API 2024")

# ── FILTRADO GLOBAL ────────────────────────────────────────────────────────────
df = df_all.copy()
if sel_waves:      df = df[df["wave_label"].isin(sel_waves)]
if sel_platforms:  df = df[df["platform"].isin(sel_platforms)]
if sel_chapters:   df = df[df["chapter"].isin(sel_chapters)]
if sel_countries:  df = df[df["country"].isin(sel_countries)]
if sel_sli_filt:   df = df[df["sli_label"].isin(sel_sli_filt)]

df, mlabel = apply_metric(df, metric_mode, df_all)

# ── CABECERA ───────────────────────────────────────────────────────────────────
st.title("📊 DisinfoCode · Comparativa de Plataformas Sociales")
st.caption("Código de Conducta sobre Desinformación (UE) — Waves 5, 6 y 8 (2025–2026)")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Registros", f"{len(df):,}")
c2.metric("Plataformas", df["platform"].nunique())
c3.metric("Variables SLI", df["sli_label"].nunique())
c4.metric("Países", df[~df["country"].str.contains("Total")]["country"].nunique())
st.divider()

# ── TABS ───────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "🏢 Por Plataforma",
    "🌍 Por País",
    "📈 Evolución temporal",
    "🔄 Comparativas avanzadas",
    "🌆 Top 10M",
    "🗺️ Mapa",
    "🔥 Heatmap",
    "📋 Tabla de datos",
])
tab1, tab2, tab3, tab4, tab4b, tab5, tab6, tab7 = tabs

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 1 — Por Plataforma                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab1:
    st.subheader("Comparativa por Plataforma")

    agg = df.groupby(["platform","wave_label","sli_label","chapter"])["metric"].sum().reset_index()
    opts = sli_opts(agg)
    if not opts:
        st.warning("Sin datos con los filtros actuales.")
    else:
        col_sel, col_chart = st.columns([3, 2])
        with col_sel:
            chosen = st.selectbox("Variable SLI", opts, key="t1_sli")
        with col_chart:
            chart_type = st.selectbox(
                "Tipo de gráfico",
                ["Barras agrupadas", "Barras apiladas", "Líneas", "Área", "Dispersión", "Treemap"],
                key="t1_chart",
            )

        d = pick_sli(agg, chosen)

        if chart_type == "Barras agrupadas":
            fig = px.bar(d, x="platform", y="metric", color="wave_label", barmode="group",
                         color_discrete_sequence=COLOR_SEQ,
                         labels={"metric": mlabel, "platform": "Plataforma", "wave_label": "Ola"},
                         title=f"{chosen} — Comparativa entre plataformas",
                         category_orders={"wave_label": WAVE_ORDER})
            fig.update_layout(xaxis_tickangle=-30)

        elif chart_type == "Barras apiladas":
            fig = px.bar(d, x="platform", y="metric", color="wave_label", barmode="stack",
                         color_discrete_sequence=COLOR_SEQ,
                         labels={"metric": mlabel, "platform": "Plataforma", "wave_label": "Ola"},
                         title=f"{chosen} — Acumulado por plataforma",
                         category_orders={"wave_label": WAVE_ORDER})
            fig.update_layout(xaxis_tickangle=-30)

        elif chart_type == "Líneas":
            fig = px.line(d, x="wave_label", y="metric", color="platform", markers=True,
                          color_discrete_sequence=COLOR_SEQ,
                          labels={"metric": mlabel, "wave_label": "Ola", "platform": "Plataforma"},
                          title=f"{chosen} — Evolución",
                          category_orders={"wave_label": WAVE_ORDER})
            fig.update_traces(line_width=2.5, marker_size=9)

        elif chart_type == "Área":
            fig = px.area(d, x="wave_label", y="metric", color="platform",
                          color_discrete_sequence=COLOR_SEQ,
                          labels={"metric": mlabel, "wave_label": "Ola", "platform": "Plataforma"},
                          title=f"{chosen} — Área acumulada",
                          category_orders={"wave_label": WAVE_ORDER})

        elif chart_type == "Dispersión":
            fig = px.scatter(d, x="platform", y="metric", color="wave_label", size="metric",
                             color_discrete_sequence=COLOR_SEQ,
                             labels={"metric": mlabel, "platform": "Plataforma", "wave_label": "Ola"},
                             title=f"{chosen} — Dispersión",
                             category_orders={"wave_label": WAVE_ORDER})

        else:  # Treemap
            fig = px.treemap(d, path=["wave_label","platform"], values="metric",
                             color="metric", color_continuous_scale="Blues",
                             title=f"{chosen} — Treemap")

        st.plotly_chart(fig, use_container_width=True)

        pivot = d.pivot_table(index="platform", columns="wave_label", values="metric", aggfunc="sum")
        pivot = pivot.reindex(columns=WAVE_ORDER).round(2)
        pivot.columns.name = None
        st.dataframe(pivot, use_container_width=True)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 2 — Por País                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab2:
    st.subheader("Comparativa por País")

    df_c = df[~df["country"].str.contains("Total", na=False)]
    if df_c.empty:
        st.warning("Selecciona 'Por estado miembro' o 'Ambos' en el filtro geográfico.")
    else:
        r1, r2, r3 = st.columns([3, 2, 2])
        with r1:
            chosen2 = st.selectbox("Variable SLI", sli_opts(df_c), key="t2_sli")
        with r2:
            wave2   = st.selectbox("Ola", [w for w in WAVE_ORDER if w in df_c["wave_label"].values], key="t2_wave")
        with r3:
            plat2   = st.selectbox("Plataforma", sorted(df_c["platform"].unique()), key="t2_plat")

        chart2 = st.radio(
            "Tipo de gráfico", ["Barras horizontales", "Barras verticales", "Burbuja (vs. población)", "Embudo"],
            horizontal=True, key="t2_chart"
        )

        d2 = (pick_sli(df_c, chosen2)
              .query("wave_label == @wave2 and platform == @plat2")
              .groupby("country")["metric"].sum().reset_index()
              .sort_values("metric", ascending=False))

        if d2.empty:
            st.info("Sin datos para esta combinación.")
        else:
            if chart2 == "Barras horizontales":
                fig = px.bar(d2, x="metric", y="country", orientation="h",
                             color="metric", color_continuous_scale="Blues",
                             labels={"metric": mlabel, "country": "País"},
                             title=f"{chosen2} · {plat2} · {wave2}")
                fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=700)

            elif chart2 == "Barras verticales":
                fig = px.bar(d2.sort_values("metric", ascending=True), x="country", y="metric",
                             color="metric", color_continuous_scale="Blues",
                             labels={"metric": mlabel, "country": "País"},
                             title=f"{chosen2} · {plat2} · {wave2}")
                fig.update_layout(xaxis_tickangle=-45, height=500)

            elif chart2 == "Burbuja (vs. población)":
                d2["population"] = d2["country"].map(POPULATION)
                d2 = d2.dropna(subset=["population"])
                fig = px.scatter(d2, x="population", y="metric", text="country",
                                 size="metric", color="metric", color_continuous_scale="Blues",
                                 labels={"metric": mlabel, "population": "Población", "country": "País"},
                                 title=f"{chosen2} — Métrica vs. Población")
                fig.update_traces(textposition="top center")

            else:  # Embudo
                fig = px.funnel(d2.head(15), x="metric", y="country",
                                labels={"metric": mlabel, "country": "País"},
                                title=f"{chosen2} · Top 15 países")

            st.plotly_chart(fig, use_container_width=True)

        # Comparativa entre olas
        st.subheader("Evolución entre olas · todos los países")
        chart2b = st.radio("Tipo de gráfico (olas)", ["Barras agrupadas", "Líneas", "Barras apiladas"], horizontal=True, key="t2b_chart")
        d2_wave = (pick_sli(df_c, chosen2).query("platform == @plat2")
                   .groupby(["country","wave_label"])["metric"].sum().reset_index())
        if not d2_wave.empty:
            kw = dict(x="country", y="metric", color="wave_label",
                      labels={"metric": mlabel, "country": "País", "wave_label": "Ola"},
                      category_orders={"wave_label": WAVE_ORDER},
                      color_discrete_sequence=COLOR_SEQ)
            if chart2b == "Barras agrupadas":
                fig2b = px.bar(d2_wave, barmode="group", **kw)
            elif chart2b == "Barras apiladas":
                fig2b = px.bar(d2_wave, barmode="stack", **kw)
            else:
                fig2b = px.line(d2_wave, markers=True, **kw)
            fig2b.update_layout(xaxis_tickangle=-45, height=450)
            st.plotly_chart(fig2b, use_container_width=True)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 3 — Evolución temporal                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab3:
    st.subheader("Evolución a lo largo de las tres olas")

    r1, r2, r3 = st.columns([3, 2, 2])
    with r1:
        chosen3  = st.selectbox("Variable SLI", sli_opts(df), key="t3_sli")
    with r2:
        country3 = st.selectbox("País / Ámbito", ["Total EU","Total EEA"]+EU_MEMBERS, key="t3_country")
    with r3:
        chart3 = st.selectbox("Tipo de gráfico", ["Líneas + marcadores","Barras agrupadas","Área","Barras apiladas"], key="t3_chart")

    d3 = (pick_sli(df, chosen3).query("country == @country3")
          .groupby(["wave_label","platform"])["metric"].sum().reset_index())

    if d3.empty:
        st.info("Sin datos para esta combinación.")
    else:
        kw3 = dict(x="wave_label", y="metric", color="platform",
                   labels={"metric": mlabel, "wave_label": "Ola", "platform": "Plataforma"},
                   title=f"{chosen3} — {country3}",
                   category_orders={"wave_label": WAVE_ORDER},
                   color_discrete_sequence=COLOR_SEQ)
        if chart3 == "Líneas + marcadores":
            fig3 = px.line(d3, markers=True, **kw3)
            fig3.update_traces(line_width=2.5, marker_size=10)
        elif chart3 == "Barras agrupadas":
            fig3 = px.bar(d3, barmode="group", **kw3)
        elif chart3 == "Área":
            fig3 = px.area(d3, **kw3)
        else:
            fig3 = px.bar(d3, barmode="stack", **kw3)
        st.plotly_chart(fig3, use_container_width=True)

        # Tabla de variaciones
        piv = d3.pivot_table(index="platform", columns="wave_label", values="metric")
        for i in range(1, len(WAVE_ORDER)):
            wp, wc = WAVE_ORDER[i-1], WAVE_ORDER[i]
            if wp in piv.columns and wc in piv.columns:
                piv[f"Δ% {wp[:3]}→{wc[:3]}"] = ((piv[wc]-piv[wp])/piv[wp].abs()*100).round(1)
        st.dataframe(piv.round(2), use_container_width=True)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 4 — Comparativas avanzadas                                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab4:
    st.subheader("Comparativas avanzadas")

    analysis = st.radio(
        "Tipo de análisis",
        [
            "A · Múltiples variables para una plataforma",
            "B · Dispersión entre dos períodos (países)",
            "C · Ranking de países · Top N",
            "D · Plataformas comparadas en un mismo país",
            "E · Gráfico de radar (múltiples variables)",
        ],
        horizontal=False,
        key="t4_analysis",
    )

    # ── A: Múltiples variables para una plataforma ─────────────────────────────
    if analysis.startswith("A"):
        st.markdown("**Selecciona una plataforma y varias variables SLI para compararlas.**")
        r1, r2 = st.columns([2, 3])
        with r1:
            plat_a = st.selectbox("Plataforma", platforms, key="t4a_plat")
            wave_a = st.selectbox("Ola", WAVE_ORDER, key="t4a_wave")
            chart_a = st.radio("Gráfico", ["Barras horizontales", "Barras verticales", "Treemap"], key="t4a_chart")
        with r2:
            scope_a = st.selectbox("País / Ámbito", ["Total EU","Total EEA"]+EU_MEMBERS, key="t4a_scope")
            slis_a = st.multiselect("Variables SLI (≥ 2)", sli_labels_all, default=sli_labels_all[:4], key="t4a_slis")

        da = (df[df["platform"]==plat_a & df["sli_label"].isin(slis_a)]
              if False else
              df[(df["platform"]==plat_a) & (df["sli_label"].isin(slis_a)) &
                 (df["wave_label"]==wave_a) & (df["country"]==scope_a)]
              .groupby("sli_label")["metric"].sum().reset_index()
              .sort_values("metric", ascending=False))

        if da.empty:
            st.info("Sin datos.")
        else:
            if chart_a == "Barras horizontales":
                fig_a = px.bar(da, x="metric", y="sli_label", orientation="h",
                               color="metric", color_continuous_scale="Blues",
                               labels={"metric": mlabel, "sli_label": "Variable SLI"},
                               title=f"{plat_a} · {wave_a} · {scope_a}")
                fig_a.update_layout(yaxis={"categoryorder":"total ascending"}, height=max(400, len(da)*35))
            elif chart_a == "Barras verticales":
                fig_a = px.bar(da, x="sli_label", y="metric",
                               color="metric", color_continuous_scale="Blues",
                               labels={"metric": mlabel, "sli_label": "Variable SLI"},
                               title=f"{plat_a} · {wave_a} · {scope_a}")
                fig_a.update_layout(xaxis_tickangle=-40)
            else:
                fig_a = px.treemap(da, path=["sli_label"], values="metric",
                                   color="metric", color_continuous_scale="Blues",
                                   title=f"{plat_a} · {wave_a} · {scope_a}")
            st.plotly_chart(fig_a, use_container_width=True)

    # ── B: Dispersión entre dos períodos ──────────────────────────────────────
    elif analysis.startswith("B"):
        st.markdown("**Compara el mismo indicador entre dos olas (eje X = ola 1, eje Y = ola 2) por país.**")
        r1, r2, r3 = st.columns(3)
        with r1:
            sli_b  = st.selectbox("Variable SLI", sli_labels_all, key="t4b_sli")
        with r2:
            plat_b = st.selectbox("Plataforma", platforms, key="t4b_plat")
        with r3:
            waves_b = st.select_slider("Olas a comparar", options=WAVE_ORDER,
                                       value=(WAVE_ORDER[0], WAVE_ORDER[-1]), key="t4b_waves")

        wave_x, wave_y = waves_b
        df_b = pick_sli(df[~df["country"].str.contains("Total")], sli_b)
        df_b = df_b[df_b["platform"] == plat_b]

        px_data = df_b[df_b["wave_label"]==wave_x].groupby("country")["metric"].sum().rename("x")
        py_data = df_b[df_b["wave_label"]==wave_y].groupby("country")["metric"].sum().rename("y")
        d_scatter = pd.concat([px_data, py_data], axis=1).dropna().reset_index()
        d_scatter["population"] = d_scatter["country"].map(POPULATION)

        if d_scatter.empty:
            st.info("No hay datos para las dos olas seleccionadas.")
        else:
            fig_b = px.scatter(
                d_scatter, x="x", y="y", text="country", size="population",
                color="country", size_max=50,
                labels={"x": f"{mlabel} · {wave_x}", "y": f"{mlabel} · {wave_y}", "country": "País"},
                title=f"{sli_b} · {plat_b} — {wave_x} vs {wave_y}",
            )
            # Línea de referencia diagonal
            mx = max(d_scatter[["x","y"]].max())
            fig_b.add_shape(type="line", x0=0, y0=0, x1=mx, y1=mx,
                            line=dict(dash="dash", color="gray"))
            fig_b.add_annotation(x=mx*0.9, y=mx*0.85, text="Sin cambio",
                                  showarrow=False, font=dict(color="gray"))
            fig_b.update_traces(textposition="top center")
            fig_b.update_layout(height=600, showlegend=False)
            st.plotly_chart(fig_b, use_container_width=True)
            st.caption("Puntos sobre la diagonal = aumento; bajo la diagonal = descenso entre las dos olas.")

    # ── C: Ranking Top N ──────────────────────────────────────────────────────
    elif analysis.startswith("C"):
        st.markdown("**Ranking de países para una variable SLI en una ola y plataforma determinadas.**")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            sli_c  = st.selectbox("Variable SLI", sli_labels_all, key="t4c_sli")
        with r2:
            wave_c = st.selectbox("Ola", WAVE_ORDER, key="t4c_wave")
        with r3:
            plat_c = st.selectbox("Plataforma", platforms, key="t4c_plat")
        with r4:
            topn   = st.slider("Top N países", 5, 30, 10, key="t4c_n")

        d_c = (pick_sli(df[~df["country"].str.contains("Total")], sli_c)
               .query("wave_label == @wave_c and platform == @plat_c")
               .groupby("country")["metric"].sum().reset_index()
               .sort_values("metric", ascending=False).head(topn))

        if d_c.empty:
            st.info("Sin datos.")
        else:
            d_c["rank"] = range(1, len(d_c)+1)
            fig_c = px.bar(
                d_c, x="metric", y="country", orientation="h",
                text="rank", color="metric", color_continuous_scale="Blues",
                labels={"metric": mlabel, "country": "País"},
                title=f"Top {topn} países · {sli_c} · {plat_c} · {wave_c}",
            )
            fig_c.update_layout(yaxis={"categoryorder":"total ascending"}, height=max(350, topn*38))
            fig_c.update_traces(texttemplate="#%{text}", textposition="inside")
            st.plotly_chart(fig_c, use_container_width=True)

            # Comparativa del mismo ranking en las otras olas
            st.markdown("**¿Cómo evolucionan esos países en las otras olas?**")
            top_countries = d_c["country"].tolist()
            d_c2 = (pick_sli(df[df["country"].isin(top_countries)], sli_c)
                    .query("platform == @plat_c")
                    .groupby(["country","wave_label"])["metric"].sum().reset_index())
            if not d_c2.empty:
                fig_c2 = px.line(d_c2, x="wave_label", y="metric", color="country",
                                 markers=True, color_discrete_sequence=px.colors.qualitative.Alphabet,
                                 labels={"metric": mlabel, "wave_label": "Ola", "country": "País"},
                                 category_orders={"wave_label": WAVE_ORDER},
                                 title=f"Evolución del Top {topn} · {sli_c} · {plat_c}")
                fig_c2.update_traces(line_width=2)
                st.plotly_chart(fig_c2, use_container_width=True)

    # ── D: Plataformas en un mismo país ───────────────────────────────────────
    elif analysis.startswith("D"):
        st.markdown("**Compara todas las plataformas para un país y variable concretos, en las tres olas.**")
        r1, r2, r3 = st.columns(3)
        with r1:
            sli_d     = st.selectbox("Variable SLI", sli_labels_all, key="t4d_sli")
        with r2:
            country_d = st.selectbox("País / Ámbito", ["Total EU","Total EEA"]+EU_MEMBERS, key="t4d_country")
        with r3:
            chart_d   = st.radio("Gráfico", ["Barras agrupadas","Líneas","Radar"], key="t4d_chart")

        d_d = (pick_sli(df, sli_d).query("country == @country_d")
               .groupby(["platform","wave_label"])["metric"].sum().reset_index())

        if d_d.empty:
            st.info("Sin datos.")
        else:
            if chart_d == "Barras agrupadas":
                fig_d = px.bar(d_d, x="platform", y="metric", color="wave_label", barmode="group",
                               color_discrete_sequence=COLOR_SEQ,
                               labels={"metric": mlabel, "platform": "Plataforma", "wave_label": "Ola"},
                               category_orders={"wave_label": WAVE_ORDER},
                               title=f"{sli_d} · {country_d}")
                fig_d.update_layout(xaxis_tickangle=-30)
                st.plotly_chart(fig_d, use_container_width=True)

            elif chart_d == "Líneas":
                fig_d = px.line(d_d, x="wave_label", y="metric", color="platform", markers=True,
                                color_discrete_sequence=COLOR_SEQ,
                                labels={"metric": mlabel, "wave_label": "Ola", "platform": "Plataforma"},
                                category_orders={"wave_label": WAVE_ORDER},
                                title=f"{sli_d} · {country_d}")
                fig_d.update_traces(line_width=2.5, marker_size=9)
                st.plotly_chart(fig_d, use_container_width=True)

            else:  # Radar
                fig_d = go.Figure()
                waves_radar = d_d["wave_label"].unique()
                plats = d_d["platform"].unique().tolist() + [d_d["platform"].unique()[0]]
                for wave in WAVE_ORDER:
                    sub = d_d[d_d["wave_label"]==wave]
                    vals = [sub[sub["platform"]==p]["metric"].sum() for p in d_d["platform"].unique()]
                    vals += [vals[0]]
                    fig_d.add_trace(go.Scatterpolar(r=vals, theta=plats, fill="toself", name=wave))
                fig_d.update_layout(polar=dict(radialaxis=dict(visible=True)),
                                    title=f"{sli_d} · {country_d} — Radar de plataformas",
                                    height=550)
                st.plotly_chart(fig_d, use_container_width=True)

    # ── E: Radar de múltiples variables ───────────────────────────────────────
    else:
        st.markdown("**Radar de múltiples variables SLI para una plataforma y ola.**")
        r1, r2, r3 = st.columns(3)
        with r1:
            plat_e  = st.selectbox("Plataforma", platforms, key="t4e_plat")
        with r2:
            wave_e  = st.selectbox("Ola", WAVE_ORDER, key="t4e_wave")
        with r3:
            scope_e = st.selectbox("País / Ámbito", ["Total EU","Total EEA"]+EU_MEMBERS, key="t4e_scope")

        slis_e = st.multiselect("Variables SLI a incluir", sli_labels_all,
                                default=sli_labels_all[:6], key="t4e_slis")

        d_e = (df[(df["platform"]==plat_e) & (df["wave_label"]==wave_e) &
                  (df["country"]==scope_e) & (df["sli_label"].isin(slis_e))]
               .groupby("sli_label")["metric"].sum().reset_index())

        if d_e.empty:
            st.info("Sin datos.")
        else:
            # Normalizar 0-1 para comparar escalas distintas
            d_e["metric_norm"] = d_e["metric"] / d_e["metric"].max()
            cats = d_e["sli_label"].tolist() + [d_e["sli_label"].iloc[0]]
            vals = d_e["metric_norm"].tolist() + [d_e["metric_norm"].iloc[0]]

            fig_e = go.Figure()
            fig_e.add_trace(go.Scatterpolar(
                r=vals, theta=cats, fill="toself", name=plat_e,
                line_color=COLOR_SEQ[0],
            ))
            fig_e.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0,1])),
                title=f"Perfil de {plat_e} · {wave_e} · {scope_e} (valores normalizados 0-1)",
                height=600,
            )
            st.plotly_chart(fig_e, use_container_width=True)
            st.caption("Los valores se normalizan (0-1) para poder comparar variables con escalas diferentes.")
            st.dataframe(d_e[["sli_label","metric"]].rename(
                columns={"sli_label":"Variable","metric":mlabel}
            ).set_index("Variable"), use_container_width=True)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 4B — Top 10M                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
TOP10M_COUNTRIES = sorted(
    [c for c, p in POPULATION.items() if p >= 10_000_000 and not c.startswith("Total")]
)
TOP10M_POPS = {c: POPULATION[c] for c in TOP10M_COUNTRIES}

with tab4b:
    st.subheader("🌆 Análisis Top 10M — Países con más de 10 millones de habitantes")

    # Información de los países
    with st.expander("ℹ️ Países incluidos en este análisis"):
        pop_df = pd.DataFrame(
            [(c, f"{TOP10M_POPS[c]:,}") for c in sorted(TOP10M_COUNTRIES, key=lambda x: -TOP10M_POPS[x])],
            columns=["País", "Población (2024)"],
        )
        st.dataframe(pop_df.set_index("País"), use_container_width=True)

    # Filtrar datos al subconjunto Top 10M
    df_10m = df[df["country"].isin(TOP10M_COUNTRIES)].copy()

    if df_10m.empty:
        st.warning("Sin datos. Asegúrate de seleccionar 'Por estado miembro' o 'Ambos' en el filtro geográfico.")
    else:
        analysis_10m = st.radio(
            "Tipo de análisis",
            [
                "1 · Una variable · Todos los países y plataformas",
                "2 · Varias variables · Una plataforma",
                "3 · Evolución temporal · Top 10M",
                "4 · Comparativa entre dos olas · Dispersión",
                "5 · Heatmap País × Plataforma",
            ],
            horizontal=False,
            key="t4b_mode",
        )

        # ── 1: Una variable, todos los países ─────────────────────────────────
        if analysis_10m.startswith("1"):
            r1, r2, r3 = st.columns(3)
            with r1:
                sli_10 = st.selectbox("Variable SLI", sli_opts(df_10m), key="t4b_1_sli")
            with r2:
                wave_10 = st.selectbox("Ola", [w for w in WAVE_ORDER if w in df_10m["wave_label"].values], key="t4b_1_wave")
            with r3:
                chart_10 = st.radio("Gráfico", ["Barras agrupadas por país", "Barras agrupadas por plataforma", "Líneas", "Mapa Top 10M"], horizontal=False, key="t4b_1_chart")

            d10 = (pick_sli(df_10m, sli_10)
                   .query("wave_label == @wave_10")
                   .groupby(["country", "platform"])["metric"].sum().reset_index())

            if d10.empty:
                st.info("Sin datos para esta combinación.")
            else:
                if chart_10 == "Barras agrupadas por país":
                    fig10 = px.bar(
                        d10, x="country", y="metric", color="platform", barmode="group",
                        color_discrete_sequence=COLOR_SEQ,
                        labels={"metric": mlabel, "country": "País", "platform": "Plataforma"},
                        title=f"{sli_10} · {wave_10} — Top 10M países",
                    )
                    fig10.update_layout(xaxis_tickangle=-30, height=500)

                elif chart_10 == "Barras agrupadas por plataforma":
                    fig10 = px.bar(
                        d10, x="platform", y="metric", color="country", barmode="group",
                        color_discrete_sequence=px.colors.qualitative.Alphabet,
                        labels={"metric": mlabel, "country": "País", "platform": "Plataforma"},
                        title=f"{sli_10} · {wave_10} — Top 10M por plataforma",
                    )
                    fig10.update_layout(xaxis_tickangle=-30, height=500)

                elif chart_10 == "Líneas":
                    fig10 = px.line(
                        d10, x="country", y="metric", color="platform", markers=True,
                        color_discrete_sequence=COLOR_SEQ,
                        labels={"metric": mlabel, "country": "País", "platform": "Plataforma"},
                        title=f"{sli_10} · {wave_10} — Top 10M países",
                    )
                    fig10.update_layout(xaxis_tickangle=-30)

                else:  # Mapa Top 10M
                    d10_map = d10.groupby("country")["metric"].sum().reset_index()
                    d10_map["country_plot"] = d10_map["country"].replace({"Czech Republic": "Czechia"})
                    fig10 = px.choropleth(
                        d10_map, locations="country_plot", locationmode="country names",
                        color="metric", color_continuous_scale="Blues", scope="europe",
                        labels={"metric": mlabel, "country_plot": "País"},
                        title=f"{sli_10} · {wave_10} — Top 10M",
                    )
                    fig10.update_layout(height=500)

                st.plotly_chart(fig10, use_container_width=True)

                # Tabla pivot país × plataforma
                pivot10 = d10.pivot_table(index="country", columns="platform", values="metric", aggfunc="sum").round(2)
                pivot10.index.name = "País"
                st.dataframe(pivot10, use_container_width=True)

        # ── 2: Varias variables, una plataforma ───────────────────────────────
        elif analysis_10m.startswith("2"):
            r1, r2 = st.columns([2, 3])
            with r1:
                plat_10b = st.selectbox("Plataforma", sorted(df_10m["platform"].unique()), key="t4b_2_plat")
                wave_10b = st.selectbox("Ola", [w for w in WAVE_ORDER if w in df_10m["wave_label"].values], key="t4b_2_wave")
                chart_10b = st.radio("Gráfico", ["Barras agrupadas", "Heatmap variable × país", "Treemap"], key="t4b_2_chart")
            with r2:
                slis_10b = st.multiselect(
                    "Variables SLI (selecciona varias)",
                    sli_opts(df_10m),
                    default=sli_opts(df_10m)[:3],
                    key="t4b_2_slis",
                )

            d10b = (df_10m[df_10m["sli_label"].isin(slis_10b)]
                    .query("platform == @plat_10b and wave_label == @wave_10b")
                    .groupby(["country", "sli_label"])["metric"].sum().reset_index())

            if d10b.empty:
                st.info("Sin datos.")
            else:
                if chart_10b == "Barras agrupadas":
                    fig10b = px.bar(
                        d10b, x="country", y="metric", color="sli_label", barmode="group",
                        color_discrete_sequence=COLOR_SEQ,
                        labels={"metric": mlabel, "country": "País", "sli_label": "Variable SLI"},
                        title=f"{plat_10b} · {wave_10b} — Variables × Países Top 10M",
                    )
                    fig10b.update_layout(xaxis_tickangle=-30, height=520)

                elif chart_10b == "Heatmap variable × país":
                    piv10b = d10b.pivot_table(index="sli_label", columns="country", values="metric", aggfunc="sum")
                    fig10b = px.imshow(
                        piv10b, color_continuous_scale="Blues", aspect="auto",
                        labels={"color": mlabel},
                        title=f"{plat_10b} · {wave_10b} — Heatmap variables × países",
                    )
                    fig10b.update_layout(height=max(350, len(piv10b) * 45))

                else:  # Treemap
                    fig10b = px.treemap(
                        d10b, path=["country", "sli_label"], values="metric",
                        color="metric", color_continuous_scale="Blues",
                        title=f"{plat_10b} · {wave_10b} — Treemap países > 10M",
                    )
                    fig10b.update_layout(height=600)

                st.plotly_chart(fig10b, use_container_width=True)

        # ── 3: Evolución temporal ──────────────────────────────────────────────
        elif analysis_10m.startswith("3"):
            r1, r2, r3 = st.columns(3)
            with r1:
                sli_10c = st.selectbox("Variable SLI", sli_opts(df_10m), key="t4b_3_sli")
            with r2:
                plat_10c = st.selectbox("Plataforma", sorted(df_10m["platform"].unique()), key="t4b_3_plat")
            with r3:
                chart_10c = st.radio("Gráfico", ["Líneas por país", "Barras agrupadas por ola", "Área"], key="t4b_3_chart")

            d10c = (pick_sli(df_10m, sli_10c)
                    .query("platform == @plat_10c")
                    .groupby(["country", "wave_label"])["metric"].sum().reset_index())

            if d10c.empty:
                st.info("Sin datos.")
            else:
                kw10c = dict(
                    x="wave_label", y="metric", color="country",
                    color_discrete_sequence=px.colors.qualitative.Alphabet,
                    labels={"metric": mlabel, "wave_label": "Ola", "country": "País"},
                    category_orders={"wave_label": WAVE_ORDER},
                    title=f"{sli_10c} · {plat_10c} — Evolución países Top 10M",
                )
                if chart_10c == "Líneas por país":
                    fig10c = px.line(d10c, markers=True, **kw10c)
                    fig10c.update_traces(line_width=2.5, marker_size=9)
                elif chart_10c == "Barras agrupadas por ola":
                    fig10c = px.bar(d10c, barmode="group", **kw10c)
                else:
                    fig10c = px.area(d10c, **kw10c)

                fig10c.update_layout(height=520)
                st.plotly_chart(fig10c, use_container_width=True)

                # Tabla de variaciones %
                piv10c = d10c.pivot_table(index="country", columns="wave_label", values="metric")
                piv10c.index.name = "País"
                for i in range(1, len(WAVE_ORDER)):
                    wp, wc = WAVE_ORDER[i-1], WAVE_ORDER[i]
                    if wp in piv10c.columns and wc in piv10c.columns:
                        piv10c[f"Δ% {wp[:3]}→{wc[:3]}"] = (
                            (piv10c[wc] - piv10c[wp]) / piv10c[wp].abs() * 100
                        ).round(1)
                st.dataframe(piv10c.round(2), use_container_width=True)

        # ── 4: Dispersión entre dos olas ──────────────────────────────────────
        elif analysis_10m.startswith("4"):
            r1, r2, r3 = st.columns(3)
            with r1:
                sli_10d = st.selectbox("Variable SLI", sli_opts(df_10m), key="t4b_4_sli")
            with r2:
                plat_10d = st.selectbox("Plataforma", sorted(df_10m["platform"].unique()), key="t4b_4_plat")
            with r3:
                waves_10d = st.select_slider(
                    "Olas a comparar", options=WAVE_ORDER,
                    value=(WAVE_ORDER[0], WAVE_ORDER[-1]), key="t4b_4_waves",
                )

            wx, wy = waves_10d
            base_d = pick_sli(df_10m, sli_10d).query("platform == @plat_10d")
            px_d = base_d[base_d["wave_label"]==wx].groupby("country")["metric"].sum().rename("x")
            py_d = base_d[base_d["wave_label"]==wy].groupby("country")["metric"].sum().rename("y")
            d10d = pd.concat([px_d, py_d], axis=1).dropna().reset_index()
            d10d["population"] = d10d["country"].map(POPULATION)

            if d10d.empty:
                st.info("Sin datos para las dos olas seleccionadas.")
            else:
                fig10d = px.scatter(
                    d10d, x="x", y="y", text="country",
                    size="population", color="country", size_max=60,
                    color_discrete_sequence=px.colors.qualitative.Alphabet,
                    labels={"x": f"{mlabel} · {wx}", "y": f"{mlabel} · {wy}", "country": "País"},
                    title=f"{sli_10d} · {plat_10d} — {wx} vs {wy} · Top 10M",
                )
                mx = max(d10d[["x","y"]].max())
                fig10d.add_shape(type="line", x0=0, y0=0, x1=mx, y1=mx,
                                 line=dict(dash="dash", color="gray"))
                fig10d.add_annotation(x=mx*0.88, y=mx*0.82, text="Sin cambio",
                                       showarrow=False, font=dict(color="gray", size=11))
                fig10d.update_traces(textposition="top center")
                fig10d.update_layout(height=580, showlegend=False)
                st.plotly_chart(fig10d, use_container_width=True)
                st.caption("Puntos sobre la diagonal = aumento; bajo la diagonal = descenso entre las dos olas.")

                d10d["variación %"] = ((d10d["y"] - d10d["x"]) / d10d["x"].abs() * 100).round(1)
                st.dataframe(
                    d10d[["country","x","y","variación %"]].rename(
                        columns={"country":"País","x":wx,"y":wy}
                    ).set_index("País").sort_values("variación %", ascending=False),
                    use_container_width=True,
                )

        # ── 5: Heatmap País × Plataforma ──────────────────────────────────────
        else:
            r1, r2 = st.columns(2)
            with r1:
                sli_10e = st.selectbox("Variable SLI", sli_opts(df_10m), key="t4b_5_sli")
            with r2:
                wave_10e = st.selectbox("Ola", [w for w in WAVE_ORDER if w in df_10m["wave_label"].values], key="t4b_5_wave")

            d10e = (pick_sli(df_10m, sli_10e)
                    .query("wave_label == @wave_10e")
                    .groupby(["country","platform"])["metric"].sum()
                    .reset_index())

            if d10e.empty:
                st.info("Sin datos.")
            else:
                piv10e = d10e.pivot_table(index="country", columns="platform", values="metric", aggfunc="sum")
                piv10e.index.name = "País"

                scale_10e = st.select_slider("Escala de color", ["Blues","Viridis","RdYlGn","Plasma"], value="Blues", key="t4b_5_scale")
                fig10e = px.imshow(
                    piv10e, color_continuous_scale=scale_10e, aspect="auto",
                    labels={"color": mlabel},
                    title=f"{sli_10e} · {wave_10e} — Heatmap País × Plataforma (Top 10M)",
                )
                fig10e.update_layout(height=500)
                st.plotly_chart(fig10e, use_container_width=True)

                st.dataframe(piv10e.round(2), use_container_width=True)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 5 — Mapa                                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab5:
    st.subheader("Mapa de Europa")

    df_map = df[~df["country"].str.contains("Total", na=False)]
    if df_map.empty:
        st.warning("Selecciona 'Por estado miembro' en los filtros.")
    else:
        r1, r2, r3 = st.columns(3)
        with r1:
            chosen5 = st.selectbox("Variable SLI", sli_opts(df_map), key="t5_sli")
        with r2:
            wave5   = st.selectbox("Ola", [w for w in WAVE_ORDER if w in df_map["wave_label"].values], key="t5_wave")
        with r3:
            plat5   = st.selectbox("Plataforma", sorted(df_map["platform"].unique()), key="t5_plat")

        d5 = (pick_sli(df_map, chosen5)
              .query("wave_label == @wave5 and platform == @plat5")
              .groupby("country")["metric"].sum().reset_index())
        d5["country_plot"] = d5["country"].replace({"Czech Republic": "Czechia"})

        if d5.empty:
            st.info("Sin datos para esta combinación.")
        else:
            fig5 = px.choropleth(
                d5, locations="country_plot", locationmode="country names",
                color="metric", color_continuous_scale="Blues", scope="europe",
                labels={"metric": mlabel, "country_plot": "País"},
                title=f"{chosen5} · {plat5} · {wave5}",
            )
            fig5.update_layout(height=620)
            st.plotly_chart(fig5, use_container_width=True)

            # Segunda ola para comparar
            st.subheader("Comparativa de dos olas en mapa")
            wave5b = st.selectbox("Segunda ola", [w for w in WAVE_ORDER if w != wave5], key="t5_wave2")
            d5b = (pick_sli(df_map, chosen5)
                   .query("wave_label == @wave5b and platform == @plat5")
                   .groupby("country")["metric"].sum().reset_index())
            d5b["country_plot"] = d5b["country"].replace({"Czech Republic": "Czechia"})
            if not d5b.empty:
                ca, cb = st.columns(2)
                with ca:
                    f5a = px.choropleth(d5, locations="country_plot", locationmode="country names",
                                        color="metric", color_continuous_scale="Blues", scope="europe",
                                        title=wave5)
                    f5a.update_layout(height=380)
                    st.plotly_chart(f5a, use_container_width=True)
                with cb:
                    f5b = px.choropleth(d5b, locations="country_plot", locationmode="country names",
                                        color="metric", color_continuous_scale="Blues", scope="europe",
                                        title=wave5b)
                    f5b.update_layout(height=380)
                    st.plotly_chart(f5b, use_container_width=True)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 6 — Heatmap                                                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab6:
    st.subheader("Heatmap comparativo")

    r1, r2, r3 = st.columns(3)
    with r1:
        hx = st.selectbox("Eje X", ["Plataforma","País","Ola","Variable SLI"], key="t6_x")
    with r2:
        hy = st.selectbox("Eje Y", ["País","Plataforma","Variable SLI","Ola"], key="t6_y")
    with r3:
        chosen6 = st.selectbox("Variable SLI (filtro)", ["Todas"]+sli_opts(df), key="t6_sli")

    d6 = df if chosen6 == "Todas" else pick_sli(df, chosen6)

    xmap = {"Plataforma":"platform","País":"country","Ola":"wave_label","Variable SLI":"sli_label"}
    ymap = {"País":"country","Plataforma":"platform","Variable SLI":"sli_label","Ola":"wave_label"}
    xc, yc = xmap[hx], ymap[hy]

    if xc == yc:
        st.warning("Selecciona ejes diferentes.")
    elif d6.empty:
        st.info("Sin datos.")
    else:
        piv6 = d6.pivot_table(index=yc, columns=xc, values="metric", aggfunc="sum")
        scale = st.select_slider("Escala de color", ["Blues","Viridis","RdYlGn","Plasma","Turbo"], value="Blues", key="t6_scale")
        fig6 = px.imshow(piv6, color_continuous_scale=scale, aspect="auto",
                         labels={"color": mlabel},
                         title=f"Heatmap: {hy} × {hx}" + (f" · {chosen6}" if chosen6 != "Todas" else ""))
        fig6.update_layout(height=max(420, len(piv6)*22))
        st.plotly_chart(fig6, use_container_width=True)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 7 — Tabla de datos                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab7:
    st.subheader("Tabla de datos filtrados")

    cols = ["wave_label","platform","chapter","sli_label","country",
            "metric_name","metric","value","population","value_per_100k","methodology"]
    cols = [c for c in cols if c in df.columns]

    df_show = df[cols].rename(columns={
        "wave_label":"Ola","platform":"Plataforma","chapter":"Capítulo",
        "sli_label":"Variable SLI","country":"País","metric_name":"Métrica",
        "metric": mlabel,"value":"Valor original",
        "population":"Población","value_per_100k":"Por 100k hab.","methodology":"Metodología",
    })

    # Filtro rápido de texto
    search = st.text_input("🔎 Buscar en tabla", placeholder="país, plataforma, variable…", key="t7_search")
    if search:
        mask = df_show.apply(lambda col: col.astype(str).str.contains(search, case=False, na=False)).any(axis=1)
        df_show = df_show[mask]

    st.dataframe(df_show, use_container_width=True, height=520)
    st.caption(f"{len(df_show):,} filas mostradas")

    csv_bytes = df_show.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("⬇️ Descargar CSV filtrado", csv_bytes,
                       file_name="disinfocode_filtrado.csv", mime="text/csv")
