# pr-arbiter in the three-project system — stub

> **Canonical contract:** `../tessera/docs/contracts/three-project-cohesion.md` (Tessera-hosted,
> peer contract; hosting ≠ ownership). This file is a STUB — pr-arbiter's own lane + the shared
> anti-conflation guards. For the full map (layering, all seams, sequencing, Open decisions) read the
> canonical. If this stub and the canonical disagree, the canonical wins.

**Layer:** pr-arbiter = the **pattern** (the multi-role union-recall review workflow). The other two:
Conclave = the **substrate** (inference serving + the measurement instrument), Tessera = the
**policy** (governance + routing/dispatch decisions).

**Directionality:** the three are runtime peers. Tessera hosts the contract as coordinator; pr-arbiter
is not built *on* Tessera today (adopting `.tessera/` is Open decision D4 — deferred).

## pr-arbiter's lane
- **Owns:** the multi-**ROLE** review pattern — reviewer → independent additive arbiter → KEEP/DROP
  mutual triage, **one strong model with role-differentiated prompts** (`agents/reviewer.py`,
  `arbiter.py`, `triage.py`). The typed-finding schema.
- **Must NOT:** decide **when** review runs or on **which tier** (Tessera's policy), or **serve** the
  models (Conclave's substrate). pr-arbiter is a pattern, not a policy and not a substrate.

## Anti-conflation guards (mirrored here because they bind work IN this repo)
1. Conclave's "judge/ensemble doesn't pay" null is **select-best only** — it does NOT apply to this
   repo's **union-recall** review objective. Do not let a sibling's select-best null be cited to kill
   the review-fan-out result.
2. The diversity that pays here is **ROLE**, NOT **MODEL** (conclave's null). One strong model +
   roles — **no fleet** for the review pattern.
3. Serving tiers ≠ routing policy. pr-arbiter consumes a tier via `base_url`; it does not choose one.
4. **pr-arbiter's own numbers are thin** — Phase-1 critical recall **7/8 vs 6/8, one seed**; Phase-2
   generation lift **~vanished under 3-seed variance** (2 tasks / 39 runs). Gate any integration build
   on the instrument (the union-recall divergence metric, seam S2), **not** the headline.

## pr-arbiter's contributions to the seams
- The **review pattern** that graduates into the tool backing Tessera's `/arbiter`, running on
  conclave's fleet (seam S4). **Status changed 2026-07-28:** S4's stated prerequisite was "pr-arbiter
  Phase 3." Phase 3 was never implemented and this repo is now frozen, so that prerequisite is void.
  The pattern graduated directly into a standalone engine repo, `arbiter`, which is where S4 is now
  satisfied from. The canonical contract still names the old gate and needs the same edit
  (Tessera-hosted — fix it there, not here).
- The **"true finding" scoring function** for the union-recall divergence variant (seam S2) —
  co-owned with conclave; pr-arbiter defines what counts as a finding (the typed-finding schema).
- Consumes conclave's gateway via `base_url` (seam S1).

Full context in this repo: `README.md`, `PHASE_2_FINAL.md` (the variance result + typed-finding
schema), `docs/PHASE_3_RESUMPTION.md` (Phase 3 status: design complete, blocked on annotator pilot).
