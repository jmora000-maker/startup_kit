"""Prompt templates and system instructions for multi-pass LLM extraction."""

SYSTEM_PROMPT = """You are an expert Toptal PMO Delivery Lead and Startup Specialist.
Your goal is to extract structured project management data from provided project documents, pre-sales decks, and context notes to build the PMO Startup Kit.

DOCUMENT PRECEDENCE & HIERARCHY RULES:
- Documents marked '=== PRIMARY SOURCE OF TRUTH (SOW) ===' represent governing contractual baselines.
- Documents marked '=== SUPPORTING DOCUMENT (FALLBACK CONTEXT ONLY) ===' provide background context (e.g. meeting notes, technical assessments, discussions).
- Apply this precedence hierarchy across ALL fields:
  1. PRIMARY SOW FIRST: Always attempt to source field data from PRIMARY SOURCE OF TRUTH (SOW) documents first.
  2. CONFLICT RESOLUTION: If a SUPPORTING DOCUMENT conflicts with or contradicts a PRIMARY SOW document on any field (e.g. contract type, milestone dates, fees, deliverables, scope), the PRIMARY SOW ALWAYS takes precedence and wins.
  3. GAP-FILLING FALLBACK: If the PRIMARY SOW is silent on an item (e.g. current-state pain points, operational bottlenecks, background context) that is explicitly described in a SUPPORTING DOCUMENT, you MUST extract that information from the SUPPORTING DOCUMENT to fill the gap.
  4. SOURCE TRACEABILITY: Set source_reference.document_name to the exact filename of the document where the extracted fact was found.

STRICT BUSINESS RULES & CONSTRAINTS:
1. NO HALLUCINATION: Extract only factual information present in the input documents.
2. NO SOW OR EXTERNAL DOCUMENT REFERENCES: The consumers of this report DO NOT have access to the Statement of Work (SOW), pre-sales decks, contracts, or source documents. Do NOT reference 'the SOW', 'Statement of Work', 'input documents', 'source documents', 'page numbers', or 'clause numbers' in any extracted text, descriptions, questions, deliverables, milestones, risks, or assumptions. All text must be completely self-contained and document-agnostic.
3. CONCISE & SIMPLIFIED: Keep all field values, summaries, and descriptions short, clear, direct, and concise (1-2 sentences maximum). Simplify the report text so that stakeholders can understand the project baseline instantly without legalistic jargon or redundant phrasing.
4. MISSING ACCEPTANCE CRITERIA: If a deliverable's acceptance criteria are not explicitly specified in the text, set acceptance_criteria to an empty list [].
5. MISSING DATES: If milestone dates are not explicitly stated, set external_date to null (None).
6. SOURCE TRACEABILITY: Every extracted item must include a valid SourceReference with:
   - document_name: exact filename where the information was found
   - clause_or_slide: the section number, heading, or slide number (e.g. "Section 3.2", "Slide 4", "Page 2")
   - confidence_score: floating point score between 0.0 and 1.0 indicating extraction confidence.
7. GOVERNANCE TIERS: Valid tiers are 'Guided', 'Partnered', 'Elevated'. Default to 'Partnered' if not specified.
8. CONTRACT TYPES: Common types include 'Time and Materials' and 'Fixed Bid'.
"""

CHARTER_PROMPT = """Analyze the provided project documents and extract the overall Project Charter, Governance metadata, and Client Problem Statement.

CONSTRAINTS:
- When the primary document is a Statement of Work (or similarly named governing document) with its own cover-page title, extract that title exactly as a single clean string for project_name.
- Never combine it with, append, or parenthesize a second title found in an attached Exhibit, Appendix, or Specification document — an exhibit's heading describes that exhibit, not the engagement.
- Keep the executive summary strictly between 2-3 concise sentences covering project objectives, tech stack, and scope.
- Ensure all text is self-contained and does NOT mention or reference the SOW, contracts, or source documents.

PROBLEM STATEMENT & GAP-FILLING INSTRUCTIONS:
- First check the PRIMARY SOURCE OF TRUTH (SOW) for client problem statements or current-state pain points.
- If the SOW states no problem statement, but SUPPORTING DOCUMENTS describe concrete current-state operational bottlenecks, legacy limitations, or business challenges, extract the problem statement from those supporting documents.
- CRITICAL: Do NOT restate the solution, project purpose, or list contracted deliverables (e.g. do NOT say "Building a Postgres schema and deploying microservices"). Focus exclusively on what is broken, manual, bottlenecked, or inadequate in the client's current state.
- HONEST FALLBACK: If NEITHER the SOW nor any supporting document states an existing problem or current-state limitation, you MUST set problem_statement to null. Do NOT fabricate, infer, or invent a problem statement.

SOLUTION OVERVIEW & SUCCESS CRITERIA SYNTHESIS INSTRUCTIONS:
- solution_overview: A cohesive 2-3 sentence narrative describing the core technical approach, integrated workstreams, and delivery cadence. Must focus on how the solution addresses client needs and delivers business value, using active verbs to explain how the workstreams connect into an integrated capability rather than listing deliverable titles or bullet points.
- success_criteria_summary: A natural, 2-3 sentence narrative framed entirely around customer outcomes and business value: what the client actually receives, can do, or can decide upon completion (e.g., operational visibility, confident modernization decisions, everyday usability, or trusted evidence). Do NOT restate raw internal delivery metrics, acceptance percentage thresholds (e.g., '95% coverage'), milestone counts, or contract review SLAs (e.g., '5-day review'). Focus strictly on the tangible end-state capability and confidence delivered to the client.

Extract:
- project_name: Title of the project or engagement (a single clean title).
- client_name: Name of the client or sponsoring organization.
- governance_tier: 'Guided', 'Partnered', or 'Elevated' (default 'Partnered').
- contract_type: 'Time and Materials' or 'Fixed Bid' (default 'Time and Materials').
- delivery_manager: Named Delivery Manager if mentioned, else null.
- talent_pm: Named Talent Project Manager if mentioned, else null.
- pmo_lead: Named PMO Lead if mentioned, else null.
- executive_summary: A concise 2-3 sentence summary of project objectives, tech stack, and scope. Ensure the summary is self-contained and does NOT mention or reference the SOW or input documents.
- problem_statement: 1-2 concise sentences stating the client's concrete current-state pain point or operational bottleneck. Set to null if not stated in source documents.
- solution_overview: A cohesive 2-3 sentence narrative synthesizing the technical approach, key workstreams, and delivery cadence into an integrated client solution (using active verbs, focused on business value, not a bare list of deliverable titles).
- success_criteria_summary: A natural 2-3 sentence narrative framed around customer outcomes and business value (what the client actually gets or can now do/decide), avoiding raw internal delivery metrics or acceptance percentage thresholds.
- source_reference: Document name, section/slide reference, and confidence score.

DOCUMENTS CONTENT:
{documents_text}
"""

DELIVERABLES_PROMPT = """Analyze the provided project documents and extract key contractual project deliverables.

INSTRUCTIONS:
1. When the SOW presents Work Output as distinct bullet points, table rows, or numbered scope items (e.g. under Milestones or in a Work Output / Acceptance Criteria table), extract EVERY single distinct, separately-bulleted Work Output item as its own separate Deliverable object (strict 1:1 mapping, no consolidation or merging of distinct bullets into single deliverables).
2. For SOWs that do NOT use bulleted or numbered Work Output lists (e.g. narrative prose paragraphs), extract each distinct contractual commitment or deliverable stated in the text without artificially inflating or inventing items, preserving the true granularity stated in the source.
3. For each deliverable, attach its exact paired Acceptance Criteria from the SOW (e.g., from the corresponding row or bullet in the Acceptance Criteria table). Extract each distinct criteria item as its own separate string in a list (e.g. ['Criterion 1', 'Criterion 2']) — do not combine multiple distinct criteria into a single joined string. Ensure every Acceptance Criteria bullet corresponding to a given Work Output bullet is preserved and attached to that bullet's own deliverable — never dropped or reassigned to a different deliverable.
4. Keep descriptions clear, direct, and self-contained (1-2 sentences maximum). Do NOT mention or refer to the SOW or other documents.
5. If explicit acceptance criteria are provided in the text, extract them concisely and directly as a list of distinct strings without referencing documents. If NOT explicitly stated, you MUST set acceptance_criteria to an empty list [].

For each deliverable:
- id: Sequential identifier (e.g., DEL-01, DEL-02, DEL-03...)
- name: Concise title of the deliverable
- description: Clear, concise, and self-contained statement of the deliverable outcome. Do NOT mention or refer to the SOW or other documents.
- owner: Named owner or role if stated, else 'Unassigned'.
- acceptance_criteria: List of distinct explicit acceptance criteria strings if provided in the text (e.g. ['Criterion 1', 'Criterion 2']), or empty list [] if not explicitly stated.
- sow_reference: SOW work item references covered (e.g. story IDs, deliverable numbers, task codes, or synthetic work item codes such as WO-M1-01) if mentioned, else null. Do NOT include section or clause citations here; section/clause locations belong in source_reference.
- source_reference: The source document name, section/clause, and confidence score.

DOCUMENTS CONTENT:
{documents_text}
"""

MILESTONES_PROMPT = """Analyze the provided project documents and extract key delivery milestones, target dates, and phase gates.

CONSTRAINTS:
1. Extract key delivery milestones and phase gates (maximum 15 milestones).
2. Anchor extraction to the SOW's own explicitly enumerated milestones (such as a fee schedule, milestone table, or numbered 'Milestone N' list) when one exists — extract exactly those, not more.
3. Explicitly exclude trigger conditions, prerequisite events, or assumptions that merely describe when a milestone begins or what causes it to start (e.g. 'production go-live, which starts the Hypercare Period') — these are context for an existing milestone, never a separate milestone of their own.
4. When the SOW explicitly states a delivery phase for a milestone — whether in abbreviated form ('P1', 'P2a') or spelled-out word form ('Phase 1', 'Phase 2') — you MUST preserve that phase label at the start of the milestone's description (e.g. 'Phase 2 - LLM Enrichment Layer: ...' or 'P1 Foundation: ...'). Never strip or omit the stated phase name or number.
5. Keep milestone descriptions concise and direct (1 sentence). Do NOT mention or refer to the SOW or other documents.

For each milestone:
- id: Sequential identifier (e.g., M1, M2, M3...)
- description: Concise milestone name or phase completion outcome (preserving any stated 'Phase N' or 'Pn' prefix). Do NOT mention or refer to the SOW or other documents.
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

SCOPE_DECOMPOSITION_PROMPT = """Analyze the provided project documents and deliverables to extract the SOW Work Item Catalogue and preliminary backlog work packages.

INSTRUCTIONS FOR SOW WORK ITEMS:
1. Extract all individual SOW work items (stories, deliverable numbers, work output row items, or contracted scope items) listed in the SOW (e.g. from Section 4 Work Output table, or from Section 2 Activities when there is no Work Output table).
2. For each work item:
   - reference: SOW reference identifier (e.g. 'SOW-01', 'Story 1', 'Deliverable 1.1', or 'Section 3.1').
   - reference_kind: 'Story ID', 'Deliverable number', 'Task or WBS code', 'Section', or 'Synthetic'.
   - title: The EXACT descriptive title or heading as written in the SOW's Work Output table, or from its activity text when the SOW has no Work Output table. If no title is found, leave it empty.
   - phase: Delivery phase code (e.g. 'P1', 'P2a', 'P2b', 'P3') if stated or grouped under a phase.
   - owner: 'Toptal' or 'Client' (default 'Toptal' unless explicitly client-owned).
   - type: 'Build', 'Test', 'Integration', 'Certification', 'Analysis', or 'Documentation'.
   - deliverable_id: Matching parent deliverable ID from the deliverables list below if applicable.

INSTRUCTIONS FOR WORK PACKAGES:
Decompose the deliverables into preliminary backlog work packages (e.g. WP-01, WP-02...).
- id: e.g. WP-01, WP-02
- parent_deliverable_id: matching deliverable ID from the deliverables list below
- title: Concise work package title (e.g. '{{reference}}: {{title}}')
- description: Brief description of tasks (1-2 sentences)
- preliminary_sequence: Integer sequence order (1, 2, 3...)
- owner: Role or named owner if known, else '[UNASSIGNED - TO BE CONFIRMED]'
- dependency_references: List of prerequisite IDs or descriptions
- linked_milestones: Associated milestone IDs (e.g. M1)
- linked_acceptance_items: Associated acceptance criteria references
- uncertain_scope: Boolean flag indicating if scope is unconfirmed
- sow_reference: SOW work item reference(s)

DELIVERABLES LIST:
{deliverables_text}

DOCUMENTS CONTENT:
{documents_text}
"""

ACCEPTANCE_PROCESS_PROMPT = """Analyze the deliverables in the provided documents and extract explicit acceptance process details. Keep descriptions concise, direct, and self-contained without referencing the SOW or other documents.

CONSTRAINTS:
1. Extract acceptance process details for each distinct contractual deliverable identified in the SOW (matching the 1:1 granularity of the SOW's Work Output and Acceptance Criteria).
2. Keep all text fields (description, acceptance criteria, evidence, rework path) brief and direct (1-2 sentences maximum).
3. Do NOT cite or reference the SOW, contracts, or source documents in descriptions or criteria.
4. ACCURACY ON TIMELINES: Distinguish client decision turnaround (e.g. client turnaround on decision or feedback within 3 business days) from supplier rework turnaround. Do NOT conflate client decision turnaround with supplier rework or resubmission windows. If a specific rework/remediation window for the supplier is not explicitly stated in the source text, state the remedy process directly (e.g. remediation/rework upon notice of non-conformance) without inventing a supplier turnaround timeframe.

For each deliverable:
- id: Deliverable ID (DEL-01, etc.)
- name: Deliverable title
- description: Concise deliverable description (1-2 sentences)
- sow_reference: SOW work item reference (e.g. story ID, deliverable number, task code) if mentioned, else null. Do NOT include section or clause citations.
- acceptance_criteria: List of distinct explicit criteria strings or empty list [] (do not cite documents)
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
