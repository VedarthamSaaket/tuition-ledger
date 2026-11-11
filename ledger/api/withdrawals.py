from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from ..db.conn import cents, dollars
from ..domain import ids, rules
from ..domain.catalog import PER_CREDIT_CODES
from ..generator.awards import net_charges
from .deps import get_db, require
from .payments import counter

router = APIRouter(prefix="/api", tags=["enrollment"])
ACADEMIC = Depends(require("academic_admin", "platform_admin"))


@router.post("/enrollments/{enrollment_id}/withdraw")
def withdraw(enrollment_id: str, db=Depends(get_db), actor=ACADEMIC):
    inv = db.execute("SELECT * FROM invoices WHERE enrollment_id=%s ORDER BY issue_date LIMIT 1 FOR UPDATE",
                     (enrollment_id,)).fetchone()
    if not inv:
        raise HTTPException(404, "invoice not found")
    if db.execute("SELECT count(*) AS n FROM invoices WHERE enrollment_id=%s", (enrollment_id,)).fetchone()["n"] != 1:
        raise HTTPException(409, "resolve duplicate invoices before withdrawal")
    enr = db.execute("SELECT * FROM enrollments WHERE enrollment_id=%s FOR UPDATE", (enrollment_id,)).fetchone()
    if enr["status"] not in ("REGISTERED", "ACTIVE"):
        raise HTTPException(409, "enrollment cannot be withdrawn")
    term = db.execute("SELECT * FROM terms WHERE term_id=%s", (enr["term_id"],)).fetchone()
    today = date.today()
    if today < inv["issue_date"] or today > term["end_date"]:
        raise HTTPException(409, "date is outside the enrollment withdrawal window")
    cancelled = today < term["start_date"]
    pct = rules.withdrawal_refund_percent(term["start_date"], today)
    status = "CANCELLED" if cancelled else "WITHDRAWN"
    account = db.execute("SELECT * FROM student_accounts WHERE student_id=%s FOR UPDATE",
                         (inv["student_id"],)).fetchone()
    lines = db.execute("SELECT * FROM invoice_lines WHERE invoice_id=%s ORDER BY line_no", (inv["invoice_id"],)).fetchall()
    for line in lines:
        line["amount"] = cents(line["amount"])
    charges = net_charges(lines)
    seq = db.execute("SELECT count(*) AS n FROM ledger_entries WHERE student_id=%s",
                     (inv["student_id"],)).fetchone()["n"]
    no = max((line["line_no"] for line in lines), default=0)
    running = account["balance"]
    total = 0
    for charge in charges:
        if not cancelled and charge["fee_code"] not in PER_CREDIT_CODES:
            continue
        value = rules.percent_of(charge["amount"], pct)
        if not value:
            continue
        total += value
        no += 1
        seq += 1
        line_id = ids.invoice_line_id(inv["invoice_id"], no)
        reversal = dollars(value)
        running -= reversal
        db.execute("INSERT INTO invoice_lines VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                   (line_id, inv["invoice_id"], no, "REVERSAL", charge["fee_code"], None, None, None,
                    -reversal, charge["line_id"], None, today, f"{status} reversal {pct} percent"))
        db.execute("INSERT INTO ledger_entries VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                   (f"LED-{inv['student_id']}-{seq:06d}", inv["student_id"], today, "REVERSAL", line_id,
                    inv["invoice_id"], -reversal, running))
    amount = dollars(total)
    invoice_balance = inv["balance"] - amount
    summary = {"balance": cents(invoice_balance), "amount_allocated": cents(inv["amount_allocated"])}
    invoice_status = rules.invoice_status(summary, inv["due_date"], today, cancelled)
    db.execute("UPDATE enrollments SET status=%s,status_on=%s,exit_date=%s,refund_percent=%s WHERE enrollment_id=%s",
               (status, today, today, pct, enrollment_id))
    db.execute("UPDATE invoices SET total_reversals=total_reversals+%s,net_amount=net_amount-%s,balance=%s,status=%s "
               "WHERE invoice_id=%s", (amount, amount, invoice_balance, invoice_status, inv["invoice_id"]))
    db.execute("UPDATE student_accounts SET total_credits=total_credits+%s,balance=%s,as_of=%s WHERE student_id=%s",
               (amount, running, today, inv["student_id"]))
    if cancelled:
        awards = db.execute("UPDATE scholarships SET status='CANCELLED' WHERE invoice_id=%s AND status='AWARDED' "
                            "RETURNING scholarship_id", (inv["invoice_id"],)).fetchall()
        for award in awards:
            event = counter(db, "event")
            db.execute("INSERT INTO events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                       (f"EVT-{event:09d}", "SCHOLARSHIP", award["scholarship_id"], "CANCELLED", "AWARDED",
                        "CANCELLED", today, actor.role, enrollment_id))
    event = counter(db, "event")
    db.execute("INSERT INTO events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (f"EVT-{event:09d}", "ENROLLMENT", enrollment_id, status, enr["status"], status, today, actor.role,
                f"{pct} percent reversal"))
    if invoice_status != inv["status"]:
        event = counter(db, "event")
        db.execute("INSERT INTO events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                   (f"EVT-{event:09d}", "INVOICE", inv["invoice_id"], "STATUS_CHANGED", inv["status"],
                    invoice_status, today, actor.role, enrollment_id))
    decision = counter(db, "decision")
    db.execute("INSERT INTO decisions VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
               (f"DEC-{decision:09d}", "RULE-WITHDRAWAL", "ENROLLMENT", enrollment_id, status, amount, today,
                f"{pct} percent reversal; any credit requires separate refund review"))
    db.commit()
    return {"status": status, "refund_percent": pct, "reversal": amount, "invoice_balance": invoice_balance}
