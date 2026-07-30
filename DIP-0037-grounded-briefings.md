# DIP-0037: Grounded Briefings

| Field | Value |
|-------|-------|
| **DIP** | 0037 |
| **Title** | Grounded Briefings |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Draft |
| **Created** | 2026-07-30 |
| **Updated** | 2026-07-30 |
| **Tags** | `briefing`, `grounding`, `hallucination`, `fact-table`, `validation`, `datacore-v2` |
| **Affects** | `.datacore/lib/briefing/` (`fact_table.py`, `render.py`), `.datacore/lib/briefing_grounded.py`, future `cos_generate.py`/`cos_reasoning.py` call sites |
| **Specs** | `.datacore/lib/briefing/fact_table.py`, `.datacore/lib/briefing/render.py`, `.datacore/lib/briefing_grounded.py` |
| **Agents** | any process that generates briefing prose via an LLM (`/today`, `cos_generate.py`, `cos_reasoning.py`, nightshift briefing jobs) |
| **Relates to** | `ENG-2026-0728-002` (the motivating incident), DIP-0034 (Event Ledger Substrate — `metric.attest` sink for facts), DIP-0035 (Job Contracts — fact-freshness verification), DIP-0038 (Action Loop + Co-sign — briefing items become ledger tasks downstream of this DIP's output) |

## Summary

Introduces a **grounded-briefing pipeline**: a deterministic `Fact` table
built by read-only adapters (`briefing.fact_table`), a token contract that
forces an LLM to reference every figure via `{{fact:ID}}` rather than typing
a number directly (`briefing.render.render`), a post-render validator that
re-scans the fully rendered text and flags any digit sequence that cannot be
traced to something real (`briefing.render.validate`), and a pipeline entry
point (`briefing_grounded.py`) that composes these into two functions —
`prompt_block(facts)` (what the LLM is shown) and `finalize(llm_text, facts,
allow=None)` (what a briefing consumer receives back) — with the property
that **finalize() never returns an unvalidated LLM-typed number**. On either
failure path (an unknown token, or a number typed directly that fails
validation) the caller receives a deterministic, fully-grounded fallback
text instead of the LLM's prose. This DIP is Phase 4 of the v2 rollout
DIP-0034 names in its Rollout Plan; it consumes DIP-0034's event schema
(`metric.attest`) for fact durability and is itself consumed by DIP-0038
(briefing items becoming ledger tasks).

## Motivation

### Problem: precise numbers are credible numbers, and credible numbers were wrong

On 2026-07-28, Datacore's `/today` Chief-of-Staff briefing produced four
individually precise, individually plausible claims — and every one of them
was wrong, and three of the four **prescribed remedies were actively
harmful**, not merely mistaken (`ENG-2026-0728-002`):

1. **"639 uncommitted changes in 0-personal, worth a manual commit"** — the
   639 were actually **deletions** on the nightshift server under
   `4-outbox/archive/`. Committing them, as the briefing recommended, would
   have deleted 639 files.
2. **"84 stale cadences, verify their schedules"** — there were **28**
   cadences with no executor scheduled at all, not 84 stale ones. Pruning on
   the strength of this claim would have deleted work on the evidence of a
   runner that had simply never fired.
3. **"Matthew Elliott awaiting your reply"** — this was **inverted**: Gregor
   had sent the message and was awaiting a reply *from* Matthew, not the
   other way around.
4. A **19:00 meeting was listed that exists on no calendar**, and a 16:00
   meeting that had actually been declined was reported as upcoming.

The rationale recorded alongside the engram is the load-bearing insight for
this DIP: **precision is what made every one of these claims credible.**
Nothing about the numbers themselves signaled unreliability — a briefing
that said "roughly some uncommitted changes" would have prompted
verification; "639" did not. The briefing's specificity created false
confidence, and three of the four wrong claims' own prescribed remedies
would have caused active damage if acted on without independent
verification. This is named, in the originating engram, as **the single
highest-value guardrail for `/today` output.**

### Why token substitution + post-hoc validation, not just "tell the LLM to be careful"

An instruction alone ("only report numbers you're sure of") is not a
guardrail — it is a request the same LLM that fabricated 639 and 84 is
equally capable of ignoring under equally high confidence, with no
structural check afterward. This DIP's design instead makes fabrication
**structurally caught, not merely discouraged**, via two independent
mechanisms with two different failure modes:

- **Token substitution** (`render()`): the LLM does not get to choose the
  digits that appear in a number it's grounding — it chooses a fact *id*,
  and the actual value is substituted in verbatim, from a table the LLM
  never computed. A `{{fact:ID}}` naming an id that doesn't exist is a hard
  error (`RenderError`).
- **Post-render validation** (`validate()`): the mechanism above only
  catches numbers the LLM *tried* to source from a token. It does nothing
  about a number the LLM types directly instead, bypassing tokens entirely
  — exactly the "639" and "84" shape of the motivating incident, where the
  LLM simply asserted a count in prose. `validate()` is the net for this:
  every digit sequence in the rendered text must trace to a real fact
  value or an explicit allowance, or it is reported as an error.

`finalize()` composes both and adds the final, non-negotiable property:
**on any failure from either mechanism, the LLM's text is discarded
entirely** — the caller receives a deterministic, fact-derived fallback
instead. There is no code path in this pipeline that returns an
LLM-authored sentence containing a number that hasn't passed both checks.

### Use cases

1. **`/today` and any CoS briefing** — the direct fix for the motivating
   incident: numeric claims about git state, task counts, cadence health,
   or anything else built from a `Fact` adapter can no longer be silently
   fabricated by the generation step.
2. **Any future LLM-authored artifact with numeric claims** — the
   `prompt_block`/`finalize` pair is generic over any `dict[str, Fact]`, not
   specific to `/today`; any pipeline that wants "LLM writes the prose, but
   every number is real" gets it by adopting these two functions.
3. **A structural, not procedural, guardrail** — replaces "the LLM should
   double check its numbers" (unenforceable, and the exact thing that failed
   on 2026-07-28) with "the pipeline discards output containing any number
   that didn't come from a fact," which holds regardless of model
   confidence, verbosity, or prompt phrasing.

## Current Workaround (pre-DIP)

- Briefing prose is generated by a single LLM call with no distinction
  between numbers grounded in real state and numbers the model asserts from
  its own (unverified) synthesis of context.
- The only check has been human review after the fact — which is precisely
  what did not happen, or happened too late, for the four wrong claims in
  `ENG-2026-0728-002`, and precision is what suppressed the reviewer's
  instinct to double-check.
- There is no fact table, no token contract, and no mechanical validator:
  a wrong number and a right number are typographically indistinguishable
  in the output.

## Specification

### Fact table (`briefing.fact_table`, consumed unchanged by this DIP)

Every number a grounded briefing can show must trace to a `Fact`:

```python
@dataclass
class Fact:
    id: str
    value: str        # ALWAYS str, even for counts -- substituted verbatim
    unit: str
    source: str
    computed_at: str   # ISO-8601 UTC, injectable `now` -- see fact.value CONTRACT below
```

`build_facts(root, adapters=None, now=None) -> dict[str, Fact]` runs a list
of adapters (default: `git_status_counts`, `ledger_task_counts`) against one
`root` directory and merges their `Fact` dicts. Adapter isolation is load
bearing: one adapter raising (or returning a malformed value) never aborts
the others — it is folded into a synthetic `_meta.adapter_errors` fact
instead; a duplicate fact id produced by two *different* adapters is a
config bug, not a runtime surprise, and raises `FactError` naming both.
`write_facts` persists the table to JSON; `emit_facts` records one
`metric.attest` ledger event per fact (see Relationship to DIP-0034, below).

### Token contract (`briefing.render.render`, consumed unchanged by this DIP)

`render(llm_text, facts) -> str` substitutes every `{{fact:ID}}` token
(`ID` matching `[A-Za-z0-9_.\-]+`) with the matching `Fact.value`, verbatim,
no reformatting. If **any** referenced id is not a key in `facts`, **nothing**
is substituted: every unknown id in the text (deduplicated, first-seen
order) is collected and raised together as one `RenderError` — never a
partial substitution, never a raise-on-first-unknown. Text that merely
*looks* like a token (invalid id characters, or an unterminated `{{fact:`)
does not match the token regex at all and is left verbatim — that is not
this function's failure mode; it is `validate()`'s.

`prompt_block(facts) -> str` (new in this DIP, `briefing_grounded.py`)
serializes a fact table into exactly what the LLM should be shown: a fixed
instruction header mandating token-only use for every figure, followed by
one line per fact, **sorted by id** (reproducible regardless of the fact
dict's insertion order, since a real table is a merge of several adapters'
output), in the shape:

```
{{fact:ID}} = <value> <unit> (<source>)
```

This is deliberately the literal token syntax `render()` substitutes — the
LLM is shown exactly what it must reproduce, not a paraphrase of it.

### Validator semantics (`briefing.render.validate`, consumed unchanged by this DIP)

`validate(rendered, facts, allow=None) -> list[str]` operates on
**already-rendered** text (no memory of where a token substitution
happened) and extracts every digit sequence via `\d[\d,.]*\d|\d` — a
comma/period-joined run of 2+ digits, or a single lone digit (this shape
matters for the Threat Model below). Each match must satisfy at least one
of four grounding rules, checked in this order but all independent:

1. **Substring-of-fact-value** — the matched text is a substring of *some*
   `Fact.value` in the table. Note this checks values, never ids: a number
   that happens to match a fact's id but not its value is still flagged.
2. **Standalone year** — the match full-matches `20\d{2}` directly (a bare
   four-digit year needs no fact to justify it).
3. **Windowed date/clock-time** — the match is a fragment of a full ISO
   date (`\d{4}-\d{2}-\d{2}`) or clock time (`\d{1,2}:\d{2}`) written in the
   surrounding text, checked via an 11-character window on each side (the
   extraction regex never captures the `-`/`:` separators these patterns
   need, so a direct match against the extracted fragment alone is
   impossible).
4. **Caller-supplied allow** — the match full-matches one of the `allow`
   regex strings passed through from `finalize()`'s own `allow` parameter,
   for legitimately fact-independent numbers (e.g. a version string).

Anything satisfying none of the four becomes an error string naming the
offending number plus 20 characters of surrounding context on each side, so
a human reviewing the error can locate the unverified claim without
re-running `validate()`. Both `render()` and `validate()` are pure and
deterministic — zero clock reads, zero randomness; "current year" means the
literal `20\d{2}` pattern, never `datetime.now().year`.

### Fallback semantics: `finalize()` never ships an unvalidated number

`briefing_grounded.finalize(llm_text, facts, allow=None) -> tuple[str, list[str]]`
(new in this DIP) is the pipeline's trust gate:

```python
def finalize(llm_text, facts, allow=None):
    try:
        rendered = render(llm_text, facts)
    except RenderError as exc:
        return _fallback_text(facts), [str(exc)]

    errors = validate(rendered, facts, allow=allow)
    if errors:
        return _fallback_text(facts), errors

    return rendered, []
```

Two independent failure paths, one deterministic outcome:

- `RenderError` (an unknown fact id was referenced) — the LLM asked for
  something that doesn't exist.
- Nonempty `validate()` errors (a number typed directly, or a token that
  resolved but produced an ungrounded result after substitution) — the
  exact ENG-2026-0728-002 shape, where there was no token to reject because
  the model never used one.

On **either** path, the return value is `(_fallback_text(facts), errors)` —
never any portion of `llm_text`. `_fallback_text(facts)` is a fixed header
(`"Briefing (grounded fallback — validation failed)"`) followed by a
**plain** listing (`ID = value unit (source)`, no `{{fact:...}}` wrapper —
this text is terminal output, not a re-submittable prompt) of every known
fact, sorted by id. A briefing consumer on the fallback path still sees
every real number that exists; it simply does not see the LLM's sentences
around them. Only the fully clean path — no unknown tokens, no ungrounded
digits — returns `(rendered, [])`, the sole case where LLM-authored prose
(with every number substituted from a fact) is what ships.

## Threat Model

This section is mandatory for this DIP because the mechanism's residual
gaps are exactly the kind of thing precision made invisible in the
motivating incident — stating them plainly here is the guardrail against
this DIP's own guardrail becoming a new source of false confidence.

### PRIMARY RESIDUAL GAP: short-digit substring looseness

`validate()`'s grounding rule 1 (substring-of-fact-value) checks whether the
matched digit text is a substring of *any* fact's value — not whether it
equals a fact's value, and not whether it's a substring of the *specific*
fact the claim is supposedly about. This is deliberately loose (a fact
table has no way to know which fact a given sentence *means* to cite,
only whether the number could plausibly come from something real), and
that looseness has a direct, unavoidable cost: **a short fabricated number
— especially a single digit, and quite often two digits — will frequently
substring-match some unrelated fact's value purely by chance, with zero
adversarial effort and no special formatting required.** In any nontrivial
fact table (several counts, a branch name containing digits, a task total),
most single digits 0–9 appear *somewhere* as a substring of *some* value.
State this plainly, not as a hedge: **the gate reliably catches distinctive
fabrications — the "639 uncommitted changes" class, where the number is
long and specific enough that coincidental substring collision is
improbable — but it catches short-digit fabrications only probabilistically,
not structurally.** A model that fabricates "3 dirty files" when the real
count is 7, in a table that happens to have *some* fact whose value contains
a "3" somewhere, passes validation clean. This is not a bug to be silently
patched by a carve-out (see `test_briefing_render.py`'s explicit design
note: `validate()` intentionally has no special case for single digits,
because a carve-out would weaken the guarantee for exactly the numbers most
likely to slip past it); it is a structural property of substring grounding
that every consumer of this pipeline must understand before treating a
clean `finalize()` result as "every number is verified" rather than "every
number passed the checks this mechanism can perform."

### `Fact.value` CONTRACT: keep timestamps and long incidental strings out

This gap compounds catastrophically if an adapter ever violates a contract
this DIP asserts explicitly: **`Fact.value` must never contain a timestamp
or any other long, incidentally-numeric string.** `Fact.computed_at` exists
as a *separate* dataclass field precisely so this never happens by
accident — an ISO timestamp such as `2026-07-30T14:23:57.123456+00:00`
contains, as substrings, most single and double digits and a large number
of 3–4 digit runs. If such a string were ever folded into `value` (e.g. a
hypothetical future adapter reporting "last sync at 2026-07-30T14:23:57"
as its fact value instead of keeping the timestamp in `computed_at` and a
short label in `value`), `validate()`'s substring-of-fact-value rule would
give **nearly every digit a free pass** system-wide — not just within that
one fact's own claim, but for *any* rendered text checked against a fact
table containing it, since rule 1 checks substring membership across every
fact's value, not just the one a sentence is nominally about. This is why
`computed_at` is kept out of `value` in both existing adapters
(`git_status_counts`, `ledger_task_counts`) and must be kept out by every
future adapter: the discipline of "value is a short, meaningful figure;
computed_at is metadata" is not a style preference here, it is what keeps
the substring-grounding check meaningful at all.

### Disclosed secondary gaps

- **Whitespace/underscore-split numerals.** The extraction regex
  (`\d[\d,.]*\d|\d`) joins digits only across `,`/`.` — a fabricated number
  written as `"1 234"` or `"6_3_9"` splits into two or three independent
  short matches, each of which is materially more likely to coincidentally
  substring-match some unrelated fact value than the same number written
  normally (a multi-digit fabrication broken into single-digit fragments
  inherits the primary gap above, once per fragment). This is inherent to
  the specified extraction regex, not an implementation defect; closing it
  would require a different extraction regex (spanning whitespace/
  underscore-joined runs), which is out of this DIP's scope and noted as
  an Open Question below.
- **Adjacent-token merge false positives.** Because `validate()` operates
  on already-rendered text with no memory of where a token substitution
  occurred, two tokens placed with no separator between them
  (`"{{fact:a}}{{fact:b}}"`, values `"12"` and `"34"`) render into a single
  contiguous digit run (`"1234"`) that `validate()` treats as one match. If
  that merged value is not itself a substring of any single fact, it is
  flagged as an error even though both constituent numbers were
  legitimately grounded — an **over-flagging** (unnecessary fallback), the
  opposite failure direction from the primary gap above (which is
  under-flagging). This is not fixed at the validator level, deliberately:
  doing so would require `validate()` to retain token-boundary information
  that `render()` has already discarded by the time `validate()` runs (per
  `render.py`'s own docstring: validation happens on rendered text, full
  stop). The practical mitigation is a prompt-writing convention — always
  separate adjacent tokens with a space, unit label, or punctuation — not a
  validator change.

## Integration

### Relationship to DIP-0034 (facts are ledger attest events)

`briefing.fact_table.emit_facts` records one `metric.attest` event per fact
(`payload.metric == "fact"`) using DIP-0034's `EventLog`/`metric.attest`
event type — this DIP does not introduce a new event type; it is a consumer
of the type DIP-0034 already reserves. A fact table is therefore durable and
mechanically auditable ("what did the briefing pipeline actually see, and
when") independent of whatever briefing text was generated from it, the
same durability property DIP-0034 provides for task/ownership state.

### Relationship to DIP-0035 (fact freshness is a job contract)

Whether a fact table is *fresh enough* to ground a briefing — e.g. "the
`facts.json` this pipeline reads was built in the last N minutes, not
stale from a failed prior run" — is explicitly **not** reinvented by this
DIP. It is a DIP-0035 job-contract concern: a manifest entry for the job
that produces `facts.json` (or emits its `metric.attest` events), with an
artifact-freshness check run by `job_verify.py`, is the correct place to
assert and alert on staleness, the same "assert outputs, not exit codes"
discipline DIP-0035 applies to every other scheduled job. This DIP's own
functions (`build_facts`, `prompt_block`, `finalize`) have no clock-based
freshness logic and should not grow any — that check belongs one layer up,
in the job contract, not in the grounding pipeline itself.

### Rollout: `COS_GROUNDED=1` behind a flag, with fallback + alert

Wiring this pipeline into the live CoS briefing generators
(`cos_generate.py`, `cos_reasoning.py`, and any nightshift briefing call
site) happens behind an opt-in environment flag, `COS_GROUNDED=1`:

- **Unset (default)**: behavior is unchanged. This DIP does not remove or
  replace the existing ungrounded briefing path in this rollout step —
  wiring is additive and reversible until the grounded path has been
  observed in production.
- **`COS_GROUNDED=1`**: the caller builds `facts` via `build_facts(root)`,
  shows the LLM `prompt_block(facts)` as (part of) its prompt, and passes
  the LLM's response through `finalize(llm_text, facts)` before any
  delivery step (Telegram, `/today` render, etc.).
- **On a `finalize()` fallback (either failure path)**: the caller MUST
  treat this as a **loud** condition, not a silent substitution — deliver
  the fallback text (still useful: every real fact, just without LLM
  prose) **and** alert (log line at minimum; Telegram/`on_fail` routing
  where the caller already has one, matching DIP-0035's job-alert
  conventions). This requirement exists because "the pipeline quietly did
  something different than intended, with no visible signal" is exactly
  the **silent-by-degradation failure genre** DIP-0035 names
  (`ENG-2026-0728-001`) for a different subsystem — a grounded-briefing
  fallback that fires silently, night after night, would recreate that
  same genre one layer up: the fix "worked" (no fabricated number shipped)
  but nobody would know the LLM's prose was being discarded until much
  later, if ever.

## Invariants

1. **`finalize()` never returns LLM-typed text that has not passed both
   `render()` and `validate()` clean.** Both failure paths return
   `_fallback_text(facts)`, derived entirely from `facts`, never from
   `llm_text`.
2. **`render()` and `validate()` are pure.** No clock reads, no randomness,
   no I/O — inherited unchanged from `briefing.render`; this DIP's own new
   functions (`prompt_block`, `finalize`) preserve this: neither reads a
   clock or generates randomness.
3. **`Fact.value` is always `str`, never a timestamp or other long
   incidentally-numeric string** (see Threat Model). This is a contract on
   every adapter, present and future, not just an implementation detail of
   the two shipped adapters.
4. **`prompt_block()`'s output is reproducible.** Fact lines are sorted by
   id; the same fact table always produces byte-identical prompt text
   regardless of dict insertion order.
5. **A `finalize()` fallback is always visible, never silent**, once wired
   behind `COS_GROUNDED=1` per the Rollout section above — this is a
   requirement on integration call sites, not on `finalize()` itself (which
   correctly returns the fallback text and an errors list; what a caller
   *does* with a nonempty errors list is the integration's responsibility).

## Rationale

**Why token substitution instead of asking the LLM to cite sources in
prose?** A citation the LLM writes in prose ("639, per git status") is
exactly as fabricable as the number itself — nothing structurally prevents
a hallucinated citation alongside a hallucinated figure. A token that must
resolve against a real, pre-built dict is not something the LLM can
satisfy by writing plausible-looking text; it either names something real
or the whole render fails.

**Why validate the rendered text with a generic digit-sequence scan, rather
than requiring 100% token coverage?** Because the motivating incident's
actual failure mode was a model **not using a citation mechanism at all**
— it simply typed "639" as prose. A design that only checks tokens (and
trusts untokenized numbers) would have done nothing for the exact incident
this DIP exists to prevent. The validator is the net for precisely the
case token-checking cannot reach.

**Why substring grounding instead of exact-value grounding?** Exact-value
grounding (the extracted text must *equal* some fact's value) would be
tighter, but numbers legitimately appear as parts of larger constructs in
prose (e.g. "3 of the 12 tasks" both deriving from real facts "3" and
"12", vs. a sentence quoting a fact value embedded in a larger formatted
number like "$1,234.56" from a fact value "1,234.56"). Substring grounding
was chosen as the specified behavior for this reason; the Threat Model
section above documents the cost of that choice honestly rather than
treating it as free.

### Alternatives considered

- **LLM self-verification (ask the model to double-check its own
  numbers)** — rejected; this is exactly the mechanism that failed on
  2026-07-28. An instruction is not a guardrail against the model that the
  instruction is addressed to.
- **Exact-value-only grounding (no substring matching)** — rejected as the
  shipped default; too brittle against numbers that legitimately combine
  with surrounding prose formatting. Noted as a possible stricter mode for
  a future DIP if the primary Threat Model gap proves unacceptable in
  practice (see Open Questions).
- **A stricter "every number must be a token, full stop" mode (reject any
  untokenized digit)** — considered and rejected for this DIP's default,
  since prose legitimately contains numbers with no fact backing at all in
  some cases (a date already covered by the ISO-date allowlist, a version
  string via `allow`); however, this remains available as a strict mode a
  caller could approximate today by passing a narrow `allow` list and
  otherwise treating any nonempty `validate()` result as fatal, which is
  exactly what `finalize()`'s fallback path already does.

## Backwards Compatibility

Purely additive. `briefing.fact_table` and `briefing.render` are consumed
unchanged (this DIP adds no new fields, no new event types, no schema
changes to either). `briefing_grounded.py` is a new file; no existing
briefing generation path is modified by this DIP itself — the Integration
section's `COS_GROUNDED=1` flag is the explicit mechanism by which adoption
happens opt-in, at a later wiring step, not as part of this DIP's own
change set.

## Security Considerations

- **Public-repo constraint.** Both `~/Data` and this dips repo are public
  (or public-adjacent). Nothing in this DIP's content, nor in
  `briefing_grounded.py`'s CLI demo output, carries secrets — facts built
  by the two shipped adapters are dirty-file counts, a branch name, and
  task counts by status; none of that is sensitive.
- **The Threat Model above is the substantive security content of this
  DIP** — a validator that can be defeated by short numbers or
  whitespace-split digits is a real, disclosed limitation of a mechanism
  whose entire purpose is trust; documenting the gap plainly is treated as
  part of shipping the mechanism responsibly, not as an afterthought.
- **No new attack surface for write access.** This DIP reads facts and
  renders/validates text; it does not itself write to the ledger, the
  filesystem, or any external system beyond what `emit_facts` (unchanged,
  DIP-0034) already does.

## Implementation

### Reference Implementation

`.datacore/lib/briefing_grounded.py` (`prompt_block`, `finalize`), with
tests in `.datacore/lib/tests/test_briefing_grounded.py` — 15 new tests
(494 total passing at HEAD of `feat/datacore-v2`, up from 479, zero
pre-existing or new failures), covering: `prompt_block` header/sort/format
including sort-order independence from dict insertion order; `finalize`'s
success path; the canonical `ENG-2026-0728-002` "639 uncommitted changes"
fabrication shape (fallback returned, fabricated number structurally
absent, real fact value present); the unknown-token (`RenderError`) path;
and a CLI subprocess smoke test against both an empty directory and a real
git repository.

Commit reference: `feat(v2): grounded briefing pipeline entry` (branch
`feat/datacore-v2`).

### Rollout Plan

**This DIP (shipped): the pipeline entry point.** `prompt_block`/`finalize`
+ full test coverage + CLI demo (`briefing_grounded.py --root <dir>
--demo`, read-only, stdout-only, always exits 0). No existing briefing
generator is wired to it yet.

**Wiring phase (follow-on, flagged): `COS_GROUNDED=1`.** `cos_generate.py`,
`cos_reasoning.py`, and any nightshift briefing call site adopt this
pipeline behind the flag described in Integration above, with mandatory
fallback + alert semantics on any `finalize()` failure. Unwiring/rollback
is simply unsetting the flag.

**Later (DIP-0038, follow-on).** Once grounded briefing output exists,
Phase 5's action loop treats briefing items as candidate ledger tasks
(`materialize()`); a grounded briefing is a better input to that
materialization step than an ungrounded one, but this DIP does not itself
define or depend on that integration.

## Open Questions

1. **Should the primary Threat Model gap (short-digit substring
   looseness) be tightened?** E.g. a stricter mode requiring a minimum
   digit length before substring grounding applies, with shorter numbers
   required to be exact-value matches or token-sourced. Deferred: no
   production data yet on how often short fabricated numbers actually
   occur in briefing prose versus how often legitimate short numbers need
   the looser substring rule. A trigger-based revisit (an actual observed
   short-number fabrication slipping through in production), not a
   scheduled one, is the right forcing function, consistent with
   DIP-0034's own "upgrade triggers not dates" principle.
2. **Should the extraction regex span whitespace/underscore-joined digit
   groups**, closing the disclosed secondary gap? Deferred for the same
   reason — no evidence yet that LLMs fabricate numbers in this shape in
   practice, and loosening the regex has its own cost (more matches to
   ground, more chances for the adjacent-token-merge false positive to
   fire).
3. **Does the adjacent-token-merge false-positive rate matter enough to
   justify token-boundary-aware validation** (a real design change,
   requiring `render()` to hand `validate()` more than plain rendered
   text)? Deferred until the wiring phase produces evidence of how often
   this actually degrades a genuinely-grounded briefing to fallback.

## References

- `ENG-2026-0728-002` — the motivating incident: four precise, individually
  wrong briefing claims, three of four prescribed remedies harmful,
  precision as the mechanism of false credibility.
- DIP-0034 — Event Ledger Substrate (`metric.attest` event type this DIP's
  `emit_facts` consumes; format and structure this DIP follows).
- DIP-0035 — Job Contracts + Unified Verifier (fact-freshness verification
  belongs here, not in this DIP; `ENG-2026-0728-001` silent-by-degradation
  genre that motivates this DIP's fallback+alert integration requirement).
- DIP-0038 — Action Loop + Co-sign (consumes grounded briefing output as
  candidate ledger tasks; follow-on, out of this DIP's scope).
