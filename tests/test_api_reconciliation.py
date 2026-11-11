def test_reconciliation_persists_results(client):
    response = client.post('/api/reconciliation/runs')
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['exceptions_found'] > 0
    runs = client.get('/api/reconciliation/runs').json()
    assert any(run['run_id'] == result['run_id'] for run in runs)
    exceptions = client.get(f"/api/reconciliation/runs/{result['run_id']}/exceptions").json()
    assert len(exceptions) == result['exceptions_found']


def test_learner_cannot_run_reconciliation(client):
    response = client.post('/api/reconciliation/runs', headers={'X-Role': 'learner', 'X-Student-Id': 'STU-000001'})
    assert response.status_code == 403
