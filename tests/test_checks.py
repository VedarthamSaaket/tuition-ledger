import copy
from datetime import date
from functools import lru_cache

from ledger.checks import reconcile, validate
from ledger.generator.pipeline import build
from ledger.generator.profile import scaled


@lru_cache(maxsize=2)
def dataset(anomalies: bool):
    return build(scaled(0.02, seed=13), anomalies=anomalies)


def statuses(result):
    return {r["check"]: r["status"] for r in result["results"]}


def test_clean_data_passes_every_check():
    result = validate.run(dataset(False).tables)
    assert result["passed"] and set(result["summary"]) == {"PASS"}


def test_labelled_anomalies_are_expected_not_failures():
    ds = dataset(True)
    result = validate.run(ds.tables, ds.ground_truth)
    assert result["passed"]
    assert "FAIL" not in result["summary"]
    assert result["summary"]["EXPECTED"] >= 5


def test_same_anomalies_fail_without_ground_truth():
    assert validate.run(dataset(True).tables)["passed"] is False


def test_detector_scores_perfectly_on_rule_violations():
    ds = dataset(True)
    found = reconcile.detect(ds.tables)
    scores = reconcile.evaluate(found, ds.ground_truth)
    assert scores["overall"]["precision"] == 1.0
    assert scores["overall"]["recall"] == 1.0


def test_detector_finds_nothing_in_clean_data():
    assert reconcile.detect(dataset(False).tables) == []


def tampered(mutate):
    tables = copy.deepcopy(dataset(False).tables)
    mutate(tables)
    return statuses(validate.run(tables))


def test_unlabelled_line_tamper_fails():
    def mutate(t):
        t["invoice_lines"][0]["amount"] += 100
    result = tampered(mutate)
    assert result["invoice totals recompute from lines, allocations and refunds"] == "FAIL"
    assert result["charge line amount equals quantity times rate"] == "FAIL"


def test_wrong_term_rate_fails():
    def mutate(t):
        line = next(x for x in t["invoice_lines"] if x["fee_code"] == "TECH")
        line["unit_amount"] += 500
        line["amount"] += 500
    assert tampered(mutate)["term specific fees: charge lines match the schedule in effect on the issue date"] == "FAIL"


def test_flipped_eligibility_fails():
    def mutate(t):
        row = next(e for e in t["eligibility"] if not e["is_eligible"])
        row["is_eligible"] = True
    assert tampered(mutate)["eligibility outcome matches the scheme rules"] == "FAIL"


def test_illegal_transition_fails():
    def mutate(t):
        ev = next(e for e in t["events"] if e["entity_type"] == "ENROLLMENT" and e["to_state"] == "COMPLETED")
        ev["from_state"] = "REGISTERED"
    assert tampered(mutate)["enrollment transitions are legal"] == "FAIL"


def test_broken_foreign_key_fails_cleanly():
    tables = copy.deepcopy(dataset(False).tables)
    tables["refunds"][0]["payment_id"] = "PAY-2099-000001"
    result = validate.run(tables)
    assert result["passed"] is False
    assert statuses(result)["foreign key: refunds.payment_id -> payments.payment_id"] == "FAIL"


def test_aging_uses_requested_date_not_stale_invoice_status():
    tables = copy.deepcopy(dataset(False).tables)
    for invoice in tables["invoices"]:
        invoice["status"] = "CANCELLED"
    invoice = tables["invoices"][0]
    invoice.update(status="UNPAID", balance=10000, due_date=date(2026, 1, 1))
    early = reconcile.kpis(tables, as_of=date(2026, 1, 10))
    late = reconcile.kpis(tables, as_of=date(2026, 4, 15))
    assert early["overdue_aging"] == {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    assert late["overdue_aging"]["90+"] == 100
    assert late["as_of"] == "2026-04-15"
