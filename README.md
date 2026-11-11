# tuition-ledger

Tuition, fees, scholarships and student balance reconciliation.
Built for the YottaFlex AI take home assignment.

This is the starting skeleton.
Right now it is a FastAPI app with a health check, a test, and CI on GitHub Actions.

## Setup

You need Python 3.11 or newer and PostgreSQL 16.

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env

## Run

uvicorn ledger.api.main:app --reload

## Test

ruff check .
pytest -q
