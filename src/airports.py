from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path

import polars as pl


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_DIR = ROOT / "data" / "external"
ANAC_AIRPORTS_PATH = EXTERNAL_DIR / "anac_siros_aerodromos.csv"
OURAIRPORTS_PATH = EXTERNAL_DIR / "ourairports_airports.csv"
ANAC_AIRPORTS_URL = "https://siros.anac.gov.br/siros/registros/aerodromo/aerodromos.csv"
OURAIRPORTS_URL = (
    "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv"
)

UF_TO_REGION = {
    "AC": "NORTE", "AL": "NORDESTE", "AP": "NORTE", "AM": "NORTE",
    "BA": "NORDESTE", "CE": "NORDESTE", "DF": "CENTRO-OESTE", "ES": "SUDESTE",
    "GO": "CENTRO-OESTE", "MA": "NORDESTE", "MT": "CENTRO-OESTE",
    "MS": "CENTRO-OESTE", "MG": "SUDESTE", "PA": "NORTE", "PB": "NORDESTE",
    "PR": "SUL", "PE": "NORDESTE", "PI": "NORDESTE", "RJ": "SUDESTE",
    "RN": "NORDESTE", "RS": "SUL", "RO": "NORTE", "RR": "NORTE",
    "SC": "SUL", "SP": "SUDESTE", "SE": "NORDESTE", "TO": "NORTE",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_source(url: str, path: Path, refresh: bool = False) -> None:
    if path.exists() and not refresh:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    urllib.request.urlretrieve(url, temporary)
    os.replace(temporary, path)


def ensure_airport_sources(refresh: bool = False) -> None:
    download_source(ANAC_AIRPORTS_URL, ANAC_AIRPORTS_PATH, refresh)
    download_source(OURAIRPORTS_URL, OURAIRPORTS_PATH, refresh)


def _clean_string(column: str) -> pl.Expr:
    value = pl.col(column).cast(pl.String).str.strip_chars()
    return pl.when(value.is_in(["", "...", "N/I", "NULL"])).then(None).otherwise(value)


def read_anac_airports(path: Path = ANAC_AIRPORTS_PATH) -> pl.DataFrame:
    columns = [
        "SIGLA ICAO AERÓDROMO", "SIGLA IATA AERÓDROMO", "NOME AERÓDROMO",
        "MUNICÍPIO AERÓDROMO", "ESTADO AERÓDROMO", "PAÍS AERÓDROMO",
        "AERONAVE CRÍTICA", "LATITUDE", "LONGITUDE",
    ]
    # The published file contains literal quotes inside names, so quoting must be disabled.
    frame = pl.read_csv(
        path,
        separator=";",
        encoding="utf8-lossy",
        quote_char=None,
        infer_schema_length=0,
    ).with_columns([_clean_string(column).alias(column) for column in columns])
    return frame.select(
        _clean_string("SIGLA ICAO AERÓDROMO").str.to_uppercase().alias("ICAO"),
        pl.when(_clean_string("SIGLA IATA AERÓDROMO").str.contains(r"^[A-Z]{3}$"))
        .then(_clean_string("SIGLA IATA AERÓDROMO"))
        .otherwise(None)
        .alias("ANAC_IATA"),
        _clean_string("NOME AERÓDROMO").alias("ANAC_NOME"),
        _clean_string("MUNICÍPIO AERÓDROMO").alias("ANAC_MUNICIPIO"),
        _clean_string("ESTADO AERÓDROMO").alias("ANAC_UF"),
        _clean_string("PAÍS AERÓDROMO").alias("ANAC_PAIS"),
        _clean_string("LATITUDE").str.replace(",", ".", literal=True).cast(pl.Float64, strict=False).alias("ANAC_LATITUDE"),
        _clean_string("LONGITUDE").str.replace(",", ".", literal=True).cast(pl.Float64, strict=False).alias("ANAC_LONGITUDE"),
    )


def read_ourairports(path: Path = OURAIRPORTS_PATH) -> pl.DataFrame:
    return (
        pl.read_csv(path, infer_schema_length=10000, null_values=[""])
        .filter(pl.col("icao_code").is_not_null())
        .select(
            pl.col("icao_code").str.to_uppercase().alias("ICAO"),
            pl.when(pl.col("iata_code").str.contains(r"^[A-Z]{3}$"))
            .then(pl.col("iata_code"))
            .otherwise(None)
            .alias("OA_IATA"),
            pl.col("name").alias("OA_NOME"),
            pl.col("municipality").alias("OA_MUNICIPIO"),
            pl.col("iso_region").str.split("-").list.last().alias("OA_UF"),
            pl.col("iso_country").alias("OA_PAIS"),
            pl.col("latitude_deg").cast(pl.Float64).alias("OA_LATITUDE"),
            pl.col("longitude_deg").cast(pl.Float64).alias("OA_LONGITUDE"),
        )
    )


def source_airport_dimension(mvp: pl.LazyFrame) -> pl.DataFrame:
    origin = mvp.select(
        "PERIODO",
        pl.col("AEROPORTO_DE_ORIGEM_SIGLA").alias("ICAO"),
        pl.col("AEROPORTO_DE_ORIGEM_NOME").alias("BASE_NOME"),
        pl.col("AEROPORTO_DE_ORIGEM_UF").alias("BASE_UF"),
        pl.col("AEROPORTO_DE_ORIGEM_REGIAO").alias("BASE_REGIAO"),
        pl.col("AEROPORTO_DE_ORIGEM_PAIS").alias("BASE_PAIS"),
    )
    destination = mvp.select(
        "PERIODO",
        pl.col("AEROPORTO_DE_DESTINO_SIGLA").alias("ICAO"),
        pl.col("AEROPORTO_DE_DESTINO_NOME").alias("BASE_NOME"),
        pl.col("AEROPORTO_DE_DESTINO_UF").alias("BASE_UF"),
        pl.col("AEROPORTO_DE_DESTINO_REGIAO").alias("BASE_REGIAO"),
        pl.col("AEROPORTO_DE_DESTINO_PAIS").alias("BASE_PAIS"),
    )
    return (
        pl.concat([origin, destination])
        .group_by("ICAO")
        .agg(
            *[
                pl.col(column).sort_by("PERIODO").drop_nulls().last().alias(column)
                for column in ["BASE_NOME", "BASE_UF", "BASE_REGIAO", "BASE_PAIS"]
            ]
        )
        .sort("ICAO")
        .collect(engine="streaming")
    )


def build_airport_dimension(mvp: pl.LazyFrame) -> tuple[pl.DataFrame, dict[str, object]]:
    base = source_airport_dimension(mvp)
    anac = read_anac_airports()
    ourairports = read_ourairports()
    if anac["ICAO"].n_unique() != anac.height:
        raise RuntimeError("A fonte SIROS/ANAC possui ICAO duplicado.")
    if ourairports["ICAO"].n_unique() != ourairports.height:
        raise RuntimeError("A fonte OurAirports possui ICAO duplicado.")
    joined = base.join(anac, on="ICAO", how="left").join(ourairports, on="ICAO", how="left")

    region_from_uf = pl.col("UF").replace_strict(UF_TO_REGION, default=None)
    dimension = joined.with_columns(
        pl.coalesce("ANAC_IATA", "OA_IATA").alias("IATA"),
        pl.coalesce("ANAC_NOME", "BASE_NOME", "OA_NOME").alias("NOME_AEROPORTO"),
        pl.coalesce("ANAC_MUNICIPIO", "OA_MUNICIPIO").alias("MUNICIPIO"),
        pl.coalesce("ANAC_UF", "BASE_UF", "OA_UF").alias("UF"),
        pl.coalesce("ANAC_PAIS", "BASE_PAIS").alias("PAIS"),
        pl.coalesce("ANAC_LATITUDE", "OA_LATITUDE").alias("LATITUDE"),
        pl.coalesce("ANAC_LONGITUDE", "OA_LONGITUDE").alias("LONGITUDE"),
    ).with_columns(
        pl.coalesce("BASE_REGIAO", region_from_uf).alias("REGIAO"),
        pl.when(pl.col("ANAC_IATA").is_not_null()).then(pl.lit("ANAC_SIROS"))
        .when(pl.col("OA_IATA").is_not_null()).then(pl.lit("OURAIRPORTS"))
        .otherwise(None).alias("FONTE_IATA"),
        pl.when(pl.col("ANAC_NOME").is_not_null()).then(pl.lit("ANAC_SIROS"))
        .when(pl.col("BASE_NOME").is_not_null()).then(pl.lit("ANAC_DADOS_ESTATISTICOS"))
        .otherwise(pl.lit("OURAIRPORTS")).alias("FONTE_NOME"),
        pl.when(pl.col("ANAC_MUNICIPIO").is_not_null()).then(pl.lit("ANAC_SIROS"))
        .when(pl.col("OA_MUNICIPIO").is_not_null()).then(pl.lit("OURAIRPORTS"))
        .otherwise(None).alias("FONTE_MUNICIPIO"),
        pl.when(pl.col("ANAC_LATITUDE").is_not_null() & pl.col("ANAC_LONGITUDE").is_not_null())
        .then(pl.lit("ANAC_SIROS"))
        .when(pl.col("OA_LATITUDE").is_not_null() & pl.col("OA_LONGITUDE").is_not_null())
        .then(pl.lit("OURAIRPORTS"))
        .otherwise(None).alias("FONTE_COORDENADAS"),
        (
            pl.col("ANAC_IATA").is_not_null()
            & pl.col("OA_IATA").is_not_null()
            & (pl.col("ANAC_IATA") != pl.col("OA_IATA"))
        ).alias("FLAG_CONFLITO_IATA"),
        pl.col("ANAC_NOME").is_not_null().alias("FLAG_COBERTO_ANAC_SIROS"),
    ).select(
        "ICAO", "IATA", "NOME_AEROPORTO", "MUNICIPIO", "UF", "REGIAO", "PAIS",
        "LATITUDE", "LONGITUDE", "FONTE_IATA", "FONTE_NOME", "FONTE_MUNICIPIO",
        "FONTE_COORDENADAS", "FLAG_COBERTO_ANAC_SIROS", "FLAG_CONFLITO_IATA",
    ).sort("ICAO")

    duplicate_iata = (
        dimension.filter(pl.col("IATA").is_not_null())
        .group_by("IATA")
        .agg(pl.col("ICAO").n_unique().alias("ICAOS"))
        .filter(pl.col("ICAOS") > 1)
        .height
    )
    stats = {
        "aeroportos": dimension.height,
        "cobertos_anac_siros": int(dimension["FLAG_COBERTO_ANAC_SIROS"].sum()),
        "com_iata": int(dimension["IATA"].is_not_null().sum()),
        "sem_iata": int(dimension["IATA"].is_null().sum()),
        "com_nome": int(dimension["NOME_AEROPORTO"].is_not_null().sum()),
        "com_municipio": int(dimension["MUNICIPIO"].is_not_null().sum()),
        "com_coordenadas": int(
            (dimension["LATITUDE"].is_not_null() & dimension["LONGITUDE"].is_not_null()).sum()
        ),
        "conflitos_iata": int(dimension["FLAG_CONFLITO_IATA"].sum()),
        "iatas_duplicados": duplicate_iata,
        "iata_anac": int((dimension["FONTE_IATA"] == "ANAC_SIROS").sum()),
        "iata_ourairports": int((dimension["FONTE_IATA"] == "OURAIRPORTS").sum()),
        "hash_anac_siros": sha256_file(ANAC_AIRPORTS_PATH),
        "hash_ourairports": sha256_file(OURAIRPORTS_PATH),
    }
    return dimension, stats

