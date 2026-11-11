from datetime import date, timedelta

from ..domain import catalog, ids
from ..domain.rules import percent_of
from .dataset import Dataset

PROGRAMS = (
    ("BSc Computer Science", "UG", "STEM", True, 62000),
    ("BSc Data Science", "UG", "STEM", True, 64000),
    ("BEng Mechanical Engineering", "UG", "STEM", True, 66000),
    ("BSc Biology", "UG", "STEM", True, 55000),
    ("BBA Business Administration", "UG", "BUSINESS", False, 52000),
    ("BCom Accounting", "UG", "BUSINESS", False, 50000),
    ("BA Psychology", "UG", "ARTS", False, 46000),
    ("BA English Literature", "UG", "ARTS", False, 44000),
    ("BSc Nursing", "UG", "HEALTH", True, 58000),
    ("BA Graphic Design", "UG", "ARTS", True, 48000),
    ("MSc Artificial Intelligence", "PG", "STEM", True, 98000),
    ("MSc Cybersecurity", "PG", "STEM", False, 92000),
    ("MBA", "PG", "BUSINESS", False, 110000),
    ("MSc Finance", "PG", "BUSINESS", False, 95000),
    ("MPH Public Health", "PG", "HEALTH", False, 86000),
    ("MA Education", "PG", "ARTS", False, 78000),
    ("Diploma in Web Development", "DIP", "STEM", True, 38000),
    ("Diploma in Hospitality", "DIP", "BUSINESS", False, 34000),
    ("Certificate in Project Management", "CERT", "BUSINESS", False, 30000),
    ("Certificate in Medical Coding", "CERT", "HEALTH", False, 32000),
)

PROGRAM_WEIGHTS = {"UG": 6, "PG": 3, "DIP": 2, "CERT": 1}

FIRST = ("Aarav", "Maya", "Noah", "Zara", "Liam", "Priya", "Ethan", "Sofia", "Omar", "Chloe", "Ravi", "Emma",
         "Kenji", "Amara", "Lucas", "Nadia", "Mateo", "Isla", "Arjun", "Leah", "Yusuf", "Mia", "Diego", "Ana",
         "Kai", "Hana", "Felix", "Ines", "Samir", "Tara", "Jonah", "Elena", "Theo", "Aisha", "Ivan", "Lina")
LAST = ("Patel", "Garcia", "Kim", "Okafor", "Nguyen", "Smith", "Haddad", "Rossi", "Silva", "Chen", "Kowalski",
        "Mensah", "Novak", "Reddy", "Fischer", "Santos", "Ito", "Murphy", "Ali", "Dubois", "Larsen", "Mehta",
        "Costa", "Brown", "Sato", "Ahmed", "Moreau", "Jensen", "Varga", "Lopez")

TERM_RATE_FACTOR = {"TERM-2025-FALL": 100, "TERM-2026-SPRING": 100, "TERM-2026-SUMMER": 90, "TERM-2026-FALL": 105}
FLAT_FEES = {"TECH": 15000, "LIBRARY": 8000, "ACTIVITY": 12000, "LAB": 30000, "HEALTH_INSURANCE": 90000}
FEE_WHEN = {
    "TUITION": "ALL", "INTL_SURCHARGE": "INTL", "TECH": "ALL", "LIBRARY": "ALL", "ACTIVITY": "FULL_TIME",
    "LAB": "LAB_PROGRAM", "HEALTH_INSURANCE": "FULL_TIME_NO_COVER",
}
TECH_REVISION = ("TERM-2026-FALL", date(2026, 7, 1), 16500)
ADMIT_WEIGHTS = (("TERM-2025-FALL", 70), ("TERM-2026-SPRING", 15), ("TERM-2026-SUMMER", 3), ("TERM-2026-FALL", 12))


def build_terms(ds: Dataset) -> None:
    for t in catalog.TERMS:
        ds.add("terms", {
            "term_id": t.term_id, "name": t.name, "season": t.season, "year": t.year,
            "invoice_date": t.invoice_date, "start_date": t.start_date, "due_date": t.due_date,
            "end_date": t.end_date,
        })


def build_programs(ds: Dataset) -> None:
    for n, (name, level, dept, lab, rate) in enumerate(PROGRAMS[: ds.profile.programs], start=1):
        ds.add("programs", {
            "program_id": ids.program_id(n), "name": name, "level": level, "department": dept,
            "has_lab": lab, "full_time_credits": catalog.FULL_TIME_CREDITS[level], "status": "ACTIVE",
            "_rate": rate,
        })


def build_schemes(ds: Dataset) -> None:
    for s in catalog.SCHEMES:
        parts = []
        if s.levels:
            parts.append(f"level in {'/'.join(s.levels)}")
        if s.min_gpa is not None:
            parts.append(f"gpa >= {s.min_gpa}")
        if s.income_bands:
            parts.append(f"income in {'/'.join(s.income_bands)}")
        if s.residency:
            parts.append(f"residency in {'/'.join(s.residency)}")
        if s.departments:
            parts.append(f"department in {'/'.join(s.departments)}")
        if s.full_time_only:
            parts.append("full time load")
        if s.staff_dependent_only:
            parts.append("staff dependent")
        ds.add("scholarship_schemes", {
            "scheme_id": s.scheme_id, "name": s.name, "award_type": s.award_type, "basis": s.basis,
            "value": s.value, "cap": s.cap, "fee_codes": "|".join(s.fee_codes), "criteria": " and ".join(parts),
        })


def build_fee_schedules(ds: Dataset) -> None:
    for program in ds.tables["programs"]:
        for term in catalog.TERMS:
            factor = TERM_RATE_FACTOR[term.term_id]
            effective_from = term.invoice_date - timedelta(days=120)
            for code in catalog.FEE_CODES:
                if code == "LAB" and not program["has_lab"]:
                    continue
                if term.season == "SUMMER" and code in ("ACTIVITY", "HEALTH_INSURANCE"):
                    continue
                if code == "TUITION":
                    rate = percent_of(program["_rate"], factor)
                elif code == "INTL_SURCHARGE":
                    rate = percent_of(percent_of(program["_rate"], factor), 40)
                else:
                    rate = FLAT_FEES[code]
                basis = "PER_CREDIT" if code in catalog.PER_CREDIT_CODES else "FLAT"
                versions = [(effective_from, None, rate)]
                if code == "TECH" and term.term_id == TECH_REVISION[0]:
                    cut = TECH_REVISION[1]
                    versions = [(effective_from, cut - timedelta(days=1), rate), (cut, None, TECH_REVISION[2])]
                for v, (start, end, amount) in enumerate(versions, start=1):
                    ds.add("fee_schedules", {
                        "fee_schedule_id": ids.fee_schedule_id(program["program_id"], term.term_id, code, v),
                        "program_id": program["program_id"], "term_id": term.term_id, "fee_code": code,
                        "basis": basis, "rate": amount, "applies_when": FEE_WHEN[code], "version": v,
                        "effective_from": start, "effective_to": end,
                    })


def pick_weighted(rng, pairs):
    total = sum(w for _, w in pairs)
    roll = rng.uniform(0, total)
    upto = 0
    for value, weight in pairs:
        upto += weight
        if roll <= upto:
            return value
    return pairs[-1][0]


def build_students(ds: Dataset) -> None:
    rng = ds.rng
    program_pairs = [(p, PROGRAM_WEIGHTS[p["level"]]) for p in ds.tables["programs"]]
    for n in range(1, ds.profile.students + 1):
        sid = ids.student_id(n)
        first, last = rng.choice(FIRST), rng.choice(LAST)
        program = pick_weighted(rng, program_pairs)
        admit = pick_weighted(rng, ADMIT_WEIGHTS)
        gpa = round(min(4.0, max(1.8, rng.gauss(3.1, 0.45))), 2)
        ds.add("students", {
            "student_id": sid, "first_name": first, "last_name": last,
            "email": f"{first.lower()}.{last.lower()}.{n:06d}@students.example.edu",
            "program_id": program["program_id"], "admit_term_id": admit,
            "residency": "INTL" if rng.random() < 0.15 else "DOMESTIC",
            "income_band": pick_weighted(rng, (("LOW", 30), ("MEDIUM", 45), ("HIGH", 25))),
            "gpa": gpa, "has_external_cover": rng.random() < 0.35, "staff_dependent": rng.random() < 0.015,
            "created_on": catalog.TERMS_BY_ID[admit].invoice_date - timedelta(days=rng.randint(30, 120)),
        })


def build_masters(ds: Dataset) -> None:
    build_terms(ds)
    build_programs(ds)
    build_schemes(ds)
    build_fee_schedules(ds)
    build_students(ds)
