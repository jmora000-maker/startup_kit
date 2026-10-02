"""Visual review aid: render each slide of a deck to a PNG beside the deck (DECK-23).

    python -m src.tools.render_deck <deck.pptx>

Uses LibreOffice (headless) to convert the deck to PDF, then writes `{deck name}_slide_{n}.png` beside the
deck. It is a review aid only: the automated checks are DECK-21 and INV-32. When LibreOffice is not
installed it says so and writes nothing.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

WINDOWS_CANDIDATES = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)


def find_soffice() -> Optional[str]:
    """The LibreOffice executable: SOFFICE_PATH, then PATH, then the usual Windows install folders."""
    configured = os.environ.get("SOFFICE_PATH")
    if configured and Path(configured).exists():
        return configured
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in WINDOWS_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


def render_deck(deck_path: Path, dpi: int = 110) -> List[Path]:
    """Render every slide to `{deck stem}_slide_{n}.png` beside the deck; returns the PNG paths."""
    soffice = find_soffice()
    if soffice is None:
        raise FileNotFoundError("LibreOffice was not found (set SOFFICE_PATH or add soffice to PATH)")
    import pymupdf  # imported here so the module loads without it

    deck_path = Path(deck_path).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, str(deck_path)],
            check=True,
            capture_output=True,
            timeout=300,
        )
        pdf = Path(tmp) / f"{deck_path.stem}.pdf"
        out: List[Path] = []
        with pymupdf.open(str(pdf)) as doc:
            for i, page in enumerate(doc, start=1):
                png = deck_path.with_name(f"{deck_path.stem}_slide_{i}.png")
                page.get_pixmap(dpi=dpi).save(str(png))
                out.append(png)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python -m src.tools.render_deck <deck.pptx>")
        return 2
    deck = Path(args[0])
    if not deck.exists():
        print(f"Deck not found: {deck}")
        return 2
    try:
        pngs = render_deck(deck)
    except FileNotFoundError as e:
        print(f"Not rendered: {e}. The deck was not changed; DECK-21 and INV-32 remain the automated checks.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"LibreOffice failed to convert the deck: {e}")
        return 1
    for p in pngs:
        print(p)
    print(f"Rendered {len(pngs)} slides beside {deck.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
