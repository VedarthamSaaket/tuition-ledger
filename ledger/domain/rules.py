from dataclasses import dataclass
from datetime import date, timedelta

from .catalog import (
    CHARGEABLE_LINE_TYPES,
    FEE_PRIORITY,
    FULL_TIME_CREDITS,
    LATE_FEE_GRACE_DAYS,
    LATE_FEE_MAX,
    LATE_FEE_MIN,
    LATE_FEE_RATE_BP,
    PER_CREDIT_CODES,
    WITHDRAWAL_SCHEDULE,
    Scheme,
)


@dataclass(frozen=True)
class StudentContext:
    level: str
    department: str
    residency: str
    income_band: str
    gpa: float
    credits: int
    has_lab: bool
    has_external_cover: bool
    staff_dependent: bool

    @property
    def full_time(self) -> bool:
        return is_full_time(self.level, self.credits)


def percent_of(amount: int, pct: int) -> int:
    return (amount * pct + 50) // 100


def is_full_time(level: str, credits: int) -> bool:
    return credits >= FULL_TIME_CREDITS[level]


def fee_applies(applies_when: str, ctx: StudentContext) -> bool:
    if applies_when == "ALL":
        return True
    if applies_when == "INTL":
        return ctx.residency == "INTL"
    if applies_when == "FULL_TIME":
        return ctx.full_time
    if applies_when == "LAB_PROGRAM":
        return ctx.has_lab
    if applies_when == "FULL_TIME_NO_COVER":
        return ctx.full_time and not ctx.has_external_cover
    raise ValueError(f"unknown applies_when {applies_when}")


def schedule_in_effect(rows: list[dict], on: date) -> list[dict]:
    return [
        r for r in rows
        if r["effective_from"] <= on and (r["effective_to"] is None or on <= r["effective_to"])
    ]


def build_charge_lines(schedule_rows: list[dict], ctx: StudentContext) -> list[dict]:
    lines = []
    for row in sorted(schedule_rows, key=lambda r: FEE_PRIORITY[r["fee_code"]]):
        if not fee_applies(row["applies_when"], ctx):
            continue
        quantity = ctx.credits if row["fee_code"] in PER_CREDIT_CODES else 1
        lines.append({
            "fee_code": row["fee_code"],
            "fee_schedule_id": row["fee_schedule_id"],
            "quantity": quantity,
            "unit_amount": row["rate"],
            "amount": quantity * row["rate"],
        })
    return lines


def assess_eligibility(scheme: Scheme, ctx: StudentContext) -> tuple[bool, list[str], list[str]]:
    checks = []
    if scheme.levels:
        checks.append((f"level in {'/'.join(scheme.levels)}", ctx.level in scheme.levels))
    if scheme.min_gpa is not None:
        checks.append((f"gpa >= {scheme.min_gpa}", ctx.gpa >= scheme.min_gpa))
    if scheme.income_bands:
        checks.append((f"income in {'/'.join(scheme.income_bands)}", ctx.income_band in scheme.income_bands))
    if scheme.residency:
        checks.append((f"residency in {'/'.join(scheme.residency)}", ctx.residency in scheme.residency))
    if scheme.departments:
        checks.append((f"department in {'/'.join(scheme.departments)}", ctx.department in scheme.departments))
    if scheme.full_time_only:
        checks.append(("full time load", ctx.full_time))
    if scheme.staff_dependent_only:
        checks.append(("staff dependent", ctx.staff_dependent))
    passed = [name for name, ok in checks if ok]
    failed = [name for name, ok in checks if not ok]
    return not failed, passed, failed


def eligible_lines(scheme: Scheme, charge_lines: list[dict]) -> list[dict]:
    order = {code: i for i, code in enumerate(scheme.fee_codes)}
    picked = [line for line in charge_lines if line["fee_code"] in order]
    return sorted(picked, key=lambda line: order[line["fee_code"]])


def compute_award(scheme: Scheme, charge_lines: list[dict]) -> tuple[int, int, list[tuple[dict, int]]]:
    targets = eligible_lines(scheme, charge_lines)
    eligible_base = sum(line["amount"] for line in targets)
    if scheme.basis == "PERCENT":
        wanted = [(line, percent_of(line["amount"], scheme.value)) for line in targets]
        budget = sum(amount for _, amount in wanted)
    else:
        wanted = [(line, line["amount"]) for line in targets]
        budget = scheme.value
    if scheme.cap is not None:
        budget = min(budget, scheme.cap)
    budget = min(budget, eligible_base)
    splits = []
    remaining = budget
    for line, amount in wanted:
        take = min(amount, remaining)
        if take > 0:
            splits.append((line, take))
            remaining -= take
    return budget, eligible_base, splits


def allocate(amount: int, open_items: list[dict]) -> tuple[list[tuple[dict, int]], int]:
    result = []
    remaining = amount
    for item in sorted(open_items, key=lambda i: (FEE_PRIORITY[i["fee_code"]], i["line_id"])):
        if remaining <= 0:
            break
        if item["open"] <= 0:
            continue
        take = min(item["open"], remaining)
        result.append((item, take))
        remaining -= take
    return result, remaining


def grace_end(due: date) -> date:
    return due + timedelta(days=LATE_FEE_GRACE_DAYS)


def late_fee_amount(overdue: int) -> int:
    if overdue <= 0:
        return 0
    fee = (overdue * LATE_FEE_RATE_BP + 5000) // 10000
    return max(LATE_FEE_MIN, min(LATE_FEE_MAX, fee))


def withdrawal_refund_percent(term_start: date, on: date) -> int:
    if on < term_start:
        return 100
    days = (on - term_start).days
    for limit, pct in WITHDRAWAL_SCHEDULE:
        if days <= limit:
            return pct
    return 0


def refund_decision(amount: int, net_paid: int, available_credit: int) -> tuple[bool, str]:
    if amount <= 0:
        return False, "refund amount must be positive"
    if amount > net_paid:
        return False, f"refund {amount} exceeds net paid {net_paid}"
    if amount > available_credit:
        return False, f"refund {amount} exceeds available credit {available_credit}"
    return True, "approved"


def line_open_amounts(lines: list[dict], allocations: list[dict]) -> dict[str, int]:
    open_amounts = {
        line["line_id"]: line["amount"] for line in lines if line["line_type"] in CHARGEABLE_LINE_TYPES
    }
    for line in lines:
        target = line.get("applies_to_line_id")
        if target in open_amounts:
            open_amounts[target] += line["amount"]
    for alloc in allocations:
        if alloc["line_id"] in open_amounts:
            open_amounts[alloc["line_id"]] -= alloc["amount"]
    return open_amounts


def summarize_invoice(lines: list[dict], allocations: list[dict], refunds: list[dict]) -> dict:
    charges = sum(line["amount"] for line in lines if line["line_type"] in CHARGEABLE_LINE_TYPES)
    credits = -sum(line["amount"] for line in lines if line["line_type"] in ("SCHOLARSHIP", "WAIVER"))
    reversals = -sum(line["amount"] for line in lines if line["line_type"] == "REVERSAL")
    net = charges - credits - reversals
    allocated = sum(a["amount"] for a in allocations)
    refunded = sum(r["amount"] for r in refunds)
    return {
        "total_charges": charges,
        "total_credits": credits,
        "total_reversals": reversals,
        "net_amount": net,
        "amount_allocated": allocated,
        "amount_refunded": refunded,
        "balance": net - allocated + refunded,
    }


def invoice_status(summary: dict, due: date, as_of: date, cancelled: bool) -> str:
    if cancelled:
        return "CANCELLED"
    if summary["balance"] < 0:
        return "IN_CREDIT"
    if summary["balance"] == 0:
        return "PAID"
    if as_of > grace_end(due):
        return "OVERDUE"
    if summary["amount_allocated"] > 0:
        return "PARTIALLY_PAID"
    return "UNPAID"
