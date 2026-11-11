from decimal import Decimal

import psycopg
from fastapi.testclient import TestClient


def test_payment_updates_ledger_and_allocations(client):
    student = client.get('/api/students?limit=1').json()['items'][0]['student_id']
    before = client.get(f'/api/students/{student}').json()
    invoice = next(e['invoice_id'] for e in before['enrollments'] if e['invoice_status'] != 'CANCELLED')
    result = client.post('/api/payments', json={'invoice_id': invoice, 'amount': '50.00', 'method': 'CARD'})
    assert result.status_code == 201, result.text
    after = client.get(f'/api/students/{student}').json()
    assert Decimal(after['ledger_balance']) == Decimal(before['ledger_balance']) - Decimal('50')
    payment = client.get('/api/payments/' + result.json()['payment_id']).json()
    assert sum(Decimal(a['amount']) for a in payment['allocations']) == Decimal(result.json()['allocated'])


def test_other_learner_cannot_pay(client):
    student = client.get('/api/students?limit=1').json()['items'][0]['student_id']
    invoice = client.get(f'/api/students/{student}').json()['enrollments'][0]['invoice_id']
    response = client.post('/api/payments', json={'invoice_id': invoice, 'amount': '50', 'method': 'CARD'},
                           headers={'X-Role': 'learner', 'X-Student-Id': 'STU-999999'})
    assert response.status_code == 403


def test_refund_is_limited_and_rejection_is_recorded(client):
    student = client.get('/api/students?limit=1').json()['items'][0]['student_id']
    detail = client.get(f'/api/students/{student}').json()
    invoice = next(e['invoice_id'] for e in detail['enrollments'] if e['invoice_status'] != 'CANCELLED')
    payment = client.post('/api/payments', json={'invoice_id': invoice, 'amount': '100000.00', 'method': 'CARD'}).json()
    rejected = client.post('/api/refunds', json={'payment_id': payment['payment_id'], 'amount': '100001.00'})
    assert rejected.status_code == 409
    decisions = client.get('/api/decisions', params={'entity_id': payment['payment_id']}).json()
    assert any(d['outcome'] == 'REJECTED' for d in decisions)
    before = Decimal(client.get(f'/api/students/{student}').json()['ledger_balance'])
    refund_payload = {'payment_id': payment['payment_id'], 'amount': '10.00'}
    refund_headers = {'Idempotency-Key': 'refund-retry-test-00001'}
    accepted = client.post('/api/refunds', json=refund_payload, headers=refund_headers)
    assert accepted.status_code == 201, accepted.text
    retry = client.post('/api/refunds', json=refund_payload, headers=refund_headers)
    assert retry.status_code == 201 and retry.json() == accepted.json()
    after = Decimal(client.get(f'/api/students/{student}').json()['ledger_balance'])
    assert after == before + Decimal('10')


def test_payment_refuses_unreconciled_account(client, loaded_db):
    student = client.get('/api/students?limit=1').json()['items'][0]['student_id']
    invoice = next(e['invoice_id'] for e in client.get(f'/api/students/{student}').json()['enrollments']
                   if e['invoice_status'] != 'CANCELLED')
    with psycopg.connect(loaded_db['url']) as conn:
        conn.execute('UPDATE student_accounts SET balance=balance+1 WHERE student_id=%s', (student,))
    try:
        response = client.post('/api/payments', json={'invoice_id': invoice, 'amount': '1', 'method': 'CARD'})
        assert response.status_code == 409
        assert 'does not reconcile' in response.json()['detail']
    finally:
        with psycopg.connect(loaded_db['url']) as conn:
            conn.execute('UPDATE student_accounts SET balance=balance-1 WHERE student_id=%s', (student,))


def test_payment_retry_is_idempotent_and_changed_request_is_rejected(client):
    student = client.get('/api/students?limit=1').json()['items'][0]['student_id']
    invoice = next(e['invoice_id'] for e in client.get(f'/api/students/{student}').json()['enrollments']
                   if e['invoice_status'] != 'CANCELLED')
    payload = {'invoice_id': invoice, 'amount': '17.00', 'method': 'CARD'}
    headers = {'Idempotency-Key': 'payment-retry-test-00001'}
    first = client.post('/api/payments', json=payload, headers=headers)
    second = client.post('/api/payments', json=payload, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert client.post('/api/payments', json={**payload, 'amount': '18.00'}, headers=headers).status_code == 409
    from ledger.api.main import app

    assert TestClient(app).post('/api/payments', json=payload).status_code == 422
