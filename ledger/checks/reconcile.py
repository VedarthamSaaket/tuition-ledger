from collections import defaultdict

from ..domain.catalog import AS_OF, ISSUE_TYPES, SCHEMES_BY_ID

DECISIONS = {
    "ALLOCATION_EXCEEDS_PAYMENT": "REJECT_EXCESS_ALLOCATION",
    "SCHOLARSHIP_EXCEEDS_ELIGIBLE": "CAP_AT_ELIGIBLE_FEES",
    "DUPLICATE_INVOICE": "VOID_DUPLICATE",
    "REFUND_EXCEEDS_NET_PAID": "REJECT_REFUND",
    "BALANCE_LEDGER_MISMATCH": "RECOMPUTE_FROM_LEDGER",
}


def finding(issue_type, entity_type, entity_id, related, value, explanation) -> dict:
    return {"issue_type": issue_type, "entity_type": entity_type, "entity_id": entity_id,
            "related_ids": "|".join(related) or None, "expected_decision": DECISIONS[issue_type],
            "detected_value": value, "explanation": explanation}


def over_allocated_payments(t: dict) -> list[dict]:
    allocs = defaultdict(list)
    for a in t["payment_allocations"]:
        allocs[a["payment_id"]].append(a)
    out = []
    for p in t["payments"]:
        total = sum(a["amount"] for a in allocs[p["payment_id"]])
        if total > p["amount"]:
            out.append(finding("ALLOCATION_EXCEEDS_PAYMENT", "PAYMENT", p["payment_id"],
                               [a["allocation_id"] for a in allocs[p["payment_id"]]], total - p["amount"],
                               f"allocated {total / 100:.2f} from a payment of {p['amount'] / 100:.2f}"))
    return out


def eligible_base_at_award(lines: list[dict], award: dict) -> int:
    scheme = SCHEMES_BY_ID[award["scheme_id"]]
    own = [line for line in lines if line["scholarship_id"] == award["scholarship_id"]]
    first_no = min((line["line_no"] for line in own), default=10**6)
    net = {line["line_id"]: line["amount"] for line in lines
           if line["line_type"] == "CHARGE" and line["fee_code"] in scheme.fee_codes}
    for line in lines:
        if line["scholarship_id"] and line["scholarship_id"] != award["scholarship_id"] and line["line_no"] < first_no:
            if line["applies_to_line_id"] in net:
                net[line["applies_to_line_id"]] += line["amount"]
    return sum(max(0, v) for v in net.values())


def over_awarded_scholarships(t: dict) -> list[dict]:
    lines = defaultdict(list)
    for line in t["invoice_lines"]:
        lines[line["invoice_id"]].append(line)
    out = []
    for award in t["scholarships"]:
        base = eligible_base_at_award(lines[award["invoice_id"]], award)
        if award["award_amount"] > base:
            out.append(finding("SCHOLARSHIP_EXCEEDS_ELIGIBLE", "SCHOLARSHIP", award["scholarship_id"],
                               [award["invoice_id"]], award["award_amount"] - base,
                               f"award {award['award_amount'] / 100:.2f} above eligible fees {base / 100:.2f}"))
    return out


def duplicate_invoices(t: dict) -> list[dict]:
    by_enrollment = defaultdict(list)
    for inv in t["invoices"]:
        by_enrollment[inv["enrollment_id"]].append(inv)
    out = []
    for enrollment_id, invs in by_enrollment.items():
        if len(invs) < 2:
            continue
        invs.sort(key=lambda i: (i["issue_date"], i["invoice_id"]))
        for dup in invs[1:]:
            out.append(finding("DUPLICATE_INVOICE", "INVOICE", dup["invoice_id"], [invs[0]["invoice_id"], enrollment_id],
                               dup["net_amount"], f"{enrollment_id} already billed on {invs[0]['invoice_id']}"))
    return out


def excess_refunds(t: dict) -> list[dict]:
    payments = {p["payment_id"]: p for p in t["payments"]}
    refunded = defaultdict(int)
    out = []
    for r in sorted(t["refunds"], key=lambda r: (r["refunded_on"], r["refund_id"])):
        before = refunded[r["payment_id"]]
        refunded[r["payment_id"]] += r["amount"]
        net_paid = payments[r["payment_id"]]["amount"] - before
        if r["amount"] > net_paid:
            out.append(finding("REFUND_EXCEEDS_NET_PAID", "REFUND", r["refund_id"], [r["payment_id"]],
                               r["amount"] - net_paid,
                               f"refund {r['amount'] / 100:.2f} but only {net_paid / 100:.2f} left to refund"))
    return out


def balance_mismatches(t: dict) -> list[dict]:
    ledger = defaultdict(int)
    for e in t["ledger_entries"]:
        ledger[e["student_id"]] += e["amount"]
    out = []
    for acct in t["student_accounts"]:
        expected = ledger[acct["student_id"]]
        if acct["balance"] != expected:
            out.append(finding("BALANCE_LEDGER_MISMATCH", "STUDENT_ACCOUNT", acct["student_id"], [],
                               acct["balance"] - expected,
                               f"stored {acct['balance'] / 100:.2f}, ledger {expected / 100:.2f}"))
    return out


DETECTORS = (over_allocated_payments, over_awarded_scholarships, duplicate_invoices, excess_refunds,
             balance_mismatches)


def detect(tables: dict) -> list[dict]:
    found = []
    for detector in DETECTORS:
        found += detector(tables)
    for n, row in enumerate(found, start=1):
        row["exception_id"] = f"EXC-{n:06d}"
    return found


def evaluate(found: list[dict], ground_truth: list[dict]) -> dict:
    per_type = {}
    for issue in ISSUE_TYPES:
        predicted = {f["entity_id"] for f in found if f["issue_type"] == issue}
        actual = {g["entity_id"] for g in ground_truth if g["issue_type"] == issue}
        tp, fp, fn = len(predicted & actual), len(predicted - actual), len(actual - predicted)
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_type[issue] = {"labelled": len(actual), "detected": len(predicted), "true_positive": tp,
                           "false_positive": fp, "false_negative": fn, "precision": round(precision, 4),
                           "recall": round(recall, 4), "f1": round(f1, 4),
                           "false_positive_ids": sorted(predicted - actual)[:20],
                           "missed_ids": sorted(actual - predicted)[:20]}
    tp = sum(v["true_positive"] for v in per_type.values())
    fp = sum(v["false_positive"] for v in per_type.values())
    fn = sum(v["false_negative"] for v in per_type.values())
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {"overall": {"labelled": tp + fn, "detected": tp + fp, "precision": round(precision, 4),
                        "recall": round(recall, 4)}, "per_type": per_type}


def money(cents: int) -> float:
    return round(cents / 100, 2)


def kpis(t: dict) -> dict:
    invoices = t["invoices"]
    billed = sum(i["total_charges"] for i in invoices)
    credits = sum(i["total_credits"] for i in invoices)
    reversals = sum(i["total_reversals"] for i in invoices)
    paid = sum(p["amount"] for p in t["payments"])
    refunded = sum(r["amount"] for r in t["refunds"])
    receivable = sum(a["balance"] for a in t["student_accounts"] if a["balance"] > 0)
    credit_owed = -sum(a["balance"] for a in t["student_accounts"] if a["balance"] < 0)
    late = [line for line in t["invoice_lines"] if line["line_type"] == "LATE_FEE"]
    aging = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    for i in invoices:
        if i["status"] == "OVERDUE":
            days = (AS_OF - i["due_date"]).days
            key = "0-30" if days <= 30 else "31-60" if days <= 60 else "61-90" if days <= 90 else "90+"
            aging[key] += i["balance"]
    by_scheme = defaultdict(lambda: {"awards": 0, "amount": 0})
    for s in t["scholarships"]:
        by_scheme[s["scheme_id"]]["awards"] += 1
        by_scheme[s["scheme_id"]]["amount"] += s["award_amount"]
    status_counts = defaultdict(int)
    for i in invoices:
        status_counts[i["status"]] += 1
    eligible = sum(1 for e in t["eligibility"] if e["is_eligible"])
    return {
        "as_of": AS_OF.isoformat(),
        "students": len(t["students"]),
        "invoices": len(invoices),
        "total_billed": money(billed),
        "total_scholarships_and_waivers": money(credits),
        "total_reversals": money(reversals),
        "net_billed": money(billed - credits - reversals),
        "total_collected": money(paid),
        "total_refunded": money(refunded),
        "collection_rate": round((paid - refunded) / (billed - credits - reversals), 4) if billed else 0,
        "outstanding_receivable": money(receivable),
        "credit_balances_owed": money(credit_owed),
        "late_fees_assessed": len(late),
        "late_fee_amount": money(sum(line["amount"] for line in late)),
        "overdue_aging": {k: money(v) for k, v in aging.items()},
        "invoice_status_counts": dict(sorted(status_counts.items())),
        "eligibility_assessments": len(t["eligibility"]),
        "eligibility_rate": round(eligible / len(t["eligibility"]), 4) if t["eligibility"] else 0,
        "scholarships_by_scheme": {k: {"awards": v["awards"], "amount": money(v["amount"])}
                                   for k, v in sorted(by_scheme.items())},
        "withdrawals": sum(1 for e in t["enrollments"] if e["status"] == "WITHDRAWN"),
        "cancellations": sum(1 for e in t["enrollments"] if e["status"] == "CANCELLED"),
    }


def boundary_cases(t: dict, found: list[dict]) -> dict:
    flagged = {f["entity_id"] for f in found}
    allocs = defaultdict(int)
    for a in t["payment_allocations"]:
        allocs[a["payment_id"]] += a["amount"]
    exact_payments = [p["payment_id"] for p in t["payments"] if allocs[p["payment_id"]] == p["amount"]]
    lines = defaultdict(list)
    for line in t["invoice_lines"]:
        lines[line["invoice_id"]].append(line)
    exact_awards = [s["scholarship_id"] for s in t["scholarships"]
                    if s["award_amount"] == eligible_base_at_award(lines[s["invoice_id"]], s)]
    payments = {p["payment_id"]: p for p in t["payments"]}
    refunded = defaultdict(int)
    exact_refunds = []
    for r in sorted(t["refunds"], key=lambda r: (r["refunded_on"], r["refund_id"])):
        if r["amount"] == payments[r["payment_id"]]["amount"] - refunded[r["payment_id"]]:
            exact_refunds.append(r["refund_id"])
        refunded[r["payment_id"]] += r["amount"]
    multi_payment_refunds = defaultdict(int)
    for r in t["refunds"]:
        if r["invoice_id"]:
            multi_payment_refunds[(r["invoice_id"], r["refunded_on"])] += 1
    cases = {
        "payments_allocated_to_the_cent": exact_payments,
        "awards_equal_to_eligible_fees": exact_awards,
        "refunds_equal_to_remaining_net_paid": exact_refunds,
    }
    report = {name: {"count": len(ids), "wrongly_flagged": len([i for i in ids if i in flagged])}
              for name, ids in cases.items()}
    report["credit_refunds_split_across_payments"] = {
        "count": sum(1 for n in multi_payment_refunds.values() if n > 1)}
    report["payments_with_unapplied_credit"] = {
        "count": sum(1 for p in t["payments"] if allocs[p["payment_id"]] < p["amount"])}
    return report
