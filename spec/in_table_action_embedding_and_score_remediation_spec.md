# Software Specification: In-Table Action Embedding and Score Remediation

**Status**: Authoritative Architecture Specification  
**Date**: 2026-09-27  
**Target Modules**: `src/core/models.py`, `src/generators/docx_generator.py`, `src/generators/checklist.py`, `src/extractors/startup_kit_docx_parser.py`, `src/scoring/readiness_engine.py`, `src/scoring/cli_reporter.py`, `src/orchestrator.py`, `main.py`  
**Baseline Application Version**: 0.1.1  

---

## 1. Executive Summary & Operational Goals

The primary objective of this architecture is to establish a **closed-loop governance and remediation mechanism** for the Toptal PMO Startup Kit Generator. In traditional project governance, review findings are recorded in disconnected action lists or static compliance checklists, forcing project managers to manually cross-reference findings against source deliverables.

Under the **In-Table Action Embedding & Score Remediation** paradigm:
1. **Direct In-Table Deficiency Localization**: Unresolved validation points, missing owners, unconfirmed dates, and open contractual ambiguities are tagged (`[ACT-01]` through `[ACT-15]`) and visually highlighted directly inside the relevant Section 4 Layer 1, Layer 2, and Layer 3 table cells (Deliverables Matrix, Milestone Delivery Plan, Talent Roster, RAID Log, Commercial Guardrails, Contract Ambiguities).
2. **Table-Driven Score Recovery**: Delivery managers and PMO stakeholders improve the project's **Startup Readiness Score** not by altering abstract checklist flags, but by directly editing the flagged table cells in Microsoft Word.
3. **Automated Re-ingestion & Rescoring**: When an edited `.docx` document is re-ingested (`--reingest-docx`), the system parses modified cells, sanitizes temporary `[ACT-XX]` annotations, deterministically recomputes dimensions ($D_1$ to $D_4$), clears resolved actions, and advances the G-01 Gate Decision toward unconditional Green approval.

---

## 2. Closed-Loop Remediation Architecture

### 2.1 Workflow Lifecycle Diagram

```mermaid
graph TD
    A[Project Input Documents: SOW, Decks, Contracts] --> B[Multi-Format Ingestion & Pydantic Validation]
    B --> C[LLM Structured Extraction & Synthesis]
    C --> D[ReadinessScoringEngine Initial Evaluation]
    D -->|Identifies Deficiencies| E[Generate ActionRequiredItems: ACT-01 .. ACT-15]
    D -->|Calculates Baseline Dimensions| F[Initial Readiness Score: e.g., 74.2% Amber]
    E --> G[DocxGenerator & G01ChecklistRenderer]
    G -->|Embeds In-Table [ACT-XX] Tags & Amber Shading| H[Generated Word Document: *_Startup_Kit.docx]
    H -->|Stakeholder Edits: Names Leads, Locks Dates, Confirms Criteria| I[Edited Word Document]
    I --> J[StartupKitDocxParser]
    J -->|Regex Sanitization: Strips [ACT-XX] Tags| K[Parsed Clean StartupKitBaseline]
    K --> L[ReadinessScoringEngine Rescoring & Resolution]
    L -->|Recalculates D1..D4 & Clears Resolved Actions| M[Elevated Readiness Score: e.g., 92.5% Green]
    M --> N[Regenerated Clean Word Document & CLI Telemetry Dashboard]
```

### 2.2 Core Operational Principles
- **Locality of Remediation**: The action indicator and the editable data live in the exact same table cell.
- **Strict Determinism**: Re-ingesting an unedited document yields identical scores down to 0.1% precision; re-ingesting an edited document deterministically awards points per resolved item.
- **Data Hygiene**: Saved models and re-generated documents contain clean business data with no lingering markup tags.

---

## 3. Comprehensive Artifact-to-Table Action Mapping Matrix

Every governance control in the G-01 Startup Readiness Gateway maps to an `ActionRequiredItem` ID, a specific Section 4 artifact table, concrete table columns, an in-cell placeholder format, and a mathematical score recovery delta:

| Gate ID | Section 4 Artifact & Table | Table Column & Flagged Cell | Placeholder Syntax & Tag | Remediation Action in Cell | Dimension & Score Recovery Delta |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `G01-01` | **Project Charter Header** | SLA Status / Waiver Note | `[ACTION REQUIRED: Log Waiver] [ACT-01]` | Log PMO Retroactive Waiver in SLA record | Dimension 1 ($+1.5\%$) |
| `G01-02` | **Charter Delivery Model** | Cadence & Governance Model | `[CONFIRMATION REQUIRED] [ACT-02]` | Confirm governance tier and weekly cadence | Dimension 1 ($+2.0\%$) |
| `G01-03` | **Deliverables Matrix** | Acceptance Criteria & Internal Owner | `[CONFIRMATION REQUIRED] [ACT-03]`<br>`[UNASSIGNED] [ACT-03]` | Replace with explicit test criteria and named owner | Dimension 2 ($+3.5\%$) |
| `G01-04` | **Milestone Delivery Plan** | External Date & Buffer Date | `[CONFIRMATION REQUIRED] [ACT-04]`<br>`[TBD] [ACT-04]` | Enter locked client date and 7-day buffer date | Dimension 1 & 4 ($+3.0\%$) |
| `G01-05` | **RAID Log** | Risk Owner & Mitigation Strategy | `[UNASSIGNED] [ACT-05]`<br>`Active monitoring [ACT-05]` | Assign named owner and concrete mitigation steps | Dimension 4 ($+2.0\%$) |
| `G01-06` | **Talent Onboarding Record** | Onboarding Leadership / KO Deck | `[UNASSIGNED] [ACT-06]` | Confirm Talent PM / DM kickoff deck approval | Dimension 1 ($+1.5\%$) |
| `G01-07` | **SOW Interpretation Summary** | Customer Obligations & Access | `[CONFIRMATION REQUIRED] [ACT-07]` | Issue access prerequisites list to client sponsor | Dimension 1 ($+2.5\%$) |
| `G01-08` | **Talent Roster Table** | Named Talent & Staffing Status | `[UNASSIGNED] [ACT-08]`<br>`Pending [ACT-08]` | Assign talent name and update status to `Staffed` | Dimension 3 ($+4.0\%$) |
| `G01-09` | **Stakeholder Model** | Client Sponsor & Decision Rights | `[CONFIRMATION REQUIRED] [ACT-09]` | Confirm primary client sign-off authority and title | Dimension 3 ($+2.0\%$) |
| `G01-10` | **RACI Decision Matrix** | Decision / Activity Roles | `[TBD] [ACT-10]` | Align RACI matrix decision rights with client | Dimension 1 ($+1.5\%$) |
| `G01-11` | **Communications Plan** | Audience, Owner & Cadence | `[CONFIRMATION REQUIRED] [ACT-11]` | Confirm weekly status distribution list & owner | Dimension 2 ($+1.5\%$) |
| `G01-12` | **Commercial Guardrails** | Budget Baseline & Margin Policy | `[NOT STATED] [ACT-12]` | Baseline SOW value, rate cards, and margin cap | Dimension 4 ($+3.0\%$) |
| `G01-13` | **Change Control Procedure** | Change Order Route & Threshold | `[CONFIRMATION REQUIRED] [ACT-13]` | Confirm written change order sign-off route | Dimension 4 ($+2.0\%$) |
| `G01-14` | **Contract Ambiguities Table** | Anomaly ID & Conflicting Clauses | `Open Conflict [ACT-14]` | Document agreed interpretation or signed waiver | Dimension 4 ($+3.5\%$) |
| `G01-15` | **Startup Readiness Checklist** | Checklist Row Status | `Review Required [ACT-15]` | Verify all open questions reviewed at kickoff | Dimension 1 ($+2.5\%$) |

---

## 4. Word Document Rendering Specifications

### 4.1 Visual Formatting Standards
1. **Warning Background Shading**: All cells containing active `[ACT-XX]` action items or unassigned/unconfirmed placeholders must be rendered with light amber shading (`#FEF3C7` / `COLOR_WARNING_BG_HEX`).
2. **Cell Text Annotation Syntax**:
   - `[UNASSIGNED] [ACT-03]` (for missing owners)
   - `[CONFIRMATION REQUIRED] [ACT-04]` (for unconfirmed milestone dates or acceptance criteria)
   - `Pending [ACT-08]` (for unstaffed roster roles)
3. **Artifact-Level Alert Banners**:
   - For every Section 4 artifact containing one or more active actions, a callout banner is rendered immediately beneath the artifact subheading:
     ```text
     ⚠️ Artifact Action Required: ACT-03 (Talent PM) - Acceptance criteria contains [CONFIRMATION REQUIRED] or unassigned deliverable owner.
     • Corrective Remediation: Finalize acceptance test criteria and assign named delivery owner (+3.5% Score Recovery)
     ```
   - Styling: Amber background (`#FEF3C7`), dark amber border (`#D97706`), bold header.

### 4.2 Document Layout Order
```
1. Header Block & Metadata (Project, Tier, SLA Status)
2. Executive Readiness Gateway (G-01)
   2.1 Governance Policy (WR-03 No-Mobilize Mandate)
   2.2 Executive Gate Decision Dashboard Box (Score, Breakdown, Gate Status)
   2.3 Action Required Table (8 Columns: ID, Type, Gate ID, Artifact, Finding/Action, Owner, Deadline, Delta)
   [ PAGE BREAK ]
   2.4 G-01 Startup Readiness Checklist Table (15-Row Audit Matrix)
3. Layer 1: Executive Startup Pack (Charter, SOW Summary, Milestones, Ambiguities)
4. Layer 2: Delivery Workbench (Deliverables Matrix, RAID Log, Decisions, Communications)
5. Layer 3: Assurance Pack (Stakeholders, RACI Matrix, Commercial Guardrails, Talent Roster)
```

---

## 5. Docx Parser Extraction & Regex Sanitization Rules

### 5.1 Tag Sanitization Standard
During re-ingestion, `StartupKitDocxParser.clean_text()` must strip all variations of action markers while preserving surrounding user text:
- Pattern: `r'\[ACT-[^\]]+\]'`
- Target replacements:
  - `"[UNASSIGNED] [ACT-03]"` $\rightarrow$ `"[UNASSIGNED]"`
  - `"Sarah Jenkins [ACT-03]"` $\rightarrow$ `"Sarah Jenkins"`
  - `"[CONFIRMATION REQUIRED] [ACT-04]"` $\rightarrow$ `"[CONFIRMATION REQUIRED]"`
  - `"2026-10-15 [ACT-04]"` $\rightarrow$ `"2026-10-15"`
  - `"Staffed [ACT-08]"` $\rightarrow$ `"Staffed"`

### 5.2 Deserialization Rules
1. **Deliverables Table**:
   - If acceptance criteria is non-empty and does not contain `[CONFIRMATION REQUIRED]`, store the verified criteria.
   - If owner is not `"Unassigned"` and does not contain `"UNASSIGNED"`, store the named owner.
2. **Milestone Table**:
   - Parse external dates and internal buffer dates; convert valid string representations into `datetime.date` objects.
3. **Talent Roster Table**:
   - Treat status values of `"Confirmed"`, `"Active"`, `"Staffed"`, and `"Approved"` as confirmed talent members.
4. **G-01 Checklist Table**:
   - If a row's status is modified from `"Exception Required"` to `"Complete"` or `"Approved"`, set `exception_required = False`.

---

## 6. Readiness Scoring Engine Rescoring Lifecycle

The `ReadinessScoringEngine` computes the composite score:

$$\text{Readiness Score} = \left( 0.40 \times D_1 + 0.25 \times D_2 + 0.20 \times D_3 + 0.15 \times D_4 \right) \times 100$$

### 6.1 Dimension Recalculation Rules
- **$D_1$ (Mandatory Controls, 40%)**:
  $$D_1 = \max\left(0.0, \min\left(1.0, \frac{\sum \text{Score}(I_k)}{15} - (E \times 0.02)\right)\right)$$
  Resolving checklist exceptions directly increases $D_1$ by clearing the 2% penalty per exception and elevating item weights.
- **$D_2$ (Deliverables Rigor, 25%)**:
  Assigning deliverable owners (+0.30) and confirming acceptance criteria (+0.40) elevates $D_2$.
- **$D_3$ (Talent Staffing, 20%)**:
  Replacing unassigned roster roles with confirmed names increases $S_{\text{roster}}$ ($0.40 \times \frac{\text{Staffed}}{\text{Total}}$).
- **$D_4$ (Commercial & Risk, 15%)**:
  Assigning risk owners, confirming commercial guardrails, and clearing contract ambiguities reduces $Q$ ($0.05 \times Q$) and increases $S_{\text{raid}}$ / $S_{\text{commercial}}$.

### 6.2 Action Resolution & Gate Advancement
1. When all deficiencies for a checklist item are resolved (e.g., all deliverables have owners and criteria), the mapped `ActionRequiredItem` is purged from `baseline.action_required_items`.
2. When the composite score reaches $\ge 85.0\%$ and $E = 0$, the `GateDecision.status` automatically transitions from `Approved with Exception` (Amber) or `Rework Required` (Red) to `Approved for Mobilize` (Green).

---

## 7. Verification & Acceptance Criteria

| Area | Verification Method | Acceptance Threshold |
| :--- | :--- | :--- |
| **In-Table Highlights** | Inspect generated `.docx` table cells via `python-docx` | 100% of cells with unassigned/unconfirmed placeholders have `#FEF3C7` background and `[ACT-XX]` tag. |
| **Artifact Banners** | Inspect artifact sections in generated `.docx` | All artifacts with active linked actions render warning callout banners with owner and recovery delta. |
| **Regex Sanitization** | Parse `.docx` containing `[ACT-XX]` tags | All extracted baseline text fields have zero trailing `[ACT-XX]` substring occurrences. |
| **Rescoring Determinism** | Re-ingest unedited `.docx` | Scores and breakdown match initial generation within $\pm 0.0\%$. |
| **Score Recovery** | Edit `.docx` to resolve deliverable and roster gaps | Composite score increases by exact calculated recovery deltas and clears corresponding action items. |
| **Regression Safety** | Run full test suite (`pytest`) | 100% pass rate across all 122+ unit, integration, and regression tests. |
