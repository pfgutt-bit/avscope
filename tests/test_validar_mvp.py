from __future__ import annotations

import unittest

import polars as pl

from scripts.validar_mvp import add_validation_flags, geography_expression, safe_ratio


class ValidateMvpTests(unittest.TestCase):
    def test_geography_classification(self) -> None:
        frame = pl.DataFrame(
            {
                "AEROPORTO_DE_ORIGEM_PAIS": ["BRASIL", "BRASIL", "FRANÇA"],
                "AEROPORTO_DE_DESTINO_PAIS": ["BRASIL", "FRANÇA", "ALEMANHA"],
            }
        ).with_columns(geography_expression())
        self.assertEqual(
            frame["ESCOPO_GEOGRAFICO"].to_list(),
            ["DOMESTICA_BRASILEIRA", "INTERNACIONAL_ENVOLVE_BRASIL", "DEMAIS_CASOS"],
        )

    def test_safe_ratio_preserves_invalid_denominator_as_null(self) -> None:
        frame = pl.DataFrame({"RPK": [80, 10, None], "ASK": [100, 0, 100]}).with_columns(
            safe_ratio("RPK", "ASK", 100.0, "LF")
        )
        self.assertEqual(frame["LF"].to_list(), [80.0, None, None])

    def test_history_keeps_zero_month_on_known_passenger_route(self) -> None:
        frame = pl.DataFrame(
            {
                "ROTA_DIRECIONAL": ["SBBE>SBGR", "SBBE>SBGR"],
                "EMPRESA_ID": ["TST|TESTE", "TST|TESTE"],
                "GRUPO_DE_VOO": ["REGULAR", "REGULAR"],
                "FLAG_EVIDENCIA_TRANSPORTE_PASSAGEIROS": [True, False],
                "AEROPORTO_DE_ORIGEM_SIGLA": ["SBBE", "SBBE"],
                "AEROPORTO_DE_DESTINO_SIGLA": ["SBGR", "SBGR"],
                "AEROPORTO_DE_ORIGEM_PAIS": ["BRASIL", "BRASIL"],
                "AEROPORTO_DE_DESTINO_PAIS": ["BRASIL", "BRASIL"],
                "NATUREZA": ["DOMÉSTICA", "DOMÉSTICA"],
            }
        )
        result = add_validation_flags(frame.lazy()).collect()
        self.assertEqual(result["FLAG_UNIVERSO_MVP_RECOMENDADO"].to_list(), [True, True])


if __name__ == "__main__":
    unittest.main()

