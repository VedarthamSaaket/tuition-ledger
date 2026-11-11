import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    test_database_url: str


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "postgresql://localhost:5432/tuition_ledger"),
        test_database_url=os.environ.get(
            "TEST_DATABASE_URL", "postgresql://localhost:5432/tuition_ledger_test"
        ),
    )
