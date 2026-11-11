from contextlib import contextmanager
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

from ..config import load_settings


def connect(url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(url or load_settings().database_url, row_factory=dict_row)


@contextmanager
def transaction(url: str | None = None):
    with connect(url) as conn:
        with conn.transaction():
            yield conn


def cents(value) -> int | None:
    if value is None:
        return None
    return int((Decimal(value) * 100).to_integral_value())


def dollars(value: int | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value) / 100
