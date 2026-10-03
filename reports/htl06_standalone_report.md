# HTL-06 / HTL-07 standalone fact-review screen (section 17 step 1)

Date: 2026-10-03. Base commit: `5836014` (pre-check: `git status` clean).

## Spec rows (raw `Select-String` output, not quoted from memory)

```
spec\PMO_Startup_Kit_Consolidated_Spec.md:267:| HTL-06 | **What the review screen shows.** For each fact category below, the extracted value, an editable field for it, and, where one exists, the exact source sentence or table row from the ingested documents that supports it: project identity (project name, client sponsor, contract type, governance tier); the award/start date, its stated-or-not provenance (VAL-11), and its source sentence when stated; named roles (Delivery Manager, Client Contact / Approver(s)); every milestone's name, phase, external date and basis, and whether VAL-01 classified it as a gate or a checkpoint; every deliverable's phase assignment and mapping basis (MAP-03); the contract-wide review window, when one was detected (KIT-03); and every extraction-validation finding (every `VAL-01` to `VAL-11` `repaired`, `warning`, or `error` entry), shown in full, never summarized or truncated. RAID items, communications items, and deliverable acceptance-criteria text are not reviewed individually in this first release. | New | Manual, `test_review_screen_content.py` |
spec\PMO_Startup_Kit_Consolidated_Spec.md:268:| HTL-07 | **Provenance recording.** Every fact in HTL-06 gets a provenance tag the moment the reviewer acts on it: `machine_extracted_unconfirmed` (shown, left unchanged) or `human_corrected` (edited). This generalizes `award_date_source` (VAL-05) to every reviewed fact. Provenance is additive on the baseline (new fields only) and is written out beside the final documents as `review_audit.json`, so what a person confirmed or changed for a run is auditable afterward without needing to appear on every page of the Kit itself. | New | `test_review_audit.py` |
spec\PMO_Startup_Kit_Consolidated_Spec.md:324:| INV-37 | When `review_audit.json` is present, it names a provenance tag for every fact category in HTL-06, with none missing and no tag other than `machine_extracted_unconfirmed` or `human_corrected` (HTL-07). |
spec\PMO_Startup_Kit_Consolidated_Spec.md:329:1. **HTL-06, HTL-07, standalone:** build and prove the fact-review screen reading one recorded fixture's `baseline.json` directly (`arc_application_implementation`'s), with no queue, no state machine, no CLI flag, and no `orchestrator.py` call involved yet. This step does not depend on step 2 and can start immediately.
```

## What was built (new files only, plus one requirements line)

- `src/review_ui/facts.py` holds the pure, Streamlit-free logic: `load_baseline`, `prepare_review_baseline`, `build_fact_categories`, `compute_review` (provenance tags and corrections), `apply_corrections`, `build_review_audit` (Appendix Q.2 shape with an INV-37 check), `save_review` (refuses any path under `tests/fixtures/` or `tests/oracles/`), and `review_and_save`.
- `src/review_ui/app.py` is a thin Streamlit renderer. It reads `tests/fixtures/sow/arc_application_implementation/baseline.json` read-only. For each field it shows the extracted value, the source text (or `No source quote captured for this fact`), the source location and any tool-generated basis label (each explicitly labelled "not a quote"), and an edit box, plus one optional reviewer note per category. Saving writes `review_ui_scratch/arc_application_implementation/corrected_baseline.json` and `review_audit.json`.
- `src/review_ui/__init__.py`, `tests/test_review_screen_content.py`, `tests/test_review_audit.py`.
- `requirements.txt`: added `streamlit==1.65.0`.

The recorded fixture baseline is stored before validation (`validation_report` is `null`; milestones are `M1` kickoff plus `M2`–`M5`). The screen therefore runs the existing, unmodified `validate_and_repair_baseline` on an in-memory copy, which is the state HTL-02 would persist. It also runs the existing, unmodified `build_workbook_model` on a copy to read the Workbook's own Date Basis and Mapping Basis values. Neither function was changed, and the fixture file is byte-identical after loading (tested).

## Step 1: source-availability table

`SourceReference` (`src/core/models.py:228`) has only `document_name`, `clause_or_slide` and `confidence_score`. It is a location, never text.

| # | Category | Literal source quote available? | Field(s) | Screen shows |
|---|---|---|---|---|
| 1 | Project identity (name, client sponsor, contract type, tier) | **No** | `project_name`, `charter.client_name`, `contract_type`, `governance_tier`; location only: `charter.source_reference.clause_or_slide` = `Page 1 Sections 1-2; Exhibit A Sections 1, 2, 4, 8, 9`. There is no client-sponsor field; the value shown is the non-Toptal stakeholder whose role contains "Sponsor" (`Mike Magwire`, role `Client Contact / Client Sponsor and Approver`). | "No source quote captured for this fact" + "Source location (not a quote)" |
| 2 | Award/start date + provenance | **No** | `sow_awarded_date` = `2026-10-07`, `award_date_source` = `stated`. `extract_stated_award_date` (`src/extractors/date_extractor.py:47`) matches the literal SOW statement (`m.group(0)`) at run time, but discards it; it is never stored. | "No source quote captured" + "Provenance (VAL-11): stated" |
| 3 | Named roles (Delivery Manager, Client Contact / Approver) | **No**, and no location either | `charter.delivery_manager`; `stakeholders[]` (`Stakeholder` has no `source_reference` field) | "No source quote captured" |
| 4 | Milestones: phase, external date, basis, gate/checkpoint | **No** | Post-validation `milestones` (gates) / `interim_checkpoints`; location `source_reference.clause_or_slide` (e.g. `Section 2.B (Milestone 1); Exhibit A Sections 2.1 and 4`). The Workbook's Date Basis (DT-03) is a label generated by `pmo_workbook/builder.py` (`Contract date` for all four gates, `Within P1 Contract date` for CP-01). It is not a quote, and nothing more literal exists in the data. | "No source quote captured" + basis "tool-generated label, not a quote" + location |
| 5 | Deliverable phase assignment + mapping basis | **No** | WBS row from `build_workbook_model` (`Catalogue phase` for all 20); location `deliverable.source_reference.clause_or_slide` (e.g. `Exhibit A, Section 4 - Milestone 1 (HS-4762)`). Mapping Basis (MAP-03) is a generated label, not a quote. | same as row 4 |
| 6 | Contract-wide review window (KIT-03) | **No** | KIT-03's normalized result `5 business days from notice of milestone completion` (`src/llm/validation.py:507-533`; held only in a local variable and written into every `deliverable.review_window`). Its input `sow_interpretation.approval_expectations` is an LLM paraphrase ("The client has 5 business days from notice of completion…"), not verbatim, so it is **not** shown as a quote. | "No source quote captured" + location |
| 7 | Validation findings | **Yes (self-describing)**. Not a SOW quote; the finding text is the fact. | `ValidationFinding.invariant_id` / `severity` / `message`, shown in full | the message in full |

### Open findings (not backfilled in this step)

- **F1. No category stores verbatim SOW text.** HTL-06's "exact source sentence or table row" and Appendix Q.3's "Source quote" cannot be met from today's baseline. This needs a model change (a quote field on `SourceReference` or per fact) and extraction changes to capture raw sentences.
- **F2. The award-date sentence is matched and then thrown away.** VAL-11's regex already holds the literal statement (`m.group(0)`). Persisting it (e.g. a new baseline field beside `award_date_source`) is the cheapest first fix.
- **F3. `Stakeholder` has no `source_reference` at all**, so named roles have neither a quote nor a location.
- **F4. The model has no "client sponsor" field.** The screen derives it from stakeholder roles and says so on screen.
- **F5. Findings use `INV-xx` ids, not `VAL-xx`** (this fixture: `INV-01`, `INV-07`). VAL-11's conflict warning (`date_warning` in `orchestrator.run()`) is never added to the `ValidationReport`, so the screen cannot show it.

## Step 3.1: extracted values vs. oracle (`tests/oracles/arc_application_implementation.json`)

Values are what the screen displays before any edit. The phase names are checked against `arc.json`'s `phases` (the oracle `extends_reference_phase_map_from: "arc"`).

| Oracle key | Oracle value | Screen value | Match |
|---|---|---|---|
| `gate_count` | 4 | 4 gates (M1–M4) | yes |
| `phases` (via `arc.json`) | `P1 Foundation`, `P2a Services and Data`, `P2b Application Surface`, `P3 Launch` | M1 `P1 Foundation`, M2 `P2a Services and Data`, M3 `P2b Application Surface`, M4 `P3 Launch` | yes |
| `award_date` | `2026-10-07` | `2026-10-07` | yes |
| `award_date_stated_in_sow` | `true` | provenance `stated` | yes |
| `milestone_external_dates.M1` | `2026-11-17` | `2026-11-17` | yes |
| `milestone_external_dates.M2` | `2027-01-26` | `2027-01-26` | yes |
| `milestone_external_dates.M3` | `2027-03-02` | `2027-03-02` | yes |
| `milestone_external_dates.M4` | `2027-04-06` | `2027-04-06` | yes |
| `named_delivery_manager` | `Saadia Iqbal` | `Saadia Iqbal` | yes |
| `named_client_contact` | `Mike Magwire` | `Mike Magwire` | yes |
| `contract_wide_review_window` | `5 business days from notice of milestone completion` | same | yes |
| `checkpoint_phases.CP-01` | `P1` | `P1 Foundation` (code `P1`) | yes |

All the oracle keys the screen covers match. `milestone_description_phrasing` is a Kit-text property and is not shown on this screen.

## Streamlit

- Version added: **`streamlit==1.65.0`** (latest at the time; installed into `.venv`).
- `streamlit run src/review_ui/app.py --server.headless true` (port 8599) started cleanly: `Uvicorn server started on :::8599`, `/_stcore/health` returned `ok`, and there were no errors in the log. The server was then stopped.
- A headless server does not execute the script until a browser connects. So the script was also run once through `streamlit.testing.v1.AppTest`: no exceptions; 7 expanders in HTL-06 order (`Project identity`, `Award / start date`, `Named roles`, `Milestones`, `Deliverable phase assignment`, `Contract-wide review window`, `Validation findings`); 45 text inputs (38 fact fields + 7 notes), 2 text areas (findings), 1 tier selectbox; the award input was pre-filled with `2026-10-07`.

## Test results

- `tests/test_review_screen_content.py`: 18 passed (category list and order; values per category; oracle comparison; Date Basis and Mapping Basis labels; findings in full; no fabricated quote in categories 1–6; locations per the Step 1 table; fixture unchanged by loading).
- `tests/test_review_audit.py`: 9 passed. One edit (award date forced to `2026-10-01`) gives `human_corrected` only for `award_date`, `machine_extracted_unconfirmed` for the other six, and one correction `{field: award_date, extracted: 2026-10-07, corrected_to: 2026-10-01, reviewer_note: ...}`. Zero edits give all seven `machine_extracted_unconfirmed` and `corrections: []`. Also covered: whitespace-only edits are not corrections; multi-field edits; invalid date rejected; INV-37 enforcement; refusal to write under `tests/fixtures/` or `tests/oracles/`.
- Full suite, plain `pytest -q`: **`600 passed in 207.69s (0:03:27)`** (previously 573; +27 new, no other change).

## Files touched

`git status` before commit: `M requirements.txt`, `?? src/review_ui/`, `?? tests/test_review_audit.py`, `?? tests/test_review_screen_content.py`, plus this report. Nothing under `tests/fixtures/`, `tests/oracles/` or `spec/`, and neither `main.py` nor `src/orchestrator.py`, was touched. No `review_queue/`, `ReviewStorage`, state machine, `--review` flag or run-listing screen was added.

## Not verified / limitations

- **No browser click-through.** Rendering was verified headlessly (`AppTest`) and via server start; an actual human edit-and-save in a browser was not performed. The save path is covered by the pure-function tests.
- **Long-quote trimming (DECK-05 discipline) is not exercised**, because no category has a quote to trim (F1). Findings are deliberately never trimmed, per HTL-06.
- **HTL-07's "additive on the baseline (new fields only)" is not implemented.** Adding fields to `StartupKitBaseline` is a model change outside this step's scope, so provenance lives only in `review_audit.json`. `corrected_baseline.json` carries the corrected values, not tags.
- **Deliverable phase edits** are applied by updating `sow_stories_catalogue[].phase` for that deliverable. This round-trips through the existing builder's "Catalogue phase" path, but regenerating documents from a corrected baseline is out of scope here (later steps).
- **`review_ui_scratch/` is not in `.gitignore`.** A real save will show it as untracked. Not changed, because this step was limited to new files.
