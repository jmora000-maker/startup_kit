"""Traceability and artifact validator for Client Kickoff Deck (OUT-14)."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import pptx

from src.config import CLIENT_DECK_TEMPLATE_PATH
from src.core.models import StartupKitBaseline, ValidationFinding


BOILERPLATE_SLIDE_INDICES = [1, 2, 3, 6, 7, 8, 9, 10, 12, 13, 15]  # Slides 2,3,4,7,8,9,10,11,13,14,16


def _extract_slide_text(slide) -> List[str]:
    """Extract all text lines from text frames and table cells in a slide."""
    texts: List[str] = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                t = p.text.strip()
                if t:
                    texts.append(t)
        elif shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    t = cell.text.strip()
                    if t:
                        texts.append(t)
    return texts


def check_boilerplate_slides_unchanged(
    generated_prs: pptx.Presentation,
    template_path: Optional[Path] = None,
) -> Tuple[bool, List[str]]:
    """Assert that boilerplate slides (2,3,4,7,8,9,10,11,13,14,16) have zero modified text frames."""
    src_tmpl = template_path or CLIENT_DECK_TEMPLATE_PATH
    if not src_tmpl.exists():
        return False, [f"Template not found at {src_tmpl}"]

    tmpl_prs = pptx.Presentation(str(src_tmpl))
    errors: List[str] = []

    offset = max(0, len(generated_prs.slides) - len(tmpl_prs.slides))

    for tmpl_idx in BOILERPLATE_SLIDE_INDICES:
        if tmpl_idx >= len(tmpl_prs.slides):
            continue
        gen_idx = tmpl_idx if tmpl_idx <= 4 else tmpl_idx + offset
        if gen_idx >= len(generated_prs.slides):
            errors.append(f"Slide index {gen_idx+1} out of bounds")
            continue

        gen_texts = _extract_slide_text(generated_prs.slides[gen_idx])
        tmpl_texts = _extract_slide_text(tmpl_prs.slides[tmpl_idx])

        if gen_texts != tmpl_texts:
            errors.append(
                f"Boilerplate Slide {gen_idx+1} modified: generated text does not match template. "
                f"Generated: {gen_texts[:2]}... vs Template: {tmpl_texts[:2]}..."
            )

    return len(errors) == 0, errors


def check_client_deck_traceability(
    baseline: StartupKitBaseline,
    deck_path: Path,
    manifest_path: Optional[Path] = None,
    template_path: Optional[Path] = None,
) -> List[ValidationFinding]:
    """Execute complete traceability and invariant audit on generated Client Kickoff Deck."""
    findings: List[ValidationFinding] = []

    if not deck_path.exists():
        findings.append(
            ValidationFinding(
                invariant_id="INV-29",
                severity="error",
                message=f"Client Kickoff Deck file not found at {deck_path}",
            )
        )
        return findings

    prs = pptx.Presentation(str(deck_path))

    # 1. Boilerplate preservation check
    is_boilerplate_ok, bp_errors = check_boilerplate_slides_unchanged(prs, template_path=template_path)
    for err in bp_errors:
        findings.append(
            ValidationFinding(
                invariant_id="INV-29",
                severity="error",
                message=err,
            )
        )

    # 2. Manifest check
    mf_path = manifest_path or deck_path.with_name(f"{deck_path.stem}.trace.json")
    if not mf_path.exists():
        findings.append(
            ValidationFinding(
                invariant_id="INV-26",
                severity="error",
                message=f"Companion trace manifest missing at {mf_path}",
            )
        )

    return findings
