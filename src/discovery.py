"""Directional market comparisons using the official, unchanged MVP dataset."""
from __future__ import annotations

from datetime import date

import polars as pl

from src.metrics import MAIN_METRICS, QUALITY_FLAGS
from src.process_data import nullable_sum

KEYS = ["ROTA_DIRECIONAL", "AEROPORTO_DE_ORIGEM_SIGLA", "AEROPORTO_DE_DESTINO_SIGLA"]
SORTS = {
    "Mais passageiros": ("PASSAGEIROS_PAGOS", True),
    "Maior crescimento": ("CRESCIMENTO_PCT", True),
    "Maior ocupação": ("LOAD_FACTOR_PCT", True),
    "Maior concentração": ("HHI", True),
    "Menor concentração": ("HHI", False),
}


def discover_markets(data: pl.DataFrame, year: int, final_month: int) -> pl.DataFrame:
    """Compare Jan–month with identical months of the prior year.

    Growth requires every month and no missing passenger values in BOTH windows.
    Missing observations never become zero or evidence that a route is new.
    """
    if not 1 <= final_month <= 12:
        raise ValueError("Mês final deve estar entre 1 e 12.")
    available = data.filter(pl.col("ANO") == year)
    if available.is_empty() or final_month > available["MES"].max():
        raise ValueError("Período solicitado não está disponível na base.")
    flags = [flag for flag in QUALITY_FLAGS if flag in data.columns]
    window = data.lazy().filter(
        pl.col("ANO").is_in([year - 1, year]) & (pl.col("MES") <= final_month)
    )
    current = window.filter(pl.col("ANO") == year)
    totals = current.group_by(KEYS).agg(
        *[nullable_sum(column) for column in MAIN_METRICS],
        pl.col("MES").n_unique().alias("MESES_COM_REGISTRO"),
        pl.col("PASSAGEIROS_PAGOS").null_count().alias("NULOS_PASSAGEIROS"),
        pl.len().alias("REGISTROS"),
        pl.any_horizontal([pl.col(flag).fill_null(False) for flag in flags]).sum().alias("REGISTROS_SINALIZADOS")
        if flags else pl.lit(0).alias("REGISTROS_SINALIZADOS"),
    )
    previous = window.filter(pl.col("ANO") == year - 1).group_by(KEYS).agg(
        nullable_sum("PASSAGEIROS_PAGOS").alias("PASSAGEIROS_ANTERIOR"),
        pl.col("MES").n_unique().alias("MESES_ANTERIOR"),
        pl.col("PASSAGEIROS_PAGOS").null_count().alias("NULOS_ANTERIOR"),
    )
    companies = current.group_by([*KEYS, "EMPRESA_ID"]).agg(nullable_sum("PASSAGEIROS_PAGOS"))
    competition = (
        companies.with_columns(pl.col("PASSAGEIROS_PAGOS").sum().over(KEYS).alias("TOTAL_ROTA"))
        .with_columns(
            pl.when(pl.col("TOTAL_ROTA") > 0)
            .then(pl.col("PASSAGEIROS_PAGOS") / pl.col("TOTAL_ROTA") * 100)
            .otherwise(None).alias("SHARE")
        )
        .group_by(KEYS).agg(
            (pl.col("PASSAGEIROS_PAGOS") > 0).sum().alias("COMPANHIAS_COM_PASSAGEIROS"),
            nullable_sum("SHARE",).alias("SOMA_SHARES"),
            pl.col("SHARE").pow(2).sum().alias("HHI"),
            pl.col("SHARE").max().alias("MAIOR_SHARE_PCT"),
        )
        .with_columns(pl.when(pl.col("SOMA_SHARES") > 0).then(pl.col("HHI")).otherwise(None).alias("HHI"))
        .drop("SOMA_SHARES")
    )
    return (
        totals.join(previous, on=KEYS, how="left")
        .join(competition, on=KEYS, how="left")
        .with_columns(
            pl.when(pl.col("ASK") > 0).then(pl.col("RPK") / pl.col("ASK") * 100).otherwise(None).alias("LOAD_FACTOR_PCT"),
            pl.when(pl.col("PASSAGEIROS_ANTERIOR").is_null()).then(pl.lit("Sem base anterior"))
            .when((pl.col("MESES_COM_REGISTRO") != final_month) | (pl.col("MESES_ANTERIOR") != final_month))
            .then(pl.lit("Meses sem registro"))
            .when((pl.col("NULOS_PASSAGEIROS") > 0) | (pl.col("NULOS_ANTERIOR") > 0))
            .then(pl.lit("Passageiros ausentes"))
            .when(pl.col("PASSAGEIROS_ANTERIOR") <= 0).then(pl.lit("Base anterior zerada"))
            .otherwise(pl.lit("Comparável")).alias("COMPARABILIDADE"),
            pl.lit(date(year, 1, 1)).alias("INICIO"),
            pl.lit(date(year, final_month, 1)).alias("FIM"),
            pl.lit(date(year - 1, 1, 1)).alias("INICIO_ANTERIOR"),
            pl.lit(date(year - 1, final_month, 1)).alias("FIM_ANTERIOR"),
        )
        .with_columns(
            pl.when(pl.col("COMPARABILIDADE") == "Comparável")
            .then((pl.col("PASSAGEIROS_PAGOS") / pl.col("PASSAGEIROS_ANTERIOR") - 1) * 100)
            .otherwise(None).alias("CRESCIMENTO_PCT")
        ).sort(["PASSAGEIROS_PAGOS", "ROTA_DIRECIONAL"], descending=[True, False], nulls_last=True)
        .collect(engine="streaming")
    )


def label_markets(markets: pl.DataFrame, airports: pl.DataFrame) -> pl.DataFrame:
    result = markets
    for side, source in [("ORIGEM", KEYS[1]), ("DESTINO", KEYS[2])]:
        dimension = airports.select(
            pl.col("ICAO").alias(source),
            pl.coalesce("IATA", "ICAO").alias(f"CODIGO_{side}"),
            pl.coalesce("MUNICIPIO", "NOME_AEROPORTO", "ICAO").str.to_titlecase().alias(f"LOCAL_{side}"),
            pl.col("UF").alias(f"UF_{side}"),
        )
        result = result.join(dimension, on=source, how="left")
    return result.with_columns(
        pl.concat_str("CODIGO_ORIGEM", pl.lit(" → "), "CODIGO_DESTINO").alias("ROTA"),
    )


def filter_markets(
    markets: pl.DataFrame, *, origin_uf: str | None = None, destination_uf: str | None = None,
    min_passengers: int = 0, max_companies: int | None = None, comparable_only: bool = False,
    sort: str = "Mais passageiros",
) -> pl.DataFrame:
    result = markets.filter(pl.col("PASSAGEIROS_PAGOS").fill_null(0) >= min_passengers)
    if origin_uf:
        result = result.filter(pl.col("UF_ORIGEM") == origin_uf)
    if destination_uf:
        result = result.filter(pl.col("UF_DESTINO") == destination_uf)
    if max_companies is not None:
        result = result.filter(pl.col("COMPANHIAS_COM_PASSAGEIROS") <= max_companies)
    if comparable_only:
        result = result.filter(pl.col("COMPARABILIDADE") == "Comparável")
    column, descending = SORTS[sort]
    return result.sort([column, "ROTA_DIRECIONAL"], descending=[descending, False], nulls_last=True)


def csv_bytes(frame: pl.DataFrame) -> bytes:
    """Portuguese-friendly CSV; protect text fields from spreadsheet formulas."""
    strings = [name for name, dtype in frame.schema.items() if dtype == pl.String]
    safe = frame.with_columns([
        pl.when(pl.col(name).str.contains(r"^[\s]*[=+@\-]"))
        .then(pl.concat_str(pl.lit("'"), pl.col(name))).otherwise(pl.col(name)).alias(name)
        for name in strings
    ])
    return safe.write_csv(separator=";", decimal_comma=True).encode("utf-8-sig")

