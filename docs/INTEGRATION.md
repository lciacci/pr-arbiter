# pr-arbiter in the three-project system — stub

> # ❄️ FROZEN — pr-arbiter NO LONGER HOLDS A LANE. Read this before the body.
>
> **pr-arbiter is a closed research study** (frozen 2026-07-28, `7d04649`). It is **not** the Pattern
> layer any more and it is **not maintained**. The Pattern lane belongs to **`arbiter`**
> (`../arbiter`, github.com/lciacci/arbiter) — a shipping CLI that reviews a git ref range: reviewer →
> independent second pass → two-voice KEEP/DROP/UNSURE triage, exit 1 on high/critical. Its stub is
> `../arbiter/docs/INTEGRATION.md`.
>
> **The body below is preserved as the study's record, not as current state.** The canonical contract
> now marks this file as *"the frozen study's stub, not maintained"*, so nothing reads it as live —
> but a reader landing here directly would have had no way to know, which is why this banner exists.
>
> **What in the body is still TRUE and load-bearing elsewhere:**
> - **Guard 4 — this study's numbers are thin.** Phase-1 critical recall **7/8 vs 6/8, one seed**;
>   Phase-2 generation lift **~vanished under 3-seed variance** (2 tasks / 39 runs). This is the most
>   cited thing in the study and it survives as anti-conflation guard **(d)** in the canonical, where
>   it binds all three repos. **Gate any build on the instrument, never on the headline** — and note
>   the headline is elsewhere still rendered as "88% vs 75%", a percentage 7/8 cannot carry.
> - **The typed-finding schema**, which `arbiter` inherited and conclave's S2 scorer still reproduces
>   to 4dp on this study's matcher and expected findings.
> - **Guards 1–3**, which now bind `arbiter` rather than this repo; they are mirrored in its stub.
>
> **What in the body is now WRONG,** flagged inline below: this repo does not own a lane (⚠ at
> "pr-arbiter's lane"), and D4 is no longer deferred (⚠ at "Directionality"). *Also settled since:*
> the body's request that the canonical be edited **was carried out 2026-08-07** — the Pattern lane
> was renamed `pr-arbiter` → `arbiter` there, with sign-off from that lane's owner.

> **Canonical contract:** `../tessera/docs/contracts/three-project-cohesion.md` (Tessera-hosted,
> peer contract; hosting ≠ ownership). This file is a STUB — pr-arbiter's own lane + the shared
> anti-conflation guards. For the full map (layering, all seams, sequencing, Open decisions) read the
> canonical. If this stub and the canonical disagree, the canonical wins.

**Layer:** pr-arbiter = the **pattern** (the multi-role union-recall review workflow). The other two:
Conclave = the **substrate** (inference serving + the measurement instrument), Tessera = the
**policy** (governance + routing/dispatch decisions).

**Directionality:** the three are runtime peers. Tessera hosts the contract as coordinator; pr-arbiter
is not built *on* Tessera today (adopting `.tessera/` is Open decision D4 — deferred).

> ⚠ **D4 IS NOT DEFERRED — RESOLVED 2026-07-28.** Moot for this repo, which is frozen and will never
> adopt `.tessera/`. Its successor `arbiter` adopted it at scaffold, so `arbiter` is a Tessera
> downstream and seam S5 (findings feedback) applies to it. The first clause stays true: this repo
> is not built on Tessera, and now never will be.

## ⚠ pr-arbiter's lane — *held until 2026-07-28; the Pattern lane is `arbiter`'s now*
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
  satisfied from. ~~The canonical contract still names the old gate and needs the same edit
  (Tessera-hosted — fix it there, not here).~~ **✅ DONE 2026-08-07** — the canonical's Pattern lane,
  title, stub list and engine-evidence paths were renamed `pr-arbiter` → `arbiter`, with sign-off
  from that lane's owner. This bullet's flag-it-where-you-see-it-but-fix-it-in-its-own-repo
  instinct was right and is the convention that caught it; conclave did the same thing to the
  canonical's Pattern row on 2026-08-07, flagging in place with an interim precedence rule.
- The **"true finding" scoring function** for the union-recall divergence variant (seam S2) —
  co-owned with conclave; pr-arbiter defines what counts as a finding (the typed-finding schema).
- Consumes conclave's gateway via `base_url` (seam S1).

Full context in this repo: `README.md`, `PHASE_2_FINAL.md` (the variance result + typed-finding
schema), `docs/PHASE_3_RESUMPTION.md` (Phase 3 status: design complete, blocked on annotator pilot).
