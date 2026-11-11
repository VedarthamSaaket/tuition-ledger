import re
from pathlib import Path

from ..io import schema_sql
from ..schema import LOAD_ORDER, TABLES_BY_NAME
from .conn import connect

APP_SCHEMA = Path(__file__).with_name("app_schema.sql")

COUNTERS = (
    ("payment", "payments", "payment_id", r"PAY-(\d{4})-(\d+)"),
    ("refund", "refunds", "refund_id", r"REF-(\d{4})-(\d+)"),
    ("scholarship", "scholarships", "scholarship_id", r"SCH-(\d{4})-(\d+)"),
    ("eligibility", "eligibility", "eligibility_id", r"ELG-(\d{4})-(\d+)"),
)


def copy_csv(cur, table: str, path: Path) -> None:
    cols = ", ".join(c.name for c in TABLES_BY_NAME[table].cols)
    with cur.copy(f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true)") as copy:
        with open(path, "rb") as fh:
            while chunk := fh.read(1 << 20):
                copy.write(chunk)


def rebuild_counters(cur) -> None:
    cur.execute("DELETE FROM id_counters")
    values: dict[str, int] = {}
    for key, table, col, pattern in COUNTERS:
        cur.execute(f"SELECT {col} AS id FROM {table}")
        for row in cur.fetchall():
            m = re.fullmatch(pattern, row["id"])
            k = f"{key}:{m.group(1)}"
            values[k] = max(values.get(k, 0), int(m.group(2)))
    cur.execute("SELECT coalesce(max(substr(event_id, 5)::bigint), 0) AS n FROM events")
    values["event"] = cur.fetchone()["n"]
    cur.execute("SELECT coalesce(max(substr(decision_id, 5)::bigint), 0) AS n FROM decisions")
    values["decision"] = cur.fetchone()["n"]
    with cur.copy("COPY id_counters (counter_key, value) FROM STDIN") as copy:
        for k, v in sorted(values.items()):
            copy.write_row((k, v))


def load_dataset(dataset: Path, url: str | None = None) -> dict[str, int]:
    counts = {}
    with connect(url) as conn:
        with conn.transaction(), conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS exceptions, reconciliation_runs, id_counters, api_idempotency CASCADE")
            cur.execute(schema_sql())
            for name in LOAD_ORDER:
                copy_csv(cur, name, dataset / "csv" / f"{name}.csv")
                counts[name] = cur.execute(f"SELECT count(*) AS n FROM {name}").fetchone()["n"]
            gt = dataset / "ground_truth" / "ground_truth.csv"
            if gt.exists():
                copy_csv(cur, "ground_truth", gt)
                counts["ground_truth"] = cur.execute("SELECT count(*) AS n FROM ground_truth").fetchone()["n"]
            cur.execute(APP_SCHEMA.read_text())
            rebuild_counters(cur)
    return counts
