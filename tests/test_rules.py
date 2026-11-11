from datetime import date

from ledger.domain import rules
from ledger.domain.catalog import SCHEMES_BY_ID


def ctx(**overrides):
    base = dict(
        level="UG", department="STEM", residency="DOMESTIC", income_band="LOW", gpa=3.6,
        credits=15, has_lab=True, has_external_cover=False, staff_dependent=False,
    )
    base.update(overrides)
    return rules.StudentContext(**base)


def schedule():
    rows = [
        ("TUITION", "ALL", 50000), ("INTL_SURCHARGE", "INTL", 20000), ("TECH", "ALL", 15000),
        ("ACTIVITY", "FULL_TIME", 12000), ("LAB", "LAB_PROGRAM", 30000), ("LIBRARY", "ALL", 8000),
        ("HEALTH_INSURANCE", "FULL_TIME_NO_COVER", 90000),
    ]
    return [
        {"fee_schedule_id": f"FS-{code}", "fee_code": code, "applies_when": when, "rate": rate,
         "effective_from": date(2026, 1, 1), "effective_to": None}
        for code, when, rate in rows
    ]


def test_charge_lines_follow_conditions():
    lines = rules.build_charge_lines(schedule(), ctx())
    codes = [line["fee_code"] for line in lines]
    assert codes == ["TECH", "LIBRARY", "ACTIVITY", "LAB", "HEALTH_INSURANCE", "TUITION"]
    tuition = lines[-1]
    assert tuition["quantity"] == 15 and tuition["amount"] == 750000


def test_part_time_international_student():
    lines = rules.build_charge_lines(schedule(), ctx(credits=6, residency="INTL", has_lab=False))
    codes = {line["fee_code"] for line in lines}
    assert codes == {"TECH", "LIBRARY", "INTL_SURCHARGE", "TUITION"}


def test_schedule_effective_dates_pick_one_version():
    old = {"fee_code": "TECH", "effective_from": date(2026, 1, 1), "effective_to": date(2026, 6, 30)}
    new = {"fee_code": "TECH", "effective_from": date(2026, 7, 1), "effective_to": None}
    assert rules.schedule_in_effect([old, new], date(2026, 7, 24)) == [new]
    assert rules.schedule_in_effect([old, new], date(2026, 6, 30)) == [old]


def test_eligibility_reports_failed_criteria():
    ok, passed, failed = rules.assess_eligibility(SCHEMES_BY_ID["SCHEME-MERIT-UG"], ctx(gpa=3.2, credits=9))
    assert not ok
    assert "gpa >= 3.5" in failed and "full time load" in failed
    assert "level in UG" in passed


def test_percent_award_is_capped():
    lines = rules.build_charge_lines(schedule(), ctx(credits=18))
    award, base, splits = rules.compute_award(SCHEMES_BY_ID["SCHEME-MERIT-UG"], lines)
    assert base == 900000
    assert award == 225000
    lines = rules.build_charge_lines(schedule(), ctx(credits=18))
    lines[-1]["amount"] = 2000000
    award, _, _ = rules.compute_award(SCHEMES_BY_ID["SCHEME-MERIT-UG"], lines)
    assert award == 300000


def test_fixed_award_never_exceeds_eligible_fees():
    lines = [{"fee_code": "TUITION", "amount": 100000}]
    award, base, splits = rules.compute_award(SCHEMES_BY_ID["SCHEME-STEM"], lines)
    assert award == base == 100000
    assert splits[0][1] == 100000


def test_need_grant_spreads_across_lines():
    lines = [{"fee_code": "TECH", "amount": 15000}, {"fee_code": "TUITION", "amount": 150000}]
    award, _, splits = rules.compute_award(SCHEMES_BY_ID["SCHEME-NEED"], lines)
    assert award == 165000
    assert [s[1] for s in splits] == [150000, 15000]


def test_allocation_follows_priority_and_returns_remainder():
    items = [
        {"line_id": "L1", "fee_code": "TUITION", "open": 1000},
        {"line_id": "L2", "fee_code": "TECH", "open": 200},
        {"line_id": "L3", "fee_code": "LATE_FEE", "open": 50},
    ]
    allocs, rest = rules.allocate(1500, items)
    assert [(a["line_id"], amt) for a, amt in allocs] == [("L2", 200), ("L1", 1000), ("L3", 50)]
    assert rest == 250


def test_late_fee_bounds():
    assert rules.late_fee_amount(0) == 0
    assert rules.late_fee_amount(10000) == 2500
    assert rules.late_fee_amount(400000) == 6000
    assert rules.late_fee_amount(5000000) == 15000


def test_withdrawal_schedule():
    start = date(2026, 8, 24)
    assert rules.withdrawal_refund_percent(start, date(2026, 8, 1)) == 100
    assert rules.withdrawal_refund_percent(start, date(2026, 9, 7)) == 80
    assert rules.withdrawal_refund_percent(start, date(2026, 9, 28)) == 50
    assert rules.withdrawal_refund_percent(start, date(2026, 10, 20)) == 0


def test_refund_decision():
    assert rules.refund_decision(500, 1000, 600) == (True, "approved")
    assert rules.refund_decision(1500, 1000, 2000)[0] is False
    assert rules.refund_decision(700, 1000, 600)[0] is False


def test_invoice_summary_and_status():
    lines = [
        {"line_id": "A", "line_type": "CHARGE", "amount": 1000},
        {"line_id": "B", "line_type": "SCHOLARSHIP", "amount": -200, "applies_to_line_id": "A"},
    ]
    allocs = [{"line_id": "A", "amount": 500}]
    summary = rules.summarize_invoice(lines, allocs, [])
    assert summary["net_amount"] == 800 and summary["balance"] == 300
    assert rules.line_open_amounts(lines, allocs) == {"A": 300}
    due = date(2026, 8, 31)
    assert rules.invoice_status(summary, due, date(2026, 9, 1), False) == "PARTIALLY_PAID"
    assert rules.invoice_status(summary, due, date(2026, 10, 1), False) == "OVERDUE"
