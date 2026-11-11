from collections import Counter, defaultdict

from ledger.generator.awards import build_awards
from ledger.generator.dataset import Dataset
from ledger.generator.enrollments import build_enrollments_and_invoices
from ledger.generator.masters import build_masters
from ledger.generator.profile import scaled


def build():
    ds = Dataset(scaled(0.02, seed=11))
    build_masters(ds)
    build_enrollments_and_invoices(ds, ds.profile.invoices)
    build_awards(ds, ds.profile.scholarships)
    return ds


def test_award_count_hits_target():
    ds = build()
    assert len(ds.tables["scholarships"]) == ds.profile.scholarships


def test_awards_only_come_from_eligible_assessments():
    ds = build()
    eligibility = {e["eligibility_id"]: e for e in ds.tables["eligibility"]}
    for award in ds.tables["scholarships"]:
        assert eligibility[award["eligibility_id"]]["is_eligible"] is True
    for e in ds.tables["eligibility"]:
        if not e["is_eligible"]:
            assert e["failed_criteria"]


def test_credit_lines_sum_to_award_and_stay_within_eligible_fees():
    ds = build()
    credits = defaultdict(int)
    for line in ds.tables["invoice_lines"]:
        if line["scholarship_id"]:
            credits[line["scholarship_id"]] += -line["amount"]
    for award in ds.tables["scholarships"]:
        assert credits[award["scholarship_id"]] == award["award_amount"]
        assert 0 < award["award_amount"] <= award["eligible_fee_base"]


def test_no_charge_line_is_credited_below_zero():
    ds = build()
    net = {}
    for line in ds.tables["invoice_lines"]:
        if line["line_type"] == "CHARGE":
            net[line["line_id"]] = line["amount"]
    for line in ds.tables["invoice_lines"]:
        if line["applies_to_line_id"]:
            net[line["applies_to_line_id"]] += line["amount"]
    assert min(net.values()) >= 0


def test_one_award_per_type_per_enrollment():
    ds = build()
    invoices = {i["invoice_id"]: i for i in ds.tables["invoices"]}
    seen = Counter((invoices[a["invoice_id"]]["enrollment_id"], a["award_type"]) for a in ds.tables["scholarships"])
    assert max(seen.values()) == 1
