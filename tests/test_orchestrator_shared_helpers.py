"""Unit tests for HTL-17 Group 1's shared, CLI/app-agnostic helper functions in src/orchestrator.py:
parse_start_date (C-2), resolve_execution_mode (C-3), and resolve_mock_io_dirs (C-4/C-10)."""

import pytest
from datetime import date
from pathlib import Path

from src.config import config
from src.orchestrator import parse_start_date, resolve_execution_mode, resolve_mock_io_dirs


def test_parse_start_date_valid_iso():
    assert parse_start_date("2026-10-07") == date(2026, 10, 7)


def test_parse_start_date_strips_whitespace():
    assert parse_start_date("  2026-10-07  ") == date(2026, 10, 7)


def test_parse_start_date_none_or_empty_returns_none():
    assert parse_start_date(None) is None
    assert parse_start_date("") is None


def test_parse_start_date_invalid_raises_value_error():
    with pytest.raises(ValueError):
        parse_start_date("not-a-date")


def test_resolve_execution_mode_reingest_flag_wins():
    assert resolve_execution_mode(Path("kit.docx"), is_interactive=True, prompted_mode="1") == "2"
    assert resolve_execution_mode(Path("kit.docx"), is_interactive=False, prompted_mode=None) == "2"


def test_resolve_execution_mode_interactive_uses_prompted_value():
    assert resolve_execution_mode(None, is_interactive=True, prompted_mode="2") == "2"
    assert resolve_execution_mode(None, is_interactive=True, prompted_mode="1") == "1"


def test_resolve_execution_mode_non_interactive_defaults_to_generation():
    assert resolve_execution_mode(None, is_interactive=False, prompted_mode=None) == "1"


def test_resolve_mock_io_dirs_explicit_paths_win():
    custom_in = Path("my_inputs")
    custom_out = Path("my_output")
    resolved_in, resolved_out = resolve_mock_io_dirs(mock=True, inputs_dir=custom_in, output_dir=custom_out)
    assert resolved_in == custom_in
    assert resolved_out == custom_out


def test_resolve_mock_io_dirs_mock_defaults_to_fixtures():
    resolved_in, resolved_out = resolve_mock_io_dirs(mock=True)
    assert resolved_in == config.mock_inputs_dir
    assert resolved_out == config.mock_output_dir


def test_resolve_mock_io_dirs_non_mock_defaults_to_normal_folders():
    resolved_in, resolved_out = resolve_mock_io_dirs(mock=False)
    assert resolved_in == config.inputs_dir
    assert resolved_out == config.output_dir
