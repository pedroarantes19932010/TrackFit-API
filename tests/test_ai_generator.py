import json
import os
import unittest
from unittest.mock import patch

from trackfit_api.ai_generator import GenerationError, generate_demo


class FakeResponse:
    def __init__(self, entries):
        self.payload = json.dumps({"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": json.dumps({"exercises": entries})}]}
        ]}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, n):
        return self.payload[:n]


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.entries = [
            {"id": "remada_sentada", "sets": 3, "reps": 10, "rest_seconds": 60},
            {"id": "supino_maquina", "sets": 3, "reps": 10, "rest_seconds": 60},
            {"id": "mesa_flexora", "sets": 3, "reps": 10, "rest_seconds": 60},
        ]

    def test_valid_output(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch(
            "trackfit_api.ai_generator.urllib.request.urlopen", return_value=FakeResponse(self.entries)
        ):
            exercises = generate_demo("general_fitness", "beginner")
        self.assertEqual(len(exercises), 3)
        self.assertEqual(exercises[0].name, "Remada sentada")

    def test_unknown_exercise_rejected(self):
        self.entries[0]["id"] = "inventado"
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch(
            "trackfit_api.ai_generator.urllib.request.urlopen", return_value=FakeResponse(self.entries)
        ):
            with self.assertRaises(GenerationError):
                generate_demo("strength", "intermediate")

    def test_missing_key_fails_closed(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with self.assertRaises(GenerationError):
                generate_demo("strength", "beginner")


if __name__ == "__main__":
    unittest.main()
