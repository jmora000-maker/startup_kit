"""Render high-resolution PNG visualizations of the new Slide 11 (Change Decision Matrix)
and fixed Slides 14 (Why We're Here) and 15 (What We Deliver) for visual verification (HTL-109).
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont
import pptx

from src.generators.governance_deck import build_governance_deck_model, export_governance_deck
from tests.test_htl_62 import _build_pge_baseline
from tests.deck_bundle import load_baseline


def render_slide11_png(baseline, out_path: Path):
    """Render high-fidelity PNG of Governance Deck Slide 11 (Change Decision Matrix - 4 cards)."""
    scale = 2
    dpi = 150
    w_in = 10.0
    h_in = 5.625
    img_w = int(w_in * dpi * scale)
    img_h = int(h_in * dpi * scale)

    img = Image.new('RGB', (img_w, img_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Fonts
    try:
        font_kicker = ImageFont.truetype('arialbd.ttf', int(9.0 * scale * (dpi / 72.0)))
        font_title = ImageFont.truetype('arialbd.ttf', int(24.0 * scale * (dpi / 72.0)))
        font_card_title = ImageFont.truetype('arialbd.ttf', int(11.0 * scale * (dpi / 72.0)))
        font_card_lbl = ImageFont.truetype('arialbd.ttf', int(8.5 * scale * (dpi / 72.0)))
        font_body = ImageFont.truetype('arial.ttf', int(8.5 * scale * (dpi / 72.0)))
        font_pill_bold = ImageFont.truetype('arialbd.ttf', int(8.5 * scale * (dpi / 72.0)))
        font_pill_reg = ImageFont.truetype('arial.ttf', int(8.5 * scale * (dpi / 72.0)))
        font_foot = ImageFont.truetype('arial.ttf', int(9.0 * scale * (dpi / 72.0)))
    except:
        font_kicker = font_title = font_card_title = font_card_lbl = font_body = font_pill_bold = font_pill_reg = font_foot = ImageFont.load_default()

    # Kicker & Title
    kicker_left = int(0.5250 * dpi * scale)
    kicker_top = int(0.4650 * dpi * scale)
    draw.text((kicker_left, kicker_top), "DECISION RIGHTS IN PRACTICE", font=font_kicker, fill=(0x2E, 0x5A, 0xAC))

    title_left = int(0.5250 * dpi * scale)
    title_top = int(0.8040 * dpi * scale)
    draw.text((title_left, title_top), "Change Decision Matrix", font=font_title, fill=(0x0F, 0x25, 0x6E))

    # 4 Cards
    card_w = int(2.04 * dpi * scale)
    card_h = int(2.7106 * dpi * scale)
    card_top = int(1.6684 * dpi * scale)
    left_positions = [
        int(0.6675 * dpi * scale),
        int(2.8755 * dpi * scale),
        int(5.0835 * dpi * scale),
        int(7.2915 * dpi * scale),
    ]

    model = build_governance_deck_model(baseline)
    cards = model.slide11.cards

    for idx, c_left in enumerate(left_positions):
        if idx >= len(cards):
            break
        card = cards[idx]

        # Outer card background
        draw.rounded_rectangle(
            [c_left, card_top, c_left + card_w, card_top + card_h],
            radius=int(8 * scale),
            fill=(0xFD, 0xFD, 0xFE),
            outline=(0xDD, 0xE3, 0xEE),
            width=int(1 * scale),
        )

        pad = int(0.12 * dpi * scale)
        c_inner_w = card_w - 2 * pad
        curr_x = c_left + pad

        # Section 1: Title & Operational Characteristics
        draw.text((curr_x, card_top + int(0.12 * dpi * scale)), card.classification, font=font_card_title, fill=(0x1B, 0x23, 0x36))

        # Wrap operational characteristics
        op_text = card.operational_characteristics
        y_op = card_top + int(0.32 * dpi * scale)
        words = op_text.split()
        line = ""
        line_step_body = int(11.0 * scale * (dpi / 72.0))
        for w in words:
            t = (line + " " + w).strip()
            if draw.textlength(t, font=font_body) <= c_inner_w:
                line = t
            else:
                draw.text((curr_x, y_op), line, font=font_body, fill=(0x5B, 0x64, 0x75))
                y_op += line_step_body
                line = w
        if line:
            draw.text((curr_x, y_op), line, font=font_body, fill=(0x5B, 0x64, 0x75))

        # Section 2: WHAT IT MEANS & Impact
        y_sec2 = card_top + int(0.82 * dpi * scale)
        draw.text((curr_x, y_sec2), "WHAT IT MEANS", font=font_card_lbl, fill=(0x20, 0x4E, 0xCF))

        y_imp = y_sec2 + int(0.20 * dpi * scale)
        imp_text = card.budget_milestone_impact
        words = imp_text.split()
        line = ""
        for w in words:
            t = (line + " " + w).strip()
            if draw.textlength(t, font=font_body) <= c_inner_w:
                line = t
            else:
                draw.text((curr_x, y_imp), line, font=font_body, fill=(0x5B, 0x64, 0x75))
                y_imp += line_step_body
                line = w
        if line:
            draw.text((curr_x, y_imp), line, font=font_body, fill=(0x5B, 0x64, 0x75))

        # Section 3: Bottom Pill Box
        pill_left = c_left + int(0.08 * dpi * scale)
        pill_top = card_top + int(2.00 * dpi * scale)
        pill_w = card_w - int(0.16 * dpi * scale)
        pill_h = int(0.56 * dpi * scale)

        draw.rounded_rectangle(
            [pill_left, pill_top, pill_left + pill_w, pill_top + pill_h],
            radius=int(6 * scale),
            fill=(0xEA, 0xEF, 0xF8),
            outline=(0xEA, 0xEF, 0xF8),
        )

        p_lbl = "Authority: "
        lbl_w = draw.textlength(p_lbl, font=font_pill_bold)
        draw.text((curr_x, pill_top + int(0.06 * dpi * scale)), p_lbl, font=font_pill_bold, fill=(0x1B, 0x23, 0x36))

        # Wrap pathway text
        path_text = card.decision_pathway
        y_p = pill_top + int(0.06 * dpi * scale)
        words = path_text.split()
        line = ""
        is_first_line = True
        line_step_pill = int(10.5 * scale * (dpi / 72.0))
        for w in words:
            t = (line + " " + w).strip()
            max_w = c_inner_w - lbl_w if is_first_line else c_inner_w
            if draw.textlength(t, font=font_pill_reg) <= max_w:
                line = t
            else:
                draw.text((curr_x + (lbl_w if is_first_line else 0), y_p), line, font=font_pill_reg, fill=(0x1B, 0x23, 0x36))
                y_p += line_step_pill
                line = w
                is_first_line = False
        if line:
            draw.text((curr_x + (lbl_w if is_first_line else 0), y_p), line, font=font_pill_reg, fill=(0x1B, 0x23, 0x36))

    # 4. Footer Banner
    foot_left = int(0.6675 * dpi * scale)
    foot_top = int(4.5934 * dpi * scale)
    foot_w = int(8.6647 * dpi * scale)
    foot_h = int(0.5252 * dpi * scale)

    draw.rounded_rectangle(
        [foot_left, foot_top, foot_left + foot_w, foot_top + foot_h],
        radius=int(6 * scale),
        fill=(0xEA, 0xEF, 0xF8),
        outline=(0xEA, 0xEF, 0xF8),
    )

    # Accent bar
    bar_left = int(0.8925 * dpi * scale)
    bar_top = int(4.6909 * dpi * scale)
    bar_w = int(0.0450 * dpi * scale)
    bar_h = int(0.3302 * dpi * scale)
    draw.rounded_rectangle(
        [bar_left, bar_top, bar_left + bar_w, bar_top + bar_h],
        radius=int(2 * scale),
        fill=(0x20, 0x4E, 0xCF),
    )

    # Footer text
    txt_left = int(1.0800 * dpi * scale)
    draw.text((txt_left, foot_top + int(0.16 * dpi * scale)), model.slide11.footer_banner, font=font_foot, fill=(0x1B, 0x23, 0x36))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path))
    print(f"Rendered Slide 11 PNG: {out_path}")


def render_slide14_why_we_are_here_png(baseline, out_path: Path):
    """Render PNG of Slide 14 (Why We're Here) showing condensed Problem Statement without truncation."""
    scale = 2
    dpi = 150
    w_in = 10.0
    h_in = 5.625
    img_w = int(w_in * dpi * scale)
    img_h = int(h_in * dpi * scale)

    img = Image.new('RGB', (img_w, img_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_kicker = ImageFont.truetype('arialbd.ttf', int(9.0 * scale * (dpi / 72.0)))
        font_title = ImageFont.truetype('arialbd.ttf', int(24.0 * scale * (dpi / 72.0)))
        font_sub = ImageFont.truetype('arial.ttf', int(12.0 * scale * (dpi / 72.0)))
        font_card_title = ImageFont.truetype('arialbd.ttf', int(12.0 * scale * (dpi / 72.0)))
        font_body = ImageFont.truetype('arial.ttf', int(10.0 * scale * (dpi / 72.0)))
    except:
        font_kicker = font_title = font_sub = font_card_title = font_body = ImageFont.load_default()

    draw.text((int(0.5250 * dpi * scale), int(0.4650 * dpi * scale)), "PROJECT SUCCESS AGREEMENT", font=font_kicker, fill=(0x2E, 0x5A, 0xAC))
    draw.text((int(0.5250 * dpi * scale), int(0.8040 * dpi * scale)), "Why we're here", font=font_title, fill=(0x0F, 0x25, 0x6E))
    draw.text((int(0.5250 * dpi * scale), int(1.22 * dpi * scale)), "Aligning on project purpose, pain points, and success criteria.", font=font_sub, fill=(0x5B, 0x64, 0x75))

    model = build_governance_deck_model(baseline)

    card_data = [
        ("Why are we doing this?", model.slide13.why_are_we_doing_this, int(1.60 * dpi * scale), int(0.85 * dpi * scale)),
        ("What problem are we solving?", model.slide13.what_problem_are_we_solving, int(2.65 * dpi * scale), int(0.85 * dpi * scale)),
        ("What does success look like?", model.slide13.what_does_success_look_like, int(3.70 * dpi * scale), int(1.20 * dpi * scale)),
    ]

    c_left = int(0.6675 * dpi * scale)
    c_w = int(8.665 * dpi * scale)

    for title, text, top, h in card_data:
        draw.rounded_rectangle(
            [c_left, top, c_left + c_w, top + h],
            radius=int(6 * scale),
            fill=(0xF8, 0xF9, 0xFA),
            outline=(0xEA, 0xEC, 0xF0),
            width=int(1 * scale),
        )
        draw.text((c_left + int(0.20 * dpi * scale), top + int(0.12 * dpi * scale)), title, font=font_card_title, fill=(0x0F, 0x25, 0x6E))

        # Wrap text
        y_txt = top + int(0.38 * dpi * scale)
        words = text.split()
        line = ""
        avail_w = c_w - int(0.40 * dpi * scale)
        line_step_s14 = int(14.0 * scale * (dpi / 72.0))
        for w in words:
            t = (line + " " + w).strip()
            if draw.textlength(t, font=font_body) <= avail_w:
                line = t
            else:
                draw.text((c_left + int(0.20 * dpi * scale), y_txt), line, font=font_body, fill=(0x1D, 0x29, 0x39))
                y_txt += line_step_s14
                line = w
        if line:
            draw.text((c_left + int(0.20 * dpi * scale), y_txt), line, font=font_body, fill=(0x1D, 0x29, 0x39))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path))
    print(f"Rendered Slide 14 PNG: {out_path}")


def render_slide15_what_we_will_deliver_png(baseline, out_path: Path):
    """Render PNG of Slide 15 (What We Deliver / Solution Overview) showing condensed Solution Overview without truncation."""
    scale = 2
    dpi = 150
    w_in = 10.0
    h_in = 5.625
    img_w = int(w_in * dpi * scale)
    img_h = int(h_in * dpi * scale)

    img = Image.new('RGB', (img_w, img_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_kicker = ImageFont.truetype('arialbd.ttf', int(9.0 * scale * (dpi / 72.0)))
        font_title = ImageFont.truetype('arialbd.ttf', int(24.0 * scale * (dpi / 72.0)))
        font_sub = ImageFont.truetype('arial.ttf', int(12.0 * scale * (dpi / 72.0)))
        font_card_title = ImageFont.truetype('arialbd.ttf', int(12.0 * scale * (dpi / 72.0)))
        font_body = ImageFont.truetype('arial.ttf', int(10.0 * scale * (dpi / 72.0)))
    except:
        font_kicker = font_title = font_sub = font_card_title = font_body = ImageFont.load_default()

    draw.text((int(0.5250 * dpi * scale), int(0.4650 * dpi * scale)), "DELIVERY SCOPE & TIMELINE", font=font_kicker, fill=(0x2E, 0x5A, 0xAC))
    draw.text((int(0.5250 * dpi * scale), int(0.8040 * dpi * scale)), "What we will deliver", font=font_title, fill=(0x0F, 0x25, 0x6E))
    draw.text((int(0.5250 * dpi * scale), int(1.22 * dpi * scale)), "Core deliverables, workstreams, and milestone commitments.", font=font_sub, fill=(0x5B, 0x64, 0x75))

    from src.generators.client_deck.builder import build_client_deck_model
    model = build_client_deck_model(baseline)

    # Solution Overview Left Box
    so_left = int(0.6675 * dpi * scale)
    so_top = int(1.60 * dpi * scale)
    so_w = int(3.00 * dpi * scale)
    so_h = int(3.30 * dpi * scale)

    draw.rounded_rectangle(
        [so_left, so_top, so_left + so_w, so_top + so_h],
        radius=int(6 * scale),
        fill=(0xF8, 0xF9, 0xFA),
        outline=(0xEA, 0xEC, 0xF0),
        width=int(1 * scale),
    )
    draw.text((so_left + int(0.15 * dpi * scale), so_top + int(0.15 * dpi * scale)), "Solution Overview", font=font_card_title, fill=(0x0F, 0x25, 0x6E))

    # Wrap Solution Overview text
    y_txt = so_top + int(0.45 * dpi * scale)
    words = model.slide6.solution_overview.split()
    line = ""
    avail_w = so_w - int(0.30 * dpi * scale)
    line_step_s15 = int(14.0 * scale * (dpi / 72.0))
    for w in words:
        t = (line + " " + w).strip()
        if draw.textlength(t, font=font_body) <= avail_w:
            line = t
        else:
            draw.text((so_left + int(0.15 * dpi * scale), y_txt), line, font=font_body, fill=(0x1D, 0x29, 0x39))
            y_txt += line_step_s15
            line = w
    if line:
        draw.text((so_left + int(0.15 * dpi * scale), y_txt), line, font=font_body, fill=(0x1D, 0x29, 0x39))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path))
    print(f"Rendered Slide 15 PNG: {out_path}")


if __name__ == "__main__":
    out_dir = Path("reports/htl109_render")
    pge = _build_pge_baseline()
    pge.contract_type = "Time and Materials"
    pge.charter.contract_type = "Time and Materials"
    arc = load_baseline("arc_application_implementation")

    render_slide11_png(pge, out_dir / "pge_slide11_change_decision_matrix.png")
    render_slide11_png(arc, out_dir / "arc_slide11_change_decision_matrix.png")
    render_slide14_why_we_are_here_png(pge, out_dir / "pge_slide14_why_we_are_here.png")
    render_slide15_what_we_will_deliver_png(pge, out_dir / "pge_slide15_what_we_will_deliver.png")
