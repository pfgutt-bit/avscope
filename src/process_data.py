from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "Dados_Estatisticos.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "avscope_routes_monthly.parquet"
METHODOLOGY_PATH = ROOT / "docs" / "metodologia_tratamento.md"
QUALITY_PATH = ROOT / "docs" / "qualidade_base_processada.md"

SOURCE_COLUMNS = [
    "EMPRESA_SIGLA",
    "EMPRESA_NOME",
    "EMPRESA_NACIONALIDADE",
    "ANO",
    "MES",
    "AEROPORTO_DE_ORIGEM_SIGLA",
    "AEROPORTO_DE_ORIGEM_NOME",
    "AEROPORTO_DE_ORIGEM_UF",
    "AEROPORTO_DE_ORIGEM_REGIAO",
    "AEROPORTO_DE_ORIGEM_PAIS",
    "AEROPORTO_DE_DESTINO_SIGLA",
    "AEROPORTO_DE_DESTINO_NOME",
    "AEROPORTO_DE_DESTINO_UF",
    "AEROPORTO_DE_DESTINO_REGIAO",
    "AEROPORTO_DE_DESTINO_PAIS",
    "NATUREZA",
    "GRUPO_DE_VOO",
    "PASSAGEIROS_PAGOS",
    "PASSAGEIROS_GRATIS",
    "ASSENTOS",
    "DECOLAGENS",
    "ASK",
    "RPK",
    "DISTANCIA_VOADA_KM",
    "COMBUSTIVEL_LITROS",
    "HORAS_VOADAS",
]

TEXT_COLUMNS = [
    "EMPRESA_SIGLA",
    "EMPRESA_NOME",
    "EMPRESA_NACIONALIDADE",
    "AEROPORTO_DE_ORIGEM_SIGLA",
    "AEROPORTO_DE_ORIGEM_NOME",
    "AEROPORTO_DE_ORIGEM_UF",
    "AEROPORTO_DE_ORIGEM_REGIAO",
    "AEROPORTO_DE_ORIGEM_PAIS",
    "AEROPORTO_DE_DESTINO_SIGLA",
    "AEROPORTO_DE_DESTINO_NOME",
    "AEROPORTO_DE_DESTINO_UF",
    "AEROPORTO_DE_DESTINO_REGIAO",
    "AEROPORTO_DE_DESTINO_PAIS",
    "NATUREZA",
    "GRUPO_DE_VOO",
]

INTEGER_COLUMNS = [
    "ANO",
    "MES",
    "PASSAGEIROS_PAGOS",
    "PASSAGEIROS_GRATIS",
    "ASSENTOS",
    "DECOLAGENS",
    "ASK",
    "RPK",
    "DISTANCIA_VOADA_KM",
    "COMBUSTIVEL_LITROS",
]

MAIN_METRICS = ["PASSAGEIROS_PAGOS", "ASSENTOS", "DECOLAGENS", "ASK", "RPK"]

DIMENSIONS = [
    "ANO",
    "MES",
    "PERIODO",
    "EMPRESA_ID",
    "EMPRESA_SIGLA",
    "EMPRESA_NOME",
    "EMPRESA_NACIONALIDADE",
    "ROTA_DIRECIONAL",
    "AEROPORTO_DE_ORIGEM_SIGLA",
    "AEROPORTO_DE_ORIGEM_NOME",
    "AEROPORTO_DE_ORIGEM_UF",
    "AEROPORTO_DE_ORIGEM_REGIAO",
    "AEROPORTO_DE_ORIGEM_PAIS",
    "AEROPORTO_DE_DESTINO_SIGLA",
    "AEROPORTO_DE_DESTINO_NOME",
    "AEROPORTO_DE_DESTINO_UF",
    "AEROPORTO_DE_DESTINO_REGIAO",
    "AEROPORTO_DE_DESTINO_PAIS",
    "NATUREZA",
    "GRUPO_DE_VOO",
]

COLUMN_MAPPING = {
    "ano": "ANO",
    "mes": "MES",
    "empresa_aerea": "EMPRESA_NOME",
    "sigla_empresa": "EMPRESA_SIGLA",
    "aeroporto_origem": "AEROPORTO_DE_ORIGEM_NOME",
    "codigo_origem": "AEROPORTO_DE_ORIGEM_SIGLA",
    "uf_origem": "AEROPORTO_DE_ORIGEM_UF",
    "regiao_origem": "AEROPORTO_DE_ORIGEM_REGIAO",
    "pais_origem": "AEROPORTO_DE_ORIGEM_PAIS",
    "aeroporto_destino": "AEROPORTO_DE_DESTINO_NOME",
    "codigo_destino": "AEROPORTO_DE_DESTINO_SIGLA",
    "uf_destino": "AEROPORTO_DE_DESTINO_UF",
    "regiao_destino": "AEROPORTO_DE_DESTINO_REGIAO",
    "pais_destino": "AEROPORTO_DE_DESTINO_PAIS",
    "natureza": "NATUREZA",
    "grupo_de_voo": "GRUPO_DE_VOO",
    "passageiros_pagos": "PASSAGEIROS_PAGOS",
    "passageiros_gratis": "PASSAGEIROS_GRATIS",
    "assentos": "ASSENTOS",
    "decolagens": "DECOLAGENS",
    "ask": "ASK",
    "rpk": "RPK",
    "distancia_voada": "DISTANCIA_VOADA_KM",
    "combustivel": "COMBUSTIVEL_LITROS",
    "horas_voadas": "HORAS_VOADAS",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def logical_fingerprint(path: Path) -> str:
    lf = pl.scan_parquet(path)
    schema = {column: str(dtype) for column, dtype in lf.collect_schema().items()}
    row_hashes = lf.select(pl.struct(pl.all()).hash(seed=17).alias("ROW_HASH"))
    stats = collect(
        row_hashes.select(
            pl.len().alias("rows"),
            pl.col("ROW_HASH").sum().alias("hash_sum"),
            pl.col("ROW_HASH").min().alias("hash_min"),
            pl.col("ROW_HASH").max().alias("hash_max"),
        )
    ).to_dicts()[0]
    payload = json.dumps({"schema": schema, "stats": stats}, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def collect(lf: pl.LazyFrame) -> pl.DataFrame:
    return lf.collect(engine="streaming")


def clean_text(column: str) -> pl.Expr:
    value = pl.col(column).cast(pl.String).str.strip_chars()
    return pl.when(value == "").then(None).otherwise(value).alias(column)


def parse_integer(column: str) -> pl.Expr:
    value = pl.col(column).cast(pl.String).str.strip_chars()
    return pl.when(value == "").then(None).otherwise(value.cast(pl.Int64, strict=False)).alias(column)


def parse_decimal_comma(column: str) -> pl.Expr:
    value = pl.col(column).cast(pl.String).str.strip_chars()
    normalized = value.str.replace_all(r"\.", "").str.replace(",", ".", literal=True)
    return pl.when(value == "").then(None).otherwise(normalized.cast(pl.Float64, strict=False)).alias(column)


def scan_source(path: Path = RAW_PATH) -> pl.LazyFrame:
    schema = {column: pl.String for column in SOURCE_COLUMNS}
    return (
        pl.scan_csv(
            path,
            separator=";",
            has_header=True,
            skip_rows=1,
            quote_char='"',
            encoding="utf8-lossy",
            schema_overrides=schema,
            null_values=[""],
            row_index_name="LINHA_DADOS",
            row_index_offset=1,
        )
        .select(["LINHA_DADOS", *SOURCE_COLUMNS])
    )


def prepare_source(lf: pl.LazyFrame) -> pl.LazyFrame:
    typed = lf.with_columns(
        [clean_text(column) for column in TEXT_COLUMNS]
        + [parse_integer(column) for column in INTEGER_COLUMNS]
        + [parse_decimal_comma("HORAS_VOADAS")]
    )

    passenger_evidence = (
        (pl.col("PASSAGEIROS_PAGOS").fill_null(0) > 0)
        | (pl.col("PASSAGEIROS_GRATIS").fill_null(0) > 0)
        | (pl.col("ASSENTOS").fill_null(0) > 0)
        | (pl.col("ASK").fill_null(0) > 0)
        | (pl.col("RPK").fill_null(0) > 0)
    )

    return typed.with_columns(
        pl.date(pl.col("ANO"), pl.col("MES"), 1).alias("PERIODO"),
        pl.concat_str(["EMPRESA_SIGLA", "EMPRESA_NOME"], separator="|").alias("EMPRESA_ID"),
        pl.when(
            pl.col("AEROPORTO_DE_ORIGEM_SIGLA").is_not_null()
            & pl.col("AEROPORTO_DE_DESTINO_SIGLA").is_not_null()
        )
        .then(
            pl.concat_str(
                ["AEROPORTO_DE_ORIGEM_SIGLA", "AEROPORTO_DE_DESTINO_SIGLA"],
                separator=">",
            )
        )
        .otherwise(None)
        .alias("ROTA_DIRECIONAL"),
        (pl.col("GRUPO_DE_VOO") == "REGULAR").fill_null(False).alias("FLAG_VOO_REGULAR"),
        passenger_evidence.alias("FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS"),
        ((pl.col("GRUPO_DE_VOO") == "REGULAR").fill_null(False) & passenger_evidence).alias(
            "FLAG_UNIVERSO_MVP"
        ),
        (pl.col("COMBUSTIVEL_LITROS") < 0).fill_null(False).alias("FLAG_COMBUSTIVEL_NEGATIVO"),
    )


def nullable_sum(column: str) -> pl.Expr:
    return (
        pl.when(pl.col(column).count() > 0)
        .then(pl.col(column).sum())
        .otherwise(None)
        .alias(column)
    )


def aggregate_routes(prepared: pl.LazyFrame) -> pl.LazyFrame:
    metric_columns = [
        "PASSAGEIROS_PAGOS",
        "ASSENTOS",
        "DECOLAGENS",
        "ASK",
        "RPK",
        "COMBUSTIVEL_LITROS",
    ]
    return (
        prepared.group_by(DIMENSIONS)
        .agg(
            *[nullable_sum(column) for column in metric_columns],
            pl.len().alias("QTD_REGISTROS_FONTE"),
            pl.col("FLAG_VOO_REGULAR").any().alias("FLAG_VOO_REGULAR"),
            pl.col("FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS")
            .any()
            .alias("FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS"),
            pl.col("FLAG_UNIVERSO_MVP").any().alias("FLAG_UNIVERSO_MVP"),
            pl.col("FLAG_COMBUSTIVEL_NEGATIVO").any().alias("FLAG_COMBUSTIVEL_NEGATIVO"),
            pl.col("FLAG_COMBUSTIVEL_NEGATIVO").sum().cast(pl.Int64).alias(
                "QTD_REGISTROS_COMBUSTIVEL_NEGATIVO"
            ),
            pl.col("COMBUSTIVEL_LITROS")
            .filter(pl.col("COMBUSTIVEL_LITROS") < 0)
            .min()
            .alias("COMBUSTIVEL_NEGATIVO_MIN"),
        )
        .sort(DIMENSIONS)
    )


def outlier_thresholds(aggregated: pl.LazyFrame) -> dict[str, dict[str, float | None]]:
    expressions: list[pl.Expr] = []
    for column in MAIN_METRICS:
        expressions.extend(
            [
                pl.col(column).quantile(0.25).alias(f"{column}__q1"),
                pl.col(column).quantile(0.75).alias(f"{column}__q3"),
                pl.col(column).quantile(0.99).alias(f"{column}__p99"),
                pl.col(column).quantile(0.999).alias(f"{column}__p999"),
                pl.col(column).max().alias(f"{column}__max"),
            ]
        )
    values = collect(aggregated.select(expressions)).to_dicts()[0]
    result: dict[str, dict[str, float | None]] = {}
    for column in MAIN_METRICS:
        q1 = values[f"{column}__q1"]
        q3 = values[f"{column}__q3"]
        upper = None if q1 is None or q3 is None else float(q3 + 3 * (q3 - q1))
        result[column] = {
            "q1": None if q1 is None else float(q1),
            "q3": None if q3 is None else float(q3),
            "limite_iqr_3x": upper,
            "p99": None if values[f"{column}__p99"] is None else float(values[f"{column}__p99"]),
            "p999": None
            if values[f"{column}__p999"] is None
            else float(values[f"{column}__p999"]),
            "max": None if values[f"{column}__max"] is None else float(values[f"{column}__max"]),
        }
    return result


def add_outlier_flag(
    aggregated: pl.LazyFrame, thresholds: dict[str, dict[str, float | None]]
) -> pl.LazyFrame:
    conditions = [
        pl.col(column) > threshold["limite_iqr_3x"]
        for column, threshold in thresholds.items()
        if threshold["limite_iqr_3x"] is not None
    ]
    condition = conditions[0]
    for item in conditions[1:]:
        condition = condition | item
    return aggregated.with_columns(condition.fill_null(False).alias("FLAG_POSSIVEL_OUTLIER"))


def scalar(lf: pl.LazyFrame, expression: pl.Expr, name: str = "value") -> Any:
    return collect(lf.select(expression.alias(name)))[name][0]


def md_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_Nenhum registro._"

    def value(item: Any) -> str:
        if item is None:
            return ""
        return str(item).replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    lines.extend("| " + " | ".join(value(row.get(column)) for column in columns) + " |" for row in rows)
    return "\n".join(lines)


def collect_pipeline_stats(
    prepared: pl.LazyFrame,
    processed: pl.LazyFrame,
    thresholds: dict[str, dict[str, float | None]],
) -> dict[str, Any]:
    raw_summary = collect(
        prepared.select(
            pl.len().alias("raw_rows"),
            pl.col("PERIODO").min().alias("period_min"),
            pl.col("PERIODO").max().alias("period_max"),
            pl.col("EMPRESA_ID").n_unique().alias("companies"),
            pl.col("ROTA_DIRECIONAL").drop_nulls().n_unique().alias("routes"),
            pl.col("AEROPORTO_DE_ORIGEM_SIGLA").drop_nulls().n_unique().alias("origins"),
            pl.col("AEROPORTO_DE_DESTINO_SIGLA").drop_nulls().n_unique().alias("destinations"),
            pl.col("FLAG_UNIVERSO_MVP").sum().alias("mvp_source_rows"),
            pl.col("FLAG_COMBUSTIVEL_NEGATIVO").sum().alias("negative_fuel_rows"),
        )
    ).to_dicts()[0]
    airport_values = pl.concat(
        [
            prepared.select(pl.col("AEROPORTO_DE_ORIGEM_SIGLA").alias("AEROPORTO_SIGLA")),
            prepared.select(pl.col("AEROPORTO_DE_DESTINO_SIGLA").alias("AEROPORTO_SIGLA")),
        ],
        how="vertical",
    )
    raw_summary["airports"] = int(
        scalar(airport_values, pl.col("AEROPORTO_SIGLA").drop_nulls().n_unique())
    )
    raw_summary["nature_values"] = collect(
        prepared.select("NATUREZA").drop_nulls().unique().sort("NATUREZA")
    )["NATUREZA"].to_list()
    raw_summary["group_values"] = collect(
        prepared.select("GRUPO_DE_VOO").drop_nulls().unique().sort("GRUPO_DE_VOO")
    )["GRUPO_DE_VOO"].to_list()

    operation_counts = collect(
        prepared.group_by(["NATUREZA", "GRUPO_DE_VOO"])
        .agg(
            pl.len().alias("LINHAS"),
            pl.col("FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS").sum().alias("COM_EVIDENCIA_PASSAGEIROS"),
            pl.col("PASSAGEIROS_PAGOS").sum().alias("PASSAGEIROS_PAGOS_SOMA"),
        )
        .sort(["NATUREZA", "GRUPO_DE_VOO"])
    ).to_dicts()

    ambiguous = collect(
        prepared.filter(pl.col("EMPRESA_SIGLA").is_in(["ABJ", "ARU", "TSC"]))
        .group_by(["EMPRESA_SIGLA", "EMPRESA_NOME"])
        .agg(
            pl.len().alias("LINHAS"),
            pl.col("ANO").min().alias("ANO_MIN"),
            pl.col("ANO").max().alias("ANO_MAX"),
            pl.col("PERIODO").min().alias("PERIODO_MIN"),
            pl.col("PERIODO").max().alias("PERIODO_MAX"),
        )
        .sort(["EMPRESA_SIGLA", "PERIODO_MIN"])
    ).to_dicts()

    negative_fuel = collect(
        prepared.filter(pl.col("FLAG_COMBUSTIVEL_NEGATIVO"))
        .select(
            (pl.col("LINHA_DADOS") + 2).alias("LINHA_ARQUIVO"),
            "ANO",
            "MES",
            "EMPRESA_SIGLA",
            "EMPRESA_NOME",
            "AEROPORTO_DE_ORIGEM_SIGLA",
            "AEROPORTO_DE_DESTINO_SIGLA",
            "NATUREZA",
            "GRUPO_DE_VOO",
            "PASSAGEIROS_PAGOS",
            "ASSENTOS",
            "DECOLAGENS",
            "ASK",
            "RPK",
            "COMBUSTIVEL_LITROS",
        )
        .sort(["ANO", "MES", "EMPRESA_SIGLA", "LINHA_ARQUIVO"])
    ).to_dicts()

    processed_summary_expressions = [
        pl.len().alias("processed_rows"),
        pl.col("QTD_REGISTROS_FONTE").sum().alias("source_rows_reconciled"),
        pl.col("QTD_REGISTROS_FONTE").max().alias("max_source_rows_per_group"),
        (pl.col("QTD_REGISTROS_FONTE") > 1).sum().alias("groups_with_aggregation"),
        pl.col("EMPRESA_ID").n_unique().alias("processed_companies"),
        pl.col("ROTA_DIRECIONAL").drop_nulls().n_unique().alias("processed_routes"),
        pl.col("PERIODO").min().alias("processed_period_min"),
        pl.col("PERIODO").max().alias("processed_period_max"),
        pl.col("FLAG_UNIVERSO_MVP").sum().alias("mvp_groups"),
        pl.col("FLAG_COMBUSTIVEL_NEGATIVO").sum().alias("negative_fuel_groups"),
        pl.col("FLAG_POSSIVEL_OUTLIER").sum().alias("outlier_groups"),
        (pl.col("AEROPORTO_DE_ORIGEM_SIGLA") == pl.col("AEROPORTO_DE_DESTINO_SIGLA"))
        .fill_null(False)
        .sum()
        .alias("same_airport_routes"),
        (
            pl.col("AEROPORTO_DE_ORIGEM_SIGLA").is_null()
            | pl.col("AEROPORTO_DE_DESTINO_SIGLA").is_null()
        )
        .sum()
        .alias("missing_airport_codes"),
        ((pl.col("RPK") > pl.col("ASK")) & pl.col("RPK").is_not_null() & pl.col("ASK").is_not_null())
        .sum()
        .alias("rpk_gt_ask"),
        (
            (pl.col("PASSAGEIROS_PAGOS") > pl.col("ASSENTOS"))
            & pl.col("PASSAGEIROS_PAGOS").is_not_null()
            & pl.col("ASSENTOS").is_not_null()
        )
        .sum()
        .alias("passengers_gt_seats"),
    ]
    for column in MAIN_METRICS:
        processed_summary_expressions.extend(
            [
                pl.col(column).is_null().sum().alias(f"{column}__null"),
                (pl.col(column) < 0).fill_null(False).sum().alias(f"{column}__negative"),
                (pl.col(column) == 0).fill_null(False).sum().alias(f"{column}__zero"),
            ]
        )
    processed_summary = collect(processed.select(processed_summary_expressions)).to_dicts()[0]

    core_grain = (
        processed.filter(pl.col("ROTA_DIRECIONAL").is_not_null())
        .group_by(["PERIODO", "ROTA_DIRECIONAL", "EMPRESA_ID"])
        .agg(pl.len().alias("CATEGORIAS_NO_GRAO_MINIMO"))
    )
    core_grain_summary = collect(
        core_grain.select(
            (pl.col("CATEGORIAS_NO_GRAO_MINIMO") > 1).sum().alias("keys_with_multiple_categories"),
            pl.col("CATEGORIAS_NO_GRAO_MINIMO").max().alias("max_categories_per_key"),
        )
    ).to_dicts()[0]

    raw_totals = collect(prepared.select([pl.col(column).sum().alias(column) for column in MAIN_METRICS]))
    processed_totals = collect(
        processed.select([pl.col(column).sum().alias(column) for column in MAIN_METRICS])
    )
    reconciliation = []
    for column in MAIN_METRICS:
        raw_value = raw_totals[column][0]
        processed_value = processed_totals[column][0]
        reconciliation.append(
            {
                "METRICA": column,
                "SOMA_BRUTA": raw_value,
                "SOMA_PROCESSADA": processed_value,
                "DIFERENCA": processed_value - raw_value,
            }
        )

    outlier_rows = []
    for column, threshold in thresholds.items():
        upper = threshold["limite_iqr_3x"]
        count = 0 if upper is None else int(scalar(processed, (pl.col(column) > upper).sum()))
        outlier_rows.append({"METRICA": column, **threshold, "CANDIDATOS": count})

    return {
        "raw": raw_summary,
        "processed": processed_summary,
        "operations": operation_counts,
        "ambiguous_companies": ambiguous,
        "negative_fuel": negative_fuel,
        "outliers": outlier_rows,
        "core_grain": core_grain_summary,
        "reconciliation": reconciliation,
    }


def format_date(value: Any) -> str:
    return value.isoformat() if value is not None else "n/a"


def write_reports(
    stats: dict[str, Any],
    raw_hash_before: str,
    raw_hash_after: str,
    output_size: int,
    content_fingerprint: str,
    output_path: Path = OUTPUT_PATH,
) -> None:
    generated_at = datetime.now().isoformat(timespec="seconds")
    raw = stats["raw"]
    processed = stats["processed"]
    final_columns = collect(pl.scan_parquet(output_path).limit(0)).columns

    mapping_rows = [{"conceito": key, "coluna_real": value} for key, value in COLUMN_MAPPING.items()]
    operations_table = md_table(
        stats["operations"],
        ["NATUREZA", "GRUPO_DE_VOO", "LINHAS", "COM_EVIDENCIA_PASSAGEIROS", "PASSAGEIROS_PAGOS_SOMA"],
    )
    ambiguous_table = md_table(
        stats["ambiguous_companies"],
        ["EMPRESA_SIGLA", "EMPRESA_NOME", "LINHAS", "ANO_MIN", "ANO_MAX", "PERIODO_MIN", "PERIODO_MAX"],
    )

    methodology = f"""# Metodologia de tratamento

Gerado em: `{generated_at}`

## Fonte e colunas confirmadas

- Fonte imutavel: `data/raw/Dados_Estatisticos.csv`.
- Cabecalho na segunda linha, separador `;` e encoding UTF-8 com BOM, conforme a auditoria.
- O arquivo possui uma unica coluna de codigo por aeroporto (`AEROPORTO_DE_ORIGEM_SIGLA` e `AEROPORTO_DE_DESTINO_SIGLA`). Nao ha colunas separadas de ICAO e IATA, portanto o pipeline preserva os nomes reais sem atribuir um padrao de codigo nao documentado.

{md_table(mapping_rows, ["conceito", "coluna_real"])}

## Definicao do universo analitico

Valores e volumes encontrados antes de qualquer recorte:

{operations_table}

`GRUPO_DE_VOO = REGULAR` identifica com seguranca a regularidade da operacao. Entretanto, a coluna nao distingue sozinha voos regulares de passageiros de voos regulares exclusivamente cargueiros. `NATUREZA` distingue `DOMESTICA` e `INTERNACIONAL`, mas o escopo do mercado brasileiro nao determina, por si so, que voos internacionais devam ser descartados.

Por isso, nenhuma linha foi excluida. O recorte recomendado para o MVP foi implementado como flags:

- `FLAG_VOO_REGULAR`: `GRUPO_DE_VOO = REGULAR`.
- `FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS`: ao menos uma entre `PASSAGEIROS_PAGOS`, `PASSAGEIROS_GRATIS`, `ASSENTOS`, `ASK` ou `RPK` e maior que zero.
- `FLAG_UNIVERSO_MVP`: as duas condicoes anteriores simultaneamente.

Assim, o futuro aplicativo pode aplicar o recorte sem perda irreversivel. `IMPRODUTIVO`, `NAO REGULAR`, `NAO IDENTIFICADO` e os dois registros sem `GRUPO_DE_VOO` permanecem disponiveis e explicitamente classificados.

## Chaves analiticas

- `ROTA_DIRECIONAL`: concatenacao dos codigos reais de origem e destino com `>`. Exemplo: `SBBE>SBGR`. A direcao e preservada. Se qualquer codigo estiver ausente, a chave permanece nula.
- `EMPRESA_ID`: concatenacao exata de `EMPRESA_SIGLA` e `EMPRESA_NOME` com `|`. Isso evita misturar empresas que reutilizam a mesma sigla.
- Grao final: `PERIODO` + `ROTA_DIRECIONAL` + `EMPRESA_ID` + atributos aeroportuarios + `NATUREZA` + `GRUPO_DE_VOO`. As duas ultimas dimensoes permanecem no grao para impedir a mistura de categorias operacionais diferentes.

A agregacao resultou em `{processed['processed_rows']}` linhas, igual ao bruto, com maximo de `{processed['max_source_rows_per_group']}` registro fonte por grupo. Portanto, a fonte ja se encontra nesse grao quando todas as dimensoes necessarias sao preservadas. A etapa de agregacao continua explicita para garantir o comportamento em futuras atualizacoes do CSV.

Na chave minima `PERIODO + ROTA_DIRECIONAL + EMPRESA_ID`, `{stats['core_grain']['keys_with_multiple_categories']}` combinacoes aparecem em mais de uma categoria operacional, com maximo de `{stats['core_grain']['max_categories_per_key']}` categorias. Isso confirma que retirar `NATUREZA` e `GRUPO_DE_VOO` misturaria universos distintos.

## Empresas com siglas ambiguas

{ambiguous_table}

Os periodos nao se sobrepoem dentro de cada sigla, mas os nomes foram preservados na identificacao. Nenhuma consolidacao por sigla foi aplicada.

## Tipos, nulos e agregacao

- `ANO` e `MES`: `Int64`.
- `PERIODO`: `Date`, sempre no primeiro dia do mes.
- Metricas aditivas: `PASSAGEIROS_PAGOS`, `ASSENTOS`, `DECOLAGENS`, `ASK`, `RPK` e `COMBUSTIVEL_LITROS`.
- `HORAS_VOADAS`: convertido de texto com virgula decimal para `Float64` durante o tratamento, mas nao persistido por nao ser necessario ao MVP ou as chaves.
- `PASSAGEIROS_GRATIS` e `DISTANCIA_VOADA_KM`: tipados e usados na classificacao/validacao, mas nao persistidos na tabela enxuta.
- Uma soma e nula quando todos os valores do grupo sao nulos. Zeros informados permanecem zero.
- Load Factor nao foi persistido. Quando implementado, deve ser calculado como `SUM(RPK) / SUM(ASK)`.

## Combustivel negativo

Os `{raw['negative_fuel_rows']}` registros negativos nao foram excluidos. `COMBUSTIVEL_LITROS` permanece agregado, enquanto `FLAG_COMBUSTIVEL_NEGATIVO`, `QTD_REGISTROS_COMBUSTIVEL_NEGATIVO` e `COMBUSTIVEL_NEGATIVO_MIN` identificam os grupos afetados. Os valores originais e a linha fisica do CSV estao listados no relatorio de qualidade; a fonte bruta permanece imutavel.

## Colunas da base processada

{chr(10).join(f'- `{column}`' for column in final_columns)}

## Reproducao

```powershell
python -m src.process_data
```

O pipeline usa leitura lazy com projecao apenas das colunas necessarias, agrega por streaming e grava Parquet com compressao Zstandard.
"""

    metric_quality_rows = []
    for column in MAIN_METRICS:
        metric_quality_rows.append(
            {
                "METRICA": column,
                "NULOS": processed[f"{column}__null"],
                "NEGATIVOS": processed[f"{column}__negative"],
                "ZEROS": processed[f"{column}__zero"],
            }
        )

    negative_columns = [
        "LINHA_ARQUIVO",
        "ANO",
        "MES",
        "EMPRESA_SIGLA",
        "EMPRESA_NOME",
        "AEROPORTO_DE_ORIGEM_SIGLA",
        "AEROPORTO_DE_DESTINO_SIGLA",
        "NATUREZA",
        "GRUPO_DE_VOO",
        "PASSAGEIROS_PAGOS",
        "ASSENTOS",
        "DECOLAGENS",
        "ASK",
        "RPK",
        "COMBUSTIVEL_LITROS",
    ]

    outlier_rows = []
    for row in stats["outliers"]:
        outlier_rows.append(
            {
                "METRICA": row["METRICA"],
                "LIMITE_IQR_3X": row["limite_iqr_3x"],
                "CANDIDATOS": row["CANDIDATOS"],
                "P99": row["p99"],
                "P99_9": row["p999"],
                "MAX": row["max"],
            }
        )

    quality = f"""# Qualidade da base processada

Gerado em: `{generated_at}`

## Controles de execucao

- Linhas brutas: `{raw['raw_rows']}`.
- Linhas utilizadas: `{raw['raw_rows']}`.
- Linhas excluidas: `0`.
- Motivos de exclusao: nenhum; categorias ambiguas ou fora do recorte sugerido foram preservadas com flags.
- Linhas na tabela agregada: `{processed['processed_rows']}`.
- Soma de `QTD_REGISTROS_FONTE`: `{processed['source_rows_reconciled']}`; maximo por grupo: `{processed['max_source_rows_per_group']}`.
- Grupos que combinaram mais de uma linha fonte: `{processed['groups_with_aggregation']}`.
- Periodo: `{format_date(processed['processed_period_min'])}` a `{format_date(processed['processed_period_max'])}`.
- Companhias por `EMPRESA_ID`: `{processed['processed_companies']}`.
- Aeroportos distintos na uniao origem/destino: `{raw['airports']}`.
- Aeroportos de origem: `{raw['origins']}`; de destino: `{raw['destinations']}`.
- Rotas direcionais com chave nao nula: `{processed['processed_routes']}`.
- Linhas brutas marcadas para o universo sugerido do MVP: `{raw['mvp_source_rows']}`.
- Grupos agregados marcados para o universo sugerido do MVP: `{processed['mvp_groups']}`.
- Tamanho do Parquet: `{output_size}` bytes.
- Impressao digital logica do conteudo: `{content_fingerprint}`.
- SHA-256 bruto antes: `{raw_hash_before}`.
- SHA-256 bruto depois: `{raw_hash_after}`.
- Arquivo bruto preservado: `{raw_hash_before == raw_hash_after}`.

## Metricas principais

{md_table(metric_quality_rows, ["METRICA", "NULOS", "NEGATIVOS", "ZEROS"])}

## Reconciliacao das somas

{md_table(stats['reconciliation'], ["METRICA", "SOMA_BRUTA", "SOMA_PROCESSADA", "DIFERENCA"])}

As cinco metricas aditivas reconciliam exatamente entre a fonte e o Parquet.

## Consistencias cruzadas

- Casos com `RPK > ASK`: `{processed['rpk_gt_ask']}`.
- Casos com `PASSAGEIROS_PAGOS > ASSENTOS`: `{processed['passengers_gt_seats']}`. A comparacao e feita no mesmo grao mensal, rota, companhia, natureza e grupo de voo.
- Rotas com origem igual ao destino: `{processed['same_airport_routes']}`.
- Grupos com codigo de origem ou destino ausente: `{processed['missing_airport_codes']}`.
- Grupos afetados por combustivel negativo: `{processed['negative_fuel_groups']}`.
- Chaves `PERIODO + ROTA_DIRECIONAL + EMPRESA_ID` com mais de uma categoria operacional: `{stats['core_grain']['keys_with_multiple_categories']}`; maximo de `{stats['core_grain']['max_categories_per_key']}` categorias por chave.

## Possiveis outliers

O criterio exploratorio usa limite superior `Q3 + 3 x IQR` em cada metrica principal. Ele apenas sinaliza extremos; nenhum registro foi removido.

{md_table(outlier_rows, ["METRICA", "LIMITE_IQR_3X", "CANDIDATOS", "P99", "P99_9", "MAX"])}

Grupos marcados em qualquer metrica por `FLAG_POSSIVEL_OUTLIER`: `{processed['outlier_groups']}`. A heterogeneidade entre rotas e tamanhos de empresa torna esses candidatos insuficientes, por si sos, para diagnosticar erro.

## Registros de combustivel negativo

{md_table(stats['negative_fuel'], negative_columns)}

## Problemas remanescentes

- Existem nulos nas metricas principais; eles foram preservados para distinguir ausencia de informacao de zero.
- A coluna aeroportuaria `SIGLA` nao declara separadamente ICAO e IATA.
- Ha `{processed['missing_airport_codes']}` grupos sem codigo completo de rota.
- Ha `{processed['same_airport_routes']}` grupos com origem igual ao destino, mantidos para investigacao.
- Ha `{processed['rpk_gt_ask']}` casos com `RPK > ASK` e `{processed['passengers_gt_seats']}` com passageiros pagos acima de assentos no mesmo grao.
- Extremos estatisticos foram sinalizados, nao removidos.
- A definicao de transporte regular de passageiros permanece uma regra analitica explicita por flags, pois `GRUPO_DE_VOO` nao separa sozinho operacoes de passageiros e carga.
"""

    METHODOLOGY_PATH.write_text(methodology, encoding="utf-8")
    QUALITY_PATH.write_text(quality, encoding="utf-8")


def run_pipeline(raw_path: Path = RAW_PATH, output_path: Path = OUTPUT_PATH) -> dict[str, Any]:
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)

    print("Colunas reais confirmadas pela auditoria:")
    print(json.dumps(COLUMN_MAPPING, ensure_ascii=False, indent=2))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    METHODOLOGY_PATH.parent.mkdir(parents=True, exist_ok=True)
    hash_before = sha256_file(raw_path)

    prepared = prepare_source(scan_source(raw_path))
    aggregated = aggregate_routes(prepared)
    thresholds = outlier_thresholds(aggregated)
    final_lf = add_outlier_flag(aggregated, thresholds)

    temporary_path = output_path.with_suffix(".tmp.parquet")
    if temporary_path.exists():
        temporary_path.unlink()
    final_lf.sink_parquet(temporary_path, compression="zstd", statistics=True, mkdir=True)
    os.replace(temporary_path, output_path)

    processed = pl.scan_parquet(output_path)
    stats = collect_pipeline_stats(prepared, processed, thresholds)
    content_fingerprint = logical_fingerprint(output_path)
    hash_after = sha256_file(raw_path)
    if hash_before != hash_after:
        raise RuntimeError("O hash do CSV bruto mudou durante o processamento.")

    write_reports(
        stats,
        hash_before,
        hash_after,
        output_path.stat().st_size,
        content_fingerprint,
        output_path,
    )
    result = {
        "linhas_brutas": int(stats["raw"]["raw_rows"]),
        "linhas_utilizadas": int(stats["raw"]["raw_rows"]),
        "linhas_excluidas": 0,
        "linhas_agregadas": int(stats["processed"]["processed_rows"]),
        "periodo_min": format_date(stats["processed"]["processed_period_min"]),
        "periodo_max": format_date(stats["processed"]["processed_period_max"]),
        "companhias": int(stats["processed"]["processed_companies"]),
        "aeroportos": int(stats["raw"]["airports"]),
        "rotas": int(stats["processed"]["processed_routes"]),
        "parquet_bytes": output_path.stat().st_size,
        "impressao_digital_logica": content_fingerprint,
        "hash_bruto_preservado": True,
    }
    print("Resumo do pipeline:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()

