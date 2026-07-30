# DIP-0034: Event Ledger Substrate

| Field | Value |
|-------|-------|
| **DIP** | 0034 |
| **Title** | Event Ledger Substrate |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Draft |
| **Created** | 2026-07-30 |
| **Updated** | 2026-07-30 |
| **Tags** | `ledger`, `events`, `hash-chain`, `hlc`, `signing`, `datacore-v2` |
| **Affects** | `.datacore/lib/ledger/` (`hlc.py`, `events.py`, `log.py`, `verify.py`, `fold.py`, `index.py`), `.datacore/lib/ledger_cli.py`, `<space>/.datacore/events/`, `~/.datacore/keys/`, `.datacore/keys/registry.yaml` |
| **Specs** | `.datacore/lib/ledger/*.py`, `.datacore/lib/ledger_cli.py` |
| **Agents** | any agent that creates, claims, completes, or verifies a task; any process that spends budget on an agent's behalf |
| **Renumbered from** | DIP-0033 (claimed by a parallel session for "Delivery Verification & Smoke Scenarios" before this DIP landed) |
| **Relates to** | ENG-2026-0729-016 (ledger-mindset direction), ENG-2026-0729-030 (signing opt-in amendment), ENG-2026-0727-004 (Mac↔box sync failure genre), ENG-2026-0423-001 (nightshift git-lock silent failure), DIP-0011 (Nightshift), DIP-0018 (Credential Management) |

## Summary

Introduces an **append-only, per-writer, hash-chained event log** as the
system-of-record substrate for task/ownership/spend state across Datacore
spaces — replacing ad-hoc mutation of shared files (org headings, JSON state
files, git-as-lock) with events that are cheap to write, safe to write
concurrently, mechanically verifiable, and deterministically foldable into
current state. Signing is designed in from day one (every event carries a
`sig` field and a documented signing contract) but is **opt-in** at the MVP
stage: unsigned operation is the default, and per-writer file attribution is
the trust model until a real multi-party trust boundary appears. This DIP
covers Phase 1 only: the `ledger` package (`hlc`, `events`, `log`, `verify`,
`fold`, `index`) and the `ledger_cli.py` operator surface. Job contracts,
config plane, grounded briefings, the action loop/co-sign policy, server-first
artifacts, agent consolidation, and executor adapters are follow-on DIPs
(0035–0041) that build on this substrate.

## Motivation

### Problem: shared mutable state is the wrong substrate for multi-writer coordination

Datacore's existing coordination primitives — org-mode files mutated in
place, JSON state files rewritten wholesale, `git push` used as a distributed
lock — were built for a single writer at a time and degrade in
well-documented, recurring ways once more than one process (Mac, box,
nightshift, multiple agents) touches the same state:

- **Duplicate resurrection / ID-conflict churn** (`ENG-2026-0727-004`): the
  Mac and the box are separate working copies of the same git remotes,
  syncing on different schedules. A stale local capture can re-add entries a
  prior sync already routed elsewhere, and because both sides mint their own
  IDs for org headings on read, the same logical task ends up under two
  different IDs on the two machines — every sync then conflicts on pure
  metadata, with no principled way to tell "the same task, seen twice" from
  "two different tasks." Mutable shared files have no concept of an
  immutable, uniquely-identified event; identity is inferred from content on
  every read, and that inference breaks under concurrent, offline-tolerant
  writers.
- **Git-lock silent failure** (`ENG-2026-0423-001`): nightshift used `git
  push` as its task-claiming lock. When a space repo was in a broken git
  state (stuck rebase, detached HEAD, missing upstream tracking), claims
  failed silently and the run reported "Complete! 0 tasks, 0 errors" —
  indistinguishable from a genuinely empty queue, and undetected for three
  days. The lock primitive (a git ref) was borrowed from a mechanism designed
  for a different purpose (code merge), and its failure mode was invisible
  because nothing *recorded the attempt* independent of the lock succeeding.

Both failures share a root cause: **there is no durable, append-only record
of "what was attempted and by whom" that survives independently of the
mutable projection (the org file, the JSON blob, the git ref) the write was
trying to update.** When the projection and the attempt-log are the same
artifact, a torn write, a race, or a broken lock corrupts or hides the only
copy of what happened.

### Use cases

1. **Concurrent, offline-tolerant task coordination** — Mac, box, and
   nightshift workers can each append task lifecycle events (create, claim,
   release, complete, verify, dismiss) to their own file without contending
   for a shared write path; a deterministic fold reconciles ownership after
   the fact instead of requiring a live lock at write time.
2. **Mechanical auditability** — "did the box actually attempt this task, and
   what happened?" is answerable by reading an append-only, hash-chained file
   — no dependence on a git ref having succeeded, a JSON file not having been
   clobbered by a concurrent writer, or a cron log line having survived.
3. **Shadow accounting** — `spend.record` events let per-actor/per-task cost
   be metered against notional budgets (observe before enforcing), a
   prerequisite named directly in the ledger-mindset direction
   (`ENG-2026-0729-016`, item 3).
4. **A substrate the later v2 phases build on** — job verification
   (`metric.attest`), content-addressed artifacts (`artifact.attest`), and
   human co-sign for side-effecting actions (`policy.set`,
   `task.create.payload.effects[]`) all need an event log with these
   properties; building it once here, correctly, avoids six follow-on DIPs
   each re-solving append-only/attribution/idempotency from scratch.

## Current Workaround (pre-DIP)

- Task state lives in org-mode headings (`TODO`/`NEXT`/`DONE`, `:PROPERTIES:`)
  mutated in place by whichever process reads them, with IDs assigned
  independently by each reader (`adapters/org.py` on both Mac and box).
- Nightshift's task claim is a `git push`: success means "I have the lock,"
  but a broken git state fails that push silently with no independent record
  that a claim was even attempted (`ENG-2026-0423-001`).
- Recovery from a duplicate/ID-conflict is a manual or best-effort scripted
  reconciliation (`inbox_dedup.py`, `org_resolve_id_conflicts.py`) run after
  the fact, against files that no longer distinguish "the same task twice"
  from "two different tasks" once IDs have diverged.
- Spend/cost is not metered at all; there is no per-actor accounting.

This workaround has no durable record of intent independent of the mutable
projection, so every one of the above failure classes recurs whenever two
writers touch overlapping state without a live, always-available lock.

## Owner Decision (folded into this DIP)

The direction (`ENG-2026-0729-016`, user decision 2026-07-29): **do not build
a blockchain now** — adopt the ledger *mindset* in the current Datacore idiom,
upgrade-ready for a real chain later. Six elements adopted now: (1) per-agent
keypairs + signed, hash-chained, append-only per-writer event logs
(attestation without consensus — this DIP); (2) verification contracts
declared at task creation (Phase 2 / DIP-0035); (3) shadow accounting (spend
events defined here, metering enforced later); (4) human co-sign policy for
side-effecting actions (Phase 5 / DIP-0038); (5) ownership-as-data for task
coordination, no live coordinator (this DIP's fold semantics); (6)
content-addressed artifacts by hash (`artifact.attest`, this DIP's schema;
consumers in Phase 6 / DIP-0039).

**Signing amendment** (`ENG-2026-0729-030`, user ruling 2026-07-30, amends
the "signatures from day one" invariant below): the **signature field and the
canonical-bytes/hash-chain schema** are present from day one — this shape is
effectively un-retrofittable once events exist — but **actual signing is
opt-in**. MVP runs unsigned (`sig=""`); `ensure_keypair` is never called on
the default path (no key material or registry files are touched); signing
switches on via `DATACORE_LEDGER_SIGN=1` (or `EventLog(..., sign=True)`).
`verify_chain` checks a signature only on events that carry one; `strict=True`
flags any unsigned event as an error, for deployments where signing has been
switched on system-wide and every event is expected to carry one. Rationale:
at the current N=1 trust domain (one owner, per-writer files already
attribute events to their writer by convention), key distribution and
rotation across three machines is the real cost, and it deserves a trigger —
foreign agents joining the ledger, or an external/enterprise audit-trail
requirement — not a default. `keys.py` (Ed25519 keypairs, sign/verify, public
registry) is built and tested but dormant until that trigger fires.

## Specification

### Event schema

Every event is one canonical-JSON line in a per-writer `.jsonl` file:

```
{
  "seq":     <int>,      # 0-based, monotonic, no gaps within one writer file
  "hlc":     <str>,      # hybrid logical clock stamp, see below
  "actor":   <str>,      # writer identity: agent/host/human id
  "type":    <str>,      # one of the 11 EVENT_TYPES below
  "payload": <dict>,     # type-specific fields
  "prev":    <str>,      # hash of the preceding event in this writer's file,
                         # or the literal string "GENESIS" for the first event
  "hash":    <str>,      # sha256 hex digest of {seq,hlc,actor,type,payload,prev}
                         # over its canonical byte encoding
  "sig":     <str>       # Ed25519 signature hex over the same canonical bytes,
                         # or "" when signing is off (the MVP default)
}
```

Canonical bytes are `json.dumps(d, sort_keys=True, separators=(",", ":"),
ensure_ascii=True)` — deterministic key order and no incidental whitespace, so
the same logical event always hashes (and, when signing is on, signs) to the
same bytes regardless of which process constructed it. `hash` covers `prev`,
which is what turns the flat per-writer list into a **hash chain**: mutating
any earlier event changes its hash, which then no longer matches the `prev`
recorded by the event after it — tampering with history is detectable without
needing a signature.

**The 11 `EVENT_TYPES`:**

| Event type | Purpose |
|---|---|
| `task.create` | Introduce a task (`id`, `title`, optional `owner`) |
| `task.claim` | An actor takes ownership of a `created` task |
| `task.release` | An owner un-claims a `claimed` task back to `created` |
| `task.complete` | The claiming owner marks work done |
| `task.verify` | A completed task is confirmed (mechanical check or panel, DIP-0035) |
| `task.dismiss` | Terminally close a task — no later event can revive it |
| `owner.set` | Administrative ownership override |
| `spend.record` | Meter cost (`cents`) against an actor — shadow accounting |
| `metric.attest` | Record a mechanical verification outcome (DIP-0035's `job_verify.py`) |
| `artifact.attest` | Content-address an artifact by hash (DIP-0039) |
| `policy.set` | Change a co-sign/approval threshold (DIP-0038) |

Only `task.create` … `task.dismiss`, `owner.set`, and `spend.record` have
fold-time handlers in Phase 1 (below); `metric.attest`, `artifact.attest`, and
`policy.set` are accepted event types with reserved semantics for the DIPs
that consume them (0035, 0039, 0038) — Phase 1's `fold()` ignores them
without erroring, by design (forward-compatible schema, narrow current
behavior).

### Hybrid logical clock (HLC)

`hlc.tick(actor, last=None) -> str` returns a sortable stamp
`"{physical_ms:013d}.{counter:04d}.{actor}"`. Per actor, it is monotonic:
given the previous stamp, if wall-clock time has advanced past it the new
stamp uses the current time with counter `0`; otherwise it holds the prior
physical time and increments the counter. This gives:

- **Global sortability**: concatenating events from every writer and sorting
  by `hlc` string produces a total, deterministic cross-writer order —
  string comparison suffices because physical time is zero-padded and the
  counter is zero-padded, both fixed-width.
- **No regressions**: a writer's own stamps never go backwards even if the
  system clock does (NTP adjustment, VM pause) — the counter absorbs it.
- **No coordination required**: computing the next stamp needs only the
  writer's own last stamp, not a round-trip to any other writer or a central
  authority — a hybrid logical clock, not a physical one, is what makes
  per-writer files viable without a sequencer for ordering purposes (a
  sequencer may still exist for other reasons — see Upgrade Path).

### Per-writer files

Each actor owns exactly one file: `<space_dir>/.datacore/events/<actor>.jsonl`
— e.g. `0-personal/.datacore/events/mac.jsonl`,
`0-personal/.datacore/events/box.jsonl`. Only the actor that owns a file ever
appends to it; multiple *processes* for that same actor can race to append,
so an exclusive `fcntl.flock` around the read-tail + compute-next + write
critical section serializes them (per `ENG-2026-0304-027` — the same
lock-around-shared-mutable-state pattern used elsewhere in Datacore for
concurrent JSON writers). A crash or concurrent flush can leave a file's
**final** line torn (incomplete); that is treated as an in-flight write, not
corruption — `append()` truncates it away under the lock, and `read_events()`
skips it silently. A malformed line **anywhere else** in the file cannot be
explained by an in-flight write and raises `CorruptLogError` naming the file
and 1-based line number — real corruption is reported loudly, never silently
dropped.

`read_events(space_dir)` merges every writer's file for a space and returns
all events sorted by `hlc` ascending — this is the cross-writer serialization
order the fold consumes. It is read-only: no lock, no mutation.

### Fold semantics

`fold(events) -> LedgerState` is a **pure function**: no clock reads, no
randomness, no I/O; the same input list always produces an equal
`LedgerState`, and it never mutates its input. `LedgerState` holds
`tasks: dict[id, TaskState]`, `spend: dict[actor, cents]`, and
`orphans: list[str]`.

Because events arrive already `hlc`-sorted and `fold()` trusts that ordering
completely (it does not re-sort), **"earliest HLC wins"** for competing
operations — e.g. two actors racing to claim the same task — falls out for
free: the fold applies events strictly in list order, the first event to
satisfy a transition's precondition wins, and every later one that no longer
satisfies it becomes a recorded no-op in that task's `history`, not a raised
error and not a silently dropped event.

Task lifecycle rules, each independently load-bearing:

- **`task.release` means "un-claim," never "un-complete."** It is legal only
  when the *event's actor is the current owner* **and** the task's status is
  exactly `claimed`. A release against a `created`, `completed`, or `verified`
  task is a no-op naming the blocking status — it never silently regresses a
  completed/verified task back to `created`. Ownership is checked before
  status: a non-owner's release is always "not owner," regardless of status.
- **`task.dismiss` is terminal.** Once a task's status is `dismissed`, every
  later event addressed to that task id — including the `owner.set`
  administrative override — is a history no-op. Nothing can revive a
  dismissed task. (This is the fold-level guarantee Phase 5/DIP-0038's
  "a dismissed item never resurfaces" acceptance test relies on.)
- **Orphans, not phantom tasks.** An event that references a task id with no
  prior `task.create` (a claim that arrives before its create, or one whose
  create never arrives) is never fabricated into a task entry. It is
  recorded in `LedgerState.orphans` instead, so diagnostics can see it
  without the fold ever inventing state that wasn't actually created.
- **`spend.record`** simply accumulates `payload["cents"]` into
  `state.spend[event.actor]` — no task association, pure per-actor
  accounting (the shadow-accounting substrate, `ENG-2026-0729-016` item 3).

`ledger.index` builds a disposable SQLite projection
(`<space>/.datacore/state/ledger/index.db`, gitignored) over a folded
`LedgerState` purely for cheap ad-hoc querying (`tasks_by(status=, owner=)`,
`spend_by_actor()`); it is never a source of truth and is always safe to
delete and rebuild from the event log by re-running `fold()` + `build_index()`.

### Amendment: Poison-Event Defense (final-review wave, 2026-07-30)

`fold()` KeyError'd on two payload shapes, both empirically confirmed via
`ledger_cli`: a `task.*`-family event missing `"id"` (or carrying a
non-string/empty one), and `spend.record` with a missing, non-`int`,
`bool`, or negative `"cents"`. Because `fold()` is a substrate primitive
every space depends on, a single poisoned event line was enough to brick
`ledger_cli tasks`/`balances` for the whole space with an unhandled
traceback — the opposite of the "mechanically auditable, never silently
corrupting" posture this DIP commits to.

Landed this wave:

- A `task.*` event without a non-empty string `"id"` is routed to
  `LedgerState.orphans` as `"{hlc} {type} -"` instead of being looked up
  (`KeyError`) or fabricated into task state — this makes the pre-existing
  `.get("id", "?")` fallback in `_orphan` actually reachable for the first
  time (a missing/invalid id used to `KeyError` before ever reaching it).
- `spend.record` with an invalid `"cents"` (missing, non-`int`, `bool` —
  Python's `bool` is an `int` subclass — or negative) is skipped entirely
  (no balance mutation) and recorded as an orphan
  `"{hlc} spend.record invalid"`.
- The negative-`cents` rejection is the **substrate-side half of the
  ledger's conservation floor**: spend only ever accumulates upward; it
  can never be pushed backwards by a single poisoned event, independent of
  whatever policy-side guard (DIP-0038) sits above it.
- `fold()` now never raises on any payload shape, for any event type it
  handles — a malformed event always becomes an orphans entry, and
  folding continues; the rest of the space's state is unaffected.

Substrate-level robustness amendment, not a behavior change for any
well-formed event: every pre-existing test in `tests/test_ledger_fold.py`
continues to pass unmodified; the new poison-shape tests (per event type,
plus a `ledger_cli tasks`/`balances`-on-a-poisoned-space subprocess check)
are additive.

### Key custody

Two locations with different trust properties and different git treatment:

- **Private key material**: `~/.datacore/keys/<actor>.key` — hex-encoded raw
  Ed25519 private key bytes, mode `0600`, generated by `ensure_keypair()` on
  first use **only when signing is on**. This directory is **outside** any
  git-tracked repo (under the user's home directory, not under `~/Data` or
  the dips repo) and must never be committed.
- **Public verify-key registry**: `<DATACORE_ROOT>/.datacore/keys/registry.yaml`
  — a tracked, public YAML file mapping `actor -> verify_key_hex`, upserted by
  `ensure_keypair()` alongside private-key generation. Because it holds only
  public keys, it is safe to commit and sync across machines like any other
  Datacore config file — any party can verify a signature without holding a
  secret. A malformed or missing registry never raises; it degrades to an
  empty actors map (fail-safe read), and `keys.verify()` returns `False` for
  an unknown actor rather than raising.
- **Concurrency**: `ensure_keypair()` is guarded by a per-actor `fcntl.flock`
  lock file (`<keys_dir>/.<actor>.lock`) with a double-checked existence test
  after acquiring the lock, so two processes cold-starting the same
  brand-new actor cannot race into generating two different keypairs for one
  actor name (the loser loads the winner's key instead of overwriting it).

### Signing (opt-in)

`EventLog(space_dir, actor, sign=None)` — `sign` is tri-state: `True`/`False`
picks explicitly; `None` (the default) reads `DATACORE_LEDGER_SIGN=1` from
the environment. When signing resolves to **off** (the MVP default),
`ensure_keypair` is never invoked — no key or registry file is created or
touched — and every appended event gets `sig=""`. When signing is **on**,
behavior is what a "signatures from day one" design would look like:
`ensure_keypair` runs at `EventLog` construction and every event body is
signed before being written. The signing contract signs the **body**
(`{seq,hlc,actor,type,payload,prev}` canonical bytes), never the serialized
line including `hash`/`sig` — so verification recomputes the same body and
checks the signature against it independently of hash computation.

`verify_chain(path, strict=False)` checks, per event, in this order
(independent — one failing does not skip the others): (1) hash mismatch —
recomputed `compute_hash` vs. stored `hash`; (2) broken `prev` linkage —
first event's `prev` must be `"GENESIS"`, every later one must equal the
*stored* (not recomputed) hash of the prior event; (3) seq gap — must run
0, 1, 2, … with no gaps or repeats; (4) signature — only for events where
`sig != ""`, verified against the registry (unknown actor and bad signature
both collapse to the same "signature verification failed" message — that
distinction isn't this checker's job to make); (5) **only in `strict=True`
mode** — `sig == ""` is itself reported as an error. `strict` is off by
default because unsigned events are valid under the opt-in signing design;
an operator switches it on only for a deployment where signing has been
turned on system-wide and every event is expected to carry one.

### Operator surface (`ledger_cli.py`)

```
ledger_cli.py append   --space <dir> --type <t> --payload '<json>' [--actor <a>]
ledger_cli.py verify   --space <dir> [--strict]
ledger_cli.py tasks    --space <dir> [--status <s>] [--owner <o>]
ledger_cli.py balances --space <dir>
```

Actor resolution for `append`: `--actor`, else `$DATACORE_ACTOR`, else
`socket.gethostname()`. Stdout/stderr discipline: every command's *data*
(hash/hlc, the `OK <n> files <n> events` summary, task JSON lines, the
balances object) goes to stdout; every *diagnostic* (verify error lines,
clean failure messages) goes to stderr. Expected failures (bad payload JSON,
unknown event type, a missing `--space` directory, a broken chain) are
caught and reported as a clean one-line stderr message with a nonzero exit
code — never a raw traceback; genuinely unexpected exceptions are allowed to
propagate, since hiding those is not this script's job.

### Changes Required

- **New**: `.datacore/lib/ledger/` package — `hlc.py`, `events.py`, `log.py`,
  `verify.py`, `fold.py`, `index.py`.
- **New**: `.datacore/lib/ledger_cli.py` — operator CLI.
- **New (per space, on first write)**: `<space>/.datacore/events/<actor>.jsonl`.
- **New (opt-in, only when signing is enabled)**: `~/.datacore/keys/<actor>.key`,
  `.datacore/keys/registry.yaml`.
- **New (gitignored, disposable)**: `<space>/.datacore/state/ledger/index.db`.

### New Components

- `ledger.hlc` — hybrid logical clock (`tick`, `parse`).
- `ledger.events` — `Event` dataclass, canonical byte encoding, hash
  computation, line (de)serialization, `EVENT_TYPES`.
- `ledger.log` — `EventLog` (locked append, per-writer files), `read_events`
  (merged, hlc-sorted read), `CorruptLogError`.
- `ledger.verify` — `verify_chain` (hash/prev/seq/signature diagnostic).
- `ledger.fold` — `fold` (pure reduction), `TaskState`, `LedgerState`.
- `ledger.index` — disposable SQLite projection (`build_index`, `tasks_by`,
  `spend_by_actor`).
- `ledger.keys` — Ed25519 keypair management, sign/verify, public registry
  (built and tested, dormant until the signing trigger fires).
- `ledger_cli.py` — the operator CLI above.

### Interface Changes

- New per-space directory `.datacore/events/` (event source of truth).
- New operator CLI `ledger_cli.py` (append/verify/tasks/balances).
- New owner-editable-by-convention (not by this DIP) key locations:
  `~/.datacore/keys/` (private, never committed) and
  `.datacore/keys/registry.yaml` (public, tracked).
- No existing file format (org-mode, JSON state files) is removed or changed
  by this DIP — the ledger is additive; migration of specific coordination
  paths (nightshift claiming, GTD task projection) onto it is explicitly out
  of Phase 1 scope (see Backwards Compatibility).

## Invariants

Five upgrade-readiness invariants (`ENG-2026-0729-016`), amended by the
signing ruling (`ENG-2026-0729-030`) as noted, that this substrate must never
violate — because every later phase (0035–0041) and any future real
consensus/chain assumes they hold:

1. **Events are append-only and immutable.** Nothing in this package ever
   rewrites or deletes a line in a writer's `.jsonl` file. `append()`'s only
   destructive operation is truncating a *torn, unparseable final line*
   (an in-flight write that never completed) — never a valid, previously
   committed event.
2. **State is derived by deterministic fold — no wall clock or randomness in
   state logic.** `fold()` takes zero inputs besides the event list; given
   the same events (in the same order) it produces byte-for-byte identical
   `LedgerState` on every call, on every machine, forever. This is what makes
   the ledger replayable and the SQLite index disposable/rebuildable.
3. **The signature *field* is present from day one; signing itself is
   opt-in** (`ENG-2026-0729-030` amendment). The schema shape
   (`sig: str`, defaulting to `""`) is fixed now precisely because retrofitting
   a signature field onto an already-running unsigned ledger would require
   re-writing or re-anchoring every prior event — an operation the append-only
   invariant (1) forbids. Shipping the field unsigned costs nothing; shipping
   it absent and adding it later costs a migration.
4. **Conservation in the balance table.** `spend.record` events only ever
   *add* to `state.spend[actor]` — there is no debit/credit pair and no
   event type that decreases a balance. Phase 1 defines the event and the
   accumulation; enforcing a budget ceiling or reconciling against an
   external ledger is future work, but the accounting primitive itself must
   never allow a spend event to net to a decrease.
5. **The sequencer is replaceable.** Nothing in this package assumes a single
   process is "the" writer for a space — every actor's file is independent,
   and `read_events`'s merge-by-`hlc` requires no coordination between
   writers at read time. `datacored` (or whatever process currently drives
   writes) can be replaced, restarted, or run redundantly without the ledger
   itself needing to change, because ordering is a property of the HLC
   stamps, not of write-time arbitration by a single process.

## Rationale

**Why per-writer files instead of one shared append-only file?** A single
shared file needs a lock held across every writer for every append — exactly
the contention this DIP exists to remove, and exactly the git-push-as-lock
failure mode (`ENG-2026-0423-001`) that motivated it. Per-writer files need
locking only *within* one actor's own concurrent processes (rare, and cheap
with `fcntl.flock`), never *across* actors; cross-writer ordering is instead
recovered at read time via the HLC-sorted merge.

**Why a hash chain instead of just trusting the filesystem?** The hash chain
makes tampering *detectable* independent of trusting that no one has write
access to the file — mutating any earlier event changes its hash, which no
longer matches the `prev` the next event recorded. This holds even before
signing is ever turned on; it does not, by itself, prove *who* wrote an
event or prevent a full-file rewrite by whoever can write to it (see Security
Considerations).

**Why opt-in signing rather than mandatory from day one?** At the current
trust domain (N=1 owner, three machines the owner controls, per-writer files
already attributing events to a writer by filename convention), the marginal
security signing buys is small relative to its cost: key generation,
distribution, and rotation across three machines is real operational work
that gates every deployment on getting key management right first. The
signature *field* is kept in the schema now because adding it later would be
a breaking migration under the append-only invariant; the *behavior* of
signing is deferred to the trigger that actually needs it (foreign agents, or
an external audit requirement) rather than imposed as a default cost paid by
every write from a system that has no adversary yet. This is the explicit
ruling in `ENG-2026-0729-030`, not an oversight.

**Why a pure fold rather than incremental/streaming state updates?** A pure
function of the full event list is trivially replayable (rebuild state from
scratch any time, on any machine, and get the same answer), trivially
testable (given events, assert state — no mocking a clock or a lock), and is
what makes the SQLite index a disposable cache rather than a second source of
truth that itself needs to stay consistent under concurrent writes.

### Alternatives considered

- **Extend the existing git-push-as-lock nightshift claim mechanism** —
  rejected; it is exactly the mechanism whose silent failure mode
  (`ENG-2026-0423-001`) motivated this DIP, and a git ref cannot express
  "record that a claim was attempted" independent of the push succeeding.
- **A single shared append-only file with a global lock** — rejected; global
  contention on every write reintroduces the coordination cost per-writer
  files exist to remove, at higher risk (one file, one point of corruption)
  for no benefit over per-writer files plus HLC-sorted merge.
- **Mandatory signing from day one** — rejected per explicit owner ruling
  (`ENG-2026-0729-030`); see Rationale above.
- **A real blockchain / consensus mechanism now** — rejected per the
  originating direction (`ENG-2026-0729-016`): "do NOT build a blockchain
  now." This DIP is deliberately the smallest substrate that is *upgrade-ready*
  toward one, not an attempt to build one prematurely.

## Backwards Compatibility

Additive and non-breaking. No existing org-mode file, JSON state file, or
nightshift claiming path is modified, removed, or migrated by this DIP —
`.datacore/events/` is a new directory that exists alongside them. Org files
remain the source of truth for GTD tasks in v2; the ledger tracks
briefing/delegation/verification objects (this is a deliberate v2 scope
boundary, revisited as v2.1 — see Open Questions). A space with no
`.datacore/events/` directory behaves exactly as before: `read_events` on a
missing directory returns `[]`, and no ledger command errors on an
as-yet-unused space. Adopting the ledger for a given coordination path (e.g.
routing a nightshift claim through `task.claim` instead of `git push`) is a
follow-on integration task in later phases, not part of this DIP.

## Security Considerations

- **Public-repo constraint.** Both `~/Data` and the dips repo are public
  (or public-adjacent). This DIP's content and the tracked
  `.datacore/keys/registry.yaml` file contain **no secrets** — the registry
  holds only public verify keys. Private key material never enters a
  git-tracked path; it lives under `~/.datacore/keys/` outside any repo, mode
  `0600`.
- **What the hash chain protects, unsigned.** A hash chain alone detects
  *retroactive tampering that does not also rewrite everything after the
  tampered event* — if an editor changes one historical event's payload
  without recomputing every subsequent hash in that file, `verify_chain`
  reports the break at the first inconsistency. It also gives free,
  low-cost **attribution by convention**: because only one actor is expected
  to write to `<actor>.jsonl`, an event appearing there is conventionally
  "from that actor" for any reader who trusts the filesystem layout.
- **What the hash chain does NOT protect, unsigned.** Anyone with write
  access to `<actor>.jsonl` can **fully regenerate that entire file from
  scratch** — including recomputing every hash correctly — and
  `verify_chain` would report it as a perfectly valid chain, because nothing
  independent of the file itself vouches for who actually authored the
  events in it. Without signing there is **no cryptographic non-repudiation**:
  attribution rests entirely on trusting that no other process wrote to
  `mac.jsonl` on behalf of an attacker, and on trusting the filesystem/OS
  access controls around `<space>/.datacore/events/`. This is the exact gap
  signing closes, which is why the trigger for enabling it (`ENG-2026-0729-030`)
  is "a foreign agent joins the ledger" or "an external/enterprise audit-trail
  need" — i.e., the moment "trust the filesystem" stops being an adequate
  model.
- **Fail-safe registry reads.** A malformed or missing
  `.datacore/keys/registry.yaml` degrades to an empty actors map rather than
  raising, and `keys.verify()` returns `False` (never raises) for an unknown
  actor or a bad signature — a corrupt registry can only cause spurious
  verification failures, never a false "verified" result and never a crash
  of the reading process.
- **Key generation concurrency.** The per-actor lock file in `ensure_keypair`
  prevents two racing cold-starts from generating two different keypairs for
  the same actor name and leaving the registry pointing at one while a
  process signs with the other.
- **Not an access-control system.** This substrate detects tampering and (once
  signing is on) attributes authorship; it does not, by itself, restrict
  *who may write* `task.claim` or `task.complete` for a given task — that is
  a fold-semantics concern (ownership checks in `_handle_release`, etc.), and
  richer authorization (co-sign for side-effecting actions) is Phase 5's
  `ledger/policy.py` (DIP-0038), layered on top of this substrate rather than
  built into it.

## Implementation

### Reference Implementation

`.datacore/lib/ledger/` (`hlc.py`, `events.py`, `log.py`, `verify.py`,
`fold.py`, `index.py`) and `.datacore/lib/ledger_cli.py`, with tests under
`.datacore/lib/tests/` (`test_ledger_*.py`, `test_ledger_cli.py`) — 293
tests passing at HEAD of `feat/datacore-v2`, zero pre-existing or new
failures.

Commit reference: `feat(v2): ledger CLI` (branch `feat/datacore-v2`).

### Rollout Plan

**Phase 1 (this DIP — shipped): the substrate.** `ledger` package + CLI, full
test coverage, signing opt-in behind `DATACORE_LEDGER_SIGN=1`. No existing
coordination path is migrated onto it yet.

**Phase 2 (DIP-0035, follow-on).** Job contracts + a unified verifier
(`job_verify.py`) emit `metric.attest` events per scheduled job, giving the
"mechanical artifact checks" tier of verification named in
`ENG-2026-0729-016` item 2 its first real consumer of this substrate.

**Phases 3–8 (DIP-0036–0041, follow-on, interface-locked at this writing).**
Config plane, grounded briefings, the action loop + co-sign policy
(`policy.set`, side-effecting-action gating), server-first artifact sync
(`artifact.attest`), agent-registry consolidation, and executor adapters
(`spend.record` going live end-to-end) each build on this event schema
without changing it. Each is expanded into its own DIP at that phase's start.

## Open Questions

1. **Org-file projection of ledger tasks** — deliberately **out of v2 scope**.
   Org files remain the source of truth for GTD tasks; the ledger tracks
   briefing/delegation/verification objects, a distinct object class.
   Whether/how ledger tasks eventually project into or replace org-mode task
   headings is deferred to v2.1.
2. **Signing rollout mechanics** — when the trigger fires (foreign agent, or
   an audit requirement), what is the migration path for *already-written*
   unsigned events in an existing `.jsonl` file? This DIP does not specify a
   backfill/re-anchor procedure; it is designed only so that new events after
   the switch carry real signatures, and `verify_chain(strict=True)` can then
   flag the pre-existing unsigned tail as expected legacy rather than an
   error, if an operator chooses non-strict verification for historical
   ranges.
3. **Sequencer replacement / quorum triggers** — this DIP asserts the
   invariant (sequencer replaceable) but does not itself specify the quorum
   protocol; that is deferred until sequencer downtime actually creates
   operational pain (trigger-based, not scheduled — see `ENG-2026-0729-016`).
4. **Cost-cap / budget enforcement semantics** for `spend.record` — Phase 1
   defines pure accumulation; whether overspend hard-blocks vs. escalates is
   future work once shadow accounting has been observed for long enough to
   set a sane threshold.

## References

- `ENG-2026-0729-016` — ledger-mindset direction (owner decision, six
  elements adopted now, five upgrade-readiness invariants, upgrade triggers
  not dates).
- `ENG-2026-0729-030` — signing opt-in amendment (owner ruling, supersedes
  "signatures from day one" with "signature field from day one, signing
  behavior opt-in").
- `ENG-2026-0727-004` — Mac↔box sync topology and its two failure modes
  (duplicate resurrection, ID-conflict churn) that motivate durable,
  uniquely-identified, append-only events over content-inferred identity in
  mutable shared files.
- `ENG-2026-0423-001` — nightshift git-lock silent failure ("Complete! 0
  tasks, 0 errors" undetected for three days) that motivates recording
  attempts independently of a fragile shared-lock primitive.
- `ENG-2026-0304-027` — the general Datacore pattern (`fcntl` locking around
  concurrent JSON/file writers) this DIP's per-writer append lock follows.
- DIP-0011 — Nightshift module (the claiming mechanism this ledger is
  designed to eventually replace, per Phase 2+).
- DIP-0018 — Credential Management (key-custody conventions this DIP's
  private-key-outside-repo / public-registry-tracked split follows).
- DIP-0032 — Egress Enforcement (structural precedent for this DIP's format
  and for "policy file + fail-closed defaults" reasoning, reused for
  `ledger/policy.py` in Phase 5).
