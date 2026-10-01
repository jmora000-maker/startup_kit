"""Unit tests for SOW reference pattern matching and reserved prefix exclusions (v6 Section 1.1)."""

import pytest
from src.config import (
    extract_sow_references,
    extract_sow_references_with_kind,
    detect_sow_reference_kind,
    is_tool_reserved_id,
)


def test_story_id_patterns():
    """Test standard Story ID pattern matching e.g. HS-4762, JIRA-101, PROJ-9999."""
    assert detect_sow_reference_kind("HS-4762") == "Story ID"
    assert detect_sow_reference_kind("ABC-1234") == "Story ID"
    assert detect_sow_reference_kind("FEAT-55555") == "Story ID"


def test_tool_reserved_id_exclusion():
    """Tool-internal prefixes (DEL, WP, RSK, ISS, DEP, ASM, AMB, Q, M, MS, COM, DEC, ACT, RAID, G01) must NOT be Story IDs."""
    reserved_ids = [
        "DEL-01", "DEL-19",
        "WP-01", "WP-15",
        "RSK-01", "RSK-10",
        "ISS-01", "ISS-05",
        "DEP-01", "ASM-01",
        "AMB-01", "AMB-15",
        "Q-01", "Q-18",
        "M-01", "MS-01",
        "COM-01", "COM-06",
        "DEC-01", "DEC-15",
        "ACT-01", "ACT-REQ-01",
        "RAID-01", "G01-01",
    ]
    for r_id in reserved_ids:
        assert is_tool_reserved_id(r_id) is True, f"{r_id} should be identified as tool reserved"
        assert detect_sow_reference_kind(r_id) != "Story ID", f"{r_id} must not be classified as Story ID"


def test_other_sow_reference_kinds():
    """Test Deliverable numbers, Task/WBS codes, Sections, and Synthetic references."""
    assert detect_sow_reference_kind("Deliverable 1.2") == "Deliverable number"
    assert detect_sow_reference_kind("D1.2") == "Deliverable number"
    assert detect_sow_reference_kind("Task 3.1") == "Task or WBS code"
    assert detect_sow_reference_kind("WBS 2.4") == "Task or WBS code"
    assert detect_sow_reference_kind("Section 4.1") == "Section"
    assert detect_sow_reference_kind("Clause 7") == "Section"
    assert detect_sow_reference_kind("SOW-P1-01") == "Synthetic"
    assert detect_sow_reference_kind("SOW-01") == "Synthetic"


def test_extract_sow_references_ordering_and_filtering():
    """Test extracting references from text while filtering internal reserved IDs."""
    text = (
        "In Section 4.2, DEL-01 covers HS-4762 and HS-4763. "
        "See also Deliverable 2 and Task 1.1 for AMB-02."
    )
    refs_with_kind = extract_sow_references_with_kind(text)
    refs = [r for r, k in refs_with_kind]

    # Must contain HS-4762, HS-4763, Deliverable 2, Task 1.1, Section 4.2
    # Must NOT contain DEL-01, AMB-02
    assert "HS-4762" in refs
    assert "HS-4763" in refs
    assert "DEL-01" not in refs
    assert "AMB-02" not in refs
