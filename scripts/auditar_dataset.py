from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import polars as pl
from charset_normalizer import from_bytes


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "Dados_Estatisticos.csv"
REPORT_PATH = ROOT / "docs" / "auditoria_dataset.md"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_newlines(path: Path) -> int:
    total = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            total += chunk.count(b"\n")
    return total


def read_sample_bytes(path: Path, size: int = 2_000_000) -> bytes:
    with path.open("rb") as handle:
        return handle.read(size)


def detect_encoding(sample: bytes) -> dict[str, str | float]:
    if sample.startswith(b"\xef\xbb\xbf"):
        return {
            "encoding": "utf-8-sig",
            "source": "BOM UTF-8 detectado no inicio do arquivo",
            "confidence": 1.0,
        }

    matches = from_bytes(sample)
    best = matches.best()
    if best is None:
        return {"encoding": "utf-8", "source": "fallback", "confidence": 0.0}

    return {
        "encoding": best.encoding or "utf-8",
        "source": "charset_normalizer",
        "confidence": float(best.percent_coherence or 0) / 100,
    }


def split_sample_lines(sample: bytes, encoding: str) -> list[str]:
    text = sample.decode(encoding, errors="replace")
    return text.splitlines()


def detect_header_and_separator(lines: list[str]) -> tuple[int, str, list[str], dict[str, int]]:
    candidates = [";", ",", "\t", "|"]
    scores: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines[:50]):
        for separator in candidates:
            scores.append((line.count(separator), index, separator))

    delimiter_count, header_index, separator = max(scores, key=lambda item: item[0])
    if delimiter_count == 0:
        raise RuntimeError("Nao foi possivel detectar separador/cabecalho.")

    reader = csv.reader([lines[header_index]], delimiter=separator, quotechar='"')
    columns = next(reader)
    delimiter_counts = {candidate: lines[header_index].count(candidate) for candidate in candidates}
    return header_index, separator, columns, delimiter_counts


def fmt_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:,.2f} {unit}".replace(",", "X").replace(".", ",").replace("X", ".")
        value /= 1024
    return f"{size} B"


def norm_name(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def find_columns(columns: list[str], *tokens: str, any_token: bool = False) -> list[str]:
    normalized_tokens = [norm_name(token) for token in tokens]
    result = []
    for col in columns:
        normalized = norm_name(col)
        if any_token:
            if any(token in normalized for token in normalized_tokens):
                result.append(col)
        elif all(token in normalized for token in normalized_tokens):
            result.append(col)
    return result


def exact_or_contains(columns: list[str], exact: str, *tokens: str) -> list[str]:
    exact_norm = norm_name(exact)
    exact_matches = [col for col in columns if norm_name(col) == exact_norm]
    return exact_matches or find_columns(columns, *tokens)


def safe_collect(lf: pl.LazyFrame) -> pl.DataFrame:
    try:
        return lf.collect(engine="streaming")
    except TypeError:
        return lf.collect(streaming=True)


def md_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    if not rows:
        return "_Nenhum registro._"

    def cell(value: object) -> str:
        if value is None:
            return ""
        text = str(value)
        text = text.replace("\n", " ").replace("|", "\\|")
        return text

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell(row.get(col, "")) for col in columns) + " |")
    return "\n".join(lines)


def get_distinct_values(lf: pl.LazyFrame, column: str, limit: int = 500) -> list[str]:
    frame = safe_collect(
        lf.select(pl.col(column).str.strip_chars().alias(column))
        .filter(pl.col(column).is_not_null() & (pl.col(column) != ""))
        .unique()
        .sort(column)
        .limit(limit)
    )
    return [str(item) for item in frame[column].to_list()]


def main() -> None:
    if not RAW_PATH.exists():
        raise FileNotFoundError(RAW_PATH)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    initial_hash = sha256_file(RAW_PATH)
    file_size = RAW_PATH.stat().st_size
    sample = read_sample_bytes(RAW_PATH)
    encoding_info = detect_encoding(sample)
    encoding = str(encoding_info["encoding"])
    sample_lines = split_sample_lines(sample, encoding)
    header_index, separator, columns, delimiter_counts = detect_header_and_separator(sample_lines)

    newline_count = count_newlines(RAW_PATH)
    approx_data_lines = max(0, newline_count - header_index - 1)

    lf_inferred = pl.scan_csv(
        RAW_PATH,
        separator=separator,
        has_header=True,
        skip_rows=header_index,
        quote_char='"',
        encoding="utf8-lossy",
        infer_schema_length=20_000,
        ignore_errors=True,
        null_values=["", "NULL", "null", "NA", "N/A"],
    )
    inferred_schema = lf_inferred.collect_schema()

    string_schema = {column: pl.String for column in columns}
    lf = pl.scan_csv(
        RAW_PATH,
        separator=separator,
        has_header=True,
        skip_rows=header_index,
        quote_char='"',
        encoding="utf8-lossy",
        schema_overrides=string_schema,
        ignore_errors=True,
        null_values=[],
    )

    row_count = int(safe_collect(lf.select(pl.len().alias("rows")))["rows"][0])
    first_rows = pl.read_csv(
        RAW_PATH,
        separator=separator,
        has_header=True,
        skip_rows=header_index,
        quote_char='"',
        encoding="utf8-lossy",
        schema_overrides=string_schema,
        n_rows=5,
    )

    missing_exprs = []
    incomplete_condition = None
    replacement_exprs = []
    for column in columns:
        cleaned = pl.col(column).str.strip_chars()
        missing = pl.col(column).is_null() | (cleaned == "")
        missing_exprs.extend(
            [
                missing.sum().alias(f"{column}__missing"),
                (pl.len() - missing.sum()).alias(f"{column}__non_missing"),
            ]
        )
        incomplete_condition = missing if incomplete_condition is None else incomplete_condition | missing
        replacement_exprs.append(pl.col(column).str.contains("\uFFFD", literal=True).sum().alias(column))

    missing_frame = safe_collect(lf.select(missing_exprs))
    missing_rows = []
    for column in columns:
        missing_count = int(missing_frame[f"{column}__missing"][0])
        non_missing = int(missing_frame[f"{column}__non_missing"][0])
        missing_rows.append(
            {
                "coluna": column,
                "ausentes": missing_count,
                "nao_ausentes": non_missing,
                "pct_ausente": round((missing_count / row_count) * 100, 4) if row_count else 0,
            }
        )

    incomplete_rows = int(safe_collect(lf.select(incomplete_condition.sum().alias("rows")))["rows"][0])
    replacement_counts = safe_collect(lf.select(replacement_exprs)).to_dicts()[0]
    replacement_total = sum(int(value or 0) for value in replacement_counts.values())

    year_cols = exact_or_contains(columns, "ANO", "ANO")
    month_cols = exact_or_contains(columns, "MES", "MES")
    company_cols = find_columns(columns, "EMPRESA")
    origin_cols = find_columns(columns, "AEROPORTO", "ORIGEM")
    dest_cols = find_columns(columns, "AEROPORTO", "DESTINO")

    year_summary = {}
    if year_cols:
        year_col = year_cols[0]
        year_stats = safe_collect(
            lf.select(
                pl.col(year_col).str.strip_chars().cast(pl.Int64, strict=False).min().alias("min"),
                pl.col(year_col).str.strip_chars().cast(pl.Int64, strict=False).max().alias("max"),
            )
        )
        year_summary = {"coluna": year_col, "min": year_stats["min"][0], "max": year_stats["max"][0]}

    month_values = []
    if month_cols:
        month_values = get_distinct_values(lf, month_cols[0], limit=100)
        month_values = sorted(month_values, key=lambda item: int(item) if item.isdigit() else math.inf)

    company_sigla_cols = [col for col in company_cols if "SIGLA" in norm_name(col)]
    company_name_cols = [col for col in company_cols if "NOME" in norm_name(col)]
    origin_sigla_cols = [col for col in origin_cols if "SIGLA" in norm_name(col)]
    dest_sigla_cols = [col for col in dest_cols if "SIGLA" in norm_name(col)]
    origin_name_cols = [col for col in origin_cols if "NOME" in norm_name(col)]
    dest_name_cols = [col for col in dest_cols if "NOME" in norm_name(col)]

    distinct_counts = {}
    for label, candidates in {
        "empresas": company_sigla_cols or company_name_cols,
        "aeroportos_origem": origin_sigla_cols or origin_name_cols,
        "aeroportos_destino": dest_sigla_cols or dest_name_cols,
    }.items():
        if candidates:
            col = candidates[0]
            value = safe_collect(
                lf.select(
                    pl.col(col)
                    .str.strip_chars()
                    .filter(pl.col(col).str.strip_chars() != "")
                    .n_unique()
                    .alias("n")
                )
            )["n"][0]
            distinct_counts[label] = {"coluna": col, "quantidade": int(value)}

    nature_group_candidates = []
    for column in columns:
        normalized = norm_name(column)
        if (
            "NATUREZA" in normalized
            or ("GRUPO" in normalized and ("VOO" in normalized or "OPERACAO" in normalized))
            or ("TIPO" in normalized and ("VOO" in normalized or "OPERACAO" in normalized))
        ):
            nature_group_candidates.append(column)

    nature_group_values = {
        column: get_distinct_values(lf, column, limit=1_000) for column in nature_group_candidates
    }

    related_columns = {
        "passageiros_pagos": find_columns(columns, "PASSAGEIROS", "PAGOS"),
        "assentos": exact_or_contains(columns, "ASSENTOS", "ASSENTOS"),
        "decolagens": exact_or_contains(columns, "DECOLAGENS", "DECOLAGENS"),
        "ask": exact_or_contains(columns, "ASK", "ASK"),
        "rpk": exact_or_contains(columns, "RPK", "RPK"),
        "empresa_aerea": company_cols,
        "aeroporto_origem": origin_cols,
        "aeroporto_destino": dest_cols,
        "ano": year_cols,
        "mes": month_cols,
    }

    numeric_profile = []
    numeric_exprs = []
    for column in columns:
        cleaned = pl.col(column).str.strip_chars()
        normalized_number = (
            pl.when(cleaned.str.contains(",", literal=True))
            .then(cleaned.str.replace_all(r"\.", "").str.replace(",", ".", literal=True))
            .otherwise(cleaned)
        )
        parsed = normalized_number.cast(pl.Float64, strict=False)
        non_missing = (cleaned.is_not_null() & (cleaned != "")).sum().alias(f"{column}__non_missing")
        numeric_exprs.extend(
            [
                non_missing,
                parsed.is_not_null().sum().alias(f"{column}__parsed"),
                (parsed < 0).sum().alias(f"{column}__negative"),
                parsed.min().alias(f"{column}__min"),
                parsed.max().alias(f"{column}__max"),
            ]
        )

    numeric_frame = safe_collect(lf.select(numeric_exprs)).to_dicts()[0]
    for column in columns:
        non_missing = int(numeric_frame[f"{column}__non_missing"] or 0)
        parsed = int(numeric_frame[f"{column}__parsed"] or 0)
        ratio = parsed / non_missing if non_missing else 0
        if parsed > 0 and (ratio >= 0.8 or int(numeric_frame[f"{column}__negative"] or 0) > 0):
            numeric_profile.append(
                {
                    "coluna": column,
                    "tipo_inferido": str(inferred_schema.get(column)),
                    "nao_ausentes": non_missing,
                    "parseaveis_como_numero": parsed,
                    "pct_parseavel": round(ratio * 100, 4),
                    "negativos": int(numeric_frame[f"{column}__negative"] or 0),
                    "min_parseado": numeric_frame[f"{column}__min"],
                    "max_parseado": numeric_frame[f"{column}__max"],
                }
            )

    numeric_text = [
        row
        for row in numeric_profile
        if row["pct_parseavel"] >= 95 and "String" in row["tipo_inferido"]
    ]

    decimal_markers = {}
    for column in [row["coluna"] for row in numeric_profile]:
        counts = safe_collect(
            lf.select(
                pl.col(column).str.contains(",", literal=True).sum().alias("com_virgula"),
                pl.col(column).str.contains(r"\.").sum().alias("com_ponto"),
            )
        )
        decimal_markers[column] = {
            "com_virgula": int(counts["com_virgula"][0] or 0),
            "com_ponto": int(counts["com_ponto"][0] or 0),
        }

    row_hash_frame = safe_collect(lf.select(pl.struct(columns).hash().alias("row_hash")).select(pl.len().alias("rows"), pl.col("row_hash").n_unique().alias("unique_hashes")))
    duplicate_estimate = int(row_hash_frame["rows"][0] - row_hash_frame["unique_hashes"][0])

    def inconsistency_by_pair(key_col: str | None, value_col: str | None, limit: int = 20) -> list[dict[str, object]]:
        if not key_col or not value_col:
            return []
        frame = safe_collect(
            lf.filter((pl.col(key_col).str.strip_chars() != "") & (pl.col(value_col).str.strip_chars() != ""))
            .group_by(pl.col(key_col).str.strip_chars().alias(key_col))
            .agg(
                pl.col(value_col).str.strip_chars().n_unique().alias("nomes_distintos"),
                pl.col(value_col).str.strip_chars().unique().sort().implode().alias("exemplos"),
            )
            .filter(pl.col("nomes_distintos") > 1)
            .sort("nomes_distintos", descending=True)
            .limit(limit)
        )
        rows = frame.to_dicts()
        for row in rows:
            exemplos = row.get("exemplos")
            if isinstance(exemplos, list):
                row["exemplos"] = "; ".join(str(item) for item in exemplos[:8])
        return rows

    airport_origin_incons = inconsistency_by_pair(
        origin_sigla_cols[0] if origin_sigla_cols else None,
        origin_name_cols[0] if origin_name_cols else None,
    )
    airport_dest_incons = inconsistency_by_pair(
        dest_sigla_cols[0] if dest_sigla_cols else None,
        dest_name_cols[0] if dest_name_cols else None,
    )
    company_incons = inconsistency_by_pair(
        company_sigla_cols[0] if company_sigla_cols else None,
        company_name_cols[0] if company_name_cols else None,
    )

    generated_at = datetime.now().isoformat(timespec="seconds")
    final_hash = sha256_file(RAW_PATH)

    first_rows_records = first_rows.to_dicts()
    dtype_rows = [{"coluna": col, "tipo_inferido_polars": str(dtype)} for col, dtype in inferred_schema.items()]
    column_rows = [{"ordem": index + 1, "coluna": column} for index, column in enumerate(columns)]
    related_rows = [
        {"variavel": key, "colunas_reais_localizadas": ", ".join(value) if value else "_nao localizada_"}
        for key, value in related_columns.items()
    ]
    marker_rows = [
        {"coluna": column, **counts} for column, counts in decimal_markers.items() if counts["com_virgula"] or counts["com_ponto"]
    ]

    summary = {
        "arquivo": str(RAW_PATH.relative_to(ROOT)),
        "tamanho_bytes": file_size,
        "linhas_dados": row_count,
        "colunas": len(columns),
        "encoding": encoding_info,
        "separador": separator,
        "hash_sha256_inicial": initial_hash,
        "hash_sha256_final": final_hash,
        "hash_preservado": initial_hash == final_hash,
    }

    report = f"""# Auditoria exploratoria do dataset ANAC

Gerado em: `{generated_at}`

Arquivo auditado: `{RAW_PATH.relative_to(ROOT)}`

## Sumario executivo

- O arquivo original nao foi alterado durante a auditoria: `{initial_hash == final_hash}`.
- Tamanho: `{file_size}` bytes ({fmt_bytes(file_size)}).
- Encoding detectado: `{encoding}` ({encoding_info["source"]}, confianca `{encoding_info["confidence"]}`).
- Separador detectado: `{separator}`.
- Linha de cabecalho real: `{header_index + 1}`; existem `{header_index}` linha(s) de metadados antes do cabecalho.
- Quantidade de colunas: `{len(columns)}`.
- Quantidade exata de linhas de dados via Polars: `{row_count}`.
- Estimativa por contagem de quebras de linha: `{approx_data_lines}`.
- Duplicidades estimadas por hash da linha completa: `{duplicate_estimate}`.
- Linhas com pelo menos um campo ausente/vazio: `{incomplete_rows}`.
- Caracter de substituicao Unicode (`�`) encontrado: `{replacement_total}` ocorrencia(s).

## Deteccao automatica

```json
{json.dumps(summary, ensure_ascii=False, indent=2)}
```

Contagem de separadores na linha de cabecalho candidata:

```json
{json.dumps(delimiter_counts, ensure_ascii=False, indent=2)}
```

## Colunas reais

{md_table(column_rows, ["ordem", "coluna"])}

## Tipos inferidos pelo Polars

{md_table(dtype_rows, ["coluna", "tipo_inferido_polars"])}

## Primeiras 5 linhas

{md_table(first_rows_records, columns)}

## Valores ausentes por coluna

{md_table(missing_rows, ["coluna", "ausentes", "nao_ausentes", "pct_ausente"])}

## Periodo, empresas e aeroportos

- Ano: coluna `{year_summary.get("coluna", "_nao localizada_")}`, menor `{year_summary.get("min", "_na_")}`, maior `{year_summary.get("max", "_na_")}`.
- Meses disponiveis pela coluna `{month_cols[0] if month_cols else "_nao localizada_"}`: `{", ".join(month_values)}`.
- Empresas: `{distinct_counts.get("empresas", {}).get("quantidade", "_na_")}` valores distintos em `{distinct_counts.get("empresas", {}).get("coluna", "_nao localizada_")}`.
- Aeroportos de origem: `{distinct_counts.get("aeroportos_origem", {}).get("quantidade", "_na_")}` valores distintos em `{distinct_counts.get("aeroportos_origem", {}).get("coluna", "_nao localizada_")}`.
- Aeroportos de destino: `{distinct_counts.get("aeroportos_destino", {}).get("quantidade", "_na_")}` valores distintos em `{distinct_counts.get("aeroportos_destino", {}).get("coluna", "_nao localizada_")}`.

## Variaveis localizadas para metricas e dimensoes solicitadas

{md_table(related_rows, ["variavel", "colunas_reais_localizadas"])}

## Natureza da operacao e grupo/tipo de voo

Colunas candidatas identificadas sem presumir nomes: `{", ".join(nature_group_candidates) if nature_group_candidates else "_nenhuma_"}`.

"""

    for column, values in nature_group_values.items():
        report += f"### `{column}`\n\n"
        report += "\n".join(f"- `{value}`" for value in values) if values else "_Sem valores nao vazios._"
        report += "\n\n"

    report += f"""## Perfil numerico e problemas potenciais

Colunas com valores parseaveis como numero (normalizando virgula decimal quando presente):

{md_table(numeric_profile, ["coluna", "tipo_inferido", "nao_ausentes", "parseaveis_como_numero", "pct_parseavel", "negativos", "min_parseado", "max_parseado"])}

Colunas possivelmente numericas armazenadas como texto:

{md_table(numeric_text, ["coluna", "tipo_inferido", "nao_ausentes", "parseaveis_como_numero", "pct_parseavel"])}

Sinais de separador decimal/milhar nas colunas numericas:

{md_table(marker_rows, ["coluna", "com_virgula", "com_ponto"])}

## Inconsistencias de nomenclatura

### Aeroportos de origem: mesma sigla com mais de um nome

{md_table(airport_origin_incons, [origin_sigla_cols[0] if origin_sigla_cols else "sigla", "nomes_distintos", "exemplos"])}

### Aeroportos de destino: mesma sigla com mais de um nome

{md_table(airport_dest_incons, [dest_sigla_cols[0] if dest_sigla_cols else "sigla", "nomes_distintos", "exemplos"])}

### Empresas: mesma sigla com mais de um nome

{md_table(company_incons, [company_sigla_cols[0] if company_sigla_cols else "sigla", "nomes_distintos", "exemplos"])}

## Observacoes de qualidade

- Numeros armazenados como texto: ver secao "Colunas possivelmente numericas armazenadas como texto".
- Separador decimal: a auditoria contou ocorrencias de virgula e ponto nas colunas numericas. Campos sem ocorrencias aparentam inteiros; campos com virgula devem ser tratados com normalizacao explicita.
- Caracteres especiais: o arquivo foi lido como UTF-8 com BOM; nao foram detectados caracteres de substituicao se o total acima for zero.
- Duplicidades: `{duplicate_estimate}` linha(s) potencialmente duplicada(s), estimadas por hash da linha completa.
- Valores negativos: ver coluna `negativos` no perfil numerico.
- Linhas incompletas: `{incomplete_rows}` linha(s) com pelo menos um campo ausente ou vazio.
- Valores nulos/vazios: detalhados por coluna na tabela de ausentes.
- Nomenclatura de aeroportos e companhias: inconsistencias potenciais listadas nas tabelas acima.

## Reprodutibilidade

Comando usado:

```powershell
python scripts/auditar_dataset.py
```

Verificacoes executadas automaticamente:

- SHA-256 antes da auditoria: `{initial_hash}`
- SHA-256 depois da auditoria: `{final_hash}`
- Arquivo preservado: `{initial_hash == final_hash}`
- Contagem exata via Polars comparada com estimativa por quebras de linha.
"""

    REPORT_PATH.write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Relatorio escrito em: {REPORT_PATH}")


if __name__ == "__main__":
    main()

