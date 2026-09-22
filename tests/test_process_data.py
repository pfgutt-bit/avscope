from __future__ import annotations

import unittest

import polars as pl

from src.process_data import aggregate_routes, parse_decimal_comma, prepare_source


def source_frame(rows: list[dict[str, object]]) -> pl.LazyFrame:
    defaults = {
        "LINHA_DADOS": "1",
        "EMPRESA_SIGLA": "TST",
        "EMPRESA_NOME": "EMPRESA TESTE",
        "EMPRESA_NACIONALIDADE": "BRASILEIRA",
        "ANO": "2024",
        "MES": "1",
        "AEROPORTO_DE_ORIGEM_SIGLA": "SBBE",
        "AEROPORTO_DE_ORIGEM_NOME": "BELEM",
        "AEROPORTO_DE_ORIGEM_UF": "PA",
        "AEROPORTO_DE_ORIGEM_REGIAO": "NORTE",
        "AEROPORTO_DE_ORIGEM_PAIS": "BRASIL",
        "AEROPORTO_DE_DESTINO_SIGLA": "SBGR",
        "AEROPORTO_DE_DESTINO_NOME": "GUARULHOS",
        "AEROPORTO_DE_DESTINO_UF": "SP",
        "AEROPORTO_DE_DESTINO_REGIAO": "SUDESTE",
        "AEROPORTO_DE_DESTINO_PAIS": "BRASIL",
        "NATUREZA": "DOMESTICA",
        "GRUPO_DE_VOO": "REGULAR",
        "PASSAGEIROS_PAGOS": None,
        "PASSAGEIROS_GRATIS": None,
        "ASSENTOS": None,
        "DECOLAGENS": None,
        "ASK": None,
        "RPK": None,
        "DISTANCIA_VOADA_KM": None,
        "COMBUSTIVEL_LITROS": None,
        "HORAS_VOADAS": None,
    }
    return pl.DataFrame([{**defaults, **row} for row in rows], strict=False).lazy()


class ProcessDataTests(unittest.TestCase):
    def test_decimal_comma_is_parsed(self) -> None:
        frame = pl.DataFrame({"HORAS_VOADAS": ["409,08", "1.234,5", None]}).select(
            parse_decimal_comma("HORAS_VOADAS")
        )
        self.assertEqual(frame["HORAS_VOADAS"].to_list(), [409.08, 1234.5, None])

    def test_keys_are_directional_and_company_uses_name(self) -> None:
        prepared = prepare_source(source_frame([{}])).collect()
        self.assertEqual(prepared["ROTA_DIRECIONAL"][0], "SBBE>SBGR")
        self.assertEqual(prepared["EMPRESA_ID"][0], "TST|EMPRESA TESTE")
        self.assertEqual(str(prepared.schema["PERIODO"]), "Date")

    def test_aggregation_sums_values_and_preserves_all_null(self) -> None:
        rows = [
            {"PASSAGEIROS_PAGOS": "10", "ASSENTOS": None, "COMBUSTIVEL_LITROS": "-5"},
            {"LINHA_DADOS": "2", "PASSAGEIROS_PAGOS": "15", "ASSENTOS": None},
        ]
        result = aggregate_routes(prepare_source(source_frame(rows))).collect()
        self.assertEqual(result.height, 1)
        self.assertEqual(result["PASSAGEIROS_PAGOS"][0], 25)
        self.assertIsNone(result["ASSENTOS"][0])
        self.assertTrue(result["FLAG_COMBUSTIVEL_NEGATIVO"][0])
        self.assertEqual(result["QTD_REGISTROS_COMBUSTIVEL_NEGATIVO"][0], 1)

    def test_missing_airport_does_not_create_route_code(self) -> None:
        prepared = prepare_source(
            source_frame([{"AEROPORTO_DE_ORIGEM_SIGLA": None}])
        ).collect()
        self.assertIsNone(prepared["ROTA_DIRECIONAL"][0])


if __name__ == "__main__":
    unittest.main()

