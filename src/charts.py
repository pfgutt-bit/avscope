from __future__ import annotations

import polars as pl
import plotly.graph_objects as go

from src.formatters import format_integer, format_month, format_percent


COLORS = {
    "background": "#0B0D10",
    "surface": "#111419",
    "surface_elevated": "#171B21",
    "text": "#F4F6F8",
    "muted": "#929AA5",
    "accent": "#6EA8FE",
    "neutral": "#727B87",
    "warning": "#E7B65A",
    "danger": "#E36D76",
    "grid": "rgba(255,255,255,0.055)",
}

CHART_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
    "scrollZoom": False,
}

METRICS = {
    "Passageiros": ("PASSAGEIROS_PAGOS", "Passageiros"),
    "Assentos": ("ASSENTOS", "Assentos"),
    "Load Factor": ("LOAD_FACTOR_PCT", "Load Factor (%)"),
    "Decolagens": ("DECOLAGENS", "Decolagens"),
}


def _context(series: pl.DataFrame) -> list[list[str]]:
    return [
        [
            format_month(row["PERIODO"]),
            format_integer(row["PASSAGEIROS_PAGOS"]),
            format_integer(row["ASSENTOS"]),
            format_integer(row["DECOLAGENS"]),
            format_percent(row["LOAD_FACTOR_PCT"]),
        ]
        for row in series.iter_rows(named=True)
    ]


def _style(figure: go.Figure, *, height: int = 360, y_title: str | None = None) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=8, r=12, t=18, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=COLORS["muted"], size=12),
        hoverlabel=dict(
            bgcolor=COLORS["surface_elevated"],
            bordercolor="rgba(255,255,255,0.12)",
            font=dict(color=COLORS["text"], size=13),
        ),
        hovermode="x unified",
        showlegend=False,
        dragmode=False,
        separators=",.",
    )
    figure.update_xaxes(
        showgrid=False,
        showline=False,
        zeroline=False,
        tickformat="%b\n%Y",
        nticks=10,
        fixedrange=True,
    )
    figure.update_yaxes(
        title=y_title,
        title_font=dict(size=11, color=COLORS["muted"]),
        gridcolor=COLORS["grid"],
        gridwidth=1,
        showline=False,
        zeroline=False,
        fixedrange=True,
        rangemode="tozero",
        tickformat=".0f" if y_title and "%" in y_title else ",.0f",
    )
    return figure


def _month_ticks(figure: go.Figure, series: pl.DataFrame, maximum: int = 9) -> go.Figure:
    periods = series["PERIODO"].to_list()
    if not periods:
        return figure
    step = max(1, len(periods) // maximum)
    ticks = periods[::step]
    if ticks[-1] != periods[-1]:
        ticks.append(periods[-1])
    figure.update_xaxes(
        tickmode="array",
        tickvals=ticks,
        ticktext=[format_month(period) for period in ticks],
    )
    return figure


def market_pulse_chart(series: pl.DataFrame, metric_label: str) -> go.Figure:
    column, axis_label = METRICS[metric_label]
    figure = go.Figure(
        go.Scatter(
            x=series["PERIODO"].to_list(),
            y=series[column].to_list(),
            mode="lines",
            line=dict(color=COLORS["accent"], width=2.4),
            customdata=_context(series),
            connectgaps=False,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "%{customdata[1]} passageiros<br>"
                "%{customdata[2]} assentos<br>"
                "%{customdata[3]} decolagens<br>"
                "%{customdata[4]} load factor<extra></extra>"
            ),
        )
    )
    return _month_ticks(_style(figure, height=390, y_title=axis_label), series)


def capacity_chart(series: pl.DataFrame) -> go.Figure:
    context = [
        [
            format_month(row["PERIODO"]),
            format_integer(row["PASSAGEIROS_PAGOS"]),
            format_integer(row["ASSENTOS"]),
            format_integer(
                None
                if row["PASSAGEIROS_PAGOS"] is None or row["ASSENTOS"] is None
                else row["ASSENTOS"] - row["PASSAGEIROS_PAGOS"]
            ),
            format_percent(row["LOAD_FACTOR_PCT"]),
        ]
        for row in series.iter_rows(named=True)
    ]
    figure = go.Figure()
    for column, name, color in [
        ("ASSENTOS", "Assentos", COLORS["neutral"]),
        ("PASSAGEIROS_PAGOS", "Passageiros", COLORS["accent"]),
    ]:
        figure.add_trace(
            go.Scatter(
                x=series["PERIODO"].to_list(),
                y=series[column].to_list(),
                name=name,
                mode="lines",
                line=dict(color=color, width=2.2),
                customdata=context,
                connectgaps=False,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "%{customdata[1]} passageiros<br>"
                    "%{customdata[2]} assentos<br>"
                    "%{customdata[3]} de diferença<br>"
                    "%{customdata[4]} load factor<extra></extra>"
                ),
            )
        )
    figure = _style(figure, height=330, y_title="Pessoas / assentos")
    figure.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
    )
    return _month_ticks(figure, series)


def load_factor_chart(series: pl.DataFrame) -> go.Figure:
    figure = go.Figure(
        go.Scatter(
            x=series["PERIODO"].to_list(),
            y=series["LOAD_FACTOR_PCT"].to_list(),
            mode="lines",
            line=dict(color=COLORS["accent"], width=2.2),
            customdata=_context(series),
            connectgaps=False,
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[4]} load factor<extra></extra>",
        )
    )
    anomalies = series.filter(pl.col("LOAD_FACTOR_PCT") > 100)
    if not anomalies.is_empty():
        figure.add_trace(
            go.Scatter(
                x=anomalies["PERIODO"].to_list(),
                y=anomalies["LOAD_FACTOR_PCT"].to_list(),
                mode="markers",
                marker=dict(color=COLORS["warning"], size=8, symbol="diamond"),
                customdata=_context(anomalies),
                hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[4]} load factor<br>Dado sinalizado<extra></extra>",
            )
        )
    return _month_ticks(_style(figure, height=320, y_title="Load Factor (%)"), series)


def market_share_chart(
    shares: pl.DataFrame, selected_company: str | None = None
) -> go.Figure:
    labels = shares["DISPLAY_NAME"].to_list()
    values = shares["MARKET_SHARE_PCT"].to_list()
    colors = [
        COLORS["accent"] if selected_company is None or company == selected_company else COLORS["neutral"]
        for company in shares["EMPRESA_ID"].to_list()
    ]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=colors),
            text=[format_percent(value) for value in values],
            textposition="outside",
            cliponaxis=False,
            customdata=[
                [format_integer(passengers), format_percent(share)]
                for passengers, share in zip(shares["PASSAGEIROS_PAGOS"], values)
            ],
            hovertemplate="<b>%{y}</b><br>%{customdata[0]} passageiros<br>%{customdata[1]} de participação<extra></extra>",
        )
    )
    figure.update_layout(
        height=max(260, 55 * shares.height + 80),
        margin=dict(l=8, r=52, t=12, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=COLORS["muted"], size=12),
        hoverlabel=dict(bgcolor=COLORS["surface_elevated"], bordercolor="rgba(255,255,255,0.12)", font=dict(color=COLORS["text"])),
        showlegend=False,
        dragmode=False,
    )
    figure.update_xaxes(visible=False, range=[0, max([100.0, *(value or 0 for value in values)]) * 1.08], fixedrange=True)
    figure.update_yaxes(autorange="reversed", showgrid=False, fixedrange=True)
    return figure

