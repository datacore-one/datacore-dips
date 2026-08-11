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
| **Relates to** | DIP-0011 (Nightshift — the `git push`-as-lock this replaces), DIP-0034 (Event Ledger Substrate — reserves this migration for its own DIP), DIP-0035 (Job Contracts — detector contracts), DIP-0043 (Org Projection), DIP-0018 (Credential Management), ENG-2026-0423-001, ENG-2026-0729-009, ENG-2026-0804-033, ENG-2026-0811-005 |

## Summary

Git carries only payloads that **cannot conflict**: append-only per-writer event
logs, and additive new files. Everything derived from the ledger is regenerated
locally rather than synchronised. Repositories are classified as **knowledge**
or **code**, and the two get different rules — knowledge commits directly to its
default branch, code goes through branch-and-review.

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

### 11. Snapshots

The fold replays every event from genesis. At 1,406 items and growing, replay
cost is linear in history forever. The ledger gains periodic **snapshots**: a
folded state at a known event, with the log retained so full history stays
recoverable. Snapshot cadence and format are deferred to implementation; the
requirement is that a snapshot never becomes the only copy of anything.

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
review. It is explicitly **out of scope** and keeps conventional git.

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
6. **Phase 1 on one space**, and observe whether the rescue machinery goes
   quiet.
7. **Delete** what nothing calls.

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
