import sqlite3
import tempfile
import unittest
from pathlib import Path

from trackfit_api.storage import connect, get_current, list_versions, save_initial, save_revision
from trackfit_api.workouts import Exercise, Status, WorkoutError, publish_initial, revise


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = connect(Path(self.temp.name) / "trackfit.db")
        self.addCleanup(self.db.close)
        self.first = publish_initial("aluno-teste", [Exercise("Remada", 3, 12, 60)])

    def test_roundtrip(self):
        save_initial(self.db, self.first)
        saved = get_current(self.db, self.first.workout_id)
        self.assertEqual(saved, self.first)
        self.assertEqual(len(list_versions(self.db, self.first.workout_id)), 1)

    def test_revisao_e_historico(self):
        save_initial(self.db, self.first)
        old, new = revise(self.first, [Exercise("Agachamento", 3, 10, 90)], "prof-teste")
        save_revision(self.db, old, new)
        self.assertEqual(get_current(self.db, new.workout_id), new)
        versions = list_versions(self.db, new.workout_id)
        self.assertEqual([v.status for v in versions], [Status.SUPERSEDED, Status.PUBLISHED])

    def test_revisao_concorrente_recusada(self):
        save_initial(self.db, self.first)
        old, new = revise(self.first, [Exercise("Agachamento", 3, 10, 90)], "prof-teste")
        save_revision(self.db, old, new)
        with self.assertRaises(WorkoutError):
            save_revision(self.db, old, new)
        self.assertEqual(len(list_versions(self.db, new.workout_id)), 2)

    def test_id_duplicado_recusado(self):
        save_initial(self.db, self.first)
        with self.assertRaises(sqlite3.IntegrityError):
            save_initial(self.db, self.first)
        self.assertEqual(len(list_versions(self.db, self.first.workout_id)), 1)


if __name__ == "__main__":
    unittest.main()
