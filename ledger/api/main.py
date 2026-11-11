from fastapi import FastAPI

from . import read

app = FastAPI(title="Tuition Ledger", version="0.2.0")
app.include_router(read.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
