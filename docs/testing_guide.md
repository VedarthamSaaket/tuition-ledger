# Testing and reviewer guide

This guide shows what the automated tests prove, how to run them, and how to exercise the five role workspaces manually. The checks are deterministic for seed `20261022` and the fixed snapshot date `2026-10-22`.

## 1. What the tests cover

| Requirement | Automated coverage |
| --- | --- |
| Fee calculation and term-specific schedules | `tests/test_rules.py`, `tests/test_generator_masters.py::test_charge_lines_use_schedule_in_effect_on_issue_date`, `test_fall_2026_uses_revised_tech_fee`; validation check `term specific fees` |
| Enrollments, invoices and lifecycle transitions | `tests/test_generator_billing.py::test_status_history_is_legal_and_matches_final_status`, `test_generator_masters.py::test_withdrawals_happen_inside_the_term`, `tests/test_db_load.py`, validation checks `lifecycle` and `duplicate` |
| Scholarship eligibility, caps and awards | `tests/test_rules.py`, `tests/test_generator_awards.py`, `tests/test_api_scholarships.py`; validation checks `eligibility outcome`, `awards only from eligible`, `scholarship within eligible fees` |
| Payment allocation, refunds and late fees | `tests/test_rules.py`, `tests/test_generator_billing.py`, `tests/test_api_payments.py`, `tests/test_api_late_fees.py` |
| Balance reconciliation | `tests/test_generator_billing.py::test_balances_reconcile_three_ways`, `tests/test_api_read.py::test_summary_reconciles`, `tests/test_checks.py`, `tests/test_db_load.py` |
| Five required anomalies | `tests/test_anomalies.py`; `tests/test_checks.py`; validation `EXPECTED` failures; `docs/full_exceptions.csv` and `docs/full_ground_truth.csv` |
| Ground truth kept separate | `tests/test_anomalies.py::test_ground_truth_is_not_in_input_tables`; `tests/test_io.py`; `data/*/ground_truth/` |
| Primary keys, foreign keys, enums, dates, duplicates | `tests/test_schema.py`, `tests/test_db_load.py`, `tests/test_checks.py` |
| Deterministic reprocessing | `tests/test_io.py::test_same_seed_gives_same_checksums`, `tests/test_generator_masters.py::test_same_seed_same_rows`; `data/starter/reproducibility.json` and `docs/full_reproducibility.json` |
| API role restrictions | `tests/test_api_read.py`, `tests/test_api_payments.py`, `tests/test_api_reconciliation.py` |
| Concurrency and idempotency | `tests/test_concurrency.py`, `tests/test_api_payments.py` |
| Frontend helpers | `frontend/lib/roles.test.js`, `money.test.js`, `table.test.js` |

There is no committed browser end-to-end suite. The UI was verified manually against both desktop and mobile widths; the walkthrough in section 5 is the reviewer path.

## 2. Setup

You need Python 3.12, PostgreSQL 16 and Node.js 22.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
createdb tuition_ledger
createdb tuition_ledger_test
set -a; source .env; set +a
```

The database tests use `TEST_DATABASE_URL` and recreate tables there. If the test database is unreachable, those tests skip; start PostgreSQL and set the URL to run the full suite.

## 3. Automated checks

```sh
ruff check .
pytest -q
npm --prefix frontend test
npm --prefix frontend run build
```

Expected results with a reachable test database:

- `ruff check .` — `All checks passed!`
- `pytest -q` — `88 passed`
- `npm --prefix frontend test` — `4` tests pass
- `npm --prefix frontend run build` — production build succeeds

The backend suite covers the generator, domain rules, validation, anomaly labels, database constraints, API permissions, payments, refunds, scholarships, withdrawals, late fees, reconciliation, concurrency and idempotency.

## 4. Dataset validation and reproducibility

The committed starter dataset is `data/starter`. The full dataset is `data/full` and is about 518 MB, so it is gitignored; the small evidence files are committed under `docs/`.

```sh
python -m ledger validate data/starter
python -m ledger reconcile data/starter

python -m ledger all --profile full --out data/full
python -m ledger validate data/full
python -m ledger reconcile data/full
```

Expected results:

- Starter validation: `103 checks, {'PASS': 96, 'EXPECTED': 7}, passed=True`.
- Full validation: `103 checks, {'PASS': 96, 'EXPECTED': 7}, passed=True`.
- Starter reconciliation: `78` labelled anomalies, precision `1.0`, recall `1.0`.
- Full reconciliation: `310` labelled anomalies, precision `1.0`, recall `1.0`.

`EXPECTED` means every failure is one of the deliberately labelled anomalies. `PASS` means no failures.

```sh
python -m ledger reproduce --profile starter --report data/starter/reproducibility.json
python -m ledger reproduce --profile full --report docs/full_reproducibility.json
```

Both reports should show `"identical": true` and matching checksums across two runs.

## 5. Reviewer walkthrough

Start the API and frontend:

```sh
python -m ledger load data/starter
uvicorn ledger.api.main:app --reload
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`.

1. **Landing page** — the first viewport shows the three-step “How to use” panel. The Learner field explains that `STU-000001` is a sample ID from the current dataset and that a replacement dataset may need a different ID. `Use sample` fills it.
2. **Learner** — select `Learner`, choose `Use sample`, then `Enter Tuition Ledger`. The workspace opens on `My account`, with `My account` and `Fees` in the left menu. `View ledger` shows ledger entries; selecting an invoice shows its lines, decisions and events.
3. **Instructor** — select `Instructor`. The workspace opens on `Roster`. Choose a programme and term, then `View roster`. The roster contains no balances.
4. **Academic administrator** — select this role. `Dashboard` shows counts, net billing and outstanding balances. `Students` supports search and account detail; `Setup` creates reference data and invoices; an invoice view offers scholarship assessment and withdrawal; `Exceptions` shows prior reconciliation runs.
5. **Finance and support** — select this role. It opens on `Dashboard`, can use `Students`, and can record externally processed payments and refunds. It cannot use `Setup` or start reconciliation.
6. **Platform administrator** — select this role. It has the broadest view: `Setup`, `Exceptions`, reconciliation runs, late-fee assessment, payments, refunds, scholarships and withdrawals.

Use `Change role` in the header to return to the landing page. Role selection is a demonstration of permissions, not authentication, and the application never transfers money.

## 6. API smoke checks

With the API running:

```sh
curl http://127.0.0.1:8000/api/health
curl -H 'X-Role: learner' -H 'X-Student-Id: STU-000001' \
  http://127.0.0.1:8000/api/students/STU-000001
curl -H 'X-Role: instructor' \
  'http://127.0.0.1:8000/api/roster?program_id=PRG-001&term_id=TERM-2027-SPRING'
curl -H 'X-Role: platform_admin' http://127.0.0.1:8000/api/summary
```

The learner response is the account and ledger view. The roster response contains no money fields. The summary reports the stored counts and status distribution.

## 7. Notes and limitations

- The committed starter dataset is 500 students. The full 10,000-student dataset is generated locally and its evidence is committed under `docs/`.
- The dataset is anchored to `2026-10-22`. Live API aging and effective dashboard aging use the current date, as documented in the README. Stored invoice statuses and the committed evaluation remain as of the fixed snapshot.
- The five role headers demonstrate access rules; they are not authentication.
- The anomaly detector is scored against synthetic labels produced from the same rules. Perfect precision and recall demonstrate consistency with those rules, not real-world performance.
