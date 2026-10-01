"""Test that no SOW-specific literals, story IDs, or title tables exist in src/."""

import re
from pathlib import Path


def test_no_sow_specific_literals_in_src():
    src_dir = Path("src")
    assert src_dir.exists() and src_dir.is_dir()

    hs_regex = re.compile(r'\bHS-\d{3,5}\b')
    forbidden_terms = [
        "ARC_KNOWN_REF_TITLES",
        "ARC_KNOWN_REF_PHASES",
        "ARC_KNOWN_",
    ]

    violations = []

    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        
        # Check HS-#### pattern
        for match in hs_regex.finditer(content):
            lineno = content[:match.start()].count("\n") + 1
            violations.append(f"{py_file}:{lineno}: Found SOW-specific story literal '{match.group(0)}'")

        # Check forbidden terms
        for term in forbidden_terms:
            if term in content:
                lineno = content[:content.find(term)].count("\n") + 1
                violations.append(f"{py_file}:{lineno}: Found hard-coded SOW dictionary '{term}'")

    assert not violations, "SOW-specific literals or tables found in src:\n" + "\n".join(violations)
