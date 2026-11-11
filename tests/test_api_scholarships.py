from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


def test_scholarship_award_is_capped_and_recorded(client, loaded_db):
    with psycopg.connect(loaded_db['url'], row_factory=dict_row) as conn:
        row = conn.execute("""SELECT i.invoice_id, i.student_id FROM invoices i
            JOIN enrollments e USING (enrollment_id) JOIN students s ON s.student_id=i.student_id
            WHERE e.status IN ('REGISTERED','ACTIVE') AND s.income_band='LOW'
            AND NOT EXISTS (SELECT 1 FROM scholarships sc WHERE sc.invoice_id=i.invoice_id
                AND sc.award_type='SCHOLARSHIP' AND sc.status='AWARDED') LIMIT 1""").fetchone()
    assert row
    before = Decimal(client.get('/api/students/' + row['student_id']).json()['ledger_balance'])
    result = client.post('/api/scholarship-assessments', json={'invoice_id': row['invoice_id'], 'scheme_id': 'SCHEME-NEED'})
    assert result.status_code == 200, result.text
    award = Decimal(result.json()['award_amount'])
    assert Decimal(0) < award <= Decimal(2000)
    after = Decimal(client.get('/api/students/' + row['student_id']).json()['ledger_balance'])
    assert after == before - award
    assert client.post('/api/scholarship-assessments', json={'invoice_id': row['invoice_id'],
                       'scheme_id': 'SCHEME-NEED'}).status_code == 409
