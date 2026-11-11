from collections import Counter
from functools import lru_cache

from ledger.domain.catalog import ISSUE_TYPES
from ledger.generator.pipeline import build
from ledger.generator.profile import anomaly_count, scaled


@lru_cache(maxsize=1)
def dataset():
    return build(scaled(0.02, seed=9))


def test_every_issue_type_is_injected_and_labelled():
    ds = dataset()
    counts = Counter(row["issue_type"] for row in ds.ground_truth)
    assert set(counts) == set(ISSUE_TYPES)
    assert counts["DUPLICATE_INVOICE"] == anomaly_count(ds.profile, ds.profile.invoices)


def test_volumes_still_hit_targets():
    ds = dataset()
    assert len(ds.tables["invoices"]) == ds.profile.invoices
    assert len(ds.tables["payments"]) == ds.profile.payments
    assert len(ds.tables["scholarships"]) == ds.profile.scholarships


def test_labels_point_at_real_records():
    ds = dataset()
    tables = {
        "PAYMENT": ("payments", "payment_id"), "SCHOLARSHIP": ("scholarships", "scholarship_id"),
        "INVOICE": ("invoices", "invoice_id"), "REFUND": ("refunds", "refund_id"),
        "STUDENT_ACCOUNT": ("student_accounts", "student_id"),
    }
    for row in ds.ground_truth:
        table, key = tables[row["entity_type"]]
        assert any(r[key] == row["entity_id"] for r in ds.tables[table]), row


def test_labelled_rows_really_break_the_rule():
    ds = dataset()
    payments = {p["payment_id"]: p for p in ds.tables["payments"]}
    awards = {s["scholarship_id"]: s for s in ds.tables["scholarships"]}
    for row in ds.ground_truth:
        if row["issue_type"] == "ALLOCATION_EXCEEDS_PAYMENT":
            p = payments[row["entity_id"]]
            assert p["amount_allocated"] > p["amount"]
        if row["issue_type"] == "SCHOLARSHIP_EXCEEDS_ELIGIBLE":
            a = awards[row["entity_id"]]
            assert a["award_amount"] > a["eligible_fee_base"]


def test_ground_truth_is_not_in_input_tables():
    ds = dataset()
    for rows in ds.tables.values():
        if rows:
            assert not any(k in rows[0] for k in ("issue_type", "ground_truth", "expected_decision"))


def test_clean_build_has_no_labels():
    assert build(scaled(0.01, seed=9), anomalies=False).ground_truth == []
