import os

import psycopg
import pytest

from ledger.config import load_settings
from ledger.generate import generate
from ledger.generator.profile import scaled


def db_url() -> str:
    return load_settings().test_database_url


@pytest.fixture(scope="session")
def loaded_db(tmp_path_factory):
    url = db_url()
    try:
        psycopg.connect(url, connect_timeout=3).close()
    except psycopg.OperationalError:
        if os.environ.get("CI"):
            raise
        pytest.skip("test database not reachable")
    from ledger.db.load import load_dataset

    out = tmp_path_factory.mktemp("dataset")
    generate(scaled(0.01, seed=21), out, {"csv"})
    counts = load_dataset(out, url)
    return {"url": url, "dir": out, "counts": counts}
