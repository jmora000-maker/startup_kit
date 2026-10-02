That sentence describes the loop to follow whenever a problem turns up. Here it is step by step, with examples from this project.

**Step 1: Find it in review.**
Notice something wrong in the generated documents, by reading them against the SOW or through a Talent PM's edits. Write it down precisely: which file, which row or cell, what it says, and what it should say.
*Example:* "The Kit work package for HS-4770 reads 'HS-4770: Pipeline Quality Gates...' (the deliverable name), but the SOW gives the story its own title."

**Step 2: Decide what kind of check would catch it.**
Ask: *is this a fact about one particular SOW, or a rule that must hold for every SOW?*

- **A fact about one SOW → add it to that SOW's oracle** (`tests\oracles\<name>.json`). Only you write oracle facts, taken straight from the contract.
  *Examples:* "ARC has 4 gates"; "HS-4770 belongs to P1"; "HS-4770's title is 'Pipeline quality-gate and deployment smoke-check automation'"; "this SOW states no award date".
- **A rule that holds for every SOW → add an invariant** (the checks run by `check_artifacts` and the test suite).
  *Examples:* "no checkpoint has phase N/A"; "every work package has a real parent"; "no Contract Reference is a fragment like 'schedule is'"; "predecessors only point backward".

Some problems need both. Wrong phases needed an oracle fact (which phase each story is in) *and* an invariant (each deliverable must sit in its oracle phase).

**Step 3: Add the check before fixing anything.**
- **For an oracle fact,** edit the oracle yourself and commit it:
  ```text
  git add tests\oracles\arc.json
  git commit -m "Oracle: <the fact>"
  ```
- **For an invariant,** ask Junie to add it, together with a deliberately broken test that proves it can fail. Make it explicit that Junie must not fix the underlying problem yet.

**Step 4: Confirm the check fails on the current output.**
Run `pytest -q`, or `python -m src.tools.check_artifacts output`. The new check must fail, for the reason you found in step 1.
- **If it fails:** the check works. Go on.
- **If it passes:** the check is too weak. That's what happened when the title test compared only the first 4 words. Tighten it before going on.

**Step 5: Fix it.**
Add the finding to the spec as a revision, and give Junie the prompt to fix the code. Junie must not change the check or the oracle to make things pass.

**Step 6: Confirm the fix.**
- The new check now passes.
- `pytest -q` shows only the expected snapshot differences.
- You review those differences, and promote with `.\promote_snapshots.ps1`.

**Why the order matters.**
- Adding the check first, and seeing it fail, proves it can catch the problem.
- Fixing second proves the fix is what made it pass.
- The check then stays in the test suite permanently. If a later change, a new SOW or a different AI extraction ever brings the problem back, the tests fail straight away. You no longer depend on someone noticing it in a review.

That's the pattern behind most of this project's revisions: the wrong phases, the hard-coded titles, the 10 milestones and the missing checkpoint phases were each found in review, turned into an oracle fact or invariant, and then fixed.
