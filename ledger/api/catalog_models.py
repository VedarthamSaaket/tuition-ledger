from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CatalogModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class Program(CatalogModel):
    name: str = Field(min_length=1, max_length=200)
    level: Literal["UG", "PG", "DIP", "CERT"]
    department: Literal["STEM", "BUSINESS", "ARTS", "HEALTH"]
    has_lab: bool = False


class Term(CatalogModel):
    name: str = Field(min_length=1, max_length=100)
    season: Literal["FALL", "SPRING", "SUMMER"]
    year: int = Field(ge=2000, le=2100)
    invoice_date: date
    start_date: date
    due_date: date
    end_date: date

    @model_validator(mode="after")
    def dates(self):
        if not (self.invoice_date < self.start_date < self.end_date and
                self.invoice_date < self.due_date <= self.end_date and self.start_date.year == self.year):
            raise ValueError("term dates must be ordered and start in the term year")
        return self


class Student(CatalogModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    program_id: str
    admit_term_id: str
    residency: Literal["DOMESTIC", "INTL"]
    income_band: Literal["LOW", "MEDIUM", "HIGH"]
    gpa: float = Field(ge=0, le=4)
    has_external_cover: bool = False
    staff_dependent: bool = False


class FeeSchedule(CatalogModel):
    program_id: str
    term_id: str
    fee_code: Literal["TECH", "LIBRARY", "ACTIVITY", "LAB", "HEALTH_INSURANCE", "INTL_SURCHARGE", "TUITION"]
    rate: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    applies_when: Literal["ALL", "INTL", "FULL_TIME", "LAB_PROGRAM", "FULL_TIME_NO_COVER"]
    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not precede effective_from")
        return self


class Enrollment(CatalogModel):
    student_id: str
    term_id: str
    credits: int = Field(ge=1, le=18)


