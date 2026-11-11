from datetime import timedelta

from ..domain import ids, rules
from ..domain.catalog import AS_OF
from .dataset import Dataset
from .profile import anomaly_count


def label(ds: Dataset, issue_type: str, entity_type: str, entity_id: str, related: list[str], decision: str,
          value: int | None, description: str) -> None:
    ds.ground_truth.append({
        "issue_type": issue_type, "entity_type": entity_type, "entity_id": entity_id,
        "related_ids": "|".join(related) or None, "expected_decision": decision, "expected_value": value,
        "description": description,
    })


def clean_payments(ds: Dataset, exclude: set) -> list[dict]:
    exited = {e["enrollment_id"] for e in ds.tables["enrollments"] if e["exit_date"]}
    invoices = {i["invoice_id"]: i for i in ds.tables["invoices"]}
    refunded = {r["payment_id"] for r in ds.tables["refunds"]}
    allocated = {}
    for a in ds.tables["payment_allocations"]:
        allocated[a["payment_id"]] = allocated.get(a["payment_id"], 0) + a["amount"]
    return [
        p for p in ds.tables["payments"]
        if allocated.get(p["payment_id"], 0) == p["amount"] and p["payment_id"] not in refunded
        and p["payment_id"] not in exclude and invoices[p["invoice_id"]]["enrollment_id"] not in exited
        and p["received_on"] + timedelta(days=30) <= AS_OF
    ]


def over_allocate(ds: Dataset, n: int, used: set) -> None:
    rng = ds.rng
    lines = ds.idx["lines"]
    counts: dict[str, int] = {}
    for a in ds.tables["payment_allocations"]:
        counts[a["payment_id"]] = counts.get(a["payment_id"], 0) + 1
    for p in rng.sample(clean_payments(ds, used), n):
        used.add(p["payment_id"])
        charges = [line for line in lines[p["invoice_id"]] if line["line_type"] == "CHARGE"]
        target = charges[-1]
        extra = rng.randint(10, 500) * 100
        alloc_id = ids.allocation_id(p["payment_id"], counts[p["payment_id"]] + 1)
        ds.add("payment_allocations", {
            "allocation_id": alloc_id, "payment_id": p["payment_id"], "invoice_id": p["invoice_id"],
            "line_id": target["line_id"], "amount": extra, "allocated_on": p["received_on"],
        })
        label(ds, "ALLOCATION_EXCEEDS_PAYMENT", "PAYMENT", p["payment_id"], [alloc_id, p["invoice_id"]],
              "REJECT_EXCESS_ALLOCATION", extra,
              f"allocations total {(p['amount'] + extra) / 100:.2f} against a payment of {p['amount'] / 100:.2f}")


def over_award(ds: Dataset, n: int) -> None:
    rng = ds.rng
    exited = {e["enrollment_id"] for e in ds.tables["enrollments"] if e["exit_date"]}
    invoices = {i["invoice_id"]: i for i in ds.tables["invoices"]}
    credit_lines = {}
    for line in ds.tables["invoice_lines"]:
        if line["scholarship_id"]:
            credit_lines.setdefault(line["scholarship_id"], []).append(line)
    candidates = [
        s for s in ds.tables["scholarships"]
        if s["status"] == "AWARDED" and len(credit_lines[s["scholarship_id"]]) == 1
        and invoices[s["invoice_id"]]["enrollment_id"] not in exited
    ]
    for award in rng.sample(candidates, n):
        correct = award["award_amount"]
        extra = max(5000, rules.percent_of(award["eligible_fee_base"], rng.randint(5, 40)))
        award["award_amount"] = award["eligible_fee_base"] + extra
        line = credit_lines[award["scholarship_id"]][0]
        line["amount"] = -award["award_amount"]
        label(ds, "SCHOLARSHIP_EXCEEDS_ELIGIBLE", "SCHOLARSHIP", award["scholarship_id"],
              [award["invoice_id"], line["line_id"]], "CAP_AT_ELIGIBLE_FEES", correct,
              f"award {award['award_amount'] / 100:.2f} is above eligible fees {award['eligible_fee_base'] / 100:.2f}")


def duplicate_invoices(ds: Dataset, n: int) -> None:
    rng = ds.rng
    exited = {e["enrollment_id"] for e in ds.tables["enrollments"] if e["exit_date"]}
    candidates = [i for i in ds.tables["invoices"] if i["enrollment_id"] not in exited]
    for original in rng.sample(candidates, n):
        year = int(original["invoice_id"].split("-")[-2])
        new_id = ids.invoice_id(original["student_id"], year, ds.counter.next(("invoice", original["student_id"], year)))
        issued = original["issue_date"] + timedelta(days=rng.randint(0, 2))
        copy = {k: original[k] for k in ("student_id", "enrollment_id", "term_id", "due_date")}
        copy.update(invoice_id=new_id, issue_date=issued)
        ds.add("invoices", copy)
        mapping = {}
        new_lines = []
        for line in ds.idx["lines"][original["invoice_id"]]:
            if line["line_type"] not in ("CHARGE", "SCHOLARSHIP", "WAIVER"):
                continue
            no = len(new_lines) + 1
            clone = dict(line, line_id=ids.invoice_line_id(new_id, no), invoice_id=new_id, line_no=no, posted_on=issued)
            mapping[line["line_id"]] = clone["line_id"]
            new_lines.append(clone)
        for clone in new_lines:
            if clone["applies_to_line_id"]:
                clone["applies_to_line_id"] = mapping[clone["applies_to_line_id"]]
            ds.add("invoice_lines", clone)
        ds.idx["lines"][new_id] = new_lines
        net = sum(line["amount"] for line in new_lines)
        ds.event("INVOICE", new_id, "ISSUED", None, "UNPAID" if net > 0 else "PAID", issued, "system", "invoice issued")
        grace = rules.grace_end(original["due_date"])
        if net > 0 and grace <= AS_OF:
            ds.event("INVOICE", new_id, "STATUS_CHANGED", "UNPAID", "OVERDUE", grace, "system", "as of date")
        label(ds, "DUPLICATE_INVOICE", "INVOICE", new_id, [original["invoice_id"], original["enrollment_id"]],
              "VOID_DUPLICATE", net, f"second invoice for {original['enrollment_id']}, first was {original['invoice_id']}")


def excess_refunds(ds: Dataset, n: int, used: set) -> None:
    rng = ds.rng
    for p in rng.sample(clean_payments(ds, used), n):
        used.add(p["payment_id"])
        extra = rng.randint(10, 300) * 100
        on = min(AS_OF, p["received_on"] + timedelta(days=rng.randint(5, 30)))
        refund_id = ids.refund_id(on.year, ds.counter.next(("refund", on.year)))
        ds.add("refunds", {
            "refund_id": refund_id, "student_id": p["student_id"], "payment_id": p["payment_id"], "invoice_id": None,
            "reason": "OVERPAYMENT", "amount": p["amount"] + extra, "refunded_on": on,
        })
        ds.event("REFUND", refund_id, "ISSUED", None, "ISSUED", on, "support_staff", "OVERPAYMENT")
        label(ds, "REFUND_EXCEEDS_NET_PAID", "REFUND", refund_id, [p["payment_id"]], "REJECT_REFUND", p["amount"],
              f"refund {(p['amount'] + extra) / 100:.2f} against net paid {p['amount'] / 100:.2f}")


def inject_source_anomalies(ds: Dataset) -> None:
    p = ds.profile
    used: set = set()
    over_allocate(ds, anomaly_count(p, p.payments), used)
    over_award(ds, anomaly_count(p, p.scholarships))
    duplicate_invoices(ds, anomaly_count(p, p.invoices))
    excess_refunds(ds, anomaly_count(p, p.payments), used)


def inject_balance_drift(ds: Dataset) -> None:
    rng = ds.rng
    for acct in rng.sample(ds.tables["student_accounts"], anomaly_count(ds.profile, ds.profile.students)):
        correct = acct["balance"]
        drift = rng.choice((-1, 1)) * rng.randint(100, 50000)
        acct["balance"] = correct + drift
        label(ds, "BALANCE_LEDGER_MISMATCH", "STUDENT_ACCOUNT", acct["student_id"], [], "RECOMPUTE_FROM_LEDGER",
              correct, f"stored balance {acct['balance'] / 100:.2f} but ledger sums to {correct / 100:.2f}")


def finalize_ground_truth(ds: Dataset) -> None:
    for n, row in enumerate(ds.ground_truth, start=1):
        row["issue_id"] = f"GT-{n:06d}"
    order = ("issue_id", "issue_type", "entity_type", "entity_id", "related_ids", "expected_decision",
             "expected_value", "description")
    ds.ground_truth = [{k: row[k] for k in order} for row in ds.ground_truth]
