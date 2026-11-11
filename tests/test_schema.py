from ledger.domain import ids
from ledger.schema import TABLES, TABLES_BY_NAME


def test_every_table_has_its_primary_key_column():
    for table in TABLES:
        assert any(c.name == table.pk for c in table.cols), table.name


def test_foreign_keys_point_at_real_columns():
    for table in TABLES:
        for col in table.cols:
            if col.fk:
                target_table, target_col = col.fk.split(".")
                assert target_table in TABLES_BY_NAME, col.fk
                assert TABLES_BY_NAME[target_table].pk == target_col, col.fk


def test_column_types_are_known():
    known = {"id", "text", "int", "money", "date", "bool", "float"}
    for table in TABLES:
        for col in table.cols:
            assert col.type in known, (table.name, col.name)


def test_allocation_id_pattern_matches_generated_ids():
    col = TABLES_BY_NAME["payment_allocations"].col("allocation_id")
    assert col.rule == "pattern ALLOC-<payment>-01"
    assert ids.allocation_id("PAY-2026-000001", 1) == "ALLOC-PAY-2026-000001-01"
