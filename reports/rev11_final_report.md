# Revision 11 final report

Branch: `main` at `75383d6` when this report was written (working tree clean before the report). Generated 2026-10-02.
All requirement text below comes from `Select-String` output (section 6). Every "Verified" entry cites a test or a command and a concrete output value; anything else is listed in section 7 as not verified.

## 1. What Parts 1 and 2 did

**Part 1: checks first.** Extended INV-27 to Slide 6 (every client stakeholder, communications item, and `; `-separated client prerequisite must be a bullet or covered by that card's `+N more` line); extended INV-32 to the cover title and subtitle; added `tests/test_output_names.py` (OUT-11). Each was shown failing on the unfixed outputs: INV-27 on ARC Slide 6 (8 of 12 prerequisites missing, no `+N more` line), the name test on the mock run (Kit and Checklist with a double underscore). The INV-32 cover check first **passed** on the unfixed mock deck, because the shared estimator puts the 38-character title on exactly one line at 43 pt. Work stopped there; the decision was a cover-only 1.15 width margin (`COVER_TITLE_WIDTH_SAFETY` in `src/tools/deck_checks.py`), leaving the shared estimator `L.text_height_pt` unchanged. With it, the mock cover failed as required. Part 1's commit is `259e6bb` (titled "rev 11 spec", not the planned message; it arrived with the merge `4c3f20c`).

**Part 2: fixes (one commit each).**
- `ae2c2d6` DECK-07: Slide 6 lists each prerequisite as `{gate}: {prerequisite}`, capacity 6, then `+N more (see Project Delivery Workbook · Project Schedule)`. INV-26 resolves `; ` segments as source items for the Workbook `Client Prerequisites` field only (approved).
- `beee63b` then `75383d6` DECK-21 (5): the writer reduces the cover title from the layout size down to 28 pt until the estimate says one line. The writer and INV-32 share `cover_title_lines` / `cover_title_height_in` / `COVER_TITLE_WIDTH_SAFETY` from `deck_checks.py` (single source of truth). Each cover shape must lie inside its **own** layout placeholder rectangle. A title that still wraps keeps its placeholder; the subtitle moves down only within its own placeholder's bottom edge. A title needing more slack than that (3 lines at 28 pt) is not auto-resolved: INV-32 reports it (known, correctly failing limit; no fallback chosen).
- `4933ded` OUT-11: `formatting.sanitize_filename` is the only implementation (spaces and underscores collapse to one underscore; empty becomes `Project`); the duplicates in `docx_generator.py` and `kit_values.py` were removed. File names that changed: the mock Kit and Checklist (`Pfizer_Analytics__Cloud_Modernization_...` became `Pfizer_Analytics_Cloud_Modernization_...`). `test_docx_generator.test_sanitize_filename` previously pinned the double underscore and was updated.
- `b5e0a28` Proposed snapshots for Rev 11 (`tests/snapshots` untouched).

Nothing under `spec/`, `tests/oracles/` or `tests/snapshots/` was modified, `--update-snapshots` was never run, and no LLM calls were made (ARC ran in `--llm-cache replay`, the other run with `--mock`).

## 2. `pytest -q` (plain, no filter)

```

tests\test_snapshots.py:63: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_snapshots.py::test_artifact_snapshots[arc_genomics] - Asser...
FAILED tests/test_snapshots.py::test_artifact_snapshots[arc_overextracted] - ...
FAILED tests/test_snapshots.py::test_artifact_snapshots[mock_sow] - Assertion...
FAILED tests/test_snapshots.py::test_artifact_snapshots[no_story_ids] - Asser...
FAILED tests/test_snapshots.py::test_artifact_snapshots[numbered_deliverables]
5 failed, 548 passed in 164.21s (0:02:44)
```

Final summary line: **5 failed, 548 passed in 164.21s (0:02:44)**. The only failures are the five snapshot tests, which fail because the approved snapshots have not been promoted (section 5).

Named tests for the Rev 11 requirements (`pytest -v`, run separately):

```
tests/test_deck_completeness.py::test_inv27_passes_on_the_arc_deck PASSED [  4%]
tests/test_deck_layout.py::test_inv32_passes_on_every_content_slide_of_every_fixture[arc_genomics] PASSED [  9%]
tests/test_deck_layout.py::test_inv32_passes_on_every_content_slide_of_every_fixture[arc_overextracted] PASSED [ 14%]
tests/test_deck_layout.py::test_inv32_passes_on_every_content_slide_of_every_fixture[mock_sow] PASSED [ 19%]
tests/test_deck_layout.py::test_inv32_passes_on_every_content_slide_of_every_fixture[no_story_ids] PASSED [ 23%]
tests/test_deck_layout.py::test_inv32_passes_on_every_content_slide_of_every_fixture[numbered_deliverables] PASSED [ 28%]
tests/test_deck_layout.py::test_inv32_cover_margin_catches_known_wrap PASSED [ 33%]
tests/test_deck_layout.py::test_cover_title_shrinks_to_one_line_for_the_mock_project PASSED [ 38%]
tests/test_deck_layout.py::test_cover_title_that_cannot_fit_at_28_pt_wraps_and_pushes_the_subtitle_down_within_its_own_box PASSED [ 42%]
tests/test_deck_layout.py::test_cover_title_needing_more_than_the_subtitle_slack_is_a_genuine_failure PASSED [ 47%]
tests/test_output_names.py::test_all_outputs_of_one_run_share_one_prefix[arc_genomics] PASSED [ 52%]
tests/test_output_names.py::test_all_outputs_of_one_run_share_one_prefix[arc_overextracted] PASSED [ 57%]
tests/test_output_names.py::test_all_outputs_of_one_run_share_one_prefix[mock_sow] PASSED [ 61%]
tests/test_output_names.py::test_all_outputs_of_one_run_share_one_prefix[no_story_ids] PASSED [ 66%]
tests/test_output_names.py::test_all_outputs_of_one_run_share_one_prefix[numbered_deliverables] PASSED [ 71%]
tests/test_output_names.py::test_output_names_have_no_double_underscore[arc_genomics] PASSED [ 76%]
tests/test_output_names.py::test_output_names_have_no_double_underscore[arc_overextracted] PASSED [ 80%]
tests/test_output_names.py::test_output_names_have_no_double_underscore[mock_sow] PASSED [ 85%]
tests/test_output_names.py::test_output_names_have_no_double_underscore[no_story_ids] PASSED [ 90%]
tests/test_output_names.py::test_output_names_have_no_double_underscore[numbered_deliverables] PASSED [ 95%]
tests/test_output_names.py::test_only_one_sanitize_filename_exists_in_src PASSED [100%]
============================= 21 passed in 25.01s =============================
```

## 3. ARC deck (replay) and check_artifacts

Command: `python main.py --llm-cache replay --start-date 2026-10-05 --slides --non-interactive` with `[V1] Exhibit A - Arc Genomics Platform.pdf` copied into `inputs\` by `Copy-Item -LiteralPath`; only that copy was deleted afterwards (`inputs\` then held just `SOWs`). Main exit code: **0**.

```
PASSED: All artifacts in 'output' satisfy all invariants.
```
`python -m src.tools.check_artifacts output` exit code: **0**.

Files in `output\` (the Checklist is from an earlier run: `--slides` does not rewrite it):

```
Mode   LastWriteTime         Length Name                                                   
----   -------------         ------ ----                                                   
-a---- 10/2/2026 3:14:10 PM   54132 ARC_Genomics_Platform_Project_Delivery_Workbook.xlsx   
-a---- 10/2/2026 3:14:10 PM   58102 ARC_Genomics_Platform_Startup_Kit.docx                 
-a---- 10/1/2026 7:42:00 PM   47342 ARC_Genomics_Platform_Startup_Readiness_Checklist.docx 
-a---- 10/2/2026 3:14:11 PM 1245457 ARC_Genomics_Platform_Talent_Onboarding_Deck.pptx      
-a---- 10/2/2026 3:14:11 PM   98007 ARC_Genomics_Platform_Talent_Onboarding_Deck.trace.json
```

## 4. Mock run and check_artifacts

Command: `python main.py --mock --non-interactive --all` (main exit **0**), then `python -m src.tools.check_artifacts output\Reports\Test`:

```
PASSED: All artifacts in 'output\Reports\Test' satisfy all invariants.
```
Exit code: **0**.

`dir` of `output\Reports\Test`. The first five files were written by this run. The last three (double underscore) are **stale pre-fix files** from earlier runs that the environment would not let me delete; they are git-ignored:

```
Mode   LastWriteTime         Length Name                                                                         
----   -------------         ------ ----                                                                         
-a---- 10/2/2026 3:14:21 PM   18569 Pfizer_Analytics_Cloud_Modernization_Project_Delivery_Workbook.xlsx          
-a---- 10/2/2026 3:14:21 PM   41784 Pfizer_Analytics_Cloud_Modernization_Startup_Kit.docx                        
-a---- 10/2/2026 3:14:21 PM   40899 Pfizer_Analytics_Cloud_Modernization_Startup_Readiness_Checklist.docx        
-a---- 10/2/2026 3:14:21 PM 1241788 Pfizer_Analytics_Cloud_Modernization_Talent_Onboarding_Deck.pptx             
-a---- 10/2/2026 3:14:21 PM   42569 Pfizer_Analytics_Cloud_Modernization_Talent_Onboarding_Deck.trace.json       
-a---- 10/2/2026 2:52:46 PM   41784 Pfizer_Analytics__Cloud_Modernization_Startup_Kit.docx                       
-a---- 10/1/2026 8:20:31 PM   41786 Pfizer_Analytics__Cloud_Modernization_Startup_Kit_backup_20261001_202041.docx
-a---- 10/2/2026 2:52:46 PM   40899 Pfizer_Analytics__Cloud_Modernization_Startup_Readiness_Checklist.docx
```

Because `check_artifacts` reads the whole folder, I repeated the run into a clean folder (`MOCK_OUTPUT_DIR=output\Reports\Rev11Verify`). Main exit **0**; `check_artifacts` exit **0**:

```
PASSED: All artifacts in 'output\Reports\Rev11Verify' satisfy all invariants.

Mode   LastWriteTime         Length Name                                                                  
----   -------------         ------ ----                                                                  
-a---- 10/2/2026 3:14:32 PM   18570 Pfizer_Analytics_Cloud_Modernization_Project_Delivery_Workbook.xlsx   
-a---- 10/2/2026 3:14:32 PM   41784 Pfizer_Analytics_Cloud_Modernization_Startup_Kit.docx                 
-a---- 10/2/2026 3:14:32 PM   40899 Pfizer_Analytics_Cloud_Modernization_Startup_Readiness_Checklist.docx 
-a---- 10/2/2026 3:14:32 PM 1241788 Pfizer_Analytics_Cloud_Modernization_Talent_Onboarding_Deck.pptx      
-a---- 10/2/2026 3:14:32 PM   42569 Pfizer_Analytics_Cloud_Modernization_Talent_Onboarding_Deck.trace.json
```

## 5. Slide text

ARC deck Slide 6, and the mock deck Slide 1 with the title's rendered font size (read from the written `.pptx`):

```
ARC deck, Slide 6 (all shapes with text):
[Title 1]
    Client Collaboration
[Subtitle 2]
    ARC GENOMICS PLATFORM · TALENT TEAM ONBOARDING
[Card text: Client roles]
    Client roles
    Client Sponsor / Approver: Gives timely written responses to decision requests flagged in weekly reports.
    Client Approver: Accept or reject each of the four sequential milestone gates (P1, P2a, P2b, P3)
    Client Delivery Counterpart: Own the platform layer (Terraform, infrastructure) and the data tier (ingestion pipelines, Snowflake data model).
    Client Subject Matter Experts: Provide trait taxonomy approvals and domain-user comparison sign-off for the MTA Store migration.
    UAT Participants: Run UAT after each milestone (limited to two runs per milestone) and surface defects.
    +1 more (see Startup Kit · Stakeholder and Responsibility Model)
[Card text: Working rhythm]
    Working rhythm
    Kickoff Call: One-time
    Daily Standups: Daily
    Biweekly Sprint Demo: Biweekly (every sprint)
    Weekly Status Meeting: Weekly
    Weekly Status Report: Weekly
    Milestone Acceptance Review: At the end of each milestone (4 milestones)
    Ad-Hoc Working Sessions: As needed
[Card text: Client prerequisites]
    Client prerequisites
    M1: Client provides design system access (code library, tokens, design files, guidelines, named contact)
    M1: Client IdP team available for Azure AD / MSAL authentication
    M1: Client-owned stories and code dependencies completed before related Toptal work begins
    M1: Coding and delivery documentation standards provided on or before the start date
    M2: Client completes Snowflake data model story (HS-4781) before P2a begins
    M2: Client domain users and domain experts available for trait taxonomy
    +6 more (see Project Delivery Workbook · Project Schedule)

mock deck, Slide 1:
   title   : 'Pfizer Analytics & Cloud Modernization' | explicit run size: 37.0 pt | layout default: n/a (explicit)
   subtitle: 'Talent Team Onboarding · Pfizer Inc. · Start 2026-10-05' | size: 23.0 pt
```

The title's 37 pt is an explicit run size set by the writer (the layout default is 43 pt). All five fixtures were also checked against the own-placeholder bound: none wraps; every title is 1 line, and the subtitle stays at its default top of 3.836 in.

**Snapshots.** `tests\snapshots_proposed` versus `tests\snapshots` (`git diff --no-index --stat`). This is large because the approved snapshots predate the Rev 10 deck changes; promotion is still pending:

```
 .../arc_genomics/snapshot.json                     | 402 +++++++++++++++++++-
 .../arc_overextracted/snapshot.json                | 420 ++++++++++++++++++++-
 .../mock_sow/snapshot.json                         | 272 ++++++++++++-
 .../no_story_ids/snapshot.json                     | 317 +++++++++++++++-
 .../numbered_deliverables/snapshot.json            | 302 ++++++++++++++-
 5 files changed, 1674 insertions(+), 39 deletions(-)
```

The Rev 11 delta alone (`git show --stat` of the proposed-snapshot commit): the mock Kit file name loses its double underscore, and the ARC-family snapshots gain the per-prerequisite Slide 6 bullets and the `+6 more` line.

```
b5e0a28 Proposed snapshots for Rev 11

 tests/snapshots_proposed/arc_genomics/snapshot.json          | 7 +++++--
 tests/snapshots_proposed/arc_overextracted/snapshot.json     | 9 ++++++---
 tests/snapshots_proposed/mock_sow/snapshot.json              | 2 +-
 tests/snapshots_proposed/no_story_ids/snapshot.json          | 1 +
 tests/snapshots_proposed/numbered_deliverables/snapshot.json | 4 +++-
 5 files changed, 16 insertions(+), 7 deletions(-)
```

## 6. Requirement rows (`Select-String` output, unedited)

```
spec\PMO_Startup_Kit_Consolidated_Spec.md:232:| DECK-07 | **Completeness.** Slide 3 shows every gate, every 
checkpoint, and every deliverable ID in the Workbook Project Schedule. Slide 4 shows every deliverable ID. On Slide 6, 
every client stakeholder, every communications item, and every client prerequisite appears, either as a bullet or in a 
`+N more` line. Each prerequisite counts separately: a Workbook Client Prerequisites cell holding several 
prerequisites separated by `; ` is split into one item per prerequisite. Where a table exceeds its row capacity 
(Appendix K), the last row reads `+N more: DEL-xx, DEL-yy, ... (see <source locator>)`, listing every omitted ID, so 
no ID is ever dropped. | Pending (ARC slide 6 shows 4 of 12 client prerequisites, the first of each gate, with no `+N 
more` line) | `test_deck_completeness.py`, INV-27 |

spec\PMO_Startup_Kit_Consolidated_Spec.md:246:| DECK-21 | **Layout and alignment.** (1) **Cards:** one text frame per 
card, inset 0.20 in from the card on every side, anchored top, word wrap on, autofit off. The card heading is a single 
line (Proxima Nova bold 16 pt, reduced to 14 pt if needed; it never wraps), followed by 8 pt of space. Subheadings are 
Proxima Nova Semibold 11 pt `204ECF` with 8 pt space before and 2 pt after. Body paragraphs are Calibri 11 pt (never 
below 10.5 pt), with 4 pt space after. Bullets use paragraph bullet formatting (bullet character `•`, left margin 0.17 
in, hanging indent 0.17 in), never a typed `•` character. (2) **Tables:** column widths as in Appendix K.1; header row 
0.40 in; body rows at least 0.30 in; body text Calibri 10 pt (9 pt allowed only for Slide 3's Deliverables column); 
cell margins 0.06 in left and right, 0.04 in top and bottom; text anchored top. The built-in table style is removed 
(no banding from PowerPoint's default style); all fills come from K.1. The `+N more` overflow row is a single merged 
cell spanning all columns. (3) **Key-value tables** (Slide 2 Key facts): no header row; the label column is Proxima 
Nova bold 10 pt on `F8FAFC`; the value column is Calibri 10 pt on `FFFFFF`. (4) **Bounds:** every shape, including a 
table's estimated full height, lies inside the content area (x 0.83 to 12.50 in, y 1.70 to 6.70 in); no two content 
shapes overlap, except that a card may contain shapes lying wholly inside it (its text frame, or a table such as Key 
facts); the footer and logo areas stay clear. (5) **Cover fit:** the cover title stays on one line, reducing from the 
layout's size down to a minimum of 28 pt. If it still does not fit, it may wrap to two lines, and the subtitle moves 
down so the two never overlap. (6) **Fit:** the writer estimates each text frame's rendered height (characters per 
line from the frame width at an average character width of 0.5 × font size; line height 1.2 × font size, plus 
paragraph spacing). If the estimate exceeds the frame, it reduces the font within the limits above, then uses the `+N 
more` row or line; it never lets text overflow and never shrinks below the minimums. | Pending (content slides 
verified in Rev 10 review; cover title overflows into the subtitle for long project names, for example the mock 
project) | `test_deck_layout.py`, INV-32 |

spec\PMO_Startup_Kit_Consolidated_Spec.md:47:| OUT-11 | **One file-name rule.** Every output (Kit, Checklist, 
Workbook, deck, trace manifest) uses the same `sanitize_filename` helper, which removes unsafe characters and 
collapses runs of spaces and underscores into a single underscore, so all files of a run share one prefix. Only one 
`sanitize_filename` exists in `src\`. | Pending (mock run: `Pfizer_Analytics__Cloud_Modernization_Startup_Kit.docx` vs 
`Pfizer_Analytics_Cloud_Modernization_Project_Delivery_Workbook.xlsx`) | `test_output_names.py` |

spec\PMO_Startup_Kit_Consolidated_Spec.md:282:| INV-27 | Slide 3 contains every gate, checkpoint, and deliverable ID 
from the Workbook Project Schedule; Slide 4 contains every deliverable ID; and Slide 6 accounts for every client 
stakeholder, communications item, and client prerequisite (DECK-07), either in a table row or in a `+N more` overflow 
row (DECK-07). |

spec\PMO_Startup_Kit_Consolidated_Spec.md:287:| INV-32 | Every deck shape, including the cover title and subtitle, 
lies inside its allowed area, content shapes do not overlap, every card text frame and table passes the DECK-21 fit 
estimate, and no font is below the DECK-21 minimums. |


```

QA-10 row:

```
spec\PMO_Startup_Kit_Consolidated_Spec.md:68:| QA-10 | **Agent reports are evidence, not claims.** Snapshot 
differences in a report come from an actual diff of `tests\snapshots` against `tests\snapshots_proposed`. Requirement 
definitions are quoted from this spec. Test totals come from plain `pytest -q` with no filter. Every "Verified" entry 
cites a test and a concrete output value; otherwise it is "Not verified". When a requirement cannot be met as written 
(for example, a fixture it names does not exist), the agent stops and reports it; it never redefines the requirement 
so that the current state passes. Requirement text in a report is copied mechanically: the report includes the raw 
output of `Select-String -Path spec\PMO_Startup_Kit_Consolidated_Spec.md -Pattern '^\| <ID> \|'` for each requirement 
it cites, never text written from memory. The report ends with the raw output of `git status` and `git --no-pager log 
--oneline -15`. | Pending (Rev 7 report contained invented Select-String output and invented example rows; reviews 
rely on snapshots and on commands run by a person) | Review |
```

## 7. Not verified, or open

- **Cover rendering is not verified visually.** LibreOffice is not installed here (`python -m src.tools.render_deck` reports it was not found). The 37 pt result for the mock title and the 1.15 margin come from the estimator only. The margin was calibrated on a single observation (the Appendix M2 render of the 38-character title) that was not reproduced here. Titles of about 34 to 37 characters are flagged as wrapping without having been rendered.
- **3-line cover titles fail INV-32 by design.** A title that needs 3 lines at 28 pt cannot be accommodated by the subtitle's own slack. No real project triggers it; no fallback was chosen (smaller font floor versus a taller placeholder is left to a real case).
- **INV-27 stakeholder and communications matching is my interpretation.** A client stakeholder is a Kit Stakeholder row whose Organization is `Client`, matched by its Role text; a communications item is matched by its Report / Meeting name. The requirement rows do not define the matching key.
- **Snapshots are not promoted.** Five snapshot tests fail until a human promotes `tests\snapshots_proposed`. I did not review the Rev 10 portion of that diff in this round.
- **Stale files** remain in `output\Reports\Test` (section 4); the clean-folder run is the evidence for the file names.
- **Spec status columns are not updated.** The spec is read-only for this work, so DECK-07, DECK-21 and OUT-11 still read "Pending" in the rows quoted in section 6 even though the checks and fixes above are in place. Rev 11 items outside Parts 1 and 2 (for example the DECK-04 non-row locators) were covered only by the existing tests in the plain `pytest -q` run, not re-examined individually.
- **One related spot left alone:** `src/extractors/startup_kit_docx_parser.py` still guesses a Checklist file name with `project_name.replace(' ', '_')` (lookup only, not an output name).
- **Commit title.** Part 1 is in `259e6bb` ("rev 11 spec"), not under the planned title.

## 8. `git --no-pager log --oneline -15`

```
75383d6 DECK-21: hold cover title and subtitle to their own placeholder boxes
b5e0a28 Proposed snapshots for Rev 11
4933ded OUT-11: single sanitize_filename for all outputs
beee63b DECK-21: cover title/subtitle fit and no-overlap
ae2c2d6 DECK-07: list every client prerequisite on Slide 6
4c3f20c Merge branch 'main' of https://github.com/jmora000-maker/startup_kit
259e6bb rev 11 spec
192f71b docs: add architecture and telemetry specs
5f8ee91 docs: add architecture and telemetry specs
7729a88 commit before pill form other laptop
ca74c9f Spec Revision 11
3df7eb8 Rev 10 final report
9cf0e6e Rev 10 tests: slide 6 working rhythm equals the Kit communications items (K.4)
e82037b Proposed snapshots for Rev 10
27b14de Rev 10 step 6: render_deck review aid (DECK-23), README (DECK-18)
```