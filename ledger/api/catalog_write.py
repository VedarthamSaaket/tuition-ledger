"""Create billing reference data and issue invoices without changing historical rows."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from ..db.conn import paise, rupees
from ..domain import catalog, ids, rules
from ..generator.enrollments import context
from ..services.transactions import counter, lock_reconciled_account
from .catalog_models import Enrollment, FeeSchedule, Program, Student, Term
from .deps import get_db, require

router = APIRouter(prefix="/api", tags=["catalog and invoicing"])
ADMIN = Depends(require("academic_admin", "platform_admin"))


def lock(db, key):
    db.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (key,))


def find(db, table, column, value):
    row = db.execute(f"SELECT * FROM {table} WHERE {column}=%s", (value,)).fetchone()
    if not row:
        raise HTTPException(404, f"{table} record not found")
    return row


def next_master(db, table, column, prefix):
    lock(db, f"catalog:{table}")
    row = db.execute(f"SELECT COALESCE(MAX(CAST(SUBSTRING({column} FROM %s) AS BIGINT)),0)+1 AS n FROM {table}",
                     (f"^{prefix}-([0-9]+)$",)).fetchone()
    return row["n"]


def event(db, kind, entity, action, old, new, actor, detail=None):
    number = counter(db, "event")
    db.execute("INSERT INTO events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (f"EVT-{number:09d}", kind, entity, action, old, new, date.today(), actor.role, detail))


@router.post("/programs", status_code=201)
def create_program(body: Program, db=Depends(get_db), actor=ADMIN):
    lock(db, "program-name")
    if db.execute("SELECT 1 FROM programs WHERE lower(name)=lower(%s)", (body.name.strip(),)).fetchone():
        raise HTTPException(409, "program name already exists")
    program_id = ids.program_id(next_master(db, "programs", "program_id", "PRG"))
    db.execute("INSERT INTO programs VALUES (%s,%s,%s,%s,%s,%s,%s)",
               (program_id, body.name.strip(), body.level, body.department, body.has_lab,
                catalog.FULL_TIME_CREDITS[body.level], "ACTIVE"))
    db.commit()
    return {"program_id": program_id}


@router.post("/terms", status_code=201)
def create_term(body: Term, db=Depends(get_db), actor=ADMIN):
    term_id = f"TERM-{body.year}-{body.season}"
    lock(db, f"term:{term_id}")
    if db.execute("SELECT 1 FROM terms WHERE term_id=%s", (term_id,)).fetchone():
        raise HTTPException(409, "term already exists")
    db.execute("INSERT INTO terms VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
               (term_id, body.name.strip(), body.season, body.year, body.invoice_date, body.start_date,
                body.due_date, body.end_date))
    db.commit()
    return {"term_id": term_id}


@router.post("/students", status_code=201)
def create_student(body: Student, db=Depends(get_db), actor=ADMIN):
    program = find(db, "programs", "program_id", body.program_id)
    find(db, "terms", "term_id", body.admit_term_id)
    if program["status"] != "ACTIVE":
        raise HTTPException(409, "program is not active")
    lock(db, "student-email")
    if db.execute("SELECT 1 FROM students WHERE lower(email)=lower(%s)", (body.email,)).fetchone():
        raise HTTPException(409, "email already exists")
    student_id = ids.student_id(next_master(db, "students", "student_id", "STU"))
    db.execute("INSERT INTO students VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (student_id, body.first_name.strip(), body.last_name.strip(), body.email.lower(), body.program_id,
                body.admit_term_id, body.residency, body.income_band, body.gpa, body.has_external_cover,
                body.staff_dependent, date.today()))
    db.execute("INSERT INTO student_accounts VALUES (%s,0,0,0,0,0,0,%s)", (student_id, date.today()))
    db.commit()
    return {"student_id": student_id}


@router.post("/fee-schedules", status_code=201)
def create_fee_schedule(body: FeeSchedule, db=Depends(get_db), actor=ADMIN):
    find(db, "programs", "program_id", body.program_id)
    find(db, "terms", "term_id", body.term_id)
    lock(db, f"catalog:fees:{body.program_id}:{body.term_id}")
    if db.execute("""SELECT 1 FROM invoices i JOIN enrollments e USING (enrollment_id)
        WHERE e.program_id=%s AND e.term_id=%s AND i.issue_date >= %s
        AND (%s::date IS NULL OR i.issue_date <= %s::date) LIMIT 1""",
                  (body.program_id, body.term_id, body.effective_from, body.effective_to, body.effective_to)).fetchone():
        raise HTTPException(409, "fee schedule would change the pricing of existing invoices")
    lock(db, f"fee:{body.program_id}:{body.term_id}:{body.fee_code}")
    existing = db.execute("SELECT * FROM fee_schedules WHERE program_id=%s AND term_id=%s AND fee_code=%s",
                          (body.program_id, body.term_id, body.fee_code)).fetchall()
    if any((r["effective_to"] is None or body.effective_from <= r["effective_to"]) and
           (body.effective_to is None or r["effective_from"] <= body.effective_to) for r in existing):
        raise HTTPException(409, "fee schedule dates overlap")
    version = max((r["version"] for r in existing), default=0) + 1
    schedule_id = ids.fee_schedule_id(body.program_id, body.term_id, body.fee_code, version)
    basis = "PER_CREDIT" if body.fee_code in catalog.PER_CREDIT_CODES else "FLAT"
    db.execute("INSERT INTO fee_schedules VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (schedule_id, body.program_id, body.term_id, body.fee_code, basis, body.rate,
                body.applies_when, version, body.effective_from, body.effective_to))
    db.commit()
    return {"fee_schedule_id": schedule_id}


@router.post("/enrollments", status_code=201)
def create_enrollment(body: Enrollment, db=Depends(get_db), actor=ADMIN):
    student = find(db, "students", "student_id", body.student_id)
    term = find(db, "terms", "term_id", body.term_id)
    program = find(db, "programs", "program_id", student["program_id"])
    if date.today() > term["end_date"]:
        raise HTTPException(409, "term has ended")
    enrollment_id = ids.enrollment_id(body.student_id, body.term_id)
    lock(db, f"enrollment:{enrollment_id}")
    if db.execute("SELECT 1 FROM enrollments WHERE enrollment_id=%s", (enrollment_id,)).fetchone():
        raise HTTPException(409, "student is already enrolled in this term")
    today = date.today()
    load = "FULL_TIME" if rules.is_full_time(program["level"], body.credits) else "PART_TIME"
    status = "ACTIVE" if today >= term["start_date"] else "REGISTERED"
    db.execute("INSERT INTO enrollments VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (enrollment_id, body.student_id, student["program_id"], body.term_id, body.credits, load,
                today, status, today, None, None))
    event(db, "ENROLLMENT", enrollment_id, "REGISTERED", None, "REGISTERED", actor)
    if status == "ACTIVE":
        event(db, "ENROLLMENT", enrollment_id, "ACTIVATED", "REGISTERED", "ACTIVE", actor)
    db.commit()
    return {"enrollment_id": enrollment_id}


@router.post("/enrollments/{enrollment_id}/invoice", status_code=201)
def issue_invoice(enrollment_id: str, db=Depends(get_db), actor=ADMIN):
    lock(db, f"invoice:{enrollment_id}")
    enr = db.execute("SELECT * FROM enrollments WHERE enrollment_id=%s FOR UPDATE", (enrollment_id,)).fetchone()
    if not enr:
        raise HTTPException(404, "enrollment not found")
    if enr["status"] not in ("REGISTERED", "ACTIVE"):
        raise HTTPException(409, "enrollment is not active")
    if db.execute("SELECT 1 FROM invoices WHERE enrollment_id=%s", (enrollment_id,)).fetchone():
        raise HTTPException(409, "enrollment already has an invoice")
    student = find(db, "students", "student_id", enr["student_id"])
    program = find(db, "programs", "program_id", enr["program_id"])
    term = find(db, "terms", "term_id", enr["term_id"])
    lock(db, f"catalog:fees:{enr['program_id']}:{enr['term_id']}")
    today = date.today()
    if today >= term["due_date"]:
        raise HTTPException(409, "invoice must be issued before the term due date")
    schedules = db.execute("SELECT * FROM fee_schedules WHERE program_id=%s AND term_id=%s",
                           (enr["program_id"], enr["term_id"])).fetchall()
    for schedule in schedules:
        schedule["rate"] = paise(schedule["rate"])
    charges = rules.build_charge_lines(rules.schedule_in_effect(schedules, today), context(student, program, enr["credits"]))
    if not any(c["fee_code"] == "TUITION" for c in charges):
        raise HTTPException(409, "an effective tuition schedule is required")
    lock(db, f"invoice-number:{enr['student_id']}:{term['year']}")
    prefix = f"INV-{enr['student_id']}-{term['year']}-"
    rows = db.execute("SELECT invoice_id FROM invoices WHERE invoice_id LIKE %s", (prefix + "%",)).fetchall()
    number = max((int(r["invoice_id"].removeprefix(prefix)) for r in rows), default=0) + 1
    invoice_id = ids.invoice_id(enr["student_id"], term["year"], number)
    account = lock_reconciled_account(db, enr["student_id"])
    total = sum(c["amount"] for c in charges)
    db.execute("INSERT INTO invoices VALUES (%s,%s,%s,%s,%s,%s,%s,0,0,%s,0,0,%s,'UNPAID')",
               (invoice_id, enr["student_id"], enrollment_id, enr["term_id"], today, term["due_date"],
                rupees(total), rupees(total), rupees(total)))
    seq = db.execute("SELECT count(*) AS n FROM ledger_entries WHERE student_id=%s", (enr["student_id"],)).fetchone()["n"]
    running = account["balance"]
    for no, charge in enumerate(charges, 1):
        line_id = ids.invoice_line_id(invoice_id, no)
        amount = rupees(charge["amount"])
        running += amount
        seq += 1
        db.execute("INSERT INTO invoice_lines VALUES (%s,%s,%s,'CHARGE',%s,%s,%s,%s,%s,NULL,NULL,%s,%s)",
                   (line_id, invoice_id, no, charge["fee_code"], charge["fee_schedule_id"], charge["quantity"],
                    rupees(charge["unit_amount"]), amount, today, charge["fee_code"]))
        db.execute("INSERT INTO ledger_entries VALUES (%s,%s,%s,'CHARGE',%s,%s,%s,%s)",
                   (f"LED-{enr['student_id']}-{seq:06d}", enr["student_id"], today, line_id, invoice_id, amount, running))
    db.execute("UPDATE student_accounts SET total_billed=total_billed+%s,balance=%s,as_of=%s WHERE student_id=%s",
               (rupees(total), running, today, enr["student_id"]))
    event(db, "INVOICE", invoice_id, "ISSUED", None, "UNPAID", actor, enrollment_id)
    db.commit()
    return {"invoice_id": invoice_id, "net_amount": rupees(total)}
