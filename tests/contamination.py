"""tests/contamination.py

Automated multi-format artifact contamination auditor (HTL-69).
Extracts all real text content from PPTX, XLSX, and DOCX files and validates
that no forbidden client terms or stale template artifacts are present.
"""

from pathlib import Path
from typing import Any, List, Optional, Sequence, Set, Tuple, Union
import docx
import openpyxl
import pptx


GLOBAL_TEMPLATE_CONTAMINATION_KEYWORDS = [
    "Rimage",
    "EnterpriseOne",
    "JD Edwards",
    "OCI landing zone",
    "DELIVERY GOVERNANCE OPERATING LAYER",
]


def _extract_pptx_shape_text(shp: Any, s_idx: int, segments: List[Tuple[str, str]]) -> None:
    """Recursively extract text from a PPTX shape, table, or group shape."""
    if getattr(shp, "has_text_frame", False) and shp.has_text_frame:
        t = shp.text_frame.text.strip()
        if t:
            shp_id = getattr(shp, "shape_id", "N/A")
            segments.append((f"Slide {s_idx} Shape '{shp.name}' (id={shp_id})", t))
    if getattr(shp, "has_table", False) and shp.has_table:
        for r_idx, row in enumerate(shp.table.rows):
            for c_idx, cell in enumerate(row.cells):
                t = cell.text.strip()
                if t:
                    segments.append((f"Slide {s_idx} Table Row {r_idx+1} Col {c_idx+1}", t))
    if hasattr(shp, "shapes"):  # GroupShape
        for child_shp in shp.shapes:
            _extract_pptx_shape_text(child_shp, s_idx, segments)


def extract_artifact_text_segments(artifact_path: Union[str, Path]) -> List[Tuple[str, str]]:
    """Extract (location_tag, text_content) segments from PPTX, XLSX, or DOCX."""
    path = Path(artifact_path)
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found at {path}")

    ext = path.suffix.lower()
    segments: List[Tuple[str, str]] = []

    if ext == ".pptx":
        prs = pptx.Presentation(str(path))
        for s_idx, slide in enumerate(prs.slides, 1):
            for shp in slide.shapes:
                _extract_pptx_shape_text(shp, s_idx, segments)
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                nt = slide.notes_slide.notes_text_frame.text.strip()
                if nt:
                    segments.append((f"Slide {s_idx} Speaker Notes", nt))

    elif ext == ".xlsx":
        wb = openpyxl.load_workbook(str(path), data_only=True)
        for sheet in wb.worksheets:
            segments.append((f"Sheet '{sheet.title}' Name", sheet.title))
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        t = str(cell.value).strip()
                        if t:
                            segments.append((f"Sheet '{sheet.title}' Cell {cell.coordinate}", t))
                    if getattr(cell, "comment", None) and cell.comment.text:
                        ct = str(cell.comment.text).strip()
                        if ct:
                            segments.append((f"Sheet '{sheet.title}' Cell {cell.coordinate} Comment", ct))

    elif ext == ".docx":
        doc = docx.Document(str(path))
        for p_idx, p in enumerate(doc.paragraphs, 1):
            t = p.text.strip()
            if t:
                segments.append((f"Docx Paragraph {p_idx}", t))
        for t_idx, table in enumerate(doc.tables, 1):
            for r_idx, row in enumerate(table.rows):
                for c_idx, cell in enumerate(row.cells):
                    t = cell.text.strip()
                    if t:
                        segments.append((f"Docx Table {t_idx} Row {r_idx+1} Col {c_idx+1}", t))
        for s_idx, section in enumerate(doc.sections, 1):
            for header_attr in ["header", "first_page_header", "even_page_header"]:
                hdr = getattr(section, header_attr, None)
                if hdr is not None:
                    for p in hdr.paragraphs:
                        t = p.text.strip()
                        if t:
                            segments.append((f"Docx Section {s_idx} {header_attr}", t))
            for footer_attr in ["footer", "first_page_footer", "even_page_footer"]:
                ftr = getattr(section, footer_attr, None)
                if ftr is not None:
                    for p in ftr.paragraphs:
                        t = p.text.strip()
                        if t:
                            segments.append((f"Docx Section {s_idx} {footer_attr}", t))

    return segments


def assert_no_cross_client_contamination(
    artifact_path: Union[str, Path],
    client_name: str,
    forbidden_keywords: Sequence[str],
    include_template_keywords: bool = True,
    allowed_terms: Optional[Sequence[str]] = None,
) -> None:
    """Assert that a generated artifact contains zero forbidden cross-client or template terms."""
    path = Path(artifact_path)
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found at {path}")

    search_terms: Set[str] = set(forbidden_keywords)
    if include_template_keywords:
        search_terms.update(GLOBAL_TEMPLATE_CONTAMINATION_KEYWORDS)

    allowed = {t.lower() for t in (allowed_terms or [])}
    segments = extract_artifact_text_segments(path)
    violations: List[str] = []

    for loc, text in segments:
        text_lower = text.lower()
        for kw in search_terms:
            if not kw or kw.lower() in allowed:
                continue
            if kw.lower() in text_lower:
                violations.append(
                    f"- Found forbidden term '{kw}' at {loc}: \"{text[:120]}...\""
                )

    if violations:
        raise AssertionError(
            f"Cross-client / template contamination detected in '{path.name}' for client '{client_name}':\n"
            + "\n".join(violations)
        )
