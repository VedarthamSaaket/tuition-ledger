# tuition-ledger

Tuition, fees, scholarships and student balance reconciliation.
Built for the YottaFlex AI take home assignment.

The generator produces linked synthetic records, labelled exceptions and validation reports. The PostgreSQL-backed application provides account views, payment recording, refunds of unapplied credit and reconciliation runs. Interactive scholarship assessment, withdrawals and late-fee processing are not yet implemented.

The role headers demonstrate access rules, not authentication: callers can choose a role and the default is platform administrator. Do not expose this prototype to an untrusted network or use real student data.

## Setup

You need Python 3.11 or newer and PostgreSQL 16.

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env

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
