from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Iterable

import polars as pl

from src.process_data import MAIN_METRICS, nullable_sum
from src.universe import year_coverage


ROOT = Path(__file__).resolve().parents[1]
MVP_PATH = ROOT / "data" / "processed" / "avscope_mvp_domestic.parquet"
QUALITY_FLAGS = [
    "FLAG_RPK_MAIOR_ASK",
    "FLAG_PASSAGEIROS_MAIOR_ASSENTOS",
    "FLAG_ASK_ZERO_RPK_POSITIVO",
    "FLAG_DECOLAGENS_ZERO_PASSAGEIROS_POSITIVOS",
    "FLAG_ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS",
]
Frame = pl.DataFrame | pl.LazyFrame


def load_mvp(path: Path | str = MVP_PATH) -> pl.LazyFrame:
    """Lazily scan the official product dataset; the raw CSV is never read here."""
    return pl.scan_parquet(path)


def _lazy(data: Frame | None) -> pl.LazyFrame:
    if data is None:
        return load_mvp()
    return data.lazy() if isinstance(data, pl.DataFrame) else data


def _date(value: date | datetime | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value[:10])


def filter_data(
    data: Frame | None = None,
    *,
    origin_icao: str | None = None,
    destination_icao: str | None = None,
    period: date | datetime | str | None = None,
    start: date | datetime | str | None = None,
    end: date | datetime | str | None = None,
    company_id: str | None = None,
) -> pl.LazyFrame:
    lf = _lazy(data)
    conditions: list[pl.Expr] = []
    if origin_icao is not None:
        conditions.append(pl.col("AEROPORTO_DE_ORIGEM_SIGLA") == origin_icao)
    if destination_icao is not None:
        conditions.append(pl.col("AEROPORTO_DE_DESTINO_SIGLA") == destination_icao)
    if company_id is not None:
        conditions.append(pl.col("EMPRESA_ID") == company_id)
    period_date = _date(period)
    start_date, end_date = _date(start), _date(end)
    if period_date is not None:
        conditions.append(pl.col("PERIODO") == period_date)
    if start_date is not None:
        conditions.append(pl.col("PERIODO") >= start_date)
    if end_date is not None:
        conditions.append(pl.col("PERIODO") <= end_date)
    for condition in conditions:
        lf = lf.filter(condition)
    return lf


def safe_divide(numerator: int | float | None, denominator: int | float | None, multiplier: float = 1.0) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return float(numerator) / float(denominator) * multiplier


def calculate_load_factor(rpk: int | float | None, ask: int | float | None) -> float | None:
    return safe_divide(rpk, ask, 100.0)


def calculate_passengers_per_departure(
    passengers: int | float | None, departures: int | float | None
) -> float | None:
    return safe_divide(passengers, departures)


def growth_percent(current: int | float | None, previous: int | float | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return (float(current) - float(previous)) / float(previous) * 100.0


def basic_metrics(data: Frame | None = None, **filters: object) -> dict[str, int | float | None]:
    lf = filter_data(data, **filters)
    row = lf.select(
        *[nullable_sum(column) for column in MAIN_METRICS],
        pl.col("EMPRESA_ID").n_unique().alias("NUMERO_COMPANHIAS"),
        pl.col("ROTA_DIRECIONAL").n_unique().alias("NUMERO_ROTAS"),
        pl.len().alias("REGISTROS"),
    ).collect(engine="streaming").to_dicts()[0]
    row["LOAD_FACTOR_PCT"] = calculate_load_factor(row["RPK"], row["ASK"])
    row["PASSAGEIROS_POR_DECOLAGEM"] = calculate_passengers_per_departure(
        row["PASSAGEIROS_PAGOS"], row["DECOLAGENS"]
    )
    return row


def metric_total(metric: str, data: Frame | None = None, **filters: object) -> int | None:
    if metric not in MAIN_METRICS:
        raise ValueError(f"Metrica nao suportada: {metric}")
    return basic_metrics(data, **filters)[metric]


def total_passengers(data: Frame | None = None, **filters: object) -> int | None:
    return metric_total("PASSAGEIROS_PAGOS", data, **filters)


def total_seats(data: Frame | None = None, **filters: object) -> int | None:
    return metric_total("ASSENTOS", data, **filters)


def total_departures(data: Frame | None = None, **filters: object) -> int | None:
    return metric_total("DECOLAGENS", data, **filters)


def total_ask(data: Frame | None = None, **filters: object) -> int | None:
    return metric_total("ASK", data, **filters)


def total_rpk(data: Frame | None = None, **filters: object) -> int | None:
    return metric_total("RPK", data, **filters)


def number_of_companies(data: Frame | None = None, **filters: object) -> int:
    return int(basic_metrics(data, **filters)["NUMERO_COMPANHIAS"] or 0)


def number_of_routes(data: Frame | None = None, **filters: object) -> int:
    return int(basic_metrics(data, **filters)["NUMERO_ROTAS"] or 0)


def market_share_by_company(data: Frame | None = None, **filters: object) -> pl.DataFrame:
    grouped = (
        filter_data(data, **filters)
        .group_by("EMPRESA_ID")
        .agg(
            pl.col("EMPRESA_SIGLA").drop_nulls().last().alias("EMPRESA_SIGLA"),
            pl.col("EMPRESA_NOME").drop_nulls().last().alias("EMPRESA_NOME"),
            nullable_sum("PASSAGEIROS_PAGOS"),
        )
        .with_columns(pl.col("PASSAGEIROS_PAGOS").sum().alias("PASSAGEIROS_PAGOS_ROTA"))
        .with_columns(
            pl.when(
                pl.col("PASSAGEIROS_PAGOS").is_not_null()
                & (pl.col("PASSAGEIROS_PAGOS_ROTA") > 0)
            )
            .then(pl.col("PASSAGEIROS_PAGOS") / pl.col("PASSAGEIROS_PAGOS_ROTA") * 100)
            .otherwise(None)
            .alias("MARKET_SHARE_PCT")
        )
        .sort("PASSAGEIROS_PAGOS", descending=True, nulls_last=True)
    )
    return grouped.collect(engine="streaming")


def hhi_from_shares(shares: Iterable[float | None] | pl.Series) -> float | None:
    values = [float(value) for value in shares if value is not None]
    return sum(value * value for value in values) if values else None


def market_hhi(data: Frame | None = None, **filters: object) -> float | None:
    return hhi_from_shares(market_share_by_company(data, **filters)["MARKET_SHARE_PCT"])


def period_coverage(data: Frame | None = None, **filters: object) -> dict[str, object]:
    lf = filter_data(data, **filters)
    periods = lf.select(
        pl.col("PERIODO").min().alias("PERIODO_MIN"),
        pl.col("PERIODO").max().alias("PERIODO_MAX"),
    ).collect(engine="streaming").to_dicts()[0]
    years = year_coverage(lf).collect(engine="streaming")
    if years.is_empty():
        return {**periods, "ULTIMO_ANO": None, "ULTIMO_MES": None, "ULTIMO_ANO_COMPLETO": None, "ANOS": years}
    latest = years.sort("ANO").row(-1, named=True)
    return {
        **periods,
        "ULTIMO_ANO": int(latest["ANO"]),
        "ULTIMO_MES": int(latest["ULTIMO_MES_DISPONIVEL"]),
        "ULTIMO_ANO_COMPLETO": bool(latest["ANO_COMPLETO"]),
        "ANOS": years,
    }


def annual_comparison(
    data: Frame | None = None,
    *,
    metric: str = "PASSAGEIROS_PAGOS",
    year: int | None = None,
    **filters: object,
) -> dict[str, object]:
    if metric not in MAIN_METRICS:
        raise ValueError(f"Metrica nao suportada: {metric}")
    lf = filter_data(data, **filters)
    coverage = period_coverage(lf)
    target_year = year if year is not None else coverage["ULTIMO_ANO"]
    if target_year is None:
        return {"ANO_ATUAL": None, "ANO_ANTERIOR": None, "VALOR_ATUAL": None, "VALOR_ANTERIOR": None, "CRESCIMENTO_PCT": None, "TIPO_COMPARACAO": None}
    year_rows = coverage["ANOS"].filter(pl.col("ANO") == target_year)
    if year_rows.is_empty():
        raise ValueError(f"Ano sem dados: {target_year}")
    target = year_rows.row(0, named=True)
    final_month = 12 if target["ANO_COMPLETO"] else int(target["ULTIMO_MES_DISPONIVEL"])
    values = (
        lf.filter(pl.col("ANO").is_in([target_year - 1, target_year]) & (pl.col("MES") <= final_month))
        .group_by("ANO")
        .agg(nullable_sum(metric))
        .collect(engine="streaming")
    )
    by_year = dict(zip(values["ANO"].to_list(), values[metric].to_list()))
    current, previous = by_year.get(target_year), by_year.get(target_year - 1)
    return {
        "ANO_ATUAL": target_year,
        "ANO_ANTERIOR": target_year - 1,
        "MES_FINAL": final_month,
        "VALOR_ATUAL": current,
        "VALOR_ANTERIOR": previous,
        "CRESCIMENTO_PCT": growth_percent(current, previous),
        "TIPO_COMPARACAO": "ANO_COMPLETO" if target["ANO_COMPLETO"] else "YTD",
    }


def monthly_route_series(
    origin_icao: str,
    destination_icao: str,
    start: date | datetime | str | None = None,
    end: date | datetime | str | None = None,
    company_id: str | None = None,
    data: Frame | None = None,
) -> pl.DataFrame:
    lf = filter_data(
        data,
        origin_icao=origin_icao,
        destination_icao=destination_icao,
        start=start,
        end=end,
        company_id=company_id,
    )
    available_flags = [flag for flag in QUALITY_FLAGS if flag in lf.collect_schema()]
    return (
        lf.group_by("PERIODO")
        .agg(
            *[nullable_sum(column) for column in MAIN_METRICS],
            *[pl.col(flag).any().alias(flag) for flag in available_flags],
        )
        .with_columns(
            pl.when(pl.col("RPK").is_not_null() & pl.col("ASK").is_not_null() & (pl.col("ASK") > 0))
            .then(pl.col("RPK") / pl.col("ASK") * 100)
            .otherwise(None)
            .alias("LOAD_FACTOR_PCT")
        )
        .sort("PERIODO")
        .collect(engine="streaming")
    )


def available_origins(data: Frame | None = None) -> list[str]:
    return _lazy(data).select("AEROPORTO_DE_ORIGEM_SIGLA").unique().sort("AEROPORTO_DE_ORIGEM_SIGLA").collect(engine="streaming").to_series().drop_nulls().to_list()


def available_destinations(origin_icao: str, data: Frame | None = None) -> list[str]:
    return filter_data(data, origin_icao=origin_icao).select("AEROPORTO_DE_DESTINO_SIGLA").unique().sort("AEROPORTO_DE_DESTINO_SIGLA").collect(engine="streaming").to_series().drop_nulls().to_list()


def available_companies(origin_icao: str, destination_icao: str, data: Frame | None = None) -> pl.DataFrame:
    return (
        filter_data(data, origin_icao=origin_icao, destination_icao=destination_icao)
        .select("EMPRESA_ID", "EMPRESA_SIGLA", "EMPRESA_NOME")
        .unique()
        .sort(["EMPRESA_SIGLA", "EMPRESA_NOME"])
        .collect(engine="streaming")
    )


def quality_summary(data: Frame | None = None, **filters: object) -> dict[str, int]:
    lf = filter_data(data, **filters)
    available = [flag for flag in QUALITY_FLAGS if flag in lf.collect_schema()]
    if not available:
        return {}
    row = lf.select(*[pl.col(flag).sum().cast(pl.Int64).alias(flag) for flag in available]).collect(engine="streaming").to_dicts()[0]
    return {key: int(value or 0) for key, value in row.items()}

