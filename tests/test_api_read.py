from decimal import Decimal


def first_student(client):
    return client.get("/api/students?sort=id&limit=1").json()["items"][0]["student_id"]


def test_summary_reconciles(client):
    s = client.get("/api/summary").json()
    net = Decimal(s["total_billed"]) - Decimal(s["total_credits"]) - Decimal(s["total_reversals"])
    assert Decimal(s["net_billed"]) == net
    assert sum(s["status_counts"].values()) == s["invoices"]


def test_student_detail_has_account_and_ledger(client):
    sid = first_student(client)
    body = client.get(f"/api/students/{sid}").json()
    assert body["enrollments"]
    ledger = client.get(f"/api/students/{sid}/ledger").json()
    assert Decimal(ledger[-1]["running_balance"]) == Decimal(body["ledger_balance"])


def test_invoice_detail_is_traceable(client):
    sid = first_student(client)
    inv_id = client.get(f"/api/students/{sid}").json()["enrollments"][0]["invoice_id"]
    inv = client.get(f"/api/invoices/{inv_id}").json()
    assert inv["lines"] and inv["events"][0]["event_type"] == "ISSUED"
    assert all(line["fee_schedule_id"] for line in inv["lines"] if line["line_type"] == "CHARGE")
    lines = sum(Decimal(line["amount"]) for line in inv["lines"])
    assert lines == Decimal(inv["net_amount"])


def test_learner_sees_only_own_account(client):
    sid = first_student(client)
    own = client.get(f"/api/students/{sid}", headers={"X-Role": "learner", "X-Student-Id": sid})
    assert own.status_code == 200
    other = client.get(f"/api/students/{sid}", headers={"X-Role": "learner", "X-Student-Id": "STU-999999"})
    assert other.status_code == 403
    assert client.get("/api/students", headers={"X-Role": "learner", "X-Student-Id": sid}).status_code == 403


def test_instructor_gets_roster_without_money(client):
    term = client.get("/api/terms").json()[-1]["term_id"]
    program = client.get("/api/programs").json()[0]["program_id"]
    roster = client.get(f"/api/roster?program_id={program}&term_id={term}", headers={"X-Role": "instructor"})
    assert roster.status_code == 200
    assert all("balance" not in r for r in roster.json())
    assert client.get("/api/summary", headers={"X-Role": "instructor"}).status_code == 403


def test_unknown_role_rejected(client):
    assert client.get("/api/me", headers={"X-Role": "hacker"}).status_code == 400


def test_fee_schedule_filter(client):
    rows = client.get("/api/fee-schedules?program_id=PRG-001&term_id=TERM-2026-FALL").json()
    tech = [r for r in rows if r["fee_code"] == "TECH"]
    assert [r["version"] for r in tech] == [1, 2]
