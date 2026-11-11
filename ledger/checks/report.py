import csv
import json
from pathlib import Path

from ..io import read_csv_dir, read_ground_truth
from . import reconcile, validate

EXCEPTION_COLUMNS = ("exception_id", "issue_type", "entity_type", "entity_id", "related_ids", "expected_decision",
                     "detected_value", "explanation")


def load(dataset: Path) -> tuple[dict, list[dict]]:
    tables = read_csv_dir(dataset / "csv")
    gt_path = dataset / "ground_truth" / "ground_truth.csv"
    return tables, read_ground_truth(gt_path) if gt_path.exists() else []


def validation_markdown(result: dict) -> str:
    lines = ["# Validation summary", "", f"As of {result['as_of']}.",
             f"{result['checks']} checks ran, result counts {result['summary']}.",
             "PASS means no failures.",
             "EXPECTED means every failure is one of the labelled anomalies in ground_truth.csv.",
             "FAIL means at least one failure is not explained by a label.", ""]
    for r in result["results"]:
        line = f"- {r['status']} {r['check']} ({r['checked']} checked, {r['failures']} failures"
        if r["failures"]:
            line += f", {r['explained_by_ground_truth']} labelled"
        lines.append(line + ")")
    return "\n".join(lines) + "\n"


def run_validate(dataset: Path) -> dict:
    tables, gt = load(dataset)
    result = validate.run(tables, gt)
    (dataset / "validation_summary.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    (dataset / "validation_summary.md").write_text(validation_markdown(result))
    return result


def run_reconcile(dataset: Path) -> dict:
    tables, gt = load(dataset)
    found = reconcile.detect(tables)
    with open(dataset / "exceptions.csv", "w", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(EXCEPTION_COLUMNS)
        for f in found:
            value = f"{f['detected_value'] / 100:.2f}"
            writer.writerow([f["exception_id"], f["issue_type"], f["entity_type"], f["entity_id"],
                             f["related_ids"] or "", f["expected_decision"], value, f["explanation"]])
    report = {
        "detection": reconcile.evaluate(found, gt) if gt else None,
        "boundary_cases": reconcile.boundary_cases(tables, found),
        "kpis": reconcile.kpis(tables),
    }
    (dataset / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
