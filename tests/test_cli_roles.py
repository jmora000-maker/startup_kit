"""Tests for CLI leadership roles (pmo_lead, delivery_lead, talent_pm) and charter defaults."""

import sys
import docx
import pytest
from pathlib import Path
from src.core.models import ProjectStartupCharter, TalentOnboardingRecord
from main import prompt_role_names, main, parse_args


def test_project_startup_charter_role_defaults():
    """Verify that ProjectStartupCharter defaults pmo_lead, delivery_manager, and talent_pm to [UNASSIGNED - TO BE CONFIRMED]."""
    charter = ProjectStartupCharter()
    assert charter.pmo_lead == "[UNASSIGNED - TO BE CONFIRMED]"
    assert charter.delivery_manager == "[UNASSIGNED - TO BE CONFIRMED]"
    assert charter.talent_pm == "[UNASSIGNED - TO BE CONFIRMED]"


def test_talent_onboarding_record_role_defaults():
    """Verify that TalentOnboardingRecord defaults pmo_lead, delivery_manager, and talent_pm to [UNASSIGNED - TO BE CONFIRMED]."""
    record = TalentOnboardingRecord()
    assert record.pmo_lead == "[UNASSIGNED - TO BE CONFIRMED]"
    assert record.delivery_manager == "[UNASSIGNED - TO BE CONFIRMED]"
    assert record.talent_pm == "[UNASSIGNED - TO BE CONFIRMED]"


def test_prompt_role_names_from_flags():
    """Verify that provided CLI flag values are used without prompting."""
    pmo, dl, tpm = prompt_role_names(
        pmo_lead="Sarah Connor",
        delivery_lead="Jane Doe",
        talent_pm="John Smith",
        interactive=False
    )
    assert pmo == "Sarah Connor"
    assert dl == "Jane Doe"
    assert tpm == "John Smith"


def test_prompt_role_names_interactive_provided(monkeypatch):
    """Verify that interactive user inputs are captured when flags are not passed."""
    inputs = iter(["Alice Wonderland", "Bob Builder", "Charlie Chaplin"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    pmo, dl, tpm = prompt_role_names(interactive=True)
    assert pmo == "Alice Wonderland"
    assert dl == "Bob Builder"
    assert tpm == "Charlie Chaplin"


def test_prompt_role_names_interactive_empty_defaults(monkeypatch):
    """Verify that empty inputs in interactive mode default to [UNASSIGNED - TO BE CONFIRMED]."""
    inputs = iter(["", "   ", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    pmo, dl, tpm = prompt_role_names(interactive=True)
    assert pmo == "[UNASSIGNED - TO BE CONFIRMED]"
    assert dl == "[UNASSIGNED - TO BE CONFIRMED]"
    assert tpm == "[UNASSIGNED - TO BE CONFIRMED]"


def test_prompt_role_names_non_interactive():
    """Verify that non-interactive mode defaults to [UNASSIGNED - TO BE CONFIRMED] without error."""
    pmo, dl, tpm = prompt_role_names(interactive=False)
    assert pmo == "[UNASSIGNED - TO BE CONFIRMED]"
    assert dl == "[UNASSIGNED - TO BE CONFIRMED]"
    assert tpm == "[UNASSIGNED - TO BE CONFIRMED]"


def test_prompt_role_names_eof_handling(monkeypatch):
    """Verify that EOFError gracefully defaults to [UNASSIGNED - TO BE CONFIRMED]."""
    def raise_eof(prompt=""):
        raise EOFError()

    monkeypatch.setattr("builtins.input", raise_eof)
    pmo, dl, tpm = prompt_role_names(interactive=True)
    assert pmo == "[UNASSIGNED - TO BE CONFIRMED]"
    assert dl == "[UNASSIGNED - TO BE CONFIRMED]"
    assert tpm == "[UNASSIGNED - TO BE CONFIRMED]"


def test_cli_main_with_explicit_roles(populated_inputs_dir, tmp_path, monkeypatch):
    """Verify that CLI execution with explicit role flags assigns them to output baseline."""
    output_dir = tmp_path / "cli_explicit_roles_output"

    test_args = [
        "main.py",
        "--mock",
        "--inputs-dir", str(populated_inputs_dir),
        "--output-dir", str(output_dir),
        "--pmo-lead", "Alex PMO",
        "--delivery-lead", "Dana Delivery",
        "--talent-pm", "Taylor Talent",
        "--non-interactive"
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    exit_code = main()
    assert exit_code == 0

    created_docx = list(output_dir.glob("*.docx"))
    assert len(created_docx) == 1

    doc = docx.Document(str(created_docx[0]))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    # Check tables for role metadata
    table_texts = "\n".join(cell.text for t in doc.tables for row in t.rows for cell in row.cells)
    combined = full_text + "\n" + table_texts

    assert "Alex PMO" in combined
    assert "Dana Delivery" in combined
    assert "Taylor Talent" in combined


def test_cli_main_with_delivery_manager_alias(populated_inputs_dir, tmp_path, monkeypatch):
    """Verify that --delivery-manager flag works as an alias for --delivery-lead."""
    output_dir = tmp_path / "cli_alias_output"

    test_args = [
        "main.py",
        "--mock",
        "--inputs-dir", str(populated_inputs_dir),
        "--output-dir", str(output_dir),
        "--delivery-manager", "Morgan Manager",
        "--non-interactive"
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    exit_code = main()
    assert exit_code == 0

    created_docx = list(output_dir.glob("*.docx"))
    assert len(created_docx) == 1

    doc = docx.Document(str(created_docx[0]))
    table_texts = "\n".join(cell.text for t in doc.tables for row in t.rows for cell in row.cells)
    assert "Morgan Manager" in table_texts


def test_cli_main_default_unassigned_roles(populated_inputs_dir, tmp_path, monkeypatch):
    """Verify that CLI execution without role flags defaults to [UNASSIGNED - TO BE CONFIRMED]."""
    output_dir = tmp_path / "cli_unassigned_output"

    test_args = [
        "main.py",
        "--mock",
        "--inputs-dir", str(populated_inputs_dir),
        "--output-dir", str(output_dir),
        "--non-interactive"
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    exit_code = main()
    assert exit_code == 0

    created_docx = list(output_dir.glob("*.docx"))
    assert len(created_docx) == 1

    doc = docx.Document(str(created_docx[0]))
    table_texts = "\n".join(cell.text for t in doc.tables for row in t.rows for cell in row.cells)
    assert "[UNASSIGNED - TO BE CONFIRMED]" in table_texts
