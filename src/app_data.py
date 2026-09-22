from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

import polars as pl
import streamlit as st

from src.formatters import format_company_name
from src.metrics import (
    MVP_PATH,
    annual_comparison,
    basic_metrics,
    calculate_load_factor,
    filter_data,
    market_hhi,
    market_share_by_company,
    monthly_route_series,
    quality_summary,
)
from src.process_data import nullable_sum


ROOT = Path(__file__).resolve().parents[1]
AIRPORTS_PATH = ROOT / "data" / "processed" / "dim_airports.parquet"
DEFAULT_ROUTE = ("SBBE", "SBGR")


@dataclass(frozen=True)
class RouteState:
    origin: str
    destination: str


@dataclass(frozen=True)
class PeriodState:
    start: date
    end: date


@st.cache_resource(show_spinner=False)
def load_datasets(
    mvp_path: str = str(MVP_PATH), airports_path: str = str(AIRPORTS_PATH)
) -> tuple[pl.DataFrame, pl.DataFrame, float]:
    """Load official Parquets once per process and report uncached elapsed time."""
    started = perf_counter()
    mvp = pl.read_parquet(mvp_path)
    airports = pl.read_parquet(airports_path)
    return mvp, airports, perf_counter() - started


def route_pairs(data: pl.DataFrame) -> set[tuple[str, str]]:
    rows = data.select(
        pl.col("AEROPORTO_DE_ORIGEM_SIGLA").alias("origin"),
        pl.col("AEROPORTO_DE_DESTINO_SIGLA").alias("destination"),
    ).unique().iter_rows()
    return set(rows)


def destinations_for(origin: str, routes: set[tuple[str, str]]) -> list[str]:
    return sorted(destination for route_origin, destination in routes if route_origin == origin)


def _query_value(params: Mapping[str, object], key: str) -> str | None:
    value = params.get(key)
    if isinstance(value, (list, tuple)):
        value = value[-1] if value else None
    return str(value) if value not in (None, "") else None


def resolve_route_state(
    params: Mapping[str, object],
    routes: set[tuple[str, str]],
    default: tuple[str, str] = DEFAULT_ROUTE,
) -> RouteState:
    requested = (_query_value(params, "origin"), _query_value(params, "destination"))
    if requested[0] is not None and requested[1] is not None and requested in routes:
        return RouteState(*requested)
    if default in routes:
        return RouteState(*default)
    first = sorted(routes)[0]
    return RouteState(*first)


def reverse_route(
    origin: str, destination: str, routes: set[tuple[str, str]]
) -> tuple[RouteState, bool]:
    if (destination, origin) in routes:
        return RouteState(destination, origin), True
    return RouteState(origin, destination), False


def route_periods(data: pl.DataFrame, origin: str, destination: str) -> list[date]:
    return (
        data.filter(
            (pl.col("AEROPORTO_DE_ORIGEM_SIGLA") == origin)
            & (pl.col("AEROPORTO_DE_DESTINO_SIGLA") == destination)
        )["PERIODO"]
        .unique()
        .sort()
        .to_list()
    )


def default_period_start(periods: Sequence[date], months: int = 60) -> date:
    return periods[max(0, len(periods) - months)]


def resolve_period_state(
    params: Mapping[str, object], periods: Sequence[date], months: int = 60
) -> PeriodState:
    if not periods:
        raise ValueError("A rota selecionada nao possui periodos.")
    default_start, default_end = default_period_start(periods, months), periods[-1]
    available = set(periods)
    try:
        start_text = _query_value(params, "start")
        end_text = _query_value(params, "end")
        start = date.fromisoformat(start_text) if start_text else default_start
        end = date.fromisoformat(end_text) if end_text else default_end
    except ValueError:
        return PeriodState(default_start, default_end)
    if start not in available or end not in available or start > end:
        return PeriodState(default_start, default_end)
    return PeriodState(start, end)


def resolve_company(params: Mapping[str, object], valid_ids: set[str]) -> str | None:
    company = _query_value(params, "company")
    return company if company in valid_ids else None


def airport_lookup(airports: pl.DataFrame) -> dict[str, dict[str, object]]:
    return {row["ICAO"]: row for row in airports.to_dicts()}


def airport_display(icao: str, lookup: Mapping[str, Mapping[str, object]]) -> str:
    airport = lookup.get(icao, {})
    code = airport.get("IATA") or icao
    place = airport.get("MUNICIPIO") or airport.get("NOME_AEROPORTO") or icao
    return f"{code} · {str(place).title()}"


def airport_code(icao: str, lookup: Mapping[str, Mapping[str, object]]) -> str:
    return str(lookup.get(icao, {}).get("IATA") or icao)


def airport_place(icao: str, lookup: Mapping[str, Mapping[str, object]]) -> str:
    airport = lookup.get(icao, {})
    return str(airport.get("MUNICIPIO") or airport.get("NOME_AEROPORTO") or icao).title()


def company_options(
    data: pl.DataFrame, origin: str, destination: str, start: date, end: date
) -> pl.DataFrame:
    return (
        filter_data(
            data,
            origin_icao=origin,
            destination_icao=destination,
            start=start,
            end=end,
        )
        .select("EMPRESA_ID", "EMPRESA_SIGLA", "EMPRESA_NOME")
        .unique()
        .sort(["EMPRESA_SIGLA", "EMPRESA_NOME"])
        .collect(engine="streaming")
        .with_columns(
            pl.struct("EMPRESA_SIGLA", "EMPRESA_NOME")
            .map_elements(
                lambda row: format_company_name(row["EMPRESA_SIGLA"], row["EMPRESA_NOME"]),
                return_dtype=pl.String,
            )
            .alias("DISPLAY_NAME")
        )
    )


def operator_table(route_data: pl.DataFrame, shares: pl.DataFrame) -> pl.DataFrame:
    """Build operator metrics while preserving total-route share denominators."""
    operations = (
        route_data.lazy()
        .group_by("EMPRESA_ID")
        .agg(
            *[nullable_sum(column) for column in ["ASSENTOS", "DECOLAGENS", "ASK", "RPK"]],
        )
        .collect(engine="streaming")
    )
    table = shares.join(operations, on="EMPRESA_ID", how="left")
    return table.with_columns(
        pl.struct("EMPRESA_SIGLA", "EMPRESA_NOME")
        .map_elements(
            lambda row: format_company_name(row["EMPRESA_SIGLA"], row["EMPRESA_NOME"]),
            return_dtype=pl.String,
        )
        .alias("COMPANHIA"),
        pl.struct("RPK", "ASK")
        .map_elements(
            lambda row: calculate_load_factor(row["RPK"], row["ASK"]),
            return_dtype=pl.Float64,
        )
        .alias("LOAD_FACTOR_PCT"),
    ).select(
        "EMPRESA_ID", "COMPANHIA", "PASSAGEIROS_PAGOS", "MARKET_SHARE_PCT",
        "ASSENTOS", "DECOLAGENS", "LOAD_FACTOR_PCT",
    ).sort("PASSAGEIROS_PAGOS", descending=True, nulls_last=True)


def build_analysis(
    data: pl.DataFrame,
    origin: str,
    destination: str,
    start: date,
    end: date,
    company_id: str | None,
) -> dict[str, object]:
    started = perf_counter()
    route_data = filter_data(
        data,
        origin_icao=origin,
        destination_icao=destination,
        start=start,
        end=end,
    ).collect(engine="streaming")
    operational = (
        route_data
        if company_id is None
        else route_data.filter(pl.col("EMPRESA_ID") == company_id)
    )
    shares = market_share_by_company(route_data)
    comparison_data = filter_data(data, origin_icao=origin, destination_icao=destination,
                                  company_id=company_id).collect(engine="streaming")
    comparison = {"CRESCIMENTO_PCT": None, "MES_FINAL": None}
    if not comparison_data.filter(pl.col("ANO") == end.year).is_empty():
        comparison = annual_comparison(comparison_data, year=end.year)
        final_month = int(comparison["MES_FINAL"])
        for comparison_year in [end.year - 1, end.year]:
            window = comparison_data.filter(
                (pl.col("ANO") == comparison_year) & (pl.col("MES") <= final_month)
            )
            if window["MES"].n_unique() != final_month or window["PASSAGEIROS_PAGOS"].null_count():
                comparison = {**comparison, "CRESCIMENTO_PCT": None}
    comparison_is_contextual = (
        start <= date(end.year, 1, 1)
        and int(comparison.get("MES_FINAL") or 0) == end.month
    )
    if not comparison_is_contextual:
        comparison = {**comparison, "CRESCIMENTO_PCT": None}
    series = monthly_route_series(origin, destination, company_id=company_id, data=route_data)
    if not series.is_empty():
        calendar = pl.DataFrame({"PERIODO": pl.date_range(start, end, interval="1mo", eager=True)})
        series = calendar.join(series, on="PERIODO", how="left").sort("PERIODO")
    return {
        "route_data": route_data,
        "operational_data": operational,
        "summary": basic_metrics(operational),
        "series": series,
        "shares": shares,
        "hhi": market_hhi(route_data),
        "operators": operator_table(route_data, shares),
        "quality": quality_summary(operational),
        "comparison": comparison,
        "elapsed_seconds": perf_counter() - started,
    }


def has_operations(series: pl.DataFrame) -> bool:
    return not series.is_empty()

