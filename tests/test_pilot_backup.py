import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from server.backup import backup


class PilotBackup(unittest.TestCase):
    def test_publish_only_verified_snapshot_and_keep_existing_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "original.sqlite3"
            target = Path(directory) / "backup.sqlite3"
            with closing(sqlite3.connect(source)) as db:
                db.execute("CREATE TABLE alunos(nome TEXT)")
                db.execute("INSERT INTO alunos VALUES('teste')")
                db.commit()

            link = os.link
            def publish(snapshot, destination):
                self.assertFalse(target.exists())
                with closing(sqlite3.connect(snapshot)) as db:
                    self.assertEqual(db.execute("SELECT nome FROM alunos").fetchone(), ("teste",))
                link(snapshot, destination)

            with patch("server.backup.os.link", side_effect=publish):
                backup(source, target)
            before = target.read_bytes()
            with self.assertRaises(FileExistsError):
                backup(source, target)
            self.assertEqual(target.read_bytes(), before)

    def test_corrupt_source_leaves_no_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "original.sqlite3"
            source.write_bytes(b"invalid database")
            with self.assertRaises(sqlite3.DatabaseError):
                backup(source, Path(directory) / "backup.sqlite3")
            self.assertEqual(list(source.parent.iterdir()), [source])
