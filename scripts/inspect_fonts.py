import sys
sys.path.insert(0, ".")
import pptx
from tests.deck_bundle import load_baseline
from src.generators.governance_deck import build_governance_deck_model, export_governance_deck
from pathlib import Path
from tests.test_htl_74 import ARC_12_STEP_NARRATIVE, PGE_10_STEP_NARRATIVE

tmp_dir = Path("reports/font_check")
tmp_dir.mkdir(parents=True, exist_ok=True)

# ARC Baseline
b_arc = load_baseline("arc_application_implementation")
b_arc.sow_interpretation.acceptance_process_narrative = ARC_12_STEP_NARRATIVE

res_arc = export_governance_deck(b_arc, tmp_dir / "arc")
prs_arc = pptx.Presentation(str(res_arc.file_path))
s16_arc = next(s for s in prs_arc.slides if any(shape.has_text_frame and "How milestone acceptance works" in shape.text_frame.text for shape in s.shapes))

cards = [
    ("Card 1 (Submission & Review)", next(s for s in s16_arc.shapes if s.has_text_frame and "Inputs ready:" in s.text_frame.text)),
    ("Card 2 (Defect Triage & Remediation)", next(s for s in s16_arc.shapes if s.has_text_frame and "Triage:" in s.text_frame.text)),
    ("Card 3 (Sign-Off & Contractual Closure)", next(s for s in s16_arc.shapes if s.has_text_frame and "Deemed accepted:" in s.text_frame.text)),
]

print("=== ARC Slide 16 python-pptx Font Inspection ===")
for card_name, box in cards:
    tf = box.text_frame
    p0 = tf.paragraphs[0]
    lead_run = p0.runs[0]
    body_run = p0.runs[1] if len(p0.runs) > 1 else p0.runs[0]
    print(f"{card_name}:")
    print(f'  Paragraph 0 Lead Run: text="{lead_run.text}", font_name="{lead_run.font.name}", font_size={lead_run.font.size.pt} pt, bold={lead_run.font.bold}')
    print(f'  Paragraph 0 Body Run: text="{body_run.text[:40]}...", font_name="{body_run.font.name}", font_size={body_run.font.size.pt} pt, bold={body_run.font.bold}')
    all_sizes = [r.font.size.pt for p in tf.paragraphs for r in p.runs if r.font and r.font.size]
    print(f"  All run sizes in card: {set(all_sizes)}")
