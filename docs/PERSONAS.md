# Personas

**This document is authoring documentation only. It must not be loaded into agent context.** The reviewer and arbiter agents see only diffs. Rubrics include the persona name as metadata for eval analysis, but no persona description.

The personas exist to make the corpus more naturalistic. Each one contributes a characteristic bug-type pattern. Real teams ship bugs that match these archetypes — flagging them isn't profiling, it's pattern recognition.

## Marcus — Senior backend, ~12 years

**Style:** Clean code. Terse commit messages. Skips tests when "the path is obvious." Reads cleanly line-by-line.

**Bug signature:** Subtle semantics. Race conditions in code that looks single-threaded. Edge cases in retry logic. Contract violations where the signature says one thing and the implementation does another. Falsy-vs-None confusion. Insecure defaults disguised as sensible fallbacks.

**Why he's hard to review:** The code is correct on the happy path. Bugs live in the unhappy path or in concurrency.

**Corpus PRs:** pr_002 (rename — control), pr_004 (race), pr_005 (retry contract), pr_006 (session expiry default), pr_007 (refactor — control)

## Priya — Mid-level, ~4 years, security-curious but not rigorous

**Style:** Knows the words. Reaches for security tools, sometimes the wrong one. Adds validation that looks thorough.

**Bug signature:** Almost-secure code. Validates the wrong input. Uses crypto primitives at the wrong layer (hashing then comparing with `==`, plain SHA where HMAC is needed). Regex sanitization of HTML. Pickle on untrusted data with type checks "for safety." SQL injection in a function that also has an allowlist.

**Why she's dangerous to review:** Review fatigue. The presence of *any* validation makes a reviewer's eye relax on the rest. Worse than no validation because no validation is at least obvious.

**Corpus PRs:** pr_001 (path traversal + secrets stack), pr_008 (SQL injection past validation), pr_009 (regex XSS), pr_010 (timing-vuln comparison), pr_011 (pickle)

## Devon — Junior, ~1 year, eager and copy-paste-y

**Style:** Loud. Lots of logging. Reuses helpers but doesn't always read them. Leaves debug code in. TODOs in committed code.

**Bug signature:** Obvious. Missing null checks. Off-by-one. No input validation. Debug logging full of secrets. Wrong HTTP status codes. UA-string parsing that returns "mozilla" for everything. The kind of bug a careful reviewer catches on first read.

**Why he's the system's recall test:** If the reviewer misses Devon-level bugs, the system has a serious recall problem. These should all be caught.

**Corpus PRs:** pr_003 (style+slice bug), pr_012 (UA parser nulls + wrong format), pr_013 (off-by-one), pr_014 (debug logs with secrets + TODO), pr_015 (open email relay), pr_016 (200 on error)

## Alex — Staff, ~9 years, opinionated

**Style:** Idiosyncratic. Clever one-liners. Refactors bundled with features. Reinvents existing tools.

**Bug signature:** Architectural. API contract changes via default-value tweaks. Hand-rolled versions of things that already exist. Test refactors that mock out the system under test. Bikeshed-bait style PRs that are sometimes pure noise and sometimes hide real issues.

**Why they're the arbiter's test:** Lots of surface findings, very few substantive ones. The arbiter has to demote correctly without over-demoting. Style-heavy PRs from Alex test whether the arbiter can recognize "no real issue here" without being fooled by visual complexity. And occasionally they ship a real architectural bug that needs to be elevated above the noise.

**Corpus PRs:** pr_017 (API contract break via default), pr_018 (clever refactor — control), pr_019 (reinvented send_from_directory), pr_020 (over-mocked tests + tautological assertion)

## Distribution

```
Marcus  5 PRs  (3 planted bug, 2 negative control)
Priya   5 PRs  (5 planted bug — all security-flavored)
Devon   6 PRs  (5 planted bug, 1 style+latent)
Alex    4 PRs  (2 planted bug, 1 negative control, 1 style+latent)
```

Total: 14 planted_bug, 3 negative_control, 3 style_nitpick_with_latent_bug.

## Isolation guarantees

The eval harness must enforce:

1. Agents receive only `before.py`, `after.py`, and `diff.patch`. Never `rubric.json` or `PERSONAS.md`.
2. The persona field in rubric.json exists for eval analysis (slicing scores by persona type). It is loaded by the scoring function, not the agent runner.
3. No shared loader function reads both rubric and agent input. Separation enforced in code.

If you find yourself wanting to pass persona info to an agent "as a hint" — don't. The point of the system is to detect bugs without persona priors.
