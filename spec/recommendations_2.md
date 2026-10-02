# Software Specification: Project Startup Kit Compliance Recommendations (Phase 2)

## 1. Purpose

This specification defines the second phase of implementation recommendations resulting from a comprehensive audit of the Startup Kit Generator codebase and existing specifications against `spec/startup.md`.

The recommendations aim to maximize delivery assurance, eliminate operational ambiguity during the Readiness phase, ensure strict gatekeeping before project mobilization, and establish full compliance with the Toptal PMO Governance Model.

## 2. Executive Audit Summary & Key Findings

An audit of the current implementation against `spec/startup.md` identified the following critical operational findings:

| Audit Domain | Current State | Requirement in `spec/startup.md` | Gap / Recommended Action |
|---|---|---|---|
| **Gate Checklist Placement** | G-01 Checklist rendered at the end of Layer 3 (Assurance Pack). | G-01 is the mandatory Readiness Exit Gate and onboarding instrument (WR-01, WR-03, AR-12). | **Move G-01 Checklist & Gate Decision to the front** as the Executive Readiness Gateway & Gate Review. |
| **PMO Stakeholder Model** | PMO Lead referenced in leadership fields and RACI matrix, but omitted from primary stakeholder entities. | PMO Lead and Director, PMO hold explicit decision rights, gate ownership, talent replacement authority, and escalation routes (AR-09, AR-10, RR-03, RR-07). | **Explicitly incorporate PMO** (PMO Lead, Director, PMO) as first-class stakeholders in models, extractions, and document tables. |
| **Readiness Scoring** | Checklist items have qualitative statuses; no consolidated quantitative score. | System shall calculate a Startup Readiness Score (0–100%) based on mandatory G-01 controls, staffing completeness, and unmitigated risks (NFR-04). | **Implement an automated Startup Readiness Scoring Engine** to compute composite and category scores. |
| **Ambiguity & Conflict Highlighting** | Ambiguities logged as generic notes or open questions. | System shall actively detect and highlight contradictory clauses, duplicate commitments, and date conflicts (NFR-02). | **Implement an automated Ambiguity & Conflict Detection Engine** with dedicated risk-impact flagging. |
| **Workflow & Gate Lifecycle** | Single-pass generation without persisted gate workflow states or 1-day SLA tracking. | PMO creates kit within 1 day of delivery; supports 9 discrete Readiness workflow states and segregation of duties (WR-01, WR-02, RR-06). | **Implement Readiness Workflow State Machine, SLA tracking, and Segregation of Duties validation**. |
| **Downstream Export Integration** | Generates standalone Word `.docx` file only. | Artifacts must seed the PMO Operating System workbook toolkit: PSA, KO, RAID, PSR, Budget Burndown (NFR-09). | **Implement Downstream PMO Toolkit Export Payloads** (JSON/CSV/Excel format seeds). |

---

## 3. Implementation Priorities

---

# Priority Recommendation 1: Move G-01 Checklist & Gate Decision to Document Beginning

## 3.1 Objective

Re-architect the Startup Kit document structure to render the **Startup Readiness Checklist (G-01)** and **Gate Decision Record** at the very beginning of the document as the **Executive Readiness Gateway & Compliance Dashboard**, immediately following the document header.

## 3.2 Rationale

From a delivery control and governance perspective, G-01 is the foundational gatekeeper of the Readiness phase. Under the **No-Mobilize / No-Kickoff rule (WR-03)**, no project may transition into Mobilize or conduct internal/client kickoffs without G-01 gate sign-off or an authorized exception. 

Placing the checklist at the front provides immediate visibility for the PMO Lead, Delivery Manager, and leadership into:
1. Overall gate clearance status (Approved, Approved with Exception, Rework Required).
2. Blocking gaps, unassigned deliverable owners, and missing acceptance routes.
3. Required exceptions with owners and expiration dates.
4. The high-level readiness posture before reviewing granular artifact packs.

## 3.3 Functional Requirements

### REC2-01.1 Document Structure Re-Ordering

The Word document generator (`src/generators/docx_generator.py`) shall produce the document in the following revised sequence:

1. **Document Header & Metadata Block**
   - Project Name, Client Name, Contract Type, Governance Tier, 1-Day Creation SLA Status.
2. **Executive Readiness Gateway: Startup Readiness Checklist (G-01) & Gate Decision**
   - G-01 Readiness Gate Decision Summary (Status, Approver, Date, Comments, Exceptions).
   - Mandatory G-01 Readiness Checklist Table (Item ID, Criterion, Section 4 Artifact Link, Owner, Due Date, Status, Evidence, Exception Details).
3. **Layer 1: Executive Startup Pack**
   - Project Startup Charter
   - SOW Interpretation Summary
   - Milestone Delivery Plan
4. **Layer 2: Delivery Control Pack**
   - Scope Decomposition / Backlog Seed
   - Deliverables and Acceptance Matrix
   - Dependency and Assumption Log
   - RAID Log & Decision Log Seed
   - Communications and Reporting Plan
5. **Layer 3: Assurance Pack**
   - Stakeholder and Responsibility Model (including PMO)
   - RACI / Decision Rights Matrix
   - Commercial and Margin Guardrails
   - Talent Onboarding Record

### REC2-01.2 Gate Decision Callout Box

The G-01 Gate Review section shall begin with an Executive Callout Box highlighting:
- Gate Review Status (`APPROVED FOR MOBILIZE`, `APPROVED WITH EXCEPTION`, `REWORK REQUIRED`, `PENDING REVIEW`).
- Author / Drafter: PMO Lead (created within 1 day).
- Independent Reviewers: Delivery Manager & Technical Lead.
- Approval Authority: PMO Lead (and Director, PMO for Elevated tier).
- Exception Summary: Count of open exceptions and nearest expiration date.

### REC2-01.3 Checklist Table Enhancement

The front-loaded checklist table shall clearly indicate compliance across all 13 Section 4 artifacts and mandatory readiness controls, with direct cross-references to the downstream sections where evidence is detailed.

## 3.4 Acceptance Criteria

- The generated `.docx` document visibly renders the G-01 Checklist and Gate Decision immediately after the document title and metadata, preceding Layer 1.
- The gate status, approver, reviewers, and exceptions are immediately visible on the first two pages.
- Tests verify the revised section sequence and validate paragraph/table headings.

---

# Priority Recommendation 2: Formally Incorporate PMO as a Primary Stakeholder

## 2.1 Objective

Formally integrate the PMO (specifically **PMO Lead** and **Director, PMO**) as core stakeholder entities across data models, extraction prompts, aggregation logic, stakeholder tables, and RACI decision rights.

## 2.2 Rationale

`spec/startup.md` establishes that the PMO is not merely an external observer, but the primary author, assurance owner, and gatekeeper of project delivery:
- **PMO Lead**: Owns kit creation within 1 day of delivery, delivery assurance, independent weekly health ratings, talent matching/replacement, work-at-risk approvals, and G-01 gate sign-off (RR-03, AR-09, AR-10).
- **Director, PMO**: Formal escalation authority beyond the PMO Lead and confirming approver for Elevated governance tier engagements and policy exceptions (RR-07).

Omitting the PMO from the Stakeholder and Responsibility Model weakens delivery control and governance clarity.

## 2.3 Functional Requirements

### REC2-02.1 Stakeholder Model & Defaults

Update `src/core/models.py` and `src/llm/aggregator.py` so that generated stakeholder rosters always include explicit PMO stakeholder entries:

1. **PMO Lead**:
   - Organization: `Toptal PMO`
   - Role: `Delivery Assurance & Governance Lead`
   - Decision Rights: `G-01 Gate Sign-off, Talent Staffing/Replacement, Work-at-Risk Approvals, Delivery Risk & Recovery`
   - Approver Responsibilities: `G-01 Gate, Baseline Exceptions, PMO Health Ratings, Talent Baseline Sign-off`
   - Escalation Responsibility: `Director, PMO`
   - Reporting Accountability: `Independent Weekly Health Rating, Leadership Rollup`

2. **Director, PMO**:
   - Organization: `Toptal PMO Leadership`
   - Role: `Executive Governance Authority`
   - Decision Rights: `Elevated Tier Approvals, Major Commercial Exception Sign-offs, Executive Escalations`
   - Approver Responsibilities: `Elevated Tier G-01 Concurrence, Governance Policy Exceptions`
   - Escalation Responsibility: `VP, Delivery / Executive Leadership`
   - Reporting Accountability: `Executive PMO Portfolio Review`

### REC2-02.2 Stakeholder Extraction & Prompt Updates

Update `src/llm/prompts.py` and `src/llm/parsers.py` (STAKEHOLDERS prompt) to explicitly instruct the LLM to identify named PMO personnel, delivery leadership, customer counterparts, and map them to standard PMO governance decision rights.

### REC2-02.3 RACI Alignment

Ensure the RACI table strictly enforces the decision rights mandated in `spec/startup.md` Section 4.3.1 (AR-10):
- **Startup readiness (G-01 gate)**: PMO Lead (`R, A`), DM (`C`), Talent PM (`C`), Sales (`C`), Client (`I`).
- **Talent staffing & replacement**: PMO Lead (`R, A`), DM (`C`), Talent PM (`C`), Sales (`C`), Client (`I`).
- **Work at risk / commercial exceptions**: PMO Lead (`R, A`), DM (`I`), Talent PM (`I`), Sales (`C`), Client (`I`).
- **Scope & change**: PMO Lead (`R`), DM (`A`), Talent PM (`—`), Sales (`C, R`), Client (`A`).
- **Delivery risk & recovery**: PMO Lead (`R, A`), DM (`C`), Talent PM (`R`), Sales (`I`), Client (`I`).

## 2.4 Acceptance Criteria

- The Stakeholder and Responsibility Model table in the generated document explicitly includes PMO Lead and Director, PMO with their defined decision rights and escalation roles.
- Default baseline aggregation automatically populates PMO stakeholders even when source SOW text is sparse.
- RACI matrix strictly mirrors the dual-role decision authority defined in AR-10.

---

# Priority Recommendation 3: Implement Automated Startup Readiness Scoring Engine

## 3.1 Objective

Implement a deterministic scoring engine that evaluates the completed baseline model and computes a quantified **Startup Readiness Score (0–100%)** alongside category-specific readiness metrics (NFR-04).

## 3.2 Rationale

`spec/startup.md` NFR-04 mandates an objective readiness score to inform PMO Lead review without replacing human judgment. A quantitative score enables portfolio-level tracking and highlights high-risk areas (such as unassigned deliverable owners or missing acceptance criteria) before gate approval.

## 3.3 Functional Requirements

### REC2-03.1 Scoring Algorithm

The system shall calculate the Startup Readiness Score across four weighted dimensions:

1. **Mandatory G-01 Controls (40% Weight)**:
   - Percentage of mandatory checklist items marked `Complete` or `Approved`.
   - Items with `Exception Required` or `Confirmation Required` reduce the score unless mitigated.
2. **Deliverable & Acceptance Rigor (25% Weight)**:
   - Percentage of deliverables with confirmed owners, explicit acceptance criteria, and named client approvers.
   - Any deliverable with `[CONFIRMATION REQUIRED]` acceptance criteria incurs a penalty.
3. **Talent & Staffing Readiness (20% Weight)**:
   - Named Talent PM, Delivery Manager, and staffed talent team roster.
   - Unresolved staffing gaps incur a penalty.
4. **Commercial & Risk Mitigation (15% Weight)**:
   - Documented top delivery and margin risks with assigned owners and mitigations.
   - Low count of unresolved high-impact open questions.

### REC2-03.2 Readiness Score Representation

Add `readiness_score: float` and `readiness_breakdown: Dict[str, float]` to `StartupKitBaseline` and render a visual score gauge/table in the Executive Readiness Gateway callout block:
- **Score >= 85%**: `READY FOR GATE REVIEW (Green)`
- **Score 70% – 84%**: `CONDITIONAL / EXCEPTION REQUIRED (Amber)`
- **Score < 70%**: `NOT READY / REWORK REQUIRED (Red)`

## 3.4 Acceptance Criteria

- The aggregator computes the numeric readiness score and sub-scores deterministically.
- The generated document displays the overall Readiness Score and health category in the front-loaded G-01 summary block.
- Unit tests validate scoring calculations under complete, partial, and empty baseline inputs.

---

# Priority Recommendation 4: Implement Contract Ambiguity & Conflict Detection Engine

## 4.1 Objective

Implement an extraction and validation pass that systematically detects and highlights contradictory contractual clauses, conflicting dates, vague acceptance terms, and duplicate commitments (NFR-02).

## 4.2 Rationale

Unresolved contractual ambiguities create acute delivery and commercial risks during project execution. Identifying and surfacing these conflicts during Readiness allows the Delivery Manager and PMO Lead to resolve them during the Sales to Delivery Handoff (G-02) or internal kickoff (G-03).

## 4.3 Functional Requirements

### REC2-04.1 Ambiguity & Conflict Schema

Add structured models for detected contractual anomalies:
- `Anomaly ID`: (e.g. `AMB-01`, `CONF-01`)
- `Category`: `Date Conflict`, `Scope Contradiction`, `Ambiguous Acceptance`, `Unclear SLA`, `Ownership Gap`
- `Conflicting Clauses / Text Excerpts`: Source quotes with page/clause citations.
- `Risk Impact Analysis`: Potential impact on delivery schedule, cost, or margin.
- `Recommended Clarification / Resolution`: Actionable question for Sales, Contracting, or Client.
- `Status`: `Open`, `Escalated`, `Resolved`.

### REC2-04.2 Extraction Prompt for Conflicts

Add `CONTRACT_CONFLICTS_PROMPT` to analyze source documents specifically for:
- Discrepancies between SOW milestone dates and proposal/estimate dates.
- Deliverables listed in scope but excluded in assumptions (or vice versa).
- Subjective or non-testable acceptance language (e.g., "to customer's complete satisfaction").
- Unspecified client review turnaround times.

### REC2-04.3 Aggregator & Document Rendering

- Detected conflicts automatically generate linked entries in `open_questions` and `raid_items` (Category: `Commercial` or `Governance`).
- Render an **Ambiguities & Contractual Conflicts Table** within Layer 1 (SOW Interpretation Summary).

## 4.4 Acceptance Criteria

- The pipeline extracts and structures contractual ambiguities with citations.
- Detected conflicts feed directly into open questions and RAID risks.
- The document generator renders the conflict table within the SOW Interpretation section.

---

# Priority Recommendation 5: Implement Readiness Workflow State Tracking & Segregation of Duties

## 5.1 Objective

Implement explicit data structures and validation logic for the 9 Readiness workflow states, 1-day creation SLA tracking, and role-based segregation of duties (WR-01 through WR-07, RR-06).

## 5.2 Rationale

`spec/startup.md` Section 5 defines a rigorous governance lifecycle within Readiness. Enforcing drafting SLAs and segregation of duties prevents unreviewed single-person approvals and guarantees independent oversight by Delivery Management and the PMO.

## 5.3 Functional Requirements

### REC2-05.1 Readiness Workflow State Machine

Model the 9 discrete workflow states in `src/core/models.py`:
1. `Awarded`
2. `Drafting in Progress` (PMO, within 1 day)
3. `Review in Progress` (DM & Tech Lead review)
4. `Clarification Pending` (Open questions blocking baseline)
5. `Talent Onboarding in Progress` (Using Startup Kit)
6. `Ready for G-01 Gate Review`
7. `Approved for Mobilize`
8. `Approved with Exception`
9. `Rework Required`

### REC2-05.2 1-Day Creation SLA Tracker

Track timestamps for:
- `sow_awarded_date`: Date SOW signed or handed over.
- `kit_drafted_date`: Date Startup Kit generated.
- `sla_met: bool`: True if generated within 1 business day of delivery handoff; if False, automatically logs a G-01 checklist exception.

### REC2-05.3 Segregation of Duties Validation

Enforce the role separation rule (RR-06):
- Author: `PMO Lead / PMO Specialist`
- Reviewers: `Delivery Manager` (voice of customer) and `Technical Lead` (technical feasibility)
- Approver: `PMO Lead`
- Concurring Approver (Elevated Tier): `Director, PMO`
- Validation Rule: The system verifies that author, reviewer, and approver roles are assigned to distinct individuals/roles.

## 5.4 Acceptance Criteria

- Baseline model carries workflow state, SLA timestamps, and assigned reviewer/approver roles.
- SLA breach automatically creates a checklist exception item.
- Document header and G-01 gate block display workflow state and segregation of duties confirmation.

---

# Priority Recommendation 6: Implement Downstream PMO Toolkit Export Payloads

## 6.1 Objective

Enable the Startup Kit to export structured data payloads formatted for direct ingestion into the standard PMO Operating System workbook toolkit (NFR-09).

## 6.2 Rationale

The Startup Kit is designed to seed the active delivery control tools used throughout the project lifecycle:
- **Project Success Agreement (PSA)** (seeded by Charter & Milestone Plan)
- **Project Kickoff Deck (KO)** (seeded by Charter, Scope, Team)
- **Standard RAID Log & Decision Log** (seeded by RAID, Assumptions, Decisions)
- **Project Status Report (PSR)** (seeded by Milestones, Comms Plan, Health Rating)
- **Budget Burndown Workbook** (seeded by Commercial Guardrails & Contract Type)

## 6.3 Functional Requirements

### REC2-06.1 Export Payload Generator

Implement `src/generators/export_payloads.py` to generate structured JSON and CSV datasets:
1. `export_raid_csv()`: Standard RAID table export (ID, Type, Summary, Owner, Impact, Mitigation, Status).
2. `export_decision_log_csv()`: Decision log seed (ID, Decision, Owner, Date, Rationale, Status).
3. `export_milestone_plan_json()`: Structured milestone baseline with internal buffer dates.
4. `export_psa_seed_json()`: Charter, objectives, success criteria, governance tier, and escalation path.
5. `export_budget_burndown_seed_json()`: Commercial guardrails, billing assumptions, and margin triggers.

### REC2-06.2 CLI Integration

Add `--export-tools` flag to `main.py` allowing users to export the `.docx` document and all associated CSV/JSON toolkit seed files into `output/`.

## 6.4 Acceptance Criteria

- Running `main.py --mock --export-tools` outputs both the primary `.docx` file and the complete set of downstream PMO toolkit seed files.
- Exported datasets validate against standard PMO schema definitions.

---

## 4. Cross-Cutting Architectural Requirements

### 4.1 Utilitarian Delivery Control Principle
Every generated section and table must serve a direct operational utility: mitigating delivery risk, enforcing commercial boundaries, or ensuring delivery alignment between the Client, Delivery Manager, Talent PM, and PMO. Redundant prose should be minimized in favor of crisp, structured, actionable tables.

### 4.2 Source Traceability & Confidence Scoring
All extracted entities (deliverables, milestones, assumptions, risks, stakeholders) must maintain bidirectional source citations (`document_name`, `clause_or_slide`, `confidence_score`).

### 4.3 Strict Placeholder Policy
The system shall never invent unstated contractual facts. Unconfirmed items must be visibly flagged with standardized tokens:
- `[CONFIRMATION REQUIRED]`
- `[UNASSIGNED - TO BE CONFIRMED]`
- `[NOT AVAILABLE IN SOURCE - REVIEW REQUIRED]`

### 4.4 Tailoring by Tier and Contract Type
- **Governance Tier**: Guided (standard cadences, 3-day buffer), Partnered (weekly check-ins, 7-day buffer), Elevated (Director PMO concurrence, tighter burn caps, 10-day buffer).
- **Contract Type**: Time and Materials (burn visibility, timesheet controls, customer dependencies) vs. Fixed Bid (strict scope boundaries, change control triggers, acceptance sign-off rigor).

---

## 5. Recommended Implementation Sequence

To maintain continuous delivery and test stability, implement the recommendations in the following sequential order:

1. **Move G-01 Checklist & Gate Decision to Document Beginning** (`src/generators/docx_generator.py`).
2. **Incorporate PMO Stakeholders & RACI Enhancements** (`src/core/models.py`, `src/llm/aggregator.py`, `src/llm/prompts.py`).
3. **Implement Automated Startup Readiness Scoring Engine** (`src/core/models.py`, `src/llm/aggregator.py`).
4. **Implement Contract Ambiguity & Conflict Detection Engine** (`src/llm/prompts.py`, `src/llm/parsers.py`, `src/core/models.py`).
5. **Implement Readiness Workflow States & 1-Day SLA Tracking** (`src/core/models.py`, `src/llm/aggregator.py`).
6. **Implement Downstream PMO Toolkit Export Payloads & CLI Options** (`src/generators/export_payloads.py`, `main.py`).
7. **Comprehensive Unit & Integration Test Suite Validation** (`tests/`).

---

## 6. Definition of Done

The implementation of Phase 2 recommendations shall be considered complete when:

1. The generated `.docx` document prominently features the **G-01 Startup Readiness Checklist and Gate Decision** as the front-loaded Executive Readiness Gateway.
2. The **PMO Lead and Director, PMO** are formally integrated as primary stakeholders with full decision rights in the Stakeholder and Responsibility Model and RACI matrix.
3. The **Startup Readiness Score (0–100%)** is automatically computed and displayed with category sub-scores.
4. Contractual ambiguities, conflicting dates, and vague terms are automatically extracted and presented in a dedicated conflicts table.
5. Readiness workflow states, 1-day SLA metrics, and segregation of duties rules are fully modeled and validated.
6. Downstream export payloads for PMO workbooks (RAID, PSA, Burndown, Milestones) can be generated via CLI.
7. All test suites pass with 100% success rate and zero regressions against mock and live pipelines.
