"""
Aggregate Phase 2 iter2 results across arms and seeds.

Reads results/phase2/iter2/<arm>/seed<N>/<task>.json for arms A, B, C and
seeds 1-3, then produces:

- results/phase2/iter2/aggregate.json  (machine-readable, all numbers)
- prints a human-readable summary to stdout for the iter2 writeup

Specifically reports:
- per-arm per-seed pass rate and test recall
- per-task convergence flippiness across seeds (3 = stable pass, 0 = stable fail)
- arm-B regression rate on task_013 (load-bearing control)
- arm-C result against pre-registered criterion
- adversarial-robustness sanity check (arm C only): count of attempted
  spec-violation findings, count downgraded, count of validated
  spec-violations actually present in spec, contamination rate.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITER2_DIR = ROOT / "results" / "phase2" / "iter2"
CORPUS_MANIFEST = ROOT / "phase2_corpus" / "manifest.json"

ARMS = [
    ("A_writer_alone", "A"),
    ("B_writer_reviewer_arbiter", "B"),
    ("C_writer_reviewer_arbiter_typed", "C"),
]
SEEDS = [1, 2, 3]


def _load_run(arm_dir: Path, seed: int, task_id: str) -> dict | None:
    p = arm_dir / f"seed{seed}" / f"{task_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def main() -> None:
    import sys

    manifest = json.loads(CORPUS_MANIFEST.read_text())
    tasks = [t["id"] for t in manifest["tasks"]]
    diff_of = {t["id"]: t["difficulty"] for t in manifest["tasks"]}

    # raw[arm_label][seed][task_id] = run dict
    raw: dict[str, dict[int, dict[str, dict]]] = {}
    missing_warnings: list[str] = []
    for arm_label, _ in ARMS:
        arm_dir = ITER2_DIR / arm_label
        raw[arm_label] = {}
        for seed in SEEDS:
            raw[arm_label][seed] = {}
            for t in tasks:
                r = _load_run(arm_dir, seed, t)
                if r is not None:
                    raw[arm_label][seed][t] = r
            loaded = len(raw[arm_label][seed])
            if loaded < len(tasks):
                # Surface partial seed directories. Silent zeros would
                # poison per-arm statistics; warn explicitly so the user
                # can decide whether to re-run or proceed.
                msg = (
                    f"WARNING: {arm_label} seed{seed} loaded {loaded}/{len(tasks)} tasks. "
                    f"Aggregate metrics for this seed are computed over the loaded subset only."
                )
                missing_warnings.append(msg)
                print(msg, file=sys.stderr)

    aggregate: dict = {
        "schema": "phase2-iter2-v1",
        "arms": [a for a, _ in ARMS],
        "seeds": SEEDS,
        "tasks": tasks,
        "per_seed": {},
        "per_task_by_arm": {},
        "criterion": {},
        "variance": {},
        "adversarial_robustness": {},
    }

    # Per-seed overall pass rate + test recall. Use string seed keys so the
    # in-memory dict matches the on-disk JSON form (json.dumps coerces int
    # keys to strings) — downstream consumers can index either way.
    for arm_label, _ in ARMS:
        aggregate["per_seed"][arm_label] = {}
        for seed in SEEDS:
            runs = raw[arm_label][seed]
            n = len(runs)
            conv = sum(1 for r in runs.values() if r["converged"])
            passed = sum(r["final_passed"] for r in runs.values())
            total = sum(r["final_total"] for r in runs.values())
            aggregate["per_seed"][arm_label][str(seed)] = {
                "n_tasks": n,
                "converged": conv,
                "pass_rate": conv / n if n else 0.0,
                "test_recall": passed / total if total else 0.0,
                "total_iterations": sum(r["iterations"] for r in runs.values()),
            }

    # Per-task convergence count across seeds, per arm
    for arm_label, _ in ARMS:
        aggregate["per_task_by_arm"][arm_label] = {}
        for t in tasks:
            convs = []
            test_pass = []
            for seed in SEEDS:
                run = raw[arm_label][seed].get(t)
                if run is None:
                    convs.append(None)
                    test_pass.append(None)
                else:
                    convs.append(run["converged"])
                    test_pass.append((run["final_passed"], run["final_total"]))
            n_conv = sum(1 for c in convs if c is True)
            aggregate["per_task_by_arm"][arm_label][t] = {
                "difficulty": diff_of[t],
                "convergence_per_seed": convs,
                "passes_per_seed": test_pass,
                "n_converged": n_conv,
                "stability": "stable_pass" if n_conv == 3 else ("stable_fail" if n_conv == 0 else "flippy"),
            }

    # Pre-registered criterion for arm C
    # 1. Underspec preserved: median underspec pass rate >= arm A's median.
    us_tasks = [t for t in tasks if diff_of[t] == "underspec"]

    def underspec_pass_rates(arm_label: str) -> list[float]:
        out = []
        for seed in SEEDS:
            run_set = raw[arm_label][seed]
            converged = sum(1 for t in us_tasks if run_set.get(t, {}).get("converged"))
            out.append(converged / len(us_tasks) if us_tasks else 0.0)
        return out

    a_us = underspec_pass_rates("A_writer_alone")
    c_us = underspec_pass_rates("C_writer_reviewer_arbiter_typed")
    a_us_median = statistics.median(a_us)
    c_us_median = statistics.median(c_us)
    crit1 = c_us_median >= a_us_median

    # 2. task_007 converges >= 2/3 arm-C seeds
    c_t007 = [
        bool(raw["C_writer_reviewer_arbiter_typed"][seed].get("task_007", {}).get("converged"))
        for seed in SEEDS
    ]
    crit2 = sum(c_t007) >= 2

    aggregate["criterion"] = {
        "criterion_1_underspec": {
            "arm_a_underspec_pass_per_seed": a_us,
            "arm_c_underspec_pass_per_seed": c_us,
            "arm_a_median": a_us_median,
            "arm_c_median": c_us_median,
            "passed": crit1,
        },
        "criterion_2_task_007": {
            "arm_c_task_007_converged_per_seed": c_t007,
            "n_converged": sum(c_t007),
            "passed": crit2,
        },
        "overall_passed": crit1 and crit2,
    }

    # Variance bound: arm-B regression rate on task_013 vs writer-alone
    # iter1 baseline: writer-alone task_013 converged 17/17.
    b_t013 = [
        bool(raw["B_writer_reviewer_arbiter"][seed].get("task_013", {}).get("converged"))
        for seed in SEEDS
    ]
    a_t013 = [
        bool(raw["A_writer_alone"][seed].get("task_013", {}).get("converged"))
        for seed in SEEDS
    ]
    b_t013_passes_per_total = [
        raw["B_writer_reviewer_arbiter"][seed].get("task_013", {}).get("final_passed", 0)
        for seed in SEEDS
    ]
    a_t013_passes_per_total = [
        raw["A_writer_alone"][seed].get("task_013", {}).get("final_passed", 0)
        for seed in SEEDS
    ]
    aggregate["variance"] = {
        "task_013": {
            "arm_a_converged_per_seed": a_t013,
            "arm_b_converged_per_seed": b_t013,
            "arm_a_passes_per_seed": a_t013_passes_per_total,
            "arm_b_passes_per_seed": b_t013_passes_per_total,
            "arm_b_regression_rate": sum(1 for c in b_t013 if not c) / len(b_t013),
            "interpretation": (
                "stable_regression" if sum(b_t013) == 0
                else ("partial_regression" if sum(b_t013) < 3 else "no_regression")
            ),
        },
        "task_007": {
            "arm_a_converged_per_seed": [
                bool(raw["A_writer_alone"][s].get("task_007", {}).get("converged")) for s in SEEDS
            ],
            "arm_b_converged_per_seed": [
                bool(raw["B_writer_reviewer_arbiter"][s].get("task_007", {}).get("converged"))
                for s in SEEDS
            ],
        },
    }

    # Adversarial robustness sanity check (arm C only). Single pass over
    # every reviewer + arbiter finding across all arm-C runs.
    arm_c_data = raw["C_writer_reviewer_arbiter_typed"]
    n_total_findings = 0
    n_spec_violation_validated = 0
    n_interpretation = 0
    n_unknown_type = 0  # finding_type missing / not in enum (should be 0 post-validation)
    n_downgraded = 0
    n_quote_in_spec = 0
    n_quote_not_in_spec = 0
    contamination = 0
    per_task_breakdown: dict[str, dict] = {}
    for seed in SEEDS:
        for t in tasks:
            run = arm_c_data[seed].get(t)
            if run is None:
                continue
            pt = per_task_breakdown.setdefault(t, {
                "violations": 0,
                "interpretations": 0,
                "unknown_type": 0,
                "downgraded": 0,
                "quote_in_spec": 0,
                "quote_not_in_spec": 0,
            })
            for att in run.get("history", []):
                for f in att.get("reviewer_feedback", []) + att.get("arbiter_feedback", []):
                    n_total_findings += 1
                    ft = f.get("finding_type")
                    qis = f.get("spec_quote_found_in_spec")
                    if "downgraded_reason" in f:
                        n_downgraded += 1
                        pt["downgraded"] += 1
                    if ft == "spec-violation":
                        n_spec_violation_validated += 1
                        pt["violations"] += 1
                        # Validator should have downgraded any SV with a quote
                        # not in spec. Surviving SV with qis=False is a leak.
                        if qis is False:
                            contamination += 1
                    elif ft == "spec-interpretation":
                        n_interpretation += 1
                        pt["interpretations"] += 1
                    else:
                        # finding_type missing or unrecognized post-validation.
                        # Should not happen given the validator; tracked
                        # explicitly rather than silently bucketed.
                        n_unknown_type += 1
                        pt["unknown_type"] += 1
                    if qis is True:
                        n_quote_in_spec += 1
                        pt["quote_in_spec"] += 1
                    elif qis is False:
                        n_quote_not_in_spec += 1
                        pt["quote_not_in_spec"] += 1

    aggregate["adversarial_robustness"] = {
        "total_findings": n_total_findings,
        "spec_violations_validated": n_spec_violation_validated,
        "spec_interpretations": n_interpretation,
        "findings_with_unknown_finding_type": n_unknown_type,
        # Count of findings with downgraded_reason set. Every downgrade
        # originates from either a spec-violation that failed validation or
        # an unknown finding_type, so this is the "attempted spec-violation
        # OR unknown type, reclassified" count — name kept verbose to avoid
        # the iter1-era mislabel.
        "findings_downgraded_total": n_downgraded,
        "findings_with_quote_in_spec": n_quote_in_spec,
        "findings_with_quote_not_in_spec": n_quote_not_in_spec,
        "contamination_count": contamination,
        "contamination_rate": (contamination / n_spec_violation_validated)
            if n_spec_violation_validated else 0.0,
        "per_task_breakdown": per_task_breakdown,
    }
    if missing_warnings:
        aggregate["missing_data_warnings"] = missing_warnings

    (ITER2_DIR / "aggregate.json").write_text(json.dumps(aggregate, indent=2))

    # Human-readable summary
    print("=" * 72)
    print("Phase 2 iter2 aggregate")
    print("=" * 72)
    print()
    print("Per-seed overall (converged / 13 tasks):")
    for arm_label, _ in ARMS:
        ps = aggregate["per_seed"][arm_label]
        row = "  " + arm_label.ljust(40)
        for seed in SEEDS:
            r = ps[str(seed)]
            row += f"  s{seed}: {r['converged']}/{r['n_tasks']}"
        print(row)
    print()

    print("Per-task convergence by arm (3 = stable pass, 0 = stable fail):")
    print(f"  {'task':12s} {'diff':10s}  arm A    arm B    arm C")
    for t in tasks:
        cells = []
        for arm_label, _ in ARMS:
            d = aggregate["per_task_by_arm"][arm_label][t]
            cells.append(f"  {d['n_converged']}/3 ({d['stability']:13s})")
        print(f"  {t:12s} {diff_of[t]:10s}  {cells[0]}  {cells[1]}  {cells[2]}")
    print()

    print("Pre-registered criterion for arm C:")
    c = aggregate["criterion"]
    print(f"  1. Underspec preserved: {c['criterion_1_underspec']['passed']}")
    print(f"     arm A pass-per-seed: {c['criterion_1_underspec']['arm_a_underspec_pass_per_seed']}")
    print(f"     arm C pass-per-seed: {c['criterion_1_underspec']['arm_c_underspec_pass_per_seed']}")
    print(f"     medians: A={c['criterion_1_underspec']['arm_a_median']:.3f}  "
          f"C={c['criterion_1_underspec']['arm_c_median']:.3f}")
    print(f"  2. task_007 converges 2/3+ seeds: {c['criterion_2_task_007']['passed']}")
    print(f"     arm C task_007 per-seed: {c['criterion_2_task_007']['arm_c_task_007_converged_per_seed']}")
    print(f"  Overall arm C: {'SUCCESS' if c['overall_passed'] else 'FAILURE'}")
    print()

    print("Variance bound on iter1 task_013 regression:")
    v = aggregate["variance"]["task_013"]
    print(f"  arm A converged per seed: {v['arm_a_converged_per_seed']}")
    print(f"  arm B converged per seed: {v['arm_b_converged_per_seed']}")
    print(f"  arm A test passes:        {v['arm_a_passes_per_seed']}")
    print(f"  arm B test passes:        {v['arm_b_passes_per_seed']}")
    print(f"  arm B regression rate:    {v['arm_b_regression_rate']*100:.0f}%")
    print(f"  interpretation:           {v['interpretation']}")
    print()

    print("Adversarial robustness (arm C):")
    ar = aggregate["adversarial_robustness"]
    print(f"  total findings:                    {ar['total_findings']}")
    print(f"  validated spec-violations:         {ar['spec_violations_validated']}")
    print(f"  spec-interpretations:              {ar['spec_interpretations']}")
    print(f"  unknown finding_type (post-validation): {ar['findings_with_unknown_finding_type']}")
    print(f"  findings downgraded (SV-attempt or unknown-type → interp): {ar['findings_downgraded_total']}")
    print(f"  quotes verified in spec:           {ar['findings_with_quote_in_spec']}")
    print(f"  quotes NOT in spec:                {ar['findings_with_quote_not_in_spec']}")
    print(f"  contamination (validated SV w/ bad quote): {ar['contamination_count']}")
    print()
    print("Per-task breakdown (arm C, summed across 3 seeds):")
    print(f"  {'task':12s} viol  interp  unkn  downgr  q_in  q_out")
    for t in tasks:
        pt = ar["per_task_breakdown"].get(t, {})
        print(f"  {t:12s}  {pt.get('violations',0):3d}    {pt.get('interpretations',0):3d}    "
              f"{pt.get('unknown_type',0):3d}     {pt.get('downgraded',0):3d}    "
              f"{pt.get('quote_in_spec',0):3d}   {pt.get('quote_not_in_spec',0):3d}")


if __name__ == "__main__":
    main()
