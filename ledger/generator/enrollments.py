import math
from collections import defaultdict
from datetime import timedelta

from ..domain import catalog, ids, rules
from ..domain.catalog import AS_OF, TERMS_BY_ID
from .dataset import Dataset

SUMMER_WEIGHT = 0.35
CANCEL_RATE = 0.015
WITHDRAW_RATE = 0.04


def term_order(term_id: str) -> int:
    return [t.term_id for t in catalog.TERMS].index(term_id)


def choose_pairs(ds: Dataset, target: int) -> list[tuple[dict, str]]:
    rng = ds.rng
    students = ds.tables["students"]
    if target < len(students):
        raise ValueError("need at least one enrollment per student")
    chosen = [(s, s["admit_term_id"]) for s in students]
    keyed = []
    for s in students:
        for t in catalog.TERMS[term_order(s["admit_term_id"]) + 1:]:
            weight = SUMMER_WEIGHT if t.season == "SUMMER" else 1.0
            keyed.append((math.log(rng.random()) / weight, s["student_id"], t.term_id, s))
    extra = target - len(students)
    if extra > len(keyed):
        raise ValueError(f"cannot place {target} enrollments for {len(students)} students")
    keyed.sort(key=lambda k: (-k[0], k[1], k[2]))
    chosen += [(s, term) for _, _, term, s in keyed[:extra]]
    chosen.sort(key=lambda pair: (pair[0]["student_id"], term_order(pair[1])))
    return chosen


def pick_credits(rng, level: str, season: str) -> int:
    threshold = catalog.FULL_TIME_CREDITS[level]
    if season == "SUMMER":
        return rng.randint(3, 9)
    if rng.random() < 0.78:
        return rng.randint(threshold, 18 if threshold == 12 else 12)
    return rng.randint(3, threshold - 1)


def context(student: dict, program: dict, credits: int) -> rules.StudentContext:
    return rules.StudentContext(
        level=program["level"], department=program["department"], residency=student["residency"],
        income_band=student["income_band"], gpa=student["gpa"], credits=credits, has_lab=program["has_lab"],
        has_external_cover=student["has_external_cover"], staff_dependent=student["staff_dependent"],
    )


def lifecycle(ds: Dataset, enr: dict) -> None:
    rng = ds.rng
    term = TERMS_BY_ID[enr["term_id"]]
    eid = enr["enrollment_id"]
    ds.event("ENROLLMENT", eid, "REGISTERED", None, "REGISTERED", enr["registered_on"], "learner")
    roll = rng.random()
    exit_date = None
    if roll < CANCEL_RATE:
        span = (term.start_date - enr["registered_on"]).days - 1
        exit_date = enr["registered_on"] + timedelta(days=rng.randint(1, max(1, span)))
        enr.update(status="CANCELLED", status_on=exit_date, exit_date=exit_date, refund_percent=100)
        ds.event("ENROLLMENT", eid, "CANCELLED", "REGISTERED", "CANCELLED", exit_date, "academic_admin")
        ds.decision("RULE-WITHDRAWAL-REFUND", "ENROLLMENT", eid, "REFUND_100_PERCENT", exit_date,
                    "cancelled before the term started so every charge is reversed")
        return
    ds.event("ENROLLMENT", eid, "ACTIVATED", "REGISTERED", "ACTIVE", term.start_date)
    if roll < CANCEL_RATE + WITHDRAW_RATE:
        candidate = term.start_date + timedelta(days=rng.randint(1, 70))
        if candidate <= min(term.end_date, AS_OF):
            exit_date = candidate
    if exit_date:
        pct = rules.withdrawal_refund_percent(term.start_date, exit_date)
        enr.update(status="WITHDRAWN", status_on=exit_date, exit_date=exit_date, refund_percent=pct)
        ds.event("ENROLLMENT", eid, "WITHDRAWN", "ACTIVE", "WITHDRAWN", exit_date, "academic_admin")
        days = (exit_date - term.start_date).days
        ds.decision("RULE-WITHDRAWAL-REFUND", "ENROLLMENT", eid, f"REFUND_{pct}_PERCENT", exit_date,
                    f"withdrew {days} days after term start, tuition refund schedule gives {pct} percent")
    elif term.end_date < AS_OF:
        enr.update(status="COMPLETED", status_on=term.end_date)
        ds.event("ENROLLMENT", eid, "COMPLETED", "ACTIVE", "COMPLETED", term.end_date)
    else:
        enr.update(status="ACTIVE", status_on=term.start_date)


def charge_description(line: dict) -> str:
    if line["fee_code"] in catalog.PER_CREDIT_CODES:
        return f"{line['fee_code']} {line['quantity']} credits at {line['unit_amount'] / 100:.2f}"
    return line["fee_code"]


def issue_invoice(ds: Dataset, enr: dict, student: dict, program: dict, schedules: dict) -> dict:
    term = TERMS_BY_ID[enr["term_id"]]
    n = ds.counter.next(("invoice", student["student_id"], term.year))
    inv_id = ids.invoice_id(student["student_id"], term.year, n)
    invoice = ds.add("invoices", {
        "invoice_id": inv_id, "student_id": student["student_id"], "enrollment_id": enr["enrollment_id"],
        "term_id": term.term_id, "issue_date": term.invoice_date, "due_date": term.due_date,
    })
    rows = rules.schedule_in_effect(schedules[(program["program_id"], term.term_id)], term.invoice_date)
    charges = rules.build_charge_lines(rows, context(student, program, enr["credits"]))
    lines = []
    for no, charge in enumerate(charges, start=1):
        lines.append(ds.add("invoice_lines", {
            "line_id": ids.invoice_line_id(inv_id, no), "invoice_id": inv_id, "line_no": no,
            "line_type": "CHARGE", "fee_code": charge["fee_code"], "fee_schedule_id": charge["fee_schedule_id"],
            "quantity": charge["quantity"], "unit_amount": charge["unit_amount"], "amount": charge["amount"],
            "applies_to_line_id": None, "scholarship_id": None, "posted_on": term.invoice_date,
            "description": charge_description(charge),
        }))
    ds.idx["lines"][inv_id] = lines
    return invoice


def build_enrollments_and_invoices(ds: Dataset, target: int) -> None:
    rng = ds.rng
    programs = {p["program_id"]: p for p in ds.tables["programs"]}
    schedules = defaultdict(list)
    for row in ds.tables["fee_schedules"]:
        schedules[(row["program_id"], row["term_id"])].append(row)
    ds.idx["lines"] = {}
    ds.idx["invoice_by_enrollment"] = {}
    for student, term_id in choose_pairs(ds, target):
        program = programs[student["program_id"]]
        term = TERMS_BY_ID[term_id]
        credits = pick_credits(rng, program["level"], term.season)
        enr = ds.add("enrollments", {
            "enrollment_id": ids.enrollment_id(student["student_id"], term_id),
            "student_id": student["student_id"], "program_id": program["program_id"], "term_id": term_id,
            "credits": credits,
            "load": "FULL_TIME" if rules.is_full_time(program["level"], credits) else "PART_TIME",
            "registered_on": term.invoice_date - timedelta(days=rng.randint(5, 40)),
            "status": None, "status_on": None, "exit_date": None, "refund_percent": None,
        })
        lifecycle(ds, enr)
        invoice = issue_invoice(ds, enr, student, program, schedules)
        ds.idx["invoice_by_enrollment"][enr["enrollment_id"]] = invoice
