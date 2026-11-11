from collections import defaultdict
from functools import lru_cache

from ledger.domain.catalog import AS_OF, INVOICE_TRANSITIONS, LATE_FEE_MAX, LATE_FEE_MIN, TERMS_BY_ID
from ledger.domain.rules import grace_end
from ledger.generator.pipeline import build
from ledger.generator.profile import scaled


@lru_cache(maxsize=1)
def dataset():
    return build(scaled(0.02, seed=5), anomalies=False)


def test_payment_count_hits_target():
    ds = dataset()
    assert len(ds.tables["payments"]) == ds.profile.payments


def test_allocations_never_exceed_payment():
    ds = dataset()
    for p in ds.tables["payments"]:
        assert 0 <= p["amount_allocated"] <= p["amount"]


def test_refunds_never_exceed_net_paid():
    ds = dataset()
    payments = {p["payment_id"]: p for p in ds.tables["payments"]}
    refunded = defaultdict(int)
    for r in sorted(ds.tables["refunds"], key=lambda r: r["refunded_on"]):
        refunded[r["payment_id"]] += r["amount"]
        assert refunded[r["payment_id"]] <= payments[r["payment_id"]]["amount"]
        assert r["refunded_on"] >= payments[r["payment_id"]]["received_on"]


def test_balances_reconcile_three_ways():
    ds = dataset()
    ledger = defaultdict(int)
    for e in ds.tables["ledger_entries"]:
        ledger[e["student_id"]] += e["amount"]
    invoice_total = defaultdict(int)
    for inv in ds.tables["invoices"]:
        invoice_total[inv["student_id"]] += inv["balance"]
    for acct in ds.tables["student_accounts"]:
        sid = acct["student_id"]
        assert acct["balance"] == ledger[sid]
        assert acct["balance"] == invoice_total[sid] - acct["unapplied_credit"]
        assert acct["balance"] == acct["total_billed"] - acct["total_credits"] - acct["total_paid"] + acct["total_refunded"]


def test_status_history_is_legal_and_matches_final_status():
    ds = dataset()
    last = {}
    for e in ds.tables["events"]:
        if e["entity_type"] != "INVOICE":
            continue
        assert e["to_state"] in INVOICE_TRANSITIONS[e["from_state"]]
        assert last.get(e["entity_id"]) == e["from_state"]
        last[e["entity_id"]] = e["to_state"]
    for inv in ds.tables["invoices"]:
        assert last[inv["invoice_id"]] == inv["status"]


def test_late_fees_follow_policy():
    ds = dataset()
    invoices = {i["invoice_id"]: i for i in ds.tables["invoices"]}
    seen = set()
    for line in ds.tables["invoice_lines"]:
        if line["line_type"] != "LATE_FEE":
            continue
        inv = invoices[line["invoice_id"]]
        assert line["invoice_id"] not in seen
        seen.add(line["invoice_id"])
        assert line["posted_on"] == grace_end(inv["due_date"]) <= AS_OF
        assert LATE_FEE_MIN <= line["amount"] <= LATE_FEE_MAX
    assert seen


def test_cancelled_invoices_net_to_zero():
    ds = dataset()
    for inv in ds.tables["invoices"]:
        if inv["status"] == "CANCELLED":
            assert inv["net_amount"] == 0


def test_scenarios_are_covered():
    ds = dataset()
    statuses = {i["status"] for i in ds.tables["invoices"]}
    assert {"PAID", "OVERDUE", "CANCELLED", "UNPAID", "PARTIALLY_PAID"} <= statuses
    reasons = {r["reason"] for r in ds.tables["refunds"]}
    assert {"OVERPAYMENT", "WITHDRAWAL"} <= reasons
    assert any(p["amount_unapplied"] > 0 for p in ds.tables["payments"])
    assert any(i["status"] == "OVERDUE" and i["amount_allocated"] > 0 for i in ds.tables["invoices"])
    assert any(line["line_type"] == "WAIVER" for line in ds.tables["invoice_lines"])


def test_early_registration_term_is_before_due_at_snapshot():
    ds = dataset()
    term = TERMS_BY_ID["TERM-2027-SPRING"]
    assert term.invoice_date <= AS_OF < term.due_date
    future = [i for i in ds.tables["invoices"] if i["term_id"] == term.term_id]
    assert future
    assert {i["status"] for i in future} & {"UNPAID", "PARTIALLY_PAID"}


def test_no_event_is_recorded_after_the_snapshot():
    ds = dataset()
    assert max(e["occurred_on"] for e in ds.tables["events"]) <= AS_OF
    for e in ds.tables["enrollments"]:
        if e["term_id"] == "TERM-2027-SPRING" and e["status"] != "CANCELLED":
            assert e["status"] == "REGISTERED"
            assert e["status_on"] <= AS_OF
