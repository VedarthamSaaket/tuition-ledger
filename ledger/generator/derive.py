from collections import defaultdict

from ..domain import rules
from ..domain.catalog import AS_OF

ENTRY_TYPE = {"CHARGE": "CHARGE", "LATE_FEE": "LATE_FEE", "SCHOLARSHIP": "SCHOLARSHIP", "WAIVER": "WAIVER",
              "REVERSAL": "REVERSAL"}


def group(rows: list[dict], key: str) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for row in rows:
        out[row[key]].append(row)
    return out


def derive_invoices(tables: dict) -> None:
    lines = group(tables["invoice_lines"], "invoice_id")
    allocs = group(tables["payment_allocations"], "invoice_id")
    refunds = group([r for r in tables["refunds"] if r["invoice_id"]], "invoice_id")
    enrollments = {e["enrollment_id"]: e for e in tables["enrollments"]}
    for inv in tables["invoices"]:
        summary = rules.summarize_invoice(lines[inv["invoice_id"]], allocs[inv["invoice_id"]],
                                          refunds[inv["invoice_id"]])
        cancelled = enrollments[inv["enrollment_id"]]["status"] == "CANCELLED"
        inv.update(summary)
        inv["status"] = rules.invoice_status(summary, inv["due_date"], AS_OF, cancelled)


def derive_payments(tables: dict) -> None:
    allocated = defaultdict(int)
    refunded = defaultdict(int)
    for a in tables["payment_allocations"]:
        allocated[a["payment_id"]] += a["amount"]
    for r in tables["refunds"]:
        refunded[r["payment_id"]] += r["amount"]
    for p in tables["payments"]:
        p["amount_allocated"] = allocated[p["payment_id"]]
        p["amount_refunded"] = refunded[p["payment_id"]]
        p["amount_unapplied"] = p["amount"] - p["amount_allocated"]


def build_ledger(tables: dict) -> list[dict]:
    invoices = {i["invoice_id"]: i for i in tables["invoices"]}
    raw = []
    for line in tables["invoice_lines"]:
        student = invoices[line["invoice_id"]]["student_id"]
        raw.append((student, line["posted_on"], 0, line["line_id"], ENTRY_TYPE[line["line_type"]],
                    line["invoice_id"], line["amount"]))
    for p in tables["payments"]:
        raw.append((p["student_id"], p["received_on"], 1, p["payment_id"], "PAYMENT", p["invoice_id"], -p["amount"]))
    for r in tables["refunds"]:
        raw.append((r["student_id"], r["refunded_on"], 2, r["refund_id"], "REFUND", r["invoice_id"], r["amount"]))
    raw.sort()
    entries = []
    running = {}
    seq = defaultdict(int)
    for student, on, _, source, kind, invoice, amount in raw:
        running[student] = running.get(student, 0) + amount
        seq[student] += 1
        entries.append({
            "entry_id": f"LED-{student}-{seq[student]:06d}", "student_id": student, "posted_on": on,
            "entry_type": kind, "source_id": source, "invoice_id": invoice, "amount": amount,
            "running_balance": running[student],
        })
    return entries


def build_accounts(tables: dict) -> list[dict]:
    totals = {s["student_id"]: defaultdict(int) for s in tables["students"]}
    for e in tables["ledger_entries"]:
        t = totals[e["student_id"]]
        if e["entry_type"] in ("CHARGE", "LATE_FEE"):
            t["billed"] += e["amount"]
        elif e["entry_type"] in ("SCHOLARSHIP", "WAIVER", "REVERSAL"):
            t["credits"] += -e["amount"]
        elif e["entry_type"] == "PAYMENT":
            t["paid"] += -e["amount"]
        else:
            t["refunded"] += e["amount"]
        t["balance"] += e["amount"]
    for p in tables["payments"]:
        totals[p["student_id"]]["unapplied"] += p["amount_unapplied"]
    for r in tables["refunds"]:
        if r["invoice_id"] is None:
            totals[r["student_id"]]["unapplied"] -= r["amount"]
    return [
        {"student_id": sid, "total_billed": t["billed"], "total_credits": t["credits"], "total_paid": t["paid"],
         "total_refunded": t["refunded"], "unapplied_credit": t["unapplied"], "balance": t["balance"], "as_of": AS_OF}
        for sid, t in totals.items()
    ]


def derive_all(tables: dict) -> None:
    derive_invoices(tables)
    derive_payments(tables)
    tables["ledger_entries"] = build_ledger(tables)
    tables["student_accounts"] = build_accounts(tables)
