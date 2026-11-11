# tuition-ledger

Tuition, fees, scholarships and student balance reconciliation.
Built for the YottaFlex AI take home assignment.

The generator produces linked synthetic records, labelled exceptions and validation reports. The PostgreSQL-backed application provides account views, scholarship assessments, payment recording, refunds, withdrawals, late-fee assessment and reconciliation runs.

The role headers demonstrate access rules, not authentication: callers can choose a role and the default is platform administrator. There is no sign-in. Do not expose the application to an untrusted network or use real student data without an independently secured deployment boundary and a trusted identity/authorization mechanism. Code modules do not by themselves enforce separation of duties.

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

The loader recreates its tables and destroys existing data in the target database. To upgrade an existing loaded database without reloading it, run `python -m ledger migrate` first; this adds application tables and indexes without deleting ledger data. Open http://127.0.0.1:8000/docs for the API. Use `--profile full` for the full dataset, `--seed` to change the fixed seed, and `python -m ledger generate --clean` to omit anomalies.

For the React interface, install Node.js 22 and run in a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open the URL printed by Vite. Its development server proxies API requests to port 8000. On the landing page, choose a role and select Enter. Learners also provide their student ID; instructors can select a programme and term to view a roster. The interface is a local demo: selecting a role does not prove identity. Use Change role in the workspace to return to the landing page.

The interface uses locally bundled Playfair Display and DM Sans fonts. Their SIL Open Font License notices are in `frontend/assets/fonts/`.

## Test

```sh
ruff check .
pytest -q
npm --prefix frontend test
python -m ledger validate data/starter
python -m ledger reconcile data/starter
```

Configure a separate `tuition_ledger_test` database for database tests; tests may otherwise be skipped locally. Output includes CSV, JSON, SQL, checksums, validation, exceptions, evaluation and separate ground truth. Generate the dictionary with `python -m ledger dictionary --out docs`.

All monetary amounts are Indian rupees (INR), with calculations in integer paise; displays use Indian digit grouping. Existing numeric amounts are retained as rupee values, not converted using an exchange rate. Fee schedules are term-specific; scholarships are eligibility checked and capped; payment allocations, refunds and balances are derived from source records. The exception detector is scored against synthetic labels built from the same rules, so its scores do not establish real-world performance. No external personal data is used.

The default dataset intentionally contains anomalies; the validation report marks labelled failures as expected. The starter profile uses seed 20261022 and a fixed snapshot date of 2026-10-22. Live actions and live aging reports use the current date. Withdrawals reverse eligible fees and leave any credit for a separate refund decision. Refunds are limited by payment and account credit; resolve duplicate invoices before withdrawing. Financial writes reject accounts whose stored balance disagrees with their ledger. The API records payments and refunds already processed outside the application: it does not initiate a bank transfer or card charge. Payment and refund requests require an `Idempotency-Key` header, which must be reused for retries of the same request. The interface handles this automatically while the page remains open.

This application has no authentication or payment gateway. It has an additive schema upgrade command, but not a complete versioned migration and recovery system. Although the test suite includes competing invoice, refund and payment-retry requests, further security, operational and financial controls and independent review are required before use with real customers.

The backend separates API endpoints, request models, shared transaction services, domain rules, persistence, data generation and checks. The frontend separates API access, reusable table components, setup, account and billing views. The Setup screen creates programs, terms, students, fee schedules and enrollments and then issues invoices. New invoices require an effective tuition schedule and are limited to one per enrollment; overlapping schedules and backdated changes affecting issued invoices are rejected.

The committed starter dataset contains 500 students, 1,500 invoices, 750 awards and 2,500 payments. Its validation report has 96 passing and 7 expected checks; the detector finds 78 labelled anomalies in this synthetic profile. `data/starter/reproducibility.json` records matching checksums from two runs. See `docs/prompt_history.md` for available AI prompts and the limits of that record.
