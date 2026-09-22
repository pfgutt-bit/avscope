from __future__ import annotations

import unittest
from datetime import date

import polars as pl

from src.app_data import (
    DEFAULT_ROUTE,
    airport_display,
    build_analysis,
    default_period_start,
    destinations_for,
    has_operations,
    resolve_company,
    resolve_period_state,
    resolve_route_state,
    reverse_route,
)
from src.formatters import (
    format_compact,
    format_integer,
    format_month,
    format_percent,
)
from src.metrics import MVP_PATH


class AppStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.routes = {("SBBE", "SBGR"), ("SBGR", "SBBE"), ("SBBE", "SBEG")}

    def test_origin_filters_destinations(self) -> None:
        self.assertEqual(destinations_for("SBBE", self.routes), ["SBEG", "SBGR"])

    def test_reverse_route(self) -> None:
        state, changed = reverse_route("SBBE", "SBGR", self.routes)
        self.assertTrue(changed)
        self.assertEqual((state.origin, state.destination), ("SBGR", "SBBE"))
        unchanged, changed = reverse_route("SBBE", "SBEG", self.routes)
        self.assertFalse(changed)
        self.assertEqual((unchanged.origin, unchanged.destination), ("SBBE", "SBEG"))

    def test_valid_and_invalid_query_routes(self) -> None:
        valid = resolve_route_state(
            {"origin": "SBGR", "destination": "SBBE"}, self.routes
        )
        self.assertEqual((valid.origin, valid.destination), ("SBGR", "SBBE"))
        invalid = resolve_route_state(
            {"origin": "XXXX", "destination": "YYYY"}, self.routes
        )
        self.assertEqual((invalid.origin, invalid.destination), DEFAULT_ROUTE)

    def test_period_query_and_dynamic_five_year_default(self) -> None:
        periods = [date(2021, 8, 1), date(2021, 9, 1), date(2026, 7, 1)]
        valid = resolve_period_state(
            {"start": "2021-09-01", "end": "2026-07-01"}, periods
        )
        self.assertEqual(valid.start, date(2021, 9, 1))
        invalid = resolve_period_state(
            {"start": "bad", "end": "2026-07-01"}, periods
        )
        self.assertEqual(invalid.end, date(2026, 7, 1))
        long_periods = [date(2021 + (month - 1) // 12, (month - 1) % 12 + 1, 1) for month in range(1, 68)]
        self.assertEqual(default_period_start(long_periods), long_periods[-60])

    def test_company_query_fallback(self) -> None:
        ids = {"GLO|GOL", "TAM|TAM"}
        self.assertEqual(resolve_company({"company": "GLO|GOL"}, ids), "GLO|GOL")
        self.assertIsNone(resolve_company({"company": "INVALID"}, ids))

    def test_airport_falls_back_to_icao(self) -> None:
        lookup = {"SBBE": {"IATA": "BEL", "MUNICIPIO": "BELÉM"}, "SBXX": {"IATA": None, "MUNICIPIO": "TESTE"}}
        self.assertEqual(airport_display("SBBE", lookup), "BEL · Belém")
        self.assertEqual(airport_display("SBXX", lookup), "SBXX · Teste")

    def test_empty_state_predicate(self) -> None:
        self.assertFalse(has_operations(pl.DataFrame()))
        self.assertTrue(has_operations(pl.DataFrame({"x": [1]})))

    def test_brazilian_formatters(self) -> None:
        self.assertEqual(format_integer(1_234_567), "1.234.567")
        self.assertEqual(format_compact(1_245_310), "1,25 mi")
        self.assertEqual(format_compact(8_430), "8,43 mil")
        self.assertEqual(format_percent(85.5792), "85,6%")
        self.assertEqual(format_month(date(2026, 7, 1)), "jul/2026")


@unittest.skipUnless(MVP_PATH.exists(), "Etapa 4 ainda nao executada.")
class AppRealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = pl.read_parquet(MVP_PATH)

    def test_company_filter_keeps_total_market_denominator(self) -> None:
        all_companies = build_analysis(
            self.data, "SBSP", "SBRJ", date(2025, 1, 1), date(2025, 12, 1), None
        )
        gol_id = (
            all_companies["shares"]
            .filter(pl.col("EMPRESA_SIGLA") == "GLO")["EMPRESA_ID"][0]
        )
        gol_view = build_analysis(
            self.data, "SBSP", "SBRJ", date(2025, 1, 1), date(2025, 12, 1), gol_id
        )
        total_share = all_companies["shares"].filter(pl.col("EMPRESA_ID") == gol_id)["MARKET_SHARE_PCT"][0]
        filtered_share = gol_view["shares"].filter(pl.col("EMPRESA_ID") == gol_id)["MARKET_SHARE_PCT"][0]
        self.assertAlmostEqual(total_share, 45.8359, places=4)
        self.assertAlmostEqual(filtered_share, total_share, places=10)
        self.assertNotEqual(filtered_share, 100.0)
        self.assertEqual(gol_view["summary"]["NUMERO_COMPANHIAS"], 1)

    def test_partial_2026_stays_ytd(self) -> None:
        analysis = build_analysis(
            self.data, "SBBE", "SBGR", date(2021, 8, 1), date(2026, 7, 1), None
        )
        self.assertEqual(analysis["comparison"]["TIPO_COMPARACAO"], "YTD")
        self.assertEqual(analysis["comparison"]["MES_FINAL"], 7)

    def test_short_period_hides_non_contextual_delta(self) -> None:
        analysis = build_analysis(
            self.data, "SBSP", "SBRJ", date(2025, 1, 1), date(2025, 7, 1), None
        )
        self.assertIsNone(analysis["comparison"]["CRESCIMENTO_PCT"])

    def test_historical_company_without_final_year_does_not_crash(self) -> None:
        historical = self.data.group_by("ROTA_DIRECIONAL", "EMPRESA_ID").agg(
            pl.col("ANO").max().alias("LAST_YEAR")
        ).filter(pl.col("LAST_YEAR") < 2020).sort("ROTA_DIRECIONAL", "EMPRESA_ID").row(0, named=True)
        origin, destination = historical["ROTA_DIRECIONAL"].split(">")
        result = build_analysis(self.data, origin, destination, date(2000, 1, 1), date(2026, 7, 1), historical["EMPRESA_ID"])
        self.assertIsNone(result["comparison"]["CRESCIMENTO_PCT"])
        self.assertGreater(result["summary"]["REGISTROS"], 0)

    def test_month_missing_from_source_is_a_gap_not_zero(self) -> None:
        data = self.data.filter(pl.col("PERIODO") != date(2025, 2, 1))
        result = build_analysis(data, "SBBE", "SBGR", date(2025, 1, 1), date(2025, 3, 1), None)
        self.assertEqual(result["series"].height, 3)
        self.assertIsNone(result["series"].filter(pl.col("PERIODO") == date(2025, 2, 1))["PASSAGEIROS_PAGOS"][0])


if __name__ == "__main__":
    unittest.main()

