CREATE TABLE IF NOT EXISTS id_counters (
    counter_key TEXT PRIMARY KEY,
    value BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_idempotency (
    operation TEXT NOT NULL,
    request_key TEXT NOT NULL,
    request_body JSONB NOT NULL,
    response_body JSONB NOT NULL,
    PRIMARY KEY (operation, request_key)
);

CREATE TABLE IF NOT EXISTS reconciliation_runs (
    run_id TEXT PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    actor_role TEXT NOT NULL,
    exceptions_found INTEGER NOT NULL,
    evaluation JSONB,
    boundary_cases JSONB NOT NULL,
    kpis JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS exceptions (
    exception_id TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES reconciliation_runs (run_id),
    issue_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    related_ids TEXT,
    expected_decision TEXT NOT NULL,
    detected_value NUMERIC(14,2) NOT NULL,
    explanation TEXT NOT NULL,
    PRIMARY KEY (run_id, exception_id)
);

CREATE INDEX IF NOT EXISTS invoices_student_idx ON invoices (student_id);
CREATE INDEX IF NOT EXISTS invoices_enrollment_idx ON invoices (enrollment_id);
CREATE INDEX IF NOT EXISTS lines_invoice_idx ON invoice_lines (invoice_id);
CREATE INDEX IF NOT EXISTS payments_student_idx ON payments (student_id);
CREATE INDEX IF NOT EXISTS payments_invoice_idx ON payments (invoice_id);
CREATE INDEX IF NOT EXISTS allocations_payment_idx ON payment_allocations (payment_id);
CREATE INDEX IF NOT EXISTS allocations_invoice_idx ON payment_allocations (invoice_id);
CREATE INDEX IF NOT EXISTS refunds_payment_idx ON refunds (payment_id);
CREATE INDEX IF NOT EXISTS ledger_student_idx ON ledger_entries (student_id, entry_id);
CREATE INDEX IF NOT EXISTS events_entity_idx ON events (entity_id);
CREATE INDEX IF NOT EXISTS decisions_entity_idx ON decisions (entity_id);
CREATE INDEX IF NOT EXISTS enrollments_student_idx ON enrollments (student_id);
CREATE INDEX IF NOT EXISTS eligibility_enrollment_idx ON eligibility (enrollment_id);
CREATE INDEX IF NOT EXISTS students_name_idx ON students (last_name, first_name);
