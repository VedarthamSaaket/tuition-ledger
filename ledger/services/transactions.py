from fastapi import HTTPException
from psycopg.types.json import Jsonb


def counter(db, key):
    return db.execute("""INSERT INTO id_counters(counter_key,value) VALUES (%s,1)
        ON CONFLICT(counter_key) DO UPDATE SET value=id_counters.value+1 RETURNING value""", (key,)).fetchone()["value"]


def lock_reconciled_account(db, student_id):
    account = db.execute("SELECT * FROM student_accounts WHERE student_id=%s FOR UPDATE", (student_id,)).fetchone()
    if account is None:
        raise HTTPException(409, "student account is missing")
    ledger = db.execute("SELECT COALESCE(SUM(amount),0) AS total FROM ledger_entries WHERE student_id=%s",
                        (student_id,)).fetchone()["total"]
    if account["balance"] != ledger:
        raise HTTPException(409, "account balance does not reconcile with the ledger; review the exception first")
    return account


def prior_request(db, operation, key, body):
    db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"{operation}:{key}",))
    prior = db.execute("SELECT request_body,response_body FROM api_idempotency WHERE operation=%s AND request_key=%s",
                       (operation, key)).fetchone()
    if prior and prior["request_body"] != body:
        raise HTTPException(409, "idempotency key was already used with a different request")
    return prior["response_body"] if prior else None


def save_request(db, operation, key, body, result):
    db.execute("INSERT INTO api_idempotency VALUES (%s,%s,%s,%s)",
               (operation, key, Jsonb(body), Jsonb(result)))


