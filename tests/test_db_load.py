import psycopg
import pytest
from psycopg.rows import dict_row

from ledger.checks import validate
from ledger.io import read_csv_dir, read_ground_truth


def query(url, sql, *params):
    with psycopg.connect(url, row_factory=dict_row) as conn:
        return conn.execute(sql, params or None).fetchall()


def test_every_table_loaded(loaded_db):
    for name, count in loaded_db["counts"].items():
        assert count > 0, name


def test_database_enforces_foreign_keys(loaded_db):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        query(loaded_db["url"], "INSERT INTO payments (payment_id, student_id, invoice_id, received_on, amount, method, "
              "amount_allocated, amount_unapplied, amount_refunded) VALUES ('PAY-2099-000001', 'STU-999999', "
              "'INV-X', '2026-01-01', 1, 'CARD', 0, 1, 0)")


def test_database_enforces_enums(loaded_db):
    with pytest.raises(psycopg.errors.CheckViolation):
        query(loaded_db["url"], "UPDATE invoices SET status = 'LOST' WHERE invoice_id = "
              "(SELECT invoice_id FROM invoices LIMIT 1)")


def test_counters_start_after_loaded_ids(loaded_db):
    rows = query(loaded_db["url"], "SELECT counter_key, value FROM id_counters WHERE counter_key LIKE 'payment:%'")
    assert rows and all(r["value"] > 0 for r in rows)


def test_sql_and_files_agree_on_balances(loaded_db):
    db = query(loaded_db["url"], "SELECT s.student_id, sum(l.amount) AS ledger, a.balance FROM students s "
               "JOIN ledger_entries l USING (student_id) JOIN student_accounts a USING (student_id) "
               "GROUP BY s.student_id, a.balance")
    mismatched = {r["student_id"] for r in db if r["ledger"] != r["balance"]}
    gt = read_ground_truth(loaded_db["dir"] / "ground_truth" / "ground_truth.csv")
    assert mismatched == {g["entity_id"] for g in gt if g["issue_type"] == "BALANCE_LEDGER_MISMATCH"}


def test_files_validate(loaded_db):
    tables = read_csv_dir(loaded_db["dir"] / "csv")
    gt = read_ground_truth(loaded_db["dir"] / "ground_truth" / "ground_truth.csv")
    assert validate.run(tables, gt)["passed"]
