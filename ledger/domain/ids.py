def student_id(n: int) -> str:
    return f"STU-{n:06d}"


def program_id(n: int) -> str:
    return f"PRG-{n:03d}"


def fee_schedule_id(program: str, term: str, fee_code: str, version: int) -> str:
    return f"FS-{program}-{term}-{fee_code}-V{version}"


def enrollment_id(student: str, term: str) -> str:
    return f"ENR-{student}-{term}"


def invoice_id(student: str, year: int, n: int) -> str:
    return f"INV-{student}-{year}-{n:06d}"


def invoice_line_id(invoice: str, n: int) -> str:
    return f"{invoice}-L{n:02d}"


def scholarship_id(year: int, n: int) -> str:
    return f"SCH-{year}-{n:06d}"


def eligibility_id(year: int, n: int) -> str:
    return f"ELG-{year}-{n:06d}"


def payment_id(year: int, n: int) -> str:
    return f"PAY-{year}-{n:06d}"


def allocation_id(payment: str, n: int) -> str:
    return f"ALLOC-{payment}-{n:02d}"


def refund_id(year: int, n: int) -> str:
    return f"REF-{year}-{n:06d}"


class Counter:
    def __init__(self) -> None:
        self._values: dict = {}

    def next(self, key) -> int:
        self._values[key] = self._values.get(key, 0) + 1
        return self._values[key]
