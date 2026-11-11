from dataclasses import dataclass

from .domain import catalog


@dataclass(frozen=True)
class Col:
    name: str
    type: str
    desc: str
    required: bool = True
    allowed: tuple | None = None
    unique: bool = False
    fk: str | None = None
    unit: str | None = None
    rule: str = ""


@dataclass(frozen=True)
class Table:
    name: str
    entity: str
    pk: str
    desc: str
    cols: tuple[Col, ...]

    def col(self, name: str) -> Col:
        return next(c for c in self.cols if c.name == name)


def pk(name: str, pattern: str, desc: str) -> Col:
    return Col(name, "id", desc, unique=True, rule=f"pattern {pattern}")


ENROLLMENT_STATUS = catalog.ENROLLMENT_STATES
INVOICE_STATUS = catalog.INVOICE_STATES

TABLES = (
    Table("programs", "Program", "program_id", "Academic programs offered by the institution.", (
        pk("program_id", "PRG-000", "Program identifier"),
        Col("name", "text", "Program name", unique=True),
        Col("level", "text", "Award level", allowed=catalog.LEVELS),
        Col("department", "text", "Owning department", allowed=("STEM", "BUSINESS", "ARTS", "HEALTH")),
        Col("has_lab", "bool", "Whether the program charges a lab fee"),
        Col("full_time_credits", "int", "Credits per term that count as full time", unit="credits",
            rule="12 for UG and DIP, 9 for PG and CERT"),
        Col("status", "text", "Program lifecycle state", allowed=("ACTIVE", "RETIRED")),
    )),
    Table("terms", "Term", "term_id", "Academic terms and their billing calendar.", (
        pk("term_id", "TERM-YYYY-SEASON", "Term identifier"),
        Col("name", "text", "Display name"),
        Col("season", "text", "Season", allowed=("FALL", "SPRING", "SUMMER")),
        Col("year", "int", "Calendar year of the term"),
        Col("invoice_date", "date", "Date invoices are issued", rule="before start_date"),
        Col("start_date", "date", "First day of classes"),
        Col("due_date", "date", "Payment due date", rule="after invoice_date"),
        Col("end_date", "date", "Last day of term", rule="after start_date"),
    )),
    Table("students", "Student", "student_id", "Synthetic learners. No real people.", (
        pk("student_id", "STU-000000", "Student identifier"),
        Col("first_name", "text", "Synthetic first name"),
        Col("last_name", "text", "Synthetic last name"),
        Col("email", "text", "Synthetic email on example.edu", unique=True),
        Col("program_id", "id", "Program the student is admitted to", fk="programs.program_id"),
        Col("admit_term_id", "id", "First term of study", fk="terms.term_id"),
        Col("residency", "text", "Fee residency", allowed=catalog.RESIDENCY),
        Col("income_band", "text", "Household income band for need based aid", allowed=catalog.INCOME_BANDS),
        Col("gpa", "float", "Cumulative GPA used for merit rules", unit="0.00 to 4.00", rule="1.80 to 4.00"),
        Col("has_external_cover", "bool", "Has outside health insurance, so health fee does not apply"),
        Col("staff_dependent", "bool", "Dependent of a staff member"),
        Col("created_on", "date", "Record creation date"),
    )),
    Table("fee_schedules", "FeeSchedule", "fee_schedule_id",
          "Fee rates by program, term and fee code with effective dating.", (
        pk("fee_schedule_id", "FS-<program>-<term>-<fee>-V<n>", "Fee schedule row identifier"),
        Col("program_id", "id", "Program", fk="programs.program_id"),
        Col("term_id", "id", "Term", fk="terms.term_id"),
        Col("fee_code", "text", "Fee code", allowed=catalog.FEE_CODES),
        Col("basis", "text", "Charging basis", allowed=("PER_CREDIT", "FLAT")),
        Col("rate", "money", "Rate per credit or flat amount", unit="USD"),
        Col("applies_when", "text", "Condition for the fee to be billed", allowed=catalog.APPLIES_WHEN),
        Col("version", "int", "Schedule version for this program, term and fee"),
        Col("effective_from", "date", "First day this rate is in effect"),
        Col("effective_to", "date", "Last day this rate is in effect", required=False,
            rule="null means open ended, versions never overlap"),
    )),
    Table("enrollments", "Enrollment", "enrollment_id", "A student taking a program in one term.", (
        pk("enrollment_id", "ENR-<student>-<term>", "Enrollment identifier"),
        Col("student_id", "id", "Student", fk="students.student_id"),
        Col("program_id", "id", "Program", fk="programs.program_id", rule="equals the student program"),
        Col("term_id", "id", "Term", fk="terms.term_id"),
        Col("credits", "int", "Credits registered", unit="credits", rule="1 to 18"),
        Col("load", "text", "Load derived from credits", allowed=("FULL_TIME", "PART_TIME")),
        Col("registered_on", "date", "Registration date", rule="on or before term invoice date"),
        Col("status", "text", "Current lifecycle state", allowed=ENROLLMENT_STATUS),
        Col("status_on", "date", "Date of the latest state change"),
        Col("exit_date", "date", "Withdrawal or cancellation date", required=False),
        Col("refund_percent", "int", "Tuition refund percent applied on exit", required=False, unit="%"),
    )),
    Table("invoices", "Invoice", "invoice_id", "One invoice per enrollment, built from eligible fee lines.", (
        pk("invoice_id", "INV-STU-000000-YYYY-000000", "Invoice identifier"),
        Col("student_id", "id", "Student", fk="students.student_id"),
        Col("enrollment_id", "id", "Enrollment billed", fk="enrollments.enrollment_id"),
        Col("term_id", "id", "Term", fk="terms.term_id"),
        Col("issue_date", "date", "Issue date"),
        Col("due_date", "date", "Due date", rule="after issue_date"),
        Col("total_charges", "money", "Sum of CHARGE and LATE_FEE lines", unit="USD", rule="derived"),
        Col("total_credits", "money", "Sum of scholarship and waiver credits", unit="USD", rule="derived"),
        Col("total_reversals", "money", "Sum of withdrawal and cancellation reversals", unit="USD",
            rule="derived"),
        Col("net_amount", "money", "Charges minus credits minus reversals", unit="USD", rule="derived"),
        Col("amount_allocated", "money", "Payments allocated to the lines", unit="USD", rule="derived"),
        Col("amount_refunded", "money", "Refunds paid out against this invoice", unit="USD", rule="derived"),
        Col("balance", "money", "net_amount minus allocated plus refunded", unit="USD", rule="derived"),
        Col("status", "text", "Status as of the dataset date", allowed=INVOICE_STATUS, rule="derived"),
    )),
    Table("invoice_lines", "InvoiceLine", "line_id", "Charges and credits on an invoice. Never edited.", (
        pk("line_id", "<invoice>-L00", "Line identifier"),
        Col("invoice_id", "id", "Invoice", fk="invoices.invoice_id"),
        Col("line_no", "int", "Line number within invoice"),
        Col("line_type", "text", "Line type", allowed=catalog.LINE_TYPES),
        Col("fee_code", "text", "Fee code", allowed=(*catalog.FEE_CODES, "LATE_FEE")),
        Col("fee_schedule_id", "id", "Schedule row priced from", required=False,
            fk="fee_schedules.fee_schedule_id", rule="required for CHARGE lines"),
        Col("quantity", "int", "Credits or 1", required=False),
        Col("unit_amount", "money", "Rate used", required=False, unit="USD"),
        Col("amount", "money", "Signed amount, charges positive, credits negative", unit="USD"),
        Col("applies_to_line_id", "id", "Charge line a credit or reversal reduces", required=False,
            fk="invoice_lines.line_id"),
        Col("scholarship_id", "id", "Award behind a credit line", required=False,
            fk="scholarships.scholarship_id"),
        Col("posted_on", "date", "Date the line was posted"),
        Col("description", "text", "Human readable reason"),
    )),
    Table("scholarship_schemes", "ScholarshipScheme", "scheme_id",
          "Reference table of scholarship and waiver rules.", (
        pk("scheme_id", "SCHEME-<NAME>", "Scheme identifier"),
        Col("name", "text", "Scheme name"),
        Col("award_type", "text", "Scholarship or waiver", allowed=("SCHOLARSHIP", "WAIVER")),
        Col("basis", "text", "Percent of eligible fees or fixed amount", allowed=("PERCENT", "FIXED")),
        Col("value", "int", "Percent for PERCENT, cents for FIXED"),
        Col("cap", "money", "Maximum award", required=False, unit="USD"),
        Col("fee_codes", "text", "Eligible fee codes, pipe separated"),
        Col("criteria", "text", "Readable eligibility criteria"),
    )),
    Table("eligibility", "Eligibility", "eligibility_id",
          "Bridge between students and schemes. One assessment per application.", (
        pk("eligibility_id", "ELG-YYYY-000000", "Assessment identifier"),
        Col("student_id", "id", "Student", fk="students.student_id"),
        Col("enrollment_id", "id", "Enrollment assessed for", fk="enrollments.enrollment_id"),
        Col("scheme_id", "id", "Scheme applied for", fk="scholarship_schemes.scheme_id"),
        Col("assessed_on", "date", "Assessment date"),
        Col("gpa", "float", "GPA at assessment"),
        Col("income_band", "text", "Income band at assessment", allowed=catalog.INCOME_BANDS),
        Col("credits", "int", "Credits at assessment"),
        Col("is_eligible", "bool", "Rule outcome"),
        Col("passed_criteria", "text", "Criteria met, pipe separated", required=False),
        Col("failed_criteria", "text", "Criteria failed, pipe separated", required=False),
    )),
    Table("scholarships", "Scholarship", "scholarship_id", "Awards made from eligible assessments.", (
        pk("scholarship_id", "SCH-YYYY-000000", "Award identifier"),
        Col("eligibility_id", "id", "Assessment the award came from", fk="eligibility.eligibility_id",
            unique=True),
        Col("student_id", "id", "Student", fk="students.student_id"),
        Col("invoice_id", "id", "Invoice credited", fk="invoices.invoice_id"),
        Col("scheme_id", "id", "Scheme", fk="scholarship_schemes.scheme_id"),
        Col("award_type", "text", "Scholarship or waiver", allowed=("SCHOLARSHIP", "WAIVER")),
        Col("eligible_fee_base", "money", "Eligible fees on the invoice when awarded", unit="USD"),
        Col("award_amount", "money", "Amount credited", unit="USD", rule="never above eligible_fee_base"),
        Col("awarded_on", "date", "Award date"),
        Col("status", "text", "Award state", allowed=("AWARDED", "CANCELLED")),
    )),
    Table("payments", "Payment", "payment_id", "Money received from or for a student.", (
        pk("payment_id", "PAY-YYYY-000000", "Payment identifier"),
        Col("student_id", "id", "Student", fk="students.student_id"),
        Col("invoice_id", "id", "Invoice quoted as reference", fk="invoices.invoice_id"),
        Col("received_on", "date", "Date received", rule="on or after invoice issue_date"),
        Col("amount", "money", "Amount received", unit="USD", rule="greater than zero"),
        Col("method", "text", "Payment method", allowed=catalog.PAYMENT_METHODS),
        Col("amount_allocated", "money", "Allocated to invoice lines", unit="USD", rule="derived"),
        Col("amount_unapplied", "money", "Held as student credit", unit="USD", rule="derived"),
        Col("amount_refunded", "money", "Refunded from this payment", unit="USD", rule="derived"),
    )),
    Table("payment_allocations", "PaymentAllocation", "allocation_id",
          "Bridge between payments and invoice lines (N to M).", (
        pk("allocation_id", "ALLOC-<payment>-00", "Allocation identifier"),
        Col("payment_id", "id", "Payment", fk="payments.payment_id"),
        Col("invoice_id", "id", "Invoice", fk="invoices.invoice_id"),
        Col("line_id", "id", "Line paid", fk="invoice_lines.line_id"),
        Col("amount", "money", "Amount allocated", unit="USD", rule="greater than zero"),
        Col("allocated_on", "date", "Allocation date"),
    )),
    Table("refunds", "Refund", "refund_id", "Money returned to a student.", (
        pk("refund_id", "REF-YYYY-000000", "Refund identifier"),
        Col("student_id", "id", "Student", fk="students.student_id"),
        Col("payment_id", "id", "Payment refunded from", fk="payments.payment_id"),
        Col("invoice_id", "id", "Invoice for withdrawal or cancellation refunds", required=False,
            fk="invoices.invoice_id"),
        Col("reason", "text", "Reason", allowed=catalog.REFUND_REASONS),
        Col("amount", "money", "Amount refunded", unit="USD", rule="not above payment net paid"),
        Col("refunded_on", "date", "Refund date", rule="on or after payment date"),
    )),
    Table("ledger_entries", "LedgerEntry", "entry_id", "Append only student ledger built from source rows.", (
        pk("entry_id", "LED-<student>-000000", "Entry identifier"),
        Col("student_id", "id", "Student", fk="students.student_id"),
        Col("posted_on", "date", "Posting date"),
        Col("entry_type", "text", "Entry type",
            allowed=("CHARGE", "LATE_FEE", "SCHOLARSHIP", "WAIVER", "REVERSAL", "PAYMENT", "REFUND")),
        Col("source_id", "id", "Line, payment or refund behind the entry"),
        Col("invoice_id", "id", "Invoice", required=False, fk="invoices.invoice_id"),
        Col("amount", "money", "Signed amount, positive raises what the student owes", unit="USD"),
        Col("running_balance", "money", "Balance after this entry", unit="USD", rule="derived"),
    )),
    Table("student_accounts", "StudentAccount", "student_id", "Stored balance snapshot per student.", (
        Col("student_id", "id", "Student", unique=True, fk="students.student_id"),
        Col("total_billed", "money", "Charges and late fees", unit="USD"),
        Col("total_credits", "money", "Scholarships, waivers and reversals", unit="USD"),
        Col("total_paid", "money", "Payments received", unit="USD"),
        Col("total_refunded", "money", "Refunds paid out", unit="USD"),
        Col("unapplied_credit", "money", "Payment money not allocated and not refunded", unit="USD"),
        Col("balance", "money", "Stored balance, positive means the student owes", unit="USD",
            rule="must equal the ledger sum"),
        Col("as_of", "date", "Snapshot date"),
    )),
    Table("events", "Event", "event_id", "State change history. Rows are only appended.", (
        pk("event_id", "EVT-000000000", "Event identifier"),
        Col("entity_type", "text", "Entity",
            allowed=("ENROLLMENT", "INVOICE", "SCHOLARSHIP", "PAYMENT", "REFUND")),
        Col("entity_id", "id", "Entity identifier"),
        Col("event_type", "text", "What happened"),
        Col("from_state", "text", "State before", required=False),
        Col("to_state", "text", "State after", required=False),
        Col("occurred_on", "date", "Date"),
        Col("actor_role", "text", "Who triggered it",
            allowed=("learner", "instructor", "academic_admin", "support_staff", "platform_admin", "system")),
        Col("detail", "text", "Extra context", required=False),
    )),
    Table("decisions", "Decision", "decision_id", "Every rule outcome with the rule that produced it.", (
        pk("decision_id", "DEC-000000000", "Decision identifier"),
        Col("rule_id", "text", "Rule applied"),
        Col("entity_type", "text", "Entity decided on"),
        Col("entity_id", "id", "Entity identifier"),
        Col("outcome", "text", "Outcome"),
        Col("amount", "money", "Amount involved", required=False, unit="USD"),
        Col("decided_on", "date", "Date"),
        Col("explanation", "text", "Why"),
    )),
)

GROUND_TRUTH = Table("ground_truth", "GroundTruth", "issue_id", "Labels for injected anomalies. Not an input.", (
    pk("issue_id", "GT-000000", "Label identifier"),
    Col("issue_type", "text", "Anomaly type", allowed=catalog.ISSUE_TYPES),
    Col("entity_type", "text", "Entity carrying the anomaly"),
    Col("entity_id", "id", "Entity identifier"),
    Col("related_ids", "text", "Related records, pipe separated", required=False),
    Col("expected_decision", "text", "What a correct system should do"),
    Col("expected_value", "money", "Correct amount where one applies", required=False, unit="USD"),
    Col("description", "text", "Plain description"),
))

TABLES_BY_NAME = {t.name: t for t in (*TABLES, GROUND_TRUTH)}
