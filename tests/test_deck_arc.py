"""Tests asserting every Appendix K.4 expected ARC result on the ARC Genomics fixture (Rev 10)."""

import re

import pytest

from src.tools.check_artifacts import check_artifacts_directory
from tests.deck_bundle import card_texts, notes_points, slide_tables, slide_text

KIT_FILE = "ARC_Genomics_Platform_Startup_Kit.docx"
WB_FILE = "ARC_Genomics_Platform_Project_Delivery_Workbook.xlsx"


def _rows(table_shape):
    return [[c.text.strip() for c in r.cells] for r in table_shape.table.rows]


def test_slide_1_cover(arc_bundle):
    slide = arc_bundle["prs"].slides[0]
    assert slide.placeholders[0].text == "ARC Genomics Platform"
    assert slide.placeholders[1].text == "Talent Team Onboarding · Syngenta · Start 2026-10-05"


def test_slide_2_charter(arc_bundle):
    slide = arc_bundle["prs"].slides[1]
    facts = {r[0]: r[1] for r in _rows(slide_tables(slide)[0])}
    assert facts["Client Sponsor"] == "Syngenta"
    assert facts["Contract Type"] == "Fixed Bid"
    assert facts["Governance Tier"] == "Partnered"
    assert facts["Start Date"] == "2026-10-05 (Provided)"
    assert facts["Talent PM"] == facts["Delivery Manager"] == facts["PMO Lead"] == "To be confirmed"
    text = slide_text(slide)
    for phase in ("P1 Foundation", "P2a Services and Data", "P2b Application Surface", "P3 Launch"):
        assert phase in text
    phases_card = card_texts(slide)["Card text: Phases & scope"]
    assert phases_card[2:6] == ["P1 Foundation", "P2a Services and Data", "P2b Application Surface", "P3 Launch"]


def test_slide_3_gates_dates_and_every_deliverable_once(arc_bundle):
    slide = arc_bundle["prs"].slides[2]
    rows = _rows(slide_tables(slide)[0])[1:]
    assert [r[1].split(":")[0] for r in rows] == ["M1", "M2", "M3", "M4"]
    assert rows[0][2].startswith("2026-10-05") and rows[-1][2].endswith("2027-04-02")
    text = slide_text(slide)
    for n in range(1, 20):
        assert len(re.findall(rf"DEL-{n:02d}\b", text)) == 1, f"DEL-{n:02d} must appear exactly once on slide 3"


def test_names_shown_whole_on_slide_3(arc_bundle):
    text = slide_text(arc_bundle["prs"].slides[2])
    assert "DEL-07 Backend Integration/Load Tests and Performance Engineering Spike" in text
    assert "DEL-17 Production Smoke Tests and 48-Hour Defect Watch" in text


def test_slide_4_every_deliverable_once_and_milestone_level(arc_bundle):
    slide = arc_bundle["prs"].slides[3]
    text = slide_text(slide)
    for n in range(1, 20):
        assert len(re.findall(rf"DEL-{n:02d}\b", text)) == 1, f"DEL-{n:02d} must appear exactly once on slide 4"
    assert any("milestone-level" in p for p in notes_points(slide))


def test_slide_4_steps_are_the_six_tasks_of_wbs_1_1_7(arc_bundle):
    slide = arc_bundle["prs"].slides[3]
    card = card_texts(slide)["Card text: How acceptance works"]
    steps = card[2:8]
    assert steps[0] == "Prepare milestone acceptance package and evidence"
    # the same six names, in order, as WBS 1.1.7.1 to 1.1.7.6 in the written Workbook
    ws = arc_bundle["wb"]["WBS"]
    header = [c.value for c in ws[5]]
    code, name = header.index("WBS Code"), header.index("Name")
    expected = [r[name] for r in ws.iter_rows(min_row=6, values_only=True) if r[code] and str(r[code]).startswith("1.1.7.")]
    assert len(expected) == 6 and steps == expected
    parent = next(r for r in ws.iter_rows(min_row=6, values_only=True) if str(r[code]) == "1.1.7")
    assert parent[name] == "M1 Milestone Acceptance"
    assert not any(p.startswith("Confirm:") or p.startswith("Build HS-") for p in card)


def test_slide_5_high_risks_and_responses(arc_bundle):
    slide = arc_bundle["prs"].slides[4]
    rows = _rows(slide_tables(slide)[0])[1:]
    assert [r[0] for r in rows] == ["RAID-01 (RSK-01)", "RAID-02 (RSK-02)", "RAID-05 (RSK-05)", "RAID-07 (ISS-01)"]
    assert all(r[2] == "High" for r in rows)
    assert rows[0][4].startswith("Use query observability (HS-4942)")
    # each Response is the Kit mitigation, in full or a clause-boundary prefix
    kit = arc_bundle["kit"]
    mitigation = {}
    for t in kit.tables:
        if t.rows[0].cells[0].text == "Item ID" and t.rows[0].cells[4].text == "Probability":
            for r in t.rows[1:]:
                mitigation[r.cells[0].text] = r.cells[7].text
    for r in rows:
        kit_id = r[0].split("(")[1].rstrip(")")
        assert mitigation[kit_id].startswith(r[4]), (kit_id, r[4])
        assert r[4], "Response must not be empty"
    # RAID-07 is High probability, Medium impact
    ws = arc_bundle["wb"]["RAID Log"]
    header = [c.value for c in ws[5]]
    raid07 = next(r for r in ws.iter_rows(min_row=6, values_only=True) if r[0] == "RAID-07")
    assert (raid07[header.index("Probability")], raid07[header.index("Impact")]) == ("High", "Medium")


def test_slide_6_client_stakeholders_and_communications(arc_bundle):
    cards = card_texts(arc_bundle["prs"].slides[5])
    roles = cards["Card text: Client roles"][1:]
    assert len(roles) == 6 and roles[-1].startswith("+1 more")
    rhythm = cards["Card text: Working rhythm"][1:]
    assert len(rhythm) == 7
    assert rhythm[0] == "Kickoff Call: One-time"
    # the 7 communications items are COM-01 to COM-07 of the written Kit, shown as "{Report / Meeting}: {Cadence}"
    kit_rows = []
    for t in arc_bundle["kit"].tables:
        if t.rows[0].cells[0].text == "Item ID" and t.rows[0].cells[1].text == "Report / Meeting":
            kit_rows = [[c.text for c in r.cells] for r in t.rows[1:]]
    assert [r[0] for r in kit_rows] == [f"COM-0{i}" for i in range(1, 8)]
    assert rhythm == [f"{r[1]}: {r[4]}" for r in kit_rows]


def test_slide_7_project_kit(arc_bundle):
    slide = arc_bundle["prs"].slides[6]
    text = slide_text(slide)
    assert KIT_FILE in text and WB_FILE in text
    for sheet in ("Project Schedule", "WBS", "RAID Log"):
        assert sheet in text
    assert (arc_bundle["dir"] / KIT_FILE).exists() and (arc_bundle["dir"] / WB_FILE).exists()


def test_no_readiness_content_and_fully_traced(arc_bundle):
    deck_text = "\n".join(slide_text(s) + s.notes_slide.notes_text_frame.text for s in arc_bundle["prs"].slides)
    assert "ACT-" not in deck_text and "G-01" not in deck_text and "readiness" not in deck_text.lower()
    assert arc_bundle["result"].elements_total > 0
    assert arc_bundle["result"].elements_traced == arc_bundle["result"].elements_total  # 100% traced
    assert [str(v) for v in check_artifacts_directory(arc_bundle["dir"])] == []
