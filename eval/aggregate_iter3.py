"""
Aggregate Phase 2 iter3 results.

Reads:
- iter2 arm C from results/phase2/iter2/C_writer_reviewer_arbiter_typed/
- iter3 arms D, E, F from results/phase2/iter3/<label>/
- iter2 arms A, B from results/phase2/iter2/ for reference comparisons.

Produces:
- results/phase2/iter3/aggregate.json (machine-readable)
- prints a human-readable summary to stdout including H1 / H2 / interaction.

The aggregator is the load-bearing iter3 artifact alongside the trajectory
narrative. Computes pre-registered criteria from iter3_preregistration.md
without modification.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results" / "phase2"
ITER2_DIR = RESULTS / "iter2"
ITER3_DIR = RESULTS / "iter3"
CORPUS_MANIFEST = ROOT / "phase2_corpus" / "manifest.json"

# Map arm name → (root_dir, label_dir). Arm C is reused from iter2.
ARMS = [
    ("A", ITER2_DIR, "A_writer_alone"),
    ("B", ITER2_DIR, "B_writer_reviewer_arbiter"),
    ("C", ITER2_DIR, "C_writer_reviewer_arbiter_typed"),
    ("D", ITER3_DIR, "D_typed_no_writer_prompt"),
    ("E", ITER3_DIR, "E_typed_iter2prompt_plus_ranking"),
    ("F", ITER3_DIR, "F_typed_ranking_only"),
]
SEEDS = [1, 2, 3]


def _load_run(root: Path, label: str, seed: int, task_id: str) -> dict | None:
    p = root / label / f"seed{seed}" / f"{task_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def main() -> None:
    manifest = json.loads(CORPUS_MANIFEST.read_text())
    tasks = [t["id"] for t in manifest["tasks"]]
    diff_of = {t["id"]: t["difficulty"] for t in manifest["tasks"]}
    us_tasks = [t for t in tasks if diff_of[t] == "underspec"]

    raw: dict[str, dict[int, dict[str, dict]]] = {}
    missing: list[str] = []
    for arm, root, label in ARMS:
        raw[arm] = {}
        for seed in SEEDS:
            raw[arm][seed] = {}
            for t in tasks:
                r = _load_run(root, label, seed, t)
                if r is not None:
                    raw[arm][seed][t] = r
            loaded = len(raw[arm][seed])
            if loaded < len(tasks):
                msg = f"WARNING: arm {arm} seed{seed} loaded {loaded}/{len(tasks)} tasks"
                missing.append(msg)
                print(msg, file=sys.stderr)

    aggregate: dict = {
        "schema": "phase2-iter3-v1",
        "arms": [a for a, _, _ in ARMS],
        "seeds": SEEDS,
        "tasks": tasks,
        "per_seed": {},
        "per_task_by_arm": {},
        "underspec_per_seed": {},
        "criteria": {},
        "interaction_effect": {},
    }

    # Per-seed aggregate
    for arm, _, _ in ARMS:
        aggregate["per_seed"][arm] = {}
        for seed in SEEDS:
            runs = raw[arm][seed]
            n = len(runs)
            conv = sum(1 for r in runs.values() if r["converged"])
            passed = sum(r["final_passed"] for r in runs.values())
            total = sum(r["final_total"] for r in runs.values())
            aggregate["per_seed"][arm][str(seed)] = {
                "n_tasks": n,
                "converged": conv,
                "pass_rate": conv / n if n else 0.0,
                "test_recall": passed / total if total else 0.0,
            }

    # Per-task per-arm convergence stability
    for arm, _, _ in ARMS:
        aggregate["per_task_by_arm"][arm] = {}
        for t in tasks:
            convs = []
            for seed in SEEDS:
                run = raw[arm][seed].get(t)
                convs.append(bool(run and run["converged"]))
            n_conv = sum(convs)
            aggregate["per_task_by_arm"][arm][t] = {
                "difficulty": diff_of[t],
                "convergence_per_seed": convs,
                "n_converged": n_conv,
                "stability": "stable_pass" if n_conv == 3 else (
                    "stable_fail" if n_conv == 0 else "flippy"
                ),
            }

    # Underspec pass rates per seed
    def us_rate(arm: str, seed: int) -> float:
        run_set = raw[arm][seed]
        c = sum(1 for t in us_tasks if run_set.get(t, {}).get("converged"))
        return c / len(us_tasks) if us_tasks else 0.0

    for arm, _, _ in ARMS:
        per_seed = [us_rate(arm, s) for s in SEEDS]
        aggregate["underspec_per_seed"][arm] = {
            "per_seed": per_seed,
            "median": statistics.median(per_seed),
            "task_012_per_seed": [
                bool(raw[arm][s].get("task_012", {}).get("converged")) for s in SEEDS
            ],
            "task_013_per_seed": [
                bool(raw[arm][s].get("task_013", {}).get("converged")) for s in SEEDS
            ],
        }

    # H1: arm D matches arm B aggregate ± 1 task/seed AND D underspec ≥ A.
    d_per_seed = [aggregate["per_seed"]["D"][str(s)]["converged"] for s in SEEDS]
    b_per_seed = [aggregate["per_seed"]["B"][str(s)]["converged"] for s in SEEDS]
    delta_per_seed = [d - b for d, b in zip(d_per_seed, b_per_seed)]
    h1_crit1 = all(abs(x) <= 1 for x in delta_per_seed)

    a_us_median = aggregate["underspec_per_seed"]["A"]["median"]
    d_us_median = aggregate["underspec_per_seed"]["D"]["median"]
    h1_crit2 = d_us_median >= a_us_median

    aggregate["criteria"]["H1_schema_neutrality"] = {
        "crit1_within_noise_floor_vs_B": {
            "d_per_seed": d_per_seed,
            "b_per_seed": b_per_seed,
            "delta_per_seed": delta_per_seed,
            "passed": h1_crit1,
        },
        "crit2_underspec_no_regression_vs_A": {
            "a_median": a_us_median,
            "d_median": d_us_median,
            "passed": h1_crit2,
        },
        "overall_passed": h1_crit1 and h1_crit2,
    }

    # H2: arm F underspec median > arm A median (strict) AND F task_007 conv >= 2/3.
    f_us_median = aggregate["underspec_per_seed"]["F"]["median"]
    h2_crit1 = f_us_median > a_us_median  # strict
    f_t007 = [
        bool(raw["F"][s].get("task_007", {}).get("converged")) for s in SEEDS
    ]
    h2_crit2 = sum(f_t007) >= 2

    aggregate["criteria"]["H2_attempt_comparison"] = {
        "crit1_underspec_strict_improvement_vs_A": {
            "a_median": a_us_median,
            "f_median": f_us_median,
            "passed": h2_crit1,
        },
        "crit2_task_007_no_regression": {
            "f_task_007_per_seed": f_t007,
            "n_converged": sum(f_t007),
            "passed": h2_crit2,
        },
        "overall_passed": h2_crit1 and h2_crit2,
    }

    # Interaction (descriptive, not pass/fail)
    e_agg = sum(aggregate["per_seed"]["E"][str(s)]["converged"] for s in SEEDS)
    f_agg = sum(aggregate["per_seed"]["F"][str(s)]["converged"] for s in SEEDS)
    if abs(e_agg - f_agg) <= 1:
        interaction = "approximately_equal"
    elif e_agg < f_agg:
        interaction = "iter2_prompt_harmful_under_ranking"
    else:
        interaction = "iter2_prompt_rescued_by_ranking"
    aggregate["interaction_effect"] = {
        "arm_e_aggregate": e_agg,
        "arm_f_aggregate": f_agg,
        "delta": e_agg - f_agg,
        "interpretation": interaction,
        "per_task_e_vs_f": {
            t: {
                "E": aggregate["per_task_by_arm"]["E"][t]["n_converged"],
                "F": aggregate["per_task_by_arm"]["F"][t]["n_converged"],
            }
            for t in ["task_007", "task_012", "task_013"]
        },
    }

    # Adversarial-robustness sanity check per typed-schema arm (C, D, E, F).
    aggregate["adversarial_robustness"] = {}
    for arm in ("C", "D", "E", "F"):
        totals = {
            "total_findings": 0,
            "spec_violations_validated": 0,
            "spec_interpretations": 0,
            "findings_downgraded_total": 0,
            "findings_with_quote_in_spec": 0,
            "findings_with_quote_not_in_spec": 0,
            "contamination_count": 0,
        }
        for seed in SEEDS:
            for t in tasks:
                run = raw[arm][seed].get(t)
                if run is None:
                    continue
                for att in run.get("history", []):
                    for f in att.get("reviewer_feedback", []) + att.get("arbiter_feedback", []):
                        totals["total_findings"] += 1
                        ft = f.get("finding_type")
                        qis = f.get("spec_quote_found_in_spec")
                        if "downgraded_reason" in f:
                            totals["findings_downgraded_total"] += 1
                        if ft == "spec-violation":
                            totals["spec_violations_validated"] += 1
                            if qis is False:
                                totals["contamination_count"] += 1
                        elif ft == "spec-interpretation":
                            totals["spec_interpretations"] += 1
                        if qis is True:
                            totals["findings_with_quote_in_spec"] += 1
                        elif qis is False:
                            totals["findings_with_quote_not_in_spec"] += 1
        aggregate["adversarial_robustness"][arm] = totals

    if missing:
        aggregate["missing_data_warnings"] = missing

    (ITER3_DIR / "aggregate.json").write_text(json.dumps(aggregate, indent=2))

    # Human-readable
    print("=" * 78)
    print("Phase 2 iter3 aggregate")
    print("=" * 78)
    print()
    print("Per-seed converged / 13:")
    print(f"  {'arm':40s}  s1   s2   s3   total")
    for arm, _, label in ARMS:
        ps = aggregate["per_seed"][arm]
        cells = [ps[str(s)]["converged"] for s in SEEDS]
        print(f"  {arm} ({label}):".ljust(42)
              + f"  {cells[0]}/13 {cells[1]}/13 {cells[2]}/13   {sum(cells)}/39")
    print()

    print("Per-task convergence (arm × task → n_converged / 3 across seeds):")
    print(f"  {'task':12s} {'diff':10s} " + " ".join(f"{a:>5s}" for a, _, _ in ARMS))
    for t in tasks:
        if t in ("task_007", "task_012", "task_013") or aggregate["per_task_by_arm"]["A"][t]["stability"] != "stable_pass":
            cells = []
            for arm, _, _ in ARMS:
                cells.append(f"{aggregate['per_task_by_arm'][arm][t]['n_converged']}/3")
            print(f"  {t:12s} {diff_of[t]:10s} " + " ".join(f"{c:>5s}" for c in cells))
    print("  (tasks not shown: stable_pass across all arms)")
    print()

    print("Underspec pass rate per seed (task_012 + task_013):")
    for arm, _, _ in ARMS:
        us = aggregate["underspec_per_seed"][arm]
        print(f"  arm {arm}: per_seed={us['per_seed']}  median={us['median']:.3f}")
    print()

    h1 = aggregate["criteria"]["H1_schema_neutrality"]
    print("H1 (schema-neutrality):")
    print(f"  crit 1 (D vs B within ±1/seed): delta={h1['crit1_within_noise_floor_vs_B']['delta_per_seed']}  "
          f"PASS={h1['crit1_within_noise_floor_vs_B']['passed']}")
    print(f"  crit 2 (D underspec ≥ A): A={h1['crit2_underspec_no_regression_vs_A']['a_median']:.3f} "
          f"D={h1['crit2_underspec_no_regression_vs_A']['d_median']:.3f}  "
          f"PASS={h1['crit2_underspec_no_regression_vs_A']['passed']}")
    print(f"  H1 overall: {'PASS' if h1['overall_passed'] else 'FAIL'}")
    print()

    h2 = aggregate["criteria"]["H2_attempt_comparison"]
    print("H2 (attempt-comparison):")
    print(f"  crit 1 (F underspec STRICT > A): A={h2['crit1_underspec_strict_improvement_vs_A']['a_median']:.3f} "
          f"F={h2['crit1_underspec_strict_improvement_vs_A']['f_median']:.3f}  "
          f"PASS={h2['crit1_underspec_strict_improvement_vs_A']['passed']}")
    print(f"  crit 2 (F task_007 conv ≥ 2/3): {h2['crit2_task_007_no_regression']['f_task_007_per_seed']}  "
          f"n={h2['crit2_task_007_no_regression']['n_converged']}  "
          f"PASS={h2['crit2_task_007_no_regression']['passed']}")
    print(f"  H2 overall: {'PASS' if h2['overall_passed'] else 'FAIL'}")
    print()

    inter = aggregate["interaction_effect"]
    print(f"Interaction (descriptive): E={inter['arm_e_aggregate']}/39  F={inter['arm_f_aggregate']}/39  "
          f"delta={inter['delta']:+d}  → {inter['interpretation']}")
    print("  Per-task E vs F:")
    for t, v in inter["per_task_e_vs_f"].items():
        print(f"    {t}: E={v['E']}/3  F={v['F']}/3")
    print()
    print("Adversarial robustness (typed-schema arms):")
    print(f"  {'metric':35s} " + " ".join(f"{a:>6s}" for a in ("C","D","E","F")))
    keys = [
        ("total_findings", "total findings"),
        ("spec_violations_validated", "validated spec-violations"),
        ("spec_interpretations", "spec-interpretations"),
        ("findings_downgraded_total", "downgrades"),
        ("findings_with_quote_in_spec", "quotes in spec"),
        ("findings_with_quote_not_in_spec", "quotes NOT in spec"),
        ("contamination_count", "contamination"),
    ]
    for k, label in keys:
        vals = [aggregate["adversarial_robustness"][a][k] for a in ("C","D","E","F")]
        print(f"  {label:35s} " + " ".join(f"{v:>6d}" for v in vals))


if __name__ == "__main__":
    main()
