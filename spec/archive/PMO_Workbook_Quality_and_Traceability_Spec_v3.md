# Quality and Traceability Spec v3: Startup Kit, Readiness Checklist, and Project Delivery Workbook

September 30, 2026

## 1. Purpose and precedence

This spec records a quality and traceability review of the three ARC Genomics Platform artifacts generated on 2026-09-30, and specifies the fixes:

- `ARC_Genomics_Platform_Startup_Kit.docx` (the Kit)
- `ARC_Genomics_Platform_Startup_Readiness_Checklist.docx` (the Checklist)
- `ARC_Genomics_Platform_Project_Delivery_Workbook.xlsx` (the Workbook)

It also removes Project Management from the Workbook, both as a workstream and from the WBS.

**Precedence.** This document amends `spec/PMO_Startup_Toolkit_Workbook_Spec.md` (base) and `spec/PMO_Workbook_Delivery_Alignment_Spec_v2.md` (v2). Where they conflict, this document wins; everything else in base and v2 stands.

- **Part A** changes the Workbook generator. It is required.
- **Part B** fixes defects in the Kit and Checklist generation that the Workbook inherits. It changes Kit and Checklist content deliberately, so implement it only when instructed. Each Part B item is independent.

## 2. Assessment summary

| Artifact | Overall | Strengths | Main defects |
| --- | --- | --- | --- |
| Workbook | Good structure, weaker content | SOW phases as workstreams, in order; dates from week ranges (2026-10-05 to 2027-04-02); all 4 milestones, 20 deliverables, 15 work packages, and 34 RAID items carried with stable IDs; no readiness content | 2 deliverables and 2 work packages under the wrong phase; no milestone predecessors; every generated task owner blank; 11 dependencies all linked to M1; contract clarification text damaged; open questions missing; evidence inherited from the Kit is wrong for 12 deliverables |
| Kit | Rich content, data-integrity problems | Strong SOW interpretation, deliverable acceptance criteria, dependency log, communications plan | Deliverable evidence attached to the wrong deliverables; every dependency hard-linked to M1 and DEL-01; all 15 decisions share ID `DEC-01`; backlog parents encode the phase, not the deliverable; RAID and communications rows have no IDs; truncated text in several cells |
| Checklist | Useful content, unreliable gate evidence | 21 actionable open questions; 15 well-cited contract ambiguities | G01-14 says "No contractual ambiguities flagged" while listing 15; G01-11 cites an MBR cadence that is not in the plan; G01-03 marked Complete with all 20 client approvers unassigned; boilerplate commercial guardrails that do not match this Fixed Bid SOW |

## 3. Traceability assessment

| Element | Kit | Checklist | Workbook | Shared IDs | Status |
| --- | --- | --- | --- | --- | --- |
| Milestones | 4 (M1–M4) | G01-04; Q-16 to Q-18 (M2–M4 only) | 4 | Yes | Traceable. The Checklist has no date question for M1. |
| Deliverables | 20 (DEL-01–20) | Count only (20) | 20 | Yes | Traceable. DEL-06 and DEL-10 are under the wrong phase in the Workbook (A2). |
| Work packages | 15 (WP-01–15) | — | 15 | Yes | Traceable. WP-09 and WP-13 are misplaced (A2). The Kit's parent column is really a phase index (B4). |
| Deliverable evidence | 20 rows, about 12 misattached | — | Copied as-is | By ID, but the wrong content | Broken at the source (B1). The Workbook flags it (A9). |
| RAID (risks and issues) | 8 rows, no IDs, no probability or impact shown | Count only (8) | RAID-01–08 | No | One-way only. Workbook P/I/Severity values cannot be traced to anything visible in the Kit (B5). |
| Dependencies and assumptions | 11 (DEP-01–08, ASM-01–03) | Count only (11) | RAID-09–19 | Yes | Traceable. All 11 are wrongly linked to M1 in the Workbook (A4, B2). |
| Contract ambiguities | Not in the Kit (it has 6 separate clarification notes) | 15 (AMB-01–15) | RAID-20–34 | Yes, AMB | Checklist to Workbook traceable. The Kit has no link to them (B7). |
| Open questions | — | 21 (Q-01–21) | None | — | Gap. Delivery questions such as Start Date, approvers, and the HS-4781 date are lost (A8). |
| Decisions | 15, every one `DEC-01` | — | None; Linked Decision always blank | Duplicated | Broken (B3). |
| Communications plan | 7 rows, no IDs | G01-11 evidence does not match | COM-01–07, generated | Workbook only | One-way. COM IDs exist only in the Workbook (B5). |

**Overall.** Milestones, deliverables, work packages, dependencies, and contract ambiguities trace across artifacts by ID. RAID risks, communications, and decisions do not, because the Kit shows no IDs for them or duplicates them. Content traceability is weakest for deliverable evidence, where the ID matches but the text belongs to another deliverable.

## 4. Detailed findings

| ID | Artifact | Finding | Evidence | Severity | Root cause | Fix |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | Workbook | Project Management workstream and WBS branch present | Workstream 5, Reporting and Control package, Project Kickoff package | High (requested change) | v2 section 7.1 and 7.5 | A1 |
| F2 | Workbook | DEL-10 (faceted search, P2b) under M1; DEL-06 (backend integration and load tests, P2a) under M3; WP-09 under M1; WP-13 under M3 as "Other work" | WBS rows 1.1.7, 3.1.2, 3.1.7.1 | High | Hyphenated tokens counted three times (`micro-frontend`); phase name excluded from the scope text; the Kit's phase-by-phase contracted-deliverables list unused | A2 |
| F3 | Workbook | Schedule Predecessor blank for M2 to M4; "P1 Foundation accepted", "P2a Services and Data accepted", and "P2b Application Surface accepted" listed as client prerequisites | Schedule column Q; prerequisite tasks 2.1.1.2, 3.1.1.1, 4.1.1.1 | High | v2 detection requires "acceptance of" before the phase code | A3 |
| F4 | Workbook | RAID-09 to RAID-19 all linked to M1 (1.1) with note "Linked via deliverable DEL-01", including DEP-02 (P2a) and DEP-05 (Milestone 3) | RAID Log columns F and G | High | The Kit hard-codes `linked_milestone` and `linked_deliverable` (B2); v2 default-fill detection covers only `linked_milestone` | A4 |
| F5 | Workbook | Every generated task owner is `[UNASSIGNED - TO BE CONFIRMED]` | WBS column I | High | Role owners resolved to named people, who are unassigned | A5 |
| F6 | Workbook | COM-06 Milestone Acceptance Review placed in recurring tasks; acceptance packages use the generic review task | WBS 5.1.1.5 | Medium | Cadence text "At the end of each milestone (P1, P2a, P2b, P3)" not recognized | A6 |
| F7 | Workbook | Contract clarification descriptions damaged, for example "...Platform.pdf,: test-suite acceptance..." and "cites Certification criteria 'as described ' ... but no exists" | RAID-20 to RAID-34 | High | `sanitize_report_text` strips "Section N" references out of contract citations | A7 |
| F8 | Workbook | The 21 open questions are not in the RAID Log | — | Medium | Not specified in v2 | A8 |
| F9 | Workbook, Kit | Evidence belongs to other deliverables. Examples: DEL-13 (nomenclature) shows smoke-test evidence; DEL-15 (test suites) shows training evidence; DEL-07 (performance spike) shows MTA migration evidence | WBS column Q; Kit Deliverables matrix | High | Kit merges acceptance items by ID across two separate LLM passes that number differently (B1) | A9, B1 |
| F10 | Workbook | All tasks in a milestone share its full date range; no time is reserved for acceptance | WBS columns J and K | Medium | v2 section 7.7 | A10 |
| F11 | Workbook | Severity column is a formula, and the P/I values it uses are not visible in the Kit | RAID columns I to L | Low | Kit table omits P/I (B5) | A11 |
| F12 | Workbook | Level 3 deliverable rows repeat the deliverable ID as Source ID; no milestone-ID dropdown list | WBS column H; defined names | Low | Implementation detail | A12 |
| F13 | Kit | All 11 dependencies and assumptions linked to M1 and DEL-01 | `aggregator.py` sets `linked_milestone=milestones[0].id` and `linked_deliverable=deliverables[0].id` | High | Hard-coded default | B2 |
| F14 | Kit | All 15 decisions have ID `DEC-01` | Decision Log Seed table | Medium | The LLM copies the model default ID; no renumbering | B3 |
| F15 | Kit | Backlog "Parent Deliv" is DEL-01 for P1 work, DEL-02 for P2a, and so on, not the real deliverable | Scope Decomposition table | Medium | Extraction prompt ambiguity | B4 |
| F16 | Kit | RAID and communications rows have no IDs; P/I/Severity not shown | RAID Log and Communications tables | Medium | Table design | B5 |
| F17 | Kit | Closing parentheses lost, for example "(Toptal and Client", "SLA Met (Yes", "(G-01 gate", "Syngenta (Client" | Charter, Communications, Stakeholder, and RACI tables | Low | Unknown; investigate text cleanup and cell formatting | B6 |
| F18 | Kit | The Kit does not list or reference the 15 contract ambiguities, which appear only in the Checklist | Kit SOW Interpretation "Ambiguities" row has 6 different notes | Medium | Rendered only in the Checklist | B7 |
| F19 | Checklist | G01-14 "No contractual ambiguities flagged", status Complete, while the same document lists AMB-01 to AMB-15 | G01-14 row | High | Hard-coded evidence in `aggregator.py` | B8 |
| F20 | Checklist | G01-11 evidence "Weekly check-in, weekly PSR, and MBR cadence" does not match the 7-item plan, which has no MBR | G01-11 row | Medium | Hard-coded evidence | B8 |
| F21 | Checklist | G01-03 Complete although all 20 deliverables lack a client approver | G01-03 row; Kit Deliverables matrix | Medium | Approver not included in the completeness check | B8 |
| F22 | Checklist | Commercial guardrails cite labor-rate realization, periodic burn tracking, and a threshold of "rework effort > 10% of deliverable budget", which do not reflect a Fixed Bid SOW billed on milestone acceptance | Commercial and Margin Guardrails table | Low | Generic defaults | B8 |
| F23 | All | This run extracted 20 deliverables where the previous run of the same SOW extracted 19; IDs are not stable across fresh generations | Prior workbook vs this one | Medium | LLM extraction is not fully deterministic | Section 7, note 3 |

# Part A: Workbook changes (required)

## A1. Remove Project Management from the Workbook

- Delete the `Project Management (ongoing)` workstream, the `Ongoing Project Management & Reporting` recurring row, and its `Reporting and Control` package (v2 section 7.5).
- Delete the `Project Kickoff` package (v2 section 7.1), including the kickoff communications task.
- Keep the task `Update schedule and RAID Log after acceptance` in the Milestone Acceptance package. It is a PM task tied to accepting that milestone's deliverables (see the rule below).
- Communications-plan items no longer appear in the WBS, except per-milestone items used as the acceptance review task (A6).
- The `Raise change requests` task is removed; change control stays documented in the Kit.
- Remove `Project Management (ongoing)` from the workstream dropdown. The list becomes the phase workstreams plus `Multiple phases` and `Cross-phase`, with the last two used only by the RAID Log.
- Remove the base 4 `PMG` fallback workstream. With no phase label, the keyword fallback may not return `PMG`; use `BLD` instead.

For example, this row in the current output must not exist in the Schedule or the WBS, and nothing may take its place:

```text
5	1	Workstream	Project Management (ongoing)	Project Management (ongoing)	...	2026-10-05	2027-04-02	...	0%	...	PM Best Practice
```

No workstream may be generated from anything other than a SOW milestone phase, and `PM Best Practice` may never appear as the Source of a level 1 or level 2 row.

The WBS now holds only work that produces or gains acceptance for SOW deliverables: Client Prerequisites, deliverables, Other work, and Milestone Acceptance. The Schedule has one workstream per SOW phase and nothing else.

**PM tasks tied to deliverables stay.** Project management tasks are allowed, and expected, when they sit inside a phase's packages and serve that milestone's deliverables or work packages. These tasks stay:

- Deliverable packages: `Assemble acceptance evidence`, `Internal quality review against acceptance criteria`, and, in per-deliverable acceptance mode, the submit, feedback, and acceptance tasks.
- Client Prerequisites: every `Confirm: ...` task.
- Milestone Acceptance: prepare the package, support UAT, the Milestone Acceptance Review, address feedback, obtain sign-off, and update the schedule and RAID Log after acceptance.

What is removed is PM work that stands apart from any deliverable: the separate workstream, the recurring reporting row and its package, and the project-level kickoff package.

## A2. Mapping accuracy (amends v2 section 6)

- **Tokenizer.** Split hyphenated words into their parts only; do not also keep the whole compound, so `micro-frontend` yields `micro` and `frontend`. Strip `ing` from tokens longer than 5 characters before the plural rule, so `testing` becomes `test`. Add `delivered`, `estimated`, and `plus` to the stop words.
- **Milestone scope text** for scoring = the milestone name (`P2a Services and Data accepted`), plus its scope, plus every `sow_interpretation.contracted_deliverables` entry for that phase. An entry belongs to a phase when it starts with that phase code (`P2a testing: ...`). Entries with no phase code inherit the code of the entry before them, so "Training materials and user documentation" joins P3.
- All other v2 section 6 rules, including thresholds, are unchanged.

With these changes, every ARC deliverable and work package maps to its correct phase (Appendix B).

## A3. Milestone predecessors (replaces v2 section 5, "Milestone predecessors")

A `key_dependencies` or `critical_path_assumptions` entry is a **schedule link** when it references another milestone, by phase code (`P2a`), full phase name (`P2a Services and Data`), or `Milestone N`, and also contains any of: `accept`, `acceptance`, `accepted`, `complete`, `completion`, `sign-off`, `after`, `before`, `begins`, `starts`.

- The referenced milestone becomes the Schedule Predecessor, and the milestone's level 2 row in the WBS shows it.
- Schedule links are removed from Client Prerequisites (column R and the prerequisite tasks).
- When a milestone has several schedule links, list them comma-separated.

## A4. RAID linking (amends v2 section 8)

- **Default-fill detection.** Apply the v2 rule (at least 4 items, at least 75% sharing one value) separately to `linked_milestone` and to `linked_deliverable`. Ignore every default-filled value.
- **New linking order:** phase codes, phase names, and `Milestone N` mentions in the item text; then milestone or deliverable IDs mentioned in the text; then non-default `linked_milestone`; then non-default `linked_deliverable`; otherwise none.
- Remove the note `Linked via deliverable ...` unless rule 4 actually applied.

## A5. Task owners are roles

The Owner column on every generated task holds the role from the template, such as `Talent PM`, `Delivery Manager`, or `Toptal Delivery Team`, and is never resolved to a person. Backlog tasks use the work package owner when it is not a placeholder, else `Toptal Delivery Team`. Deliverable rows keep the Kit owner. `[UNASSIGNED - TO BE CONFIRMED]` appears only where the Kit itself is unassigned.

## A6. Per-milestone communications (amends v2 section 7.4)

A communications-plan item is per-milestone when its cadence, delivery day, or name matches, case-insensitive:

```text
each\s+milestone|per\s+milestone|end\s+of\s+(each|every)\s+milestone|milestone\s+acceptance
```

It replaces `Hold milestone acceptance review with client approvers` in every Milestone Acceptance package, named `{name} for {audience}` (for ARC: `Milestone Acceptance Review for Client's designated approvers and project stakeholders`).

## A7. Contract clarification rows (amends base 7 and v2 section 3 text cleanup)

- Parse `conflicting_clauses` with:

    ```text
    ^\s*\[V\d+\]\s*(?P<doc>[^,]+?\.(?:pdf|docx|pptx))\s*,?\s*(?P<ref>[^:]*?)\s*:\s*(?P<text>.+)$
    ```

- Add a RAID column **Contract Reference** after Description, holding `{doc}, {ref}` (for example `Exhibit A - Arc Genomics Platform.pdf, Section 4 (Latency Acceptance Criteria)`). Leave it blank for non-contract rows.
- Description = `{category}: {text}`.
- For these rows, apply only the `ACTION_TAG_REGEX` removal and whitespace cleanup. Do not apply `sanitize_report_text`, because the clause references are what the Talent PM needs to resolve each item. The same applies to `recommended_clarification` in Mitigation / Response.
- The final RAID column order becomes: A RAID ID · B Type · C Description · D Contract Reference · then the v2 section 8 columns from Category onward, shifted one column right.

## A8. Open questions in the RAID Log

- Add each `baseline.open_questions` entry as a RAID row after the contract clarifications, with Type `Issue`, Category `Open Question`, Owner `Talent PM`, Status `Open`, and Source `Baseline - Open Questions`.
- Source ID = `Q-NN`, numbered by the entry's position in the full, unfiltered list, so the IDs match the Checklist.
- Skip entries matching the section 3 readiness pattern of v2, or matching `\brole is unassigned\b`. For ARC this skips Q-19 to Q-21.
- Link them to milestones with the A4 rules.

## A9. Evidence consistency flag

For each deliverable whose `evidence_required` is not a placeholder, score the evidence text against every deliverable's `name + acceptance_criteria`. Use the v2 weighted overlap, with IDF computed across those 20 texts.

If the deliverable's own score is below 0.10, the best score is at least 0.35, and the best-scoring deliverable is a different one, add the note `Evidence may belong to {DEL-xx} - verify against the SOW` to the deliverable row, and apply the warning fill to its Acceptance / Completion Criteria cell.

Count flags in `PMOWorkbookResult.evidence_flags` and print the count in the CLI summary.

## A10. Task timing (replaces v2 section 7.7)

When a milestone spans at least 2 weeks, its final week is reserved for acceptance:

| Package | Planned Start | Planned Finish |
| --- | --- | --- |
| Client Prerequisites | Project Start Date | For the first milestone, the Start Date. Otherwise the last working day before the milestone's Planned Start. |
| Deliverables and Other work | Milestone Planned Start | `internal_buffer_date` if present, else the Friday of the milestone's second-to-last week |
| Milestone Acceptance | Monday of the milestone's final week | Milestone Planned Finish |

Milestones shorter than 2 weeks keep the v2 rule.

## A11. RAID rating

Rename column `Severity` to `Rating`. It keeps the current formula derived from Probability and Impact. When the Kit supplies a non-default severity (anything other than `Medium` together with default P/I), write that value instead and add the note `Rating from baseline`.

## A12. Minor fixes

- Leave Source ID blank on level 3 deliverable rows; the Deliverable ID column already carries the ID.
- Add a hidden defined name `List_Milestone_IDs` and use it for the RAID Linked Milestone validation.
- Recurring status defaults are no longer needed (A1).

## A13. Traceability self-check

After building the model, compute this table and print it in the CLI summary. Also expose it as `PMOWorkbookResult.traceability`.

| Element | In baseline | In workbook | Missing IDs |
| --- | --- | --- | --- |
| Milestones | n | n | ... |
| Deliverables | n | n | ... |
| Work packages | n | n | ... |
| RAID items, dependencies, contract clarifications, open questions | n each | n each | ... |

Any missing ID is logged at WARNING. A test asserts that none is missing for `arc_baseline_v3`.

# Part B: Kit and Checklist fixes (implement only when instructed)

## B1. Deliverable acceptance merge (`aggregator.py`, acceptance merge block)

Stop matching `acceptance_matrix_items` to deliverables by `id`. Match each acceptance item to the deliverable whose normalized name has the highest token overlap (the A2 tokenizer, Jaccard at least 0.5). Use the ID only as a tie-breaker. Items with no match are logged and not merged. Add a test with two lists numbered in different orders.

## B2. Dependency and assumption links (`aggregator.py`, dependency block)

Remove `linked_milestone=milestones[0].id` and `linked_deliverable=deliverables[0].id`. Set a link only when the item text names a milestone phase code, milestone ID, or deliverable ID. Apply the same fix to the fallback backlog's `linked_milestones=[m.id for m in milestones[:1]]`.

## B3. Decision IDs

After extraction, renumber decisions `DEC-01`, `DEC-02`, and so on, in order, whenever any ID repeats or equals the model default. Update any `linked_decision` references that point to renumbered IDs.

## B4. Backlog parents

Change `SCOPE_DECOMPOSITION_PROMPT` so the model receives the extracted deliverable list, and must return an existing `parent_deliverable_id` and the `linked_milestones` for each work package. Validate the result: when a parent ID does not exist, or its deliverable maps to a different phase than the work package (A2 scoring), clear the parent and log it.

## B5. IDs and columns in Kit tables

- The RAID Log table gains an ID column (`RSK-NN` for risks, `ISS-NN` for issues) plus Probability and Impact columns.
- The Communications and Reporting Plan table gains an ID column (`COM-NN`).
- The docx parser reads these back.
- The Workbook uses these IDs as Source ID, replacing its generated COM numbering.

## B6. Truncated parentheses

Find the cause of lost closing parentheses in Kit cells (F17), fix it, and add a round-trip test on the strings in F17.

## B7. Contract ambiguities in the Kit

Add a row to the Kit's SOW Interpretation table, "Contract Ambiguities Logged", listing `AMB-NN: {category}` for each item and pointing to the Checklist for detail.

## B8. Checklist evidence

- **G01-14:** evidence = `{n} contractual ambiguities logged with recommended clarifications`. Status is `Review Required` when any item is `Open`, and `Complete` only when none are open.
- **G01-11:** evidence = the communications-plan item names joined with `, `.
- **G01-03:** `has_unconfirmed_delivs` also includes an unassigned or placeholder `client_approver`.
- **G01-02:** drop "tailored buffers" when no milestone has an internal buffer date.
- **Commercial guardrails:** for Fixed Bid, replace the burn and rate defaults with milestone-acceptance billing wording, or mark each default value `[Standard PMO guardrail - confirm]`.
- **Open questions:** generate the "no committed external delivery date" question for every undated milestone, including M1.

# 5. Tests and expected results

**Fixture `arc_baseline_v3`** is built from Appendix A: this run's 4 milestones with their scopes and key dependencies; the contracted-deliverables list; 20 deliverables with their acceptance criteria and the Kit's misattached evidence; 15 work packages with the Kit's phase-index parents; 11 dependencies and assumptions, all with `linked_milestone="M1"` and `linked_deliverable="DEL-01"`; 8 risks and issues; 15 contract ambiguities with `[V1] Exhibit A ...` citations; 21 open questions; and the 7-item communications plan with the cadences shown in Appendix A.

**New and updated tests**

- `test_no_project_management.py`: no workstream, WBS row, or dropdown value contains "Project Management", "Kickoff", "Reporting and Control", or "Ongoing"; the WBS has exactly 4 level 1 rows.
- `test_mapping_v3.py`: the Appendix B mapping table exactly.
- `test_predecessors_v3.py`: M2←M1, M3←M2, M4←M3, and none of the "... accepted" entries appear in Client Prerequisites.
- `test_raid_links_v3.py`: default-fill detection on both fields, and the Appendix B RAID links.
- `test_contract_reference.py`: the parsed Contract Reference and an intact Description for AMB-01 and AMB-15, with no `,:` sequences and no empty-quote fragments such as `'as described '`.
- `test_open_questions.py`: 18 rows, Q-01 to Q-18, IDs matching the Checklist numbering.
- `test_evidence_flags.py`: exactly the 12 flags in Appendix B.
- `test_task_owners.py`: no generated task has a placeholder owner.
- `test_task_timing.py`: the Appendix B dates.
- `test_traceability_self_check.py`: nothing missing.
- Part B tests only when Part B is implemented.

# 6. Appendix A: ARC fixture data (this run)

**Milestones** (Start Date 2026-10-05). The name is the text before the colon in each description.

| ID | Scope (after the colon) | Key dependencies |
| --- | --- | --- |
| M1 | micro-frontend shell, Azure AD/MSAL authentication, E2E test harness, pipeline quality gates, and security/data validation delivered (estimated weeks 1-6). | Client provides design system access (code library, tokens, design files, guidelines, named contact) by the start date; Client IdP team available for Azure AD / MSAL authentication; Client-built pipelines, Snowflake data model, and governance controls completed before related testing begins |
| M2 | FastAPI search/detail endpoints, async processing, OneGWAS direct-write integration, performance spike, and data ingestion validations delivered (estimated weeks 7-16). | Client completes HS-4781 (Snowflake schema) before P2a begins; P1 Foundation accepted; Client-built ingestion and migration pipelines completed before validation work; Domain users and trait taxonomy domain experts available; Cogen API stable at approximately 95% |
| M3 | ARC faceted search, result detail and haplotype visualization, haplotype endpoints, nomenclature service, and related test suites delivered (estimated weeks 17-21). | P2a Services and Data accepted; Client provides UI/UX designs for the Milestone 3 screens by the start date; Client design system available and any design-system changes communicated in advance |
| M4 | integration, performance, security, and cross-browser testing, UAT, hardening, production smoke tests with 48-hour defect watch, MTA Store parity confirmation, and training materials delivered (estimated weeks 22-26). | P2b Application Surface accepted; Client maintains development, staging, and production environments; Client scientist UAT groups available; Client remediates defects in Client-built components before cutover |

**Contracted deliverables:** as in the Kit's SOW Interpretation table, 8 entries. The P2a entries are "P2a Services and Data (weeks 7–16): ..." and "P2a testing: Backend integration and load tests, ...". The final entry, "Training materials and user documentation.", has no phase code.

**Deliverables, work packages, dependencies, RAID, ambiguities, questions, and communications:** exactly as they appear in the Kit and Checklist of this run. Copy them into the fixture verbatim, including the misattached evidence and the phase-index backlog parents.

# 7. Appendix B: Expected ARC results

**Schedule**

| WBS | Workstream | Milestone | Planned Start | Planned Finish | Predecessor |
| --- | --- | --- | --- | --- | --- |
| `1.1` | P1 Foundation | M1 | 2026-10-05 | 2026-11-13 | |
| `2.1` | P2a Services and Data | M2 | 2026-11-16 | 2027-01-22 | M1 |
| `3.1` | P2b Application Surface | M3 | 2027-01-25 | 2027-02-26 | M2 |
| `4.1` | P3 Launch | M4 | 2027-03-01 | 2027-04-02 | M3 |

There are no other rows.

**Deliverable mapping and work packages**

| Milestone | Deliverable (basis, matched work package) |
| --- | --- |
| M1 | DEL-01 (Scope match, WP-01) · DEL-02 (Scope match, WP-02) · DEL-03 (Scope match, WP-03) · DEL-04 (Phase code, WP-04) |
| M2 | DEL-05 (Scope match, WP-05) · DEL-06 (Scope match, WP-06) · DEL-07 (Scope match, none) · DEL-08 (Scope match, WP-07) · DEL-09 (Phase code, WP-08) |
| M3 | DEL-10 (Scope match, WP-09) · DEL-11 (Scope match, none) · DEL-12 (Scope match, WP-10) · DEL-13 (Scope match, WP-11) · DEL-14 (Phase code, WP-12) |
| M4 | DEL-15 (Scope match, WP-13) · DEL-16 (Scope match, WP-14) · DEL-17 (Scope match, none) · DEL-18 (Scope match, none) · DEL-19 (Scope match, WP-15) · DEL-20 (Scope match, none) |

There are no Other-work packages and no unmapped deliverables.

**Task counts**

| Package | Count | Tasks |
| --- | --- | --- |
| Client Prerequisites | 4 | 12 (M1 3, M2 4, M3 2, M4 3) |
| Deliverables | 20 | 120 (6 each) |
| Milestone Acceptance | 4 | 24 (6 each: prepare package, support UAT, Milestone Acceptance Review, address feedback, obtain sign-off, update schedule and RAID Log) |
| **Total** | | **156 tasks** |

**Task timing**

| Milestone | Prerequisites due | Deliverable work finish | Acceptance window |
| --- | --- | --- | --- |
| M1 | 2026-10-05 | 2026-11-06 | 2026-11-09 to 2026-11-13 |
| M2 | 2026-11-13 | 2027-01-15 | 2027-01-18 to 2027-01-22 |
| M3 | 2027-01-22 | 2027-02-19 | 2027-02-22 to 2027-02-26 |
| M4 | 2027-02-26 | 2027-03-26 | 2027-03-29 to 2027-04-02 |

**RAID Log:** 52 rows. These are RAID-01 to RAID-08 (risks and issues), RAID-09 to RAID-19 (dependencies and assumptions), RAID-20 to RAID-34 (contract clarifications), and RAID-35 to RAID-52 (open questions Q-01 to Q-18). Link spot checks:

- DEP-02 (HS-4781 before P2a) → M2.
- DEP-03 (sequential gates) → M2, M3, M4 (`Multiple phases`).
- DEP-05 (Milestone 3 screens) → M3.
- ASM-01 (week ranges for all phases) → `Multiple phases`.
- DEP-01, DEP-04, DEP-06, DEP-07, DEP-08, ASM-02, ASM-03 → `Cross-phase`.

No dependency row is linked to M1 by default.

**Evidence flags:** 12. They are DEL-02, 03, 04, 05, 07, 08, 10, 11, 12, 13, 14, and 15. For example, DEL-13 → DEL-18, DEL-14 → DEL-19, and DEL-15 → DEL-20. DEL-01, DEL-06, and DEL-09 are not flagged; DEL-16 to DEL-20 have placeholder evidence.

# 8. Implementation notes

1. Implement Part A in the order A1, A2, A3, A4, A5, A6, A7, A8, A9, A10, A11, A12, A13, running tests after each item.
2. Appendix B is the source of truth for the ARC result. If your output differs, fix the code. If you believe an expected value is wrong, stop and report it with the reason.
3. To keep IDs stable, generate the Workbook from `--reingest-docx` of an approved Kit rather than from a fresh SOW extraction, because fresh extractions can renumber deliverables (F23). Add this to the README.
4. Part B changes Kit and Checklist content. Implement it only when instructed, one item at a time, each with its own tests.
