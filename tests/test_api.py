import unittest
from trackfit_api.main import app, capabilities, health


class ApiSmokeTests(unittest.TestCase):
    def test_health(self):
        self.assertEqual(health().status, "ok")

    def test_capabilities(self):
        statuses = {item.key: item.status for item in capabilities()}
        self.assertEqual(statuses["geracao_fichas_ia"], "prototipo_local")
        self.assertEqual(statuses["revisao_professor"], "prototipo_local")

    def test_routes_exist(self):
        paths = {route.path for route in app.routes if hasattr(route, 'path')}
        self.assertTrue({"/health", "/capabilities", "/docs"}.issubset(paths))


if __name__ == "__main__":
    unittest.main()
