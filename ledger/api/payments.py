from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..db.conn import cents, dollars
from ..domain import ids, rules
from .deps import get_actor, get_db

router = APIRouter(prefix="/api", tags=["payments"])


class PaymentRequest(BaseModel):
    invoice_id: str
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    method: Literal["CARD", "BANK_TRANSFER", "SPONSOR", "CHEQUE"]


def counter(db, key):
    return db.execute("""INSERT INTO id_counters(counter_key,value) VALUES (%s,1)
        ON CONFLICT(counter_key) DO UPDATE SET value=id_counters.value+1 RETURNING value""", (key,)).fetchone()["value"]


@router.post("/payments", status_code=201)
def record_payment(body: PaymentRequest, db=Depends(get_db), actor=Depends(get_actor)):
    inv = db.execute("SELECT * FROM invoices WHERE invoice_id=%s FOR UPDATE", (body.invoice_id,)).fetchone()
    if inv is None:
        raise HTTPException(404, "invoice not found")
    if actor.role not in ("support_staff", "platform_admin") and not (
        actor.role == "learner" and actor.student_id == inv["student_id"]
    ):
        raise HTTPException(403, "not permitted")
    today = date.today()
    if today < inv["issue_date"] or inv["status"] == "CANCELLED":
        raise HTTPException(409, "invoice cannot accept payment")
    account = db.execute("SELECT * FROM student_accounts WHERE student_id=%s FOR UPDATE",
                         (inv["student_id"],)).fetchone()
    lines = db.execute("SELECT * FROM invoice_lines WHERE invoice_id=%s", (body.invoice_id,)).fetchall()
    allocations = db.execute("SELECT * FROM payment_allocations WHERE invoice_id=%s", (body.invoice_id,)).fetchall()
    for row in lines + allocations:
        row["amount"] = cents(row["amount"])
    opened = rules.line_open_amounts(lines, allocations)
    items = [{**line, "open": opened[line["line_id"]]} for line in lines if line["line_id"] in opened]
    amount = cents(body.amount)
    splits, remainder = rules.allocate(amount, items)
    payment_id = ids.payment_id(today.year, counter(db, f"payment:{today.year}"))
    db.execute("INSERT INTO payments VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (payment_id, inv["student_id"], body.invoice_id, today, body.amount, body.method,
                dollars(amount - remainder), dollars(remainder), 0))
    for n, (line, value) in enumerate(splits, 1):
        db.execute("INSERT INTO payment_allocations VALUES (%s,%s,%s,%s,%s,%s)",
                   (ids.allocation_id(payment_id, n), payment_id, body.invoice_id, line["line_id"],
                    dollars(value), today))
    seq = db.execute("SELECT count(*) AS n FROM ledger_entries WHERE student_id=%s",
                     (inv["student_id"],)).fetchone()["n"] + 1
    balance = account["balance"] - body.amount
    db.execute("INSERT INTO ledger_entries VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
               (f"LED-{inv['student_id']}-{seq:06d}", inv["student_id"], today, "PAYMENT", payment_id,
                body.invoice_id, -body.amount, balance))
    db.execute("UPDATE student_accounts SET total_paid=total_paid+%s, unapplied_credit=unapplied_credit+%s, "
               "balance=%s, as_of=%s WHERE student_id=%s",
               (body.amount, dollars(remainder), balance, today, inv["student_id"]))
    allocated = inv["amount_allocated"] + dollars(amount - remainder)
    invoice_balance = inv["net_amount"] - allocated + inv["amount_refunded"]
    status = rules.invoice_status({"balance": cents(invoice_balance), "amount_allocated": cents(allocated)},
                                  inv["due_date"], today, False)
    db.execute("UPDATE invoices SET amount_allocated=%s,balance=%s,status=%s WHERE invoice_id=%s",
               (allocated, invoice_balance, status, body.invoice_id))
    event = counter(db, "event")
    db.execute("INSERT INTO events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
               (f"EVT-{event:09d}", "PAYMENT", payment_id, "RECEIVED", None, "RECEIVED", today,
                actor.role, f"Payment for {body.invoice_id}"))
    if status != inv["status"]:
        event = counter(db, "event")
        db.execute("INSERT INTO events VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                   (f"EVT-{event:09d}", "INVOICE", body.invoice_id, "STATUS_CHANGED", inv["status"], status,
                    today, actor.role, payment_id))
    db.commit()
    return {"payment_id": payment_id, "allocated": dollars(amount - remainder), "unapplied": dollars(remainder)}
