# Worked example: pr_009 — the critical the multi-agent catches

This is the load-bearing result for the project. A critical security bug
that every single-agent configuration misses across every prompt variant
tried, surfaced by the multi-agent pipeline and promoted to high-confidence
blocking.

## The diff

pr_009 (Priya persona — almost-secure code) introduces a `sanitize_user_html`
helper in `templating.py`:

```python
def sanitize_user_html(raw: str) -> str:
    """Sanitize a user-supplied HTML string for safe rendering.

    Strips <script> tags and on* event handler attributes to prevent
    XSS. The result is safe to embed inside a Jinja template using the
    ``|safe`` filter.
    """
    import re

    # Remove script tags and their contents
    cleaned = re.sub(
        r"<script.*?>.*?</script>",
        "",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Strip on* event handler attributes
    cleaned = re.sub(
        r'\s+on\w+\s*=\s*"[^"]*"',
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    return cleaned
```

It looks reasonable on a quick read. It's labeled an XSS prevention helper,
strips script tags, strips on* handlers. A senior reviewer who reads quickly
might let it through.

## What's actually wrong

Regex-based HTML sanitization is a long-known anti-pattern (cf. the famous
"You can't parse HTML with regex" Stack Overflow answer). The specific
bypasses:

1. **Non-recursive script-tag removal** — `<scr<script>ipt>` survives one
   substitution and becomes `<script>`.
2. **Quote-style mismatch** — `on\w+\s*=\s*"[^"]*"` only matches
   double-quoted values. `<a onclick='alert(1)'>` survives. `<a onclick=alert(1)>`
   survives too.
3. **Other XSS vectors entirely unhandled** — `<iframe srcdoc=...>`,
   `<img onerror=alert(1)>` (the `onerror` itself uses quotes, but image-load
   based vectors and SVG-based vectors are missed), `<svg onload=...>`,
   `javascript:` URLs in `href`, `<object data=...>`, data URIs, etc.

The function's docstring claims it produces a safe-to-embed string. Any
caller will trust the helper and pass the output to Jinja's `|safe` filter
(unescaped rendering). That's a stored-XSS class vulnerability.

The rubric calls this critical: "regex-based HTML sanitization is a known
anti-pattern and cannot safely sanitize against XSS."

## What each agent did

### Single-agent reviewer (v2): empty review

Across all six configurations and every prompt variant, the single-pass
reviewer **caught nothing on pr_009**. The reviewer's pattern matching is
strong on classic vuln shapes (path traversal, SQLi, credential exposure),
but "regex sanitization is broken" requires recognizing that the entire
approach is wrong, not that any specific line has a bug. That's a different
kind of reasoning, and one prompt doesn't reach it on Sonnet 4.6.

### Independent arbiter (iter2): five findings, three critical

The iter2 arbiter, instructed to do an independent second-pass review with
the reviewer's empty output as anti-redundancy context, surfaced:

| Severity | Lines  | Finding                                                                   |
|----------|--------|---------------------------------------------------------------------------|
| critical | 228-235 | Script-tag regex is non-recursive; nested or malformed tags bypass it     |
| critical | 240-247 | Event-handler regex only matches double-quoted values                     |
| critical | 228-249 | Many XSS vectors entirely unhandled (iframe, object, embed, img onerror)  |
| high     | 228-235 | Case-insensitive flag applied but encoding obfuscation still bypasses     |
| high     | 222-249 | `import re` inside function body — re-executed every call                 |

Three independent critical findings on a PR the reviewer flagged as clean.
The arbiter's "look for what the first reviewer missed, especially
correctness-critical and architectural issues" framing surfaced the
regex-sanitization anti-pattern by treating it as an architectural concern
("this approach is wrong"), not a per-line vuln.

### Mutual triage (iter3): all three criticals promoted to blocking

The merged finding list (5 from arbiter, 0 from reviewer) went through
mutual triage. Both voices voted KEEP on all three critical findings.
Result: three critical findings in the **high-confidence blocking tier**.
The two highs landed in advisory.

The pr_009 row of the iter3 results:

```
pr_009  merged=4 -> high=3 low=0 dropped=1  ...
```

Three blocking, zero advisory, one dropped (the `import re` style nit got
dropped by both voices — correctly).

## Why this matters

Two things you can take from this example.

**First, the multi-agent architecture caught a class of bug that single-pass
review can't.** The reviewer's prompt is well-tuned (iter1 brought it from
50.9% to 52.7% recall, +12pp precision). It still missed pr_009 on every
run. The miss isn't a prompt problem; it's a single-pass-on-one-model
ceiling. The independent arbiter, with a different framing focused on
gaps and architectural issues, reaches a class of reasoning the reviewer
doesn't.

**Second, the mutual triage promoted the catch to blocking, not advisory.**
The risk going into iter3 was that single-source findings (only one agent
flagged it) would get triaged down to low confidence. They didn't:
both triage voices independently voted KEEP on the three criticals. The
agreement criterion held because the bug is genuinely reproducible from the
code — both voices, reading the diff, arrived at the same conclusion.

If you're sketching a multi-agent code review pitch internally, this is
the worked example.

## Reproducing

```bash
# See pr_009 in isolation across configurations
.venv/bin/python -c "
import json
for path, key in [
    ('results/iter1_20260513.json', 'final_findings'),
    ('results/iter2_20260513.json', 'arbiter_findings'),
    ('results/iter3_20260513.json', 'high_conf_findings'),
]:
    d = json.load(open(path))
    p = next(p for p in d['per_pr'] if p['pr_id']=='pr_009')
    print(f'--- {path} ({key}) ---')
    for f in p.get(key, []):
        print(f'  {f[\"severity\"]:8} {f[\"category\"]:11} L{f[\"line_range\"]}: {f[\"description\"][:80]}')
"
```
