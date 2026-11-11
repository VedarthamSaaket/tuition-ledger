import heapq
from datetime import date, timedelta

from ..domain import ids, rules
from ..domain.catalog import AS_OF, PER_CREDIT_CODES
from .dataset import Dataset
from .masters import pick_weighted

BEHAVIOURS = (
    ("ON_TIME", 40), ("INSTALLMENTS", 22), ("PARTIAL", 12), ("LATE", 9), ("OVERPAY", 6), ("UNPAID", 8),
    ("SPONSOR", 3),
)
METHODS = (("CARD", 45), ("BANK_TRANSFER", 40), ("CHEQUE", 15))
MAX_COUNT = {"INSTALLMENTS": 6, "PARTIAL": 4}
CREDIT_REFUND_RATE = 0.9
OVERPAY_REFUND_RATE = 0.65


def initial_count(rng, behaviour: str) -> int:
    if behaviour in ("ON_TIME", "SPONSOR", "PAID_THEN_CANCELLED"):
        return 1
    if behaviour == "INSTALLMENTS":
        return rng.randint(2, 4)
    if behaviour == "PARTIAL":
        return rng.randint(1, 3)
    if behaviour in ("LATE", "OVERPAY"):
        return rng.randint(1, 2)
    return 0


def plan(ds: Dataset, target: int) -> dict[str, list]:
    rng = ds.rng
    enrollments = {e["enrollment_id"]: e for e in ds.tables["enrollments"]}
    plans = {}
    for inv in ds.tables["invoices"]:
        net = sum(line["amount"] for line in ds.idx["lines"][inv["invoice_id"]])
        enr = enrollments[inv["enrollment_id"]]
        if net <= 0:
            behaviour = "NOTHING_DUE"
        elif enr["status"] == "CANCELLED":
            behaviour = "PAID_THEN_CANCELLED" if rng.random() < 0.5 else "UNPAID"
        else:
            behaviour = pick_weighted(rng, BEHAVIOURS)
        plans[inv["invoice_id"]] = [behaviour, initial_count(rng, behaviour)]
    diff = target - sum(count for _, count in plans.values())
    keys = list(plans)
    rng.shuffle(keys)
    while diff > 0:
        moved = False
        for key in keys:
            behaviour, count = plans[key]
            if diff > 0 and behaviour in MAX_COUNT and count < MAX_COUNT[behaviour]:
                plans[key][1] += 1
                diff -= 1
                moved = True
        if not moved:
            raise ValueError("payment target too high for the invoice volume")
    while diff < 0:
        moved = False
        for key in keys:
            behaviour, count = plans[key]
            floor = 2 if behaviour == "INSTALLMENTS" else 1
            if diff < 0 and behaviour in MAX_COUNT and count > floor:
                plans[key][1] -= 1
                diff += 1
                moved = True
        if not moved:
            raise ValueError("payment target too low for the invoice volume")
    return plans


def window(behaviour: str, inv: dict, enr: dict) -> tuple[date, date]:
    issue, due = inv["issue_date"], inv["due_date"]
    grace = rules.grace_end(due)
    lo, hi = issue + timedelta(days=1), due
    if behaviour == "INSTALLMENTS":
        hi = grace - timedelta(days=1)
    elif behaviour == "PARTIAL":
        hi = due + timedelta(days=60)
    elif behaviour == "LATE":
        lo, hi = grace + timedelta(days=1), grace + timedelta(days=60)
    hi = min(hi, AS_OF)
    if enr["exit_date"]:
        hi = min(hi, enr["exit_date"] - timedelta(days=1))
    if hi < lo:
        lo = max(issue, hi)
        hi = max(hi, lo)
    return lo, hi


def random_dates(rng, lo: date, hi: date, k: int) -> list[date]:
    span = (hi - lo).days
    return sorted(lo + timedelta(days=rng.randint(0, span)) for _ in range(k))


def round_dollars(cents: int) -> int:
    return max(100, (cents // 100) * 100)


class InvoiceSim:
    def __init__(self, ds: Dataset, inv: dict, enr: dict) -> None:
        self.ds = ds
        self.inv = inv
        self.enr = enr
        self.lines = ds.idx["lines"][inv["invoice_id"]]
        self.allocs: list[dict] = []
        self.refunds: list[dict] = []
        self.payments: list[dict] = []
        self.cancelled = False
        self.status = None
        self.status_log: list[tuple] = []

    def balance(self) -> int:
        return rules.summarize_invoice(self.lines, self.allocs, self.refunds)["balance"]

    def update_status(self, on: date, reason: str) -> None:
        summary = rules.summarize_invoice(self.lines, self.allocs, self.refunds)
        status = rules.invoice_status(summary, self.inv["due_date"], on, self.cancelled)
        if status != self.status:
            self.status_log.append((on, self.status, status, reason))
            self.status = status

    def add_line(self, line_type: str, fee_code: str, amount: int, on: date, description: str,
                 applies_to: str | None = None) -> dict:
        no = len(self.lines) + 1
        line = {
            "line_id": ids.invoice_line_id(self.inv["invoice_id"], no), "invoice_id": self.inv["invoice_id"],
            "line_no": no, "line_type": line_type, "fee_code": fee_code, "fee_schedule_id": None,
            "quantity": None, "unit_amount": None, "amount": amount, "applies_to_line_id": applies_to,
            "scholarship_id": None, "posted_on": on, "description": description,
        }
        self.lines.append(self.ds.add("invoice_lines", line))
        return line

    def pay(self, on: date, amount: int, method: str) -> None:
        payment = {
            "payment_id": None, "student_id": self.inv["student_id"], "invoice_id": self.inv["invoice_id"],
            "received_on": on, "amount": amount, "method": method, "_allocs": [], "_refunded": 0,
        }
        opens = rules.line_open_amounts(self.lines, self.allocs)
        items = [
            {"line_id": line["line_id"], "fee_code": line["fee_code"], "open": opens[line["line_id"]]}
            for line in self.lines if line["line_id"] in opens
        ]
        taken, rest = rules.allocate(amount, items)
        for item, cents in taken:
            alloc = {"payment": payment, "invoice_id": self.inv["invoice_id"], "line_id": item["line_id"],
                     "amount": cents, "allocated_on": on}
            payment["_allocs"].append(alloc)
            self.allocs.append(alloc)
        payment["_unapplied"] = rest
        self.payments.append(payment)
        self.update_status(on, "payment received")

    def grace_check(self, on: date) -> None:
        if self.cancelled:
            return
        outstanding = self.balance()
        if outstanding <= 0:
            return
        fee = rules.late_fee_amount(outstanding)
        line = self.add_line("LATE_FEE", "LATE_FEE", fee, on,
                             f"late fee on overdue balance {outstanding / 100:.2f}")
        self.ds.decision("RULE-LATE-FEE", "INVOICE", self.inv["invoice_id"], "ASSESSED", on,
                         f"balance {outstanding / 100:.2f} unpaid at end of grace period, 1.5 percent "
                         f"bounded to 25.00 and 150.00 gives {fee / 100:.2f}, posted as {line['line_id']}", fee)
        self.update_status(on, "late fee assessed")

    def exit(self, on: date) -> None:
        pct = self.enr["refund_percent"] or 0
        cancel = self.enr["status"] == "CANCELLED"
        net = {line["line_id"]: line["amount"] for line in self.lines if line["line_type"] == "CHARGE"}
        for line in self.lines:
            if line["applies_to_line_id"] in net:
                net[line["applies_to_line_id"]] += line["amount"]
        for line in list(self.lines):
            if line["line_type"] != "CHARGE" or net[line["line_id"]] <= 0:
                continue
            if not cancel and line["fee_code"] not in PER_CREDIT_CODES:
                continue
            amount = rules.percent_of(net[line["line_id"]], pct)
            if amount <= 0:
                continue
            word = "cancellation" if cancel else f"withdrawal {pct} percent"
            self.add_line("REVERSAL", line["fee_code"], -amount, on, f"{word} reversal of {line['fee_code']}",
                          line["line_id"])
        self.cancelled = cancel
        self.update_status(on, "enrollment cancelled" if cancel else "enrollment withdrawn")

    def refund(self, payment: dict, amount: int, on: date, reason: str, invoice_id: str | None) -> None:
        payment["_refunded"] += amount
        refund = {"refund_id": None, "student_id": self.inv["student_id"], "payment": payment,
                  "invoice_id": invoice_id, "reason": reason, "amount": amount, "refunded_on": on}
        if invoice_id:
            self.refunds.append(refund)
        self.ds.idx["refunds"].append(refund)
        self.update_status(on, f"{reason.lower()} refund")

    def settle_credit(self, on: date) -> None:
        credit = -self.balance()
        if credit <= 0:
            return
        reason = "CANCELLATION" if self.cancelled else "WITHDRAWAL"
        for payment in sorted(self.payments, key=lambda p: p["received_on"], reverse=True):
            take = min(credit, payment["amount"] - payment["_refunded"])
            if take > 0:
                self.refund(payment, take, on, reason, self.inv["invoice_id"])
                credit -= take
            if credit <= 0:
                break

    def refund_overpayment(self, payment: dict, on: date) -> None:
        spare = min(payment["_unapplied"], payment["amount"] - payment["_refunded"])
        if spare > 0:
            self.refund(payment, spare, on, "OVERPAYMENT", None)


def payment_amount(behaviour: str, i: int, count: int, remaining: int, plan_values: dict) -> int:
    last = i == count - 1
    if behaviour == "PARTIAL":
        return round_dollars(plan_values["partial_total"] // count)
    if behaviour == "OVERPAY" and count == 2 and last:
        return plan_values["previous"]
    if behaviour == "OVERPAY" and count == 1:
        return remaining + plan_values["extra"]
    if last or behaviour == "OVERPAY":
        return remaining
    return round_dollars(remaining // (count - i))


def run_invoice(ds: Dataset, inv: dict, enr: dict, behaviour: str, count: int) -> None:
    rng = ds.rng
    sim = InvoiceSim(ds, inv, enr)
    sim.update_status(inv["issue_date"], "invoice issued")
    dates = random_dates(rng, *window(behaviour, inv, enr), count)
    method = "SPONSOR" if behaviour == "SPONSOR" else pick_weighted(rng, METHODS)
    values = {"partial_total": rules.percent_of(sim.balance(), rng.randint(30, 90)),
              "extra": rng.randint(50, 600) * 100, "previous": None}
    queue: list = []
    seq = 0

    def push(on: date, order: int, kind: str, data=None) -> None:
        nonlocal seq
        seq += 1
        heapq.heappush(queue, (on, order, seq, kind, data))

    for i, d in enumerate(dates):
        push(d, 1, "PAY", i)
    grace = rules.grace_end(inv["due_date"])
    if grace <= AS_OF:
        push(grace, 2, "GRACE")
    if enr["exit_date"]:
        push(enr["exit_date"], 0, "EXIT")
        settle_on = enr["exit_date"] + timedelta(days=rng.randint(3, 14))
        if settle_on <= AS_OF and rng.random() < CREDIT_REFUND_RATE:
            push(settle_on, 3, "SETTLE")
    while queue:
        on, _, _, kind, data = heapq.heappop(queue)
        if kind == "GRACE":
            sim.grace_check(on)
        elif kind == "EXIT":
            sim.exit(on)
        elif kind == "SETTLE":
            sim.settle_credit(on)
        elif kind == "OVERPAY_REFUND":
            sim.refund_overpayment(data, on)
        else:
            amount = payment_amount(behaviour, data, count, max(sim.balance(), 100), values)
            values["previous"] = amount
            sim.pay(on, amount, method)
            payment = sim.payments[-1]
            if payment["_unapplied"] > 0 and rng.random() < OVERPAY_REFUND_RATE:
                refund_on = on + timedelta(days=rng.randint(5, 20))
                if refund_on <= AS_OF:
                    push(refund_on, 3, "OVERPAY_REFUND", payment)
    sim.update_status(AS_OF, "as of date")
    ds.idx["sims"][inv["invoice_id"]] = sim


def assign_ids(ds: Dataset) -> None:
    payments = [p for sim in ds.idx["sims"].values() for p in sim.payments]
    payments.sort(key=lambda p: (p["received_on"], p["invoice_id"]))
    for p in payments:
        year = p["received_on"].year
        p["payment_id"] = ids.payment_id(year, ds.counter.next(("payment", year)))
        for n, alloc in enumerate(p["_allocs"], start=1):
            alloc["allocation_id"] = ids.allocation_id(p["payment_id"], n)
            alloc["payment_id"] = p["payment_id"]
        ds.add("payments", p)
        ds.event("PAYMENT", p["payment_id"], "RECEIVED", None, "RECEIVED", p["received_on"],
                 "learner" if p["method"] != "SPONSOR" else "support_staff", f"{p['amount'] / 100:.2f}")
        if p["_unapplied"] > 0:
            ds.decision("RULE-ALLOCATION", "PAYMENT", p["payment_id"], "UNAPPLIED_CREDIT", p["received_on"],
                        f"payment exceeded open lines, {p['_unapplied'] / 100:.2f} held as student credit",
                        p["_unapplied"])
    for p in payments:
        for alloc in p["_allocs"]:
            ds.add("payment_allocations", {k: alloc[k] for k in (
                "allocation_id", "payment_id", "invoice_id", "line_id", "amount", "allocated_on")})
    refunds = sorted(ds.idx["refunds"], key=lambda r: (r["refunded_on"], r["payment"]["payment_id"]))
    for r in refunds:
        year = r["refunded_on"].year
        r["refund_id"] = ids.refund_id(year, ds.counter.next(("refund", year)))
        r["payment_id"] = r["payment"]["payment_id"]
        ds.add("refunds", {k: r[k] for k in (
            "refund_id", "student_id", "payment_id", "invoice_id", "reason", "amount", "refunded_on")})
        ds.event("REFUND", r["refund_id"], "ISSUED", None, "ISSUED", r["refunded_on"], "support_staff", r["reason"])
        ds.decision("RULE-REFUND-LIMIT", "REFUND", r["refund_id"], "APPROVED", r["refunded_on"],
                    f"{r['reason'].lower()} refund within net paid on {r['payment_id']}", r["amount"])
    for sim in ds.idx["sims"].values():
        prev = None
        for on, before, after, reason in sim.status_log:
            ds.event("INVOICE", sim.inv["invoice_id"], "ISSUED" if before is None else "STATUS_CHANGED",
                     before, after, on, "system", reason)
            prev = after
        sim.inv["_status"] = prev


def build_billing(ds: Dataset, target: int) -> None:
    ds.idx["sims"] = {}
    ds.idx["refunds"] = []
    enrollments = {e["enrollment_id"]: e for e in ds.tables["enrollments"]}
    plans = plan(ds, target)
    for inv in ds.tables["invoices"]:
        behaviour, count = plans[inv["invoice_id"]]
        run_invoice(ds, inv, enrollments[inv["enrollment_id"]], behaviour, count)
    assign_ids(ds)
