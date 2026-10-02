# PMO Startup Kit Generator: Consolidated Requirements Spec

Revision 11 · October 2, 2026

## 0. Document control

**This document is the single source of truth.** It replaces every earlier spec. Move these files to `spec/archive/` and do not implement from them:

- `PMO_Startup_Toolkit_Workbook_Spec.md` (base)
- `PMO_Workbook_Delivery_Alignment_Spec.md` (v1)
- `PMO_Workbook_Delivery_Alignment_Spec_v2.md`
- `PMO_Workbook_Quality_and_Traceability_Spec_v3.md` to `..._v7.md`

**How it changes.** Future changes edit this document in place. A change adds, edits, or retires a requirement by ID, increments the Revision, and lists the change in section 18. Never add an amending document. A requirement ID is never reused.

**Status legend**

- `Done`: implemented in v0.5.5. Verify it with its test; do not re-implement it.
- `Pending`: not yet implemented, or implemented and failing review.
- `New`: introduced by this revision.

**Format of a requirement.** Each requirement has an ID, a statement, a status, and the test that proves it, written as `Test:` followed by the test file. A test may cover several requirements.

## 1. Principles

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| P-01 | The Project Delivery Workbook is the Talent PM's initial delivery plan: a Schedule of SOW acceptance gates, a WBS for producing and accepting SOW deliverables, and a delivery RAID Log. | Done | INV suite |
| P-02 | The Workbook contains no startup-readiness content, no Project Management workstream, and no recurring PM row. PM tasks are allowed only inside a phase's packages. | Done | `test_no_readiness_content.py`, `test_no_project_management.py` |
| P-03 | No output contains resource hours, effort, FTE, capacity, allocation, utilization, rate, or cost data. Text copied from the SOW or baseline is exempt. | Done | `test_no_effort_columns.py` |
| P-04 | The same baseline always produces the same Workbook rows, IDs, and order. Only the generation date may differ. | Done | `test_determinism.py` |
| P-05 | Every feature works for any SOW: with story IDs, with other SOW identifiers, with synthetic references, or with no work items at all. Nothing requires story IDs. | Done | `test_no_story_sow.py`, `test_empty_catalogue.py` |
| P-06 | Invalid extraction output is repaired or rejected at the extraction boundary (section 4). It is never silently rendered, and downstream generators do not add their own workarounds for it. | New | `test_validation_layer.py` |
| P-07 | Changes are minimal. A change touches only the requirements it names. Any other change in a snapshot (section 3) is a regression unless explicitly approved. | New | Snapshot suite |
| P-08 | **No project-specific data in production code.** `src\` contains no SOW references, titles, phases, client names, or lookup tables for any particular SOW. Everything SOW-specific comes from extraction at run time, or from fixtures and oracles under `tests\`. | Done (verified Rev 4 round: `ARC_KNOWN_REF_TITLES` and hard-coded ARC phases removed in `b655c2f`; `git grep HS-4 -- src` empty) | `test_no_sow_literals.py` |

## 2. Outputs, CLI, and architecture

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| OUT-01 | Output flags `--export-tools`, `--kit`, `--checklist`, and `--all` are additive. With no output flag, only the Workbook is written. `--all` writes all four outputs: the Startup Kit, the Readiness Checklist, the Project Delivery Workbook, and the Talent Team Onboarding Deck. `--slides` writes the deck, together with its two sources (DECK-02). | Pending (`--slides` and the deck in `--all` are new in Rev 8) | `test_orchestrator_export.py` |
| OUT-02 | `OutputSelection.from_flags` and `RunResult` (`kit_path`, `checklist_path`, `workbook`, `slides_path`, `readiness_score`) are as originally specified. `run()` and `run_reingest()` take `outputs=`. | Pending (`slides` and `slides_path` are new in Rev 8) | `test_orchestrator_export.py` |
| OUT-03 | `docx_generator` exposes `write_kit_docx`, `write_checklist_docx`, and `_resolve_output_paths`. `write_docx` writes both documents. `write_documents` writes each document exactly once. | Done | `test_orchestrator_export.py` |
| OUT-04 | Re-ingest backs up the input `.docx` only when the Kit is selected and would overwrite it. A Workbook-only re-ingest never touches the input file, and logs that the Kit was not rewritten. | Done | `test_orchestrator_export.py` |
| OUT-05 | `--start-date YYYY-MM-DD` passes through `run()`, `run_reingest()`, and `export_pmo_workbook(..., start_date=None)`. | Done | `test_phases.py` |
| OUT-06 | The Workbook file is `{sanitize_filename(project)}_Project_Delivery_Workbook.xlsx`, written to the same folder as the Kit. A write failure raises `PermissionError` naming the path. | Done | `test_writer.py` |
| OUT-11 | **One file-name rule.** Every output (Kit, Checklist, Workbook, deck, trace manifest) uses the same `sanitize_filename` helper, which removes unsafe characters and collapses runs of spaces and underscores into a single underscore, so all files of a run share one prefix. Only one `sanitize_filename` exists in `src\`. | Pending (mock run: `Pfizer_Analytics__Cloud_Modernization_Startup_Kit.docx` vs `Pfizer_Analytics_Cloud_Modernization_Project_Delivery_Workbook.xlsx`) | `test_output_names.py` |
| OUT-07 | Package `src/generators/pmo_workbook/` contains `workstreams.py`, `task_library.py`, `mapping.py`, `rows.py`, `builder.py` (pure, no `openpyxl`), `writer.py`, and `styles.py`. `build_workbook_model(baseline, today, start_date)` is deterministic. | Done | `test_builder.py` |
| OUT-08 | `PMOWorkbookResult` has these fields: `file_path`, `schedule_rows`, `wbs_rows`, `task_rows`, `raid_rows`, `unmapped_deliverables`, `excluded_items`, `evidence_flags`, `traceability`, and `validation` (section 4). | Pending (`validation` is new) | `test_builder.py` |
| OUT-09 | The CLI prints the readiness summary on every run, with one path per file written. The `PROJECT DELIVERY WORKBOOK` summary prints only when the Workbook is written, and includes the traceability self-check, the evidence-flag count, and the validation findings. The `TALENT ONBOARDING DECK` block prints only when the deck is written (DECK-16). All blocks respect `NO_COLOR` and non-TTY output. | Done (validation line new) | `test_cli_reporter.py` |
| OUT-10 | The README documents every flag (including `--slides`, DECK-18), the default output, `--start-date`, `--llm-cache` (QA-01), and the advice to re-ingest an approved Kit rather than regenerate it from the SOW. | Pending (`--llm-cache`) | Manual |

## 3. Quality infrastructure

These requirements exist to stop fixed behaviour from breaking again. They are implemented before any other Pending requirement.

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| QA-01 | **Record and replay of LLM calls.** `ILLMClient.generate_structured` and `generate_text` pass through a caching wrapper. The cache key is SHA-256 of model ID, system prompt, prompt, and schema name. Entries are JSON files in `tests/fixtures/llm_cache/`. The mode is set by `--llm-cache {off,record,replay}` or `LLM_CACHE_MODE`, and defaults to `off` on the CLI and `replay` in tests. In `replay`, a missing key raises `LLMCacheMiss` naming the prompt; there is never a silent live call. | New | `test_llm_cache.py` |
| QA-02 | **Recorded SOW corpus.** Record full extractions for at least: ARC Genomics Platform; the repo's mock SOW; one SOW with no story IDs; and one SOW with numbered deliverables (`Deliverable 3.2` style). A synthetic SOW is acceptable where no real one is available. Each recording is a fixture set under `tests/fixtures/sow/{name}/`: inputs, LLM cache, and baseline JSON. | New | Fixture presence check |
| QA-03 | **Snapshots.** For each fixture, normalize the three generated artifacts to JSON and commit them under `tests/snapshots/{name}/`: Kit tables, Checklist tables, and Workbook rows per sheet. Normalizing excludes generation dates and timestamps. `pytest` fails on any difference. Snapshots change only through `pytest --update-snapshots`, and the commit message must name the requirement IDs that justify the change. **The coding agent never applies snapshot updates.** It writes proposed snapshots to `tests/snapshots_proposed/` and lists every difference with its requirement ID; a human reviews and promotes them in a separate commit. A snapshot difference with no Pending requirement behind it is a regression. | Pending (revised in Rev 2) | `test_snapshots.py` |
| QA-04 | **Invariant suite.** Every invariant in section 16 runs against every fixture snapshot, and against any output folder through `python -m src.tools.check_artifacts <folder>`. That command exits non-zero on any violation and prints the invariant IDs that failed. | New | `test_invariants.py` |
| QA-05 | **Prompt-change gate.** Any change to `src/llm/prompts.py`, a Pydantic extraction schema, or the aggregator re-records QA-02 for all fixtures. The resulting snapshot differences are reviewed and approved as a separate commit. Running the invariant suite against all fixtures is mandatory. A re-recording is never in the same commit as a code change, and is accepted only when every oracle check (QA-08) passes. | Pending (revised in Rev 2) | CI rule; documented in README |
| QA-06 | **Legacy fixtures.** `arc_run1` to `arc_run5` (frozen baselines from earlier reviews) stay as baseline-level fixtures for the Workbook builder. Their expected results move from spec appendices into snapshots. | New | `test_snapshots.py` |
| QA-07 | `test_story_phase_stability.py` asserts that every SOW work item in `arc_run3`, `arc_run4`, and `arc_run5` is placed in the same phase. Items are matched by reference, or by fingerprint (Jaccard of at least 0.6) for synthetic references. | Done (extend to run 5) | `test_story_phase_stability.py` |
| QA-08 | **Oracles.** Each QA-02 fixture has a hand-curated oracle, `tests/oracles/{name}.json`, written from the SOW by a person. It records: the gate count and phase names; every SOW reference and its phase; client-owned references; whether the SOW states an award date; and the minimum evidence coverage. Oracles are never generated or edited by tooling or by the coding agent. Re-recording cannot change them, so they catch errors that a regenerated snapshot would hide. The ARC oracle is in Appendix D. | New | `test_oracles.py` |
| QA-09 | **Over-extraction fixture.** A frozen fixture `arc_overextracted` holds a real 10-milestone ARC baseline: M1 to M10, with three acceptance-review restatements (P1, P2a, and P2b) and three P3 checkpoints (testing, UAT, smoke tests), as produced by the generator v0.5.5 run of 2026-10-01 10:12 (Appendix I). It is built by re-ingesting that run's Kit `.docx` when it is available, otherwise by transcribing Appendix I. It is stored as data under `tests\fixtures\`, never derived from another fixture, and a test asserts its 10 milestone IDs. The expected results: 4 gates, `M1 (+M2)`, `M3 (+M4)`, and `M5 (+M6)` merged (MS-04), and exactly 3 checkpoints, `CP-01` to `CP-03` (MS-05, VAL-01). `arc_run5` is retired: it was always a copy of `arc_run4` and never held 10 milestones. | Done (verified Rev 7 round) | `test_fixture_integrity.py` |
| QA-10 | **Agent reports are evidence, not claims.** Snapshot differences in a report come from an actual diff of `tests\snapshots` against `tests\snapshots_proposed`. Requirement definitions are quoted from this spec. Test totals come from plain `pytest -q` with no filter. Every "Verified" entry cites a test and a concrete output value; otherwise it is "Not verified". When a requirement cannot be met as written (for example, a fixture it names does not exist), the agent stops and reports it; it never redefines the requirement so that the current state passes. Requirement text in a report is copied mechanically: the report includes the raw output of `Select-String -Path spec\PMO_Startup_Kit_Consolidated_Spec.md -Pattern '^\| <ID> \|'` for each requirement it cites, never text written from memory. The report ends with the raw output of `git status` and `git --no-pager log --oneline -15`. | Pending (Rev 7 report contained invented Select-String output and invented example rows; reviews rely on snapshots and on commands run by a person) | Review |
| QA-11 | **The spec is tracked and read-only for agents.** `spec\PMO_Startup_Kit_Consolidated_Spec.md` is committed in git. Agents never modify anything under `spec\`; `git --no-pager log --oneline -- spec` shows only human commits. | Done (verified Rev 7 round) | Review, `git log -- spec` |

## 4. Extraction validation layer

A single module, `src/llm/validation.py`, runs after `BaselineAggregator` and before any document is generated. It returns a `ValidationReport` of findings. Each finding has an invariant ID, a severity (`repaired`, `warning`, or `error`), and a message.

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| VAL-01 | **Milestones are reconciled to SOW gates.** The gate count comes from, in order: an explicit statement ("four sequential milestones", "N milestones") in decisions, assumptions, or the SOW Interpretation; the phases listed in approver decision rights or a per-milestone communications item; or the distinct phase codes in the contracted deliverables. When more milestones were extracted than there are gates, restatements (`acceptance\s+review\|sign-?off\|gating\s+the\s+start`) merge into their gate, and within-phase checkpoints move to `baseline.interim_checkpoints` (`CP-NN`). Gates are renumbered `M1`–`MN` in delivery order. Each renumbered gate keeps its extracted ID, and any merged IDs, as provenance (for example `extracted_ids: ["M3", "M4"]`). The Kit, Checklist, and Workbook all use the renumbered IDs. Provenance appears in the Workbook Notes as `Extracted as M3; includes M4 (acceptance review and sign-off)`. RAID rows and questions that name an extracted ID are relinked to the renumbered gate, with the note `Refers to extracted M4 (now M2)`. When fewer milestones were extracted than there are gates, record a `warning` and add an open question naming the missing phase. | Done (verified Rev 7 round) | `test_validation_layer.py`, `test_gate_reconciliation.py` |
| VAL-02 | **Work packages are built after deliverables, from the work item catalogue (REF-03).** Every work package has an existing parent deliverable, a SOW reference that matches `SOW_REFERENCE_PATTERNS` or is synthetic, an owner that is not an action placeholder (default `Toptal Delivery Team`), and `linked_milestones` set to the gate of **its own work item's phase**, never to a default or first gate. Phase names in the reference field are rejected. Invalid LLM work packages are discarded and rebuilt from the catalogue. If the catalogue is empty even though the SOW lists scope, record an `error`. | Done (verified Rev 2 run, Appendix F) | `test_validation_layer.py`, `test_backlog_recorded.py` |
| VAL-03 | **IDs are unique.** Decisions, deliverables, work packages, and milestones are renumbered sequentially when IDs repeat or equal a model default. Linked references are updated. | Done for decisions; generalize | `test_validation_layer.py` |
| VAL-04 | **No default-filled links.** `linked_milestone` and `linked_deliverable` on dependencies and assumptions are set only when the item text names the target. They are never copied from the first milestone or deliverable. | Done | `test_validation_layer.py` |
| VAL-05 | **Award date provenance.** `sow_awarded_date` is set only when the SOW or the user supplies it. There is no `today - 1 day` fallback. When it is absent, record a `warning` and add an open question. Anything that depends on the award date is then undeterminable: the Kit's 1-Day SLA Status shows `Not determinable - award date not stated`, and G01-01 has status `Confirmation Required`, never `Complete` or `Met`. | Done (verified Rev 3 run, Appendix G) | `test_award_date.py` |
| VAL-06 | **One numbering system.** Deliverable SOW references hold references only. Phase context is stored separately as a phase name. "Milestone N" annotations are never written into Kit fields. | Done | `test_validation_layer.py` |
| VAL-07 | **Visible findings.** `error` findings add an exception to Checklist G01-03 (scope and backlog) or G01-04 (milestones), and print in the CLI summary. `repaired` and `warning` findings print in the CLI summary and are listed in `PMOWorkbookResult.validation`. | Pending | `test_validation_layer.py` |
| VAL-08 | **Work package titles** are the SOW work item's own title from the catalogue. A title is never `{deliverable name} implementation task` or any other generated filler. When the catalogue has no title, the title is `{reference}: {deliverable name}`, and the work package is flagged degenerate (MAP-06). No two work packages share an identical title. | Done (verified Rev 2 run, Appendix F) | `test_validation_layer.py` |
| VAL-09 | **Catalogue phases.** Every catalogue item has a phase that matches a gate. Phases come from the SOW's phase grouping (for example, the contracted-deliverables list or Work Output tables), never from a default. Items whose phase cannot be determined are recorded as a `warning` and left unphased, not assigned to the first gate. | Done (verified Rev 2 run, Appendix F) | `test_validation_layer.py` |
| VAL-10 | **Contract ambiguity citations.** Every contract ambiguity's `conflicting_clauses` includes a citation: a document and section, a SOW reference, or a section number. When the LLM output lacks one, fill it from the item's `source_reference` (document and clause) when available. Otherwise record a `warning` and mark the item `[CITATION MISSING]` in the Checklist. Never invent a citation. | Done (verified Rev 3 run, Appendix G) | `test_validation_layer.py` |

## 5. SOW reference model

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| REF-01 | A **SOW work item** is the smallest unit of contracted scope the SOW identifies or lists. Each item has a reference, a reference kind (`Story ID`, `Deliverable number`, `Task or WBS code`, `Section`, or `Synthetic`), a title, a phase, an owner (Toptal or Client), a type (Build, Integration, Test, Certification, Analysis, or Documentation), and a fingerprint (the sorted unique tokens from TXT-05). | Done | `test_sow_reference_patterns.py` |
| REF-02 | `SOW_REFERENCE_PATTERNS` in `src/config.py` is an ordered, configurable list (Appendix C). It excludes this tool's own prefixes. No hard-coded `HS-` pattern exists outside config and fixtures. | Done | `test_sow_reference_patterns.py` |
| REF-03 | The work item catalogue is extracted from the SOW. When the SOW has no identifiers, items come from its contracted-scope list and get synthetic references `SOW-{phase code or milestone ID}-{nn}`, or `SOW-{nn}` when there are no phases or milestones. | Done | `test_no_story_sow.py` |
| REF-04 | When the SOW lists no scope items, behaviour falls back to deliverables from extraction with template tasks. Record a `warning`, and the self-check reports `No SOW work items identified`. | Done | `test_empty_catalogue.py` |
| REF-05 | **Work item titles.** The catalogue captures each work item's own title from the SOW (for example, a story's title or a Work Output row heading). VAL-08's fallback `{reference}: {deliverable name}` is used only when the SOW gives no title, which records a `warning`. Story tasks in the WBS then read `{verb} {reference}: {title}`. | Done (verified Rev 4 round, Appendix H) | `test_sow_reference_patterns.py`, snapshot |

## 6. Phases, gates, and milestones

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| MS-01 | **Phase label.** A milestone description matching `^\s*(P\d+[a-z]?)\s+(name)\s*(accepted\|completed\|complete\|approved\|sign[- ]?off)?\s*:\s*(scope)` defines a phase. The workstream is `"{code} {name}"`, the milestone name is the text before the colon, and the scope is the text after it. | Done | `test_phases.py` |
| MS-02 | **Phase attachment for every milestone:** (1) the first phase code or full phase name anywhere in the text; else (2) a phase-corpus score of at least 0.20 (MAP-02); else (3) the phase of the nearest preceding milestone in Kit order. The keyword taxonomy (Appendix B.4) is used only when the baseline has no phase labels at all. Keyword and phase workstreams are never mixed. | Pending | `test_gate_reconciliation.py` |
| MS-03 | **Gates.** A phase's gate is the milestone that begins with the phase label and "accepted", "completed", "approved", or "sign-off". If none does, it is the phase's last milestone in Kit order. Deliverables and work packages map only to gates. | Pending | `test_gate_reconciliation.py` |
| MS-04 | **Merged duplicates (Workbook, defensive).** A non-gate milestone in the same phase matching the VAL-01 restatement pattern merges into its gate. When VAL-01 has already reconciled the baseline, the Workbook shows the renumbered gate ID, with provenance in Notes. Only when it receives an unreconciled baseline does the gate's Milestone ID show `M1 (+M2)`, with the Notes `Includes M2: acceptance review and sign-off`. Its key dependencies join the gate's prerequisites, de-duplicated. It gets no row or packages of its own. | Done (verified Rev 7 round) | `test_gate_reconciliation.py` |
| MS-05 | **Checkpoints.** Other non-gate milestones, and `interim_checkpoints`, become level 2 rows with Row Type `Checkpoint`, placed before the gate in Kit order. Every checkpoint has a phase, assigned by the MS-02 attachment rules (first phase named, then phase-corpus score, then the nearest preceding milestone's phase). It is never `N/A` or blank, in the Kit's Interim Checkpoints table or the Workbook. They have no packages; their key dependencies join the gate's prerequisites; their Date Basis is `Within {phase} weeks a–b` unless dated; their Source is `Baseline - Milestone Plan`. | Done (verified Rev 7 round) | `test_gate_reconciliation.py` |
| MS-06 | Workstreams and gates are ordered by delivery sequence: planned start, then external date, then natural sort of ID. There is exactly one workstream per SOW phase, and nothing else. | Done (with MS-02 Pending) | INV-02 |
| MS-07 | A defensive filter drops any milestone, deliverable, work package, or RAID item matching the readiness pattern (Appendix C). Drops are counted in `excluded_items`. | Done | `test_no_readiness_content.py` |
| MS-08 | If the baseline has no milestones, create placeholder `MS-TBC` "Delivery milestones to be confirmed", with Source `PM Best Practice` and a warning note. | Done | `test_empty_catalogue.py` |

## 7. Dates and predecessors

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| DT-01 | **Start Date.** `--start-date` gives basis `Provided`. Otherwise, the first Monday on or after a provided `sow_awarded_date`, with basis `Assumed - first Monday after award; confirm`. Otherwise, the first Monday on or after the generation date, with basis `Assumed - first Monday after generation date; confirm`. | Pending (last case, with VAL-05) | `test_phases.py`, `test_award_date.py` |
| DT-02 | **Week ranges.** `weeks?\s+(\d+)\s*(?:–\|—\|-\|to)\s*(\d+)` or `week\s+(\d+)`, searched in the description and then the critical path assumptions. Planned Start = Start + 7(a−1) days. Planned Finish = Start + 7(b−1) + 4 days (Friday). Basis `SOW estimate, weeks a–b`. | Done | `test_phases.py` |
| DT-03 | **Date precedence.** An `external_date` is the External Commitment Date and the Planned Finish, with basis `Contract date`. Otherwise a week range applies. Otherwise dates stay blank, with basis `To be confirmed` and a confirmation note. `internal_buffer_date` is copied when present and never invented. | Done | `test_phases.py` |
| DT-04 | **Predecessors** are computed between gates only. A dependency or assumption entry that names another gate (by phase code, phase name, or "Milestone N" per RAID-05), together with any of accept, acceptance, accepted, complete, completion, sign-off, after, before, begins, or starts, is a schedule link. It is not a client prerequisite. | Done | `test_predecessors_v3.py` |
| DT-05 | **Sequential gates.** A sequential-gate statement (Appendix C) gives each gate after the first the previous gate as predecessor, with the note `Predecessor from sequential-gate assumption ({source ID})`. | Done (verified Rev 3 run, Appendix G) | `test_sequential_predecessors.py` |
| DT-06 | **Predecessor sanity.** A predecessor must come earlier in delivery order. Any that points to the same or a later gate is dropped with a WARNING. The graph is acyclic. | Pending | `test_predecessor_graph.py` |
| DT-07 | **Task timing.** Client Prerequisites run from the Start Date to the last working day before the gate's Planned Start (for the first gate, the Start Date). Deliverable and Other-work tasks run from the gate start to the internal buffer date if present, else the Friday of the gate's second-to-last week. Milestone Acceptance runs from the Monday of the final week to the gate's Planned Finish. Gates shorter than 2 weeks use their full range for all tasks. | Done | `test_task_timing.py` |

## 8. Mapping

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| MAP-01 | **Tokenizer.** Lowercase the text and replace `/` with a space. Split on non-alphanumeric characters, so hyphenated words split into their parts only. Strip `ing` from tokens longer than 5 characters, then plurals (`ies` → `y`, trailing `s` except `ss`). Drop tokens under 3 characters, numbers, and the stop words in Appendix C. | Done | `test_mapping_v3.py` |
| MAP-02 | **Weighted overlap.** Score = the sum of IDF weights of shared tokens divided by the sum of the item's token weights, where IDF = ln((N+1)/df). A gate's scope corpus is its phase name, its scope, and every contracted-deliverables entry for its phase (entries without a phase code inherit the previous entry's code). | Done | `test_mapping_v3.py` |
| MAP-03 | **Deliverable to gate, first match wins:** (1) `Catalogue phase`: all of the deliverable's work items are in one phase; (2) `Phase code` in the name; (3) `Referenced by milestone` (ID mention); (4) `Backlog match ({WP})`: a non-degenerate work package scoring at least 0.75 whose gate comes from its work item's phase (never from a default); (5) `Scope match`: at least 0.20, ties to the earlier gate; (6) `Backlog match`: work package title score at least 0.30; (7) `Submission date`; (8) `Unmapped - confirm milestone`, placed at the latest gate. Acceptance fields (evidence, review window, rework path) are never used for mapping. | Done (verified Rev 2 run, Appendix F) | `test_mapping_v2.py`, `test_mapping_v3.py` |
| MAP-04 | **Work package to gate:** `Work item phase` (the phase of its SOW work item); else `Backlog link` (valid `linked_milestones`); else `Backlog phase order` (the parents are exactly the first N deliverable IDs, non-decreasing, one per gate); else phase code; else scope match. | Done (verified Rev 2 run, Appendix F) | `test_backlog_phase_order.py` |
| MAP-05 | **Work package to deliverable:** `Parent link` (a valid parent in the same gate) first, before any text scoring; a SOW reference is used as a matching key only when it is unique to one deliverable (never a Section-kind reference or one shared by several deliverables); else the best score of at least 0.20 within the gate (ties to the lower ID); else a second pass to a deliverable without a work package that shares a distinctive token (IDF of at least ln 2); else `Other {workstream} work`. | Done (verified Rev 5 round: parent link evaluated first; no work package moved in any fixture) | `test_second_pass_wp.py` |
| MAP-06 | **Degenerate work packages.** After removing a `Work Package:` prefix, a work package is degenerate if it scores at least 0.80 against its parent's name, or if every deliverable has exactly one work package, or if its title is its parent's name plus generic filler (`implementation task`, `task`, `work package`, `deliverable`), or if two or more work packages share its title. A degenerate work package never becomes a task and never supports `Backlog match`; its ID goes into the deliverable row's Source ID. | Done (verified Rev 2 run, Appendix F) | `test_degenerate_backlog.py` |
| MAP-07 | **Multi-deliverable notes.** Only within the same gate, with a score of at least 0.45 and a shared distinctive token: `Also covers {DEL}` on the owning deliverable, and `Covered by {WP} ({DEL})` on the others. | Done (verified Rev 4 round, Appendix H) | `test_multi_deliverable_precision.py` |

## 9. WBS

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| WBS-01 | Levels: 1 = phase workstream; 2 = gate or checkpoint; 3 = `Client Prerequisites`, each mapped deliverable (natural ID order), `Other {workstream} work` (when needed), and `{Gate ID} Milestone Acceptance`; 4 = tasks. Codes are assigned depth-first, are strings, and are never sorted. | Done (checkpoints Pending) | `test_builder.py` |
| WBS-02 | **Client Prerequisites:** one `Confirm: {dependency}` task per gate key dependency that is not a schedule link, plus merged and checkpoint dependencies, de-duplicated. Owner `Talent PM`. Source `Baseline - Milestone Plan`. | Done | `test_builder.py` |
| WBS-03 | **Deliverable tasks:** the work-type template (Appendix B.1). The core task is replaced by (1) non-degenerate work packages; else (2) one task per SOW work item, `{verb} {reference}[: {title}]`, owner `Toptal Delivery Team`, Source `Baseline - SOW Work Items` (Source ID = reference); else (3) the template core task. Then `Assemble acceptance evidence` (Talent PM) and `Internal quality review against acceptance criteria` (Delivery Manager). In per-deliverable acceptance mode, add `Submit for client review`, `Address client feedback and rework`, and `Obtain written client acceptance`. | Done | `test_story_tasks.py` |
| WBS-04 | **Acceptance mode** is milestone-level when any milestone, deliverable acceptance field, communications item, or RAID item mentions "Acceptance Review", "Milestone Sign-Off", or "end-of-milestone". Otherwise it is per-deliverable. | Done | `test_acceptance_mode.py` |
| WBS-05 | **Milestone Acceptance** (milestone-level mode), 6 tasks: `Prepare milestone acceptance package and evidence` (Talent PM); `Support client UAT for {gate}` (Delivery Manager, only if "UAT" appears in the baseline); the per-milestone communications item (matching `each\s+milestone\|per\s+milestone\|end\s+of\s+(each\|every)\s+milestone\|milestone\s+acceptance`), or `Hold milestone acceptance review with client approvers`; `Address client feedback and rework` (Talent PM); `Obtain milestone sign-off from the client's designated approvers` (Delivery Manager); `Update schedule and RAID Log after acceptance` (Talent PM). | Done | `test_builder.py` |
| WBS-06 | No Project Kickoff package, no recurring row, and no Reporting and Control package. Communications items appear only as the WBS-05 review task. | Done | `test_no_project_management.py` |
| WBS-07 | **Owners are roles:** Talent PM, Delivery Manager, Toptal Delivery Team. Roles are never resolved to people. Deliverable rows keep the Kit owner. | Done | `test_task_owners.py` |
| WBS-08 | **Predecessors within packages:** tasks chain sequentially. The first deliverable task depends on the last prerequisite task. `Prepare milestone acceptance package` depends on every deliverable package. A work package's `dependency_references` are kept only within the same gate. | Done | `test_builder.py` |
| WBS-09 | **Evidence.** The deliverable row's Acceptance / Completion Criteria holds the acceptance criteria plus `Evidence: {evidence}`. Placeholder evidence adds the note `Evidence not defined in baseline - agree with the client` to the row and to its evidence task. An evidence-consistency flag is added when the deliverable's own score is below 0.10, another deliverable scores at least 0.35, and that best match is a different deliverable that shares at least one distinctive token with the evidence (IDF of at least ln 2 across deliverable texts). Generic evidence such as "test scripts, execution results and a results report" never raises a flag. | Done (verified Rev 3 run, Appendix G) | `test_evidence_flags.py`, `test_missing_evidence_note.py` |

## 10. RAID Log

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| RAID-01 | **Row order and IDs:** Kit risks and issues, then dependencies and assumptions, then contract clarifications, then open questions, numbered `RAID-01` onwards without re-sorting. Source ID is the Kit or Checklist ID. Duplicate type and normalized description across the first two sources merge into one row, with both Sources. | Done | `test_builder.py` |
| RAID-02 | **Open questions:** Type `Issue`, Category `Open Question`, Owner `Talent PM`. Q-IDs are numbered by position in the full list, so they match the Checklist. Skip questions matching the readiness pattern or `\brole is unassigned\b`. | Done | `test_open_questions.py` |
| RAID-03 | **Contract clarifications:** Category `Contract Clarification`. The citation parser recognizes (1) `[V#] <document words>[.ext], <ref>:`; (2) `Exhibit\|Schedule\|Appendix\|Attachment\|Annex <id>[, <section words>]:`; (3) `<document>.<ext>[, <ref>]:` (a file extension or an Exhibit-type word is required). Contract Reference = the citation, then ` \| SOW refs: ...` (any reference kind, not only stories) and ` \| Sections: ...` when present, listing every section cited, in singular and plural forms ("Section 2 and Section 3", "Sections 2 and 4", and "Sections 1, 2 and 3" give `2, 3`, `2, 4`, and `1, 2, 3`), never with an empty part or a trailing comma. Plural SOW references are expanded too ("Deliverables 2.2 and 3.1" gives `SOW refs: Deliverable 2.2, Deliverable 3.1` and links both). Non-numeric parts such as "Header" are kept as written. When a document citation is recognised, the SOW references and section numbers it contains are still listed in the `SOW refs` and `Sections` parts, so every row uses the same format: `{document}[, {section label}] \| SOW refs: ... \| Sections: ...`. **No information loss:** a citation is removed from the description only when every part of it appears in the Contract Reference; otherwise the description keeps it. Citation format 3 accepts `.txt` and `.md` documents as well as `.pdf`, `.docx`, and `.pptx`, and the citation is removed from the description wherever it appears after the category prefix. Description = `{category}: {text without the citation}`. Use `Not cited` when nothing is found. A Contract Reference that is not `Not cited` must contain a file extension, an Exhibit-type word, a SOW reference, or a section number; anything else (for example `schedule is` on Q-01, or `schedule impact` on Q-09) is a parser error. Enforce this with a final check on the parsed value, not with per-case fixes. Neither `sanitize_report_text` nor section stripping is applied to these rows. | Done (verified Rev 7 round) | `test_citation_precision.py` |
| RAID-04 | **Contract Reference** is filled on every Contract Clarification and Open Question row, and blank on other rows. | Done | `test_contract_reference_consistency.py` |
| RAID-05 | **Linking, in order:** phase codes, phase names, and `Milestone N` (the N-th gate when the Kit has more milestones than gates or the number is paired with a phase name; otherwise Kit ID `MN`); then milestone or deliverable IDs in the text; then non-default `linked_milestone`; then non-default `linked_deliverable`. Linked Deliverables come from SOW references found in the text (REF index), using only references unique to one deliverable; Section-kind references and references shared by several deliverables never create links. Work package mapping and RAID linking use one shared helper for this rule. Linked Milestone is the union of all linked gates, with merged and checkpoint IDs mapped to their gate. Workstream is the phase name, `Multiple phases`, or `Cross-phase`. | Done (verified Rev 4 round: mock RAID-05 links to M2 only; numbered_deliverables links via unique "Deliverable N.N" references are correct) | `test_raid_links_v3.py`, `test_milestone_n_resolution.py` |
| RAID-06 | **Normalization.** Probability and Impact map to Low, Medium, or High. Status maps to Open, In Progress, Monitoring, Escalated, or Closed. Owners that are placeholders become `[UNASSIGNED - TO BE CONFIRMED]` with the note `Owner unassigned`. Rating is derived from P and I unless the baseline gives a non-default severity. | Done | `test_raid_owner_normalization.py` |
| RAID-07 | **Decision links:** a shared SOW reference or a text score of at least 0.50; at most 3, best first. | Done | `test_decision_links.py` |
| RAID-08 | **Questions about merged or checkpoint milestones** link to the phase's gate, with the note `Refers to {ID} (merged into {gate})` or `(checkpoint of {gate})`. | Done (verified on `arc_overextracted`, Rev 6 round) | `test_gate_reconciliation.py` |
| RAID-09 | **Kit RAID fields reach the Workbook.** For every Workbook RAID row whose Source ID is a Kit risk or issue (`RSK-`, `ISS-`), the Workbook's Probability, Impact, Owner, Mitigation / Response, Trigger / Early Warning, and Status equal the Kit RAID Log values (after TXT-01 cleanup and RAID-06 normalization). | Done (verified Rev 10 review: Kit mitigations in the Workbook; Trigger / Early Warning compared at model level, because the Kit RAID table has no trigger column) | `test_raid_kit_consistency.py`, INV-30 |

## 11. Layout and formatting

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| FMT-01 | Sheets: `Project Schedule` (active), `WBS`, `RAID Log`, and a hidden `_Lists` sheet with defined names `List_*`, including `List_Milestone_IDs`. Validations reference defined names, cover the data plus 200 rows, and use error style `warning`. | Done | `test_writer.py` |
| FMT-02 | **Title block on every sheet.** Row 1: `{PROJECT} - PROJECT SCHEDULE`, `- WORK BREAKDOWN STRUCTURE`, or `- RAID LOG`. Row 2: `Client \| Contract \| Talent PM \| Delivery Manager`. Row 3: `Start Date: {date} ({basis}) \| Generated {date} from the project baseline`. Row 4 (Schedule only): the planned-dates note, plus the synthetic-reference note when applicable. Header on row 5. | Done | `test_writer.py` |
| FMT-03 | Column layouts are exactly as in Appendix A. | Done (verified on `arc_overextracted`, Rev 6 round) | `test_writer.py` |
| FMT-04 | **Styling.** Arial; navy header with white bold text; thin borders; level styling in the Schedule and WBS; zebra striping in the RAID Log; dates as date cells formatted `yyyy-mm-dd`; a warning fill on placeholder text (`[CONFIRMATION REQUIRED]`, `UNASSIGNED`, `[TBD]`) and on missing dates. | Done | `test_writer.py` |
| FMT-05 | **Weekly timeline** (Schedule, from column Y). Mondays, up to 78 weeks. Bars run from Planned Start to Planned Finish. The finish week is marked in navy and the buffer week in accent blue. | Done | `test_writer.py` |
| FMT-06 | **Safety.** Text beginning with `=` is written as a string. Illegal XML characters are stripped. Text is truncated at 32,000 characters. Formula ranges are exact. `fullCalcOnLoad` is on. Freeze panes, autofilter, print setup, and tab colors are set. | Done | `test_writer.py` |
| FMT-07 | Workbook properties: title `{Project} Project Delivery Workbook`; creator `Toptal PMO Generator v{version}`. | Done | `test_writer.py` |

## 12. Text hygiene and naming

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| TXT-01 | Copied text passes through `sanitize_report_text` (except RAID-03 rows and text the tool generates itself, such as its own open questions), then has `ACTION_TAG_REGEX` matches removed, whitespace collapsed, and stray separators trimmed. | Done (verified Rev 3 run, Appendix G) | `test_no_readiness_content.py` |
| TXT-02 | Task names are at most 120 characters, cut at a word boundary with the full text in Notes. Task names never contain Kit acceptance text. A `Work Package:` prefix is always stripped. | Done | `test_builder.py` |
| TXT-03 | Notes are de-duplicated and joined with `; `. | Done | `test_builder.py` |
| TXT-04 | **Source values:** `Baseline - Milestone Plan`, `Baseline - Deliverables`, `Baseline - Backlog`, `Baseline - SOW Work Items`, `Baseline - Communications Plan`, `Baseline - RAID Log`, `Baseline - Dependency Log`, `Baseline - Contract Clarifications`, `Baseline - Open Questions`, `PM Best Practice`. A level 1 or level 2 row never has `PM Best Practice` as its Source (MS-08 excepted). | Done (verified Rev 2 run, Appendix F) | `test_builder.py` |
| TXT-05 | **Fingerprint** = the sorted unique MAP-01 tokens of a title. | Done | `test_story_phase_stability.py` |

## 13. Traceability self-check

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| TR-01 | After the model is built, compute in-baseline versus in-Workbook counts, and missing IDs, for: gates, checkpoints, deliverables, work packages, SOW references, RAID items, dependencies and assumptions, contract clarifications, and open questions. Print the result in the CLI and store it in `PMOWorkbookResult.traceability`. Missing IDs are logged as WARNING. | Done (gates and checkpoints Pending) | `test_traceability_self_check.py` |
| TR-02 | Cross-artifact counts agree. Kit deliverables, milestones, RAID items, and dependencies equal the Checklist G01-03, G01-04, and G01-05 counts and the Workbook counts. The G01-15 validation-point count equals the number of rows in the Checklist questions table. The Workbook's open-question rows equal that number minus the excluded role questions. | Done (verified Rev 3 run, Appendix G) | INV-12 |

## 14. Startup Kit generation

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| KIT-01 | Every register shows IDs: `M`, `CP`, `DEL`, `WP`, `RSK`, `ISS`, `DEP`, `ASM`, `DEC`, and `COM`. Risks and issues show Probability and Impact. The parser reads all of them back. | Done (`CP` Pending) | Snapshot, `test_parser_roundtrip.py` |
| KIT-02 | **Milestone Delivery Plan** lists the gates only (VAL-01). A new **Interim Checkpoints** table (`CP-NN`, Phase, Description, Source Reference) appears when checkpoints exist. | Done (verified Rev 7 round) | `test_gate_reconciliation.py` |
| KIT-03 | **Deliverables and Acceptance Matrix:** a SOW References column (references only, VAL-06). Evidence is per work item when the SOW states acceptance at that level; group items are shared with every deliverable they cover, noted as `Shared evidence item covering ...`; otherwise a one-to-one name join (Jaccard of at least 0.35). The review window defaults to `Not specified; reviewed at the Milestone Acceptance Review at the end of {phase}`, or to the first sentence of the SOW statement (at most 120 characters). | Done (verified Rev 2 run, Appendix F) | Snapshot |
| KIT-04 | **Deliverables are deterministic.** They are the SOW's own deliverables when the SOW lists them. Otherwise they are grouped from the catalogue by phase and then work type, split at Work Output headings, with at most 5 items each, and numbered by phase, work type, and lowest reference. Two extractions of the same SOW produce identical deliverables. | Done | QA-07, snapshot |
| KIT-05 | **Scope Decomposition** is built from the catalogue (VAL-02), with Parent Deliv, SOW References, and an owner on every row. | Done (verified Rev 2 run, Appendix F) | `test_backlog_recorded.py` |
| KIT-06 | `format_cell_with_action` strips only unbalanced trailing brackets. `PLACEHOLDER_REGEX` applies only to bracketed tokens or whole-cell matches. | Done | `test_format_cell.py` |
| KIT-07 | Action tags sit in the cell their action targets (owner actions in Owner, and so on). The Contract Ambiguities Logged row carries no tag. | Done | `test_action_tag_placement.py` |
| KIT-08 | The SOW Interpretation table includes a `Contract Ambiguities Logged` row. | Done | Snapshot |
| KIT-09 | Charter and award date follow VAL-05. | Pending | `test_award_date.py` |
| KIT-10 | **Roster and named roles.** Names (PMO Lead, Delivery Manager, Talent PM) come only from the CLI or config. When none is supplied, every name shows `[UNASSIGNED - TO BE CONFIRMED]` and the role questions are raised; the tool never infers or carries over a name from an earlier run. The talent roster lists the roles the SOW names. | Done (verified Rev 3: roster 4 roles; names unassigned because none were supplied) | `test_roster.py` |
| KIT-11 | **Decision owners** are a stakeholder role from the Kit's stakeholder model, `Client`, or `Toptal`. Invented roles (`Delivery Lead`, `QA Lead`) are mapped to the nearest stakeholder role or `Toptal`. | Done (verified Rev 3 run, Appendix G) | Snapshot |

## 15. Readiness Checklist generation

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| CHK-01 | G01-14 evidence is `{n} contractual ambiguities logged with recommended clarifications`, with status `Review Required` while any is open. | Done | Snapshot |
| CHK-02 | G01-11 evidence lists the actual communications item names. | Done | Snapshot |
| CHK-03 | G01-03 counts an unconfirmed client approver as unconfirmed. A generic role with no named person (for example "Client's designated approvers") is unconfirmed while an open question asks for the names (Q-02). G01-02 omits "tailored buffers" when no milestone has a buffer date. | Done (verified Rev 4 round, Appendix H) | Snapshot |
| CHK-04 | G01-08 evidence is `{n} delivery talent roles listed; {m} named`, with status `In Progress` while m < n. | Done | Snapshot |
| CHK-05 | A date question is generated for every gate (not checkpoints) without an external date, whether or not a date action exists. | Done (gates-only Pending with VAL-01) | `test_date_questions.py` |
| CHK-06 | Fixed Bid guardrails, **in every column**, never mention effort, rate, burn, variance percentages, or a percentage of budget. Status wording: `Schedule slip > 3 days or acceptance rejection` and `Milestone acceptance and Change Order log review`. | Done (verified Rev 2 run, Appendix F) | `test_guardrails.py` |
| CHK-07 | G01-04 counts gates. VAL errors add the exceptions defined in VAL-07. | Pending | `test_validation_layer.py` |

## 15A. Talent Team Onboarding Deck

**Purpose.** A seven-slide PowerPoint deck (a cover slide, five content slides, and a closing "Your Project Kit" slide), built on the Toptal presentation template, used to onboard the Talent PM and the whole Talent Project Team. Each slide carries talking points in its speaker notes, for later reference. Every fact in the deck traces to the Startup Kit or the Project Delivery Workbook, which are the only sources of truth. Appendix K gives the slide-by-slide design.

| ID | Requirement | Status | Test |
| --- | --- | --- | --- |
| DECK-01 | **Output.** The deck is written to `{sanitize_filename(project)}_Talent_Onboarding_Deck.pptx`, in the same folder as the Kit and Workbook. It has exactly 7 slides, in this order: (1) Cover; (2) Project Charter; (3) Workstreams, Milestones, Deliverables and Dates; (4) Acceptance Criteria; (5) High-Risk Items; (6) Client Collaboration; (7) Your Project Kit. | Done (verified Rev 10 review: 7 slides) | `test_deck_structure.py` |
| DECK-02 | **Flags.** `--slides` writes the deck. Because the deck must trace to its sources, `--slides` also writes the Startup Kit and the Project Delivery Workbook in the same run, and the log says so: `Deck sources: Startup Kit and Project Delivery Workbook also written`. `--all` writes all four outputs (Kit, Checklist, Workbook, deck). With `--reingest-docx`, the input Kit is the Kit source; it is rewritten only if `--kit` or `--all` is given. `OutputSelection` gains `slides: bool`, and `from_flags` gains `slides`. `RunResult` gains `slides_path`. | New | `test_orchestrator_export.py` |
| DECK-03 | **One model, two sources.** The deck is built from a `DeckModel` assembled from (a) the validated `StartupKitBaseline` used to write (or read) the Kit, and (b) the `WorkbookModel` returned by `build_workbook_model` for the same run, with the same `start_date`. The deck never re-extracts, never calls the LLM, and never reads the SOW. Building the `DeckModel` is pure (no file I/O), in `src\generators\onboarding_deck\builder.py`. | New | `test_deck_builder.py` |
| DECK-04 | **Trace references.** Every content element on a slide (each table cell value, bullet, fact, and talking-point fact) carries one or more `TraceRef(artifact, locator, key, field)`. `artifact` is `Kit` or `Workbook`. `locator` is the Kit section heading (for example `Project Startup Charter`, `Deliverables and Acceptance Matrix`, `RAID Log`, `Communications and Reporting Plan`, `Stakeholder and Responsibility Model`) or the Workbook sheet name (`Project Schedule`, `WBS`, `RAID Log`). `key` is the row ID as it appears in the source (for example `M2`, `DEL-07`, `RAID-14`, `COM-03`, or a WBS code such as `1.1.7.2`), or the field label shown in the source for single-value facts (for example `Client Sponsor`, or `Start Date` in the Project Schedule title block). Invented keys such as `M1 Step 1` or `Title Row 3` are not allowed; INV-26 rejects any key that does not appear in the source. Facts that are not table rows use these locators and fields: the Kit's untitled header table has locator `Header table`; file names use field `File name` (checked against the output folder); Kit section headings use field `Section heading`; Workbook sheet names use field `Sheet name`. `field` is the column or field name. Fixed labels written by the tool (slide titles, column headers, the kicker) are the only text without a `TraceRef`. | Done (verified Rev 10 review: real keys; talking points in the manifest) | `test_deck_traceability.py` |
| DECK-05 | **Strict 100% traceability.** (1) Every content element has at least one `TraceRef`. (2) Every `TraceRef` resolves to a cell or table row in the written Kit `.docx` or Workbook `.xlsx`. (3) The displayed text equals the source text after normalization (TXT-01 cleanup, whitespace collapsed, action tags removed), or is a prefix of it that ends at a sentence or clause boundary (`.`, `?`, `!`, `;`, `:`, ` - `, or the close of a complete parenthetical). A comma is not a clause boundary. A prefix may never end in an ellipsis (`...` or `…`), never leave an unbalanced bracket, parenthesis, or quotation mark, and never cut a name: deliverable names, milestone names, stakeholder names, communications item names, and file names are always shown whole (if one does not fit, the font is reduced per DECK-21, or the element shows the ID only with the name in the talking points). Paraphrasing, summarizing, and LLM rewording are never allowed. (4) Dates are shown as `YYYY-MM-DD`, exactly as in the Workbook. The check reads the written files back, not the in-memory model. | Done (verified Rev 10 review: no ellipses, comma cuts, or shortened names found) | `test_deck_traceability.py`, INV-26 |
| DECK-06 | **Trace manifest.** The generator writes `{project}_Talent_Onboarding_Deck.trace.json` beside the deck. For each slide it lists every element: its slide number, shape name, displayed text, and `TraceRef` list. `check_artifacts` uses it to run DECK-05 against any output folder. | New | `test_deck_traceability.py` |
| DECK-07 | **Completeness.** Slide 3 shows every gate, every checkpoint, and every deliverable ID in the Workbook Project Schedule. Slide 4 shows every deliverable ID. On Slide 6, every client stakeholder, every communications item, and every client prerequisite appears, either as a bullet or in a `+N more` line. Each prerequisite counts separately: a Workbook Client Prerequisites cell holding several prerequisites separated by `; ` is split into one item per prerequisite. Where a table exceeds its row capacity (Appendix K), the last row reads `+N more: DEL-xx, DEL-yy, ... (see <source locator>)`, listing every omitted ID, so no ID is ever dropped. | Pending (ARC slide 6 shows 4 of 12 client prerequisites, the first of each gate, with no `+N more` line) | `test_deck_completeness.py`, INV-27 |
| DECK-08 | **Concise text.** Slide title at most 8 words. Bullets and table cells target at most 15 words, cut at a clause boundary by the DECK-05 prefix rule. When no DECK-05-compliant cut exists within 15 words, the shortest compliant cut is shown, and INV-28 accepts it; DECK-05 always takes precedence over the word target. At most 6 bullets per text block, where each subheading group in a card counts as one block; where Appendix K.2 gives a different capacity for a block (for example Working rhythm, 7), K.2 takes precedence. At most 6 talking points per slide, each at most 30 words. No text may overflow its shape: the writer measures each text frame against its character capacity (Appendix K) and reduces font size by at most 2 pt before cutting at a clause boundary. | Done (verified Rev 10 review; word target revised in Rev 11) | `test_deck_text_limits.py`, INV-28 |
| DECK-09 | **Talking points.** Each content slide's speaker notes contain a `TALKING POINTS` section of 3 to 6 bullets, and a `SOURCES` line. The cover and Your Project Kit slides' notes contain 2 to 4 talking points and a `SOURCES` line (Appendix K.2). Every talking point on slides 2 to 6 contains at least one traced value and is recorded in the trace manifest with its `TraceRef`s. Fixed guidance sentences (no traced value) are allowed only on the cover and Your Project Kit slides, and come from a fixed list in `talking_points.py`. Talking points never use evaluative filler (for example "ensures", "proactive", "robust", "seamless", "active alignment") and never state something the slide's sources do not show (for example claiming mitigations are assigned when none are listed). A placeholder reads naturally inside a sentence (`PMO Lead: to be confirmed`), and there is no doubled punctuation (`..`). Talking points are sentences built deterministically from templates in `talking_points.py`, filled only with traced facts, for example `The project runs in {n} phases, from {start} to {finish}.` Templates contain no project-specific data (P-08). The `SOURCES` line names each Kit section and Workbook sheet used on the slide. | Done (verified Rev 10 review: every talking point traced; no filler) | `test_deck_talking_points.py` |
| DECK-10 | **Placeholders.** Action tags (`[ACT-...]`) are removed. A value that is a placeholder (`[CONFIRMATION REQUIRED]`, `UNASSIGNED`, `[TBD]`, empty) is shown as `To be confirmed`, in italic accent blue (`204ECF`). It still carries its `TraceRef`, and the trace check accepts it against the placeholder in the source. | New | `test_deck_traceability.py` |
| DECK-11 | **No readiness content.** The deck contains no readiness score, G-01 gate, checklist status, `ACT-` ID, or other INV-04 readiness term. The Readiness Checklist is never a deck source. | Done (Rev 9 deck: no readiness content found) | INV-04 (extended to the deck) |
| DECK-12 | **Template.** The template is stored in the repository as `templates\Toptal_Presentation_Template.pptx`, a copy of the supplied file, with its path configurable by `DECK_TEMPLATE_PATH`. The generator opens it, removes every existing slide **and its slide part** (so no template slide content remains in the package), and adds the cover slide on the layout named `CUSTOM_1` and the 5 content slides on the layout named `CUSTOM_16`, both from the first slide master. `CUSTOM_1` provides the cover title and subtitle; `CUSTOM_16` provides the title and kicker; both provide the `Confidential` footer with slide number and the Toptal logo. If either layout is missing, the generator fails with an error naming it; it never falls back to another layout. | Done (verified Rev 10 review: 7 slide parts on the correct layouts) | `test_deck_structure.py`, INV-29 |
| DECK-13 | **Style.** The deck follows the template's styling (Appendix K, K.1). The writer sets these explicitly on every slide rather than relying on layout defaults (the layout default renders the title blue and the kicker large): title Proxima Nova bold 28 pt `0F172A`; kicker Proxima Nova bold 11 pt `64748B`, reading `{PROJECT NAME} · TALENT TEAM ONBOARDING`; card headings Proxima Nova bold 16 pt `0F172A`; card subheadings Proxima Nova Semibold 11 pt `204ECF`; body Calibri 11 pt `475569`; tables with a `204ECF` header row (white Proxima Nova bold 12 pt), alternating `F8FAFC` and `FFFFFF` rows, and `E2E8F0` borders; cards as white rounded rectangles with corner adjustment `6153` (the template's value) and a 1.1 pt `E2E8F0` outline. No Material Icons glyphs (the font is not guaranteed on viewers' machines), no accent bars, no decorative stripes. | Done (verified Rev 10 review: bold black titles, grey kicker, template card radius) | `test_deck_style.py` |
| DECK-14 | **Determinism.** The same Kit and Workbook always produce the same deck and trace manifest, apart from file timestamps. | New | `test_deck_builder.py` |
| DECK-15 | **Works for any SOW.** The deck builds without error for every fixture (ARC, ARC over-extracted, mock, no story IDs, numbered deliverables), including SOWs with no phases, no SOW references, no risks rated High, no client stakeholders, or no communications plan. Empty sections show one line, `None recorded in the Startup Kit` or `None recorded in the Project Delivery Workbook`, which is a fixed label. | New | `test_deck_any_sow.py` |
| DECK-16 | **CLI summary.** When the deck is written, the CLI prints a `TALENT ONBOARDING DECK` block: slide count, content elements, elements traced (must be 100%), omitted-ID rows used, and the output path. | New | `test_cli_reporter.py` |
| DECK-17 | **Snapshots and normalizer.** `normalize_artifacts` gains a `deck_slides` key: for each slide, its title, kicker, every text frame's paragraphs, every table's rows, and the notes text. All five fixtures get deck snapshots, following QA-03 (proposed only; a person promotes them). | New | `test_snapshots.py` |
| DECK-18 | **README.** The README documents `--slides`, its source-writing behaviour, the deck file and its trace manifest, and the template path. | New | Manual |
| DECK-19 | **Only displayed content is a source.** A deck fact may come only from content that the written Kit or Workbook actually displays. Model fields that neither document renders (for example `delivery_objectives` and `success_criteria`, which the Kit does not show) are never used, even though they exist in the baseline. | New | `test_deck_traceability.py` |
| DECK-20 | **Formula cells.** Workbook cells that hold formulas (Rating, Score (P x I), Duration, Days to Finish, Health) have no stored value in the file. A deck fact derived from one is traced to the formula's input cells (for example Probability and Impact), and the trace check recomputes it with the same rule as the formula. Rating is `High` when Probability and Impact are (High, High), (High, Medium), or (Medium, High); `Low` when both are Low; otherwise `Medium`. | New | `test_deck_traceability.py` |
| DECK-21 | **Layout and alignment.** (1) **Cards:** one text frame per card, inset 0.20 in from the card on every side, anchored top, word wrap on, autofit off. The card heading is a single line (Proxima Nova bold 16 pt, reduced to 14 pt if needed; it never wraps), followed by 8 pt of space. Subheadings are Proxima Nova Semibold 11 pt `204ECF` with 8 pt space before and 2 pt after. Body paragraphs are Calibri 11 pt (never below 10.5 pt), with 4 pt space after. Bullets use paragraph bullet formatting (bullet character `•`, left margin 0.17 in, hanging indent 0.17 in), never a typed `•` character. (2) **Tables:** column widths as in Appendix K.1; header row 0.40 in; body rows at least 0.30 in; body text Calibri 10 pt (9 pt allowed only for Slide 3's Deliverables column); cell margins 0.06 in left and right, 0.04 in top and bottom; text anchored top. The built-in table style is removed (no banding from PowerPoint's default style); all fills come from K.1. The `+N more` overflow row is a single merged cell spanning all columns. (3) **Key-value tables** (Slide 2 Key facts): no header row; the label column is Proxima Nova bold 10 pt on `F8FAFC`; the value column is Calibri 10 pt on `FFFFFF`. (4) **Bounds:** every shape, including a table's estimated full height, lies inside the content area (x 0.83 to 12.50 in, y 1.70 to 6.70 in); no two content shapes overlap, except that a card may contain shapes lying wholly inside it (its text frame, or a table such as Key facts); the footer and logo areas stay clear. (5) **Cover fit:** the cover title stays on one line, reducing from the layout's size down to a minimum of 28 pt. If it still does not fit, it may wrap to two lines, and the subtitle moves down so the two never overlap. (6) **Fit:** the writer estimates each text frame's rendered height (characters per line from the frame width at an average character width of 0.5 × font size; line height 1.2 × font size, plus paragraph spacing). If the estimate exceeds the frame, it reduces the font within the limits above, then uses the `+N more` row or line; it never lets text overflow and never shrinks below the minimums. | Pending (content slides verified in Rev 10 review; cover title overflows into the subtitle for long project names, for example the mock project) | `test_deck_layout.py`, INV-32 |
| DECK-22 | **Your Project Kit slide.** Slide 7 points the team to the two source documents, with a short explanation of each (Appendix K.2, Slide 7). It names each file exactly as written in the output folder, lists the Kit sections and Workbook sheets the deck draws on (traced to the actual headings and sheet names), and states that every fact in the deck traces to these two documents. It never mentions the Readiness Checklist or readiness content. | Done (verified Rev 10 review) | `test_deck_structure.py`, `test_deck_traceability.py` |
| DECK-23 | **Visual review aid.** `python -m src.tools.render_deck <deck.pptx>` renders each slide to a PNG beside the deck (using LibreOffice when available) for human review. It is a review aid only; the automated checks are DECK-21 and INV-32. | New | Manual |

## 16. Invariants

These rules must hold for every fixture and every generated output folder (QA-04). Each violation names the invariant ID.

| ID | Invariant |
| --- | --- |
| INV-01 | The Kit milestone count equals the SOW gate count (VAL-01). |
| INV-02 | The Workbook has exactly one level 1 row per SOW phase, and no other level 1 rows. |
| INV-03 | No workstream, row, dropdown value, or Source contains "Project Management", "Kickoff", "Reporting and Control", or "Ongoing", and no level 1 or 2 row has Source `PM Best Practice` (MS-08 excepted). |
| INV-04 | No Workbook cell, sheet name, defined name, or property, and no deck slide text or speaker note, matches the readiness terms (readiness, G-01, G01, gate approval, Startup Kit, mobiliz, `ACT-` followed by a digit). |
| INV-05 | The predecessor graph is acyclic and points backward only. |
| INV-06 | Every Kit deliverable appears exactly once at WBS level 3, under a gate. Every gate has a Milestone Acceptance package. |
| INV-07 | Every Kit work package has an existing parent deliverable, a valid SOW reference, and a non-placeholder owner. Each appears in the WBS as a task or as a degenerate Source ID. |
| INV-08 | Every SOW reference in the catalogue appears in the WBS SOW References (TR-01 reports none missing). |
| INV-09 | Every Kit and Checklist register ID (RSK, ISS, DEP, ASM, AMB, and non-excluded Q) appears exactly once as a RAID Source ID. |
| INV-10 | No task name exceeds 120 characters, starts with `Work Package:`, or contains an action placeholder. |
| INV-11 | No generated task has a placeholder owner. |
| INV-12 | Cross-artifact counts agree (TR-02), including G01-15 against the Checklist questions table. |
| INV-13 | No description begins with a citation prefix (`[V#]`, `Exhibit X,`). No Contract Reference ends with an empty part. |
| INV-14 | Every deliverable has evidence or the missing-evidence note. Every evidence flag names a different deliverable. |
| INV-15 | No header, template task, or builder formula contains a banned effort word (P-03). |
| INV-16 | Every date cell is a date or blank. No `None` or `null` text appears anywhere. |
| INV-17 | Decision, deliverable, work package, and milestone IDs are unique in the Kit. |
| INV-18 | The award date is not computed by the tool (VAL-05). |
| INV-19 | Every deliverable's gate equals the phase of its SOW work items, as given by the oracle (QA-08). A deliverable whose items span several phases is allowed only if the oracle lists it. |
| INV-20 | Every Kit work package's `linked_milestones` equals the oracle phase of its SOW reference. No gate holds more than its oracle share of work items. |
| INV-21 | No two work packages share a title. No title contains `implementation task`. |
| INV-22 | Evidence coverage (deliverables with non-placeholder evidence, divided by all deliverables) is at least the oracle minimum (ARC: 0.90). Every evidence text shared between deliverables carries the shared-item note. |
| INV-23 | Every Contract Reference is `Not cited`, blank (non-clarification rows), or contains a file extension, an Exhibit-type word, a SOW reference, or a section number. |
| INV-24 | The review window is the KIT-03 default or SOW text. It never contains `NOT SPECIFIED - TO BE CONFIRMED` or ends with `...`. |
| INV-25 | Nothing sits in an `Other {workstream} work` package when its Kit parent deliverable exists in another gate. |
| INV-26 | Every deck content element has a `TraceRef`, every `TraceRef` resolves in the written Kit or Workbook, and every displayed value equals its source or a clause-boundary prefix of it (DECK-05, DECK-20). The trace manifest exists beside the deck. |
| INV-27 | Slide 3 contains every gate, checkpoint, and deliverable ID from the Workbook Project Schedule; Slide 4 contains every deliverable ID; and Slide 6 accounts for every client stakeholder, communications item, and client prerequisite (DECK-07), either in a table row or in a `+N more` overflow row (DECK-07). |
| INV-28 | The deck has exactly 7 slides with the DECK-01 titles in order. The cover and Your Project Kit slides have 2 to 4 talking points and slides 2 to 6 have 3 to 6, each with a `SOURCES` line; no title exceeds 8 words and no bullet or table cell exceeds 15 words (DECK-08, DECK-09). |
| INV-29 | The deck package contains exactly 7 slide parts: slide 1 on layout `CUSTOM_1`, slides 2 to 7 on layout `CUSTOM_16`; and none of the template's original slide text (for example `DELIVERY GOVERNANCE OPERATING LAYER`) appears anywhere in it (DECK-12). |
| INV-30 | Every Workbook RAID row whose Source ID is a Kit risk or issue matches the Kit RAID Log on Probability, Impact, Owner, Mitigation / Response, Trigger / Early Warning, and Status (RAID-09). |
| INV-31 | No deck text or speaker note ends in or contains an ellipsis (`...`, `…`), leaves an unbalanced bracket, parenthesis, or quotation mark, contains doubled punctuation (`..`, `,,`), or contains a shortened name (DECK-05). Every talking point on slides 2 to 6 has a manifest entry (DECK-09). |
| INV-32 | Every deck shape, including the cover title and subtitle, lies inside its allowed area, content shapes do not overlap, every card text frame and table passes the DECK-21 fit estimate, and no font is below the DECK-21 minimums. |

## 17. Pending work, in implementation order

1. **Checks first:** extend INV-27 (Slide 6 completeness) and INV-32 (cover title and subtitle), and add `test_output_names.py`. Each must fail on the current outputs: INV-27 on ARC (8 prerequisites missing), INV-32 on the mock deck's cover, and the name test on the mock run.
2. **Fixes:** DECK-07 (Slide 6 lists every prerequisite or a `+N more` line), DECK-21 (5) cover fit, OUT-11 (one file-name rule).
3. **Carried:** QA-10.

## 18. Change log

| Revision | Change |
| --- | --- |
| 1 | Consolidates the base spec and v1 to v7 into one register. Adds the QA, VAL, and INV sections. Replaces per-run spec appendices with snapshots. |
| 2 | Review of the 2026-10-01 12:23 ARC run (Appendix E). Adds QA-08 (oracles), VAL-08, VAL-09, KIT-10, KIT-11, and INV-19 to INV-25. Revises QA-03 (the agent never applies snapshot updates), QA-05, VAL-02, MAP-03, MAP-04, MAP-06, and RAID-03. Reopens VAL-05, KIT-03, TXT-04, and CHK-06. |
| 3 | Review of the 2026-10-01 13:21 ARC run, generator v0.5.7 (Appendix F). Marks VAL-02, VAL-08, VAL-09, MAP-03, MAP-04, MAP-06, KIT-03, KIT-05, TXT-04, and CHK-06 Done. Adds VAL-10 and REF-05. Revises VAL-05, RAID-03, WBS-09, TR-02, TXT-01, and INV-12. Reopens KIT-11. Closes KIT-10: no names were supplied for the run, so `[UNASSIGNED]` is correct; the James Mora name in earlier runs came from a supplied value. |
| 4 | Review of the 2026-10-01 14:30 ARC run, generator v0.5.8 (Appendix G). Marks VAL-05, VAL-10, KIT-11, RAID-03, WBS-09, TXT-01, TR-02, and DT-05 Done. Keeps REF-05 Pending, with a decision path. Reopens CHK-03 (generic approver role). |
| 5 | Rev 4 implementation round (generator v0.5.9 and later; Appendix H). Adds P-08, QA-09, and QA-10. Marks REF-05, CHK-03, MAP-07, and RAID-05 Done. Revises MAP-05 and RAID-05 (unique-reference rule), and RAID-03 (generic label, section lists, `.txt` and `.md` citations). |
| 6 | Rev 5 implementation round (Appendix I). Replaces QA-09 with the `arc_overextracted` fixture and retires `arc_run5`. Revises RAID-03 (plural forms, no information loss) and QA-10 (stop rather than redefine). Marks MAP-05 Done. |
| 7 | Rev 6 implementation round (Appendix J). Adds QA-11. Revises QA-10 (mechanical quotes, git output), VAL-01 (renumbering with provenance), MS-04, MS-05 (checkpoint phases), and RAID-03 (consistent format). Marks QA-09, RAID-08, and FMT-03 Done. |
| 8 | Adds the Talent Team Onboarding Deck: section 15A (DECK-01 to DECK-20), INV-26 to INV-29, and Appendix K. Revises OUT-01, OUT-02, OUT-09, OUT-10, and INV-04 for the deck. Marks the Rev 7 items (VAL-01, MS-04, MS-05, KIT-02, RAID-03, QA-09, QA-11) Done. |
| 9 | Adds a cover slide to the deck (6 slides in total; cover on layout `CUSTOM_1`). Revises DECK-01, DECK-07, DECK-09, DECK-12, INV-27 to INV-29, and Appendix K; content slides renumbered 2 to 6. Confirms that `--slides` also writes the Kit and Workbook (DECK-02). |
| 10 | Review of the Rev 9 deck (Appendix L). Adds DECK-21 (layout and alignment), DECK-22 (Your Project Kit slide, making 7 slides), DECK-23 (render aid), RAID-09 and INV-30 (Kit RAID fields in the Workbook), INV-31 (text quality), and INV-32 (layout). Revises DECK-01, DECK-04, DECK-05, DECK-09, DECK-12, DECK-13, INV-28, INV-29, and Appendix K. |
| 11 | Review of the Rev 10 decks (Appendix M). Adds OUT-11. Revises DECK-04 (non-row locators), DECK-07, INV-27, DECK-08 (word target and block capacities), DECK-21 (cover fit; shapes inside cards), INV-32, and K.1 (inset 0.20 in; card height up to 5.00 in). Marks the Rev 10 deck requirements Done where verified. |

## Appendix A: Workbook column layouts

**Project Schedule:**

A WBS Code · B Row Type (`Workstream`, `Milestone`, `Checkpoint`) · C Workstream · D Milestone ID · E Milestone · F Milestone Scope · G Owner · H Planned Start · I Planned Finish · J Internal Buffer Date · K External Commitment Date · L Date Basis · M Duration (working days) · N Days to Finish · O Status · P Health · Q Predecessor · R Client Prerequisites · S Critical Path Assumptions · T Linked Deliverables · U SOW References · V Linked RAID IDs · W Source · X Notes · Y onward: timeline.

Formulas (row 6 shown):

- Duration: `=IF(OR(H6="",I6=""),"",NETWORKDAYS(H6,I6))`.
- Days to Finish: `=IF(OR(AND(K6="",I6=""),O6="Complete"),"",IF(K6<>"",K6,I6)-TODAY())`.
- Health: `=IF(O6="Complete","Complete",IF(AND(K6="",I6=""),"Date TBC",IF(TODAY()>IF(K6<>"",K6,I6),"Overdue",IF(AND(J6<>"",TODAY()>J6),"In Buffer","On Track"))))`.

Workstream rows use MIN and MAX over their child rows.

**WBS:**

A WBS Code · B Level · C Element Type · D Name · E Workstream · F Milestone ID · G Deliverable ID · H Source ID · I SOW References · J Owner · K Planned Start · L Planned Finish · M Milestone Finish · N Status · O % Complete · P Cadence (reserved, empty) · Q Predecessors · R Acceptance / Completion Criteria · S Linked RAID IDs · T Source · U Mapping Basis · V Notes.

**RAID Log:**

A RAID ID · B Type · C Description · D Contract Reference · E Category · F Workstream · G Linked Milestone · H Linked WBS Code · I Linked Deliverables · J Owner · K Probability · L Impact · M Rating · N Score (P x I) · O Trigger / Early Warning · P Mitigation / Response · Q Due Date · R Status · S Date Raised · T Last Updated · U Linked Decision · V Linked Dependency / Assumption · W Source · X Source ID · Y Notes.

## Appendix B: Templates

**B.1 Work-type templates.** The work type comes from the deliverable name: the highest keyword count wins; ties follow table order; with no hits, Build. `*` marks the core task.

| Work type | Keywords | Tasks (owner) |
| --- | --- | --- |
| Integration | integrat, api, endpoint, direct-write, interface, authentication | Confirm interface contract, credentials, and environment access (Talent PM) · `*` Build the integration (Talent PM) · Test error handling, retries, and performance targets (Talent PM) · Demo the working integration to the client (Delivery Manager) |
| Build | shell, service, frontend, micro-frontend, view, feature, component, search | Refine stories and acceptance criteria (Talent PM) · `*` Develop and configure (Talent PM) · Peer review and unit test (Talent PM) · Demo completed work to the client (Delivery Manager) |
| Test | test, suite, harness, uat, scan, validation, smoke, certification, defect, hardening, quality | Agree test scope, targets, and environment (Talent PM) · `*` Prepare test scripts, data, and fixtures (Talent PM) · Execute tests in the target environment (Talent PM) · Log defects and produce the results report (Talent PM) |
| Analysis | spike, parity, assessment, benchmark, report | Agree method, targets, and data sources (Talent PM) · `*` Perform the analysis (Talent PM) · Document findings and recommendations (Talent PM) · Review findings with the client (Delivery Manager) |
| Documentation | training, documentation, material, guide, runbook | Agree outline and audience (Talent PM) · `*` Draft the content (Talent PM) · Walk through the draft with the client (Delivery Manager) · Finalize and publish (Talent PM) |

**B.2 Work-item task verbs:** Build and Integration: `Build`; Test: `Automate and execute`; Analysis: `Complete`; Documentation: `Produce`.

**B.3 Milestone Acceptance tasks:** see WBS-05.

**B.4 Keyword taxonomy (fallback only, MS-02):** Discovery & Requirements, Design & Architecture, Build & Configuration (the default), Data & Integration, Testing & Quality Assurance, Deployment & Release, Transition & Hypercare, with the original keyword lists. Ties go to the later entry.

## Appendix C: Patterns and lists

- **Readiness filter:** `\b(G-?01|readiness\s+gate|startup\s+readiness|readiness\s+checklist|readiness\s+score|gate\s+decision)\b`.
- **Sequential-gate statement:** `run[s]?\s+(?:sequentially|in\s+sequence)|sequential\s+(?:acceptance\s+)?gates?|each\s+milestone\s+(?:is\s+an\s+acceptance\s+gate|depends\s+on\s+(?:the\s+)?acceptance\s+of\s+the\s+previous)|after\s+the\s+prior\s+milestone\s+is\s+accepted`.
- **Restatement:** `acceptance\s+review|sign-?off|gating\s+the\s+start`.
- **Stop words:** the and for with of to a an in on at by from or as is are be phase phases milestone milestones deliverable deliverables delivery project client built toptal accepted completed complete est estimated delivered week weeks related output outputs result results report reports work plus.
- **SOW_REFERENCE_PATTERNS**, in order (case-insensitive), excluding the tool's own prefixes (DEL, WP, RSK, ISS, DEP, ASM, AMB, Q, M, MS, CP, COM, DEC, ACT, ACT-REQ, RAID, G01):

```text
Story ID            \b[A-Z][A-Z0-9]{1,9}-\d{2,6}\b
Deliverable number  \bDeliverable\s+\d+(?:\.\d+)*\b
                    \bD\d+(?:\.\d+)*\b
Task or WBS code    \b(?:Task|WBS)\s+\d+(?:\.\d+)*\b
Section             \b(?:Section|Clause|§)\s*\d+(?:\.\d+)*\b
```

## Appendix D: ARC oracle (draft for `tests/oracles/arc.json`)

This is a **draft**. A person must check it against `Exhibit A - Arc Genomics Platform.pdf` before committing it. After that it is maintained only by people (QA-08). It was assembled from runs 3, 4, 5, and Rev 1, all of which agree on the phase of every reference below.

```json
{
  "fixture": "arc",
  "gate_count": 4,
  "phases": ["P1 Foundation", "P2a Services and Data", "P2b Application Surface", "P3 Launch"],
  "week_ranges": {"P1": [1, 6], "P2a": [7, 16], "P2b": [17, 21], "P3": [22, 26]},
  "sow_reference_phase": {
    "P1":  ["HS-4762", "HS-4763", "HS-4765", "HS-4938", "HS-4770", "HS-4782", "HS-4941"],
    "P2a": ["HS-4777", "HS-4778", "HS-4779", "HS-4942", "HS-4803", "HS-4804", "HS-4797", "HS-4785", "HS-4807", "HS-4801", "HS-4791"],
    "P2b": ["HS-4772", "HS-4773", "HS-4809", "HS-4810", "HS-4813", "HS-4793", "HS-4775", "HS-4815", "HS-4794", "HS-4811"],
    "P3":  ["HS-4825", "HS-4826", "HS-4828", "HS-4943", "HS-4832", "HS-4788", "HS-4829"]
  },
  "client_owned_references": ["HS-4781", "HS-4827", "HS-4824"],
  "award_date_stated_in_sow": false,
  "min_evidence_coverage": 0.90,
  "acceptance_mode": "milestone"
}
```

Totals: 35 Toptal-owned references (P1 7, P2a 11, P2b 10, P3 7). Verify the client-owned list and the award date against the SOW, because they are inferred from Kit and Checklist text.

## Appendix E: Review of the 2026-10-01 12:23 ARC run (the basis for Revision 2)

**Verdict.** Revision 1 fixed the two worst Kit defects: the Kit now has exactly 4 milestones, and every work package has a parent, a SOW reference, and an owner. But the Workbook regressed badly, and the safety net did not catch it.

**Why the safety net missed it:**

1. The fixtures were re-recorded and the snapshots regenerated in the same task, so the snapshots recorded the broken output as correct.
2. The invariants check structure (each deliverable appears once, under some gate), not correctness (under the right gate).

QA-03 (revised), QA-08, and INV-19 to INV-25 close both gaps.

| # | Finding | Evidence | Requirement |
| --- | --- | --- | --- |
| E1 | 16 of 20 deliverables placed in P1; only the four with a phase code in their name are correct | Schedule M1 Linked Deliverables lists DEL-01 to 08, 10 to 13, and 16 to 20; mapping basis `Backlog match (WP-xx)` | VAL-02, VAL-09, MAP-03, MAP-04, INV-19, INV-20 |
| E2 | Backlog work packages took their gate from a default-filled `linked_milestones` (M1). This is the exact anti-pattern VAL-04 bans for dependencies. | Kit WP table; WBS placement | VAL-02, INV-20 |
| E3 | Work package titles are filler (`<deliverable> implementation task`), repeated up to 5 times. They defeat degenerate detection and say nothing about the work. | Kit WP-03/04, WP-14 to 18, and others | VAL-08, MAP-06, INV-21 |
| E4 | P2a and P2b work packages (WP-14 to 18, WP-26 to 28) sit in `Other P1 Foundation work` | WBS 1.1.19 | INV-25 |
| E5 | Evidence coverage fell from 19 of 19 (run 5) to 13 of 20; DEL-17 holds DEL-16's UAT evidence with no shared-item note | Kit Deliverables matrix | KIT-03, INV-22 |
| E6 | Review windows regressed to `NOT SPECIFIED - TO BE CONFIRMED` or a truncated paragraph | Kit Deliverables matrix | KIT-03, INV-24 |
| E7 | Award date is still run date minus one (`Project awarded 2026-09-30`); Workbook Start Date basis says "after award" | G01-01; Workbook row 3 | VAL-05, INV-18 |
| E8 | Q-01 Contract Reference is still `schedule is` | RAID-34 | RAID-03, INV-23 |
| E9 | `Baseline - SOW Stories` Source value still used | WBS story tasks | TXT-04 |
| E10 | Guardrail description still says "escalate if budget burn rate exceeds" | Checklist Internal Escalation Thresholds | CHK-06 |
| E11 | PMO Lead name lost (`[UNASSIGNED]`, was James Mora); talent roster now 0 roles (G01-08 "0 delivery talent roles listed") | Kit charter; Checklist G01-08 | KIT-10 |
| E12 | Decision owners invented (`Delivery Lead`, `QA Lead`) | Decision Log | KIT-11 |
| E13 | **Positive:** exactly 4 milestones (M1 to M4); unique, real parents and references on all 35 work packages; one numbering system; citations stripped from contract clarification descriptions; date questions for gates only; cross-artifact counts consistent (20 deliverables, 4 RAID items, 15 dependencies and assumptions, 14 ambiguities) | Kit, Checklist | VAL-01, VAL-06, RAID-03 (partial), CHK-05 |

## Appendix F: Review of the 2026-10-01 13:21 ARC run (generator v0.5.7; the basis for Revision 3)

**Verdict.** This is the first run where the Workbook is correct against the oracle, and it is usable as the Talent PM's initial plan. Every deliverable sits in its oracle phase by `Catalogue phase`, with P1 7, P2a 11, P2b 10, and P3 7 SOW references, matching Appendix D exactly. The remaining defects are small and mostly in text quality and cross-artifact consistency. Two of them (E14 and E16 below) should have been caught by existing invariants, so the safety net still needs checking (section 17, item 1).

**Quality**

| Artifact | Assessment | Strengths | Remaining defects |
| --- | --- | --- | --- |
| Workbook | Correct and usable | 4 phase workstreams with correct predecessors (M2←M1, M3←M2, M4←M3); 19 deliverables, all in the right phase; 35 SOW work item tasks; 164 tasks with role owners; no Other-work packages; 54 RAID rows with Kit and Checklist Source IDs; Start Date basis "after generation date" | Q-09 false citation; one false evidence flag; work item tasks have no titles (`Build HS-4762`); Q-22 wording |
| Kit | Good | 4 milestones; 35 work packages with real parents, references, and owners; unique titles; evidence 19 of 19 with shared-item notes; review windows phase-specific; award date not invented; roster restored (4 roles) | SLA row says `Met` while the award date is unknown; DEC-15 owner `Technical Lead`; 7 of 15 contract ambiguities lack citations |
| Checklist | Good | G01-03, 04, 05, 08, 11, and 14 consistent with the Kit; date questions for the 4 gates only; Q-22 asks for the award date; Fixed Bid guardrails free of burn and rate wording | G01-01 `Complete` with the award date unknown; G01-15 says 21 points while there are 22 questions; the staffing guardrail still mentions "fixed capacity and sprint budget allocations" (low) |

**Traceability**

| Link | Status |
| --- | --- |
| SOW reference → work package → deliverable → gate | Complete. All 35 references trace through the Kit and Workbook, and match the oracle. |
| Kit registers (RSK, ISS, DEP, ASM, DEC, COM) → Workbook RAID Source IDs | Complete |
| Checklist AMB and Q → Workbook RAID | Complete. Role questions Q-19 to Q-21 are excluded by design; Q-22 is included. |
| Contract ambiguity → SOW clause | Partial. 7 of 15 ambiguities have no citation in the extraction, so they show `Not cited` (E17). |
| RAID → deliverable, via SOW reference | Working where references are cited (for example AMB-03 → DEL-07, 12, 13, 14) |
| Counts across artifacts | Consistent, except G01-15 (E16) |

**Findings**

| # | Finding | Evidence | Requirement |
| --- | --- | --- | --- |
| E14 | Q-09 Contract Reference `schedule impact`. The Q-01 case was patched rather than enforced as a rule, and INV-23 did not catch it. | RAID-44 | RAID-03, INV-23, section 17 item 1 |
| E15 | Kit 1-Day SLA Status `Met` and G01-01 `Complete` while the award date is not stated | Kit charter; G01-01 | VAL-05 |
| E16 | G01-15 says 21 validation points; the questions table has 22 | Checklist | TR-02, INV-12 |
| E17 | 7 of 15 contract ambiguities have no clause citation (AMB-02, 07, 09, 10, 12, 13, 15) | RAID Contract Reference `Not cited` | VAL-10 |
| E18 | Work item titles missing, so tasks read `Build HS-4762` and work packages read `HS-4762: <deliverable name>` | WBS; Kit backlog | REF-05 |
| E19 | False evidence flag: DEL-13 "may belong to DEL-03" on generic test evidence | WBS 3.1.5 | WBS-09 |
| E20 | Q-22 reads "formal project baseline contract award" | RAID-54 | TXT-01 |
| E21 | DEC-15 owner `Technical Lead`. The PMO Lead `[UNASSIGNED]` is correct, because no names were supplied for this run. | Kit | KIT-11 (KIT-10 closed) |
| E22 | The predecessor note cites `(M1)` rather than the source dependency or assumption ID | Schedule M2 Notes | DT-05 (verify) |


## Appendix G: Review of the 2026-10-01 14:30 ARC run (generator v0.5.8; the basis for Revision 4)

**Verdict.** Revision 3 is implemented correctly, and the artifacts are fit for use. `check_artifacts` passed every invariant. The Workbook still matches the oracle exactly (P1 7, P2a 11, P2b 10, P3 7 references; 20 deliverables, all in their oracle phases). Every Appendix F defect except E18 (work item titles) is fixed. The ARC recording was re-captured for this revision (20 deliverables, 12 dependencies and assumptions, 14 ambiguities, 20 questions), and the oracle checks still pass on it.

| Appendix F item | Result |
| --- | --- |
| E14 Q-09 false citation | Fixed. Every question shows a real reference or `Not cited`. |
| E15 SLA and G01-01 | Fixed. `Not determinable - award date not stated`; G01-01 `Confirmation Required`. |
| E16 G01-15 count | Fixed. 20 validation points, 20 questions. |
| E17 Contract citations | Fixed. All 14 ambiguities carry a document, section, or SOW reference citation. |
| E18 Work item titles | Open. Fallback titles on all 35 work packages (REF-05). |
| E19 False evidence flag | Fixed. No flags. |
| E20 Q-22 wording | Fixed. The award-date question reads naturally. |
| E21 Decision owners | Fixed. Owners are PMO Lead, Delivery Manager, Client Sponsor, or Toptal. |
| E22 Predecessor note | Fixed. Cites `DEP-02`. |

**New finding**

| # | Finding | Requirement |
| --- | --- | --- |
| E23 | G01-03 is `Complete` with no exception, while every deliverable's approver is the unnamed role "Client's designated approvers" and Q-02 asks for their names | CHK-03 |

**Traceability.** Complete within the run: SOW reference → work package → deliverable → gate; Kit and Checklist register IDs → RAID Source IDs; contract ambiguities → SOW clauses. Cross-artifact counts all agree.


## Appendix H: Rev 4 implementation round (the basis for Revision 5)

**Outcome.** REF-05 and CHK-03 are complete. Work item titles now come from extraction: the oracle's three sample titles match exactly, and `git grep HS-4 -- src` is empty. The round needed four passes, because each one uncovered a new problem.

| Pass | Problem found in review | Resolution |
| --- | --- | --- |
| 1 | The agent reported that the SOW had no story titles, giving examples and a "Table 3.1" that are not in the SOW | A person checked the PDF ("Build automated pipeline quality gates and deployment smoke checks (HS-4770)"); oracle sample titles were added |
| 2 | mock_sow: WP-03 mapped to DEL-02 through the shared "Section 3.1" reference; ARC work package tasks lost their SOW References; cross-type "Covered by" notes appeared | Fixed: unique-reference matching, SOW References on tasks, Test vs Build filtering |
| 3 | `ARC_KNOWN_REF_TITLES` (and hard-coded ARC phases) in `src\llm\validation.py` filled titles when extraction returned none; the sample-title test compared only 4 words | Removed (`b655c2f`); extraction prompt changed (`e0bed1b`); ARC re-recorded in its own commit (`7ed4459`); exact title comparison; P-08 added |
| 4 | mock_sow: RAID-05 linked to M1, M2 and all three deliverables through "Section 3.1" | Fixed with one shared unique-reference helper for work package mapping and RAID linking |

**Snapshots promoted at the end of the round:**

- `arc_genomics`: re-recorded extraction. It was checked against the oracle and the earlier requirements: P1 7, P2a 11, P2b 10, P3 7 references; 19 deliverables in their correct phases; exact sample titles; evidence 19 of 19; G01-03 `Review Required`; G01-15 equal to 23 questions; valid contract references; SOW References on every work package task.
- `mock_sow`: no change.
- `no_story_ids`: no change.
- `numbered_deliverables`: 7 RAID items gained correct links to the deliverables their `Deliverable N.N` references name, for example `Deliverable 3.1` → DEL-05 in M3.

**Open items carried into Revision 5:** the RAID-03 label and section list, `arc_run5` integrity (QA-09), and the MAP-05 order.

**Process lesson.** Three of the four problems were visible only in the review, not in the agent's report. QA-10 makes reports evidence-based. P-08 and its test make hard-coded data fail automatically.


## Appendix I: Rev 5 implementation round (the basis for Revision 6)

**Findings**

| # | Finding | Requirement |
| --- | --- | --- |
| I1 | `arc_run5` was created in `6ce46f1` as `arc_run4.model_copy()`, so it never held the 10-milestone run. The Rev 5 agent then made the integrity test assert 4 milestones, which redefines QA-09 instead of reporting that it could not be met. | QA-09, QA-10 |
| I2 | On a synthetic 10-milestone baseline, the agent reports 6 checkpoints. ARC's 10 milestones should reconcile to 4 gates, 3 merged restatements, and 3 checkpoints. | VAL-01, MS-04, MS-05 |
| I3 | Citation stripping drops plural forms. no_story_ids "sow.txt, Sections 2 and 4:" becomes Contract Reference `sow.txt`, losing the sections from both the reference and the description. numbered_deliverables RAID-11 "(Deliverables 2.2 and 3.1)" loses both references. | RAID-03 |
| I4 | **Correct:** the "SOW refs:" label; singular section lists; `.txt` citations; parent link evaluated first (no work package moved in any fixture). | RAID-03 (partial), MAP-05 |

**The 10-milestone ARC run (generator v0.5.5, 2026-10-01 10:12): the Kit's Milestone Delivery Plan, summarised for transcription when the `.docx` is not available**

| ID | Description (start) | Role |
| --- | --- | --- |
| M1 | P1 Foundation accepted: micro-frontend shell, Azure AD/MSAL authentication, E2E test harness, pipeline quality gates, data validation (est. weeks 1–6) | P1 gate |
| M2 | P1 Foundation milestone acceptance review and Client sign-off, gating the start of P2a | Restatement → merge into M1 |
| M3 | P2a Services and Data accepted: FastAPI endpoints, async processing, OneGWAS integration, performance spike, ingestion validation (est. weeks 7–16) | P2a gate |
| M4 | P2a Services and Data milestone acceptance review and Client sign-off, gating the start of P2b | Restatement → merge into M3 |
| M5 | P2b Application Surface accepted: ARC search and detail views, haplotype features, nomenclature service, test suites (est. weeks 17–21) | P2b gate |
| M6 | P2b Application Surface milestone acceptance review and Client sign-off, gating the start of P3 | Restatement → merge into M5 |
| M7 | P3 Launch integration, performance, security and cross-browser testing completed | Checkpoint → CP-01 |
| M8 | UAT execution completed with Client scientist groups (at most two UAT runs) | Checkpoint → CP-02 |
| M9 | Production smoke tests and 48-hour defect watch completed | Checkpoint → CP-03 |
| M10 | P3 Launch accepted: hardening, MTA Store parity confirmation, training materials (est. weeks 22–26) | P3 gate |


## Appendix J: Rev 6 implementation round (the basis for Revision 7)

**Outcome.** `arc_overextracted` exists, and reconciliation works on the real 10-milestone case: 3 restatements merged, exactly 3 checkpoints (CP-01 testing, CP-02 UAT, CP-03 smoke tests) before the P3 gate, and predecessors M3←M1, M5←M3, M10←M5. Plural citations now parse ("Sections 2 and 4" gives `2, 4`; "Deliverables 2.2 and 3.1" links both), with no information loss.

| # | Finding | Requirement |
| --- | --- | --- |
| J1 | The report "quoted" requirement rows that are not in the spec. The spec file was verified unchanged by its MD5 fingerprint, so the quotes were invented. | QA-10 |
| J2 | The report gave "337 passed, 0 failed"; plain `pytest -q` showed 337 passed and 5 failed (the snapshot tests). | QA-10 |
| J3 | All Rev 6 work was left uncommitted. The spec itself had never been committed to git. | QA-10, QA-11 |
| J4 | Gates keep their extracted IDs (M1, M3, M5, M10) instead of being renumbered M1 to M4. | VAL-01, MS-04 |
| J5 | CP-02 and CP-03 have phase `N/A` in the Kit's Interim Checkpoints table. | MS-05, KIT-02 |
| J6 | ARC contract references with a recognised document citation drop the `SOW refs` part, while other rows keep it. | RAID-03 |


## Appendix K: Talent Team Onboarding Deck design

### K.1 Template and style tokens

- **Canvas:** 13.33 × 7.5 in (16:9), from the template.
- **Cover layout:** `CUSTOM_1` on master 1, with title placeholder (idx 0) at 1.33, 3.09 in (11.37 × 0.75 in) and subtitle placeholder (idx 1) at 1.33, 3.84 in (11.37 × 0.57 in), plus the footer and logo. The cover keeps the layout's own placeholder styling (Proxima Nova; no font overrides), matching the template's cover.
- **Content layout:** `CUSTOM_16` on master 1, with title placeholder (idx 0) at 0.29, 0.22 in (12.76 × 0.70 in) and kicker placeholder (idx 1) at 0.29, 0.84 in (12.76 × 0.53 in). The layout also supplies the `Confidential | <slide number>` footer and the logo.
- **Content area:** x 0.83 to 12.50 in, y 1.70 to 6.70 in. Nothing is placed outside it.
- **Cards:** white rounded rectangles, `E2E8F0` outline; three across at x 0.83, 4.81, 8.79 in (3.71 × 4.58 in each, from the template), or two across at x 0.83 and 6.75 in (5.75 in wide each). Text inset 0.20 in. All cards on a slide share one height: 4.58 in by default, up to 5.00 in (the bottom of the content area) when the content needs it (Slides 2 and 4 on ARC).
- **Tables:** header `204ECF` with white Proxima Nova bold 12 pt; body Calibri 10 to 11 pt `0F172A` (first column bold) and `475569`; rows alternate `F8FAFC` and `FFFFFF`; borders `E2E8F0`.
- **Placeholder text:** `To be confirmed`, Calibri italic, `204ECF`.
- **Card headings (fixed labels, chosen to fit on one line):** Slide 2 `Key facts`, `Purpose & delivery`, `Phases & scope`; Slide 4 `How acceptance works`; Slide 6 `Client roles`, `Working rhythm`, `Client prerequisites`; Slide 7 `Startup Kit`, `Project Delivery Workbook`.
- **Table column widths (inches):** Slide 2 Key facts: 1.35 and 1.96. Slide 3: Workstream 2.00, Milestone 2.60, Dates 1.90, Deliverables 5.17. Slide 4: ID 0.80, Acceptance Criteria 6.00, Gate 0.89. Slide 5: ID 1.50, Item 3.70, Rating 0.85, Owner 1.60, Response 3.00, Phase 1.02.

### K.2 Slides

**Slide 1: Cover** (layout `CUSTOM_1`)

| Element | Content | Source (`TraceRef`) |
| --- | --- | --- |
| Title | `{Project Name}` | Kit · header table (Project Name) |
| Subtitle | `Talent Team Onboarding · {Client Sponsor} · Start {Start Date}` (`Talent Team Onboarding` and `Start` are fixed labels) | Kit · header table (Client Sponsor); Workbook · Project Schedule title row 3 (Start Date) |

Nothing else is placed on the cover. Talking points (2 to 4): who the deck is for (the Talent PM and the Talent Project Team) and how to use the notes; the project and client; the start date and whether it was provided or assumed. The cover title is exempt from the 8-word title limit (DECK-08), because it is the project's name.

The five content slides use layout `CUSTOM_16`, with the kicker `{PROJECT NAME} · TALENT TEAM ONBOARDING`. Capacities are maximums for the DECK-07 overflow row and the DECK-08 fit check.

**Slide 2: Project Charter**

| Element | Content | Source (`TraceRef`) | Capacity |
| --- | --- | --- | --- |
| Left card, "Key facts" | Two-column table: Client Sponsor; Contract Type; Governance Tier; Start Date (with its basis); Talent PM; Delivery Manager; PMO Lead | Kit · header table (Client Sponsor, Contract Type, Governance Tier, Talent PM, Delivery Manager, PMO Lead); Workbook · Project Schedule title row 3 (Start Date and basis) | 7 rows |
| Middle card, "Purpose & delivery" | The purpose sentence; the delivery model; the escalation path | Kit · Project Startup Charter (Project Purpose & Delivery Baseline; Delivery Model & Governance Tier; Escalation Path & Decision Hierarchy) | 3 blocks |
| Right card, "Phases & scope" | The phase workstreams in order, as bullets; then "Out of scope" bullets | Workbook · Project Schedule (Workstream rows); Kit · SOW Interpretation Summary (Explicit Exclusions & Out-of-Scope) | 4 + 4 bullets, then `+N more` |

Talking points: the purpose in one sentence; the contract type and governance tier; who leads delivery and how issues escalate; the start date and whether it was provided or assumed; the number of phases.

**Slide 3: Workstreams, Milestones, Deliverables and Dates**

A single table, one row per Workbook Project Schedule level 2 row, in Schedule order, grouped by workstream:

| Column | Content | Source |
| --- | --- | --- |
| Workstream | Phase workstream name (on its first row only) | Workbook · Project Schedule · Workstream |
| Milestone | `{Milestone ID}: {Milestone}`; checkpoints shown as `{CP ID}: {name}` in italic | Workbook · Project Schedule · Milestone ID, Milestone |
| Dates | `{Planned Start} – {Planned Finish}`; `To be confirmed` when blank | Workbook · Project Schedule · Planned Start, Planned Finish |
| Deliverables | `DEL-xx {name}` per line when the slide has at most 20 deliverables; IDs only when more | Workbook · Project Schedule · Linked Deliverables; names from Kit · Deliverables and Acceptance Matrix |

Capacity: 12 table rows. Talking points: number of phases and the overall date span; each gate's predecessor chain (from the Workbook Predecessor column); the date basis (for example `SOW estimate, weeks 1–6`); checkpoints inside phases, if any.

**Slide 4: Acceptance Criteria**

| Element | Content | Source | Capacity |
| --- | --- | --- | --- |
| Left card, "How acceptance works" | The approval expectation (first sentence); then the Milestone Acceptance steps of the first gate, in order: the level 4 tasks under the WBS level 3 element named `{first gate ID} Milestone Acceptance` (for ARC, WBS `1.1.7`), in WBS code order, and nothing else; then the review window and client approver | Kit · SOW Interpretation Summary (Approval & Acceptance Expectations); Workbook · WBS (task names, keyed by WBS code, for example `1.1.7.1`); Kit · Deliverables and Acceptance Matrix (review window and client approver of the first deliverable; `To be confirmed` if a placeholder) | 1 sentence + 6 steps + 2 facts |
| Right, table | One row per deliverable: `DEL-xx` · acceptance criteria (first clause, at most 15 words) · gate | Kit · Deliverables and Acceptance Matrix (acceptance criteria); Workbook · WBS (deliverable's gate) | 14 rows, then the overflow row |

Talking points: acceptance is per milestone or per deliverable (WBS-04 mode); the evidence expected before submission; how rejection and rework work (Kit rework path); the number of deliverables whose criteria are still to be confirmed.

**Slide 5: High-Risk Items**

Selection (deterministic): Workbook RAID Log rows of type Risk or Issue whose Rating (DECK-20) is `High`, ordered by Score descending, then RAID ID. If fewer than 3 qualify, add the next highest-scored Risks and Issues until there are 3. At most 6 rows; if more qualify, the last row is the `+N more` overflow row listing their RAID IDs. Contract clarifications and open questions have no Probability or Impact, so they are never selected.

| Column | Content | Source |
| --- | --- | --- |
| ID | RAID ID, with the Kit Source ID in brackets (for example `RAID-03 (RSK-02)`) | Workbook · RAID Log · RAID ID, Source ID |
| Item | Description, first clause | Workbook · RAID Log · Description |
| Rating | Rating (High, Medium, Low), with a light red, amber, or green cell fill (`FEE2E2`, `FEF3C7`, `DCFCE7`) | Workbook · RAID Log · Probability and Impact (DECK-20) |
| Owner | Owner | Workbook · RAID Log · Owner |
| Response | Mitigation / Response, first clause; `To be confirmed` only if both the Workbook and the Kit are empty | Workbook · RAID Log · Mitigation / Response (populated per RAID-09) |
| Phase | Linked Milestone's workstream, or `Cross-phase` | Workbook · RAID Log · Workstream |

Talking points: how many High items there are in total; the early-warning trigger of each shown item (Trigger / Early Warning column); who to raise new risks with (the escalation path from Slide 2's source).

**Slide 6: Client Collaboration**

Three cards:

| Card | Content | Source | Capacity |
| --- | --- | --- | --- |
| "Client roles" | Stakeholders whose Organization is `Client`: role, then decision rights (first clause) | Kit · Stakeholder and Responsibility Model | 5 bullets, then `+N more` |
| "Working rhythm" | Communications plan items: `{Report / Meeting}: {Cadence}` | Kit · Communications and Reporting Plan | 7 bullets, then `+N more` |
| "Client prerequisites" | Client prerequisites, earliest gate first: `{gate}: {prerequisite}` | Workbook · Project Schedule · Client Prerequisites | 6 bullets, then `+N more (see Project Delivery Workbook · Project Schedule)` |

Talking points: who signs off each milestone; the main meetings and when they happen; the first client prerequisite and when it is needed (the gate's Planned Start); the number of open questions waiting on the client (Workbook RAID Log rows with Category `Open Question`).

**Slide 7: Your Project Kit**

Two cards side by side (two-across geometry), then one line across the bottom of the content area.

| Element | Content | Source |
| --- | --- | --- |
| Left card, "Startup Kit" | File name (`{project}_Startup_Kit.docx`); one fixed line: `The approved project baseline: scope, deliverables and acceptance, governance, and RAID.`; subheading `Sections used in this deck`, then the Kit section headings named in the SOURCES lines of slides 1 to 6, in Kit order | Kit file name in the output folder; Kit section headings |
| Right card, "Project Delivery Workbook" | File name (`{project}_Project_Delivery_Workbook.xlsx`); one fixed line: `The working delivery plan: schedule by phase, tasks, and the RAID Log.`; subheading `Sheets`, then each sheet name with a fixed purpose: `Project Schedule: gates, dates, and client prerequisites`; `WBS: deliverables and tasks, with acceptance steps`; `RAID Log: risks, issues, dependencies, and open questions` | Workbook file name in the output folder; Workbook sheet names |
| Bottom line | Fixed text: `Every fact in this deck traces to these two documents. Each slide's notes list its sources.` | Fixed label |

Talking points (2 to 4, fixed guidance allowed): both files sit in the same folder as this deck; the Startup Kit is the approved baseline and changes to it go through the escalation path on Slide 2; the Workbook is the plan to keep current as work progresses; each slide's SOURCES note says which section or sheet to open for detail.

### K.3 Example talking-point templates

```text
The project runs in {phase_count} phases, from {first_start} to {last_finish}.
{gate_id} ({phase}) is due {planned_finish}; it starts after {predecessor_id} is accepted.
Acceptance happens at a milestone review: {first_three_steps}.
{high_count} risks are rated High; the first to watch is {raid_id}: {first_clause}.
Before {phase} starts on {planned_start}, the client must provide: {prerequisite}.
```

Each placeholder is filled only with a traced value. A template whose value is missing is skipped, never filled with a guess.

### K.4 Expected ARC results (from the current fixture and oracle)

These follow from the oracle (Appendix D) and the Rev 7 ARC outputs, and are asserted by `test_deck_arc.py` alongside the deck snapshot:

- **Slide 1 (Cover):** title `ARC Genomics Platform`; subtitle `Talent Team Onboarding · Syngenta · Start 2026-10-05`.
- **Slide 2:** Client Sponsor `Syngenta`; Contract Type `Fixed Bid`; Governance Tier `Partnered`; Start Date `2026-10-05 (Provided)`; Talent PM, Delivery Manager, and PMO Lead `To be confirmed` (no names supplied); phases P1 Foundation, P2a Services and Data, P2b Application Surface, P3 Launch.
- **Slide 3:** 4 gates, M1 to M4, one per phase, from 2026-10-05 to 2027-04-02; every deliverable ID in the Workbook appears exactly once.
- **Slide 4:** every deliverable ID appears exactly once; acceptance is milestone-level.
- **Slide 5:** RAID-01 (RSK-01), RAID-02 (RSK-02), RAID-05 (RSK-05), and RAID-07 (ISS-01), all rated High (RAID-07 is High Probability, Medium Impact).
- **Slide 6:** 6 client stakeholders (5 shown, then `+1 more`); 7 communications items (COM-01 to COM-07).
- **Slide 4:** the acceptance steps are the 6 tasks of WBS `1.1.7` (M1 Milestone Acceptance), starting `Prepare milestone acceptance package and evidence`.
- **Slide 5:** each Response is RAID-01's to RAID-07's Kit mitigation (first clause), for example RAID-01 begins `Use query observability (HS-4942)`.
- **Slide 7:** `ARC_Genomics_Platform_Startup_Kit.docx` and `ARC_Genomics_Platform_Project_Delivery_Workbook.xlsx`; sheets Project Schedule, WBS, RAID Log.
- **Names shown whole:** DEL-07 `Backend Integration/Load Tests and Performance Engineering Spike`; DEL-17 `Production Smoke Tests and 48-Hour Defect Watch`.
- **Everywhere:** no `ACT-` tags, no readiness score, no G-01, and 100% of elements traced.


## Appendix L: Review of the Rev 9 ARC deck (the basis for Revision 10)

**Verdict.** The structure is right: 6 slides on the correct layouts, template slides removed, every gate and deliverable ID present, no readiness content. But the text and layout fail review, and INV-26 passed defects it should have caught.

| # | Finding | Evidence | Requirement |
| --- | --- | --- | --- |
| L1 | Text in cards crowded at the top, headings wrapping into body text, lower half of cards empty, tiny body fonts | Slides 2, 4, 6 | DECK-21 |
| L2 | Title rendered blue and regular weight, kicker large; cards with a large default corner radius | All content slides | DECK-13 |
| L3 | Tables: very tall header rows, poor column widths, PowerPoint default banding (Key facts table shows a blue "header" on its first data row) | Slides 2, 3, 5 | DECK-21 |
| L4 | The `+N more` overflow row sits in the narrow ID column, wraps past the slide bottom, and overlaps the footer | Slide 4 | DECK-21, INV-32 |
| L5 | Ellipses and mid-phrase cuts: `by the...`, `sharing...`, `(Snowflake sizing,`, `(code library, tokens, design files, guidelines`, `(limited to two` | Slides 4, 5, 6 | DECK-05, INV-31 |
| L6 | Shortened names: DEL-07 loses `Spike`, DEL-17 loses `Watch` | Slide 3 | DECK-05 |
| L7 | "Milestone Acceptance Process" lists client prerequisites and build tasks (`Confirm: ...`, `Refine stories`, `Build HS-4762`) instead of the M1 Milestone Acceptance tasks (WBS 1.1.7) | Slide 4 | Appendix K.2 |
| L8 | Response column empty for every row, because the Workbook's Mitigation / Response is empty for Kit RAID rows (a Workbook defect) | Slide 5; Workbook RAID-01 to RAID-07 | RAID-09, INV-30 |
| L9 | Talking points include filler and untraced claims (`Mitigations and proactive response ownership are assigned...`, `Active alignment ensures...`), doubled punctuation (`platform..`), and mid-phrase cuts | Notes, slides 2, 4, 5, 6 | DECK-09, INV-31 |
| L10 | The manifest uses invented keys (`M1 Step 1`, `Title Row 3`) and has no talking-point entries | Trace manifest | DECK-04, DECK-09 |
| L11 | INV-26 and the deck tests passed all of the above | Agent report: check_artifacts exit 0 | Section 17, item 1 |

**Requested addition:** a final slide pointing the team to the Startup Kit and the Project Delivery Workbook, with a short explanation of each (DECK-22).


## Appendix M: Review of the Rev 10 decks (the basis for Revision 11)

Both decks (ARC from replay; Pfizer from the mock run) were rendered with LibreOffice and checked against their Kit and Workbook.

**Verdict.** The deck is now fit for use on ARC. Layout, styling, traceability, and talking points meet the spec. Every Appendix L finding is fixed, and the Workbook carries the Kit's mitigations (RAID-09; root cause: the builder read `trigger` and `mitigation` instead of `trigger_or_early_warning` and `mitigation_or_response`). Three defects remain.

| # | Finding | Evidence | Requirement |
| --- | --- | --- | --- |
| M1 | Slide 6 shows 4 of ARC's 12 client prerequisites (the first of each gate), with no `+N more` line, because each Workbook cell holds several prerequisites separated by `; ` | ARC slide 6; Workbook Project Schedule column R | DECK-07, INV-27 |
| M2 | The cover title wraps onto the subtitle for a long project name | Mock deck slide 1: `Pfizer Analytics & Cloud Modernization` | DECK-21 (5), INV-32 |
| M3 | Output file names differ within one run: the Kit uses a double underscore | `Pfizer_Analytics__Cloud_Modernization_Startup_Kit.docx` vs `Pfizer_Analytics_Cloud_Modernization_Project_Delivery_Workbook.xlsx` | OUT-11 |

**Implementation decisions accepted from the Rev 10 round (report section 8):** card height up to 5.00 in on slides that need it; text inset 0.20 in; DECK-05 takes precedence over the 15-word target, with INV-28 accepting a longer line only when it is a whole name or no compliant cut exists within 15 words (DECK-08 revised); K.2 block capacities take precedence over the 6-bullet limit, counting each subheading group as a block (DECK-08 revised); a card may contain shapes wholly inside it (DECK-21 revised); locators `Header table` and fields `File name`, `Section heading`, and `Sheet name` for non-row facts (DECK-04 revised); Trigger / Early Warning compared at model level only, because the Kit has no trigger column; Rev 9 deck tests rewritten for the 7-slide deck rather than loosened; steps 3 to 5 committed together.
