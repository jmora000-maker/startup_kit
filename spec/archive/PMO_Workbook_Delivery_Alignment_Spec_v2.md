# Correction Spec v2: Align the Workbook to SOW Delivery (Amends the PMO Startup Toolkit Workbook Spec)

September 30, 2026

## 1. Purpose and precedence

The workbook produced by `--export-tools` must be the Talent Project Manager's initial delivery plan: a schedule of the SOW milestones, a WBS for producing and getting acceptance of the SOW deliverables, and a delivery RAID log. This spec is based on a review of the actual output for ARC Genomics Platform (`ARC_Genomics_Platform_PMO_Startup_Toolkit.xlsx`) and fixes every problem found there.

**Precedence**

- This document amends `spec/PMO_Startup_Toolkit_Workbook_Spec.md` (the "base spec"). Where they conflict, this document wins.
- It fully replaces `spec/PMO_Workbook_Delivery_Alignment_Spec.md` (correction v1). Delete v1 from the `spec` folder; do not implement it.
- Anything the base spec defines that this document does not change stays as written. "Base 6.2" means section 6.2 of the base spec.

**Target outcome, in one line per tab**

- **Project Schedule:** the SOW phases as workstreams, each with its SOW milestone, in delivery order, with planned dates derived from the SOW week ranges.
- **WBS:** phase, then milestone, then each SOW deliverable with the tasks to produce it, plus client prerequisites and milestone acceptance.
- **RAID Log:** the Kit's delivery risks, assumptions, issues, and dependencies, linked to the phases they affect.

No readiness content appears anywhere in the workbook.

## 2. Problems found in the ARC Genomics output

| # | Symptom in the workbook | Cause | Fixed in |
| --- | --- | --- | --- |
| 1 | PM-01 G-01 gate, 15 G01 checklist tasks, mobilization tasks, PM-02 closure, readiness score, `ACT-NN` IDs, "Startup Kit" labels | Base spec sections 4 to 7 | Section 3 |
| 2 | Milestones out of order (M2, M1, M3, M4); M1 "P1 Foundation" and M3 "P2b Application Surface" placed under Testing & QA | Keyword classifier on long milestone text; Schedule grouped by taxonomy order | Section 4 |
| 3 | Every milestone date blank; no timeline; "External date not confirmed" on every row | The SOW gives relative week ranges ("est. weeks 1–6"), which nothing parses | Section 5 |
| 4 | DEL-02 (Azure AD authentication) placed under M2; DEL-03 (E2E harness) under M3; DEL-04 under M4 | `Backlog link` rule trusts `parent_deliverable_id`, which is wrong in the Kit (for example WP-04 FastAPI is parented to DEL-02 authentication) | Section 6 |
| 5 | Kit backlog items attached to the wrong deliverables (FastAPI tasks under authentication) | Same as 4 | Section 6 |
| 6 | Generic "Testing & QA Milestone Activities" and "Data & Integration Milestone Activities" task lists that do not match the milestone | Template chosen from the misclassified workstream | Section 7 |
| 7 | 95 per-deliverable "submit / feedback / obtain written acceptance from [UNASSIGNED]" tasks | Base 6.2 assumes per-deliverable acceptance; this SOW accepts at an end-of-milestone Acceptance Review | Section 7.4 |
| 8 | Task names hundreds of characters long, embedding evidence and review-window text | Base 6.2 interpolates Kit text into task names | Section 9 |
| 9 | One-time Kickoff Call and per-milestone Acceptance Review listed as recurring tasks | All communications-plan items treated as recurring | Section 7.5 |
| 10 | Recurring tasks chained as predecessors of each other; cross-milestone predecessor chains from backlog references | Base 6.5 predecessor rule applied to every package | Section 7.6 |
| 11 | RAID-08 to RAID-19 all linked to M1, including items about P2a, P2b, and P3 | The Kit's `linked_milestone` is default-filled with M1 | Section 8 |
| 12 | RAID workstreams from keyword guesses (Build, Design) that are not phases | Keyword classifier on RAID text | Section 8 |
| 13 | Duplicate note text ("External date not confirmed ..." twice) | Notes appended without de-duplication | Section 9 |

**Known upstream issue (out of scope, do not fix here).** In this Kit, deliverable `evidence_required` and `review_window` values appear shifted between rows. For example, DEL-07 (performance spike) carries evidence about "Working UI and render-time results ... Milestone 3", and DEL-15 (UAT records) carries evidence about training materials. The workbook must not use `evidence_required`, `review_window`, or `rejection_rework_path` to decide mapping. It copies them only into the Acceptance / Completion Criteria column, where the PM can correct them.

## 3. Remove all readiness content

The builder must not read these baseline fields: `readiness_checklist`, `gate_decision`, `action_required_items`, `readiness_score`, `readiness_breakdown`, `workflow_state`, `sla_met`, `kit_drafted_date`, `talent_onboarding`, `governance_tier`.

Remove from the base spec: `PM-01`, `PM-02`, and their substitution rules (base 4); the Mobilization Activities and G-01 Readiness Checklist packages and the tier health review (base 6.4); every Linked Action ID column (base 5, 6.5, 7); and the RAID owner fallback to action items (base 7).

**Defensive filter.** Drop any milestone, deliverable, work package, or RAID item whose text matches the pattern below (case-insensitive). Log each at WARNING and count them in `PMOWorkbookResult.excluded_items`.

```text
\b(G-?01|readiness\s+gate|startup\s+readiness|readiness\s+checklist|readiness\s+score|gate\s+decision)\b
```

**Naming**

| Item | Value |
| --- | --- |
| File name | `{Project}_Project_Delivery_Workbook.xlsx` |
| Workbook title property | `{Project} Project Delivery Workbook` |
| Workbook creator property | `Toptal PMO Generator v{version}` |
| CLI summary heading | `PROJECT DELIVERY WORKBOOK` |
| `--export-tools` help, parser epilog, README | "Project Delivery Workbook" in place of "PMO Startup Toolkit workbook" |

**Source values**

| Base value | New value |
| --- | --- |
| `Startup Kit - Milestone Delivery Plan` | `Baseline - Milestone Plan` |
| `Startup Kit - Deliverables` | `Baseline - Deliverables` |
| `Startup Kit - Backlog Seed` | `Baseline - Backlog` |
| `Startup Kit - Communications Plan` | `Baseline - Communications Plan` |
| `Startup Kit - Commercial Guardrails` | `Baseline - Commercial Guardrails` |
| `Startup Kit - RAID Log` | `Baseline - RAID Log` |
| `Startup Kit - Dependency and Assumption Log` | `Baseline - Dependency Log` |
| `Startup Kit - Contract Ambiguities` | `Baseline - Contract Clarifications` |
| Any G-01, checklist, or talent-onboarding source | Removed |
| `PM Best Practice` | Unchanged |

**Text cleanup.** After `sanitize_report_text`, remove every `ACTION_TAG_REGEX` match from copied text, then collapse whitespace and trim stray `;`, `,`, and `-` at either end. Keep `[CONFIRMATION REQUIRED]` and `[UNASSIGNED - TO BE CONFIRMED]`; they keep the base 8 warning fill. Remove `ACTION_TAG_REGEX` from the base 8 highlighting rule.

## 4. Workstreams are the SOW phases (replaces base 4)

**Phase label.** Parse each milestone description with this pattern (case-insensitive):

```text
^\s*(?P<code>P\d+[a-z]?)\s+(?P<name>[^:]*?)\s*(?:accepted|completed|complete|approved|sign[- ]?off)?\s*:\s*(?P<scope>.+)$
```

- Workstream = `"{code} {name}"`, keeping the Kit's casing, for example `P1 Foundation` or `P2a Services and Data`.
- Milestone name = the text before the colon, for example `P1 Foundation accepted`.
- Milestone scope = the text after the colon.
- With no match, fall back to the base 4 keyword classifier for the workstream. Use the whole description as the name, and add the note `Workstream inferred from keywords - confirm`.

**Grouping and order**

- Milestones that share a phase code share a workstream.
- Workstreams and milestones are ordered by delivery sequence: planned start (section 5), then `external_date`, then natural sort of milestone ID. Never order by taxonomy.
- WBS level 1 numbers follow that order, so P1 is `1`, P2a is `2`, and so on.
- The recurring row (section 7.5) sits under a final workstream named `Project Management (ongoing)`.

The Schedule and RAID workstream dropdown lists the phase workstreams plus `Project Management (ongoing)`, `Multiple phases`, and `Cross-phase`. The keyword taxonomy is used only as a fallback and to pick deliverable templates (section 7.3). It is never shown as a workstream when a phase label exists.

## 5. Dates (replaces the base 5 Planned Start rule)

**Start Date.** Add an optional CLI argument `--start-date YYYY-MM-DD` and pass it through `run()`, `run_reingest()`, and `export_pmo_workbook(..., start_date=None)`.

- When given, it is the project Start Date, with basis `Provided`.
- Otherwise use the first Monday on or after `sow_awarded_date`, with basis `Assumed - first Monday after award; confirm`. With no award date, use the first Monday on or after the generation date.

**Week ranges.** Search the milestone description, then each `critical_path_assumptions` entry, for:

```text
weeks?\s+(\d+)\s*(?:–|—|-|to)\s*(\d+)   or   week\s+(\d+)
```

For weeks `a` to `b`:

- Planned Start = Start Date + 7 × (a − 1) days.
- Planned Finish = Start Date + 7 × (b − 1) + 4 days, which is the Friday of week `b`.
- Date Basis = `SOW estimate, weeks a–b`.

**Precedence of dates, per milestone**

1. `external_date` present: it is the External Commitment Date and the Planned Finish. The base 5 start rule gives the Planned Start. Basis `Contract date`.
2. Else a week range: dates as above. The External Commitment Date stays blank, because the SOW gives no contractual date.
3. Else all dates blank, Basis `To be confirmed`, and the note `Dates not stated in the SOW [CONFIRMATION REQUIRED]`.

`internal_buffer_date` is copied when present and never invented. Holidays are not modelled.

**Milestone predecessors.** When a milestone's `key_dependencies` or `critical_path_assumptions` contains "acceptance of", "completion of", "upon acceptance", or "after" followed by another milestone's phase code (for example "P2b begins upon acceptance of P2a"), set that milestone as the predecessor. That dependency entry is then treated as a schedule link, not a client prerequisite (section 7.2).

## 6. Mapping deliverables and backlog items (replaces base 6.1)

**Tokenizing.** Lowercase the text and replace `/` with a space. Split on anything other than letters, digits, and hyphens. Keep each hyphenated token and also add its parts (`micro-frontend` yields `micro-frontend`, `micro`, and `frontend`). Strip a trailing plural `s` (and `ies` to `y`). Drop tokens shorter than 3 characters, numbers, and these stop words: `the and for with of to a an in on at by from or as is are be phase phases milestone milestones deliverable deliverables delivery project client built toptal accepted completed complete est week weeks related output outputs result results report reports work`.

**Weighted overlap.** `score(item, milestone)` = sum of IDF weights of tokens shared by the item and the milestone scope, divided by the sum of IDF weights of the item's tokens. IDF is `ln((N + 1) / df)`, where `N` is the number of milestones and `df` is the number of milestone scopes containing the token.

**Deliverable to milestone.** Apply in order; the first match wins and is written to Mapping Basis.

1. **Phase code.** The deliverable name contains a phase code (`P2b`) or `Milestone N`. Basis `Phase code`.
2. **ID mention.** The deliverable ID appears in a milestone's description, key dependencies, or critical path assumptions. Basis `Referenced by milestone`.
3. **Scope match.** The highest `score` against the milestone scopes, if at least 0.20. Ties go to the earlier milestone. Basis `Scope match`.
4. **Backlog text match.** Map every work package first (next rule). Score the deliverable name against each work package title, with IDF computed across work package titles. If the best is at least 0.30, use that work package's milestone. Basis `Backlog match`.
5. **Submission date**, as base 6.1 rule 3. Basis `Submission date`.
6. **Fallback**, as base 6.1 rule 5. Basis `Unmapped - confirm milestone`.

`WorkPackageSeed.parent_deliverable_id` and `linked_milestones`, and every deliverable acceptance field, are not used for mapping (section 2, known upstream issue).

**Work package to milestone.** Use rules 1 (phase code in the title), 2, and 3 above. With no match, the work package goes to the fallback milestone.

**Work package to deliverable.** Within its milestone, score the work package title against each deliverable name mapped to that milestone, with IDF computed across those deliverable names plus the work package title. If the best score is at least 0.25, the work package belongs to that deliverable; ties go to the lower deliverable ID. Otherwise it goes to the milestone's `Other {phase} work` package (section 7).

When the work package's Kit `parent_deliverable_id` differs from where it lands, add the note `Baseline backlog lists parent {id}`.

## 7. WBS structure (replaces base 6, 6.2 to 6.4)

**Level 3 elements under each milestone, in order**

1. `Project Kickoff`, in the first milestone only (7.1).
2. `Client Prerequisites`, when the milestone has any (7.2).
3. Each mapped deliverable, by natural sort of ID (7.3).
4. `Other {workstream} work`, holding unmatched work packages, when there are any.
5. `{Milestone ID} Milestone Acceptance` (7.4).

### 7.1 Project Kickoff

Tasks finish on the Friday of week 1.

- One task per communications-plan item whose cadence is one-time (`One-time`, `Once`, `At kickoff`), named `{name} for {audience}`. It uses Source `Baseline - Communications Plan` and the item's owner.
- `Hold client kickoff meeting` (Delivery Manager). Omit it when a one-time item's name contains "kickoff" or "kick-off".
- `Confirm scope, milestones, and acceptance approach with the client` (Delivery Manager).
- `Confirm client approvers and escalation path` (Delivery Manager).
- `Agree status reporting format and cadence` (Talent PM).

### 7.2 Client Prerequisites

One task per milestone `key_dependencies` entry that is not a schedule link (section 5): `Confirm: {dependency}`. Owner Talent PM, finishing on the milestone Planned Start, with Source `Baseline - Milestone Plan`. These are the items the Talent PM must chase before the phase can start.

### 7.3 Tasks under a deliverable

**Work type.** Classify the deliverable name by counting keyword hits (word-start, case-insensitive). The highest count wins; ties follow the table order. With no hits, use Build.

| Work type | Keywords | Tasks (owner); `*` marks the core task |
| --- | --- | --- |
| Integration | integrat, api, endpoint, direct-write, interface, authentication | Confirm interface contract, credentials, and environment access (Talent PM) · `*` Build the integration (Talent PM) · Test error handling, retries, and performance targets (Talent PM) · Demo the working integration to the client (Delivery Manager) |
| Build | shell, service, frontend, micro-frontend, view, feature, component, search | Refine stories and acceptance criteria (Talent PM) · `*` Develop and configure (Talent PM) · Peer review and unit test (Talent PM) · Demo completed work to the client (Delivery Manager) |
| Test | test, suite, harness, uat, scan, validation, smoke, certification, defect, hardening, quality | Agree test scope, targets, and environment (Talent PM) · `*` Prepare test scripts, data, and fixtures (Talent PM) · Execute tests in the target environment (Talent PM) · Log defects and produce the results report (Talent PM) |
| Analysis | spike, parity, assessment, benchmark, report | Agree method, targets, and data sources (Talent PM) · `*` Perform the analysis (Talent PM) · Document findings and recommendations (Talent PM) · Review findings with the client (Delivery Manager) |
| Documentation | training, documentation, material, guide, runbook | Agree outline and audience (Talent PM) · `*` Draft the content (Talent PM) · Walk through the draft with the client (Delivery Manager) · Finalize and publish (Talent PM) |

**Tasks, in order**

1. The work type's tasks. If the deliverable has matched work packages, replace the `*` core task with one task per work package (title as name, Source `Baseline - Backlog`, Source ID the WP ID, owner from the work package), in `preliminary_sequence` order.
2. `Assemble acceptance evidence` (Talent PM). Put `evidence_required` in the Acceptance / Completion Criteria column, not the name.
3. `Internal quality review against acceptance criteria` (Delivery Manager).
4. Per-deliverable acceptance mode only (7.4): `Submit for client review` (Talent PM), `Address client feedback and rework` (Talent PM), `Obtain written client acceptance` (Delivery Manager).

The deliverable's level 3 row carries `acceptance_criteria` in Acceptance / Completion Criteria, with `evidence_required` appended after `Evidence:`. Its Notes carry `Work type: {type}`.

### 7.4 Milestone acceptance

**Acceptance mode** is decided once per project.

- **Milestone-level** when any milestone, deliverable acceptance field, communications-plan item, or RAID item mentions "Acceptance Review", "Milestone Sign-Off", or "end-of-milestone".
- **Per-deliverable** otherwise.

ARC is milestone-level.

The `{Milestone ID} Milestone Acceptance` package holds these tasks, all finishing on the milestone Planned Finish:

1. `Prepare milestone acceptance package and evidence` (Talent PM).
2. `Support client UAT for {Milestone ID}` (Delivery Manager). Include only when "UAT" appears in any milestone, assumption, or RAID text.
3. Each communications-plan item whose cadence is per milestone (`End of each Milestone`, `Per milestone`, `Each milestone`), named `{name} for {audience}`. With none, use `Hold milestone acceptance review with client approvers` (Delivery Manager).
4. `Address client feedback and rework` (Talent PM).
5. `Obtain milestone sign-off from the client's designated approvers` (Delivery Manager).
6. `Update schedule and RAID Log after acceptance` (Talent PM).

In per-deliverable mode, drop tasks 1, 3, and 4. Task 5 becomes `Confirm all {Milestone ID} deliverables are accepted`.

### 7.5 Ongoing project management

One `Recurring` row, `Ongoing Project Management & Reporting`, is the only level 2 element of the final workstream, `Project Management (ongoing)`. It runs from the Start Date to the last milestone's Planned Finish, with Source `PM Best Practice` and the note `Recurring activity, not a SOW milestone`. Its package `Reporting and Control` holds:

- Each communications-plan item whose cadence is recurring (daily, weekly, biweekly, monthly, as needed, or anything not one-time or per milestone): `{name} for {audience}`, with the cadence in the Cadence column.
- `Review and update the RAID Log` (Talent PM, Weekly).
- `Update schedule and WBS status` (Talent PM, Weekly).
- `Maintain the decision log` (Delivery Manager, As needed).
- `Raise change requests when triggers are met` (Delivery Manager, As needed), only when `commercial_guardrails.change_control_trigger` is present. The trigger text goes in Acceptance / Completion Criteria.

### 7.6 Predecessors (replaces the base 6.5 Predecessors rule)

- Tasks inside a Kickoff, Prerequisites, deliverable, Other-work, or Acceptance package chain sequentially.
- Recurring tasks have no predecessors.
- The first task of each deliverable package depends on the last Client Prerequisites task of its milestone, when one exists.
- `Prepare milestone acceptance package` depends on every deliverable package of its milestone.
- The milestone's level 2 row shows the milestone predecessor from section 5 as that milestone's WBS code.
- A work package's `dependency_references` are added only when they point to a work package in the same milestone.

### 7.7 Task dates

- Planned Start is the milestone Planned Start.
- Planned Finish is: the Friday of week 1 for kickoff tasks; the milestone Planned Start for prerequisites; `internal_buffer_date` if present, else the milestone Planned Finish, for deliverable and other-work tasks; and the milestone Planned Finish for acceptance tasks.

## 8. RAID Log changes (amends base 7)

**Distrust default-filled links.** When at least 4 items across `raid_items` and `dependencies_assumptions` have a `linked_milestone`, and at least 75% of them share one value, treat that value as a default fill. Ignore it for all of them, and log it once at INFO.

**Linking, in order**

1. A non-default `linked_milestone` that names a milestone.
2. `linked_deliverable` names a deliverable; use its milestone.
3. Phase codes (`P2a`) and `Milestone N` references in the description and linked fields. `Milestone N` maps to the milestone whose ID number is `N`. Every phase mentioned is linked.
4. A milestone or deliverable ID mentioned as a whole word.
5. None.

**Columns.** Linked Milestone becomes a comma-separated list of milestone IDs, and Linked WBS Code the matching list of codes. Workstream is the linked phase, `Multiple phases` when more than one is linked, or `Cross-phase` when none is. The keyword classifier is not used on RAID items.

The final RAID columns are:

A RAID ID · B Type · C Description · D Category · E Workstream · F Linked Milestone · G Linked WBS Code · H Owner · I Probability · J Impact · K Severity · L Score (P x I) · M Trigger / Early Warning · N Mitigation / Response · O Due Date · P Status · Q Date Raised (generation date) · R Last Updated · S Linked Decision · T Linked Dependency / Assumption · U Source · V Source ID · W Notes

Contract ambiguities use Category `Contract Clarification`. The Linked Milestone data validation allows the comma list (error style `warning`).

## 9. Layout and text hygiene

**Title block, all tabs**

- Row 1: `{PROJECT NAME} - PROJECT SCHEDULE`, `- WORK BREAKDOWN STRUCTURE`, or `- RAID LOG`.
- Row 2: `Client: {client} | Contract: {contract_type} | Talent PM: {talent_pm} | Delivery Manager: {delivery_manager}`.
- Row 3: `Start Date: {date} ({basis}) | Generated {YYYY-MM-DD} from the project baseline`.
- Row 4, Schedule: "Planned dates are estimated from the SOW week ranges and the Start Date. External Commitment Date is shown only where the SOW states a date."

**Project Schedule columns** (replaces the base 5 table)

| Col | Header | Content |
| --- | --- | --- |
| A | WBS Code | Matches the WBS |
| B | Row Type | `Workstream`, `Milestone`, `Recurring` |
| C | Workstream | Phase workstream (section 4) |
| D | Milestone ID | Kit milestone ID |
| E | Milestone | Text before the colon |
| F | Milestone Scope | Text after the colon, without the week-range parenthetical |
| G | Owner | Normalized owner |
| H | Planned Start | Section 5. Workstream rows: MIN over children. |
| I | Planned Finish | Section 5. Workstream rows: MAX over children. |
| J | Internal Buffer Date | Copied when present |
| K | External Commitment Date | `external_date` only |
| L | Date Basis | `Contract date`, `SOW estimate, weeks a–b`, or `To be confirmed` |
| M | Duration (working days) | `=IF(OR(H6="",I6=""),"",NETWORKDAYS(H6,I6))` |
| N | Days to Finish | `=IF(OR(AND(K6="",I6=""),O6="Complete"),"",IF(K6<>"",K6,I6)-TODAY())` |
| O | Status | Dropdown, as base 5 |
| P | Health | `=IF(O6="Complete","Complete",IF(AND(K6="",I6=""),"Date TBC",IF(TODAY()>IF(K6<>"",K6,I6),"Overdue",IF(AND(J6<>"",TODAY()>J6),"In Buffer","On Track"))))` |
| Q | Predecessor | Milestone ID from section 5 |
| R | Client Prerequisites | `key_dependencies` that are not schedule links, joined with `; ` |
| S | Critical Path Assumptions | Joined with `; ` |
| T | Linked Deliverables | Deliverable IDs |
| U | Linked RAID IDs | RAID IDs |
| V | Source | Source value |
| W | Notes | De-duplicated auto-flags |

The timeline starts at column X, and its span test uses `$H` and `$I`. Finish-week marker: navy. Buffer-week marker (J): accent blue. Freeze panes at `F6`, and autofilter `A5:W{last_row}`.

**WBS columns:** as base 6.5 without Linked Action ID: A WBS Code · B Level · C Element Type · D Name · E Workstream · F Milestone ID · G Deliverable ID · H Source ID · I Owner · J Planned Start · K Planned Finish · L Milestone Finish · M Status · N % Complete · O Cadence · P Predecessors · Q Acceptance / Completion Criteria · R Linked RAID IDs · S Source · T Mapping Basis · U Notes.

**Text hygiene**

- Task names are at most 120 characters and never contain Kit acceptance text (`evidence_required`, `review_window`, `rejection_rework_path`, approver names). Kit text of that kind goes to Acceptance / Completion Criteria or Notes. Kit backlog titles and communications-plan names longer than 120 characters are cut at a word boundary with `...`, with the full text in Notes.
- Notes are de-duplicated before joining with `; `.
- Owner placeholders `Unassigned` and `[UNASSIGNED - TO BE CONFIRMED]` display as `[UNASSIGNED - TO BE CONFIRMED]`, with the warning fill and a single `Owner unassigned` note.

## 10. Tests and acceptance (amends base 9)

**New fixture `arc_baseline`.** Build it from the data in Appendix A: 4 milestones with their descriptions, critical path assumptions, and key dependencies; 19 deliverables; 15 work packages whose `parent_deliverable_id` values are the wrong ones listed in Appendix A; and a communications plan containing a one-time kickoff item, a per-milestone acceptance review, and five recurring items. Also populate `sow_awarded_date = 2026-09-29`, `commercial_guardrails` with a change-control trigger, RAID items, and a Dependency Log whose `linked_milestone` is `M1` on all 12 entries. Populate the readiness fields listed in section 3 with marker text.

**New tests**

- `test_no_readiness_content.py`: scan every cell, sheet name, defined name, and workbook property. Assert no case-insensitive match for `readiness`, `G-01`, `G01`, `gate approval`, `Startup Kit`, `mobiliz`, or `ACT-` followed by a digit. Headers and builder-generated text must also not contain `startup` as a whole word. No readiness marker text appears.
- `test_phases.py`: phase label parsing, ordering, week-range parsing (en dash, hyphen, and "to"), Start Date default and `--start-date` override, and predecessor detection.
- `test_mapping_v2.py`: every mapping in Appendix B, including DEL-18 via `Backlog match` and the `Baseline backlog lists parent` notes.
- `test_acceptance_mode.py`: milestone-level mode for `arc_baseline`; per-deliverable mode when no acceptance-review wording exists.
- `test_raid_links.py`: default-fill detection ignores the `M1` links; RAID items mentioning several phases get `Multiple phases`.

**Acceptance criteria to replace in base 9**

- `minimal_baseline` produces a valid workbook with `MS-TBC`, the `Project Management (ongoing)` workstream, and the empty-RAID row.
- The Schedule's milestone IDs equal the baseline milestone IDs, in delivery order, with no additions.
- Every deliverable appears exactly once at WBS level 3. Every milestone has a Milestone Acceptance package.
- `arc_baseline` output matches Appendix B exactly.

## 11. Implementation notes for the coding agent

1. Apply on top of the implemented base spec. Remove all dead code for PM-01, PM-02, mobilization, checklist tasks, action IDs, and taxonomy-ordered grouping; do not leave it behind flags.
2. Add `--start-date` to `main.py` and the README CLI table.
3. Re-run the full suite and the mock commands. Then run `--reingest-docx` against the ARC Startup Kit, if it is available locally, with `--start-date 2026-10-05`, and compare the result with Appendix B.
4. Report the acceptance checklist with pass or fail per item, and list any Appendix B values your output differs from, with the reason.

## Appendix A: ARC Genomics baseline data for the fixture

**Milestones** (Start Date 2026-10-05)

| ID | Description | Critical path assumptions (week-range entry) | Key dependencies |
| --- | --- | --- | --- |
| M1 | P1 Foundation accepted: micro-frontend shell, Azure AD/MSAL authentication, E2E test harness, and Client-built pipeline, data model and governance validation completed (est. weeks 1–6). | Schedule is estimated from the Start Date, with P1 running weeks 1–6 | Client design system access (code library, tokens, design files, guidelines, named contact) by the start date; Client IdP team availability for Azure AD / MSAL authentication; Client-owned stories and code dependencies completed before dependent Toptal work begins; Coding and delivery documentation standards provided on or before the start date |
| M2 | P2a Services and Data accepted: FastAPI search and async services, OneGWAS integration, performance spike, and Client-built data ingestion validation completed (est. weeks 7–16). | P2a begins upon completion of HS-4781; P2a runs weeks 7–16 from the Start Date | Client completion of HS-4781 (Snowflake schema) before P2a begins; Client-built data ingestion and migration completed before related validation; Domain users and domain experts for trait taxonomy available; Cogen API available and stable at about 95% |
| M3 | P2b Application Surface accepted: ARC micro-frontend search and detail views, haplotype features, nomenclature service, and related test suites completed (est. weeks 17–21). | P2b begins upon acceptance of P2a; P2b runs weeks 17–21 from the Start Date | Acceptance of P2a before P2b begins; Client UI/UX designs for Milestone 3 screens provided by the start date; Client design system access and advance notice of design-system changes |
| M4 | P3 Launch accepted: integration, performance, security and cross-browser testing, UAT, hardening, production smoke tests with 48-hour defect watch, and training materials completed (est. weeks 22–26). | P3 begins upon acceptance of P2b; P3 runs weeks 22–26 from the Start Date | Acceptance of P2b before P3 begins; Client scientist UAT groups available; Client maintains development, staging and production environments; Client remediation of defects in Client-built components |

**Deliverables:** DEL-01 Micro-frontend shell · DEL-02 Azure AD / MSAL authentication integration · DEL-03 Shell and authentication E2E test harness · DEL-04 Pipeline quality gates and deployment smoke checks · DEL-05 Authentication negative-test suite and security scan results · DEL-06 FastAPI search, detail and async query services with backend tests · DEL-07 Performance engineering spike output · DEL-08 OneGWAS direct-write integration and E2E/retry tests · DEL-09 Client-built data tier validation scripts, results and defect reports · DEL-10 ARC micro-frontend faceted search, results table and detail view · DEL-11 Haplotype filter, comparison, and API endpoints · DEL-12 Nomenclature service and test suite · DEL-13 P2b frontend and haplotype test suites · DEL-14 Integration, performance, security and cross-browser test suites with test data · DEL-15 UAT execution records and defect log · DEL-16 Pre-launch hardening iteration results · DEL-17 Production smoke test results and 48-hour defect watch report · DEL-18 MTA Store parity and usage-zero confirmation report · DEL-19 Training materials and user documentation

**Work packages (with the Kit's incorrect parent):** WP-01 Micro-frontend shell and Azure AD/MSAL authentication (DEL-01) · WP-02 Shell E2E harness and authentication security testing (DEL-01) · WP-03 P1 certification testing of Client-built pipeline, data model and governance (DEL-01) · WP-04 FastAPI search/detail endpoints and async query processing (DEL-02) · WP-05 Performance spike and backend integration/load testing (DEL-02) · WP-06 OneGWAS direct-write integration and tests (DEL-02) · WP-07 P2a certification testing of Client-built data ingestion and migration (DEL-02) · WP-08 ARC faceted search, results table and result detail view (DEL-03) · WP-09 Haplotype filter, comparison, search endpoints and API (DEL-03) · WP-10 Nomenclature service (DEL-03) · WP-11 P2b frontend, haplotype and nomenclature test suites (DEL-03) · WP-12 Test data, fixtures and full integration/performance/security/cross-browser suites (DEL-04) · WP-13 UAT execution and pre-launch hardening (DEL-04) · WP-14 Production smoke tests, 48-hour defect watch and MTA Store parity check (DEL-04) · WP-15 Training materials and user documentation (DEL-04)

**Communications plan:** COM-01 Kickoff Call (One-time) · COM-02 Daily Standups (Daily) · COM-03 Biweekly Sprint Demo (Biweekly) · COM-04 Weekly Status Meeting (Weekly) · COM-05 Weekly Status Report (Weekly) · COM-06 Milestone Acceptance Review (End of each Milestone) · COM-07 Ad-Hoc Working Sessions (As needed)

## Appendix B: Expected ARC Genomics result

These values were produced by running the section 6 and 7.3 rules on the Appendix A data, and are what the tests assert.

**Project Schedule**

| WBS | Workstream | Milestone | Planned Start | Planned Finish | Date Basis | Predecessor |
| --- | --- | --- | --- | --- | --- | --- |
| `1` / `1.1` | P1 Foundation | M1 P1 Foundation accepted | 2026-10-05 | 2026-11-13 | SOW estimate, weeks 1–6 | |
| `2` / `2.1` | P2a Services and Data | M2 P2a Services and Data accepted | 2026-11-16 | 2027-01-22 | SOW estimate, weeks 7–16 | |
| `3` / `3.1` | P2b Application Surface | M3 P2b Application Surface accepted | 2027-01-25 | 2027-02-26 | SOW estimate, weeks 17–21 | M2 |
| `4` / `4.1` | P3 Launch | M4 P3 Launch accepted | 2027-03-01 | 2027-04-02 | SOW estimate, weeks 22–26 | M3 |
| `5` / `5.1` | Project Management (ongoing) | Ongoing Project Management & Reporting | 2026-10-05 | 2027-04-02 | | |

M2's "begins upon completion of HS-4781" names a client story, not a phase, so it stays a client prerequisite and M2 has no milestone predecessor. External Commitment Date is blank on every row.

**Deliverable mapping, work type, and matched work packages**

| Milestone | Deliverable (basis, work type, work packages) |
| --- | --- |
| M1 | DEL-01 (Scope match, Build, WP-01) · DEL-02 (Scope match, Integration) · DEL-03 (Scope match, Test, WP-02) · DEL-04 (Scope match, Test) · DEL-05 (Scope match, Test) · DEL-09 (Scope match, Test) |
| M2 | DEL-06 (Scope match, Build, WP-04) · DEL-07 (Scope match, Analysis, WP-05) · DEL-08 (Scope match, Integration, WP-06) |
| M3 | DEL-10 (Scope match, Build, WP-08) · DEL-11 (Scope match, Integration, WP-09) · DEL-12 (Scope match, Test, WP-10) · DEL-13 (Phase code, Test, WP-11) |
| M4 | DEL-14 (Scope match, Test, WP-12) · DEL-15 (Scope match, Test) · DEL-16 (Scope match, Test, WP-13) · DEL-17 (Scope match, Test, WP-14) · DEL-18 (Backlog match via WP-14, Analysis) · DEL-19 (Scope match, Documentation, WP-15) |

Other-work packages: `Other P1 Foundation work` holds WP-03, and `Other P2a Services and Data work` holds WP-07. Unmapped deliverables: 0.

**Task counts** (milestone-level acceptance mode)

| Package type | Count | Tasks |
| --- | --- | --- |
| Project Kickoff (M1) | 1 | 4 (COM-01 replaces "Hold client kickoff meeting") |
| Client Prerequisites | 4 | 13 (M1 4, M2 4, M3 2, M4 3) |
| Deliverables | 19 | 114 (6 each: 4 work-type tasks, with the core replaced by a work package where matched, plus 2 evidence and review tasks) |
| Other work | 2 | 2 |
| Milestone Acceptance | 4 | 24 (6 each, with COM-06 as the review task and UAT support included) |
| Reporting and Control | 1 | 9 (COM-02, 03, 04, 05, 07, plus 4 standard) |
| **Total** | | **166 tasks** |

**RAID Log spot checks:** 34 rows, as in the current output. The dependency-log `M1` links are ignored as default fill. RAID-09 (HS-4781 before P2a) links to M2. RAID-10 and RAID-16 (sequencing across all phases) show `Multiple phases`. RAID-01 (Cogen API availability) shows `Cross-phase`. No row has a Linked Action ID column.
