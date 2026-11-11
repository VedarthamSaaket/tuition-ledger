from collections import defaultdict

from ..domain import rules
from ..domain.catalog import (
    AS_OF,
    ENROLLMENT_TRANSITIONS,
    INVOICE_TRANSITIONS,
    LATE_FEE_MAX,
    LATE_FEE_MIN,
    SCHEMES_BY_ID,
    TERMS_BY_ID,
)
from ..generator.derive import build_ledger, group
from ..schema import LOAD_ORDER, TABLES_BY_NAME
from . import reconcile


class Check:
    def __init__(self, name: str, category: str, checked: int, failures: list[str], note: str = "") -> None:
        self.name = name
        self.category = category
        self.checked = checked
        self.failures = failures
        self.note = note


def key_checks(t: dict) -> list[Check]:
    out = []
    keys = {}
    for name in LOAD_ORDER:
        table = TABLES_BY_NAME[name]
        seen, dupes = set(), []
        for row in t[name]:
            k = row[table.pk]
            if k in seen:
                dupes.append(k)
            seen.add(k)
        keys[name] = seen
        out.append(Check(f"primary key unique: {name}", "primary_key", len(t[name]), dupes))
    for name in LOAD_ORDER:
        table = TABLES_BY_NAME[name]
        for col in table.cols:
            rows = t[name]
            if col.fk:
                target = col.fk.split(".")[0]
                bad = [r[table.pk] for r in rows if r[col.name] is not None and r[col.name] not in keys[target]]
                out.append(Check(f"foreign key: {name}.{col.name} -> {col.fk}", "foreign_key", len(rows), bad))
            if col.required:
                bad = [r[table.pk] for r in rows if r[col.name] is None]
                if bad:
                    out.append(Check(f"required: {name}.{col.name}", "required", len(rows), bad))
            if col.allowed:
                bad = [r[table.pk] for r in rows if r[col.name] is not None and r[col.name] not in col.allowed]
                out.append(Check(f"allowed values: {name}.{col.name}", "enum", len(rows), bad))
            if col.unique and col.name != table.pk:
                seen, dupes = set(), []
                for r in rows:
                    if r[col.name] in seen:
                        dupes.append(r[table.pk])
                    seen.add(r[col.name])
                out.append(Check(f"unique: {name}.{col.name}", "duplicate", len(rows), dupes))
    return out


def date_checks(t: dict) -> list[Check]:
    invoices = {i["invoice_id"]: i for i in t["invoices"]}
    payments = {p["payment_id"]: p for p in t["payments"]}
    out = [
        Check("term calendar order", "date_order", len(t["terms"]), [
            r["term_id"] for r in t["terms"]
            if not (r["invoice_date"] < r["start_date"] < r["end_date"] and r["invoice_date"] < r["due_date"])]),
        Check("fee schedule effective range", "date_order", len(t["fee_schedules"]), [
            r["fee_schedule_id"] for r in t["fee_schedules"]
            if r["effective_to"] is not None and r["effective_to"] < r["effective_from"]]),
        Check("invoice issued before due", "date_order", len(t["invoices"]), [
            i["invoice_id"] for i in t["invoices"] if not i["issue_date"] < i["due_date"]]),
        Check("payment on or after invoice issue and not after as of", "date_order", len(t["payments"]), [
            p["payment_id"] for p in t["payments"]
            if not invoices[p["invoice_id"]]["issue_date"] <= p["received_on"] <= AS_OF]),
        Check("refund on or after payment", "date_order", len(t["refunds"]), [
            r["refund_id"] for r in t["refunds"] if r["refunded_on"] < payments[r["payment_id"]]["received_on"]]),
        Check("allocation dated with its payment", "date_order", len(t["payment_allocations"]), [
            a["allocation_id"] for a in t["payment_allocations"]
            if a["allocated_on"] != payments[a["payment_id"]]["received_on"]]),
    ]
    bad = []
    for e in t["enrollments"]:
        term = TERMS_BY_ID[e["term_id"]]
        if e["registered_on"] > term.invoice_date:
            bad.append(e["enrollment_id"])
        elif e["status"] == "CANCELLED" and not term.invoice_date < e["exit_date"] < term.start_date:
            bad.append(e["enrollment_id"])
        elif e["status"] == "WITHDRAWN" and not term.start_date < e["exit_date"] <= min(term.end_date, AS_OF):
            bad.append(e["enrollment_id"])
    out.append(Check("enrollment dates inside the term calendar", "date_order", len(t["enrollments"]), bad))
    return out


def arithmetic_checks(t: dict) -> list[Check]:
    lines = group(t["invoice_lines"], "invoice_id")
    allocs = group(t["payment_allocations"], "invoice_id")
    refunds = group([r for r in t["refunds"] if r["invoice_id"]], "invoice_id")
    fields = ("total_charges", "total_credits", "total_reversals", "net_amount", "amount_allocated",
              "amount_refunded", "balance")
    bad_summary = []
    for inv in t["invoices"]:
        s = rules.summarize_invoice(lines[inv["invoice_id"]], allocs[inv["invoice_id"]], refunds[inv["invoice_id"]])
        if any(s[f] != inv[f] for f in fields):
            bad_summary.append(inv["invoice_id"])
    bad_lines = [
        line["line_id"] for line in t["invoice_lines"]
        if line["line_type"] == "CHARGE" and line["quantity"] * line["unit_amount"] != line["amount"]
    ]
    sign_bad = [
        line["line_id"] for line in t["invoice_lines"]
        if (line["line_type"] in ("CHARGE", "LATE_FEE")) != (line["amount"] > 0)
    ]
    credit_sum = defaultdict(int)
    for line in t["invoice_lines"]:
        if line["scholarship_id"]:
            credit_sum[line["scholarship_id"]] -= line["amount"]
    award_bad = [s["scholarship_id"] for s in t["scholarships"] if credit_sum[s["scholarship_id"]] != s["award_amount"]]
    rebuilt = build_ledger(t)
    stored = {e["entry_id"]: (e["amount"], e["running_balance"], e["source_id"]) for e in t["ledger_entries"]}
    ledger_bad = [e["entry_id"] for e in rebuilt
                  if stored.get(e["entry_id"]) != (e["amount"], e["running_balance"], e["source_id"])]
    if len(rebuilt) != len(t["ledger_entries"]):
        ledger_bad.append("entry count differs")
    return [
        Check("invoice totals recompute from lines, allocations and refunds", "arithmetic", len(t["invoices"]),
              bad_summary),
        Check("charge line amount equals quantity times rate", "arithmetic", len(t["invoice_lines"]), bad_lines),
        Check("line sign matches line type", "arithmetic", len(t["invoice_lines"]), sign_bad),
        Check("award equals the sum of its credit lines", "arithmetic", len(t["scholarships"]), award_bad),
        Check("ledger rebuilds exactly from source rows", "arithmetic", len(t["ledger_entries"]), ledger_bad),
        Check("payment allocations do not exceed payment", "reconciliation", len(t["payments"]),
              [f["entity_id"] for f in reconcile.over_allocated_payments(t)]),
        Check("refunds do not exceed net paid", "reconciliation", len(t["refunds"]),
              [f["entity_id"] for f in reconcile.excess_refunds(t)]),
        Check("stored balance equals ledger", "reconciliation", len(t["student_accounts"]),
              [f["entity_id"] for f in reconcile.balance_mismatches(t)]),
    ]


def context_for(student: dict, program: dict, credits: int) -> rules.StudentContext:
    return rules.StudentContext(
        level=program["level"], department=program["department"], residency=student["residency"],
        income_band=student["income_band"], gpa=student["gpa"], credits=credits, has_lab=program["has_lab"],
        has_external_cover=student["has_external_cover"], staff_dependent=student["staff_dependent"],
    )


def business_checks(t: dict) -> list[Check]:
    students = {s["student_id"]: s for s in t["students"]}
    programs = {p["program_id"]: p for p in t["programs"]}
    enrollments = {e["enrollment_id"]: e for e in t["enrollments"]}
    schedules = defaultdict(list)
    for row in t["fee_schedules"]:
        schedules[(row["program_id"], row["term_id"])].append(row)
    lines = group(t["invoice_lines"], "invoice_id")
    fee_bad = []
    for inv in t["invoices"]:
        enr = enrollments[inv["enrollment_id"]]
        rows = rules.schedule_in_effect(schedules[(enr["program_id"], enr["term_id"])], inv["issue_date"])
        expected = rules.build_charge_lines(rows, context_for(students[enr["student_id"]], programs[enr["program_id"]],
                                                              enr["credits"]))
        actual = [line for line in lines[inv["invoice_id"]] if line["line_type"] == "CHARGE"]
        want = sorted((c["fee_code"], c["fee_schedule_id"], c["quantity"], c["unit_amount"], c["amount"]) for c in expected)
        got = sorted((c["fee_code"], c["fee_schedule_id"], c["quantity"], c["unit_amount"], c["amount"]) for c in actual)
        if want != got:
            fee_bad.append(inv["invoice_id"])
    elig_bad = []
    for e in t["eligibility"]:
        enr = enrollments[e["enrollment_id"]]
        student = dict(students[e["student_id"]], gpa=e["gpa"], income_band=e["income_band"])
        ok, _, _ = rules.assess_eligibility(SCHEMES_BY_ID[e["scheme_id"]],
                                            context_for(student, programs[enr["program_id"]], e["credits"]))
        if ok != e["is_eligible"]:
            elig_bad.append(e["eligibility_id"])
    eligibility = {e["eligibility_id"]: e for e in t["eligibility"]}
    award_from_ineligible = [s["scholarship_id"] for s in t["scholarships"]
                             if not eligibility[s["eligibility_id"]]["is_eligible"]]
    late_bad = []
    invoices = {i["invoice_id"]: i for i in t["invoices"]}
    late_seen = defaultdict(int)
    for line in t["invoice_lines"]:
        if line["line_type"] != "LATE_FEE":
            continue
        inv = invoices[line["invoice_id"]]
        late_seen[line["invoice_id"]] += 1
        if not (LATE_FEE_MIN <= line["amount"] <= LATE_FEE_MAX and line["posted_on"] == rules.grace_end(inv["due_date"])):
            late_bad.append(line["line_id"])
    late_bad += [inv for inv, n in late_seen.items() if n > 1]
    refund_pct_bad = [
        e["enrollment_id"] for e in t["enrollments"] if e["exit_date"] and e["refund_percent"] !=
        rules.withdrawal_refund_percent(TERMS_BY_ID[e["term_id"]].start_date, e["exit_date"])
    ]
    return [
        Check("term specific fees: charge lines match the schedule in effect on the issue date", "business_rule",
              len(t["invoices"]), fee_bad),
        Check("eligibility outcome matches the scheme rules", "business_rule", len(t["eligibility"]), elig_bad),
        Check("awards only from eligible assessments", "business_rule", len(t["scholarships"]), award_from_ineligible),
        Check("scholarship within eligible fees", "business_rule", len(t["scholarships"]),
              [f["entity_id"] for f in reconcile.over_awarded_scholarships(t)]),
        Check("late fee policy: one per invoice, bounded, posted at grace end", "business_rule",
              len(late_seen), late_bad),
        Check("withdrawal refund percent follows the schedule", "business_rule", len(t["enrollments"]), refund_pct_bad),
    ]


def lifecycle_checks(t: dict) -> list[Check]:
    out = []
    for entity, table, pk, transitions in (
        ("ENROLLMENT", "enrollments", "enrollment_id", ENROLLMENT_TRANSITIONS),
        ("INVOICE", "invoices", "invoice_id", INVOICE_TRANSITIONS),
    ):
        state, illegal = {}, []
        for ev in t["events"]:
            if ev["entity_type"] != entity:
                continue
            current = state.get(ev["entity_id"])
            if ev["from_state"] != current or ev["to_state"] not in transitions[current]:
                illegal.append(ev["entity_id"])
            state[ev["entity_id"]] = ev["to_state"]
        final_bad = [r[pk] for r in t[table] if state.get(r[pk]) != r["status"]]
        out.append(Check(f"{entity.lower()} transitions are legal", "lifecycle", len(t[table]), sorted(set(illegal))))
        out.append(Check(f"{entity.lower()} status equals its last event", "lifecycle", len(t[table]), final_bad))
    return out


def duplicate_checks(t: dict) -> list[Check]:
    pairs = defaultdict(list)
    for e in t["enrollments"]:
        pairs[(e["student_id"], e["term_id"])].append(e["enrollment_id"])
    per_enrollment = defaultdict(list)
    for inv in t["invoices"]:
        per_enrollment[inv["enrollment_id"]].append(inv["invoice_id"])
    return [
        Check("one enrollment per student per term", "duplicate", len(t["enrollments"]),
              [ids[1] for ids in pairs.values() if len(ids) > 1]),
        Check("one invoice per enrollment", "duplicate", len(t["invoices"]),
              [f["entity_id"] for f in reconcile.duplicate_invoices(t)]),
    ]


def explained_ids(ground_truth: list[dict]) -> set[str]:
    ids = set()
    for g in ground_truth:
        ids.add(g["entity_id"])
        if g["related_ids"]:
            ids.update(g["related_ids"].split("|"))
    return ids


def run(t: dict, ground_truth: list[dict] | None = None) -> dict:
    checks = key_checks(t)
    for group_fn in (date_checks, arithmetic_checks, business_checks, lifecycle_checks, duplicate_checks):
        try:
            checks += group_fn(t)
        except (KeyError, TypeError) as exc:
            name = group_fn.__name__.replace("_", " ")
            checks.append(Check(f"{name} could not run", "integrity", 1, [f"broken reference {exc}"]))
    known = explained_ids(ground_truth or [])
    results = []
    for c in checks:
        unexplained = [f for f in c.failures if f not in known]
        status = "PASS" if not c.failures else ("EXPECTED" if not unexplained else "FAIL")
        results.append({"check": c.name, "category": c.category, "checked": c.checked, "failures": len(c.failures),
                        "explained_by_ground_truth": len(c.failures) - len(unexplained),
                        "unexplained": len(unexplained), "status": status, "sample_failures": c.failures[:5]})
    summary = defaultdict(int)
    for r in results:
        summary[r["status"]] += 1
    return {"as_of": AS_OF.isoformat(), "checks": len(results), "summary": dict(summary),
            "passed": all(r["status"] != "FAIL" for r in results), "results": results}
