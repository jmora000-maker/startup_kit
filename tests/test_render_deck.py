"""DECK-23: the visual review aid degrades gracefully; rendering itself is a manual review step."""

import subprocess
from pathlib import Path

import pytest

from src.tools import render_deck


def test_find_soffice_honours_soffice_path(tmp_path, monkeypatch):
    fake = tmp_path / "soffice.exe"
    fake.write_text("")
    monkeypatch.setenv("SOFFICE_PATH", str(fake))
    assert render_deck.find_soffice() == str(fake)


def test_missing_libreoffice_is_reported_and_nothing_is_written(tmp_path, monkeypatch, capsys):
    deck = tmp_path / "Deck.pptx"
    deck.write_bytes(b"x")
    monkeypatch.delenv("SOFFICE_PATH", raising=False)
    monkeypatch.setattr(render_deck, "find_soffice", lambda: None)
    assert render_deck.main([str(deck)]) == 0
    assert "Not rendered" in capsys.readouterr().out
    assert list(tmp_path.glob("*.png")) == []


def test_usage_and_missing_deck(tmp_path, capsys):
    assert render_deck.main([]) == 2
    assert render_deck.main([str(tmp_path / "absent.pptx")]) == 2


def test_render_writes_one_png_per_slide_beside_the_deck(tmp_path, monkeypatch):
    """With LibreOffice stubbed to produce a 2-page PDF, one PNG per slide lands beside the deck."""
    import pymupdf

    deck = tmp_path / "Deck.pptx"
    deck.write_bytes(b"x")

    def fake_run(cmd, **kwargs):
        outdir = Path(cmd[cmd.index("--outdir") + 1])
        doc = pymupdf.open()
        for _ in range(2):
            doc.new_page(width=960, height=540)
        doc.save(str(outdir / "Deck.pdf"))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(render_deck, "find_soffice", lambda: "soffice")
    monkeypatch.setattr(render_deck.subprocess, "run", fake_run)
    pngs = render_deck.render_deck(deck)
    assert [p.name for p in pngs] == ["Deck_slide_1.png", "Deck_slide_2.png"]
    assert all(p.exists() and p.parent == tmp_path for p in pngs)
