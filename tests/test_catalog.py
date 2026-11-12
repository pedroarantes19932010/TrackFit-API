import unittest
from fastapi.testclient import TestClient
from trackfit_api.main import app
from trackfit_api.catalog_routes import ExerciseVideo


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_list_and_search(self):
        response = self.client.get("/v1/exercises")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 8)
        self.assertEqual(len(self.client.get("/v1/exercises?muscle_group=costas").json()), 2)
        self.assertEqual(self.client.get("/v1/exercises?search=Remada").json()[0]["exercise_id"], "seated_row")

    def test_detail_and_unknown(self):
        response = self.client.get("/v1/exercises/plank")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["videos"], [])
        self.assertEqual(self.client.get("/v1/exercises/not-found").status_code, 404)

    def test_ai_catalog_matches_public_catalog(self):
        from trackfit_api.ai_generator import CATALOG, AI_TO_CATALOG_ID
        response = self.client.get("/v1/exercises")
        public = {item["exercise_id"]: item["name"] for item in response.json()}
        self.assertEqual(
            {key: public[value] for key, value in AI_TO_CATALOG_ID.items()},
            CATALOG,
        )

    def test_video_id_validation(self):
        valid = ExerciseVideo(youtube_id="dQw4w9WgXcQ", kind="demonstration", creator_name="Exemplo")
        self.assertEqual(len(valid.youtube_id), 11)
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            ExerciseVideo(youtube_id="https://youtube.com/watch?v=bad", kind="demonstration", creator_name="Exemplo")


if __name__ == "__main__":
    unittest.main()
