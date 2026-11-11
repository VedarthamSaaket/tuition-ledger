# Reviews and decisions

This note records the owner’s review requests, the audits I performed, and the decisions that shaped the implementation. It is intended for the supervisor as context, not as a substitute for the README or `docs/testing_guide.md`.

## 1. Review requests from the owner

The owner reviewed the work in stages and asked for these changes:

1. **Match the role guide.** The guide defines five roles, their starting views, navigation and actions, and a reviewer sample learner ID of `STU-000001`. The application needed to match that guide.
2. **Make the learner example visible in the app.** The sample ID had to appear beside the Learner student-ID field without requiring the separate document, with a clear caveat that a replaced dataset may need a different ID.
3. **Apply Libre Baskerville Italic consistently.** Replace Playfair Display and DM Sans across headings, navigation, buttons, forms, tables and role cards; bundle the font and its licence locally; check readability and layout at desktop and mobile widths.
4. **Verify the final experience.** Build and test the frontend, exercise all five role entry paths, confirm the learner example works, and inspect typography for clipping or awkward wrapping.
5. **Make the landing page self-explanatory.** Add crisp usage instructions near the top of the landing page, not at the bottom, and make every button give visible feedback: success, error, or a message when nothing changed.
6. **Keep the application running.** Start and verify both the backend and frontend.
7. **Audit readiness against the problem statement.** Identify gaps, then fix them to the core, especially packaging evidence, the full-profile artifacts, the allocation ID pattern and lifecycle-state coverage.
8. **Document tests, reviewer instructions and decisions.** This document and `docs/testing_guide.md` are the result.

## 2. Audits performed

The audits found and fixed these issues:

- **Brand mark regression.** Replacing the stylesheet caused the `T·L` mark to stack vertically. It was restored to a centred flex layout.
- **Rupee glyph.** Libre Baskerville does not contain `₹`. The glyph falls back to the system serif; this is visually clean but is not the same typeface. It is disclosed in the README.
- **No-op button feedback.** A global guard reports when a click produces no visible change. It originally risked false positives on invalid forms and on the “Use sample” button, which only changes an input value. Invalid forms are now excluded, and “Use sample” shows an explicit confirmation.
- **Full volume not public.** `data/full` is about 518 MB and gitignored. The full manifest, validation summary, evaluation, exceptions, ground truth and reproducibility report are now committed under `docs/`.
- **Allocation ID mismatch.** The dictionary said `ALLOC-<payment>-00`; generated IDs start at `-01` and match the problem statement. The schema text was corrected, the dictionary regenerated, and a regression test added.
- **Missing lifecycle states.** `UNPAID` and `PARTIALLY_PAID` never appeared because every invoice was past due at the snapshot. An early-registration Spring 2027 term now creates invoices issued before the snapshot and due after it, so both states occur. Future-term enrollments remain `REGISTERED`, and no event is dated after the snapshot.
- **Dictionary line endings.** The generated CSV used CRLF, which made diffs noisy. It now writes LF; a test locks this in.
- **Evidence drift.** Full-profile evidence copies were compared byte-for-byte with the regenerated artifacts; they match.

## 3. Major decisions

### Data and provenance

- **Fully synthetic data.** No public dataset, scrape, API or personal data is used. Names are hand-written, emails use `example.edu`, the seed is fixed at `20261022`, and the generator is parameterised for starter and full profiles. This keeps provenance lawful, reproducible and free of licensing or privacy risk. The README records this explicitly and leaves a template for adding a public source with URL, version, retrieval date, licence, attribution, transformations and discarded fields.
- **Two profiles.** The starter profile (500 students) is committed as a reviewable sample. The full profile (10,000 students, 30,000 invoices, 15,000 awards, 50,000 payments) is generated locally because its export is about 518 MB. Its small evidence files are committed under `docs/`.
- **Five terms.** `TERM-2027-SPRING` is an early-registration term invoiced on 2026-10-05 and due on 2026-11-16. The snapshot is 2026-10-22. This makes `UNPAID` and `PARTIALLY_PAID` observable without future-dating records.
- **Fixed snapshot, live aging.** The dataset and committed evaluation use `2026-10-22`. The live API uses the current date for aging and effective dashboard status, as documented; stored invoice statuses and the evaluation remain anchored to the snapshot.

### Domain rules

- **Fees by program, term and effective date.** Fee schedules are versioned and carry effective ranges. Charge lines record the schedule row they were priced from. A revised Fall 2026 technology fee exercises the effective-dating rule.
- **One invoice per enrollment in clean data.** A second invoice is a labelled `DUPLICATE_INVOICE` anomaly, not a normal state.
- **Scholarship eligibility is explicit.** Eligibility is a bridge between students and schemes, with pass/fail criteria recorded. Awards come only from eligible assessments and are capped by the eligible fee base. Ground truth is separate.
- **Payments allocate to invoice lines.** `PaymentAllocation` is a bridge table. Overpayments remain as unapplied credit. Refunds are bounded by net paid and available credit. Late fees are bounded and posted at the grace date. Withdrawals reverse eligible fees on a documented schedule.
- **Append-only history.** Ledger entries, events and decisions are append-only. Balances are derived from source rows; the stored account balance must reconcile with the ledger.
- **Five required anomalies.** Allocation beyond payment, scholarship above eligible fees, duplicate invoice, refund above net paid, and stored balance disagreeing with the ledger are injected deliberately, labelled separately and detected by reconciliation.

### Application and access

- **Roles are a demonstration of permissions, not authentication.** Five roles are selected by request headers and the UI. There is no sign-in. The README warns that a deployment boundary and real identity/authorisation are required before real use.
- **INR with integer paise.** All monetary values are Indian rupees; arithmetic is in paise; display uses Indian digit grouping.
- **Idempotency and concurrency.** Payment and refund requests require an idempotency key. Row locking and tests cover competing refunds and simultaneous payment retries.
- **Error and no-op feedback.** The UI reports loading, success and failure. API errors are normalised. A global guard reports a click that produces no visible change. Invalid native form submissions are excluded so validation is not mistaken for a dead button.

### Frontend design

- **Libre Baskerville Italic throughout.** The font is bundled locally with its SIL Open Font License. Playfair Display and DM Sans were removed. Type sizes, line heights and letter spacing were adjusted for the italic face, and layouts were checked at desktop and mobile widths.
- **Crisp landing guidance.** A three-step “How to use” panel sits in the first viewport, with the learner sample ID, a “Use sample” action and a dataset-replacement caveat.
- **Clear success/error states.** Workspace actions show a status message; failures show an inline error and a toast.

## 4. Residual trade-offs

- No authentication or payment gateway. This is a local demonstration, not a payment processor.
- No committed browser end-to-end suite. The five role paths were verified manually in a browser at desktop and mobile widths; this is documented in `docs/testing_guide.md`.
- The full 518 MB dataset is not committed. The committed evidence makes the claims reviewable; the generator reproduces the data identically.
- The anomaly detector scores perfectly against labels generated from the same rules. This measures consistency with the documented rules, not real-world detection performance.
- The live dashboard uses the current date for effective aging while the stored dataset is anchored to the snapshot. A reviewer running after the early-registration due date may see different effective dashboard statuses; the stored invoice statuses and committed evaluation remain the canonical snapshot.
- The application has an additive schema upgrade command, not a complete versioned migration and recovery system. Further operational, security and financial controls are required before real deployment.
