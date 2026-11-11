from collections.abc import Iterator
from dataclasses import dataclass

import psycopg
from fastapi import Depends, Header, HTTPException

from ..db.conn import connect

ROLES = ("learner", "instructor", "academic_admin", "support_staff", "platform_admin")
STAFF = ("academic_admin", "support_staff", "platform_admin")

PERMISSIONS = {
    "learner": ["view own account", "pay own invoices"],
    "instructor": ["view programs and fee schedules", "view class rosters"],
    "academic_admin": ["view all accounts", "assess scholarships", "withdraw or cancel enrollments", "view exceptions"],
    "support_staff": ["view all accounts", "record payments", "issue refunds", "view exceptions"],
    "platform_admin": ["everything", "run reconciliation", "assess late fees"],
}


@dataclass(frozen=True)
class Actor:
    role: str
    student_id: str | None

    def can_view_student(self, student_id: str) -> bool:
        return self.role in STAFF or (self.role == "learner" and self.student_id == student_id)


def get_db() -> Iterator[psycopg.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def get_actor(x_role: str = Header("platform_admin"), x_student_id: str | None = Header(None)) -> Actor:
    if x_role not in ROLES:
        raise HTTPException(400, f"unknown role {x_role}")
    if x_role == "learner" and not x_student_id:
        raise HTTPException(400, "learner role needs an X-Student-Id header")
    return Actor(x_role, x_student_id)


def require(*roles: str):
    def check(actor: Actor = Depends(get_actor)) -> Actor:
        if actor.role not in roles:
            raise HTTPException(403, f"{actor.role} cannot do this")
        return actor
    return check


def ensure_student(actor: Actor, student_id: str) -> None:
    if not actor.can_view_student(student_id):
        raise HTTPException(403, "learners can only see their own account")


STAFF_ONLY = Depends(require(*STAFF))
ROSTER_ROLES = Depends(require("instructor", "academic_admin", "platform_admin"))
