# DIP-0046: Git as Ledger Transport

| Field | Value |
|-------|-------|
| **DIP** | 0046 |
| **Title** | Git as Ledger Transport |
| **Author** | Datacore Team |
| **Type** | Architecture |
| **Status** | Draft |
| **Created** | 2026-08-11 |
| **Updated** | 2026-08-11 |
| **Tags** | `git`, `transport`, `ledger`, `sync`, `provenance`, `detectors` |
| **Affects** | `.datacore/lib/` (sync scripts), `.datacore/githooks/`, `.datacore/hooks/`, `.datacore/modules/nightshift/lib/`, `.datacore/modules/chief-of-staff/server/lib/`, 10+ module `*-hook` commands, `/today`, `/tomorrow`, `/wrap-up`, `/continue`, `/process-inbox`, and — in separate repositories — `datacore-mcp` (GTD write tools) and `datacore-app` (no ledger awareness today) |
| **Specs** | `.datacore/lib/jobs/manifest.yaml` (detector contracts) |
| **Agents** | `nightshift-orchestrator`, `journal-coordinator`, `wrap-up-executor` |
| **Relates to** | DIP-0011 (Nightshift — the `git push`-as-lock this replaces), DIP-0034 (Event Ledger Substrate — reserves this migration for its own DIP; **this DIP obliges an amendment adding `member.*` event types**), DIP-0044 (Actor Identity — authentication, where this DIP is authorization), DIP-0035 (Job Contracts — detector contracts), DIP-0043 (Org Projection), DIP-0018 (Credential Management), ENG-2026-0423-001, ENG-2026-0729-009, ENG-2026-0804-033, ENG-2026-0811-005 |

## Summary

Git carries only payloads that **cannot conflict**: append-only per-writer event
logs, and additive new files. Everything derived from the ledger is regenerated
locally rather than synchronised. Repositories are classified as **knowledge**
or **code**, and the two get different rules — knowledge commits directly to its
default branch, code goes through branch-and-review.

The **space is the unit**: facts, knowledge and projections live together, and
membership in a space — not possession of a clone — is what grants an actor
access to both. Transport binds per space, so a space that outgrows git changes
one binding rather than the architecture.

This retires `git push`-as-lock, the rescue-branch machinery, the merge
gatekeeper, and the branch-recovery tooling, because it removes the conditions
that made them necessary rather than hardening them.

## Motivation

Every git incident in this installation has the same root cause: **git is
carrying mutable shared state**. Mutable state produces conflicts; conflicts
produce rebases; rebases produce rescue branches, hard resets, gatekeepers, and
stranded work.

The record, all verified rather than recalled:

| Incident | Cost |
|---|---|
| Checkout left on `ops/b17-sprint-claim` (DIP-0011, 2026-07-13) | 610 commits invisible — 52 zettels, 19 literature notes, 15 journal entries |
| `nightshift/run-*` branches, 2026-08-06..11 | **645 commits across 74 branches**, growing nightly |
| `git_fleet_sync` failure (`caa7d58`, 2026-07-21) | **110 files wiped** from datafund-space |
| stash→pull→stash-pop on the Mac (ENG-2026-0729-009) | 10 orphaned stashes over six weeks |
| `git push … \|\| true` in `cos_sync.sh` | failed pushes reported as "synced clean" |

Four independent implementations of the same sync algorithm exist
(`cos_sync.sh` ×2 paths, `space_sync.py`, `git_fleet_sync.py`), so each defect
must be fixed four times — and in practice was not: the `|| true` fix lived only
on the box while the repository carried two older broken copies.

The ledger is the opposite shape. It is **append-only, one file per writer**.
That is the single data structure git handles with no discipline at all: two
actors never touch the same file, so a merge is a union and a conflict is
impossible by construction. The problem is not that git is the wrong transport.
The problem is what we ask it to carry.

DIP-0034 explicitly reserved this migration: *"Adopting the ledger for a given
coordination path (e.g. routing a nightshift claim through `item.claim` instead
of `git push`) is a follow-on integration task in later phases, requiring its
own ratified DIP."* This is that DIP.

## Specification

### 1. Two categories

Repositories are classified, and the classification is **data**, not convention:
it lives in `registry/repositories.yaml`, alongside the existing `agents.yaml`,
`commands.yaml` and `infrastructure.yaml`, and maps each repository to its
category and its transport binding (§11). A repository absent from that registry
is **unclassified and refused by `ledger_transport.py`** — silently defaulting to
either category is how a production repo would end up taking knowledge rules.

Space membership is *not* duplicated there: the registry says what a repository
IS, the space's own log says who may write to it (§11).

| Category | Contents | Rule |
|---|---|---|
| **knowledge** | spaces: facts, org, journals, notes, ledger events | commit and push directly to the default branch |
| **code** | product repos: `plur`, `enterprise`, `datacore-app`, modules | branch, PR, review, merge queue |
| **agent-personal** | each agent's own space | that agent's own default branch, no review |

Industry guidance for AI agents ("never let an agent commit to a shared
branch"; `agent/<ticket>-<desc>` naming) is written for **code**, where review is
the deliverable. It is correct there and is adopted verbatim for the code
category. It is wrong for knowledge, where a pull request per journal entry
would be ceremony without a reviewer. This DIP states that explicitly so the two
are not "harmonised" later by someone applying one category's rule to the other.

### 2. Three payload classes

| Class | Example | Rule | Conflict risk |
|---|---|---|---|
| **Facts** | `<space>/.datacore/events/<actor>.jsonl` | append-only, one file per writer, never edited | impossible by construction |
| **Derived** | `next_actions.org`, briefings, status JSON | **not tracked** — regenerated from the fold | none: nothing to sync |
| **Content** | reports, zettels, journal entries | additive new paths, one author per path | rare and genuine |

**Every machine projects for itself.** Because a projection is untracked, there
is no shared file to contend for: each machine folds the log it holds and writes
its own local copy. Two machines projecting at the same moment is not a race, it
is the normal case, and they agree because the fold is deterministic over the
same events — checked by comparing state roots (§3.7) rather than by
coordinating writes.

This is why no projector election, lock, or designated machine is needed. The
refuse-to-overwrite guard belongs to **Phase 0**, where the file is still
tracked and hand-authored and an overwrite would destroy human work; it has no
role once the file is generated. An earlier draft carried a projector-election
open question straight from the old model into this one, which was a
contradiction of this very section.

Winston's role is unchanged and unrelated: it sequences **finality** over the
combined log (DIP-0042). Appends need no sequencer — they are per-actor and
disjoint — and projection needs no sequencer either. What a sequencer provides
is ordering *across* actors for settlement, which is a different question from
who renders a local view.

The **Derived** row is the load-bearing decision. A projection that is
deterministic from the ledger is a build artifact. Tracking a build artifact in
git and then merging it across five machines is the whole disease. Gitignore it
and regenerate.

This is what deletes the rescue branch, the hard reset, the merge gatekeeper,
and the recovery script — not better handling of those paths, but the removal of
the state that required them.

**What this costs, stated rather than discovered later.** Two capabilities are
lost when a projection stops being tracked:

- *Readability without the toolchain.* Today `next_actions.org` opens in
  Obsidian, in Emacs, on a phone, in a web UI. After Phase 1 a machine without
  the ledger code sees an empty directory. The projection is regenerated on
  every `converge()`, so any machine that syncs still has the file on disk —
  but a machine that only clones does not.
- *`git log next_actions.org`.* Task history via diff is a real forensic tool
  and it ends at Phase 1 for that file. The ledger holds the history, but folded
  JSONL is not a readable diff.

Mitigation is deliberately weak and deliberately explicit: a **weekly tracked
snapshot** of the projection is committed to the space as
`org/next_actions.weekly.org` — human-readable, diffable, and never read by any
program. It is an archive, not a source. Anything that reads it is a bug.

### 3. Transport rules for facts

1. **One writer per file.** Enforced by filename (`<actor>.jsonl`) and the
   roster in `registry/infrastructure.yaml`. Two machines never share an actor
   name.
2. **Never rebase; merge only.** Disjoint files always merge cleanly. Rebase
   buys nothing here and is the operation that strands work.
3. **Push after append, and treat a failed push as an error.** Appends are
   idempotent by content hash, so retry is always safe.

   "Immediately" and the existing 15-minute sync interval were stated in the
   same document and contradict each other; the resolution is that **latency is
   per event class**, not global. A `item.claim` pushes immediately, because the
   claim window is the duplication window. A `metric.attest` from a detector can
   ride the next scheduled converge. Pushing *every* event immediately means a
   git round trip per event across 15+ migrated writers, which is a real
   operational cost and buys nothing for events nobody is racing on.
4. **Never force-push; never `reset --hard`.** With no mutable shared state
   there is no divergence to resolve.
5. **Integrity is not git's job.** `verify_chain` proves the log is intact
   regardless of how it travelled. Fault-injected 2026-08-11: a single changed
   byte yields `line 52: hash mismatch` and a non-zero exit.
6. **Sequence numbers are enforced on read, not merely observed.** Each actor's
   events carry a monotonic `seq`. A gap is not a warning — the fold refuses to
   advance past it and reports the missing range. Ethereum enforces exactly this
   with per-account nonces: a transaction with the wrong nonce is rejected
   rather than applied out of order. Our present design only *detects* gaps,
   which is why a missing push looked identical to a slow one.
7. **The fold publishes a state root**, over **all three** `LedgerState`
   fields — `items`, `spend` and `orphans` — encoded with the same
   `canonical_bytes` the event hash already uses. Hashing only `items` would
   attest agreement while `spend` totals differed or one machine had silently
   accumulated orphans, which is worse than no root: a confident answer to a
   question it did not ask.

   A root mismatch is **not** an alarm on its own. Two machines mid-convergence
   hold different event sets and *must* differ. The root is only meaningful once
   per-actor `seq` agrees, so the comparison is gated on seq-agreement first —
   otherwise the detector is noisy by construction and gets ignored, which is
   the failure mode alarms die of.

### 4. Commit provenance

Every agent commit carries trailers binding it to the ledger:

```
Datacore-Actor: data
Datacore-Space: 5-plur
Datacore-Event: 1786407657798.0001.data
Generated-by: openclaw/codex-gpt-5.5
Signed-off-by: Gregor <gregor@datafund.io>
```

Git and the ledger become **cross-verifiable in both directions**: every agent
commit must name an event that exists in the chain, and every `item.complete`
must have a commit. A missing pair is a detector rather than an unanswerable
question.

**Order replaces atomicity.** An event and the artifact it describes do not need
to land in one commit, and chasing that is the wrong goal — the two-phase write
it implies is unachievable over git and unnecessary. Instead the write is
**sequenced**:

1. commit **and push** the **artifact** — and *confirm the push*;
2. only then append the **event**, carrying the artifact's commit sha.

The confirmation is a hard gate, not narrative. "Commit and push" is two
operations with different failure profiles: a commit essentially never fails, a
push fails routinely — offline, auth, non-fast-forward. If step 2 proceeds
regardless of step 1's *push* outcome, the result is an event naming a commit no
other machine can resolve — the "dangerous direction" below, reached not by
lying but by a swallowed push. That is `cos_sync.sh`'s `|| true` wearing a
different hat, and this DIP's own motivation table lists it as a root cause.
So: **push unconfirmed ⇒ no event.** The item stays incomplete and the push is
retried.

```
{"type": "item.complete", "payload": {
   "id": "...", "artifact_commit": "a327401", "artifact_paths": ["0-inbox/report.md"]}}
```

A commit sha is an immutable content hash, so an event that names one is making
a claim that can be checked by anyone, later, without trusting the writer. The
ordering is what makes the failure modes benign and *distinguishable*:

- **artifact committed, event missing** → work exists, unrecorded. Detected by
  a commit with `Datacore-Event` trailers and no matching event. Recoverable:
  append the event.
- **event present, artifact commit unresolvable** → a claim about work that does
  not exist. This is the dangerous direction, and the ordering makes it
  impossible to reach by crashing — only by lying.

The reverse order would invert that: a crash between the two would leave the
ledger asserting a completion whose artifact was never pushed, which is exactly
the state no detector can distinguish from a fabrication.

`Generated-by` / `Co-authored-by` / `Assisted-by` follow the emerging convention
graded by AI contribution, with `Signed-off-by` naming the accountable human.
The convention's own caveat is respected: trailers are inspectable but are not
proof by themselves — here the proof is the chain the trailer points into.

**Provenance is an interface with pluggable sinks, not a trailer format.** The
trailers above are what the *local* sink emits; they are not the definition. A
provenance record is:

```
{ subject: <commit sha>,        # what is being attested — a content hash
  actor:   <ledger actor>,      # who
  action:  <event type>,        # what they did
  event:   <hlc>,               # where it is recorded
  at:      <timestamp> }
```

Two sinks consume it. The **local sink** writes the trailers and the ledger
event, and is always on. An **external attestor** is optional and additive:
Datafund's Verity already models exactly this as a `ProvenanceEvent` with
`signature`, `notarySigner`, `notaryTimestamp` and blockchain anchoring, so
wiring it in is an adapter that maps the record above onto that schema and posts
it — **no caller changes, no record changes**.

This is the same discipline as §9: the thing that varies is behind an interface
from the start, so adopting it later is wiring rather than redesign. Two
properties make that possible and are therefore requirements, not niceties:

- **`subject` is a content hash.** A commit sha is verifiable by anyone, later,
  without trusting us — which is the minimum an external notary needs to attest
  anything meaningful.
- **A sink never gates the write.** An attestor that is slow, down, or absent
  must not block an append. Attestation is asynchronous and its own failure is
  a detector's problem, not the writer's.

**Commit messages are rendered, not validated.** The agent emits structured
fields (`type`, `scope`, `subject`, `body`, `breaking`); the renderer constructs
the Conventional Commits header. An agent is never permitted to author the
prefix, so a malformed prefix cannot leak into a summary.

### 5. Verification must be isolated from execution

A completion check **must not run in an environment the executing agent could
write to**. Otherwise the check is satisfiable by the thing being checked:
`test -s proof.txt` is met by `touch proof.txt`.

Checks run against a fresh worktree of the **committed** result. That buys two
things: a pass means something durable anyone can re-verify from the sha rather
than a fact about one machine's `/tmp`, and a check cannot quietly depend on
machine-local state.

**It does not prevent a fabricated artifact, and an earlier draft wrongly
implied it did.** Measured: an agent that writes `faked` into `proof.txt`
without doing the work still passes `test -s proof.txt` under isolation, because
committing the agent's output is exactly what isolation does — and for a
file-producing task, producing the file *is* the work.

The defence against fabrication is **check strength**:

```
test -s proof.txt             passes on "faked"    — asserts existence
grep -qx verified proof.txt   fails  on "faked"    — asserts content
```

So the requirement is on the check, not the sandbox: **a check must assert the
outcome, never merely that something appeared.** Isolation and strength are
independent, and only the second one resists a reward hack.

**This covers file-producing tasks only, and that limit is the point.** A task
whose deliverable is a file can be verified from a checkout the agent never
touched. A task whose deliverable is an effect in the world — a service running,
an email sent, a PR merged — has no such artifact, and re-reading the agent's
own report is not verification.

**Effects are verified per type, against their own system of record.** There is
no universal mechanism, and looking for one is what made this appear unsolvable.
Each `effects` tag binds a verifier, and the verifier's defining property is
that it reads **a record the acting agent does not control**:

| Effect tag | System of record | Verifier reads |
|---|---|---|
| `service.deploy` | the service itself | health endpoint, or the server's own logs |
| `email.send` | the mail provider | the Sent folder, or a control recipient BCC'd on every send |
| `pr.merge` | the forge | the API — is the PR merged, at which sha |
| `payment` | the ledger of the payment provider | the transaction record |

The BCC case is the sharpest illustration of the principle: it does not inspect
the agent's claim, it **manufactures independent evidence in a third place**
before the claim is made. A verifier that queries the agent, or a log the agent
writes, verifies nothing.

The result is recorded as a `metric.attest` event of class `effect.verify`,
carrying `{item, effect, ok, source_of_record, evidence}` — allocated by
amendment to DIP-0034's discriminator table, per that DIP's rule that a new
measurement class is a table amendment and never a new event type.

**An effect with no registered verifier cannot auto-complete.** It finishes in
review with its evidence attached. This is the honest failure mode: the set of
verifiable effects grows as verifiers are written, and everything outside that
set is visibly pending rather than silently trusted. Side-effecting items remain
gated at creation by `guarded_append` regardless — creation-time co-sign and
completion-time verification are independent controls.

### 6. Loud degrade

Any fallback that silently changes isolation, execution mode, or transport is a
**failure**, not a warning. A degrade that reports success is indistinguishable
from success, and this installation has produced that failure at least five
times (silent push failure, silent auth failure, silent PR-flow failure, silent
stash loss, silent worktree in-place fallback in an independently-built system).

### 7. Enforcement by host

Client-side git hooks are **advisory**: `--no-verify` bypasses them, and a fresh
clone has none. They are a safety net, not a gate. Enforcement differs by host
and the difference is stated rather than papered over.

| Host | Mechanism | Spaces |
|---|---|---|
| Gitea (self-hosted) | `pre-receive` rejecting a push that writes another actor's log — server-side, unbypassable, applies to all protocols and the API | 0-personal, 4-forge, 6-meridian, 7-megaphone |
| GitHub | Rulesets with `bypass_actors` for agent accounts; merge queue for code repos | 1-datafund, 2-datacore, 3-fds, 5-plur, 8-firm |

Rulesets supersede classic branch protection. Removing protection entirely to
let agents push is the wrong fix; adding the agent accounts to `bypass_actors`
achieves the same outcome while keeping the rule for everyone else.

`core.hooksPath` is set per machine so every repository — including future
clones, which never receive hooks — resolves the same hook directory. **This
setting is itself monitored** (§8): configuration that silently switches off
enforcement is the failure mode observability normally misses.

### 8. Detectors

Continuous, contracted through DIP-0035, each emitting `metric.attest` with a
dated artifact and `max_age_hours`:

| Detector | Catches |
|---|---|
| **seq gap** — local head seq vs remote, per actor | unpushed / stranded work |
| **chain verify** | tampering, truncation |
| **commit ↔ event cross-ref** | agent wrote without recording, or recorded without writing |
| **projection drift** — regenerate and diff | fold divergence between machines |
| **actor-file ownership** | one actor wrote another's log |
| **config drift** — `core.hooksPath`, ruleset state, on **all five machines** | our own enforcement being switched off |
| **actor presence** — every rostered actor has a log that is present, advancing, and **written only by its owner** | a log that was **deleted**, truncated, or written by the wrong actor |

Six, not eight. Two pairs collapsed because each pair asked one question twice:

- **state-root agreement folded into projection drift.** Both ask "do machines
  agree on derived state", and regenerate-and-diff is strictly more informative
  than a hash — it says *what* differs, not merely *that* something does. The
  root becomes a field the drift detector emits, not a job of its own. It is
  also weakly motivated: once seq-gap says no gap and chain-verify says intact,
  both machines hold the identical event set, and `fold()` is a pure function
  over it. Divergence then means version skew in `fold.py`, which a golden-
  fixture test catches more cheaply than a standing job.
- **actor-file ownership folded into actor presence.** Both check the roster's
  claim against the logs on disk; that is one check with two assertions, not two
  detectors with two contracts and two `metric.attest` streams.

**Absence is a first-class failure.** `verify_chain` verifies a file it is
given; it has nothing to say about a file that is not there, because a chain of
zero events is a valid chain. Delete `data.jsonl` and every surviving copy still
reports OK. This is not hypothetical — a sweep wiped 110 files from
datafund-space on 2026-07-21, and `git_fleet_sync` refuses to propagate
deletions precisely because of it.

The roster in `registry/infrastructure.yaml` is therefore **load-bearing for
integrity, not just for naming**: it is the only statement of which logs must
exist. The actor-presence detector reads it and asserts each named actor has a
log whose `seq` is non-decreasing since the last run. A log that vanishes, or
stops advancing while its machine is up, is a failure.

**Detectors report positively.** Each emits counts — events published, events
converged, gaps, chain status, root agreement, per actor per day — never merely
the absence of an alarm. Silence is consistent with "nothing is wrong" and with
"the detector is broken", and telling those apart is the entire purpose.

The seq-gap detector subsumes `git_fleet_audit.py`'s purpose: a gap **is** the
drain metric. It works under both the current and target designs, which is why
it is built first.

### 9. Transport is an interface, not an architecture

Git is **one implementation** of the transport, selected by configuration —
never a decision baked into callers. The interface is small:

```
append(space, actor, event)     # publish a fact
converge(space)                 # receive others' facts
can_receive(space) / gaps(space)  # readiness and drain state
```

**Expected git failures return a structured result; they never raise.** A push
rejected as non-fast-forward, an offline remote, a missing ref — these are
outcomes, not exceptions, and every one carries `ok`, a reason, and enough
context to act. Callers branch on `ok` rather than wrapping every call in
`try`/`except`, which is what made sixteen call sites each invent their own
partial error handling and what let `|| true` look reasonable in three of them.

Only *unexpected* failures raise. The distinction matters: a caller that cannot
tell "the remote is down" from "the repository is corrupt" will treat both the
same way, and treating them the same way is how a corrupt repository gets
retried in a loop.

Prime Intellect's `prime-rl` does exactly this: a `MicroBatchSender` /
`MicroBatchReceiver` pair with `filesystem` and `zmq` implementations chosen by
`transport.type`, so producers and consumers never learn which is in use. The
simple, durable transport is the default; the fast one is swapped in by config.

The same reasoning applies here for a concrete reason. Two of our five actors
(`tris`, `data`) hold partial checkouts and have no business carrying full space
history; a satellite transport (rsync of `events/`, or an HTTP endpoint) may be
correct for them later. If callers speak to the interface, that is a
configuration change. If callers call `git` directly — as sixteen of them do
today — it is a rewrite.

### 10. Atomic publish applies to whole-file artifacts, not to the log

An earlier draft required every fact to be published by writing a temporary file
and `rename()`-ing it into place, borrowing prime-rl's `rank_N.bin.tmp → rename`
pattern. **That was wrong, and applying it would have regressed working code.**

The analogy does not hold. prime-rl's file is a fixed-size shard rewritten
wholesale once per round. Ours is an ever-growing append-only log taking
thousands of small appends. To publish one line by temp+rename you must read the
entire file, build old+new, and write the whole blob back — turning an O(n)
append into O(n) read *plus* O(n) write, so **O(n²) I/O over the life of the
log**. Worse, done without preserving a single critical section it reintroduces
a lost update: two appenders each read the current file, each build their own
old+one-line content, and whichever renames second silently discards the other's
event — the precise failure this DIP exists to eliminate, reintroduced by the
rule meant to harden it.

`log.py` already solves this correctly and has since before this DIP:
`EventLog.append()` opens the actor's file, takes `fcntl.flock(LOCK_EX)`, reads
the tail under that lock, truncates a torn final line if it finds one, computes
`seq`/`prev`/`hlc`, and appends one line — all inside one critical section. No
reader observes a partial line; no two same-actor appenders fork the chain.
**Nothing in this DIP changes it.**

Temp-file-plus-rename remains correct for the payloads it was designed for —
whole-file artifacts that are replaced rather than extended: **snapshots (§12)
and generated projections (§2)**. Those are rewritten wholesale, so an atomic
swap is exactly right and costs nothing.

The general rule this leaves is narrower and truer: *a reader must never observe
a partially-written artifact.* For an append-only log that is achieved by
locking and appending; for a replaced file, by renaming. Choosing the mechanism
by file shape rather than by analogy is the actual requirement.

### 11. The space is the unit

Facts live **inside their space**, not in a separate ledger repository. An
earlier draft proposed extracting them; that draft was wrong, and the reason it
was wrong is worth recording because it is a trap this design invites.

It argued that `data` cloning 2.3 GB of `5-plur` to read 1.6 MB of events was
waste, and that the read access to journals and knowledge which came with it was
an access-control problem. **The knowledge is not overhead — it is the point.**
An agent producing work in a space draws on that space's knowledge base; an
agent holding only the event log can claim items and cannot do them well. The
size number was real and the conclusion drawn from it was not.

A single installation-wide ledger fails for a second, structural reason: **not
every actor belongs to every space, new actors will join, and the design must
reach past this cluster.** One global log makes membership a fiction — everyone
holds everything — and there is no natural boundary at which to admit an agent
that should see one space and not another. Per-space keeps the permission
boundary where it already is.

A space is therefore the unit of participation, and has five parts:

| Part | Example | Class (§2) |
|---|---|---|
| **identity** | name, id | — |
| **membership** | which actors write here, and as which actor name | — |
| **facts** | `.datacore/events/<actor>.jsonl` | Facts |
| **knowledge + content** | `3-knowledge/`, journals, reports, org | Content |
| **projections** | `next_actions.org` | Derived |

**Membership becomes explicit data**, not an implication of who holds a clone.
That is the piece that lets this reach beyond the cluster: an agent joins a
space, and joining grants its events and its knowledge together.

Two different facts were conflated in `registry/infrastructure.yaml`, and
separating them resolves it:

| Fact | Question it answers | Where it lives |
|---|---|---|
| **deployment** | which actor names may run on machine M | `infrastructure.yaml` — machine-shaped, correct as-is, retained |
| **membership** | which actors may write to space S | a **fact in S's own log** |

Membership is a **flat, git-tracked file** in the space:
`<space>/.datacore/members.yaml`, listing actor names.

An earlier draft made it `member.add` / `member.remove` events with genesis
membership and "any existing member may admit another", modelled explicitly on a
genesis validator set. That was wrong for two reasons, and the second is
decisive.

It imports admission machinery — bootstrap, authority, revocation ordering —
built for many mutually-distrusting writers, into a fact that **one person edits
a few times a year**. This DIP already refuses consensus on exactly that ground
("all five machines belong to one principal… nothing to vote on"); admission
control is consensus's sibling and the same argument applies. The audit question
it was meant to answer — *who admitted this actor, and when* — is answered for
free by `git log` on a tracked file, which is the audit mechanism this DIP
relies on everywhere else.

And it would have contradicted its own justification. The argument for
membership-as-fact was that "the enforcement point has the repository and
nothing else" — but folding member events at push time means the **Gitea server
needs a correct, version-locked copy of `fold.py`**, a deployment dependency
nothing else in this design has. A flat file in the same repository is equally
available to the hook and needs no code at all. The reasoning that made
membership a fact argued *against* it once followed through.

**Placement.** DIP-0044 answers *what key proves you are `data`*; membership
answers *which spaces `data` may write to*. Authentication and authorization
stay separate on purpose, so this is not folded into DIP-0044. The `member.add`
membership needs no new event types at all — the amendment obligation on
DIP-0034 is withdrawn.

**Transport binds per space, not globally.** §9 makes transport an interface;
this makes the binding a property of the space. Git is the implementation for
all nine today. A space that outgrows git — or a member that cannot be given a
clone — changes one binding rather than the architecture. That is the
scaling path, and it is deliberately not exercised yet.

**What co-location costs, stated plainly.** Putting facts inside a repository
that also carries human content means the whole repository inherits the facts'
rules: **no rebase, no force-push, no history rewrite** — because those
operations would destroy the log. Humans lose those operations in their own
knowledge repository. That is judged acceptable (rebasing a notes repo is rare
and never necessary) but it is a real constraint, and it is the price of not
splitting.

Full modularity — pluggable transport *and* pluggable knowledge bases, so a
space's storage, facts and knowledge can each be swapped independently — is a
later version's problem. This DIP makes the transport an interface and the
membership explicit, which are the two seams that make that later work possible
without making it now.

### 12. Snapshots

The fold replays every event from genesis. At 1,406 items and growing, replay
cost is linear in history forever. The ledger gains periodic **snapshots**: a
folded state at a known event, with the log retained so full history stays
recoverable.

**Snapshots are NOT tracked in git.** This is decided here rather than deferred,
because it is the architectural question and not a detail. A tracked snapshot is
derived mutable shared state — precisely what §2 removes — and would reintroduce
merges over a file every machine rewrites. Untracked, a snapshot is a local
cache: each machine builds its own, and a corrupt or missing one costs a replay
and nothing else.

The consequence is accepted: **a new machine bootstraps by replaying from
genesis.** Snapshots do not solve bootstrap. They solve the steady state, which
is the case that runs thousands of times a day, and bootstrap happens when a
machine joins the fleet.

What *is* published is the **state root** (§3.7) — a hash, not a state. It
travels in a `projection.attest` event, so any machine can check agreement
without holding anyone else's snapshot.

### 13. The code category: isolation and a commit gate

§1 classifies repositories; this states what the **code** category actually
requires. Industry practice for agents writing code is adopted here in full,
because unlike the knowledge rules it is answering the same question we have.

**Worktrees, not clones, for agent code work.** Each agent task gets an isolated
checkout sharing one object store — measured on this installation at 1.3 MB
versus 6.2 MB for a clone of the same repository, and commits are visible across
worktrees without a remote round-trip. Branch namespace is `agent/<task-id>`,
**unique per run**: an independently-built system stranded work by deriving the
branch from a stable alias while the path varied, so `worktree add -b` failed on
the second run and silently fell back to editing the user's source tree. Per §6
that degrade is a failure, not a warning.

Worktrees are for **code only**. They cannot span machines, so they contribute
nothing to the ledger's problem, which is five machines agreeing.

**A commit-decision gate.** An agent does not decide to commit. When work
reaches a verdict on a non-empty working tree, the run **pauses** and records a
pending decision; an operator chooses `approve` / `fix` / `apply` / `skip` /
`halt`; the choice is persisted as an audit artifact naming the exact
instruction the resume path executed.

Two properties are the point. The decision is **durable and attributable** —
"who approved this agent's commit, and what exactly did they approve" is
answerable afterwards from a file, not from memory. And the default is **stop**:
an agent that cannot reach an operator does not merge, it waits.

This closes the standing task *"Design a sign-off gate for nightshift/Miles-
authored features before merge"* (`5-plur`, priority A, created 2026-07-09),
whose `CONTEXT` has been empty since. It became urgent when agent accounts were
added to branch-protection bypass and protection was removed from `plur-space`:
nothing currently stands between an agent and an unreviewed write to a code
default branch.

**Merge queue** on code repositories with more than one agent contributing.
Required status checks force every PR to be current with the target branch,
which under a fleet of agents produces constant rebasing and serialisation — the
specific problem a merge queue exists to remove.

## Not in scope, and where it belongs

Several ideas worth taking are **not** transport concerns, and are recorded here
so they are not lost by being out of scope:

| Idea | Belongs to |
|---|---|
| Evidence-backed self-improvement — record the *trigger* and *outcome* of each learned rule, not just the rule | PLUR engrams / DIP-0019 |
| Bounded autonomy — token, turn and wall-clock budgets per run | DIP-0011 (nightshift) |
| Agent-to-agent messaging scoped to parent/sibling/child | agent-consolidation (DIP-0040) |
| Harness state as CRUD-able data with rollback; immutable base plus mutable layers | config plane (DIP-0036), layered context (DIP-0002) |

One idea is deliberately **rejected**: branching a log by moving a leaf pointer
within a single file. It is elegant for a forkable conversation history and
wrong here — our logs are one linear chain per actor precisely so that two
writers never touch one file, which is the property §2 depends on.

## Changes Required

### New

- `.datacore/lib/ledger_transport.py` — the single writer.
  `append_and_push(space, actor, event)`, `converge(space)` (fetch + merge,
  never rebase), `gaps(space)` (seq comparison), per-repo lock. Every caller
  uses it; no caller invokes `git` directly.
- `.datacore/lib/detectors/` — the eight detectors of §8.
- `registry/repositories.yaml` — repository category and transport binding (§1).
- `.datacore/githooks/commit-msg` — renders and validates the trailer block.
- Gitea `pre-receive` — actor-file ownership, on the four self-hosted spaces.

### Modified

- `run.py` — drop `git_commit_push` in favour of the transport module; the
  default-branch invariant of DIP-0011 principle 1 stays.
- `claim.py` — `item.claim` replaces `git push`-as-lock.
- `/today`, `/tomorrow`, `/process-inbox` — replace their inline
  `git add / commit / cos_sync.sh` pairs with `converge()` before reading and
  `append_and_push()` after writing.
- `/wrap-up` — step 13 ("push ALL repos") becomes a `gaps()` assertion; the
  session ends only when every actor's log is pushed.
- `/continue` — bootstrap reads folded ledger state rather than org text.
- `.gitignore` per space — add the projected org file once its space reaches
  Phase 1.

### Deleted

| File | LOC |
|---|---|
| `nightshift_recover_stranded.py` | 249 |
| `cos_sync.sh` (both paths) | 160 |
| `space_sync.py` | 142 |
| `cos_merge_runs.sh` + its three contracts | — |
| most of `git_fleet_sync.py` | ~300 of 390 |
| `git_fleet_audit.py` → seq-gap detector | 172 → ~40 |
| the shadowed duplicate copies of `claim.py`, `today_orchestrator.py`, `research_orchestrator.py` | — |

Track C alone removes roughly **1,000 lines** against **~200 written**, and that
reduction is real because the problem is deleted rather than refactored.

**That figure is not the DIP's net**, and quoting it as one would be flattering
arithmetic over a favourable subset. It excludes everything the other tracks
*add*: six detectors, the repository registry, the commit-decision gate,
worktree isolation, snapshots, and the provenance module. Several of those are
justified by a named incident; none of them are free. The honest claim is that
**Track C is strongly net-negative in code** and the rest of the DIP is net-
positive, bought deliberately.

## Rationale

**Why not simply harden the current design?** Because the failure recurred after
being fixed. DIP-0011 added the default-branch invariant on 2026-07-13 in
response to 610 stranded commits, and 645 more stranded four weeks later by a
different mechanism. Hardening addresses instances; the payload classification
addresses the class.

**Why is `nightshift_recover_stranded.py` evidence?** 249 lines of forensics —
diffing branches, classifying added-versus-modified files, judging what is safe
to replay — exists solely because git carried mutable state on unmerged
branches. In this design "stranded" is not a category: a gap in a sequence, with
`git push` as the fix.

**Independent convergence.** Two external systems, built without knowledge of
this one, arrived at the same primitives: `grite` models an issue tracker as an
append-only event log in git refs with a materialised view, where "coordination
state travels with the code through ordinary git fetch and push"; and Prime
Intellect's agent harness stores "the entire session history as append-only
JSONL files" with workers recoverable from those logs plus snapshots. A second
and third team reaching the same shape is stronger evidence for the direction
than another internal review round.

**What a settled distributed ledger already answers.** Ethereum solves the same
shape of problem — many writers, no single trusted machine, state derived by
folding an ordered log — and four of its answers transfer:

- **State root.** State is a fold over the log, and the *root hash* of that
  state is published with it, so agreement is one comparison rather than two
  replays (§3.7).
- **Per-account nonces.** Sequence gaps are *rejected*, not logged. A
  transaction out of order does not apply. Our seq gap should stall that actor's
  fold rather than be noted in a report (§3.6).
- **Finality versus head.** Reads that matter use settled state; only the UI
  reads the tip. That is the distinction DIP-0042 draws for block time.
- **Light clients.** A fact can be verified against a root without holding the
  chain — the honest long-run answer to satellite access (§11, OQ-9).

What does **not** transfer is the part people usually copy: consensus. Proof of
stake, mining, and fork choice exist to tolerate byzantine participants competing
to write. All five of our machines belong to one principal, write disjoint files,
and have no incentive to lie. There are no competing histories per writer, so
there is no fork to choose and nothing to vote on. Adopting consensus here would
buy nothing and cost everything — and the reason our design is simple is exactly
that we are allowed to skip it.

**What we take from those systems, and what we do not.** Snapshots, isolated
verification, and evidence-backed self-improvement transfer. Their *transports*
do not: Prime Intellect's harness is single-host with no cross-machine sync at
all, and their network layer (DHT, HTTP tree-topology broadcast, object storage,
on-chain attestation) solves high-throughput binary distribution, which is not
our problem. Adopting their transport would be cargo cult.

## Backwards Compatibility

Phased, and each phase is independently reversible until the last.

- **Phase 0 — shadow.** Projection written alongside the authored file and
  diffed. Currently 9/9 clean, streak 1 day. No behaviour change.
- **Phase 1 — generated.** Per space, once the streak is credible: the org file
  becomes generated and gitignored. Taken **one space at a time**.

  Calling this irreversible was imprecise. Reverting is mechanical — un-gitignore
  the file, commit the current projection, resume hand-authoring — and the ledger
  still holds every fact. What cannot be recovered is the **git history of that
  file for the period it was untracked**: `git log next_actions.org` will show a
  gap. That is the actual one-way cost, and it is small enough to accept and
  large enough to state.
- **Phase 2 — transport.** Callers migrate to `ledger_transport.py`. Old scripts
  remain until their callers are gone, then are deleted.
- **Phase 3 — claim migration.** `item.claim` replaces `git push`-as-lock, with
  a dual-write period.

The root `~/Data` repository is a public repository with human commits and
review, and it keeps conventional git — including rebase, which §3 forbids only
for fact repositories.

But it is **not** out of scope, and saying so earlier was the gap that produced
part of the incident this DIP is motivated by. `_run_repos()` includes the root
repository: nightshift writes to it, and 3 of the 76 stranded branches were
there. A repository that agents write to cannot be governed by neither category.

It is therefore classified **code**: agent writes go through a branch and a
review, human writes continue as today. That is the same rule the category
already carries, applied to the one repository that was quietly exempt.

## Security Considerations

- **Client hooks are advisory.** `--no-verify` bypasses them; a fresh clone has
  none. Anything that must hold is enforced server-side (Gitea) or detected
  (§8). This DIP does not claim client hooks as a control.
- **Enforcement asymmetry.** GitHub-hosted spaces cannot have server-side hooks.
  Their invariant is detected rather than enforced, and that gap is stated
  rather than hidden.
- **Provenance is not authorship.** A trailer asserts what a commit claims. The
  binding to a hash-chained event is what makes it checkable; the trailer alone
  is not proof.
- **Credentials.** Actors authenticate differently by design (HTTPS PAT, SSH
  key, per-machine). Per DIP-0018, no credential enters a tracked file. Actor
  identity in the ledger is a name, not a secret.
- **Verification isolation** (§5) is a security property, not a nicety: a check
  an agent can satisfy without doing the work is a reward hack surface.

## Implementation

Six tracks. Within a track the order is a dependency; across tracks there is
none, so all six start together. Every item carries its own verification — a
track is done when its checks pass, not when its code lands.

**Track A — detectors** *(no dependencies; ships first and guards everything else)*
1. seq-gap · 2. actor-presence · 3. state-root · 4. contracts in `manifest.yaml`
Verify: fault-inject each — delete a log, withhold a push, diverge a fold — and
confirm a red artifact with a non-zero exit, as `job.verify` was fault-injected
on 2026-08-11.

**Track B — provenance**
1. commit trailers · 2. `commit-msg` hook rendering from structured fields ·
3. commit↔event cross-reference detector *(needs B1)*
Verify: a commit whose `Datacore-Event` names no event fails the cross-check; a
model-authored Conventional Commits prefix is refused by the renderer.

**Track C — transport** *(the long pole)*
1. atomic publish (tmp + rename) in `log.py` · 2. `ledger_transport.py` ·
3. migrate 16 git callers *(needs C2)* · 4. migrate **org writers** *(needs C2)* ·
5. delete dead code *(needs C3, C4)*

The org-writer surface is larger than an earlier draft implied, and the
scoping principle that makes it tractable is: **Phase 1 breaks writers, not
readers.** A generated file is still a file — anything that reads
`next_actions.org` keeps working untouched. Only writes must route through the
ledger. Measured surface:

| Writer | Count | Repo |
|---|---|---|
| slash commands (`/today`, `/tomorrow`, `/process-inbox`, `/wrap-up`, `/continue`) | 5 | this |
| library + module code writing org state | 15 | this, nightshift |
| module hooks that write task state | **1** — measured 2026-08-11: 10 of the 11 org-referencing hooks are readers only, and `research/nightshift-hook` writes a journal entry, not task state | this |
| GTD MCP write tools (`add_task`, `complete_task`, `set_task_state`, …) | — | `datacore-mcp` |
| desktop app task actions — currently **no ledger awareness at all** | — | `datacore-app` |

The last two are separate repositories and are the reason C is the critical
path: this DIP cannot be finished inside one repo.
Verify: a concurrent-append test observes no torn line; every caller migrated is
a caller that no longer invokes `git` directly (`grep`-assertable); `/wrap-up`
refuses to close with a non-zero gap count.

**Track D — membership and enforcement**
1. `member.*` in `events.py` · 2. genesis backfill from `ledger_actors` *(needs
D1)* · 3. `registry/repositories.yaml` · 4. `core.hooksPath` on the agent
machines + config-drift detector · 5. Gitea `pre-receive` *(needs D2)*
Verify: a push writing a non-member's log is rejected server-side on a Gitea
space; an unregistered repository is refused by the transport module; unsetting
`core.hooksPath` turns the config-drift detector red.

**Track E — verification and the code gate**
1. check isolation — checks run in a checkout the agent never had ·
2. effect verifiers + `effect.verify` attestation · 3. commit-decision gate
(§13) · 4. worktree isolation for agent code work, degrading loudly *(needs E3)*
Verify: the `touch proof.txt` attack fails against the isolated check; an effect
with no registered verifier lands in review rather than complete; a run reaching
a verdict on a dirty tree pauses and writes a pending decision instead of
committing; a second run in one workspace gets its own worktree branch and fails
loudly rather than falling back to the source checkout.

**Track F — projection**
1. snapshots + state root · 2. Phase 1 on one space *(needs A, and a credible
shadow streak)*
Verify: fourteen consecutive days of positive counts — events published and
converged per actor, zero gaps, chain verified, roots in agreement, every
rostered actor present.

Critical path is **C**. A and D are the widest and least coupled, so they absorb
parallel effort best. F2 is the only step gated on elapsed time rather than
work, and it is deliberately last.

Detectors precede the migration deliberately: they are what tell us whether the
migration worked.

## Open Questions
- **OQ-1.** Snapshot cadence and format — event count, wall clock, or
  size-triggered?
- **OQ-2.** Journals are genuinely co-authored (a real conflict occurred
  2026-08-10). Split per-actor and merge at read time, or accept conflicts?
- **OQ-3.** Claim latency equals the sync interval — currently 15 minutes, so
  two actors can both claim for that long. The HLC resolves it correctly and
  records the loser as a no-op; the cost is duplicated work. Is a shorter
  interval, or an eager push on claim, worth it?
- **OQ-4.** Do agent-personal spaces participate in the shared ledger, or keep
  their own?
- **OQ-5.** Is a satellite transport (rsync of `events/`, or HTTP) worth adding
  for `tris` and `data`, which hold partial checkouts and do not need full space
  history? §9 makes this a configuration change rather than a rewrite, but it is
  not obviously worth doing.
- **OQ-6.** Atomic publish (§10) costs a temporary file and a rename per event.
  At claim/complete frequency that is negligible; if event rate rises, batching
  appends within a bounded window may be needed, which reintroduces a window in
  which facts exist only locally.
