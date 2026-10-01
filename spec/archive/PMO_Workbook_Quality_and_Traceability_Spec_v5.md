# Quality and Traceability Spec v5: Startup Kit, Readiness Checklist, and Project Delivery Workbook

September 30, 2026

## 1. Purpose and precedence

This spec reviews the third ARC Genomics Platform run, produced after v4 Parts A and B were implemented (generator v0.5.3; all three files generated 23:50):

- `ARC_Genomics_Platform_Startup_Kit.docx` (the Kit)
- `ARC_Genomics_Platform_Startup_Readiness_Checklist.docx` (the Checklist)
- `ARC_Genomics_Platform_Project_Delivery_Workbook.xlsx` (the Workbook)

It verifies v4, re-assesses quality and traceability, and specifies the remaining fixes.

**Precedence.** This document amends the base spec, v2, v3, and v4. Where they conflict, this document wins; everything else stands. Part A (Workbook) and Part B (Kit and Checklist) are both in scope, because v4 Part B was implemented at your instruction.

**This run was again a fresh extraction.** It produced 19 deliverables (previously 20); DEL-03 now bundles five SOW stories. It also produced 9 RAID items (7 risks, 2 issues), 10 dependencies and assumptions, and 21 open questions. The run-2 regression fixture (`arc_run2`) stays as-is, and this run becomes `arc_run3` (A27).

## 2. v4 verification

| v4 item | Result | Status |
| --- | --- | --- |
| A14 Phase order and strong backlog match | All 19 deliverables are in the correct phase. Work packages now map 1:1 to deliverables, so phase-order detection correctly does not trigger. | Pass |
| A15 Sequential-gate predecessors | M2←M1, M3←M2, M4←M3 | Pass |
| A16 Contract Reference fallback | Populated where the text cites stories or sections (AMB-02, 03, 05, 06, 07, 09, 15; Q-06). `Not cited` on 8 ambiguities. Open-question rows without references are blank rather than `Not cited`. | Pass, minor inconsistency |
| A17 Story links | RAID-21 → DEL-05, 07, 13, 14; RAID-22 → DEL-03; RAID-26 → DEL-15; RAID-28 → DEL-17, 18; RAID-34 → DEL-04, 05, 06; deliverable rows carry the back-links. RAID-21 links deliverables in three phases but shows `Cross-phase` with no milestone. | Partial |
| A18 Owner normalization | RAID-08 (ISS-01) normalized, with the note | Pass |
| A19 Decision links | 7 rows linked (DEC-09, 10, 12, 13) | Pass |
| A20 Regression fixtures | Not visible in the files; confirm from the test run | Unverified |
| B1 Evidence merge | No evidence now belongs to another deliverable (0 flags). But 10 of 19 deliverables lost their evidence (placeholder), and two carry blended evidence: DEL-05 includes the spike's benchmarks and tuning backlog, and DEL-16 includes the UAT records. | Partial: accuracy fixed, completeness lost |
| B2 Dependency links | No default links | Pass |
| B3 Decision IDs | DEC-01 to DEC-15, unique | Pass |
| B4 Backlog parents | Parents are real deliverable IDs, but the backlog is now a 1:1 copy of the deliverable list: 19 work packages titled `Work Package: <deliverable name>`, with no decomposition and an empty SOW Stories column | Over-corrected |
| B5 Kit IDs | RSK-01 to 07, ISS-01 to 02 with Probability and Impact; COM-01 to 07; the Workbook uses them as Source ID | Pass |
| B6 Truncated text | `SLA Met (Yes)` and bracketed text intact | Pass |
| B7 Ambiguities in the Kit | "Contract Ambiguities Logged" row present, but an unrelated `[ACT-09: ...design-system components...]` tag is attached to it | Pass, minor defect |
| B8 Checklist evidence | G01-14 (15 ambiguities, Review Required), G01-11 (actual meeting names), G01-03 (Review Required), and G01-02 are fixed. Still missing: the M1 date question, and the Fixed Bid commercial guardrails are still generic ("Labor rate realization", "Periodic Invoicing / Burn Tracking", "rework effort > 10% of deliverable budget"). | Partial |
| B9 SOW stories | 35 story IDs across the 19 deliverables. Work packages have none. | Partial |
| B10 Extraction stability | IDs follow the SOW order within this run, but the deliverable set and granularity still change between runs (20 → 19) | Partial |

## 3. Quality assessment

| Artifact | Overall | Strengths | Remaining defects |
| --- | --- | --- | --- |
| Workbook | Good; correct structure and mapping, with clear links to the Kit and Checklist | Correct phases, dates, predecessors, and mapping; all Kit and Checklist IDs carried as Source IDs; story-based RAID-to-deliverable links; no readiness or PM-workstream content; 149 tasks with role owners | Tasks named `Work Package: <deliverable>` repeat their parent; the 35 SOW stories are not visible anywhere in the WBS; 10 deliverables lack evidence; RAID-21 not linked to its three phases; mapping basis `Backlog match` is circular now that work packages copy deliverables |
| Kit | Strongly improved | IDs on every register; probability and impact on risks; SOW stories on deliverables; unique decisions; intact text | Degenerate backlog; 10 deliverables with placeholder evidence; the same 10 show "5 business days" review windows, which contradicts the Kit's own statement that no review window is stated; two blended evidence rows; misplaced action tags (DEL-01's owner action sits in its Acceptance Criteria cell; ACT-09 sits on the ambiguities row) |
| Checklist | Mostly accurate | Gate evidence now matches the Kit; counts consistent (19 deliverables, 9 RAID, 10 dependencies, 15 ambiguities, 21 questions) | No M1 date question; generic Fixed Bid guardrails |

## 4. Traceability assessment

| Element | Kit | Checklist | Workbook | Status |
| --- | --- | --- | --- | --- |
| Milestones | M1–M4 | G01-04; Q-16 to Q-18 | M1–M4 | Traceable (no M1 date question) |
| Deliverables | DEL-01–19 | G01-03 (19) | DEL-01–19 | Traceable |
| SOW stories | 35 on deliverables; none on work packages | Cited in ambiguities and questions | Used for RAID links only; not shown in the WBS or Schedule | One-way (A21, A22) |
| Work packages | WP-01–19, 1:1 copies | — | Tasks named `Work Package: ...` | Traceable but adds no information (A24, B13) |
| Risks and issues | RSK-01–07, ISS-01–02 | G01-05 (9) | RAID-01–09, Source ID set | Traceable |
| Dependencies and assumptions | DEP-01–08, ASM-01–02 | G01-05 (10) | RAID-10–19 | Traceable |
| Contract ambiguities | Count row (15) | AMB-01–15 | RAID-20–34 | Traceable |
| Open questions | — | Q-01–21 | Q-01–18 (role questions excluded) | Traceable |
| Decisions | DEC-01–15 | — | Linked Decision on 7 rows | Traceable where linked |
| Communications | COM-01–07 | G01-11 names | COM-06 in acceptance packages | Traceable |

**Overall.** Every register now carries IDs, and all counts agree across the three artifacts. The remaining gaps are:

1. The SOW stories, the finest-grained contractual unit, reach the Workbook only indirectly.
2. The backlog carries no information beyond the deliverable list.
3. Evidence is complete for only 9 of 19 deliverables.

## 5. Findings

| ID | Artifact | Finding | Evidence | Severity | Root cause | Fix |
| --- | --- | --- | --- | --- | --- | --- |
| H1 | Kit, Workbook | Backlog is a 1:1 copy of the deliverables; WBS tasks read `Work Package: Micro-Frontend Shell` under deliverable "Micro-Frontend Shell" | Kit backlog; WBS 1.1.2.2 and the equivalent task under every deliverable | High | B4 prompt change produced one work package per deliverable instead of a decomposition | A21, A24, B13 |
| H2 | Workbook | The 35 SOW story IDs are not shown in the WBS or Schedule | WBS has no story column | High | No column specified | A21, A22 |
| H3 | Kit, Workbook | 10 deliverables (DEL-03, 06, 09, 10, 11, 13, 15, 17, 18, 19) have placeholder evidence | Kit Deliverables matrix; WBS Acceptance column shows `[CONFIRMATION REQUIRED]` | High | B1 name matching (Jaccard at least 0.5) leaves items unmatched, and allows one acceptance item to serve two deliverables | B11 |
| H4 | Kit | DEL-05 evidence includes the performance spike's outputs, and DEL-16 includes the UAT records | Deliverables matrix | Medium | Same as H3: matching is not one-to-one | B11 |
| H5 | Kit | The 10 unmatched deliverables show review window "5 business days", while the Approval row states no review window is specified | Deliverables matrix vs SOW Interpretation "Approval & Acceptance Expectations" | Medium | Model default review window rendered as fact | B12 |
| H6 | Workbook | RAID-21 (AMB-02) links DEL-05, 07, 13, and 14 (M2, M3, M4) but shows `Cross-phase` with no milestone | RAID columns F to I | Medium | A17 only links a milestone when the deliverables share a single one | A23 |
| H7 | Workbook | Deliverable mapping basis reads `Backlog match (WP-01)`, which is circular because WP-01 copies DEL-01 | WBS column T | Low | A14 strong-match rule applied to degenerate work packages | A24 |
| H8 | Workbook | Open-question rows without references have a blank Contract Reference; ambiguity rows show `Not cited` | RAID column D | Low | A16 applied inconsistently | A25 |
| H9 | Workbook | Deliverables with no evidence show only `Evidence: [CONFIRMATION REQUIRED]` and no note | WBS Acceptance column | Low | No specific note | A26 |
| H10 | Kit | Action tags attached to the wrong cells: DEL-01 "Assign named delivery owner" in Acceptance Criteria; ACT-09 (design components) on the Contract Ambiguities Logged row | Deliverables matrix; SOW Interpretation | Low | Tag placement uses the wrong target cell | B14 |
| H11 | Checklist | No M1 date question; generic Fixed Bid guardrails | Questions Q-16 to Q-18; Guardrails table | Medium | B8 partly implemented | B15 |
| H12 | Kit | Deliverable granularity changes between runs (20 → 19; DEL-03 now bundles HS-4765, 4770, 4938, 4782, and 4941) | Run comparison | Medium | LLM extraction variance | B16 |

# Part A: Workbook changes

## A21. SOW stories as the core delivery tasks (amends v2 section 7.3 and v4 A14)

In each deliverable package, the `*` core task is replaced by the first applicable option:

1. **Non-degenerate work packages** (A24), one task each, as today.
2. **Otherwise, the deliverable's SOW stories**, one task per story ID in the order listed in the Kit:
    - Name: `{verb} {HS-ID}`, where the verb comes from the work type (Build and Integration: `Build`; Test: `Automate and execute`; Analysis: `Complete`; Documentation: `Produce`). When B13 supplies a story title, the name becomes `{verb} {HS-ID}: {story title}`.
    - Owner `Toptal Delivery Team`; Source `Baseline - SOW Stories`; Source ID is the story ID.
3. **Otherwise**, the template core task.

Degenerate work packages never become tasks. Their IDs are kept on the deliverable row in Source ID (for example `WP-01`).

## A22. SOW Stories columns

- WBS: add column **SOW Stories** after Source ID. Deliverable rows list all their story IDs; story tasks carry their own ID; other rows are blank.
- Schedule: add **SOW Stories** after Linked Deliverables, holding the milestone's story IDs in deliverable order, de-duplicated.
- Extend the A13 traceability self-check with a SOW stories line: stories in the baseline, stories in the WBS, and any missing.

## A23. RAID milestones from linked deliverables (amends v4 A17)

When a RAID row has linked deliverables, its Linked Milestone is the union of those deliverables' milestones, together with any milestones found by the v3 A4 rules. Workstream follows the v2 rule: one phase, `Multiple phases`, or `Cross-phase` when there are none. Linked WBS Code lists the deliverable codes when deliverables are linked.

## A24. Degenerate work packages

- A work package is **degenerate** when its title, after removing a leading `Work Package:` prefix, scores at least 0.80 against its parent deliverable's name (v2 weighted overlap), or when every deliverable has exactly one work package.
- Always strip a leading `Work Package:` (case-insensitive) from work package titles used as task names.
- A strong backlog match (v4 A14) against a degenerate work package does not count as evidence. When that is the only basis, use the next mapping rule, and never write `Backlog match` for it.
- A work package whose parent is a real deliverable and whose milestone comes from `linked_milestones` uses the basis `Backlog link`.

## A25. Contract Reference consistency

Every Contract Clarification and Open Question row shows Contract Reference, using `Not cited` when nothing is found. Other row types leave it blank.

## A26. Missing evidence note

When `evidence_required` is a placeholder, the deliverable row's Notes gains `Evidence not defined in baseline - agree with the client`, and its `Assemble acceptance evidence` task carries the same note.

## A27. Third regression fixture

Freeze `arc_run3` from this run's Kit and Checklist. Include the 19 deliverables with their SOW stories and the degenerate backlog. Assert the Appendix results. `arc_run1` and `arc_run2` must still pass.

# Part B: Kit and Checklist changes

## B11. One-to-one acceptance merge using story IDs (amends v4 B1)

1. Ask the acceptance extraction for each item's SOW story IDs, in the same way as B9.
2. Join acceptance items to deliverables in this order:
    1. Shared story IDs (the item and the deliverable share at least one).
    2. Name similarity (Jaccard, A2 tokenizer).
3. Make the assignment **one-to-one**: sort all candidate pairs by score, highest first, and assign greedily so that each deliverable receives at most one item and each item is used at most once. The story-ID join takes precedence over name similarity.
4. Lower the name threshold to 0.35 for pairs that share no story ID.
5. Log unmatched items and unmatched deliverables. A deliverable left unmatched keeps the placeholder evidence.

**Target on this SOW:** no blended evidence, and at least 17 of 19 deliverables with real evidence.

## B12. Review-window default

When no acceptance item matches a deliverable, set its review window to the SOW-level statement from "Approval & Acceptance Expectations" (for ARC: `Not specified; reviewed at the end-of-milestone Acceptance Review`). If that statement is also missing, use `Not specified [CONFIRMATION REQUIRED]`. Never render the model default "5 business days" unless the SOW states it.

## B13. Backlog from SOW stories (amends v4 B4)

- Extract a **SOW story catalogue**: story ID, title, phase, owner (Toptal or Client), and type (Build, Test, or Certification).
- Build the backlog from the catalogue: one work package per Toptal-owned story, whose parent is the deliverable carrying that story, whose `linked_milestones` is the story's phase milestone, and whose `sow_reference` is the story ID. Order by phase, then story ID.
- Populate the Scope Decomposition table's SOW Stories column. Titles never start with `Work Package:`.
- Client-owned stories (for example HS-4781) do not become work packages. They are listed in the External Dependencies row with their IDs.
- The docx parser reads the catalogue back from the backlog table.

With B13 in place, A21 option 1 applies, and every task is traceable to a SOW story.

## B14. Action-tag placement

- The "Assign named delivery owner" action is attached to the deliverable's Owner cell.
- The question-derived action on the Contract Ambiguities Logged row is removed; that row carries no action tag.
- Add a test asserting that each action tag appears in the column its action type targets.

## B15. Finish B8

- Generate the "no committed external delivery date" question for every undated milestone, including M1. Deduplicate against the Start Date question only if the Start Date question names that milestone.
- Fixed Bid guardrails: replace "Periodic Invoicing / Burn Tracking" with "Milestone-acceptance invoicing". Replace "Roster Locked & Rate Realization" with "Fixed scope; changes by Change Order". Remove "Labor rate realization" and "rework effort > 10% of deliverable budget" from the margin and escalation rows. Where a Fixed Bid value is a generic default, mark it `[Standard PMO guardrail - confirm]`.

## B16. Deliverable granularity

Define deliverables at the SOW's own grouping. Each SOW "Work Output" or phase activity group becomes one deliverable, and stories map to deliverables through the catalogue (B13). Add a check that no deliverable carries more than 5 stories unless the SOW groups them. When one does, log it for review. Keep recommending `--reingest-docx` for approved Kits.

# 6. Tests

- `test_story_tasks.py`: with degenerate work packages, deliverable packages contain one story task per story ID (35 in `arc_run3`); no task name starts with `Work Package:`.
- `test_sow_story_columns.py`: WBS and Schedule SOW Stories columns; the self-check reports 35 of 35.
- `test_raid_milestones_from_deliverables.py`: RAID-21 → M2, M3, M4 and `Multiple phases`.
- `test_degenerate_backlog.py`: detection; no `Backlog match` basis from degenerate work packages; `Backlog link` basis when applicable.
- `test_contract_reference_consistency.py`: every Contract Clarification and Open Question row is populated.
- `test_missing_evidence_note.py`: all 10 deliverables in `arc_run3`.
- `test_regression_fixtures.py`: runs 1, 2, and 3.
- Part B tests: one-to-one merge (no item used twice; a story-ID join beats name similarity); review-window default; story catalogue and backlog; action-tag placement; M1 date question; Fixed Bid guardrail text; the granularity check.

# 7. Appendix: Expected `arc_run3` Workbook results (Part A only)

- **Schedule.** Unchanged from this run: 4 phase workstreams, 2026-10-05 to 2027-04-02, M2←M1, M3←M2, M4←M3. The new SOW Stories column holds: M1 7 stories; M2 11; M3 10; M4 7.
- **Deliverables per phase.** M1: DEL-01, 02, 03. M2: DEL-04 to 08. M3: DEL-09 to 13. M4: DEL-14 to 19. No deliverable's basis is `Backlog match`.
- **Tasks.**

    | Package | Tasks |
    | --- | --- |
    | Client Prerequisites | 11 (M1 3, M2 3, M3 2, M4 3) |
    | Deliverables | 130 (19 × 5 template and closing tasks, plus 35 story tasks) |
    | Milestone Acceptance | 24 |
    | **Total** | **165** |

- **RAID.** 52 rows, unchanged. RAID-21 → M2, M3, M4 and `Multiple phases`. Every Contract Clarification and Open Question row has a Contract Reference or `Not cited`.
- **Evidence notes.** 10 (A26). Evidence flags: 0.
