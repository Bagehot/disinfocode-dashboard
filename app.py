"""
DisinfoCode Interactive Dashboard — v5
Ejecutar: streamlit run app.py
"""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
from data.population import POPULATION
from data.sli_labels import label as make_label

st.set_page_config(
    page_title="DisinfoCode · Comparativa de Plataformas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSV_PATH   = Path(__file__).parent / "output" / "metrics_raw.csv"
WAVE_ORDER = ["March 2025", "September 2025", "March 2026"]
EU_MEMBERS = [k for k in POPULATION if not k.startswith("Total")]
NONE_OPT   = "— Ninguna —"
GEO_OPTS   = ["Total EU", "Total EEA"] + sorted(EU_MEMBERS)

COLOR_SEQ  = px.colors.qualitative.Bold
COLOR_ALPHA = px.colors.qualitative.Alphabet


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[df["value"].notna()].copy()
    df["wave_label"] = pd.Categorical(df["wave_label"], categories=WAVE_ORDER, ordered=True)
    df["population"] = df["country"].map(POPULATION)
    df["value_per_100k"] = df.apply(
        lambda r: (r["value"] / r["population"] * 100_000)
        if pd.notna(r["population"]) and r["population"] > 0 else None,
        axis=1,
    )
    df["sli_label"] = df.apply(lambda r: make_label(r["sli_code"], r["sli_name"]), axis=1)
    df = df[df["country"].isin(set(POPULATION.keys()))].copy()
    return df


df_all = load_data()

platforms      = sorted(df_all["platform"].unique())
countries      = sorted(df_all["country"].unique())
chapters       = sorted(df_all["chapter"].dropna().unique())
sli_labels_all = sorted(df_all["sli_label"].unique())


def sli_opts(frame: pd.DataFrame) -> list[str]:
    return [NONE_OPT] + sorted(frame["sli_label"].unique())


def pick_sli(frame: pd.DataFrame, chosen: str) -> pd.DataFrame:
    if not chosen or chosen == NONE_OPT:
        return pd.DataFrame()
    return frame[frame["sli_label"] == chosen]


def filter_countries(frame: pd.DataFrame, selected: list) -> pd.DataFrame:
    if selected:
        return frame[frame["country"].isin(selected)]
    return frame


def apply_metric(frame: pd.DataFrame, mode: str, df_base: pd.DataFrame) -> tuple[pd.DataFrame, str]:
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
        lbl = "% sobre Total EU"
    elif mode == "Por 100.000 habitantes":
        frame["metric"] = frame["value_per_100k"]
        lbl = "Por 100.000 hab."
    else:
        frame["metric"] = frame["value"]
        lbl = "Valor absoluto"
    return frame[frame["metric"].notna()], lbl


def no_data_warning():
    st.info("Sin datos con los filtros actuales.")


def run_btn(key: str) -> bool:
    return st.form_submit_button("▶ Analizar", use_container_width=True, type="primary")


def color_radio(key: str) -> str:
    return st.radio("Color por", ["Plataforma", "País"], horizontal=True, key=key)


def to_excel(frame: pd.DataFrame, index: bool = False) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        frame.to_excel(writer, index=index, sheet_name="Datos")
    return buf.getvalue()


def dl_excel(frame: pd.DataFrame, fname: str, key: str, index: bool = False):
    st.download_button(
        "⬇️ Descargar Excel",
        data=to_excel(frame, index=index),
        file_name=f"{fname}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=key,
    )


def tab_frame(selected: list) -> pd.DataFrame:
    """Si el usuario selecciona países en un tab, usa df_base (sin filtro de país
    del sidebar). Si no hay selección, usa df (respeta el filtro global)."""
    if selected:
        return df_base[df_base["country"].isin(selected)]
    return df


def tab_frame_members(selected: list) -> pd.DataFrame:
    """Como tab_frame pero excluye siempre las filas Total EU/EEA."""
    frame = tab_frame(selected)
    return frame[~frame["country"].str.contains("Total", na=False)]


# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 Filtros globales")
    st.caption("Acumula valores en cada filtro. Vacío = sin restricción.")

    sel_waves     = st.multiselect("Ola / Wave", WAVE_ORDER, default=[])
    sel_platforms = st.multiselect("Plataforma", platforms, default=[])
    sel_chapters  = st.multiselect("Capítulo temático", chapters, default=[])

    scope = st.radio(
        "Ámbito geográfico",
        ["Solo totales EU/EEA", "Por estado miembro", "Ambos"],
    )
    if scope == "Solo totales EU/EEA":
        sel_countries = [c for c in countries if "Total" in c]
    elif scope == "Por estado miembro":
        sel_countries = st.multiselect("Países", EU_MEMBERS, default=[])
    else:
        sel_countries = countries

    metric_mode = st.radio(
        "Unidad de medida",
        ["Valor absoluto", "% sobre Total EU", "Por 100.000 habitantes"],
    )

    st.divider()
    sel_sli_filt = st.multiselect("Limitar a variables SLI", sli_labels_all, default=[])
    st.caption("Fuente: disinfocode.eu · Población: REST Countries API 2024")

# ── FILTRADO GLOBAL ────────────────────────────────────────────────────────────
# df_base: todos los filtros globales EXCEPTO el filtro de país del sidebar.
# Permite que los selectores de país dentro de cada tab accedan a cualquier país
# independientemente de lo que el sidebar haya restringido.
df_base = df_all.copy()
if sel_waves:      df_base = df_base[df_base["wave_label"].isin(sel_waves)]
if sel_platforms:  df_base = df_base[df_base["platform"].isin(sel_platforms)]
if sel_chapters:   df_base = df_base[df_base["chapter"].isin(sel_chapters)]
if sel_sli_filt:   df_base = df_base[df_base["sli_label"].isin(sel_sli_filt)]
df_base, mlabel = apply_metric(df_base, metric_mode, df_all)

# df: filtrado completo incluyendo el país del sidebar (para métricas generales)
df = df_base[df_base["country"].isin(sel_countries)].copy() if sel_countries else df_base.copy()

# ── CABECERA ───────────────────────────────────────────────────────────────────
st.title("📊 DisinfoCode · Comparativa de Plataformas Sociales")
st.caption("Código de Conducta sobre Desinformación (UE) — Waves 5, 6 y 8 (2025–2026)")

# ── TABS ───────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "🔍 Análisis general",
    "🏢 Por Plataforma",
    "🌍 Por País",
    "📈 Evolución temporal",
    "🔄 Comparativas avanzadas",
    "🌆 Top 10M",
    "🗺️ Mapa",
    "🔥 Heatmap",
    "📋 Tabla de datos",
])
tab0, tab1, tab2, tab3, tab4, tab4b, tab5, tab6, tab7 = tabs


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 0 — Análisis general                                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab0:
    st.subheader("Análisis general — resumen de los filtros activos")

    with st.expander("📌 Filtros activos", expanded=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            st.markdown(f"**Olas:** {', '.join(sel_waves) if sel_waves else '_todas_'}")
            st.markdown(f"**Plataformas:** {', '.join(sel_platforms) if sel_platforms else '_todas_'}")
        with f2:
            st.markdown(f"**Ámbito:** {scope}")
            if scope == "Por estado miembro":
                st.markdown(f"**Países:** {', '.join(sel_countries) if sel_countries else '_ninguno_'}")
        with f3:
            st.markdown(f"**Capítulos:** {', '.join(sel_chapters) if sel_chapters else '_todos_'}")
            st.markdown(f"**Unidad:** {mlabel}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", f"{len(df):,}")
    c2.metric("Plataformas", df["platform"].nunique() if not df.empty else 0)
    c3.metric("Variables SLI", df["sli_label"].nunique() if not df.empty else 0)
    c4.metric("Países", df[df["country"].isin(EU_MEMBERS)]["country"].nunique() if not df.empty else 0)

    st.divider()

    if df.empty:
        no_data_warning()
    else:
        with st.form("tab0_form"):
            r1, r2, r3 = st.columns([3, 2, 2])
            with r1:
                chart0_type = st.selectbox(
                    "Tipo de visualización general",
                    ["Barras por plataforma y ola", "Distribución por capítulo", "Evolución por plataforma", "Top variables SLI"],
                    key="t0_chart",
                )
            with r2:
                chart0_countries = st.multiselect("Países (vacío = todos)", GEO_OPTS, default=[], key="t0_countries")
            with r3:
                chart0_color = color_radio("t0_color")
            submitted0 = run_btn("tab0")

        if submitted0:
            st.session_state["t0_params"] = {
                "chart_type": chart0_type,
                "countries": chart0_countries,
                "color_by": chart0_color,
            }

        p0 = st.session_state.get("t0_params")
        if not p0:
            st.info("Configura los filtros en la barra lateral y pulsa **▶ Analizar**.")
        else:
            d0 = tab_frame(p0["countries"])
            cb0 = p0["color_by"]
            ct0 = p0["chart_type"]

            if d0.empty:
                no_data_warning()
            elif ct0 == "Barras por plataforma y ola":
                if cb0 == "País":
                    agg0 = d0.groupby(["wave_label", "country"])["metric"].sum().reset_index()
                    fig0 = px.bar(agg0, x="wave_label", y="metric", color="country", barmode="group",
                                  color_discrete_sequence=COLOR_ALPHA,
                                  labels={"metric": mlabel, "wave_label": "Ola", "country": "País"},
                                  title="Total por país y ola",
                                  category_orders={"wave_label": WAVE_ORDER})
                else:
                    agg0 = d0.groupby(["platform", "wave_label"])["metric"].sum().reset_index()
                    fig0 = px.bar(agg0, x="platform", y="metric", color="wave_label", barmode="group",
                                  color_discrete_sequence=COLOR_SEQ,
                                  labels={"metric": mlabel, "platform": "Plataforma", "wave_label": "Ola"},
                                  title="Total por plataforma y ola",
                                  category_orders={"wave_label": WAVE_ORDER})
                fig0.update_layout(xaxis_tickangle=-30)
                st.plotly_chart(fig0, use_container_width=True)
                dl_excel(agg0, "analisis_general_barras", key="dl_t0_barras")

            elif ct0 == "Distribución por capítulo":
                color_col = "country" if cb0 == "País" else "platform"
                color_lbl = "País" if cb0 == "País" else "Plataforma"
                agg0 = d0.groupby(["chapter", color_col])["metric"].sum().reset_index()
                fig0 = px.bar(agg0, x="chapter", y="metric", color=color_col, barmode="stack",
                              color_discrete_sequence=COLOR_ALPHA if cb0 == "País" else COLOR_SEQ,
                              labels={"metric": mlabel, "chapter": "Capítulo", color_col: color_lbl},
                              title="Distribución por capítulo temático")
                fig0.update_layout(xaxis_tickangle=-30)
                st.plotly_chart(fig0, use_container_width=True)
                dl_excel(agg0, "analisis_general_capitulos", key="dl_t0_cap")

            elif ct0 == "Evolución por plataforma":
                color_col = "country" if cb0 == "País" else "platform"
                color_lbl = "País" if cb0 == "País" else "Plataforma"
                agg0 = d0.groupby(["wave_label", color_col])["metric"].sum().reset_index()
                fig0 = px.line(agg0, x="wave_label", y="metric", color=color_col, markers=True,
                               color_discrete_sequence=COLOR_ALPHA if cb0 == "País" else COLOR_SEQ,
                               labels={"metric": mlabel, "wave_label": "Ola", color_col: color_lbl},
                               title="Evolución total",
                               category_orders={"wave_label": WAVE_ORDER})
                fig0.update_traces(line_width=2.5, marker_size=9)
                st.plotly_chart(fig0, use_container_width=True)
                dl_excel(agg0, "analisis_general_evolucion", key="dl_t0_evol")

            else:  # Top variables SLI
                agg0 = (d0.groupby("sli_label")["metric"].sum().reset_index()
                        .sort_values("metric", ascending=False).head(20))
                fig0 = px.bar(agg0, x="metric", y="sli_label", orientation="h",
                              color="metric", color_continuous_scale="Blues",
                              labels={"metric": mlabel, "sli_label": "Variable SLI"},
                              title="Top 20 variables SLI por valor agregado")
                fig0.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(400, len(agg0) * 30))
                st.plotly_chart(fig0, use_container_width=True)
                dl_excel(agg0, "analisis_general_top_sli", key="dl_t0_sli")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 1 — Por Plataforma                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab1:
    st.subheader("Comparativa por Plataforma")

    agg1_raw = df_base.groupby(["platform", "wave_label", "sli_label", "country"])["metric"].sum().reset_index()
    opts1 = sli_opts(agg1_raw)

    with st.form("tab1_form"):
        r1, r2 = st.columns([3, 2])
        with r1:
            chosen1 = st.selectbox("Variable SLI", opts1, key="t1_sli")
            chart1 = st.selectbox(
                "Tipo de gráfico",
                ["Barras agrupadas", "Barras apiladas", "Líneas", "Área", "Dispersión", "Treemap"],
                key="t1_chart",
            )
        with r2:
            countries1 = st.multiselect("Países (vacío = todos)", GEO_OPTS, default=[], key="t1_countries")
            color_by1 = color_radio("t1_color")
        submitted1 = run_btn("tab1")

    if submitted1:
        st.session_state["t1_params"] = {
            "chosen": chosen1, "chart": chart1,
            "countries": countries1, "color_by": color_by1,
        }

    p1 = st.session_state.get("t1_params")
    if not p1:
        st.info("Selecciona una variable y tipo de gráfico, luego pulsa **▶ Analizar**.")
    elif p1["chosen"] == NONE_OPT:
        st.info("Selecciona una variable SLI para continuar.")
    else:
        d1_raw = pick_sli(tab_frame(p1["countries"]), p1["chosen"])
        cb1 = p1["color_by"]
        ct1 = p1["chart"]

        if cb1 == "Plataforma":
            d1 = d1_raw.groupby(["platform", "wave_label"])["metric"].sum().reset_index()
            color_col, color_lbl = "wave_label", "Ola"
            x_col, x_lbl = "platform", "Plataforma"
        else:
            d1 = d1_raw.groupby(["wave_label", "country"])["metric"].sum().reset_index()
            color_col, color_lbl = "country", "País"
            x_col, x_lbl = "wave_label", "Ola"

        if d1.empty:
            no_data_warning()
        else:
            kw = dict(
                color_discrete_sequence=COLOR_ALPHA if cb1 == "País" else COLOR_SEQ,
                labels={"metric": mlabel, x_col: x_lbl, color_col: color_lbl},
                category_orders={"wave_label": WAVE_ORDER},
            )
            title1 = f"{p1['chosen']} — {'por país' if cb1 == 'País' else 'por plataforma'}"
            if ct1 == "Barras agrupadas":
                fig1 = px.bar(d1, x=x_col, y="metric", color=color_col, barmode="group", title=title1, **kw)
                fig1.update_layout(xaxis_tickangle=-30)
            elif ct1 == "Barras apiladas":
                fig1 = px.bar(d1, x=x_col, y="metric", color=color_col, barmode="stack", title=title1, **kw)
                fig1.update_layout(xaxis_tickangle=-30)
            elif ct1 == "Líneas":
                fig1 = px.line(d1, x=x_col, y="metric", color=color_col, markers=True, title=title1, **kw)
                fig1.update_traces(line_width=2.5, marker_size=9)
            elif ct1 == "Área":
                fig1 = px.area(d1, x=x_col, y="metric", color=color_col, title=title1, **kw)
            elif ct1 == "Dispersión":
                fig1 = px.scatter(d1, x=x_col, y="metric", color=color_col, size="metric", title=title1, **kw)
            else:
                path1 = ["wave_label", "platform"] if cb1 == "Plataforma" else ["wave_label", "country"]
                fig1 = px.treemap(d1_raw.groupby(["wave_label","platform","country"])["metric"].sum().reset_index(),
                                  path=path1, values="metric",
                                  color="metric", color_continuous_scale="Blues", title=title1)
            st.plotly_chart(fig1, use_container_width=True)

            idx_col = "platform" if cb1 == "Plataforma" else "country"
            pivot1 = d1.pivot_table(index=idx_col, columns="wave_label", values="metric", aggfunc="sum")
            pivot1 = pivot1.reindex(columns=[w for w in WAVE_ORDER if w in pivot1.columns]).round(2)
            pivot1.columns.name = None
            st.dataframe(pivot1, use_container_width=True)
            dl_excel(pivot1.reset_index(), "por_plataforma", key="dl_t1")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 2 — Por País                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab2:
    st.subheader("Comparativa por País")

    df_c = df_base[~df_base["country"].str.contains("Total", na=False)]
    if df_c.empty:
        st.warning("Sin datos de estados miembro con los filtros actuales.")
    else:
        with st.form("tab2_form"):
            r1, r2, r3 = st.columns([3, 2, 2])
            with r1:
                chosen2 = st.selectbox("Variable SLI", sli_opts(df_c), key="t2_sli")
            with r2:
                wave2 = st.selectbox(
                    "Ola",
                    [NONE_OPT] + [w for w in WAVE_ORDER if w in df_c["wave_label"].values],
                    key="t2_wave",
                )
            with r3:
                plat2 = st.selectbox(
                    "Plataforma",
                    [NONE_OPT] + sorted(df_c["platform"].unique()),
                    key="t2_plat",
                )
            countries2 = st.multiselect("Filtrar países (vacío = todos)", sorted(df_c["country"].unique()), default=[], key="t2_countries")
            chart2 = st.radio(
                "Tipo de gráfico",
                ["Barras horizontales", "Barras verticales", "Burbuja (vs. población)", "Embudo"],
                horizontal=True, key="t2_chart",
            )
            submitted2 = run_btn("tab2")

        if submitted2:
            st.session_state["t2_params"] = {
                "chosen": chosen2, "wave": wave2, "plat": plat2,
                "countries": countries2, "chart": chart2,
            }

        p2 = st.session_state.get("t2_params")
        if not p2:
            st.info("Selecciona los parámetros y pulsa **▶ Analizar**.")
        elif p2["chosen"] == NONE_OPT or p2["wave"] == NONE_OPT or p2["plat"] == NONE_OPT:
            st.info("Selecciona variable SLI, ola y plataforma para continuar.")
        else:
            base2 = pick_sli(tab_frame_members(p2["countries"]), p2["chosen"])
            d2 = (base2.query("wave_label == @p2['wave'] and platform == @p2['plat']")
                  .groupby("country")["metric"].sum().reset_index()
                  .sort_values("metric", ascending=False))

            if d2.empty:
                no_data_warning()
            else:
                ct2 = p2["chart"]
                if ct2 == "Barras horizontales":
                    fig2 = px.bar(d2, x="metric", y="country", orientation="h",
                                  color="metric", color_continuous_scale="Blues",
                                  labels={"metric": mlabel, "country": "País"},
                                  title=f"{p2['chosen']} · {p2['plat']} · {p2['wave']}")
                    fig2.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(400, len(d2) * 28))
                elif ct2 == "Barras verticales":
                    fig2 = px.bar(d2, x="country", y="metric",
                                  color="metric", color_continuous_scale="Blues",
                                  labels={"metric": mlabel, "country": "País"},
                                  title=f"{p2['chosen']} · {p2['plat']} · {p2['wave']}")
                    fig2.update_layout(xaxis_tickangle=-45, height=500)
                elif ct2 == "Burbuja (vs. población)":
                    d2["population"] = d2["country"].map(POPULATION)
                    d2 = d2.dropna(subset=["population"])
                    fig2 = px.scatter(d2, x="population", y="metric", text="country",
                                     size="metric", color="metric", color_continuous_scale="Blues",
                                     labels={"metric": mlabel, "population": "Población"},
                                     title=f"{p2['chosen']} — Métrica vs. Población")
                    fig2.update_traces(textposition="top center")
                else:
                    fig2 = px.funnel(d2.head(15), x="metric", y="country",
                                     labels={"metric": mlabel, "country": "País"},
                                     title=f"{p2['chosen']} · Top 15 países")
                st.plotly_chart(fig2, use_container_width=True)
                dl_excel(d2, "por_pais", key="dl_t2")

        # Evolución entre olas
        st.subheader("Evolución entre olas · comparativa por país")
        with st.form("tab2b_form"):
            cb1, cb2, cb3, cb4 = st.columns(4)
            with cb1:
                chosen2b = st.selectbox("Variable SLI", sli_opts(df_c), key="t2b_sli")
            with cb2:
                plat2b = st.selectbox("Plataforma", [NONE_OPT] + sorted(df_c["platform"].unique()), key="t2b_plat")
            with cb3:
                countries2b = st.multiselect("Países (vacío = todos)", sorted(df_c["country"].unique()), default=[], key="t2b_countries")
            with cb4:
                chart2b = st.radio("Tipo", ["Barras agrupadas", "Líneas", "Barras apiladas"], key="t2b_chart")
            submitted2b = run_btn("tab2b")

        if submitted2b:
            st.session_state["t2b_params"] = {
                "chosen": chosen2b, "plat": plat2b,
                "countries": countries2b, "chart": chart2b,
            }

        p2b = st.session_state.get("t2b_params")
        if p2b and p2b["chosen"] != NONE_OPT and p2b["plat"] != NONE_OPT:
            base2b = pick_sli(tab_frame_members(p2b["countries"]), p2b["chosen"])
            d2b = (base2b.query("platform == @p2b['plat']")
                   .groupby(["country", "wave_label"])["metric"].sum().reset_index())
            if not d2b.empty:
                kw2b = dict(x="country", y="metric", color="wave_label",
                            labels={"metric": mlabel, "country": "País", "wave_label": "Ola"},
                            category_orders={"wave_label": WAVE_ORDER},
                            color_discrete_sequence=COLOR_SEQ)
                if p2b["chart"] == "Barras agrupadas":
                    fig2b = px.bar(d2b, barmode="group", **kw2b)
                elif p2b["chart"] == "Barras apiladas":
                    fig2b = px.bar(d2b, barmode="stack", **kw2b)
                else:
                    fig2b = px.line(d2b, markers=True, **kw2b)
                fig2b.update_layout(xaxis_tickangle=-45, height=450)
                st.plotly_chart(fig2b, use_container_width=True)
                dl_excel(d2b, "por_pais_evolucion", key="dl_t2b")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 3 — Evolución temporal                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab3:
    st.subheader("Evolución a lo largo de las tres olas")

    with st.form("tab3_form"):
        r1, r2, r3, r4 = st.columns([3, 2, 2, 2])
        with r1:
            chosen3 = st.selectbox("Variable SLI", sli_opts(df), key="t3_sli")
        with r2:
            countries3 = st.multiselect("Países (vacío = todos)", GEO_OPTS, default=[], key="t3_countries")
        with r3:
            chart3 = st.selectbox(
                "Tipo de gráfico",
                ["Líneas + marcadores", "Barras agrupadas", "Área", "Barras apiladas"],
                key="t3_chart",
            )
        with r4:
            color_by3 = color_radio("t3_color")
        submitted3 = run_btn("tab3")

    if submitted3:
        st.session_state["t3_params"] = {
            "chosen": chosen3, "countries": countries3,
            "chart": chart3, "color_by": color_by3,
        }

    p3 = st.session_state.get("t3_params")
    if not p3:
        st.info("Selecciona los parámetros y pulsa **▶ Analizar**.")
    elif p3["chosen"] == NONE_OPT:
        st.info("Selecciona una variable SLI para continuar.")
    else:
        cb3 = p3["color_by"]
        base3 = pick_sli(tab_frame(p3["countries"]), p3["chosen"])

        if cb3 == "Plataforma":
            d3 = base3.groupby(["wave_label", "platform"])["metric"].sum().reset_index()
            color_col3, color_lbl3 = "platform", "Plataforma"
        else:
            d3 = base3.groupby(["wave_label", "country"])["metric"].sum().reset_index()
            color_col3, color_lbl3 = "country", "País"

        if d3.empty:
            no_data_warning()
        else:
            paises_str = ", ".join(p3["countries"]) if p3["countries"] else "todos"
            kw3 = dict(x="wave_label", y="metric", color=color_col3,
                       labels={"metric": mlabel, "wave_label": "Ola", color_col3: color_lbl3},
                       title=f"{p3['chosen']} — {paises_str}",
                       category_orders={"wave_label": WAVE_ORDER},
                       color_discrete_sequence=COLOR_ALPHA if cb3 == "País" else COLOR_SEQ)
            ct3 = p3["chart"]
            if ct3 == "Líneas + marcadores":
                fig3 = px.line(d3, markers=True, **kw3)
                fig3.update_traces(line_width=2.5, marker_size=10)
            elif ct3 == "Barras agrupadas":
                fig3 = px.bar(d3, barmode="group", **kw3)
            elif ct3 == "Área":
                fig3 = px.area(d3, **kw3)
            else:
                fig3 = px.bar(d3, barmode="stack", **kw3)
            st.plotly_chart(fig3, use_container_width=True)

            piv3 = d3.pivot_table(index=color_col3, columns="wave_label", values="metric")
            for i in range(1, len(WAVE_ORDER)):
                wp, wc = WAVE_ORDER[i - 1], WAVE_ORDER[i]
                if wp in piv3.columns and wc in piv3.columns:
                    piv3[f"Δ% {wp[:3]}→{wc[:3]}"] = ((piv3[wc] - piv3[wp]) / piv3[wp].abs() * 100).round(1)
            st.dataframe(piv3.round(2), use_container_width=True)
            dl_excel(piv3.round(2).reset_index(), "evolucion_temporal", key="dl_t3")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 4 — Comparativas avanzadas                                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab4:
    st.subheader("Comparativas avanzadas")

    analysis4 = st.radio(
        "Tipo de análisis",
        [
            "A · Múltiples variables para una plataforma",
            "B · Dispersión entre dos períodos (países)",
            "C · Ranking de países · Top N",
            "D · Plataformas comparadas en un mismo país",
            "E · Gráfico de radar (múltiples variables)",
        ],
        horizontal=False, key="t4_analysis",
    )

    # ── A ─────────────────────────────────────────────────────────────────────
    if analysis4.startswith("A"):
        st.markdown("**Selecciona una plataforma y varias variables SLI para compararlas.**")
        with st.form("tab4a_form"):
            r1, r2 = st.columns([2, 3])
            with r1:
                plat_a = st.selectbox("Plataforma", [NONE_OPT] + platforms, key="t4a_plat")
                wave_a = st.selectbox("Ola", [NONE_OPT] + WAVE_ORDER, key="t4a_wave")
                chart_a = st.radio("Gráfico", ["Barras horizontales", "Barras verticales", "Treemap"], key="t4a_chart")
                color_by_a = color_radio("t4a_color")
            with r2:
                countries_a = st.multiselect("Países (vacío = todos)", GEO_OPTS, default=[], key="t4a_countries")
                slis_a = st.multiselect("Variables SLI (≥ 2)", sli_labels_all, default=[], key="t4a_slis")
            submitted4a = run_btn("tab4a")

        if submitted4a:
            st.session_state["t4a_params"] = {
                "plat": plat_a, "wave": wave_a, "chart": chart_a,
                "color_by": color_by_a, "countries": countries_a, "slis": slis_a,
            }

        p4a = st.session_state.get("t4a_params")
        if not p4a:
            st.info("Configura los parámetros y pulsa **▶ Analizar**.")
        elif any(v == NONE_OPT for v in [p4a["plat"], p4a["wave"]]) or not p4a["slis"]:
            st.info("Completa plataforma, ola y al menos una variable SLI.")
        else:
            _fra = tab_frame(p4a["countries"])
            base_a = _fra[(_fra["platform"] == p4a["plat"]) &
                          (_fra["sli_label"].isin(p4a["slis"])) &
                          (_fra["wave_label"] == p4a["wave"])]
            cb_a = p4a["color_by"]

            if cb_a == "País":
                da = base_a.groupby(["sli_label", "country"])["metric"].sum().reset_index()
            else:
                da = base_a.groupby("sli_label")["metric"].sum().reset_index().sort_values("metric", ascending=False)

            if da.empty:
                no_data_warning()
            else:
                paises_str_a = ", ".join(p4a["countries"]) if p4a["countries"] else "todos"
                title_a = f"{p4a['plat']} · {p4a['wave']} · {paises_str_a}"
                ct4a = p4a["chart"]
                if cb_a == "País":
                    fig4a = px.bar(da, x="metric", y="sli_label", color="country", orientation="h",
                                   barmode="group", color_discrete_sequence=COLOR_ALPHA,
                                   labels={"metric": mlabel, "sli_label": "Variable SLI", "country": "País"},
                                   title=title_a)
                    fig4a.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(400, len(da) * 25))
                elif ct4a == "Barras horizontales":
                    fig4a = px.bar(da, x="metric", y="sli_label", orientation="h",
                                   color="metric", color_continuous_scale="Blues",
                                   labels={"metric": mlabel, "sli_label": "Variable SLI"}, title=title_a)
                    fig4a.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(400, len(da) * 35))
                elif ct4a == "Barras verticales":
                    fig4a = px.bar(da, x="sli_label", y="metric",
                                   color="metric", color_continuous_scale="Blues",
                                   labels={"metric": mlabel, "sli_label": "Variable SLI"}, title=title_a)
                    fig4a.update_layout(xaxis_tickangle=-40)
                else:
                    fig4a = px.treemap(da, path=["sli_label"], values="metric",
                                       color="metric", color_continuous_scale="Blues", title=title_a)
                st.plotly_chart(fig4a, use_container_width=True)
                dl_excel(da, "avanzado_A_variables_plataforma", key="dl_t4a")

    # ── B ─────────────────────────────────────────────────────────────────────
    elif analysis4.startswith("B"):
        st.markdown("**Compara el mismo indicador entre dos olas (eje X = ola 1, eje Y = ola 2) por país.**")
        with st.form("tab4b_form"):
            r1, r2, r3 = st.columns(3)
            with r1:
                sli_b = st.selectbox("Variable SLI", [NONE_OPT] + sli_labels_all, key="t4b_sli")
            with r2:
                plat_b = st.selectbox("Plataforma", [NONE_OPT] + platforms, key="t4b_plat")
            with r3:
                waves_b = st.select_slider("Olas a comparar", options=WAVE_ORDER,
                                           value=(WAVE_ORDER[0], WAVE_ORDER[-1]), key="t4b_waves")
            countries_b = st.multiselect("Países (vacío = todos)", sorted(EU_MEMBERS), default=[], key="t4b_countries")
            submitted4b = run_btn("tab4b")

        if submitted4b:
            st.session_state["t4b_params"] = {
                "sli": sli_b, "plat": plat_b, "waves": waves_b, "countries": countries_b,
            }

        p4b = st.session_state.get("t4b_params")
        if not p4b:
            st.info("Configura los parámetros y pulsa **▶ Analizar**.")
        elif p4b["sli"] == NONE_OPT or p4b["plat"] == NONE_OPT:
            st.info("Selecciona variable SLI y plataforma.")
        else:
            wave_x, wave_y = p4b["waves"]
            df_b = pick_sli(tab_frame_members(p4b["countries"]), p4b["sli"])
            df_b = df_b[df_b["platform"] == p4b["plat"]]
            px_d = df_b[df_b["wave_label"] == wave_x].groupby("country")["metric"].sum().rename("x")
            py_d = df_b[df_b["wave_label"] == wave_y].groupby("country")["metric"].sum().rename("y")
            d_sc = pd.concat([px_d, py_d], axis=1).dropna().reset_index()
            d_sc["population"] = d_sc["country"].map(POPULATION)
            if d_sc.empty:
                no_data_warning()
            else:
                fig4b = px.scatter(d_sc, x="x", y="y", text="country", size="population",
                                   color="country", size_max=50,
                                   labels={"x": f"{mlabel} · {wave_x}", "y": f"{mlabel} · {wave_y}"},
                                   title=f"{p4b['sli']} · {p4b['plat']} — {wave_x} vs {wave_y}")
                mx = max(d_sc[["x", "y"]].max())
                fig4b.add_shape(type="line", x0=0, y0=0, x1=mx, y1=mx, line=dict(dash="dash", color="gray"))
                fig4b.add_annotation(x=mx * 0.9, y=mx * 0.85, text="Sin cambio", showarrow=False, font=dict(color="gray"))
                fig4b.update_traces(textposition="top center")
                fig4b.update_layout(height=600, showlegend=False)
                st.plotly_chart(fig4b, use_container_width=True)
                st.caption("Puntos sobre la diagonal = aumento; bajo la diagonal = descenso.")
                dl_excel(d_sc[["country", "x", "y"]].rename(columns={"country": "País", "x": wave_x, "y": wave_y}),
                         "avanzado_B_dispersion", key="dl_t4b")

    # ── C ─────────────────────────────────────────────────────────────────────
    elif analysis4.startswith("C"):
        st.markdown("**Ranking de países para una variable SLI en una ola y plataforma determinadas.**")
        with st.form("tab4c_form"):
            r1, r2, r3, r4 = st.columns(4)
            with r1:
                sli_c = st.selectbox("Variable SLI", [NONE_OPT] + sli_labels_all, key="t4c_sli")
            with r2:
                wave_c = st.selectbox("Ola", [NONE_OPT] + WAVE_ORDER, key="t4c_wave")
            with r3:
                plat_c = st.selectbox("Plataforma", [NONE_OPT] + platforms, key="t4c_plat")
            with r4:
                topn = st.slider("Top N países", 5, 30, 10, key="t4c_n")
            submitted4c = run_btn("tab4c")

        if submitted4c:
            st.session_state["t4c_params"] = {"sli": sli_c, "wave": wave_c, "plat": plat_c, "topn": topn}

        p4c = st.session_state.get("t4c_params")
        if not p4c:
            st.info("Configura los parámetros y pulsa **▶ Analizar**.")
        elif any(v == NONE_OPT for v in [p4c["sli"], p4c["wave"], p4c["plat"]]):
            st.info("Selecciona variable SLI, ola y plataforma.")
        else:
            d_c = (pick_sli(tab_frame_members([]), p4c["sli"])
                   .query("wave_label == @p4c['wave'] and platform == @p4c['plat']")
                   .groupby("country")["metric"].sum().reset_index()
                   .sort_values("metric", ascending=False).head(p4c["topn"]))
            if d_c.empty:
                no_data_warning()
            else:
                d_c["rank"] = range(1, len(d_c) + 1)
                fig4c = px.bar(d_c, x="metric", y="country", orientation="h",
                               text="rank", color="metric", color_continuous_scale="Blues",
                               labels={"metric": mlabel, "country": "País"},
                               title=f"Top {p4c['topn']} países · {p4c['sli']} · {p4c['plat']} · {p4c['wave']}")
                fig4c.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(350, p4c["topn"] * 38))
                fig4c.update_traces(texttemplate="#%{text}", textposition="inside")
                st.plotly_chart(fig4c, use_container_width=True)
                dl_excel(d_c[["rank", "country", "metric"]].rename(columns={"country": "País", "metric": mlabel, "rank": "Ranking"}),
                         "avanzado_C_ranking", key="dl_t4c")

                top_countries = d_c["country"].tolist()
                d_c2 = (pick_sli(df[df["country"].isin(top_countries)], p4c["sli"])
                        .query("platform == @p4c['plat']")
                        .groupby(["country", "wave_label"])["metric"].sum().reset_index())
                if not d_c2.empty:
                    fig4c2 = px.line(d_c2, x="wave_label", y="metric", color="country",
                                     markers=True, color_discrete_sequence=COLOR_ALPHA,
                                     labels={"metric": mlabel, "wave_label": "Ola", "country": "País"},
                                     category_orders={"wave_label": WAVE_ORDER},
                                     title=f"Evolución del Top {p4c['topn']} · {p4c['sli']} · {p4c['plat']}")
                    fig4c2.update_traces(line_width=2)
                    st.plotly_chart(fig4c2, use_container_width=True)
                    dl_excel(d_c2, "avanzado_C_evolucion_top", key="dl_t4c2")

    # ── D ─────────────────────────────────────────────────────────────────────
    elif analysis4.startswith("D"):
        st.markdown("**Compara todas las plataformas para uno o varios países y una variable, en las tres olas.**")
        with st.form("tab4d_form"):
            r1, r2, r3 = st.columns(3)
            with r1:
                sli_d = st.selectbox("Variable SLI", [NONE_OPT] + sli_labels_all, key="t4d_sli")
            with r2:
                countries_d = st.multiselect("Países (vacío = todos)", GEO_OPTS, default=[], key="t4d_countries")
            with r3:
                chart_d = st.radio("Gráfico", ["Barras agrupadas", "Líneas", "Radar"], key="t4d_chart")
            color_by_d = color_radio("t4d_color")
            submitted4d = run_btn("tab4d")

        if submitted4d:
            st.session_state["t4d_params"] = {
                "sli": sli_d, "countries": countries_d,
                "chart": chart_d, "color_by": color_by_d,
            }

        p4d = st.session_state.get("t4d_params")
        if not p4d:
            st.info("Configura los parámetros y pulsa **▶ Analizar**.")
        elif p4d["sli"] == NONE_OPT:
            st.info("Selecciona una variable SLI.")
        else:
            cb_d = p4d["color_by"]
            base_d = pick_sli(tab_frame(p4d["countries"]), p4d["sli"])

            if cb_d == "Plataforma":
                d_d = base_d.groupby(["platform", "wave_label"])["metric"].sum().reset_index()
                color_col_d, color_lbl_d = "wave_label", "Ola"
                x_col_d, x_lbl_d = "platform", "Plataforma"
            else:
                d_d = base_d.groupby(["country", "wave_label"])["metric"].sum().reset_index()
                color_col_d, color_lbl_d = "country", "País"
                x_col_d, x_lbl_d = "wave_label", "Ola"

            paises_str_d = ", ".join(p4d["countries"]) if p4d["countries"] else "todos"
            if d_d.empty:
                no_data_warning()
            else:
                ct4d = p4d["chart"]
                if ct4d == "Barras agrupadas":
                    fig4d = px.bar(d_d, x=x_col_d, y="metric", color=color_col_d, barmode="group",
                                   color_discrete_sequence=COLOR_ALPHA if cb_d == "País" else COLOR_SEQ,
                                   labels={"metric": mlabel, x_col_d: x_lbl_d, color_col_d: color_lbl_d},
                                   category_orders={"wave_label": WAVE_ORDER},
                                   title=f"{p4d['sli']} · {paises_str_d}")
                    fig4d.update_layout(xaxis_tickangle=-30)
                elif ct4d == "Líneas":
                    fig4d = px.line(d_d, x=x_col_d, y="metric", color=color_col_d, markers=True,
                                    color_discrete_sequence=COLOR_ALPHA if cb_d == "País" else COLOR_SEQ,
                                    labels={"metric": mlabel, x_col_d: x_lbl_d, color_col_d: color_lbl_d},
                                    category_orders={"wave_label": WAVE_ORDER},
                                    title=f"{p4d['sli']} · {paises_str_d}")
                    fig4d.update_traces(line_width=2.5, marker_size=9)
                else:  # Radar
                    cats_d = d_d[color_col_d].unique().tolist()
                    fig4d = go.Figure()
                    for wave in WAVE_ORDER:
                        sub = d_d[d_d["wave_label"] == wave] if cb_d == "Plataforma" else d_d
                        if cb_d == "Plataforma":
                            vals = [sub[sub["platform"] == p]["metric"].sum() for p in cats_d]
                        else:
                            vals = [sub[sub["country"] == c]["metric"].sum() for c in cats_d]
                        if vals:
                            vals += [vals[0]]
                            fig4d.add_trace(go.Scatterpolar(r=vals, theta=cats_d + [cats_d[0]], fill="toself", name=wave))
                    fig4d.update_layout(polar=dict(radialaxis=dict(visible=True)),
                                        title=f"{p4d['sli']} · {paises_str_d} — Radar", height=550)
                st.plotly_chart(fig4d, use_container_width=True)
                dl_excel(d_d, "avanzado_D_plataformas_pais", key="dl_t4d")

    # ── E ─────────────────────────────────────────────────────────────────────
    else:
        st.markdown("**Radar de múltiples variables SLI para una plataforma y ola.**")
        with st.form("tab4e_form"):
            r1, r2, r3 = st.columns(3)
            with r1:
                plat_e = st.selectbox("Plataforma", [NONE_OPT] + platforms, key="t4e_plat")
            with r2:
                wave_e = st.selectbox("Ola", [NONE_OPT] + WAVE_ORDER, key="t4e_wave")
            with r3:
                countries_e = st.multiselect("Países (vacío = todos)", GEO_OPTS, default=[], key="t4e_countries")
            slis_e = st.multiselect("Variables SLI a incluir", sli_labels_all, default=[], key="t4e_slis")
            submitted4e = run_btn("tab4e")

        if submitted4e:
            st.session_state["t4e_params"] = {
                "plat": plat_e, "wave": wave_e,
                "countries": countries_e, "slis": slis_e,
            }

        p4e = st.session_state.get("t4e_params")
        if not p4e:
            st.info("Configura los parámetros y pulsa **▶ Analizar**.")
        elif any(v == NONE_OPT for v in [p4e["plat"], p4e["wave"]]) or not p4e["slis"]:
            st.info("Completa plataforma, ola y variables SLI.")
        else:
            _fre = tab_frame(p4e["countries"])
            base_e = _fre[(_fre["platform"] == p4e["plat"]) &
                          (_fre["wave_label"] == p4e["wave"]) &
                          (_fre["sli_label"].isin(p4e["slis"]))]
            d_e = base_e.groupby("sli_label")["metric"].sum().reset_index()

            if d_e.empty:
                no_data_warning()
            else:
                d_e["metric_norm"] = d_e["metric"] / d_e["metric"].max()
                cats = d_e["sli_label"].tolist() + [d_e["sli_label"].iloc[0]]
                vals = d_e["metric_norm"].tolist() + [d_e["metric_norm"].iloc[0]]
                paises_str_e = ", ".join(p4e["countries"]) if p4e["countries"] else "todos"
                fig4e = go.Figure()
                fig4e.add_trace(go.Scatterpolar(r=vals, theta=cats, fill="toself",
                                                name=p4e["plat"], line_color=COLOR_SEQ[0]))
                fig4e.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                    title=f"Perfil de {p4e['plat']} · {p4e['wave']} · {paises_str_e} (norm. 0-1)",
                    height=600,
                )
                st.plotly_chart(fig4e, use_container_width=True)
                st.caption("Valores normalizados (0-1) para comparar variables con escalas distintas.")
                tbl_e = d_e[["sli_label", "metric"]].rename(
                    columns={"sli_label": "Variable", "metric": mlabel}).set_index("Variable")
                st.dataframe(tbl_e, use_container_width=True)
                dl_excel(tbl_e.reset_index(), "avanzado_E_radar", key="dl_t4e")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 4B — Top 10M                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
TOP10M_COUNTRIES = sorted(
    [c for c, p in POPULATION.items() if p >= 10_000_000 and not c.startswith("Total")]
)
TOP10M_POPS = {c: POPULATION[c] for c in TOP10M_COUNTRIES}

with tab4b:
    st.subheader("🌆 Análisis Top 10M — Países con más de 10 millones de habitantes")

    with st.expander("ℹ️ Países incluidos"):
        pop_df = pd.DataFrame(
            [(c, f"{TOP10M_POPS[c]:,}") for c in sorted(TOP10M_COUNTRIES, key=lambda x: -TOP10M_POPS[x])],
            columns=["País", "Población (2024)"],
        )
        st.dataframe(pop_df.set_index("País"), use_container_width=True)

    df_10m = df_base[df_base["country"].isin(TOP10M_COUNTRIES)].copy()

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
            horizontal=False, key="t4b_mode",
        )

        # ── 1 ─────────────────────────────────────────────────────────────────
        if analysis_10m.startswith("1"):
            with st.form("tab10m1_form"):
                r1, r2, r3, r4 = st.columns(4)
                with r1:
                    sli_10 = st.selectbox("Variable SLI", sli_opts(df_10m), key="t4b_1_sli")
                with r2:
                    wave_10 = st.selectbox("Ola", [NONE_OPT] + [w for w in WAVE_ORDER if w in df_10m["wave_label"].values], key="t4b_1_wave")
                with r3:
                    chart_10 = st.radio("Gráfico", ["Barras agrupadas por país", "Barras agrupadas por plataforma", "Líneas", "Mapa Top 10M"], key="t4b_1_chart")
                with r4:
                    color_by_10 = color_radio("t4b_1_color")
                sub10_1 = run_btn("tab10m1")

            if sub10_1:
                st.session_state["t10m1_params"] = {"sli": sli_10, "wave": wave_10, "chart": chart_10, "color_by": color_by_10}

            p10_1 = st.session_state.get("t10m1_params")
            if not p10_1:
                st.info("Configura los parámetros y pulsa **▶ Analizar**.")
            elif p10_1["sli"] == NONE_OPT or p10_1["wave"] == NONE_OPT:
                st.info("Selecciona variable SLI y ola.")
            else:
                cb_10 = p10_1["color_by"]
                d10 = (pick_sli(df_10m, p10_1["sli"]).query("wave_label == @p10_1['wave']")
                       .groupby(["country", "platform"])["metric"].sum().reset_index())
                if d10.empty:
                    no_data_warning()
                else:
                    ct10 = p10_1["chart"]
                    color_10 = "country" if cb_10 == "País" else "platform"
                    x_10 = "platform" if cb_10 == "País" else "country"
                    if ct10 == "Barras agrupadas por país" or ct10 == "Barras agrupadas por plataforma":
                        fig10 = px.bar(d10, x=x_10, y="metric", color=color_10, barmode="group",
                                       color_discrete_sequence=COLOR_ALPHA if cb_10 == "País" else COLOR_SEQ,
                                       labels={"metric": mlabel, "country": "País", "platform": "Plataforma"},
                                       title=f"{p10_1['sli']} · {p10_1['wave']} — Top 10M")
                        fig10.update_layout(xaxis_tickangle=-30, height=500)
                    elif ct10 == "Líneas":
                        fig10 = px.line(d10, x=x_10, y="metric", color=color_10, markers=True,
                                        color_discrete_sequence=COLOR_ALPHA if cb_10 == "País" else COLOR_SEQ,
                                        labels={"metric": mlabel, "country": "País", "platform": "Plataforma"},
                                        title=f"{p10_1['sli']} · {p10_1['wave']} — Top 10M")
                        fig10.update_layout(xaxis_tickangle=-30)
                    else:
                        d10_map = d10.groupby("country")["metric"].sum().reset_index()
                        d10_map["country_plot"] = d10_map["country"].replace({"Czech Republic": "Czechia"})
                        fig10 = px.choropleth(d10_map, locations="country_plot", locationmode="country names",
                                              color="metric", color_continuous_scale="Blues", scope="europe",
                                              labels={"metric": mlabel, "country_plot": "País"},
                                              title=f"{p10_1['sli']} · {p10_1['wave']} — Top 10M")
                        fig10.update_layout(height=500)
                    st.plotly_chart(fig10, use_container_width=True)
                    pivot10 = d10.pivot_table(index="country", columns="platform", values="metric", aggfunc="sum").round(2)
                    pivot10.index.name = "País"
                    st.dataframe(pivot10, use_container_width=True)
                    dl_excel(pivot10.reset_index(), "top10m_1_variable", key="dl_t10m1")

        # ── 2 ─────────────────────────────────────────────────────────────────
        elif analysis_10m.startswith("2"):
            with st.form("tab10m2_form"):
                r1, r2 = st.columns([2, 3])
                with r1:
                    plat_10b = st.selectbox("Plataforma", [NONE_OPT] + sorted(df_10m["platform"].unique()), key="t4b_2_plat")
                    wave_10b = st.selectbox("Ola", [NONE_OPT] + [w for w in WAVE_ORDER if w in df_10m["wave_label"].values], key="t4b_2_wave")
                    chart_10b = st.radio("Gráfico", ["Barras agrupadas", "Heatmap variable × país", "Treemap"], key="t4b_2_chart")
                with r2:
                    slis_10b = st.multiselect("Variables SLI", sli_opts(df_10m)[1:], default=[], key="t4b_2_slis")
                sub10_2 = run_btn("tab10m2")

            if sub10_2:
                st.session_state["t10m2_params"] = {"plat": plat_10b, "wave": wave_10b, "chart": chart_10b, "slis": slis_10b}

            p10_2 = st.session_state.get("t10m2_params")
            if not p10_2:
                st.info("Configura los parámetros y pulsa **▶ Analizar**.")
            elif p10_2["plat"] == NONE_OPT or p10_2["wave"] == NONE_OPT or not p10_2["slis"]:
                st.info("Selecciona plataforma, ola y al menos una variable SLI.")
            else:
                d10b = (df_10m[df_10m["sli_label"].isin(p10_2["slis"])]
                        .query("platform == @p10_2['plat'] and wave_label == @p10_2['wave']")
                        .groupby(["country", "sli_label"])["metric"].sum().reset_index())
                if d10b.empty:
                    no_data_warning()
                else:
                    ct10b = p10_2["chart"]
                    if ct10b == "Barras agrupadas":
                        fig10b = px.bar(d10b, x="country", y="metric", color="sli_label", barmode="group",
                                        color_discrete_sequence=COLOR_SEQ,
                                        labels={"metric": mlabel, "country": "País", "sli_label": "Variable SLI"},
                                        title=f"{p10_2['plat']} · {p10_2['wave']} — Variables × Países Top 10M")
                        fig10b.update_layout(xaxis_tickangle=-30, height=520)
                    elif ct10b == "Heatmap variable × país":
                        piv10b = d10b.pivot_table(index="sli_label", columns="country", values="metric", aggfunc="sum")
                        fig10b = px.imshow(piv10b, color_continuous_scale="Blues", aspect="auto",
                                           labels={"color": mlabel},
                                           title=f"{p10_2['plat']} · {p10_2['wave']} — Heatmap variables × países")
                        fig10b.update_layout(height=max(350, len(piv10b) * 45))
                    else:
                        fig10b = px.treemap(d10b, path=["country", "sli_label"], values="metric",
                                            color="metric", color_continuous_scale="Blues",
                                            title=f"{p10_2['plat']} · {p10_2['wave']} — Treemap países > 10M")
                        fig10b.update_layout(height=600)
                    st.plotly_chart(fig10b, use_container_width=True)
                    dl_excel(d10b, "top10m_2_variables_plataforma", key="dl_t10m2")

        # ── 3 ─────────────────────────────────────────────────────────────────
        elif analysis_10m.startswith("3"):
            with st.form("tab10m3_form"):
                r1, r2, r3, r4 = st.columns(4)
                with r1:
                    sli_10c = st.selectbox("Variable SLI", sli_opts(df_10m), key="t4b_3_sli")
                with r2:
                    plat_10c = st.selectbox("Plataforma", [NONE_OPT] + sorted(df_10m["platform"].unique()), key="t4b_3_plat")
                with r3:
                    chart_10c = st.radio("Gráfico", ["Líneas por país", "Barras agrupadas por ola", "Área"], key="t4b_3_chart")
                with r4:
                    color_by_10c = color_radio("t4b_3_color")
                sub10_3 = run_btn("tab10m3")

            if sub10_3:
                st.session_state["t10m3_params"] = {"sli": sli_10c, "plat": plat_10c, "chart": chart_10c, "color_by": color_by_10c}

            p10_3 = st.session_state.get("t10m3_params")
            if not p10_3:
                st.info("Configura los parámetros y pulsa **▶ Analizar**.")
            elif p10_3["sli"] == NONE_OPT or p10_3["plat"] == NONE_OPT:
                st.info("Selecciona variable SLI y plataforma.")
            else:
                cb_10c = p10_3["color_by"]
                color_col_10c = "country" if cb_10c == "País" else "platform"
                base_10c = pick_sli(df_10m, p10_3["sli"]).query("platform == @p10_3['plat']")
                d10c = base_10c.groupby(["wave_label", color_col_10c])["metric"].sum().reset_index()
                if d10c.empty:
                    no_data_warning()
                else:
                    kw10c = dict(x="wave_label", y="metric", color=color_col_10c,
                                 color_discrete_sequence=COLOR_ALPHA if cb_10c == "País" else COLOR_SEQ,
                                 labels={"metric": mlabel, "wave_label": "Ola", color_col_10c: cb_10c},
                                 category_orders={"wave_label": WAVE_ORDER},
                                 title=f"{p10_3['sli']} · {p10_3['plat']} — Evolución Top 10M")
                    ct10c = p10_3["chart"]
                    if ct10c == "Líneas por país":
                        fig10c = px.line(d10c, markers=True, **kw10c)
                        fig10c.update_traces(line_width=2.5, marker_size=9)
                    elif ct10c == "Barras agrupadas por ola":
                        fig10c = px.bar(d10c, barmode="group", **kw10c)
                    else:
                        fig10c = px.area(d10c, **kw10c)
                    fig10c.update_layout(height=520)
                    st.plotly_chart(fig10c, use_container_width=True)
                    piv10c = d10c.pivot_table(index=color_col_10c, columns="wave_label", values="metric")
                    for i in range(1, len(WAVE_ORDER)):
                        wp, wc = WAVE_ORDER[i - 1], WAVE_ORDER[i]
                        if wp in piv10c.columns and wc in piv10c.columns:
                            piv10c[f"Δ% {wp[:3]}→{wc[:3]}"] = ((piv10c[wc] - piv10c[wp]) / piv10c[wp].abs() * 100).round(1)
                    st.dataframe(piv10c.round(2), use_container_width=True)
                    dl_excel(piv10c.round(2).reset_index(), "top10m_3_evolucion", key="dl_t10m3")

        # ── 4 ─────────────────────────────────────────────────────────────────
        elif analysis_10m.startswith("4"):
            with st.form("tab10m4_form"):
                r1, r2, r3 = st.columns(3)
                with r1:
                    sli_10d = st.selectbox("Variable SLI", sli_opts(df_10m), key="t4b_4_sli")
                with r2:
                    plat_10d = st.selectbox("Plataforma", [NONE_OPT] + sorted(df_10m["platform"].unique()), key="t4b_4_plat")
                with r3:
                    waves_10d = st.select_slider("Olas a comparar", options=WAVE_ORDER,
                                                 value=(WAVE_ORDER[0], WAVE_ORDER[-1]), key="t4b_4_waves")
                sub10_4 = run_btn("tab10m4")

            if sub10_4:
                st.session_state["t10m4_params"] = {"sli": sli_10d, "plat": plat_10d, "waves": waves_10d}

            p10_4 = st.session_state.get("t10m4_params")
            if not p10_4:
                st.info("Configura los parámetros y pulsa **▶ Analizar**.")
            elif p10_4["sli"] == NONE_OPT or p10_4["plat"] == NONE_OPT:
                st.info("Selecciona variable SLI y plataforma.")
            else:
                wx, wy = p10_4["waves"]
                base_d = pick_sli(df_10m, p10_4["sli"]).query("platform == @p10_4['plat']")
                px_d = base_d[base_d["wave_label"] == wx].groupby("country")["metric"].sum().rename("x")
                py_d = base_d[base_d["wave_label"] == wy].groupby("country")["metric"].sum().rename("y")
                d10d = pd.concat([px_d, py_d], axis=1).dropna().reset_index()
                d10d["population"] = d10d["country"].map(POPULATION)
                if d10d.empty:
                    no_data_warning()
                else:
                    fig10d = px.scatter(d10d, x="x", y="y", text="country",
                                        size="population", color="country", size_max=60,
                                        color_discrete_sequence=COLOR_ALPHA,
                                        labels={"x": f"{mlabel} · {wx}", "y": f"{mlabel} · {wy}"},
                                        title=f"{p10_4['sli']} · {p10_4['plat']} — {wx} vs {wy} · Top 10M")
                    mx = max(d10d[["x", "y"]].max())
                    fig10d.add_shape(type="line", x0=0, y0=0, x1=mx, y1=mx, line=dict(dash="dash", color="gray"))
                    fig10d.update_traces(textposition="top center")
                    fig10d.update_layout(height=580, showlegend=False)
                    st.plotly_chart(fig10d, use_container_width=True)
                    d10d["variación %"] = ((d10d["y"] - d10d["x"]) / d10d["x"].abs() * 100).round(1)
                    tbl10d = (d10d[["country", "x", "y", "variación %"]]
                              .rename(columns={"country": "País", "x": wx, "y": wy})
                              .set_index("País").sort_values("variación %", ascending=False))
                    st.dataframe(tbl10d, use_container_width=True)
                    dl_excel(tbl10d.reset_index(), "top10m_4_dispersion", key="dl_t10m4")

        # ── 5 ─────────────────────────────────────────────────────────────────
        else:
            with st.form("tab10m5_form"):
                r1, r2, r3 = st.columns(3)
                with r1:
                    sli_10e = st.selectbox("Variable SLI", sli_opts(df_10m), key="t4b_5_sli")
                with r2:
                    wave_10e = st.selectbox("Ola", [NONE_OPT] + [w for w in WAVE_ORDER if w in df_10m["wave_label"].values], key="t4b_5_wave")
                with r3:
                    scale_10e = st.select_slider("Escala de color", ["Blues", "Viridis", "RdYlGn", "Plasma"], value="Blues", key="t4b_5_scale")
                sub10_5 = run_btn("tab10m5")

            if sub10_5:
                st.session_state["t10m5_params"] = {"sli": sli_10e, "wave": wave_10e, "scale": scale_10e}

            p10_5 = st.session_state.get("t10m5_params")
            if not p10_5:
                st.info("Configura los parámetros y pulsa **▶ Analizar**.")
            elif p10_5["sli"] == NONE_OPT or p10_5["wave"] == NONE_OPT:
                st.info("Selecciona variable SLI y ola.")
            else:
                d10e = (pick_sli(df_10m, p10_5["sli"]).query("wave_label == @p10_5['wave']")
                        .groupby(["country", "platform"])["metric"].sum().reset_index())
                if d10e.empty:
                    no_data_warning()
                else:
                    piv10e = d10e.pivot_table(index="country", columns="platform", values="metric", aggfunc="sum")
                    piv10e.index.name = "País"
                    fig10e = px.imshow(piv10e, color_continuous_scale=p10_5["scale"], aspect="auto",
                                       labels={"color": mlabel},
                                       title=f"{p10_5['sli']} · {p10_5['wave']} — Heatmap País × Plataforma (Top 10M)")
                    fig10e.update_layout(height=500)
                    st.plotly_chart(fig10e, use_container_width=True)
                    st.dataframe(piv10e.round(2), use_container_width=True)
                    dl_excel(piv10e.round(2).reset_index(), "top10m_5_heatmap", key="dl_t10m5")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 5 — Mapa                                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab5:
    st.subheader("Mapa de Europa")

    df_map = df_base[~df_base["country"].str.contains("Total", na=False)]
    if df_map.empty:
        st.warning("Sin datos de estados miembro con los filtros actuales.")
    else:
        with st.form("tab5_form"):
            r1, r2, r3 = st.columns(3)
            with r1:
                chosen5 = st.selectbox("Variable SLI", sli_opts(df_map), key="t5_sli")
            with r2:
                wave5 = st.selectbox("Ola", [NONE_OPT] + [w for w in WAVE_ORDER if w in df_map["wave_label"].values], key="t5_wave")
            with r3:
                plat5 = st.selectbox("Plataforma", [NONE_OPT] + sorted(df_map["platform"].unique()), key="t5_plat")
            submitted5 = run_btn("tab5")

        if submitted5:
            st.session_state["t5_params"] = {"chosen": chosen5, "wave": wave5, "plat": plat5}

        p5 = st.session_state.get("t5_params")
        if not p5:
            st.info("Selecciona los parámetros y pulsa **▶ Analizar**.")
        elif any(v == NONE_OPT for v in [p5["chosen"], p5["wave"], p5["plat"]]):
            st.info("Selecciona variable SLI, ola y plataforma.")
        else:
            d5 = (pick_sli(df_map, p5["chosen"])
                  .query("wave_label == @p5['wave'] and platform == @p5['plat']")
                  .groupby("country")["metric"].sum().reset_index())
            d5["country_plot"] = d5["country"].replace({"Czech Republic": "Czechia"})
            if d5.empty:
                no_data_warning()
            else:
                fig5 = px.choropleth(d5, locations="country_plot", locationmode="country names",
                                     color="metric", color_continuous_scale="Blues", scope="europe",
                                     labels={"metric": mlabel, "country_plot": "País"},
                                     title=f"{p5['chosen']} · {p5['plat']} · {p5['wave']}")
                fig5.update_layout(height=620)
                st.plotly_chart(fig5, use_container_width=True)
                dl_excel(d5[["country", "metric"]].rename(columns={"country": "País", "metric": mlabel}),
                         "mapa_europa", key="dl_t5")

        st.subheader("Comparativa de dos olas en mapa")
        with st.form("tab5b_form"):
            cb1, cb2, cb3 = st.columns(3)
            with cb1:
                chosen5b = st.selectbox("Variable SLI", sli_opts(df_map), key="t5b_sli")
            with cb2:
                wave5b_1 = st.selectbox("Ola 1", [NONE_OPT] + [w for w in WAVE_ORDER if w in df_map["wave_label"].values], key="t5b_wave1")
            with cb3:
                wave5b_2 = st.selectbox("Ola 2", [NONE_OPT] + [w for w in WAVE_ORDER if w in df_map["wave_label"].values], key="t5b_wave2")
            plat5b = st.selectbox("Plataforma", [NONE_OPT] + sorted(df_map["platform"].unique()), key="t5b_plat")
            submitted5b = run_btn("tab5b")

        if submitted5b:
            st.session_state["t5b_params"] = {"chosen": chosen5b, "wave1": wave5b_1, "wave2": wave5b_2, "plat": plat5b}

        p5b = st.session_state.get("t5b_params")
        if p5b and all(v != NONE_OPT for v in [p5b["chosen"], p5b["wave1"], p5b["wave2"], p5b["plat"]]):
            def make_map(wave_val):
                d = (pick_sli(df_map, p5b["chosen"])
                     .query("wave_label == @wave_val and platform == @p5b['plat']")
                     .groupby("country")["metric"].sum().reset_index())
                d["country_plot"] = d["country"].replace({"Czech Republic": "Czechia"})
                return d

            da5 = make_map(p5b["wave1"])
            db5 = make_map(p5b["wave2"])
            if not da5.empty and not db5.empty:
                ca, cb = st.columns(2)
                with ca:
                    fa = px.choropleth(da5, locations="country_plot", locationmode="country names",
                                       color="metric", color_continuous_scale="Blues", scope="europe", title=p5b["wave1"])
                    fa.update_layout(height=380)
                    st.plotly_chart(fa, use_container_width=True)
                with cb:
                    fb = px.choropleth(db5, locations="country_plot", locationmode="country names",
                                       color="metric", color_continuous_scale="Blues", scope="europe", title=p5b["wave2"])
                    fb.update_layout(height=380)
                    st.plotly_chart(fb, use_container_width=True)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 6 — Heatmap                                                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab6:
    st.subheader("Heatmap comparativo")

    with st.form("tab6_form"):
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            hx = st.selectbox("Eje X", ["Plataforma", "País", "Ola", "Variable SLI"], key="t6_x")
        with r2:
            hy = st.selectbox("Eje Y", ["País", "Plataforma", "Variable SLI", "Ola"], key="t6_y")
        with r3:
            chosen6 = st.selectbox("Variable SLI (filtro)", [NONE_OPT, "Todas"] + sli_opts(df)[1:], key="t6_sli")
        with r4:
            scale6 = st.select_slider("Escala de color", ["Blues", "Viridis", "RdYlGn", "Plasma", "Turbo"], value="Blues", key="t6_scale")
        submitted6 = run_btn("tab6")

    if submitted6:
        st.session_state["t6_params"] = {"hx": hx, "hy": hy, "chosen": chosen6, "scale": scale6}

    p6 = st.session_state.get("t6_params")
    if not p6:
        st.info("Configura los ejes y pulsa **▶ Analizar**.")
    else:
        d6 = df if p6["chosen"] in ("Todas", NONE_OPT) else pick_sli(df, p6["chosen"])
        xmap = {"Plataforma": "platform", "País": "country", "Ola": "wave_label", "Variable SLI": "sli_label"}
        ymap = {"País": "country", "Plataforma": "platform", "Variable SLI": "sli_label", "Ola": "wave_label"}
        xc, yc = xmap[p6["hx"]], ymap[p6["hy"]]
        if xc == yc:
            st.warning("Selecciona ejes diferentes.")
        elif d6.empty:
            no_data_warning()
        else:
            piv6 = d6.pivot_table(index=yc, columns=xc, values="metric", aggfunc="sum")
            fig6 = px.imshow(piv6, color_continuous_scale=p6["scale"], aspect="auto",
                             labels={"color": mlabel},
                             title=f"Heatmap: {p6['hy']} × {p6['hx']}")
            fig6.update_layout(height=max(420, len(piv6) * 22))
            st.plotly_chart(fig6, use_container_width=True)
            dl_excel(piv6.round(2).reset_index(), "heatmap", key="dl_t6")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  TAB 7 — Tabla de datos                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
with tab7:
    st.subheader("Tabla de datos filtrados")

    cols = ["wave_label", "platform", "chapter", "sli_label", "country",
            "metric_name", "metric", "value", "population", "value_per_100k", "methodology"]
    cols = [c for c in cols if c in df.columns]

    df_show = df[cols].rename(columns={
        "wave_label": "Ola", "platform": "Plataforma", "chapter": "Capítulo",
        "sli_label": "Variable SLI", "country": "País", "metric_name": "Métrica",
        "metric": mlabel, "value": "Valor original",
        "population": "Población", "value_per_100k": "Por 100k hab.", "methodology": "Metodología",
    })

    search = st.text_input("🔎 Buscar en tabla", placeholder="país, plataforma, variable…", key="t7_search")
    if search:
        mask = df_show.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        df_show = df_show[mask]

    st.dataframe(df_show, use_container_width=True, height=520)
    st.caption(f"{len(df_show):,} filas mostradas")

    dl1, dl2 = st.columns(2)
    with dl1:
        csv_bytes = df_show.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("⬇️ Descargar CSV", csv_bytes,
                           file_name="disinfocode_filtrado.csv", mime="text/csv")
    with dl2:
        dl_excel(df_show, "disinfocode_filtrado", key="dl_t7_excel")
