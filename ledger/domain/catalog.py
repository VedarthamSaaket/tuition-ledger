from dataclasses import dataclass
from datetime import date

FEE_PRIORITY = {
    "TECH": 1,
    "LIBRARY": 2,
    "ACTIVITY": 3,
    "LAB": 4,
    "HEALTH_INSURANCE": 5,
    "INTL_SURCHARGE": 6,
    "TUITION": 7,
    "LATE_FEE": 8,
}

FEE_CODES = tuple(code for code in FEE_PRIORITY if code != "LATE_FEE")
PER_CREDIT_CODES = ("TUITION", "INTL_SURCHARGE")
APPLIES_WHEN = ("ALL", "INTL", "FULL_TIME", "LAB_PROGRAM", "FULL_TIME_NO_COVER")

LINE_TYPES = ("CHARGE", "SCHOLARSHIP", "WAIVER", "LATE_FEE", "REVERSAL")
CHARGEABLE_LINE_TYPES = ("CHARGE", "LATE_FEE")

LEVELS = ("UG", "PG", "DIP", "CERT")
FULL_TIME_CREDITS = {"UG": 12, "PG": 9, "DIP": 12, "CERT": 9}

RESIDENCY = ("DOMESTIC", "INTL")
INCOME_BANDS = ("LOW", "MEDIUM", "HIGH")

ENROLLMENT_STATES = ("REGISTERED", "ACTIVE", "COMPLETED", "WITHDRAWN", "CANCELLED")
ENROLLMENT_TRANSITIONS = {
    None: {"REGISTERED"},
    "REGISTERED": {"ACTIVE", "CANCELLED"},
    "ACTIVE": {"COMPLETED", "WITHDRAWN"},
    "COMPLETED": set(),
    "WITHDRAWN": set(),
    "CANCELLED": set(),
}

INVOICE_STATES = ("UNPAID", "PARTIALLY_PAID", "PAID", "OVERDUE", "IN_CREDIT", "CANCELLED")
INVOICE_TRANSITIONS = {
    None: {"UNPAID", "PAID"},
    "UNPAID": {"PARTIALLY_PAID", "PAID", "OVERDUE", "IN_CREDIT", "CANCELLED"},
    "PARTIALLY_PAID": {"PAID", "OVERDUE", "IN_CREDIT", "CANCELLED", "UNPAID"},
    "OVERDUE": {"PARTIALLY_PAID", "PAID", "IN_CREDIT", "CANCELLED"},
    "PAID": {"IN_CREDIT", "PARTIALLY_PAID", "OVERDUE", "CANCELLED"},
    "IN_CREDIT": {"PAID", "PARTIALLY_PAID", "OVERDUE", "CANCELLED"},
    "CANCELLED": set(),
}

PAYMENT_METHODS = ("CARD", "BANK_TRANSFER", "SPONSOR", "CHEQUE")
REFUND_REASONS = ("OVERPAYMENT", "WITHDRAWAL", "CANCELLATION")

LATE_FEE_GRACE_DAYS = 14
LATE_FEE_RATE_BP = 150
LATE_FEE_MIN = 2500
LATE_FEE_MAX = 15000

WITHDRAWAL_SCHEDULE = ((14, 80), (35, 50))

ISSUE_TYPES = (
    "ALLOCATION_EXCEEDS_PAYMENT",
    "SCHOLARSHIP_EXCEEDS_ELIGIBLE",
    "DUPLICATE_INVOICE",
    "REFUND_EXCEEDS_NET_PAID",
    "BALANCE_LEDGER_MISMATCH",
)


@dataclass(frozen=True)
class Term:
    term_id: str
    name: str
    season: str
    year: int
    start_date: date
    end_date: date
    invoice_date: date
    due_date: date


TERMS = (
    Term("TERM-2025-FALL", "Fall 2025", "FALL", 2025, date(2025, 8, 25), date(2025, 12, 12),
         date(2025, 7, 25), date(2025, 9, 1)),
    Term("TERM-2026-SPRING", "Spring 2026", "SPRING", 2026, date(2026, 1, 12), date(2026, 5, 1),
         date(2025, 12, 12), date(2026, 1, 19)),
    Term("TERM-2026-SUMMER", "Summer 2026", "SUMMER", 2026, date(2026, 5, 18), date(2026, 8, 7),
         date(2026, 4, 17), date(2026, 5, 25)),
    Term("TERM-2026-FALL", "Fall 2026", "FALL", 2026, date(2026, 8, 24), date(2026, 12, 11),
         date(2026, 7, 24), date(2026, 8, 31)),
)
TERMS_BY_ID = {t.term_id: t for t in TERMS}
AS_OF = date(2026, 10, 22)


@dataclass(frozen=True)
class Scheme:
    scheme_id: str
    name: str
    award_type: str
    basis: str
    value: int
    cap: int | None
    fee_codes: tuple[str, ...]
    levels: tuple[str, ...] = ()
    min_gpa: float | None = None
    income_bands: tuple[str, ...] = ()
    residency: tuple[str, ...] = ()
    departments: tuple[str, ...] = ()
    full_time_only: bool = False
    staff_dependent_only: bool = False


SCHEMES = (
    Scheme("SCHEME-MERIT-UG", "Undergraduate Merit Award", "SCHOLARSHIP", "PERCENT", 25, 300000,
           ("TUITION",), levels=("UG",), min_gpa=3.5, full_time_only=True),
    Scheme("SCHEME-MERIT-PG", "Postgraduate Merit Award", "SCHOLARSHIP", "PERCENT", 30, 500000,
           ("TUITION",), levels=("PG",), min_gpa=3.7),
    Scheme("SCHEME-NEED", "Need Based Grant", "SCHOLARSHIP", "FIXED", 200000, None,
           ("TUITION", "TECH", "LIBRARY", "LAB"), income_bands=("LOW",)),
    Scheme("SCHEME-STEM", "STEM Bursary", "SCHOLARSHIP", "FIXED", 150000, None,
           ("TUITION",), departments=("STEM",), min_gpa=3.0, income_bands=("LOW", "MEDIUM")),
    Scheme("SCHEME-INTL", "International Excellence Award", "SCHOLARSHIP", "PERCENT", 50, None,
           ("INTL_SURCHARGE",), residency=("INTL",), min_gpa=3.3),
    Scheme("SCHEME-WAIVER-HARDSHIP", "Hardship Fee Waiver", "WAIVER", "PERCENT", 100, None,
           ("TECH", "ACTIVITY", "LIBRARY"), income_bands=("LOW",), residency=("DOMESTIC",)),
    Scheme("SCHEME-WAIVER-STAFF", "Staff Dependent Tuition Waiver", "WAIVER", "PERCENT", 100, None,
           ("TUITION",), staff_dependent_only=True),
)
SCHEMES_BY_ID = {s.scheme_id: s for s in SCHEMES}
