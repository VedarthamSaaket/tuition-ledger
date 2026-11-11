import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from .deps import PERMISSIONS, ROSTER_ROLES, STAFF_ONLY, Actor, ensure_student, get_actor, get_db

router = APIRouter(prefix="/api")


def rows(db: psycopg.Connection, sql: str, *params) -> list[dict]:
    return db.execute(sql, params or None).fetchall()


def one(db: psycopg.Connection, sql: str, *params) -> dict:
    row = db.execute(sql, params or None).fetchone()
    if row is None:
        raise HTTPException(404, "not found")
    return row


@router.get("/me")
def me(actor: Actor = Depends(get_actor)) -> dict:
    return {"role": actor.role, "student_id": actor.student_id, "permissions": PERMISSIONS[actor.role]}


@router.get("/summary")
def summary(db=Depends(get_db), actor: Actor = STAFF_ONLY) -> dict:
    totals = one(db, """
        SELECT
          (SELECT count(*) FROM students) AS students,
          (SELECT count(*) FROM invoices) AS invoices,
          (SELECT coalesce(sum(total_charges), 0) FROM invoices) AS total_billed,
          (SELECT coalesce(sum(total_credits), 0) FROM invoices) AS total_credits,
          (SELECT coalesce(sum(total_reversals), 0) FROM invoices) AS total_reversals,
          (SELECT coalesce(sum(amount), 0) FROM payments) AS total_collected,
          (SELECT coalesce(sum(amount), 0) FROM refunds) AS total_refunded,
          (SELECT coalesce(sum(balance), 0) FROM student_accounts WHERE balance > 0) AS outstanding,
          (SELECT coalesce(-sum(balance), 0) FROM student_accounts WHERE balance < 0) AS credit_owed,
          (SELECT count(*) FROM invoice_lines WHERE line_type = 'LATE_FEE') AS late_fees,
          (SELECT coalesce(sum(amount), 0) FROM invoice_lines WHERE line_type = 'LATE_FEE') AS late_fee_amount,
          (SELECT count(*) FROM scholarships) AS scholarships
    """)
    net = totals["total_billed"] - totals["total_credits"] - totals["total_reversals"]
    totals["net_billed"] = net
    totals["collection_rate"] = float((totals["total_collected"] - totals["total_refunded"]) / net) if net else 0
    totals["status_counts"] = {r["status"]: r["n"] for r in rows(
        db, "SELECT status, count(*) AS n FROM invoices GROUP BY status ORDER BY status")}
    totals["by_term"] = rows(db, """
        SELECT term_id, count(*) AS invoices, sum(net_amount) AS net_billed, sum(amount_allocated) AS collected,
               sum(GREATEST(balance, 0)) AS outstanding
        FROM invoices GROUP BY term_id ORDER BY min(issue_date)""")
    totals["by_scheme"] = rows(db, """
        SELECT s.scheme_id, ss.name, count(*) AS awards, sum(s.award_amount) AS amount
        FROM scholarships s JOIN scholarship_schemes ss USING (scheme_id) GROUP BY s.scheme_id, ss.name
        ORDER BY amount DESC""")
    totals["aging"] = rows(db, """
        SELECT CASE WHEN d <= 30 THEN '0-30' WHEN d <= 60 THEN '31-60' WHEN d <= 90 THEN '61-90' ELSE '90+' END
               AS bucket, count(*) AS invoices, sum(balance) AS amount
        FROM (SELECT balance, (DATE '2026-10-22' - due_date) AS d FROM invoices WHERE status = 'OVERDUE') x
        GROUP BY 1 ORDER BY 1""")
    return totals


@router.get("/students")
def students(q: str | None = None, sort: str = Query("balance", pattern="^(balance|name|id)$"),
             limit: int = Query(50, le=500), offset: int = 0, db=Depends(get_db),
             actor: Actor = STAFF_ONLY) -> dict:
    where, params = "", []
    if q:
        where = "WHERE s.student_id ILIKE %s OR s.first_name ILIKE %s OR s.last_name ILIKE %s OR s.email ILIKE %s"
        params = [f"%{q}%"] * 4
    order = {"balance": "a.balance DESC, s.student_id", "name": "s.last_name, s.first_name", "id": "s.student_id"}[sort]
    total = one(db, f"SELECT count(*) AS n FROM students s {where}", *params)["n"]
    items = rows(db, f"""
        SELECT s.student_id, s.first_name, s.last_name, s.email, s.residency, p.name AS program, p.level,
               a.balance, a.unapplied_credit, a.total_billed, a.total_paid
        FROM students s JOIN programs p USING (program_id) JOIN student_accounts a USING (student_id)
        {where} ORDER BY {order} LIMIT %s OFFSET %s""", *params, limit, offset)
    return {"total": total, "items": items}


@router.get("/students/{student_id}")
def student(student_id: str, db=Depends(get_db), actor: Actor = Depends(get_actor)) -> dict:
    ensure_student(actor, student_id)
    s = one(db, """SELECT s.*, p.name AS program_name, p.level, p.department FROM students s
                   JOIN programs p USING (program_id) WHERE student_id = %s""", student_id)
    s["account"] = one(db, "SELECT * FROM student_accounts WHERE student_id = %s", student_id)
    s["ledger_balance"] = one(db, "SELECT coalesce(sum(amount), 0) AS b FROM ledger_entries WHERE student_id = %s",
                              student_id)["b"]
    s["enrollments"] = rows(db, """
        SELECT e.*, i.invoice_id, i.status AS invoice_status, i.net_amount, i.balance, i.due_date
        FROM enrollments e LEFT JOIN invoices i USING (enrollment_id)
        WHERE e.student_id = %s ORDER BY e.registered_on, i.invoice_id""", student_id)
    s["scholarships"] = rows(db, """SELECT sc.*, ss.name AS scheme_name FROM scholarships sc
        JOIN scholarship_schemes ss USING (scheme_id) WHERE sc.student_id = %s ORDER BY sc.awarded_on""", student_id)
    s["eligibility"] = rows(db, "SELECT * FROM eligibility WHERE student_id = %s ORDER BY assessed_on", student_id)
    s["payments"] = rows(db, "SELECT * FROM payments WHERE student_id = %s ORDER BY received_on", student_id)
    s["refunds"] = rows(db, "SELECT * FROM refunds WHERE student_id = %s ORDER BY refunded_on", student_id)
    return s


@router.get("/students/{student_id}/ledger")
def ledger(student_id: str, db=Depends(get_db), actor: Actor = Depends(get_actor)) -> list[dict]:
    ensure_student(actor, student_id)
    return rows(db, "SELECT * FROM ledger_entries WHERE student_id = %s ORDER BY entry_id", student_id)


@router.get("/invoices/{invoice_id}")
def invoice(invoice_id: str, db=Depends(get_db), actor: Actor = Depends(get_actor)) -> dict:
    inv = one(db, "SELECT * FROM invoices WHERE invoice_id = %s", invoice_id)
    ensure_student(actor, inv["student_id"])
    inv["lines"] = rows(db, """
        SELECT l.*, coalesce(sum(a.amount), 0) AS allocated FROM invoice_lines l
        LEFT JOIN payment_allocations a USING (line_id) WHERE l.invoice_id = %s
        GROUP BY l.line_id ORDER BY l.line_no""", invoice_id)
    inv["allocations"] = rows(db, "SELECT * FROM payment_allocations WHERE invoice_id = %s ORDER BY allocation_id",
                              invoice_id)
    inv["payments"] = rows(db, "SELECT * FROM payments WHERE invoice_id = %s ORDER BY received_on", invoice_id)
    inv["refunds"] = rows(db, """SELECT r.* FROM refunds r WHERE r.invoice_id = %s
        OR r.payment_id IN (SELECT payment_id FROM payments WHERE invoice_id = %s) ORDER BY refunded_on""",
                          invoice_id, invoice_id)
    inv["events"] = rows(db, "SELECT * FROM events WHERE entity_id = %s ORDER BY occurred_on, event_id", invoice_id)
    inv["decisions"] = rows(db, """SELECT * FROM decisions WHERE entity_id = %s OR entity_id IN
        (SELECT scholarship_id FROM scholarships WHERE invoice_id = %s) ORDER BY decided_on, decision_id""",
                            invoice_id, invoice_id)
    inv["enrollment"] = one(db, "SELECT * FROM enrollments WHERE enrollment_id = %s", inv["enrollment_id"])
    return inv


@router.get("/payments/{payment_id}")
def payment(payment_id: str, db=Depends(get_db), actor: Actor = Depends(get_actor)) -> dict:
    p = one(db, "SELECT * FROM payments WHERE payment_id = %s", payment_id)
    ensure_student(actor, p["student_id"])
    p["allocations"] = rows(db, """SELECT a.*, l.fee_code, l.line_type FROM payment_allocations a
        JOIN invoice_lines l USING (line_id) WHERE a.payment_id = %s ORDER BY allocation_id""", payment_id)
    p["refunds"] = rows(db, "SELECT * FROM refunds WHERE payment_id = %s ORDER BY refunded_on", payment_id)
    p["events"] = rows(db, "SELECT * FROM events WHERE entity_id = %s ORDER BY event_id", payment_id)
    p["decisions"] = rows(db, "SELECT * FROM decisions WHERE entity_id = %s ORDER BY decision_id", payment_id)
    return p


@router.get("/programs")
def programs(db=Depends(get_db), actor: Actor = Depends(get_actor)) -> list[dict]:
    return rows(db, "SELECT * FROM programs ORDER BY program_id")


@router.get("/terms")
def terms(db=Depends(get_db), actor: Actor = Depends(get_actor)) -> list[dict]:
    return rows(db, "SELECT * FROM terms ORDER BY start_date")


@router.get("/fee-schedules")
def fee_schedules(program_id: str | None = None, term_id: str | None = None, db=Depends(get_db),
                  actor: Actor = Depends(get_actor)) -> list[dict]:
    return rows(db, """SELECT * FROM fee_schedules WHERE (%s::text IS NULL OR program_id = %s)
        AND (%s::text IS NULL OR term_id = %s) ORDER BY program_id, term_id, fee_code, version""",
                program_id, program_id, term_id, term_id)


@router.get("/schemes")
def schemes(db=Depends(get_db), actor: Actor = Depends(get_actor)) -> list[dict]:
    return rows(db, """SELECT ss.*, count(s.scholarship_id) AS awards, coalesce(sum(s.award_amount), 0) AS awarded
        FROM scholarship_schemes ss LEFT JOIN scholarships s USING (scheme_id)
        GROUP BY ss.scheme_id ORDER BY ss.scheme_id""")


@router.get("/roster")
def roster(program_id: str, term_id: str, db=Depends(get_db),
           actor: Actor = ROSTER_ROLES) -> list[dict]:
    return rows(db, """SELECT e.enrollment_id, e.student_id, s.first_name, s.last_name, e.credits, e.load, e.status
        FROM enrollments e JOIN students s USING (student_id)
        WHERE e.program_id = %s AND e.term_id = %s ORDER BY s.last_name, s.first_name""", program_id, term_id)


@router.get("/decisions")
def decisions(entity_id: str | None = None, rule_id: str | None = None, limit: int = Query(100, le=1000),
              db=Depends(get_db), actor: Actor = STAFF_ONLY) -> list[dict]:
    return rows(db, """SELECT * FROM decisions WHERE (%s::text IS NULL OR entity_id = %s)
        AND (%s::text IS NULL OR rule_id = %s) ORDER BY decision_id DESC LIMIT %s""",
                entity_id, entity_id, rule_id, rule_id, limit)


@router.get("/events")
def events(entity_id: str, db=Depends(get_db), actor: Actor = STAFF_ONLY) -> list[dict]:
    return rows(db, "SELECT * FROM events WHERE entity_id = %s ORDER BY occurred_on, event_id", entity_id)
