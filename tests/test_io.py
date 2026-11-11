import json

from ledger.generate import generate
from ledger.generator.pipeline import build
from ledger.generator.profile import scaled
from ledger.io import read_csv_dir, read_ground_truth, schema_sql, write_dataset
from ledger.schema import LOAD_ORDER


def test_csv_round_trip_keeps_values(tmp_path):
    ds = build(scaled(0.01, seed=3))
    write_dataset(tmp_path, ds.tables, ds.ground_truth, {"csv"})
    back = read_csv_dir(tmp_path / "csv")
    for name in LOAD_ORDER:
        cols = list(back[name][0].keys())
        original = [{k: row[k] for k in cols} for row in ds.tables[name]]
        assert back[name] == original, name
    assert read_ground_truth(tmp_path / "ground_truth" / "ground_truth.csv") == ds.ground_truth


def test_internal_keys_are_not_exported(tmp_path):
    ds = build(scaled(0.01, seed=3))
    write_dataset(tmp_path, ds.tables, ds.ground_truth, {"json"})
    programs = json.loads((tmp_path / "json" / "programs.json").read_text())
    assert all(not k.startswith("_") for k in programs[0])


def test_same_seed_gives_same_checksums(tmp_path):
    a = generate(scaled(0.01, seed=4), tmp_path / "a", {"csv"})
    b = generate(scaled(0.01, seed=4), tmp_path / "b", {"csv"})
    c = generate(scaled(0.01, seed=5), tmp_path / "c", {"csv"})
    assert a["dataset_sha256"] == b["dataset_sha256"]
    assert a["dataset_sha256"] != c["dataset_sha256"]


def test_schema_sql_creates_every_table():
    sql = schema_sql()
    for name in LOAD_ORDER:
        assert f"CREATE TABLE {name} (" in sql
