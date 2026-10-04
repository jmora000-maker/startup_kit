Here's the actual cycle we've been running, start to finish, with concrete examples from this session at each step.

## 1. Something surfaces a need for change

This comes from one of a few sources:
- **A new real SOW produces wrong output** (the Syngenta `arc_application_implementation` run showing wrong workstreams, a fabricated award date).
- **You ask for a new capability** (the deck, then the Streamlit review UI).
- **An investigation turns up something nobody was looking for** (the citation checker finding 25 fabricated test names across the spec).

Whatever the trigger, nothing gets fixed yet — the first job is understanding it precisely.

## 2. I investigate the real artifacts directly

I open the actual generated files (not a summary of them), read the real git history, trace the actual code path — never guess at root cause from a description. This is where things like the `PHASE_LABEL_REGEX` anchoring bug, or the `.gitignore`'s UTF-16 corruption, actually got found: by looking, not assuming.

## 3. I write the spec change — never the coding agent

Every revision follows the same shape: a new or revised requirement, a reason recorded (usually in a numbered appendix — Appendix N, O, S, T, and so on — so the *why* survives, not just the *what*), a changelog line, and a fingerprint (an MD5 hash) so we can always confirm which exact version is in front of us. `QA-11` means the agent is never allowed to touch `spec\` — that boundary has held for the entire session.

## 4. You review and commit the spec

You read what changed, push back if something's wrong (the `VAL-11` tie-break reversal is the clearest example — you overruled my lean and that became the decided answer), and commit it. Nothing gets implemented against an uncommitted spec.

## 5. I write a scoped prompt for the coding agent

Each prompt:
- Starts with a pre-check (confirm the working tree is clean before starting).
- States scope boundaries explicitly — what *not* to touch, which files are off-limits (`tests\oracles\`, `spec\`).
- Follows `QA-10`'s discipline: **prove the bug fails first, then fix it, then prove the fix passes** — never just apply a fix and declare victory.
- Asks for raw evidence: actual quoted code, actual test output, actual diffs — not a prose summary of what supposedly happened.
- Often gets split into parts (Part 1/2/3) when a task is large, so each part commits independently and can be reviewed before the next starts.

## 6. You run it against the coding agent, it reports back

## 7. I review the report critically before accepting anything

This is the step that's caught the most real problems this session:
- Checking whether claimed evidence is real (the fabricated `test_inv_33_passes_on_phase_workstreams` names that never existed).
- Checking whether the fix is scoped correctly, or quietly did something unasked.
- Asking follow-up investigation when something doesn't add up (the stale-file investigation, the `git log` archaeology on the mislabeled "rev 16 spec" commit).
- Sometimes this loops several times before I'm satisfied — this step is allowed to take as many rounds as it needs.

## 8. For anything touching generated output, I review the actual diff — not a summary of it

Snapshot changes get reviewed line by line against the approved baseline, every difference accounted for and tied to a specific, intended cause. "The content looks fine, trust me" has never been sufficient here — I've asked for the real diff every time, and it's caught real problems more than once (the `WBS-05` latent bug hiding in snapshots nobody had looked at closely).

## 9. Promotion

Only once I've actually confirmed the diff is clean: `pytest --update-snapshots`, a final `pytest -q` to confirm zero failures, commit, push. The coding agent is never the one who approves its own output becoming the new baseline — that step is always yours.

## 10. Close the loop, which usually opens the next one

I write up what was found as a new spec revision — marking things Done with real evidence, logging anything still open as a named finding rather than letting it quietly vanish. Those open findings often become the next cycle's starting point (the Kit re-ingestion provenance gap, the `mock_sow` date-pattern misses, and now the six zero-coverage test requirements are all sitting exactly there, waiting to be picked up).

---

**The thread that runs through all ten steps:** the coding agent proposes and implements; it never grades its own work, never touches the spec, and never gets to decide a fix is correct — a human (you, or me reviewing on your behalf) checks real evidence before anything is accepted as true.