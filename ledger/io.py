import csv
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from .schema import GROUND_TRUTH, LOAD_ORDER, TABLES_BY_NAME, Table

SQL_TYPES = {"id": "TEXT", "text": "TEXT", "int": "INTEGER", "money": "NUMERIC(14,2)", "date": "DATE",
             "bool": "BOOLEAN", "float": "NUMERIC(5,2)"}


def money_text(paise: int) -> str:
    sign = "-" if paise < 0 else ""
    paise = abs(paise)
    return f"{sign}{paise // 100}.{paise % 100:02d}"


def to_text(col_type: str, value) -> str:
    if value is None:
        return ""
    if col_type == "money":
        return money_text(value)
    if col_type == "bool":
        return "true" if value else "false"
    if col_type == "float":
        return f"{value:.2f}"
    if col_type == "date":
        return value.isoformat()
    return str(value)


def from_text(col_type: str, text: str):
    if text == "":
        return None
    if col_type == "money":
        return int((Decimal(text) * 100).to_integral_value())
    if col_type == "int":
        return int(text)
    if col_type == "bool":
        return text == "true"
    if col_type == "float":
        return float(text)
    if col_type == "date":
        return date.fromisoformat(text)
    return text


def to_json_value(col_type: str, value):
    if value is None:
        return None
    if col_type == "money":
        return float(Decimal(value) / 100)
    if col_type == "date":
        return value.isoformat()
    return value


def sql_literal(col_type: str, value) -> str:
    if value is None:
        return "NULL"
    if col_type in ("int", "money", "float"):
        return to_text(col_type, value)
    if col_type == "bool":
        return "TRUE" if value else "FALSE"
    return "'" + to_text(col_type, value).replace("'", "''") + "'"


def ddl(table: Table) -> str:
    parts = []
    for col in table.cols:
        line = f"    {col.name} {SQL_TYPES[col.type]}"
        if col.required:
            line += " NOT NULL"
        if col.allowed:
            values = ", ".join("'" + v + "'" for v in col.allowed)
            line += f" CHECK ({col.name} IN ({values}))"
        parts.append(line)
    parts.append(f"    PRIMARY KEY ({table.pk})")
    for col in table.cols:
        if col.unique and col.name != table.pk:
            parts.append(f"    UNIQUE ({col.name})")
    for col in table.cols:
        if col.fk:
            target, target_col = col.fk.split(".")
            parts.append(f"    FOREIGN KEY ({col.name}) REFERENCES {target} ({target_col})")
    return f"CREATE TABLE {table.name} (\n" + ",\n".join(parts) + "\n);\n"


def schema_sql(include_ground_truth: bool = True) -> str:
    names = list(LOAD_ORDER) + (["ground_truth"] if include_ground_truth else [])
    drops = "".join(f"DROP TABLE IF EXISTS {n} CASCADE;\n" for n in reversed(names))
    return drops + "\n" + "\n".join(ddl(TABLES_BY_NAME[n]) for n in names)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, table: Table, rows: list[dict]) -> None:
    names = [c.name for c in table.cols]
    types = [c.type for c in table.cols]
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(names)
        for row in rows:
            writer.writerow([to_text(t, row[n]) for n, t in zip(names, types, strict=True)])


def write_json(path: Path, table: Table, rows: list[dict]) -> None:
    pairs = [(c.name, c.type) for c in table.cols]
    with open(path, "w") as fh:
        fh.write("[\n")
        for i, row in enumerate(rows):
            obj = {n: to_json_value(t, row[n]) for n, t in pairs}
            fh.write(("," if i else "") + json.dumps(obj, separators=(",", ":")) + "\n")
        fh.write("]\n")


def write_inserts(fh, table: Table, rows: list[dict]) -> None:
    pairs = [(c.name, c.type) for c in table.cols]
    names = ", ".join(n for n, _ in pairs)
    for start in range(0, len(rows), 500):
        values = ",\n".join(
            "(" + ", ".join(sql_literal(t, row[n]) for n, t in pairs) + ")" for row in rows[start:start + 500]
        )
        fh.write(f"INSERT INTO {table.name} ({names}) VALUES\n{values};\n")


def write_dataset(out: Path, tables: dict, ground_truth: list[dict], formats: set[str]) -> list[Path]:
    for sub in (*formats, "ground_truth"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    for name in LOAD_ORDER:
        table = TABLES_BY_NAME[name]
        if "csv" in formats:
            write_csv(out / "csv" / f"{name}.csv", table, tables[name])
        if "json" in formats:
            write_json(out / "json" / f"{name}.json", table, tables[name])
    if "sql" in formats:
        (out / "sql" / "schema.sql").write_text(schema_sql())
        with open(out / "sql" / "seed.sql", "w") as fh:
            for name in LOAD_ORDER:
                write_inserts(fh, TABLES_BY_NAME[name], tables[name])
        with open(out / "sql" / "ground_truth.sql", "w") as fh:
            write_inserts(fh, GROUND_TRUTH, ground_truth)
    write_csv(out / "ground_truth" / "ground_truth.csv", GROUND_TRUTH, ground_truth)
    write_json(out / "ground_truth" / "ground_truth.json", GROUND_TRUTH, ground_truth)
    return sorted(p for p in out.rglob("*") if p.is_file() and p.parent != out and p.suffix in (".csv", ".json", ".sql"))


def read_csv_dir(directory: Path) -> dict[str, list[dict]]:
    tables = {}
    for name in LOAD_ORDER:
        table = TABLES_BY_NAME[name]
        types = {c.name: c.type for c in table.cols}
        with open(directory / f"{name}.csv", newline="") as fh:
            tables[name] = [{k: from_text(types[k], v) for k, v in row.items()} for row in csv.DictReader(fh)]
    return tables


def read_ground_truth(path: Path) -> list[dict]:
    types = {c.name: c.type for c in GROUND_TRUTH.cols}
    with open(path, newline="") as fh:
        return [{k: from_text(types[k], v) for k, v in row.items()} for row in csv.DictReader(fh)]
