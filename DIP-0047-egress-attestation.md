# DIP-0047: Egress Attestation

| Field | Value |
|-------|-------|
| **DIP** | 0047 |
| **Title** | Egress Attestation — recording what agents do to the outside world |
| **Status** | Draft |
| **Created** | 2026-08-14 |
| **Depends on** | DIP-0038 (event vocabulary), DIP-0044 (actor identity), DIP-0046 (payload classes) |

## Summary

Datacore meters spend to the cent and records every task transition, but until
2026-08-14 it recorded almost nothing about what its agents *did* — the posts,
the emails, the trades, the issues filed. `artifact.attest` existed in the
vocabulary and one call site emitted it.

This DIP makes external actions attestable the way logging made diagnostics
recordable: one import, one decorator, and — unlike logging — a test that fails
when coverage is missing.

## Motivation

A task can be re-derived from org. A tweet cannot be un-sent. External side
effects are the actions least reconstructible from local state and most worth
recording, and they were the ones with no record at all.

The gap was found by being *asked* "if Data posts to X, will the system know?"
— not by any check. That is the core problem: **a missing attestation has no
symptom.** No error, no gap, no anomaly. Absence is indistinguishable from "the
agent did not act." Every other class of defect in Datacore eventually announces
itself; this one cannot.

Measured at the time of writing:

| Egress class | Chokepoint | Attested |
|---|---|---|
| X posts/replies | `x_api.post_tweet` / `post_reply` | yes |
| Telegram to humans | none — 27 senders, 2 via the shared helper | no |
| Email | `gmail.send_email` / `reply` | no |
| GitHub issue/PR/comment | 3 sites | no |
| Trade orders | `place_market_order` / `place_limit_order` | no |
| Spend (LLM, search, image) | scattered | no |

One of six.

## Why this is not simply "add the hook everywhere"

The first attempt — hand-wiring `attest()` into one module — failed silently on
one of five machines for four independent reasons, each of which returned
`None` and rendered identically to "nothing happened":

1. actor inferred from hostname resolved to `holodeck`, not `data`
2. the registry consulted as a fallback was a four-month-stale copy
3. the space lookup globbed one root and matched a space nobody meant
4. `ledger_attest.py` was deployed where the `ledger` package was not importable

The fourth is the general case. **There is no supported way for a module to
import the core.** 129 module files hand-roll `sys.path.insert`, in at least
four distinct spellings including `Path(__file__).parent.parent.parent.parent`.
Each is a guess about where the core lives, and on a machine whose layout
differs, the guess is wrong — silently, because attestation must never raise.

Wiring six more modules by hand would reproduce that bug six more times.

## Design

### Layer 1 — one import that always works

```python
from datacore.ledger import attest, attests
```

No paths, no `DATACORE_ROOT`, no parent-counting. The core becomes importable as
a package on every machine. This is the actual blocker; the rest is cheap once
it exists.

### Layer 2 — a decorator at the chokepoint

```python
@attests("x.post", ref=lambda r: r["data"]["id"])
def post_tweet(text: str) -> dict: ...
```

Records **after** return, never before — attesting an intended action creates a
record of something that may not have happened, which is worse than no record
because it reads as authoritative. Never raises: a tweet that went out but could
not be recorded is still a tweet that went out.

Deliberately **not** manifest-driven monkeypatching. Rewriting functions at
import time fails invisibly, and invisible failure is the thing this DIP exists
to defeat. The decorator is greppable, debuggable, and obvious in a diff.

**Attest chokepoints, not call sites.** 15 comms files reference X; publishing
funnels through 2 functions; decorating those 2 covers all 15. Where no
chokepoint exists — Telegram, with 27 direct senders — the fix is to build one,
not to add 27 decorators.

### Layer 3 — declare in the manifest, enforce in a test

```yaml
# module.yaml
egress:
  - fn: lib/x_api.py:post_tweet
    kind: x.post
exempt:
  - fn: lib/today_thread.py:_exa_search
    reason: read-only search, no external side effect
```

A conformance check asserts both directions:

- every declared egress is still decorated — catches silent removal
- every outbound write in module code is declared or exempted — catches silent
  addition
- every `kind` exists in the event vocabulary — catches typos

The decorator can only describe code that exists. The manifest plus an AST scan
describes code that *should* have been decorated. Since absence is the failure
mode, absence is what must be tested.

This is the part stdlib logging has no equivalent for, and it is the part that
makes the rest hold. Logging is best-effort by design; a dropped log line costs
debuggability. A dropped attestation costs the truth.

## Rollout

1. Make `datacore.ledger` importable fleet-wide
2. Add `@attests` and the egress event vocabulary
3. Add `egress:` to the module.yaml schema; run the AST scan **report-only**
4. Fix chokepoints in priority order: trading, email, Telegram, GitHub, spend
5. Flip the scan to enforcing in `v2_verify`

Step 3 is the load-bearing step: the scan *generates* the audit mechanically, so
the gap list never again depends on someone grepping and eyeballing. The manual
audit that motivated this DIP misread one file as a bypass when it was making
search and inference calls.

## Non-goals

- **Signing.** Attestations are unsigned, consistent with the standing choice
  for seals. An attestation proves the system recorded an action, not that a
  particular key authorised it.
- **Blocking.** Attestation never gates an action. A failure to record is
  reported, never enforced.
- **Read tracking.** Only actions with external side effects. Reads are exempt
  by declaration, so the exemption is visible rather than assumed.
