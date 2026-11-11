DROP TABLE IF EXISTS ground_truth CASCADE;
DROP TABLE IF EXISTS decisions CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS student_accounts CASCADE;
DROP TABLE IF EXISTS ledger_entries CASCADE;
DROP TABLE IF EXISTS refunds CASCADE;
DROP TABLE IF EXISTS payment_allocations CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS invoice_lines CASCADE;
DROP TABLE IF EXISTS scholarships CASCADE;
DROP TABLE IF EXISTS eligibility CASCADE;
DROP TABLE IF EXISTS scholarship_schemes CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS enrollments CASCADE;
DROP TABLE IF EXISTS fee_schedules CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS terms CASCADE;
DROP TABLE IF EXISTS programs CASCADE;

CREATE TABLE programs (
    program_id TEXT NOT NULL,
    name TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('UG', 'PG', 'DIP', 'CERT')),
    department TEXT NOT NULL CHECK (department IN ('STEM', 'BUSINESS', 'ARTS', 'HEALTH')),
    has_lab BOOLEAN NOT NULL,
    full_time_credits INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'RETIRED')),
    PRIMARY KEY (program_id),
    UNIQUE (name)
);

CREATE TABLE terms (
    term_id TEXT NOT NULL,
    name TEXT NOT NULL,
    season TEXT NOT NULL CHECK (season IN ('FALL', 'SPRING', 'SUMMER')),
    year INTEGER NOT NULL,
    invoice_date DATE NOT NULL,
    start_date DATE NOT NULL,
    due_date DATE NOT NULL,
    end_date DATE NOT NULL,
    PRIMARY KEY (term_id)
);

CREATE TABLE students (
    student_id TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL,
    program_id TEXT NOT NULL,
    admit_term_id TEXT NOT NULL,
    residency TEXT NOT NULL CHECK (residency IN ('DOMESTIC', 'INTL')),
    income_band TEXT NOT NULL CHECK (income_band IN ('LOW', 'MEDIUM', 'HIGH')),
    gpa NUMERIC(5,2) NOT NULL,
    has_external_cover BOOLEAN NOT NULL,
    staff_dependent BOOLEAN NOT NULL,
    created_on DATE NOT NULL,
    PRIMARY KEY (student_id),
    UNIQUE (email),
    FOREIGN KEY (program_id) REFERENCES programs (program_id),
    FOREIGN KEY (admit_term_id) REFERENCES terms (term_id)
);

CREATE TABLE fee_schedules (
    fee_schedule_id TEXT NOT NULL,
    program_id TEXT NOT NULL,
    term_id TEXT NOT NULL,
    fee_code TEXT NOT NULL CHECK (fee_code IN ('TECH', 'LIBRARY', 'ACTIVITY', 'LAB', 'HEALTH_INSURANCE', 'INTL_SURCHARGE', 'TUITION')),
    basis TEXT NOT NULL CHECK (basis IN ('PER_CREDIT', 'FLAT')),
    rate NUMERIC(14,2) NOT NULL,
    applies_when TEXT NOT NULL CHECK (applies_when IN ('ALL', 'INTL', 'FULL_TIME', 'LAB_PROGRAM', 'FULL_TIME_NO_COVER')),
    version INTEGER NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    PRIMARY KEY (fee_schedule_id),
    FOREIGN KEY (program_id) REFERENCES programs (program_id),
    FOREIGN KEY (term_id) REFERENCES terms (term_id)
);

CREATE TABLE enrollments (
    enrollment_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    program_id TEXT NOT NULL,
    term_id TEXT NOT NULL,
    credits INTEGER NOT NULL,
    load TEXT NOT NULL CHECK (load IN ('FULL_TIME', 'PART_TIME')),
    registered_on DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('REGISTERED', 'ACTIVE', 'COMPLETED', 'WITHDRAWN', 'CANCELLED')),
    status_on DATE NOT NULL,
    exit_date DATE,
    refund_percent INTEGER,
    PRIMARY KEY (enrollment_id),
    FOREIGN KEY (student_id) REFERENCES students (student_id),
    FOREIGN KEY (program_id) REFERENCES programs (program_id),
    FOREIGN KEY (term_id) REFERENCES terms (term_id)
);

CREATE TABLE invoices (
    invoice_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    enrollment_id TEXT NOT NULL,
    term_id TEXT NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    total_charges NUMERIC(14,2) NOT NULL,
    total_credits NUMERIC(14,2) NOT NULL,
    total_reversals NUMERIC(14,2) NOT NULL,
    net_amount NUMERIC(14,2) NOT NULL,
    amount_allocated NUMERIC(14,2) NOT NULL,
    amount_refunded NUMERIC(14,2) NOT NULL,
    balance NUMERIC(14,2) NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('UNPAID', 'PARTIALLY_PAID', 'PAID', 'OVERDUE', 'IN_CREDIT', 'CANCELLED')),
    PRIMARY KEY (invoice_id),
    FOREIGN KEY (student_id) REFERENCES students (student_id),
    FOREIGN KEY (enrollment_id) REFERENCES enrollments (enrollment_id),
    FOREIGN KEY (term_id) REFERENCES terms (term_id)
);

CREATE TABLE scholarship_schemes (
    scheme_id TEXT NOT NULL,
    name TEXT NOT NULL,
    award_type TEXT NOT NULL CHECK (award_type IN ('SCHOLARSHIP', 'WAIVER')),
    basis TEXT NOT NULL CHECK (basis IN ('PERCENT', 'FIXED')),
    value INTEGER NOT NULL,
    cap NUMERIC(14,2),
    fee_codes TEXT NOT NULL,
    criteria TEXT NOT NULL,
    PRIMARY KEY (scheme_id)
);

CREATE TABLE eligibility (
    eligibility_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    enrollment_id TEXT NOT NULL,
    scheme_id TEXT NOT NULL,
    assessed_on DATE NOT NULL,
    gpa NUMERIC(5,2) NOT NULL,
    income_band TEXT NOT NULL CHECK (income_band IN ('LOW', 'MEDIUM', 'HIGH')),
    credits INTEGER NOT NULL,
    is_eligible BOOLEAN NOT NULL,
    passed_criteria TEXT,
    failed_criteria TEXT,
    PRIMARY KEY (eligibility_id),
    FOREIGN KEY (student_id) REFERENCES students (student_id),
    FOREIGN KEY (enrollment_id) REFERENCES enrollments (enrollment_id),
    FOREIGN KEY (scheme_id) REFERENCES scholarship_schemes (scheme_id)
);

CREATE TABLE scholarships (
    scholarship_id TEXT NOT NULL,
    eligibility_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    invoice_id TEXT NOT NULL,
    scheme_id TEXT NOT NULL,
    award_type TEXT NOT NULL CHECK (award_type IN ('SCHOLARSHIP', 'WAIVER')),
    eligible_fee_base NUMERIC(14,2) NOT NULL,
    award_amount NUMERIC(14,2) NOT NULL,
    awarded_on DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('AWARDED', 'CANCELLED')),
    PRIMARY KEY (scholarship_id),
    UNIQUE (eligibility_id),
    FOREIGN KEY (eligibility_id) REFERENCES eligibility (eligibility_id),
    FOREIGN KEY (student_id) REFERENCES students (student_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices (invoice_id),
    FOREIGN KEY (scheme_id) REFERENCES scholarship_schemes (scheme_id)
);

CREATE TABLE invoice_lines (
    line_id TEXT NOT NULL,
    invoice_id TEXT NOT NULL,
    line_no INTEGER NOT NULL,
    line_type TEXT NOT NULL CHECK (line_type IN ('CHARGE', 'SCHOLARSHIP', 'WAIVER', 'LATE_FEE', 'REVERSAL')),
    fee_code TEXT NOT NULL CHECK (fee_code IN ('TECH', 'LIBRARY', 'ACTIVITY', 'LAB', 'HEALTH_INSURANCE', 'INTL_SURCHARGE', 'TUITION', 'LATE_FEE')),
    fee_schedule_id TEXT,
    quantity INTEGER,
    unit_amount NUMERIC(14,2),
    amount NUMERIC(14,2) NOT NULL,
    applies_to_line_id TEXT,
    scholarship_id TEXT,
    posted_on DATE NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY (line_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices (invoice_id),
    FOREIGN KEY (fee_schedule_id) REFERENCES fee_schedules (fee_schedule_id),
    FOREIGN KEY (applies_to_line_id) REFERENCES invoice_lines (line_id),
    FOREIGN KEY (scholarship_id) REFERENCES scholarships (scholarship_id)
);

CREATE TABLE payments (
    payment_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    invoice_id TEXT NOT NULL,
    received_on DATE NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    method TEXT NOT NULL CHECK (method IN ('CARD', 'BANK_TRANSFER', 'SPONSOR', 'CHEQUE')),
    amount_allocated NUMERIC(14,2) NOT NULL,
    amount_unapplied NUMERIC(14,2) NOT NULL,
    amount_refunded NUMERIC(14,2) NOT NULL,
    PRIMARY KEY (payment_id),
    FOREIGN KEY (student_id) REFERENCES students (student_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices (invoice_id)
);

CREATE TABLE payment_allocations (
    allocation_id TEXT NOT NULL,
    payment_id TEXT NOT NULL,
    invoice_id TEXT NOT NULL,
    line_id TEXT NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    allocated_on DATE NOT NULL,
    PRIMARY KEY (allocation_id),
    FOREIGN KEY (payment_id) REFERENCES payments (payment_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices (invoice_id),
    FOREIGN KEY (line_id) REFERENCES invoice_lines (line_id)
);

CREATE TABLE refunds (
    refund_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    payment_id TEXT NOT NULL,
    invoice_id TEXT,
    reason TEXT NOT NULL CHECK (reason IN ('OVERPAYMENT', 'WITHDRAWAL', 'CANCELLATION')),
    amount NUMERIC(14,2) NOT NULL,
    refunded_on DATE NOT NULL,
    PRIMARY KEY (refund_id),
    FOREIGN KEY (student_id) REFERENCES students (student_id),
    FOREIGN KEY (payment_id) REFERENCES payments (payment_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices (invoice_id)
);

CREATE TABLE ledger_entries (
    entry_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    posted_on DATE NOT NULL,
    entry_type TEXT NOT NULL CHECK (entry_type IN ('CHARGE', 'LATE_FEE', 'SCHOLARSHIP', 'WAIVER', 'REVERSAL', 'PAYMENT', 'REFUND')),
    source_id TEXT NOT NULL,
    invoice_id TEXT,
    amount NUMERIC(14,2) NOT NULL,
    running_balance NUMERIC(14,2) NOT NULL,
    PRIMARY KEY (entry_id),
    FOREIGN KEY (student_id) REFERENCES students (student_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices (invoice_id)
);

CREATE TABLE student_accounts (
    student_id TEXT NOT NULL,
    total_billed NUMERIC(14,2) NOT NULL,
    total_credits NUMERIC(14,2) NOT NULL,
    total_paid NUMERIC(14,2) NOT NULL,
    total_refunded NUMERIC(14,2) NOT NULL,
    unapplied_credit NUMERIC(14,2) NOT NULL,
    balance NUMERIC(14,2) NOT NULL,
    as_of DATE NOT NULL,
    PRIMARY KEY (student_id),
    FOREIGN KEY (student_id) REFERENCES students (student_id)
);

CREATE TABLE events (
    event_id TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('ENROLLMENT', 'INVOICE', 'SCHOLARSHIP', 'PAYMENT', 'REFUND')),
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT,
    occurred_on DATE NOT NULL,
    actor_role TEXT NOT NULL CHECK (actor_role IN ('learner', 'instructor', 'academic_admin', 'support_staff', 'platform_admin', 'system')),
    detail TEXT,
    PRIMARY KEY (event_id)
);

CREATE TABLE decisions (
    decision_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    amount NUMERIC(14,2),
    decided_on DATE NOT NULL,
    explanation TEXT NOT NULL,
    PRIMARY KEY (decision_id)
);

CREATE TABLE ground_truth (
    issue_id TEXT NOT NULL,
    issue_type TEXT NOT NULL CHECK (issue_type IN ('ALLOCATION_EXCEEDS_PAYMENT', 'SCHOLARSHIP_EXCEEDS_ELIGIBLE', 'DUPLICATE_INVOICE', 'REFUND_EXCEEDS_NET_PAID', 'BALANCE_LEDGER_MISMATCH')),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    related_ids TEXT,
    expected_decision TEXT NOT NULL,
    expected_value NUMERIC(14,2),
    description TEXT NOT NULL,
    PRIMARY KEY (issue_id)
);
