from decimal import Decimal


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
