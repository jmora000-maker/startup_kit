# PMO Startup Toolkit Workbook — Implementation Spec (--export-tools)

September 30, 2026

## 1. Purpose and scope

Replace the current `--export-tools` output (five CSV/JSON seed files) with one Excel workbook, `{Project}_PMO_Startup_Toolkit.xlsx`, containing three tabs: **Project Schedule**, **WBS**, and **RAID Log**.

The workbook is built from the same in-memory `StartupKitBaseline` that renders `{Project}_Startup_Kit.docx`. That is how content alignment with the Startup Kit is guaranteed: no new extraction, no new LLM calls, and no re-reading of the SOW.

**In scope**

- A new workbook generator package under `src/generators/pmo_workbook/`.
- Removal of `src/generators/export_payloads.py` and every call to `export_all_pmo_tools`.
- Rewiring `StartupKitController.run()` and `run_reingest()` to produce the workbook.
- New output-selection flags `--kit`, `--checklist`, and `--all`, with the workbook becoming the default output when no flag is given (section 3.1).
- Updating the `--export-tools` help text in `main.py`, adding `openpyxl` to `requirements.txt` (currently missing), updating `README.md`, and fixing one mock-client keyword in `main.py`.
- A deterministic, rules-based best-practice task library that generates the tasks needed to reach each milestone.
- A short CLI summary of the export.
- Tests.

**Out of scope**

- Changes to the content or layout of the Word Startup Kit or the G-01 checklist document, the readiness score, or any LLM prompt. The generator is refactored only so each document can be written on its own (section 3.1).
- Changes to the existing Pydantic models in `src/core/models.py`. The workbook derives everything it needs from existing fields; the only additions are the new `OutputSelection` and `RunResult` dataclasses.
- Interactive prompts for output selection. Outputs are chosen by flags only.

**Hard constraints**

- **No resource hours or capacity.** No columns, formulas, or text for effort, hours, FTE, allocation, utilization, capacity, rates, or cost. Owners are roles or names only. Schedule duration in working days is allowed because it is calendar span, not effort.
- **Alignment with the Startup Kit.** Every milestone, deliverable, work package, RAID item, owner, and date that exists in the baseline must appear exactly as the Startup Kit shows it, after the same `sanitize_report_text` cleanup the Word generator applies. Anything the workbook adds from best practice is marked in a `Source` column as `PM Best Practice`.
- **Determinism.** The same baseline always produces the same rows, IDs, and ordering. Only the generated-date cell may differ between runs.

**Outputs no longer produced**

| Old file | Old function | Replacement |
| --- | --- | --- |
| `{Project}_PMO_RAID_Log.csv` | `export_raid_csv` | RAID Log tab |
| `{Project}_PMO_Milestone_Plan.json` | `export_milestone_plan_json` | Project Schedule tab |
| `{Project}_PMO_Decision_Log.csv` | `export_decision_log_csv` | None. Decision IDs appear only as links in the RAID Log. |
| `{Project}_PMO_PSA_Seed.json` | `export_psa_seed_json` | None |
| `{Project}_PMO_Budget_Burndown_Seed.json` | `export_budget_burndown_seed_json` | None. Budget content conflicts with the no-capacity rule. |

## 2. Codebase context

The export is triggered in two places, and both must produce the workbook. Today `main.py` defines `--export-tools` as a `store_true` flag and passes it as `export_tools=args.export_tools` to `controller.run(...)` (initial generation) and to `controller.run_reingest(...)` (`--reingest-docx`). Section 3.1 replaces that single boolean with an `OutputSelection`.

| Entry point | Current call | Output directory |
| --- | --- | --- |
| `StartupKitController.run(export_tools=True)` | `export_all_pmo_tools(baseline, out_path)` | `out_path` (`config.output_dir`, or `config.mock_output_dir` when the client is `MockLLMClient`) |
| `StartupKitController.run_reingest(export_tools=True)` | `export_all_pmo_tools(baseline, export_dir)` | `target_path.parent` |

**Baseline fields the workbook reads** (all in `src/core/models.py`):

- `project_name`, `governance_tier`, `contract_type`, `governance_context`, `charter` for the title block.
- `milestones: List[Milestone]`: `id`, `description`, `external_date`, `internal_buffer_date`, `owner`, `key_dependencies`, `critical_path_assumptions`, `linked_action_id`.
- `deliverables: List[Deliverable]`: `id`, `name`, `owner`, `acceptance_criteria`, `evidence_required`, `client_approver`, `submission_target_date`, `review_window`, `rejection_rework_path`, `linked_action_id`.
- `backlog_seed: List[WorkPackageSeed]`: `id`, `parent_deliverable_id`, `title`, `preliminary_sequence`, `owner`, `linked_milestones`, `dependency_references`, `status`.
- `raid_items: List[RiskAssumption]`, `dependencies_assumptions: List[DependencyAssumptionItem]`, `contract_ambiguities: List[ContractAmbiguityItem]`.
- `readiness_checklist`, `gate_decision`, `communications_plan`, `talent_onboarding`, `kit_drafted_date`, `sow_awarded_date` for governance milestones and tasks.

**Model gaps the design works around** (do not change the models):

- `Milestone` has no workstream field. Workstreams are derived by the classifier in section 4.
- `Deliverable` has no milestone link. Deliverables are mapped to milestones by the rules in section 6.
- `WorkPackageSeed.linked_milestones` is lost on the re-ingest path, because the Word backlog table has no milestone column. The mapping rules must not depend on it.
- `RiskAssumption` has no `id` field. The parser passes `id=` and Pydantic silently drops it, so the Word generator falls back to a description prefix. The workbook assigns its own RAID IDs (section 7).

**Existing behavior to reuse, not reimplement**

- Internal buffer dates are already computed by `BaselineAggregator` (3 days Guided, 7 Partnered, 10 Elevated). Read `internal_buffer_date`; never recompute it.
- `sanitize_report_text` from `src/config.py` on every free-text field, exactly as `DocxGenerator` does.
- `normalize_person_name` from `src/config.py` on every owner field.
- Palette constants from `src/generators/formatting.py` (`COLOR_NAVY_HEX`, `COLOR_PRIMARY_BLUE_HEX`, `COLOR_ACCENT_BLUE_HEX`, `COLOR_LIGHT_BG_HEX`, `COLOR_WARNING_BG_HEX`, `COLOR_BORDER_HEX`, `COLOR_TEXT_MUTED_HEX`) and `ACTION_TAG_REGEX`. Import them; do not copy the values.
- `sanitize_filename` from `src/generators/docx_generator.py`. The copy in `export_payloads.py` is deleted with that file.
- Placeholder conventions: `[CONFIRMATION REQUIRED]`, `[UNASSIGNED - TO BE CONFIRMED]`, and `ACT-NN` action IDs.

## 3. Architecture and integration

The generator is split into a pure model-building layer and a thin rendering layer. The builders turn a `StartupKitBaseline` into plain row objects with no `openpyxl` imports, so all mapping and task logic is unit-testable without writing a file.

**Package layout** (`src/generators/pmo_workbook/`)

| Module | Responsibility |
| --- | --- |
| `__init__.py` | Exports `export_pmo_workbook` and `PMOWorkbookResult`. |
| `workstreams.py` | The fixed workstream taxonomy and `classify_milestone()` (section 4). |
| `task_library.py` | Best-practice task templates as frozen dataclasses (section 6). No logic beyond lookups. |
| `mapping.py` | Deliverable-to-milestone and RAID-to-milestone mapping rules (sections 6 and 7). |
| `rows.py` | Frozen dataclasses `ScheduleRow`, `WBSRow`, `RAIDRow`, and `WorkbookModel` (all three row lists plus title-block metadata). |
| `builder.py` | `build_workbook_model(baseline, today) -> WorkbookModel`. Pure. `today` is injected so tests are deterministic. |
| `writer.py` | `write_workbook(model, file_path) -> Path`. All `openpyxl` code lives here: styles, formulas, validation, conditional formatting. |
| `styles.py` | Named styles built from the `formatting.py` palette. |

**Public API**

```python
@dataclass(frozen=True)
class PMOWorkbookResult:
    file_path: Path
    schedule_rows: int
    wbs_rows: int
    task_rows: int
    raid_rows: int
    unmapped_deliverables: int

def export_pmo_workbook(baseline: StartupKitBaseline, output_dir: Path) -> PMOWorkbookResult:
    """Build and save {Project}_PMO_Startup_Toolkit.xlsx into output_dir."""
```

- `output_dir` is created if missing. An existing file with the same name is overwritten.
- File name: `f"{sanitize_filename(baseline.project_name)}_PMO_Startup_Toolkit.xlsx"`.
- On a write failure (for example, the file is open in Excel on Windows), raise `PermissionError` with a message naming the path and telling the user to close the file. Do not swallow it. Any Word documents already written in the same run stay on disk.

**Orchestrator changes** (`src/orchestrator.py`)

1. Replace `from src.generators.export_payloads import export_all_pmo_tools` with `from src.generators.pmo_workbook import export_pmo_workbook`, and add `from src.scoring.cli_reporter import print_workbook_export_summary`.
2. In `run()` and `run_reingest()`, replace the `export_tools` parameter and the `export_all_pmo_tools(...)` call with the output-selection logic in section 3.1. The workbook call is `result = export_pmo_workbook(baseline, <same dir as today>)`.
3. Order: selected Word documents, then the workbook, then `print_readiness_cli_summary`, then `print_workbook_export_summary(result)` when the workbook was written.
4. Update the log lines to say "Exporting PMO Startup Toolkit workbook to %s".

**CLI summary** (`src/scoring/cli_reporter.py`)

Add `format_workbook_export_summary(result, use_color=None) -> str` and `print_workbook_export_summary(...)`. Use the same color detection (`NO_COLOR`, non-TTY), the same 80-character separators, and this content:

```text
 PMO STARTUP TOOLKIT WORKBOOK
   • Project Schedule     : 4 workstreams, 9 milestones
   • WBS                  : 112 elements (86 tasks)
   • RAID Log             : 17 items
   • Unmapped deliverables: 1 (placed under final milestone - review)
   • Output File Path     : /abs/path/Acme_PMO_Startup_Toolkit.xlsx
```

Print the unmapped line in amber when the count is greater than 0, and omit it when 0.

**Other changes**

- `main.py`: add `--kit`, `--checklist`, and `--all` (`dest="all_outputs"`), change the `--export-tools` help text, and add the parser epilog, all as in section 3.1. Build an `OutputSelection` and pass `outputs=` to both controller calls in place of `export_tools=args.export_tools`, and log each path in the returned `RunResult`.
- `main.py`, mock client bug: `create_mock_llm_client()` builds `CommunicationsExtraction(communications_plan=[...])`, but the model field is `communications`. Pydantic drops the unknown keyword, so mock runs have an empty communications plan. Rename the keyword to `communications=` so mock runs exercise the Governance Cadence tasks (section 6.4).
- `requirements.txt`: `openpyxl` is not present. Add `openpyxl>=3.1` after `python-pptx`. Do not add `xlsxwriter` or `pandas`.
- `README.md`, five edits:
    1. Features list: replace the "PMO Operating System Export" bullet with "**PMO Startup Toolkit Workbook**: Default Excel output with a Project Schedule by workstream, a four-level WBS with best-practice tasks, and a consolidated RAID Log, all built from the Startup Kit baseline. Word documents are written on request with `--kit`, `--checklist`, or `--all`."
    2. Project Structure tree: replace the `export_payloads.py` line with `pmo_workbook/  # Excel PMO Startup Toolkit workbook generator`.
    3. CLI options table: replace the `--export-tools` row, and add rows for `--kit`, `--checklist`, and `--all`, using the help text from section 3.1. Add a line under the table: "With no output flag, only the workbook is written."
    4. Example commands: add `--all` to the interactive, Anthropic, and OpenAI examples so they keep producing Word documents. Change the plain re-ingest example to `--reingest-docx output/Project_Startup_Kit.docx --kit --non-interactive`. Change the re-export example's comment to "Re-evaluate and write all three outputs" and its flag to `--all`.
    5. Add examples: `python main.py --mock --non-interactive` ("Offline mock run: workbook only") and `python main.py --mock --non-interactive --checklist` ("Offline mock run: readiness checklist only").
- Delete `src/generators/export_payloads.py`. Search the repo for `export_payloads`, `export_all_pmo_tools`, `export_raid_csv`, `export_tools=`, and `_PMO_`, and remove or update every remaining reference, including tests.
- `src/generators/__init__.py`: add `export_pmo_workbook` to the exports.

### 3.1 Output selection flags

The workbook becomes the default output. Word documents are only written when asked for. Four `store_true` flags select outputs; they are additive, and with none of them the run behaves as if `--export-tools` were given.

| Flag | Writes | Help text |
| --- | --- | --- |
| `--export-tools` | `{Project}_PMO_Startup_Toolkit.xlsx` | "Write the PMO Startup Toolkit Excel workbook (default when no output flag is given)" |
| `--kit` | `{Project}_Startup_Kit.docx` | "Write the Startup Kit Word document" |
| `--checklist` | `{Project}_Startup_Readiness_Checklist.docx` | "Write the Startup Readiness Checklist Word document" |
| `--all` | All three files | "Write the Startup Kit, the Readiness Checklist, and the PMO Startup Toolkit workbook" |

**Resolution rules** (`OutputSelection.from_flags`, in `src/core/models.py` or a new `src/core/outputs.py`)

| Flags given | Kit | Checklist | Workbook |
| --- | --- | --- | --- |
| None | No | No | Yes |
| `--export-tools` | No | No | Yes |
| `--kit` | Yes | No | No |
| `--checklist` | No | Yes | No |
| `--kit --checklist` | Yes | Yes | No |
| `--kit --export-tools` | Yes | No | Yes |
| `--all`, alone or with any other flag | Yes | Yes | Yes |

```python
@dataclass(frozen=True)
class OutputSelection:
    kit: bool = False
    checklist: bool = False
    workbook: bool = True

    @classmethod
    def from_flags(cls, *, all_: bool, kit: bool, checklist: bool, export_tools: bool) -> "OutputSelection":
        if all_:
            return cls(kit=True, checklist=True, workbook=True)
        if not (kit or checklist or export_tools):
            return cls()  # default: workbook only
        return cls(kit=kit, checklist=checklist, workbook=export_tools)
```

`argparse` uses `dest="all_outputs"` for `--all`, because `all` shadows a builtin. Add an `epilog` to the parser: "Output: by default only the PMO Startup Toolkit workbook is written. Add --kit, --checklist, or --all to also write Word documents."

**Generator refactor** (`src/generators/docx_generator.py`)

`write_docx` currently writes both Word files, so the Kit and the checklist cannot be chosen separately. `write_documents` also calls `write_docx` and then `write_checklist_docx`, writing the checklist twice. Fix both without changing either document's content:

1. Extract `_resolve_output_paths(baseline, output_path) -> tuple[Path, Path]` from the duplicated path logic in `write_docx` and `write_documents`. It returns the Kit and checklist paths, keeping today's naming rules exactly.
2. Add `write_kit_docx(baseline, output_path) -> Path`, holding the current `write_docx` body minus the final `write_checklist_docx` call.
3. Keep `write_docx` (required by `IDocumentWriter`) as `write_kit_docx` followed by `write_checklist_docx`, so existing callers and tests keep today's behavior.
4. Make `write_documents` call `write_kit_docx` and `write_checklist_docx` once each.
5. `write_checklist_docx` takes either a directory or a Kit-style path. When given a Kit path, it derives the checklist path with `_resolve_output_paths`.

**Controller** (`src/orchestrator.py`)

- `run()` and `run_reingest()` replace `export_tools: bool = False` with `outputs: Optional[OutputSelection] = None`. `None` means `OutputSelection()`, the workbook-only default.
- Both return a new `RunResult` dataclass instead of the Kit path: `kit_path: Optional[Path]`, `checklist_path: Optional[Path]`, `workbook: Optional[PMOWorkbookResult]`, and `readiness_score: float`.
- Write only what `outputs` selects, in this order: Kit, checklist, workbook.
- Output directories are unchanged. Initial generation writes everything to `out_path`. Re-ingest writes to `target_path` and its parent, as today.
- Re-ingest backups: create the `_backup_{timestamp}.docx` copy only when the Kit is selected and would overwrite the input file. A workbook-only re-ingest never touches the input `.docx`.
- When re-ingest runs without `--kit` or `--all`, log at INFO: "Readiness recalculated; the Startup Kit .docx was not rewritten. Add --kit or --all to update it."
- When `--output-file` is given but neither the Kit nor the checklist is selected, log a WARNING that it only sets the folder for the workbook.

**CLI output**

- `print_readiness_cli_summary` always prints, since the readiness score is recalculated on every run.
- Change its second parameter to `artifact_paths: Sequence[Path]`, and print one `• Output File Path` line per file written. Still accept a single `Path` for backward compatibility.
- `print_workbook_export_summary` prints only when the workbook was written.
- In `main.py`, build the selection with `OutputSelection.from_flags(...)`, pass `outputs=` to both controller calls, log `Outputs -> Kit: yes | Checklist: no | Workbook: yes` before the run, and replace the single `Report File:` / `Updated Report File:` log line with one line per non-empty path in the `RunResult`.

## 4. Workstreams and milestone classification

Every milestone gets exactly one workstream from a fixed eight-item taxonomy, assigned by a deterministic keyword classifier. Workstreams are WBS level 1, numbered in taxonomy order, and only workstreams with at least one milestone appear. Project Management & Governance always appears and is always `1`.

**Taxonomy** (`workstreams.py`, in this order)

| Code | Workstream | Keywords (case-insensitive, word-start match) |
| --- | --- | --- |
| `PMG` | Project Management & Governance | kickoff, kick-off, mobiliz, onboard, governance, charter, gate, steering, baseline, closure, close-out, closeout |
| `DIS` | Discovery & Requirements | discovery, requirement, workshop, assessment, current state, as-is, analysis, research, audit, scoping |
| `DES` | Design & Architecture | design, architect, blueprint, prototype, wireframe, mockup, mock-up, specification, ux, ui |
| `BLD` | Build & Configuration | build, develop, implement, configur, sprint, mvp, feature, code, module, iteration |
| `DAT` | Data & Integration | data, migrat, integrat, interface, api, etl, pipeline, reconcil |
| `TST` | Testing & Quality Assurance | test, uat, qa, quality, sit, validat, defect |
| `DEP` | Deployment & Release | deploy, go-live, go live, launch, release, cutover, cut-over, production, rollout, roll-out |
| `TRN` | Transition & Hypercare | hypercare, handover, hand-over, transition, knowledge transfer, training, runbook, warranty, stabiliz |

Keywords of four characters or fewer (`ux`, `ui`, `qa`, `sit`, `uat`, `api`, `etl`, `mvp`, `data`, `code`, `test`, `gate`) match whole words only. The rest match at a word start, so `configur` matches "configuration".

**Classifier** (`classify_milestone(milestone, mapped_deliverables) -> (code, basis)`)

1. Run deliverable mapping (section 6) first, so the deliverables under each milestone are known.
2. Score each workstream by counting the distinct keywords found in the sanitized milestone description.
3. The highest score wins. On a tie, pick the workstream that comes **later** in taxonomy order. A milestone named after several activities is usually named for the stage it completes: "Data Pipeline Production Go-Live" ties Data & Integration with Deployment & Release, and resolves to Deployment & Release.
4. Only when the description matches no keyword, score the names of the mapped deliverables the same way, with the same tie-break. Basis: `Deliverable keyword: {kw}`.
5. With still no match, assign `BLD` with basis `Default - confirm workstream`.
6. `basis` records why, for example `Keyword: uat`. It is shown in the Schedule's `Workstream Basis` column so the PM can review it.

**Governance milestones**

The builder adds two milestones to `PMG` so that startup and closure work has a home. They are clearly labelled and never replace a Startup Kit milestone.

| ID | Name | Date | Owner | Source |
| --- | --- | --- | --- | --- |
| `PM-01` | G-01 Startup Readiness Gate Approved | `gate_decision.approval_date`, else blank | `gate_decision.approver_name`, else `PMO Lead` | `Startup Kit - G-01 Gate Decision` |
| `PM-02` | Project Closure and Handover Accepted | Latest `external_date` among Kit milestones, else blank | `charter.pmo_lead`, else `PMO Lead` | `PM Best Practice` |

If a Kit milestone already classifies as `PMG` and its description contains "gate" or "G-01", do not add `PM-01`; that Kit milestone takes PM-01's task set instead. Apply the same rule to `PM-02` with "closure", "close-out", or "closeout".

If a Kit `PMG` milestone contains "kickoff", "kick-off", "mobiliz", or "onboard" (for example, the mock's `M1 Project Kickoff & Architecture Baseline`), it takes the `Mobilization Activities` package, and `PM-01` keeps only its `G-01 Readiness Checklist` package. Any other Kit `PMG` milestone uses the Governance template in section 6.3.

WBS level 2 also holds one non-milestone element, `Ongoing Governance & Reporting`, under `PMG` (section 6). The Workstream column in the Schedule is a dropdown, so a PM can re-classify a milestone. The WBS does not update automatically when they do; state this in the Schedule's instruction row.

## 5. Tab 1: Project Schedule

The Schedule is the high-level plan: one summary row per workstream, then its milestones beneath it, with a weekly timeline to the right. It carries WBS codes to level 2 only, so every row here has a matching element in the WBS tab.

**Sheet layout** (sheet name `Project Schedule`)

- Row 1: `TOPTAL PMO STARTUP KIT - PROJECT SCHEDULE`, merged A1:U1, Arial 16 bold, navy.
- Row 2: `Project: {name} | Client: {client} | Governance Tier: {tier} | Contract: {contract_type}`. Client comes from `governance_context.client_name`, else `charter.client_name`, else `N/A`.
- Row 3: `Generated {YYYY-MM-DD} from the Startup Kit baseline | Readiness score: {score:.1f}%`, muted text.
- Row 4: instruction row, italic muted: "Dates from the Startup Kit are commitments. Planned Start is a proposed sequence; adjust as needed. Changing a Workstream here does not update the WBS tab."
- Row 5: header row. Data starts on row 6.

**Row order**

1. Workstreams in taxonomy order, each as a `Workstream` summary row followed by its child rows.
2. Within `PMG`: `PM-01` (or the Kit gate milestone), other Kit `PMG` milestones by date, the `Recurring` row `Ongoing Governance & Reporting`, then `PM-02` (or the Kit closure milestone) last.
3. Within every other workstream: milestones by `external_date` ascending, undated last, ties by natural sort of ID (`MS-2` before `MS-10`).

**Columns**

| Col | Header | Content | Width |
| --- | --- | --- | --- |
| A | WBS Code | `1`, `1.1`, `1.2` ... matching the WBS tab | 9 |
| B | Row Type | `Workstream`, `Milestone`, or `Recurring` | 12 |
| C | Workstream | Workstream name. Dropdown from the taxonomy list. | 26 |
| D | Milestone ID | Kit `Milestone.id`, or `PM-01` / `PM-02`. Blank on workstream and recurring rows. | 12 |
| E | Milestone / Activity | Sanitized description. Workstream rows show the workstream name in bold. | 45 |
| F | Owner | `normalize_person_name(owner)` | 22 |
| G | Planned Start | Date; rule below. Workstream rows: `=IF(COUNT(G7:G10)=0,"",MIN(G7:G10))` over their child range. | 13 |
| H | Internal Buffer Date | `internal_buffer_date`. Blank on workstream rows. | 13 |
| I | External Commitment Date | `external_date`. Workstream rows: MAX formula over child range, same pattern as G. | 13 |
| J | Duration (working days) | `=IF(OR(G6="",I6=""),"",NETWORKDAYS(G6,I6))` | 11 |
| K | Days to Commitment | `=IF(OR(I6="",M6="Complete"),"",I6-TODAY())` | 11 |
| L | Status | Dropdown: `Not Started`, `In Progress`, `At Risk`, `Complete`, `On Hold`. Default `Not Started`. Blank on workstream rows. | 13 |
| M | Health | Formula below. Blank on workstream rows. | 12 |
| N | Key Dependencies | `"; ".join(key_dependencies)` | 30 |
| O | Critical Path Assumptions | `"; ".join(critical_path_assumptions)` | 30 |
| P | Linked Deliverables | Comma-separated deliverable IDs mapped to this milestone (section 6) | 18 |
| Q | Linked RAID IDs | Comma-separated RAID IDs linked to this milestone (section 7) | 18 |
| R | Linked Action ID | `linked_action_id` | 12 |
| S | Source | `Startup Kit - Milestone Delivery Plan`, `Startup Kit - G-01 Gate Decision`, `Startup Kit - Communications Plan`, or `PM Best Practice` | 26 |
| T | Workstream Basis | Classifier basis, for example `Keyword: uat` | 22 |
| U | Notes | Auto-flags, joined with `; ` (list below) | 40 |

**Planned Start rule** (computed in Python, written as date values)

- `project_start` = `gate_decision.approval_date`, else `kit_drafted_date`, else `sow_awarded_date`, else blank.
- `PM-01` starts on `kit_drafted_date`, else `sow_awarded_date`, else blank.
- Every other dated Kit milestone starts on the next working day (Mon to Fri) after the latest `external_date` strictly earlier than its own, across all workstreams. With no earlier date, it starts on `project_start`.
- Undated milestones have a blank start.
- `PM-02` starts and finishes on its own date, since closure is recorded at final acceptance.
- The `Recurring` row runs from `project_start` to the `PM-02` date.

**Health formula** (column M)

```text
=IF(L6="Complete","Complete",IF(I6="","Date TBC",IF(TODAY()>I6,"Overdue",IF(AND(H6<>"",TODAY()>H6),"In Buffer","On Track"))))
```

Conditional fills on M: `Overdue` light red (`FEE2E2`), `In Buffer` amber (`COLOR_WARNING_BG_HEX`), `Date TBC` amber, `On Track` and `Complete` light green (`DCFCE7`).

**Notes auto-flags**

- `External date not confirmed [CONFIRMATION REQUIRED]` when `external_date` is empty.
- `Owner unassigned` when the owner contains `UNASSIGNED` or equals `Unassigned`.
- `No deliverables mapped` for a Kit milestone with no deliverables under it.
- `Added from PM best practice` on `PM-02` and on `PM-01` when no gate decision exists.

**Weekly timeline** (columns V onward)

- One column per week, headed with that week's Monday as a date (format `d-mmm`), width 4.5, header text rotated 90 degrees.
- Span: from the Monday on or before the earliest date in G, H, or I, to the Monday on or after the latest date. Cap at 78 columns. If capped, add `Timeline truncated at 78 weeks` to the row 4 instruction.
- If no row has any date, write no timeline columns and add `Timeline appears once milestone dates are confirmed` to row 4.
- Conditional formatting, applied in this priority order with stop-if-true:
    1. Week containing I (external date) on `Milestone` rows: navy fill.
    2. Week containing H (buffer date) on `Milestone` rows: accent blue fill.
    3. Span from G to I on `Milestone` and `Recurring` rows: light blue fill (`DBEAFE`).
    4. Span from G to I on `Workstream` rows: primary blue fill.
- A span test for a header cell in V5: `=AND($G6<>"",$I6<>"",V$5<=$I6,V$5+6>=$G6)`.
- A rule on `$B6` targets each row type, so the formatting keeps working after users sort or filter.

**Sheet behavior**

- Freeze panes at `F6`, keeping the code, type, workstream, ID, and name visible.
- Autofilter on `A5:U{last_row}`.
- Outline grouping: child rows at outline level 1 under their workstream row, with the summary row above (`sheet_properties.outlinePr.summaryBelow = False`).
- Workstream rows: bold, light background fill across A to U.

## 6. Tab 2: WBS

The WBS decomposes every Schedule row into work packages and tasks, four levels deep. Levels 1 and 2 are identical to the Schedule, with the same codes, names, and order. Levels 3 and 4 add the Startup Kit's deliverables and backlog work packages, plus the best-practice tasks needed to reach each milestone.

**Hierarchy**

| Level | Element Type | Example code | What it is |
| --- | --- | --- | --- |
| 1 | `Workstream` | `4` | Taxonomy workstream (section 4) |
| 2 | `Milestone` or `Recurring` | `4.2` | Kit milestone, `PM-01`, `PM-02`, or `Ongoing Governance & Reporting` |
| 3 | `Deliverable` or `Work Package` | `4.2.1` | A Kit deliverable mapped to that milestone, or a named activity package |
| 4 | `Task` | `4.2.1.3` | A Kit backlog item or a best-practice task |

Codes are assigned depth-first, numbering children 1, 2, 3 under each parent. Codes are strings; never sort rows by code, because `4.10` would sort before `4.9`. Row order always comes from the builder.

**Level 3 order under each Kit milestone**

1. `{Workstream} Milestone Activities` work package, holding that workstream's template tasks.
2. Each mapped deliverable, by natural sort of deliverable ID.

### 6.1 Deliverable-to-milestone mapping

Each deliverable maps to exactly one Kit milestone. Apply these rules in order in `mapping.py`; the first match wins and its name is written to `Mapping Basis`.

1. **Work package link.** A `WorkPackageSeed` with `parent_deliverable_id == deliverable.id` has `linked_milestones` naming a Kit milestone ID. If links point to several milestones, use the earliest-dated. Basis: `Backlog link`.
2. **ID mention.** The deliverable ID appears as a whole word in a milestone's description, `key_dependencies`, or `critical_path_assumptions`. Basis: `Referenced by milestone`.
3. **Date.** `submission_target_date` is set. Use the earliest Kit milestone with `external_date >= submission_target_date`. Basis: `Submission date`.
4. **Text overlap.** Tokenize the deliverable name and each milestone description: lowercase, words of 3 or more letters, minus a small stop-word list (`the, and, for, with, of, to, a, in, on, phase, milestone, deliverable, delivery, project`). Score = shared tokens divided by deliverable tokens. Take the best score if it is at least `0.25`; ties go to the earlier milestone. Basis: `Name match`.
5. **Fallback.** The latest-dated Kit milestone, or the last in Schedule order if none is dated. Basis: `Unmapped - confirm milestone`. Count it in `PMOWorkbookResult.unmapped_deliverables` and add a Notes flag.

If the baseline has no Kit milestones at all, create one placeholder milestone `MS-TBC` named `Delivery milestones to be confirmed` in `BLD`, with source `PM Best Practice` and note `No milestones in Startup Kit [CONFIRMATION REQUIRED]`. Map all deliverables to it.

### 6.2 Tasks under a deliverable

In this order:

1. **Kit backlog items.** One task per `WorkPackageSeed` whose `parent_deliverable_id` matches, ordered by `preliminary_sequence`, then ID. Name = `title`, owner = `owner`, Source = `Startup Kit - Backlog Seed`, Source ID = WP ID. Map status `Draft` to `Not Started`; keep any other valid status; otherwise use `Not Started`. With no matching work packages, add one best-practice task: `Produce {deliverable name}`.
2. `Assemble acceptance evidence: {evidence_required}`. Owner: deliverable owner.
3. `Internal quality review of {deliverable name} against acceptance criteria`. Owner: `Delivery Manager`.
4. `Submit {deliverable name} for client review (review window: {review_window})`. Owner: deliverable owner. Finish: `submission_target_date`, else the milestone buffer date.
5. `Address client feedback and rework ({rejection_rework_path})`. Owner: `Talent PM`.
6. `Obtain written acceptance from {client_approver}`. Owner: `Delivery Manager`. Finish: the milestone external date.

The deliverable's level 3 row carries `acceptance_criteria` in the Acceptance column. Placeholder values such as `[CONFIRMATION REQUIRED]` stay visible in task names and get the warning fill.

### 6.3 Workstream template tasks

These go in each Kit milestone's `Milestone Activities` package. The first package of every Kit milestone, whichever template it uses, ends with the closing task `Confirm {milestone ID} completion and update schedule status` (owner `Delivery Manager`, finish = external date). All other template tasks finish on the milestone buffer date, else the external date.

| Workstream | Tasks, in order (owner) |
| --- | --- |
| Discovery & Requirements | Confirm discovery objectives, scope, and participants (Delivery Manager) · Schedule and facilitate stakeholder discovery workshops (Talent PM) · Document current state, requirements, and constraints (Talent PM) · Prioritize requirements with the client product owner (Delivery Manager) · Log discovery findings as RAID items and open questions (Talent PM) · Obtain client approval of the requirements baseline (Delivery Manager) |
| Design & Architecture | Confirm design principles, standards, and non-functional requirements (Talent PM) · Produce solution design and architecture artifacts (Talent PM) · Conduct internal technical design review (Delivery Manager) · Walk the client through the design and capture feedback (Delivery Manager) · Update backlog and RAID for design decisions (Talent PM) · Obtain client design sign-off (Delivery Manager) |
| Build & Configuration | Confirm environments, tooling, and access are in place (Talent PM) · Refine and prioritize the backlog for this milestone (Talent PM) · Plan iterations or sprints to the milestone date (Talent PM) · Develop and configure in-scope features (Talent PM) · Peer review and unit test completed work (Talent PM) · Demo completed work to the client (Delivery Manager) · Update backlog, RAID, and status report (Talent PM) |
| Data & Integration | Confirm data sources, owners, and access (Talent PM) · Define data mapping and interface specifications (Talent PM) · Build integrations or migration routines (Talent PM) · Run trial loads or integration tests (Talent PM) · Reconcile and validate results with the data owner (Delivery Manager) · Log data quality issues in RAID (Talent PM) |
| Testing & Quality Assurance | Agree test strategy, scope, and entry and exit criteria (Delivery Manager) · Prepare test cases, test data, and environments (Talent PM) · Execute system and integration testing (Talent PM) · Triage and resolve defects (Talent PM) · Support client user acceptance testing (Delivery Manager) · Obtain test exit and UAT sign-off (Delivery Manager) |
| Deployment & Release | Prepare release and cutover plan, including rollback (Talent PM) · Agree go/no-go criteria with the client (Delivery Manager) · Hold release readiness review (Delivery Manager) · Execute deployment (Talent PM) · Run post-deployment verification (Talent PM) · Communicate release outcome to stakeholders (Delivery Manager) |
| Transition & Hypercare | Agree handover and hypercare scope and exit criteria (Delivery Manager) · Produce runbooks and handover documentation (Talent PM) · Deliver knowledge transfer sessions (Talent PM) · Provide hypercare support and track incidents (Talent PM) · Transfer open RAID items to the client or support owner (Delivery Manager) · Obtain hypercare exit sign-off (Delivery Manager) |

A Kit `PMG` milestone that is not a gate, closure, or kickoff milestone (section 4) uses the Governance template: Prepare review materials and evidence (Delivery Manager) · Hold the review with client and Toptal stakeholders (Delivery Manager) · Record decisions in the decision log and actions in the RAID Log (Delivery Manager) · Obtain approval of the review outcome (PMO Lead). Store all templates in `task_library.py` as `TaskTemplate(name: str, owner_role: str, finish_anchor: Literal["buffer", "external"])`.

### 6.4 Governance elements

**PM-01 (or the Kit gate milestone)** has two level 3 packages:

- `Mobilization Activities`:
    1. Hold internal kickoff with the delivery team (Delivery Manager).
    2. Complete talent onboarding and Startup Kit walkthrough (Talent PM). Finish: `talent_onboarding.onboarding_completion_date`. Source: `Startup Kit - Talent Onboarding` when that record exists.
    3. One task per entry in `talent_onboarding.staffing_gaps`: `Close staffing gap: {gap}` (Talent PM). Source: `Startup Kit - Talent Onboarding`.
    4. Confirm stakeholder register and RACI with the client (Delivery Manager).
    5. Confirm communications and reporting cadence (Delivery Manager).
    6. Baseline the project schedule, WBS, and RAID Log (PMO Lead).
    7. Hold client kickoff meeting (Delivery Manager).
- `G-01 Readiness Checklist`: one task per `readiness_checklist` item, named `{item_id}: {gate_criterion}`. Owner: item owner. Finish: item `due_date`, else the PM-01 date. Source: `Startup Kit - G-01 Checklist`. Source ID: `item_id`. Linked Action ID: every `action_required_items[].action_id` whose `checklist_id` equals the item ID. Status mapping: `Complete`, `Approved`, and `Approved with Exception` map to `Complete`; `Exception Required` and `Rework Required` map to `Blocked`; `In Progress`, `Review Required`, and `Confirmation Required` map to `In Progress`; `Not Started` maps to `Not Started`.

**Ongoing Governance & Reporting** has one level 3 package, `Governance Cadence`. Its tasks run from `project_start` to the PM-02 date, with the Cadence column filled:

- One task per `communications_plan` item: `{name} for {audience} ({format})`. Owner: `content_owner`. Cadence: `cadence`. Source: `Startup Kit - Communications Plan`. Source ID: item ID.
- `Review and update the RAID Log` (Delivery Manager, Weekly).
- `Maintain the decision log` (Delivery Manager, As needed).
- `Update schedule and WBS status` (Delivery Manager, Weekly).
- `Raise change requests when triggers are met: {commercial_guardrails.change_control_trigger}` (PMO Lead, As needed). Source: `Startup Kit - Commercial Guardrails` when present.
- `{governance_tier}-tier governance health review` (PMO Lead, Monthly).

**PM-02 (or the Kit closure milestone)** has one package, `Closure Activities`. Every task finishes on the PM-02 date:

1. Confirm all deliverables are formally accepted (Delivery Manager).
2. Close or transfer all open RAID items (PMO Lead).
3. Issue final status report (Delivery Manager).
4. Run lessons-learned review (PMO Lead).
5. Archive project records and acceptance evidence (PMO Lead).
6. Complete talent offboarding and access removal (Talent PM).
7. Obtain formal project closure sign-off from the client (Delivery Manager).

### 6.5 Columns

| Col | Header | Content |
| --- | --- | --- |
| A | WBS Code | Dotted code |
| B | Level | 1 to 4 |
| C | Element Type | `Workstream`, `Milestone`, `Recurring`, `Work Package`, `Deliverable`, `Task` |
| D | Name | Name, indented with cell alignment `indent = level - 1` |
| E | Workstream | Workstream name |
| F | Milestone ID | Parent milestone ID, or the row's own ID on level 2 |
| G | Deliverable ID | On deliverable rows and their tasks |
| H | Source ID | `WP-xx`, `G01-xx`, `COM-xx` |
| I | Owner | Normalized owner |
| J | Planned Start | Tasks: the milestone's Planned Start from the Schedule. Levels 1 to 3: MIN formula over descendant rows. |
| K | Planned Finish | Tasks: per the rules above. Level 2: Kit external date as a value. Levels 1 and 3: MAX formula over descendant rows. |
| L | Milestone Date | Parent milestone external date, on task rows |
| M | Status | Tasks only. Dropdown: `Not Started`, `In Progress`, `Blocked`, `Complete`, `Not Applicable`. |
| N | % Complete | Levels 1 to 3: `=IFERROR(COUNTIFS(C7:C20,"Task",M7:M20,"Complete")/(COUNTIFS(C7:C20,"Task")-COUNTIFS(C7:C20,"Task",M7:M20,"Not Applicable")),"")` over descendant rows, formatted `0%`. It counts tasks, not effort, and carries no weighting. |
| O | Cadence | Recurring tasks only |
| P | Predecessors | WBS codes, comma-separated. Each task depends on the previous task in its package. The closing template task depends on every deliverable package under the milestone. A backlog task's `dependency_references` naming other WP IDs are translated to their WBS codes and appended. |
| Q | Acceptance / Completion Criteria | Deliverable rows: `acceptance_criteria`. Checklist tasks: item `evidence`. |
| R | Linked RAID IDs | From section 7, on milestone and deliverable rows |
| S | Linked Action ID | From the source object's `linked_action_id`, or the checklist mapping above |
| T | Source | `Startup Kit - ...` or `PM Best Practice` |
| U | Mapping Basis | Deliverable rows only (section 6.1) |
| V | Notes | Auto-flags as in the Schedule, plus `Finish after milestone date` |

**Sheet behavior**

- Same title block (rows 1 to 4) and header row 5 as the Schedule, titled `TOPTAL PMO STARTUP KIT - WORK BREAKDOWN STRUCTURE`.
- Freeze panes at `E6`. Autofilter on the header row.
- Outline levels: level 2 rows at outline 1, level 3 at outline 2, level 4 at outline 3, with the summary row above.
- Row styling by level: level 1 navy fill with white bold text; level 2 light background, bold; level 3 bold; level 4 plain.
- Conditional formatting on task rows: red font on K when `K > L`, with both non-blank.

## 7. Tab 3: RAID Log

The RAID Log merges the Startup Kit's three RAID-type registers into one list, gives every row a stable `RAID-NN` ID, and links each row to a Schedule milestone and WBS code where the Kit supports the link. It adds no best-practice risks: every row comes from the Kit.

**Sources, in this order**

| Order | Baseline field | Kit section | Type |
| --- | --- | --- | --- |
| 1 | `raid_items` | RAID Log | As recorded |
| 2 | `dependencies_assumptions` | Dependency and Assumption Log | `Dependency` or `Assumption` |
| 3 | `contract_ambiguities` | SOW Interpretation Summary | `Issue` |

Assign `RAID-01`, `RAID-02` ... in this order, without re-sorting, so IDs stay stable across runs. The original ID (`DEP-01`, `AMB-02`) goes in Source ID.

**Deduplication.** Normalize descriptions (lowercase, strip punctuation, collapse whitespace). When a `dependencies_assumptions` row has the same type and normalized description as an earlier `raid_items` row, keep one row. Join both Source values with `; `, keep the dependency row's Source ID, and prefer whichever owner is not a placeholder.

**Field mapping**

| Column | `raid_items` | `dependencies_assumptions` | `contract_ambiguities` |
| --- | --- | --- | --- |
| Type | `type` | `type` | `Issue` |
| Description | `description` | `description` | `{category}: {conflicting_clauses}` |
| Category | `category` | `category` | `Contract` |
| Owner | `owner` | `owner` | Owner of the matching action item, else `[UNASSIGNED - TO BE CONFIRMED]` |
| Probability | `probability`, Risks only | Blank | Blank |
| Impact | `impact` | Blank | Blank |
| Severity | `severity` | Blank | Blank |
| Trigger / Early Warning | `trigger_or_early_warning` | `escalation_trigger` | Blank |
| Mitigation / Response | `mitigation_or_response` | Blank | `recommended_clarification` |
| Due Date | `due_date` | `required_validation_date` | Blank |
| Status | `status` | `status` | `status` |
| Linked Decision | `linked_decision` | Blank | Blank |
| Linked Dependency / Assumption | `linked_dependency_or_assumption` | Blank | Blank |
| Linked Action ID | `linked_action_id` | `linked_action_id` | `linked_action_id` |
| Notes | Auto-flags | `Impact if unmet: {impact_if_unmet}` + auto-flags | `Risk impact: {risk_impact}` + auto-flags |

Apply `sanitize_report_text` to every text field, which matters most for `conflicting_clauses`. Whenever an owner is a placeholder and `linked_action_id` matches an `action_required_items` entry, use that action's owner instead.

**Value normalization**

- Probability and Impact: `very high`, `critical`, and `high` become `High`; `medium` and `moderate` become `Medium`; `low` and `very low` become `Low`. Anything else becomes `Medium` with the note `Rating normalized from '{original}'`.
- Status: `Open`, `In Progress`, `Monitoring`, `Escalated`, and `Closed`. `Resolved`, `Done`, and `Complete` become `Closed`; `Pending` and `Unconfirmed` become `Open`. Anything else becomes `Open` with the note `Status normalized from '{original}'`. Closed rows are kept.
- `Linked Dependency / Assumption`: if the value is a `DEP-xx` ID present in the log, write `RAID-07 (DEP-01)`.

**Milestone linking** (`mapping.py`, first match wins)

1. `linked_milestone` names a Schedule milestone ID.
2. `linked_deliverable` names a deliverable; use that deliverable's milestone and its WBS code.
3. A Schedule milestone ID or deliverable ID appears as a whole word in the description or the linked fields.
4. The normalized description equals, or is contained in, an entry of a milestone's `key_dependencies` or `critical_path_assumptions`.
5. No link: leave Linked Milestone and Linked WBS Code blank. Classify Workstream from the description with the section 4 keyword scorer, defaulting to Project Management & Governance.

With a link, Workstream is the linked milestone's workstream. These links also fill the back-references in Schedule column Q and WBS column R.

**Columns**

| Col | Header | Notes |
| --- | --- | --- |
| A | RAID ID | `RAID-NN` |
| B | Type | Dropdown: `Risk`, `Assumption`, `Issue`, `Dependency` |
| C | Description | Wrapped, width 50 |
| D | Category | |
| E | Workstream | Dropdown from the taxonomy |
| F | Linked Milestone | Dropdown from Schedule milestone IDs |
| G | Linked WBS Code | |
| H | Owner | |
| I | Probability | Dropdown: `Low`, `Medium`, `High` |
| J | Impact | Dropdown: `Low`, `Medium`, `High` |
| K | Severity | Kit value, as written |
| L | Score (P x I) | `=IF(AND(B6="Risk",I6<>"",J6<>""),MATCH(I6,{"Low","Medium","High"},0)*MATCH(J6,{"Low","Medium","High"},0),"")`. Fills: 6 to 9 light red, 3 to 4 amber, 1 to 2 light green. |
| M | Trigger / Early Warning | |
| N | Mitigation / Response | |
| O | Due Date | Date. Red font when past due and Status is not `Closed`. |
| P | Status | Dropdown from the normalized list |
| Q | Date Raised | `kit_drafted_date`, else the generation date |
| R | Last Updated | Blank, for the PM |
| S | Linked Decision | |
| T | Linked Dependency / Assumption | |
| U | Linked Action ID | |
| V | Source | `Startup Kit - RAID Log`, `Startup Kit - Dependency and Assumption Log`, or `Startup Kit - Contract Ambiguities` |
| W | Source ID | |
| X | Notes | Auto-flags joined with `; `, including `Owner unassigned` and `Mitigation not documented` when the mitigation is empty, `[TBD]`, or `[CONFIRMATION REQUIRED]` |

**Sheet behavior.** Same title block pattern, titled `TOPTAL PMO STARTUP KIT - RAID LOG`. Freeze panes at `D6`, autofilter on the header row, and grey text on rows where Status is `Closed`. With no RAID items at all, write the header plus one row reading `No RAID items recorded in the Startup Kit`, and leave the dropdowns in place for 200 blank rows.

## 8. Workbook-wide rules

The workbook should look like the Word Startup Kit's tables: Arial, a navy header row, and amber highlighting on anything unconfirmed. It must open cleanly in Excel 2016 or later without repair prompts.

**Workbook structure**

- Sheet order: `Project Schedule` (active on open), `WBS`, `RAID Log`, then a hidden sheet `_Lists` with `sheet_state = "hidden"`.
- `_Lists` holds one column per dropdown source, each exposed as a workbook defined name: `WorkstreamList`, `ScheduleStatusList`, `TaskStatusList`, `RAIDTypeList`, `RAIDStatusList`, `RatingList`, `MilestoneIDList`. Every data validation references a defined name, never an inline list.
- Data validations cover the data rows plus 200 blank rows below, so users can add rows. Use `showErrorMessage = True` with error style `warning`, so custom values are allowed after a prompt.
- Workbook properties: title `{Project} PMO Startup Toolkit`, creator `Toptal PMO Startup Kit Generator v{__version__}` (from `src/version.py`). No other personal data.
- Set `wb.calculation.fullCalcOnLoad = True`, because `openpyxl` writes formulas without cached values.
- Tab colors: Schedule navy, WBS primary blue, RAID Log accent blue.

**Styling**

- Font: Arial throughout. 9 pt for body, 9.5 pt bold white for headers.
- Header row 5: `COLOR_NAVY_HEX` fill, white bold, wrapped, vertically centered, height 32.
- Borders: thin `COLOR_BORDER_HEX` on all data cells.
- RAID Log body: zebra striping with `COLOR_LIGHT_BG_HEX` on odd rows. Schedule and WBS use the level styling in sections 5 and 6 instead.
- Text columns wrap and align top-left. Dates use number format `yyyy-mm-dd` and are written as `datetime.date` values, never strings.
- Placeholders: any cell whose text contains `[CONFIRMATION REQUIRED]`, `UNASSIGNED`, `[TBD]`, or matches `ACTION_TAG_REGEX` gets a `COLOR_WARNING_BG_HEX` fill and bold text. Apply this in Python at write time, not as conditional formatting. A blank date cell whose source date is missing gets the same fill.
- Zoom 90%. Print setup on every visible sheet: landscape, fit to 1 page wide, row 5 repeated as the print title row, footer `{Project} - {sheet name} - Page &P of &N`.

**Safety and robustness**

- **Formula injection.** Any text from the baseline that begins with `=` must be written as a string: assign the value, then set `cell.data_type = "s"`. Only the builder's own formulas may be formulas.
- **Illegal characters.** Strip characters matched by `openpyxl.cell.cell.ILLEGAL_CHARACTERS_RE` before writing, since `openpyxl` otherwise raises `IllegalCharacterError`.
- **Length.** Truncate any text over 32,000 characters and append ` [truncated]`.
- **Formula ranges.** Every MIN, MAX, and COUNTIFS formula uses the exact contiguous child range computed by the builder. A summary row with no children writes a blank instead of a formula.
- **Empty collections.** Missing `charter`, `gate_decision`, `talent_onboarding`, `commercial_guardrails`, or `communications_plan` simply omits the tasks that depend on them. No `None` or `null` text ever reaches a cell.
- **No effort data.** No header, template task name, or builder-generated formula may contain `hour`, `hrs`, `FTE`, `effort`, `capacity`, `allocation`, `utilization`, `rate`, or `cost`, matched case-insensitively as whole words. Text copied from the Startup Kit is exempt, since a RAID item may legitimately mention cost. A test enforces this (section 9).

## 9. Testing and acceptance

The work is done when every acceptance criterion below passes in `pytest`, and one manual open in Excel shows no repair prompt and no `#VALUE!` or `#NAME?` cells.

**Fixtures** (`tests/generators/pmo_workbook/conftest.py`)

- `rich_baseline`: 6 Kit milestones covering at least five workstreams, one undated milestone, and one milestone whose description contains "G-01 gate". Deliverables must exercise all five mapping rules, including one unmappable deliverable. Include backlog work packages with `dependency_references`, `raid_items` plus `dependencies_assumptions` with one duplicate pair, two `contract_ambiguities` (one `Resolved`), a readiness checklist with `Exception Required` items and matching action items, a communications plan, commercial guardrails, and talent onboarding with staffing gaps.
- `minimal_baseline`: `StartupKitBaseline(project_name="Minimal")` and nothing else.
- A fixed `today = date(2026, 10, 1)` passed to `build_workbook_model`.

**Unit tests**

| File | Covers |
| --- | --- |
| `test_workstreams.py` | Each taxonomy keyword; whole-word matching for short keywords; the later-in-taxonomy tie-break; deliverable names used only when the description has no match; the default to `BLD` |
| `test_mapping.py` | Each deliverable rule in order, including a deliverable that matches rules 3 and 4 resolving to rule 3; the fallback and its counter; `MS-TBC` creation; each RAID linking rule |
| `test_builder.py` | Row order; WBS codes; Schedule and WBS level 1 and 2 identity; Planned Start chain; PM-01 and PM-02 suppression when Kit gate or closure milestones exist; task counts per template; checklist status mapping; RAID IDs, dedup, normalization; determinism (two builds compare equal) |
| `test_writer.py` | Opens the saved file with `openpyxl.load_workbook`; sheet names and order; `_Lists` hidden; defined names exist; headers match the spec column lists exactly; formulas present in the expected cells; dates are date cells; freeze panes and autofilter set; a baseline string `=HYPERLINK("x")` lands as text; illegal characters stripped |
| `test_no_effort_columns.py` | Headers, template task names before interpolation, and formulas contain none of the banned words from section 8 |
| `test_orchestrator_export.py` | `OutputSelection.from_flags` for every row of the section 3.1 table; `run()` and `run_reingest()` with `MockLLMClient` write exactly the selected files and no CSV or JSON; the default writes only the workbook; a workbook-only re-ingest never modifies or backs up the input docx; `write_kit_docx` writes no checklist; `write_documents` writes each file once (patch `docx.Document.save` and count calls); `RunResult` paths match the files on disk |

**Acceptance criteria**

- [ ] `python main.py --non-interactive` and `python main.py --export-tools --non-interactive` write only `{Project}_PMO_Startup_Toolkit.xlsx`: no `.docx`, and no `_PMO_*.csv` or `_PMO_*.json` files.
- [ ] `--kit` writes only the Startup Kit `.docx`; `--checklist` writes only the Readiness Checklist `.docx`; `--kit --checklist` writes both Word files and no workbook; `--all` writes all three.
- [ ] Each Word document is written exactly once per run, and its extracted text and tables match today's output for the same baseline, apart from generated dates.
- [ ] A workbook-only re-ingest leaves the input `.docx` untouched, creates no backup, and logs the "not rewritten" message. `--reingest-docx ... --kit` overwrites it with a backup, as today.
- [ ] Alignment: every baseline milestone ID appears exactly once in the Schedule and once at WBS level 2; every deliverable ID exactly once at level 3; every backlog WP ID exactly once as a task; every RAID source row exactly once after dedup.
- [ ] Alignment: every copied description equals `sanitize_report_text(original)`, and every copied date equals the baseline date.
- [ ] Round trip: generate a Kit `.docx` from `rich_baseline`, re-ingest it with `StartupKitDocxParser`, export the workbook, and confirm the same milestone, deliverable, and RAID descriptions appear.
- [ ] Every Schedule milestone row has a non-blank Workstream.
- [ ] Every row added by the builder, rather than copied from the Kit, has Source `PM Best Practice`.
- [ ] No effort, hours, or capacity data anywhere, per the test above.
- [ ] `minimal_baseline` produces a valid workbook with the PMG workstream, `PM-01`, `PM-02`, `MS-TBC`, and the empty-RAID row, without raising.
- [ ] The readiness summary always prints and lists one output path per file written. The workbook summary prints only when the workbook was written, with no ANSI codes when `NO_COLOR` is set.
- [ ] `export_payloads.py` and every reference to it are gone, and the full existing test suite passes after updating tests that relied on the old `export_tools` parameter or the old `run()` return value.
- [ ] Manual: the workbook opens in Excel with no repair prompt; outline groups collapse; dropdowns work; the timeline bars render; Health and Score formulas calculate.

**Expected result: `python main.py --mock --non-interactive --export-tools`**

Use this as an end-to-end check against the mock data in `main.py`, after the `communications=` fix. Dates in parentheses are external / internal buffer.

| WBS | Row | Workstream basis | Level 3 packages |
| --- | --- | --- | --- |
| `1` | Project Management & Governance | | |
| `1.1` | `PM-01` G-01 Startup Readiness Gate Approved | Governance (derived) | G-01 Readiness Checklist (one task per checklist row; 15 with the standard checklist) |
| `1.2` | `M1` Project Kickoff & Architecture Baseline (2026-10-15 / 2026-10-08) | `Keyword: kickoff, baseline` | Mobilization Activities (6 tasks + closing task); `DEL-01` via `Name match` |
| `1.3` | Ongoing Governance & Reporting | | Governance Cadence (`COM-01`, `COM-02`, + 5 standard tasks) |
| `1.4` | `PM-02` Project Closure and Handover Accepted (2026-11-30) | Governance (derived) | Closure Activities (7 tasks) |
| `2` | Deployment & Release | | |
| `2.1` | `M2` Data Pipeline Production Go-Live (2026-11-30 / 2026-11-23) | `Keyword: production, go-live` (tie with Data & Integration) | Deployment template (6 tasks + closing task); `DEL-02` via `Name match`; `DEL-03` via `Unmapped - confirm milestone` |

Also expected: `M2` Planned Start is 2026-10-16; each deliverable package holds its one work package (`WP-01` to `WP-03`) plus 5 standard tasks; the CLI reports `Unmapped deliverables: 1`; and the RAID Log holds at least 5 rows, with the three mock RAID items first and the two contract ambiguities last as `Issue` rows, their `Section 4.2` references removed by `sanitize_report_text`.
