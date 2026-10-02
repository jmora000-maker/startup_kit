"""Pure builder for the DeckModel: StartupKitBaseline and WorkbookModel in, slide specifications out (DECK-03, Appendix K.2).

No file I/O and no LLM calls. Every fact is taken from content that the written Kit or Workbook
displays (DECK-19), shown whole or cut only at a clause boundary (DECK-05), and carries TraceRefs
whose keys exist in the source (DECK-04). Sizes and capacities follow DECK-21 (layout and fit).
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from src.core.models import StartupKitBaseline
from src.generators.kit_values import kit_header_values, kit_sanitize_filename
from src.generators.formatting import sanitize_filename
from src.generators.onboarding_deck import fixed_text as FT
from src.generators.onboarding_deck import layout as L
from src.generators.onboarding_deck import talking_points as TP
from src.generators.onboarding_deck.spec import (
    BODY,
    BULLET,
    HEADING,
    ITALIC,
    LABEL,
    MORE,
    MUTED,
    PLACEHOLDER,
    STRONG,
    SUBHEADING,
    TEXT,
    CardSpec,
    CellSpec,
    CoverSpec,
    DeckModel,
    ParaSpec,
    RowSpec,
    Run,
    SlideSpec,
    TableSpec,
    TextBoxSpec,
)
from src.generators.onboarding_deck.textrules import (
    clause_prefix,
    first_sentence,
    is_placeholder_text,
    normalize_text,
    word_count,
)
from src.generators.onboarding_deck.trace import KIT, WORKBOOK, DeckTraceManifest, TraceRef
from src.generators.pmo_workbook.builder import build_workbook_model, check_acceptance_mode
from src.generators.pmo_workbook.rows import RAIDRow, ScheduleRow, WBSRow, WorkbookModel

DEFENSIVE_FILTER_REGEX = re.compile(
    r"\b(G-?01|g01|readiness\s+gate|startup\s+readiness|readiness\s+checklist|readiness\s+score|gate\s+decision|gate\s+approval|startup\s+kit|mobiliz\w*|ACT-\d+)\b",
    re.IGNORECASE,
)

# Kit sections and Workbook sheets
HDR = FT.HEADER_TABLE
SEC_CHARTER = "Project Startup Charter"
SEC_SOW = "SOW Interpretation Summary"
SEC_DELIV = "Deliverables and Acceptance Matrix"
SEC_COMMS = "Communications and Reporting Plan"
SEC_STAKE = "Stakeholder and Responsibility Model"
PS, WBS, RAID = "Project Schedule", "WBS", "RAID Log"
CHARTER_VALUE_FIELD = "Charter Commitment & Governance Baseline"
SOW_VALUE_FIELD = "Contractual Summary & Operational Meaning"

MAX_BULLET_WORDS = 15
SCORE = {"High": 3, "Medium": 2, "Low": 1}


def compute_deck20_rating(probability: str, impact: str) -> str:
    """Rating per DECK-20."""
    p, i = (probability or "").strip().capitalize(), (impact or "").strip().capitalize()
    if (p == "High" and i in ("High", "Medium")) or (i == "High" and p in ("High", "Medium")):
        return "High"
    if p == "Low" and i == "Low":
        return "Low"
    return "Medium"


def compute_deck20_score(probability: str, impact: str) -> int:
    return SCORE.get((probability or "").strip().capitalize(), 1) * SCORE.get((impact or "").strip().capitalize(), 1)


# =================================================================================================
# Run and paragraph helpers
# =================================================================================================
def T(artifact: str, locator: str, key: str, field: str) -> TraceRef:
    return TraceRef(artifact, locator, key, field)


def plain(text: str, kind: str = TEXT) -> Run:
    """Fixed text written by the tool (a label, a separator): no TraceRef."""
    return Run(text, kind)


def traced(text: str, *refs: TraceRef, kind: str = TEXT, element: str = "", derived: Optional[str] = None) -> Run:
    return Run(text, kind, list(refs), element, derived)


def value_run(raw: Optional[str], refs: Sequence[TraceRef], element: str, kind: str = TEXT, shown: Optional[str] = None) -> Run:
    """A traced value; a placeholder reads `To be confirmed` in italic accent blue (DECK-10)."""
    if is_placeholder_text(raw):
        return traced(FT.PLACEHOLDER_TEXT, *refs, kind=PLACEHOLDER, element=element)
    return traced(shown if shown is not None else normalize_text(raw), *refs, kind=kind, element=element)


def para(kind: str, *runs: Run) -> ParaSpec:
    return ParaSpec(kind, list(runs))


def clean_bullet(text: str) -> str:
    return re.sub(r"^[•\-\*]\s*", "", text or "").strip()


def see_more(n: int, artifact_label: str, locator: Optional[str] = None) -> Run:
    tail = f"{artifact_label} · {locator}" if locator else artifact_label
    return plain(f"+{n} more (see {tail})", MUTED)


# =================================================================================================
# Fit estimates (DECK-21 (5))
# =================================================================================================
def _para_estimates(card: CardSpec, paras: List[ParaSpec]) -> List[L.Para]:
    out = [L.Para(card.heading, card.heading_pt, 0.0, L.HEADING_SPACE_AFTER_PT)]
    for p in paras:
        if p.kind == SUBHEADING:
            out.append(L.Para(p.text, L.CARD_SUBHEADING_PT, L.SUBHEADING_SPACE_BEFORE_PT, L.SUBHEADING_SPACE_AFTER_PT))
        elif p.kind == BULLET:
            out.append(L.Para(p.text, card.body_pt, 0.0, L.BODY_SPACE_AFTER_PT, L.BULLET_INDENT_IN))
        else:
            out.append(L.Para(p.text, card.body_pt, 0.0, L.BODY_SPACE_AFTER_PT))
    return out


@dataclass
class Block:
    """A card block: one paragraph, or a bullet group that may show fewer items with a `+N more` line."""
    paras: List[ParaSpec]
    items: Optional[List[ParaSpec]] = None
    more: Optional[Callable[[int], Run]] = None
    shown: int = 0

    def render(self) -> List[ParaSpec]:
        if self.items is None:
            return list(self.paras)
        out = list(self.paras) + self.items[:self.shown]
        omitted = len(self.items) - self.shown
        if omitted > 0 and self.more is not None:
            out.append(para(MORE, self.more(omitted)))
        return out


def fixed_block(*paras: ParaSpec) -> Block:
    return Block(list(paras))


def bullet_block(heading_paras: List[ParaSpec], items: List[ParaSpec], capacity: int, more: Callable[[int], Run]) -> Block:
    return Block(heading_paras, items, more, min(len(items), capacity))


def _render(blocks: List[Block]) -> List[ParaSpec]:
    out: List[ParaSpec] = []
    for b in blocks:
        out.extend(b.render())
    return out


def fit_card(card: CardSpec, blocks: List[Block], min_h: float = L.CARD_H) -> CardSpec:
    """Choose the card height and font, then the bullets shown, so the text frame fits (DECK-21 (5)).

    Order: body 11 pt, then 10.5 pt, at the template card height; then the same at the full content
    height; then fewer bullets with a `+N more` line. Text is never cut and never shrinks below 10.5 pt.
    """
    card.heading_pt = L.CARD_HEADING_PT
    if L.wrap_lines(card.heading, L.card_inner(card.w)[0], card.heading_pt) > 1:
        card.heading_pt = L.CARD_HEADING_MIN_PT
    for height in sorted({min_h, L.CONTENT_HEIGHT}):
        inner_w, inner_h = L.card_inner(card.w, height)
        for body_pt in (L.BODY_PT, L.BODY_MIN_PT):
            card.body_pt = body_pt
            paras = _render(blocks)
            if L.frame_fits(_para_estimates(card, paras), inner_w, inner_h):
                card.h, card.paras = height, paras
                return card
    card.h = L.CONTENT_HEIGHT
    card.body_pt = L.BODY_MIN_PT
    inner_w, inner_h = L.card_inner(card.w, card.h)
    droppable = [b for b in blocks if b.items is not None]
    while True:
        paras = _render(blocks)
        if L.frame_fits(_para_estimates(card, paras), inner_w, inner_h):
            break
        candidates = [b for b in droppable if b.shown > 1]
        if not candidates:
            break
        candidates[-1].shown -= 1
    card.paras = paras
    return card


def _text_h(card_paras: List[L.Para], width: float) -> float:
    return L.frame_height_pt(card_paras, width) / 72.0


# =================================================================================================
# Tables
# =================================================================================================
def _cell(*lines: List[Run], fill: Optional[str] = None, text_color: Optional[str] = None, bold: bool = False) -> CellSpec:
    return CellSpec([list(l) for l in lines], fill, text_color, bold)


def _row_height(row: RowSpec, widths: Sequence[float], sizes: Sequence[float]) -> float:
    if row.overflow:
        return L.row_height_in([row.cells[0].text], [sum(widths)], [sizes[0]])
    return L.row_height_in([c.text for c in row.cells], widths, sizes)


def size_table(table: TableSpec) -> None:
    """Set each row's height from the fit estimate."""
    sizes = [table.body_pt] * len(table.col_widths)
    if table.deliverables_pt is not None:
        sizes[-1] = table.deliverables_pt
    for r in table.rows:
        r.height = _row_height(r, table.col_widths, sizes)


def fit_rows(
    table: TableSpec,
    all_rows: List[RowSpec],
    capacity: int,
    overflow: Callable[[List[RowSpec]], RowSpec],
    avail_h: float,
) -> int:
    """Show as many rows as fit within `capacity` and `avail_h`; the rest go into one merged `+N more` row.

    Returns the number of rows omitted.
    """
    n = min(len(all_rows), capacity)
    while True:
        shown = all_rows[:n]
        rows = list(shown)
        if n < len(all_rows):
            rows.append(overflow(all_rows[n:]))
        table.rows = rows
        size_table(table)
        if table.height <= avail_h + 1e-6 or n <= 1:
            return len(all_rows) - n
        n -= 1


# =================================================================================================
# The model
# =================================================================================================
@dataclass
class _Ctx:
    baseline: StartupKitBaseline
    wb: WorkbookModel
    hv: dict
    start_iso: str
    start_basis: str


def _date(d: Optional[date]) -> str:
    return d.isoformat() if d else ""


def _slide_sources(slide: SlideSpec) -> List[Tuple[str, str]]:
    refs: List[Tuple[str, str]] = []

    def add(ts):
        for t in ts:
            if (t.artifact, t.locator) not in refs and t.locator not in ("File name",):
                refs.append((t.artifact, t.locator))

    for c in slide.cards:
        for p in c.paras:
            for r in p.runs:
                add(r.traces)
        if c.table:
            for row in c.table.rows:
                for cell in row.cells:
                    for line in cell.paras:
                        for r in line:
                            add(r.traces)
    for t in slide.tables:
        for row in t.rows:
            for cell in row.cells:
                for line in cell.paras:
                    for r in line:
                        add(r.traces)
    for _, refs_tp, _v in slide.talking_points:
        add(refs_tp)
    return refs


def sources_line(refs: Sequence[Tuple[str, str]]) -> str:
    """`Startup Kit · sections; Project Delivery Workbook · sheets` for the SOURCES line (DECK-09)."""
    kit = [loc for art, loc in refs if art == KIT]
    sheets = [loc for art, loc in refs if art == WORKBOOK]
    kit_named = [s for s in FT.KIT_SECTION_ORDER if s in kit]
    if HDR in kit:
        kit_named = ["header table"] + kit_named
    sheet_named = [s for s in FT.SHEET_ORDER if s in sheets]
    parts = []
    if kit_named:
        parts.append(f"{FT.KIT_LABEL} · {', '.join(kit_named)}")
    if sheet_named:
        parts.append(f"{FT.WORKBOOK_LABEL} · {', '.join(sheet_named)}")
    return "; ".join(parts)


def _pick(options: List[Tuple[str, List[str], List[TraceRef]]]) -> Optional[Tuple[str, List[str], List[TraceRef]]]:
    """The first talking-point option that fits the 30-word limit (DECK-08)."""
    for text, values, refs in options:
        if word_count(text) <= TP.MAX_TALKING_POINT_WORDS:
            return text, values, refs
    return None


def build_deck_model(
    baseline: StartupKitBaseline,
    workbook_model: Optional[WorkbookModel] = None,
    start_date: Optional[date] = None,
) -> DeckModel:
    """Build the pure DeckModel from the baseline and the WorkbookModel (DECK-03, Appendix K.2)."""
    wb = workbook_model if workbook_model is not None else build_workbook_model(baseline, start_date=start_date)
    hv = kit_header_values(baseline)
    ctx = _Ctx(baseline, wb, hv, wb.start_date.isoformat(), wb.start_date_basis)
    project = hv["project_name"] or "Project"
    kicker = f"{project.upper()} · {FT.KICKER_SUFFIX}"
    manifest = DeckTraceManifest(project_name=project)

    cover = _build_cover(ctx, project)
    slides: List[SlideSpec] = [
        _build_charter(ctx, kicker),
        _build_schedule(ctx, kicker),
        _build_acceptance(ctx, kicker),
        _build_risks(ctx, kicker),
        _build_collaboration(ctx, kicker),
    ]
    kit_file = f"{kit_sanitize_filename(project)}_Startup_Kit.docx"
    wb_file = f"{sanitize_filename(project)}_Project_Delivery_Workbook.xlsx"
    slides.append(_build_project_kit(ctx, kicker, slides, cover, kit_file, wb_file))

    overflow_rows = 0
    for s in slides:
        s.sources = _slide_sources(s)
    for s in slides[:-1]:
        s.notes = TP.build_notes([t for t, _r, _v in s.talking_points], sources_line(s.sources))
    cover.notes = TP.build_notes([t for t, _r, _v in cover.talking_points], sources_line(_cover_sources(cover)))
    last = slides[-1]
    last.notes = TP.build_notes([t for t, _r, _v in last.talking_points], sources_line(last.sources))

    _register_manifest(manifest, cover, slides)
    for s in slides:
        for t in s.tables:
            overflow_rows += sum(1 for r in t.rows if r.overflow)
        for c in s.cards:
            overflow_rows += sum(1 for p in c.paras if p.kind == MORE)
    return DeckModel(project, hv["client_sponsor"], cover, slides, manifest, kit_file, wb_file, overflow_rows)


def _cover_sources(cover: CoverSpec) -> List[Tuple[str, str]]:
    refs: List[Tuple[str, str]] = []
    for r in [cover.title] + cover.subtitle_runs:
        for t in r.traces:
            if (t.artifact, t.locator) not in refs:
                refs.append((t.artifact, t.locator))
    return refs


# =================================================================================================
# Slide 1: Cover
# =================================================================================================
def _build_cover(ctx: _Ctx, project: str) -> CoverSpec:
    hv = ctx.hv
    title = traced(project, T(KIT, HDR, "Project Name", "Project Name"), element="Project name")
    sponsor_ref = T(KIT, HDR, "Client Sponsor", "Client Sponsor")
    start_ref = T(WORKBOOK, PS, "Start Date", "Start Date")
    subtitle = [
        plain(f"{FT.COVER_SUBTITLE_PREFIX} · "),
        traced(hv["client_sponsor"], sponsor_ref, element="Client Sponsor"),
        plain(" · Start "),
        traced(ctx.start_iso, start_ref, element="Start Date"),
    ]
    points: List[Tuple[str, List[TraceRef], List[str]]] = [(TP.COVER_GUIDANCE[0], [], [])]
    points.append((
        TP.cover_project_and_client(project, hv["client_sponsor"]),
        [T(KIT, HDR, "Project Name", "Project Name"), sponsor_ref],
        [project, hv["client_sponsor"]],
    ))
    points.append((
        TP.cover_start_date(ctx.start_iso, ctx.start_basis),
        [start_ref, start_ref],
        [ctx.start_iso, ctx.start_basis],
    ))
    return CoverSpec(title, subtitle, "", points)


# =================================================================================================
# Slide 2: Project Charter
# =================================================================================================
def _build_charter(ctx: _Ctx, kicker: str) -> SlideSpec:
    b, hv, wb = ctx.baseline, ctx.hv, ctx.wb
    charter, sow = b.charter, b.sow_interpretation
    x1, x2, x3 = L.THREE_ACROSS_X
    w = L.THREE_ACROSS_W

    # ---- Card 1: Key facts (a key-value table inside the card) --------------------------------
    sponsor_ref = T(KIT, HDR, "Client Sponsor", "Client Sponsor")
    start_ref = T(WORKBOOK, PS, "Start Date", "Start Date")
    facts: List[Tuple[str, Run]] = [
        ("Client Sponsor", value_run(hv["client_sponsor"], [sponsor_ref], "Key fact: Client Sponsor")),
        ("Contract Type", value_run(hv["contract_type"], [T(KIT, HDR, "Contract Type", "Contract Type")], "Key fact: Contract Type")),
        ("Governance Tier", value_run(hv["governance_tier"], [T(KIT, HDR, "Governance Tier", "Governance Tier")], "Key fact: Governance Tier")),
        ("Start Date", traced(f"{ctx.start_iso} ({ctx.start_basis})", start_ref, element="Key fact: Start Date")),
        ("Talent PM", value_run(hv["talent_pm"], [T(KIT, HDR, "Talent PM", "Talent PM")], "Key fact: Talent PM")),
        ("Delivery Manager", value_run(hv["delivery_manager"], [T(KIT, HDR, "Delivery Manager", "Delivery Manager")], "Key fact: Delivery Manager")),
        ("PMO Lead", value_run(hv["pmo_lead"], [T(KIT, HDR, "PMO Lead", "PMO Lead")], "Key fact: PMO Lead")),
    ]
    c1 = CardSpec("Key facts", x1, L.CONTENT_Y0, w, L.CARD_H)
    kf_rows = [RowSpec([_cell([plain(label, STRONG)]), _cell([run])]) for label, run in facts]
    kf = TableSpec(c1.table_name, x1 + L.CARD_INSET, 0.0, list(L.KEY_FACTS_COLS), None, kf_rows, key_value=True)
    size_table(kf)
    c1.table = kf

    # ---- Card 2: Purpose & delivery -----------------------------------------------------------
    c2 = CardSpec("Purpose & delivery", x2, L.CONTENT_Y0, w, L.CARD_H)
    blocks2: List[Block] = []
    purpose_text = delivery_text = escalation_text = None
    if charter is not None:
        purpose_text = charter.project_purpose
        delivery_text = f"Delivery: {charter.delivery_model} | Governance: {charter.governance_model}"
        escalation_text = charter.escalation_path
        spec = (
            ("Purpose", "Project Purpose & Delivery Baseline", purpose_text, True),
            ("Delivery model", "Delivery Model & Governance Tier", delivery_text, False),
            ("Escalation path", "Escalation Path & Decision Hierarchy", escalation_text, False),
        )
        for sub, key, raw, sentence_only in spec:
            ref = T(KIT, SEC_CHARTER, key, CHARTER_VALUE_FIELD)
            shown = first_sentence(raw) if sentence_only and not is_placeholder_text(raw) else normalize_text(raw)
            blocks2.append(fixed_block(para(SUBHEADING, plain(sub)), para(BODY, value_run(raw, [ref], sub, shown=shown))))
    else:
        blocks2.append(fixed_block(para(BODY, plain(FT.NONE_IN_KIT))))
    fit_card(c2, blocks2)

    # ---- Card 3: Phases & scope ---------------------------------------------------------------
    c3 = CardSpec("Phases & scope", x3, L.CONTENT_Y0, w, L.CARD_H)
    phase_items: List[ParaSpec] = []
    for r in wb.schedule_rows:
        if r.row_type == "Workstream" and r.workstream:
            phase_items.append(para(BULLET, traced(r.workstream, T(WORKBOOK, PS, r.wbs_code, "Workstream"), element=f"Phase {r.wbs_code}")))
    exc_items: List[ParaSpec] = []
    if sow is not None:
        for exc in sow.out_of_scope_items or []:
            clean = clean_bullet(exc)
            if not clean or DEFENSIVE_FILTER_REGEX.search(clean):
                continue
            shown = clause_prefix(clean, MAX_BULLET_WORDS)
            exc_items.append(para(BULLET, traced(shown, T(KIT, SEC_SOW, "Explicit Exclusions & Out-of-Scope", SOW_VALUE_FIELD), element="Out of scope")))
    blocks3: List[Block] = []
    if phase_items:
        blocks3.append(bullet_block([para(SUBHEADING, plain("Phases"))], phase_items, 4, lambda n: see_more(n, FT.WORKBOOK_LABEL, PS)))
    else:
        blocks3.append(fixed_block(para(SUBHEADING, plain("Phases")), para(BODY, plain(FT.NONE_IN_WORKBOOK))))
    if exc_items:
        blocks3.append(bullet_block([para(SUBHEADING, plain("Out of scope"))], exc_items, 4, lambda n: see_more(n, FT.KIT_LABEL, SEC_SOW)))
    else:
        blocks3.append(fixed_block(para(SUBHEADING, plain("Out of scope")), para(BODY, plain(FT.NONE_IN_KIT))))
    fit_card(c3, blocks3)

    # one height for the three cards of a row
    h = max(c1.h, c2.h, c3.h)
    for c in (c1, c2, c3):
        c.h = h
    kf.y = round(c1.y + L.CARD_INSET + 0.40, 2)

    slide = SlideSpec(2, FT.SLIDE_TITLES[2], kicker, cards=[c1, c2, c3])
    _charter_points(ctx, slide, purpose_text, escalation_text, phase_items)
    return slide


def _charter_points(ctx: _Ctx, slide: SlideSpec, purpose_text, escalation_text, phase_items) -> None:
    hv, wb = ctx.hv, ctx.wb
    pts = slide.talking_points
    purpose_ref = T(KIT, SEC_CHARTER, "Project Purpose & Delivery Baseline", CHARTER_VALUE_FIELD)
    if purpose_text and not is_placeholder_text(purpose_text):
        sent = first_sentence(purpose_text)
        got = _pick([
            (TP.charter_purpose(sent), [sent], [purpose_ref]),
            (TP.charter_purpose(clause_prefix(sent, 22)), [clause_prefix(sent, 22)], [purpose_ref]),
        ])
        if got:
            pts.append((got[0], got[2], got[1]))
    ct_ref, gt_ref = T(KIT, HDR, "Contract Type", "Contract Type"), T(KIT, HDR, "Governance Tier", "Governance Tier")
    pts.append((TP.charter_contract_and_tier(hv["contract_type"], hv["governance_tier"]), [ct_ref, gt_ref], [hv["contract_type"], hv["governance_tier"]]))
    roles = [("delivery_manager", "Delivery Manager"), ("talent_pm", "Talent PM"), ("pmo_lead", "PMO Lead")]
    spoken, refs, vals = [], [], []
    for key, label in roles:
        ph = is_placeholder_text(hv[key])
        spoken.append(TP.spoken(normalize_text(hv[key]), ph))
        refs.append(T(KIT, HDR, label, label))
        vals.append(FT.PLACEHOLDER_TEXT if ph else normalize_text(hv[key]))
    pts.append((TP.charter_leads(*spoken), refs, vals))
    if escalation_text and not is_placeholder_text(escalation_text):
        esc = normalize_text(escalation_text)
        esc_ref = T(KIT, SEC_CHARTER, "Escalation Path & Decision Hierarchy", CHARTER_VALUE_FIELD)
        pts.append((TP.charter_escalation(esc), [esc_ref], [esc]))
    start_ref = T(WORKBOOK, PS, "Start Date", "Start Date")
    pts.append((TP.charter_start_date(ctx.start_iso, ctx.start_basis), [start_ref, start_ref], [ctx.start_iso, ctx.start_basis]))
    span = _phase_span(wb)
    if span:
        n, first_ref, last_ref, first, last = span
        pts.append((TP.phases_and_span(n, first, last), [first_ref, last_ref], [first, last]))


def _gates(wb: WorkbookModel) -> List[ScheduleRow]:
    return [r for r in wb.schedule_rows if r.row_type == "Milestone"]


def _phase_span(wb: WorkbookModel):
    gates = _gates(wb)
    phases = [r for r in wb.schedule_rows if r.row_type == "Workstream" and r.workstream]
    starts = [g for g in gates if g.planned_start]
    finishes = [g for g in gates if g.planned_finish]
    if not phases or not starts or not finishes:
        return None
    first, last = starts[0], finishes[-1]
    return (
        len(phases),
        T(WORKBOOK, PS, first.milestone_id, "Planned Start"),
        T(WORKBOOK, PS, last.milestone_id, "Planned Finish"),
        _date(first.planned_start),
        _date(last.planned_finish),
    )


# =================================================================================================
# Slide 3: Workstreams, Milestones, Deliverables and Dates
# =================================================================================================
def _build_schedule(ctx: _Ctx, kicker: str) -> SlideSpec:
    b, wb = ctx.baseline, ctx.wb
    names = {d.id: (d.name or d.description) for d in b.deliverables}
    level2 = [r for r in wb.schedule_rows if r.row_type in ("Milestone", "Checkpoint")]
    show_names = len(b.deliverables) <= 20

    def build_rows(with_names: bool) -> List[RowSpec]:
        rows: List[RowSpec] = []
        prev_ws = None
        for r in level2:
            key = r.milestone_id
            ws_cell = _cell([traced(r.workstream, T(WORKBOOK, PS, key, "Workstream"), element="Workstream")]) if r.workstream != prev_ws else _cell([])
            prev_ws = r.workstream
            kind = ITALIC if r.row_type == "Checkpoint" else STRONG
            ms_cell = _cell([
                traced(key, T(WORKBOOK, PS, key, "Milestone ID"), kind=kind, element="Milestone ID"),
                plain(": ", kind),
                traced(r.name, T(WORKBOOK, PS, key, "Milestone"), kind=ITALIC if r.row_type == "Checkpoint" else TEXT, element="Milestone"),
            ])
            start, finish = _date(r.planned_start), _date(r.planned_finish)
            if start and finish:
                dates_cell = _cell([
                    traced(start, T(WORKBOOK, PS, key, "Planned Start"), element="Planned Start"),
                    plain(" – "),
                    traced(finish, T(WORKBOOK, PS, key, "Planned Finish"), element="Planned Finish"),
                ])
            else:
                dates_cell = _cell([[traced(FT.PLACEHOLDER_TEXT, T(WORKBOOK, PS, key, "Planned Finish"), kind=PLACEHOLDER, element="Dates")][0]])
            lines: List[List[Run]] = []
            for did in [x.strip() for x in (r.linked_deliverables or "").split(",") if x.strip()]:
                refs = [T(WORKBOOK, PS, key, "Linked Deliverables"), T(KIT, SEC_DELIV, did, "ID")]
                id_run = traced(did, *refs, kind=STRONG, element="Deliverable ID")
                if with_names and names.get(did):
                    lines.append([id_run, plain(" "), traced(names[did], T(KIT, SEC_DELIV, did, "Deliverable Name"), element="Deliverable name")])
                else:
                    lines.append([id_run])
            deliv_cell = _cell(*lines) if lines else _cell([plain("—")])
            rows.append(RowSpec([ws_cell, ms_cell, dates_cell, deliv_cell]))
        return rows

    def overflow(omitted: List[RowSpec]) -> RowSpec:
        runs: List[Run] = [plain(f"+{len(omitted)} more: ", MUTED)]
        ids: List[Tuple[str, TraceRef]] = []
        for row in omitted:
            for line in [row.cells[1].paras[0]] + row.cells[3].paras:
                for run in line:
                    if run.element in ("Milestone ID", "Deliverable ID") and run.traces:
                        ids.append((run.text, run.traces[-1] if run.element == "Deliverable ID" else run.traces[0]))
        for i, (text, ref) in enumerate(ids):
            if i:
                runs.append(plain(", ", MUTED))
            runs.append(traced(text, ref, kind=MUTED, element="Omitted ID"))
        runs.append(plain(f" (see {FT.WORKBOOK_LABEL} · {PS})", MUTED))
        return RowSpec([_cell(runs)] + [_cell([]) for _ in range(3)], overflow=True)

    table = TableSpec("Table: Schedule", L.CONTENT_X0, L.CONTENT_Y0, list(L.SCHEDULE_COLS), list(FT.TABLE_HEADERS[3]), [], deliverables_pt=L.TABLE_BODY_PT)
    avail = round(L.CONTENT_Y1 - table.y, 2)
    omitted = 0
    plans = [(True, L.TABLE_BODY_PT), (True, L.TABLE_DELIVERABLES_MIN_PT), (False, L.TABLE_BODY_PT)] if show_names else [(False, L.TABLE_BODY_PT)]
    for with_names, pt in plans:
        table.deliverables_pt = pt
        all_rows = build_rows(with_names)
        omitted = fit_rows(table, all_rows, 12, overflow, avail)
        if omitted == 0:
            break
    slide = SlideSpec(3, FT.SLIDE_TITLES[3], kicker, tables=[table])
    _schedule_points(ctx, slide, level2)
    return slide


def _schedule_points(ctx: _Ctx, slide: SlideSpec, level2: List[ScheduleRow]) -> None:
    wb = ctx.wb
    pts = slide.talking_points
    span = _phase_span(wb)
    if span:
        n, first_ref, last_ref, first, last = span
        pts.append((TP.phases_and_span(n, first, last), [first_ref, last_ref], [first, last]))
    gates = _gates(wb)
    checkpoints = [r for r in level2 if r.row_type == "Checkpoint"]
    reserved = 1 + (1 if gates else 0) + (1 if checkpoints else 0)
    gate_slots = max(0, 6 - len(pts) - (reserved - 1 if gates else reserved))
    for g in gates[:gate_slots]:
        if not g.planned_finish:
            continue
        key = g.milestone_id
        pred = (g.predecessor or "").strip() or None
        refs = [T(WORKBOOK, PS, key, "Milestone ID"), T(WORKBOOK, PS, key, "Workstream"), T(WORKBOOK, PS, key, "Planned Finish")]
        vals = [key, g.workstream, _date(g.planned_finish)]
        if pred:
            refs.append(T(WORKBOOK, PS, key, "Predecessor"))
            vals.append(pred)
        pts.append((TP.gate_due(key, g.workstream, _date(g.planned_finish), pred), refs, vals))
    if gates and gates[0].date_basis and not is_placeholder_text(gates[0].date_basis):
        g0 = gates[0]
        pts.append((TP.date_basis(g0.milestone_id, g0.date_basis), [T(WORKBOOK, PS, g0.milestone_id, "Milestone ID"), T(WORKBOOK, PS, g0.milestone_id, "Date Basis")], [g0.milestone_id, g0.date_basis]))
    if checkpoints and len(pts) < 6:
        ids = [c.milestone_id for c in checkpoints]
        pts.append((TP.checkpoints(len(ids), ids), [T(WORKBOOK, PS, i, "Milestone ID") for i in ids], ids))


# =================================================================================================
# Slide 4: Acceptance Criteria
# =================================================================================================
def _acceptance_steps(wb: WorkbookModel, first_gate: str) -> List[WBSRow]:
    """The level 4 tasks under the WBS level 3 element named `{first gate} Milestone Acceptance`, in WBS order."""
    parent = next((w for w in wb.wbs_rows if w.level == 3 and w.name == f"{first_gate} Milestone Acceptance"), None)
    if parent is None:
        return []
    prefix = parent.wbs_code + "."
    return [w for w in wb.wbs_rows if w.level == 4 and w.wbs_code.startswith(prefix) and w.wbs_code.count(".") == parent.wbs_code.count(".") + 1]


def _build_acceptance(ctx: _Ctx, kicker: str) -> SlideSpec:
    b, wb = ctx.baseline, ctx.wb
    sow = b.sow_interpretation
    gates = _gates(wb)
    first_gate = gates[0].milestone_id if gates else ""
    card = CardSpec("How acceptance works", L.THREE_ACROSS_X[0], L.CONTENT_Y0, L.THREE_ACROSS_W, L.CARD_H)
    blocks: List[Block] = []

    approval_raw = (sow.approval_expectations or "[CONFIRMATION REQUIRED]") if sow is not None else None
    if approval_raw is not None:
        ref = T(KIT, SEC_SOW, "Approval & Acceptance Expectations", SOW_VALUE_FIELD)
        shown = first_sentence(approval_raw) if not is_placeholder_text(approval_raw) else ""
        blocks.append(fixed_block(para(BODY, value_run(approval_raw, [ref], "Approval expectation", shown=shown))))
    steps = _acceptance_steps(wb, first_gate) if first_gate else []
    step_runs: List[ParaSpec] = [
        para(BULLET, traced(normalize_text(s.name), T(WORKBOOK, WBS, s.wbs_code, "Name"), element=f"Acceptance step {s.wbs_code}"))
        for s in steps
    ]
    if step_runs:
        blocks.append(bullet_block([], step_runs, 6, lambda n: see_more(n, FT.WORKBOOK_LABEL, WBS)))
    first = b.deliverables[0] if b.deliverables else None
    review_ph = approver_ph = False
    review_val = approver_val = ""
    if first is not None:
        review_ref = T(KIT, SEC_DELIV, first.id, "Review Window")
        approver_ref = T(KIT, SEC_DELIV, first.id, "Client Approver")
        approver_raw = first.client_approver if (first.client_approver and "UNASSIGNED" not in first.client_approver.upper()) else "[CONFIRMATION REQUIRED]"
        review_run = value_run(first.review_window, [review_ref], "Review window")
        approver_run = value_run(approver_raw, [approver_ref], "Client approver")
        review_val, approver_val = normalize_text(first.review_window), normalize_text(approver_raw)
        review_ph, approver_ph = review_run.kind == PLACEHOLDER, approver_run.kind == PLACEHOLDER
        blocks.append(fixed_block(para(BODY, plain("Review window: ", LABEL), review_run)))
        blocks.append(fixed_block(para(BODY, plain("Client approver: ", LABEL), approver_run)))
    if not blocks:
        blocks.append(fixed_block(para(BODY, plain(FT.NONE_IN_KIT))))
    fit_card(card, blocks)

    # ---- right table: one row per deliverable --------------------------------------------------
    gate_of: Dict[str, Tuple[str, str]] = {}
    for w in wb.wbs_rows:
        if w.deliverable_id and w.element_type == "Deliverable" and w.milestone_id:
            gate_of.setdefault(w.deliverable_id, (w.wbs_code, w.milestone_id))
    rows_all: List[RowSpec] = []
    for d in b.deliverables:
        if DEFENSIVE_FILTER_REGEX.search(d.name or "") or DEFENSIVE_FILTER_REGEX.search(d.description or ""):
            continue
        crit_raw = d.acceptance_criteria if d.acceptance_criteria else "[CONFIRMATION REQUIRED]"
        crit_ph = is_placeholder_text(crit_raw) or "UNASSIGNED" in crit_raw.upper()
        crit_run = value_run("" if crit_ph else crit_raw, [T(KIT, SEC_DELIV, d.id, "Acceptance Criteria")], "Acceptance criteria", shown=None if crit_ph else clause_prefix(crit_raw, MAX_BULLET_WORDS))
        wbs_code, gate = gate_of.get(d.id, ("", ""))
        if gate:
            gate_run = traced(gate, T(WORKBOOK, WBS, wbs_code, "Milestone ID"), element="Gate")
        else:
            gate_run = plain(FT.PLACEHOLDER_TEXT, PLACEHOLDER)
        rows_all.append(RowSpec([
            _cell([traced(d.id, T(KIT, SEC_DELIV, d.id, "ID"), kind=STRONG, element="Deliverable ID")]),
            _cell([crit_run]),
            _cell([gate_run]),
        ]))

    def overflow(omitted: List[RowSpec]) -> RowSpec:
        runs: List[Run] = [plain(f"+{len(omitted)} more: ", MUTED)]
        for i, r in enumerate(omitted):
            if i:
                runs.append(plain(", ", MUTED))
            idrun = r.cells[0].paras[0][0]
            runs.append(traced(idrun.text, *idrun.traces, kind=MUTED, element="Omitted ID"))
        runs.append(plain(f" (see {FT.KIT_LABEL} · {SEC_DELIV})", MUTED))
        return RowSpec([_cell(runs), _cell([]), _cell([])], overflow=True)

    table = TableSpec("Table: Acceptance", L.THREE_ACROSS_X[1], L.CONTENT_Y0, list(L.ACCEPTANCE_COLS), list(FT.TABLE_HEADERS[4]), [])
    if rows_all:
        fit_rows(table, rows_all, 14, overflow, round(L.CONTENT_Y1 - table.y, 2))
    else:
        table.rows = [RowSpec([_cell([plain(FT.NONE_IN_KIT)]), _cell([]), _cell([])])]
        size_table(table)
    slide = SlideSpec(4, FT.SLIDE_TITLES[4], kicker, cards=[card], tables=[table])
    _acceptance_points(ctx, slide, first_gate, steps, first, review_val, approver_val, review_ph, approver_ph, rows_all)
    return slide


def _acceptance_points(ctx, slide, first_gate, steps, first, review_val, approver_val, review_ph, approver_ph, rows_all) -> None:
    b, wb = ctx.baseline, ctx.wb
    pts = slide.talking_points
    mode = check_acceptance_mode(b)
    mode_word = "milestone-level" if mode == "milestone-level" else "per deliverable"
    if steps:
        first_step = normalize_text(steps[0].name)
        refs = [T(WORKBOOK, WBS, steps[0].wbs_code, "Name"), T(WORKBOOK, WBS, steps[-1].wbs_code, "Name")]
        pts.append((TP.acceptance_mode(mode_word, first_gate, len(steps), first_step), refs[:1], [first_step]))
    if first is not None:
        rw = TP.spoken(review_val, review_ph)
        ap = TP.spoken(approver_val, approver_ph)
        got = _pick([(TP.acceptance_review(rw, ap), [FT.PLACEHOLDER_TEXT if review_ph else review_val, FT.PLACEHOLDER_TEXT if approver_ph else approver_val], [T(KIT, SEC_DELIV, first.id, "Review Window"), T(KIT, SEC_DELIV, first.id, "Client Approver")])])
        if got:
            pts.append((got[0], got[2], got[1]))
        evidence = normalize_text(first.evidence_required)
        if evidence and not is_placeholder_text(evidence):
            ev_ref = T(KIT, SEC_DELIV, first.id, "Evidence Required")
            short = clause_prefix(evidence, 18)
            got = _pick([(TP.acceptance_evidence(first.id, short), [first.id, short], [T(KIT, SEC_DELIV, first.id, "ID"), ev_ref])])
            if got:
                pts.append((got[0], got[2], got[1]))
    pending = [d.id for d in b.deliverables if not d.acceptance_criteria or is_placeholder_text(d.acceptance_criteria) or "UNASSIGNED" in d.acceptance_criteria.upper()]
    if pending:
        pts.append((TP.criteria_to_confirm(len(pending), pending), [T(KIT, SEC_DELIV, i, "ID") for i in pending], pending))


# =================================================================================================
# Slide 5: High-Risk Items
# =================================================================================================
def _build_risks(ctx: _Ctx, kicker: str) -> SlideSpec:
    wb = ctx.wb
    cands: List[Tuple[int, RAIDRow]] = []
    for r in wb.raid_rows:
        # Contract clarifications and open questions have no Probability or Impact: never selected (K.2)
        if r.type in ("Risk", "Issue") and r.probability and r.impact and not DEFENSIVE_FILTER_REGEX.search(r.description or ""):
            cands.append((compute_deck20_score(r.probability, r.impact), r))
    high = sorted([c for c in cands if compute_deck20_rating(c[1].probability, c[1].impact) == "High"], key=lambda c: (-c[0], c[1].raid_id))
    selected = list(high)
    if len(selected) < 3:
        rest = sorted([c for c in cands if c not in selected], key=lambda c: (-c[0], c[1].raid_id))
        selected.extend(rest[:3 - len(selected)])

    rows_all: List[RowSpec] = []
    for _score, r in selected:
        rid = r.raid_id

        def ref(field: str) -> TraceRef:
            return T(WORKBOOK, RAID, rid, field)

        id_runs = [traced(rid, ref("RAID ID"), kind=STRONG, element="RAID ID")]
        if r.source_id and r.source_id != rid:
            id_runs += [plain(" (", STRONG), traced(r.source_id, ref("Source ID"), kind=STRONG, element="Source ID"), plain(")", STRONG)]
        rating = compute_deck20_rating(r.probability, r.impact)
        fill, color = {"High": ("FEE2E2", "991B1B"), "Medium": ("FEF3C7", "92400E"), "Low": ("DCFCE7", "166534")}[rating]
        rating_run = traced(rating, ref("Probability"), ref("Impact"), kind=STRONG, element="Rating", derived="rating")
        item = clause_prefix(r.description, MAX_BULLET_WORDS)
        response = value_run(clause_prefix(r.mitigation_or_response, MAX_BULLET_WORDS) if r.mitigation_or_response else "", [ref("Mitigation / Response")], "Response")
        rows_all.append(RowSpec([
            _cell(id_runs),
            _cell([traced(item, ref("Description"), element="Item")]),
            _cell([rating_run], fill=fill, text_color=color, bold=True),
            _cell([value_run(r.owner, [ref("Owner")], "Owner")]),
            _cell([response]),
            _cell([traced(r.workstream or "Cross-phase", ref("Workstream"), element="Phase")]),
        ]))

    def overflow(omitted: List[RowSpec]) -> RowSpec:
        runs: List[Run] = [plain(f"+{len(omitted)} more: ", MUTED)]
        for i, row in enumerate(omitted):
            if i:
                runs.append(plain(", ", MUTED))
            first = row.cells[0].paras[0][0]
            runs.append(traced(first.text, *first.traces, kind=MUTED, element="Omitted ID"))
        runs.append(plain(f" (see {FT.WORKBOOK_LABEL} · {RAID})", MUTED))
        return RowSpec([_cell(runs)] + [_cell([]) for _ in range(5)], overflow=True)

    table = TableSpec("Table: Risks", L.CONTENT_X0, L.CONTENT_Y0, list(L.RISK_COLS), list(FT.TABLE_HEADERS[5]), [])
    if rows_all:
        fit_rows(table, rows_all, 6, overflow, round(L.CONTENT_Y1 - table.y, 2))
    else:
        table.rows = [RowSpec([_cell([plain(FT.NONE_IN_WORKBOOK)])] + [_cell([]) for _ in range(5)])]
        size_table(table)
    slide = SlideSpec(5, FT.SLIDE_TITLES[5], kicker, tables=[table])
    _risk_points(ctx, slide, selected, high)
    return slide


def _risk_points(ctx: _Ctx, slide: SlideSpec, selected, high) -> None:
    pts = slide.talking_points
    if not selected:
        return
    top = selected[0][1]
    rid = top.raid_id
    id_ref = T(WORKBOOK, RAID, rid, "RAID ID")
    desc = clause_prefix(top.description, 12)
    got = _pick([
        (TP.high_risks(len(high), rid, desc), [rid, desc], [id_ref, T(WORKBOOK, RAID, rid, "Description")]),
        (TP.high_risks(len(high), rid, None), [rid], [id_ref]),
    ])
    if got:
        pts.append((got[0], got[2], got[1]))
    for _score, r in selected[:4]:
        trig = normalize_text(r.trigger_or_early_warning)
        if trig and not is_placeholder_text(trig):
            got = _pick([(TP.early_warning(r.raid_id, trig), [r.raid_id, trig], [T(WORKBOOK, RAID, r.raid_id, "RAID ID"), T(WORKBOOK, RAID, r.raid_id, "Trigger / Early Warning")])])
            if got:
                pts.append((got[0], got[2], got[1]))
    if len(pts) < 3:
        owner_ph = is_placeholder_text(top.owner)
        owner_val = FT.PLACEHOLDER_TEXT if owner_ph else normalize_text(top.owner)
        pts.append((TP.item_owner(rid, TP.spoken(owner_val, owner_ph)), [T(WORKBOOK, RAID, rid, "RAID ID"), T(WORKBOOK, RAID, rid, "Owner")], [rid, owner_val]))
    charter = ctx.baseline.charter
    if charter is not None and charter.escalation_path and not is_placeholder_text(charter.escalation_path) and len(pts) < 6:
        esc = normalize_text(charter.escalation_path)
        pts.append((TP.raise_new_risks(esc), [T(KIT, SEC_CHARTER, "Escalation Path & Decision Hierarchy", CHARTER_VALUE_FIELD)], [esc]))


# =================================================================================================
# Slide 6: Client Collaboration
# =================================================================================================
def _build_collaboration(ctx: _Ctx, kicker: str) -> SlideSpec:
    b, wb = ctx.baseline, ctx.wb
    xs, w = L.THREE_ACROSS_X, L.THREE_ACROSS_W

    roles: List[ParaSpec] = []
    for s in b.stakeholders:
        if (s.organization or "").strip().lower() != "client" or DEFENSIVE_FILTER_REGEX.search(s.name or ""):
            continue
        key = normalize_text(s.name)
        role_run = value_run(s.role, [T(KIT, SEC_STAKE, key, "Role")], "Client role")
        rights = clause_prefix(s.decision_rights or "", MAX_BULLET_WORDS)
        rights_run = value_run(s.decision_rights, [T(KIT, SEC_STAKE, key, "Decision Rights")], "Decision rights", shown=rights)
        roles.append(para(BULLET, role_run, plain(": "), rights_run))

    comms: List[ParaSpec] = []
    for idx, c in enumerate(b.communications_plan, start=1):
        if DEFENSIVE_FILTER_REGEX.search(c.name or ""):
            continue
        cid = getattr(c, "id", None) or f"COM-{idx:02d}"
        if not re.match(r"^COM-\d{2}$", cid):
            cid = f"COM-{idx:02d}"
        comms.append(para(BULLET,
                          traced(normalize_text(c.name), T(KIT, SEC_COMMS, cid, "Report / Meeting"), element="Report / Meeting"),
                          plain(": "),
                          value_run(c.cadence, [T(KIT, SEC_COMMS, cid, "Cadence")], "Cadence")))

    prereqs: List[ParaSpec] = []
    for g in _gates(wb):
        # DECK-07: a cell holds several prerequisites separated by "; "; each is its own bullet
        for one in (g.client_prerequisites or "").split("; "):
            if not one.strip():
                continue
            shown = clause_prefix(one, MAX_BULLET_WORDS)
            prereqs.append(para(BULLET,
                                traced(g.milestone_id, T(WORKBOOK, PS, g.milestone_id, "Milestone ID"), element="Gate"),
                                plain(": "),
                                traced(shown, T(WORKBOOK, PS, g.milestone_id, "Client Prerequisites"), element="Client prerequisite")))

    cards: List[CardSpec] = []
    for heading, items, cap, label, none_line, x in (
        ("Client roles", roles, 5, (FT.KIT_LABEL, SEC_STAKE), FT.NONE_IN_KIT, xs[0]),
        ("Working rhythm", comms, 7, (FT.KIT_LABEL, SEC_COMMS), FT.NONE_IN_KIT, xs[1]),
        ("Client prerequisites", prereqs, 6, (FT.WORKBOOK_LABEL, PS), FT.NONE_IN_WORKBOOK, xs[2]),
    ):
        card = CardSpec(heading, x, L.CONTENT_Y0, w, L.CARD_H)
        if items:
            blocks = [bullet_block([], items, cap, lambda n, lb=label: see_more(n, lb[0], lb[1]))]
        else:
            blocks = [fixed_block(para(BODY, plain(none_line)))]
        fit_card(card, blocks)
        cards.append(card)
    h = max(c.h for c in cards)
    for c in cards:
        c.h = h

    slide = SlideSpec(6, FT.SLIDE_TITLES[6], kicker, cards=cards)
    _collaboration_points(ctx, slide)
    return slide


def _collaboration_points(ctx: _Ctx, slide: SlideSpec) -> None:
    b, wb = ctx.baseline, ctx.wb
    pts = slide.talking_points
    for s in b.stakeholders:
        if (s.organization or "").strip().lower() == "client" and "approver" in f"{s.role} {s.name}".lower():
            name = normalize_text(s.name)
            pts.append((TP.sign_off(name), [T(KIT, SEC_STAKE, name, "Stakeholder Name")], [name]))
            break
    meetings, others = [], []
    for idx, c in enumerate(b.communications_plan, start=1):
        cid = getattr(c, "id", None) or f"COM-{idx:02d}"
        if not re.match(r"^COM-\d{2}$", cid):
            cid = f"COM-{idx:02d}"
        if not c.cadence or is_placeholder_text(c.cadence) or DEFENSIVE_FILTER_REGEX.search(c.name or ""):
            continue
        item = (cid, normalize_text(c.name), normalize_text(c.cadence))
        (meetings if re.search(r"meeting|review|demo|call|standup|session", c.name or "", re.IGNORECASE) else others).append(item)
    for cid, name, cadence in (meetings + others)[:3]:
        got = _pick([(TP.meeting_cadence(name, cadence), [name, cadence], [T(KIT, SEC_COMMS, cid, "Report / Meeting"), T(KIT, SEC_COMMS, cid, "Cadence")])])
        if got:
            pts.append((got[0], got[2], got[1]))
    shown_prereqs = 0
    for g in _gates(wb):
        if g.client_prerequisites and g.client_prerequisites.strip() and g.planned_start:
            start = _date(g.planned_start)
            key = g.milestone_id
            prereq = clause_prefix(g.client_prerequisites, 16)
            refs = [T(WORKBOOK, PS, key, "Workstream"), T(WORKBOOK, PS, key, "Planned Start"), T(WORKBOOK, PS, key, "Client Prerequisites")]
            got = _pick([
                (TP.first_prerequisite(g.workstream, start, prereq), [g.workstream, start, prereq], refs),
                (TP.first_prerequisite_short(g.workstream, start), [g.workstream, start], refs[:2]),
            ])
            if got:
                pts.append((got[0], got[2], got[1]))
                shown_prereqs += 1
            if shown_prereqs >= (1 if len(pts) >= 4 else 2):
                break
    open_q = [r for r in wb.raid_rows if r.category == "Open Question"]
    if open_q:
        first = open_q[0].raid_id
        pts.append((TP.open_questions(len(open_q), first), [T(WORKBOOK, RAID, first, "RAID ID")], [first]))


# =================================================================================================
# Slide 7: Your Project Kit
# =================================================================================================
def _build_project_kit(ctx: _Ctx, kicker: str, earlier: List[SlideSpec], cover: CoverSpec, kit_file: str, wb_file: str) -> SlideSpec:
    used_kit = {loc for art, loc in _cover_sources(cover) if art == KIT}
    for s in earlier:
        used_kit |= {loc for art, loc in _slide_sources(s) if art == KIT}
    kit_sections = [s for s in FT.KIT_SECTION_ORDER if s in used_kit]

    xs, w = L.TWO_ACROSS_X, L.TWO_ACROSS_W
    card_h = 4.40
    left = CardSpec(FT.KIT_LABEL, xs[0], L.CONTENT_Y0, w, card_h)
    blocks_l = [
        fixed_block(para(BODY, traced(kit_file, T(KIT, "File name", kit_file, "File name"), kind=STRONG, element="Kit file name"))),
        fixed_block(para(BODY, plain(FT.KIT_DESCRIPTION))),
        bullet_block(
            [para(SUBHEADING, plain("Sections used in this deck"))],
            [para(BULLET, traced(sec, T(KIT, sec, sec, "Section heading"), element="Kit section")) for sec in kit_sections],
            len(kit_sections), lambda n: see_more(n, FT.KIT_LABEL),
        ) if kit_sections else fixed_block(),
    ]
    fit_card(left, [blk for blk in blocks_l if blk.paras or blk.items], min_h=card_h)
    right = CardSpec(FT.WORKBOOK_LABEL, xs[1], L.CONTENT_Y0, w, card_h)
    sheet_items = [
        para(BULLET, traced(sheet, T(WORKBOOK, sheet, sheet, "Sheet name"), element="Workbook sheet"), plain(f": {FT.SHEET_PURPOSES[sheet]}"))
        for sheet in FT.SHEET_ORDER
    ]
    blocks_r = [
        fixed_block(para(BODY, traced(wb_file, T(WORKBOOK, "File name", wb_file, "File name"), kind=STRONG, element="Workbook file name"))),
        fixed_block(para(BODY, plain(FT.WORKBOOK_DESCRIPTION))),
        bullet_block([para(SUBHEADING, plain("Sheets"))], sheet_items, len(sheet_items), lambda n: see_more(n, FT.WORKBOOK_LABEL)),
    ]
    fit_card(right, blocks_r, min_h=card_h)
    h = max(left.h, right.h)
    left.h = right.h = h
    bottom_y = round(L.CONTENT_Y0 + h + 0.10, 2)
    bottom = TextBoxSpec(
        "Text: Trace statement", L.CONTENT_X0, bottom_y, L.CONTENT_WIDTH, round(L.CONTENT_Y1 - bottom_y, 2),
        [para(BODY, plain(FT.TRACE_STATEMENT))],
    )
    slide = SlideSpec(7, FT.SLIDE_TITLES[7], kicker, cards=[left, right], boxes=[bottom])
    slide.talking_points = [(t, [], []) for t in TP.KIT_SLIDE_GUIDANCE]
    return slide


# =================================================================================================
# Manifest
# =================================================================================================
def _register_manifest(manifest: DeckTraceManifest, cover: CoverSpec, slides: List[SlideSpec]) -> None:
    """One manifest entry per traced run, with the shape that holds it, plus one per talking point (DECK-06)."""
    manifest.add(1, "Cover title", cover.title.element or "Project name", cover.title.text, cover.title.traces)
    for r in cover.subtitle_runs:
        manifest.add(1, "Cover subtitle", r.element, r.text, r.traces)
    for i, (text, refs, vals) in enumerate(cover.talking_points, start=1):
        if refs:
            manifest.add(1, "Notes", f"Talking point {i}", text, refs, values=vals)
    for s in slides:
        for c in s.cards:
            for p in c.paras:
                for r in p.runs:
                    manifest.add(s.number, c.text_name, r.element, r.text, r.traces, derived=r.derived)
            if c.table is not None:
                _register_table(manifest, s.number, c.table)
        for t in s.tables:
            _register_table(manifest, s.number, t)
        for i, (text, refs, vals) in enumerate(s.talking_points, start=1):
            if refs:
                manifest.add(s.number, "Notes", f"Talking point {i}", text, refs, values=vals)


def _register_table(manifest: DeckTraceManifest, slide_no: int, table: TableSpec) -> None:
    for row in table.rows:
        for cell in row.cells:
            for line in cell.paras:
                for r in line:
                    manifest.add(slide_no, table.name, r.element, r.text, r.traces, derived=r.derived)
