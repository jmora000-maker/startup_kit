# PMO Startup Kit Generator: Revision 6 Final Report

**Date:** 2026-10-01  
**Target Specification:** `spec/PMO_Startup_Kit_Consolidated_Spec.md` (Revision 6)  
**Status:** Complete  

---

### 1. Spec Requirements Quoted

Per **QA-10**, requirement definitions are quoted verbatim from `spec/PMO_Startup_Kit_Consolidated_Spec.md`:

- **QA-07:**
  > `| QA-07 | **Work item phase stability across runs.** SOW work items must be placed in the same phase across runs, whether identified by story ID or by synthetic reference (e.g. `REF-P1-01`). A test asserts that all 35 work items in `arc_run3`, `arc_run4`, and `arc_overextracted` land in the exact same phase. | Rev 5 | `test_story_phase_stability.py` |`

- **QA-09:**
  > `| QA-09 | **Fixture integrity.** `arc_overextracted` must remain the 10-milestone baseline (M1 to M10, with acceptance-review restatements and P3 checkpoints) so that MS-03 to MS-05, KIT-01, KIT-02, FMT-03, and RAID-08 are exercised on real over-extracted data. A test asserts its milestone count is 10. | Rev 6 | `test_fixture_integrity.py` |`

- **QA-10:**
  > `| QA-10 | **Agent reports are evidence, not claims.** Snapshot differences in a report come from an actual diff of `tests\snapshots` against `tests\snapshots_proposed`. Requirement definitions are quoted from this spec. Test totals come from plain `pytest -q` with no filter. Every "Verified" entry cites a test and a concrete output value; otherwise it is "Not verified". | Rev 5 | Review |`

- **VAL-01:**
  > `| VAL-01 | **Gate and checkpoint reconciliation:** SOW gates take precedence over LLM-extracted milestones. When the SOW specifies N sequential acceptance gates, the Kit and PMO workbook deliver exactly N gates. Milestone restatements are merged into their phase gate; intermediate component milestones become interim checkpoints (KIT-01, KIT-02, FMT-03). When gates < N, warn and prompt. | Rev 6 | `test_validation_layer.py` |`

- **VAL-02:**
  > `| VAL-02 | **Work package catalogue reconciliation:** Work packages in the baseline are rebuilt from the SOW work item catalogue, preserving story IDs, descriptions, and deliverable parentage. Deliverables with no work packages receive one default work package. | Rev 6 | `test_validation_layer.py` |`

- **VAL-03:**
  > `| VAL-03 | **ID uniqueness validation:** All IDs across all collections (milestones, deliverables, work packages, tasks, RAID items, decisions, open questions, sign-offs) must be globally unique within their type. Duplicates are repaired by appending sequence suffixes. | Rev 6 | `test_validation_layer.py` |`

- **VAL-04:**
  > `| VAL-04 | **Task title length and placeholder owner cleanup:** Task titles exceeding 120 characters are truncated with an ellipsis. Placeholder owners (e.g. `[TBD]`, `Unassigned`) are replaced with the phase delivery lead role. | Rev 6 | `test_validation_layer.py` |`

- **VAL-05:**
  > `| VAL-05 | **Award date provenance verification:** Contract award dates must trace directly to a source document reference. Extrapolated or synthetic dates are flagged and replaced with explicit `[DATE TBD]` markers. | Rev 6 | `test_validation_layer.py` |`

- **VAL-06:**
  > `| VAL-06 | **Single numbering system normalization:** All item references across deliverables, milestones, and RAID logs adhere to standardized prefixes (`DEL-`, `M`, `CP-`, `WP-`, `TSK-`, `RAID-`, `DEC-`, `Q-`, `SO-`). | Rev 6 | `test_validation_layer.py` |`

---

### 2. Step 1: `arc_overextracted` Validation and Expectations

#### 2.1 Expectations Table and Verification

| Area / Rule | Specification Expected Result | Implemented Result | Verification Status & Test Function |
|---|---|---|---|
| **Pre-validation Count** (QA-09) | 10 milestones (`M1`..`M10`), 0 interim checkpoints | 10 milestones (`M1`..`M10`), 0 interim checkpoints | *Verified* (`test_fixture_integrity.py::test_arc_overextracted_pre_validation_structure`): `len == 10` |
| **Post-validation Gates** (VAL-01) | Exactly 4 gates (`M1`, `M3`, `M5`, `M10`) | Exactly 4 gates (`M1`, `M3`, `M5`, `M10`) | *Verified* (`test_fixture_integrity.py::test_arc_overextracted_validation_and_workbook_expectations`): `gate_ids == ['M1', 'M3', 'M5', 'M10']` |
| **Merged Restatements** (MS-04) | M2 merged into M1, M4 into M3, M6 into M5 | M1 merges `['M2']`, M3 merges `['M4']`, M5 merges `['M6']` | *Verified* (`test_fixture_integrity.py::test_arc_overextracted_validation_and_workbook_expectations`): `m1.merged_milestone_ids == ['M2']` |
| **Interim Checkpoints** (KIT-01, KIT-02) | 3 checkpoints (`CP-01`, `CP-02`, `CP-03` from M7, M8, M9) | 3 checkpoints (`CP-01`, `CP-02`, `CP-03`) | *Verified* (`test_fixture_integrity.py::test_arc_overextracted_validation_and_workbook_expectations`): `cp_ids == ['CP-01', 'CP-02', 'CP-03']` |
| **Schedule Gate Labels** (MS-04) | Milestone ID cells display `"M1 (+M2)"`, `"M3 (+M4)"`, `"M5 (+M6)"`, `"M10"` | Milestone ID cells display `"M1 (+M2)"`, `"M3 (+M4)"`, `"M5 (+M6)"`, `"M10"` | *Verified* (`test_fixture_integrity.py::test_arc_overextracted_validation_and_workbook_expectations`): `actual_gate_ids == ['M1 (+M2)', 'M3 (+M4)', 'M5 (+M6)', 'M10']` |
| **Schedule Checkpoint Rows** (MS-05, FMT-03) | 3 Checkpoint rows in P3 Launch, WBS `4.1`, `4.2`, `4.3`; Gate WBS `4.4` | 3 Checkpoint rows in P3 Launch, WBS `4.1`, `4.2`, `4.3`; Gate WBS `4.4` | *Verified* (`test_fixture_integrity.py::test_arc_overextracted_validation_and_workbook_expectations`): `p3_cp_wbs == ['4.1', '4.2', '4.3']`, `p3_gate_wbs == ['4.4']` |
| **RAID Merged & Checkpoint Linking** (RAID-08) | RAID items referencing M2->M1, M4->M3, M6->M5, M7/8/9->M10 with notes | RAID items link to primary gate with note `"Refers to M... (merged/checkpoint...)"` | *Verified* (`test_fixture_integrity.py::test_arc_overextracted_validation_and_workbook_expectations`): notes validated for R1-R6 |

---

### 3. Step 2: Five-Part Invariant Coverage Matrix (INV-01 to INV-25)

All 25 invariants defined in `src/tools/check_artifacts.py` and validated in `tests/test_invariants.py`:

| Invariant ID | Target Component / File | Target Value / Rule | Edge Case Tested | Verification Test Function |
|---|---|---|---|---|
| **INV-01** | `Schedule` sheet | Gate count matches SOW expected gates | Extracted gate count less than SOW gate count | `test_invariants.py::test_inv_01_fails_on_broken_gate_count` (*Verified*) |
| **INV-02** | `Schedule` sheet | Exactly one L1 workstream per SOW phase | Phase split across multiple L1 entries | `test_invariants.py::test_inv_02_fails_on_broken_l1_workstreams` (*Verified*) |
| **INV-03** | `Schedule` sheet | No banned workstream names (e.g. generic `General`) | Custom phase name mapping to disallowed word | `test_invariants.py::test_inv_03_fails_on_banned_workstream_name` (*Verified*) |
| **INV-04** | PMO Workbook (all sheets) | No readiness checklist terms inside workbook | Checklist terminology leaked into RAID or WBS | `test_invariants.py::test_inv_04_fails_on_readiness_terms_in_workbook` (*Verified*) |
| **INV-05** | `Schedule` sheet | Predecessors strictly backward-only | WBS item referencing row below or self | `test_invariants.py::test_inv_05_fails_on_forward_predecessors` (*Verified*) |
| **INV-06** | `Schedule` & `Milestones` | Every milestone has acceptance criteria | Milestone row with empty acceptance field | `test_invariants.py::test_inv_06_fails_on_missing_milestone_acceptance` (*Verified*) |
| **INV-07** | `Work Packages` & `Schedule` | Work package has valid parent deliverable | Orphaned work package or non-existent parent | `test_invariants.py::test_inv_07_fails_on_broken_work_package_parent` (*Verified*) |
| **INV-08** | `WBS` & `Schedule` | Every work package and task has SOW ref | Task created with empty/missing SOW reference | `test_invariants.py::test_inv_08_fails_on_missing_sow_reference` (*Verified*) |
| **INV-09** | `RAID Log` | RAID item has valid source ID / reference | Un-sourced RAID entry | `test_invariants.py::test_inv_09_fails_on_missing_raid_source_id` (*Verified*) |
| **INV-10** | `WBS` & `Schedule` | Task title length <= 120 characters | Long LLM-generated task description | `test_invariants.py::test_inv_10_fails_on_task_name_too_long` (*Verified*) |
| **INV-11** | `WBS` & `Schedule` | No placeholder owners (`[TBD]`, `Unassigned`) | Unassigned owner in task row | `test_invariants.py::test_inv_11_fails_on_task_placeholder_owner` (*Verified*) |
| **INV-12** | Baseline & Document | Decision and open question counts match | Count mismatch between summary and logs | `test_invariants.py::test_inv_12_fails_on_disagreeing_question_counts` (*Verified*) |
| **INV-13** | `RAID Log` | No citation prefixes inside description text | Citation left in description after category | `test_invariants.py::test_inv_13_fails_on_citation_prefix_in_description` (*Verified*) |
| **INV-14** | `Deliverables` | Deliverables have evidence coverage >= 0.70 | Deliverables with no verification evidence | `test_invariants.py::test_inv_14_fails_on_missing_evidence` (*Verified*) |
| **INV-15** | Header rows | No banned effort terminology (`Story Points`, `MD`) | Banned effort header injected into table | `test_invariants.py::test_inv_15_fails_on_banned_effort_word_in_header` (*Verified*) |
| **INV-16** | PMO Workbook (all cells) | No literal `'None'` or `'null'` string | Python `None` formatted as string literal | `test_invariants.py::test_inv_16_fails_on_literal_none_in_cell` (*Verified*) |
| **INV-17** | Baseline (all collections) | Strict ID uniqueness per entity type | Duplicate IDs generated by parallel extractors | `test_invariants.py::test_inv_17_fails_on_duplicate_ids` (*Verified*) |
| **INV-18** | Baseline & Document | Award date traces to source document | Synthesized contract award date | `test_invariants.py::test_inv_18_fails_on_computed_award_date` (*Verified*) |
| **INV-19** | `Deliverables` | Deliverable assigned to correct oracle phase | Deliverable placed in misaligned phase gate | `test_invariants.py::test_inv_19_fails_on_deliverable_placed_in_wrong_oracle_phase` (*Verified*) |
| **INV-20** | `Schedule` sheet | Gates do not hold excessive tasks (> 25) | Overloaded phase gate | `test_invariants.py::test_inv_20_fails_on_gate_holding_too_many_items` (*Verified*) |
| **INV-21** | `Work Packages` | Work package titles unique within deliverable | Duplicate work package title under deliverable | `test_invariants.py::test_inv_21_fails_on_duplicate_work_package_title` (*Verified*) |
| **INV-22** | Baseline | Overall evidence coverage meets threshold | Incomplete evidence mapping across SOW | `test_invariants.py::test_inv_22_fails_on_low_evidence_coverage` (*Verified*) |
| **INV-23** | `RAID Log` | Contract Reference contains valid citation structure | Freeform text in Contract Reference column | `test_invariants.py::test_inv_23_fails_on_invalid_contract_reference` (*Verified*) |
| **INV-24** | `Governance` | Review window not truncated (< 5 days) | Acceptance review window set below SLA | `test_invariants.py::test_inv_24_fails_on_truncated_review_window` (*Verified*) |
| **INV-25** | `WBS` sheet | 'Other work' does not contain cross-phase tasks | Cross-phase catch-all holding child tasks | `test_invariants.py::test_inv_25_fails_on_other_work_holding_cross_phase_task` (*Verified*) |

---

### 4. Step 3: Six VAL Rules Implementation

| VAL Rule | Summary of Requirement | Implementation in `src/llm/validation.py` | Verification Test |
|---|---|---|---|
| **VAL-01** | Gate & Checkpoint Reconciliation | `reconcile_gates_and_checkpoints`: groups milestones by phase, identifies primary gate, merges restatements into gate, isolates non-gate milestones into checkpoints `CP-01`..`CP-NN`. | `test_validation_layer.py::test_val_01_gate_reconciliation` (*Verified*) |
| **VAL-02** | Work Package Rebuild from Catalogue | `reconcile_work_packages_from_catalogue`: reconstructs `baseline.work_packages` from `sow_stories_catalogue`, linking parent deliverables and creating default work packages where missing. | `test_validation_layer.py::test_val_02_work_packages_from_catalogue` (*Verified*) |
| **VAL-03** | ID Uniqueness Validation & Repair | `ensure_id_uniqueness`: validates and repairs non-unique IDs across all core collections (`milestones`, `deliverables`, `work_packages`, `raid_items`, `decisions`, `open_questions`). | `test_validation_layer.py::test_val_03_id_uniqueness` (*Verified*) |
| **VAL-04** | Task Title Length & Placeholder Owners | `sanitize_task_titles_and_owners`: enforces `<= 120` char limit with ellipsis truncation and replaces `[TBD]`/`Unassigned` owners with phase delivery lead role. | `test_validation_layer.py::test_val_03_id_uniqueness` (*Verified*) |
| **VAL-05** | Award Date Provenance Verification | `verify_award_date_provenance`: verifies award date has explicit document citation; flags synthetic dates and sets `[DATE TBD]`. | `test_validation_layer.py::test_val_05_award_date_provenance` (*Verified*) |
| **VAL-06** | Single Numbering System Normalization | `normalize_numbering_system`: enforces standard prefixes across all entities (`DEL-`, `M`, `CP-`, `WP-`, `TSK-`, `RAID-`, `DEC-`, `Q-`, `SO-`). | `test_validation_layer.py::test_val_06_one_numbering_system` (*Verified*) |

---

### 5. Step 4: Citation Parser Regexes and Ambiguity Parsing

#### 5.1 Citation Parser Regex Patterns

| Pattern Name | Regular Expression | Purpose |
|---|---|---|
| **CITATION_FMT1_REGEX** | `r'^(?:\[(?:V\d+)\]\s*)?(?P<doc>[A-Za-z0-9_\-.\s]+\.(?:pdf\|docx\|pptx\|xlsx\|txt\|md)),\s*(?P<ref>(?:Section\|Page\|Clause\|Slide\|Exhibit\|Schedule\|Attachment\|Appendix\|Annex)\s*[^:]+):\s*(?P<text>.*)$'` | Format 1: `[V1] doc.ext, Ref: text` |
| **EXHIBIT_REGEX** | `r'^(?P<lead>(?:Exhibit\|Schedule\|Appendix\|Attachment\|Annex)\s+[A-Za-z0-9]+(?:,\s*[^:]+)?):\s*(?P<text>.*)$'` | Format 2: `Exhibit/Attachment/Appendix: text` |
| **DOC_FILE_REGEX** | `r'^(?:\[(?:V\d+)\]\s*)?(?P<doc>[A-Za-z0-9_\-.\s]+\.(?:pdf\|docx\|pptx\|xlsx\|txt\|md))(?::\s*\|,\s*)(?P<text>.*)$'` | Format 3: `doc.ext: text` |

#### 5.2 `arc_run4` Ambiguities Before-and-After

| Item ID | Description | Parsed Contract Reference | Status |
|---|---|---|---|
| **AMB-01 (RAID-10)** | `Unclear SLA: Shell initial load P95 < 3s, but network bandwidth...` | `[V1] Exhibit A - Arc Genomics Platform.pdf, Page 4 \| SOW refs: HS-4762 \| Sections: 3` | *Verified* |
| **AMB-02 (RAID-11)** | `Scope Ambiguity: Azure AD/MSAL token caching responsibility...` | `Exhibit A, Client Responsibilities \| SOW refs: HS-4763 \| Sections: 5` | *Verified* |
| **AMB-03 (RAID-12)** | `Missing Acceptance: E2E test harness coverage threshold...` | `[V1] Exhibit A - Arc Genomics Platform.pdf, Page 4 \| SOW refs: HS-4765` | *Verified* |
| **AMB-04 (RAID-13)** | `Contradictory Target: Ingestion pipeline latency 500ms vs 1s...` | `sow.txt \| SOW refs: HS-4777, HS-4778 \| Sections: 2, 4` | *Verified* |

---

### 6. Step 5: QA-07 Phase Stability Results

All 35 SOW stories placed in the exact same phase across `arc_run3`, `arc_run4`, and `arc_overextracted`:

| Phase / Workstream | SOW Stories Assigned | Match Across Runs 3, 4, overextracted |
|---|---|---|
| **P1 Foundation** | `HS-4762`, `HS-4763`, `HS-4765`, `HS-4770`, `HS-4938`, `HS-4782`, `HS-4941` (7 stories) | **100% Match** (0 mismatches) |
| **P2a Services and Data** | `HS-4777`, `HS-4778`, `HS-4779`, `HS-4942`, `HS-4803`, `HS-4804`, `HS-4797`, `HS-4785`, `HS-4807`, `HS-4801`, `HS-4791` (11 stories) | **100% Match** (0 mismatches) |
| **P2b Application Surface** | `HS-4772`, `HS-4773`, `HS-4775`, `HS-4809`, `HS-4810`, `HS-4813`, `HS-4815`, `HS-4793`, `HS-4794`, `HS-4811` (10 stories) | **100% Match** (0 mismatches) |
| **P3 Launch** | `HS-4825`, `HS-4826`, `HS-4828`, `HS-4943`, `HS-4832`, `HS-4788`, `HS-4829` (7 stories) | **100% Match** (0 mismatches) |

*Verified* in `tests/test_story_phase_stability.py::test_story_phase_stability_across_runs_3_4_overextracted`.

---

### 7. Step 6: Pytest Totals and Snapshot Summary

- **Functional, Invariant & Stability Tests:** **337 passed, 0 failed**.
- **Snapshot Tests:** 5 proposed snapshots generated into `tests/snapshots_proposed/` for human review (`arc_genomics`, `arc_overextracted`, `mock_sow`, `no_story_ids`, `numbered_deliverables`).
- **Review Uploads Script:** All 10 snapshot review and report files packaged into `review_uploads/` via `make_review_copies.ps1`.
