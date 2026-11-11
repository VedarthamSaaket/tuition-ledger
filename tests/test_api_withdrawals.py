from datetime import date
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


def test_withdrawal_records_reversal_and_cannot_repeat(client, loaded_db, monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 22)

    monkeypatch.setattr('ledger.api.withdrawals.date', FixedDate)
    with psycopg.connect(loaded_db['url'], row_factory=dict_row) as conn:
        row = conn.execute("""SELECT e.enrollment_id,e.student_id FROM enrollments e
            JOIN terms t USING (term_id) WHERE e.status='ACTIVE' AND DATE '2026-10-22' BETWEEN t.start_date AND t.end_date
            AND (SELECT count(*) FROM invoices i WHERE i.enrollment_id=e.enrollment_id)=1
            LIMIT 1""").fetchone()
    assert row
    before = Decimal(client.get('/api/students/' + row['student_id']).json()['ledger_balance'])
    url = '/api/enrollments/' + row['enrollment_id'] + '/withdraw'
    response = client.post(url)
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'WITHDRAWN'
    after = Decimal(client.get('/api/students/' + row['student_id']).json()['ledger_balance'])
    assert after == before - Decimal(response.json()['reversal'])
    assert client.post(url).status_code == 409
