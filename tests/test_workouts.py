import unittest
from dataclasses import FrozenInstanceError

from trackfit_api.workouts import Exercise, Status, WorkoutError, publish_initial, revise


class WorkoutDomainTests(unittest.TestCase):
    def setUp(self):
        self.exercise = Exercise("Agachamento", 3, 10, 90)

    def test_publicacao_imediata(self):
        workout = publish_initial("aluno-1", [self.exercise], source="ai")
        self.assertEqual(workout.version, 1)
        self.assertEqual(workout.status, Status.PUBLISHED)
        self.assertEqual(workout.source, "ai")
        self.assertIsNotNone(workout.created_at.tzinfo)

    def test_revisao_preserva_historico(self):
        first = publish_initial("aluno-1", [self.exercise], source="ai")
        old, new = revise(first, [Exercise("Remada", 3, 12, 60)], "prof-1")
        self.assertEqual(first.status, Status.PUBLISHED)
        self.assertEqual(old.status, Status.SUPERSEDED)
        self.assertEqual(new.version, 2)
        self.assertEqual(new.workout_id, first.workout_id)
        self.assertEqual(new.student_id, first.student_id)
        self.assertEqual(new.reviewed_by, "prof-1")
        self.assertEqual(new.exercises[0].name, "Remada")
        with self.assertRaises(FrozenInstanceError):
            new.version = 99

    def test_nao_revisar_versao_arquivada(self):
        first = publish_initial("aluno-1", [self.exercise])
        old, _ = revise(first, [self.exercise], "prof-1")
        with self.assertRaises(WorkoutError):
            revise(old, [self.exercise], "prof-1")

    def test_rejeita_entradas_invalidas(self):
        for kwargs in ({"name": "", "sets": 3, "reps": 10, "rest_seconds": 60},
                       {"name": "Teste", "sets": True, "reps": 10, "rest_seconds": 60},
                       {"name": "Teste", "sets": 3, "reps": 0, "rest_seconds": 60}):
            with self.subTest(kwargs=kwargs), self.assertRaises(WorkoutError):
                Exercise(**kwargs)
        with self.assertRaises(WorkoutError):
            publish_initial("aluno-1", [])
        with self.assertRaises(WorkoutError):
            publish_initial("aluno-1", [self.exercise], source="unknown")
        with self.assertRaises(WorkoutError):
            revise(publish_initial("aluno-1", [self.exercise]), [self.exercise], "")


if __name__ == "__main__":
    unittest.main()
