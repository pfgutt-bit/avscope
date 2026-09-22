from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.process_data import MAIN_METRICS, nullable_sum, sha256_file
from src.universe import add_universe_flags as add_validation_flags
from src.universe import geography_expression, year_coverage


SOURCE_PATH = ROOT / "data" / "processed" / "avscope_routes_monthly.parquet"
VALIDATION_PATH = ROOT / "data" / "processed" / "avscope_mvp_validation.parquet"
REPORT_PATH = ROOT / "docs" / "validacao_mvp.md"

IATA_TO_SOURCE_CODE = {
    "BEL": "SBBE",
    "GRU": "SBGR",
    "CGH": "SBSP",
    "SDU": "SBRJ",
    "BSB": "SBBR",
    "MAO": "SBEG",
}

TEST_ROUTES = [
    ("BEL", "GRU"),
    ("GRU", "BEL"),
    ("CGH", "SDU"),
    ("SDU", "CGH"),
    ("GRU", "BSB"),
    ("BSB", "GRU"),
    ("BEL", "MAO"),
    ("MAO", "BEL"),
]

ANAC_DATA_METADATA_URL = (
    "https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/"
    "voos-e-operacoes-aereas/dados-estatisticos-do-transporte-aereo/"
    "48-dados-estatisticos-do-transporte-aereo"
)
ANAC_AIRPORT_METADATA_URL = (
    "https://www.gov.br/anac/pt-br/acesso-a-informacao/dados-abertos/areas-de-atuacao/"
    "aerodromos/aerodromos-publicos/aerodromos-publicos-caracteristicas-gerais/"
    "metadados-aerodromos-publicos-caracteristicas-gerais"
)


def collect(lf: pl.LazyFrame) -> pl.DataFrame:
    return lf.collect(engine="streaming")


def safe_ratio(numerator: str, denominator: str, multiplier: float, alias: str) -> pl.Expr:
    valid = pl.col(numerator).is_not_null() & pl.col(denominator).is_not_null() & (
        pl.col(denominator) > 0
    )
    return (
        pl.when(valid)
        .then(pl.col(numerator).cast(pl.Float64) / pl.col(denominator) * multiplier)
        .otherwise(None)
        .alias(alias)
    )


def source_route(iata_origin: str, iata_destination: str) -> str:
    return f"{IATA_TO_SOURCE_CODE[iata_origin]}>{IATA_TO_SOURCE_CODE[iata_destination]}"


def iata_route_mapping() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "ROTA_DIRECIONAL": [source_route(origin, destination) for origin, destination in TEST_ROUTES],
            "IATA_ORIGEM": [origin for origin, _ in TEST_ROUTES],
            "IATA_DESTINO": [destination for _, destination in TEST_ROUTES],
            "ROTA_IATA": [f"{origin}>{destination}" for origin, destination in TEST_ROUTES],
        }
    )


def test_route_monthly(base: pl.LazyFrame, coverage: pl.LazyFrame) -> pl.LazyFrame:
    route_map = iata_route_mapping().lazy()
    return (
        base.filter(pl.col("FLAG_UNIVERSO_MVP_RECOMENDADO"))
        .join(route_map, on="ROTA_DIRECIONAL", how="inner")
        .group_by(
            [
                "ANO",
                "MES",
                "PERIODO",
                "ROTA_DIRECIONAL",
                "ROTA_IATA",
                "IATA_ORIGEM",
                "IATA_DESTINO",
                "AEROPORTO_DE_ORIGEM_SIGLA",
                "AEROPORTO_DE_ORIGEM_NOME",
                "AEROPORTO_DE_DESTINO_SIGLA",
                "AEROPORTO_DE_DESTINO_NOME",
            ]
        )
        .agg(
            *[nullable_sum(column) for column in MAIN_METRICS],
            pl.col("EMPRESA_ID").n_unique().alias("COMPANHIAS_NO_MES"),
            pl.len().alias("REGISTROS_FONTE"),
        )
        .with_columns(
            safe_ratio("RPK", "ASK", 100.0, "LOAD_FACTOR_PCT"),
            safe_ratio(
                "PASSAGEIROS_PAGOS",
                "DECOLAGENS",
                1.0,
                "PASSAGEIROS_POR_DECOLAGEM",
            ),
            pl.lit("DOMESTICA_BRASILEIRA").alias("ESCOPO_GEOGRAFICO"),
            pl.lit("DOMÉSTICA").alias("NATUREZA"),
            pl.lit("REGULAR").alias("GRUPO_DE_VOO"),
            pl.lit(True).alias("FLAG_ROTA_OD_VALIDA"),
            pl.lit(True).alias("FLAG_REGULAR_PASSAGEIROS_HISTORICO"),
            pl.lit(True).alias("FLAG_UNIVERSO_MVP_RECOMENDADO"),
        )
        .join(coverage, on="ANO", how="left")
        .sort(["ROTA_IATA", "PERIODO"])
    )


def universe_summary(base: pl.LazyFrame, flag: str) -> dict[str, Any]:
    selected = base.filter(pl.col(flag))
    result = collect(
        selected.select(
            pl.len().alias("REGISTROS"),
            pl.col("PASSAGEIROS_PAGOS").sum().alias("PASSAGEIROS_PAGOS"),
            pl.col("ROTA_DIRECIONAL").drop_nulls().n_unique().alias("ROTAS"),
            pl.col("EMPRESA_ID").n_unique().alias("COMPANHIAS"),
            pl.col("PERIODO").min().alias("PERIODO_MIN"),
            pl.col("PERIODO").max().alias("PERIODO_MAX"),
        )
    ).to_dicts()[0]
    airports = pl.concat(
        [
            selected.select(pl.col("AEROPORTO_DE_ORIGEM_SIGLA").alias("AEROPORTO")),
            selected.select(pl.col("AEROPORTO_DE_DESTINO_SIGLA").alias("AEROPORTO")),
        ],
        how="vertical",
    )
    result["AEROPORTOS"] = int(
        collect(airports.select(pl.col("AEROPORTO").drop_nulls().n_unique().alias("N")))["N"][0]
    )
    return result


def airport_code_validation(lf: pl.LazyFrame) -> list[dict[str, Any]]:
    codes = list(IATA_TO_SOURCE_CODE.values())
    origin = lf.filter(pl.col("AEROPORTO_DE_ORIGEM_SIGLA").is_in(codes)).select(
        pl.col("AEROPORTO_DE_ORIGEM_SIGLA").alias("CODIGO_FONTE"),
        pl.col("AEROPORTO_DE_ORIGEM_NOME").alias("NOME_FONTE"),
    )
    destination = lf.filter(pl.col("AEROPORTO_DE_DESTINO_SIGLA").is_in(codes)).select(
        pl.col("AEROPORTO_DE_DESTINO_SIGLA").alias("CODIGO_FONTE"),
        pl.col("AEROPORTO_DE_DESTINO_NOME").alias("NOME_FONTE"),
    )
    observed = collect(pl.concat([origin, destination]).drop_nulls().unique().sort("CODIGO_FONTE"))
    names_by_code = {
        code: "; ".join(
            observed.filter(pl.col("CODIGO_FONTE") == code)["NOME_FONTE"].unique().sort().to_list()
        )
        for code in codes
    }
    return [
        {
            "IATA_EXIBICAO": iata,
            "CODIGO_INTERNO_FONTE": code,
            "NOME_NO_DATASET": names_by_code[code],
        }
        for iata, code in IATA_TO_SOURCE_CODE.items()
    ]


def anomaly_condition(name: str) -> pl.Expr:
    conditions = {
        "RPK_MAIOR_ASK": (pl.col("RPK") > pl.col("ASK"))
        & pl.col("RPK").is_not_null()
        & pl.col("ASK").is_not_null(),
        "PASSAGEIROS_MAIOR_ASSENTOS": (pl.col("PASSAGEIROS_PAGOS") > pl.col("ASSENTOS"))
        & pl.col("PASSAGEIROS_PAGOS").is_not_null()
        & pl.col("ASSENTOS").is_not_null(),
        "ORIGEM_IGUAL_DESTINO": (
            pl.col("AEROPORTO_DE_ORIGEM_SIGLA") == pl.col("AEROPORTO_DE_DESTINO_SIGLA")
        ).fill_null(False),
        "CODIGO_AEROPORTO_AUSENTE": pl.col("AEROPORTO_DE_ORIGEM_SIGLA").is_null()
        | pl.col("AEROPORTO_DE_DESTINO_SIGLA").is_null(),
        "ASK_ZERO_RPK_POSITIVO": ((pl.col("ASK") == 0) & (pl.col("RPK") > 0)).fill_null(False),
        "DECOLAGENS_ZERO_PASSAGEIROS_POSITIVOS": (
            (pl.col("DECOLAGENS") == 0) & (pl.col("PASSAGEIROS_PAGOS") > 0)
        ).fill_null(False),
        "ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS": (
            (pl.col("ASSENTOS") == 0) & (pl.col("PASSAGEIROS_PAGOS") > 0)
        ).fill_null(False),
    }
    return conditions[name]


def anomaly_summary(candidate: pl.LazyFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    names = [
        "RPK_MAIOR_ASK",
        "PASSAGEIROS_MAIOR_ASSENTOS",
        "ORIGEM_IGUAL_DESTINO",
        "CODIGO_AEROPORTO_AUSENTE",
        "ASK_ZERO_RPK_POSITIVO",
        "DECOLAGENS_ZERO_PASSAGEIROS_POSITIVOS",
        "ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS",
    ]
    totals: list[dict[str, Any]] = []
    concentrations: list[dict[str, Any]] = []
    for name in names:
        affected = candidate.filter(anomaly_condition(name))
        total = collect(
            affected.select(
                pl.len().alias("CASOS"),
                pl.col("PERIODO").min().alias("PRIMEIRO_PERIODO"),
                pl.col("PERIODO").max().alias("ULTIMO_PERIODO"),
                pl.col("EMPRESA_ID").n_unique().alias("COMPANHIAS"),
                pl.col("ROTA_DIRECIONAL").drop_nulls().n_unique().alias("ROTAS"),
            )
        ).to_dicts()[0]
        totals.append({"ANOMALIA": name, **total})

        by_year = collect(
            affected.group_by("ANO")
            .agg(pl.len().alias("CASOS"))
            .sort("CASOS", descending=True)
            .limit(5)
        ).to_dicts()
        concentrations.extend({"ANOMALIA": name, **row} for row in by_year)
    return totals, concentrations


def route_summaries(
    base: pl.LazyFrame, route_monthly: pl.DataFrame
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    route_map = iata_route_mapping().lazy()
    selected = base.filter(pl.col("FLAG_UNIVERSO_MVP_RECOMENDADO")).join(
        route_map, on="ROTA_DIRECIONAL", how="inner"
    )
    summaries = collect(
        selected.group_by(["ROTA_IATA", "ROTA_DIRECIONAL"])
        .agg(
            pl.col("PERIODO").min().alias("PRIMEIRO_MES"),
            pl.col("PERIODO").max().alias("ULTIMO_MES"),
            pl.col("PERIODO").n_unique().alias("MESES_COM_REGISTROS"),
            pl.col("EMPRESA_ID").n_unique().alias("QTD_COMPANHIAS"),
            pl.col("EMPRESA_SIGLA").unique().sort().implode().alias("COMPANHIAS"),
            *[nullable_sum(column) for column in MAIN_METRICS],
        )
        .sort("ROTA_IATA")
    ).to_dicts()
    for row in summaries:
        row["COMPANHIAS"] = ", ".join(row["COMPANHIAS"])

    last_12: dict[str, list[dict[str, Any]]] = {}
    for route in [f"{origin}>{destination}" for origin, destination in TEST_ROUTES]:
        rows = (
            route_monthly.filter(pl.col("ROTA_IATA") == route)
            .sort("PERIODO", descending=True)
            .head(12)
            .sort("PERIODO")
            .select(
                "PERIODO",
                "COMPANHIAS_NO_MES",
                *MAIN_METRICS,
                "LOAD_FACTOR_PCT",
                "PASSAGEIROS_POR_DECOLAGEM",
            )
            .to_dicts()
        )
        last_12[route] = rows
    return summaries, last_12


def market_share_example(
    base: pl.LazyFrame, latest_complete_year: int
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    route_map = iata_route_mapping().lazy()
    candidates = (
        base.filter(
            pl.col("FLAG_UNIVERSO_MVP_RECOMENDADO") & (pl.col("ANO") == latest_complete_year)
        )
        .join(route_map, on="ROTA_DIRECIONAL", how="inner")
        .group_by(["ROTA_IATA", "ROTA_DIRECIONAL", "EMPRESA_ID", "EMPRESA_SIGLA", "EMPRESA_NOME"])
        .agg(nullable_sum("PASSAGEIROS_PAGOS"))
    )
    route_choice = collect(
        candidates.group_by(["ROTA_IATA", "ROTA_DIRECIONAL"])
        .agg(
            pl.col("EMPRESA_ID").filter(pl.col("PASSAGEIROS_PAGOS") > 0).n_unique().alias(
                "COMPANHIAS_COM_PASSAGEIROS"
            ),
            pl.col("PASSAGEIROS_PAGOS").sum().alias("PASSAGEIROS_ROTA"),
        )
        .filter(pl.col("COMPANHIAS_COM_PASSAGEIROS") > 1)
        .sort("PASSAGEIROS_ROTA", descending=True)
        .limit(1)
    ).to_dicts()[0]

    companies = collect(
        candidates.filter(pl.col("ROTA_DIRECIONAL") == route_choice["ROTA_DIRECIONAL"])
        .with_columns(pl.lit(route_choice["PASSAGEIROS_ROTA"]).alias("PASSAGEIROS_ROTA"))
        .with_columns(
            safe_ratio("PASSAGEIROS_PAGOS", "PASSAGEIROS_ROTA", 100.0, "MARKET_SHARE_PCT")
        )
        .sort("MARKET_SHARE_PCT", descending=True)
    )
    shares = companies["MARKET_SHARE_PCT"].drop_nulls()
    summary = {
        "ANO": latest_complete_year,
        **route_choice,
        "SOMA_MARKET_SHARE_PCT": float(shares.sum()),
        "HHI": float((shares**2).sum()),
    }
    return summary, companies.to_dicts()


def current_flag_audit(base: pl.LazyFrame) -> dict[str, Any]:
    current_regular = (pl.col("GRUPO_DE_VOO") == "REGULAR").fill_null(False)
    current_universe = current_regular & pl.col("FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS")
    return collect(
        base.select(
            (pl.col("FLAG_VOO_REGULAR") != current_regular).sum().alias("ERROS_FLAG_REGULAR"),
            (pl.col("FLAG_UNIVERSO_MVP") != current_universe).sum().alias("ERROS_FLAG_UNIVERSO"),
            pl.col("FLAG_UNIVERSO_MVP").sum().alias("REGISTROS_FLAG_ATUAL"),
            (
                pl.col("FLAG_CANDIDATO_MVP_DOMESTICO")
                & ~pl.col("FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS")
            )
            .sum()
            .alias("MESES_RECUPERADOS_PELO_HISTORICO_CANDIDATO"),
            (
                pl.col("FLAG_UNIVERSO_MVP_RECOMENDADO")
                & ~pl.col("FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS")
            )
            .sum()
            .alias("MESES_RECUPERADOS_PELO_HISTORICO_MVP"),
            (
                pl.col("FLAG_CANDIDATO_MVP_DOMESTICO")
                & ~pl.col("FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS")
                & (pl.col("DECOLAGENS") > 0)
            )
            .fill_null(False)
            .sum()
            .alias("MESES_RECUPERADOS_COM_DECOLAGENS"),
        )
    ).to_dicts()[0]


def md_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_Nenhum registro._"

    def text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.4f}"
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    lines.extend("| " + " | ".join(text(row.get(column)) for column in columns) + " |" for row in rows)
    return "\n".join(lines)


def write_report(stats: dict[str, Any]) -> None:
    route_sections = []
    route_summary_by_name = {row["ROTA_IATA"]: row for row in stats["route_summaries"]}
    for origin, destination in TEST_ROUTES:
        route = f"{origin}>{destination}"
        summary = route_summary_by_name.get(route)
        route_sections.append(f"### `{origin} -> {destination}`\n")
        if summary is None:
            route_sections.append("Rota nao localizada no universo recomendado.\n")
            continue
        route_sections.append(
            md_table(
                [summary],
                [
                    "ROTA_DIRECIONAL",
                    "PRIMEIRO_MES",
                    "ULTIMO_MES",
                    "MESES_COM_REGISTROS",
                    "QTD_COMPANHIAS",
                    "COMPANHIAS",
                    *MAIN_METRICS,
                ],
            )
        )
        route_sections.append("\n\nUltimos 12 meses disponiveis:\n")
        route_sections.append(
            md_table(
                stats["last_12"][route],
                [
                    "PERIODO",
                    "COMPANHIAS_NO_MES",
                    *MAIN_METRICS,
                    "LOAD_FACTOR_PCT",
                    "PASSAGEIROS_POR_DECOLAGEM",
                ],
            )
        )
        route_sections.append("\n")

    latest_route_values = {
        row["ROTA_IATA"]: row for row in stats["last_12_totals"]
    }
    direction_rows = []
    for forward, reverse in [("BEL>GRU", "GRU>BEL"), ("CGH>SDU", "SDU>CGH"), ("GRU>BSB", "BSB>GRU"), ("BEL>MAO", "MAO>BEL")]:
        for route in [forward, reverse]:
            row = latest_route_values.get(route, {"ROTA_IATA": route})
            direction_rows.append(row)

    report = f"""# Validacao metodologica do universo do MVP

Gerado em: `{datetime.now().isoformat(timespec='seconds')}`

Fonte: `data/processed/avscope_routes_monthly.parquet`. O arquivo principal nao foi alterado.

## Flags atuais

- `FLAG_VOO_REGULAR`: verdadeira quando `GRUPO_DE_VOO == "REGULAR"`; nulos viram `False`.
- `FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS`: verdadeira quando pelo menos um destes campos e maior que zero: `PASSAGEIROS_PAGOS`, `PASSAGEIROS_GRATIS`, `ASSENTOS`, `ASK` ou `RPK`.
- `FLAG_UNIVERSO_MVP`: conjuncao de `FLAG_VOO_REGULAR` e `FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS`.

A regra nao exige `PASSAGEIROS_PAGOS > 0`: uma etapa com zero passageiros pagos permanece quando ha oferta ou outra evidencia positiva. Entretanto, `DECOLAGENS` nao participa da expressao. Alem disso, a evidencia e avaliada linha a linha, o que elimina meses zerados de uma rota-companhia que possui operacao de passageiros comprovada em outros meses.

Nao e adequado simplesmente acrescentar `DECOLAGENS > 0` a regra da linha, porque operacoes exclusivamente cargueiras tambem decolam. A evidencia historica no mesmo par rota-companhia inclui a continuidade dos meses zerados sem transformar toda decolagem regular em transporte de passageiros.

A implementacao das flags persistidas confere com o codigo: `{stats['flag_audit']['ERROS_FLAG_REGULAR']}` divergencias em `FLAG_VOO_REGULAR` e `{stats['flag_audit']['ERROS_FLAG_UNIVERSO']}` em `FLAG_UNIVERSO_MVP`. A regra historica recupera `{stats['flag_audit']['MESES_RECUPERADOS_PELO_HISTORICO_MVP']}` meses no universo final, dos quais `{stats['flag_audit']['MESES_RECUPERADOS_COM_DECOLAGENS']}` no universo candidato possuem decolagens positivas. Portanto, usar a flag atual como filtro definitivo causaria vies de selecao temporal.

## Universo recomendado

A validacao propoe duas camadas:

1. `FLAG_CANDIDATO_MVP_DOMESTICO`: `GRUPO_DE_VOO = REGULAR`, `NATUREZA = DOMÉSTICA`, ambos os paises iguais a `BRASIL` e evidencia positiva de passageiros em pelo menos um mes regular da mesma `ROTA_DIRECIONAL + EMPRESA_ID`.
2. `FLAG_UNIVERSO_MVP_RECOMENDADO`: camada anterior mais codigo de origem e destino presentes e origem diferente do destino.

Isso inclui meses com zero passageiros na continuidade de uma operacao de passageiros, exclui rotas puramente cargueiras sem evidencia historica e separa registros que nao representam um mercado origem-destino valido. Nenhum registro foi removido do Parquet principal.

### Comparacao de escopos

{md_table(stats['universe_comparison'], ['UNIVERSO', 'REGISTROS', 'PASSAGEIROS_PAGOS', 'ROTAS', 'COMPANHIAS', 'AEROPORTOS', 'PERIODO_MIN', 'PERIODO_MAX'])}

O universo com internacional inclui rotas geograficamente domesticas e rotas com exatamente uma ponta no Brasil, desde que regulares, validas e com evidencia historica de passageiros. `DEMAIS_CASOS` nao entra.

## Codigos de aeroportos

{md_table(stats['airport_codes'], ['IATA_EXIBICAO', 'CODIGO_INTERNO_FONTE', 'NOME_NO_DATASET'])}

Os campos `AEROPORTO_DE_ORIGEM_SIGLA` e `AEROPORTO_DE_DESTINO_SIGLA` contem codigos de quatro letras compatíveis com designadores OACI/ICAO, como `SBBE` e `SBGR`. O dataset nao possui coluna IATA. A chave interna continua usando o codigo oficial de quatro letras da fonte; para exibicao, o futuro app deve juntar uma tabela aeroportuaria oficial OACI-IATA e mostrar o IATA com o nome. A tabela acima e apenas o mapeamento validado das seis localidades usadas neste teste.

Fontes metodologicas: [metadados dos Dados Estatisticos do Transporte Aereo da ANAC]({ANAC_DATA_METADATA_URL}) e [metadados de Aerodromos Publicos da ANAC]({ANAC_AIRPORT_METADATA_URL}).

## Rotas de teste

{''.join(route_sections)}

## Ida e volta

As chaves usam origem e destino em ordem. Portanto, `SBBE>SBGR` e `SBGR>SBBE` sao distintas, assim como todas as demais duplas testadas. Os totais dos ultimos 12 meses disponiveis confirmam que as metricas podem divergir por sentido:

{md_table(direction_rows, ['ROTA_IATA', *MAIN_METRICS, 'LOAD_FACTOR_PCT', 'PASSAGEIROS_POR_DECOLAGEM'])}

Nao foi criada rota nao direcional.

## Calculo de indicadores

- `LOAD_FACTOR_PCT = SUM(RPK) / SUM(ASK) * 100`. O resultado e nulo quando `ASK` e nulo ou menor/igual a zero.
- `PASSAGEIROS_POR_DECOLAGEM = SUM(PASSAGEIROS_PAGOS) / SUM(DECOLAGENS)`. O resultado e nulo quando `DECOLAGENS` e nulo ou menor/igual a zero.
- Nenhuma media simples de percentuais foi usada.

Exemplo mais recente da rota `{stats['metric_example']['ROTA_IATA']}` em `{stats['metric_example']['PERIODO']}`: `RPK = {stats['metric_example']['RPK']}`, `ASK = {stats['metric_example']['ASK']}` e `LOAD_FACTOR_PCT = {stats['metric_example']['LOAD_FACTOR_PCT']:.4f}%`. Passageiros pagos por decolagem: `{stats['metric_example']['PASSAGEIROS_POR_DECOLAGEM']:.4f}`.

## Market share e HHI

Foi escolhida automaticamente, entre as rotas de teste, a rota com maior volume e mais de uma companhia no ultimo ano completo: `{stats['market']['ROTA_IATA']}`, ano `{stats['market']['ANO']}`.

{md_table(stats['market_companies'], ['EMPRESA_SIGLA', 'EMPRESA_NOME', 'PASSAGEIROS_PAGOS', 'MARKET_SHARE_PCT'])}

- Soma dos market shares: `{stats['market']['SOMA_MARKET_SHARE_PCT']:.8f}%`.
- HHI em escala 0-100: `{stats['market']['HHI']:.4f}`.

O HHI foi calculado como a soma dos quadrados dos shares. Nenhuma classificacao concorrencial foi aplicada.

## Anos completos e parciais

{md_table(stats['year_coverage'], ['ANO', 'MESES_DISPONIVEIS', 'PRIMEIRO_MES_DISPONIVEL', 'ULTIMO_MES_DISPONIVEL', 'ANO_COMPLETO', 'ANO_PARCIAL'])}

Regra: um ano e completo somente quando contem os 12 meses de janeiro a dezembro. O ultimo ano disponivel e `{stats['latest_year']}`, com dados ate o mes `{stats['latest_month']}`, e deve ser tratado como parcial. Uma comparacao com `{stats['latest_year'] - 1}` deve usar janeiro a mes `{stats['latest_month']}` nos dois anos. Totais anuais completos nunca devem ser comparados diretamente com esse acumulado parcial.

Exemplo YTD do universo recomendado, janeiro a mes `{stats['latest_month']}`: `{stats['latest_year'] - 1}` teve `{stats['ytd_previous']}` passageiros pagos e `{stats['latest_year']}` teve `{stats['ytd_current']}`. A variacao calculada sobre periodos equivalentes e `{stats['ytd_growth_pct']:.4f}%`.

## Anomalias no candidato domestico

Os controles abaixo sao calculados antes de retirar origem igual a destino, para que esses casos permaneçam visiveis na validacao:

{md_table(stats['anomalies'], ['ANOMALIA', 'CASOS', 'PRIMEIRO_PERIODO', 'ULTIMO_PERIODO', 'COMPANHIAS', 'ROTAS'])}

Anos com maior concentracao:

{md_table(stats['anomaly_concentrations'], ['ANOMALIA', 'ANO', 'CASOS'])}

Tratamento recomendado:

- `RPK_MAIOR_ASK`: os casos domesticos vao de 2000 a 2018 e se concentram em 2005-2009, indicando forte componente historico. Sinalizar. O Load Factor pode superar 100%, mas nao deve ser truncado. A ressalva da ANAC sobre desagregacao por rota de empresas estrangeiras explica parte do problema no universo internacional, mas nao explica sozinha os casos domesticos.
- `PASSAGEIROS_MAIOR_ASSENTOS`: ocorre desde 2000 e ainda aparece em 2026, portanto nao e apenas legado historico. Sinalizar e impedir qualquer indicador que use passageiros/assentos como taxa de ocupacao. Nao excluir automaticamente passageiros de market share sem validacao adicional.
- `ORIGEM_IGUAL_DESTINO`: persiste ate 2026. Pode refletir etapas especiais ou registros operacionais, mas nao representa um mercado origem-destino. Preservar na base principal e excluir do universo de mercado pela `FLAG_ROTA_OD_VALIDA`.
- `CODIGO_AEROPORTO_AUSENTE`: preservar e sinalizar; nao construir chave de rota nem usar em metricas por mercado.
- `ASK_ZERO_RPK_POSITIVO`: os casos terminam em 2018 e parecem uma inconsistencia historica. Manter o registro, sinalizar e retornar Load Factor nulo.
- `DECOLAGENS_ZERO_PASSAGEIROS_POSITIVOS`: manter e retornar passageiros por decolagem nulo.
- `ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS`: ainda ocorre em 2025, portanto nao deve ser tratado apenas como problema historico. Sinalizar e nao usar em indicadores baseados em assentos.

## Artefato de validacao

`data/processed/avscope_mvp_validation.parquet` contem apenas as oito rotas de teste, agregadas por mes no universo recomendado. Ele inclui as somas, indicadores com divisao segura e flags de ano completo/parcial. Nao substitui a base principal.

## Recomendacoes antes do app

1. Substituir, na proxima versao metodologica, o uso direto de `FLAG_UNIVERSO_MVP` pela regra historica e geografica validada nesta etapa.
2. Manter `NATUREZA` e a classificacao geografica separadas, pois medem conceitos diferentes.
3. Criar uma dimensao aeroportuaria oficial OACI-IATA antes da interface; nao derivar IATA por manipulacao de texto.
4. Aplicar `FLAG_ROTA_OD_VALIDA` nas telas de mercado e manter as anomalias disponiveis para auditoria.
5. Centralizar Load Factor, passageiros por decolagem, market share, HHI e comparacao YTD no modulo oficial de metricas da Etapa 4.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def run_validation() -> dict[str, Any]:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(SOURCE_PATH)

    source_hash_before = sha256_file(SOURCE_PATH)
    source = pl.scan_parquet(SOURCE_PATH)
    base = add_validation_flags(source)
    coverage_lf = year_coverage(source)
    coverage = collect(coverage_lf)
    latest_year = int(coverage["ANO"].max())
    latest_month = int(
        coverage.filter(pl.col("ANO") == latest_year)["ULTIMO_MES_DISPONIVEL"][0]
    )
    latest_complete_year = int(coverage.filter(pl.col("ANO_COMPLETO"))["ANO"].max())

    route_monthly_lf = test_route_monthly(base, coverage_lf)
    route_monthly = collect(route_monthly_lf)
    VALIDATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = VALIDATION_PATH.with_suffix(".tmp.parquet")
    if temporary_path.exists():
        temporary_path.unlink()
    route_monthly.write_parquet(temporary_path, compression="zstd", statistics=True)
    os.replace(temporary_path, VALIDATION_PATH)

    candidate = base.filter(pl.col("FLAG_CANDIDATO_MVP_DOMESTICO"))
    anomalies, concentrations = anomaly_summary(candidate)
    route_summary_rows, last_12 = route_summaries(base, route_monthly)

    last_12_totals = []
    for route, rows in last_12.items():
        frame = pl.DataFrame(rows)
        if frame.is_empty():
            continue
        totals: dict[str, Any] = {"ROTA_IATA": route}
        for metric in MAIN_METRICS:
            totals[metric] = frame[metric].sum()
        totals["LOAD_FACTOR_PCT"] = (
            totals["RPK"] / totals["ASK"] * 100 if totals["ASK"] not in (None, 0) else None
        )
        totals["PASSAGEIROS_POR_DECOLAGEM"] = (
            totals["PASSAGEIROS_PAGOS"] / totals["DECOLAGENS"]
            if totals["DECOLAGENS"] not in (None, 0)
            else None
        )
        last_12_totals.append(totals)

    market, market_companies = market_share_example(base, latest_complete_year)
    metric_example = (
        route_monthly.filter(
            pl.col("ASK").is_not_null()
            & (pl.col("ASK") > 0)
            & pl.col("RPK").is_not_null()
            & pl.col("DECOLAGENS").is_not_null()
            & (pl.col("DECOLAGENS") > 0)
        )
        .sort("PERIODO", descending=True)
        .row(0, named=True)
    )

    ytd = collect(
        base.filter(
            pl.col("FLAG_UNIVERSO_MVP_RECOMENDADO")
            & pl.col("ANO").is_in([latest_year - 1, latest_year])
            & (pl.col("MES") <= latest_month)
        )
        .group_by("ANO")
        .agg(pl.col("PASSAGEIROS_PAGOS").sum().alias("PASSAGEIROS_PAGOS"))
        .sort("ANO")
    )
    ytd_values = dict(zip(ytd["ANO"].to_list(), ytd["PASSAGEIROS_PAGOS"].to_list()))
    ytd_previous = int(ytd_values[latest_year - 1])
    ytd_current = int(ytd_values[latest_year])

    universe_comparison = []
    for label, flag in [
        ("CANDIDATO_DOMESTICO_ANTES_DA_VALIDACAO_OD", "FLAG_CANDIDATO_MVP_DOMESTICO"),
        ("MVP_DOMESTICO_RECOMENDADO", "FLAG_UNIVERSO_MVP_RECOMENDADO"),
        ("REGULAR_PASSAGEIROS_INCLUINDO_INTERNACIONAL", "FLAG_UNIVERSO_REGULAR_COM_INTERNACIONAL"),
    ]:
        universe_comparison.append({"UNIVERSO": label, **universe_summary(base, flag)})

    stats = {
        "flag_audit": current_flag_audit(base),
        "universe_comparison": universe_comparison,
        "airport_codes": airport_code_validation(source),
        "route_summaries": route_summary_rows,
        "last_12": last_12,
        "last_12_totals": last_12_totals,
        "metric_example": metric_example,
        "market": market,
        "market_companies": market_companies,
        "year_coverage": coverage.to_dicts(),
        "latest_year": latest_year,
        "latest_month": latest_month,
        "ytd_previous": ytd_previous,
        "ytd_current": ytd_current,
        "ytd_growth_pct": (ytd_current / ytd_previous - 1) * 100,
        "anomalies": anomalies,
        "anomaly_concentrations": concentrations,
    }
    write_report(stats)

    source_hash_after = sha256_file(SOURCE_PATH)
    if source_hash_before != source_hash_after:
        raise RuntimeError("A base processada principal foi alterada durante a validacao.")

    result = {
        "fonte_preservada": True,
        "fonte_sha256": source_hash_after,
        "validacao_registros": route_monthly.height,
        "validacao_bytes": VALIDATION_PATH.stat().st_size,
        "mvp_recomendado": universe_comparison[1],
        "incluindo_internacional": universe_comparison[2],
        "market_share": market,
        "relatorio": str(REPORT_PATH.relative_to(ROOT)),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return result


if __name__ == "__main__":
    run_validation()

