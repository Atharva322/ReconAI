from __future__ import annotations

from pathlib import Path
from typing import Iterator

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from .config import Settings


def connect(settings: Settings) -> Connection:
    return psycopg.connect(settings.database_url, row_factory=dict_row)


def run_migrations(settings: Settings) -> None:
    migrations_dir = Path(__file__).resolve().parents[3] / "migrations"
    with connect(settings) as conn:
        with conn.cursor() as cursor:
            for migration in sorted(migrations_dir.glob("*.sql")):
                cursor.execute(migration.read_text(encoding="utf-8"))
        conn.commit()


def connection_scope(settings: Settings) -> Iterator[Connection]:
    with connect(settings) as conn:
        yield conn
