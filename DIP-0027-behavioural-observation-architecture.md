# DIP-0027: Behavioural Observation Architecture

| Field | Value |
|-------|-------|
| **DIP** | 0027 |
| **Title** | Behavioural Observation Architecture |
| **Author** | @datacore-one |
| **Type** | Standards Track |
| **Status** | Draft |
| **Created** | 2026-05-01 |
| **Updated** | 2026-05-01 |
| **Tags** | `observation`, `privacy`, `capture`, `redaction`, `personalisation`, `metacognition` |
| **Affects** | `lens` module, `health`, `trading`, `mail`, future appbuilder modules |
| **Specs** | `lens/docs/spec.md`, `docs/research/2026-05-01-hci-foundations-lens-module.md` |
| **Reference module** | `lens` (`.datacore/modules/lens/`, also `datacore-one/datacore-lens`) |
| **Depends on** | DIP-0019 (Learning Architecture), DIP-0022 (Module Specification), DIP-0002 (Layered Context) |

> **Note on numbering.** This proposal was originally drafted as DIP-0023; that
> number is held by the messaging-module DIP. The next available slot
> (DIP-0027) is used here. The substance is unchanged.

## Summary

This DIP establishes a system-wide pattern for capturing user-system interaction
data inside Datacore. It defines a three-tier write path (raw → curated →
derivations), an opt-in redaction policy with a productization-flip default,
a per-source disclosure-and-opt-in flow, and the principle that privacy is
enforced at processing and transmission boundaries rather than at capture.

The pattern is named so that any module touching behavioural data — `lens`
(reference implementation), `health`, `trading`, `mail`, and apps built on the
appbuilder framework — can declare DIP-0027 compliance and inherit a single,
audited contract instead of reinventing one.

## Agent Context

### When to Reference This DIP

**Always reference when:**

- Designing a new module that captures user behaviour, interactions, or
  derived signals
- Adding a new source to the `lens` event taxonomy
- Reviewing a redaction or retention policy for any local data store
- Auditing whether a capture path is privacy-respecting before productization
- Wrapping an external integration (Oura, Hyperliquid, Gmail) whose data feeds
  observation pipelines

**Key decisions this DIP informs:**

- Tier 1 raw streams are never scrubbed at capture, regardless of redaction
  setting
- Redaction is opt-in (`redaction_enabled`), defaulting OFF in personal/dev
  mode and flipping ON at productization
- Modules MUST gate every source behind explicit user opt-in via a disclosure
  flow before capture begins
- Distillation — not capture — is where privacy crosses the device boundary
- Schema evolution is forward-only; readers handle higher versions with a
  `forward_compat=True` flag rather than crashing

### Quick Reference

| Question | Answer |
|----------|--------|
| Where does the reference implementation live? | `.datacore/modules/lens/` (also `datacore-one/datacore-lens`) |
| Where is the raw store? | `~/.datacore/lens/observations.db` (SQLite) |
| What are the three tiers? | `events_raw` (verbatim) → `events` (validated) → `event_derivations` (embeddings, summaries) |
| When is the Tier 1 stream redacted? | Never. Tier 1 is always pure. |
| When is Tier 2 redacted? | When `redaction_enabled=true` (default OFF in dev, ON in productization) |
| Which boundary enforces privacy? | Processing + transmission, not capture |
| How does a user enable a source? | `lens enable <source>` after viewing `lens disclosure show` |
| How does a user revoke? | `lens disable <source>` (kill switch) and `lens redact --source <source>` (retroactive deletion) |
| What scope does observation operate at? | Cross-space — global across the Datacore install |

### Related DIPs

- [DIP-0019](./DIP-0019-learning-architecture.md) — Learning Architecture.
  Engrams are the *distilled directives* that DIP-0027's pipeline emits across
  the device boundary; DIP-0019 owns the engram store, DIP-0027 owns the
  observation stream that feeds it.
- [DIP-0022](./DIP-0022-module-specification.md) — Module Specification. Any
  module declaring DIP-0027 compliance follows the standard module layout
  defined here.
- [DIP-0002](./DIP-0002-layered-context-pattern.md) — Layered Context. Different
  concern (context loading) but the same "privacy across layers" tradition that
  this DIP extends to behavioural data.
- [DIP-0011](./DIP-0011-nightshift-module.md) — Nightshift. Detectors,
  distillers, and housekeeping (TTL on the audit log) run on the Nightshift
  schedule.
- [DIP-0026](./DIP-0026-architectural-primitives.md) — Architectural
  Primitives. DIP-0027 introduces a new candidate primitive ("Three-Tier
  Capture") that may be promoted to DIP-0026 once a second module adopts it.

### Related Agents and Skills

| Component | Role |
|-----------|------|
| `lens-classifier` agent | Triages candidate engrams emitted by detectors |
| `lens-reflector` agent | Synthesises weekly self-portrait from observation events |
| `learning-classifier` agent (DIP-0019) | Consumes lens candidates as one input among many |
| `engram-inject` skill (DIP-0019) | Reads distilled directives from `lens.profile()` and injects at LLM-call boundary |
| `nightshift` orchestrator (DIP-0011) | Runs detectors, distillers, and the redaction-log TTL sweep |

## Motivation

### Convergent need across modules

Multiple Datacore modules already capture, or will soon capture, behavioural
data:

- `lens` — comprehensive cross-surface observation (this DIP's reference
  implementation)
- `health` — biometric trends, sleep, HRV
- `trading` — execution events, journal entries, framework adherence
- `mail` — triage actions, response latency, draft abandonment
- `crm` — interaction cadence with contacts
- Future apps built on the `datacore-appbuilder` framework, each of which will
  need analytics + personalisation primitives

Without a system-wide pattern, every module reinvents:

- The redaction policy and its failure modes
- The schema-versioning strategy
- The disclosure-and-opt-in UX
- The trade-off between raw retention (forward-proofness) and storage cost
- The audit/redact CLI surface

The result is a privacy posture that is only as strong as its weakest module
and a fragmented onboarding experience for users who must learn each module's
local conventions.

### Empirical pressure from the `lens` design

The `lens` module specification (`lens/docs/spec.md`, locked 2026-05-01)
arrived at a specific architecture under HCI, calm-technology, IA, and
privacy-preserving-ML constraints. Several of the decisions made there are
**not specific to `lens`** — they apply to any module that captures
user-system interactions:

1. *Tier 1 is the source of truth for re-derivation when redactors or schemas
   evolve.* This is true for any append-only behavioural log, not just `lens`.
2. *Privacy lives at processing and transmission, not capture.* This shapes
   storage decisions for `health`, `trading`, and `mail` identically.
3. *Disclosure-then-opt-in beats opt-out.* Any source that captures user
   activity benefits from this pattern.
4. *Cross-space scope is correct for behavioural data.* A user's capture-form
   cycle time is the same human regardless of which space they are in.

These are architectural decisions, not implementation details. Promoting them
to a DIP lets future modules inherit them by reference rather than rediscover
them under similar pressure.

### What goes wrong without this DIP

Concrete failure modes already observable in adjacent systems:

- A module that scrubs at capture cannot be retroactively patched when its
  redactor misses a new secret format. The data is gone.
- A module without per-source kill switches forces all-or-nothing privacy
  decisions; users disable the whole module instead of one noisy source.
- A module that captures by default with a "settings page" buried in
  documentation creates surprise — a violation of HCI's gulf-of-evaluation
  principle and a reasonable trigger for distrust.
- Two modules with different audit CLIs double the user's burden; neither
  becomes habitual.

## Specification

### 1. Three-tier capture architecture

Compliant modules write capture events through three tiers, in cascade. Each
tier serves a distinct role; together they make capture forward-proof.

| Tier | Purpose | Validation | Mutability | Volume tradeoff |
|------|---------|------------|------------|-----------------|
| **1 — Raw** | Verbatim ingest. Source of truth for re-derivation when curated schema, redactor, or distillation logic evolves. | None — accepts arbitrary payloads | Append-only. Never modified. | Largest tier. |
| **2 — Curated** | Structured, validated, indexed. What detectors and analysers query. Linked to Tier 1 via `raw_event_id`. | Disciplined-core strict + wide-net warn | Mutable via re-derivation from Tier 1; never edited in place. | Smaller. Re-derivable. |
| **3 — Derived** | Pre-computed expensive transforms — embeddings, semantic clusters, summaries. Reproducible from Tier 1. | Per-deriver versioned | Regenerable. | Opt-in per event-type; not all events get derivations. |

#### Write path

```
capture(...)
    ├── source enabled?           → DISABLED if not (silent, by design)
    ├── scrub(metadata) [if redaction_enabled]
    │                             → REDACTION_FAILED if drop-mode + scrub failed
    ├── store.append_raw(...)     → Tier 1 always lands first (forward-proof)
    ├── validate(curated event)   → VALIDATION_ERROR if curated rejected
    │                               (raw is preserved regardless)
    └── store.append(curated, raw_event_id=...)
                                  → Tier 2 lands, linked back to Tier 1
```

Failure modes ordered by severity:

| Code | Meaning | Tier 1 written? | Tier 2 written? |
|------|---------|-----------------|-----------------|
| `DISABLED` | Source not opted in | No | No |
| `REDACTION_FAILED` | Drop-mode redactor unable to scrub | No | No (entry in `redaction_failures` log only) |
| `VALIDATION_ERROR` | Curated schema rejected event | Yes | No (re-shapeable later from raw) |
| `LOCKED` / `INTERNAL_ERROR` | Store unavailable | No | No (surface to caller) |
| `OK` | Both tiers written | Yes | Yes |

#### Tier 1 invariant (locked)

**Tier 1 is ALWAYS pure**, regardless of `redaction_enabled` setting. Redacting
at the raw boundary defeats the purpose of having a raw stream — if the
redactor was ever wrong about a pattern, scrubbed raw cannot recover. Tier 1
is the source of truth for re-derivation. This invariant is what makes the
architecture forward-proof.

The reference implementation enforces this in `lens/lib/store.py`:
`append_raw()` does not call the redactor; only `append()` (Tier 2) does.

### 2. Opt-in redaction policy

A single setting, `redaction_enabled`, governs whether Tier 2 is scrubbed at
write. The setting has two operational modes:

| Mode | `redaction_enabled` | When | Rationale |
|------|---------------------|------|-----------|
| **Personal / dev** | `false` (default) | Active during build phase. Tier 1 AND Tier 2 contain pure raw. | Maximum signal for re-derivation, minimum capture-time complexity. The user accepts that secrets in their own personal store on their own device are not a leak. |
| **Product release** | `true` (default at productization) | Activated when the module ships to users beyond the developer. Tier 2 gets scrubbed at write per per-source mode (`SCRUB_AND_WRITE` or `DROP_ON_REDACTION_FAILURE`). | Defence in depth: if Tier 2 is ever shared, exported, or read by a less-careful consumer, it has been scrubbed. Tier 1 stays pure regardless — invariant. |

The redactor lives in the module (mature, tested) but is **dormant** in
personal/dev mode. At productization, the default flips. The same code path
serves both modes; the only difference is the boolean.

#### Redactor failure modes (per-source)

A compliant redactor exposes two distinct write modes, configurable per
source:

- `SCRUB_AND_WRITE` (default): redactor removes the offending substring,
  replaces with `[REDACTED:type]` marker, writes the event. Use when the
  offending fragment is a clear pattern match.
- `DROP_ON_REDACTION_FAILURE`: redactor cannot confidently scrub (crash on
  malformed input, ambiguous match) → event is **not** written; failure is
  logged to a `redaction_failures` table with timestamp + source + reason
  (no payload). User can review failures via `lens audit --failures`.

The conservative default for `mail` and `trading` (or any future high-stakes
source) is `DROP_ON_REDACTION_FAILURE`.

### 3. Privacy at processing/transmission, not capture

This is the principle that shapes every other decision in the architecture:

> Privacy is enforced at the moment data is **processed for some purpose** or
> **transmitted off-device**, not at the moment of capture. Capture is
> unconstrained because — until raw data is processed or sent somewhere —
> there is no leak.

Four consequences follow:

1. **Capture is allowed to be promiscuous.** Every interaction, every AI
   response, every tool result, every page rendered. Volume is not a privacy
   concern; SQLite handles GB easily and storage is cheap.
2. **Detectors can mine richer signals.** Response text, tool outputs,
   conversation context — none of this would be available if the line were
   drawn at "user-emitted only".
3. **Distillation is the boundary.** Engrams (DIP-0019), abstract directives,
   and aggregated metrics are the only artefacts that may cross the device
   boundary. Raw never does.
4. **Retroactive controls are first-class.** Because capture is permissive,
   the user must be able to audit, redact, and disable retroactively without
   architectural friction.

This principle is **load-bearing**. It is not a stylistic preference; reversing
it would invalidate the rest of the design. New modules adopting DIP-0027
inherit this principle as an invariant.

### 4. Disclosure flow and per-source opt-in

No source captures until the user has read a plain-English manifest of what
that source captures and what it does NOT, then explicitly opts in.

#### First-run flow

1. Module install scaffolds `lens/disclosure/<source>.md` for every declared
   source, containing:
   - **What is captured** (event types, fields, examples)
   - **What is NOT captured** (explicit non-list)
   - **Where it is stored** (`~/.datacore/lens/observations.db`)
   - **How to disable** (`lens disable <source>`)
   - **How to redact retroactively** (`lens redact --source <source>`)
2. First run prints `lens disclosure show` summary and exits without enabling
   any source.
3. User runs `lens enable <source>` per source they wish to activate. The
   command requires confirmation and logs the opt-in timestamp.
4. Default state is **all sources off**. There is no global "enable all"
   shortcut on first run.

#### Ongoing reference

`lens disclosure show [<source>]` is always available and always reflects the
currently installed redactor + schema version. If a source's disclosure
changes between releases (new fields captured, redactor updated), the next
`lens enable` call surfaces a diff and re-prompts.

#### Per-source kill switch

`lens disable <source>` stops capture on that source. Disable is propagated
through both an in-process flag (immediate effect on calls in the current
process) and the SQLite `source_state` table (effective for the next process
to read it). In-flight events that have already passed `is_source_enabled()`
complete the write — guaranteed cut-off is *one event cycle* (typically
<100ms), not "instant".

`lens disable` also prints a retroactive-deletion suggestion:

```
Capture stopped. 47 past events from `trading` remain in the store.
Run `lens redact --source trading` to delete them.
```

### 5. Cross-space scope

Behavioural observation operates **across all spaces, not within one**. The
event store, pattern registry, and distilled-directive output are global to
the Datacore install.

Rationale:

- A user's capture-to-form cycle time is the same person regardless of which
  space they are working in.
- Recurrence detection benefits from cross-space data — a pattern that
  appears in `0-personal` and again in `2-datacore` is stronger evidence than
  either alone.
- Distilled directives (engrams) injected at the LLM-call boundary should
  reflect the whole user, not their `2-datacore`-shaped persona.

This is a deliberate departure from the per-space-data convention of
DIP-0026's *Space-Local Data* primitive. A behavioural-observation module
**MUST** declare global scope in its `module.yaml`:

```yaml
data_scope: global   # not per-space; required for DIP-0027 compliance
data_path: ~/.datacore/lens/   # under XDG / $DATACORE_HOME
```

The data path is required to be **outside** any sync root (iCloud, Dropbox,
Obsidian sync). Module install verifies this and refuses to start if the path
is under a sync root.

### 6. Privacy guarantees (formal)

A DIP-0027-compliant module makes five formal guarantees:

1. **Locality.** All raw events live on-device, in a path under
   `$DATACORE_HOME` (default `~/.datacore/<module>/`). Never sync, never copy
   off-device, never transmit. The only writer is the local daemon; there is
   no remote ingest path. Path is git-ignored, excluded from default backups,
   and not under a sync root. Verified at install.

2. **Write-time redaction (when enabled).** When `redaction_enabled=true`,
   known-sensitive substrings (API keys, OAuth bearer tokens, PEM blocks,
   GitHub/Slack/Stripe-typed keys, JWT, paths under `private/`, credit-card
   numbers) are redacted before the Tier 2 write. Two failure modes
   (`SCRUB_AND_WRITE`, `DROP_ON_REDACTION_FAILURE`) are configurable per
   source. Tier 1 remains pure regardless.

3. **Per-source kill switches with retroactive-deletion suggestion.** Every
   source can be disabled independently. Disable is logged so the user can
   trace gaps. The disable command prints the retroactive-deletion command
   for past events from that source.

4. **Distillation as the privacy boundary.** Only distilled directives —
   abstract, aggregated, semantically detached from any single event —
   cross the device boundary into external LLM calls. Directives are
   reviewed by the user before injection. Raw events never cross the
   boundary.

5. **Audit and redact retroactively.** `<module> audit` shows captured data
   with filters; `<module> redact` allows retroactive deletion of events or
   directives. The redaction log is itself subject to a 30-day TTL — entries
   older than 30 days are deleted by the nightly housekeeping run (per
   DIP-0011) unless the user has explicitly pinned them for compliance. This
   prevents the redaction log from becoming a fingerprint of sensitive
   events.

These five guarantees form the **privacy contract**. A module is not
DIP-0027-compliant unless all five hold.

### 7. Schema evolution

Every event carries a `schema_version` (semantic, e.g., `1.2`). Schema
evolution follows three rules:

1. **Forward-only migration.** New fields, new event types, new sources are
   added in higher versions. Old events are never modified — they remain at
   the version they were written under.

2. **Reading higher versions degrades gracefully.** A detector compiled
   against schema `1.2` that encounters a `1.3` event MUST return the event
   with `forward_compat=True` flagged, not crash. The detector skips fields
   it does not understand.

3. **Never break old events.** A migration that would invalidate older Tier 2
   events triggers re-derivation from Tier 1 instead. Tier 1 is the canonical
   source; Tier 2 can be rebuilt.

Detectors filter by minimum schema version (`min_schema_version`) when they
require a specific field. Events below that version are skipped, not errored.

## Compliance criteria

A module is DIP-0027-compliant if and only if:

| # | Requirement | Verification |
|---|-------------|--------------|
| 1 | Has a Tier 1 raw stream that NEVER scrubs | `append_raw()` does not call redactor; covered by test |
| 2 | Implements opt-in redaction with productization-flip semantics | `redaction_enabled` setting present, default OFF in dev mode, ON in product config |
| 3 | Provides per-source disclosure flow before any capture begins | `<module> disclosure show` exists; `<module> enable <source>` required before first event |
| 4 | Operates cross-space (not within a single space) | `data_scope: global` declared in `module.yaml`; install verifies path is not under sync root |
| 5 | Implements all five privacy guarantees (§6) | Each guarantee has a test in `tests/` |
| 6 | Schema evolution is forward-only | `migrate_forward()` rejects backwards calls; covered by test |
| 7 | Audit + redact CLI surface | `<module> audit`, `<module> redact`, `<module> disable`, `<module> enable` |

A module that captures behavioural data without satisfying these criteria
**MUST NOT** declare DIP-0027 compliance and **SHOULD** be reviewed before
release.

## Rationale

### Why three tiers and not one

A single tier forces every capture decision to be permanent. If the redactor
missed a Stripe key pattern in week 3 and the patch lands in week 4, there is
no way to retroactively scrub older events without losing the underlying data
— unless the raw stream was kept. If a Phase B detector wants
`tool_chain_signature` and the system never extracted it, the system is stuck
— unless the raw stream was kept. Three tiers give reversibility without
sacrificing query speed.

The cost is roughly 3x storage. SQLite handles the volumes involved (~7-10 GB
per year for the heaviest profile) trivially, and disk is cheap. The
trade-off is unambiguous.

### Why opt-in redaction, not always-on

Always-on redaction at capture sounds safer and is, in fact, weaker: it
collapses the dev/personal mode (where redaction adds complexity for no
benefit — the user knows their own secrets) into the product mode, slowing
iteration and making it harder to debug detector behaviour against real raw
data.

The productization flip is the right time to enable redaction: precisely when
the data may be seen by something other than the user who captured it.
Before then, redaction is theatre.

### Why privacy-at-processing, not privacy-at-capture

Privacy-at-capture has surface appeal — "we never see your raw data" — but
breaks under scrutiny:

- It conflates *capture* with *exposure*. Data captured to a local SQLite file
  on the user's own device is not exposed to anyone. The leak happens at
  transmission.
- It forecloses re-derivation. A scrub at capture is permanent.
- It produces worse detection. Detectors deprived of context produce more
  false positives, more friction, and more correction events — exactly the
  signals the system is trying to learn from.

Privacy-at-processing puts the boundary where the leak can actually happen.
Apple's Private Cloud Compute architecture (2024) makes the same argument at
a much larger scale: the structural impossibility of third-party benefit from
captured data is what makes capture acceptable, not the absence of capture.

### Why cross-space, not per-space

Behavioural data describes the user, who is one person across spaces. A
distilled directive that says *"prefers data-dense responses"* is true in
`0-personal` and in `2-datacore`. Forcing per-space duplication would either
fragment the signal (small per-space samples) or duplicate it (drift over
time as each space's redactor and detector versions diverge).

Cross-space scope is also what makes recurrence-promotion meaningful. A
pattern that appears in two spaces is stronger evidence than the same pattern
appearing twice in one.

### Alternatives considered and rejected

- **Per-module privacy posture, no DIP.** Rejected: the result is a posture
  that is only as strong as the weakest module, and the user faces an
  inconsistent audit/redact surface across modules.
- **Always-on redaction, no opt-out.** Rejected: collapses dev mode into
  product mode, slowing iteration; provides false security under
  privacy-at-capture framing.
- **Per-space behavioural data.** Rejected: fragments signal, complicates
  cross-space recurrence detection, drifts over time as redactor/schema
  versions diverge.
- **Capture-with-immediate-scrub-and-discard-raw.** Rejected: forecloses
  re-derivation when the redactor or schema evolves. The whole point of
  Tier 1 is to keep the raw stream available for future detectors that have
  not been written yet.

## Backwards Compatibility

This DIP defines a new pattern; no existing module is broken by its
adoption. However, modules that informally capture user data today (early
versions of `health`, `trading`, `mail` with ad-hoc logging) **SHOULD** be
audited against the §7 compliance checklist before they declare DIP-0027
compliance.

Migration friction for existing modules is real: each would need to:

1. Introduce a Tier 1 raw stream alongside the existing capture path
2. Add a `redaction_enabled` setting
3. Add the disclosure-and-opt-in flow
4. Move data path to global scope if currently per-space
5. Add the audit/redact CLI surface

This is non-trivial. The recommended sequencing is to migrate one module at a
time, treating `lens` as the prototype and copying its `lib/store.py`,
`lib/redact.py`, `lib/audit.py` patterns.

## Security Considerations

The privacy contract in §6 is the core security commitment. Three additional
considerations:

1. **The audit log itself is a side channel.** A redaction record reveals
   that *something sensitive happened at time T from source S*. The 30-day
   TTL on the redaction log mitigates this for casual fingerprinting; users
   with stricter requirements can pin entries explicitly.
2. **The disclosure manifest is the user's mental model.** It must be kept
   accurate as the redactor and schema evolve. A misleading disclosure is
   worse than no disclosure — it produces the gulf-of-evaluation failure
   that the disclosure flow is meant to prevent.
3. **Path-safety is enforced at install.** A module install that finds its
   data path under iCloud, Dropbox, or Obsidian sync MUST refuse to start.
   The user's most-private store ending up in the sync of a third-party SaaS
   is the worst plausible failure mode and the easiest to prevent.

## Implementation

### Reference implementation

`lens` is the reference implementation. Phase A (Capture Foundation) covers
the architecture defined in this DIP:

- Module scaffolding: `.datacore/modules/lens/module.yaml`,
  `CLAUDE.base.md`, `README.md`
- Schema: `lens/lib/schema.py` (event taxonomy, dataclasses, JSON-Schema
  export, actor enum)
- Store: `lens/lib/store.py` (SQLite wrapper, Tier 1 + Tier 2, schema
  versioning, `redaction_failures` table, `migrate_forward`)
- Redactor: `lens/lib/redact.py` (secret patterns: JWT, OAuth bearer, PEM,
  Stripe/Slack/GitHub/AWS keys; entropy backstop; context-aware exemptions
  for legitimate hex like git commit hashes)
- Capture API: `lens/lib/capture.py` (`lens.capture(...)` with
  disclosure-gated source enable, two-mode redaction failure, in-process
  disable flag)
- Audit: `lens/lib/audit.py`, `lens/lib/cli.py` (`lens status`, `lens
  summary`, `lens daily-digest`, `lens disclosure show`, `lens audit`,
  `lens redact`, `lens disable`/`enable`)
- Tests: `lens/tests/` — TDD-first, ≥80% coverage on `lib/`

The Phase A acceptance criteria in `lens/docs/spec.md` map directly onto the
compliance criteria in §7 of this DIP. Modules adopting DIP-0027 should
treat the `lens` Phase A scope as the minimum viable surface.

### Adoption path for new modules

1. Declare `data_scope: global` and `compliance: [DIP-0027]` in
   `module.yaml`.
2. Vendor or import the `lens` redactor (`lens.lib.redact`) — do not
   reimplement the secret-pattern set.
3. Implement the three-tier write path. The `lens.lib.store` module can be
   used directly if the module's events fit the lens schema; otherwise
   reimplement following the same shape.
4. Author per-source disclosure documents in `disclosure/<source>.md`.
5. Provide `<module> {status, audit, redact, disable, enable, disclosure}`
   CLI commands. The signatures should match `lens` for consistency.
6. Add tests covering the seven compliance criteria.
7. Register in `module.yaml` triggers and hooks per DIP-0022.

### Rollout plan

- **Now (2026-05):** `lens` Phase A ships as the reference implementation.
  This DIP enters Draft.
- **+1 month:** Review pass. `lens` Phase B (detectors, distillation) does
  not affect this DIP.
- **+3 months:** First adoption — likely `health` or `trading` migrating to
  the pattern. DIP enters Review based on adoption findings.
- **+6 months:** Second adoption confirms generalisability. DIP can move to
  Accepted; the Three-Tier Capture pattern is added to DIP-0026 Architectural
  Primitives.

## Consequences

### Positive

- **Forward-proof capture.** When the redactor evolves or the curated schema
  changes, the system re-derives from Tier 1. No data is lost to schema
  decisions made before the use case existed.
- **Re-usable across modules.** Future modules adopt the pattern by
  reference rather than reinventing privacy + capture from scratch. This is
  the same lever DIP-0026 architectural primitives provide for other
  patterns.
- **Trustable.** The five formal guarantees give users (and reviewers) a
  precise contract to evaluate against, rather than a vague "we respect
  privacy" claim.
- **One code path, two modes.** The same module serves personal-dev (no
  redaction) and product-release (full redaction) via a single setting flip.
  This collapses what would otherwise be two diverging codebases.
- **Audit + redact uniformity.** Users learn the CLI surface once and apply
  it to every observation-capable module.

### Negative

- **Storage cost.** Tier 1 + Tier 2 + Tier 3 multiplies storage roughly 3x
  versus a single-table append-only log. For `lens`, this is ~7-10 GB/year on
  a heavy-use profile — manageable but not free.
- **Complexity.** Three tiers, two redaction modes, per-source disclosure,
  per-source kill switches. More moving parts than a one-file log. New
  authors need to read this DIP before adding a source.
- **Migration friction.** Existing modules that informally capture user data
  must rewrite to comply. This is real work, not a wrapper.
- **Cross-space scope is a departure.** DIP-0026's Space-Local Data primitive
  is the default for module data; DIP-0027 explicitly overrides it for
  behavioural observation. Reviewers should understand the rationale before
  approving global-scope declarations.

## Open Questions

1. **Granularity of the productization flip.** Should `redaction_enabled` be
   one global setting, or should each source carry its own flag? The
   reference implementation currently uses a single global flag with
   per-source mode (`SCRUB_AND_WRITE` vs `DROP_ON_REDACTION_FAILURE`).
   Per-source enable might be needed if some sources are released to product
   while others are still in dev iteration.

2. **Retroactive redaction under privacy-at-processing.** When a user
   redacts past events, what happens to derivations that were already emitted
   to the engram store (DIP-0019)? The `lens redact` command in the
   reference implementation deletes events and the redaction log, but
   downstream engrams may carry residue. This is partly addressed by
   DIP-0019's reconsolidation mechanism, but the contract between DIP-0027
   redact and DIP-0019 retire needs to be made explicit.

3. **Team-space contexts.** When multiple users share a Datacore space (team
   spaces, per DIP-0001), behavioural observation is no longer about a single
   user. Either: (a) team-space modules MUST NOT capture behaviour,
   (b) team-space capture is per-user and tagged, or (c) a separate DIP
   addresses team-space observation. The current scope of this DIP is
   personal-space only; team-space is left for a future DIP.

4. **Sibling DIP for the wire format.** A future DIP defining the
   cross-process capture endpoint contract (HTTP wire format for non-Python
   clients to emit events) is anticipated. Such a DIP would specify
   authentication, schema validation, rate limiting, and the same disclosure
   flow at the network boundary. Its number is reserved for the next
   available slot at the time of authoring.

## References

### Datacore

- `.datacore/modules/lens/docs/spec.md` — reference implementation specification
  (locked 2026-05-01)
- `.datacore/modules/lens/lib/store.py` — three-tier store
- `.datacore/modules/lens/lib/redact.py` — redactor
- `.datacore/modules/lens/lib/capture.py` — public capture API
- `docs/research/2026-05-01-hci-foundations-lens-module.md` — annotated
  bibliography (HCI methodology, calm technology, IA tradition,
  privacy-preserving ML, pattern language)
- DIP-0019 — Learning Architecture (engrams as the distilled output)
- DIP-0022 — Module Specification (module layout)
- DIP-0011 — Nightshift Module (housekeeping, detectors)
- DIP-0002 — Layered Context Pattern (privacy-across-layers tradition)
- DIP-0026 — Architectural Primitives (where Three-Tier Capture may be
  promoted on second adoption)

### External

- Apple Private Cloud Compute architecture (2024) — structural-impossibility
  framing for the privacy-at-processing principle.
- Engelbart, D. (1962). *Augmenting Human Intellect: A Conceptual Framework*.
  Stanford Research Institute. — IA tradition: amplify what the user
  already does, never substitute.
- Weiser, M. (1991). The Computer for the 21st Century. *Scientific
  American*, 265(3), 94-104. — Calm technology: periphery by default.
- Alexander, C. (1977). *A Pattern Language*. Oxford University Press. —
  Recurrence-as-promotion criterion.
- Card, S., Moran, T., & Newell, A. (1983). *The Psychology of
  Human-Computer Interaction*. Lawrence Erlbaum. — Passive
  moment-of-occurrence capture.
- Shneiderman, B. (1998). *Designing the User Interface*. Addison-Wesley. —
  Readable system-model for users (gulf of evaluation).

---

*This DIP names a pattern that the `lens` module arrived at under specific
HCI, privacy, and forward-proofness constraints, and promotes it to a
system-wide contract that future behavioural-observation modules can
inherit by reference.*
