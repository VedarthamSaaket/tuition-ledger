from fastapi import FastAPI

from . import read, reconciliation

app = FastAPI(title="Tuition Ledger", version="0.2.0")
app.include_router(read.router)
app.include_router(reconciliation.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
