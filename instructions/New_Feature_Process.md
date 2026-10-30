**Updated process, with the feedback loop made explicit:**

1. Clarify the request.

2. Log it in the spec.

3. Send an investigation-first prompt.

4. Review the investigation for real evidence.

5. Approve the design.

6. Request implementation.

7. Review the implementation against real evidence (files, raw test output, structural counts).

8. Push back on anything inconsistent or fabricated.

9. Commit, version-bump, push — verify the real git log.

10. Mark the spec item Done.

11. Deploy, then smoke-test the deployed instance.

12. You run real UAT against the deployed app — using it the way an actual user would, with real documents, for real work.

13. Whatever UAT surfaces becomes new input, not an afterthought — it goes back to step 1: a new backlog item gets logged (sometimes immediately, like HTL-62’s silent truncation or HTL-65’s trace misattribution), scoped, investigated, and fixed through the same cycle.
    Repeat for as many rounds as it takes before the next deploy.

The reason this matters, concretely: my own review (steps 4–8) only catches what I think to check against what the coding agent claims. UAT catches things neither of us was looking for — real usage surfaces gaps that no amount of scrutinizing a described test result would find, because the defect only shows up when you’re actually trying to use the thing for its real purpose. That’s exactly why several of tonight’s most important findings came from you looking at a real generated deck, not from anything I verified in review.



Here's the real process, as it's actually played out across tonight's work — not an idealized version, but what I've genuinely been doing:

**1. Clarify before committing to a design.** When a request is ambiguous or has real open questions (like `HTL-72`'s slide mapping, the subtitle treatment, how the acceptance-process slide should work), I ask specific, substantive questions rather than guessing — and I keep asking until the genuinely important ones are resolved, even if it takes several rounds.

**2. Log it in the spec before any code gets touched.** Once a feature or fix is sufficiently specified, I write it into `PMO_Startup_Kit_Consolidated_Spec.md` as a new numbered item, bump the revision, add a changelog row, verify there are no duplicate IDs, and hand you the file to commit. This is the durable record — if a session gets compacted or a new one starts, the spec is what survives.

**3. Send an investigation-first prompt, not an implementation request.** For anything nontrivial, I ask the coding agent to investigate and propose a design, explicitly saying "do not implement yet" — quoting real code, real file structure, running real tests where relevant.

**4. Review the investigation like it might be wrong, because it sometimes is.** I check whether the response actually contains real evidence — quoted code, real command output, real file content — versus vague description or (as just happened with `HTL-72`) generic marketing-style filler with nothing underneath it. If it's not real, I reject it and ask for a redo, pointing at exactly what's missing.

**5. Approve the design, sometimes after multiple rounds of pushback**, once it holds up to scrutiny.

**6. Request implementation**, usually specifying up front what verification I'll require — specific real test cases, visual rendering, etc.

**7. Review the implementation the same way — insisting on real evidence.** Real code diffs, not descriptions. Real raw test output, not summarized pass counts. For anything visual (a deck, a document), I insist on the actual file being uploaded so I can render and inspect it myself — a described inspection isn't acceptable. For data correctness, I check real structural counts against the real source document, not just "the content is present" (this is `HTL-64`'s standing rule, born from exactly this kind of gap being caught).

**8. Push back hard on anything inconsistent or fabricated.** Tonight alone caught a fabricated "live test" using invented content, real cross-client data contamination traced to its actual root cause, a silent content-truncation bug, and test-count reporting that gave three different answers for the same commit. Each time, I asked for the real thing rather than accepting a plausible-sounding narrative.

**9. Commit, version-bump, and push — then verify the real git log.** I give exact commands and ask for the literal `git log`/`git status` output to confirm it actually landed on `origin/main`, not just that the commands were run.

**10. Mark the spec item Done**, with a real summary of what shipped and how it was verified, same revision-bump discipline as step 2.

**11. Deploy, then smoke-test the deployed instance**, not just the local environment — local and Cloud Run have genuinely diverged before (the Firestore-vs-emulator gap).

**12. Keep the backlog honest.** Anything discovered along the way that isn't the immediate task gets logged as its own item rather than lost, and I periodically surface the whole backlog so you can decide what's next.



The throughline is: nothing gets trusted just because it's described well — content quality, test results, and structural correctness all get independently checked against something real before I'll approve a commit.
