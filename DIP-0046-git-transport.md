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
| **Affects** | `.datacore/lib/` (sync scripts), `.datacore/githooks/`, `.datacore/hooks/`, `.datacore/modules/nightshift/lib/run.py`, `.datacore/modules/chief-of-staff/server/lib/`, `/today`, `/tomorrow`, `/wrap-up`, `/continue`, `/process-inbox` |
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

Repositories are classified, and the classification is **data**, not convention.

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
3. **Push immediately after append.** A failed push is an error, never a
   warning. Appends are idempotent by content hash, so retry is always safe.
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
7. **The fold publishes a state root.** Folding produces a hash over the
   resulting state, not just the state. Two machines then answer "do we agree?"
   by comparing one hash instead of replaying two logs. This is the single most
   useful idea to take from Ethereum's design and it costs a few lines.

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

1. commit and push the **artifact**;
2. append the **event**, carrying the artifact's commit sha.

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

**Commit messages are rendered, not validated.** The agent emits structured
fields (`type`, `scope`, `subject`, `body`, `breaking`); the renderer constructs
the Conventional Commits header. An agent is never permitted to author the
prefix, so a malformed prefix cannot leak into a summary.

### 5. Verification must be isolated from execution

A completion check **must not run in an environment the executing agent could
write to**. Otherwise the check is satisfiable by the thing being checked:
`test -s proof.txt` is met by `touch proof.txt`.

Checks run against a separate checkout, populated from the committed result,
that the executing agent never had access to. This mirrors the practice of
withholding grading material during execution, on the stated principle that
anything readable by the agent is fair game for a reward hack.

**This covers file-producing tasks only, and that limit is the point.** A task
whose deliverable is a file can be verified from a checkout the agent never
touched. A task whose deliverable is an effect in the world — a service running,
an email sent, a PR merged — has no such artifact, and re-reading the agent's
own report is not verification.

Side-effecting tasks are therefore **not** covered by this section. They remain
gated at creation by `guarded_append` (co-sign against a recorded grant) and are
never auto-completed: they finish in a review state with the evidence attached.
Independent verification of effects is an open problem, recorded as OQ-8 rather
than papered over — a check that only covers the easy half while reading as a
general guarantee is the same defect this section exists to remove.

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
| **config drift** — `core.hooksPath`, ruleset state | our own enforcement being switched off |
| **actor presence** — every actor in the roster has a log, non-empty, advancing | a log that was **deleted** |
| **state-root agreement** — compare roots across machines | silent fold divergence |

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

### 10. Facts are published atomically

Appending to a JSONL file is **not atomic**. A concurrent reader, or a
`git add` racing an append, can observe a truncated final line. The chain hash
catches it on verification, but only after a malformed record may already have
been committed and replicated.

Every fact is published by writing to a temporary path and `rename()`-ing it
into place, so a reader sees either the previous complete state or the new
complete state and never a partial one. Readiness is then a simple existence or
length check, which is only sound *because* publication is atomic — the two go
together and neither is safe alone.

This is `prime-rl`'s filesystem transport verbatim in principle
(`rank_N.bin.tmp` → `rename` → `rank_N.bin`, receiver checks `exists()`), and it
is the one piece of their design that transfers without modification, because
the hazard is identical: multiple processes, one directory, no lock.

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

Membership is recorded as `member.add` / `member.remove` events in the space's
own event log. The space becomes **self-describing**: clone it, fold it, and you
know who belongs — no external registry to consult, drift from, or forget to
update. It is also the right shape for the question membership actually raises,
which is not "who is a member" but "**who admitted this actor, and when**". That
is an audit question, and audit questions belong in the ledger.

Bootstrap is the obvious objection: writing to a space's log requires
membership, and membership is established by writing to that log. The resolution
is the one every chain uses — **genesis membership**. A space's founding events
declare its initial members, exactly as a genesis block declares an initial
validator set. Thereafter an existing member admits a new one, and every change
is an auditable event authored by a named actor.

Authority is deliberately weak for now: **any existing member may admit
another**, because all current members belong to a single principal and a richer
role model would be unenforced ceremony. It tightens naturally when DIP-0044
lands and `member.*` events carry signatures, at which point admission becomes a
cryptographically attributable act rather than an assertion.

The folded member set is what §3.1 validates against, and what a Gitea
`pre-receive` (§7) derives in order to reject a push writing a non-member's log.
That is the reason membership must be a fact rather than a config file: the
enforcement point has the repository and nothing else.

**Placement.** DIP-0044 answers *what key proves you are `data`*; membership
answers *which spaces `data` may write to*. Authentication and authorization
stay separate on purpose, so this is not folded into DIP-0044. The `member.add`
/ `member.remove` **event types belong to DIP-0034**, which owns the event
vocabulary — an amendment obligation on that DIP, not a new DIP here.

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

## Changes Required

### New

- `.datacore/lib/ledger_transport.py` — the single writer.
  `append_and_push(space, actor, event)`, `converge(space)` (fetch + merge,
  never rebase), `gaps(space)` (seq comparison), per-repo lock. Every caller
  uses it; no caller invokes `git` directly.
- `.datacore/lib/detectors/` — the six detectors of §8.
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

Net: roughly **1,000+ lines removed** against **~200 written**. The reduction is
large because the problem is deleted, not refactored.

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
  becomes generated and gitignored. **This is the irreversible step** and is
  taken one space at a time.
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

Ordered so that each step is verifiable before the next depends on it.

1. **Seq-gap detector.** ~40 lines, works under the current design, would have
   caught both stranding incidents on day one. Contract it immediately.
2. **Commit trailers.** Pure addition, no behaviour change; makes the
   cross-reference detector possible.
3. **Gitea `pre-receive`.** The only unbypassable enforcement available.
4. **`core.hooksPath`** on the agent machines, plus its config-drift detector.
5. **`ledger_transport.py`**, then migrate callers one at a time.
6. **Phase 1 on one space.** Success is a *positive* signal, not a silence:
   for fourteen consecutive days, that space reports events published and
   converged per actor, zero seq gaps, chain verified, roots in agreement, and
   every rostered actor present. "The rescue machinery went quiet" is
   consistent with both success and a broken detector, and distinguishing those
   is the whole point.
7. **Delete** what nothing calls.

**Amendment obligation on DIP-0034.** The `member.add` / `member.remove` event
types resolved in §11 belong to DIP-0034's event vocabulary. This DIP does not
add them unilaterally; ratifying it obliges an amendment to DIP-0034 introducing
the two types and their payloads, in the same way DIP-0044 records its
supersession obligation over DIP-0034's key-custody sections.

Detectors precede the migration deliberately: they are what tell us whether the
migration worked.

## Open Questions
- **OQ-1.** Snapshot cadence and format — event count, wall clock, or
  size-triggered?
- **OQ-2.** Which machine projects a space in Phase 1, and what happens when two
  project concurrently? The refuse-to-overwrite guard detects it; nothing
  resolves it.
- **OQ-3.** Journals are genuinely co-authored (a real conflict occurred
  2026-08-10). Split per-actor and merge at read time, or accept conflicts?
- **OQ-4.** Claim latency equals the sync interval — currently 15 minutes, so
  two actors can both claim for that long. The HLC resolves it correctly and
  records the loser as a no-op; the cost is duplicated work. Is a shorter
  interval, or an eager push on claim, worth it?
- **OQ-5.** Do agent-personal spaces participate in the shared ledger, or keep
  their own?
- **OQ-6.** Is a satellite transport (rsync of `events/`, or HTTP) worth adding
  for `tris` and `data`, which hold partial checkouts and do not need full space
  history? §9 makes this a configuration change rather than a rewrite, but it is
  not obviously worth doing.
- **OQ-7.** Atomic publish (§10) costs a temporary file and a rename per event.
  At claim/complete frequency that is negligible; if event rate rises, batching
  appends within a bounded window may be needed, which reintroduces a window in
  which facts exist only locally.
- **OQ-8.** Effects have no artifact to verify against (§5). A service running,
  an email sent, a PR merged — how is any of that checked without re-reading the
  agent's own claim? Unsolved, and the reason side-effecting tasks finish in
  review rather than complete.
