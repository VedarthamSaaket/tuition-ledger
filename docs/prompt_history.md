# Prompt history

This is a record of the user prompts available in the local Claude session and the later Codex continuation. Tool outputs and assistant responses are excluded. The original Codex handoff included a long pasted transcript; it is represented below by its request and source limitation, not claimed as a verbatim export.

## Claude session

### User message

```text


<pasted_content id="516b">
MAKE IT RUN

Submit working, executable code. Include clear steps so another person can
install dependencies, configure the project, run it, and verify key behavior.

EXECUTABLE

02 SHOW YOUR WORK

Use a public GitHub repository. Make the evolution of your work understandable
through the code, meaningful commits, and supporting context.

PUBLIC REPOSITORY

03 USE LLMs TRANSPARENTLY

LLM tools are allowed. Submit your prompt history and explain where AI accelerated
your work, where you relied heavily on it, and what you personally reviewed,
changed, or validated.

PROMPT HISTORY REQUIRED

04 MAKE YOUR REASONING VISIBLE

Help reviewers understand the problem, assumptions, key decisions, trade-offs,
testing approach, limitations, and how you know the solution works.

EXPLAIN THE WHY

BE READY TO WALK US THROUGH YOUR SOLUTION.
We value sound judgment, working software, honest AI disclosure, and clear communication.
</pasted_content id="516b">

 

<pasted_content id="516b">
1. When does my 72-hour window start?
When YottaFlex AI sends you the project. Your deadline is exactly
72 hours later, using the recorded send timestamp and its time
zone.

7. Must I write all code myself?
The project must be your individual work. AI and public learning
resources are allowed; implementation help from other people is
not. Understand the core logic, key design choices,
dependencies, and limitations.

2. Can I submit early?
Yes. You may submit as soon as you are ready. Keep your
public repository available and editable until the 72-hour
deadline; the latest version at the deadline is evaluated.

8. Can I choose my own technology stack?
Yes. Choose suitable languages, frameworks, and storage. Use
only free or locally runnable services, and avoid unusually large
or slow dependencies where possible.

3. How do I submit my repository link?
Create a new, dedicated public GitHub repository. Send the link
from the same email address you used during recruitment and
follow the submission instructions provided.

9. Must I provide a live demo or automated tests?
No hosted demo or automated test suite is mandatory. Provide
clear setup/run instructions and demonstrate how you verified
the core functionality. Document environment needs and
limitations.

4. What belongs in my repository?
Include your code, prompt history, and relevant supporting
artifacts in a clearly identifiable directory. There is no fixed list of
documents or prescribed format.

10. Can I reuse existing code?
Standard dependencies and small illustrative snippets are
acceptable. Do not import a complete solution or existing code
that performs the core project work. Follow licenses and provide
attribution where required.

5. Which AI tools may I use?
Any LLM or AI coding tool is allowed, including cloud-based and
locally hosted tools. AI use is unrestricted; your judgment,
understanding, ownership, and validation matter.

11. What if requirements are unclear or work is
incomplete?
Make reasonable assumptions and explain them. Partial
solutions are acceptable if you state what works, what remains
incomplete, known limitations, and next steps. Explain any
requirement deviations.

6. What prompt history is required?
Include all prompts submitted to every AI tool you used. AI
responses are optional. If a tool cannot export prompts, keep a
reasonable record and disclose the limitation.

12. What must I keep out of a public repository?
Never include secrets, credentials, personal or sensitive
information, or proprietary code you are not authorized to
publish. Use safe sample data and local configuration; explain
setup in the README.
</pasted_content id="516b">

 make a document of it saved in /Documents section of my laptop, here's the problem statement. but also i want you to (in VedarthamSaaket account btw) build skeletal application -> commit -> push ; add features -> commit -> push ; and repeat. mimic human development and ci/cd pipeline methods for development, which makes superviser look at the project and think this is neat the process of sdlc using ci/cd. 

<pasted_content id="516b">
Business Context / Problem
Calculate tuition and fees, apply scholarship eligibility and payments, and reconcile student balances.

Objective and Scope
Build a working solution for this end-to-end workflow: Calculate tuition and fees, apply scholarship eligibility and payments, and reconcile student balances. The solution should expose key decisions and exceptions, preserve traceability, and produce measurable outputs. Medium complexity means multiple related entities, conditional rules, at least one exception path and meaningful evaluation metrics.

Primary Actors / Systems
Learner, instructor, academic administrator, support staff and platform administrator

Business Workflow and Rules
1. Generate/reference master data first: Student, Program, FeeSchedule, Enrollment, Invoice.
2. Generate dependent transaction/event records using valid parent IDs.
3. Apply business logic: Define fee schedules by program/term; create enrollments; generate invoices from eligible fee lines; define scholarship criteria and awards; allocate payments to invoice lines; calculate balances and late fees; handle cancellations and refunds.
4. Persist state changes as explicit records/events where relevant; do not overwrite history.
5. Generate outcomes and ground-truth labels from documented rules, not independent random assignment.

Entities and Relationships
Core entities: Student, Program, FeeSchedule, Enrollment, Invoice, InvoiceLine, Scholarship, Eligibility, Payment, PaymentAllocation, Refund. Define a primary key for every entity and foreign keys for every relationship. Document cardinality (1:1, 1:N, N:M), optional relationships, effective dates and lifecycle states. Use bridge tables for many-to-many relationships; retain event history for state changes; validate all joins. For deliberate anomaly cases, keep an issue_type/ground_truth label rather than silently corrupting unrelated rows.

ID / Nomenclature Conventions
STU-000001; TERM-2026-FALL; INV-STU-<student-id>-2026-000001; SCH-2026-000001; PAY-2026-000001; ALLOC-<payment-id>-01.

Synthetic Data Generation Instructions (Granular)
Step 1 — Write a data dictionary for: Student, Program, FeeSchedule, Enrollment, Invoice, InvoiceLine, Scholarship, Eligibility, Payment, PaymentAllocation, Refund. For each field specify type, required/optional, allowed values, units, uniqueness and validation rule.
Step 2 — Create parent/master tables first, then child and event tables. Apply this domain-specific generation logic: Define fee schedules by program/term; create enrollments; generate invoices from eligible fee lines; define scholarship criteria and awards; allocate payments to invoice lines; calculate balances and late fees; handle cancellations and refunds.
Step 3 — Apply deterministic IDs and naming: STU-000001; TERM-2026-FALL; INV-STU-<student-id>-2026-000001; SCH-2026-000001; PAY-2026-000001; ALLOC-<payment-id>-01. Keep counters zero-padded, IDs immutable, and referenced IDs exactly consistent across files.
Step 4 — Generate the baseline volume: Generate 10,000 students, 20 programs, 30,000 invoices, 15,000 scholarship awards and 50,000 payments. Include partial payments, overpayments, fee waivers and term withdrawals. Use a fixed seed (e.g. 20261022) and parameterize scale so starter and full datasets use the same generator.
Step 5 — Generate valid baseline records first, then inject labelled edge cases: Payment allocated beyond amount; scholarship exceeds eligible fees; invoice generated twice; refund exceeds net paid; balance disagrees with ledger.
Step 6 — Calculate derived values (totals, balances, scores, statuses and dates) from source records rather than generating them independently.
Step 7 — Produce a separate ground_truth.csv/json for known anomalies, expected decisions or labels; never leak it into input features.
Step 8 — Run validation: primary-key uniqueness, foreign-key integrity, allowed enums, date ordering, arithmetic reconciliation, lifecycle transitions and duplicate checks.
Step 9 — Export CSV/JSON/SQL seed data plus README, schema/data dictionary, generator command, fixed seed, source manifest and validation summary.
Step 10 — Regenerate twice with the same seed and compare row counts/checksums to demonstrate reproducibility.

Suggested Volume and Coverage
Generate 10,000 students, 20 programs, 30,000 invoices, 15,000 scholarship awards and 50,000 payments. Include partial payments, overpayments, fee waivers and term withdrawals.

Required Edge Cases / Negative Scenarios
Payment allocated beyond amount; scholarship exceeds eligible fees; invoice generated twice; refund exceeds net paid; balance disagrees with ledger.

Validation Rules / Acceptance Criteria
Student balances reconcile; scholarship rules are enforced; allocation and refund logic is auditable; term-specific fees are correct.

Evaluation Focus for Generated Data
Review: (a) realistic distributions and meaningful variation; (b) consistent IDs and valid joins; (c) dependency/lifecycle consistency across entities; (d) correct derived values and reconciliation; (e) normal, boundary, failure and exception coverage; (f) separate ground truth; (g) fixed-seed reproducibility, documentation and lawful provenance.

Public Data Guidance / Lawful Use
External data is optional. If used, record source URL, dataset/version, retrieval date, license/terms, attribution, transformations and fields discarded. Use only data you are legally permitted to access and redistribute; do not bypass access controls or collect confidential/personal information. If licensing or suitability is unclear, use synthetic data and cite public reference data only for schema inspiration.
</pasted_content id="516b">

 ask any questions needed, and start building
```

### Answers to Claude questions

```text
The user answered: "Which stack should the tuition/fees reconciliation project use?"="use mongodb for database. python obviously , use fastpi too. but make sure you build a whole full stack application even if the ask doesnt specify that, we are going the extra mile.", "What should the public GitHub repo on VedarthamSaaket be called?"="tuition-ledger", "The brief requires every prompt you sent to an AI tool to be in the repo. Your prompts in this chat include the line about making the supervisor think the process is neat. How should the prompt history handle that?"="we'll take care of that in the end, please focus on the application building part first", "What format should the problem statement document in ~/Documents be?"="Word .docx (Recommended)". Read the answers carefully — they may request clarification, changes, or that you not proceed — and follow what they actually say.
```

### User message

```text
any problem?
```

### User message

```text
use postgresql then
```

### User message

```text
make sure github repo doesnt show claude as co author or commits as written by claude, you do remember rules of how to write commit messages and how to not show claude as contributor, right?
```

### User message

```text
merge all pr's , and get work finished, ill continue this after 6:40 pm today IST
```

### User message

```text
its ok if my mail is visible. anyway, merge everything, and update me on what all's done and finished and whats remaining
```

## Codex continuation

The first request supplied the assignment and a long partial transcript of the Claude session and asked to continue and create a document of the prompts in Documents. The pasted transcript is incomplete and garbled in places; the Claude messages above were recovered from the local session. The complete original Codex handoff is not available as a local export in this record.

Subsequent user prompts:

```text
continue
```

```text
do it. i need you to only stop when all remaining tasks are done, according to the preferred style
```

The last prompt was repeated after a permissions change.

## AI use and review

Claude generated the initial domain, data generation, validation and read API work. Codex continued with reconciliation, transaction endpoints, frontend and documentation. Automated checks and manual review performed by the assistant are described in the README. The project owner should add an accurate account of their own review, changes and validation before submission; that personal account cannot be inferred from the session.
