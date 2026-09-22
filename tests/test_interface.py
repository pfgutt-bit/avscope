from datetime import date
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


class InterfaceTests(unittest.TestCase):
    def start(self, query=None):
        app = AppTest.from_file(str(APP), default_timeout=60)
        if query:
            app.query_params.update(query)
        app.run()
        self.assertFalse(app.exception, str(app.exception))
        return app

    def test_route_company_and_invalid_link(self):
        app = self.start({"origin": "INVALID", "destination": "INVALID", "start": "bad"})
        self.assertEqual(app.selectbox(key="origin_icao").value, "SBBE")
        app.selectbox(key="origin_icao").set_value("SBSP").run()
        app.selectbox(key="destination_icao").set_value("SBRJ").run()
        app.selectbox(key="period_start").set_value(date(2025, 1, 1)).run()
        app.selectbox(key="period_end").set_value(date(2025, 12, 1)).run()
        self.assertFalse(app.exception, str(app.exception))
        companies = app.selectbox(key="company_id").options
        gol_label = next(x for x in companies if "GLO" in x)
        app.selectbox(key="company_id").select(gol_label).run()
        self.assertFalse(app.exception, str(app.exception))

    def test_discover_filter_open_route_and_about(self):
        app = self.start({"view": "discover", "year": "2026", "month": "7"})
        self.assertEqual(app.title[0].value, "Descobrir mercados")
        app.selectbox(key="discover_origin_uf").set_value("PA").run()
        self.assertFalse(app.exception, str(app.exception))
        route = app.selectbox(key="discover_selection").value
        next(x for x in app.button if x.label.startswith("Explorar mercado")).click().run()
        self.assertFalse(app.exception, str(app.exception))
        self.assertEqual(app.selectbox(key="origin_icao").value, route.split(">", 1)[0])
        self.assertEqual(app.selectbox(key="period_start").value, date(2026, 1, 1))
        app.radio(key="navigation").set_value("Sobre os dados").run()
        self.assertFalse(app.exception, str(app.exception))
        self.assertEqual(app.title[0].value, "Sobre os dados")

    def test_empty_discovery_and_invalid_discovery_link(self):
        app = self.start({"view": "discover", "year": "oops", "month": "99"})
        app.number_input(key="discover_minimum").set_value(10**12).run()
        self.assertFalse(app.exception, str(app.exception))
        self.assertTrue(any("Nenhum mercado" in x.value for x in app.info))


if __name__ == "__main__":
    unittest.main()

