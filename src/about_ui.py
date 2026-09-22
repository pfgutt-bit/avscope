from __future__ import annotations

import polars as pl
import streamlit as st

from src.formatters import format_integer, format_month
from src.metrics import MAIN_METRICS, QUALITY_FLAGS


def render_about(data: pl.DataFrame, airports: pl.DataFrame) -> None:
    st.title("Sobre os dados")
    st.write("O AVScope acompanha a demanda, a oferta e a concorrência em rotas aéreas domésticas brasileiras.")
    st.info(f"Esta edição cobre {format_month(data['PERIODO'].min())} a {format_month(data['PERIODO'].max())}. A base é uma fotografia histórica; não há atualização automática.")
    a, b, c = st.columns(3)
    a.metric("Registros", format_integer(data.height))
    b.metric("Rotas direcionais", format_integer(data["ROTA_DIRECIONAL"].n_unique()))
    c.metric("Aeroportos", format_integer(airports.height))
    st.subheader("Critérios do produto")
    st.write("Voos regulares domésticos, com os dois aeroportos no Brasil, códigos presentes, origem diferente do destino e evidência histórica de transporte de passageiros na mesma rota-companhia. Meses zerados dessas operações são mantidos. Ida e volta são analisadas separadamente.")
    st.write("A evidência histórica caracteriza a operação ao longo do tempo; não comprova que cada linha individual corresponda exclusivamente a passageiros. Ausência de registro não é convertida em zero.")
    st.subheader("Indicadores")
    st.markdown("""
| Indicador | O que significa |
| --- | --- |
| Passageiros | Passageiros pagos registrados por trecho; não são pessoas únicas. |
| Assentos | Capacidade ofertada informada na fonte. |
| Decolagens | Quantidade de decolagens registrada. |
| ASK | Assentos ofertados multiplicados pela distância, em km. |
| RPK | Passageiros pagos multiplicados pela distância, em km. |
| Ocupação / Load Factor | Soma de RPK ÷ soma de ASK × 100. |
| Participação / Market share | Passageiros da companhia ÷ passageiros totais da rota. |
| HHI | Soma dos quadrados das participações percentuais; maior valor indica maior concentração. |
""")
    st.subheader("Qualidade e limites")
    flagged = data.filter(pl.any_horizontal([pl.col(flag).fill_null(False) for flag in QUALITY_FLAGS])).height
    st.write(f"{format_integer(flagged)} registros possuem pelo menos uma das cinco sinalizações operacionais. Uma linha pode ter mais de uma sinalização. Nenhuma delas foi removida ou corrigida automaticamente.")
    st.dataframe(pl.DataFrame({
        "Métrica": MAIN_METRICS,
        "Registros sem valor": [data[column].null_count() for column in MAIN_METRICS],
    }), hide_index=True, width="stretch")
    st.write("Nulos significam ausência de informação. Totais somam os valores informados e podem ser incompletos. Divisão por zero retorna valor ausente. Ocupação acima de 100% e passageiros acima de assentos permanecem visíveis com avisos.")
    st.write("No Descobrir mercados, o crescimento exige registros em todos os meses das duas janelas e passageiros sem nulos. Isso evita tratar lacunas como queda ou crescimento. Os dados não incluem tarifas, custos, margem ou previsão de demanda.")
    st.subheader("Fontes")
    st.markdown("""
- [Dados Estatísticos do Transporte Aéreo — ANAC](https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas/dados-estatisticos/dados-estatisticos)
- [Cadastro de aeródromos — SIROS/ANAC](https://siros.anac.gov.br/siros/registros/aerodromo/aerodromos.csv)
- [OurAirports](https://ourairports.com/data/), complemento de lacunas do cadastro.
""")
    st.caption(f"Chave interna: ICAO. {airports['IATA'].null_count()} aeroportos sem IATA continuam identificados pelo ICAO. AVScope é um explorador independente; não é um produto oficial da ANAC.")

