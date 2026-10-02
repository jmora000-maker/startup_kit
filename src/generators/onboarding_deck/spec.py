"""Slide specifications produced by the deck builder and rendered by the writer (DECK-03, DECK-21).

Every text run that comes from a source carries its TraceRefs, so the manifest is derived from exactly
what is written (DECK-06).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from src.generators.onboarding_deck import layout as L
from src.generators.onboarding_deck.trace import DeckTraceManifest, TraceRef

# Run kinds map to styles in the writer
TEXT = "text"              # body text (Calibri, 475569)
LABEL = "label"            # bold label in front of a value (Calibri bold, 0F172A)
PLACEHOLDER = "placeholder"  # To be confirmed (italic, 204ECF)
MUTED = "muted"            # +N more lines (italic, 64748B)
STRONG = "strong"          # first-column ID / name (Calibri bold, 0F172A)
ITALIC = "italic"          # checkpoints (italic, 475569)

# Paragraph kinds
HEADING = "heading"
SUBHEADING = "subheading"
BODY = "body"
BULLET = "bullet"
MORE = "more"


@dataclass
class Run:
    text: str
    kind: str = TEXT
    traces: List[TraceRef] = field(default_factory=list)
    element: str = ""
    derived: Optional[str] = None


@dataclass
class ParaSpec:
    kind: str
    runs: List[Run]

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)


@dataclass
class CellSpec:
    paras: List[List[Run]]            # one list of runs per paragraph
    fill: Optional[str] = None        # hex fill override (rating cells)
    text_color: Optional[str] = None  # hex text colour override (rating cells)
    bold: bool = False

    @property
    def text(self) -> str:
        return "\n".join("".join(r.text for r in runs) for runs in self.paras)


@dataclass
class RowSpec:
    cells: List[CellSpec]
    overflow: bool = False
    height: float = L.TABLE_MIN_ROW_H


@dataclass
class TableSpec:
    name: str
    x: float
    y: float
    col_widths: List[float]
    header: Optional[List[str]]       # None for key-value tables (no header row)
    rows: List[RowSpec]
    body_pt: float = L.TABLE_BODY_PT
    deliverables_pt: Optional[float] = None  # slide 3, column 4
    key_value: bool = False
    header_height: float = L.TABLE_HEADER_H

    @property
    def width(self) -> float:
        return round(sum(self.col_widths), 2)

    @property
    def height(self) -> float:
        return round((self.header_height if self.header else 0.0) + sum(r.height for r in self.rows), 2)


@dataclass
class CardSpec:
    heading: str
    x: float
    y: float
    w: float
    h: float
    paras: List[ParaSpec] = field(default_factory=list)  # excludes the heading
    heading_pt: float = L.CARD_HEADING_PT
    body_pt: float = L.BODY_PT
    table: Optional[TableSpec] = None  # a table inside the card, below the heading

    @property
    def card_name(self) -> str:
        return f"Card: {self.heading}"

    @property
    def text_name(self) -> str:
        return f"Card text: {self.heading}"

    @property
    def table_name(self) -> str:
        return f"Table: {self.heading}"


@dataclass
class TextBoxSpec:
    name: str
    x: float
    y: float
    w: float
    h: float
    paras: List[ParaSpec]
    size_pt: float = L.BODY_PT


@dataclass
class SlideSpec:
    number: int
    title: str
    kicker: str
    cards: List[CardSpec] = field(default_factory=list)
    tables: List[TableSpec] = field(default_factory=list)
    boxes: List[TextBoxSpec] = field(default_factory=list)
    notes: str = ""
    talking_points: List[Tuple[str, List[TraceRef], List[str]]] = field(default_factory=list)  # (text, traces, values)
    sources: List[Tuple[str, str]] = field(default_factory=list)  # (artifact, locator) used on the slide


@dataclass
class CoverSpec:
    title: Run
    subtitle_runs: List[Run]
    notes: str = ""
    talking_points: List[Tuple[str, List[TraceRef], List[str]]] = field(default_factory=list)


@dataclass
class DeckModel:
    project_name: str
    client_name: str
    cover: CoverSpec
    slides: List[SlideSpec]  # slides 2 to 7
    manifest: DeckTraceManifest
    kit_file_name: str = ""
    workbook_file_name: str = ""
    overflow_rows_used: int = 0
