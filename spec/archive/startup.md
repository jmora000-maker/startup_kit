# Requirements Specification: Project Startup Kit

> **Alignment note (v3, September 2026):** This version aligns the Startup Kit to the Toptal PMO Governance Model. Startup and onboarding take place in the **Readiness** phase, during the **On-Board Talent PM / DM** gate. The **PMO creates the Startup Kit within 1 day of delivery** and uses it to onboard the Talent PM, DM, and delivery team. The PMO owns the gate and evidences it with the **G-01 checklist**. The kit has to be baselined before the engagement leaves Readiness and enters **Mobilize**. Roles, decision rights, governance tiers, and toolkit references now use the PMO model's terms.
>
> **Gate codes (v5):** checklists are numbered in lifecycle order: G-01 On-Board Talent PM / DM (includes the governance baseline), G-02 Sales to Delivery Handoff, G-03 Internal Project Kickoff, G-04 Communications Plan, G-05 Stakeholder Map, G-06 Weekly Check-in, G-07 MBR/QBR, G-08 Retrospective. The Decision Log is part of the RAID Log and has no code of its own. The PMO owns the Client Project Kickoff.

## 1. Purpose and Business Requirements

### 1.1 Purpose

**BR-01** The PMO shall create the Project Startup Kit within **1 day of delivery**. The kit shall convert an awarded Statement of Work (SOW), together with any available pre-sales and contracting materials, into a minimum executable delivery control system during the **Readiness** phase, as part of the **On-Board Talent PM / DM** gate, before the engagement enters Mobilize.

The kit is the onboarding vehicle: the PMO uses it to onboard the Talent PM, DM, and delivery team against the requirements in this specification. It removes startup ambiguity and creates an evidence-based delivery baseline so the Talent PM, Delivery Manager, and PMO Lead start with clear contractual, operational, and commercial control. It also puts into practice the PMO principle that engagement starts *before the project is sold, not at kickoff*.

### 1.2 Business Problem

**BR-02** The kit shall address recurring startup failure modes, including delayed planning, weak decomposition of deliverables into manageable work, poor milestone awareness, undefined acceptance routes, unmanaged dependencies, inconsistent reporting, late talent onboarding, and avoidable margin erosion.

### 1.3 Business Outcomes

**BR-03** Before exiting Readiness, the startup kit shall ensure the delivery team can answer the following questions with traceable evidence:

1. What are we contracted to deliver, and what is explicitly out of scope?
2. How will we deliver against committed dates and milestone obligations?
3. How will progress, issues, and financial exposure be tracked?
4. What conditions threaten delivery success or margin performance?
5. Who is responsible, accountable, consulted, and informed for each critical startup control?
6. Is the talent team (Talent PM, Delivery Manager, and delivery talent) staffed, onboarded, and aligned to the baseline?

### 1.4 Design Principles

**BR-04** The solution shall be designed according to the following principles:

- Contract-to-delivery traceability: Each deliverable, date, assumption, and commitment shall trace back to a source clause, slide, estimate, or explicit confirmation.
- Minimum viable control: The kit shall be lightweight enough to produce rapidly, but sufficient to govern execution and protect margin.
- Risk-based tailoring: The depth of the kit shall scale with the engagement's governance tier (Guided, Partnered, Elevated) rather than being applied uniformly.
- Hybrid execution practicality: The kit shall support milestone-driven governance combined with iterative execution management through work packages, epics, features, stories, or tasks.
- Readiness before Mobilize: The kit shall establish a minimum control baseline in Readiness, before the Sales to Delivery Handoff and the Mobilize kickoffs.
- Automation-first drafting with human confirmation: The system may draft artifacts automatically, but unresolved or low-confidence items shall remain visible for human validation.
- Continuous improvement: Lessons learned from Retrospectives (G-08) shall feed updates to startup standards, checklists, and thresholds.

### 1.5 Success Measures

**BR-05** The solution shall be considered successful when:

- the PMO produces the startup kit within **1 day** of delivery, within the Readiness phase;
- the Talent PM, DM, and delivery team are onboarded using the kit;
- no engagement exits Readiness into Mobilize, and no Client Project Kickoff occurs, without G-01 gate approval or a documented exception approval;
- all contractual deliverables have a mapped owner and acceptance route;
- all contractual milestone dates have corresponding internal plan dates;
- all missing or ambiguous source information is logged as a validation point;
- the PMO Lead and Delivery Manager can assess startup readiness and margin risk from the pack;
- G-01 gate approval (kit created and team onboarded) before Mobilize is tracked as the PMO's leading indicator for **Delivery Consistency**.

### 1.6 Lifecycle Placement

**BR-10** The Startup Kit shall be positioned in the PMO delivery lifecycle as follows:

| Phase | Gate / Meeting | Owner | Startup Kit Role |
|---|---|---|---|
| Contracting (pre-sale) | PMO engagement | PMO Lead | PMO joins before the project is sold. It gains early context and sets the governance tier. |
| **Readiness** | **On-Board Talent PM / DM (first step)** | **PMO** | **Primary startup event.** Within 1 day of delivery, the PMO creates the kit and uses it to onboard the Talent PM, DM, and team. The same session sets the governance baseline: governance tier confirmed, RAID log and Decision Log baselined, cadence set, escalation briefed. Evidenced by the **G-01 checklist**. |
| Readiness | Sales to Delivery Handoff | Contracting | Follows On-Board: the onboarded Talent PM and DM attend, and the handoff detail (deal assumptions, unwritten commitments) refines the kit (G-02 checklist). |
| Mobilize | Internal Project Kickoff | Talent PM | Walks the internal team through the baselined kit (G-03 checklist). |
| Mobilize | Client Project Kickoff | PMO | Presents the kit outputs to the client through the Client Kickoff Deck and Project Success Agreement. Fed by G-04 and G-05. |
| Execution | Status meetings, PSR, MBR/QBR | Talent PM / PMO / DM | The kit's artifacts become the living controls for execution reporting. |
| Closure | Close / Acceptance, Retrospective | PMO | Lessons learned (G-08) update the startup standards for future engagements. |

---

## 2. Scope of the Solution

### 2.1 In Scope

**BR-06** The solution shall support startup mobilization for **contracted project engagements with a defined outcome**. This includes bespoke Azure, AWS, and GCP delivery engagements operating under SOWs, on both Time and Materials and Fixed Bid contracts.

**BR-07** The solution shall support projects delivered by Toptal talent teams. That includes Talent PMs, Delivery Managers, PMO Leads, the Director, PMO, Sales / Accounts, Contracting, and supporting technical leads or architects.

### 2.2 Out of Scope

**BR-08** The solution shall not perform full project execution management, detailed resource scheduling beyond startup baseline needs, commercial contracting, legal interpretation, or automated approval of ambiguous contractual terms.

**BR-08a** Consistent with the PMO model, the solution does not apply to managed services, fixed-capacity, or staff augmentation engagements.

**BR-09** Where source materials are incomplete, the solution shall generate placeholders, clarification items, and risk flags rather than substitute invented content.

### 2.3 Governance Tier Tailoring

**BR-11** The PMO Lead shall assign the engagement's governance tier during Contracting or at the start of Readiness. The kit shall scale to that tier:

- **Guided** (small scope, low complexity, established client): streamlined kit, with mandatory gate controls only and lighter reporting cadence.
- **Partnered** (standard thresholds, the baseline): full kit as defined in this specification.
- **Elevated** (high value, high complexity, new client, or elevated delivery risk): full kit plus closer forecast oversight, tighter internal buffers, and a named escalation path to the Director, PMO.

---

## 3. Functional Requirements

### 3.1 Input Handling

**FR-01** The system shall accept, at minimum, the following inputs where available:

- signed or awarded SOW;
- pre-sales presentations, proposals, solution decks, and estimate summaries;
- known contractual milestone dates;
- known acceptance language;
- named customer stakeholders;
- contract type and pricing model;
- Contracting and pre-sales materials available before the Sales to Delivery Handoff (the Handoff and its G-02 checklist then refine the kit);
- PMO Lead context gathered during Contracting, including the assigned governance tier;
- talent team staffing plan and onboarding status.

**FR-02** The absence of one or more non-SOW inputs shall not block draft generation. Missing information shall be recorded as unresolved validation points.

### 3.2 Document Ingestion and Extraction

**FR-03** The system shall extract, where present, the following information from the available source set:

- project and customer metadata;
- contract type and commercial model;
- delivery dates and milestone commitments;
- deliverables and scope statements;
- exclusions and constraints;
- acceptance language and approval requirements;
- customer obligations and dependencies;
- environment, access, data, and third-party prerequisites;
- reporting clauses and governance obligations;
- named stakeholders, approvers, and escalation contacts;
- platform references such as Azure, AWS, and GCP;
- role and skill requirements needed to staff the talent team.

### 3.3 Draft Artifact Generation

**FR-04** The system shall generate first-pass drafts of the following artifacts from extracted content and default rules:

- Project Startup Charter;
- SOW Interpretation Summary;
- Deliverables and Acceptance Matrix;
- Milestone Delivery Plan;
- Scope Decomposition or Backlog Seed;
- Dependency and Assumption Log;
- RAID Log (seed for the standard RAID Log and Decision Log);
- Stakeholder and Responsibility Model (aligned to G-05 Stakeholder Map);
- Communications and Reporting Plan (aligned to G-04 Comms Plan and the PSR template);
- Commercial and Margin Guardrails (seed for the Budget Burndown);
- Talent Onboarding Record;
- Startup Readiness Checklist (G-01).

**FR-04a** Kit outputs shall be structured to pre-populate the Mobilize toolkit: the Project Success Agreement (PSA), Client Kickoff Deck (KO), and RAID Log.

### 3.4 Unresolved Information Handling

**FR-05** The system shall not silently invent missing information. If required information is absent, unclear, or contradictory, the system shall:

- create a placeholder in the affected artifact;
- add a validation item to the open questions list;
- identify the required owner for clarification;
- assign a target date for confirmation where workflow rules permit;
- flag the delivery and/or commercial risk of non-resolution.

### 3.5 Source Traceability

**FR-06** Every generated deliverable, milestone, assumption, acceptance item, dependency, risk seed, and reporting obligation shall retain bi-directional traceability to its originating source.

**FR-07** Traceability shall support:

- source document identification;
- section, clause, page, or slide reference where available;
- extracted text or source excerpt reference;
- confidence level of extraction;
- downstream artifact references using that source element, including Mobilize toolkit artifacts.

### 3.6 Contract-Type Tailoring

**FR-08** The system shall adjust required fields and emphasis by contract type and governance tier.

**FR-09** For **Time and Materials**, the system shall emphasize:

- burn visibility;
- staffing and role assumptions;
- reporting cadence;
- consumption controls;
- customer dependency management.

**FR-10** For **Fixed Bid**, the system shall emphasize:

- scope containment;
- change control triggers;
- acceptance precision;
- internal milestone buffers;
- commercial exposure and margin protection.

### 3.7 Workflow Support

**FR-11** The system shall support PMO startup drafting within 1 day of delivery, kit-based onboarding of the Talent PM, DM, and team, review, rework, G-01 gate decision, exception handling, and controlled transition from Readiness into Mobilize.

---

## 4. Artifact Requirements

The startup kit shall produce three controlled layers of artifacts. All layers shall be baselined during Readiness and handed into Mobilize.

### 4.1 Layer 1: Executive Startup Pack

#### 4.1.1 Project Startup Charter

**AR-01** The charter shall contain:

- project purpose;
- delivery objectives and success criteria;
- high-level scope and exclusions;
- key deliverables and milestone dates;
- contract type;
- governance tier (Guided, Partnered, Elevated);
- delivery model and governance model;
- major startup risks;
- named leadership roles (Delivery Manager, Talent PM, PMO Lead);
- escalation path (any role → PMO Lead → Director, PMO);
- status of unresolved assumptions.

**AR-01a** The charter shall be the primary input to the Project Success Agreement (PSA) presented in Mobilize.

#### 4.1.2 SOW Interpretation Summary

**AR-02** This artifact shall translate contract language into operational delivery meaning and shall include:

- contracted deliverables;
- out-of-scope items and exclusions;
- customer obligations;
- assumptions and constraints;
- platform and environment commitments;
- dependencies and approval expectations;
- ambiguities or items requiring confirmation.

#### 4.1.3 Milestone Delivery Plan

**AR-03** This artifact shall contain:

- all contractual and internal milestones;
- backward planning from external commitments;
- predecessor relationships and key dependencies;
- internal review dates;
- internal buffer dates;
- critical path assumptions;
- explicit milestone ownership.

### 4.2 Layer 2: Delivery Control Pack

#### 4.2.1 Scope Decomposition / Backlog Seed

**AR-04** This artifact shall decompose SOW deliverables into the minimum level needed to make sequence, ownership, and acceptance visible. It shall include:

- deliverable-to-work-package or epic mapping;
- preliminary sequencing;
- ownership;
- dependency references;
- status of uncertain scope areas;
- linkages to milestones and acceptance items.

#### 4.2.2 Deliverables and Acceptance Matrix

**AR-05** This artifact shall support the PMO's Deliverable Acceptance mechanism, which requires documented client sign-off for every contracted deliverable. It shall include:

- deliverable name;
- SOW reference;
- acceptance criteria or acceptance placeholder;
- evidence required for submission;
- client approver;
- submission target date;
- review window;
- rejection or rework path;
- unresolved acceptance clarifications.

#### 4.2.3 Dependency and Assumption Log

**AR-06** This artifact shall include:

- dependency or assumption description;
- category;
- source reference;
- owner;
- required validation date;
- impact if unmet;
- status;
- escalation trigger where relevant.

#### 4.2.4 RAID Log

**AR-07** This artifact shall seed the standard RAID Log and the Decision Log, which are baselined at the G-01 session. It shall include:

- risks, assumptions, issues, and dependencies;
- decisions made during Readiness, with owner and date;
- category such as technical, customer, commercial, operational, platform, or governance;
- owner;
- probability and impact where used;
- trigger or early warning sign;
- mitigation or response action;
- due dates and status.

#### 4.2.5 Communications and Reporting Plan

**AR-08** This artifact shall align to the G-04 Comms Plan and define:

- required reports and meetings, including the weekly 30-minute check-in (Talent PM, Delivery Manager, PMO), weekly Project Status Report (PSR), and MBR/QBR (G-07);
- audience;
- content owner;
- cadence, scaled to governance tier;
- format;
- delivery day;
- escalation route;
- PMO health rating process: evidence is exchanged at the weekly check-in, and the PMO Lead then issues the rating independently, sharing it with the DM and Talent PM before it reaches leadership.

### 4.3 Layer 3: Assurance Pack

#### 4.3.1 Stakeholder and Responsibility Model

**AR-09** This artifact shall align to the G-05 Stakeholder Map and identify:

- named roles and stakeholders;
- decision rights;
- approvers;
- escalation contacts;
- reporting accountabilities;
- the responsibility split across Delivery Manager (voice of the customer), Talent PM (project delivery), PMO Lead (delivery assurance), Technical Lead, Sales / Accounts, Contracting, and customer roles.

**AR-10** A RACI or equivalent model may be used, but ownership shall be unambiguous and consistent with the PMO decision rights:

| Decision | PMO Lead | Delivery Manager | Talent PM | Sales / Accounts | Client |
|---|---|---|---|---|---|
| Startup readiness (G-01 gate) | R, A | C | C | C | I |
| Talent staffing & replacement | R, A | C | C | C | I |
| Work at risk / commercial exceptions | R, A | I | I | C | I |
| Scope & change | R | A | — | C, R | A |
| Delivery risk & recovery | R, A | C | R | I | I |

On scope and change, the DM is accountable for Toptal's position, the client approves the change, and Contracting issues the change order. The Director, PMO is the next point of escalation beyond the PMO Lead.

#### 4.3.2 Commercial and Margin Guardrails

**AR-11** This artifact shall seed the Budget Burndown and shall include:

- contract type implications;
- billing or consumption assumptions where applicable;
- staffing assumptions tied to commercial exposure;
- approved and non-approved work rules, including work-at-risk rules (PMO Lead owned);
- change control triggers and the change order route (PMO Lead leads → DM aligns client → client approves → Contracting issues change order);
- budget vs. actuals and variance baseline;
- margin risk indicators;
- internal escalation thresholds.

#### 4.3.3 Talent Onboarding Record

**AR-13** This artifact shall evidence that the PMO used the Startup Kit to onboard the Talent PM, DM, and team. It is implemented by Parts A–B of the G-01 checklist, which walk through every Section 4 artifact item by item. It shall include:

- the kit artifacts walked through with the Talent PM, DM, and team (all of Section 4), with date and attendees;
- open questions raised during onboarding, logged to the open questions list;
- named Talent PM and Delivery Manager, with onboarding completion date;
- delivery talent roster against the required roles and skills;
- open staffing gaps and planned replacements (PMO Lead owned);
- confirmation that the Talent PM, DM, and delivery team have reviewed the startup kit baseline.

#### 4.3.4 Startup Readiness Checklist (G-01)

**AR-12** This artifact shall be implemented as, or mapped one-to-one to, Section 24 (G-01 Gate Criteria) of the PMO **G-01 checklist** for the On-Board Talent PM / DM gate. It shall include:

- mandatory readiness checks, including talent onboarding;
- owner and due date for each check;
- open exception items;
- gate decision status;
- approver fields;
- bypass reason and approving authority where an exception is granted.

---

## 5. Workflow and Governance Requirements

### 5.1 Startup Timeline

**WR-01** The PMO shall create the startup kit within **1 day of delivery**, during the Readiness phase, and use it to onboard the Talent PM, DM, and team. It shall be approved at the On-Board Talent PM / DM gate before the Sales to Delivery Handoff (G-02) and Mobilize.

### 5.2 Workflow States

**WR-02** The startup process shall support the following states, all of which occur within Readiness:

- Awarded;
- Drafting in Progress (PMO, within 1 day);
- Review in Progress;
- Clarification Pending;
- Talent Onboarding in Progress (using the kit);
- Ready for G-01 Gate Review;
- Approved for Mobilize;
- Approved with Exception;
- Rework Required.

### 5.3 Readiness Exit Gate (No-Mobilize / No-Kickoff)

**WR-03** The engagement shall not exit Readiness into Mobilize, and no Internal Project Kickoff or Client Project Kickoff shall occur, until:

- the G-01 minimum gate criteria are met; or
- an authorized exception is documented with owner, rationale, expiry, and mitigation.

### 5.4 Minimum Gate Criteria

**WR-04** The G-01 gate shall require confirmation that:

- the startup kit was created by the PMO within 1 day of delivery, or the delay is logged as an exception;
- the Talent PM, Delivery Manager, and delivery team are onboarded using the kit, and the talent team is staffed or has an owned staffing plan;
- the Talent PM and DM are ready to attend the Sales to Delivery Handoff (G-02);
- the SOW has been translated into a delivery summary;
- every contracted deliverable has an owner and acceptance route;
- contractual milestones have internal planned dates;
- critical assumptions and dependencies are logged and owned;
- reporting cadence and governance roles are defined;
- top delivery and margin risks are documented;
- the governance tier is assigned;
- the Delivery Manager and Technical Lead have reviewed the kit;
- unresolved ambiguities are explicitly listed.

### 5.5 Initial Planning Prerequisites

**WR-05** No sprint, technical, or delivery execution shall begin until the following minimum controls exist and have been baselined at G-01:

- milestone plan;
- dependency and assumption log;
- communications and reporting cadence;
- responsibility model;
- RAID log seeded with initial startup risks.

### 5.6 Review and Approval Rules

**WR-06** Every artifact shall have:

- a named owner;
- a named reviewer;
- a named approver or approval authority.

**WR-07** Approval rules shall distinguish between:

- draft completeness;
- operational validity;
- commercial or governance acceptance.

### 5.7 Exception Management

**WR-08** If any mandatory gate criterion is not met, the system shall require:

- explicit identification of the missing control;
- risk impact statement;
- temporary mitigation;
- exception owner;
- exception approval authority (PMO Lead, escalating to the Director, PMO for Elevated-tier engagements or material margin exposure);
- target date for closure.

### 5.8 Continuous Improvement

**WR-09** Lessons learned captured at the Retrospective (G-08) and in the monthly delivery signal review shall be used to update the startup checklist, default rules, templates, and governance tier thresholds.

---

## 6. Data Requirements

### 6.1 Logical Data Model

**DR-01** The system shall maintain a normalized logical data model comprising, at minimum, the following entities:

- Project Metadata;
- Contract Metadata;
- Source Documents;
- Source References;
- Deliverables;
- Milestones;
- Acceptance Criteria;
- Assumptions;
- Dependencies;
- Risks;
- Issues;
- Decisions;
- Stakeholders;
- Roles and Responsibility Assignments;
- Talent Assignments;
- Reporting Obligations;
- Commercial Guardrails;
- Open Questions;
- Workflow States;
- Approval Records;
- Version History.

### 6.2 Minimum Entity Requirements

**DR-02** The model shall support the following attributes at minimum:

- **Project Metadata:** project ID, name, customer, delivery model, governance tier, lifecycle phase, status, award date.
- **Contract Metadata:** contract type, commercial basis, source references, contractual dates.
- **Source Documents:** file identifier, document type, version, ingest date.
- **Source References:** document link, clause or slide reference, excerpt reference, confidence score.
- **Deliverables:** ID, description, scope status, source reference, owner.
- **Milestones:** ID, external date, internal date, buffer date, linked deliverables, owner.
- **Acceptance Criteria:** criterion, evidence required, approver, review period, clarification status.
- **Assumptions/Dependencies:** description, category, owner, criticality, validation date, impact.
- **Risks/Issues:** category, severity, trigger, response, owner, status.
- **Decisions:** decision text, decision owner, date, rationale, linked RAID items.
- **Stakeholders/Roles:** name, role, organization, contact details, decision rights, reporting role.
- **Talent Assignments:** name, role, start date, onboarding status, replacement status.
- **Reporting Obligations:** report type, cadence, audience, owner, delivery channel.
- **Commercial Guardrails:** threshold type, contract relevance, exposure note, escalation trigger.
- **Open Questions:** question text, source gap, owner, due date, status.
- **Approval Records:** artifact, approver, decision, date, comments, exception status.
- **Version History:** artifact version, timestamp, editor, change summary, approval status.

### 6.3 Data Integrity Requirements

**DR-03** The system shall enforce:

- unique identifiers for core entities;
- version control for all generated artifacts;
- auditability of edits and approvals;
- referential integrity across deliverables, milestones, and source references;
- status tracking for unresolved and approved items.

---

## 7. Role Requirements

### 7.1 PMO Lead

**RR-03** The PMO Lead owns the On-Board Talent PM / DM gate and shall be responsible for:

- engaging during Contracting and assigning the governance tier;
- creating the startup kit within 1 day of delivery;
- building the talent team, onboarding the Talent PM, DM, and team using the kit, and leading replacements;
- setting the delivery baseline with the Delivery Manager;
- startup assurance, completeness, and quality checks;
- visibility of commercial and margin risk, including budget vs. actuals baseline and work-at-risk decisions;
- standards enforcement;
- administering the G-01 gate and approving or recommending within the no-Mobilize control process;
- running the G-01 session (onboarding plus the governance baseline) and the Client Project Kickoff;
- serving as the first point of escalation for startup and delivery risk.

### 7.2 Talent PM

**RR-01** The Talent PM, once onboarded with the kit, shall be responsible for:

- taking ownership of and maintaining the startup kit the PMO created;
- maintaining the milestone plan;
- maintaining the decomposition or backlog seed;
- managing the RAID log;
- maintaining reporting outputs;
- driving closure of open startup clarifications;
- running the Internal Project Kickoff (G-03) in Mobilize.

### 7.3 Delivery Manager

**RR-02** The Delivery Manager, as voice of the customer, shall be responsible for:

- continuity from pre-sales to delivery mobilization and ownership of the client relationship;
- validating customer-facing assumptions;
- confirming governance and escalation paths with the client;
- being accountable for Toptal's position on scope and change;
- reviewing delivery readiness;
- attending the PMO-led Client Project Kickoff as the client relationship owner;
- partnering with the PMO Lead on client impact when startup risks surface.

### 7.4 Director, PMO

**RR-07** The Director, PMO shall be the next point of escalation beyond the PMO Lead. The Director shall also approve exceptions where governance rules or tier require it.

### 7.5 Technical Lead / Architect

**RR-04** The Technical Lead or Architect shall be responsible for:

- validating technical assumptions and dependencies;
- confirming feasibility of decomposition and milestone logic;
- identifying environment, access, data, and integration prerequisites;
- reviewing technical readiness risks.

### 7.6 Sales / Accounts and Contracting

**RR-05** Sales / Accounts, with Contracting as owner of the Sales to Delivery Handoff (G-02), shall be responsible for:

- documenting deal assumptions;
- clarifying customer sensitivities;
- identifying non-obvious expectations discussed during pre-sales;
- highlighting unwritten commitments that require confirmation or rejection;
- issuing change orders (Contracting) once the client approves a scope change.

### 7.7 Approval and Segregation of Duties

**RR-06** The system shall support segregation of drafting, review, and approval responsibilities. The PMO creates the kit, the Delivery Manager and Technical Lead review it, and the PMO Lead approves. The DM and Tech Lead review is the independent check; for Elevated-tier engagements the Director, PMO confirms the approval. A single individual should not both author and unilaterally approve the full startup gate where governance rules require independent review.

---

## 8. Non-Functional Requirements

### 8.1 Confidence Scoring

**NFR-01** The ingestion and extraction engine shall display confidence levels for extracted fields and generated inferences so reviewers can prioritize validation effort.

### 8.2 Ambiguity and Conflict Highlighting

**NFR-02** The system shall flag contradictory clauses, duplicate commitments, unclear acceptance language, and date conflicts visible in source materials.

### 8.3 Template Adaptability

**NFR-03** Generated artifacts shall adapt by contract type, governance tier, delivery model, and available source completeness without removing mandatory control visibility.

### 8.4 Readiness Scoring

**NFR-04** The system shall calculate a Startup Readiness Score based on the completion status of mandatory G-01 controls, talent onboarding status, unresolved high-risk gaps, and gate prerequisites. The score shall not replace human approval by the PMO Lead.

### 8.5 Auditability

**NFR-05** The system shall maintain a full audit trail of extraction, edits, approvals, exceptions, and artifact version changes.

### 8.6 Access Control

**NFR-06** The system shall support role-based access so that editing, review, approval, and read-only permissions can be separated across Talent PMs, Delivery Managers, PMO Leads, the Director, PMO, and other stakeholders.

### 8.7 Performance

**NFR-07** For a standard startup package, the system shall generate an initial draft within **[X] minutes/hours** after source ingestion, subject to document size and complexity constraints defined by implementation standards.

### 8.8 Usability

**NFR-08** The system shall present unresolved items, low-confidence extractions, and gate blockers so that the required review action is obvious and fast for Delivery Managers and PMO Leads.

### 8.9 Export and Portability

**NFR-09** The system shall support export of the startup kit and individual artifacts into standard shareable formats for delivery use and audit retention, including direct population of the PMO Operating System workbook toolkit (PSA, KO, RAID, PSR, Budget Burndown).

### 8.10 Reliability

**NFR-10** The system shall preserve source-to-output traceability and artifact history across regeneration cycles and shall not overwrite confirmed human edits without explicit user action.

---

## 9. Business Rules

1. Missing information shall never be treated as confirmed information.
2. All contractual commitments shall trace to source.
3. The PMO creates the startup kit within 1 day of delivery and uses it to onboard the Talent PM, DM, and team, in Readiness at the On-Board Talent PM / DM gate. The engagement exits Readiness into Mobilize, and any kickoff occurs, only with G-01 gate approval or a documented exception.
4. Fixed Bid projects shall require stricter scope, acceptance, and change control visibility than T&M projects.
5. Kit depth scales with governance tier, but mandatory gate controls apply to every tier.
6. Open questions with material delivery or commercial impact shall remain visible until resolved or explicitly accepted as risk.
7. Human approval shall remain mandatory for readiness decisions, even where automation produces the draft pack.
8. Raising a startup risk early is always welcome. Thresholds right-size the response; they do not gate whether someone speaks up.

---

## 10. Acceptance Criteria for the Solution

The solution shall be accepted when it can demonstrate that it:

- ingests an SOW and optional pre-sales materials, and accepts refinements from the Sales to Delivery Handoff (G-02);
- extracts required startup information with confidence indicators;
- generates the defined artifact set with placeholders rather than invented content;
- preserves source traceability across generated outputs and into the Mobilize toolkit;
- supports T&M and Fixed Bid tailoring and Guided, Partnered, and Elevated governance tiers;
- shows the PMO created the kit within 1 day of delivery and used it to onboard the Talent PM, DM, and team;
- enforces the G-01 gate workflow, approvals, and exceptions before Mobilize;
- captures version history and audit trail;
- presents a usable readiness view for PMO Lead and Delivery Manager review.
