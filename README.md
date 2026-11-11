# tuition-ledger

Tuition, fees, scholarships and student balance reconciliation.
Built for the YottaFlex AI take home assignment.

The generator produces linked synthetic records, labelled exceptions and validation reports. The PostgreSQL-backed application provides account views, scholarship assessments, payment recording, refunds, withdrawals, late-fee assessment and reconciliation runs.

The role headers demonstrate access rules, not authentication: callers can choose a role and the default is platform administrator. There is no sign-in. Do not expose the application to an untrusted network or use real student data without an independently secured deployment boundary and a trusted identity/authorization mechanism. Code modules do not by themselves enforce separation of duties.

## Dataset profiles

| Profile | Students | Programs | Terms | Invoices | Awards | Payments | Labelled anomalies | Committed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| starter | 500 | 20 | 5 | 1,500 | 750 | 2,500 | 78 | `data/starter/` |
| full | 10,000 | 20 | 5 | 30,000 | 15,000 | 50,000 | 310 | evidence in `docs/`; regenerate `data/full/` |

`TERM-2027-SPRING` is an early-registration term: invoices are issued on 2026-10-05 and become due on 2026-11-16. With the snapshot at 2026-10-22, the dataset exercises every invoice state: `UNPAID`, `PARTIALLY_PAID`, `PAID`, `OVERDUE`, `IN_CREDIT` and `CANCELLED`. Status precedence is `CANCELLED`, `IN_CREDIT`, `PAID`, `OVERDUE` (on or after grace), `PARTIALLY_PAID` (before grace with an allocation), then `UNPAID`. Enrollments in a term that starts after the snapshot remain `REGISTERED`, and no event is dated after the snapshot.

The full profile is generated locally but not committed: the CSV/JSON/SQL export is about 518 MB. The committed starter profile uses the same generator at a smaller scale.

## Reviewer documents

- `docs/testing_guide.md` — requirement-to-test mapping, exact commands, expected results and a five-role walkthrough.
- `docs/reviews_and_decisions.md` — owner review requests, audit findings and the major design decisions.

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
python -m ledger reproduce --profile starter --report data/starter/reproducibility.json
python -m ledger load data/starter
uvicorn ledger.api.main:app --reload
```

The loader recreates its tables and destroys existing data in the target database. To upgrade an existing loaded database without reloading it, run `python -m ledger migrate` first; this adds application tables and indexes without deleting ledger data. Open http://127.0.0.1:8000/docs for the API. Use `--seed` to change the fixed seed and `python -m ledger generate --clean` to omit anomalies.

For the full 10,000-student volume:

```sh
python -m ledger all --profile full --out data/full
python -m ledger reproduce --profile full --report docs/full_reproducibility.json
python -m ledger load data/full
```

For the React interface, install Node.js 22 and run in a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open the URL printed by Vite. Its development server proxies API requests to port 8000. On the landing page, choose a role and select Enter. Learners also provide their student ID; instructors can select a programme and term to view a roster. The interface is a local demo: selecting a role does not prove identity. Use Change role in the workspace to return to the landing page.

The interface uses a locally bundled Libre Baskerville Italic font. Its SIL Open Font License notice is in `frontend/assets/fonts/LIBRE-BASKERVILLE-OFL.txt`.

## Full-profile evidence

The full-volume data is gitignored because of its size, so the small review artifacts are committed under `docs/`:

- `docs/full_manifest.json` — generator command, fixed seed, row counts and file checksums.
- `docs/full_validation_summary.json` and `.md` — all 103 checks, with 96 PASS and 7 EXPECTED, and zero unexplained failures.
- `docs/full_evaluation.json` — detection precision/recall, boundary cases and KPIs.
- `docs/full_exceptions.csv` — the 310 detected exceptions with related IDs and explanations.
- `docs/full_ground_truth.csv` — the 310 separate labels used for scoring, never loaded as input.
- `docs/full_reproducibility.json` — identical checksums from two independent runs.

The full run produces 10,000 students, 30,000 invoices, 15,000 awards, 50,000 payments, 29,940 enrollments, 143,096 payment allocations and 1,728 refunds. Detection found all 310 labelled anomalies with precision 1.0 and recall 1.0. Net billed is ₹22,49,61,455.41, collected is ₹20,54,12,087.28, the collection rate is 0.8823 and outstanding receivable is ₹2,94,35,110.12. Invoice states at the snapshot are `PAID` 23,517, `OVERDUE` 4,616, `PARTIALLY_PAID` 798, `UNPAID` 543, `CANCELLED` 368 and `IN_CREDIT` 158.

## Data provenance

No external or public dataset is used. Every row is produced by the fixed-seed generator in this repository; names are hand-written synthetic values, emails use `example.edu`, and no API, scrape or confidential data is involved. There is therefore no source URL, dataset version, retrieval date, licence, attribution, transformation or discarded-field list to record.

If external reference data is added later, record the source URL, dataset name and version, retrieval date, licence and terms, attribution, transformations and discarded fields here, and confirm redistribution rights before use. Do not add personal or confidential data.

## Test

```sh
ruff check .
pytest -q
npm --prefix frontend test
python -m ledger validate data/starter
python -m ledger reconcile data/starter
python -m ledger validate data/full
python -m ledger reconcile data/full
```

Configure a separate `tuition_ledger_test` database for database tests; tests may otherwise be skipped locally. Output includes CSV, JSON, SQL, checksums, validation, exceptions, evaluation and separate ground truth. Generate the dictionary with `python -m ledger dictionary --out docs`.

All monetary amounts are Indian rupees (INR), with calculations in integer paise; displays use Indian digit grouping. Existing numeric amounts are retained as rupee values, not converted using an exchange rate. Fee schedules are term-specific; scholarships are eligibility checked and capped; payment allocations, refunds and balances are derived from source records. The exception detector is scored against synthetic labels built from the same rules, so its scores do not establish real-world performance. No external personal data is used.

The default dataset intentionally contains anomalies; the validation report marks labelled failures as expected. The starter profile uses seed 20261022 and a fixed snapshot date of 2026-10-22. Live actions and live aging reports use the current date. Withdrawals reverse eligible fees and leave any credit for a separate refund decision. Refunds are limited by payment and account credit; resolve duplicate invoices before withdrawing. Financial writes reject accounts whose stored balance disagrees with their ledger. The API records payments and refunds already processed outside the application: it does not initiate a bank transfer or card charge. Payment and refund requests require an `Idempotency-Key` header, which must be reused for retries of the same request. The interface handles this automatically while the page remains open.

This application has no authentication or payment gateway. It has an additive schema upgrade command, but not a complete versioned migration and recovery system. Although the test suite includes competing invoice, refund and payment-retry requests, further security, operational and financial controls and independent review are required before use with real customers.

The backend separates API endpoints, request models, shared transaction services, domain rules, persistence, data generation and checks. The frontend separates API access, reusable table components, setup, account and billing views. The Setup screen creates programs, terms, students, fee schedules and enrollments and then issues invoices. New invoices require an effective tuition schedule and are limited to one per enrollment; overlapping schedules and backdated changes affecting issued invoices are rejected.

The committed starter dataset contains 500 students, 5 terms, 1,500 invoices, 750 awards and 2,500 payments, and exercises all six invoice states. Its validation report has 96 passing and 7 expected checks; the detector finds 78 labelled anomalies in this synthetic profile. `data/starter/reproducibility.json` records matching checksums from two runs. See `docs/prompt_history.md` for available AI prompts and the limits of that record.
