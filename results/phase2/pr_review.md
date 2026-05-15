# Phase 2 PR — agent review

Phase 1 reviewer + arbiter run against the Phase 2 PR (`HEAD` vs `main`).
Per-file reviews. Findings merged across reviewer + arbiter with
approximate-match dedup.

## Summary

- Files reviewed: **4** Python files
- Total merged findings: **20**
- high: 2
- medium: 9
- low: 9

## `agents/writer.py` (M)

### [medium/correctness] lines 218–242

The pass-ranking block is not recorded on the `Attempt` it describes, so `pass_ranking_shown` is always `None` despite the field being added for logging purposes.

_Rationale:_ The docstring and field comment say `pass_ranking_shown` stores the rendered block shown to the writer at the iteration *following* this attempt. However, `render_pass_ranking` is called inside `_format_user_message` and the result is never assigned back to any `Attempt.pass_ranking_shown`. The caller (`write`) receives only a `WriterOutput` and has no path to set this field either. The logging intent is entirely unfulfilled — the field will always remain `None` for every attempt.

### [low/correctness] lines 162–168

When `include_pass_ranking=True` but `history` is empty, `render_pass_ranking` is never called (guarded by `if history:`), which is correct. However, when `include_pass_ranking=True` and `history` is non-empty, the pass ranking block is prepended *before* the `# Prior attempts` section header — but the ranking block itself uses `#` as its own markdown heading. This will produce two consecutive `#`-level headings with no intervening content, which may confuse the model's parsing of the document structure.

### [low/correctness] lines 218–242

`render_pass_ranking` sorts by raw `passed` count rather than pass *rate* (`passed/total`), which can misrank attempts when the total differs across attempts.

_Rationale:_ If an earlier attempt ran against 10 tests and passed 7, while a later attempt ran against 20 tests and passed 8, the later attempt ranks higher (8 > 7) even though its pass rate (40%) is much worse than the earlier one (70%). The docstring says the ranking IS the signal, so this misordering could mislead the writer. Whether totals can differ depends on the test harness, but the code makes no assumption they are constant.

### [low/correctness] lines 230–237

The `non_numeric` list is never sorted, so its insertion order (attempt index ascending) is incidental rather than guaranteed.

_Rationale:_ The docstring promises ties are broken by attempt index ascending, but non-numeric entries are appended in enumeration order, which happens to be ascending only because `enumerate` is used in order. This is correct incidentally, but the intent would be clearer — and more robust if the collection loop ever changes — with an explicit sort. Minor correctness risk if the loop is ever refactored.

---

## `eval/aggregate_iter3.py` (A)

### [high/correctness] lines 153–157

H2 crit2 checks `task_007` convergence using `raw['F'][s].get('task_007', {})`, but arm F is an iter3 arm stored under `ITER3_DIR`. If `task_007` is missing from arm F's data (e.g. it was not run or failed to load), the `.get` silently returns `{}`, `converged` is absent, so `bool({}.get('converged'))` is `False`. The criterion then counts as 0 converged out of 3, forcing H2 crit2 to FAIL with no warning. This is different from the reviewer's finding about malformed JSON; it is a silent-False issue specific to the task_007 lookup used exclusively for hypothesis evaluation.

### [medium/correctness] lines 85–97

The per-seed pass-rate and test-recall denominators are computed from only the tasks that were successfully loaded (`n = len(runs)`), not from the full task list; missing-data warnings are emitted but the metrics silently use a smaller denominator, making pass rates across arms incomparable when any arm has missing data.

_Rationale:_ If arm D is missing 2 tasks but arm B is not, `pass_rate` for arm D is computed over 11 tasks while arm B uses 13. The H1 criterion directly compares `converged` counts across arms without normalising, so the count comparison is still valid, but `pass_rate` and `test_recall` stored in the JSON are misleading and could be used downstream. At minimum the denominator should be the full `len(tasks)` or the discrepancy should be flagged more prominently.

### [medium/correctness] lines 108–119

The underspec task list `us_tasks` is derived from the manifest and may be empty (e.g. if the 'underspec' difficulty label changes or is absent). When `us_tasks` is empty, `us_rate` returns 0.0 for every arm and seed, causing all H1/H2 underspec criteria to silently produce 0.0 medians and potentially spurious PASS/FAIL results. No warning is emitted when `us_tasks` is empty.

### [medium/correctness] lines 176–191

The interaction effect `per_task_e_vs_f` hardcodes exactly three task IDs ('task_007', 'task_012', 'task_013'). If any of these tasks don't exist in `aggregate['per_task_by_arm']['E']` or `['F']` (e.g. they were not loaded due to missing files), the dict comprehension will raise a `KeyError` and abort the script, without a clear error message.

### [medium/correctness] lines 224–226

The human-readable output hardcodes '/13' and '/39' as denominators regardless of the actual number of tasks in the manifest. If the corpus grows or shrinks the printed fractions will be wrong while the underlying data is correct.

### [medium/correctness] lines 232–235

The per-task table filter uses only arm A's stability to decide which tasks to print, but does not check the stability of arms B–F; a task that is `stable_pass` in arm A but fails in another arm will be silently omitted from the output.

_Rationale:_ The condition `aggregate['per_task_by_arm']['A'][t]['stability'] != 'stable_pass'` only looks at arm A. If a task is `stable_pass` in arm A but `stable_fail` or `flippy` in arms D, E, or F (the new iter3 arms), it will be hidden from the printed table even though it is scientifically interesting. The aggregate JSON is still fully correct, but the human-readable summary — which is the main artifact cited in the narrative — will silently miss important regressions.

### [low/correctness] lines 52–54

`_load_run` silently swallows `json.JSONDecodeError` if a file exists but contains malformed JSON, because `p.read_text()` succeeds but `json.loads` will raise an unhandled exception that propagates as an uncaught error mid-loop rather than being treated as missing data.

_Rationale:_ This is not a silent suppression bug (the exception would propagate and terminate the script), but it is not caught like the missing-file case is, so a corrupted run file produces a hard crash rather than a graceful warning. For a research aggregation script that is supposed to be robust to partial data, this inconsistency is worth flagging.

### [low/correctness] lines 62–72

The missing-data check compares `loaded < len(tasks)`, which counts only successfully-loaded task files. If a task file exists but contains valid JSON that lacks expected keys (e.g. no 'converged' field), it is counted as loaded and no warning is emitted, but the later `r['converged']` access (line 90) will raise a `KeyError`.

### [low/correctness] lines 236–236

The comment says '(tasks not shown: stable_pass across all arms)' but the filter only checks arm A, so the comment is factually incorrect and misleading.

_Rationale:_ Minor documentation inaccuracy that misrepresents the filtering logic to future readers of the output.

---

## `eval/phase2_harness.py` (M)

### [high/correctness] lines 280–289

When `run_task` raises an exception, the fallback `TaskRun` is constructed without a `history` attribute, but `serialize_run` unconditionally iterates `run.history` and accesses `att.pass_ranking_shown`. This will raise an `AttributeError`, swallowing the original exception and crashing the serialization path.

### [medium/correctness] lines 171–182

Arm D imports `arbitrate` and `review` from the typed modules, but unlike arms C and E, it does NOT import `ARM_C_TYPED_FINDINGS_GUIDANCE`. The intent is `writer_extra_system=""` (no iter2 prompt), so the missing import is correct — but arm D is supposed to be the 'H1 control: typed schema only' condition. The table in the comment shows D as 'no iter2 writer prompt / no prior-attempt prompt', identical to arm C minus the writer prompt. However, arm C uses `ARM_C_TYPED_FINDINGS_GUIDANCE` as the extra system. Arm D sets `writer_extra_system=""` which matches the comment, but the factorial table in the header is misleading: both C and D appear in the 'no prior-attempt prompt' column yet differ in writer prompt. This is not a code bug, but arm D effectively duplicates arm C with the writer prompt stripped — arm C already has `include_pass_ranking=False`. The factorial design as implemented does not have a true 'no typed schema' baseline among D/E/F, making the 2×2 label in the comment incorrect (it's actually a 2×2 on writer-prompt × prior-attempt-ranking, all with typed schema).

### [medium/correctness] lines 250–252

Default output directory changed to `iter3` for all arms, silently breaking iter2 arms (A, B, C) when run without `--out_root`.

_Rationale:_ The comment says iter2 arms 'land in iter2 as before', but the code now sets `out_root = RESULTS_DIR / 'iter3'` unconditionally. Any new run with arm A, B, or C will write results into the iter3 directory instead of iter2, potentially mixing experiment data. The comment is aspirational but the code does not implement the conditional routing it describes.

### [low/correctness] lines 239–240

`include_pass_ranking` is read with `cfg.get("include_pass_ranking", False)` but `_arm_config` always returns a plain dict with that key explicitly set for every arm. The `.get()` with a default is therefore dead code that creates a false impression that the key might be absent. More importantly, if a future arm omits the key accidentally, the silent default `False` would suppress the feature without any warning.

### [low/style] lines 310–312

The `__main__` usage string still lists only arms A, B, C and does not mention the new D, E, F arms.

_Rationale:_ The help text `arms: A | B | C (or legacy: ...)` is now incomplete since D, E, and F are valid arms. Users invoking the script for the first time will not know these arms exist. Not a runtime bug, but makes the tool harder to use correctly.

---

## `eval/writer_loop.py` (M)

### [medium/correctness] lines 74–82

ranking_for_this_call is computed independently from write(), so the logged value may diverge from what the writer actually received.

_Rationale:_ render_pass_ranking(history) is called here to capture what was shown to the writer, but write() internally calls the same function again (with the same history) when include_pass_ranking=True. If render_pass_ranking is non-deterministic (e.g., uses timestamps, random ordering, or any mutable state), or if its implementation changes, the logged ranking_for_this_call and the actual ranking injected into the prompt will silently differ, making the log untrustworthy for experiment reproducibility. Even when it is deterministic today, calling the same function twice is fragile and the intent (log exactly what was shown) is not guaranteed by the current design.

### [low/correctness] lines 196–202

The __main__ block calls run_task without passing include_pass_ranking, so arms E and F cannot be exercised from the CLI even when run directly. The new parameter is silently defaulted to False with no way to pass it via argv.

---
