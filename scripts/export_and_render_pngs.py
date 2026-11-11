import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pptx

from src.generators.client_deck import export_client_deck
from src.generators.governance_deck import export_governance_deck
from tests.deck_bundle import load_baseline
from tests.test_htl_62 import _build_pge_baseline

output_dir = Path("exported_pptx_decks")
output_dir.mkdir(parents=True, exist_ok=True)

arc = load_baseline("arc_application_implementation")
pge = _build_pge_baseline()

gov_res = export_governance_deck(arc, output_dir / "ARC_Governance_Kickoff_Deck")
client_res = export_client_deck(arc, output_dir / "ARC_Client_Kickoff_Deck")

pge_gov_res = export_governance_deck(pge, output_dir / "PGE_Governance_Kickoff_Deck")
pge_client_res = export_client_deck(pge, output_dir / "PGE_Client_Kickoff_Deck")

print(f"Exported ARC Governance Deck: {gov_res.file_path}")
print(f"Exported ARC Client Deck: {client_res.file_path}")
print(f"Exported PGE Governance Deck: {pge_gov_res.file_path}")
print(f"Exported PGE Client Deck: {pge_client_res.file_path}")

# Check COM/PowerPoint availability
try:
    import win32com.client
    ppt_app = win32com.client.Dispatch("PowerPoint.Application")
    # Export slide PNGs
    gov_abs = str(gov_res.file_path.resolve())
    client_abs = str(client_res.file_path.resolve())
    
    png_dir = output_dir / "rendered_pngs"
    png_dir.mkdir(parents=True, exist_ok=True)
    
    pres_gov = ppt_app.Presentations.Open(gov_abs, WithWindow=False)
    # Slide 16 in ARC Governance (find slide index)
    for idx, s in enumerate(pres_gov.Slides, start=1):
        for shp in s.Shapes:
            if shp.HasTextFrame and "How milestone acceptance works" in shp.TextFrame.Text:
                png_path = str((png_dir / f"ARC_Governance_Slide_{idx}_How_Milestone_Acceptance_Works.png").resolve())
                s.Export(png_path, "PNG", 1920, 1080)
                print(f"Rendered PNG: {png_path}")
            elif shp.HasTextFrame and "Deliverable acceptance criteria" in shp.TextFrame.Text and "Page 1" in shp.TextFrame.Text:
                png_path = str((png_dir / f"ARC_Governance_Slide_{idx}_Deliverable_Acceptance_Criteria.png").resolve())
                s.Export(png_path, "PNG", 1920, 1080)
                print(f"Rendered PNG: {png_path}")
            elif shp.HasTextFrame and "Approach" in shp.TextFrame.Text and "Execution phases" in shp.TextFrame.Text:
                png_path = str((png_dir / f"ARC_Governance_Slide_{idx}_Approach.png").resolve())
                s.Export(png_path, "PNG", 1920, 1080)
                print(f"Rendered PNG: {png_path}")
    pres_gov.Close()

    pres_client = ppt_app.Presentations.Open(client_abs, WithWindow=False)
    for idx, s in enumerate(pres_client.Slides, start=1):
        for shp in s.Shapes:
            if shp.HasTextFrame and "What we will deliver" in shp.TextFrame.Text and "Page 1" in shp.TextFrame.Text:
                png_path = str((png_dir / f"ARC_Client_Slide_{idx}_What_We_Will_Deliver.png").resolve())
                s.Export(png_path, "PNG", 1920, 1080)
                print(f"Rendered PNG: {png_path}")
            elif shp.HasTextFrame and "Initial risk register" in shp.TextFrame.Text:
                png_path = str((png_dir / f"ARC_Client_Slide_{idx}_Initial_Risk_Register.png").resolve())
                s.Export(png_path, "PNG", 1920, 1080)
                print(f"Rendered PNG: {png_path}")
    pres_client.Close()
    ppt_app.Quit()
    print("PowerPoint COM rendering completed successfully.")
except Exception as e:
    print(f"PowerPoint COM export not available/failed: {e}")
