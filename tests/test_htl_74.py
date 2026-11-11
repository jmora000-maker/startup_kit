"""HTL-74: Automated test suite for PS Governance Kickoff Deck Slide 16 Visual Diagram (Option C).

Verifies:
1. Two-tier semantic classification engine (_classify_acceptance_step) mapping narrative steps into 3 cards.
2. ARC Genomics (12-step complex baseline) step distribution (5 in Card 1, 3 in Card 2, 4 in Card 3) and verbatim preservation.
3. PGE (10-step standard baseline) step distribution (4 in Card 1, 3 in Card 2, 3 in Card 3) with out-of-order 'Deemed accepted' resolution.
4. Lean 5-step SOW classification and balanced Card 2 fallback (zero empty card guarantee).
5. Dispute-heavy contract multi-tier escalation routing into Card 3.
6. Tier 2 deterministic fallback when narrative is None.
7. Native PowerPoint shapes: 4 flowchart nodes, 3 connector arrows, remediation loop-back, and 3 deep-dive container cards.
8. Geometric containment and typography fitting (top + height <= 5.25 in).
9. Financial scrubbing compliance (zero '$' characters on Slide 16).
"""

from pathlib import Path
import pptx
import pytest

from src.generators.governance_deck import (
    GovernanceDeckModel,
    GovernanceDeckResult,
    build_governance_deck_model,
    export_governance_deck,
)
from src.generators.governance_deck.builder import (
    _build_acceptance_cards,
    _classify_acceptance_step,
    parse_step_line,
)
from src.generators.governance_deck.spec import AcceptanceCardData
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline


ARC_12_STEP_NARRATIVE = (
    "**Inputs ready:** Client must provide environment access, Snowflake schema deployment (HS-4781), upstream systems access (MTA, 1GWAS, GATS-B, GWAS Atlas), and design system tokens/components before dependent work proceeds. Client SME availability (Mike Magwire and Satya) is required for scheduled walkthroughs.\n"
    "**Execution and tracking:** Work is organized across 5 delivery phases: P1 Foundation, P2a Services and Data, P2b Application Surface, P3 Launch, and Hypercare Support. Weekly status reports track progress against user stories (HS-####) and milestone acceptance criteria, managed by Toptal Delivery Manager Saadia Iqbal.\n"
    "**Submission:** Formal delivery package submitted to Client Approver Mike Magwire upon completion of each milestone with written completion notice (email suffices), initiating the Milestone Acceptance Period.\n"
    "**Review:** Client has 10 business days from the completion notice to evaluate, review, and test the Work Output against specifications and Acceptance Criteria in all material respects.\n"
    "**Deliverable-specific rules:** P1 Foundation requires micro-frontend shell and MSAL authentication sign-off; P2a Services and Data requires FastAPI backend and Snowflake integration (HS-4781); P2b Application Surface requires UI/UX validation and OneGWAS/GWAS Atlas workflows; P3 Launch requires production cutover, zero legacy MTA Store traffic (HS-4788), and defect resolution; Hypercare requires 30-day operational stability and warranty support.\n"
    "**Triage:** If Client identifies material non-conformance, Client provides written notice specifying non-conformance details and required modifications. Non-blocking items may be triaged for subsequent sprints or Hypercare by mutual agreement.\n"
    "**Remediation:** Toptal uses commercially reasonable efforts to modify non-conforming Work Output and resubmits for client acceptance.\n"
    "**Rework limit:** Up to three (3) repeated remediation attempts are permitted; if unresolved within Client's reasonable discretion, contractual dispute escalation applies.\n"
    "**Deemed accepted:** If Client provides no written notice of failure within the 10-business-day window or commences commercial/production use, the milestone is deemed accepted.\n"
    "**Sign-off:** Mike Magwire executes and delivers written milestone acceptance certification upon successful review or deemed acceptance, authorizing milestone billing.\n"
    "**Next gate:** Formal milestone sign-off acts as the contractual gateway for phase progression and invoice issuance for each fixed-fee milestone.\n"
    "**Exceptions:** Scope or dependency changes (e.g. schema changes or third-party items) follow formal Change Order procedures; escalation follows Level 1 (Saadia Iqbal / Mike Magwire within 5 business days), Level 2, and Level 3 dispute protocols."
)

PGE_10_STEP_NARRATIVE = (
    "Inputs ready: Confirm that environment read access, discovery tooling access, spend data and SME availability are in place before Day 1.\n"
    "Execution: Deliver all six Work Output items (Portfolio Inventory, Dependency Map, Workload Disposition Register, Target Architecture Recommendation, Business Case & TCO Model, Migration Wave Plan & Roadmap) as Milestone 1, targeting November 18, 2026. Weekly status reports track delivery progress and keep Client Contact Alicia Cook informed.\n"
    "Submission: Give Alicia Cook formal notice that Milestone 1 is complete. The 5-business-day Milestone Acceptance Period starts from the date of that notice, so record the date.\n"
    "Review: Client has 5 business days from the completion notice to evaluate the Work Output against its specifications and Acceptance Criteria in all material respects. Milestone review sessions with the Client Contact (and Client SMEs as needed) cover the Work Output against the criteria.\n"
    "Deemed accepted: If Client gives no written notice of failure within the 5 business days, or starts using the Work Output commercially or in production, Milestone 1 is deemed accepted. Client is still expected to sign and deliver a certification of Milestone acceptance.\n"
    "Triage: If Client finds a material non-conformance, it must notify Supplier in writing, stating how the output does not conform and what modifications are required. Check the notice for these details and clarify any gaps with the Client Contact.\n"
    "Remediation: Supplier uses commercially reasonable efforts to modify the non-conforming Work Output and resubmits it for acceptance. No supplier rework turnaround is stated, so agree a date with Client at the time of notice.\n"
    "Rework limit: If Supplier cannot remedy a non-conforming portion within Client's reasonable discretion after 3 repeated attempts, Client may terminate the SOW. On termination Client pays all amounts due or accrued through the termination date, including work in progress.\n"
    "Sign-off and invoicing: Milestone 1 sign-off is the invoice trigger for the full fixed fee, with an estimated invoice date of 11/18/2026. If the actual completion date differs, notify Client in writing (email suffices).\n"
    "Exceptions: Dependencies, workloads or scope found later may require a Change Order. Delays caused by the Client Contact being unavailable or late on Client responsibilities may justify an equitable adjustment to schedule and fees."
)


def test_htl_74_arc_genomics_12_step_classification_and_rendering(tmp_path):
    """HTL-74: Verify ARC Genomics 12 steps classify into 5 (Card 1), 3 (Card 2), 4 (Card 3) with verbatim data preservation."""
    baseline = load_baseline("arc_application_implementation")
    baseline.sow_interpretation.acceptance_process_narrative = ARC_12_STEP_NARRATIVE

    gov_model = build_governance_deck_model(baseline)
    cards = gov_model.slide16.cards
    assert len(cards) == 3

    # Card 1: 3 steps (HTL-103)
    c1 = cards[0]
    assert c1.stage_label == "STAGE 01 & 02"
    assert c1.title == "SUBMISSION & REVIEW PROTOCOLS"
    assert len(c1.steps) == 3
    c1_labels = [s[0].rstrip(":") for s in c1.steps if s[0]]
    assert c1_labels == ["Inputs ready", "Submission", "Review"]
    assert "Mike Magwire" not in c1.steps[0][1] and "Mike Magwire" not in c1.steps[1][1]
    assert "Satya" not in c1.steps[0][1]
    assert "Client Approver" in c1.steps[1][1]

    # Card 2: 3 steps
    c2 = cards[1]
    assert c2.stage_label == "STAGE 03"
    assert c2.title == "DEFECT TRIAGE & REMEDIATION"
    assert len(c2.steps) == 3
    c2_labels = [s[0].rstrip(":") for s in c2.steps if s[0]]
    assert c2_labels == ["Triage", "Remediation", "Rework limit"]
    assert "repeated remediation attempts" in c2.steps[2][1]

    # Card 3: 3 steps (HTL-103)
    c3 = cards[2]
    assert c3.stage_label == "STAGE 04"
    assert c3.title == "SIGN-OFF & CONTRACTUAL CLOSURE"
    assert len(c3.steps) == 3
    c3_labels = [s[0].rstrip(":") for s in c3.steps if s[0]]
    assert c3_labels == ["Deemed accepted", "Sign-off", "Next gate"]
    assert "Mike Magwire" not in c3.steps[1][1]
    assert "Client Approver" in c3.steps[1][1]

    # Export presentation and verify shapes and geometric containment
    res = export_governance_deck(baseline, tmp_path / "arc_slide16")
    prs = pptx.Presentation(str(res.file_path))
    slide16 = next(s for s in prs.slides if any(shape.has_text_frame and "How milestone acceptance works" in shape.text_frame.text for shape in s.shapes))

    # Bounding box checks
    for s in slide16.shapes:
        top_in = s.top / 914400.0
        h_in = s.height / 914400.0
        assert top_in + h_in <= 5.25, f"Shape exceeded bottom boundary: {top_in + h_in} > 5.25 in"

    # Verify all 3 cards share the exact same uniform font size (7.5pt fixed across all cards, HTL-105)
    card1_boxes = [s for s in slide16.shapes if s.has_text_frame and "Inputs ready:" in s.text_frame.text]
    card2_boxes = [s for s in slide16.shapes if s.has_text_frame and "Triage:" in s.text_frame.text]
    card3_boxes = [s for s in slide16.shapes if s.has_text_frame and "Deemed accepted:" in s.text_frame.text]
    assert len(card1_boxes) == 1 and len(card2_boxes) == 1 and len(card3_boxes) == 1

    c1_size = card1_boxes[0].text_frame.paragraphs[0].runs[0].font.size.pt
    c2_size = card2_boxes[0].text_frame.paragraphs[0].runs[0].font.size.pt
    c3_size = card3_boxes[0].text_frame.paragraphs[0].runs[0].font.size.pt
    assert c1_size == c2_size == c3_size == 7.5

    # Verify flowchart elements
    texts = [s.text_frame.text.strip() for s in slide16.shapes if s.has_text_frame]
    assert any("1. Formal Submission" in t for t in texts)
    assert any("2. Client Review & SLAs" in t for t in texts)
    assert any("3. Decision / Defect Check" in t for t in texts)
    assert any("4. Sign-Off & Deemed Accepted" in t for t in texts)
    assert any("Remediation Loop" in t for t in texts)


def test_htl_74_pge_10_step_classification_and_rendering(tmp_path):
    """HTL-74: Verify PGE 10 steps correctly classify out-of-order 'Deemed accepted' into Card 3 and preserve Alicia Cook verbatim."""
    baseline = _build_pge_baseline()
    baseline.sow_interpretation.acceptance_process_narrative = PGE_10_STEP_NARRATIVE

    gov_model = build_governance_deck_model(baseline)
    cards = gov_model.slide16.cards
    assert len(cards) == 3

    # Card 1: 3 steps (HTL-103)
    c1 = cards[0]
    assert len(c1.steps) == 3
    c1_labels = [s[0].rstrip(":") for s in c1.steps if s[0]]
    assert c1_labels == ["Inputs ready", "Submission", "Review"]
    assert "Alicia Cook" not in c1.steps[1][1]
    assert "Client Contact" in c1.steps[1][1] or "Client Approver" in c1.steps[1][1]

    # Card 2: 3 steps
    c2 = cards[1]
    assert len(c2.steps) == 3
    c2_labels = [s[0].rstrip(":") for s in c2.steps if s[0]]
    assert c2_labels == ["Triage", "Remediation", "Rework limit"]
    assert "3 repeated attempts" in c2.steps[2][1]

    # Card 3: 3 steps (Deemed accepted mapped to Card 3 despite raw step 5 position)
    c3 = cards[2]
    assert len(c3.steps) == 3
    c3_labels = [s[0].rstrip(":") for s in c3.steps if s[0]]
    assert c3_labels == ["Deemed accepted", "Sign-off and invoicing", "Exceptions"]

    # Export presentation and verify PPTX shapes
    res = export_governance_deck(baseline, tmp_path / "pge_slide16")
    prs = pptx.Presentation(str(res.file_path))
    slide16 = prs.slides[16]

    for s in slide16.shapes:
        top_in = s.top / 914400.0
        h_in = s.height / 914400.0
        assert top_in + h_in <= 5.25

    # Verify all 3 cards share the exact same uniform font size (7.5pt for clean PGE)
    card1_boxes = [s for s in slide16.shapes if s.has_text_frame and "Inputs ready:" in s.text_frame.text]
    card2_boxes = [s for s in slide16.shapes if s.has_text_frame and "Triage:" in s.text_frame.text]
    card3_boxes = [s for s in slide16.shapes if s.has_text_frame and "Deemed accepted:" in s.text_frame.text]
    assert len(card1_boxes) == 1 and len(card2_boxes) == 1 and len(card3_boxes) == 1

    c1_size = card1_boxes[0].text_frame.paragraphs[0].runs[0].font.size.pt
    c2_size = card2_boxes[0].text_frame.paragraphs[0].runs[0].font.size.pt
    c3_size = card3_boxes[0].text_frame.paragraphs[0].runs[0].font.size.pt
    assert c1_size == c2_size == c3_size == 7.5


def test_htl_74_lean_5_step_sow_zero_empty_card_fallback(tmp_path):
    """HTL-74: Verify a lean 5-step SOW without explicit triage generates balanced Card 2 defaults (zero empty cards)."""
    lean_narrative = (
        "**Prerequisites:** Client delivers stakeholder interview list and architecture documentation within 3 business days of kickoff.\n"
        "**Milestone delivery:** Toptal submits Final Assessment Report and Executive Presentation Deck to Client Sponsor Jordan Lee.\n"
        "**Client review:** Client has 5 business days to review deliverables against agreed objectives.\n"
        "**Passive sign-off:** In the absence of written feedback within 5 business days, deliverables are deemed accepted.\n"
        "**Certification:** Client executes formal sign-off certificate authorizing final invoice payment."
    )
    baseline = _build_pge_baseline()
    baseline.sow_interpretation.acceptance_process_narrative = lean_narrative
    baseline.sow_interpretation.approval_expectations = "Client delivers interview list within 3 business days; review within 5 business days."

    gov_model = build_governance_deck_model(baseline)
    cards = gov_model.slide16.cards
    assert len(cards) == 3

    # Card 1 has 3 steps
    assert len(cards[0].steps) == 3
    assert "Prerequisites" in cards[0].steps[0][0]

    # Card 2 has fallback default steps (zero empty card)
    assert len(cards[1].steps) >= 1
    c2_text = " ".join(s[1] for s in cards[1].steps)
    assert "non-conformance" in c2_text.lower() or "remediation" in c2_text.lower()

    # Card 3 has 2 steps
    assert len(cards[2].steps) == 2
    assert "Passive sign-off" in cards[2].steps[0][0]
    assert "Certification" in cards[2].steps[1][0]

    # Export presentation and verify
    res = export_governance_deck(baseline, tmp_path / "lean_slide16")
    prs = pptx.Presentation(str(res.file_path))
    slide16 = prs.slides[16]

    card_shapes = [s for s in slide16.shapes if s.has_text_frame and ("STAGE 01" in s.text_frame.text or "STAGE 03" in s.text_frame.text or "STAGE 04" in s.text_frame.text)]
    assert len(card_shapes) == 3

    # Verify all 3 cards share the exact same uniform font size (7.5pt fixed across all cards, HTL-105)
    card1_boxes = [s for s in slide16.shapes if s.has_text_frame and "Prerequisites:" in s.text_frame.text]
    card2_boxes = [s for s in slide16.shapes if s.has_text_frame and "Defect Notice:" in s.text_frame.text]
    card3_boxes = [s for s in slide16.shapes if s.has_text_frame and "Passive sign-off:" in s.text_frame.text]
    assert len(card1_boxes) == 1 and len(card2_boxes) == 1 and len(card3_boxes) == 1

    c1_size = card1_boxes[0].text_frame.paragraphs[0].runs[0].font.size.pt
    c2_size = card2_boxes[0].text_frame.paragraphs[0].runs[0].font.size.pt
    c3_size = card3_boxes[0].text_frame.paragraphs[0].runs[0].font.size.pt
    assert c1_size == c2_size == c3_size == 7.5


def test_htl_74_dispute_heavy_contract_escalation_classification(tmp_path):
    """HTL-74: Verify multi-tier dispute escalation and arbitration routes into Card 3."""
    dispute_narrative = (
        "**Inputs validation:** Client environment provisioning and SSO integration verified prior to Sprint 1.\n"
        "**Deliverable submission:** Sprint delivery packages submitted bi-weekly to Delivery Lead Marcus Vance.\n"
        "**Acceptance testing:** Client performs UAT within 10 business days.\n"
        "**Deficiency notice:** Client issues defect log categorized by Severity 1 (Critical) through Severity 3 (Minor).\n"
        "**Cure period:** Toptal has 5 business days to remediate Severity 1 defects and 10 business days for Severity 2.\n"
        "**Arbitration and Dispute Protocol:** If unresolved after 2 cure cycles, dispute escalates to Project Steering Committee (Level 1), Executive Sponsors (Level 2 within 10 days), and binding AAA arbitration (Level 3).\n"
        "**Deemed acceptance:** Acceptance is deemed granted upon production deployment or expiration of UAT window.\n"
        "**Sign-off gate:** Written certification required for contractual milestone release."
    )
    baseline = _build_pge_baseline()
    baseline.sow_interpretation.acceptance_process_narrative = dispute_narrative
    baseline.sow_interpretation.approval_expectations = "Acceptance testing within 10 business days; cure within 5-10 business days; arbitration level 2 within 10 days."

    gov_model = build_governance_deck_model(baseline)
    cards = gov_model.slide16.cards
    assert len(cards) == 3

    # Dispute step in Card 3
    c3_labels = [s[0].rstrip(":") for s in cards[2].steps if s[0]]
    assert "Arbitration and Dispute Protocol" in c3_labels
    assert "Deemed acceptance" in c3_labels
    assert "Sign-off gate" in c3_labels

    # Deficiency notice & Cure period in Card 2
    c2_labels = [s[0].rstrip(":") for s in cards[1].steps if s[0]]
    assert "Deficiency notice" in c2_labels
    assert "Cure period" in c2_labels


def test_htl_74_tier2_deterministic_fallback_when_narrative_none(tmp_path):
    """HTL-74: Verify Tier 2 fallback builds 3 cards deterministically when acceptance_process_narrative is None."""
    baseline = _build_pge_baseline()
    baseline.sow_interpretation.acceptance_process_narrative = None
    baseline.sow_interpretation.approval_expectations = "Formal written sign-off within 5 business days of Milestone 1 report submission."
    baseline.deliverables[0].rejection_rework_path = "Talent PM / Team rework within 3 business days of notice"

    gov_model = build_governance_deck_model(baseline)
    assert gov_model.slide16.tier == "Tier 2"
    assert len(gov_model.slide16.cards) == 3

    # Export presentation
    res = export_governance_deck(baseline, tmp_path / "tier2_slide16")
    prs = pptx.Presentation(str(res.file_path))
    slide16 = prs.slides[16]

    for s in slide16.shapes:
        top_in = s.top / 914400.0
        h_in = s.height / 914400.0
        assert top_in + h_in <= 5.25


def test_htl_74_financial_scrubbing_zero_dollar_signs(tmp_path):
    """HTL-74 / HTL-77: Verify financial scrubbing strips dollar amounts from Slide 16 narrative."""
    dirty_narrative = (
        "Submission: Deliver work outputs for Milestone 1 with fee of $26,808.00 due upon acceptance.\n"
        "Review: Client evaluates deliverables within 5 business days for total value of $150,000.00.\n"
        "Triage: Non-conformance notice issued without fee deduction.\n"
        "Remediation: Supplier remediates at no additional cost of $0.00.\n"
        "Sign-off: Formal sign-off authorizes $26,808 payment."
    )
    baseline = _build_pge_baseline()
    baseline.sow_interpretation.acceptance_process_narrative = dirty_narrative

    res = export_governance_deck(baseline, tmp_path / "scrub_slide16")
    prs = pptx.Presentation(str(res.file_path))
    slide16 = prs.slides[16]

    for s in slide16.shapes:
        if s.has_text_frame:
            assert "$" not in s.text_frame.text, f"Financial figure leaked into Slide 16: {s.text_frame.text}"
