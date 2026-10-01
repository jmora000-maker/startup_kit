# Quality and Traceability Spec v4: Startup Kit, Readiness Checklist, and Project Delivery Workbook

September 30, 2026

## 1. Purpose and precedence

This spec reviews the second ARC Genomics Platform run produced after v3 was implemented (all three files generated 2026-09-30 22:26):

- `ARC_Genomics_Platform_Startup_Kit.docx` (the Kit)
- `ARC_Genomics_Platform_Startup_Readiness_Checklist.docx` (the Checklist)
- `ARC_Genomics_Platform_Project_Delivery_Workbook.xlsx` (the Workbook, generator v0.5.2)

It verifies v3 against this output, re-assesses quality and traceability, and specifies the remaining fixes.

**Precedence.** This document amends the base spec, v2 (`PMO_Workbook_Delivery_Alignment_Spec_v2.md`), and v3 (`PMO_Workbook_Quality_and_Traceability_Spec_v3.md`). Where they conflict, this document wins; everything else stands.

- **Part A** (Workbook generator) is required.
- **Part B** (Kit and Checklist generation) remains optional and is implemented only when instructed. It now includes the confirmed root cause for the truncated text (B6).

**This run was a fresh extraction, not a re-ingest.** Deliverable names and IDs differ from the previous run: the previous DEL-04 (P1 certification) is now DEL-05, and DEL-04 is now the authentication negative-test suite. There are now 13 dependencies and assumptions (previously 11), 6 RAID items (previously 8), and 20 open questions (previously 21). So v3 Appendix B no longer describes the current Kit. It stays valid as a frozen regression fixture (A20).

## 2. v3 verification

| v3 item | Result in this Workbook | Status |
| --- | --- | --- |
| A1 Remove Project Management | 4 workstreams, one per phase; no PM workstream, recurring row, or kickoff package; 6 tasks in each Milestone Acceptance package | Pass |
| A2 Mapping accuracy | 19 of 20 deliverables correct. DEL-07 (backend integration and load test suites, a P2a item) sits under M3. WP-09 (ARC faceted search UI, P2b) sits under DEL-06 FastAPI in M2. | Partial |
| A3 Predecessors | M3←M2 and M4←M3 correct, and acceptance entries removed from prerequisites. M2 has none, although the Kit states milestones run sequentially. | Partial |
| A4 RAID linking | No default M1 links. DEP-02 links to M2, DEP-03 to M3, and ASM-01 to multiple phases. | Pass |
| A5 Role owners | All 154 tasks carry a role (Talent PM 113, Delivery Manager 26, Toptal Delivery Team 15). RAID-01, RAID-02, and RAID-06 show a bare `Unassigned`. | Pass, with a minor defect |
| A6 Per-milestone communications | COM-06 Milestone Acceptance Review appears in every acceptance package | Pass |
| A7 Contract clarifications | Descriptions are intact and readable. The Contract Reference column is empty on all 15 rows, because this run's citations have no `[V1] Exhibit ...` prefix. | Partial |
| A8 Open questions | 17 rows, Q-01 to Q-17; role questions Q-18 to Q-20 excluded; IDs match the Checklist | Pass |
| A9 Evidence flags | 11 flags (DEL-02, 03, 04, 06, 08, 09, 11, 12, 13, 14, 15), all genuine; the Kit defect is not yet fixed | Pass |
| A10 Task timing | Prerequisites due 2026-10-05; deliverable work finishes the Friday before the final week; acceptance runs in the final week | Pass |
| A11 Rating | Column renamed; `Rating from baseline` note on RAID-03 and RAID-04 | Pass |
| A12 Minor fixes | Level 3 Source ID blank; `List_Milestone_IDs` present | Pass |
| A13 Traceability self-check | Not visible in the files. Confirm from the CLI output. | Unverified |

## 3. Quality assessment

| Artifact | Overall | Improved since last run | Remaining defects |
| --- | --- | --- | --- |
| Workbook | Good; usable as the Talent PM's initial plan after the two mapping fixes | PM workstream gone; role owners; correct acceptance windows; readable contract clarifications; open questions present; no default M1 links | DEL-07 and WP-09 under the wrong phase; M2 predecessor missing; Contract Reference empty; 3 RAID owners not normalized; evidence inherited from the Kit still wrong for 11 deliverables |
| Kit | Rich content; the same data-integrity defects as before | Decision IDs now unique (DEC-01 to DEC-15). This may be extraction luck rather than a fix; B3 is not confirmed. | Evidence attached to the wrong deliverables (11 of 15 non-placeholder rows); backlog parent is still a phase index; RAID and communications rows have no IDs; trailing `)` and `]` still dropped (`SLA Met (Yes`, `Delivery Manager (Toptal`, `approvers [NAMES`); words removed from prose (`...re-test cycles ... is.`, `Not specified ; reviewed`); P2a contracted deliverables omit "backend integration and load tests", which the previous run included |
| Checklist | Unchanged | — | G01-14 still says "No contractual ambiguities flagged" beside AMB-01 to AMB-15; G01-11 still cites an MBR cadence that does not exist; G01-03 still Complete with every approver unconfirmed; still no date question for M1; commercial guardrails still generic |

## 4. Traceability assessment

| Element | Kit | Checklist | Workbook | Link | Status |
| --- | --- | --- | --- | --- | --- |
| Milestones | 4 (M1–M4) | G01-04; Q-15 to Q-17 (M2–M4) | 4 | ID | Traceable |
| Deliverables | 20 | Count only (20) | 20, 1 misplaced | ID | Traceable; placement fix A14 |
| Work packages | 15 | — | 15, 1 misplaced | ID | Traceable; placement fix A14 |
| Deliverable evidence | 20 rows, 11 misattached | — | Copied and flagged | ID, wrong content | Broken at the source (B1) |
| RAID risks and issues | 6, no IDs | Count only (6) | RAID-01 to 06, Source ID blank | None | One-way (B5) |
| Dependencies and assumptions | 13 (DEP-01–09, ASM-01–04) | Count only (13) | RAID-07 to 19 | ID | Traceable |
| Contract ambiguities | Not in the Kit | 15 (AMB-01–15) | RAID-20 to 34 | ID | Checklist to Workbook traceable; the Kit has no link (B7) |
| Open questions | — | 20 (Q-01–20) | 17 (Q-01–17) | ID | Traceable; role questions excluded by design |
| Decisions | 15 (DEC-01–15) | — | Not carried; Linked Decision blank | ID | One-way (A19) |
| Communications plan | 7, no IDs | G01-11 evidence does not match | COM-06 in acceptance; others not in the WBS by design | Generated ID | One-way (B5) |
| SOW story IDs (`HS-####`) | Cited in decisions, dependencies, and ambiguity notes; not on deliverables or work packages | Cited in 9 of 15 ambiguities and 2 questions | Present only inside description text | None | Gap: nothing links a RAID item to the deliverable it concerns (A16, A17, B9) |

**Overall.** Every structural element now traces by ID across the three artifacts, and the Workbook's self-consistency is high. The remaining gaps are:

1. Content-level: deliverable evidence (B1).
2. Kit RAID and communications rows without IDs (B5).
3. No SOW story traceability, which is the most useful link for a Talent PM. For example, AMB-08 concerns HS-4828 and HS-4943, which are the UAT and hardening deliverables, but nothing connects them.
4. Run-to-run instability: regenerating from the SOW renumbers deliverables, so any Workbook edits keyed to IDs break (B10).

## 5. Findings

| ID | Artifact | Finding | Evidence | Severity | Root cause | Fix |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | Workbook | DEL-07 "Backend integration and load test suites" under M3 (P2b); should be M2 (P2a) | WBS 3.1.2; Schedule M3 Linked Deliverables | High | This run's P2a contracted-deliverables text omits the item, while P2b mentions "backend haplotype integration tests", so the scope score favours M3 (1.00 vs 0.37). The Kit's own backlog puts the matching WP-06 in P2a. | A14 |
| G2 | Workbook | WP-09 "ARC faceted search and result detail UI" (P2b) placed under DEL-06 FastAPI in M2 | WBS 2.1.2.3 | High | The P2a text now says "FastAPI faceted search/filter/detail endpoints", so M2 and M3 tie and the earlier milestone wins | A14 |
| G3 | Workbook | M2 has no predecessor | Schedule column Q | Medium | M2's dependencies name HS-4781 only; the sequential-gate statements (ASM-01 "Milestones run in sequence ... Each milestone is an acceptance gate"; SOW summary "Each Milestone depends on acceptance of the previous one") are not used | A15 |
| G4 | Workbook | Contract Reference empty on RAID-20 to 34 | RAID column D | Medium | The citation-prefix regex matches only `[V1] Exhibit ...`; this run cites story IDs and sections inline (`HS-4828`, `Section 5`) | A16 |
| G5 | Workbook | RAID-01, RAID-02, and RAID-06 owner shows `Unassigned`, with no warning fill or note | RAID column I | Low | Owner cell became empty after the `[ACT-...]` tag was removed; not normalized | A18 |
| G6 | Workbook | Decisions not carried; Linked Decision always blank | RAID column T | Low | No decision linking | A19 |
| G7 | Kit | Evidence attached to the wrong deliverables. Examples: DEL-11 (faceted search UI) shows "UAT execution records and defect log"; DEL-13 (nomenclature) shows production smoke-test evidence; DEL-15 (launch test suites) shows training evidence | Deliverables matrix | High | Unchanged from v3 F9 | B1 |
| G8 | Kit | Backlog "Parent Deliv" is DEL-01 to DEL-04 by phase (WP-01–04 → DEL-01, WP-05–08 → DEL-02, and so on) | Scope Decomposition table | Medium | Unchanged from v3 F15. Consistent across both runs, so the Workbook can use it (A14) | B4 |
| G9 | Kit | Trailing `)` and `]` dropped, and words removed mid-sentence: `SLA Met (Yes`, `Delivery Manager (Toptal`, `Client Approver (Milestone Sign-Off`, `approvers [NAMES`, `...re-test cycles included after Client remediation of Certification failures is.`, `Not specified ; reviewed` | Charter, Stakeholder, Deliverables, SOW Interpretation tables | Medium | **Confirmed**, in `docx_generator.format_cell_with_action`: (1) `re.sub(r'[\s\:\-\—\(\)\[\]]+$', '', c_line)` strips every trailing bracket from every line; (2) `PLACEHOLDER_REGEX.sub('', line)` deletes case-insensitive words such as "pending", "undefined", "TBD", and "to be confirmed" from ordinary prose | B6 |
| G10 | Kit, Checklist | SOW story IDs appear throughout the text but are not attached to deliverables or work packages | Deliverables matrix; AMB table | Medium | Deliverable extraction does not capture story IDs | B9 |
| G11 | Kit | Fresh extraction changes content and numbering between runs. P2a lost "backend integration and load tests"; DEL-04 and DEL-05 swapped meaning; dependency count changed from 11 to 13 | Comparison with the previous run | Medium | LLM extraction variance | A20, B10 |
| G12 | Checklist | G01-14, G01-11, G01-03, and the missing M1 date question are all unchanged | Checklist table and questions | High | Hard-coded evidence (v3 F19 to F21) | B8 |
| G13 | Checklist | Q-18 to Q-20 ("... role is unassigned") are staffing questions mixed with delivery questions | Questions table | Low | Same list for both purposes | Handled in the Workbook by A8; no change needed |

# Part A: Workbook changes (required)

## A14. Backlog phase order and strong backlog matches (amends v2 section 6 and v3 A2)

**1. Phase-order detection.** Treat the Kit's work package `parent_deliverable_id` values as a phase index when all of these hold:

- the number of distinct parent IDs equals the number of milestones;
- ordered by `preliminary_sequence`, the parent IDs never decrease;
- the parent IDs are exactly the first `N` deliverable IDs in natural order.

When detected:

- Each work package's milestone is the milestone at the same position, in delivery order, as its parent ID among the distinct parents. Basis: `Backlog phase order`. This rule comes before phase-code and scope-match rules for work packages.
- Log at INFO once: `Backlog parents encode phases, not deliverables; using them as phase order.`
- Do not show the `Baseline backlog lists parent ...` note on those tasks, because the parent is not a deliverable claim.

When not detected, including after B4 is fixed, the v2 and v3 rules apply unchanged.

**2. Strong backlog match for deliverables.** Insert a new rule after v2 rule 2 (ID mention) and before rule 3 (scope match). Score the deliverable name against every work package title, with IDF across those titles. If the best score is at least 0.75 and that work package's milestone is known (from phase order, `linked_milestones`, or its own phase code), the deliverable takes that milestone. Basis: `Backlog match ({WP-ID})`.

**3. Work package to deliverable threshold.** Lower the threshold from 0.25 to 0.20.

**Verified on this run's data:** DEL-07 moves to M2 via WP-06 (score 0.80). WP-09 moves to M3 and attaches to DEL-11. WP-06 attaches to DEL-07, WP-08 to DEL-10, and WP-12 to DEL-14. All 20 deliverables and all 15 work packages land correctly. The same rules applied to the previous run's data (v3 Appendix B) produce the same results as before.

## A15. Sequential-gate predecessors (amends v3 A3)

After the v3 A3 rule, check the milestone key dependencies and critical path assumptions, the `dependencies_assumptions` descriptions, and the `sow_interpretation.assumptions` and `dependencies` entries for a sequential-gate statement:

```text
run[s]?\s+(?:sequentially|in\s+sequence)|sequential\s+(?:acceptance\s+)?gates?|each\s+milestone\s+(?:is\s+an\s+acceptance\s+gate|depends\s+on\s+(?:the\s+)?acceptance\s+of\s+the\s+previous)|after\s+the\s+prior\s+milestone\s+is\s+accepted
```

When one is present, every milestone after the first that still has no predecessor takes the previous milestone in delivery order as its predecessor, with the note `Predecessor from sequential-gate assumption ({source ID})`. Client prerequisites are unchanged. For M2, "HS-4781 before P2a begins" stays a prerequisite; the conflict between the two start conditions is already logged as AMB-01.

## A16. Contract Reference fallback (amends v3 A7)

When the v3 citation-prefix regex does not match, build Contract Reference from the references found in `conflicting_clauses`, in order of first appearance and de-duplicated:

- SOW story IDs matching `\bHS-\d{3,5}\b`;
- section references matching `\bSection\s+\d+(?:\.\d+)*\b`.

Format the result as `Stories: HS-4828, HS-4943 | Sections: 5, 6`, omitting an empty part. When both parts are empty, write `Not cited` and add the note `No clause reference in baseline`.

Apply the same extraction to open questions (RAID rows with Category `Open Question`), which also cite story IDs (Q-03 HS-4781, Q-12 HS-4788).

## A17. Story-ID links

Build a story index. Map every `HS-####` found in a deliverable's name, `acceptance_criteria`, `sow_reference`, or `source_reference.clause_or_slide`, and in each work package title and description, to that deliverable or work package.

- For each RAID row, look up every story ID in its Contract Reference or description. Add the matching deliverable IDs to a new RAID column **Linked Deliverables**, placed after Linked WBS Code.
- When a matched deliverable belongs to a single milestone and the row has no milestone link yet, link that milestone too.
- Add the RAID IDs to the WBS Linked RAID IDs column of those deliverable rows.

In the current Kit, deliverables carry no story IDs, so this produces no links until B9 is implemented. Implement it now, so the links appear as soon as the Kit supplies story IDs, and cover it with a fixture that includes them.

## A18. RAID owner normalization

Apply the v2 section 9 owner-placeholder rule to RAID rows. An owner that is empty, `Unassigned`, or a placeholder after tag removal becomes `[UNASSIGNED - TO BE CONFIRMED]`, with the warning fill and the note `Owner unassigned`.

## A19. Decision links

When a RAID row's `linked_decision` is empty, link decisions whose text shares a story ID with the row, or whose text scores at least 0.50 against the row's description (the v2 weighted overlap, with IDF across decision texts). Write the decision IDs to Linked Decision, comma-separated, at most 3, highest score first.

## A20. Regression fixtures for extraction variance

Keep two frozen fixtures, and require both to map with zero errors:

- `arc_run1`: v3 Appendix A.
- `arc_run2`: this run's Kit and Checklist (Appendix A below).

The mapping tests assert each fixture's expected table. They catch rule changes that fix one extraction and break the other.

Add a README note: generate the Workbook for an approved Kit with `--reingest-docx`, because regenerating from the SOW can renumber deliverables and work packages.

# Part B: Kit and Checklist fixes (implement only when instructed)

v3 items B1, B2, B4, B5, B7, and B8 are unchanged and still open. B3 (decision IDs) is unique in this run but not confirmed fixed; add the renumbering guard anyway. B6 now has a confirmed root cause, and B9 and B10 are new.

## B6. Truncated text: confirmed fix (`docx_generator.format_cell_with_action`)

1. Replace the trailing-strip line with one that removes only whitespace, colons, dashes, and **unbalanced** closing brackets. A `)` or `]` stays when its matching opener appears earlier in the line.
2. Apply `PLACEHOLDER_REGEX` only when it matches a bracketed token (`[TBD]`, `(TO BE CONFIRMED)`) or the entire cell text. Never remove bare words such as "pending", "undefined", or "to be confirmed" from sentences.
3. Add unit tests with these inputs, which must render unchanged: `SLA Met (Yes)`; `Delivery Manager (Toptal)`; `Client's designated approvers [NAMES TO BE CONFIRMED]`; `The number of re-test cycles is undefined.`; `Not specified (TBD); reviewed at the Milestone Acceptance Review`.

For the fourth input, the word "undefined" stays; only a bracketed placeholder may be replaced.

## B9. SOW story IDs on deliverables and work packages

- Extend the deliverables, acceptance, and scope decomposition prompts to return the SOW story IDs (`HS-####`) that each deliverable and work package covers, stored in `Deliverable.sow_reference` (comma-separated) and in a work package description suffix `Stories: HS-...`.
- Add a "SOW Stories" column to the Kit's Deliverables and Acceptance Matrix and Scope Decomposition tables, and read it back in `StartupKitDocxParser`.
- This enables A17 and gives every deliverable a direct link to the contract.

## B10. Extraction stability

- Assign deliverable IDs by first appearance in the SOW (story order), not by extraction order, so repeated extractions number the same deliverables the same way.
- After extraction, run a completeness check: every SOW story ID found in the source documents must appear in at least one deliverable or work package (once B9 is in place). Log missing stories as open questions.
- Document in the README that an approved Kit is the system of record and later runs should use `--reingest-docx`.

# 6. Tests

- `test_backlog_phase_order.py`: detection on and off; the WP-06, WP-08, WP-09, and WP-12 placements; no `Baseline backlog lists parent` note when detected.
- `test_strong_backlog_match.py`: DEL-07 → M2 with basis `Backlog match (WP-06)`; no change for deliverables whose best work package score is below 0.75.
- `test_sequential_predecessors.py`: M2←M1 from ASM-01, with the note; HS-4781 stays a prerequisite of M2.
- `test_contract_reference_fallback.py`: AMB-08 → `Stories: HS-4828, HS-4943`; AMB-02 → `Stories: HS-4781 | Sections: 5, 6`; AMB-05 → `Not cited` (6 of 15 ambiguities are `Not cited`).
- `test_story_links.py`: with a fixture that has story IDs on deliverables, AMB-08 links to the UAT and hardening deliverables.
- `test_raid_owner_normalization.py`: RAID-01, RAID-02, and RAID-06.
- `test_decision_links.py`: at least one AMB row links to a DEC by shared story ID or text.
- `test_regression_fixtures.py`: `arc_run1` and `arc_run2` both match their expected mappings exactly.
- Part B tests only when Part B is implemented, including the B6 string cases.

# 7. Appendix A: `arc_run2` fixture

Copy verbatim from this run's Kit and Checklist:

- 4 milestones and their descriptions;
- the 8 contracted-deliverables entries, including "P1 Foundation QA: ...", "P2a OneGWAS integration: ...", "P2a validation of Client-built data work: ...", and "P2b test suites: ...";
- 20 deliverables, including the misattached evidence;
- 15 work packages with their phase-index parents;
- 13 dependencies and assumptions;
- 6 RAID items;
- 15 decisions;
- 7 communications-plan items;
- 15 contract ambiguities;
- 20 open questions.

The milestone key dependencies are the Workbook's Client Prerequisites values plus the acceptance-of-previous-phase entries already recognized as schedule links:

- M1: design system and standards; IdP team; client pipelines and data model.
- M2: HS-4781; client ingestion and migration; domain users and experts.
- M3: P2a acceptance; UI/UX designs and design system.
- M4: P2b acceptance; UAT groups; environments.

# 8. Appendix B: Expected `arc_run2` results

**Schedule:** 4 workstreams (P1 Foundation, P2a Services and Data, P2b Application Surface, P3 Launch), with dates as the current output (2026-10-05 to 2027-04-02). Predecessors: M2←M1 (sequential-gate note citing ASM-01), M3←M2, M4←M3.

**Deliverable mapping**

| Milestone | Deliverables (basis) |
| --- | --- |
| M1 | DEL-01, DEL-02, DEL-03, DEL-04 (Scope match) · DEL-05 (Phase code) |
| M2 | DEL-06 (Scope match) · DEL-07 (Backlog match (WP-06)) · DEL-08, DEL-09 (Scope match) · DEL-10 (Phase code) |
| M3 | DEL-11, DEL-12, DEL-13 (Scope match) · DEL-14 (Phase code) |
| M4 | DEL-15 to DEL-20 (Scope match) |

**Work package placement**

WP-01→DEL-01, WP-02→DEL-02, WP-03→DEL-03, WP-04→DEL-04, WP-05→DEL-06, WP-06→DEL-07, WP-07→DEL-09, WP-08→DEL-10, WP-09→DEL-11, WP-10→DEL-12, WP-11→DEL-13, WP-12→DEL-14, WP-13→DEL-15, WP-14→DEL-17, WP-15→DEL-19. All have basis `Backlog phase order`, and there are no Other-work packages.

**Task counts**

| Package | Tasks |
| --- | --- |
| Client Prerequisites | 9 (M1 3, M2 3, M3 1, M4 2) |
| Deliverables | 120 (20 × 6) |
| Milestone Acceptance | 24 (4 × 6) |
| **Total** | **153** |

**RAID:** 51 rows (6 risks and issues, 13 dependencies and assumptions, 15 contract clarifications, 17 open questions). Every contract clarification has a Contract Reference or `Not cited`. RAID-01, RAID-02, and RAID-06 have the normalized placeholder owner.

**Evidence flags:** 11, unchanged: DEL-02, 03, 04, 06, 08, 09, 11, 12, 13, 14, 15.
