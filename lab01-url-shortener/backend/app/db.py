from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS url_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    short_code TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def connect(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        connection.executescript(SCHEMA)


def find_by_url(db_path: str | Path, url: str) -> sqlite3.Row | None:
    with connect(db_path) as connection:
        return connection.execute(
            "SELECT short_code, url FROM url_mappings WHERE url = ?",
            (url,),
        ).fetchone()


def find_by_code(db_path: str | Path, short_code: str) -> sqlite3.Row | None:
    with connect(db_path) as connection:
        return connection.execute(
            "SELECT short_code, url FROM url_mappings WHERE short_code = ?",
            (short_code,),
        ).fetchone()


def insert_mapping(db_path: str | Path, url: str, short_code: str) -> None:
    with connect(db_path) as connection:
        connection.execute(
            "INSERT INTO url_mappings (url, short_code) VALUES (?, ?)",
            (url, short_code),
        )
