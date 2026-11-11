from ledger.domain.catalog import TERMS_BY_ID
from ledger.domain.rules import schedule_in_effect
from ledger.generator.dataset import Dataset
from ledger.generator.enrollments import build_enrollments_and_invoices
from ledger.generator.masters import build_masters
from ledger.generator.profile import scaled


def build(seed=7):
    ds = Dataset(scaled(0.01, seed=seed))
    build_masters(ds)
    build_enrollments_and_invoices(ds, ds.profile.invoices)
    return ds


def test_counts_match_profile():
    ds = build()
    assert len(ds.tables["students"]) == ds.profile.students
    assert len(ds.tables["programs"]) == 20
    assert len(ds.tables["enrollments"]) == ds.profile.invoices
    assert len(ds.tables["invoices"]) == ds.profile.invoices


def test_same_seed_same_rows():
    a, b = build(), build()
    assert a.tables["invoice_lines"] == b.tables["invoice_lines"]
    assert a.tables["events"] == b.tables["events"]


def test_every_student_enrolls_and_once_per_term():
    ds = build()
    keys = [(e["student_id"], e["term_id"]) for e in ds.tables["enrollments"]]
    assert len(keys) == len(set(keys))
    assert {e["student_id"] for e in ds.tables["enrollments"]} == {s["student_id"] for s in ds.tables["students"]}


def test_charge_lines_use_schedule_in_effect_on_issue_date():
    ds = build()
    schedules = {r["fee_schedule_id"]: r for r in ds.tables["fee_schedules"]}
    invoices = {i["invoice_id"]: i for i in ds.tables["invoices"]}
    for line in ds.tables["invoice_lines"]:
        row = schedules[line["fee_schedule_id"]]
        issued = invoices[line["invoice_id"]]["issue_date"]
        assert schedule_in_effect([row], issued) == [row]
        assert line["unit_amount"] == row["rate"]


def test_fall_2026_uses_revised_tech_fee():
    ds = build()
    fall = {i["invoice_id"] for i in ds.tables["invoices"] if i["term_id"] == "TERM-2026-FALL"}
    tech = [line for line in ds.tables["invoice_lines"] if line["invoice_id"] in fall and line["fee_code"] == "TECH"]
    assert tech and all(line["amount"] == 16500 for line in tech)


def test_withdrawals_happen_inside_the_term():
    ds = build()
    for e in ds.tables["enrollments"]:
        term = TERMS_BY_ID[e["term_id"]]
        if e["status"] == "WITHDRAWN":
            assert term.start_date < e["exit_date"] <= term.end_date
        if e["status"] == "CANCELLED":
            assert e["registered_on"] < e["exit_date"] < term.start_date
