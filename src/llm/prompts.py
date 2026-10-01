"""Prompt templates and system instructions for multi-pass LLM extraction."""

SYSTEM_PROMPT = """You are an expert Toptal PMO Delivery Lead and Startup Specialist.
Your goal is to extract structured project management data from provided project documents, pre-sales decks, and context notes to build the PMO Startup Kit.

STRICT BUSINESS RULES & CONSTRAINTS:
1. NO HALLUCINATION: Extract only factual information present in the input documents.
2. NO SOW OR EXTERNAL DOCUMENT REFERENCES: The consumers of this report DO NOT have access to the Statement of Work (SOW), pre-sales decks, contracts, or source documents. Do NOT reference 'the SOW', 'Statement of Work', 'input documents', 'source documents', 'page numbers', or 'clause numbers' in any extracted text, descriptions, questions, deliverables, milestones, risks, or assumptions. All text must be completely self-contained and document-agnostic.
3. CONCISE & SIMPLIFIED: Keep all field values, summaries, and descriptions short, clear, direct, and concise (1-2 sentences maximum). Simplify the report text so that stakeholders can understand the project baseline instantly without legalistic jargon or redundant phrasing.
4. MISSING ACCEPTANCE CRITERIA: If a deliverable's acceptance criteria are not explicitly specified in the text, set acceptance_criteria to null (None).
5. MISSING DATES: If milestone dates are not explicitly stated, set external_date to null (None).
6. SOURCE TRACEABILITY: Every extracted item must include a valid SourceReference with:
   - document_name: exact filename where the information was found
   - clause_or_slide: the section number, heading, or slide number (e.g. "Section 3.2", "Slide 4", "Page 2")
   - confidence_score: floating point score between 0.0 and 1.0 indicating extraction confidence.
7. GOVERNANCE TIERS: Valid tiers are 'Guided', 'Partnered', 'Elevated'. Default to 'Partnered' if not specified.
8. CONTRACT TYPES: Common types include 'Time and Materials' and 'Fixed Bid'.
"""

CHARTER_PROMPT = """Analyze the provided project documents and extract the overall Project Charter and Governance metadata.

CONSTRAINTS:
- Keep the executive summary strictly between 2-3 concise sentences covering project objectives, tech stack, and scope.
- Ensure all text is self-contained and does NOT mention or reference the SOW, contracts, or source documents.

Extract:
- project_name: Title of the project or engagement.
- client_name: Name of the client or sponsoring organization.
- governance_tier: 'Guided', 'Partnered', or 'Elevated' (default 'Partnered').
- contract_type: 'Time and Materials' or 'Fixed Bid' (default 'Time and Materials').
- delivery_manager: Named Delivery Manager if mentioned, else null.
- talent_pm: Named Talent Project Manager if mentioned, else null.
- pmo_lead: Named PMO Lead if mentioned, else null.
- executive_summary: A concise 2-3 sentence summary of project objectives, tech stack, and scope. Ensure the summary is self-contained and does NOT mention or reference the SOW or input documents.
- source_reference: Document name, section/slide reference, and confidence score.

DOCUMENTS CONTENT:
{documents_text}
"""

DELIVERABLES_PROMPT = """Analyze the provided project documents and extract key contractual project deliverables.

CONSTRAINTS:
1. Focus strictly on top key contractual deliverables and major deliverables (maximum 15-20 deliverables).
2. Keep descriptions clear, direct, and self-contained (1-2 sentences maximum). Do NOT mention or refer to the SOW or other documents.
3. Keep acceptance criteria concise and direct (1-2 sentences). If not explicitly stated, you MUST set acceptance_criteria to null.

For each deliverable:
- id: Sequential identifier (e.g., DEL-01, DEL-02, DEL-03...)
- name: Concise title of the deliverable
- description: Clear, concise, and self-contained statement of the deliverable outcome. Do NOT mention or refer to the SOW or other documents.
- owner: Named owner or role if stated, else 'Unassigned'.
- acceptance_criteria: Exact explicit acceptance criteria if provided in the text (state concisely and directly without referencing the SOW or documents). If NOT explicitly stated, you MUST set this to null.
- sow_reference: SOW work item references covered (e.g. story IDs, deliverable numbers, task codes, or section references) if mentioned, else null.
- source_reference: The source document name, section/clause, and confidence score.

DOCUMENTS CONTENT:
{documents_text}
"""

MILESTONES_PROMPT = """Analyze the provided project documents and extract key delivery milestones, target dates, and phase gates.

CONSTRAINTS:
1. Extract key delivery milestones and phase gates (maximum 15 milestones).
2. Keep milestone descriptions concise and direct (1 sentence). Do NOT mention or refer to the SOW or other documents.

For each milestone:
- id: Sequential identifier (e.g., M1, M2, M3...)
- description: Concise milestone name or phase completion outcome. Do NOT mention or refer to the SOW or other documents.
- external_date: Contractual or committed target date in ISO format YYYY-MM-DD. If no specific date is found, set to null.
- internal_buffer_date: Internal target date with contingency buffer in ISO format YYYY-MM-DD if explicitly mentioned, else null.
- source_reference: The source document name, section/page, and confidence score.

DOCUMENTS CONTENT:
{documents_text}
"""

RAID_PROMPT = """Analyze the provided project documents and extract key RAID items (Risks, Assumptions, Issues, Dependencies).

CONSTRAINTS:
1. Extract the most critical items (maximum 20 items total across all 4 categories).
2. Keep descriptions concise, direct, and actionable (1-2 sentences).
3. Do NOT reference the SOW or other documents in descriptions; state the risk, assumption, issue, or dependency directly.

For each item:
- type: Must be exactly one of: 'Risk', 'Assumption', 'Issue', 'Dependency'.
- description: Concise statement of the risk, assumption, issue, or external dependency.
- owner: Responsible party or role, else 'Unassigned'.
- status: Current status, default 'Open'.
- source_reference: The source document name, section/slide, and confidence score.

DOCUMENTS CONTENT:
{documents_text}
"""

QUESTIONS_PROMPT = """Review the provided project documents and identify critical open clarification questions, ambiguous requirements, unconfirmed dates, or unstated acceptance criteria that require confirmation from the client or delivery team.

CONSTRAINTS:
- Return a concise, prioritized list of the top 10-15 actionable questions (strings).
- Keep each question direct, simple, and self-contained (1 sentence per question).
- CRITICAL: Do NOT phrase questions by referencing the SOW or other documents (e.g. do NOT say 'The SOW does not specify X' or 'The document is unclear about Y'). Instead, ask direct questions about the project (e.g. 'What is the target completion date for Phase 1?', 'Who is the client sign-off approver for DEL-01?').

DOCUMENTS CONTENT:
{documents_text}
"""

SOW_INTERPRETATION_PROMPT = """Analyze the provided project documents and extract the Scope & Baseline Interpretation Summary.

CONSTRAINTS:
1. Extract only the top essential items per category (maximum 5-8 items per list field).
2. Keep each item/summary concise, direct, and self-contained (1-2 sentences maximum per item).
3. Do NOT mention or reference the SOW, contracts, or source documents in any text or field.

Extract:
- contracted_deliverables: Key deliverables agreed for the project (maximum 8 items). Keep descriptions concise and self-contained.
- out_of_scope_items: Explicit scope exclusions and out-of-scope tasks (maximum 8 items).
- customer_obligations: Prerequisites, data, environments, or access customer must provide (maximum 8 items).
- assumptions: Baseline delivery and project assumptions (maximum 8 items).
- constraints: Known delivery, technical, regulatory, or schedule constraints (maximum 8 items).
- platform_environment_commitments: Cloud platform (AWS/Azure/GCP) and infrastructure commitments (maximum 8 items).
- dependencies: External dependencies (maximum 8 items).
- approval_expectations: Client review windows and sign-off expectations (maximum 5 items).
- ambiguity_notes: Unclear or unconfirmed scope terms (maximum 8 items, stating scope gaps concisely without referencing documents).

Keep all text concise, simplified, and self-contained without referencing the SOW or other documents.

DOCUMENTS CONTENT:
{documents_text}
"""

SCOPE_DECOMPOSITION_PROMPT = """Analyze the provided project deliverables and decompose them into a preliminary backlog seed / work packages (maximum 15 work packages). Keep titles and descriptions concise.

CONSTRAINTS:
1. Maximum 15 work packages total.
2. Keep descriptions brief and actionable (1-2 sentences maximum), appending SOW references if applicable (e.g. 'Stories: HS-4781', 'Deliverable 1.2').
3. Every work package MUST reference an existing parent deliverable ID from the deliverables list below, and its associated linked milestone IDs.

DELIVERABLES LIST:
{deliverables_text}

For each work package:
- id: e.g. WP-01, WP-02
- parent_deliverable_id: e.g. DEL-01 (MUST match one of the deliverable IDs listed above)
- title: Concise work package title
- description: Brief description of tasks (1-2 sentences, with 'Stories: <ID>' or 'Ref: <Section>' suffix if SOW references apply)
- preliminary_sequence: Integer sequence order (1, 2, 3...)
- owner: Role or named owner if known, else '[UNASSIGNED - TO BE CONFIRMED]'
- dependency_references: List of IDs or descriptions of prerequisites
- linked_milestones: Associated milestone IDs (e.g. M1)
- linked_acceptance_items: Associated acceptance criteria references
- uncertain_scope: Boolean flag indicating if scope is unconfirmed

DOCUMENTS CONTENT:
{documents_text}
"""

ACCEPTANCE_PROCESS_PROMPT = """Analyze the deliverables in the provided documents and extract explicit acceptance process details. Keep descriptions concise, direct, and self-contained without referencing the SOW or other documents.

CONSTRAINTS:
1. Focus only on primary deliverables and major acceptance gates (maximum 15 deliverables).
2. Keep all text fields (description, acceptance criteria, evidence, rework path) brief and direct (1-2 sentences maximum).
3. Do NOT cite or reference the SOW, contracts, or source documents in descriptions or criteria.

For each deliverable:
- id: Deliverable ID (DEL-01, etc.)
- name: Deliverable title
- description: Concise deliverable description (1-2 sentences)
- sow_reference: Section or clause reference
- acceptance_criteria: Explicit criteria or null (do not cite documents)
- evidence_required: Documents, artifacts, or sign-offs required as proof (1-2 sentences)
- client_approver: Named client approver or role, or '[UNASSIGNED - TO BE CONFIRMED]'
- submission_target_date: Target submission date (YYYY-MM-DD) if stated
- review_window: Client review window (e.g. '5 business days')
- rejection_rework_path: Rework and resubmission mechanism (1-2 sentences)

DOCUMENTS CONTENT:
{documents_text}
"""

STAKEHOLDERS_PROMPT = """Analyze the provided project documents and extract key delivery stakeholders and decision rights.
Ensure you identify PMO leadership (PMO Lead, Director, PMO), delivery leadership (Delivery Manager, Talent PM, Technical Lead), and customer counterparts (Client Sponsor, Client Approver).

CONSTRAINTS:
1. Extract key delivery stakeholders and leadership roles (maximum 10-12 key stakeholders).
2. Keep decision rights, responsibilities, and escalation summaries concise (1-2 sentences per field).

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

CONSTRAINTS:
1. Extract primary governance communications and meetings (maximum 8-10 key governance events/reports).
2. Keep all descriptions, audiences, formats, and notes concise and direct (1 sentence per field).

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

CONSTRAINTS:
1. Provide concise, direct 1-2 sentence summaries for each commercial guardrail field.
2. Do NOT mention or reference the SOW, contracts, or source documents.

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

CONSTRAINTS:
1. Focus on core delivery roles and essential technical skills (maximum 10 key roles/skills).
2. Keep descriptions and gap notes concise (1-2 sentences).

Extract:
- talent_pm: Named Talent PM or '[UNASSIGNED - TO BE CONFIRMED]'
- delivery_manager: Named Delivery Manager or '[UNASSIGNED - TO BE CONFIRMED]'
- pmo_lead: Named PMO Lead
- required_roles: Roles required to staff delivery (maximum 10 key roles)
- required_skills: Key technical skills (e.g. AWS, Terraform, Python) (maximum 10 skills)
- staffing_gaps: Any identified staffing gaps
- replacement_plan: Protocol for talent replacement

DOCUMENTS CONTENT:
{documents_text}
"""

DECISIONS_PROMPT = """Analyze the provided project documents and extract key baseline decisions already agreed during pre-sales or Readiness (maximum 15 key decisions). Keep descriptions concise, direct, and self-contained without referencing the SOW or other documents.

CONSTRAINTS:
1. Extract maximum 15 key decisions.
2. Keep decision statements and rationales concise and direct (1-2 sentences).

For each decision:
- id: DEC-01, DEC-02...
- decision_text: Concise statement of decision
- decision_owner: Responsible owner
- decision_date: Date if known
- rationale: Concise context or reason for decision (do not cite SOW or documents)
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
