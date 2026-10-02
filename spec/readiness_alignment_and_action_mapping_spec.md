# Software Specification: Startup Readiness Scoring, Action Mapping, and Gateway Alignment

**Status**: Proposed Architectural & Governance Specification  
**Date**: 2026-09-27  
**Target Modules**: `src/core/models.py`, `src/generators/checklist.py`, `src/generators/docx_generator.py`, `src/llm/aggregator.py`, `src/scoring/readiness_engine.py` (New)  
**Baseline Application Version**: 0.1.1  

---

## 1. Executive Summary & Utilitarian Objectives

The **Startup Readiness Gateway (G-01)** is the primary operational filter in the Toptal PMO delivery lifecycle. Under the **No-Mobilize / No-Kickoff governance rule (WR-03)**, no project may transition into delivery mobilization or conduct kickoff meetings without an approved G-01 Gate Decision or an authorized exception.

### Core Problems Identified in Current Implementation

1. **Scoring Inconsistency and Duplication**:
   - Startup Readiness Score calculations are duplicated across `_build_baseline_from_results()` and `recalculate_readiness_score()` in `src/llm/aggregator.py`, risking mathematical drift.
   - Dimension penalties (e.g., open exception deductions and open question penalties) operate on opaque heuristics rather than transparent, reversible mathematical components.
2. **Action Item Disconnect and Shallow Visibility**:
   - Open clarifications and open exceptions are treated as detached secondary artifacts. `baseline.open_questions` is currently output as a generic bulleted callout box with no mapping to owners, deadlines, or checklist criteria.
   - Open exceptions identified in the G-01 checklist are not consolidated into an actionable remediation roadmap.
3. **Suboptimal Document Ordering**:
   - The "Action Required" callout is rendered *after* the 15-row Checklist Table, forcing executive reviewers to scroll past the audit matrix before seeing the specific blocking actions required to unlock mobilization.
4. **Tri-directional Misalignment**:
   - The Gate Decision summary box, the Action Required list, and the G-01 Checklist Table operate with independent counts and narratives rather than a single source of truth.

### Key Enhancements Specified

1. **Authoritative `ReadinessScoringEngine`**: Consolidates all scoring logic into a single deterministic engine with strict 4-dimension mathematical models, verifiable sub-scores, and reversible delta tracking.
2. **Structured Action Required Matrix**: Replaces the generic bulleted box with an actionable, structured table categorizing **Open Exceptions** and **Open Clarifications**, directly mapped to **Checklist Item IDs (`G01-XX`)**, designated owners, resolution milestones, and quantified **Score Recovery Potentials**.
3. **Gateway Document Re-ordering**: Positions the Action Required Table immediately following the Executive Gate Decision summary box and *before* the detailed G-01 Checklist Table.
4. **Tri-directional Alignment Guarantees**: Enforces exact mathematical and categorical parity across the Gate Decision dashboard, Action Required items, and G-01 Checklist rows.

---

## 2. Standardized Startup Readiness Scoring Engine

To eliminate calculation drift, all scoring logic is centralized into `src/scoring/readiness_engine.py` (or a dedicated scoring service inside `src/core/`), shared identically by ingestion, baseline aggregation, and Word re-ingestion recalculation.

```
+----------------------------------------------------------------------------------------------------+
|                                    STARTUP READINESS SCORE (100%)                                  |
+---------------------------------+----------------------------------+-------------------------------+
|  Dimension 1: Controls (40%)    |  Dimension 2: Deliverables (25%) |  Dimension 3: Staffing (20%)  |
|  - 15 G-01 Checklist Items     |  - Acceptance Criteria Rigor     |  - Core Role Assignments      |
|  - Normalized Status Weights    |  - Named Deliverable Owners      |  - Talent Roster Completeness |
|  - Exception Penalty Reductions |  - Explicit Acceptance Routes    |  - Skill Matrix Mapping       |
+---------------------------------+----------------------------------+-------------------------------+
                                  |  Dimension 4: Risk & Guardrails (15%)                            |
                                  |  - RAID Item Ownership & Seeding                                 |
                                  |  - Commercial Guardrail Definitions                              |
                                  |  - Open Clarification Deductions                                |
                                  +------------------------------------------------------------------+
```

### 2.1 Four-Dimension Mathematical Formulation

$$\text{Readiness Score} = \sum_{i=1}^{4} \left( W_i \times D_i \right) \times 100$$

Where $W = [0.40, 0.25, 0.20, 0.15]$ and each dimension score $D_i \in [0.0, 1.0]$.

#### Dimension 1: Mandatory G-01 Controls ($W_1 = 40\%$)

Evaluates the 15 baseline governance checklist items ($N = 15$):

$$D_1 = \max\left(0.0, \min\left(1.0, \frac{\sum_{k=1}^{N} \text{Score}(I_k)}{N} - (E \times 0.02)\right)\right)$$

Where $E$ is the count of active Open Exceptions, and $\text{Score}(I_k)$ is determined by the checklist status:

| Checklist Item Status | Raw Point Weight ($\text{Score}(I_k)$) | Governance Interpretation |
| :--- | :---: | :--- |
| `Complete` / `Approved` | **1.00** | Fully baselined, validated, and signed off. |
| `Approved with Exception` | **0.85** | Authorized temporary waiver logged with expiry date. |
| `Review Required` | **0.50** | Drafted but pending peer or stakeholder validation. |
| `In Progress` | **0.50** | Active drafting/refinement underway. |
| `Confirmation Required` | **0.30** | Critical external client/sales input pending. |
| `Exception Required` | **0.20** | Unresolved gap requiring formal waiver. |
| `Rework Required` / `Not Started` | **0.00** | Missing, invalid, or rejected control. |

#### Dimension 2: Deliverable & Acceptance Rigor ($W_2 = 25\%$)

Evaluates contractual clarity for each extracted deliverable $d \in \text{Deliverables}$:

$$\text{Score}(d) = S_{\text{criteria}}(d) + S_{\text{owner}}(d) + S_{\text{route}}(d)$$

- **Criteria Score ($S_{\text{criteria}}$)**: $0.40$ if acceptance criteria are explicit and contain no `[CONFIRMATION REQUIRED]`; otherwise $0.00$.
- **Owner Score ($S_{\text{owner}}$)**: $0.30$ if owner is assigned and contains no `[UNASSIGNED]`; otherwise $0.00$.
- **Route Score ($S_{\text{route}}$)**: $0.30$ if acceptance route contains standard formal approval mechanisms; $0.15$ if informal/partial; $0.00$ if unstated.

$$D_2 = \begin{cases} 
\frac{1}{|\text{Deliverables}|} \sum_{d} \text{Score}(d) & \text{if } |\text{Deliverables}| > 0 \\
0.50 & \text{if no deliverables defined in baseline}
\end{cases}$$

#### Dimension 3: Talent Staffing Readiness ($W_3 = 20\%$)

Evaluates staffing assignment and leadership readiness:

$$D_3 = S_{\text{leadership}} + S_{\text{roster}}$$

- **Leadership Score ($S_{\text{leadership}}$, max 0.60)**:
  - PMO Lead Assigned: $+0.20$
  - Delivery Manager Assigned: $+0.20$
  - Talent PM Assigned: $+0.20$
- **Roster Completeness ($S_{\text{roster}}$, max 0.40)**:
  - Ratio of staffed roles: $0.40 \times \left(\frac{\text{Staffed Roles}}{\text{Total Required Roles}}\right)$

#### Dimension 4: Commercial & Risk Mitigation ($W_4 = 15\%$)

Evaluates commercial boundaries and open uncertainties:

$$D_4 = \max\left(0.0, \min\left(1.0, S_{\text{raid}} + S_{\text{commercial}} - (Q \times 0.05)\right)\right)$$

- **RAID Maturity ($S_{\text{raid}}$, max 0.50)**: $0.50 \times \left(\frac{\text{Assigned RAID Items}}{\text{Total RAID Items}}\right)$ (or $0.25$ if 0 items).
- **Commercial Guardrails ($S_{\text{commercial}}$, max 0.50)**: $0.50$ if budget, work-at-risk, and change control rules are populated; $0.20$ if partial.
- **Clarification Deduction**: Deducts $0.05$ per unresolved open question / clarification ($Q = |\text{Open Questions}|$).

### 2.2 Score Breakdown & Gate Decision Thresholds

```
   0%                          70%                     85%                    100%
   +----------------------------+-----------------------+-----------------------+
   |   REWORK REQUIRED (Red)    | CONDITIONAL / EXCEPTION| READY FOR GATE (Green)|
   |   - Mobilization Blocked   | - Waiver Required     | - Immediate Mobilize  |
   |   - Fundamental Gaps       | - Expiring 14-Day Plan| - Full Clearance      |
   +----------------------------+-----------------------+-----------------------+
```

| Composite Score Range | Gate Health Category | Gate Decision Status | Permitted Mobilization Action |
| :---: | :--- | :--- | :--- |
| **85.0% – 100.0%** | **READY FOR GATE REVIEW (Green)** | `Approved for Mobilize` | Full authorization for internal & client kickoff. |
| **70.0% – 84.9%** | **CONDITIONAL / EXCEPTION (Amber)** | `Approved with Exception` | Conditional mobilization; open exceptions must close in 14 days. |
| **0.0% – 69.9%** | **NOT READY / REWORK (Red)** | `Rework Required` | Mobilization blocked; PMO must resolve critical defects. |

---

## 3. Data Model Specifications (`src/core/models.py`)

### 3.1 `ActionRequiredItem` Model

Represents a single granular exception or clarification required before or during mobilization:

```python
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class ActionRequiredItem(BaseModel):
    """Represents a specific unresolved validation point, open exception, or clarification."""
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(..., description="Unique ID, e.g. 'ACT-01', 'ACT-02'")
    item_type: Literal["Open Exception", "Open Clarification"] = Field(
        ..., description="Categorization: formal exception vs contractual ambiguity"
    )
    checklist_id: str = Field(..., description="Mapped G-01 Checklist ID (e.g., 'G01-03', 'G01-04')")
    related_artifact: str = Field(..., description="Section 4 artifact (e.g., 'Deliverables and Acceptance Matrix')")
    finding_description: str = Field(..., description="Specific validation gap or ambiguity identified")
    required_action: str = Field(..., description="Explicit corrective step required to close the item")
    owner: str = Field(..., description="Role/individual accountable for resolution")
    resolution_deadline: str = Field(
        default="Prior to Mobilize Kickoff",
        description="Target resolution milestone (e.g., 'Pre-Kickoff', 'Sprint 0 Day 1')"
    )
    score_recovery_delta: float = Field(
        default=0.0,
        description="Estimated points added to composite Readiness Score upon resolution"
    )
    target_gate_impact: str = Field(
        default="Clears G-01 checklist item to Approved",
        description="Impact on gate health (e.g., 'Upgrades G01-03 from Review Required to Approved')"
    )
```

### 3.2 Enhanced `StartupKitBaseline` Integration

Add the structured action item list and score breakdown models to `StartupKitBaseline`:

```python
class StartupKitBaseline(BaseModel):
    # ... existing fields ...
    readiness_score: float = 0.0
    readiness_breakdown: dict[str, float] = Field(default_factory=dict)
    action_required_items: list[ActionRequiredItem] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    readiness_checklist: list[ReadinessChecklistItem] = Field(default_factory=list)
    gate_decision: Optional[GateDecision] = None
```

---

## 4. Checklist-to-Action Mapping Matrix (G01-01 through G01-15)

Every possible gap identified during ingestion or review maps deterministically to a checklist item, an action item, and a score recovery potential:

| Gate ID | Standard Gate Criterion | Validation Gap / Trigger Condition | Action Item Type | Required Remediation Action | Designated Owner | Estimated Score Delta |
| :---: | :--- | :--- | :---: | :--- | :--- | :---: |
| **G01-01** | Startup Kit created <= 1 day | SLA breached (> 1 business day) | Open Exception | Log retroactive PMO waiver for delayed drafting | PMO Lead | $+1.5\%$ |
| **G01-02** | Governance Tier & Cadence | Tier unassigned or missing meeting cadence | Open Clarification | Confirm governance tier and agree weekly cadence | PMO Lead | $+2.0\%$ |
| **G01-03** | Deliverable Ownership & Acceptance | Acceptance criteria contains `[CONFIRMATION REQUIRED]` or unassigned owner | Open Exception / Clarification | Finalize acceptance test criteria and assign named delivery owner | Talent PM | $+3.5\%$ |
| **G01-04** | Milestone Delivery Plan | External milestone date unconfirmed or buffer missing | Open Exception | Agree milestone baseline with client sponsor and log 7-day buffer | Delivery Manager | $+3.0\%$ |
| **G01-05** | RAID Log Seeded | High-severity risks unassigned or missing mitigation | Open Clarification | Assign risk owners and document fallback mitigations | Talent PM | $+2.0\%$ |
| **G01-06** | Talent Briefing & KO Decks | Talent PM / DM kickoff deck unconfirmed | Open Clarification | Complete briefing on PMO cadences and approve KO deck | PMO Lead | $+1.5\%$ |
| **G01-07** | Client Onboarding & Prerequisites | Client environment/access dependencies missing | Open Clarification | Issue access prerequisites list to client sponsor | Delivery Manager | $+2.5\%$ |
| **G01-08** | Talent Roster Staffed | Key role listed as `[UNASSIGNED]` | Open Exception | Complete candidate selection and lock staffing | Talent PM | $+4.0\%$ |
| **G01-09** | Client Sponsor Identified | Sponsor name or escalation path unconfirmed | Open Clarification | Confirm primary client sign-off authority and title | PMO Lead | $+2.0\%$ |
| **G01-10** | RACI Decision Rights Matrix | Decision activity missing explicit PMO/DM/Client role | Open Clarification | Align RACI matrix with client project sponsor | PMO Lead | $+1.5\%$ |
| **G01-11** | Communications Plan | Report recipient audience or cadence unconfirmed | Open Clarification | Confirm weekly status distribution list | Delivery Manager | $+1.5\%$ |
| **G01-12** | Budget Burndown & Commercials | Budget baseline unstated or margin cap missing | Open Exception | Baseline SOW total value and confirm margin floor | PMO Lead | $+3.0\%$ |
| **G01-13** | Change Control Procedure | Formal change order workflow undefined | Open Clarification | Confirm written change request sign-off route | PMO Lead | $+2.0\%$ |
| **G01-14** | Ambiguity & Conflict Resolution | Conflicting milestone dates or vague clauses logged | Open Exception | Execute formal clarification note with client accounts | PMO Lead | $+3.5\%$ |
| **G01-15** | Open Questions Consolidated | Active open questions pending mobilization | Open Clarification | Review open questions during mobilization kickoff | PMO Lead | $+2.5\%$ |

---

## 5. Document Structure & Rendering Sequence

### 5.1 Revised Word Document Layout (`src/generators/docx_generator.py`)

The layout is restructured to position the **Action Required Table** immediately after the **Gate Decision Dashboard** and before the **15-row Checklist Table**:

```
================================================================================
1. DOCUMENT HEADER & METADATA BLOCK
   - Project Title, Governance Tier, Key Owners, SLA Status, Workflow State
================================================================================
2. EXECUTIVE READINESS GATEWAY (G-01)
   2.1 Section Intro & Regulatory Rule (WR-03 No-Mobilize Mandate)
   2.2 G-01 Gate Decision Summary Box
       - Readiness Score (e.g. 74.2% - CONDITIONAL / EXCEPTION)
       - Score Breakdown: Controls | Acceptance | Staffing | Risk
       - Key Governance Roles & SLA Metrics
       - Open Exceptions Count & Open Clarifications Count
   
   2.3 ACTION REQUIRED: UNRESOLVED VALIDATION POINTS & CLARIFICATIONS (NEW PLACEMENT)
       [ Table of Open Exceptions & Clarifications ]
       - Action ID | Type | Checklist ID | Artifact | Finding & Action | Owner | Target Deadline | Score Recovery
       - Summary Callout: Total Score Recovery Potential (+18.5% -> Target 92.7%)
   
   [ PAGE BREAK ]

   2.4 STARTUP READINESS CHECKLIST TABLE (G-01)
       [ 15-Row Comprehensive Audit Matrix ]
       - Gate ID | Criterion | Artifact | Status | Owner | Reviewer | Approver | Evidence & Exceptions
================================================================================
3. LAYER 1: EXECUTIVE STARTUP PACK
   - 1.1 Project Startup Charter
   - 1.2 SOW Interpretation Summary
   - 1.3 Contract Ambiguity & Conflict Analysis
   - 1.4 Scope Decomposition
================================================================================
4. LAYER 2: DELIVERY WORKBENCH
   - 2.1 Deliverables & Acceptance Matrix
   - 2.2 Milestone Delivery Plan
   - 2.3 RAID Log
   - 2.4 Stakeholder Communications Matrix
================================================================================
5. LAYER 3: ASSURANCE PACK
   - 3.1 Stakeholder & Responsibility Model
   - 3.2 RACI Matrix
   - 3.3 Commercial & Margin Guardrails
   - 3.4 Talent Onboarding Record
================================================================================
```

### 5.2 Implementation of `G01ChecklistRenderer.render()`

```python
class G01ChecklistRenderer:
    """Renders the executive readiness gateway, action required table, and G-01 checklist."""

    def render(self, doc: docx.Document, baseline: StartupKitBaseline):
        # 1. Section Title and Policy Mandate
        add_section_heading(
            doc,
            "Executive Readiness Gateway: Startup Readiness Checklist (G-01) & Gate Decision",
            level=1
        )
        self._render_policy_intro(doc)

        # 2. Executive Gate Decision Summary Dashboard Box
        self._render_decision_dashboard(doc, baseline)

        # 3. Action Required Table (Rendered BEFORE the checklist table)
        if baseline.action_required_items:
            doc.add_paragraph().paragraph_format.space_after = Pt(6)
            self._render_action_required_table(doc, baseline)

        # 4. Page Break
        doc.add_page_break()

        # 5. Full G-01 Checklist Table (15 items)
        self._render_checklist_table(doc, baseline)
```

### 5.3 Action Required Table Formatting Specification

| Column | Header | Width | Styling / Content |
| :---: | :--- | :---: | :--- |
| 1 | **Action ID** | 0.8 in | Bold text (e.g., `ACT-01`, `ACT-02`). |
| 2 | **Type** | 1.1 in | Highlighted badge: Amber background for `Open Exception`, Light Blue for `Open Clarification`. |
| 3 | **Gate ID** | 0.8 in | Hyper-referenced Checklist ID (e.g., `G01-03`, `G01-04`). |
| 4 | **Related Artifact** | 1.3 in | Section 4 Artifact title. |
| 5 | **Validation Finding & Required Action** | 2.5 in | Clear finding description followed by explicit remediation instruction. |
| 6 | **Owner** | 1.0 in | Accountable governance role. |
| 7 | **Deadline** | 1.0 in | Target milestone (e.g., `Pre-Kickoff`, `Sprint 0`). |
| 8 | **Score Impact** | 0.8 in | Positive score recovery delta (e.g., `+3.5%`). |

---

## 6. Tri-directional Alignment Guarantees

To ensure that the document and data structures remain fully synchronized, the system enforces four invariant alignment rules:

```
+-----------------------------------------------------------------------------------+
|                            TRI-DIRECTIONAL ALIGNMENT                              |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|         [ 1. Gate Decision Dashboard ]                                            |
|         - Open Exceptions Count: 2                                                |
|         - Open Clarifications Count: 3                                            |
|         - Current Readiness Score: 74.2% (Amber)                                  |
|         - Max Potential Score: 92.7% (Green)                                      |
|                       ^                                ^                          |
|                      /                                  \                         |
|                     v                                    v                        |
|   [ 2. Action Required Table ] <===============> [ 3. G-01 Checklist Table ]      |
|   - ACT-01 (Exception): G01-03 (+3.5%)          - G01-03: Exception Required     |
|   - ACT-02 (Exception): G01-08 (+4.0%)          - G01-08: Exception Required     |
|   - ACT-03 (Clarification): G01-04 (+3.0%)      - G01-04: Confirmation Required  |
|   - ACT-04 (Clarification): G01-14 (+3.5%)      - G01-14: Review Required        |
|   - ACT-05 (Clarification): G01-15 (+2.5%)      - G01-15: Review Required        |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Alignment Rules

1. **Count & State Parity**:
   $$\text{GateDecision.open_exceptions_count} = \sum [I \in \text{Checklist} \mid I.\text{exception\_required} = \text{True}] = \sum [A \in \text{Actions} \mid A.\text{item\_type} = \text{"Open Exception"}]$$
2. **Clarification Parity**:
   $$\text{len}(\text{Open Questions}) = \sum [A \in \text{Actions} \mid A.\text{item\_type} = \text{"Open Clarification"}]$$
3. **Score Recovery Invariant**:
   $$\text{Current Score} + \sum_{A \in \text{Actions}} A.\text{score\_recovery\_delta} = \text{Target Potential Score (Up to 100.0\%)}$$
4. **Owner & Artifact Traceability**:
   $$\forall A \in \text{Actions}, \quad A.\text{owner} = \text{Checklist}[A.\text{checklist\_id}].\text{owner}$$

---

## 7. Acceptance Test Matrix

| Test Suite / Function | Verification Target | Input Test Conditions | Expected Outcome |
| :--- | :--- | :--- | :--- |
| `test_readiness_scoring_engine_determinism` | Mathematical Consistency | Run scoring engine on fixed baseline 1,000 times | Identical composite score and breakdown down to 0.1% precision. |
| `test_readiness_scoring_weights_sum_to_100` | Dimension Weights | $W_1=0.40, W_2=0.25, W_3=0.20, W_4=0.15$ | Sum of weighted max dimension scores strictly equals 100.0%. |
| `test_action_items_generated_from_exceptions` | Exception Extraction | Baseline with unassigned deliverable owner (`G01-03`) and missing role (`G01-08`) | Generates 2 `Open Exception` action items mapped to `G01-03` and `G01-08`. |
| `test_action_items_generated_from_questions` | Clarification Extraction | Baseline with 3 open questions and date ambiguity | Generates 3 `Open Clarification` action items with positive score recovery deltas. |
| `test_action_required_table_rendered_before_checklist` | Document Ordering | Generate `.docx` report with actions | Word table hierarchy confirms Action Required table precedes G-01 Checklist table. |
| `test_tri_directional_alignment` | Alignment Invariants | Baseline with mixed statuses | Decision box counts, Action table row counts, and Checklist exception flags match 100%. |
| `test_score_recovery_potential_reaches_green` | Remediation Pathway | Baseline at 74.0% Amber with 3 action items | Applying all action remediation steps raises score $\ge 85.0\%$ Green. |

---

## 8. Implementation Plan & Migration Pathway

1. **Step 1: Create Centralized Scoring Engine** (`src/scoring/readiness_engine.py`):
   - Encapsulate the 4-dimension scoring formula into a dedicated `ReadinessScoringEngine` class.
   - Refactor `src/llm/aggregator.py` to delegate `_build_baseline_from_results()` and `recalculate_readiness_score()` to this engine.
2. **Step 2: Update Data Models** (`src/core/models.py`):
   - Add `ActionRequiredItem` model.
   - Add `action_required_items: List[ActionRequiredItem]` to `StartupKitBaseline`.
3. **Step 3: Implement Action Item Generation Logic** (`src/llm/aggregator.py`):
   - Automatically compile `action_required_items` from identified exceptions, open questions, and contract ambiguities during baseline creation.
4. **Step 4: Update Document Renderer** (`src/generators/checklist.py` and `src/generators/docx_generator.py`):
   - Implement `_render_action_required_table()` in `G01ChecklistRenderer`.
   - Reposition the Action Required table before the checklist table and remove the redundant post-checklist callout box in `DocxGenerator`.
5. **Step 5: Execute Test Validation**:
   - Create `tests/test_readiness_scoring.py` and update `tests/test_phase2.py`, `tests/test_docx_generator.py`, and `tests/test_docx_reingestion.py`.
