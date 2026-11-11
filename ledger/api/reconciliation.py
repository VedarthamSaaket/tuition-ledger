from datetime import UTC, date, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends
from psycopg.types.json import Jsonb

from ..checks import reconcile
from ..db.conn import paise, rupees
from ..schema import LOAD_ORDER, TABLES_BY_NAME
from .deps import get_db, require

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])
ADMIN = Depends(require("platform_admin"))
STAFF = Depends(require("platform_admin", "academic_admin", "support_staff"))


@router.post("/runs")
def run(db=Depends(get_db), actor=ADMIN):
    started = datetime.now(UTC)
    tables = {}
    for name in LOAD_ORDER:
        rows = db.execute(f"SELECT * FROM {name}").fetchall()
        monetary = [col.name for col in TABLES_BY_NAME[name].cols if col.type == "money"]
        for row in rows:
            for col in monetary:
                row[col] = paise(row[col])
        tables[name] = rows
    found = reconcile.detect(tables)
    boundaries = reconcile.boundary_cases(tables, found)
    kpis = reconcile.kpis(tables, as_of=date.today())
    run_id = f"RUN-{uuid4()}"
    db.execute("INSERT INTO reconciliation_runs VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
               (run_id, started, datetime.now(UTC), actor.role, len(found), None,
                Jsonb(boundaries), Jsonb(kpis)))
    for row in found:
        db.execute("INSERT INTO exceptions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                   (row["exception_id"], run_id, row["issue_type"], row["entity_type"], row["entity_id"],
                    row["related_ids"], row["expected_decision"], rupees(row["detected_value"]),
                    row["explanation"]))
    db.commit()
    return {"run_id": run_id, "exceptions_found": len(found), "kpis": kpis, "boundary_cases": boundaries}


@router.get("/runs")
def runs(db=Depends(get_db), actor=STAFF):
    return db.execute("SELECT * FROM reconciliation_runs ORDER BY started_at DESC LIMIT 50").fetchall()


@router.get("/runs/{run_id}/exceptions")
def exceptions(run_id: str, db=Depends(get_db), actor=STAFF):
    return db.execute("SELECT * FROM exceptions WHERE run_id = %s ORDER BY exception_id", (run_id,)).fetchall()
