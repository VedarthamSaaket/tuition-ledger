from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from ..db.conn import cents, dollars
from ..domain import ids, rules
from .deps import get_db, require
from .payments import counter

router = APIRouter(prefix="/api", tags=["late fees"])
ADMIN = Depends(require("platform_admin"))


@router.post("/invoices/{invoice_id}/late-fee")
def assess_late_fee(invoice_id: str, db=Depends(get_db), actor=ADMIN):
    inv = db.execute("SELECT * FROM invoices WHERE invoice_id=%s FOR UPDATE", (invoice_id,)).fetchone()
    if inv is None:
        raise HTTPException(404, "invoice not found")
    today = date.today()
    if inv["status"] == "CANCELLED" or today < rules.grace_end(inv["due_date"]) or inv["balance"] <= 0:
        raise HTTPException(409, "invoice is not eligible for a late fee")
    if db.execute("SELECT 1 FROM invoice_lines WHERE invoice_id=%s AND line_type='LATE_FEE'", (invoice_id,)).fetchone():
        raise HTTPException(409, "late fee already assessed")
    account = db.execute("SELECT * FROM student_accounts WHERE student_id=%s FOR UPDATE",
                         (inv["student_id"],)).fetchone()
    fee = dollars(rules.late_fee_amount(cents(inv["balance"])))
    number = db.execute("SELECT coalesce(max(line_no),0)+1 AS n FROM invoice_lines WHERE invoice_id=%s",
                        (invoice_id,)).fetchone()["n"]
    line_id = ids.invoice_line_id(invoice_id, number)
    db.execute("INSERT INTO invoice_lines VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (line_id, invoice_id, number, "LATE_FEE", "LATE_FEE", None, 1, fee, fee, None, None,
                today, "Late fee after grace period"))
    seq = db.execute("SELECT count(*) AS n FROM ledger_entries WHERE student_id=%s",
                     (inv["student_id"],)).fetchone()["n"] + 1
    balance = account["balance"] + fee
    db.execute("INSERT INTO ledger_entries VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
               (f"LED-{inv['student_id']}-{seq:06d}", inv["student_id"], today, "LATE_FEE", line_id,
                invoice_id, fee, balance))
    db.execute("UPDATE student_accounts SET total_billed=total_billed+%s,balance=%s,as_of=%s WHERE student_id=%s",
               (fee, balance, today, inv["student_id"]))
    db.execute("UPDATE invoices SET total_charges=total_charges+%s,net_amount=net_amount+%s,balance=balance+%s,"
               "status='OVERDUE' WHERE invoice_id=%s", (fee, fee, fee, invoice_id))
    decision = counter(db, "decision")
    db.execute("INSERT INTO decisions VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
               (f"DEC-{decision:09d}", "RULE-LATE-FEE", "INVOICE", invoice_id, "ASSESSED", fee, today,
                "1.5 percent of overdue balance, bounded to $25-$150"))
    if inv["status"] != "OVERDUE":
        event = counter(db, "event")
        db.execute("INSERT INTO events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                   (f"EVT-{event:09d}", "INVOICE", invoice_id, "STATUS_CHANGED", inv["status"], "OVERDUE",
                    today, actor.role, line_id))
    db.commit()
    return {"line_id": line_id, "amount": fee}
