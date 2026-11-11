from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal


def test_create_catalog_enrollment_and_invoice(client):
    today = date.today()
    year = today.year + 1
    program = client.post('/api/programs', json={'name': 'Test Program', 'level': 'UG',
                          'department': 'STEM', 'has_lab': False})
    assert program.status_code == 201, program.text
    program_id = program.json()['program_id']
    term = client.post('/api/terms', json={'name': 'Test Term', 'season': 'FALL', 'year': year,
                       'invoice_date': today.isoformat(), 'start_date': f'{year}-08-01',
                       'due_date': f'{year}-09-01', 'end_date': f'{year}-12-01'})
    assert term.status_code == 201, term.text
    term_id = term.json()['term_id']
    student = client.post('/api/students', json={'first_name': 'Test', 'last_name': 'Student',
                          'email': 'new.student@example.edu', 'program_id': program_id, 'admit_term_id': term_id,
                          'residency': 'DOMESTIC', 'income_band': 'LOW', 'gpa': 3.5})
    assert student.status_code == 201, student.text
    student_id = student.json()['student_id']
    enrollment = client.post('/api/enrollments', json={'student_id': student_id, 'term_id': term_id, 'credits': 12})
    assert enrollment.status_code == 201, enrollment.text
    enrollment_id = enrollment.json()['enrollment_id']
    invoice_url = f'/api/enrollments/{enrollment_id}/invoice'
    assert client.post(invoice_url).status_code == 409
    fee = {'program_id': program_id, 'term_id': term_id, 'fee_code': 'TUITION', 'rate': '125.00',
           'applies_when': 'ALL', 'effective_from': today.isoformat()}
    schedule = client.post('/api/fee-schedules', json=fee)
    assert schedule.status_code == 201, schedule.text
    assert client.post('/api/fee-schedules', json=fee).status_code == 409
    with ThreadPoolExecutor(max_workers=2) as workers:
        issued = list(workers.map(lambda _: client.post(invoice_url), range(2)))
    assert sorted(response.status_code for response in issued) == [201, 409]
    invoice = next(response for response in issued if response.status_code == 201)
    assert Decimal(invoice.json()['net_amount']) == Decimal('1500.00')
    detail = client.get('/api/invoices/' + invoice.json()['invoice_id']).json()
    assert detail['lines'][0]['fee_schedule_id'] == schedule.json()['fee_schedule_id']
    assert Decimal(client.get('/api/students/' + student_id).json()['ledger_balance']) == Decimal('1500.00')
    assert client.post(invoice_url).status_code == 409


def test_reject_invalid_term_dates(client):
    today = date.today()
    response = client.post('/api/terms', json={'name': 'Bad', 'season': 'SPRING', 'year': today.year,
                           'invoice_date': (today + timedelta(days=3)).isoformat(),
                           'start_date': today.isoformat(), 'due_date': today.isoformat(),
                           'end_date': today.isoformat()})
    assert response.status_code == 422
