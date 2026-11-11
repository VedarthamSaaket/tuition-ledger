from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..db.conn import cents, dollars
from ..domain import ids, rules
from ..domain.catalog import SCHEMES_BY_ID
from ..generator.awards import net_charges
from ..generator.enrollments import context
from .deps import get_db, require
from .payments import counter

router = APIRouter(prefix="/api", tags=["scholarships"])
ACADEMIC = Depends(require("academic_admin", "platform_admin"))


class Assessment(BaseModel):
    invoice_id: str
    scheme_id: str


@router.post("/scholarship-assessments")
def assess(body: Assessment, db=Depends(get_db), actor=ACADEMIC):
    scheme = SCHEMES_BY_ID.get(body.scheme_id)
    if not scheme:
        raise HTTPException(404, "scheme not found")
    inv = db.execute("SELECT * FROM invoices WHERE invoice_id=%s FOR UPDATE", (body.invoice_id,)).fetchone()
    if not inv:
        raise HTTPException(404, "invoice not found")
    enr = db.execute("SELECT * FROM enrollments WHERE enrollment_id=%s", (inv["enrollment_id"],)).fetchone()
    if enr["status"] not in ("REGISTERED", "ACTIVE"):
        raise HTTPException(409, "enrollment is not active")
    if db.execute("SELECT 1 FROM scholarships WHERE invoice_id=%s AND award_type=%s AND status='AWARDED'",
                  (body.invoice_id, scheme.award_type)).fetchone():
        raise HTTPException(409, "an award of this type already exists")
    student = db.execute("SELECT * FROM students WHERE student_id=%s", (inv["student_id"],)).fetchone()
    program = db.execute("SELECT * FROM programs WHERE program_id=%s", (enr["program_id"],)).fetchone()
    eligible, passed, failed = rules.assess_eligibility(scheme, context(student, program, enr["credits"]))
    today = date.today()
    elg = ids.eligibility_id(today.year, counter(db, f"eligibility:{today.year}"))
    db.execute("INSERT INTO eligibility VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (elg, student["student_id"], enr["enrollment_id"], scheme.scheme_id, today, student["gpa"],
                student["income_band"], enr["credits"], eligible, "|".join(passed) or None, "|".join(failed) or None))
    decision = counter(db, "decision")
    db.execute("INSERT INTO decisions VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
               (f"DEC-{decision:09d}", "RULE-ELIGIBILITY", "ELIGIBILITY", elg,
                "ELIGIBLE" if eligible else "INELIGIBLE", None, today, ", ".join(passed if eligible else failed)))
    if not eligible:
        db.commit()
        return {"eligibility_id": elg, "eligible": False, "failed": failed}
    lines = db.execute("SELECT * FROM invoice_lines WHERE invoice_id=%s ORDER BY line_no", (body.invoice_id,)).fetchall()
    for line in lines:
        line["amount"] = cents(line["amount"])
    award, base, splits = rules.compute_award(scheme, net_charges(lines))
    if award == 0:
        db.commit()
        return {"eligibility_id": elg, "eligible": True, "award_amount": 0}
    account = db.execute("SELECT * FROM student_accounts WHERE student_id=%s FOR UPDATE",
                         (student["student_id"],)).fetchone()
    sch = ids.scholarship_id(today.year, counter(db, f"scholarship:{today.year}"))
    db.execute("INSERT INTO scholarships VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (sch, elg, student["student_id"], body.invoice_id, scheme.scheme_id, scheme.award_type,
                dollars(base), dollars(award), today, "AWARDED"))
    seq = db.execute("SELECT count(*) AS n FROM ledger_entries WHERE student_id=%s",
                     (student["student_id"],)).fetchone()["n"]
    line_no = max((line["line_no"] for line in lines), default=0)
    running = account["balance"]
    for charge, value in splits:
        seq += 1
        line_no += 1
        line_id = ids.invoice_line_id(body.invoice_id, line_no)
        credit = dollars(value)
        running -= credit
        db.execute("INSERT INTO invoice_lines VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                   (line_id, body.invoice_id, line_no, scheme.award_type, charge["fee_code"], None, None, None,
                    -credit, charge["line_id"], sch, today, scheme.name))
        db.execute("INSERT INTO ledger_entries VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                   (f"LED-{student['student_id']}-{seq:06d}", student["student_id"], today, scheme.award_type,
                    line_id, body.invoice_id, -credit, running))
    amount = dollars(award)
    new_balance = inv["balance"] - amount
    status = rules.invoice_status({"balance": cents(new_balance), "amount_allocated": cents(inv["amount_allocated"])},
                                  inv["due_date"], today, False)
    db.execute("UPDATE invoices SET total_credits=total_credits+%s,net_amount=net_amount-%s,balance=%s,status=%s "
               "WHERE invoice_id=%s", (amount, amount, new_balance, status, body.invoice_id))
    db.execute("UPDATE student_accounts SET total_credits=total_credits+%s,balance=%s,as_of=%s WHERE student_id=%s",
               (amount, running, today, student["student_id"]))
    event = counter(db, "event")
    db.execute("INSERT INTO events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (f"EVT-{event:09d}", "SCHOLARSHIP", sch, "AWARDED", None, "AWARDED", today, actor.role, scheme.name))
    if status != inv["status"]:
        event = counter(db, "event")
        db.execute("INSERT INTO events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                   (f"EVT-{event:09d}", "INVOICE", body.invoice_id, "STATUS_CHANGED", inv["status"], status,
                    today, actor.role, sch))
    decision = counter(db, "decision")
    db.execute("INSERT INTO decisions VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
               (f"DEC-{decision:09d}", "RULE-AWARD-AMOUNT", "SCHOLARSHIP", sch, "AWARDED", amount, today,
                "Award capped by scheme and remaining eligible fees"))
    db.commit()
    return {"eligibility_id": elg, "eligible": True, "scholarship_id": sch, "award_amount": amount}
