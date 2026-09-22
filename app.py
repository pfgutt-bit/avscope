from __future__ import annotations

from datetime import date

import polars as pl
import streamlit as st

from src.app_data import (
    airport_code,
    airport_display,
    airport_lookup,
    airport_place,
    build_analysis,
    company_options,
    destinations_for,
    has_operations,
    load_datasets,
    resolve_company,
    resolve_period_state,
    resolve_route_state,
    reverse_route,
    route_pairs,
)
from src.charts import (
    CHART_CONFIG,
    capacity_chart,
    load_factor_chart,
    market_pulse_chart,
    market_share_chart,
)
from src.formatters import format_company_name, format_month, format_period_range
from src.discovery import csv_bytes
from src.discovery_ui import render_discovery
from src.about_ui import render_about
from src.ui import (
    inject_css,
    render_empty_state,
    render_hhi,
    render_kpi_rail,
    render_route_hero,
    render_section_header,
    render_topbar,
)


st.set_page_config(
    page_title="AVScope",
    page_icon=":material/travel_explore:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()


def sync_query_params(
    origin: str, destination: str, start: date, end: date, company: str | None
) -> None:
    values = {
        "view": "route",
        "origin": origin,
        "destination": destination,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    if company:
        values["company"] = company
    st.query_params.from_dict(values)


def swap_callback(routes: set[tuple[str, str]]) -> None:
    state, swapped = reverse_route(
        st.session_state["origin_icao"], st.session_state["destination_icao"], routes
    )
    if swapped:
        st.session_state["origin_icao"] = state.origin
        st.session_state["destination_icao"] = state.destination
        for key in ["period_start", "period_end", "company_id"]:
            st.session_state.pop(key, None)
        st.session_state["route_feedback"] = "Rota invertida."
    else:
        st.session_state["route_feedback"] = "A rota inversa não está disponível neste universo."


try:
    mvp, airports, initial_load_seconds = load_datasets()
except (FileNotFoundError, pl.exceptions.PolarsError):
    st.error("Não foi possível abrir a base do AVScope. Verifique se os dois arquivos de dados processados acompanham esta instalação.")
    st.stop()
if mvp.is_empty():
    st.info("A base está vazia. Gere os dados do produto antes de abrir o aplicativo.")
    st.stop()
routes = route_pairs(mvp)
lookup = airport_lookup(airports)
initial_route = resolve_route_state(st.query_params, routes)
st.session_state.setdefault("origin_icao", initial_route.origin)
st.session_state.setdefault("destination_icao", initial_route.destination)

latest_period = mvp["PERIODO"].max()
render_topbar(format_month(latest_period))
views = {"route": "Explorar rota", "discover": "Descobrir mercados", "about": "Sobre os dados"}
st.session_state.setdefault("navigation", views.get(st.query_params.get("view", "route"), "Explorar rota"))
page = st.radio("Navegação", list(views.values()), key="navigation", horizontal=True, label_visibility="collapsed")
if page == "Descobrir mercados":
    render_discovery(mvp)
    st.stop()
if page == "Sobre os dados":
    st.query_params.from_dict({"view": "about"})
    render_about(mvp, airports)
    st.stop()

with st.container(border=True):
    st.markdown('<div class="av-kicker">Quero entender esta rota</div>', unsafe_allow_html=True)
    origin_col, swap_col, destination_col = st.columns([5, 1, 5], vertical_alignment="bottom")
    origins = sorted({origin for origin, _ in routes})
    with origin_col:
        origin = st.selectbox(
            "Origem",
            origins,
            key="origin_icao",
            format_func=lambda code: airport_display(code, lookup),
        )
    valid_destinations = destinations_for(origin, routes)
    if st.session_state.get("destination_icao") not in valid_destinations:
        preferred = initial_route.destination if initial_route.destination in valid_destinations else valid_destinations[0]
        st.session_state["destination_icao"] = preferred
    with swap_col:
        st.button(
            "⇄",
            help="Inverter rota",
            key="swap_route",
            on_click=swap_callback,
            args=(routes,),
            use_container_width=True,
        )
    with destination_col:
        destination = st.selectbox(
            "Destino",
            valid_destinations,
            key="destination_icao",
            format_func=lambda code: airport_display(code, lookup),
        )

    if feedback := st.session_state.pop("route_feedback", None):
        st.caption(feedback)

    periods = pl.date_range(mvp["PERIODO"].min(), latest_period, interval="1mo", eager=True).to_list()
    query_period = resolve_period_state(st.query_params, periods)
    st.session_state.setdefault("period_start", query_period.start)
    st.session_state.setdefault("period_end", query_period.end)
    if st.session_state["period_start"] not in periods or st.session_state["period_end"] not in periods:
        st.session_state["period_start"], st.session_state["period_end"] = query_period.start, query_period.end

    start_col, end_col, company_col = st.columns([2, 2, 3])
    with start_col:
        start = st.selectbox("Período inicial", periods, key="period_start", format_func=format_month)
    valid_end_periods = [period for period in periods if period >= start]
    if st.session_state["period_end"] not in valid_end_periods:
        st.session_state["period_end"] = valid_end_periods[-1]
    with end_col:
        end = st.selectbox("Período final", valid_end_periods, key="period_end", format_func=format_month)

    companies = company_options(mvp, origin, destination, start, end)
    company_ids = companies["EMPRESA_ID"].to_list()
    company_map = {
        row["EMPRESA_ID"]: f"{row['DISPLAY_NAME']} · {row['EMPRESA_SIGLA']}"
        for row in companies.to_dicts()
    }
    requested_company = resolve_company(st.query_params, set(company_ids))
    st.session_state.setdefault("company_id", requested_company)
    if st.session_state["company_id"] not in [None, *company_ids]:
        st.session_state["company_id"] = None
    with company_col:
        company = st.selectbox(
            "Companhia",
            [None, *company_ids],
            key="company_id",
            format_func=lambda value: "Todas as companhias" if value is None else company_map[value],
            placeholder="Todas as companhias",
        )

sync_query_params(origin, destination, start, end, company)
analysis = build_analysis(mvp, origin, destination, start, end, company)
series = analysis["series"]

partial_label = None
if end.year == latest_period.year and latest_period.month < 12:
    partial_label = f"{latest_period.year} parcial · dados até {format_month(latest_period).split('/')[0]}"
render_route_hero(
    airport_code(origin, lookup),
    airport_place(origin, lookup),
    airport_code(destination, lookup),
    airport_place(destination, lookup),
    format_period_range(start, end),
    partial_label,
)

if not has_operations(series):
    render_empty_state()
    st.stop()

render_kpi_rail(analysis["summary"], analysis["comparison"])
st.caption("Totais do período selecionado. A variação, quando exibida, compara o último ano com os mesmos meses do anterior.")
missing = {column: analysis["operational_data"][column].null_count()
           for column in ["PASSAGEIROS_PAGOS", "ASSENTOS", "DECOLAGENS", "RPK", "ASK"]}
months_with_records = analysis["operational_data"]["PERIODO"].n_unique()
if any(missing.values()) or months_with_records < series.height:
    st.warning("Há valores ausentes ou meses sem registro neste recorte. Os totais usam os valores informados; lacunas no gráfico não significam zero.")

render_section_header(
    "Evolução da rota",
    "Leitura mensal do recorte selecionado." if company is None else f"Operação de {company_map[company].split(' · ')[0]} no mercado.",
)
metric = st.segmented_control(
    "Métrica",
    ["Passageiros", "Assentos", "Load Factor", "Decolagens"],
    default="Passageiros",
    label_visibility="collapsed",
    key="market_pulse_metric",
)
st.plotly_chart(
    market_pulse_chart(series, metric or "Passageiros"),
    width="stretch",
    theme=None,
    config=CHART_CONFIG,
)

render_section_header("Oferta × demanda", "Capacidade ofertada e passageiros pagos, mês a mês.")
st.plotly_chart(capacity_chart(series), width="stretch", theme=None, config=CHART_CONFIG)

render_section_header("Ocupação", "Load Factor calculado pela razão entre RPK e ASK agregados.")
st.plotly_chart(load_factor_chart(series), width="stretch", theme=None, config=CHART_CONFIG)
st.caption("Alguns recortes da ANAC podem apresentar Load Factor acima de 100%.")

render_section_header("Estrutura competitiva", "Participação por passageiros no mercado total da rota.")
shares = analysis["shares"].with_columns(
    pl.struct("EMPRESA_SIGLA", "EMPRESA_NOME")
    .map_elements(
        lambda row: format_company_name(row["EMPRESA_SIGLA"], row["EMPRESA_NOME"]),
        return_dtype=pl.String,
    )
    .alias("DISPLAY_NAME")
)
share_col, hhi_col = st.columns([2, 1], vertical_alignment="center")
with share_col:
    st.plotly_chart(
        market_share_chart(shares, company),
        width="stretch",
        theme=None,
        config=CHART_CONFIG,
    )
with hhi_col:
    render_hhi(analysis["hhi"])
if company is not None:
    st.caption("A companhia selecionada é destacada, mas sua participação continua usando o mercado total da rota como denominador.")

render_section_header("Companhias na rota", "Ordenadas por passageiros no período selecionado.")
operators = analysis["operators"].select(
    pl.col("COMPANHIA").alias("Companhia"),
    pl.col("PASSAGEIROS_PAGOS").alias("Passageiros"),
    pl.col("MARKET_SHARE_PCT").alias("Participação"),
    pl.col("ASSENTOS").alias("Assentos"),
    pl.col("DECOLAGENS").alias("Decolagens"),
    pl.col("LOAD_FACTOR_PCT").alias("Load Factor"),
)
st.dataframe(
    operators,
    hide_index=True,
    width="stretch",
    column_config={
        "Passageiros": st.column_config.NumberColumn(format="localized"),
        "Participação": st.column_config.NumberColumn(format="%.1f%%"),
        "Assentos": st.column_config.NumberColumn(format="localized"),
        "Decolagens": st.column_config.NumberColumn(format="localized"),
        "Load Factor": st.column_config.NumberColumn(format="%.1f%%"),
    },
)

quality = analysis["quality"]
quality_labels = {
    "FLAG_RPK_MAIOR_ASK": "RPK > ASK",
    "FLAG_PASSAGEIROS_MAIOR_ASSENTOS": "Passageiros > assentos",
    "FLAG_ASK_ZERO_RPK_POSITIVO": "ASK zero com RPK positivo",
    "FLAG_DECOLAGENS_ZERO_PASSAGEIROS_POSITIVOS": "Decolagens zero com passageiros",
    "FLAG_ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS": "Assentos zero com passageiros",
}
warning_count = sum(quality.values())
quality_title = (
    "Qualidade dos dados · nenhuma das cinco anomalias detectada"
    if warning_count == 0
    else f"! Qualidade dos dados · {warning_count} ocorrências sinalizadas"
)
with st.expander(quality_title):
    for key, label in quality_labels.items():
        st.write(f"**{label}:** {quality.get(key, 0)}")
    st.write(f"**Meses sem registro:** {series.height - months_with_records}")
    st.write("**Valores ausentes:** " + " · ".join(f"{key}: {value}" for key, value in missing.items()))
    st.caption("Ocorrências não são registros únicos: uma linha pode ter mais de uma sinalização.")
    st.caption("Os registros foram preservados conforme a base de origem. O AVScope não corrige silenciosamente observações sinalizadas.")

with st.expander("Metodologia e fontes"):
    st.markdown(
        """
        **Fonte:** Dados Estatísticos do Transporte Aéreo da ANAC.  
        **Universo:** operações domésticas regulares com evidência histórica de passageiros.  
        **Rota:** direcional; ida e volta são mercados distintos.  
        **Load Factor:** soma de RPK dividida pela soma de ASK.  
        **HHI:** soma dos quadrados das participações percentuais das companhias.  
        **YTD:** ano parcial comparado aos mesmos meses do ano anterior.  
        **Qualidade:** observações sinalizadas são preservadas, nunca corrigidas silenciosamente.

        Consulte a aba **Sobre os dados** para conhecer as fontes, os conceitos e as limitações.
        """
    )

with st.expander("Exportar análise"):
    st.caption("CSV com separador ponto e vírgula, vírgula decimal e codificação compatível com Excel. Campos vazios representam dados ausentes.")
    metadata = [pl.lit(origin).alias("ORIGEM_ICAO"), pl.lit(destination).alias("DESTINO_ICAO"),
                pl.lit(start).alias("INICIO_RECORTE"), pl.lit(end).alias("FIM_RECORTE")]
    export_series = series.with_columns(*metadata, pl.lit(company or "TODAS").alias("COMPANHIA_RECORTE"))
    a, b = st.columns(2)
    with a:
        st.download_button("Baixar série mensal", csv_bytes(export_series),
                           file_name=f"avscope_{origin}_{destination}_mensal.csv", mime="text/csv", width="stretch")
    with b:
        st.download_button("Baixar companhias da rota", csv_bytes(analysis["operators"].with_columns(*metadata)),
                           file_name=f"avscope_{origin}_{destination}_companhias.csv", mime="text/csv", width="stretch")
    st.caption("A tabela de companhias mantém o mercado total da rota. Para compartilhar este recorte, copie o endereço do navegador; endereços locais funcionam apenas neste computador.")
st.caption(f"AVScope · Fonte: ANAC · Dados até {format_month(latest_period)} · Atualização da base mediante nova carga.")
