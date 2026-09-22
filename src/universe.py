from __future__ import annotations

import polars as pl


def geography_expression() -> pl.Expr:
    origin_br = pl.col("AEROPORTO_DE_ORIGEM_PAIS") == "BRASIL"
    destination_br = pl.col("AEROPORTO_DE_DESTINO_PAIS") == "BRASIL"
    return (
        pl.when(origin_br & destination_br)
        .then(pl.lit("DOMESTICA_BRASILEIRA"))
        .when(origin_br ^ destination_br)
        .then(pl.lit("INTERNACIONAL_ENVOLVE_BRASIL"))
        .otherwise(pl.lit("DEMAIS_CASOS"))
        .alias("ESCOPO_GEOGRAFICO")
    )


def add_universe_flags(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Add the historically validated universe flags without changing row grain."""
    regular_history = lf.group_by(["ROTA_DIRECIONAL", "EMPRESA_ID"]).agg(
        pl.col("FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS")
        .filter(pl.col("GRUPO_DE_VOO") == "REGULAR")
        .any()
        .alias("FLAG_HISTORICO_PASSAGEIROS_ROTA_EMPRESA")
    )
    base = lf.with_columns(geography_expression()).join(
        regular_history,
        on=["ROTA_DIRECIONAL", "EMPRESA_ID"],
        how="left",
    )

    route_valid = (
        pl.col("AEROPORTO_DE_ORIGEM_SIGLA").is_not_null()
        & pl.col("AEROPORTO_DE_DESTINO_SIGLA").is_not_null()
        & (pl.col("AEROPORTO_DE_ORIGEM_SIGLA") != pl.col("AEROPORTO_DE_DESTINO_SIGLA"))
    )
    regular = (pl.col("GRUPO_DE_VOO") == "REGULAR").fill_null(False)
    passenger_history = pl.col("FLAG_HISTORICO_PASSAGEIROS_ROTA_EMPRESA").fill_null(False)
    domestic_geography = pl.col("ESCOPO_GEOGRAFICO") == "DOMESTICA_BRASILEIRA"
    official_domestic = pl.col("NATUREZA") == "DOMÉSTICA"
    involves_brazil = pl.col("ESCOPO_GEOGRAFICO").is_in(
        ["DOMESTICA_BRASILEIRA", "INTERNACIONAL_ENVOLVE_BRASIL"]
    )

    return base.with_columns(
        route_valid.alias("FLAG_ROTA_OD_VALIDA"),
        (regular & passenger_history).alias("FLAG_REGULAR_PASSAGEIROS_HISTORICO"),
        (regular & passenger_history & domestic_geography & official_domestic).alias(
            "FLAG_CANDIDATO_MVP_DOMESTICO"
        ),
        (regular & passenger_history & domestic_geography & official_domestic & route_valid).alias(
            "FLAG_UNIVERSO_MVP_RECOMENDADO"
        ),
        (regular & passenger_history & involves_brazil & route_valid).alias(
            "FLAG_UNIVERSO_REGULAR_COM_INTERNACIONAL"
        ),
    )


def year_coverage(lf: pl.LazyFrame) -> pl.LazyFrame:
    return (
        lf.select("ANO", "MES")
        .unique()
        .group_by("ANO")
        .agg(
            pl.col("MES").n_unique().alias("MESES_DISPONIVEIS"),
            pl.col("MES").min().alias("PRIMEIRO_MES_DISPONIVEL"),
            pl.col("MES").max().alias("ULTIMO_MES_DISPONIVEL"),
        )
        .with_columns(
            (
                (pl.col("MESES_DISPONIVEIS") == 12)
                & (pl.col("PRIMEIRO_MES_DISPONIVEL") == 1)
                & (pl.col("ULTIMO_MES_DISPONIVEL") == 12)
            ).alias("ANO_COMPLETO")
        )
        .with_columns((~pl.col("ANO_COMPLETO")).alias("ANO_PARCIAL"))
        .sort("ANO")
    )

