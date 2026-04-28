"""
DisinfoCode Interactive Dashboard
Ejecutar: streamlit run app.py
"""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
from data.population import POPULATION

# ── Configuración ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DisinfoCode · Comparativa de Plataformas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSV_PATH = Path(__file__).parent / "output" / "metrics_raw.csv"
WAVE_ORDER = ["March 2025", "September 2025", "March 2026"]
EU_MEMBERS = [k for k in POPULATION if not k.startswith("Total")]


# ── Carga de datos ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df = df[df["value"].notna()].copy()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[df["value"].notna()]
    df["wave_label"] = pd.Categorical(df["wave_label"], categories=WAVE_ORDER, ordered=True)
    df["population"] = df["country"].map(POPULATION)
    df["value_per_100k"] = df.apply(
        lambda r: (r["value"] / r["population"] * 100_000)
        if pd.notna(r["population"]) and r["population"] > 0 else None,
        axis=1,
    )
    return df


df_all = load_data()

platforms = sorted(df_all["platform"].unique())
countries = sorted(df_all["country"].unique())
chapters  = sorted(df_all["chapter"].dropna().unique())
sli_names = sorted(df_all["sli_name"].unique())

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 Filtros")

    sel_waves = st.multiselect("Ola / Wave", WAVE_ORDER, default=WAVE_ORDER)
    sel_platforms = st.multiselect("Plataforma", platforms, default=platforms)
    sel_chapters = st.multiselect("Capítulo temático", chapters, default=chapters)

    country_scope = st.radio("Ámbito geográfico", ["Solo totales EU/EEA", "Por país (estados miembro)", "Ambos"])
    if country_scope == "Solo totales EU/EEA":
        sel_countries = [c for c in countries if "Total" in c]
    elif country_scope == "Por país (estados miembro)":
        sel_countries = st.multiselect("Países", EU_MEMBERS, default=EU_MEMBERS)
    else:
        sel_countries = countries

    metric_mode = st.radio("Métrica", ["Valor absoluto", "% sobre Total EU", "Por 100.000 habitantes"])

    st.divider()
    sel_slis = st.multiselect("Filtrar por SLI específico", sli_names, default=[])

    st.caption("Fuente: disinfocode.eu · Población: REST Countries API 2024")

# ── Filtrado ───────────────────────────────────────────────────────────────────
df = df_all.copy()
if sel_waves:      df = df[df["wave_label"].isin(sel_waves)]
if sel_platforms:  df = df[df["platform"].isin(sel_platforms)]
if sel_chapters:   df = df[df["chapter"].isin(sel_chapters)]
if sel_countries:  df = df[df["country"].isin(sel_countries)]
if sel_slis:       df = df[df["sli_name"].isin(sel_slis)]

# Normalización de la métrica
if metric_mode == "% sobre Total EU":
    totals_eu = (
        df_all[df_all["country"] == "Total EU"]
        .groupby(["wave_label", "sli_name"])["value"]
        .sum()
        .rename("total_eu")
    )
    df = df.merge(totals_eu.reset_index(), on=["wave_label", "sli_name"], how="left")
    df["metric"] = df.apply(
        lambda r: (r["value"] / r["total_eu"] * 100) if pd.notna(r.get("total_eu")) and r["total_eu"] > 0 else None,
        axis=1,
    )
    metric_label = "% sobre Total EU"
elif metric_mode == "Por 100.000 habitantes":
    df["metric"] = df["value_per_100k"]
    metric_label = "Por 100.000 hab."
else:
    df["metric"] = df["value"]
    metric_label = "Valor absoluto"

df = df[df["metric"].notna()]

# ── Cabecera ───────────────────────────────────────────────────────────────────
st.title("📊 DisinfoCode · Comparativa de Plataformas Sociales")
st.caption("Código de Conducta sobre Desinformación (UE) — Waves 5, 6 y 8 (2025–2026)")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Filas seleccionadas", f"{len(df):,}")
col2.metric("Plataformas", df["platform"].nunique())
col3.metric("SLIs", df["sli_name"].nunique())
col4.metric("Países", df[~df["country"].str.contains("Total")]["country"].nunique())

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏢 Por Plataforma",
    "🌍 Por País",
    "📈 Evolución temporal",
    "🗺️ Mapa",
    "🔥 Heatmap",
    "📋 Tabla de datos",
])

# ────────────────────────────────────────────────────────────────────────────────
# TAB 1 — Por Plataforma
# ────────────────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Comparativa por Plataforma")

    agg_platform = (
        df.groupby(["platform", "wave_label", "sli_name", "chapter"])["metric"]
        .sum()
        .reset_index()
    )

    # Selector de SLI para este gráfico
    sli_opts = sorted(agg_platform["sli_name"].unique())
    if not sli_opts:
        st.warning("Sin datos con los filtros actuales.")
    else:
        chosen_sli = st.selectbox("Selecciona un SLI para visualizar", sli_opts, key="sli_plat")
        df_sli = agg_platform[agg_platform["sli_name"] == chosen_sli]

        col_a, col_b = st.columns(2)
        with col_a:
            fig = px.bar(
                df_sli, x="platform", y="metric", color="wave_label",
                barmode="group",
                color_discrete_sequence=px.colors.qualitative.Bold,
                labels={"metric": metric_label, "platform": "Plataforma", "wave_label": "Ola"},
                title=f"{chosen_sli} — Comparativa entre plataformas",
                category_orders={"wave_label": WAVE_ORDER},
            )
            fig.update_layout(xaxis_tickangle=-30, legend_title="Ola")
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig2 = px.bar(
                df_sli, x="wave_label", y="metric", color="platform",
                barmode="group",
                color_discrete_sequence=px.colors.qualitative.Pastel,
                labels={"metric": metric_label, "wave_label": "Ola", "platform": "Plataforma"},
                title=f"{chosen_sli} — Evolución por ola",
                category_orders={"wave_label": WAVE_ORDER},
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Tabla resumen
        pivot = df_sli.pivot_table(
            index="platform", columns="wave_label", values="metric", aggfunc="sum"
        ).reindex(columns=WAVE_ORDER)
        pivot.columns.name = None
        pivot = pivot.round(2)
        st.dataframe(pivot.style.background_gradient(cmap="Blues"), use_container_width=True)

# ────────────────────────────────────────────────────────────────────────────────
# TAB 2 — Por País
# ────────────────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Comparativa por País")

    df_country = df[~df["country"].str.contains("Total", na=False)]
    if df_country.empty:
        st.warning("Selecciona 'Por país (estados miembro)' o 'Ambos' en el filtro geográfico.")
    else:
        sli_opts2 = sorted(df_country["sli_name"].unique())
        chosen_sli2 = st.selectbox("Selecciona un SLI", sli_opts2, key="sli_country")
        chosen_wave2 = st.selectbox("Ola", [w for w in WAVE_ORDER if w in df_country["wave_label"].values], key="wave_country")
        chosen_plat2 = st.selectbox("Plataforma", sorted(df_country["platform"].unique()), key="plat_country")

        df_c = df_country[
            (df_country["sli_name"] == chosen_sli2) &
            (df_country["wave_label"] == chosen_wave2) &
            (df_country["platform"] == chosen_plat2)
        ].groupby("country")["metric"].sum().reset_index().sort_values("metric", ascending=False)

        if df_c.empty:
            st.info("Sin datos para esta combinación.")
        else:
            fig3 = px.bar(
                df_c, x="metric", y="country", orientation="h",
                color="metric", color_continuous_scale="Blues",
                labels={"metric": metric_label, "country": "País"},
                title=f"{chosen_sli2} · {chosen_plat2} · {chosen_wave2}",
            )
            fig3.update_layout(yaxis={"categoryorder": "total ascending"}, height=700)
            st.plotly_chart(fig3, use_container_width=True)

        # Comparativa entre olas para el país seleccionado
        st.subheader("Comparativa entre olas por país")
        agg_c_wave = (
            df_country[
                (df_country["sli_name"] == chosen_sli2) &
                (df_country["platform"] == chosen_plat2)
            ]
            .groupby(["country", "wave_label"])["metric"].sum()
            .reset_index()
        )
        if not agg_c_wave.empty:
            fig4 = px.bar(
                agg_c_wave, x="country", y="metric", color="wave_label",
                barmode="group",
                color_discrete_sequence=px.colors.qualitative.Bold,
                labels={"metric": metric_label, "country": "País", "wave_label": "Ola"},
                category_orders={"wave_label": WAVE_ORDER},
            )
            fig4.update_layout(xaxis_tickangle=-45, height=450)
            st.plotly_chart(fig4, use_container_width=True)

# ────────────────────────────────────────────────────────────────────────────────
# TAB 3 — Evolución temporal
# ────────────────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Evolución a lo largo de las tres olas")

    sli_opts3 = sorted(df["sli_name"].unique())
    if not sli_opts3:
        st.warning("Sin datos.")
    else:
        chosen_sli3 = st.selectbox("SLI", sli_opts3, key="sli_evo")
        scope_country3 = st.selectbox(
            "País / Ámbito",
            ["Total EU", "Total EEA"] + EU_MEMBERS,
            key="country_evo",
        )

        df_evo = (
            df[
                (df["sli_name"] == chosen_sli3) &
                (df["country"] == scope_country3)
            ]
            .groupby(["wave_label", "platform"])["metric"]
            .sum()
            .reset_index()
        )

        if df_evo.empty:
            st.info("Sin datos para esta combinación.")
        else:
            fig5 = px.line(
                df_evo, x="wave_label", y="metric", color="platform",
                markers=True,
                color_discrete_sequence=px.colors.qualitative.Bold,
                labels={"metric": metric_label, "wave_label": "Ola", "platform": "Plataforma"},
                title=f"{chosen_sli3} — {scope_country3}",
                category_orders={"wave_label": WAVE_ORDER},
            )
            fig5.update_traces(line_width=2.5, marker_size=10)
            st.plotly_chart(fig5, use_container_width=True)

            # Variación %
            pivot_evo = df_evo.pivot_table(index="platform", columns="wave_label", values="metric")
            for i in range(1, len(WAVE_ORDER)):
                w_prev, w_curr = WAVE_ORDER[i - 1], WAVE_ORDER[i]
                if w_prev in pivot_evo.columns and w_curr in pivot_evo.columns:
                    pivot_evo[f"Δ {w_prev[:3]}→{w_curr[:3]}"] = (
                        (pivot_evo[w_curr] - pivot_evo[w_prev]) / pivot_evo[w_prev].abs() * 100
                    ).round(1)
            st.dataframe(pivot_evo.round(2), use_container_width=True)

# ────────────────────────────────────────────────────────────────────────────────
# TAB 4 — Mapa
# ────────────────────────────────────────────────────────────────────────────────
with tab4:
    st.subheader("Mapa de Europa")

    df_map = df[~df["country"].str.contains("Total", na=False)]
    if df_map.empty:
        st.warning("Selecciona 'Por país (estados miembro)' en los filtros.")
    else:
        sli_opts4 = sorted(df_map["sli_name"].unique())
        chosen_sli4 = st.selectbox("SLI", sli_opts4, key="sli_map")
        chosen_wave4 = st.selectbox("Ola", [w for w in WAVE_ORDER if w in df_map["wave_label"].values], key="wave_map")
        chosen_plat4 = st.selectbox("Plataforma", sorted(df_map["platform"].unique()), key="plat_map")

        df_m = (
            df_map[
                (df_map["sli_name"] == chosen_sli4) &
                (df_map["wave_label"] == chosen_wave4) &
                (df_map["platform"] == chosen_plat4)
            ]
            .groupby("country")["metric"]
            .sum()
            .reset_index()
        )
        # Corrige nombre para Plotly
        df_m["country_plot"] = df_m["country"].replace({"Czech Republic": "Czechia"})

        if df_m.empty:
            st.info("Sin datos para esta combinación.")
        else:
            fig6 = px.choropleth(
                df_m,
                locations="country_plot",
                locationmode="country names",
                color="metric",
                color_continuous_scale="Blues",
                scope="europe",
                labels={"metric": metric_label, "country_plot": "País"},
                title=f"{chosen_sli4} · {chosen_plat4} · {chosen_wave4}",
            )
            fig6.update_layout(height=600)
            st.plotly_chart(fig6, use_container_width=True)

# ────────────────────────────────────────────────────────────────────────────────
# TAB 5 — Heatmap
# ────────────────────────────────────────────────────────────────────────────────
with tab5:
    st.subheader("Heatmap comparativo")

    heatmap_x = st.radio("Eje X", ["Plataforma", "País", "Ola"], horizontal=True)
    heatmap_y = st.radio("Eje Y", ["País", "Plataforma", "SLI"], horizontal=True)

    sli_opts5 = sorted(df["sli_name"].unique())
    chosen_sli5 = st.selectbox("SLI", sli_opts5, key="sli_heat")
    df_heat = df[df["sli_name"] == chosen_sli5]

    x_col = {"Plataforma": "platform", "País": "country", "Ola": "wave_label"}[heatmap_x]
    y_col = {"País": "country", "Plataforma": "platform", "SLI": "sli_name"}[heatmap_y]

    if x_col == y_col:
        st.warning("Selecciona ejes diferentes.")
    elif df_heat.empty:
        st.info("Sin datos.")
    else:
        pivot_h = df_heat.pivot_table(index=y_col, columns=x_col, values="metric", aggfunc="sum")
        fig7 = px.imshow(
            pivot_h,
            color_continuous_scale="Blues",
            aspect="auto",
            labels={"color": metric_label},
            title=f"Heatmap: {chosen_sli5}",
        )
        fig7.update_layout(height=max(400, len(pivot_h) * 22))
        st.plotly_chart(fig7, use_container_width=True)

# ────────────────────────────────────────────────────────────────────────────────
# TAB 6 — Tabla de datos
# ────────────────────────────────────────────────────────────────────────────────
with tab6:
    st.subheader("Tabla de datos filtrados")

    show_cols = ["wave_label", "platform", "chapter", "sli_name", "country",
                 "metric_name", "metric", "value", "population", "value_per_100k", "methodology"]
    show_cols = [c for c in show_cols if c in df.columns]

    df_show = df[show_cols].rename(columns={
        "wave_label": "Ola", "platform": "Plataforma", "chapter": "Capítulo",
        "sli_name": "SLI", "country": "País", "metric_name": "Métrica",
        "metric": metric_label, "value": "Valor original",
        "population": "Población", "value_per_100k": "Por 100k hab.",
        "methodology": "Metodología",
    })

    st.dataframe(df_show, use_container_width=True, height=500)

    # Descarga
    csv = df_show.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="⬇️ Descargar datos filtrados (CSV)",
        data=csv,
        file_name="disinfocode_filtrado.csv",
        mime="text/csv",
    )
