import psycopg
from psycopg.rows import dict_row


def test_late_fee_is_idempotent(client, loaded_db):
    with psycopg.connect(loaded_db['url'], row_factory=dict_row) as conn:
        invoice = conn.execute("""SELECT i.invoice_id FROM invoices i WHERE i.balance > 0
            AND i.status <> 'CANCELLED' AND i.due_date < CURRENT_DATE - 30
            AND NOT EXISTS (SELECT 1 FROM invoice_lines l WHERE l.invoice_id=i.invoice_id AND l.line_type='LATE_FEE')
            LIMIT 1""").fetchone()
    assert invoice is not None
    url = '/api/invoices/' + invoice['invoice_id'] + '/late-fee'
    result = client.post(url)
    assert result.status_code == 200, result.text
    assert 25 <= float(result.json()['amount']) <= 150
    assert client.post(url).status_code == 409
