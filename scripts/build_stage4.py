from __future__ import annotations

import argparse
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

from src.airports import (  # noqa: E402
    ANAC_AIRPORTS_PATH,
    ANAC_AIRPORTS_URL,
    OURAIRPORTS_PATH,
    OURAIRPORTS_URL,
    build_airport_dimension,
    ensure_airport_sources,
)
from src.process_data import DIMENSIONS, sha256_file  # noqa: E402
from src.universe import add_universe_flags  # noqa: E402


SOURCE_PATH = ROOT / "data" / "processed" / "avscope_routes_monthly.parquet"
MVP_PATH = ROOT / "data" / "processed" / "avscope_mvp_domestic.parquet"
AIRPORT_DIM_PATH = ROOT / "data" / "processed" / "dim_airports.parquet"
UNIVERSE_DOC_PATH = ROOT / "docs" / "universo_mvp.md"
AIRPORT_DOC_PATH = ROOT / "docs" / "fontes_dimensao_aeroportos.md"

EXPECTED = {
    "registros": 515_449,
    "rotas": 5_187,
    "aeroportos": 334,
    "companhias": 43,
    "periodo_min": "2000-01-01",
    "periodo_max": "2026-07-01",
    "recuperados": 11_416,
}


def atomic_write_parquet(frame: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.parquet")
    if temporary.exists():
        temporary.unlink()
    frame.write_parquet(temporary, compression="zstd", statistics=True)
    os.replace(temporary, path)


def add_product_flags(lf: pl.LazyFrame) -> pl.LazyFrame:
    return add_universe_flags(lf).with_columns(
        pl.col("FLAG_UNIVERSO_MVP_RECOMENDADO").alias("FLAG_UNIVERSO_MVP_V2"),
        (
            pl.col("FLAG_UNIVERSO_MVP_RECOMENDADO")
            & ~pl.col("FLAG_UNIVERSO_MVP").fill_null(False)
        ).alias("FLAG_REGISTRO_RECUPERADO_MVP_V2"),
        (pl.col("RPK").is_not_null() & pl.col("ASK").is_not_null() & (pl.col("RPK") > pl.col("ASK"))).alias("FLAG_RPK_MAIOR_ASK"),
        (pl.col("PASSAGEIROS_PAGOS").is_not_null() & pl.col("ASSENTOS").is_not_null() & (pl.col("PASSAGEIROS_PAGOS") > pl.col("ASSENTOS"))).alias("FLAG_PASSAGEIROS_MAIOR_ASSENTOS"),
        (pl.col("ASK") == 0).fill_null(False).and_(pl.col("RPK") > 0).fill_null(False).alias("FLAG_ASK_ZERO_RPK_POSITIVO"),
        (pl.col("DECOLAGENS") == 0).fill_null(False).and_(pl.col("PASSAGEIROS_PAGOS") > 0).fill_null(False).alias("FLAG_DECOLAGENS_ZERO_PASSAGEIROS_POSITIVOS"),
        (pl.col("ASSENTOS") == 0).fill_null(False).and_(pl.col("PASSAGEIROS_PAGOS") > 0).fill_null(False).alias("FLAG_ASSENTOS_ZERO_PASSAGEIROS_POSITIVOS"),
    )


def summarize_mvp(frame: pl.DataFrame) -> dict[str, Any]:
    airports = pl.concat(
        [
            frame.select(pl.col("AEROPORTO_DE_ORIGEM_SIGLA").alias("ICAO")),
            frame.select(pl.col("AEROPORTO_DE_DESTINO_SIGLA").alias("ICAO")),
        ]
    )["ICAO"].n_unique()
    duplicate_grain = frame.height - frame.select(DIMENSIONS).unique().height
    return {
        "registros": frame.height,
        "rotas": frame["ROTA_DIRECIONAL"].n_unique(),
        "aeroportos": airports,
        "companhias": frame["EMPRESA_ID"].n_unique(),
        "periodo_min": str(frame["PERIODO"].min()),
        "periodo_max": str(frame["PERIODO"].max()),
        "recuperados": int(frame["FLAG_REGISTRO_RECUPERADO_MVP_V2"].sum()),
        "flag_antiga_verdadeira": int(frame["FLAG_UNIVERSO_MVP"].sum()),
        "duplicidades_no_grao": duplicate_grain,
        "grupo_de_voo": frame["GRUPO_DE_VOO"].unique().sort().to_list(),
        "natureza": frame["NATUREZA"].unique().sort().to_list(),
    }


def validate_expected(stats: dict[str, Any]) -> None:
    differences = {key: (EXPECTED[key], stats[key]) for key in EXPECTED if stats[key] != EXPECTED[key]}
    if differences:
        raise RuntimeError(f"O universo divergiu da Etapa 3: {differences}")
    if stats["duplicidades_no_grao"] != 0:
        raise RuntimeError(f"Foram encontradas {stats['duplicidades_no_grao']} duplicidades no grao.")


def validate_reference_airports(dimension: pl.DataFrame) -> list[dict[str, Any]]:
    expected = {"SBBE": "BEL", "SBGR": "GRU", "SBSP": "CGH", "SBRJ": "SDU", "SBBR": "BSB", "SBEG": "MAO"}
    rows = dimension.filter(pl.col("ICAO").is_in(expected)).select("ICAO", "IATA", "NOME_AEROPORTO", "MUNICIPIO").sort("ICAO").to_dicts()
    found = {row["ICAO"]: row["IATA"] for row in rows}
    differences = {icao: (iata, found.get(icao)) for icao, iata in expected.items() if found.get(icao) != iata}
    if differences:
        raise RuntimeError(f"Mapeamentos aeroportuarios de referencia divergentes: {differences}")
    return rows


def write_docs(mvp: dict[str, Any], airport: dict[str, Any], references: list[dict[str, Any]]) -> None:
    generated = datetime.now().isoformat(timespec="seconds")
    UNIVERSE_DOC_PATH.write_text(
        f"""# Universo oficial do MVP

Gerado em: `{generated}`.

## Definicao

O produto usa exclusivamente registros com `GRUPO_DE_VOO = REGULAR`, `NATUREZA = DOMÉSTICA`, pais de origem e destino iguais a `BRASIL`, codigos aeroportuarios presentes, origem diferente de destino e evidencia historica de transporte de passageiros na mesma combinacao `ROTA_DIRECIONAL + EMPRESA_ID`.

A evidencia historica e verdadeira quando ao menos um mes regular da rota-companhia possui `FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS`. Ela preserva meses zerados pertencentes a uma operacao historicamente caracterizada como transporte de passageiros, sem admitir automaticamente toda operacao cargueira regular.

## Flags e rastreabilidade

- `FLAG_UNIVERSO_MVP`: regra original da Etapa 2, avaliada linha a linha: voo regular e evidencia positiva na propria linha.
- `FLAG_UNIVERSO_MVP_V2`: regra oficial validada na Etapa 3, com evidencia historica, recorte domestico brasileiro e rota OD valida.
- `FLAG_REGISTRO_RECUPERADO_MVP_V2`: linha aceita pela V2 que seria perdida pela flag original.

No arquivo oficial, `{mvp['flag_antiga_verdadeira']}` linhas tambem satisfazem a flag antiga e `{mvp['recuperados']}` foram recuperadas pela V2. Total: `{mvp['registros']}` registros.

Na base processada completa, a matriz e: `{mvp['flags_ambas_verdadeiras']}` registros aceitos por ambas, `{mvp['flags_v2_apenas']}` somente pela V2, `{mvp['flags_antiga_apenas']}` somente pela antiga e `{mvp['flags_ambas_falsas']}` por nenhuma. Os registros aceitos apenas pela regra antiga ficam fora do produto porque a flag original nao exigia simultaneamente o recorte domestico brasileiro, a validade OD e a evidencia historica usada pela V2.

## Cobertura

- Rotas direcionais: `{mvp['rotas']}`.
- Aeroportos: `{mvp['aeroportos']}`.
- Companhias por `EMPRESA_ID`: `{mvp['companhias']}`.
- Periodo: `{mvp['periodo_min']}` a `{mvp['periodo_max']}`.
- `GRUPO_DE_VOO`: `{', '.join(mvp['grupo_de_voo'])}`.
- `NATUREZA`: `{', '.join(mvp['natureza'])}`.

## Grao

O Parquet preserva o grao da base processada: `PERIODO + ROTA_DIRECIONAL + EMPRESA_ID + categorias operacionais e atributos de origem/destino`. Nao houve nova agregacao nem mistura de categorias. Embora `GRUPO_DE_VOO` e `NATUREZA` sejam constantes neste recorte, elas foram mantidas para rastreabilidade. Duplicidades no conjunto completo de dimensoes da Etapa 2: `{mvp['duplicidades_no_grao']}`.

## Anomalias

Registros com `RPK > ASK`, passageiros acima de assentos ou denominadores zerados nao foram excluidos. O arquivo inclui flags especificas para que as metricas e a futura interface possam sinaliza-los. Valores nulos permanecem nulos; zero observado nao e usado como substituto de ausencia de informacao.
""",
        encoding="utf-8",
    )

    reference_lines = "\n".join(
        f"- `{row['ICAO']}` -> `{row['IATA']}`: {row['NOME_AEROPORTO']} ({row['MUNICIPIO']})."
        for row in references
    )
    AIRPORT_DOC_PATH.write_text(
        f"""# Fontes da dimensao de aeroportos

Gerado em: `{generated}`.

## Fontes

1. **SIROS/ANAC**, arquivo estruturado `{ANAC_AIRPORTS_URL}`. E a fonte prioritaria para ICAO, IATA, nome oficial, municipio, UF, pais, latitude e longitude. Snapshot local: `data/external/{ANAC_AIRPORTS_PATH.name}`, SHA-256 `{airport['hash_anac_siros']}`.
2. **Dados Estatisticos do Transporte Aereo da ANAC**, por meio do Parquet da Etapa 2. Fornecem nome, UF, regiao e pais para codigos historicos ausentes do cadastro SIROS atual.
3. **OurAirports**, arquivo aberto `{OURAIRPORTS_URL}` e dicionario em `https://ourairports.com/help/data-dictionary.html`. E usado somente como complemento para IATA, municipio ou coordenadas ausentes na ANAC. Snapshot local: `data/external/{OURAIRPORTS_PATH.name}`, SHA-256 `{airport['hash_ourairports']}`.

ICAO e a chave interna. Nenhum IATA foi inferido por manipulacao de texto. A precedencia e ANAC SIROS, dados estatisticos ANAC quando aplicavel e, por ultimo, OurAirports.

## Cobertura do universo

- Aeroportos do MVP: `{airport['aeroportos']}`.
- Encontrados no cadastro SIROS atual: `{airport['cobertos_anac_siros']}`.
- Com IATA: `{airport['com_iata']}` (`{airport['iata_anac']}` pela ANAC e `{airport['iata_ourairports']}` complementares).
- Sem IATA: `{airport['sem_iata']}`.
- Com nome: `{airport['com_nome']}`.
- Com municipio: `{airport['com_municipio']}`.
- Com coordenadas completas: `{airport['com_coordenadas']}`.
- Conflitos de IATA valido entre ANAC e OurAirports: `{airport['conflitos_iata']}`.
- Codigos IATA associados a mais de um ICAO no universo: `{airport['iatas_duplicados']}`.

Os codigos sem correspondencia no SIROS atual sao principalmente aerodromos historicos, militares, encerrados ou codigos legados. Nesses casos, o nome/UF/regiao/pais da propria serie estatistica foi preservado. Ausencia de IATA continua nula.

## Validacoes explicitas

{reference_lines}

## Observacoes de ingestao

O CSV do SIROS usa ponto e virgula e virgula decimal. Alguns nomes internacionais possuem aspas literais sem escape CSV; por isso a leitura desabilita semantica de aspas e valida exatamente nove campos por linha. O OurAirports e UTF-8 separado por virgula. Os snapshots locais tornam a execucao repetivel; use `--refresh-airports` somente para atualizar conscientemente as fontes externas.
""",
        encoding="utf-8",
    )


def run(refresh_airports: bool = False) -> dict[str, Any]:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(SOURCE_PATH)
    source_hash_before = sha256_file(SOURCE_PATH)
    flagged = add_product_flags(pl.scan_parquet(SOURCE_PATH))
    flag_matrix = (
        flagged.group_by("FLAG_UNIVERSO_MVP", "FLAG_UNIVERSO_MVP_V2")
        .len()
        .collect(engine="streaming")
    )
    flag_counts = {
        (bool(row["FLAG_UNIVERSO_MVP"]), bool(row["FLAG_UNIVERSO_MVP_V2"])): int(row["len"])
        for row in flag_matrix.to_dicts()
    }
    selected = (
        flagged
        .filter(pl.col("FLAG_UNIVERSO_MVP_V2"))
        .sort(DIMENSIONS)
        .collect(engine="streaming")
    )
    mvp_stats = summarize_mvp(selected)
    mvp_stats.update(
        {
            "flags_ambas_verdadeiras": flag_counts.get((True, True), 0),
            "flags_v2_apenas": flag_counts.get((False, True), 0),
            "flags_antiga_apenas": flag_counts.get((True, False), 0),
            "flags_ambas_falsas": flag_counts.get((False, False), 0),
        }
    )
    validate_expected(mvp_stats)
    atomic_write_parquet(selected, MVP_PATH)

    ensure_airport_sources(refresh_airports)
    dimension, airport_stats = build_airport_dimension(pl.scan_parquet(MVP_PATH))
    references = validate_reference_airports(dimension)
    if dimension["ICAO"].n_unique() != EXPECTED["aeroportos"]:
        raise RuntimeError("A dimensao nao possui uma linha unica para cada aeroporto do MVP.")
    atomic_write_parquet(dimension, AIRPORT_DIM_PATH)
    write_docs(mvp_stats, airport_stats, references)

    if sha256_file(SOURCE_PATH) != source_hash_before:
        raise RuntimeError("O Parquet principal foi alterado durante a Etapa 4.")
    result = {
        "fonte_principal_preservada": True,
        "mvp": {**mvp_stats, "bytes": MVP_PATH.stat().st_size, "sha256": sha256_file(MVP_PATH)},
        "aeroportos": {**airport_stats, "bytes": AIRPORT_DIM_PATH.stat().st_size, "sha256": sha256_file(AIRPORT_DIM_PATH)},
        "referencias": references,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Constroi os artefatos oficiais da Etapa 4.")
    parser.add_argument("--refresh-airports", action="store_true", help="Atualiza os snapshots externos antes de construir a dimensao.")
    args = parser.parse_args()
    run(refresh_airports=args.refresh_airports)


if __name__ == "__main__":
    main()

