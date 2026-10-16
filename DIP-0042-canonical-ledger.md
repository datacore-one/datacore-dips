# DIP-0042: Canonical Ledger & Finality

| Field | Value |
|-------|-------|
| **DIP** | 0042 |
| **Title** | Canonical Ledger & Finality |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Draft |
| **Created** | 2026-08-04 |
| **Updated** | 2026-08-04 |
| **Tags** | `ledger`, `finality`, `sequencer`, `bitemporality`, `hash-chain`, `snapshots`, `datacore-v2` |
| **Affects** | `.datacore/lib/ledger/` (new: `chain.py`, `snapshot.py`, `sequencer.py` — none built yet, see Implementation), `.datacore/lib/ledger_cli.py` (new subcommands, unbuilt), `<space>/.datacore/ledger/blocks/` (new), `<space>/.datacore/ledger/snapshots/` (new), `<space>/.datacore/ledger/archive/` (new, deferred — see Retention, Snapshots and Pruning) |
| **Specs** | None yet — this DIP is the spec; no code exists (see Implementation) |
| **Agents** | any process that needs to distinguish settled from provisional ledger state; the actor currently named sequencer via `policy.set`; any process auditing or verifying the chain locally |
| **Depends** | [DIP-0034](DIP-0034-event-ledger-substrate.md) — Event Ledger Substrate. Non-functional without it: the per-writer pool, the `hlc` field and its ordering guarantee, `fold()`'s left-to-right reduction semantics, and the `policy.set`/`EVENT_TYPES` schema this DIP reuses without modification. |
| **Relates to** | [DIP-0038](DIP-0038-action-loop-cosign.md) (the other consumer of `policy.set`; this DIP proposes the same payload-discriminator pattern DIP-0038 uses nowhere but that DIP-0034 already established for `metric.attest`), [DIP-0043](DIP-0043-org-projection.md) (drafted alongside this DIP; its genesis import is the first workload likely to exercise the `late` flag in practice), `ENG-2026-0729-016` (the original "do NOT build a blockchain now" owner direction this DIP stays inside the spirit of — see Owner Decision), `.datacore/dip-review/DESIGN-BRIEF-v2.1.md` §B/§C (binding design brief, conversation ratified 2026-08-03/04 — authoritative wording where this DIP and the brief must agree) |


> **Published 2026-10-04 as Draft** (ledger upgrade Phase 3, audit A#13). This
> text was written in August 2026 and is published as it stood, so that the
> code's citations of DIP-0042 resolve. Part of it is built since: the
> `ledger.seal` event, the sequencer role and settlement readers live in
> `.datacore/lib/ledger/seal.py` and `ledger_seal.py`; only the designated
> sequencer's seals count, and there is no default sequencer (each install
> declares one, or nothing is sealed). Blocks, snapshots and archives are not
> built. What the code does today is stated in
> [DIP-0034](DIP-0034-event-ledger-substrate.md), "Normative current state".

## Summary

Answers the standing question "canonical ledger, or fold on the fly?" as
**both, layered.** The per-writer event pool defined by
[DIP-0034](DIP-0034-event-ledger-substrate.md) remains the sole write path
and the sole source of truth for event payloads — nothing about that
changes. This DIP adds a second, **derived** layer: a single-writer,
hash-linked **canonical chain** (`<space>/.datacore/ledger/blocks/`) that
indexes pool events by hash and locator, plus periodic **snapshots**
(`<space>/.datacore/ledger/snapshots/`) that turn `fold()`'s cost from
O(all events) into O(tail). The chain gives two things the pool alone
cannot: a **settled height** below which the fold's answer is guaranteed
stable (finality), and a bounded-cost read path. It is verified, never
trusted — any machine recomputes block content from its own copy of the
pool and rejects anything that doesn't check out.

> **The canonical chain is derived and reproducible, never a second source
> of truth.** Every block is an index over events that already exist,
> immutably, in the per-writer pool (DIP-0034). Nothing in this DIP creates
> a second place where truth can diverge from the pool. Any machine can
> recompute the chain, a snapshot, or the full folded state from its own
> pool copy at any time, with or without the sequencer's help — and if the
> sequencer is down, the system degrades to exactly what DIP-0034 already
> specifies: on-the-fly fold, full accuracy, no coordination required. See
> Specification, "Degradation" below — stated there prominently, not as an
> afterthought.

## Agent Context

### When to Reference This DIP

**Always reference when:**
- Implementing the sequencer, its fallback takeover, or fork detection.
- Building or reasoning about any tool that reports ledger state and needs
  to say whether that state is **settled** (finalized, below the chain's
  frontier) or **provisional** (only ever available via DIP-0034's
  on-the-fly fold).
- Reasoning about bitemporal ordering — the difference between an event's
  `hlc` (valid time, DIP-0034, unchanged) and `observed_at` (transaction
  time, defined here) — or the `late` flag.
- Deciding whether a read path needs full on-the-fly fold (DIP-0034, always
  correct, O(all events)) or the snapshot-based fast path (this DIP,
  O(tail), only as good as the chain it's built from).
- Detecting or handling a fork: two blocks at the same height with
  different hashes. This is a hard, loud error in this design — never
  silently resolved by any heuristic.
- Assigning or reasoning about the sequencer role, which is **data**
  (a `policy.set` event), never a hardcoded process identity.
- Reasoning about ledger storage growth, archival, or pruning — see
  Retention, Snapshots and Pruning below. The answer is snapshots plus
  optional archival, never rewriting or compacting history in place.

### Quick Reference for Agents

| Question | Answer |
|----------|--------|
| Is the chain the write path? | No. The pool ([DIP-0034](DIP-0034-event-ledger-substrate.md)) is still the only write path. The chain is a derived, read-side index, built after the fact. |
| What happens if the sequencer is down? | Writes continue and on-the-fly fold works exactly as it does today (DIP-0034, unchanged). Only finality pauses — no new blocks, settled height stops advancing. Nothing blocks. |
| What does a block contain? | References to pool events — `{writer, file, seq, event_hash, hlc, observed_at, late}` per entry — never copies of event payloads. |
| How does fold cost stay bounded as the pool grows forever? | Snapshots at settled heights give O(tail) fold instead of O(all events) — see Specification, "Snapshots." |
| How often is a block cut? | Hybrid: a daily floor, or when the un-blocked tail exceeds a configured event count — whichever first (resolved 2026-08-05). Do not lower the floor; a shorter window manufactures `late` entries out of ordinary sync jitter. |
| Should I shorten the cadence to catch drift or forks faster? | No. Drift detection is anchored to a writer version vector, not a height ([DIP-0043](DIP-0043-org-projection.md)), so it is bounded by sync latency. Forks are prevented by `fallback_after_seconds` exceeding the cadence floor, not detected by cutting more often. |
| A `late: true` entry landed below my snapshot's frontier. Now what? | That snapshot and every snapshot above it are invalidated and MUST NOT be used as a fold base. Recompute from the most recent still-valid snapshot below the late event's `hlc`. A from-scratch fold was and remains correct. |
| Who is the sequencer? | Whoever the most recent `policy.set` event (payload `policy: "ledger.sequencer"`) names. Role assignment is data, not code. |
| Are the sequencer and the arbiter the same role? | No — three roles exist (sequencer, arbiter, hub) and they are separately assigned. They may be held by the same actor and by default should be, but merging them into one concept costs you the ability to fail over or diagnose one independently. See "Three roles, separately assigned." |
| Which actor should hold them? | Apply the three selection criteria (highest availability, single writer, freshest view). An installation's Chief-of-Staff actor typically satisfies all three and is the recommended default — but this spec assigns nothing. |
| Is there a message bus / gossip hub between actors? | No, and it is deliberately deferred. Per-writer files already sync conflict-free over git; a hub is push-based and would make progress depend on a live path to one machine. It buys latency, not correctness — see the trigger in "Three roles, separately assigned." |
| What if two sequencers write at once? | A second block at the same height with a different hash is a fork — a hard, loud error, never silently reconciled. See "Fork detection." |
| Can a consumer trust a block just because the sequencer produced it? | No. Verify, don't trust: recompute event hashes from your own pool copy and check `root_hash`/`prev_block_hash` before treating a block as valid. A block that fails this is rejected locally and reported. |
| Does this change DIP-0034's event schema? | No new `EVENT_TYPES`, no new required payload field on any existing type. `policy.set` gains a second recognized payload family (`policy: "ledger.sequencer"`) under DIP-0034's existing payload-additive invariant — the same pattern already used for `metric.attest`'s `metric` discriminator. |
| Does the ledger grow without bound? | Storage, no — tens of MB/year at this installation's actual scale, git handles it trivially (see Retention, Snapshots and Pruning). Fold time, yes without snapshots — that's the real cost, and it's what Snapshots solve, not what archival solves. |
| Can old blocks or events be compacted to save space? | No. Moving data to `ledger/archive/` is permitted; rewriting, recomputing, or compacting anything in place is forbidden — a normative constraint, see Retention, Snapshots and Pruning. |

### Related Agents

| Agent | Uses This DIP For |
|-------|-------------------|
| `dip-preparer` | Treats this DIP, alongside [DIP-0034](DIP-0034-event-ledger-substrate.md), as the dependency anchor when authoring or amending [DIP-0043](DIP-0043-org-projection.md) — genesis import's valid-time fallback ladder and any read-time verification design assume this DIP's block/snapshot shape and the `late` flag defined here. |
| `context-maintainer` | Owns the same class of doctrine follow-up DIP-0034 named for itself (Implementation, Rollout Plan): once this DIP ratifies, any corpus text that describes "the ledger" as a single flat event log should be qualified to note the derived chain/snapshot layer exists alongside the pool — same bifurcation pattern, one layer deeper. |
| `nightshift-orchestrator` | Named only as a plausible host for the sequencer role — it already runs continuously on always-on hosts per [DIP-0011](DIP-0011-nightshift-module.md) and is the kind of long-lived process a `policy.set`-named sequencer or fallback would realistically be. No code path in this DIP or DIP-0011 wires them together; this is not a live integration. |

### Integration Points

- [DIP-0034](DIP-0034-event-ledger-substrate.md) — hard dependency. This DIP
  changes nothing in DIP-0034's event schema, `EventLog`, `fold()`, or
  invariants; it adds a read-side derived index over the pool DIP-0034
  defines. The bitemporal mechanism referenced by the DIP-0034 amendment on
  valid-time/transaction-time (design brief §B) is specified here: `hlc`
  stays the fold's ordering key (DIP-0034, unchanged); `observed_at` and
  `late` live only in this DIP's block index, never in the DIP-0034 event
  itself — see Specification, "Bitemporality."
- [DIP-0038](DIP-0038-action-loop-cosign.md) — this DIP is the second
  consumer of the `policy.set` event type DIP-0038 uses for co-sign
  thresholds. Same event type, disjoint payload family, disambiguated by a
  `policy` discriminator field — the identical pattern DIP-0034 already
  established for `metric.attest`'s `metric` field, applied here to
  `policy.set` for the first time.
- [DIP-0043](DIP-0043-org-projection.md) — drafted alongside
  this DIP from the same design-brief conversation. Its genesis import
  (bulk-importing historical org tasks with a valid-time fallback ladder
  reaching back through git history) is the first workload plausibly
  producing systematically late events relative to a settled frontier —
  named here as a Rollout Plan trigger, not a functional dependency in
  either direction.
- [DIP-0011](DIP-0011-nightshift-module.md) — Nightshift module; the kind of
  long-lived, cross-machine process a sequencer or fallback would plausibly
  run as, per the Related Agents note above. No integration exists.

## Motivation

This DIP is not part of DIP-0034's original Phase 1–8 roadmap (DIP-0034
Specification, "Phase → DIP mapping"). It is a new addition, ratified via
the 2026-08-03/04 design-brief conversation, sitting alongside that roadmap
rather than filling a slot in it. It closes two concrete problems that
Phase 1, as shipped, leaves open by design.

### Problem 1: retroactive insertion changes the answer, silently

Consider a laptop that goes offline for a week — an already-documented
topology in Datacore (`ENG-2026-0727-004`, cited in DIP-0034 Motivation as
the workstation-to-server sync gap) — and then reconnects. Under DIP-0034 alone,
`read_events()` merges every writer's `.jsonl` file and sorts by `hlc`:
global, deterministic, valid-time order (DIP-0034 Specification, "Hybrid
logical clock"). That part is *correct* — the newly-synced week-old events
get folded in at the point their `hlc` says they causally belong, and the
fold recomputes cleanly, with no corruption and no crash.

But nothing about this is bounded or visible. Every fold, at any point in
time, is provisional forever: the moment that offline laptop syncs,
`fold()` over the newly-merged event list can — silently — produce a
different `LedgerState` than it did an hour earlier for the exact same
question ("what is item `t-042`'s status?"), because a new event with an
earlier `hlc` has inserted itself into the middle of an order that was
never actually fixed. DIP-0034 alone has no concept of "the answer as of a
moment ago is guaranteed stable." Every read is exposed to every future
sync, forever, with no error, no warning, and no way for a reader who
already acted on yesterday's answer to know it changed underneath them.

### Problem 2: fold cost is O(all events), forever

`fold()` is, by design, a pure function over the *entire* merged event
list, replayed from the first event ever written (DIP-0034 Rationale, "Why
a pure fold rather than incremental/streaming state updates?" — the
correct trade for testability and replayability at Phase 1's scale). But
nothing bounds it: every actor's file only ever grows (DIP-0034 Invariant
1, append-only), across every space, forever — and Phase 8
([DIP-0041](DIP-0041-executor-adapters.md)) is explicit that `spend.record`
goes live "end-to-end," i.e. on every metered execution. A query as simple
as `ledger_cli.py items --status completed` pays the cost of replaying the
complete history of a space, every single time, indefinitely. That is a
fine trade at hundreds or thousands of events. It is not a fine trade at
the millions of events a matured, multi-agent, multi-year installation will
eventually accumulate — and DIP-0034 explicitly declines to solve it: its
own Rationale accepts the O(all events) cost as the price of purity, and
its Open Question 3 ("Sequencer replacement / quorum triggers") defers any
sequencer concept as trigger-based future work, not a Phase 1 concern.

### Use cases

1. **Finality for downstream consumers.** Anything that reports "current
   state" — a dashboard, a briefing, the `fact` class of `metric.attest`
   ([DIP-0037](DIP-0037-grounded-briefings.md)) — can distinguish "this
   answer is settled, safe to cite" from "this answer is still provisional,
   still open to correction by a late arrival." DIP-0034 alone cannot
   express this distinction at all.
2. **Bounded-cost reads at scale.** Snapshots give `ledger_cli.py
   items`/`balances` an O(tail) path, without weakening `fold()`'s purity
   or replayability guarantees — see Specification, "Snapshots."
3. **Sync anomalies become visible, not silent.** A late arrival is a
   recorded fact (`late: true` in the block index) instead of an invisible
   silent reorder — an operator, or DIP-0043's future org reconciler, can
   audit exactly which events were late and when.
4. **A substrate for genesis import.** [DIP-0043](DIP-0043-org-projection.md)'s
   bulk import of historical org tasks (design brief §D) is exactly the
   kind of workload likely to produce systematically late events — valid
   times reaching back through git history, arriving all at once. This DIP
   is what lets that import be observed and audited rather than silently
   absorbed into an already-settled fold.

### Current Workaround (pre-DIP)

Exactly DIP-0034 Phase 1 as shipped: `read_events()` + `fold()` over the
full pool, on every call, with no concept of settled vs. provisional and no
bound on replay cost. This is the actual current behavior of every
installed ledger today. This DIP changes none of it as a write path or as
a correctness guarantee — it adds a derived, optional, independently
verifiable index alongside it (see Backwards Compatibility).

## Owner Decision (folded into this DIP)

The design brief ratified in conversation 2026-08-03/04
(`.datacore/dip-review/DESIGN-BRIEF-v2.1.md`, Section C — authoritative
wording for this DIP where the two documents must agree) settles the
standing question **"canonical ledger, or fold on the fly?"** as: both,
layered. Adopted now:

1. **Pool remains the sole write path and sole source of truth for
   payloads** — completely unchanged from DIP-0034.
2. **A derived chain** (blocks referencing, never copying, pool events)
   provides finality: a settled height below which the fold's answer for
   already-included events is guaranteed stable.
3. **Snapshots** provide bounded-cost reads without weakening `fold()`'s
   purity (Specification, "Snapshots").
4. **Verify, don't trust.** Every consumer that uses the fast path
   re-derives correctness locally against its own pool copy; the sequencer
   is never a trusted oracle, signed or not.
5. **Sequencer role is data** (`policy.set`), not a fixed process —
   DIP-0034 Invariant 5 ("the sequencer is replaceable") extended here into
   a concrete assignment-plus-fallback mechanism.
6. **Explicitly NOT adopted now:** multi-sequencer consensus or voting;
   mandatory migration of any existing coordination path onto the chain;
   any change to signing's opt-in status
   (`ENG-2026-0729-030`, DIP-0034 — this DIP does not touch signing at
   all).

Continuing the original owner direction (`ENG-2026-0729-016`, cited in
DIP-0034's Owner Decision): "do NOT build a blockchain now" remains in
force. This DIP is not a distributed consensus mechanism between
mutually-untrusting parties — it is a single-sequencer, verify-don't-trust
derived index, chosen as the smallest structure that buys finality and
bounded fold cost without a quorum protocol nobody yet needs. See
Rationale, "Alternatives considered," and DIP-0034 Open Question 3, which
already defers exactly that.

## Specification

> **Repeated from Summary.** The canonical chain is derived and
> reproducible, never a second source of truth. Every block indexes events
> that already exist, immutably, in the DIP-0034 pool. Any machine can
> recompute the chain, a snapshot, or the full fold from its own pool copy
> at any time, with or without the sequencer.

### Pool vs. chain

Two layers, with different write models:

- **Pool (unchanged).** Per-writer `<space>/.datacore/events/<actor>.jsonl`
  (DIP-0034). Still the write path. Still the only place a payload lives.
  Multiple writers, no live coordination required, per-writer locking only.
- **Canonical chain (new, derived).**
  `<space>/.datacore/ledger/blocks/NNNNNN.json`, written only by the actor
  currently holding the sequencer role. Single-writer, so it never
  conflicts in git — no merge, no lock contention, the same way a
  per-writer pool file never conflicts across *different* writers.

### Block shape

```jsonc
{
  "height": 0,
  "prev_block_hash": "GENESIS",
  "cut_at": "2026-08-04T09:00:00Z",
  "entries": [
    {
      "writer": "node1",
      "file": "0-personal/.datacore/events/node1.jsonl",
      "seq": 0,
      "event_hash": "9f2c...a1",
      "hlc": "1785400000000.0000.node1",
      "observed_at": "2026-08-04T09:00:00Z",
      "late": false
    }
  ],
  "root_hash": "b13e...77"
}
```

`height` is the block's position in the chain, monotonic from 0.
`prev_block_hash` is the previous block's `root_hash`, or the literal
string `"GENESIS"` for height 0 — the same genesis convention DIP-0034
uses for a writer file's first event, applied one layer up. Each `entries[]`
item **references** one pool event: `writer`/`file` locate which per-writer
file it lives in, `seq` locates it within that file (DIP-0034's per-writer
monotonic sequence number), `event_hash` is that event's own DIP-0034
`hash` field copied verbatim (not recomputed — it's already
content-derived), `hlc` is copied for convenience so the block can be
scanned by valid-time without re-opening the pool, `observed_at` is when
the sequencer first saw this event (transaction time, defined by this DIP —
see "Bitemporality"), and `late` flags whether `hlc` fell below the
sequencer's settled frontier at observation time. `root_hash` is a hash
over the `entries` list (canonical bytes, same encoding convention as
DIP-0034 events), making the block self-verifying: any change to any entry
changes `root_hash`, which then no longer matches what the next block's
`prev_block_hash` expects.

### Why blocks reference, never copy

A block never contains an event's `payload`. Three reasons, all load-bearing:

1. **Single source of truth.** Copying a payload into a block would create
   a second place the same fact lives — exactly what the through-line of
   this DIP forbids. If a copy and the original could ever diverge (a bug,
   a partial write, a stale cache), there would be no principled way to say
   which one is "the" answer. A reference cannot diverge from what it
   references; it can only be stale or wrong, both of which verification
   (below) catches.
2. **The append-only invariant already durably stores it.** DIP-0034
   Invariant 1 guarantees the pool event is immutable and permanent. A
   block gains nothing by re-storing what's already guaranteed to exist and
   never change.
3. **Blocks stay small.** An installation's pool grows without bound
   (Motivation, Problem 2); a block that only stores small, fixed-shape
   index entries per event stays cheap to write, cheap to verify, and cheap
   to sync across machines via the existing git-based sync path — the
   thing making the chain viable as a *thin* derived index rather than a
   second heavy datastore.

### Snapshots and the O(tail) fold

A **snapshot** at height N (`<space>/.datacore/ledger/snapshots/NNNNNN.json`)
stores the `LedgerState` (DIP-0034's `fold()` output type) that results
from folding exactly the events referenced by blocks `0..N`, in `hlc`
order — i.e. `fold(events_referenced_by(blocks[0..N]))`. Because DIP-0034's
canonical-bytes encoding makes `fold()` byte-for-byte reproducible given
the same input (Invariant 2), any machine holding the same pool events and
the same blocks can recompute the identical snapshot from scratch — a
snapshot is never trusted on its own; it is a cache of a reproducible
computation, subject to the same "verify, don't trust" posture as blocks
(below).

A reader wanting current state loads the newest snapshot it has and
verified, then extends it with only the **tail** — events observed since
that snapshot's height, not yet referenced by any block — instead of
re-folding the entire pool. Because blocks cut on a bounded cadence
(Specification, "Block cadence"), the tail stays bounded regardless of how
large the total pool has grown: O(tail), not O(all events).

This is possible **without weakening DIP-0034 Invariant 2** (pure fold, no
incremental/streaming state logic as the primary model) because `fold()`'s
own semantics already describe a strict left-to-right reduction: events are
applied "strictly in list order," with no event's transition depending on
anything that comes after it (DIP-0034 Specification, "Fold semantics"). A
snapshot is a memoized checkpoint of that same pure reduction at a given
height, not a new incremental algorithm. `fold(events)` over the whole list
and `resume(snapshot_at(N), tail_events)` over just the un-settled tail are
required to produce byte-identical `LedgerState`; a snapshot that fails to
reproduce this equivalence when re-derived from scratch is a bug in this
DIP's implementation, not an accepted variance. This is the same
replayability guarantee DIP-0034 makes for `fold()` itself, extended to
cover its checkpointed form — `fold()` itself is not modified.

### Verification: verify, don't trust

Any machine — the sequencer's own, or any reader's — recomputes: for every
entry in a block, re-derive `event_hash` from its own local copy of the
referenced pool file (via `verify_chain`-style hash recomputation, DIP-0034
Specification, "Signing"), recompute `root_hash` over the entries, and
check `prev_block_hash` against the prior block's `root_hash`. **A block
that doesn't verify is rejected locally and reported** — never silently
accepted, never silently "fixed," never treated as canonical just because
the sequencer produced it.

This is the load-bearing property that keeps the chain from becoming a
second source of truth by accident: a reader who distrusts, or simply
never syncs, the `ledger/blocks/` directory loses *nothing* but
performance. `read_events()` + `fold()` over the raw pool (DIP-0034,
completely unchanged) is always available, always correct, and always the
final word if the chain and the pool ever disagree — the chain is useful
exactly to the extent it verifies against the pool, and not one bit more.

### Bitemporality: valid time, transaction time, and the `late` flag

(Mechanism for design brief §B; motivation for the DIP-0034 amendment,
mechanism lives here as directed.)

Two times are now tracked, with different owners and different guarantees:

- **Valid time** = the event's `hlc` (DIP-0034, unchanged). Records *when
  the event happened*, per its writer's own logical clock. **This remains
  the fold's ordering key** — `read_events()`'s `hlc`-sorted merge and
  `fold()`'s left-to-right application are exactly as DIP-0034 specifies
  them. Causality is preserved: nothing in this DIP re-sorts by anything
  else.
- **Transaction time** = `observed_at`, recorded by the sequencer the first
  time it sees an event (i.e., the first time that event appears in some
  block's `entries[]`). **`observed_at` lives only in the block index
  (this DIP) — never in the DIP-0034 event itself.** Events remain
  immutable and hash-stable exactly as DIP-0034 Invariant 1 requires; the
  append-only guarantee is completely untouched, because nothing about a
  pool event's bytes, hash, or `prev` chain changes when a sequencer
  observes it. This is the entire reason the design works, and is stated
  here explicitly rather than left implicit.

**Finality.** Events at or below the settled height cannot be reordered —
meaning: once a snapshot at height N has been cut and verified, no later
observation of an event whose `hlc` falls below that snapshot's frontier
causes the *already-cut* snapshot at N to be silently regenerated with a
different answer. A late arrival — an event whose `hlc` places it below
the current frontier but which the sequencer is only now observing — is
**admitted, not rejected**: it is included in a later block, its position
in `entries[]` still carries its true `hlc` (so any reader doing a full
on-the-fly fold over the raw pool, unaffected by "settled height," always
sees the true valid-time order regardless of when anything was observed),
and it is **flagged `late: true`** in the block index — visible, auditable,
never silent. Default policy accepts and records every late arrival; a
stricter policy may instead quarantine a late arrival for review before
it's folded into any snapshot (Open Questions).

This is a property of the **derived index**, not of truth: finality never
changes what a from-scratch fold over the pool reports (that's still
DIP-0034's job, and it's always right); it changes only which *cached
snapshots* downstream consumers are entitled to treat as fixed without
re-deriving them.

**Snapshot invalidation (normative, owner decision 2026-08-05).** The
paragraph above says an already-cut snapshot is never *silently* regenerated
with a different answer. That is a guarantee about silence, and on its own it
leaves a hole: a consumer would otherwise be entitled to keep trusting a
snapshot it can prove is stale. The missing rule:

> A block entry flagged `late: true` whose `hlc` falls **below** the frontier
> of snapshot *N* **invalidates snapshot *N* and every snapshot above it**.
> An invalidated snapshot MUST NOT be used as a fold base. The next snapshot
> is recomputed from the most recent still-valid snapshot below the late
> event's `hlc`, or from genesis if none remains.

Consumers therefore have three states rather than two — valid, invalidated,
and absent — and `late: true` is the transition signal. This is cheap because
late arrivals below a settled frontier are rare by construction: they require
an actor to have been out of contact for longer than the block cadence. It is
also the reason `late` is a *flag in the index* rather than a log line: a
consumer must be able to detect invalidation mechanically, from data it
already reads, without consulting an operator.

Note what this does **not** change. The affected events are still ordered by
`hlc`, causality is still preserved, and a from-scratch fold was correct
before the invalidation and remains correct after it. Only the cache is
discarded.

### Degradation: no single point of failure

**Stated prominently, per design intent — this is the property that
preserves the explicit no-single-point-of-failure requirement, and it does
not get buried in an appendix.**

If the sequencer is down — crashed, offline, mid-migration, anything —
**writes continue and on-the-fly fold works exactly as it does today.**
Nothing about DIP-0034's write path or fold path depends on the sequencer
existing, running, or ever having run. The only thing that pauses is
finality: no new blocks are cut, the settled height stops advancing, no new
`observed_at`/`late` classification happens for events written during the
outage (there's nothing to compare against a frontier), and any consumer
that wants the O(tail) fast path falls back to the O(all events) path until
the sequencer resumes or a fallback takes over (below). **Nothing blocks.**
A space that has never run a sequencer at all is in this exact state
permanently, and behaves in every functional respect like a DIP-0034-only
installation (Backwards Compatibility).

### Three roles, separately assigned (owner ruling, 2026-08-04)

Coordination in this design is **three distinct roles**, not one. They may —
and by default should — be held by the same actor, but they MUST remain
separately named and separately failed-over.

| Role | What it does | If it is unavailable |
|---|---|---|
| **Sequencer** | Cuts blocks, records `observed_at`, orders the pool into the canonical chain | **Finality pauses.** Appends, folds, reads and projections all continue on the pool. Benign, and the property this DIP's Degradation section already guarantees. |
| **Arbiter** | Grants claims ([DIP-0034](DIP-0034-event-ledger-substrate.md) `item.grant`) for arbitrated-pool items | **Arbitrated work stops** until the fallback takes over — nothing may execute without a grant. This is an availability dependency, not a delay. |
| **Hub** (transport) | Relays events between actors ahead of git sync | **Not adopted.** See "Transport hub: deferred" below. |

**Why they must not be collapsed into one concept.** The failure modes above
are not merely different in degree; a sequencer outage is invisible to a
working system, while an arbiter outage halts execution. Collapsed, you cannot
fail over one without the other, and — the sharper cost — you cannot tell
which one is broken from the symptom. Keeping them named separately costs one
extra `policy.set` payload and buys diagnosability.

**Selection criteria** (installation-agnostic; this spec assigns nothing):

1. **Highest availability in the roster.** The holder must be reachable
   whenever any other actor is doing work — an intermittently-connected
   workstation is the wrong choice.
2. **Single writer.** The holder's decisions must be totally ordered by
   construction, which per-writer files already guarantee. This is why an
   arbiter needs no consensus: its grants are ordered by the file they land
   in, and a second grant for an already-granted item is a recorded no-op.
3. **Freshest view of the pool.** The holder should be the actor that syncs
   most often, so its ordering decisions are made on the most complete input.

**Recommended default.** An installation's **Chief-of-Staff actor** typically
satisfies all three — it is always-on, it already holds adjacent
responsibilities (merge gatekeeping, the approvals policy of
[DIP-0038](DIP-0038-action-loop-cosign.md)), and it syncs on the tightest
cadence. Assigning both sequencer and arbiter to it is therefore the
recommended default, and it requires **no new component**: the daemon already
runs, and both roles are assigned by data (below), not by code. This is a
recommendation, not a requirement — an installation with a different
availability profile should apply the criteria and choose differently.

**Concentration risk, named.** Assigning both roles to the actor that already
holds merge gatekeeping, approvals and briefing production means one machine
carries five responsibilities. Each degrades gracefully or has a fallback *in
principle*; in practice a fallback that is specified but unset is not a
fallback. Both `policy.set` assignments below MUST carry an explicit
`fallback`, and an installation SHOULD verify the fallback can actually take
over rather than assuming it.

**Transport hub: deferred, with a trigger.** A hub — a daemon receiving and
relaying events between actors ahead of git sync — was evaluated and is **not
adopted**. Sequencing and block-serving are **pull-based**: an actor requests
blocks when it syncs, and an unavailable answer costs it nothing. A hub is
**push-based**: it makes an actor's progress depend on a live network path to
one machine. Since per-writer files are append-only and single-writer, they
already sync without conflict over the existing git transport, so a hub adds a
new dependency to a system that has no correctness problem — it buys latency,
not correctness.

The honest counter-argument is that latency is real: a claim→grant round trip
costs one sync interval per hop. But cheaper remedies come first, and they
already exist in DIP-0034's claim-safety policy — set `owner` at create
(partitioned; no handshake at all) or mark idempotent, cheap work `open: true`
(self-granting). **Trigger for revisiting:** once most work is partitioned or
open, if grant latency is still a *measured* complaint rather than an
anticipated one. Should that trigger ever fire, the answer is
[DIP-0023](DIP-0023-messaging-module.md) — every user *and agent* is already
an ActivityPub actor there, with inbox/outbox endpoints authenticated by
fds-id keypairs and federation by design, which is the hub capability
deferred here without inventing a second transport.
[DIP-0045](DIP-0045-node-protocol.md) proposed exactly such a second
transport and was **withdrawn on 2026-08-05**: each of its four endpoints had
an existing home, including this one. Note in particular that
*projection/verify* — the endpoint that looked most ledger-specific — needs no
network path at all: [DIP-0043](DIP-0043-org-projection.md)'s
`projection.attest` event carries `{height, projector_version,
projection_hash}` into each machine's own writer file, so comparing two
machines is a fold rather than a request. **The ledger is its own comparison
channel.**

### Sequencer role as data

Both roles are assigned by `policy.set`, discriminated by the `policy` field:
`ledger.sequencer` (below) and `ledger.arbiter.default` (same shape, naming
the standing arbiter used when an `item.create` does not specify its own).
An `item.create` that names its own `arbiter` overrides the standing default
for that item, per DIP-0034.

A `policy.set` event names the sequencer, using the same event type
[DIP-0038](DIP-0038-action-loop-cosign.md) uses for co-sign thresholds,
disambiguated by a `policy` discriminator field — mirroring the pattern
DIP-0034 already established for `metric.attest`'s `metric` field
(Specification, "Event schema"):

```jsonc
{
  "policy": "ledger.sequencer",
  "actor": "<always-on actor from the roster>",
  "fallback": "<second actor>",
  "fallback_after_seconds": 3600
}
```

The **current sequencer** for a space is the actor named by the
most-recent-by-`hlc` `policy.set` event whose `payload.policy ==
"ledger.sequencer"`. Unlike `item.claim`'s earliest-wins race semantics
(DIP-0034), this is **latest-wins** — an administrative assignment, the
same semantic DIP-0034 uses for `owner.set` ("administrative ownership
override"), not a race between competing claimants. Consumers of
`policy.set` MUST check `payload.policy` before dispatching, exactly as
`metric.attest` consumers MUST check `payload.metric` — an unrecognized
`policy` value is ignored, never an error, per DIP-0034 Invariant 6
(payload dicts are additive).

### Fallback takeover

If no new block has been observed at the expected cadence for longer than
`fallback_after_seconds`, the named `fallback` actor may begin cutting
blocks itself, continuing the height sequence from `prev_block_hash` set to
the last block it can independently verify. **Takeover requires no
permission and no live coordination** — it is unambiguous purely because
blocks are hash-linked: the fallback only has to correctly identify "the
last block" from the git-synced `ledger/blocks/` directory, which is
exactly the same operation it would perform to produce any other block.

### Fallback drills (owner ruling, 2026-08-04)

A fallback that has never taken over is an untested code path, and the
arbiter's failure mode — work stops — is the one where discovering that at
the wrong moment is expensive. **Fallback capability MUST therefore be
rehearsed, not merely declared.**

The rehearsal is a **read-only drill**, not a real takeover. The fallback
actor does exactly what it would do in a genuine takeover, and then compares
its answer against what the primary actually produced, instead of writing a
block:

- **Sequencer drill.** The fallback independently identifies the last block
  from its own `ledger/blocks/` copy, recomputes the block it *would* cut at
  that height from its own pool copy, and compares to the primary's actual
  block. Equal blocks prove the fallback can produce a valid, chain-continuing
  block from its own data. A mismatch is the finding — it means the two actors
  disagree about pool contents or ordering, which is exactly the condition that
  would produce a fork during a real takeover.
- **Arbiter drill.** The fallback folds the pool and enumerates the items
  currently awaiting a grant, confirming it can identify the same set the
  primary would. This is the arbiter's entire decision input; being able to
  compute it is being able to take over.

Neither drill writes to `events/` on behalf of the primary, cuts a block, or
requires the primary to be unavailable. Both are safe to run against a healthy
system on a schedule.

**Result reporting reuses existing mechanisms rather than adding any.** The
drill emits `metric.attest` with `metric: "ledger.fallback_drill"` — a class
allocated in [DIP-0034](DIP-0034-event-ledger-substrate.md)'s discriminator
table, not a new event type — carrying
`{space, role, primary, fallback, height, ok, mismatch?}`. The drill itself is
declared as a job contract under [DIP-0035](DIP-0035-job-contracts.md), so a
drill that silently stops running is caught by the same verifier that catches
any other silent job failure, and its `on_fail` routing is the existing one.
This is deliberate: a rehearsal mechanism that needs its own monitoring has
merely moved the problem.

**Cadence.** Weekly is sufficient for a steady-state installation. Two
additional triggers are normative: a drill MUST pass **before the first time a
space relies on arbitrated-pool work for anything time-sensitive**, and after
any change to the roster, the sequencer/arbiter assignment, or the ledger
code on either actor.

### Fork detection

Because the sequencer role is singular in data (exactly one actor is named
per the most recent `policy.set`), two blocks legitimately appearing at the
same height with different hashes should never happen under correct
operation. If it does — a fallback took over prematurely while the primary
was still alive, a misconfiguration named two actors as sequencer at once,
or something worse — **this is a hard, loud error.** Chain progression is
refused past that height until a human resolves which block is canonical
(or determines both are re-sends of identical content, in which case there
was no true fork). This is deliberately **not** auto-resolved by any
heuristic ("first writer wins," "longest chain wins," or similar) — any
such heuristic would produce a canonical answer that isn't verifiably
correct without introducing trust assumptions this design doesn't need for
a single-owner, N=1 trust domain, the same reasoning DIP-0034 uses to defer
mandatory signing (`ENG-2026-0729-030`).

### Block cadence and why two sequencers must not run concurrently

Blocks are cut on a **hybrid trigger: a daily wall-clock floor, or whenever
the un-blocked tail exceeds a configured event count — whichever comes
first** (Open Question 1, resolved 2026-08-05). The floor is what keeps quiet
days cheap: one block, one file, and a window wide enough to absorb ordinary
sync jitter so routine out-of-order arrival never registers as `late`. The
volume trigger is what keeps a busy period from accumulating a tail large
enough to make the O(tail) fold meaningfully worse than the O(all events)
fold it replaces — bounding fold cost by *work done* rather than by *time
elapsed*, which is the quantity that actually drives it.

Do not lower the floor below a day to make anything else faster. A shorter
window absorbs less sync jitter and therefore manufactures `late` entries out
of ordinary machine behaviour; and the two things a shorter cadence looks
like it would help are both better served elsewhere. **Drift detection** is
not cadence-bound — [DIP-0043](DIP-0043-org-projection.md) anchors projection
comparison to a writer version vector rather than to a height precisely so
that detection latency is bounded by sync latency rather than by how often
this sequencer runs. **Fork detection** is not cadence-bound either: a fork
requires two concurrent sequencers, which requires a fallback to take over
while the primary is alive, which is governed by `fallback_after_seconds`.
**That value MUST exceed the cadence floor by a clear margin** — otherwise a
sequencer that is merely between cuts looks indistinguishable from one that
has stopped, and the design invites the very fork it detects. Set the
threshold and forks are prevented structurally; shortening blocks only
detects them sooner.

At each cut, the acting sequencer includes every pool event it
has observed — meaning every event present in its local, synced copy of
the pool — that isn't already referenced by an earlier block. Two
sequencers with byte-identical views of the pool at the same cut instant
would deterministically produce byte-identical blocks: determinism here is
a direct consequence of DIP-0034's canonical-bytes encoding applied one
layer up, not a coincidence. But two machines' views of the pool differ in
practice — different sync schedules, one offline, one racing an in-flight
append — even when nominally covering "the same space." Two sequencers
cutting concurrently would therefore almost certainly diverge and fork
(above). This is why the design commits to **exactly one active sequencer
at a time**, enforced as a data fact via `policy.set` rather than a live
mutual-exclusion protocol — the same "ownership as data, no live
coordinator" principle DIP-0034's Owner Decision names as element 5,
applied here to the sequencer role instead of item ownership.

### Worked example

Continuing DIP-0034's worked example (`node1` creates, claims, and completes
`t-042`, three events in `node1.jsonl`): the sequencer (`node1`, self-assigned
via `policy.set`) cuts a block at height 0 referencing all three:

```jsonc
{
  "height": 0,
  "prev_block_hash": "GENESIS",
  "cut_at": "2026-08-04T09:10:00Z",
  "entries": [
    {"writer":"node1","file":"0-personal/.datacore/events/node1.jsonl","seq":0,
     "event_hash":"9f2c...a1","hlc":"1785400000000.0000.server",
     "observed_at":"2026-08-04T09:10:00Z","late":false},
    {"writer":"node1","file":"0-personal/.datacore/events/node1.jsonl","seq":1,
     "event_hash":"3b7e...d4","hlc":"1785400015000.0000.server",
     "observed_at":"2026-08-04T09:10:00Z","late":false},
    {"writer":"node1","file":"0-personal/.datacore/events/node1.jsonl","seq":2,
     "event_hash":"c081...9e","hlc":"1785400600000.0000.server",
     "observed_at":"2026-08-04T09:10:00Z","late":false}
  ],
  "root_hash":"b13e...77"
}
```

The snapshot at height 0 is `fold()` over exactly these three events —
identical to the `LedgerState` in DIP-0034's worked example. Now suppose a
laptop actor `workstation` reconnects a week later with a `item.dismiss` for a
different, unrelated item `t-011`, whose `hlc` places it *before* height
0's cut. Height 0 is not rewritten. The next block, height 1, includes the
`workstation` event with `late: true`:

```jsonc
{"writer":"workstation","file":"0-personal/.datacore/events/workstation.jsonl","seq":4,
 "event_hash":"7ad1...02","hlc":"1784800000000.0000.workstation",
 "observed_at":"2026-08-11T09:10:00Z","late":true}
```

Any reader doing a full on-the-fly fold over the raw pool (DIP-0034,
unaffected by settled height) still sees `t-011`'s dismissal at its true
`hlc` position, exactly where causality puts it. The fast, snapshot-based
path instead sees it appear in height 1's tail, flagged `late` — visible,
not silently absorbed into height 0's already-reported snapshot.

### Changes Required

- **New (unbuilt)**: `.datacore/lib/ledger/chain.py` — block construction,
  append, `prev_block_hash`/`root_hash` computation and verification.
- **New (unbuilt)**: `.datacore/lib/ledger/snapshot.py` — snapshot
  construction (`fold` over referenced events) and `resume` (checkpointed
  continuation, see "Snapshots").
- **New (unbuilt)**: `.datacore/lib/ledger/sequencer.py` — cut-cadence
  loop, fallback-takeover check, fork detection.
- **New (unbuilt, Phase E, deferred)**: `.datacore/lib/ledger/archive.py` —
  segmentation of old blocks/pool ranges into `ledger/archive/`, header-only
  chain retention (Retention, Snapshots and Pruning).
- **New (unbuilt), per space, only where a sequencer has run**:
  `<space>/.datacore/ledger/blocks/`, `<space>/.datacore/ledger/snapshots/`,
  `<space>/.datacore/ledger/archive/` (Phase E only).
- **New (unbuilt) `ledger_cli.py` subcommands**: `cut-block`, `verify-chain`
  (distinct from DIP-0034's existing `verify`, which checks a single
  writer's pool file — this checks the block index), `snapshot`.
- **No changes** to any DIP-0034 file: `hlc.py`, `events.py`, `log.py`,
  `verify.py`, `fold.py`, `index.py` are untouched.

### New Components

- `ledger.chain` — block schema, append (sequencer-only), verify
  (any reader).
- `ledger.snapshot` — snapshot construction and checkpointed `resume`
  (Specification, "Snapshots" — provably equivalent to `fold()`, not a
  replacement for it).
- `ledger.sequencer` — role resolution from `policy.set` (latest-wins),
  cadence loop, fallback-takeover, fork detection.
- `ledger.archive` (Phase E, deferred) — moves old blocks/pool ranges to
  `ledger/archive/` or an external store while retaining a header-only
  hash chain and the covering snapshot; never rewrites or discards data
  (Retention, Snapshots and Pruning).

### Interface Changes

- New per-space directories: `.datacore/ledger/blocks/` (git-tracked —
  single-writer, so it never conflicts; see Security Considerations) and
  `.datacore/ledger/snapshots/` (gitignored, disposable, rebuildable from
  blocks + pool at any time — the same disposable-cache precedent as
  DIP-0034's SQLite index).
- New `ledger_cli.py` subcommands (`cut-block`, `verify-chain`, `snapshot`)
  — additive; every existing subcommand (`append`, `verify`, `items`,
  `balances`) is unmodified.
- `policy.set` gains a second recognized payload family
  (`policy: "ledger.sequencer"`) alongside DIP-0038's cosign-threshold
  family — additive per DIP-0034 Invariant 6.

## Retention, Snapshots and Pruning

Ledger growth is bounded and unremarkable at this installation's actual
scale — worth showing the arithmetic once, explicitly, so nobody
over-engineers a solution to a problem that doesn't exist here.

### The arithmetic

An order-of-magnitude estimate from this installation's actual event
sources, not a measured figure:

| Source | Basis | Events/day |
|---|---|---|
| `metric.attest` (`job.verify`) | ~11 attests/machine/day × 3 machines (workstation, server, executor — DIP-0034 Rationale's "three machines the owner controls") | 33 |
| `item.*` lifecycle | ~30 ledger items/day × ~3 events/item (create, claim, complete — `verify` not always emitted) | 90 |
| `spend.record` | ~1 per executed job, same order as item completions ([DIP-0041](DIP-0041-executor-adapters.md), "goes live end-to-end") | 30 |
| Briefing/approval (`item.create` from [DIP-0037](DIP-0037-grounded-briefings.md), `approval.grant`, `policy.set`) | smaller, occasional rather than per-item | 20 |
| **Total** | | **~173/day** |

`173/day × 365 ≈ 63,000 events/year`. At 300–500 bytes/event — DIP-0034's
canonical JSON line (`seq`, `hlc`, `actor`, `type`, `payload`, `prev`,
`hash`, `sig`) — that's `63,000 × 300–500 bytes ≈ 19–32 MB/year`.

**Conclusion, stated plainly: storage growth is not the problem at
single-user scale.** Tens of megabytes per year is a quantity git already
handles trivially, compounding to a few hundred MB after a decade — nowhere
near a threshold that needs solving now, or plausibly ever, for an N=1
owner, few-machine installation. **The real cost is fold time** — O(all
events), unbounded, forever (Motivation, Problem 2) — and that is exactly
what Snapshots (Specification, above) already exist to solve, independent
of how much storage the pool and chain consume.

### Why this isn't a blockchain-scale problem

Public blockchains have a real growth problem because they are **global**
(every participant stores the same history), **adversarial** (verification
must be possible without trusting any single party, so redundancy is the
whole point), and **replicate everything to everyone** (no participant can
opt out of holding data and still trust the chain). None of those
properties hold here: this is a single-owner, few-machine, non-adversarial
system (DIP-0034 Rationale: "at the current trust domain, N=1 owner, three
machines the owner controls"), where one verified local copy is sufficient
and nothing needs replicating to parties who don't already have it via the
existing git sync. Do not import blockchain-scale storage engineering
(pruned nodes, state rent, sharding) into a system that does not have a
blockchain-scale growth problem.

### Three mechanisms, in escalation order

1. **Snapshots** (Specification, "Snapshots and the O(tail) fold" —
   already core to this design, not new here). Decouples read cost from
   history length: `fold()` cost becomes O(tail) regardless of how large
   the pool or chain has grown. This alone answers the actual problem
   (fold time), independent of storage size.
2. **Segmentation/archival**, for the point — not projected to arrive for
   years, per the arithmetic above — where resident storage, not fold
   time, becomes inconvenient. Once a height's snapshot has been durably
   cut and verified, the raw material below it is no longer needed for any
   routine read: the snapshot already summarizes it correctly by
   construction. Old blocks, and optionally the pool event ranges they
   reference, may move to `<space>/.datacore/ledger/archive/` (a local
   cold directory) or an external store, while the routinely-synced local
   copy retains only:
   - the **snapshot** at or above the archive frontier, so O(tail) fold
     never needs archived data for any current read; and
   - a **header-only chain** for every archived height —
     `{height, prev_block_hash, root_hash, cut_at}` — enough to keep the
     hash-linked sequence intact and unbroken from genesis to the current
     tip, without keeping full `entries[]` content resident.

   Verifiability survives archival because the hashes never move:
   `root_hash` for an archived height still exists in its header, still
   chains to the next block's `prev_block_hash`, and still matches what
   would be recomputed if the archived content were retrieved. Archival
   changes *where* data lives and *how quickly* it can be re-verified
   (payloads become retrievable, not resident — a deliberate
   latency/space tradeoff), never *whether* it can be verified.
3. **What is forbidden.** Nothing in this DIP ever rewrites, recomputes, or
   compacts a block's or event's content **in place** to save space.
   Moving data — to `ledger/archive/`, to an external store, to cold
   storage — is permitted, and is exactly what mechanism 2 does. Mutating
   or discarding data — collapsing multiple blocks into one with a
   recomputed hash, deleting a pool event range without preserving it
   somewhere retrievable, or any operation that would change what a
   from-scratch verification recomputes — is forbidden. This is a
   **normative constraint**, not a preference: it mirrors, one layer up,
   DIP-0034 Invariant 1 (events are append-only and immutable) applied to
   the block index, and the audit property this entire DIP exists to
   provide depends on it holding without exception.

### The disposable index is exempt, by construction

DIP-0034's `ledger.index` (the disposable SQLite projection,
`<space>/.datacore/state/ledger/index.db`) holds only **current state**,
not history — it is rebuilt from a fold, not accumulated event-by-event —
so it does not grow with the pool or chain at all, regardless of how many
years of history exist behind it. It is already exempt from everything in
this section, unaffected by any retention or archival policy defined here.

## Rationale

**Why not make the chain the write path?** That would reintroduce exactly
the coordination cost and single point of failure DIP-0034's per-writer
pool design exists to remove (DIP-0034 Rationale: "why per-writer files
instead of one shared append-only file?", and the git-push-as-lock failure
mode, `ENG-2026-0423-001`, that originally motivated the whole substrate).
Writes must keep working when the sequencer is down (Specification,
"Degradation"); that is only possible if the chain is strictly downstream
of writes, never upstream of or gating them.

**Why order by valid time (`hlc`) and not arrival time (`observed_at`)?**
Ordering by arrival time inverts causality. Concretely: an offline machine
dismisses an item on Tuesday; a user reopens it Wednesday, having no idea
the dismissal exists yet; the offline laptop finally syncs Friday. Under
arrival-time ordering, Friday's arriving Tuesday-dismissal would be applied
*after* Wednesday's reopen and would win — silently undoing a deliberate,
later, causally-informed decision with a stale one that only happens to
have shown up last. `hlc`-based valid-time ordering (unchanged from
DIP-0034) gets this right by construction: the dismissal is folded in at
its true causal position, before the reopen, and the reopen correctly
wins. This DIP's entire bitemporal design exists to add finality *on top
of* that correct ordering, never to replace it.

**Why references, never payload copies, in a block?** See Specification,
"Why blocks reference, never copy" — single source of truth, the
append-only invariant already durably stores the payload, and blocks stay
small regardless of pool size.

### Alternatives considered

- **Making the chain the write path** — rejected. Reintroduces a live
  coordinator on every write, which is precisely the single point of
  failure and the git-lock failure genre (`ENG-2026-0423-001`) DIP-0034's
  per-writer file design was built to eliminate. Writes must survive
  sequencer downtime; only a strictly-downstream, derived chain allows
  that.
- **Ordering by arrival time (`observed_at`) instead of valid time
  (`hlc`)** — rejected. Inverts causality; see Rationale above for the
  concrete Tuesday/Wednesday/Friday counterexample. `hlc` remains the
  fold's ordering key, unconditionally.
- **Copying event payloads into blocks** — rejected. Creates a second
  place a payload could diverge from the pool, defeating the "derived,
  never a second source of truth" through-line this entire DIP is built
  around, and bloats blocks with data DIP-0034's append-only pool already
  stores durably. See Specification, "Why blocks reference, never copy."
- **A real multi-sequencer consensus/voting protocol now** — rejected, per
  the original owner direction still in force (`ENG-2026-0729-016`, "do NOT
  build a blockchain now," cited in DIP-0034's Owner Decision). A
  single-sequencer, verify-don't-trust index is the smallest structure that
  buys finality and bounded fold cost without a quorum protocol nobody yet
  needs; DIP-0034's own Open Question 3 already defers exactly this until
  sequencer downtime creates real operational pain.
- **Heuristic fork resolution ("longest chain wins," "first writer wins")**
  — rejected. Any such heuristic manufactures a canonical answer that isn't
  verifiably correct without trust assumptions this design doesn't need at
  the current N=1 trust domain. A fork is a hard, loud error instead — see
  Specification, "Fork detection," and the same reasoning DIP-0034 uses to
  defer mandatory signing.
- **Incremental/streaming `fold()` as the primary state model** (instead of
  a pure fold plus optional checkpointed snapshots) — already rejected by
  DIP-0034 (Rationale, "why a pure fold rather than incremental/streaming
  state updates?"), and not revisited here. This DIP's snapshot mechanism
  is deliberately framed as a checkpoint of the same pure reduction, not a
  competing incremental model — see Specification, "Snapshots."

## Backwards Compatibility

Purely additive; nothing about the existing write path or event schema
changes.

- **No change to the write path.** `EventLog.append`, per-writer `.jsonl`
  files, `fcntl`-based locking — all exactly as DIP-0034 specifies. DIP-0034
  Invariant 1 (append-only) and Invariant 2 (deterministic pure fold) are
  unmodified, unextended in scope, and unweakened by anything in this DIP.
- **No change to the event schema.** No new `EVENT_TYPES`. No new required
  payload field on any existing type. `policy.set` gains a second
  recognized payload family under DIP-0034's pre-existing payload-additive
  invariant (Invariant 6) — not a schema change, the same mechanism
  `metric.attest`'s discriminator table already uses.
- **Systems that ignore blocks behave exactly as they do today.** A space
  that never runs a sequencer never creates `.datacore/ledger/` at all, and
  behaves in every functional respect like a DIP-0034-only installation:
  fold-on-the-fly, no settled height, no `late` flag, nothing to verify.
  This is the same get-out DIP-0034 defines one layer down for a space with
  no `.datacore/events/` directory.
- **A consumer that doesn't know this DIP exists can still read a space
  that has a chain.** It simply ignores `.datacore/ledger/` and folds the
  pool directly, at full O(all events) cost, exactly as before this DIP
  existed. There is no correctness hazard from ignoring the chain — only a
  performance one.
- Adopting the chain for a coordination path this DIP doesn't already cover
  (e.g. gating some other write on settled height) is explicitly out of
  scope here and would need its own ratified DIP, per the same boundary
  discipline DIP-0034 applies to migrating nightshift's claiming mechanism.

## Security Considerations

- **Verify-don't-trust is the whole model.** Sequencer output is a hint,
  never an authority, until independently reverified against a reader's own
  pool copy. This holds regardless of whether DIP-0034 signing is on or
  off — this DIP does not change or depend on the signing trust boundary
  (`ENG-2026-0729-030`) at all.
- **A compromised or malfunctioning sequencer** can, at worst, produce a
  block that fails local verification (rejected, reported) or simply stop
  producing blocks (finality pauses; Specification, "Degradation"). It
  cannot forge canonical state without also forging the underlying pool
  events, and pool-event attribution is exactly DIP-0034's existing,
  unchanged trust boundary — not a new problem this DIP introduces or
  attempts to solve differently.
- **Fork as a tamper/misconfiguration signal.** Any second block at a given
  height is treated as adversarial-or-broken by default and never silently
  reconciled (Specification, "Fork detection"). This reduces the value of
  "just publish a favorable second block" as an attack: doing so halts
  chain progression rather than winning it.
- **Public-repo constraint.** Blocks contain only event hashes, `hlc`
  strings, file locators, and timestamps — no payloads, no secrets — and
  are safe to commit to a public-adjacent repo under the same posture
  DIP-0034 establishes for its public key registry. Snapshots (materialized
  `LedgerState`) may contain the same fields `fold()` already exposes via
  `ledger_cli.py items`/`balances` today; they are gitignored here as
  disposable local cache, not because of any new sensitivity this DIP
  introduces.
- **Archival never weakens the audit property.** Retention, Snapshots and
  Pruning states this as a normative constraint: moving data to
  `ledger/archive/` or an external store is permitted; rewriting,
  recomputing, or compacting a block's or event's content in place is
  forbidden, without exception. Any process implementing archival that
  discards data instead of relocating it, or that recomputes a hash to
  make archived content "fit" a smaller representation, violates this
  DIP — the audit and finality properties this DIP exists to provide
  depend on every hash in the chain remaining independently
  re-derivable from the retrievable original, forever.
- **Not an access-control system**, exactly as DIP-0034 states of itself:
  this DIP detects and surfaces sync anomalies and provides finality; it
  does not restrict who may write to the pool or who may hold the
  sequencer role beyond "whoever the most recent `policy.set` names" — a
  process-boundary control, not cryptographic authorization, identical in
  kind to DIP-0038's `policy.set`-gated cosign trust boundary.

## Implementation

**Nothing specified in this DIP is built yet.** No file under
`.datacore/lib/ledger/` implements `chain.py`, `snapshot.py`, or
`sequencer.py`; no `ledger_cli.py` subcommand for `cut-block`,
`verify-chain`, or `snapshot` exists; no space has a
`.datacore/ledger/blocks/` or `.datacore/ledger/snapshots/` directory. This
DIP is the design only, ratified per Owner Decision above, awaiting
implementation triggers rather than a schedule.

### Reference Implementation

None. This is a Draft specification DIP.

### Rollout Plan

Trigger-based, not date-based, following the same discipline DIP-0034 uses
for its own Open Questions:

- **Phase A — chain substrate** (trigger: either Motivation problem is
  actually observed in a running installation — a retroactive-insertion
  incident recurs, or fold cost measurably becomes a bottleneck on a real
  `ledger_cli.py` query — not built speculatively ahead of either). Build
  `ledger.chain` (block append/verify) and sequencer role assignment via
  `policy.set`.
- **Phase B — snapshots** (trigger: Phase A's chain has been stable across
  enough consecutive cuts to trust checkpointing it). Build
  `ledger.snapshot` and wire the O(tail) fast path into `ledger_cli.py`.
- **Phase C — the `late` flag, end-to-end** (trigger: a real late arrival
  occurs in practice — most plausibly [DIP-0043](DIP-0043-org-projection.md)'s
  genesis import, whose valid-time fallback ladder is likely to backfill
  events with `hlc`s below any already-settled frontier — whichever comes
  first). Wire `observed_at`/`late` classification into the sequencer's cut
  loop.
- **Phase D — fallback takeover and fork detection, validated against a
  real incident** (trigger: the first actual sequencer outage, not a unit
  test). Confirm takeover and fork detection behave as specified under real
  conditions before relying on them operationally.
- **Phase E — segmentation/archival** (trigger: resident pool/chain storage
  actually becomes inconvenient — not projected to occur for years at this
  installation's scale, per Retention, Snapshots and Pruning's arithmetic;
  Snapshots alone, from Phase B, remain sufficient for fold-time cost
  indefinitely regardless of whether Phase E ever fires).

Before Phase A: per the guardrail this installation already applies to
every new system ("what is the simplest version that solves the actual
problem?"), standing up a sequencer at all is not justified until one of
the two Motivation problems has actually been observed — this DIP
specifies the design now, while it's fresh from the ratifying conversation,
precisely so it doesn't need to be re-derived under pressure once the
trigger fires.

## Open Questions

1. **Block cadence value — RESOLVED (2026-08-05, owner decision: daily).**
   One block per day. The reasoning is recorded because the obvious
   alternative — tuning cadence to reduce late arrivals — does not work:
   an actor may be offline for days, so **no cadence eliminates lateness**,
   and choosing a short one to chase that goal buys nothing while producing
   more blocks, more files in git, and more `late` flags to triage. Cadence
   is therefore chosen for read cost alone, and read cost is not yet a real
   problem — at this design's realistic event volume a from-scratch fold
   stays inexpensive for years, so snapshots are a bounded-cost guarantee
   rather than an urgent optimisation. Daily also matches the system's
   existing rhythm (overnight sync, morning briefing) and is legible to a
   human: *yesterday is settled*. **Consequence, stated so it is not
   rediscovered painfully:** a daily cadence makes settlement-gating
   unusable as a precondition for action — no actor can wait up to 24 hours
   to begin work — which is why Open Question 10 resolves the way it does.
   **Hybrid trigger (added same day):** daily is the *floor*, not the only
   trigger — a block is also cut whenever the un-blocked tail exceeds a
   configured event count, so fold cost is bounded by work done rather than
   by time elapsed. The specific count is left to implementation experience;
   what is normative is that both triggers exist and that the floor is not
   lowered below a day (see "Block cadence" for why, and for the constraint
   this places on `fallback_after_seconds`). Revisit only if fold cost
   becomes measurable, not on a schedule.
2. **Archive-frontier threshold.** Retention, Snapshots and Pruning
   specifies the *mechanism* (snapshots for read cost, archival for
   resident storage, never in-place rewriting) but not the specific
   trigger — how old, or how far below the settled height, a block and its
   referenced pool ranges must be before they're eligible to move to
   `ledger/archive/`. Given the arithmetic in that section (tens of MB/year
   at this installation's actual scale), this is not urgent to resolve and
   is left for Phase A/B implementation experience.
3. **Verification enforced at read time vs. audited periodically.** Should
   every fast-path read reverify the relevant block chain before trusting
   its snapshot (maximally safe, adds latency to every read), or should
   verification run on a schedule (`verify-chain` as a periodic job,
   trusting the fast path within some staleness bound between audits)? This
   is a real cost/safety tradeoff, not resolved by this DIP.
4. **Fallback depth / quorum beyond a single named fallback.** This DIP
   specifies one fallback actor with a takeover timer; it does not specify
   what happens if the fallback is also unavailable, or whether a chain of
   fallbacks is ever justified. Mirrors DIP-0034's own Open Question 3
   ("sequencer replacement / quorum triggers"), deferred there and still
   deferred here — trigger-based (an actual double-outage), not scheduled.
5. **Late-arrival policy: accept-and-record vs. quarantine.** Specification
   states the default (accept and record, `late: true`) and names a
   stricter alternative (quarantine for review before folding) as
   available but unspecified. Which should be the actual default for a
   given deployment, and what does "review" concretely mean operationally,
   is not decided here.

9. **Arbiter fallback must be exercised, not just declared — RESOLVED
   (2026-08-04, owner ruling: yes).** Takeover capability MUST be rehearsed.
   The mechanism is specified in "Fallback drills" above: a read-only drill in
   which the fallback computes what it would produce and compares against what
   the primary actually produced, reported as `metric.attest` with
   `metric: "ledger.fallback_drill"` and scheduled as a DIP-0035 job contract
   so a drill that stops running is itself caught. Weekly cadence, plus two
   normative triggers — before any space relies on arbitrated work for
   something time-sensitive, and after any change to the roster, the role
   assignment, or the ledger code on either actor.
10. **Does the arbiter need its own finality?** A grant is an ordinary pool
   event and is therefore subject to the same provisional-until-settled status
   as everything else. Open: whether an executor should require its grant to be
   *below the settled height* before acting, or whether observing the grant in
   the pool is sufficient. The permissive answer is almost certainly right at
   N=1 owner, but it should be a decision rather than an omission. **Trigger:**
   before any grant authorizes a side-effecting action under
   [DIP-0038](DIP-0038-action-loop-cosign.md).

## References

- `.datacore/dip-review/DESIGN-BRIEF-v2.1.md` — Section C, the binding
  design brief this DIP implements; Section B, the bitemporality
  requirement this DIP's mechanism answers. Ratified in conversation
  2026-08-03/04.
- [DIP-0034](DIP-0034-event-ledger-substrate.md) — Event Ledger Substrate.
  Hard dependency: pool, `hlc`, `fold()`, `EVENT_TYPES`, all invariants,
  all unmodified by this DIP.
- [DIP-0038](DIP-0038-action-loop-cosign.md) — Action Loop & Co-sign. First
  consumer of `policy.set`; this DIP is the second, disambiguated by the
  `policy` payload discriminator.
- [DIP-0043](DIP-0043-org-projection.md) — Org Projection &
  Genesis Import. Drafted alongside this DIP from the same design-brief
  conversation; its genesis import is named here as a Rollout Plan trigger
  for the `late` flag (Phase C).
- [DIP-0011](DIP-0011-nightshift-module.md) — Nightshift module; named only
  as a plausible sequencer/fallback host, no live integration.
- `ENG-2026-0729-016` — the original "do NOT build a blockchain now" owner
  direction (cited in DIP-0034's Owner Decision) this DIP stays inside the
  spirit of: single-sequencer, verify-don't-trust, not distributed
  consensus.
- `ENG-2026-0727-004` — workstation↔server sync topology; the concrete scenario
  motivating Motivation Problem 1 (retroactive insertion) and the worked
  example's late-arrival illustration.
- `ENG-2026-0423-001` — nightshift git-lock silent failure; cited again
  here (via DIP-0034) as the reason the chain must never become the write
  path (Rationale).
