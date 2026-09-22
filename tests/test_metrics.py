from __future__ import annotations

import unittest
from datetime import date

import polars as pl

from src.metrics import (
    MVP_PATH,
    annual_comparison,
    available_companies,
    available_destinations,
    basic_metrics,
    calculate_load_factor,
    calculate_passengers_per_departure,
    growth_percent,
    hhi_from_shares,
    market_hhi,
    market_share_by_company,
    monthly_route_series,
    period_coverage,
)


class MetricFormulaTests(unittest.TestCase):
    def test_ratios_and_growth(self) -> None:
        self.assertAlmostEqual(calculate_load_factor(80, 100), 80.0)
        self.assertAlmostEqual(calculate_load_factor(120, 100), 120.0)
        self.assertAlmostEqual(calculate_passengers_per_departure(320, 2), 160.0)
        self.assertAlmostEqual(growth_percent(110, 100), 10.0)

    def test_zero_and_null_are_safe(self) -> None:
        self.assertIsNone(calculate_load_factor(10, 0))
        self.assertIsNone(calculate_load_factor(None, 100))
        self.assertIsNone(calculate_passengers_per_departure(10, 0))
        self.assertIsNone(calculate_passengers_per_departure(None, 2))
        self.assertIsNone(growth_percent(10, 0))
        self.assertIsNone(growth_percent(None, 10))

    def test_hhi_uses_percentage_scale(self) -> None:
        self.assertEqual(hhi_from_shares([50.0, 30.0, 20.0]), 3800.0)
        self.assertIsNone(hhi_from_shares([None]))

    def test_all_null_aggregation_stays_null(self) -> None:
        frame = pl.DataFrame(
            {
                "PASSAGEIROS_PAGOS": [None, None], "ASSENTOS": [None, None],
                "DECOLAGENS": [None, None], "ASK": [None, None], "RPK": [None, None],
                "EMPRESA_ID": ["A", "A"], "ROTA_DIRECIONAL": ["X>Y", "X>Y"],
            },
            schema_overrides={name: pl.Int64 for name in ["PASSAGEIROS_PAGOS", "ASSENTOS", "DECOLAGENS", "ASK", "RPK"]},
        )
        result = basic_metrics(frame)
        self.assertIsNone(result["PASSAGEIROS_PAGOS"])
        self.assertIsNone(result["LOAD_FACTOR_PCT"])


@unittest.skipUnless(MVP_PATH.exists(), "Execute scripts/build_stage4.py antes dos testes reais.")
class RealMvpMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = pl.scan_parquet(MVP_PATH)

    def test_bel_gru_july_2026_reference(self) -> None:
        series = monthly_route_series("SBBE", "SBGR", "2026-07-01", "2026-07-01", data=self.data)
        self.assertEqual(series.height, 1)
        row = series.row(0, named=True)
        exact_period = basic_metrics(
            self.data,
            origin_icao="SBBE",
            destination_icao="SBGR",
            period=date(2026, 7, 1),
        )
        self.assertEqual(exact_period["PASSAGEIROS_PAGOS"], row["PASSAGEIROS_PAGOS"])
        self.assertAlmostEqual(row["LOAD_FACTOR_PCT"], 85.5792, places=4)
        self.assertAlmostEqual(
            calculate_passengers_per_departure(row["PASSAGEIROS_PAGOS"], row["DECOLAGENS"]),
            160.1783,
            places=4,
        )

    def test_cgh_sdu_2025_market_share_and_hhi(self) -> None:
        shares = market_share_by_company(
            self.data, origin_icao="SBSP", destination_icao="SBRJ", start="2025-01-01", end="2025-12-01"
        )
        by_sigla = dict(zip(shares["EMPRESA_SIGLA"].to_list(), shares["MARKET_SHARE_PCT"].to_list()))
        self.assertAlmostEqual(sum(value for value in by_sigla.values() if value is not None), 100.0, places=8)
        self.assertAlmostEqual(by_sigla["GLO"], 45.8359, places=4)
        self.assertAlmostEqual(by_sigla["TAM"], 39.3442, places=4)
        self.assertAlmostEqual(by_sigla["AZU"], 14.8198, places=4)
        self.assertAlmostEqual(
            market_hhi(self.data, origin_icao="SBSP", destination_icao="SBRJ", start="2025-01-01", end="2025-12-01"),
            3868.5283,
            places=4,
        )

    def test_ytd_uses_equivalent_months(self) -> None:
        coverage = period_coverage(self.data)
        self.assertEqual(coverage["ULTIMO_ANO"], 2026)
        self.assertEqual(coverage["ULTIMO_MES"], 7)
        self.assertFalse(coverage["ULTIMO_ANO_COMPLETO"])
        result = annual_comparison(self.data)
        self.assertEqual(result["TIPO_COMPARACAO"], "YTD")
        self.assertEqual(result["MES_FINAL"], 7)
        self.assertEqual(result["VALOR_ANTERIOR"], 55_664_808)
        self.assertEqual(result["VALOR_ATUAL"], 58_343_401)
        self.assertAlmostEqual(result["CRESCIMENTO_PCT"], 4.8120, places=4)

    def test_directional_routes_remain_separate(self) -> None:
        forward = basic_metrics(self.data, origin_icao="SBBE", destination_icao="SBGR")
        reverse = basic_metrics(self.data, origin_icao="SBGR", destination_icao="SBBE")
        self.assertEqual(forward["NUMERO_ROTAS"], 1)
        self.assertEqual(reverse["NUMERO_ROTAS"], 1)
        self.assertNotEqual(forward["PASSAGEIROS_PAGOS"], reverse["PASSAGEIROS_PAGOS"])

    def test_origin_destination_and_company_filters(self) -> None:
        destinations = available_destinations("SBBE", self.data)
        self.assertIn("SBGR", destinations)
        companies = available_companies("SBBE", "SBGR", self.data)
        self.assertIn("EMPRESA_ID", companies.columns)
        company_id = companies["EMPRESA_ID"][0]
        filtered = monthly_route_series("SBBE", "SBGR", company_id=company_id, data=self.data)
        self.assertGreater(filtered.height, 0)
        expected = basic_metrics(self.data, origin_icao="SBBE", destination_icao="SBGR", company_id=company_id)
        self.assertEqual(filtered["PASSAGEIROS_PAGOS"].sum(), expected["PASSAGEIROS_PAGOS"])


if __name__ == "__main__":
    unittest.main()

