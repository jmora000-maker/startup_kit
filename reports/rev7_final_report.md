# Revision 7 Final Report: PMO Startup Kit

## 1. Raw Select-String Output for Cited Requirements

```text
spec\PMO_Startup_Kit_Consolidated_Spec.md:129:| VAL-01 | Reconcile extracted milestones to SOW gates. Overarching phase acceptance gates take precedence over intermediate milestone completion. Gates are renumbered M1 to MN in delivery order, saving each gate's extracted ID and any merged IDs as provenance. Non-gate milestones become interim checkpoints (CP-01..CP-n) or merge into their phase gate. |
spec\PMO_Startup_Kit_Consolidated_Spec.md:154:| MS-04 | Reconciled phase gates use their renumbered milestone ID (M1..MN) in the Kit, Checklist, and Workbook. The Workbook Milestone ID column shows "M1 (+M2)" only when receiving an unreconciled baseline (defensive path); on reconciled baselines, it shows "M1". The Notes column records provenance: "Extracted as M3; includes M4 (acceptance review and sign-off)". RAID rows and open questions referencing an extracted milestone ID are relinked to the renumbered gate with the note "Refers to extracted M4 (now M2)". |
spec\PMO_Startup_Kit_Consolidated_Spec.md:155:| MS-05 | Every checkpoint has a phase, assigned using the MS-02 attachment rules. Checkpoints are never assigned "N/A" or left blank in any artifact. |
spec\PMO_Startup_Kit_Consolidated_Spec.md:162:| KIT-02 | The Interim Checkpoints table includes columns for Checkpoint ID, Phase, Description, and Source Reference. The Phase column contains the checkpoint's assigned delivery phase (e.g. P3), never "N/A" or blank. |
spec\PMO_Startup_Kit_Consolidated_Spec.md:175:| RAID-03 | Contract Reference column hygiene: strip leading document citations and format as "<doc> | SOW refs: <stories> | Sections: <sections>". When a document citation is recognised, still append " | SOW refs: ..." and " | Sections: ..." for every SOW reference and section number it contains. Multiple sections format as "Sections: X, Y", never trailing commas. Never produce empty parts or dangling delimiters. Invariant: no information loss between raw input and Contract Reference / Description. |
spec\PMO_Startup_Kit_Consolidated_Spec.md:195:| QA-10 | Strict requirement adherence. If any requirement cannot be satisfied as written, STOP and report the blocker immediately. Never change a test or a requirement's meaning so that the current state passes. |
spec\PMO_Startup_Kit_Consolidated_Spec.md:196:| QA-11 | Spec protection. Never modify anything under spec\. All changes are made in implementation, tests, or reports. |
```

---

## 2. Step 1: Gate Renumbering and Provenance (VAL-01 / MS-04)

### Model Provenance Change
The `Milestone` model in `src/core/models.py` was extended with an additive field:
```python
extracted_ids: List[str] = Field(
    default_factory=list,
    description="Original extracted milestone ID(s) and any merged IDs as provenance (e.g. ['M3', 'M4'])"
)
```

### arc_overextracted Verification
- Reconciled Gates: 4 sequential gates `M1`, `M2`, `M3`, `M4`
- Extracted IDs and Merges:
  - `M1`: Extracted as `M1`, merged `M2` (`extracted_ids = ['M1', 'M2']`)
  - `M2`: Extracted as `M3`, merged `M4` (`extracted_ids = ['M3', 'M4']`)
  - `M3`: Extracted as `M5`, merged `M6` (`extracted_ids = ['M5', 'M6']`)
  - `M4`: Extracted as `M10` (`extracted_ids = ['M10']`)
- Predecessors in Schedule:
  - `M1`: Predecessor = `""`
  - `M2`: Predecessor = `"1.1"` (Gate M1)
  - `M3`: Predecessor = `"2.1"` (Gate M2)
  - `M4`: Predecessor = `"3.1"` (Gate M3)
- Checkpoints: `CP-01`, `CP-02`, `CP-03` placed before `M4` in Workstream P3 Launch.

#### Quoted Schedule Milestone ID and Notes Cells:
| WBS Code | Milestone ID | Name | Predecessors | Notes |
| :--- | :--- | :--- | :--- | :--- |
| 1.1 | M1 | P1 Foundation accepted: shell and IAM | | Extracted as M1; includes M2 (acceptance review and sign-off) |
| 2.1 | M2 | P2a Services and Data accepted: API and ingestion | 1.1 | Extracted as M3; includes M4 (acceptance review and sign-off) |
| 3.1 | M3 | P2b Application Surface accepted: frontend | 2.1 | Extracted as M5; includes M6 (acceptance review and sign-off) |
| 4.4 | M4 | P3 Launch accepted: rollout and testing | 3.1 | Extracted as M10 |

#### Quoted Relinked RAID Rows:
| RAID ID | Type | Description | Linked Milestone | Notes |
| :--- | :--- | :--- | :--- | :--- |
| RAID-01 | Risk | Risk regarding M2 sign-off turnaround | M1 | Refers to extracted M2 (now M1) |
| RAID-02 | Dependency | Dependency on M4 client approval | M2 | Refers to extracted M4 (now M2) |
| RAID-03 | Issue | Issue with M6 acceptance review | M3 | Refers to extracted M6 (now M3) |
| RAID-04 | Risk | Risk during M7 cross-browser testing | M4 | Refers to extracted M7 (checkpoint of M4) |
| RAID-05 | Dependency | Dependency on M8 UAT scientist group | M4 | Refers to extracted M8 (checkpoint of M4) |
| RAID-06 | Issue | Issue during M9 production smoke test | M4 | Refers to extracted M9 (checkpoint of M4) |

### ARC (arc_genomics) Milestone IDs
ARC Genomics already has 4 sequential gates (`M1`, `M2`, `M3`, `M4`). Its proposed snapshot shows **no milestone ID changes** in Schedule or elsewhere.

---

## 3. Step 2: Checkpoint Phases (MS-05 / KIT-02)

### arc_overextracted Checkpoint Verification
In both the Startup Kit document (`*_Startup_Kit.docx`) and the Project Delivery Workbook (`*_Project_Delivery_Workbook.xlsx`), every checkpoint has a valid phase.

#### Quoted Kit Interim Checkpoints Table Rows:
| Checkpoint ID | Phase | Description | Source Reference |
| :--- | :--- | :--- | :--- |
| CP-01 | P3 | P3 Cross-browser and regression testing completed | Project Baseline |
| CP-02 | P3 | P3 User acceptance testing (UAT) completed | Project Baseline |
| CP-03 | P3 | P3 Production deployment smoke tests completed | Project Baseline |

#### Invariant and Broken-Input Test
- Invariant added in `src/tools/check_artifacts.py`: Under `INV-01`, verifies that no checkpoint in Kit or Workbook has a blank or "N/A" phase.
- Unit test added in `tests/test_invariants.py`: `test_inv_01_fails_on_checkpoint_blank_or_na_phase` corrupts a checkpoint phase to `"N/A"` and verifies that `check_artifacts_directory` fails with `INV-01`.

---

## 4. Step 3: Consistent Document Citation Format (RAID-03)

### Formatting Rules Implemented
Document citations recognised via `[V1]`, file extensions (`.pdf`, `.docx`, etc.), or Exhibit/Attachment prefixes consistently append ` | SOW refs: ...` and ` | Sections: ...` for all contained story references and section numbers.

#### Quoted ARC Genomics Contract Clarifications:
- **RAID-21**:
  - `contract_reference`: `Exhibit A - Arc Genomics Platform.pdf | SOW refs: HS-4781 | Sections: 7, 6`
- **RAID-24**:
  - `contract_reference`: `Exhibit A - Arc Genomics Platform.pdf | SOW refs: HS-4779, HS-4775, HS-4794, HS-4804, HS-4825 | Sections: 3, 4`
- **RAID-26**:
  - `contract_reference`: `Exhibit A - Arc Genomics Platform.pdf | SOW refs: HS-4762, HS-4772, HS-4775, HS-4825, HS-4942 | Sections: 4`

#### Unit Test
- Added `test_raid_03_arc_genomics_citations` to `tests/test_raid_03.py`, validating the exact references for RAID-21, RAID-24, and RAID-26.

---

## 5. Files Changed per Step

- **Step 1 (VAL-01, MS-04)**:
  - `src/core/models.py`: Added `extracted_ids` to `Milestone`.
  - `src/llm/validation.py`: Renumbered reconciled gates `M1` to `MN` and stored `extracted_ids` provenance.
  - `src/generators/pmo_workbook/builder.py`: Implemented provenance notes formatting and unreconciled defensive display.
  - `src/generators/pmo_workbook/mapping.py`: Relinked RAID items referencing extracted IDs with provenance notes.
  - `tests/test_fixture_integrity.py`: Updated assertions for renumbered gates and provenance notes.
- **Step 2 (MS-05, KIT-02)**:
  - `src/generators/docx_generator.py`: Output checkpoint phase in Interim Checkpoints table.
  - `src/extractors/startup_kit_docx_parser.py`: Ingested checkpoint phase.
  - `src/tools/check_artifacts.py`: Added INV-01 invariant check requiring non-empty, non-N/A checkpoint phase.
  - `tests/test_invariants.py`: Added `test_inv_01_fails_on_checkpoint_blank_or_na_phase` broken-input test.
- **Step 3 (RAID-03)**:
  - `src/generators/pmo_workbook/builder.py`: Unified contract reference parsing to consistently append SOW refs and Sections.
  - `tests/test_raid_03.py`: Added `test_raid_03_arc_genomics_citations`.
- **QA & Unit Test Alignment**:
  - `tests/test_citation_parser.py`: Updated assertions to match Rev 7 citation format.
  - `tests/test_contract_reference.py`: Updated assertions to match Rev 7 citation format.
  - `tests/test_validation_layer.py`: Updated `test_val_01_gate_reconciliation` for M1..M4 gate renumbering.
  - `tests/snapshots_proposed/`: Generated proposed snapshots for all fixtures.

---

## 6. Exact Pytest Summary Line

```text
5 failed, 339 passed in 105.36s
```
*(All 5 failures are snapshot comparison tests in `tests/test_snapshots.py` for human review and promotion per Revision 7 rules).*

---

## 7. Snapshot Differences Summary

Diff between `tests/snapshots` and `tests/snapshots_proposed`:
- **`arc_genomics`**:
  - RAID rows citing Exhibit A with SOW references (e.g. RAID-21, RAID-24, RAID-26) now consistently format `contract_reference` as `Exhibit A - Arc Genomics Platform.pdf | SOW refs: ... | Sections: ...`.
  - Milestone IDs in Schedule and RAID logs remain unchanged (`M1` to `M4`).
- **`arc_overextracted`**:
  - Reconciled gates in Workbook Schedule and Kit renumbered from `M1, M3, M5, M10` to `M1, M2, M3, M4`.
  - Schedule Notes display provenance: `Extracted as M1; includes M2 (acceptance review and sign-off)`, etc.
  - Checkpoints `CP-01`, `CP-02`, `CP-03` display phase `P3` instead of `N/A`.
  - RAID rows referencing extracted IDs (e.g. M2, M4, M6, M7, M8, M9) are relinked to the renumbered gates `M1`, `M2`, `M3`, `M4` with note `Refers to extracted MX (now MY)`.
- **`no_story_ids`**, **`numbered_deliverables`**, **`mock_sow`**:
  - Contract Clarification rows in RAID logs adopt the unified ` | SOW refs: ... | Sections: ...` format without trailing commas or dangling delimiters.

---

## 8. Verification Outputs

- `git grep -n HS-4 -- src`: Empty (Rule P-08 satisfied).
- `git --no-pager log --oneline -- spec`: Shows no commits by assistant (Rule QA-11 satisfied).
- `python main.py --mock --non-interactive --all && python -m src.tools.check_artifacts output`: Exit code 0, all invariants passed.
- `python main.py --llm-cache replay --start-date 2026-10-05 --all --non-interactive && python -m src.tools.check_artifacts output`: Exit code 0, all invariants passed.

---

## 9. Repository Status and Git Log

### Raw Output of `git status`
```text
On branch main
Your branch is ahead of 'origin/main' by 7 commits.
  (use "git push" to publish your local commits)

nothing to commit, working tree clean
```

### Raw Output of `git --no-pager log --oneline -15`
```text
bfc8fbb QA-10: commit Revision 7 final report
c8154ab Proposed snapshots for Rev 7
f8095eb QA-10: update unit test assertions to match Rev 7 gate renumbering and citation formats
81a6278 RAID-03: consistent SOW refs and Sections format on recognized document citations
902d03a MS-05/KIT-02: every checkpoint has a phase
376d6da VAL-01/MS-04: renumber reconciled gates M1 to MN with provenance
f34d248 spec 6 changes
6d67daa Spec Revision 7
8916d16 checkpoint
```
