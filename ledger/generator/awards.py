from ..domain import ids, rules
from ..domain.catalog import SCHEMES, TERMS_BY_ID
from .dataset import Dataset
from .enrollments import context

APPLY_TO_LIKELY_SCHEME = 0.8


def money(paise: int) -> str:
    return f"{paise / 100:.2f}"


def award_lines(ds: Dataset, invoice: dict, scheme, scholarship_id: str, splits) -> None:
    lines = ds.idx["lines"][invoice["invoice_id"]]
    for charge, amount in splits:
        no = len(lines) + 1
        lines.append(ds.add("invoice_lines", {
            "line_id": ids.invoice_line_id(invoice["invoice_id"], no), "invoice_id": invoice["invoice_id"],
            "line_no": no, "line_type": scheme.award_type, "fee_code": charge["fee_code"], "fee_schedule_id": None,
            "quantity": None, "unit_amount": None, "amount": -amount, "applies_to_line_id": charge["line_id"],
            "scholarship_id": scholarship_id, "posted_on": invoice["issue_date"],
            "description": f"{scheme.name} on {charge['fee_code']}",
        }))


def net_charges(lines: list[dict]) -> list[dict]:
    net = {line["line_id"]: dict(line) for line in lines if line["line_type"] == "CHARGE"}
    for line in lines:
        if line["applies_to_line_id"] in net:
            net[line["applies_to_line_id"]]["amount"] += line["amount"]
    return [line for line in net.values() if line["amount"] > 0]


def assess(ds: Dataset, enr: dict, student: dict, program: dict, scheme, invoice: dict) -> None:
    term = TERMS_BY_ID[enr["term_id"]]
    ctx = context(student, program, enr["credits"])
    eligible, passed, failed = rules.assess_eligibility(scheme, ctx)
    elg_id = ids.eligibility_id(term.year, ds.counter.next(("eligibility", term.year)))
    on = invoice["issue_date"]
    ds.add("eligibility", {
        "eligibility_id": elg_id, "student_id": student["student_id"], "enrollment_id": enr["enrollment_id"],
        "scheme_id": scheme.scheme_id, "assessed_on": on, "gpa": student["gpa"],
        "income_band": student["income_band"], "credits": enr["credits"], "is_eligible": eligible,
        "passed_criteria": "|".join(passed) or None, "failed_criteria": "|".join(failed) or None,
    })
    explanation = "met " + ", ".join(passed) if eligible else "failed " + ", ".join(failed)
    ds.decision("RULE-ELIGIBILITY", "ELIGIBILITY", elg_id, "ELIGIBLE" if eligible else "INELIGIBLE", on,
                f"{scheme.scheme_id}: {explanation}")
    if not eligible:
        return
    charges = net_charges(ds.idx["lines"][invoice["invoice_id"]])
    award, base, splits = rules.compute_award(scheme, charges)
    if award <= 0:
        ds.decision("RULE-AWARD-AMOUNT", "ELIGIBILITY", elg_id, "NO_ELIGIBLE_FEES", on,
                    f"{scheme.scheme_id} covers {', '.join(scheme.fee_codes)} and none are billed", 0)
        return
    sch_id = ids.scholarship_id(term.year, ds.counter.next(("scholarship", term.year)))
    status = "CANCELLED" if enr["status"] == "CANCELLED" else "AWARDED"
    ds.add("scholarships", {
        "scholarship_id": sch_id, "eligibility_id": elg_id, "student_id": student["student_id"],
        "invoice_id": invoice["invoice_id"], "scheme_id": scheme.scheme_id, "award_type": scheme.award_type,
        "eligible_fee_base": base, "award_amount": award, "awarded_on": on, "status": status,
    })
    award_lines(ds, invoice, scheme, sch_id, splits)
    ds.event("SCHOLARSHIP", sch_id, "AWARDED", None, "AWARDED", on, "academic_admin", scheme.scheme_id)
    if status == "CANCELLED":
        ds.event("SCHOLARSHIP", sch_id, "CANCELLED", "AWARDED", "CANCELLED", enr["exit_date"], "academic_admin",
                 "enrollment cancelled")
    if scheme.basis == "PERCENT":
        detail = f"{scheme.value} percent of eligible fees {money(base)}"
    else:
        detail = f"fixed {money(scheme.value)} against eligible fees {money(base)}"
    capped = award < (rules.percent_of(base, scheme.value) if scheme.basis == "PERCENT" else scheme.value)
    outcome = "CAPPED" if capped else "AWARDED"
    if capped:
        detail += f", capped to {money(award)}"
    ds.decision("RULE-AWARD-AMOUNT", "SCHOLARSHIP", sch_id, outcome, on, detail, award)


def build_awards(ds: Dataset, target: int) -> None:
    rng = ds.rng
    students = {s["student_id"]: s for s in ds.tables["students"]}
    programs = {p["program_id"]: p for p in ds.tables["programs"]}
    order = list(ds.tables["enrollments"])
    rng.shuffle(order)
    applied: dict[str, set] = {}
    for award_round in (1, 2):
        for enr in order:
            if len(ds.tables["scholarships"]) >= target:
                return
            student = students[enr["student_id"]]
            program = programs[enr["program_id"]]
            ctx = context(student, program, enr["credits"])
            taken = applied.setdefault(enr["enrollment_id"], set())
            pool = [s for s in SCHEMES if s.award_type not in taken]
            if award_round == 2 and not taken:
                continue
            likely = [s for s in pool if rules.assess_eligibility(s, ctx)[0]]
            if likely and rng.random() < APPLY_TO_LIKELY_SCHEME:
                scheme = rng.choice(likely)
            elif award_round == 1:
                scheme = rng.choice(pool)
            else:
                continue
            taken.add(scheme.award_type)
            assess(ds, enr, student, program, scheme, ds.idx["invoice_by_enrollment"][enr["enrollment_id"]])
