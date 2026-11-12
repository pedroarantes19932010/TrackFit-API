"""Gera uma cópia consistente sem parar o SQLite e verifica sua integridade."""
import argparse
import os
import sqlite3
from pathlib import Path
from contextlib import closing

def backup(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with closing(sqlite3.connect(source.as_uri()+"?mode=ro",uri=True)) as old, closing(sqlite3.connect(destination)) as new:
            old.backup(new)
            if new.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Cópia inválida.")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    args=parser.parse_args()
    backup(args.source,args.destination)
