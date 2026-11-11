"""Validation and structural checks for PS Governance Kickoff Deck (HTL-72)."""

from pathlib import Path
from typing import List
import pptx

from src.generators.governance_deck.spec import GovernanceDeckModel


def check_governance_deck_traceability(
    model: GovernanceDeckModel,
    pptx_path: Path,
) -> List[str]:
    """Validate structural correctness, placeholder eradication, and traceability for Governance Deck (HTL-72)."""
    errors: List[str] = []

    if not pptx_path.exists():
        return [f"Presentation file does not exist: {pptx_path}"]

    try:
        prs = pptx.Presentation(str(pptx_path))
    except Exception as e:
        return [f"Failed to open presentation: {e}"]

    # 1. Slide Count
    from src.generators.client_deck.writer import chunk_workstreams_for_deliverables_table
    chunks_s14 = chunk_workstreams_for_deliverables_table(model.slide14.workstreams)
    total_s14_pages = len(chunks_s14)
    rows_s15 = model.slide15.rows
    max_per_page = len(rows_s15) if len(rows_s15) <= 7 else 4
    chunks_s15 = [rows_s15[i : i + max_per_page] for i in range(0, len(rows_s15), max_per_page)] if rows_s15 else [[]]
    total_s15_pages = len(chunks_s15)
    expected_slides = 18 + total_s14_pages + total_s15_pages

    if len(prs.slides) != expected_slides:
        errors.append(f"Expected exactly {expected_slides} slides in Governance Deck, found {len(prs.slides)}")

    # 2. Slide 1 Validation
    if len(prs.slides) >= 1:
        s1 = prs.slides[0]
        s1_text = " ".join([s.text_frame.text for s in s1.shapes if s.has_text_frame])
        if "Governance Kickoff" not in s1_text:
            errors.append("Slide 1 title is missing 'Governance Kickoff'")
        if "Aligning on governance, outcomes and project plan." not in s1_text:
            errors.append("Slide 1 is missing subtitle 'Aligning on governance, outcomes and project plan.'")
        if "[Client Name]" in s1_text or "[Project Name]" in s1_text:
            errors.append("Slide 1 contains unreplaced [Client Name] or [Project Name] placeholders")

    # 3. Slide 11 (Change Decision Matrix) Validation (HTL-109)
    if len(prs.slides) >= 11:
        s11 = prs.slides[10]
        s11_text = " ".join([s.text_frame.text for s in s11.shapes if s.has_text_frame])
        if "Change Decision Matrix" not in s11_text:
            errors.append("Slide 11 title is missing 'Change Decision Matrix'")
        if "DECISION RIGHTS IN PRACTICE" not in s11_text:
            errors.append("Slide 11 kicker is missing 'DECISION RIGHTS IN PRACTICE'")

    # 4. Slide 13 (Team Roster) Validation
    if len(prs.slides) >= 13:
        s13 = prs.slides[12]
        s13_text = " ".join([s.text_frame.text for s in s13.shapes if s.has_text_frame])
        if "The people delivering this project" not in s13_text:
            errors.append("Slide 13 title is missing 'The people delivering this project'")
        if "The people delivering your project" in s13_text:
            errors.append("Slide 13 title still contains 'The people delivering your project'")

    # 5. Slide 14 (Why We're Here) Validation
    if len(prs.slides) >= 14:
        s14 = prs.slides[13]
        s14_text = " ".join([s.text_frame.text for s in s14.shapes if s.has_text_frame])
        if "[Pre-filled:" in s14_text:
            errors.append("Slide 14 contains unreplaced '[Pre-filled:' placeholders")

    # 6. Slide 15 (What We Deliver) Validation
    for p_idx in range(total_s14_pages):
        s15_idx = 14 + p_idx
        if len(prs.slides) > s15_idx:
            s15 = prs.slides[s15_idx]
            s15_text = " ".join([s.text_frame.text for s in s15.shapes if s.has_text_frame])
            if "[high level summary" in s15_text or "[Workstream or Feature" in s15_text:
                errors.append(f"Slide {s15_idx + 1} contains unreplaced placeholder text")

    # 7. Slide 16 (Acceptance Criteria) Validation
    for p_idx in range(total_s15_pages):
        s16_idx = 14 + total_s14_pages + p_idx
        if len(prs.slides) > s16_idx:
            s16 = prs.slides[s16_idx]
            table_found = any(s.has_table for s in s16.shapes)
            if not table_found:
                errors.append(f"Slide {s16_idx + 1} is missing Deliverable Acceptance Criteria table")
            s16_text = " ".join([s.text_frame.text for s in s16.shapes if s.has_text_frame])
            if "Deliverable acceptance criteria" not in s16_text:
                errors.append(f"Slide {s16_idx + 1} is missing title 'Deliverable acceptance criteria'")

    # 8. Slide 17 (How Milestone Acceptance Works) Validation
    s17_idx = 14 + total_s14_pages + total_s15_pages
    if len(prs.slides) > s17_idx:
        s17 = prs.slides[s17_idx]
        s17_text = " ".join([s.text_frame.text for s in s17.shapes if s.has_text_frame])
        if "How milestone acceptance works" not in s17_text:
            errors.append("Slide 17 is missing title 'How milestone acceptance works'")
        if "[Pre-filled:" in s17_text or "[CONFIRMATION REQUIRED]" in s17_text:
            errors.append("Slide 17 contains unreplaced placeholder text")

    # 9. Slide 18 (Approach) Validation
    s18_idx = 15 + total_s14_pages + total_s15_pages
    if len(prs.slides) > s18_idx:
        s18 = prs.slides[s18_idx]
        s18_text = " ".join([s.text_frame.text for s in s18.shapes if s.has_text_frame])
        if "Approach" not in s18_text:
            errors.append("Slide 18 is missing title 'Approach'")
        if "[Pre-filled:" in s18_text or "[CONFIRMATION REQUIRED]" in s18_text:
            errors.append("Slide 18 contains unreplaced placeholder text")

    # 10. Slide 19 (Risk Register) Validation
    s19_idx = 16 + total_s14_pages + total_s15_pages
    if len(prs.slides) > s19_idx:
        s19 = prs.slides[s19_idx]
        table_found = any(s.has_table for s in s19.shapes)
        if not table_found:
            errors.append("Slide 19 is missing Initial Risk Register table")

    # 11. Slide 20 (Next Steps) Validation
    s20_idx = 17 + total_s14_pages + total_s15_pages
    if len(prs.slides) > s20_idx:
        s20 = prs.slides[s20_idx]
        table_found = any(s.has_table for s in s20.shapes)
        if not table_found:
            errors.append("Slide 20 is missing Next Steps table")

    # 10. Companion Trace Manifest Validation
    manifest_path = pptx_path.with_name(f"{pptx_path.stem}.trace.json")
    if not manifest_path.exists():
        errors.append(f"Trace manifest file missing at {manifest_path}")
    elif len(model.manifest.entries) == 0:
        errors.append("Trace manifest has 0 entries")

    return errors
