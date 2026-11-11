# Data dictionary

Generated from ledger/schema.py by python -m ledger dictionary.
Money is stored as rupees with two decimals and handled as integer paise in code.

## Relationships

- Program 1 to N Student, every student is admitted to exactly one program
- Program 1 to N FeeSchedule, Term 1 to N FeeSchedule
- Student 1 to N Enrollment, at most one enrollment per student per term
- Enrollment 1 to 1 Invoice in clean data, a second invoice for the same enrollment is the DUPLICATE_INVOICE anomaly
- Invoice 1 to N InvoiceLine
- InvoiceLine 0..1 to N InvoiceLine through applies_to_line_id, credits and reversals point at the charge they reduce
- FeeSchedule 1 to N InvoiceLine, every CHARGE line records the schedule row it was priced from
- Student N to M ScholarshipScheme through Eligibility (bridge)
- Eligibility 1 to 0..1 Scholarship, only eligible assessments become awards
- Scholarship 1 to N InvoiceLine, one credit line per fee code covered
- Student 1 to N Payment, Invoice 1 to N Payment through the quoted reference
- Payment N to M InvoiceLine through PaymentAllocation (bridge)
- Payment 1 to N Refund, Invoice 0..1 to N Refund
- Student 1 to N LedgerEntry, Student 1 to 1 StudentAccount
- Every entity 1 to N Event and 1 to N Decision through entity_type and entity_id

## Program (programs)

Academic programs offered by the institution.
Primary key is program_id.

- program_id: Program identifier. id; required; unique; pattern PRG-000
- name: Program name. text; required; unique
- level: Award level. text; required; one of UG, PG, DIP, CERT
- department: Owning department. text; required; one of STEM, BUSINESS, ARTS, HEALTH
- has_lab: Whether the program charges a lab fee. bool; required
- full_time_credits: Credits per term that count as full time. int; required; unit credits; 12 for UG and DIP, 9 for PG and CERT
- status: Program lifecycle state. text; required; one of ACTIVE, RETIRED

## Term (terms)

Academic terms and their billing calendar.
Primary key is term_id.

- term_id: Term identifier. id; required; unique; pattern TERM-YYYY-SEASON
- name: Display name. text; required
- season: Season. text; required; one of FALL, SPRING, SUMMER
- year: Calendar year of the term. int; required
- invoice_date: Date invoices are issued. date; required; before start_date
- start_date: First day of classes. date; required
- due_date: Payment due date. date; required; after invoice_date
- end_date: Last day of term. date; required; after start_date

## Student (students)

Synthetic learners. No real people.
Primary key is student_id.

- student_id: Student identifier. id; required; unique; pattern STU-000000
- first_name: Synthetic first name. text; required
- last_name: Synthetic last name. text; required
- email: Synthetic email on example.edu. text; required; unique
- program_id: Program the student is admitted to. id; required; references programs.program_id
- admit_term_id: First term of study. id; required; references terms.term_id
- residency: Fee residency. text; required; one of DOMESTIC, INTL
- income_band: Household income band for need based aid. text; required; one of LOW, MEDIUM, HIGH
- gpa: Cumulative GPA used for merit rules. float; required; unit 0.00 to 4.00; 1.80 to 4.00
- has_external_cover: Has outside health insurance, so health fee does not apply. bool; required
- staff_dependent: Dependent of a staff member. bool; required
- created_on: Record creation date. date; required

## FeeSchedule (fee_schedules)

Fee rates by program, term and fee code with effective dating.
Primary key is fee_schedule_id.

- fee_schedule_id: Fee schedule row identifier. id; required; unique; pattern FS-<program>-<term>-<fee>-V<n>
- program_id: Program. id; required; references programs.program_id
- term_id: Term. id; required; references terms.term_id
- fee_code: Fee code. text; required; one of TECH, LIBRARY, ACTIVITY, LAB, HEALTH_INSURANCE, INTL_SURCHARGE, TUITION
- basis: Charging basis. text; required; one of PER_CREDIT, FLAT
- rate: Rate per credit or flat amount. money; required; unit INR
- applies_when: Condition for the fee to be billed. text; required; one of ALL, INTL, FULL_TIME, LAB_PROGRAM, FULL_TIME_NO_COVER
- version: Schedule version for this program, term and fee. int; required
- effective_from: First day this rate is in effect. date; required
- effective_to: Last day this rate is in effect. date; optional; null means open ended, versions never overlap

## Enrollment (enrollments)

A student taking a program in one term.
Primary key is enrollment_id.

- enrollment_id: Enrollment identifier. id; required; unique; pattern ENR-<student>-<term>
- student_id: Student. id; required; references students.student_id
- program_id: Program. id; required; references programs.program_id; equals the student program
- term_id: Term. id; required; references terms.term_id
- credits: Credits registered. int; required; unit credits; 1 to 18
- load: Load derived from credits. text; required; one of FULL_TIME, PART_TIME
- registered_on: Registration date. date; required; on or before term invoice date
- status: Current lifecycle state. text; required; one of REGISTERED, ACTIVE, COMPLETED, WITHDRAWN, CANCELLED
- status_on: Date of the latest state change. date; required
- exit_date: Withdrawal or cancellation date. date; optional
- refund_percent: Tuition refund percent applied on exit. int; optional; unit %

## Invoice (invoices)

One invoice per enrollment, built from eligible fee lines.
Primary key is invoice_id.

- invoice_id: Invoice identifier. id; required; unique; pattern INV-STU-000000-YYYY-000000
- student_id: Student. id; required; references students.student_id
- enrollment_id: Enrollment billed. id; required; references enrollments.enrollment_id
- term_id: Term. id; required; references terms.term_id
- issue_date: Issue date. date; required
- due_date: Due date. date; required; after issue_date
- total_charges: Sum of CHARGE and LATE_FEE lines. money; required; unit INR; derived
- total_credits: Sum of scholarship and waiver credits. money; required; unit INR; derived
- total_reversals: Sum of withdrawal and cancellation reversals. money; required; unit INR; derived
- net_amount: Charges minus credits minus reversals. money; required; unit INR; derived
- amount_allocated: Payments allocated to the lines. money; required; unit INR; derived
- amount_refunded: Refunds paid out against this invoice. money; required; unit INR; derived
- balance: net_amount minus allocated plus refunded. money; required; unit INR; derived
- status: Status as of the dataset date. text; required; one of UNPAID, PARTIALLY_PAID, PAID, OVERDUE, IN_CREDIT, CANCELLED; derived

## InvoiceLine (invoice_lines)

Charges and credits on an invoice. Never edited.
Primary key is line_id.

- line_id: Line identifier. id; required; unique; pattern <invoice>-L00
- invoice_id: Invoice. id; required; references invoices.invoice_id
- line_no: Line number within invoice. int; required
- line_type: Line type. text; required; one of CHARGE, SCHOLARSHIP, WAIVER, LATE_FEE, REVERSAL
- fee_code: Fee code. text; required; one of TECH, LIBRARY, ACTIVITY, LAB, HEALTH_INSURANCE, INTL_SURCHARGE, TUITION, LATE_FEE
- fee_schedule_id: Schedule row priced from. id; optional; references fee_schedules.fee_schedule_id; required for CHARGE lines
- quantity: Credits or 1. int; optional
- unit_amount: Rate used. money; optional; unit INR
- amount: Signed amount, charges positive, credits negative. money; required; unit INR
- applies_to_line_id: Charge line a credit or reversal reduces. id; optional; references invoice_lines.line_id
- scholarship_id: Award behind a credit line. id; optional; references scholarships.scholarship_id
- posted_on: Date the line was posted. date; required
- description: Human readable reason. text; required

## ScholarshipScheme (scholarship_schemes)

Reference table of scholarship and waiver rules.
Primary key is scheme_id.

- scheme_id: Scheme identifier. id; required; unique; pattern SCHEME-<NAME>
- name: Scheme name. text; required
- award_type: Scholarship or waiver. text; required; one of SCHOLARSHIP, WAIVER
- basis: Percent of eligible fees or fixed amount. text; required; one of PERCENT, FIXED
- value: Percent for PERCENT, paise for FIXED. int; required
- cap: Maximum award. money; optional; unit INR
- fee_codes: Eligible fee codes, pipe separated. text; required
- criteria: Readable eligibility criteria. text; required

## Eligibility (eligibility)

Bridge between students and schemes. One assessment per application.
Primary key is eligibility_id.

- eligibility_id: Assessment identifier. id; required; unique; pattern ELG-YYYY-000000
- student_id: Student. id; required; references students.student_id
- enrollment_id: Enrollment assessed for. id; required; references enrollments.enrollment_id
- scheme_id: Scheme applied for. id; required; references scholarship_schemes.scheme_id
- assessed_on: Assessment date. date; required
- gpa: GPA at assessment. float; required
- income_band: Income band at assessment. text; required; one of LOW, MEDIUM, HIGH
- credits: Credits at assessment. int; required
- is_eligible: Rule outcome. bool; required
- passed_criteria: Criteria met, pipe separated. text; optional
- failed_criteria: Criteria failed, pipe separated. text; optional

## Scholarship (scholarships)

Awards made from eligible assessments.
Primary key is scholarship_id.

- scholarship_id: Award identifier. id; required; unique; pattern SCH-YYYY-000000
- eligibility_id: Assessment the award came from. id; required; unique; references eligibility.eligibility_id
- student_id: Student. id; required; references students.student_id
- invoice_id: Invoice credited. id; required; references invoices.invoice_id
- scheme_id: Scheme. id; required; references scholarship_schemes.scheme_id
- award_type: Scholarship or waiver. text; required; one of SCHOLARSHIP, WAIVER
- eligible_fee_base: Eligible fees on the invoice when awarded. money; required; unit INR
- award_amount: Amount credited. money; required; unit INR; never above eligible_fee_base
- awarded_on: Award date. date; required
- status: Award state. text; required; one of AWARDED, CANCELLED

## Payment (payments)

Money received from or for a student.
Primary key is payment_id.

- payment_id: Payment identifier. id; required; unique; pattern PAY-YYYY-000000
- student_id: Student. id; required; references students.student_id
- invoice_id: Invoice quoted as reference. id; required; references invoices.invoice_id
- received_on: Date received. date; required; on or after invoice issue_date
- amount: Amount received. money; required; unit INR; greater than zero
- method: Payment method. text; required; one of CARD, BANK_TRANSFER, SPONSOR, CHEQUE
- amount_allocated: Allocated to invoice lines. money; required; unit INR; derived
- amount_unapplied: Held as student credit. money; required; unit INR; derived
- amount_refunded: Refunded from this payment. money; required; unit INR; derived

## PaymentAllocation (payment_allocations)

Bridge between payments and invoice lines (N to M).
Primary key is allocation_id.

- allocation_id: Allocation identifier. id; required; unique; pattern ALLOC-<payment>-00
- payment_id: Payment. id; required; references payments.payment_id
- invoice_id: Invoice. id; required; references invoices.invoice_id
- line_id: Line paid. id; required; references invoice_lines.line_id
- amount: Amount allocated. money; required; unit INR; greater than zero
- allocated_on: Allocation date. date; required

## Refund (refunds)

Money returned to a student.
Primary key is refund_id.

- refund_id: Refund identifier. id; required; unique; pattern REF-YYYY-000000
- student_id: Student. id; required; references students.student_id
- payment_id: Payment refunded from. id; required; references payments.payment_id
- invoice_id: Invoice for withdrawal or cancellation refunds. id; optional; references invoices.invoice_id
- reason: Reason. text; required; one of OVERPAYMENT, WITHDRAWAL, CANCELLATION
- amount: Amount refunded. money; required; unit INR; not above payment net paid
- refunded_on: Refund date. date; required; on or after payment date

## LedgerEntry (ledger_entries)

Append only student ledger built from source rows.
Primary key is entry_id.

- entry_id: Entry identifier. id; required; unique; pattern LED-<student>-000000
- student_id: Student. id; required; references students.student_id
- posted_on: Posting date. date; required
- entry_type: Entry type. text; required; one of CHARGE, LATE_FEE, SCHOLARSHIP, WAIVER, REVERSAL, PAYMENT, REFUND
- source_id: Line, payment or refund behind the entry. id; required
- invoice_id: Invoice. id; optional; references invoices.invoice_id
- amount: Signed amount, positive raises what the student owes. money; required; unit INR
- running_balance: Balance after this entry. money; required; unit INR; derived

## StudentAccount (student_accounts)

Stored balance snapshot per student.
Primary key is student_id.

- student_id: Student. id; required; unique; references students.student_id
- total_billed: Charges and late fees. money; required; unit INR
- total_credits: Scholarships, waivers and reversals. money; required; unit INR
- total_paid: Payments received. money; required; unit INR
- total_refunded: Refunds paid out. money; required; unit INR
- unapplied_credit: Payment money not allocated and not refunded. money; required; unit INR
- balance: Stored balance, positive means the student owes. money; required; unit INR; must equal the ledger sum
- as_of: Snapshot date. date; required

## Event (events)

State change history. Rows are only appended.
Primary key is event_id.

- event_id: Event identifier. id; required; unique; pattern EVT-000000000
- entity_type: Entity. text; required; one of ENROLLMENT, INVOICE, SCHOLARSHIP, PAYMENT, REFUND
- entity_id: Entity identifier. id; required
- event_type: What happened. text; required
- from_state: State before. text; optional
- to_state: State after. text; optional
- occurred_on: Date. date; required
- actor_role: Who triggered it. text; required; one of learner, instructor, academic_admin, support_staff, platform_admin, system
- detail: Extra context. text; optional

## Decision (decisions)

Every rule outcome with the rule that produced it.
Primary key is decision_id.

- decision_id: Decision identifier. id; required; unique; pattern DEC-000000000
- rule_id: Rule applied. text; required
- entity_type: Entity decided on. text; required
- entity_id: Entity identifier. id; required
- outcome: Outcome. text; required
- amount: Amount involved. money; optional; unit INR
- decided_on: Date. date; required
- explanation: Why. text; required

## GroundTruth (ground_truth)

Labels for injected anomalies. Not an input.
Primary key is issue_id.

- issue_id: Label identifier. id; required; unique; pattern GT-000000
- issue_type: Anomaly type. text; required; one of ALLOCATION_EXCEEDS_PAYMENT, SCHOLARSHIP_EXCEEDS_ELIGIBLE, DUPLICATE_INVOICE, REFUND_EXCEEDS_NET_PAID, BALANCE_LEDGER_MISMATCH
- entity_type: Entity carrying the anomaly. text; required
- entity_id: Entity identifier. id; required
- related_ids: Related records, pipe separated. text; optional
- expected_decision: What a correct system should do. text; required
- expected_value: Correct amount where one applies. money; optional; unit INR
- description: Plain description. text; required
