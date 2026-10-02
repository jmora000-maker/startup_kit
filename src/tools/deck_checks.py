"""Deck and RAID checks: INV-26 (strict), INV-30, INV-31, INV-32 (DECK-04, DECK-05, DECK-09, DECK-21, RAID-09).

Every check reads the written files (the Kit .docx, the Workbook .xlsx, the deck .pptx, and the trace
manifest). None of them looks at in-memory models.
"""

import datetime
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pptx
from pptx.enum.shapes import MSO_SHAPE_TYPE, MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE

from src.generators.onboarding_deck import layout as L
from src.generators.onboarding_deck import fixed_text as FT
from src.generators.onboarding_deck.coverage import coverage
from src.generators.onboarding_deck.textrules import (
    normalize_text,
    source_units,
    prefix_violation,
    has_ellipsis,
    has_doubled_punctuation,
    is_balanced,
)
from src.tools.invariant_violation import InvariantViolation

KIT_ARTIFACT = "Kit"
WORKBOOK_ARTIFACT = "Workbook"
LEGACY_ARTIFACTS = {"Startup Kit": KIT_ARTIFACT, "Project Delivery Workbook": WORKBOOK_ARTIFACT}
HEADER_TABLE_LOCATOR = "Header table"

# Fields whose displayed value is a name and must be shown whole (DECK-05)
WHOLE_FIELDS = {"Deliverable Name", "Milestone", "Stakeholder Name", "Report / Meeting", "Name", "Workstream"}
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
PLACEHOLDER_SOURCE_RE = re.compile(r"^(?:\[?(?:CONFIRMATION REQUIRED|TBD|UNASSIGNED[^\]]*|TO BE CONFIRMED)\]?)?$", re.IGNORECASE)
WORKBOOK_KEY_COLUMNS = {
    "Project Schedule": ("Milestone ID", "WBS Code"),
    "WBS": ("WBS Code",),
    "RAID Log": ("RAID ID",),
}
WORKBOOK_HEADER_ANCHORS = ("WBS Code", "RAID ID")
EPS = 0.01
FILLER_REGEX = re.compile(
    r"\b(?:ensures?|ensuring|proactive(?:ly)?|robust|seamless(?:ly)?|active alignment|rapid|best-in-class|world-class|streamlined?|effortless(?:ly)?)\b",
    re.IGNORECASE,
)


def _inv(inv_id: str, msg: str) -> InvariantViolation:
    return InvariantViolation(inv_id, msg, "Deck")


# =================================================================================================
# Source index (the written Kit and Workbook)
# =================================================================================================
def _cell_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.strftime("%Y-%m-%d")
    return str(value).strip()


class SourceIndex:
    """Lookup of Kit sections and Workbook sheets, built from the written files."""

    def __init__(self, kit_doc: Optional[Any], wb: Optional[Any], file_names: Sequence[str] = ()):
        self.file_names = set(file_names)
        self.kit_headings: set = set()
        self.kit_sections: Dict[str, List[List[List[str]]]] = {}
        self.sheets: Dict[str, Dict[str, Any]] = {}
        self.has_kit = kit_doc is not None
        self.has_workbook = wb is not None
        if kit_doc is not None:
            self._index_kit(kit_doc)
        if wb is not None:
            self._index_workbook(wb)

    # ---- Kit --------------------------------------------------------------------------------
    def _index_kit(self, kit_doc: Any) -> None:
        from docx.oxml.ns import qn
        import docx.table as docx_table
        import docx.text.paragraph as docx_par

        current = HEADER_TABLE_LOCATOR
        for el in kit_doc.element.body.iterchildren():
            if el.tag == qn("w:p"):
                p = docx_par.Paragraph(el, kit_doc)
                if p.style is not None and p.style.name.startswith("Heading") and p.text.strip():
                    current = p.text.strip()
                    self.kit_headings.add(current)
            elif el.tag == qn("w:tbl"):
                t = docx_table.Table(el, kit_doc)
                rows = [[c.text for c in r.cells] for r in t.rows]
                self.kit_sections.setdefault(current, []).append(rows)

    # ---- Workbook ---------------------------------------------------------------------------
    def _index_workbook(self, wb: Any) -> None:
        for name in wb.sheetnames:
            rows = [[_cell_str(c) for c in r] for r in wb[name].iter_rows(values_only=True)]
            header_idx = None
            for i, r in enumerate(rows[:12]):
                if any(a in r for a in WORKBOOK_HEADER_ANCHORS):
                    header_idx = i
                    break
            info: Dict[str, Any] = {"rows": rows, "header_idx": header_idx, "headers": {}, "title": {}}
            if header_idx is not None:
                info["headers"] = {h: i for i, h in enumerate(rows[header_idx]) if h}
                for r in rows[:header_idx]:
                    for cell in r:
                        for part in cell.split(" | "):
                            if ": " in part:
                                label, value = part.split(": ", 1)
                                info["title"].setdefault(label.strip(), value.strip())
            self.sheets[name] = info

    # ---- Resolution -------------------------------------------------------------------------
    def resolve(self, artifact: str, locator: str, key: str, field: str) -> Tuple[Optional[List[str]], Optional[str]]:
        """The source units for a TraceRef, or (None, reason) when the locator, key, or field is not in the source."""
        if artifact not in (KIT_ARTIFACT, WORKBOOK_ARTIFACT):
            return None, f"unknown artifact '{artifact}'"
        # facts about the documents themselves: a file in the output folder, a Kit heading, a Workbook sheet
        if field == "File name":
            if locator == "File name" and key in self.file_names:
                return [key], None
            return None, f"file '{key}' is not in the output folder"
        if field == "Section heading":
            if artifact == KIT_ARTIFACT and key == locator and key in self.kit_headings:
                return [key], None
            return None, f"Kit section heading '{key}' not found"
        if field == "Sheet name":
            if artifact == WORKBOOK_ARTIFACT and key == locator and key in self.sheets:
                return [key], None
            return None, f"Workbook sheet '{key}' not found"
        if artifact == KIT_ARTIFACT:
            return self._resolve_kit(locator, key, field)
        return self._resolve_workbook(locator, key, field)

    def _resolve_kit(self, locator: str, key: str, field: str) -> Tuple[Optional[List[str]], Optional[str]]:
        tables = self.kit_sections.get(locator)
        if tables is None:
            return None, f"Kit section '{locator}' not found"
        key_n = normalize_text(key)
        key_seen = False
        for t in tables:
            if not t:
                continue
            if locator != HEADER_TABLE_LOCATOR:
                hdr = [normalize_text(h) for h in t[0]]
                for r in t[1:]:
                    if r and normalize_text(r[0]) == key_n:
                        key_seen = True
                        if field in hdr:
                            return source_units(r[hdr.index(field)]), None
                        if field == key and len(r) > 1:
                            return source_units(r[1]), None
            for r in t:
                for ci in range(0, len(r) - 1, 2):
                    if normalize_text(r[ci]) == key_n:
                        key_seen = True
                        if field == key:
                            return source_units(r[ci + 1]), None
        if key_seen:
            return None, f"field '{field}' not found for key '{key}' in Kit section '{locator}'"
        return None, f"key '{key}' not found in Kit section '{locator}'"

    def _resolve_workbook(self, locator: str, key: str, field: str) -> Tuple[Optional[List[str]], Optional[str]]:
        info = self.sheets.get(locator)
        if info is None:
            return None, f"Workbook sheet '{locator}' not found"
        if key in info["title"] and field == key:
            return [normalize_text(info["title"][key])], None
        if info["header_idx"] is None:
            return None, f"Workbook sheet '{locator}' has no table header"
        headers = info["headers"]
        key_cols = [headers[c] for c in WORKBOOK_KEY_COLUMNS.get(locator, ()) if c in headers]
        key_seen = False
        for r in info["rows"][info["header_idx"] + 1:]:
            if any(ci < len(r) and r[ci] == key for ci in key_cols):
                key_seen = True
                if field in headers and headers[field] < len(r):
                    cell = r[headers[field]]
                    if cell.startswith("="):
                        return None, f"field '{field}' of '{key}' is a formula cell with no stored value; trace its input cells"
                    return source_units(cell) or [""], None
        if key_seen:
            return None, f"field '{field}' not found for key '{key}' in Workbook sheet '{locator}'"
        return None, f"key '{key}' not found in Workbook sheet '{locator}'"

    # ---- Names --------------------------------------------------------------------------------
    def names(self) -> List[str]:
        """Every deliverable, milestone, stakeholder, communications, and workstream name in the sources."""
        out: List[str] = []

        def add(v: str) -> None:
            v = normalize_text(v)
            if v and v not in out and len(v.split()) >= 2:
                out.append(v)

        for locator, col in (
            ("Deliverables and Acceptance Matrix", "Deliverable Name"),
            ("Stakeholder and Responsibility Model", "Stakeholder Name"),
            ("Communications and Reporting Plan", "Report / Meeting"),
        ):
            for t in self.kit_sections.get(locator, []):
                if t and col in [normalize_text(h) for h in t[0]]:
                    ci = [normalize_text(h) for h in t[0]].index(col)
                    for r in t[1:]:
                        add(r[ci])
        info = self.sheets.get("Project Schedule")
        if info and info["header_idx"] is not None:
            for col in ("Milestone", "Workstream"):
                ci = info["headers"].get(col)
                if ci is not None:
                    for r in info["rows"][info["header_idx"] + 1:]:
                        if ci < len(r):
                            add(r[ci])
        info = self.sheets.get("WBS")
        if info and info["header_idx"] is not None:
            ci, li = info["headers"].get("Name"), info["headers"].get("Level")
            if ci is not None and li is not None:
                for r in info["rows"][info["header_idx"] + 1:]:
                    if li < len(r) and r[li] in ("3", "4") and ci < len(r):
                        add(r[ci])
        return out


# =================================================================================================
# Manifest loading
# =================================================================================================
def load_manifest_entries(manifest_path: Path) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Entries with a normalized `traces` list (a legacy single `trace` becomes a one-item list)."""
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        return [], f"Failed to load trace manifest: {e}"
    entries = data.get("entries", [])
    for e in entries:
        if "traces" not in e:
            e["traces"] = [e["trace"]] if e.get("trace") else []
    return entries, None



def shortened_names_in(text: str, names: Sequence[str]) -> List[Tuple[str, str]]:
    """(shortened form, full name) pairs found in `text`: a word-prefix of a known name that is not the whole name (DECK-05)."""
    name_set = set(names)
    found: List[Tuple[str, str]] = []
    for n in names:
        words = n.split()
        for k in range(len(words) - 1, 1, -1):
            p = " ".join(words[:k])
            if len(p) < 0.6 * len(n) or p in name_set:
                continue
            at = text.find(p)
            if at < 0 or text.startswith(n, at):
                continue
            if any(m != n and text.startswith(m, at) for m in names):
                continue  # the text shows a different, complete name that begins with the same words
            found.append((p, n))
            break
    return found


def missing_talking_point_entries(prs: Any, entries: List[Dict[str, Any]]) -> List[Tuple[int, str]]:
    """(slide, talking point) for every talking point on slides 2 to 6 with no manifest entry (DECK-09)."""
    tp_entries: Dict[int, List[str]] = {}
    for e in entries:
        if str(e.get("element", "")).startswith("Talking point"):
            tp_entries.setdefault(e.get("slide"), []).append(normalize_text(e.get("displayed_value")))
    out: List[Tuple[int, str]] = []
    for idx, slide in enumerate(prs.slides, start=1):
        if idx < 2 or idx > 6 or not slide.has_notes_slide:
            continue
        for tp in talking_point_lines(slide.notes_slide.notes_text_frame.text):
            if normalize_text(tp) not in tp_entries.get(idx, []):
                out.append((idx, tp))
    return out


# =================================================================================================
# INV-26: traceability
# =================================================================================================
def _compute_rating(prob: str, imp: str) -> str:
    p, i = (prob or "").strip().capitalize(), (imp or "").strip().capitalize()
    if (p == "High" and i in ("High", "Medium")) or (i == "High" and p in ("High", "Medium")):
        return "High"
    if p == "Low" and i == "Low":
        return "Low"
    return "Medium"


def _is_placeholder_source(units: Sequence[str]) -> bool:
    return all(PLACEHOLDER_SOURCE_RE.match(normalize_text(u)) is not None for u in units) if units else True


def _value_in_units(value: str, units: Sequence[str]) -> bool:
    v = normalize_text(value).lower()
    if not v:
        return False
    return any(v in normalize_text(u).lower() for u in units)


def _display_violation(disp: str, units_by_trace: List[Tuple[Dict[str, Any], List[str]]]) -> Optional[str]:
    """None when `disp` equals a source unit, or a clause-boundary prefix of one (names whole). Else a reason."""
    disp_n = normalize_text(disp)
    if disp_n == FT.PLACEHOLDER_TEXT:
        if any(_is_placeholder_source(u) for _, u in units_by_trace):
            return None
        return "is shown as 'To be confirmed' but the source holds a value"
    reasons: List[str] = []
    for trace, units in units_by_trace:
        whole_only = trace.get("field") in WHOLE_FIELDS
        for u in units:
            if disp_n == normalize_text(u):
                return None
            if DATE_RE.fullmatch(disp_n) and disp_n in u:
                return None
            if disp_n in [x.strip() for x in u.split(",")]:
                return None
            reason = prefix_violation(disp_n, u)
            if reason is None:
                if whole_only:
                    reasons.append(f"cuts the name in {trace.get('field')} '{u}'")
                    continue
                return None
            reasons.append(reason)
    if not reasons:
        return "has no source text to compare"
    # prefer the most informative reason (a real prefix with a problem) over "not a prefix"
    informative = [r for r in reasons if r != "is not the source text or a prefix of it"]
    return (informative or reasons)[0]


def check_inv26(
    entries: List[Dict[str, Any]],
    index: SourceIndex,
    prs: Optional[Any] = None,
    manifest_error: Optional[str] = None,
) -> List[InvariantViolation]:
    """INV-26: TraceRefs exist in the written sources, displayed values equal the source or a clause prefix of it."""
    v: List[InvariantViolation] = []
    if manifest_error:
        return [_inv("INV-26", manifest_error)]
    if not entries:
        return [_inv("INV-26", "Trace manifest has zero entries")]

    bad_artifacts = sorted({t.get("artifact") for e in entries for t in e["traces"] if t.get("artifact") in LEGACY_ARTIFACTS})
    for name in bad_artifacts:
        v.append(_inv("INV-26", f"TraceRef artifact '{name}' must be '{LEGACY_ARTIFACTS[name]}' (DECK-04)"))
    missing_shape = [e for e in entries if not e.get("shape")]
    if missing_shape:
        v.append(_inv("INV-26", f"{len(missing_shape)} manifest entries lack a shape name (DECK-06), for example slide {missing_shape[0].get('slide')} element '{missing_shape[0].get('element')}'"))

    for e in entries:
        slide, element, disp = e.get("slide"), e.get("element", ""), normalize_text(e.get("displayed_value"))
        where = f"Slide {slide} element '{element}'"
        traces = e["traces"]
        if disp and not str(element).startswith("Talking point"):
            if has_ellipsis(disp):
                v.append(_inv("INV-26", f"{where}: displayed value '{disp}' contains an ellipsis (DECK-05)"))
            if not is_balanced(disp):
                v.append(_inv("INV-26", f"{where}: displayed value '{disp}' leaves an unbalanced bracket, parenthesis, or quotation mark (DECK-05)"))
            if disp.endswith(","):
                v.append(_inv("INV-26", f"{where}: displayed value '{disp}' is cut at a comma (DECK-05)"))
        if not traces:
            v.append(_inv("INV-26", f"{where} has no TraceRef"))
            continue
        resolved: List[Tuple[Dict[str, Any], List[str]]] = []
        for t in traces:
            art = LEGACY_ARTIFACTS.get(t.get("artifact"), t.get("artifact"))
            if not (art and t.get("locator") and t.get("key") is not None and t.get("field")):
                v.append(_inv("INV-26", f"{where} has an incomplete TraceRef: {t}"))
                continue
            if (art == KIT_ARTIFACT and not index.has_kit) or (art == WORKBOOK_ARTIFACT and not index.has_workbook):
                continue
            units, err = index.resolve(art, t["locator"], str(t["key"]), t["field"])
            if err:
                v.append(_inv("INV-26", f"{where}: TraceRef ({art} / {t['locator']} / {t['key']} / {t['field']}) does not resolve: {err}"))
                continue
            resolved.append((t, units or [""]))
        if len(resolved) != len(traces):
            continue

        if e.get("derived") == "rating":
            cells = {t["field"]: u[0] for t, u in resolved}
            if "Probability" not in cells or "Impact" not in cells:
                v.append(_inv("INV-26", f"{where}: a Rating is derived from Probability and Impact; both must be traced (DECK-20)"))
            elif disp != _compute_rating(cells["Probability"], cells["Impact"]):
                v.append(_inv("INV-26", f"{where}: Rating '{disp}' differs from the DECK-20 rating '{_compute_rating(cells['Probability'], cells['Impact'])}' (Probability={cells['Probability']}, Impact={cells['Impact']})"))
            continue

        if str(element).startswith("Talking point"):
            values = e.get("values") or []
            if not values:
                v.append(_inv("INV-26", f"{where} contains no traced value (DECK-09)"))
            pool = [u for _, units in resolved for u in units]
            aligned = len(values) == len(resolved)
            for vi, val in enumerate(values):
                own = list(resolved[vi][1]) if aligned else pool
                if normalize_text(val).lower() not in disp.lower():
                    v.append(_inv("INV-26", f"{where}: traced value '{val}' does not appear in the talking point"))
                elif normalize_text(val) != FT.PLACEHOLDER_TEXT and not _value_in_units(val, own):
                    v.append(_inv("INV-26", f"{where}: traced value '{val}' is not in its source"))
                elif normalize_text(val) == FT.PLACEHOLDER_TEXT and not _is_placeholder_source(own):
                    v.append(_inv("INV-26", f"{where}: placeholder value but the source holds a value"))
            continue

        reason = _display_violation(disp, resolved)
        if reason:
            v.append(_inv("INV-26", f"{where}: displayed value '{disp}' {reason} (DECK-05)"))

    if prs is not None:
        v.extend(_coverage_violations(entries, prs))
        names = index.names()
        for slide_no, where, text in deck_text_units(prs):
            for p, n in shortened_names_in(text, names):
                v.append(_inv("INV-26", f"Slide {slide_no} {where} shows a shortened name '{p}' for '{n}' (DECK-05)"))
        for slide_no, tp in missing_talking_point_entries(prs, entries):
            v.append(_inv("INV-26", f"Slide {slide_no} talking point has no trace manifest entry (DECK-09): '{tp}'"))
    return v


def _coverage_violations(entries: List[Dict[str, Any]], prs: Any) -> List[InvariantViolation]:
    """DECK-05 (1): every text on slides must be a traced value or a fixed label."""
    v: List[InvariantViolation] = []
    _content, uncovered = coverage(entries, prs)
    for idx, shape_name, text in uncovered:
        v.append(_inv("INV-26", f"Slide {idx} shape '{shape_name}' text has no TraceRef: '{text}'"))
    shape_names = {idx: {sh.name for sh in slide.shapes} for idx, slide in enumerate(prs.slides, start=1)}
    for e in entries:
        shape, slide_no = e.get("shape"), e.get("slide")
        if shape and slide_no in shape_names and shape not in shape_names[slide_no] and not str(e.get("element", "")).startswith("Talking point"):
            v.append(_inv("INV-26", f"Slide {slide_no} manifest entry '{e.get('element')}' names shape '{shape}', which is not on the slide"))
    return v


# =================================================================================================
# INV-27: completeness
# =================================================================================================
ID_TOKEN_RE = re.compile(r"[A-Z]+-?\d+")


def _slide_text(slide: Any) -> str:
    parts: List[str] = []
    for sh in slide.shapes:
        if sh.has_text_frame:
            parts.append(sh.text_frame.text)
        if getattr(sh, "has_table", False) and sh.has_table:
            for r in sh.table.rows:
                parts.extend(c.text for c in r.cells)
    return " ".join(parts)


def check_inv27_completeness(prs: Any, index: SourceIndex) -> List[InvariantViolation]:
    """INV-27 (DECK-07): slide 3 holds every gate, checkpoint, and deliverable ID of the Project Schedule; slide 4 every deliverable ID."""
    v: List[InvariantViolation] = []
    slides = list(prs.slides)
    ps = index.sheets.get("Project Schedule")
    sched_ids: List[str] = []
    if ps and ps["header_idx"] is not None and len(slides) >= 3:
        h = ps["headers"]
        for r in ps["rows"][ps["header_idx"] + 1:]:
            if h.get("Row Type") is None or r[h["Row Type"]] not in ("Milestone", "Checkpoint"):
                continue
            for col in ("Milestone ID", "Linked Deliverables"):
                if col in h and h[col] < len(r):
                    sched_ids.extend(ID_TOKEN_RE.findall(r[h[col]]))
        text3 = _slide_text(slides[2])
        for i in dict.fromkeys(sched_ids):
            if not re.search(r"(?<![A-Za-z0-9-])" + re.escape(i) + r"(?![A-Za-z0-9])", text3):
                v.append(_inv("INV-27", f"Slide 3 does not contain {i}, which is in the Workbook Project Schedule"))
    deliv_ids: List[str] = []
    for t in index.kit_sections.get("Deliverables and Acceptance Matrix", []):
        if t and normalize_text(t[0][0]) == "ID":
            deliv_ids.extend(normalize_text(r[0]) for r in t[1:] if r and normalize_text(r[0]))
    if deliv_ids and len(slides) >= 4:
        text4 = _slide_text(slides[3])
        for i in deliv_ids:
            if not re.search(r"(?<![A-Za-z0-9-])" + re.escape(i) + r"(?![A-Za-z0-9])", text4):
                v.append(_inv("INV-27", f"Slide 4 does not contain {i}, which is in the Kit Deliverables and Acceptance Matrix"))
    return v


# =================================================================================================
# INV-31: text quality
# =================================================================================================
def deck_text_units(prs: Any) -> List[Tuple[int, str, str]]:
    """(slide number, where, text) for every title, kicker, text frame paragraph, table cell line, and note line."""
    out: List[Tuple[int, str, str]] = []
    for idx, slide in enumerate(prs.slides, start=1):
        for sh in slide.shapes:
            if sh.has_text_frame:
                for p in sh.text_frame.paragraphs:
                    if p.text.strip():
                        out.append((idx, f"shape '{sh.name}'", p.text.strip()))
            if getattr(sh, "has_table", False) and sh.has_table:
                for ri, r in enumerate(sh.table.rows):
                    for ci, c in enumerate(r.cells):
                        for line in c.text.splitlines():
                            if line.strip():
                                out.append((idx, f"table '{sh.name}' R{ri}C{ci}", line.strip()))
        if slide.has_notes_slide:
            for line in slide.notes_slide.notes_text_frame.text.splitlines():
                if line.strip():
                    out.append((idx, "speaker notes", line.strip()))
    return out


def talking_point_lines(notes_text: str) -> List[str]:
    return [ln.strip().lstrip("•").strip() for ln in notes_text.splitlines() if ln.strip().startswith("•")]


def check_inv31(
    prs: Any,
    entries: List[Dict[str, Any]],
    names: Sequence[str],
    file_names: Sequence[str] = (),
) -> List[InvariantViolation]:
    """INV-31: no ellipsis, unbalanced brackets, doubled punctuation, or shortened names; talking points in the manifest."""
    v: List[InvariantViolation] = []
    name_set = set(names)
    for slide_no, where, text in deck_text_units(prs):
        loc = f"Slide {slide_no} {where}"
        if has_ellipsis(text):
            v.append(_inv("INV-31", f"{loc} contains an ellipsis: '{text}'"))
        if not is_balanced(text):
            v.append(_inv("INV-31", f"{loc} has an unbalanced bracket, parenthesis, or quotation mark: '{text}'"))
        if where == "speaker notes" and FILLER_REGEX.search(text):
            v.append(_inv("INV-31", f"{loc} uses evaluative filler '{FILLER_REGEX.search(text).group(0)}' (DECK-09): '{text}'"))
        dbl = has_doubled_punctuation(text)
        if dbl:
            v.append(_inv("INV-31", f"{loc} has doubled punctuation '{dbl}': '{text}'"))
        for p, n in shortened_names_in(text, names):
            v.append(_inv("INV-31", f"{loc} shows a shortened name '{p}' for '{n}'"))
        for fn in file_names:
            stem = fn.rsplit(".", 1)[0]
            at = text.find(stem)
            if at >= 0 and not text.startswith(fn, at):
                v.append(_inv("INV-31", f"{loc} shows a shortened file name '{stem}' for '{fn}'"))

    for slide_no, tp in missing_talking_point_entries(prs, entries):
        v.append(_inv("INV-31", f"Slide {slide_no} talking point has no trace manifest entry: '{tp}'"))
    return v


# =================================================================================================
# INV-32: layout
# =================================================================================================
def _in(emu: int) -> float:
    return emu / 914400.0


def _para_size(p: Any) -> Optional[float]:
    sizes = [r.font.size.pt for r in p.runs if r.font.size is not None and r.text]
    return max(sizes) if sizes else None


def _para_for_estimate(p: Any) -> Optional[L.Para]:
    size = _para_size(p)
    if size is None:
        return None
    marL = p._p.pPr.get("marL") if p._p.pPr is not None else None
    return L.Para(
        text=p.text,
        size_pt=size,
        space_before_pt=p.space_before.pt if p.space_before is not None else 0.0,
        space_after_pt=p.space_after.pt if p.space_after is not None else 0.0,
        indent_in=(int(marL) / 914400.0) if marL else 0.0,
    )


def _is_card(sh: Any) -> bool:
    return sh.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE and sh.auto_shape_type == MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE


def _rect(sh: Any) -> Tuple[float, float, float, float]:
    return _in(sh.left), _in(sh.top), _in(sh.left + sh.width), _in(sh.top + sh.height)


def _table_estimate(sh: Any, slide_no: int) -> Tuple[float, List[str]]:
    """(estimated full height in inches, font problems) for a table shape."""
    table = sh.table
    widths = [_in(c.width) for c in table.columns]
    total = 0.0
    problems: List[str] = []
    for ri, row in enumerate(table.rows):
        row_h = _in(row.height)
        for ci, cell in enumerate(row.cells):
            if cell.is_spanned:
                continue
            span = cell.span_width if cell.is_merge_origin else 1
            w = sum(widths[ci:ci + span])
            lr = _in(cell.margin_left) + _in(cell.margin_right)
            tb = _in(cell.margin_top) + _in(cell.margin_bottom)
            h = 0.0
            for p in cell.text_frame.paragraphs:
                size = _para_size(p)
                if size is None:
                    if p.text.strip():
                        problems.append(f"R{ri}C{ci} has no explicit font size")
                    continue
                floor = L.TABLE_DELIVERABLES_MIN_PT if (slide_no == 3 and ci == 3 and ri > 0) else L.TABLE_BODY_MIN_PT
                if size < floor - 1e-6:
                    problems.append(f"R{ri}C{ci} font {size:g} pt is below the {floor:g} pt minimum")
                h += L.text_height_pt(p.text, w - lr, size) / 72.0
            row_h = max(row_h, h + tb)
        total += row_h
    return total, problems


def check_inv32(prs: Any) -> List[InvariantViolation]:
    """INV-32: bounds, overlaps, fit estimate, card text frames, and minimum fonts."""
    v: List[InvariantViolation] = []
    for idx, slide in enumerate(prs.slides, start=1):
        if idx == 1:
            continue
        content = [sh for sh in slide.shapes if not sh.is_placeholder]
        cards = [sh for sh in content if _is_card(sh)]
        rects: Dict[int, Tuple[float, float, float, float]] = {}

        for sh in content:
            x0, y0, x1, y1 = _rect(sh)
            if getattr(sh, "has_table", False) and sh.has_table:
                est, problems = _table_estimate(sh, idx)
                y1 = max(y1, y0 + est)
                for pr in problems:
                    v.append(_inv("INV-32", f"Slide {idx} table '{sh.name}': {pr}"))
            rects[id(sh)] = (x0, y0, x1, y1)
            if x0 < L.CONTENT_X0 - EPS or x1 > L.CONTENT_X1 + EPS or y0 < L.CONTENT_Y0 - EPS or y1 > L.CONTENT_Y1 + EPS:
                v.append(_inv("INV-32", f"Slide {idx} shape '{sh.name}' lies outside the content area (x {x0:.2f}-{x1:.2f}, y {y0:.2f}-{y1:.2f}; allowed x {L.CONTENT_X0}-{L.CONTENT_X1}, y {L.CONTENT_Y0}-{L.CONTENT_Y1})"))

        # overlaps: only a card and shapes fully inside it may overlap
        for i, a in enumerate(content):
            for b in content[i + 1:]:
                ax0, ay0, ax1, ay1 = rects[id(a)]
                bx0, by0, bx1, by1 = rects[id(b)]
                ox, oy = min(ax1, bx1) - max(ax0, bx0), min(ay1, by1) - max(ay0, by0)
                if ox <= EPS or oy <= EPS:
                    continue

                def inside(inner, outer) -> bool:
                    return inner[0] >= outer[0] - EPS and inner[1] >= outer[1] - EPS and inner[2] <= outer[2] + EPS and inner[3] <= outer[3] + EPS

                if (_is_card(a) and inside(rects[id(b)], rects[id(a)])) or (_is_card(b) and inside(rects[id(a)], rects[id(b)])):
                    continue
                v.append(_inv("INV-32", f"Slide {idx} shapes '{a.name}' and '{b.name}' overlap"))

        # text frames
        for sh in content:
            if not sh.has_text_frame or not sh.text_frame.text.strip() or _is_card(sh):
                continue
            tf = sh.text_frame
            in_card = next((c for c in cards if (_rect(sh)[0] >= _rect(c)[0] - EPS and _rect(sh)[2] <= _rect(c)[2] + EPS and _rect(sh)[1] >= _rect(c)[1] - EPS and _rect(sh)[3] <= _rect(c)[3] + EPS)), None)
            paras = tf.paragraphs
            est_paras: List[L.Para] = []
            for pi, p in enumerate(paras):
                if not p.text.strip():
                    continue
                ep = _para_for_estimate(p)
                if ep is None:
                    v.append(_inv("INV-32", f"Slide {idx} text frame '{sh.name}' paragraph {pi + 1} has no explicit font size: '{p.text[:50]}'"))
                    continue
                floor = (L.CARD_HEADING_MIN_PT if pi == 0 and in_card is not None else L.BODY_MIN_PT)
                if ep.size_pt < floor - 1e-6:
                    v.append(_inv("INV-32", f"Slide {idx} text frame '{sh.name}' paragraph {pi + 1} font {ep.size_pt:g} pt is below the {floor:g} pt minimum"))
                est_paras.append(ep)
            width = _in(sh.width) - _in(tf.margin_left) - _in(tf.margin_right)
            height = _in(sh.height) - _in(tf.margin_top) - _in(tf.margin_bottom)
            need = L.frame_height_pt(est_paras, width)
            if need > height * 72.0 + 1e-6:
                v.append(_inv("INV-32", f"Slide {idx} text frame '{sh.name}' needs about {need / 72.0:.2f} in but has {height:.2f} in (fit estimate)"))
            if in_card is not None:
                first = next((p for p in paras if p.text.strip()), None)
                fp = _para_for_estimate(first) if first is not None else None
                if fp is not None and L.wrap_lines(fp.text, width, fp.size_pt) > 1:
                    v.append(_inv("INV-32", f"Slide {idx} card heading '{first.text}' wraps to more than one line"))
                cx0, cy0, cx1, cy1 = _rect(in_card)
                sx0, sy0, sx1, sy1 = _rect(sh)
                shares_card = any(
                    getattr(t, "has_table", False) and t.has_table and _rect(t)[0] >= cx0 - EPS and _rect(t)[2] <= cx1 + EPS and _rect(t)[1] >= cy0 - EPS and _rect(t)[3] <= cy1 + EPS
                    for t in content
                )
                edges = [(sx0 - cx0, L.CARD_INSET), (sy0 - cy0, L.CARD_INSET), (cx1 - sx1, L.CARD_INSET)]
                if not shares_card:
                    edges.append((cy1 - sy1, L.CARD_INSET))
                inset_ok = all(abs(a - b) <= 0.015 for a, b in edges)
                if not inset_ok:
                    v.append(_inv("INV-32", f"Slide {idx} card text frame '{sh.name}' is not inset {L.CARD_INSET} in from its card"))
                if not tf.word_wrap or tf.auto_size not in (MSO_AUTO_SIZE.NONE,) or tf.vertical_anchor != MSO_ANCHOR.TOP:
                    v.append(_inv("INV-32", f"Slide {idx} card text frame '{sh.name}' must have word wrap on, autofit off, and top anchor"))
    return v


# =================================================================================================
# INV-30: Workbook RAID matches Kit RAID
# =================================================================================================
RAID_FIELDS = ("Probability", "Impact", "Owner", "Mitigation / Response", "Trigger / Early Warning", "Status")


def check_inv30(kit_doc: Optional[Any], wb: Optional[Any]) -> List[InvariantViolation]:
    """INV-30 (RAID-09): every Workbook RAID row sourced from a Kit risk or issue matches the Kit RAID Log."""
    if kit_doc is None or wb is None or "RAID Log" not in wb.sheetnames:
        return []
    from src.generators.pmo_workbook.builder import (
        _normalize_rating_v2,
        _normalize_status_v2,
        clean_text_v2,
        normalize_owner_v2,
    )

    index = SourceIndex(kit_doc, wb)
    kit_rows: Dict[str, Dict[str, str]] = {}
    for tables in index.kit_sections.values():
        for t in tables:
            if t and t[0] and normalize_text(t[0][0]) == "Item ID" and "Probability" in [normalize_text(h) for h in t[0]]:
                hdr = [normalize_text(h) for h in t[0]]
                for r in t[1:]:
                    kit_rows[normalize_text(r[0])] = dict(zip(hdr, r))
    info = index.sheets["RAID Log"]
    if info["header_idx"] is None or "Source ID" not in info["headers"]:
        return [InvariantViolation("INV-30", "Workbook RAID Log has no Source ID column", "Workbook")]
    h = info["headers"]
    v: List[InvariantViolation] = []
    for r in info["rows"][info["header_idx"] + 1:]:
        raid_id = r[h["RAID ID"]] if "RAID ID" in h else ""
        src_ids = [s for s in re.split(r"[,;/\s]+", r[h["Source ID"]]) if s.startswith(("RSK-", "ISS-"))]
        for sid in src_ids:
            kit = kit_rows.get(sid)
            if kit is None:
                v.append(InvariantViolation("INV-30", f"{raid_id} Source ID '{sid}' is not in the Kit RAID Log", "Workbook"))
                continue
            expected = {
                "Probability": _normalize_rating_v2(clean_text_v2(kit.get("Probability")))[0],
                "Impact": _normalize_rating_v2(clean_text_v2(kit.get("Impact")))[0],
                "Owner": normalize_owner_v2(clean_text_v2(kit.get("Owner")))[0],
                "Mitigation / Response": clean_text_v2(kit.get("Mitigation / Response")),
                "Status": _normalize_status_v2(clean_text_v2(kit.get("Status")))[0],
            }
            if "Trigger / Early Warning" in kit:  # the written Kit RAID Log has no such column unless the Kit adds one
                expected["Trigger / Early Warning"] = clean_text_v2(kit.get("Trigger / Early Warning"))
            for fld, exp in expected.items():
                if fld not in h:
                    v.append(InvariantViolation("INV-30", f"Workbook RAID Log has no '{fld}' column", "Workbook"))
                    continue
                got = normalize_text(r[h[fld]])
                if got != normalize_text(exp):
                    v.append(InvariantViolation("INV-30", f"{raid_id} ({sid}) {fld} is '{got}' but the Kit RAID Log says '{normalize_text(exp)}' (RAID-09)", "Workbook"))
    return v
