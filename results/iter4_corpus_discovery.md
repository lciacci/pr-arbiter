# Iteration 4 — corpus discovery, not prompt iteration

Run date: 2026-05-13. This iteration found that the "persistent hallucination"
on pr_007 — flagged across all six prior runs — is not a hallucination. The
rubric mislabels a real architectural foot-gun as a clean refactor.

## The supposed hallucination

In iter1, iter2, and iter3, the reviewer consistently flagged pr_007 with a
finding like:

> `_parse_env_bool` is inconsistent with `get_debug_flag`: for the same env
> var pattern, `get_debug_flag` returns `True` for truthy strings, but
> `_parse_env_bool` returns `False` for those same truthy strings.

The rubric labels pr_007 as `negative_control` with summary "Extracts the
environment-variable-as-bool parsing logic from `get_load_dotenv` into a
private helper `_parse_env_bool`. Semantically identical; no behavior change."
The reviewer's finding therefore counted as a false positive on every run.

After six runs the pattern was durable enough to investigate, on the assumption
the reviewer was over-eager. The opposite turned out to be true.

## What the diff actually does

Before:
```python
def get_load_dotenv(default: bool = True) -> bool:
    """Get whether the user has disabled loading default dotenv files by
    setting FLASK_SKIP_DOTENV."""
    val = os.environ.get("FLASK_SKIP_DOTENV")
    if not val:
        return default
    return val.lower() in ("0", "false", "no")
```

After:
```python
def _parse_env_bool(name: str, default: bool) -> bool:
    """Parse an environment variable as a boolean.

    Returns ``default`` if the variable is unset or empty. Otherwise
    returns True unless the value matches one of the recognized
    'falsy' string forms.
    """
    val = os.environ.get(name)
    if not val:
        return default
    return val.lower() in ("0", "false", "no")


def get_load_dotenv(default: bool = True) -> bool:
    return _parse_env_bool("FLASK_SKIP_DOTENV", default)
```

The function-body returns `val.lower() in ("0", "false", "no")` — the same as
the original. For the *single existing caller* (`get_load_dotenv` with the
`FLASK_SKIP_DOTENV` inverted-naming convention), runtime behavior is preserved.
The rubric is correct about that.

The refactor introduces **two new problems** that did not exist before:

### Problem 1: docstring/implementation mismatch

The new docstring says:

> Otherwise returns True unless the value matches one of the recognized
> 'falsy' string forms.

Reading carefully: "returns True UNLESS falsy" = returns True when value is
**not** in `{"0", "false", "no"}`. For val="1" → True; for val="0" → False.

The implementation does the opposite: `return val.lower() in ("0", "false", "no")`
returns True when value **is** in the falsy set. For val="1" → False; for
val="0" → True.

A future maintainer reading the docstring will believe the function does
conventional truthy parsing. It does not. This is a bug planted by the
refactor — the original `get_load_dotenv` had an inverted convention but
documented itself accurately ("get whether the user has *disabled*…").

### Problem 2: inconsistency with the neighboring function

The same file already has a generic env-bool parser:

```python
def get_debug_flag() -> bool:
    val = os.environ.get("FLASK_DEBUG")
    return bool(val and val.lower() not in {"0", "false", "no"})
```

This uses **conventional** boolean semantics: True when not falsy.

After the refactor, the file contains two ways to parse an env var as a
boolean, with opposite semantics:

- `get_debug_flag` (existing): True when value is truthy.
- `_parse_env_bool` (new): True when value is *falsy*.

Both are private to the module. A future developer writing
`def get_some_flag(): return _parse_env_bool("FLASK_SOMETHING", False)` will
get silently inverted behavior. The `_parse_env_bool` name does not signal
this — it implies the conventional reading the `get_debug_flag` body uses.

## Why the rubric missed it

The rubric author was checking "does the refactor preserve runtime behavior
of the single existing caller?" The answer is yes. They didn't check "does
the refactor introduce a foot-gun for future callers?" — which is exactly
what the reviewer was flagging.

The `should_not_flag` list does say "The 'not val' check carrying over from
the original — unchanged behavior is not a new bug." But the reviewer isn't
flagging unchanged behavior. It's flagging that the new helper's
documentation and naming set up a future bug that didn't exist before.

## Implications

This isn't just a corpus correction. It changes the read on every prior result:

- **Reviewer is more accurate than the rubric credits.** Across six runs the
  reviewer flagged a real architectural issue and was penalized for it.
- **The "negative control failure rate" metric is misleading on this corpus.**
  pr_007 should not be a negative control. The 1/3 NC failure rate that has
  persisted across all configurations is, at least in part, the system being
  right on a mislabeled item.
- **Iter3's "advisory tier surfaces real bugs" thesis is reinforced.** The
  mutual triage put pr_007 in advisory (one voter KEEP, one DROP) — which is
  exactly the right disposition for a finding that's correct but borderline.
  The human reviewer would see it; the system wouldn't block on it.

## Proposed corpus change (NOT applied yet — needs approval)

Relabel `pr_007`:

```diff
- "category": "negative_control"
+ "category": "planted_bug_unintentional"   # or just "style_with_latent_bug"
```

Add to `expected_findings`:

```json
{
  "id": "F1",
  "category": "correctness",
  "severity": "medium",
  "file": "after.py",
  "line_range": [35, 47],
  "description": "_parse_env_bool docstring promises 'returns True unless value is falsy', but the implementation returns True if value IS in the falsy set — opposite semantics. Worse, the file already contains get_debug_flag which uses conventional truthy parsing; the new helper invites silent inversion bugs for future callers."
}
```

Update `summary` to acknowledge the issue.

Update `notes_for_arbiter`: this is a finding the arbiter should KEEP at
medium severity (not block, but flag) — exactly where iter3's advisory tier
places it.

The other two negative controls (`pr_002`, `pr_018`) should be re-audited too
to make sure the same kind of mislabel isn't hiding there.

## What would the numbers look like post-correction?

A quick estimate, assuming the pr_007 finding is credited as a medium-severity
match in iter3 blocking tier:

- iter3 blocking precision: would go from 58.5% to ~62% (1 FP becomes 1 TP).
- iter3 advisory tier: gains a correctly-credited finding.
- Negative controls: drop from 3 → 2. NC failure rate becomes 0/2 in iter3
  blocking and final slices (pr_018 already dropped by triage).
- All six configurations re-score; the relative ranking probably doesn't
  change but the absolute numbers move in the system's favor.

## Recommendation

Do not change the corpus to help the agent. **But do correct a mislabeled
corpus item once you've discovered the mislabel.** The bar is whether the
corpus is correct about ground truth, not whether the agent looks good.

If you agree the analysis above is right, the right move is:

1. Update pr_007 rubric to add the `_parse_env_bool` finding as a medium-
   severity expected finding, change category from `negative_control` to
   `style_with_latent_bug` (or a new category).
2. Audit pr_002 and pr_018 for similar mislabels. Don't trust "looks clean
   to the rubric author" without re-reading the diff carefully.
3. Re-run scoring against the corrected rubric. No agent calls needed —
   `score_pr` reads the rubric, the cached findings are unchanged.

## Audit results for the other two negative controls

- **pr_002** (Marcus, `config.py`): renames the local variable `d` to
  `config_module` in `from_pyfile`. Pure rename, no semantic change.
  **Confirmed true negative control.** Across all six runs, no agent flagged it.
- **pr_018** (Alex, `helpers.py`): refactors
  `if not val: return default\nreturn val.lower()...` into a ternary
  `val.lower()... if val else default`. Pure style refactor, no semantic
  change. **Confirmed true negative control.** Note: pr_018's `after.py`
  doesn't have the `_parse_env_bool` extraction — it's an earlier helpers.py
  state. The iter2 arbiter's FP on this PR was a real hallucination (since
  dropped by iter3 mutual triage).

So only pr_007 is mislabeled. The other two negative controls are correctly
labeled.

If you disagree (i.e., you think the reviewer is over-reading what a
maintainer would notice), the corpus stays as-is and we accept that the
system gets penalized for surfacing this kind of issue. That's also a
legitimate position — depending on how much you weight "won't generalize to
maintainers who'd read code carefully."

## Pause point

This is a better stopping point than another prompt iteration. The
architectural story is told (iter3), the corpus has been stress-tested by
the agents to the point of finding a mislabel, and the next move requires
your judgment on what the corpus should call ground truth. Cheaper to think
than to run more API calls.
