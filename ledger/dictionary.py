import csv
from pathlib import Path

from .schema import GROUND_TRUTH, TABLES

RELATIONSHIPS = (
    "Program 1 to N Student, every student is admitted to exactly one program",
    "Program 1 to N FeeSchedule, Term 1 to N FeeSchedule",
    "Student 1 to N Enrollment, at most one enrollment per student per term",
    "Enrollment 1 to 1 Invoice in clean data, a second invoice for the same enrollment is the DUPLICATE_INVOICE anomaly",
    "Invoice 1 to N InvoiceLine",
    "InvoiceLine 0..1 to N InvoiceLine through applies_to_line_id, credits and reversals point at the charge they reduce",
    "FeeSchedule 1 to N InvoiceLine, every CHARGE line records the schedule row it was priced from",
    "Student N to M ScholarshipScheme through Eligibility (bridge)",
    "Eligibility 1 to 0..1 Scholarship, only eligible assessments become awards",
    "Scholarship 1 to N InvoiceLine, one credit line per fee code covered",
    "Student 1 to N Payment, Invoice 1 to N Payment through the quoted reference",
    "Payment N to M InvoiceLine through PaymentAllocation (bridge)",
    "Payment 1 to N Refund, Invoice 0..1 to N Refund",
    "Student 1 to N LedgerEntry, Student 1 to 1 StudentAccount",
    "Every entity 1 to N Event and 1 to N Decision through entity_type and entity_id",
)


def rows():
    for table in (*TABLES, GROUND_TRUTH):
        for col in table.cols:
            yield table, col


def write(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "data_dictionary.csv", "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["table", "entity", "field", "type", "required", "unique", "allowed_values",
                         "unit", "foreign_key", "validation_rule", "description"])
        for table, col in rows():
            writer.writerow([
                table.name, table.entity, col.name, col.type, "yes" if col.required else "no",
                "yes" if col.unique or col.name == table.pk else "no",
                "|".join(col.allowed) if col.allowed else "", col.unit or "", col.fk or "", col.rule,
                col.desc,
            ])
    lines = ["# Data dictionary", "", "Generated from ledger/schema.py by python -m ledger dictionary.",
             "Money is stored as dollars with two decimals and handled as integer cents in code.", "",
             "## Relationships", ""]
    lines += [f"- {r}" for r in RELATIONSHIPS]
    for table in (*TABLES, GROUND_TRUTH):
        lines += ["", f"## {table.entity} ({table.name})", "", table.desc, f"Primary key is {table.pk}.", ""]
        for col in table.cols:
            bits = [col.type, "required" if col.required else "optional"]
            if col.unique or col.name == table.pk:
                bits.append("unique")
            if col.unit:
                bits.append(f"unit {col.unit}")
            if col.fk:
                bits.append(f"references {col.fk}")
            if col.allowed:
                bits.append(f"one of {', '.join(col.allowed)}")
            if col.rule:
                bits.append(col.rule)
            lines.append(f"- {col.name}: {col.desc}. {'; '.join(bits)}")
    (out_dir / "data_dictionary.md").write_text("\n".join(lines) + "\n")
