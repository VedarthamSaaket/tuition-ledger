# tuition-ledger

Tuition, fees, scholarships and student balance reconciliation.
Built for the YottaFlex AI take home assignment.

The generator produces linked synthetic records, labelled exceptions and validation reports. The PostgreSQL-backed application provides account views, scholarship assessments, payment recording, refunds, withdrawals, late-fee assessment and reconciliation runs.

The role headers demonstrate access rules, not authentication: callers can choose a role and the default is platform administrator. Do not expose this prototype to an untrusted network or use real student data.

## Setup

You need Python 3.11 or newer and PostgreSQL 16.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

For a default local server, create both databases with `createdb tuition_ledger` and `createdb tuition_ledger_test`. Edit the URLs in `.env` if credentials or a different host are required, then export them with `set -a; source .env; set +a` in each terminal. Tests recreate tables in the test database: use a dedicated database.

## Run

Create a dedicated PostgreSQL database named `tuition_ledger`, then run:

```sh
python -m ledger all --profile starter --out data/starter
python -m ledger reproduce --profile starter --report data/reproducibility.json
python -m ledger load data/starter
uvicorn ledger.api.main:app --reload
```

The loader recreates its tables and destroys existing data in the target database. Open http://127.0.0.1:8000/docs for the API. Use `--profile full` for the full dataset, `--seed` to change the fixed seed, and `python -m ledger generate --clean` to omit anomalies.

For the React interface, install Node.js 22 and run in a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open the URL printed by Vite. Its development server proxies API requests to port 8000. The interface is a local demo: selecting a role does not prove identity.

## Test

```sh
ruff check .
pytest -q
python -m ledger validate data/starter
python -m ledger reconcile data/starter
```

Configure a separate `tuition_ledger_test` database for database tests; tests may otherwise be skipped locally. Output includes CSV, JSON, SQL, checksums, validation, exceptions, evaluation and separate ground truth. Generate the dictionary with `python -m ledger dictionary --out docs`.

Money is calculated in integer cents. Fee schedules are term-specific; scholarships are eligibility checked and capped; payment allocations, refunds and balances are derived from source records. The exception detector is scored against synthetic labels built from the same rules, so its scores do not establish real-world performance. No external personal data is used.

The default dataset intentionally contains anomalies; the validation report marks labelled failures as expected. The starter profile uses seed 20261022 and a fixed snapshot date of 2026-10-22. Live actions use the machine's current date. Withdrawals reverse eligible fees and leave any credit for a separate refund decision. Refunds are limited by payment and account credit; resolve duplicate invoices before withdrawing. This demonstration has no authentication, payment gateway, migration framework or production deployment. The transaction flows require further review and concurrency testing before real use.

The committed starter dataset contains 500 students, 1,500 invoices, 750 awards and 2,500 payments. Its validation report has 96 passing and 7 expected checks; the detector finds 78 labelled anomalies in this synthetic profile. `data/starter/reproducibility.json` records matching checksums from two runs. See `docs/prompt_history.md` for available AI prompts and the limits of that record.
