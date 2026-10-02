# Revision 10 final report: deck layout, stricter traceability, Your Project Kit slide

Spec: `spec\PMO_Startup_Kit_Consolidated_Spec.md` at 30f4cc2 (not modified). Oracles (`tests\oracles\`) and approved snapshots (`tests\snapshots\`) not modified. No LLM calls, no re-recording, no snapshot updates applied.

## 1. Outcome

All seven steps are done and committed. The checks were strengthened first and shown to fail on the Rev 9 deck for every Appendix L finding they were meant to catch; the Workbook defect was then fixed; the deck was rebuilt (content, layout, slide 7); the review aid was added.

Not fully met or interpreted (details in section 8): steps 3 to 5 are one commit; the Kit RAID Log table does not display Trigger / Early Warning, so INV-30 compares that field at model level; the DECK-05 boundary rule and the 15-word guide conflict for some text and DECK-05 won; the K.1 and DECK-21 text insets differ and DECK-21 was used; **LibreOffice is not installed here, so no slide was rendered to an image and the layout has been verified by the DECK-21 fit estimate and INV-32 only.**

## 2. Baseline and plan

Pre-check: `git status` was clean (`nothing to commit, working tree clean`).

Baseline `pytest -q` summary line: `5 failed, 366 passed in 105.37s (0:01:45)`. The 5 failures were the snapshot tests, which already failed because the Rev 9 deck snapshots had been proposed but not promoted.

Plan followed: (1) harden INV-26 and add INV-30 to INV-32 with broken-input tests, run them against the regenerated Rev 9 deck; (2) fix the Workbook (RAID-09); (3) deck content; (4) deck layout; (5) slide 7 and structure; (6) `render_deck`; then tests, proposed snapshots, this report.

## 3. Commits

| Commit | Message |
| --- | --- |
| 444e34b | Rev 10 step 1: harden INV-26, add INV-30 to INV-32 |
| f3dc6e7 | Rev 10 step 2: Workbook RAID rows carry the Kit RAID fields (RAID-09, INV-30) |
| 79d69e8 | Rev 10 steps 3 to 5: deck content, layout, and Your Project Kit slide |
| 27b14de | Rev 10 step 6: render_deck review aid (DECK-23), README (DECK-18) |
| e82037b | Proposed snapshots for Rev 10 |
| 9cf0e6e | Rev 10 tests: slide 6 working rhythm equals the Kit communications items (K.4) |
| (this file) | Rev 10 final report |

Steps 3, 4, and 5 are in one commit because the DeckModel, the builder, and the writer were rewritten together (the model now carries traced runs, sizes, and shape names that the writer renders). They cannot be built or tested separately. The step 1 and step 2 commits left the Rev 9 deck tests red, as intended: those tests had asserted that the defective deck passed.

## 4. Step 1: the checks failed on the Rev 9 deck

The Rev 9 ARC deck was regenerated with `python main.py --llm-cache replay --start-date 2026-10-05 --slides --non-interactive` (code unchanged at that point) and `python -m src.tools.check_artifacts` was run on it. Result: exit 1, 298 violations (INV-26: 169, INV-30: 7, INV-31: 42, INV-32: 80).

| Appendix L finding | Invariant that failed | Evidence in the output below |
| --- | --- | --- |
| L1 crowded cards, tiny fonts | INV-32 | `no explicit font size`, `font 9.5 pt is below the 10 pt minimum`, `not inset 0.2 in from its card`, `shapes 'TextBox 4' and 'Table 5' overlap` |
| L4 overflow row runs off the slide | INV-32 | `Slide 4 shape 'Table 5' lies outside the content area (x 4.81-12.50, y 1.70-9.14 ...)`; slide 3 table to y 7.02 |
| L5 ellipses and mid-phrase cuts | INV-31 and INV-26 | `contains an ellipsis`, `has an unbalanced bracket ...`, `ends at a comma` |
| L6 shortened names | INV-31 and INV-26 | `shows a shortened name 'Backend Integration/Load Tests and Performance Engineering' for '...Spike'`, `'Production Smoke Tests and 48-Hour Defect' for '...Watch'` |
| L8 empty Response | INV-30 | `RAID-01 (RSK-01) Mitigation / Response is '' but the Kit RAID Log says ...` (7 rows) |
| L9 filler, doubled punctuation, no manifest entries | INV-31 and INV-26 | `uses evaluative filler 'proactive'`, `'Active alignment'`, `doubled punctuation '..'`, `talking point has no trace manifest entry` |
| L10 invented keys | INV-26 | `key 'Title Row 3' not found`, `key 'M1 Step 1' not found`, talking points without entries |

No finding passed, so no check needed to be reworked. (L7, the wrong slide 4 steps, also surfaces as INV-26 invented keys `M1 Step n`; L2 and L3 are covered by the new style and layout tests; L11 is this process.)

Raw `check_artifacts` output (also committed as `reports\rev10_step1_failing_check_output.txt`):

```text
FAILED: Found 298 invariant violation(s) in 'output\_rev9':
  - INV-26 [Deck]: TraceRef artifact 'Project Delivery Workbook' must be 'Workbook' (DECK-04)
  - INV-26 [Deck]: TraceRef artifact 'Startup Kit' must be 'Kit' (DECK-04)
  - INV-26 [Deck]: 120 manifest entries lack a shape name (DECK-06), for example slide 1 element 'Title'
  - INV-26 [Deck]: Slide 1 element 'Title': TraceRef (Kit / Project Charter / Project Name / Project Name) does not resolve: Kit section 'Project Charter' not found
  - INV-26 [Deck]: Slide 1 element 'Client Sponsor': TraceRef (Kit / Project Charter / Client Sponsor / Client Sponsor) does not resolve: Kit section 'Project Charter' not found
  - INV-26 [Deck]: Slide 1 element 'Start Date': TraceRef (Workbook / Project Schedule / Title Row 3 / Start Date) does not resolve: key 'Title Row 3' not found in Workbook sheet 'Project Schedule'
  - INV-26 [Deck]: Slide 2 element 'Key Fact: Client Sponsor': TraceRef (Kit / Project Charter / Client Sponsor / Client Sponsor) does not resolve: Kit section 'Project Charter' not found
  - INV-26 [Deck]: Slide 2 element 'Key Fact: Contract Type': TraceRef (Kit / Project Charter / Contract Type / Contract Type) does not resolve: Kit section 'Project Charter' not found
  - INV-26 [Deck]: Slide 2 element 'Key Fact: Governance Tier': TraceRef (Kit / Project Charter / Governance Tier / Governance Tier) does not resolve: Kit section 'Project Charter' not found
  - INV-26 [Deck]: Slide 2 element 'Key Fact: Start Date': TraceRef (Workbook / Project Schedule / Title Row 3 / Start Date) does not resolve: key 'Title Row 3' not found in Workbook sheet 'Project Schedule'
  - INV-26 [Deck]: Slide 2 element 'Key Fact: Talent PM': TraceRef (Kit / Project Charter / Talent PM / Talent PM) does not resolve: Kit section 'Project Charter' not found
  - INV-26 [Deck]: Slide 2 element 'Key Fact: Delivery Manager': TraceRef (Kit / Project Charter / Delivery Manager / Delivery Manager) does not resolve: Kit section 'Project Charter' not found
  - INV-26 [Deck]: Slide 2 element 'Key Fact: PMO Lead': TraceRef (Kit / Project Charter / PMO Lead / PMO Lead) does not resolve: Kit section 'Project Charter' not found
  - INV-26 [Deck]: Slide 2 element 'Project Purpose': TraceRef (Kit / Project Charter / Project Purpose / Project Purpose) does not resolve: Kit section 'Project Charter' not found
  - INV-26 [Deck]: Slide 2 element 'Delivery Model': TraceRef (Kit / Project Charter / Delivery Model / Delivery Model) does not resolve: Kit section 'Project Charter' not found
  - INV-26 [Deck]: Slide 2 element 'Escalation Path': TraceRef (Kit / Project Charter / Escalation Path / Escalation Path) does not resolve: Kit section 'Project Charter' not found
  - INV-26 [Deck]: Slide 2 element 'Phase: P1 Foundation': TraceRef (Workbook / Project Schedule / P1 Foundation / Workstream) does not resolve: key 'P1 Foundation' not found in Workbook sheet 'Project Schedule'
  - INV-26 [Deck]: Slide 2 element 'Phase: P2a Services and Data': TraceRef (Workbook / Project Schedule / P2a Services and Data / Workstream) does not resolve: key 'P2a Services and Data' not found in Workbook sheet 'Project Schedule'
  - INV-26 [Deck]: Slide 2 element 'Phase: P2b Application Surface': TraceRef (Workbook / Project Schedule / P2b Application Surface / Workstream) does not resolve: key 'P2b Application Surface' not found in Workbook sheet 'Project Schedule'
  - INV-26 [Deck]: Slide 2 element 'Phase: P3 Launch': TraceRef (Workbook / Project Schedule / P3 Launch / Workstream) does not resolve: key 'P3 Launch' not found in Workbook sheet 'Project Schedule'
  - INV-26 [Deck]: Slide 2 element 'Exclusion 1': TraceRef (Kit / SOW Interpretation Summary / Exclusion 1 / Out of Scope) does not resolve: key 'Exclusion 1' not found in Kit section 'SOW Interpretation Summary'
  - INV-26 [Deck]: Slide 2 element 'Exclusion 2': TraceRef (Kit / SOW Interpretation Summary / Exclusion 2 / Out of Scope) does not resolve: key 'Exclusion 2' not found in Kit section 'SOW Interpretation Summary'
  - INV-26 [Deck]: Slide 2 element 'Exclusion 3': TraceRef (Kit / SOW Interpretation Summary / Exclusion 3 / Out of Scope) does not resolve: key 'Exclusion 3' not found in Kit section 'SOW Interpretation Summary'
  - INV-26 [Deck]: Slide 2 element 'Exclusion 4': TraceRef (Kit / SOW Interpretation Summary / Exclusion 4 / Out of Scope) does not resolve: key 'Exclusion 4' not found in Kit section 'SOW Interpretation Summary'
  - INV-26 [Deck]: Slide 3 element 'R1C2': displayed value 'M1: P1 Foundation accepted' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 3 element 'R1C3': displayed value '2026-10-05 – 2026-11-13' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 3 element 'R1C4': displayed value 'DEL-01 Micro-Frontend Shell and Azure AD/MSAL Authentication DEL-02 Shell and Authentication E2E Test Harness DEL-03 Pipeline Quality Gates and Deployment Smoke DEL-04 Authentication Negative-Test Suite and Security Scan DEL-05 Snowflake Data Model and Data Governance' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 3 element 'R2C2': displayed value 'M2: P2a Services and Data accepted' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 3 element 'R2C3': displayed value '2026-11-16 – 2027-01-22' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 3 element 'R2C4': displayed value 'DEL-06 FastAPI Search/Detail Endpoints and Asynchronous Query DEL-07 Backend Integration/Load Tests and Performance Engineering DEL-08 OneGWAS Direct-Write Integration and Test Suite DEL-09 Data Ingestion and Migration Validation DEL-10 PubMed Extraction and Trait Taxonomy Validation' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 3 element 'R3C2': displayed value 'M3: P2b Application Surface accepted' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 3 element 'R3C3': displayed value '2027-01-25 – 2027-02-26' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 3 element 'R3C4': displayed value 'DEL-11 ARC Faceted Search DEL-12 Haplotype Search, Visualization and API DEL-13 Nomenclature Service DEL-14 P2b Test Suites (Frontend, Haplotype, Nomenclature)' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 3 element 'R4C2': displayed value 'M4: P3 Launch accepted' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 3 element 'R4C3': displayed value '2027-03-01 – 2027-04-02' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 3 element 'R4C4': displayed value 'DEL-15 Launch Test Suites and Test Data/Fixtures DEL-16 UAT Execution and Pre-Launch Hardening DEL-17 Production Smoke Tests and 48-Hour Defect DEL-18 MTA Store Parity and Usage-Zero Confirmation DEL-19 Training Materials and User Documentation' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 4 element 'Acceptance Step 1': displayed value 'Confirm: Client provides design system access (code library, tokens, design files, guidelines, named contact) by the...' contains an ellipsis (DECK-05)
  - INV-26 [Deck]: Slide 4 element 'Acceptance Step 1': TraceRef (Workbook / WBS / M1 Step 1 / Task Name) does not resolve: key 'M1 Step 1' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'Acceptance Step 2': TraceRef (Workbook / WBS / M1 Step 2 / Task Name) does not resolve: key 'M1 Step 2' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'Acceptance Step 3': TraceRef (Workbook / WBS / M1 Step 3 / Task Name) does not resolve: key 'M1 Step 3' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'Acceptance Step 4': TraceRef (Workbook / WBS / M1 Step 4 / Task Name) does not resolve: key 'M1 Step 4' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'Acceptance Step 5': TraceRef (Workbook / WBS / M1 Step 5 / Task Name) does not resolve: key 'M1 Step 5' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'Acceptance Step 6': displayed value 'Build HS-4762: Micro-frontend shell with global navigation, routing, built with Client's design system and sharing...' contains an ellipsis (DECK-05)
  - INV-26 [Deck]: Slide 4 element 'Acceptance Step 6': TraceRef (Workbook / WBS / M1 Step 6 / Task Name) does not resolve: key 'M1 Step 6' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'Review Window': displayed value 'Not specified; reviewed at the Milestone Acceptance Review' is cut mid-phrase (not at a sentence or clause boundary) (DECK-05)
  - INV-26 [Deck]: Slide 4 element 'R1C3': TraceRef (Workbook / WBS / DEL-01 / Milestone ID) does not resolve: key 'DEL-01' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'R2C3': TraceRef (Workbook / WBS / DEL-02 / Milestone ID) does not resolve: key 'DEL-02' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'R3C3': TraceRef (Workbook / WBS / DEL-03 / Milestone ID) does not resolve: key 'DEL-03' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'R4C3': TraceRef (Workbook / WBS / DEL-04 / Milestone ID) does not resolve: key 'DEL-04' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'R5C2': displayed value 'Targets are referential integrity 100%, representative query patterns validated, controls audited' is cut mid-phrase (not at a sentence or clause boundary) (DECK-05)
  - INV-26 [Deck]: Slide 4 element 'R5C3': TraceRef (Workbook / WBS / DEL-05 / Milestone ID) does not resolve: key 'DEL-05' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'R6C3': TraceRef (Workbook / WBS / DEL-06 / Milestone ID) does not resolve: key 'DEL-06' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'R7C3': TraceRef (Workbook / WBS / DEL-07 / Milestone ID) does not resolve: key 'DEL-07' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'R8C3': TraceRef (Workbook / WBS / DEL-08 / Milestone ID) does not resolve: key 'DEL-08' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'R9C3': TraceRef (Workbook / WBS / DEL-09 / Milestone ID) does not resolve: key 'DEL-09' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'R10C3': TraceRef (Workbook / WBS / DEL-10 / Milestone ID) does not resolve: key 'DEL-10' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'R11C3': TraceRef (Workbook / WBS / DEL-11 / Milestone ID) does not resolve: key 'DEL-11' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'R12C3': TraceRef (Workbook / WBS / DEL-12 / Milestone ID) does not resolve: key 'DEL-12' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 4 element 'R13C3': TraceRef (Workbook / WBS / DEL-13 / Milestone ID) does not resolve: key 'DEL-13' not found in Workbook sheet 'WBS'
  - INV-26 [Deck]: Slide 5 element 'R1C1': displayed value 'RAID-01 (RSK-01)' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 5 element 'R1C2': displayed value 'Latency and render-time targets may be missed because they depend on Client-owned components (Snowflake sizing,' leaves an unbalanced bracket, parenthesis, or quotation mark (DECK-05)
  - INV-26 [Deck]: Slide 5 element 'R1C2': displayed value 'Latency and render-time targets may be missed because they depend on Client-owned components (Snowflake sizing,' is cut at a comma (DECK-05)
  - INV-26 [Deck]: Slide 5 element 'R1C2': displayed value 'Latency and render-time targets may be missed because they depend on Client-owned components (Snowflake sizing,' leaves an unbalanced bracket, parenthesis, or quotation mark (DECK-05)
  - INV-26 [Deck]: Slide 5 element 'R1C3': TraceRef (Workbook / RAID Log / RAID-01 / Probability and Impact) does not resolve: field 'Probability and Impact' not found for key 'RAID-01' in Workbook sheet 'RAID Log'
  - INV-26 [Deck]: Slide 5 element 'R2C1': displayed value 'RAID-02 (RSK-02)' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 5 element 'R2C2': displayed value 'Client-built components may fail certification targets (e.g., PubMed precision ≥85%, GWAS Atlas coverage ≥90%' leaves an unbalanced bracket, parenthesis, or quotation mark (DECK-05)
  - INV-26 [Deck]: Slide 5 element 'R2C2': displayed value 'Client-built components may fail certification targets (e.g., PubMed precision ≥85%, GWAS Atlas coverage ≥90%' leaves an unbalanced bracket, parenthesis, or quotation mark (DECK-05)
  - INV-26 [Deck]: Slide 5 element 'R2C3': TraceRef (Workbook / RAID Log / RAID-02 / Probability and Impact) does not resolve: field 'Probability and Impact' not found for key 'RAID-02' in Workbook sheet 'RAID Log'
  - INV-26 [Deck]: Slide 5 element 'R3C1': displayed value 'RAID-05 (RSK-05)' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 5 element 'R3C3': TraceRef (Workbook / RAID Log / RAID-05 / Probability and Impact) does not resolve: field 'Probability and Impact' not found for key 'RAID-05' in Workbook sheet 'RAID Log'
  - INV-26 [Deck]: Slide 5 element 'R4C1': displayed value 'RAID-07 (ISS-01)' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 5 element 'R4C2': displayed value 'The number of ARC-specific design system components included in the estimate is still undefined ([N]),' is cut at a comma (DECK-05)
  - INV-26 [Deck]: Slide 5 element 'R4C2': displayed value 'The number of ARC-specific design system components included in the estimate is still undefined ([N]),' ends at a comma (DECK-05)
  - INV-26 [Deck]: Slide 5 element 'R4C3': TraceRef (Workbook / RAID Log / RAID-07 / Probability and Impact) does not resolve: field 'Probability and Impact' not found for key 'RAID-07' in Workbook sheet 'RAID Log'
  - INV-26 [Deck]: Slide 6 element 'Client Role 1': TraceRef (Kit / Stakeholder and Responsibility Model / Client Contact (designated) / Role and Decision Rights) does not resolve: field 'Role and Decision Rights' not found for key 'Client Contact (designated)' in Kit section 'Stakeholder and Responsibility Model'
  - INV-26 [Deck]: Slide 6 element 'Client Role 2': TraceRef (Kit / Stakeholder and Responsibility Model / Client Designated Milestone Approvers / Role and Decision Rights) does not resolve: field 'Role and Decision Rights' not found for key 'Client Designated Milestone Approvers' in Kit section 'Stakeholder and Responsibility Model'
  - INV-26 [Deck]: Slide 6 element 'Client Role 3': displayed value 'Client Platform and Data Tier Owners (Client Delivery Counterpart): Own the platform layer (Terraform' leaves an unbalanced bracket, parenthesis, or quotation mark (DECK-05)
  - INV-26 [Deck]: Slide 6 element 'Client Role 3': TraceRef (Kit / Stakeholder and Responsibility Model / Client Platform and Data Tier Owners / Role and Decision Rights) does not resolve: field 'Role and Decision Rights' not found for key 'Client Platform and Data Tier Owners' in Kit section 'Stakeholder and Responsibility Model'
  - INV-26 [Deck]: Slide 6 element 'Client Role 4': TraceRef (Kit / Stakeholder and Responsibility Model / Client Domain Experts and Domain Users / Role and Decision Rights) does not resolve: field 'Role and Decision Rights' not found for key 'Client Domain Experts and Domain Users' in Kit section 'Stakeholder and Responsibility Model'
  - INV-26 [Deck]: Slide 6 element 'Client Role 5': displayed value 'Client Scientist UAT Groups (UAT Participants): Run UAT after each milestone (limited to two' leaves an unbalanced bracket, parenthesis, or quotation mark (DECK-05)
  - INV-26 [Deck]: Slide 6 element 'Client Role 5': TraceRef (Kit / Stakeholder and Responsibility Model / Client Scientist UAT Groups / Role and Decision Rights) does not resolve: field 'Role and Decision Rights' not found for key 'Client Scientist UAT Groups' in Kit section 'Stakeholder and Responsibility Model'
  - INV-26 [Deck]: Slide 6 element 'Working Rhythm 1': TraceRef (Kit / Communications and Reporting Plan / Kickoff Call / Name and Cadence) does not resolve: key 'Kickoff Call' not found in Kit section 'Communications and Reporting Plan'
  - INV-26 [Deck]: Slide 6 element 'Working Rhythm 2': TraceRef (Kit / Communications and Reporting Plan / Daily Standups / Name and Cadence) does not resolve: key 'Daily Standups' not found in Kit section 'Communications and Reporting Plan'
  - INV-26 [Deck]: Slide 6 element 'Working Rhythm 3': TraceRef (Kit / Communications and Reporting Plan / Biweekly Sprint Demo / Name and Cadence) does not resolve: key 'Biweekly Sprint Demo' not found in Kit section 'Communications and Reporting Plan'
  - INV-26 [Deck]: Slide 6 element 'Working Rhythm 4': TraceRef (Kit / Communications and Reporting Plan / Weekly Status Meeting / Name and Cadence) does not resolve: key 'Weekly Status Meeting' not found in Kit section 'Communications and Reporting Plan'
  - INV-26 [Deck]: Slide 6 element 'Working Rhythm 5': TraceRef (Kit / Communications and Reporting Plan / Weekly Status Report / Name and Cadence) does not resolve: key 'Weekly Status Report' not found in Kit section 'Communications and Reporting Plan'
  - INV-26 [Deck]: Slide 6 element 'Working Rhythm 6': TraceRef (Kit / Communications and Reporting Plan / Milestone Acceptance Review / Name and Cadence) does not resolve: key 'Milestone Acceptance Review' not found in Kit section 'Communications and Reporting Plan'
  - INV-26 [Deck]: Slide 6 element 'Working Rhythm 7': TraceRef (Kit / Communications and Reporting Plan / Ad-Hoc Working Sessions / Name and Cadence) does not resolve: key 'Ad-Hoc Working Sessions' not found in Kit section 'Communications and Reporting Plan'
  - INV-26 [Deck]: Slide 6 element 'Client Prerequisite 1': displayed value 'M1: Client provides design system access (code library, tokens, design files, guidelines' leaves an unbalanced bracket, parenthesis, or quotation mark (DECK-05)
  - INV-26 [Deck]: Slide 6 element 'Client Prerequisite 1': displayed value 'M1: Client provides design system access (code library, tokens, design files, guidelines' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 6 element 'Client Prerequisite 2': displayed value 'M2: Client completes Snowflake data model story (HS-4781) before P2a begins' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 6 element 'Client Prerequisite 3': displayed value 'M3: Client provides UI/UX designs for the Milestone 3 screens by the Start' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 6 element 'Client Prerequisite 4': displayed value 'M4: Client scientist UAT groups available; Client maintains staging and production environments' is not the source text or a prefix of it (DECK-05)
  - INV-26 [Deck]: Slide 2 shape 'Table 5' text has no TraceRef: 'Client Sponsor'
  - INV-26 [Deck]: Slide 2 shape 'Table 5' text has no TraceRef: 'Contract Type'
  - INV-26 [Deck]: Slide 2 shape 'Table 5' text has no TraceRef: 'Governance Tier'
  - INV-26 [Deck]: Slide 2 shape 'Table 5' text has no TraceRef: 'Start Date'
  - INV-26 [Deck]: Slide 2 shape 'Table 5' text has no TraceRef: 'Talent PM'
  - INV-26 [Deck]: Slide 2 shape 'Table 5' text has no TraceRef: 'Delivery Manager'
  - INV-26 [Deck]: Slide 2 shape 'Table 5' text has no TraceRef: 'PMO Lead'
  - INV-26 [Deck]: Slide 2 shape 'TextBox 7' text has no TraceRef: 'Purpose and delivery model'
  - INV-26 [Deck]: Slide 2 shape 'TextBox 7' text has no TraceRef: 'Project Purpose'
  - INV-26 [Deck]: Slide 2 shape 'TextBox 7' text has no TraceRef: 'Delivery Model & Governance'
  - INV-26 [Deck]: Slide 2 shape 'TextBox 7' text has no TraceRef: 'Escalation Path'
  - INV-26 [Deck]: Slide 2 shape 'TextBox 9' text has no TraceRef: 'Phases and boundaries'
  - INV-26 [Deck]: Slide 2 shape 'TextBox 9' text has no TraceRef: 'Delivery Phases'
  - INV-26 [Deck]: Slide 2 shape 'TextBox 9' text has no TraceRef: 'Out of Scope'
  - INV-26 [Deck]: Slide 2 shape 'TextBox 9' text has no TraceRef: '• +4 more (see Startup Kit)'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-01 Micro-Frontend Shell and Azure AD/MSAL Authentication'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-02 Shell and Authentication E2E Test Harness'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-03 Pipeline Quality Gates and Deployment Smoke'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-04 Authentication Negative-Test Suite and Security Scan'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-05 Snowflake Data Model and Data Governance'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-06 FastAPI Search/Detail Endpoints and Asynchronous Query'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-07 Backend Integration/Load Tests and Performance Engineering'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-08 OneGWAS Direct-Write Integration and Test Suite'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-09 Data Ingestion and Migration Validation'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-10 PubMed Extraction and Trait Taxonomy Validation'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-11 ARC Faceted Search'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-12 Haplotype Search, Visualization and API'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-13 Nomenclature Service'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-14 P2b Test Suites (Frontend, Haplotype, Nomenclature)'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-15 Launch Test Suites and Test Data/Fixtures'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-16 UAT Execution and Pre-Launch Hardening'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-17 Production Smoke Tests and 48-Hour Defect'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-18 MTA Store Parity and Usage-Zero Confirmation'
  - INV-26 [Deck]: Slide 3 shape 'Table 3' text has no TraceRef: 'DEL-19 Training Materials and User Documentation'
  - INV-26 [Deck]: Slide 4 shape 'TextBox 4' text has no TraceRef: 'Milestone Acceptance Process'
  - INV-26 [Deck]: Slide 4 shape 'TextBox 4' text has no TraceRef: '1. Confirm: Client provides design system access (code library, tokens, design files, guidelines, named contact) by the...'
  - INV-26 [Deck]: Slide 4 shape 'TextBox 4' text has no TraceRef: '2. Confirm: Client IdP team available for Azure AD / MSAL authentication'
  - INV-26 [Deck]: Slide 4 shape 'TextBox 4' text has no TraceRef: '3. Confirm: Client-owned stories and code dependencies completed before related Toptal work begins'
  - INV-26 [Deck]: Slide 4 shape 'TextBox 4' text has no TraceRef: '4. Confirm: Coding and delivery documentation standards provided on or before the start date'
  - INV-26 [Deck]: Slide 4 shape 'TextBox 4' text has no TraceRef: '5. Refine stories and acceptance criteria'
  - INV-26 [Deck]: Slide 4 shape 'TextBox 4' text has no TraceRef: '6. Build HS-4762: Micro-frontend shell with global navigation, routing, built with Client's design system and sharing...'
  - INV-26 [Deck]: Slide 4 shape 'TextBox 4' text has no TraceRef: 'Governance Parameters'
  - INV-26 [Deck]: Slide 4 shape 'TextBox 4' text has no TraceRef: 'Review Window: Not specified; reviewed at the Milestone Acceptance Review'
  - INV-26 [Deck]: Slide 4 shape 'TextBox 4' text has no TraceRef: 'Client Approver: Client's designated Milestone Sign-Off approver (name not specified)'
  - INV-26 [Deck]: Slide 4 shape 'Table 5' text has no TraceRef: '+6 more: DEL-14, DEL-15, DEL-16, DEL-17, DEL-18, DEL-19 (see Startup Kit · Deliverables and Acceptance Matrix)'
  - INV-26 [Deck]: Slide 6 shape 'TextBox 4' text has no TraceRef: 'Client roles and approvers'
  - INV-26 [Deck]: Slide 6 shape 'TextBox 4' text has no TraceRef: '• +1 more (see Startup Kit)'
  - INV-26 [Deck]: Slide 6 shape 'TextBox 8' text has no TraceRef: 'What we need from the client'
  - INV-26 [Deck]: Slide 3 table 'Table 3' R1C3 shows a shortened name 'Pipeline Quality Gates and Deployment Smoke' for 'Pipeline Quality Gates and Deployment Smoke Checks' (DECK-05)
  - INV-26 [Deck]: Slide 3 table 'Table 3' R1C3 shows a shortened name 'Snowflake Data Model and Data Governance' for 'Snowflake Data Model and Data Governance Validation' (DECK-05)
  - INV-26 [Deck]: Slide 3 table 'Table 3' R2C3 shows a shortened name 'FastAPI Search/Detail Endpoints and Asynchronous Query' for 'FastAPI Search/Detail Endpoints and Asynchronous Query Processing' (DECK-05)
  - INV-26 [Deck]: Slide 3 table 'Table 3' R2C3 shows a shortened name 'Backend Integration/Load Tests and Performance Engineering' for 'Backend Integration/Load Tests and Performance Engineering Spike' (DECK-05)
  - INV-26 [Deck]: Slide 3 table 'Table 3' R4C3 shows a shortened name 'Production Smoke Tests and 48-Hour Defect' for 'Production Smoke Tests and 48-Hour Defect Watch' (DECK-05)
  - INV-26 [Deck]: Slide 3 table 'Table 3' R4C3 shows a shortened name 'MTA Store Parity and Usage-Zero Confirmation' for 'MTA Store Parity and Usage-Zero Confirmation Report' (DECK-05)
  - INV-26 [Deck]: Slide 4 shape 'TextBox 4' shows a shortened name 'Milestone Acceptance' for 'Milestone Acceptance Review' (DECK-05)
  - INV-26 [Deck]: Slide 2 talking point has no trace manifest entry (DECK-09): 'Project operates under Fixed Bid contract terms and Partnered governance.'
  - INV-26 [Deck]: Slide 2 talking point has no trace manifest entry (DECK-09): 'Delivery leadership: PMO Lead To be confirmed, Delivery Manager To be confirmed, Talent PM To be confirmed.'
  - INV-26 [Deck]: Slide 2 talking point has no trace manifest entry (DECK-09): 'Purpose: Build part of the ARC application and automate its QA testing so ARC can launch as one application within the client's larger genomics platform..'
  - INV-26 [Deck]: Slide 2 talking point has no trace manifest entry (DECK-09): 'Escalation path: Talent PM / Delivery Manager -> PMO Lead -> Director, PMO.'
  - INV-26 [Deck]: Slide 2 talking point has no trace manifest entry (DECK-09): 'Delivery spans 4 phases from 2026-10-05 to 2027-04-02.'
  - INV-26 [Deck]: Slide 3 talking point has no trace manifest entry (DECK-09): 'The project runs in 4 phases, from 2026-10-05 to 2027-04-02.'
  - INV-26 [Deck]: Slide 3 talking point has no trace manifest entry (DECK-09): 'Delivery commits to 4 milestones across 4 workstreams.'
  - INV-26 [Deck]: Slide 3 talking point has no trace manifest entry (DECK-09): 'All 19 deliverables are mapped to baseline milestone dates.'
  - INV-26 [Deck]: Slide 3 talking point has no trace manifest entry (DECK-09): 'Date basis: SOW estimate, weeks 1–6.'
  - INV-26 [Deck]: Slide 4 talking point has no trace manifest entry (DECK-09): 'Acceptance is conducted at milestone level following defined quality review gates.'
  - INV-26 [Deck]: Slide 4 talking point has no trace manifest entry (DECK-09): 'Milestone review window is Not specified; reviewed at the Milestone Acceptance Review with client approver Client's designated Milestone Sign-Off approver (name not specified).'
  - INV-26 [Deck]: Slide 4 talking point has no trace manifest entry (DECK-09): 'All 19 deliverable acceptance criteria must be verified with required completion evidence.'
  - INV-26 [Deck]: Slide 4 talking point has no trace manifest entry (DECK-09): 'Submissions follow standard verification and rework remediation workflows.'
  - INV-26 [Deck]: Slide 5 talking point has no trace manifest entry (DECK-09): 'Active RAID tracking monitors 4 items rated High severity.'
  - INV-26 [Deck]: Slide 5 talking point has no trace manifest entry (DECK-09): 'First priority risk is RAID-01: Latency and render-time targets may be missed because they depend.'
  - INV-26 [Deck]: Slide 5 talking point has no trace manifest entry (DECK-09): 'Mitigations and proactive response ownership are assigned across delivery phases.'
  - INV-26 [Deck]: Slide 5 talking point has no trace manifest entry (DECK-09): 'New risks or issues should be raised via the delivery escalation path.'
  - INV-26 [Deck]: Slide 6 talking point has no trace manifest entry (DECK-09): 'Engagement governance establishes regular cadence with 6 client stakeholders.'
  - INV-26 [Deck]: Slide 6 talking point has no trace manifest entry (DECK-09): 'Communications rhythm includes 7 scheduled governance touchpoints.'
  - INV-26 [Deck]: Slide 6 talking point has no trace manifest entry (DECK-09): 'First client prerequisite is required by M1: Client provides design system access (code library.'
  - INV-26 [Deck]: Slide 6 talking point has no trace manifest entry (DECK-09): 'Active alignment ensures clear decision rights and rapid resolution of open items.'
  - INV-31 [Deck]: Slide 2 speaker notes has doubled punctuation '..': '• Purpose: Build part of the ARC application and automate its QA testing so ARC can launch as one application within the client's larger genomics platform..'
  - INV-31 [Deck]: Slide 3 table 'Table 3' R1C3 shows a shortened name 'Pipeline Quality Gates and Deployment Smoke' for 'Pipeline Quality Gates and Deployment Smoke Checks'
  - INV-31 [Deck]: Slide 3 table 'Table 3' R1C3 shows a shortened name 'Snowflake Data Model and Data Governance' for 'Snowflake Data Model and Data Governance Validation'
  - INV-31 [Deck]: Slide 3 table 'Table 3' R2C3 shows a shortened name 'FastAPI Search/Detail Endpoints and Asynchronous Query' for 'FastAPI Search/Detail Endpoints and Asynchronous Query Processing'
  - INV-31 [Deck]: Slide 3 table 'Table 3' R2C3 shows a shortened name 'Backend Integration/Load Tests and Performance Engineering' for 'Backend Integration/Load Tests and Performance Engineering Spike'
  - INV-31 [Deck]: Slide 3 table 'Table 3' R4C3 shows a shortened name 'Production Smoke Tests and 48-Hour Defect' for 'Production Smoke Tests and 48-Hour Defect Watch'
  - INV-31 [Deck]: Slide 3 table 'Table 3' R4C3 shows a shortened name 'MTA Store Parity and Usage-Zero Confirmation' for 'MTA Store Parity and Usage-Zero Confirmation Report'
  - INV-31 [Deck]: Slide 4 shape 'TextBox 4' shows a shortened name 'Milestone Acceptance' for 'Milestone Acceptance Review'
  - INV-31 [Deck]: Slide 4 shape 'TextBox 4' contains an ellipsis: '1. Confirm: Client provides design system access (code library, tokens, design files, guidelines, named contact) by the...'
  - INV-31 [Deck]: Slide 4 shape 'TextBox 4' has doubled punctuation '..': '1. Confirm: Client provides design system access (code library, tokens, design files, guidelines, named contact) by the...'
  - INV-31 [Deck]: Slide 4 shape 'TextBox 4' contains an ellipsis: '6. Build HS-4762: Micro-frontend shell with global navigation, routing, built with Client's design system and sharing...'
  - INV-31 [Deck]: Slide 4 shape 'TextBox 4' has doubled punctuation '..': '6. Build HS-4762: Micro-frontend shell with global navigation, routing, built with Client's design system and sharing...'
  - INV-31 [Deck]: Slide 5 table 'Table 3' R1C1 has an unbalanced bracket, parenthesis, or quotation mark: 'Latency and render-time targets may be missed because they depend on Client-owned components (Snowflake sizing,'
  - INV-31 [Deck]: Slide 5 table 'Table 3' R2C1 has an unbalanced bracket, parenthesis, or quotation mark: 'Client-built components may fail certification targets (e.g., PubMed precision ≥85%, GWAS Atlas coverage ≥90%'
  - INV-31 [Deck]: Slide 5 table 'Table 3' R2C1 has doubled punctuation '.,': 'Client-built components may fail certification targets (e.g., PubMed precision ≥85%, GWAS Atlas coverage ≥90%'
  - INV-31 [Deck]: Slide 5 speaker notes uses evaluative filler 'proactive' (DECK-09): '• Mitigations and proactive response ownership are assigned across delivery phases.'
  - INV-31 [Deck]: Slide 6 shape 'TextBox 4' has an unbalanced bracket, parenthesis, or quotation mark: '• Client Platform and Data Tier Owners (Client Delivery Counterpart): Own the platform layer (Terraform'
  - INV-31 [Deck]: Slide 6 shape 'TextBox 4' has an unbalanced bracket, parenthesis, or quotation mark: '• Client Scientist UAT Groups (UAT Participants): Run UAT after each milestone (limited to two'
  - INV-31 [Deck]: Slide 6 shape 'TextBox 8' has an unbalanced bracket, parenthesis, or quotation mark: '• M1: Client provides design system access (code library, tokens, design files, guidelines'
  - INV-31 [Deck]: Slide 6 speaker notes has an unbalanced bracket, parenthesis, or quotation mark: '• First client prerequisite is required by M1: Client provides design system access (code library.'
  - INV-31 [Deck]: Slide 6 speaker notes uses evaluative filler 'Active alignment' (DECK-09): '• Active alignment ensures clear decision rights and rapid resolution of open items.'
  - INV-31 [Deck]: Slide 2 talking point has no trace manifest entry: 'Project operates under Fixed Bid contract terms and Partnered governance.'
  - INV-31 [Deck]: Slide 2 talking point has no trace manifest entry: 'Delivery leadership: PMO Lead To be confirmed, Delivery Manager To be confirmed, Talent PM To be confirmed.'
  - INV-31 [Deck]: Slide 2 talking point has no trace manifest entry: 'Purpose: Build part of the ARC application and automate its QA testing so ARC can launch as one application within the client's larger genomics platform..'
  - INV-31 [Deck]: Slide 2 talking point has no trace manifest entry: 'Escalation path: Talent PM / Delivery Manager -> PMO Lead -> Director, PMO.'
  - INV-31 [Deck]: Slide 2 talking point has no trace manifest entry: 'Delivery spans 4 phases from 2026-10-05 to 2027-04-02.'
  - INV-31 [Deck]: Slide 3 talking point has no trace manifest entry: 'The project runs in 4 phases, from 2026-10-05 to 2027-04-02.'
  - INV-31 [Deck]: Slide 3 talking point has no trace manifest entry: 'Delivery commits to 4 milestones across 4 workstreams.'
  - INV-31 [Deck]: Slide 3 talking point has no trace manifest entry: 'All 19 deliverables are mapped to baseline milestone dates.'
  - INV-31 [Deck]: Slide 3 talking point has no trace manifest entry: 'Date basis: SOW estimate, weeks 1–6.'
  - INV-31 [Deck]: Slide 4 talking point has no trace manifest entry: 'Acceptance is conducted at milestone level following defined quality review gates.'
  - INV-31 [Deck]: Slide 4 talking point has no trace manifest entry: 'Milestone review window is Not specified; reviewed at the Milestone Acceptance Review with client approver Client's designated Milestone Sign-Off approver (name not specified).'
  - INV-31 [Deck]: Slide 4 talking point has no trace manifest entry: 'All 19 deliverable acceptance criteria must be verified with required completion evidence.'
  - INV-31 [Deck]: Slide 4 talking point has no trace manifest entry: 'Submissions follow standard verification and rework remediation workflows.'
  - INV-31 [Deck]: Slide 5 talking point has no trace manifest entry: 'Active RAID tracking monitors 4 items rated High severity.'
  - INV-31 [Deck]: Slide 5 talking point has no trace manifest entry: 'First priority risk is RAID-01: Latency and render-time targets may be missed because they depend.'
  - INV-31 [Deck]: Slide 5 talking point has no trace manifest entry: 'Mitigations and proactive response ownership are assigned across delivery phases.'
  - INV-31 [Deck]: Slide 5 talking point has no trace manifest entry: 'New risks or issues should be raised via the delivery escalation path.'
  - INV-31 [Deck]: Slide 6 talking point has no trace manifest entry: 'Engagement governance establishes regular cadence with 6 client stakeholders.'
  - INV-31 [Deck]: Slide 6 talking point has no trace manifest entry: 'Communications rhythm includes 7 scheduled governance touchpoints.'
  - INV-31 [Deck]: Slide 6 talking point has no trace manifest entry: 'First client prerequisite is required by M1: Client provides design system access (code library.'
  - INV-31 [Deck]: Slide 6 talking point has no trace manifest entry: 'Active alignment ensures clear decision rights and rapid resolution of open items.'
  - INV-32 [Deck]: Slide 2 table 'Table 5': R0C0 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R0C1 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R1C0 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R1C1 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R2C0 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R2C1 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R3C0 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R3C1 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R4C0 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R4C1 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R5C0 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R5C1 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R6C0 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 table 'Table 5': R6C1 font 9.5 pt is below the 10 pt minimum
  - INV-32 [Deck]: Slide 2 shapes 'TextBox 4' and 'Table 5' overlap
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 4' paragraph 1 has no explicit font size: 'Key facts'
  - INV-32 [Deck]: Slide 2 card text frame 'TextBox 4' is not inset 0.2 in from its card
  - INV-32 [Deck]: Slide 2 card text frame 'TextBox 4' must have word wrap on, autofit off, and top anchor
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 7' paragraph 1 has no explicit font size: 'Purpose and delivery model'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 7' paragraph 2 has no explicit font size: 'Project Purpose'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 7' paragraph 3 has no explicit font size: 'Build part of the ARC application and automate its'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 7' paragraph 4 has no explicit font size: 'Delivery Model & Governance'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 7' paragraph 5 has no explicit font size: 'Toptal Talent Team (Agile/Milestone Hybrid)'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 7' paragraph 6 has no explicit font size: 'Escalation Path'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 7' paragraph 7 has no explicit font size: 'Talent PM / Delivery Manager -> PMO Lead -> Direct'
  - INV-32 [Deck]: Slide 2 card text frame 'TextBox 7' is not inset 0.2 in from its card
  - INV-32 [Deck]: Slide 2 card text frame 'TextBox 7' must have word wrap on, autofit off, and top anchor
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 9' paragraph 1 has no explicit font size: 'Phases and boundaries'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 9' paragraph 2 has no explicit font size: 'Delivery Phases'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 9' paragraph 3 has no explicit font size: '• P1 Foundation'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 9' paragraph 4 has no explicit font size: '• P2a Services and Data'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 9' paragraph 5 has no explicit font size: '• P2b Application Surface'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 9' paragraph 6 has no explicit font size: '• P3 Launch'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 9' paragraph 7 has no explicit font size: 'Out of Scope'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 9' paragraph 8 has no explicit font size: '• Platform infrastructure and DevOps: environment/'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 9' paragraph 9 has no explicit font size: '• Security design, threat modeling, platform harde'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 9' paragraph 10 has no explicit font size: '• Architecture and design work: shell architecture'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 9' paragraph 11 has no explicit font size: '• Snowflake data model design, schema DDL, haploty'
  - INV-32 [Deck]: Slide 2 text frame 'TextBox 9' paragraph 12 has no explicit font size: '• +4 more (see Startup Kit)'
  - INV-32 [Deck]: Slide 2 card text frame 'TextBox 9' is not inset 0.2 in from its card
  - INV-32 [Deck]: Slide 2 card text frame 'TextBox 9' must have word wrap on, autofit off, and top anchor
  - INV-32 [Deck]: Slide 3 shape 'Table 3' lies outside the content area (x 0.83-12.50, y 1.70-7.02; allowed x 0.83-12.5, y 1.7-6.7)
  - INV-32 [Deck]: Slide 4 shape 'Table 5' lies outside the content area (x 4.81-12.50, y 1.70-9.14; allowed x 0.83-12.5, y 1.7-6.7)
  - INV-32 [Deck]: Slide 4 text frame 'TextBox 4' paragraph 1 has no explicit font size: 'How acceptance works'
  - INV-32 [Deck]: Slide 4 text frame 'TextBox 4' paragraph 2 has no explicit font size: 'Milestone Acceptance Process'
  - INV-32 [Deck]: Slide 4 text frame 'TextBox 4' paragraph 3 has no explicit font size: '1. Confirm: Client provides design system access ('
  - INV-32 [Deck]: Slide 4 text frame 'TextBox 4' paragraph 4 has no explicit font size: '2. Confirm: Client IdP team available for Azure AD'
  - INV-32 [Deck]: Slide 4 text frame 'TextBox 4' paragraph 5 has no explicit font size: '3. Confirm: Client-owned stories and code dependen'
  - INV-32 [Deck]: Slide 4 text frame 'TextBox 4' paragraph 6 has no explicit font size: '4. Confirm: Coding and delivery documentation stan'
  - INV-32 [Deck]: Slide 4 text frame 'TextBox 4' paragraph 7 has no explicit font size: '5. Refine stories and acceptance criteria'
  - INV-32 [Deck]: Slide 4 text frame 'TextBox 4' paragraph 8 has no explicit font size: '6. Build HS-4762: Micro-frontend shell with global'
  - INV-32 [Deck]: Slide 4 text frame 'TextBox 4' paragraph 9 has no explicit font size: 'Governance Parameters'
  - INV-32 [Deck]: Slide 4 card text frame 'TextBox 4' is not inset 0.2 in from its card
  - INV-32 [Deck]: Slide 4 card text frame 'TextBox 4' must have word wrap on, autofit off, and top anchor
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 4' paragraph 1 has no explicit font size: 'Client roles and approvers'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 4' paragraph 2 has no explicit font size: '• Client Contact (designated) (Client Sponsor / Ap'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 4' paragraph 3 has no explicit font size: '• Client Designated Milestone Approvers (Client Ap'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 4' paragraph 4 has no explicit font size: '• Client Platform and Data Tier Owners (Client Del'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 4' paragraph 5 has no explicit font size: '• Client Domain Experts and Domain Users (Client S'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 4' paragraph 6 has no explicit font size: '• Client Scientist UAT Groups (UAT Participants): '
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 4' paragraph 7 has no explicit font size: '• +1 more (see Startup Kit)'
  - INV-32 [Deck]: Slide 6 card text frame 'TextBox 4' is not inset 0.2 in from its card
  - INV-32 [Deck]: Slide 6 card text frame 'TextBox 4' must have word wrap on, autofit off, and top anchor
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 6' paragraph 1 has no explicit font size: 'Working rhythm'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 6' paragraph 2 has no explicit font size: '• Kickoff Call: One-time'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 6' paragraph 3 has no explicit font size: '• Daily Standups: Daily'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 6' paragraph 4 has no explicit font size: '• Biweekly Sprint Demo: Biweekly (every sprint)'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 6' paragraph 5 has no explicit font size: '• Weekly Status Meeting: Weekly'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 6' paragraph 6 has no explicit font size: '• Weekly Status Report: Weekly'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 6' paragraph 7 has no explicit font size: '• Milestone Acceptance Review: At the end of each '
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 6' paragraph 8 has no explicit font size: '• Ad-Hoc Working Sessions: As needed'
  - INV-32 [Deck]: Slide 6 card text frame 'TextBox 6' is not inset 0.2 in from its card
  - INV-32 [Deck]: Slide 6 card text frame 'TextBox 6' must have word wrap on, autofit off, and top anchor
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 8' paragraph 1 has no explicit font size: 'What we need from the client'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 8' paragraph 2 has no explicit font size: '• M1: Client provides design system access (code l'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 8' paragraph 3 has no explicit font size: '• M2: Client completes Snowflake data model story '
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 8' paragraph 4 has no explicit font size: '• M3: Client provides UI/UX designs for the Milest'
  - INV-32 [Deck]: Slide 6 text frame 'TextBox 8' paragraph 5 has no explicit font size: '• M4: Client scientist UAT groups available; Clien'
  - INV-32 [Deck]: Slide 6 card text frame 'TextBox 8' is not inset 0.2 in from its card
  - INV-32 [Deck]: Slide 6 card text frame 'TextBox 8' must have word wrap on, autofit off, and top anchor
  - INV-30 [Workbook]: RAID-01 (RSK-01) Mitigation / Response is '' but the Kit RAID Log says 'Use query observability (HS-4942) to attribute misses and report Client-owned causes for remediation' (RAID-09)
  - INV-30 [Workbook]: RAID-02 (RSK-02) Mitigation / Response is '' but the Kit RAID Log says 'Report defects early, agree Client remediation timelines, and manage re-runs beyond the first through Change Order' (RAID-09)
  - INV-30 [Workbook]: RAID-03 (RSK-03) Mitigation / Response is '' but the Kit RAID Log says 'Ask Client for advance notice of changes and raise a Change Order for resulting rework' (RAID-09)
  - INV-30 [Workbook]: RAID-04 (RSK-04) Mitigation / Response is '' but the Kit RAID Log says 'Agree UAT scope, scientist group availability, and entry criteria before each run' (RAID-09)
  - INV-30 [Workbook]: RAID-05 (RSK-05) Mitigation / Response is '' but the Kit RAID Log says 'Include forward-looking risk assessment at each Milestone Acceptance Review and track critical path weekly' (RAID-09)
  - INV-30 [Workbook]: RAID-06 (RSK-06) Mitigation / Response is '' but the Kit RAID Log says 'Review holiday calendars with the Client at kickoff and plan around known breaks' (RAID-09)
  - INV-30 [Workbook]: RAID-07 (ISS-01) Mitigation / Response is '' but the Kit RAID Log says 'Agree and document the component count with the Client at kickoff; additional components go through Change Order' (RAID-09)
```

## 5. RAID-09 root cause: why Mitigation / Response was empty

`src\generators\pmo_workbook\builder.py` built the Workbook RAID rows for Kit risks and issues with

```python
trig = clean_text_v2(getattr(r_item, "trigger", "") or "")
mitig = clean_text_v2(getattr(r_item, "mitigation", "") or "")
```

but the `RiskAssumption` model fields are `trigger_or_early_warning` and `mitigation_or_response`. `getattr` found no attribute named `trigger` or `mitigation`, fell back to `""`, and so both columns were empty for every Kit risk and issue. (Dependencies, assumptions, contract clarifications, and open questions use their own fields and were not affected.) The Kit was correct, which is why only the Workbook and the deck showed the empty Response.

Fix: read `trigger_or_early_warning` and `mitigation_or_response`. One consequence: the model's own default trigger text, `Initial startup assessment` (written when extraction found no trigger, never displayed in the Kit), contains the word `startup`, which `test_no_readiness_content_in_workbook` forbids in the Workbook (INV-04). It is therefore not copied; those rows keep an empty trigger, as before. Probability, Impact, Owner, and Status already matched the Kit and are unchanged.

## 6. Non-deck snapshot differences

Compared `tests\snapshots_proposed\<fixture>\snapshot.json` with the approved `tests\snapshots\<fixture>\snapshot.json`, ignoring `deck_slides` (the approved snapshots have no deck section at all, because the Rev 9 deck snapshots were never promoted):

```text
== arc_genomics keys approved: ['checklist_tables', 'kit_tables', 'workbook_sheets'] proposed: ['checklist_tables', 'deck_slides', 'kit_tables', 'workbook_sheets']
  identical: checklist_tables
  identical: kit_tables
  workbook RAID Log: rows 59 -> 59
    row 4 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-01
    row 5 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-02
    row 6 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-03
    row 7 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-04
    row 8 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-05
    row 9 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-06
    row 10 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-07
== arc_overextracted keys approved: ['checklist_tables', 'kit_tables', 'workbook_sheets'] proposed: ['checklist_tables', 'deck_slides', 'kit_tables', 'workbook_sheets']
  identical: checklist_tables
  identical: kit_tables
  workbook RAID Log: rows 59 -> 59
    row 4 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-01
    row 5 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-02
    row 6 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-03
    row 7 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-04
    row 8 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-05
    row 9 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-06
    row 10 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-07
== mock_sow keys approved: ['checklist_tables', 'kit_tables', 'workbook_sheets'] proposed: ['checklist_tables', 'deck_slides', 'kit_tables', 'workbook_sheets']
  identical: checklist_tables
  identical: kit_tables
  workbook RAID Log: rows 9 -> 9
    row 4 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-01
== no_story_ids keys approved: ['checklist_tables', 'kit_tables', 'workbook_sheets'] proposed: ['checklist_tables', 'deck_slides', 'kit_tables', 'workbook_sheets']
  identical: checklist_tables
  identical: kit_tables
  workbook RAID Log: rows 50 -> 50
    row 4 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-01
== numbered_deliverables keys approved: ['checklist_tables', 'kit_tables', 'workbook_sheets'] proposed: ['checklist_tables', 'deck_slides', 'kit_tables', 'workbook_sheets']
  identical: checklist_tables
  identical: kit_tables
  workbook RAID Log: rows 46 -> 46
    row 4 cols ['Trigger / Early Warning', 'Mitigation / Response'] | RAID-01
```

Justification, per RAID-09: the only non-deck differences are the `Trigger / Early Warning` and `Mitigation / Response` columns of Workbook RAID Log rows whose Source ID is a Kit risk or issue (RSK- or ISS-): 7 rows each in the two ARC fixtures and 1 row each in the other three. Kit tables and Checklist tables are identical in all five fixtures. No other Workbook cell changed. There is nothing to fix.

## 7. Raw outputs

### 7.1 `pytest -q`

```text
$ pytest -q        (before any change, at 30f4cc2)
FAILED tests/test_snapshots.py::test_artifact_snapshots[arc_genomics] - Asser...
FAILED tests/test_snapshots.py::test_artifact_snapshots[arc_overextracted] - ...
FAILED tests/test_snapshots.py::test_artifact_snapshots[mock_sow] - Assertion...
FAILED tests/test_snapshots.py::test_artifact_snapshots[no_story_ids] - Asser...
FAILED tests/test_snapshots.py::test_artifact_snapshots[numbered_deliverables]
5 failed, 366 passed in 105.37s (0:01:45)

$ pytest -q        (final, at 9cf0e6e; git status clean afterwards, so the proposed snapshots are deterministic)
FAILED tests/test_snapshots.py::test_artifact_snapshots[arc_genomics] - Asser...
FAILED tests/test_snapshots.py::test_artifact_snapshots[arc_overextracted] - ...
FAILED tests/test_snapshots.py::test_artifact_snapshots[mock_sow] - Assertion...
FAILED tests/test_snapshots.py::test_artifact_snapshots[no_story_ids] - Asser...
FAILED tests/test_snapshots.py::test_artifact_snapshots[numbered_deliverables]
5 failed, 521 passed in 158.23s (0:02:38)
```

Only the five snapshot tests fail. They fail because of Revision 10: the proposed snapshots now contain the seven-slide deck and the populated RAID columns (section 6). They were committed as proposed and not promoted.

### 7.2 ARC run, `check_artifacts`, and `render_deck`

The ARC SOW (`[V1] Exhibit A - Arc Genomics Platform.pdf`, from `tests\fixtures\sow\arc_genomics\inputs`) was copied into `inputs\` with `cp --`; nothing else in `inputs\` was touched; only the copied PDF was deleted afterwards.

`python main.py --llm-cache replay --start-date 2026-10-05 --slides --non-interactive`

```text
[12:20:01] [INFO] main: =========================================================
[12:20:01] [INFO] main:     TOPTAL PMO STARTUP KIT GENERATOR (Readiness Phase)   
[12:20:01] [INFO] main: =========================================================
[12:20:01] [INFO] main: Outputs -> Kit: yes | Checklist: no | Workbook: yes | Slides: yes
[12:20:01] [INFO] main: Mode: Initial Generation (From SOWs and input artifacts)
[12:20:01] [INFO] main: Directories -> Inputs: inputs | Output: output
[12:20:01] [INFO] main: Leadership Roles -> PMO Lead: [UNASSIGNED - TO BE CONFIRMED] | Delivery Lead: [UNASSIGNED - TO BE CONFIRMED] | Talent PM: [UNASSIGNED - TO BE CONFIRMED]
[12:20:01] [INFO] main: Using Anthropic Claude client (claude-sonnet-5-5) with OpenAI fallback (gpt-4o)
[12:20:01] [INFO] src.orchestrator: Starting PMO Startup Kit generation from directory: inputs
[12:20:01] [INFO] src.orchestrator: Ingested 1 document(s): ['[V1] Exhibit A - Arc Genomics Platform.pdf']
[12:20:01] [INFO] src.orchestrator: Executing concurrent multi-pass LLM extractions (12 domain passes)...
[12:20:01] [INFO] src.orchestrator: Setting PMO Lead: [UNASSIGNED - TO BE CONFIRMED]
[12:20:01] [INFO] src.orchestrator: Setting Delivery Lead / Manager: [UNASSIGNED - TO BE CONFIRMED]
[12:20:01] [INFO] src.orchestrator: Setting Talent PM: [UNASSIGNED - TO BE CONFIRMED]
[12:20:01] [INFO] src.orchestrator: Synthesizing baseline model and enforcing business rules...
[12:20:02] [INFO] src.orchestrator: Running extraction validation layer and reconciliation...
[12:20:02] [INFO] src.orchestrator: Deck sources: Startup Kit and Project Delivery Workbook also written
[12:20:02] [INFO] src.orchestrator: Generating Word Startup Kit document in output...
[12:20:02] [INFO] src.generators.docx_generator: Successfully generated Startup Kit Word document at: output\ARC_Genomics_Platform_Startup_Kit.docx
[12:20:02] [INFO] src.orchestrator: Exporting Project Delivery Workbook to output
[12:20:02] [INFO] src.orchestrator: Exporting Talent Onboarding Deck to output
[12:20:03] [INFO] src.orchestrator: Startup Kit execution complete! Readiness score: 50.4%
[12:20:03] [INFO] main: SUCCESS: Project Startup Kit generated successfully!
[12:20:03] [INFO] main: Startup Kit Word Document: C:\Users\james\PycharmProjects\startup_kit\output\ARC_Genomics_Platform_Startup_Kit.docx
[12:20:03] [INFO] main: Project Delivery Workbook: C:\Users\james\PycharmProjects\startup_kit\output\ARC_Genomics_Platform_Project_Delivery_Workbook.xlsx
[12:20:03] [INFO] main: Talent Onboarding Deck: C:\Users\james\PycharmProjects\startup_kit\output\ARC_Genomics_Platform_Talent_Onboarding_Deck.pptx
================================================================================
           TOPTAL PMO STARTUP READINESS GATEWAY (G-01) SUMMARY
================================================================================
 Project Name             : ARC Genomics Platform
 Client Sponsor           : Syngenta
 Governance Tier          : Partnered | SLA: BREACHED (Drafting exceeded 1-day SLA)
--------------------------------------------------------------------------------
 COMPOSITE READINESS SCORE: 50.4% [NOT READY / REWORK REQUIRED - RED]
 GATE DECISION STATUS     : Rework Required
--------------------------------------------------------------------------------
 SCORE BREAKDOWN:
   • Mandatory Controls   (D1 - 40% Weight): 55.3%
   • Deliverables Rigor   (D2 - 25% Weight): 85.8%
   • Talent Staffing      (D3 - 20% Weight): 0.0%
   • Commercial & Risk    (D4 - 15% Weight): 45.7%
--------------------------------------------------------------------------------
 ACTION REQUIRED SUMMARY:
   • Open Exceptions      : 6 item(s) (G01-03, G01-04, G01-05, G01-06, G01-08, G01-09)
   • Open Clarifications  : 22 item(s) (G01-04, G01-09, G01-15, G01-04, G01-15, G01-07, G01-15, G01-04, G01-15, G01-07, G01-15, G01-04, G01-04, G01-04, G01-15, G01-15, G01-15, G01-15, G01-15, G01-08, G01-08, G01-08)
   • Total Score Recovery : +49.1% -> Achievable Target: 99.5% (GREEN)
--------------------------------------------------------------------------------
 REPORT ARTIFACTS:
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\ARC_Genomics_Platform_Startup_Kit.docx
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\ARC_Genomics_Platform_Project_Delivery_Workbook.xlsx
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\ARC_Genomics_Platform_Talent_Onboarding_Deck.pptx
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\ARC_Genomics_Platform_Talent_Onboarding_Deck.trace.json
================================================================================
================================================================================
                     PROJECT DELIVERY WORKBOOK
--------------------------------------------------------------------------------
   • Project Schedule     : 4 workstreams, 4 milestones
   • WBS                  : 198 elements (163 tasks)
   • RAID Log             : 55 items
--------------------------------------------------------------------------------
   EXTRACTION VALIDATION (Section 4):
   • Findings             : 1 repaired, 1 warning(s), 0 error(s)
     - [INV-07] (REPAIRED): Rebuilt 35 work packages from SOW work item catalogue with verified parent deliverables and work item phases.
     - [INV-18] (WARNING): SOW Award Date is not specified in the contract or inputs.
--------------------------------------------------------------------------------
   TRACEABILITY SELF-CHECK (v3 A13):
   • Milestones          : 4 in baseline -> 4 in workbook (Missing: None)
   • Deliverables        : 19 in baseline -> 19 in workbook (Missing: None)
   • Work packages       : 35 in baseline -> 35 in workbook (Missing: None)
   • RAID items          : 55 in baseline -> 55 in workbook (Missing: None)
   • SOW References      : 35 in baseline -> 35 in workbook (Missing: None)
--------------------------------------------------------------------------------
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\ARC_Genomics_Platform_Project_Delivery_Workbook.xlsx
================================================================================
================================================================================
                     TALENT ONBOARDING DECK
--------------------------------------------------------------------------------
   • Slides               : 7 slides (Cover, Charter, Schedule, Acceptance, Risks, Collaboration, Your Project Kit)
   • Content elements     : 137 elements
   • Elements traced      : 100% (137/137 elements traced)
   • Omitted-ID rows used : 3
   • Trace Manifest       : C:\Users\james\PycharmProjects\startup_kit\output\ARC_Genomics_Platform_Talent_Onboarding_Deck.trace.json
--------------------------------------------------------------------------------
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\ARC_Genomics_Platform_Talent_Onboarding_Deck.pptx
================================================================================
main exit=0
```

`python -m src.tools.check_artifacts output`

```text
PASSED: All artifacts in 'output' satisfy all invariants.
check exit=0
```

`python -m src.tools.render_deck output\ARC_Genomics_Platform_Talent_Onboarding_Deck.pptx`

```text
Not rendered: LibreOffice was not found (set SOFFICE_PATH or add soffice to PATH). The deck was not changed; DECK-21 and INV-32 remain the automated checks.
render exit=0
```

LibreOffice is not installed on this machine (not on `PATH`, not in the usual Windows folders), so `render_deck` correctly reports that it rendered nothing. The command works when LibreOffice is present (a unit test stubs LibreOffice and checks that one PNG per slide is written beside the deck), but I have not seen a rendered slide.

### 7.3 Mock run

`python main.py --mock --non-interactive --all`

```text
[12:20:11] [INFO] main: =========================================================
[12:20:11] [INFO] main:     TOPTAL PMO STARTUP KIT GENERATOR (Readiness Phase)   
[12:20:11] [INFO] main: =========================================================
[12:20:11] [INFO] main: Outputs -> Kit: yes | Checklist: yes | Workbook: yes | Slides: yes
[12:20:11] [INFO] main: Mode: Initial Generation (From SOWs and input artifacts)
[12:20:11] [INFO] main: Directories -> Inputs: inputs\SOWs\Test | Output: output\Reports\Test
[12:20:11] [INFO] main: Leadership Roles -> PMO Lead: [UNASSIGNED - TO BE CONFIRMED] | Delivery Lead: [UNASSIGNED - TO BE CONFIRMED] | Talent PM: [UNASSIGNED - TO BE CONFIRMED]
[12:20:11] [INFO] main: Using offline Mock LLM client for deterministic generation.
[12:20:11] [INFO] src.orchestrator: Starting PMO Startup Kit generation from directory: inputs\SOWs\Test
[12:20:12] [INFO] src.orchestrator: Ingested 1 document(s): ['Syngenta Crop Protection, LLC - ARC Application Implementation SOW + Exhibit A.pdf']
[12:20:12] [INFO] src.orchestrator: Executing concurrent multi-pass LLM extractions (12 domain passes)...
[12:20:12] [INFO] src.orchestrator: Setting PMO Lead: [UNASSIGNED - TO BE CONFIRMED]
[12:20:12] [INFO] src.orchestrator: Setting Delivery Lead / Manager: [UNASSIGNED - TO BE CONFIRMED]
[12:20:12] [INFO] src.orchestrator: Setting Talent PM: [UNASSIGNED - TO BE CONFIRMED]
[12:20:12] [INFO] src.orchestrator: Synthesizing baseline model and enforcing business rules...
[12:20:12] [INFO] src.orchestrator: Running extraction validation layer and reconciliation...
[12:20:12] [INFO] src.orchestrator: Generating Word Startup Kit document in output\Reports\Test...
[12:20:12] [INFO] src.generators.docx_generator: Successfully generated Startup Kit Word document at: output\Reports\Test\Pfizer_Analytics__Cloud_Modernization_Startup_Kit.docx
[12:20:12] [INFO] src.orchestrator: Generating Word Startup Readiness Checklist document in output\Reports\Test...
[12:20:12] [INFO] src.generators.docx_generator: Successfully generated Startup Readiness Checklist Word document at: output\Reports\Test\Pfizer_Analytics__Cloud_Modernization_Startup_Readiness_Checklist.docx
[12:20:12] [INFO] src.orchestrator: Exporting Project Delivery Workbook to output\Reports\Test
[12:20:12] [INFO] src.orchestrator: Exporting Talent Onboarding Deck to output\Reports\Test
[12:20:12] [INFO] src.orchestrator: Startup Kit execution complete! Readiness score: 73.0%
[12:20:12] [INFO] main: SUCCESS: Project Startup Kit generated successfully!
[12:20:12] [INFO] main: Startup Kit Word Document: C:\Users\james\PycharmProjects\startup_kit\output\Reports\Test\Pfizer_Analytics__Cloud_Modernization_Startup_Kit.docx
[12:20:12] [INFO] main: Readiness Checklist Word Document: C:\Users\james\PycharmProjects\startup_kit\output\Reports\Test\Pfizer_Analytics__Cloud_Modernization_Startup_Readiness_Checklist.docx
[12:20:12] [INFO] main: Project Delivery Workbook: C:\Users\james\PycharmProjects\startup_kit\output\Reports\Test\Pfizer_Analytics_Cloud_Modernization_Project_Delivery_Workbook.xlsx
[12:20:12] [INFO] main: Talent Onboarding Deck: C:\Users\james\PycharmProjects\startup_kit\output\Reports\Test\Pfizer_Analytics_Cloud_Modernization_Talent_Onboarding_Deck.pptx
================================================================================
           TOPTAL PMO STARTUP READINESS GATEWAY (G-01) SUMMARY
================================================================================
 Project Name             : Pfizer Analytics & Cloud Modernization
 Client Sponsor           : Pfizer Inc.
 Governance Tier          : Partnered | SLA: BREACHED (Drafting exceeded 1-day SLA)
--------------------------------------------------------------------------------
 COMPOSITE READINESS SCORE: 73.0% [CONDITIONAL / EXCEPTION REQUIRED - AMBER]
 GATE DECISION STATUS     : Approved with Exception
--------------------------------------------------------------------------------
 SCORE BREAKDOWN:
   • Mandatory Controls   (D1 - 40% Weight): 78.0%
   • Deliverables Rigor   (D2 - 25% Weight): 100.0%
   • Talent Staffing      (D3 - 20% Weight): 20.0%
   • Commercial & Risk    (D4 - 15% Weight): 85.0%
--------------------------------------------------------------------------------
 ACTION REQUIRED SUMMARY:
   • Open Exceptions      : 2 item(s) (G01-06, G01-08)
   • Open Clarifications  : 3 item(s) (G01-08, G01-08, G01-08)
   • Total Score Recovery : +10.9% -> Achievable Target: 83.9% (AMBER)
--------------------------------------------------------------------------------
 REPORT ARTIFACTS:
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\Reports\Test\Pfizer_Analytics__Cloud_Modernization_Startup_Kit.docx
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\Reports\Test\Pfizer_Analytics__Cloud_Modernization_Startup_Readiness_Checklist.docx
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\Reports\Test\Pfizer_Analytics_Cloud_Modernization_Project_Delivery_Workbook.xlsx
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\Reports\Test\Pfizer_Analytics_Cloud_Modernization_Talent_Onboarding_Deck.pptx
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\Reports\Test\Pfizer_Analytics_Cloud_Modernization_Talent_Onboarding_Deck.trace.json
================================================================================
================================================================================
                     PROJECT DELIVERY WORKBOOK
--------------------------------------------------------------------------------
   • Project Schedule     : 2 workstreams, 2 milestones
   • WBS                  : 44 elements (33 tasks)
   • RAID Log             : 6 items
   • Unmapped deliverables: 1 (placed under final milestone - review)
--------------------------------------------------------------------------------
   EXTRACTION VALIDATION (Section 4):
   • Findings             : 1 repaired, 3 warning(s), 0 error(s)
     - [INV-20] (WARNING): SOW work item 'Section 3.1' has no identified phase grouping.
     - [INV-20] (WARNING): SOW work item 'Section 3.1' has no descriptive title in SOW; using fallback title.
     - [INV-07] (REPAIRED): Rebuilt 3 work packages from SOW work item catalogue with verified parent deliverables and work item phases.
     - [INV-18] (WARNING): SOW Award Date is not specified in the contract or inputs.
--------------------------------------------------------------------------------
   TRACEABILITY SELF-CHECK (v3 A13):
   • Milestones          : 2 in baseline -> 2 in workbook (Missing: None)
   • Deliverables        : 3 in baseline -> 3 in workbook (Missing: None)
   • Work packages       : 3 in baseline -> 3 in workbook (Missing: None)
   • RAID items          : 6 in baseline -> 6 in workbook (Missing: None)
   • SOW References      : 1 in baseline -> 1 in workbook (Missing: None)
--------------------------------------------------------------------------------
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\Reports\Test\Pfizer_Analytics_Cloud_Modernization_Project_Delivery_Workbook.xlsx
================================================================================
================================================================================
                     TALENT ONBOARDING DECK
--------------------------------------------------------------------------------
   • Slides               : 7 slides (Cover, Charter, Schedule, Acceptance, Risks, Collaboration, Your Project Kit)
   • Content elements     : 51 elements
   • Elements traced      : 100% (51/51 elements traced)
   • Omitted-ID rows used : 0
   • Trace Manifest       : C:\Users\james\PycharmProjects\startup_kit\output\Reports\Test\Pfizer_Analytics_Cloud_Modernization_Talent_Onboarding_Deck.trace.json
--------------------------------------------------------------------------------
   • Output File Path     : C:\Users\james\PycharmProjects\startup_kit\output\Reports\Test\Pfizer_Analytics_Cloud_Modernization_Talent_Onboarding_Deck.pptx
================================================================================
main exit=0
```

`python -m src.tools.check_artifacts output\Reports\Test`

```text
PASSED: All artifacts in 'output\Reports\Test' satisfy all invariants.
check exit=0
```

### 7.4 python-pptx dump of the ARC deck

`python -m src.tools.dump_deck output\ARC_Genomics_Platform_Talent_Onboarding_Deck.pptx` (slide number, layout, title; every text frame; every table's rows; speaker notes; slide-part count; geometry is x,y w x h in inches).

```text
=== Slide 1 | layout=CUSTOM_1 | title='ARC Genomics Platform'
  [text] Cover title (1.33,3.09 11.37x0.75)
      | ARC Genomics Platform
  [text] Cover subtitle (1.33,3.84 11.37x0.57)
      | Talent Team Onboarding · Syngenta · Start 2026-10-05
  [notes]
      | TALKING POINTS:
      | • This deck is for the Talent PM and the Talent Project Team; use these notes as a script and for later reference.
      | • This deck covers ARC Genomics Platform for Syngenta.
      | • The start date is 2026-10-05, and it was provided.
      | 
      | SOURCES: Startup Kit · header table; Project Delivery Workbook · Project Schedule
=== Slide 2 | layout=CUSTOM_16 | title='Project Charter'
  [text] Title 1 (0.29,0.22 12.76x0.70)
      | Project Charter
  [text] Subtitle 2 (0.29,0.84 12.76x0.53)
      | ARC GENOMICS PLATFORM · TALENT TEAM ONBOARDING
  [text] Card text: Key facts (1.03,1.90 3.31x0.40)
      | Key facts
  [table] Table: Key facts (1.03,2.30 3.31x2.10)
      | Client Sponsor || Syngenta
      | Contract Type || Fixed Bid
      | Governance Tier || Partnered
      | Start Date || 2026-10-05 (Provided)
      | Talent PM || To be confirmed
      | Delivery Manager || To be confirmed
      | PMO Lead || To be confirmed
  [text] Card text: Purpose & delivery (5.01,1.90 3.31x4.60)
      | Purpose & delivery
      | Purpose
      | Build part of the ARC application and automate its QA testing so ARC can launch as one application within the client's larger genomics platform.
      | Delivery model
      | Delivery: Toptal Talent Team (Agile/Milestone Hybrid) | Governance: PMO Partnered Tier Governance Model
      | Escalation path
      | Talent PM / Delivery Manager -> PMO Lead -> Director, PMO
  [text] Card text: Phases & scope (8.99,1.90 3.31x4.60)
      | Phases & scope
      | Phases
      | P1 Foundation
      | P2a Services and Data
      | P2b Application Surface
      | P3 Launch
      | Out of scope
      | Platform infrastructure and DevOps: environment/IaC strategy, Terraform, CI/CD pipelines, monitoring and alerting, and shell telemetry.
      | Security design, threat modeling, platform hardening, and RBAC/secrets implementation.
      | Architecture and design work
      | Snowflake data model design, schema DDL, haplotype schema extensions, and data governance design and controls.
      | +4 more (see Startup Kit · SOW Interpretation Summary)
  [notes]
      | TALKING POINTS:
      | • Purpose: Build part of the ARC application and automate its QA testing so ARC can launch as one application within the client's larger genomics platform.
      | • The contract type is Fixed Bid, and the governance tier is Partnered.
      | • Delivery Manager: to be confirmed; Talent PM: to be confirmed; PMO Lead: to be confirmed.
      | • Issues escalate along this path: Talent PM / Delivery Manager -> PMO Lead -> Director, PMO.
      | • The start date is 2026-10-05, and it was provided.
      | • The project runs in 4 phases, from 2026-10-05 to 2027-04-02.
      | 
      | SOURCES: Startup Kit · header table, Project Startup Charter, SOW Interpretation Summary; Project Delivery Workbook · Project Schedule
=== Slide 3 | layout=CUSTOM_16 | title='Workstreams, Milestones, Deliverables and Dates'
  [text] Title 1 (0.29,0.22 12.76x0.70)
      | Workstreams, Milestones, Deliverables and Dates
  [text] Subtitle 2 (0.29,0.84 12.76x0.53)
      | ARC GENOMICS PLATFORM · TALENT TEAM ONBOARDING
  [table] Table: Schedule (0.83,1.70 11.67x3.91)
      | Workstream || Milestone || Dates || Deliverables
      | P1 Foundation || M1: P1 Foundation accepted || 2026-10-05 – 2026-11-13 || DEL-01 Micro-Frontend Shell and Azure AD/MSAL Authentication / DEL-02 Shell and Authentication E2E Test Harness / DEL-03 Pipeline Quality Gates and Deployment Smoke Checks / DEL-04 Authentication Negative-Test Suite and Security Scan / DEL-05 Snowflake Data Model and Data Governance Validation
      | P2a Services and Data || M2: P2a Services and Data accepted || 2026-11-16 – 2027-01-22 || DEL-06 FastAPI Search/Detail Endpoints and Asynchronous Query Processing / DEL-07 Backend Integration/Load Tests and Performance Engineering Spike / DEL-08 OneGWAS Direct-Write Integration and Test Suite / DEL-09 Data Ingestion and Migration Validation / DEL-10 PubMed Extraction and Trait Taxonomy Validation
      | P2b Application Surface || M3: P2b Application Surface accepted || 2027-01-25 – 2027-02-26 || DEL-11 ARC Faceted Search, Results Table and Result Detail View / DEL-12 Haplotype Search, Visualization and API / DEL-13 Nomenclature Service / DEL-14 P2b Test Suites (Frontend, Haplotype, Nomenclature)
      | P3 Launch || M4: P3 Launch accepted || 2027-03-01 – 2027-04-02 || DEL-15 Launch Test Suites and Test Data/Fixtures / DEL-16 UAT Execution and Pre-Launch Hardening / DEL-17 Production Smoke Tests and 48-Hour Defect Watch / DEL-18 MTA Store Parity and Usage-Zero Confirmation Report / DEL-19 Training Materials and User Documentation
  [notes]
      | TALKING POINTS:
      | • The project runs in 4 phases, from 2026-10-05 to 2027-04-02.
      | • M1 (P1 Foundation) is due 2026-11-13.
      | • M2 (P2a Services and Data) is due 2027-01-22; it starts after M1 is accepted.
      | • M3 (P2b Application Surface) is due 2027-02-26; it starts after M2 is accepted.
      | • M4 (P3 Launch) is due 2027-04-02; it starts after M3 is accepted.
      | • The dates for M1 are based on: SOW estimate, weeks 1–6.
      | 
      | SOURCES: Startup Kit · Deliverables and Acceptance Matrix; Project Delivery Workbook · Project Schedule
=== Slide 4 | layout=CUSTOM_16 | title='Acceptance Criteria'
  [text] Title 1 (0.29,0.22 12.76x0.70)
      | Acceptance Criteria
  [text] Subtitle 2 (0.29,0.84 12.76x0.53)
      | ARC GENOMICS PLATFORM · TALENT TEAM ONBOARDING
  [text] Card text: How acceptance works (1.03,1.90 3.31x4.60)
      | How acceptance works
      | Each Milestone is an acceptance gate with Client Sign-Off through designated approvers, following a Milestone Acceptance Review at the end of each Milestone and UAT after each Milestone.
      | Prepare milestone acceptance package and evidence
      | Support client user acceptance testing
      | Milestone Acceptance Review for Client designated approvers and Toptal delivery team
      | Triage and address client review feedback
      | Obtain formal milestone acceptance and sign-off
      | Update schedule and RAID Log after acceptance
      | Review window: Not specified; reviewed at the Milestone Acceptance Review at the end of P1 Foundation
      | Client approver: Client's designated Milestone Sign-Off approver (name not specified)
  [table] Table: Acceptance (4.81,1.70 7.69x4.76)
      | ID || Acceptance Criteria || Gate
      | DEL-01 || Shell load P50 < 1.5s, P90 < 2.5s, P95 < 3s || M1
      | DEL-02 || E2E coverage of composition, navigation and authentication with 100% critical-path pass. || M1
      | DEL-03 || Quality gates block on fail and deployment smoke checks pass 100% before promotion. || M1
      | DEL-04 || Negative tests pass and the scan is clean. || M1
      | DEL-05 || Targets are referential integrity 100%, representative query patterns validated, controls audited, classification coverage validated and gaps logged. || M1
      | DEL-06 || Search P50 < 300ms, P90 < 700ms, P95 < 1s || M2
      | DEL-07 || Search P95 < 1s under load. || M2
      | DEL-08 || 100% of completed runs are written, retryable errors recovered and write P95 < 60s. || M2
      | DEL-09 || Targets are ≥90% GWAS Atlas import coverage with schema-change handling verified, MTA domain-user comparison sign-off with the data-quality log triaged/closed, and 100% of sampled PHG/GATSBY keys matching. || M2
      | DEL-10 || Targets are ≥85% precision on key fields with a green E2E run, and ≥80% taxonomy coverage with approvals captured. || M2
      | DEL-11 || Results render P50 < 400ms, P90 < 800ms, P95 < 1s (excluding network). || M3
      | +8 more: DEL-12, DEL-13, DEL-14, DEL-15, DEL-16, DEL-17, DEL-18, DEL-19 (see Startup Kit · Deliverables and Acceptance Matrix) ||  || 
  [notes]
      | TALKING POINTS:
      | • Acceptance is milestone-level; the M1 acceptance package has 6 steps, starting with: Prepare milestone acceptance package and evidence.
      | • Review window: Not specified; reviewed at the Milestone Acceptance Review at the end of P1 Foundation; client approver: Client's designated Milestone Sign-Off approver (name not specified).
      | • Evidence expected for DEL-01: Work outputs, test results and defect reports for all P1 stories, presented at the Milestone Acceptance Review.
      | 
      | SOURCES: Startup Kit · SOW Interpretation Summary, Deliverables and Acceptance Matrix; Project Delivery Workbook · WBS
=== Slide 5 | layout=CUSTOM_16 | title='High-Risk Items'
  [text] Title 1 (0.29,0.22 12.76x0.70)
      | High-Risk Items
  [text] Subtitle 2 (0.29,0.84 12.76x0.53)
      | ARC GENOMICS PLATFORM · TALENT TEAM ONBOARDING
  [table] Table: Risks (0.83,1.70 11.67x3.06)
      | ID || Item || Rating || Owner || Response || Phase
      | RAID-01 (RSK-01) || Latency and render-time targets may be missed because they depend on Client-owned components (Snowflake sizing, Azure AD, CloudFront, OneGWAS, network). || High || Toptal Delivery Manager || Use query observability (HS-4942) to attribute misses and report Client-owned causes for remediation || Cross-phase
      | RAID-02 (RSK-02) || Client-built components may fail certification targets (e.g., PubMed precision ≥85%, GWAS Atlas coverage ≥90%, taxonomy coverage ≥80%), causing schedule slippage and re-test cycles. || High || Client || Report defects early, agree Client remediation timelines, and manage re-runs beyond the first through Change Order || Cross-phase
      | RAID-05 (RSK-05) || Milestones run sequentially as acceptance gates, so any delay or late acceptance in one Milestone cascades to the later Milestones and the 26-week schedule. || High || Toptal Delivery Manager || Include forward-looking risk assessment at each Milestone Acceptance Review and track critical path weekly || Cross-phase
      | RAID-07 (ISS-01) || The number of ARC-specific design system components included in the estimate is still undefined ([N]), so scope for further components is unclear. || High || To be confirmed || Agree and document the component count with the Client at kickoff || Cross-phase
  [notes]
      | TALKING POINTS:
      | • 4 risks and issues are rated High; the first to watch is RAID-01.
      | • Early warning for RAID-01: Missed p95 targets in benchmarks or load tests.
      | • Early warning for RAID-02: Failed certification test runs reported in defect reports.
      | • Early warning for RAID-05: Milestone acceptance review slipping past planned week.
      | • Early warning for RAID-07: Component count not agreed before frontend work starts.
      | • Raise new risks and issues along this path: Talent PM / Delivery Manager -> PMO Lead -> Director, PMO.
      | 
      | SOURCES: Startup Kit · Project Startup Charter; Project Delivery Workbook · RAID Log
=== Slide 6 | layout=CUSTOM_16 | title='Client Collaboration'
  [text] Title 1 (0.29,0.22 12.76x0.70)
      | Client Collaboration
  [text] Subtitle 2 (0.29,0.84 12.76x0.53)
      | ARC GENOMICS PLATFORM · TALENT TEAM ONBOARDING
  [text] Card text: Client roles (1.03,1.90 3.31x4.18)
      | Client roles
      | Client Sponsor / Approver: Gives timely written responses to decision requests flagged in weekly reports.
      | Client Approver: Accept or reject each of the four sequential milestone gates (P1, P2a, P2b, P3)
      | Client Delivery Counterpart: Own the platform layer (Terraform, infrastructure) and the data tier (ingestion pipelines, Snowflake data model).
      | Client Subject Matter Experts: Provide trait taxonomy approvals and domain-user comparison sign-off for the MTA Store migration.
      | UAT Participants: Run UAT after each milestone (limited to two runs per milestone) and surface defects.
      | +1 more (see Startup Kit · Stakeholder and Responsibility Model)
  [text] Card text: Working rhythm (5.01,1.90 3.31x4.18)
      | Working rhythm
      | Kickoff Call: One-time
      | Daily Standups: Daily
      | Biweekly Sprint Demo: Biweekly (every sprint)
      | Weekly Status Meeting: Weekly
      | Weekly Status Report: Weekly
      | Milestone Acceptance Review: At the end of each milestone (4 milestones)
      | Ad-Hoc Working Sessions: As needed
  [text] Card text: Client prerequisites (8.99,1.90 3.31x4.18)
      | Client prerequisites
      | M1: Client provides design system access (code library, tokens, design files, guidelines, named contact)
      | M2: Client completes Snowflake data model story (HS-4781) before P2a begins
      | M3: Client provides UI/UX designs for the Milestone 3 screens by the Start Date
      | M4: Client scientist UAT groups available
  [notes]
      | TALKING POINTS:
      | • Milestone sign-off sits with Client Contact (designated).
      | • Kickoff Call: One-time.
      | • Daily Standups: Daily.
      | • Biweekly Sprint Demo: Biweekly (every sprint).
      | • Before P1 Foundation starts on 2026-10-05, the client prerequisite is: Client provides design system access (code library, tokens, design files, guidelines, named contact).
      | • 20 open questions are waiting on the client; the first is RAID-36.
      | 
      | SOURCES: Startup Kit · Communications and Reporting Plan, Stakeholder and Responsibility Model; Project Delivery Workbook · Project Schedule, RAID Log
=== Slide 7 | layout=CUSTOM_16 | title='Your Project Kit'
  [text] Title 1 (0.29,0.22 12.76x0.70)
      | Your Project Kit
  [text] Subtitle 2 (0.29,0.84 12.76x0.53)
      | ARC GENOMICS PLATFORM · TALENT TEAM ONBOARDING
  [text] Card text: Startup Kit (1.03,1.90 5.35x4.00)
      | Startup Kit
      | ARC_Genomics_Platform_Startup_Kit.docx
      | The approved project baseline: scope, deliverables and acceptance, governance, and RAID.
      | Sections used in this deck
      | Project Startup Charter
      | SOW Interpretation Summary
      | Deliverables and Acceptance Matrix
      | Communications and Reporting Plan
      | Stakeholder and Responsibility Model
  [text] Card text: Project Delivery Workbook (6.95,1.90 5.35x4.00)
      | Project Delivery Workbook
      | ARC_Genomics_Platform_Project_Delivery_Workbook.xlsx
      | The working delivery plan: schedule by phase, tasks, and the RAID Log.
      | Sheets
      | Project Schedule: gates, dates, and client prerequisites
      | WBS: deliverables and tasks, with acceptance steps
      | RAID Log: risks, issues, dependencies, and open questions
  [text] Text: Trace statement (0.83,6.20 11.67x0.50)
      | Every fact in this deck traces to these two documents. Each slide's notes list its sources.
  [notes]
      | TALKING POINTS:
      | • Both files sit in the same folder as this deck.
      | • The Startup Kit is the approved baseline; changes to it go through the escalation path on slide 2.
      | • The Project Delivery Workbook is the plan to keep current as work progresses.
      | • Each slide's SOURCES note says which section or sheet to open for detail.
      | 
      | SOURCES: Startup Kit · Project Startup Charter, SOW Interpretation Summary, Deliverables and Acceptance Matrix, Communications and Reporting Plan, Stakeholder and Responsibility Model; Project Delivery Workbook · Project Schedule, WBS, RAID Log
slide parts in zip: 7
```

### 7.5 Git

```text
$ git grep -n HS-4 -- src
(exit code 1 : no matches)

$ git --no-pager log --oneline -- spec
30f4cc2 Spec Revision 10: deck layout, stricter traceability, Your Project Kit slide
80ab360 Spec Revision 9: onboarding deck with cover slide
4e8b216 version 8 spec
f34d248 spec 6 changes
6d67daa Spec Revision 7

$ git status
On branch main
Your branch is ahead of 'origin/main' by 14 commits.
  (use "git push" to publish your local commits)

nothing to commit, working tree clean

$ git --no-pager log --oneline -20
9cf0e6e Rev 10 tests: slide 6 working rhythm equals the Kit communications items (K.4)
e82037b Proposed snapshots for Rev 10
27b14de Rev 10 step 6: render_deck review aid (DECK-23), README (DECK-18)
79d69e8 Rev 10 steps 3 to 5: deck content, layout, and Your Project Kit slide
f3dc6e7 Rev 10 step 2: Workbook RAID rows carry the Kit RAID fields (RAID-09, INV-30)
444e34b Rev 10 step 1: harden INV-26, add INV-30 to INV-32
30f4cc2 Spec Revision 10: deck layout, stricter traceability, Your Project Kit slide
c7dc2e4 Commit Revision 9 Talent Team Onboarding Deck final report
da694ef Proposed snapshots for Rev 9 deck
7e992cf Step 5: Safety net and docs (DECK-17, DECK-18, OUT-10)
6413f0d Step 4: Integration (DECK-02, OUT-01, OUT-02, DECK-16, OUT-09, DECK-14, DECK-15)
22dc387 Step 3: Slides and talking points (DECK-07, DECK-08, DECK-10, DECK-11, DECK-09, INV-27, INV-28, INV-29)
e0034d6 Step 2: Model and traceability (DECK-03, DECK-04, DECK-19, DECK-20, DECK-05, DECK-06, INV-26)
fc86a51 Step 1: Template and structure (DECK-12, DECK-01, DECK-13)
40155ba Add Toptal presentation template for onboarding deck
80ab360 Spec Revision 9: onboarding deck with cover slide
4e8b216 version 8 spec
3d77df6 chore(release): bump version to 0.6.0
95bf853 misc files
ef85ca8 Update README for current tool and workflow
```

The report commit follows this output; `git status` is clean after it.

## 8. Anything not met, interpreted, or in tension, and why

Each of these is a place where two requirements pull against each other or the text allows more than one reading. I did not weaken any new check or change a requirement's meaning (QA-10); one existing check, INV-28's 15-word rule, now yields to DECK-05 (item 4). Where I chose, I say what, so you can overrule it.

1. **No visual verification.** LibreOffice is not installed, so no slide was rendered. Layout is verified by the DECK-21 fit estimate and INV-32 on the written file, plus the structure tests. Please render the ARC deck once on a machine with LibreOffice (or open it in PowerPoint) before relying on the look. The estimator is the one the spec describes (characters per line from the frame width at an average character width of 0.5 × font size); it is slightly more optimistic than real word wrapping, so a line may wrap one row earlier in PowerPoint than the estimate says.
2. **Slide 4 left card height.** With the 6 acceptance steps, the approval sentence, and the two facts, the card text needs 4.38 in at 10.5 pt by the spec's estimate (the slide 2 Phases & scope card needs 4.32 in). Neither fits the template card height (4.58 in, 4.18 in inside), so the cards on slides 2 and 4 are 5.00 in tall (the full content area, y 1.70 to 6.70). Slide 6 cards keep 4.58 in. This is the DECK-21 order (font, then more room within the content area, then `+N more`).
3. **K.1 and DECK-21 disagree on the card text inset.** K.1 says `Text inset 0.25 in.`; DECK-21 says `one text frame per card, inset 0.20 in from the card on every side`. I used 0.20 in (DECK-21 is the one INV-32 checks). The Key facts columns (1.35 + 1.96 in) add up to a 3.31 in card text width, which only works with a 0.20 in inset.
4. **DECK-05 versus the 15-word guide.** DECK-08 says `Bullets and table cells at most 15 words, cut at a clause boundary by the DECK-05 prefix rule.`, and DECK-05 says `A comma is not a clause boundary.` and forbids any cut that is not at a boundary. For some ARC text there is no boundary within 15 words (the first clause of DEL-05, DEL-09, and DEL-10 acceptance criteria; the description of RAID-01, RAID-02, RAID-05, and RAID-07; milestone names in two fixtures). The builder shows the shortest compliant cut, or the whole name, and sizes it by DECK-21. INV-28's 15-word check therefore accepts a line over 15 words only if it holds a whole name or `has_compliant_cut` finds no boundary within 15 words (a unit test shows a late boundary is still flagged). This is a change to an existing check, so please confirm it.
5. **DECK-08 bullet limit versus K.2 capacities.** DECK-08 says `At most 6 bullets per card or text block.`, but K.2 and K.4 give Working rhythm 7 bullets and Slide 2 `4 + 4 bullets`. I followed K.2 and K.4 (I treated each subheading group as a text block).
6. **INV-30 and Trigger / Early Warning.** INV-30 reads `Every Workbook RAID row whose Source ID is a Kit risk or issue matches the Kit RAID Log on Probability, Impact, Owner, Mitigation / Response, Trigger / Early Warning, and Status (RAID-09).`, and RAID-09 names the same fields, but the Kit RAID Log table has no Trigger / Early Warning column. Adding one would change the Kit, which rule 4 forbids. So INV-30 compares Trigger / Early Warning on the written files only if a Kit table has that column (none does today), and `test_raid_kit_consistency.py` compares all six fields at model level on all five fixtures. The model's default trigger text is not copied (section 5).
7. **Overlap rule.** DECK-21 says `no two content shapes overlap except a card and its own text frame`. The Key facts table sits inside its card, as K.2 describes. INV-32 allows a card to overlap shapes that lie wholly inside it, and still fails any overlap between two non-card shapes (a unit test covers the heading frame covering the table).
8. **TraceRef locators for facts that are not table rows.** The Kit header table has no heading, so its locator is `Header table`. File names, Kit section headings, and Workbook sheet names are traced with the fields `File name`, `Section heading`, and `Sheet name`; INV-26 checks them against the output folder, the Kit headings, and the Workbook sheets.
9. **Rev 9 tests rewritten.** `test_deck_traceability.py`, `test_deck_arc.py`, `test_deck_structure.py`, `test_deck_talking_points.py`, `test_deck_builder.py`, `test_deck_completeness.py`, `test_deck_any_sow.py`, `test_deck_style.py`, `test_deck_text_limits.py`, and `test_cli_reporter.py` were updated for the seven-slide deck and the new manifest (`Kit` / `Workbook`, `traces` list, shape names). The old tests that asserted the defective Rev 9 deck passes were replaced by tests of the new behaviour, not loosened.
10. **Kit file names.** The Kit writer's file-name sanitiser differs from the Workbook and deck one: in the mock run the Kit is `Pfizer_Analytics__Cloud_Modernization_Startup_Kit.docx` (two underscores) while the Workbook and deck use one. Slide 7 names each file exactly as it is in the output folder. This pre-existing inconsistency is not changed here (Kit output must be unchanged).
11. **Not built:** no Checklist content in the deck; no `rejection_rework_path` talking point (the model field exists but no written document displays it, DECK-19).

## 9. Tests named by the spec

All exist and pass: `test_deck_layout.py` (DECK-21, INV-32), `test_deck_structure.py` (DECK-01, DECK-12, DECK-22, INV-28, INV-29), `test_deck_traceability.py` (DECK-04, DECK-05, DECK-22, INV-26), `test_deck_talking_points.py` (DECK-09), `test_deck_text_quality.py` (INV-31), `test_raid_kit_consistency.py` (RAID-09, INV-30), `test_render_deck.py` (DECK-23, the part that can be automated), `test_deck_arc.py` (every K.4 bullet).
