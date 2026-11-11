from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal


def test_concurrent_refunds_do_not_exceed_available_credit(client):
    sid = client.get('/api/students?sort=id&limit=1').json()['items'][0]['student_id']
    student = client.get(f'/api/students/{sid}').json()
    invoice_id = next(e['invoice_id'] for e in student['enrollments'] if e['invoice_status'] != 'CANCELLED')
    payment = client.post('/api/payments', json={'invoice_id': invoice_id, 'amount': '100000.00', 'method': 'CARD'})
    assert payment.status_code == 201, payment.text
    assert Decimal(payment.json()['unapplied']) > Decimal('60000')
    payload = {'payment_id': payment.json()['payment_id'], 'amount': '60000.00'}
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: client.post('/api/refunds', json=payload), range(2)))
    assert sorted(result.status_code for result in results) == [201, 409]
    record = client.get('/api/payments/' + payment.json()['payment_id']).json()
    assert sum(Decimal(refund['amount']) for refund in record['refunds']) == Decimal('60000')


def test_simultaneous_payment_retries_create_only_one_payment(client):
    sid = client.get('/api/students?sort=id&limit=1').json()['items'][0]['student_id']
    student = client.get(f'/api/students/{sid}').json()
    invoice_id = next(e['invoice_id'] for e in student['enrollments'] if e['invoice_status'] != 'CANCELLED')
    payload = {'invoice_id': invoice_id, 'amount': '19.00', 'method': 'CARD'}
    headers = {'Idempotency-Key': 'concurrent-payment-retry-12345'}
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: client.post('/api/payments', json=payload, headers=headers), range(2)))
    assert [r.status_code for r in results] == [201, 201]
    assert results[0].json() == results[1].json()
