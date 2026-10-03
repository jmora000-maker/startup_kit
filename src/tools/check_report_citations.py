"""Check that every test name cited in a report actually exists under tests/.

Reports under reports/ cite test functions as verification evidence, e.g.
`test_invariants.py::test_inv_34_passes_when_stated_award_date_reflected`.
This tool scans every report for test-name tokens (``test_<identifier>``) and
confirms each one is defined somewhere under tests/ (AST scan of every .py file:
functions, async functions, classes) or is the name of a file/folder under
tests/ (e.g. ``test_snapshots.py``).

Glob-style citations such as ``test_inv_33/34/35_fails_*`` are treated as
prefixes: they pass if at least one known name starts with the cited prefix.

Any other cited name that is not an exact match is also tried as a prefix,
but ONLY if that exact name has never existed anywhere in the git history of
tests/ (as a whole word in any added/removed line, or as a file stem). A name
that did exist once and was later renamed or removed is a stale citation, not
a shortened one, so it stays MISSING. A shortened citation such as
``test_inv_18`` (never a real name) still resolves:
- FOUND (by prefix) if it is the prefix of exactly one known name;
- AMBIGUOUS if it is the prefix of more than one known name. All candidates
  are listed and the run fails, so a person resolves it instead of the tool
  guessing;
- MISSING if it is the prefix of no known name.
Prefix resolutions are always printed, so a reviewer can see what each
shortened citation was matched to.

A missing name that is also mentioned inside a ``## Correction Note`` section of
the same report is listed as ACKNOWLEDGED rather than failing: the report has
already documented that the citation was wrong (this project corrects reports
by appending notes, never by rewriting them).

With ``--history``, each missing citation is classified using git: the commit
that wrote the citing line (git blame) is looked up, and the tool checks
whether the name existed under tests/ at that commit. This separates a citation
that was never valid from one that was valid when written and removed later.

Not part of the default pytest run (reports are not code). Run on demand,
before approving any final report as "verified":

    python -m src.tools.check_report_citations
    python -m src.tools.check_report_citations --history   # classify missing names via git

Exit code 0 = every citation resolves; 1 = at least one cited name is missing or ambiguous.
"""
import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

FOUND = "FOUND"
FOUND_BY_PREFIX = "FOUND_BY_PREFIX"
AMBIGUOUS = "AMBIGUOUS"
MISSING = "MISSING"

REPORT_SUFFIXES = {".md", ".txt"}
TEST_NAME_REGEX = re.compile(r"\btest_[A-Za-z0-9_]+")
CORRECTION_HEADING_REGEX = re.compile(r"^#{1,6}\s+Correction Note\b", re.IGNORECASE)


@dataclass
class Citation:
    report: Path
    line_no: int
    name: str
    is_prefix: bool
    line: str
    status: str = ""
    candidates: Tuple[str, ...] = ()


def collect_known_test_names(tests_dir: Path) -> Set[str]:
    """Every function/class name defined in tests/*.py, plus every file and folder stem under tests/."""
    names: Set[str] = set()
    for path in tests_dir.rglob("*"):
        if "__pycache__" in path.parts:
            continue
        names.add(path.stem if path.is_file() else path.name)
        if path.is_file() and path.suffix == ".py":
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.add(node.name)
    return names


def extract_citations(report: Path) -> List[Citation]:
    """Find every test_<identifier> token in a report, with its line number."""
    text = report.read_text(encoding="utf-8", errors="replace")
    citations: List[Citation] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for m in TEST_NAME_REGEX.finditer(line):
            name = m.group(0)
            following = line[m.end():m.end() + 1]
            is_prefix = following in ("*", "/") or name.endswith("_")
            citations.append(Citation(report, line_no, name, is_prefix, line.strip()))
    return citations


def corrected_names(report: Path) -> Set[str]:
    """Test names mentioned in any 'Correction Note' section of the report (heading to next same-or-higher heading)."""
    names: Set[str] = set()
    in_note_level = 0
    for line in report.read_text(encoding="utf-8", errors="replace").splitlines():
        heading = re.match(r"^(#{1,6})\s", line)
        if heading:
            level = len(heading.group(1))
            if CORRECTION_HEADING_REGEX.match(line):
                in_note_level = level
                continue
            if in_note_level and level <= in_note_level:
                in_note_level = 0
        if in_note_level:
            names.update(m.group(0) for m in TEST_NAME_REGEX.finditer(line))
    return names


def resolve_citation(citation: Citation, known: Set[str],
                     ever_existed: Optional[Callable[[str], bool]] = None) -> Tuple[str, Tuple[str, ...]]:
    """Return (status, candidates) for a citation.

    Explicit wildcard citations (``*``, ``/``, trailing ``_``) pass if any known name
    starts with them, as they deliberately cover several tests. Any other name is
    FOUND on an exact match. Otherwise prefix matching is tried only if the exact
    cited name has never existed anywhere in tests/ history (``ever_existed`` returns
    False): then it is FOUND_BY_PREFIX if it is the prefix of exactly one known name,
    AMBIGUOUS if it is the prefix of several. A name that did exist once (renamed or
    removed since) is stale, not shortened, so it is MISSING. Without an
    ``ever_existed`` lookup, prefix matching is not applied.
    """
    if citation.name in known:
        return FOUND, ()
    candidates = tuple(sorted(k for k in known if k.startswith(citation.name)))
    if citation.is_prefix:
        return (FOUND, candidates) if candidates else (MISSING, ())
    if not candidates or ever_existed is None or ever_existed(citation.name):
        return MISSING, ()
    if len(candidates) == 1:
        return FOUND_BY_PREFIX, candidates
    return AMBIGUOUS, candidates


def citation_resolves(citation: Citation, known: Set[str],
                      ever_existed: Optional[Callable[[str], bool]] = None) -> bool:
    return resolve_citation(citation, known, ever_existed)[0] in (FOUND, FOUND_BY_PREFIX)


def _git(args: List[str], repo_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def make_history_lookup(repo_root: Path, tests_dir: Path) -> Callable[[str], bool]:
    """Return a cached ``ever_existed(name)`` lookup over the git history of tests_dir.

    A name has existed if it ever appeared as a whole word in an added or removed
    line of any commit touching tests_dir (all refs), or as the stem of any file
    path ever committed under tests_dir. If git cannot be queried, every name is
    treated as having existed, so no prefix guess is made.
    """
    cache: Dict[str, bool] = {}
    pathspec = tests_dir.as_posix()
    stems: Optional[Set[str]] = None

    def ever_existed(name: str) -> bool:
        nonlocal stems
        if name in cache:
            return cache[name]
        try:
            if stems is None:
                files = _git(["log", "--all", "--name-only", "--format=", "--", pathspec], repo_root)
                if files.returncode != 0:
                    raise OSError(files.stderr.strip())
                stems = {Path(p).stem for p in files.stdout.split()} | \
                        {part for p in files.stdout.split() for part in Path(p).parts}
            diffs = _git(["log", "--all", "-p", "--format=", "-G", name, "--", pathspec], repo_root)
            if diffs.returncode != 0:
                raise OSError(diffs.stderr.strip())
        except OSError:
            cache[name] = True
            return True
        word = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])")
        in_diff = any(
            line[:1] in ("+", "-") and not line.startswith(("+++", "---")) and word.search(line)
            for line in diffs.stdout.splitlines()
        )
        cache[name] = in_diff or name in stems
        return cache[name]

    return ever_existed


def git_history_status(citation: Citation, repo_root: Path) -> str:
    """Did the cited name exist under tests/ at the commit that wrote the citing line?"""
    try:
        blame = _git(["blame", "--porcelain", "-L", f"{citation.line_no},{citation.line_no}", "--",
                      citation.report.as_posix()], repo_root)
        ever = _git(["log", "--all", "--format=%h", "-S", citation.name, "--", "tests"], repo_root).stdout.split()
    except OSError as e:
        return f"git lookup failed: {e}"
    commit = blame.stdout.split()[0] if blame.returncode == 0 and blame.stdout else ""
    ever_text = f"; appears in tests/ history at {', '.join(ever[:5])}" if ever else "; never appears anywhere in tests/ history"
    if not commit or set(commit) == {"0"}:
        return "citing line is not committed yet" + ever_text
    pattern = citation.name if not citation.is_prefix else citation.name + "[A-Za-z0-9_]*"
    found = _git(["grep", "-q", "-w", "-E", pattern, commit, "--", "tests"], repo_root).returncode == 0
    when = f"line written in {commit[:7]}"
    if found:
        return f"{when}: existed in tests/ then, removed or renamed since" + ever_text
    return f"{when}: did NOT exist in tests/ when cited" + ever_text


def check_reports(reports_dir: Path, tests_dir: Path, by_prefix: Optional[Dict[Path, List[Citation]]] = None):
    """Return ({report: [missing/ambiguous citations]}, {report: [acknowledged citations]}) for reports with unresolved names.

    If ``by_prefix`` is given, citations resolved by unique prefix are collected into it.
    """
    known = collect_known_test_names(tests_dir)
    ever_existed = make_history_lookup(Path.cwd(), tests_dir)
    missing: Dict[Path, List[Citation]] = {}
    acknowledged: Dict[Path, List[Citation]] = {}
    for report in sorted(reports_dir.rglob("*")):
        if not report.is_file() or report.suffix.lower() not in REPORT_SUFFIXES:
            continue
        bad = []
        for c in extract_citations(report):
            c.status, c.candidates = resolve_citation(c, known, ever_existed)
            if c.status == FOUND_BY_PREFIX and by_prefix is not None:
                by_prefix.setdefault(report, []).append(c)
            elif c.status in (AMBIGUOUS, MISSING):
                bad.append(c)
        if not bad:
            continue
        corrected = corrected_names(report)
        ack = [c for c in bad if c.name in corrected]
        bad = [c for c in bad if c.name not in corrected]
        if bad:
            missing[report] = bad
        if ack:
            acknowledged[report] = ack
    return missing, acknowledged


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check that test names cited in reports/ exist under tests/.")
    parser.add_argument("--reports-dir", type=str, default="reports", help="Folder of reports to scan (default: reports)")
    parser.add_argument("--tests-dir", type=str, default="tests", help="Folder of tests to resolve names against (default: tests)")
    parser.add_argument("--history", action="store_true", help="For each missing name, classify it using git history of tests/")
    args = parser.parse_args(argv)

    reports_dir = Path(args.reports_dir)
    tests_dir = Path(args.tests_dir)
    for d in (reports_dir, tests_dir):
        if not d.is_dir():
            print(f"Error: Directory '{d}' does not exist.", file=sys.stderr)
            return 2

    by_prefix: Dict[Path, List[Citation]] = {}
    missing, acknowledged = check_reports(reports_dir, tests_dir, by_prefix)
    scanned = sum(1 for p in reports_dir.rglob("*") if p.is_file() and p.suffix.lower() in REPORT_SUFFIXES)

    def _print(groups: Dict[Path, List[Citation]]) -> None:
        for report, cites in groups.items():
            print(f"\n{report.as_posix()}")
            for c in cites:
                kind = " (prefix)" if c.is_prefix else ""
                quoted = " (inside quoted text)" if c.line.startswith(">") else ""
                status = f" [{c.status}]" if c.status in (AMBIGUOUS, FOUND_BY_PREFIX) else ""
                print(f"  line {c.line_no}: {c.name}{kind}{quoted}{status}")
                if c.status == FOUND_BY_PREFIX:
                    print(f"      resolved to: {c.candidates[0]}")
                elif c.status == AMBIGUOUS:
                    print(f"      {len(c.candidates)} candidates: {', '.join(c.candidates)}")
                if args.history and c.status in (AMBIGUOUS, MISSING):
                    print(f"      history: {git_history_status(c, Path.cwd())}")

    if by_prefix:
        total_prefix = sum(len(v) for v in by_prefix.values())
        print(f"FOUND BY PREFIX: {total_prefix} shortened citation(s) matched exactly one test name:")
        _print(by_prefix)
        print()

    if acknowledged:
        total_ack = sum(len(v) for v in acknowledged.values())
        print(f"ACKNOWLEDGED: {total_ack} missing citation(s) already documented in a report's Correction Note:")
        _print(acknowledged)
        print()

    if not missing:
        print(f"PASSED: every other test name cited in {scanned} report(s) under '{reports_dir}' exists under '{tests_dir}'.")
        return 0

    total = sum(len(v) for v in missing.values())
    n_ambiguous = sum(1 for v in missing.values() for c in v if c.status == AMBIGUOUS)
    print(f"FAILED: {total} cited test name(s) in {len(missing)} of {scanned} report(s) do not resolve under '{tests_dir}' "
          f"({total - n_ambiguous} missing, {n_ambiguous} ambiguous):")
    _print(missing)
    return 1


if __name__ == "__main__":
    sys.exit(main())
