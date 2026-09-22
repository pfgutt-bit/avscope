from datetime import date
import unittest

import polars as pl

from src.discovery import csv_bytes, discover_markets, filter_markets, label_markets
from src.metrics import MVP_PATH, market_hhi, basic_metrics


def fixture() -> pl.DataFrame:
    rows = []
    for year, factor in [(2025, 1), (2026, 2)]:
        for month in [1, 2]:
            for company, passengers in [("A", 60), ("B", 40)]:
                rows.append({
                    "ANO": year, "MES": month, "PERIODO": date(year, month, 1),
                    "ROTA_DIRECIONAL": "AAAA>BBBB", "EMPRESA_ID": company,
                    "AEROPORTO_DE_ORIGEM_SIGLA": "AAAA", "AEROPORTO_DE_DESTINO_SIGLA": "BBBB",
                    "PASSAGEIROS_PAGOS": passengers * factor, "ASSENTOS": 100 * factor,
                    "DECOLAGENS": 1, "RPK": passengers * factor * 100, "ASK": 10000 * factor,
                    "FLAG_RPK_MAIOR_ASK": False,
                })
    return pl.DataFrame(rows)


class DiscoveryTests(unittest.TestCase):
    def test_same_months_weighted_ratio_and_concentration(self):
        row = discover_markets(fixture(), 2026, 2).row(0, named=True)
        self.assertEqual(row["PASSAGEIROS_PAGOS"], 400)
        self.assertEqual(row["CRESCIMENTO_PCT"], 100)
        self.assertEqual(row["LOAD_FACTOR_PCT"], 50)
        self.assertEqual(row["HHI"], 5200)
        self.assertEqual(row["COMPANHIAS_COM_PASSAGEIROS"], 2)

    def test_missing_month_never_becomes_zero_growth(self):
        data = fixture().filter(~((pl.col("ANO") == 2025) & (pl.col("MES") == 2)))
        row = discover_markets(data, 2026, 2).row(0, named=True)
        self.assertIsNone(row["CRESCIMENTO_PCT"])
        self.assertEqual(row["COMPARABILIDADE"], "Meses sem registro")

    def test_zero_and_absent_prior_base_are_distinct(self):
        zero = fixture().with_columns(pl.when(pl.col("ANO") == 2025).then(0).otherwise(pl.col("PASSAGEIROS_PAGOS")).alias("PASSAGEIROS_PAGOS"))
        self.assertEqual(discover_markets(zero, 2026, 2)["COMPARABILIDADE"][0], "Base anterior zerada")
        absent = fixture().filter(pl.col("ANO") == 2026)
        self.assertEqual(discover_markets(absent, 2026, 2)["COMPARABILIDADE"][0], "Sem base anterior")

    def test_null_passengers_suppress_growth_and_all_null_hhi(self):
        data = fixture().with_columns(pl.when(pl.col("ANO") == 2026).then(None).otherwise(pl.col("PASSAGEIROS_PAGOS")).alias("PASSAGEIROS_PAGOS"))
        row = discover_markets(data, 2026, 2).row(0, named=True)
        self.assertIsNone(row["PASSAGEIROS_PAGOS"])
        self.assertIsNone(row["HHI"])
        self.assertIsNone(row["CRESCIMENTO_PCT"])

    def test_direction_and_quality_are_not_combined(self):
        data = fixture()
        reverse = data.with_columns(pl.lit("BBBB>AAAA").alias("ROTA_DIRECIONAL"),
                                    pl.lit("BBBB").alias("AEROPORTO_DE_ORIGEM_SIGLA"),
                                    pl.lit("AAAA").alias("AEROPORTO_DE_DESTINO_SIGLA"),
                                    pl.lit(True).alias("FLAG_RPK_MAIOR_ASK"))
        result = discover_markets(pl.concat([data, reverse]), 2026, 2)
        self.assertEqual(result.height, 2)
        self.assertEqual(result["REGISTROS_SINALIZADOS"].sum(), 4)

    def test_filters_fallback_and_empty_results(self):
        airports = pl.DataFrame({"ICAO": ["AAAA", "BBBB"], "IATA": [None, "BBB"],
                                 "MUNICIPIO": ["ALFA", "BETA"], "NOME_AEROPORTO": ["Alfa", "Beta"], "UF": ["PA", "SP"]})
        catalog = label_markets(discover_markets(fixture(), 2026, 2), airports)
        self.assertEqual(catalog["ROTA"][0], "AAAA → BBB")
        self.assertEqual(filter_markets(catalog, origin_uf="SP").height, 0)
        self.assertEqual(filter_markets(catalog, destination_uf="SP", comparable_only=True).height, 1)
        self.assertEqual(filter_markets(catalog, max_companies=1).height, 0)

    def test_unavailable_month_is_rejected(self):
        with self.assertRaises(ValueError):
            discover_markets(fixture(), 2026, 12)

    def test_csv_preserves_nulls_accents_and_escapes_formula_text(self):
        payload = csv_bytes(pl.DataFrame({"Nome": ["Belém", "=1+1"], "Valor": [1.5, None]}))
        self.assertTrue(payload.startswith(b"\xef\xbb\xbf"))
        text = payload.decode("utf-8-sig")
        self.assertIn("Belém;1,5", text)
        self.assertIn("'=1+1", text)


@unittest.skipUnless(MVP_PATH.exists(), "Base do produto ausente")
class DiscoveryIntegrationTests(unittest.TestCase):
    def test_catalog_reconciles_with_official_metrics(self):
        data = pl.read_parquet(MVP_PATH)
        result = discover_markets(data, 2025, 12)
        route = result.filter(pl.col("ROTA_DIRECIONAL") == "SBSP>SBRJ").row(0, named=True)
        source = data.filter((pl.col("ANO") == 2025) & (pl.col("ROTA_DIRECIONAL") == "SBSP>SBRJ"))
        self.assertAlmostEqual(route["HHI"], market_hhi(source), places=8)
        self.assertEqual(route["PASSAGEIROS_PAGOS"], basic_metrics(source)["PASSAGEIROS_PAGOS"])
        self.assertEqual(result["PASSAGEIROS_PAGOS"].sum(), data.filter(pl.col("ANO") == 2025)["PASSAGEIROS_PAGOS"].sum())


if __name__ == "__main__":
    unittest.main()

