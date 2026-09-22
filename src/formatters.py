from __future__ import annotations

from datetime import date, datetime


MONTHS_PT = [
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
]


def format_integer(value: int | float | None) -> str:
    if value is None:
        return "—"
    return f"{int(round(value)):,}".replace(",", ".")


def format_decimal(value: int | float | None, decimals: int = 1) -> str:
    if value is None:
        return "—"
    rendered = f"{float(value):,.{decimals}f}"
    return rendered.replace(",", "_").replace(".", ",").replace("_", ".")


def format_percent(value: int | float | None, decimals: int = 1) -> str:
    return "—" if value is None else f"{format_decimal(value, decimals)}%"


def format_compact(value: int | float | None) -> str:
    if value is None:
        return "—"
    absolute = abs(float(value))
    if absolute >= 1_000_000_000:
        return f"{format_decimal(value / 1_000_000_000, 2)} bi"
    if absolute >= 1_000_000:
        return f"{format_decimal(value / 1_000_000, 2)} mi"
    if absolute >= 1_000:
        return f"{format_decimal(value / 1_000, 2)} mil"
    return format_integer(value)


def format_month(value: date | datetime | None) -> str:
    if value is None:
        return "—"
    return f"{MONTHS_PT[value.month - 1]}/{value.year}"


def format_period_range(start: date | None, end: date | None) -> str:
    return f"{format_month(start)} — {format_month(end)}"


def format_full_number(value: int | float | None) -> str:
    return "Sem informação" if value is None else format_integer(value)


def format_company_name(sigla: str | None, name: str | None) -> str:
    if not name:
        return sigla or "Companhia"
    normalized = name.strip()
    for marker in [" LINHAS AÉREAS", " - VIAÇÃO", " SERVIÇOS DE"]:
        if marker in normalized:
            normalized = normalized.split(marker, 1)[0]
            break
    if len(normalized) > 24 and sigla:
        return sigla
    return normalized.title() if normalized.isupper() else normalized

