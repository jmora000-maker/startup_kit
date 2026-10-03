# Revision 13 Final Implementation & Verification Report

**Date:** 2026-10-02  
**Specification:** `spec/PMO_Startup_Kit_Consolidated_Spec.md` (Revision 13)  
**Status:** Complete & Fully Verified  

---

### 1. Executive Summary & Overview

Revision 13 addresses all findings in **Appendix O** (O1 through O5) identified during the verification of Revision 12 against the `arc_application_implementation` fixture:

1. **Part 1 (QA-12 / Finding O1)**: Eliminated loose substring matching (`"arc" in folder_str`) in `check_artifacts.py`, implementing strict exact-match-first oracle resolution with a centralized fallback alias map in `src/config.py`.
2. **Part 2 (CHK-07, WBS-05 / Findings O2, O4)**: Fixed Checklist `G01-04` evidence generation to count acceptance gates only (excluding interim checkpoints like `CP-01`), and updated `WBS-05` Milestone Acceptance Review tasks to use clean communications plan item names without approver/audience expansion.
3. **Part 3 (DECK-07 / INV-27, DECK-21 / Findings O3, O5)**: Corrected Slide 5 High-Risk table capacity accounting (reserving space for the `+N more` overflow row so maximum body rows never exceed 6), and implemented independent shrink-to-fit logic for the cover subtitle down to 16 pt for longer client entity names.

All invariant checks on `arc_application_implementation` now **PASS with 0 violations**, and zero regressions were introduced across all existing fixtures in the test corpus.

---

### 2. Recap of Parts 1 and 2

#### Part 1: QA-12 Exact-Match-First Oracle Resolution (Finding O1)
- **Problem**: `load_oracle_for_folder` in `src/tools/check_artifacts.py` matched any folder containing `"arc"` to `tests/oracles/arc.json`, causing `arc_application_implementation` to load the wrong oracle when run without `--oracle` and producing a false `INV-18` violation.
- **Fix**: Implemented candidate extraction (exact project name slug and folder name) to check `tests/oracles/{candidate}.json` first before falling back to `ORACLE_ALIAS_MAP` in `src/config.py`.
- **Commit**: `a364d6d QA-12: exact-match-first oracle resolution, replacing the arc substring fallback`
- **Evidence**: `tests/test_oracle_resolution.py` unit tests pass 100%.

#### Part 2: CHK-07 Checklist Gate Counting & WBS-05 Task Naming (Findings O2, O4)
- **CHK-07 (Finding O2)**: Synchronized Checklist `G01-04` evidence generation (`src/scoring/readiness_engine.py`) to count gates only (`len(baseline.milestones)`), resolving the 5-vs-4 mismatch with Table 3.
  - **Commit**: `682e96a CHK-07: Checklist gate counts exclude checkpoints, matching the Kit`
- **WBS-05 (Finding O4)**: Removed audience suffix expansion (`for {c_aud}`) in `src/generators/pmo_workbook/builder.py`, generating plain `Milestone Acceptance Review` task names.
  - **Commit**: `49a2710 WBS-05: Milestone Acceptance task name uses plain communications item name without audience expansion`
- **Evidence**: `tests/test_checklist_gate_counting.py` and `tests/test_wbs_05_task_name.py` pass 100%; resolved `INV-12`, `INV-26`, and both `INV-31` occurrences on `arc_application_implementation`.

---

### 3. Part 3 Detailed Implementation & Findings

#### Fix 1: DECK-07 / INV-27 — Slide 5 Risk Table Capacity Accounting (Finding O3)

##### 1. Problem Identification
In `src/generators/onboarding_deck/builder.py` (`fit_rows`), the initial row selection took `n = min(len(all_rows), capacity)`. When 7 qualifying items existed and `capacity = 6`, `n` was initialized to 6, and because `n < len(all_rows)` (6 < 7), an overflow row was appended, resulting in 6 real rows + 1 overflow row = **7 total body rows** (exceeding the 6-row capacity and triggering `INV-27`).

##### 2. Implementation
Updated `fit_rows` so that when `len(all_rows) > capacity`, initial real rows are capped at `max(1, capacity - 1)`:
```python
def fit_rows(
    table: TableSpec,
    all_rows: List[RowSpec],
    capacity: int,
    overflow: Callable[[List[RowSpec]], RowSpec],
    avail_h: float,
) -> int:
    """Show as many rows as fit within `capacity` and `avail_h`; the rest go into one merged `+N more` row."""
    if len(all_rows) <= capacity:
        n = len(all_rows)
    else:
        n = max(1, capacity - 1)
    while True:
        shown = all_rows[:n]
        rows = list(shown)
        if n < len(all_rows):
            rows.append(overflow(all_rows[n:]))
        table.rows = rows
        size_table(table)
        if table.height <= avail_h + 1e-6 or n <= 1:
            return len(all_rows) - n
        n -= 1
```

##### 3. Unit Tests & Boundary Verification
Added to `tests/test_deck_completeness.py`:
- `test_slide5_capacity_counts_overflow_row_with_eight_risks`: Confirms 8 risks produce exactly 5 real rows + 1 `+3 more` row (6 total rows).
- `test_slide5_capacity_boundary_case_with_six_risks`: Confirms exactly 6 risks produce all 6 real rows with **no overflow row**.
- **Commit**: `754a891 DECK-07/INV-27: Slide 5 capacity counts the overflow row, never adds a 7th`

---

#### Fix 2: DECK-21 / INV-32 — Cover Subtitle Independent Shrink-to-Fit (Finding O5)

##### 1. Problem Identification
In `src/generators/onboarding_deck/writer.py` (`_fit_cover`), only the cover title had a shrink-to-fit loop from layout size down to `L.TITLE_PT` (28 pt). The subtitle remained fixed at its default layout size (23 pt). For longer client names such as `"Syngenta Crop Protection, LLC"`, the subtitle text `"Talent Team Onboarding · Syngenta Crop Protection, LLC · Start 2026-10-07"` required 0.77 in of height against a 0.57 in frame, causing an `INV-32` violation.

##### 2. Implementation
Added an independent shrink-to-fit rule for the cover subtitle from layout size (23 pt) down to 16 pt before calculating top offsets:
```python
    # DECK-21 (5): cover subtitle shrink-to-fit from layout size (23 pt) down to 16 pt
    sub_text = sub.text_frame.text
    sub_base = _inherited_size_pt(sub) or 23.0
    sub_size = sub_base
    sl, sr = _inherited_insets_in(sub)
    sub_width_in = ls.width / 914400.0 - sl - sr
    while sub_size > 16.0 and L.wrap_lines(sub_text, sub_width_in, sub_size) > 1:
        sub_size -= 1.0
    if sub_size != sub_base:
        for p in sub.text_frame.paragraphs:
            for run in p.runs:
                run.font.size = Pt(sub_size)

    if cover_title_lines(text, width_in, size) > 1:
        wanted_top = lt.top + int(round(cover_title_height_in(text, width_in, size) * 914400))
        sub_need = int(round(L.text_height_pt(sub_text, sub_width_in, sub_size) / 72.0 * 914400))
        sub_bottom = ls.top + ls.height
        sub_top = max(ls.top, min(wanted_top, sub_bottom - sub_need))
        sub.left, sub.top, sub.width, sub.height = ls.left, sub_top, ls.width, sub_bottom - sub_top
```

##### 3. Unit Tests & Composition Verification
Added to `tests/test_deck_layout.py`:
- `test_cover_subtitle_shrinks_to_fit_for_longer_client_name`: Proves subtitle shrinks to fit on 1 line for `"Syngenta Crop Protection, LLC"` with 0 violations.
- `test_cover_title_two_line_and_subtitle_shrink_compose_correctly`: Proves wrapped 2-line title and shrunk subtitle compose properly on the cover without placeholder overflow or overlap.
- **Commit**: `c851ee0 DECK-21: cover subtitle has its own shrink-to-fit rule, independent of the title`

---

### 4. Final Verification Results

#### 1. Artifact Check on `arc_application_implementation`
Ran `check_artifacts` without any explicit `--oracle` CLI flag (relying on `QA-12` exact-match resolution):

```powershell
& .venv\Scripts\python.exe -m src.tools.check_artifacts output/arc_application_implementation
```

**Raw Output:**
```
PASSED: All artifacts in 'output\arc_application_implementation' satisfy all invariants.
```

#### 2. Full Test Suite Execution Summary
Executed `pytest -q` across the entire project test suite:

```
5 failed, 563 passed in 704.58s (0:11:44)
```

*(Note: The 5 failed tests are exclusively the artifact snapshot assertions in `tests/test_snapshots.py` for the 5 parameterized fixtures awaiting snapshot promotion; all 563 unit, integration, invariant, and validation tests pass).*

---

### 5. Complete Snapshot Accounting (Revision 13)

| Fixture Name | Status vs. Approved Snapshot | Summary of Changes & Root Cause |
|---|---|---|
| `arc_genomics` | **Differs** (37 diff lines) | Task naming in WBS and Slide 4 updated from `"Milestone Acceptance Review for Client designated approvers and Toptal delivery team"` to `"Milestone Acceptance Review"` (**Part 2: WBS-05**). |
| `arc_overextracted` | **Differs** (37 diff lines) | Task naming in WBS and Slide 4 updated from `"Milestone Acceptance Review for Client designated approvers and Toptal delivery team"` to `"Milestone Acceptance Review"` (**Part 2: WBS-05**). |
| `mock_sow` | **Differs** (127 diff lines) | Schedule title reflects provided start date (`2026-09-30 (Provided)`), normalized spacing (**Rev 12 / VAL-11**). |
| `no_story_ids` | **Differs** (4,050 diff lines) | Schedule title reflects provided start date (`2026-09-30 (Provided)`), phase workstream naming (`Phase 1 Architecture and Core Foundation`), deliverable review windows (**Rev 12: VAL-11, MS-02, KIT-03**). |
| `numbered_deliverables` | **Differs** (1,038 diff lines) | Schedule title reflects provided start date (`2026-09-30 (Provided)`), phase workstream naming (`Phase 1 Ingestion Setup`), deliverable review windows (**Rev 12: VAL-11, MS-02, KIT-03**). |

*Neither `DECK-07` nor `DECK-21` introduced diffs to any of the 5 existing fixtures, as none had >=6 risks on Slide 5 or long client names requiring subtitle shrinking.*

---

### 6. Git Status and Commit History

#### Working Tree Status (`git status`)
```
On branch main
Your branch is ahead of 'origin/main' by 8 commits.
  (use "git push" to publish your local commits)

nothing to commit, working tree clean
```

#### Commit Log (`git --no-pager log --oneline -15`)
```
c851ee0 DECK-21: cover subtitle has its own shrink-to-fit rule, independent of the title
754a891 DECK-07/INV-27: Slide 5 capacity counts the overflow row, never adds a 7th
e6070b6 Proposed snapshots for Rev 13 (CHK-07, WBS-05)
49a2710 WBS-05: Milestone Acceptance task name uses plain communications item name without audience expansion
682e96a CHK-07: Checklist gate counts exclude checkpoints, matching the Kit
a364d6d QA-12: exact-match-first oracle resolution, replacing the arc substring fallback
a66205b rev 13 spec
e84792c docs: add Rev 12 final report
81a15ea part 2 prompt
ebc2330 Proposed snapshots for Rev 12
178efb6 KIT-03: propagate contract-wide review window to all deliverables
9b60cd6 VAL-11: recognize explicit award/start date statements
569dce4 MS-02: recognize wrapped Milestone N (PX Name) phase labels
bfd47f0 MS-02: recognize wrapped Milestone N (PX Name) phase labels
1fbbd6d INV-33, INV-34, INV-35: invariant checks and unit tests
```
