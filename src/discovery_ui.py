from __future__ import annotations

from datetime import date

import polars as pl
import plotly.graph_objects as go
import streamlit as st

from src.app_data import load_datasets
from src.charts import CHART_CONFIG, COLORS, _style
from src.discovery import SORTS, csv_bytes, discover_markets, filter_markets, label_markets
from src.formatters import MONTHS_PT, format_integer, format_month


@st.cache_data(show_spinner=False, max_entries=24)
def market_catalog(year: int, month: int) -> pl.DataFrame:
    data, airports, _ = load_datasets()
    return label_markets(discover_markets(data, year, month), airports)


def open_route(origin: str, destination: str, year: int, month: int) -> None:
    st.session_state.update({
        "navigation": "Explorar rota", "origin_icao": origin, "destination_icao": destination,
        "period_start": date(year, 1, 1), "period_end": date(year, month, 1), "company_id": None,
    })
    st.query_params.from_dict({
        "origin": origin, "destination": destination, "view": "route",
        "start": date(year, 1, 1).isoformat(), "end": date(year, month, 1).isoformat(),
    })


def _query_int(key: str, default: int, options: list[int]) -> int:
    try:
        value = int(st.query_params.get(key, default))
    except (ValueError, TypeError):
        return default
    return value if value in options else default


def render_discovery(data: pl.DataFrame) -> None:
    st.title("Descobrir mercados")
    st.write("Compare rotas domésticas e escolha um mercado para investigar.")
    years = sorted(data["ANO"].unique().to_list(), reverse=True)
    st.session_state.setdefault("discovery_year", _query_int("year", years[0], years))
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        year = st.selectbox("Ano", years, key="discovery_year")
    last_month = int(data.filter(pl.col("ANO") == year)["MES"].max())
    months = list(range(1, last_month + 1))
    st.session_state.setdefault("discovery_month", _query_int("month", last_month, months))
    if st.session_state["discovery_month"] not in months:
        st.session_state["discovery_month"] = last_month
    with c2:
        month = st.selectbox("Acumulado até", months, format_func=lambda x: MONTHS_PT[x - 1], key="discovery_month")
    with c3:
        order = st.selectbox("Ordenar por", list(SORTS), key="discovery_sort")
    st.query_params.from_dict({"view": "discover", "year": str(year), "month": str(month)})
    current_label = f"jan–{MONTHS_PT[month - 1]}/{year}"
    previous_label = f"jan–{MONTHS_PT[month - 1]}/{year - 1}"
    st.caption(f"{current_label} comparado com {previous_label}. Ida e volta permanecem separadas.")
    if last_month < 12:
        st.info(f"{year} parcial · dados disponíveis até {MONTHS_PT[last_month - 1]}. A comparação usa os mesmos meses do ano anterior.")
    with st.spinner("Comparando os mercados…"):
        catalog = market_catalog(year, month)
    with st.expander("Filtrar mercados", expanded=True):
        a, b, c, d = st.columns(4)
        with a:
            origin_uf = st.selectbox("UF de origem", [None, *sorted(catalog["UF_ORIGEM"].drop_nulls().unique().to_list())], format_func=lambda x: x or "Todas", key="discover_origin_uf")
        with b:
            destination_uf = st.selectbox("UF de destino", [None, *sorted(catalog["UF_DESTINO"].drop_nulls().unique().to_list())], format_func=lambda x: x or "Todas", key="discover_destination_uf")
        with c:
            minimum = st.number_input("Mínimo de passageiros", min_value=0, value=1000, step=1000, key="discover_minimum")
        with d:
            max_companies = st.selectbox("Companhias com passageiros", [None, 1, 2, 3], format_func=lambda x: "Qualquer quantidade" if x is None else f"Até {x}", key="discover_companies")
        comparable = st.checkbox("Somente rotas com crescimento comparável", key="discover_comparable")
    result = filter_markets(catalog, origin_uf=origin_uf, destination_uf=destination_uf,
                            min_passengers=int(minimum), max_companies=max_companies,
                            comparable_only=comparable, sort=order)
    if result.is_empty():
        st.info("Nenhum mercado atende aos filtros. Diminua o mínimo de passageiros ou amplie as UFs.")
        return
    a, b, c = st.columns(3)
    a.metric("Rotas encontradas", format_integer(result.height))
    b.metric("Passageiros registrados", format_integer(result["PASSAGEIROS_PAGOS"].sum()))
    c.metric("Rotas com dados sinalizados", format_integer(result.filter(pl.col("REGISTROS_SINALIZADOS") > 0).height))
    st.caption("Passageiros somados por trecho: esse total não representa pessoas únicas. Indicadores calculados sobre os valores informados.")
    top = result.head(12)
    column, _ = SORTS[order]
    valid_top = top.filter(pl.col(column).is_not_null())
    if not valid_top.is_empty():
        figure = go.Figure(go.Bar(
            x=valid_top[column].to_list(), y=valid_top["ROTA"].to_list(), orientation="h",
            marker_color=COLORS["accent"], hovertemplate="%{y}<br>%{x:,.2f}<extra></extra>",
        ))
        figure = _style(figure, height=max(240, valid_top.height * 30 + 50))
        figure.update_layout(hovermode="closest")
        figure.update_xaxes(tickmode="auto", tickformat=",.0f", title=order)
        figure.update_yaxes(autorange="reversed", type="category", tickformat=None, rangemode="normal")
        st.plotly_chart(figure, width="stretch", theme=None, config=CHART_CONFIG)
    st.subheader("Mercados do recorte")
    display = result.select(
        pl.col("ROTA").alias("Rota"),
        pl.col("PASSAGEIROS_PAGOS").alias("Passageiros"),
        pl.col("CRESCIMENTO_PCT").alias("Crescimento (%)"),
        pl.col("LOAD_FACTOR_PCT").alias("Ocupação (%)"),
        pl.col("COMPANHIAS_COM_PASSAGEIROS").alias("Companhias"),
        "HHI", pl.col("REGISTROS_SINALIZADOS").alias("Registros sinalizados"),
        pl.col("COMPARABILIDADE").alias("Comparação"),
    )
    st.dataframe(display, hide_index=True, width="stretch", column_config={
        "Passageiros": st.column_config.NumberColumn(format="localized"),
        "Crescimento (%)": st.column_config.NumberColumn(format="%.1f%%"),
        "Ocupação (%)": st.column_config.NumberColumn(format="%.1f%%"),
        "HHI": st.column_config.NumberColumn(format="%.0f"),
    })
    st.caption("Ocupação = RPK ÷ ASK. Crescimento fica em branco quando faltam meses ou valores de passageiros, ou a base anterior é zero. HHI usa participações sobre os passageiros informados; dados ausentes podem afetá-lo.")
    rows = {row["ROTA_DIRECIONAL"]: row for row in result.to_dicts()}
    selection = st.selectbox("Mercado para explorar", list(rows), format_func=lambda key: (
        f"{rows[key]['ROTA']} · {rows[key]['LOCAL_ORIGEM']} → {rows[key]['LOCAL_DESTINO']}"
    ), key="discover_selection")
    chosen = rows[selection]
    a, b = st.columns(2)
    with a:
        st.button("Explorar mercado selecionado →", type="primary", on_click=open_route,
                  args=(chosen["AEROPORTO_DE_ORIGEM_SIGLA"], chosen["AEROPORTO_DE_DESTINO_SIGLA"], year, month),
                  width="stretch")
    with b:
        st.download_button("Baixar mercados (CSV)", csv_bytes(result),
                           file_name=f"avscope_mercados_{year}_{month:02d}.csv", mime="text/csv", width="stretch")
    with st.expander("Como interpretar esta descoberta"):
        st.write("Este ranking descreve mercados já observados na base. Ocupação alta, crescimento ou poucas companhias são sinais para investigação; não estimam rentabilidade nem demanda de uma rota ainda inexistente.")
        st.write("Os filtros de UF usam o cadastro de aeroportos. Companhias são contadas quando têm passageiros pagos positivos no período. HHI não recebe uma classificação concorrencial automática. Os valores anômalos continuam visíveis e sinalizados.")
        st.write(f"Exportação: {current_label} e {previous_label}, códigos ICAO, métricas, cobertura mensal, nulos e sinalizações. O arquivo contém todas as rotas que atendem aos filtros.")

