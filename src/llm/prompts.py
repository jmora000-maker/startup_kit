"""Prompt templates and system instructions for multi-pass LLM extraction."""

SYSTEM_PROMPT = """You are an expert Toptal PMO Delivery Lead and Startup Specialist.
Your goal is to extract structured project management data from provided Statement of Work (SOW) documents, pre-sales decks, and context notes to build the PMO Startup Kit.

STRICT BUSINESS RULES & CONSTRAINTS:
1. NO HALLUCINATION: Extract only factual information present in the input documents.
2. CONCISE & FOCUSED: Keep all field values concise, specific, and factual (1-2 sentences per field). Avoid verbose repetition.
3. MISSING ACCEPTANCE CRITERIA: If a deliverable's acceptance criteria are not explicitly specified in the text, set acceptance_criteria to null (None).
4. MISSING DATES: If milestone dates are not explicitly stated, set external_date to null (None).
5. SOURCE TRACEABILITY: Every extracted item must include a valid SourceReference with:
   - document_name: exact filename where the information was found
   - clause_or_slide: the section number, heading, or slide number (e.g. "Section 3.2", "Slide 4", "Page 2")
   - confidence_score: floating point score between 0.0 and 1.0 indicating extraction confidence.
6. GOVERNANCE TIERS: Valid tiers are 'Guided', 'Partnered', 'Elevated'. Default to 'Partnered' if not specified.
7. CONTRACT TYPES: Common types include 'Time and Materials' and 'Fixed Bid'.
"""

CHARTER_PROMPT = """Analyze the provided project documents and extract the overall Project Charter and Governance metadata.

Extract:
- project_name: Title of the project or engagement.
- client_name: Name of the client or sponsoring organization.
- governance_tier: 'Guided', 'Partnered', or 'Elevated' (default 'Partnered').
- contract_type: 'Time and Materials' or 'Fixed Bid' (default 'Time and Materials').
- delivery_manager: Named Delivery Manager if mentioned, else null.
- talent_pm: Named Talent Project Manager if mentioned, else null.
- pmo_lead: Named PMO Lead if mentioned, else null.
- executive_summary: A concise 2-4 sentence summary of project objectives, tech stack, and scope.
- source_reference: Document name, section/slide reference, and confidence score.

DOCUMENTS CONTENT:
{documents_text}
"""

DELIVERABLES_PROMPT = """Analyze the provided project documents and extract all contractual deliverables.

For each deliverable:
- id: Sequential identifier (e.g., DEL-01, DEL-02, DEL-03...)
- description: Clear and concise statement of the deliverable outcome.
- owner: Named owner or role if stated, else 'Unassigned'.
- acceptance_criteria: Exact explicit acceptance criteria if provided in the text. If NOT explicitly stated, you MUST set this to null.
- source_reference: The source document name, section/clause, and confidence score.

DOCUMENTS CONTENT:
{documents_text}
"""

MILESTONES_PROMPT = """Analyze the provided project documents and extract all delivery milestones and target dates.

For each milestone:
- id: Sequential identifier (e.g., M1, M2, M3...)
- description: Milestone name or phase completion outcome.
- external_date: Contractual or committed target date in ISO format YYYY-MM-DD. If no specific date is found, set to null.
- internal_buffer_date: Internal target date with contingency buffer in ISO format YYYY-MM-DD if explicitly mentioned, else null.
- source_reference: The source document name, section/page, and confidence score.

DOCUMENTS CONTENT:
{documents_text}
"""

RAID_PROMPT = """Analyze the provided project documents and extract key RAID items (Risks, Assumptions, Issues, Dependencies).

CONSTRAINTS:
1. Extract the most critical items (maximum 20 items total across all 4 categories).
2. Keep descriptions concise and actionable (1-2 sentences).

For each item:
- type: Must be exactly one of: 'Risk', 'Assumption', 'Issue', 'Dependency'.
- description: Concise statement of the risk, assumption, issue, or external dependency.
- owner: Responsible party or role, else 'Unassigned'.
- status: Current status, default 'Open'.
- source_reference: The source document name, section/slide, and confidence score.

DOCUMENTS CONTENT:
{documents_text}
"""

QUESTIONS_PROMPT = """Review the provided project documents and identify critical open clarification questions, ambiguous statements, unconfirmed dates, or unstated acceptance criteria that require confirmation from the client or delivery team.

CONSTRAINTS:
- Return a concise, prioritized list of the top 10-15 actionable questions (strings).
- Keep each question direct and focused on delivery/commercial risk.

DOCUMENTS CONTENT:
{documents_text}
"""

SOW_INTERPRETATION_PROMPT = """Analyze the provided project documents and extract the SOW Interpretation Summary.

Extract:
- contracted_deliverables: Key deliverables explicitly contracted in the SOW.
- out_of_scope_items: Explicit scope exclusions and out-of-scope tasks.
- customer_obligations: Prerequisites, data, environments, or access customer must provide.
- assumptions: Baseline delivery and commercial assumptions.
- constraints: Known delivery, technical, regulatory, or schedule constraints.
- platform_environment_commitments: Cloud platform (AWS/Azure/GCP) and infrastructure commitments.
- dependencies: External dependencies.
- approval_expectations: Client review windows and sign-off expectations.
- ambiguity_notes: Unclear or conflicting contractual terms.

DOCUMENTS CONTENT:
{documents_text}
"""

SCOPE_DECOMPOSITION_PROMPT = """Analyze the provided project deliverables and decompose them into a preliminary backlog seed / work packages (maximum 15 work packages). Keep titles and descriptions concise.

For each work package:
- id: e.g. WP-01, WP-02
- parent_deliverable_id: e.g. DEL-01
- title: Concise work package title
- description: Brief description of tasks (1-2 sentences)
- preliminary_sequence: Integer sequence order (1, 2, 3...)
- owner: Role or named owner if known, else '[UNASSIGNED - TO BE CONFIRMED]'
- dependency_references: List of IDs or descriptions of prerequisites
- linked_milestones: Associated milestone IDs (e.g. M1)
- linked_acceptance_items: Associated acceptance criteria references
- uncertain_scope: Boolean flag indicating if scope is unconfirmed

DOCUMENTS CONTENT:
{documents_text}
"""

ACCEPTANCE_PROCESS_PROMPT = """Analyze the deliverables in the provided documents and extract explicit acceptance process details.

For each deliverable:
- id: Deliverable ID (DEL-01, etc.)
- name: Deliverable title
- description: Description
- sow_reference: Section or clause reference
- acceptance_criteria: Explicit contractual criteria or null
- evidence_required: Documents, artifacts, or sign-offs required as proof
- client_approver: Named client approver or role, or '[UNASSIGNED - TO BE CONFIRMED]'
- submission_target_date: Target submission date (YYYY-MM-DD) if stated
- review_window: Client review window (e.g. '5 business days')
- rejection_rework_path: Rework and resubmission mechanism

DOCUMENTS CONTENT:
{documents_text}
"""

STAKEHOLDERS_PROMPT = """Analyze the provided project documents and extract key delivery stakeholders and decision rights.
Ensure you identify PMO leadership (PMO Lead, Director, PMO), delivery leadership (Delivery Manager, Talent PM, Technical Lead), and customer counterparts (Client Sponsor, Client Approver).

For each stakeholder:
- name: Named individual or role placeholder
- role: PMO Lead, Director, PMO, Delivery Manager, Talent PM, Client Sponsor / Approver, Tech Lead, etc.
- organization: 'Toptal PMO', 'Toptal PMO Leadership', 'Toptal', or client organization name
- decision_rights: Summary of decision authority (e.g., G-01 Gate Sign-off, Talent Staffing/Replacement, Work-at-Risk Approvals, Scope Change Approval)
- approver_responsibilities: Specific approval scope (e.g., G-01 Gate, Baseline Exceptions, Deliverables Acceptance)
- escalation_responsibility: Escalation path (e.g., PMO Lead -> Director, PMO -> VP, Delivery)
- reporting_accountability: Reporting received or delivered (e.g., Independent Weekly Health Rating, Weekly PSR, Leadership Rollup)

DOCUMENTS CONTENT:
{documents_text}
"""

COMMUNICATIONS_PROMPT = """Analyze the provided project documents and extract required communications, reports, and governance meetings.

For each item:
- id: COM-01, COM-02...
- name: Report or meeting name (e.g., Weekly Check-in, Weekly PSR, MBR/QBR)
- audience: Target stakeholders
- content_owner: Role responsible for preparation
- cadence: Frequency (Weekly, Monthly, etc.)
- governance_tier_applicability: Tiers where this applies
- format: Format (e.g., Virtual 30-min call, Email/PDF report)
- delivery_day: Day of week or period
- escalation_route: Escalation channel
- pmo_health_rating_notes: PMO health rating mechanism

DOCUMENTS CONTENT:
{documents_text}
"""

COMMERCIAL_GUARDRAILS_PROMPT = """Analyze the project commercial model and extract guardrails to protect delivery margin and budget.

Extract:
- contract_type_implication: Commercial rules based on Time and Materials or Fixed Bid
- billing_consumption_assumption: Invoicing and timesheet rules
- staffing_assumption: Team allocation and staffing constraints
- commercial_exposure_note: Financial exposure notes
- approved_work_rule: Policy for authorized work
- non_approved_work_rule: Policy for unauthorized / out-of-scope work
- work_at_risk_rule: Rules for pre-contract or out-of-budget execution
- change_control_trigger: Triggers requiring formal change order
- change_order_route: Approval route for change orders
- budget_baseline: Baseline budget or cap
- variance_indicator: Variance status
- margin_risk_indicator: Risk rating (Low/Medium/High)
- escalation_threshold: Financial variance escalation trigger

DOCUMENTS CONTENT:
{documents_text}
"""

TALENT_ONBOARDING_PROMPT = """Analyze the project talent staffing and onboarding requirements.

Extract:
- talent_pm: Named Talent PM or '[UNASSIGNED - TO BE CONFIRMED]'
- delivery_manager: Named Delivery Manager or '[UNASSIGNED - TO BE CONFIRMED]'
- pmo_lead: Named PMO Lead
- required_roles: Roles required to staff delivery
- required_skills: Key technical skills (e.g. AWS, Terraform, Python)
- staffing_gaps: Any identified staffing gaps
- replacement_plan: Protocol for talent replacement

DOCUMENTS CONTENT:
{documents_text}
"""

DECISIONS_PROMPT = """Analyze the provided project documents and extract key baseline decisions already agreed during pre-sales or Readiness (maximum 15 key decisions). Keep descriptions concise.

For each decision:
- id: DEC-01, DEC-02...
- decision_text: Concise statement of decision
- decision_owner: Responsible owner
- decision_date: Date if known
- rationale: Concise context or reason for decision
- linked_raid_item: Linked risk or assumption ID if applicable
- status: Status (default 'Approved')

DOCUMENTS CONTENT:
{documents_text}
"""

CONTRACT_CONFLICTS_PROMPT = """Analyze the provided project documents and extract the most critical contractual ambiguities, contradictory clauses, conflicting dates, subjective acceptance terms, and duplicate or unaligned commitments (NFR-02).

CRITICAL CONSTRAINTS:
1. Focus on the most material ambiguities and conflicts (maximum 15 items).
2. Keep descriptions, quotes, and recommendations concise and direct (1-2 sentences per field).
3. Do not duplicate similar items.

For each detected ambiguity or conflict:
- anomaly_id: Sequential identifier (e.g., AMB-01, AMB-02...)
- category: One of 'Date Conflict', 'Scope Contradiction', 'Ambiguous Acceptance', 'Unclear SLA', 'Ownership Gap'
- conflicting_clauses: Concise quotes or citations from source documents with document name and section/page reference
- risk_impact: Concise summary of the schedule, margin, or contractual risk (1-2 sentences)
- recommended_clarification: Actionable clarification question for Client/Contracting
- status: 'Open'

DOCUMENTS CONTENT:
{documents_text}
"""
