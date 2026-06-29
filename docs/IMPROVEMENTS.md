# pr-arbiter — improvements backlog

Discrete enhancements queued for pickup. Captured outside a phase handoff so a
single idea doesn't have to wait for a phase boundary.

---

## SQL review: two separate layers

Surfaced 2026-06-28 while evaluating sqlfluff for the Tessera ecosystem. Both
relate to pr-arbiter's SQL review quality; they are **different fixes** and
neither substitutes for the other.

### IMP-001 — Threat-model context for SQL/path findings (the false-positive fix)

**Problem (observed).** The Phase-2 pr-arbiter run over the tess-dashboard v1 diff
produced false positives: SQL-injection and path-traversal flagged on inputs that
are never user-derived (`resolveConfig()` defaults, hardcoded literals, dynamic SQL
identifiers from config). The lone CRITICAL (`countBy` SQLi) and 3 of 8 HIGHs were
false in context — the reviewer prompt assumes request-derived input. Source:
`~/Claude/tess-dashboard/docs/FINDINGS.md` (pr-arbiter triage section).

**Fix.** Give the reviewer prompt threat-model context: discount request-derived-input
findings (SQLi, path traversal, XSS) unless a route actually threads user input to
the sink. For local-only / CLI / config-driven tools, request-derived-input findings
should default to low confidence or be suppressed. Consider a per-target threat-model
declaration (is there an untrusted caller? where does input enter?) the reviewer reads
before scoring.

**Note.** This is a *prompt / reasoning* fix. A SQL linter (IMP-002) does **not** help
here — sqlfluff has no concept of taint or input provenance.

### IMP-002 — sqlfluff as a deterministic SQL pre-pass (the noise-floor fix)

**Idea.** Run sqlfluff over SQL in the diff before the LLM review, to:

- strip style-nit noise so the model stops flagging formatting,
- validate parse deterministically (catch malformed SQL without the LLM),
- normalize formatting so the model reviews clean, consistent SQL.

**Scope limit.** sqlfluff is style + parse linting, **not** security/taint analysis —
it does not address IMP-001's false positives. It lowers the noise floor; IMP-001 fixes
the false-positive class. Do both, independently.

**Caveat for this codebase.** sqlfluff lints `.sql` files and templated SQL (dbt/jinja).
It does not see SQL embedded as Python/TS string literals without an extraction step —
check how much of the review corpus is standalone SQL vs inline strings before investing.
