# DIP-0043: Org Projection & Genesis Import

| Field | Value |
|-------|-------|
| **DIP** | 0043 |
| **Title** | Org Projection & Genesis Import |
| **Author** | Datacore Team |
| **Type** | Core |
| **Status** | Draft |
| **Created** | 2026-08-04 |
| **Updated** | 2026-08-04 |
| **Tags** | `org-mode`, `ledger`, `projection`, `genesis-import`, `migration`, `gtd`, `datacore-v2` |
| **Affects** | `<space>/org/next_actions.org` (becomes generated in Phase 1), `<space>/org/inbox.org` (exempt, unchanged), `.datacore/lib/ledger/` (new: `projector.py`, `genesis.py`, and the `item.clock.*` additions to `events.py`'s `EVENT_TYPES` this DIP requires), `.datacore/lib/org_workspace_adapter.py` and GTD MCP tools (write paths affected from Phase 1 onward — see Compatibility) |
| **Specs** | `.datacore/lib/ledger/*.py` ([DIP-0034](DIP-0034-event-ledger-substrate.md)), `org-mode-conventions.md`, the Rich Task Standard ([DIP-0009](DIP-0009-gtd-specification.md) Part 3.5) |
| **Agents** | `gtd-inbox-processor`, `gtd-inbox-coordinator`, `ai-task-executor`, `nightshift-orchestrator`, `context-maintainer`, `dip-preparer` |
| **Depends** | [DIP-0034](DIP-0034-event-ledger-substrate.md) — event schema, HLC, per-writer files, and fold semantics this DIP projects onto org and imports into via genesis. This DIP additionally requires two new `EVENT_TYPES` entries (`item.clock.start`, `item.clock.stop`) that DIP-0034's registry does not yet contain — see Specification and Compatibility. |
| **Amends (deferred, not in this PR)** | [DIP-0034](DIP-0034-event-ledger-substrate.md)'s Source-of-Truth Boundary (Summary / head of Specification) and Open Question 1, which both name "its own ratified DIP" as the prerequisite for any org-mode migration onto the ledger. This DIP is that prerequisite DIP. Per this drafting wave's rule, DIP-0034's file itself is not edited here — ratifying DIP-0043 requires a small follow-up edit to DIP-0034's boundary statement, tracked as a to-do in Implementation, not performed by this document. |
| **Relates to** | [DIP-0009](DIP-0009-gtd-specification.md) (GTD Specification — owns the org state vocabulary, Rich Task Standard, and file model this DIP projects), [DIP-0010](DIP-0010-external-sync-architecture.md) (External Sync Architecture — owns the "org-mode is the coordination layer / source of truth" claim this DIP proposes to retire for GTD tasks specifically), [DIP-0011](DIP-0011-nightshift-module.md) (Nightshift Module — its executor's direct writes to task files are the sharpest compatibility conflict this DIP creates, see Compatibility), `ENG-2026-0727-004` (duplicate resurrection / ID-conflict churn), `ENG-2026-0423-001` (git-lock silent failure) |

## Summary

DIP-0034 built an append-only, hash-chained, per-writer event ledger and then explicitly excluded GTD tasks from it, leaving org-mode files as the multi-writer mutable state they always were. This DIP finishes the job DIP-0034 started: it defines a schema for projecting `item.*` ledger events onto org-mode task files, a genesis import that folds the *existing* corpus of active org tasks into the ledger without discarding their identity, and a three-phase migration (shadow projection → read-only generated file with a refuse-to-overwrite guard → org-edit reconciler) that gets from today's hand-edited `next_actions.org` to a generated one without a flag-day cutover or an unverified leap of faith. `inbox.org` is exempt throughout — it stays the single, frictionless, append-only capture surface it already is.

## Agent Context

### When to Reference This DIP

**Always reference when:**
- Implementing, reviewing, or extending the projector (`ledger/projector.py`) or the genesis importer (`ledger/genesis.py`) — this DIP is the schema, phase-gate, and refuse-to-overwrite contract they must satisfy.
- Deciding whether a new org property or task field belongs in the ledger's first-class schema or stays opaque payload — the (a)/(b)/(c) criterion in Specification is the disambiguation rule, not ad hoc judgment.
- Migrating any agent or tool that currently writes directly to `next_actions.org` (`gtd-inbox-processor`, `ai-task-executor`, `nightshift-orchestrator`, the GTD MCP tools) — once Phase 1 lands for a given space, direct writes to that space's `next_actions.org` are a bug, not a feature; the write path is `EventLog.append()` plus a projector run, not a file edit.
- Touching DIP-0034's `EVENT_TYPES` registry — this DIP is the reason `item.clock.start`/`item.clock.stop` need to be added to it (see Specification, Compatibility).
- Evaluating whether Phase 0→1 or Phase 1→2 is safe to flip — the gate is N consecutive days of exact shadow-diff equivalence (Phase 0→1) and a working reconciler with test coverage (Phase 1→2), not a calendar date.
- Wiring `/process-inbox` or `gtd-inbox-processor` for a migrated space — the content-hash identity rule in Inbox Processing is the load-bearing mechanism against reproducing the duplicate-resurrection failure class inside the ledger; do not key a routed entry's `item.create` on a freshly-minted random id.
- Implementing or reasoning about any GTD MCP tool's write path (`add_task`, `complete_task`, `set_task_state`, `write_clock_entry`, `archive_tasks`) — see Write Path for the call-site-by-call-site mapping from today's direct file write to event emission.
- Deciding when the projector should run — see Projection Timing; a timer-only design is explicitly rejected here, not merely unspecified.

### Quick Reference for Agents

| Question | Answer |
|----------|--------|
| Is `next_actions.org` still hand-editable? | Phase 0: yes, unchanged. Phase 1: no — generated, `chmod 444`, edits refused by the projector's guard. Phase 2: yes again, via the reconciler. |
| Is `inbox.org` ever projected or made read-only? | No, in any phase. It remains the single capture point, append-only, forever exempt — see Specification. |
| Where do org-derived ledger events live? | `<space>/.datacore/events/<actor>.jsonl`, same per-writer files DIP-0034 defines. Genesis import writes to its own dedicated `genesis.jsonl`. |
| What is a ledger item's org `:ID:`? | The same `:ID:` org-workspace's `ensure-ids` already assigned — genesis import reuses it verbatim as the ledger item id. No remapping. |
| What happens to a task with no `:CREATED:` property? | The three-rung valid-time fallback ladder in Specification: `:CREATED:` → first git-history appearance of its `:ID:` → a single documented genesis timestamp. Never silently invented. |
| Are CLOCK entries and LOGBOOK hand-editable post-Phase-1? | No — CLOCK becomes `item.clock.start`/`item.clock.stop` events; LOGBOOK is rendered by the projector from event history, never an independent write surface. |
| Are SCHEDULED repeaters (`+1w` etc.) handled yet? | No — Open Question, unresolved, explicitly deferred (see Open Questions). The real `next_actions.org` corpus has zero live repeater instances today, so this does not block Phase 0/1 for that file. |
| What breaks for nightshift once Phase 1 lands? | Its direct writes of `QUEUED`/`WORKING`/`REVIEW`/`FAILED` overlay states into task files must migrate onto event emission in the same wave, or they will be refused by the projector's guard — see Compatibility. |
| Do `add_task`/`complete_task`/etc. change name or signature? | No — only their implementation changes, from direct file writes to event emission. See Write Path. |
| How does routing a stale, twice-processed inbox entry avoid creating two ledger items? | The emitted `item.create` is keyed on a content hash of the normalized entry (heading + body), the same identity primitive DIP-0038's `materialize()` uses — reprocessing computes the same id, and the fold treats the second `item.create` as a no-op. See Inbox Processing. |
| Does the projector run on a timer only? | No — eagerly after any local event append (so a just-created task appears immediately), plus periodically to absorb events synced in from other machines. See Projection Timing. |

### Related Agents

| Agent | Relationship to This DIP |
|-------|---------------------------|
| `gtd-inbox-processor` | Currently writes new tasks directly into `next_actions.org` during routing (DIP-0009 Part 1/Part 3.7). Once Phase 1 lands for a space, this agent's write path becomes "classify, emit a content-hash-keyed `item.create`, let the projector render it" — inbox processing becomes the ledger's ongoing entry point, not just org's. See Inbox Processing for the identity mechanism this agent must implement. |
| `gtd-inbox-coordinator` | Batch orchestrator over `gtd-inbox-processor`; inherits the same write-path change, applied per entry. |
| `ai-task-executor` | Scans `next_actions.org` for `:AI:`-tagged tasks and writes overlay-state transitions directly (DIP-0009 Part 2/4). This is the other half of the nightshift compatibility gap — see Compatibility. |
| `nightshift-orchestrator` (nightshift module) | Owns the claim/execute/complete write cycle DIP-0034 was designed to eventually replace (per DIP-0034's own Related Agents table). This DIP is the first concrete step of that replacement for the GTD task class specifically; nightshift's direct file writes are the sharpest compatibility conflict Phase 1 creates. |
| `context-maintainer` | Owns the follow-up (see Implementation) to update the `Org-Mode-as-Coordination-Layer` zettel and CLAUDE.base.md's "org-mode for AI" principle once this DIP starts landing phases, since Phase 1 makes the "org-mode is the source of truth" claim in DIP-0009/DIP-0010 conditionally false for whichever spaces have migrated. |
| `dip-preparer` | Treats this DIP, alongside DIP-0034, as the schema and migration-phase contract when authoring any further org-projection follow-on work. |

### Integration Points

- [DIP-0034: Event Ledger Substrate](DIP-0034-event-ledger-substrate.md) — the substrate this DIP projects onto org and imports the existing corpus into; this DIP requires a small registry amendment (two new `EVENT_TYPES`) that DIP-0034's text does not yet contain.
- [DIP-0009: GTD System Specification](DIP-0009-gtd-specification.md) — owns the org state vocabulary, Rich Task Standard, file model, and the execution-overlay states this DIP's `state` field and genesis-import scope must reconcile with.
- [DIP-0010: External Sync Architecture](DIP-0010-external-sync-architecture.md) — owns the "org-mode is the coordination layer / source of truth for all content" claim this DIP is the ratified proposal to narrow, for GTD tasks, in the phases below.
- [DIP-0011: Nightshift Module](DIP-0011-nightshift-module.md) — the execution overlay-state writer whose direct file access this DIP's Phase 1 guard puts in direct conflict; migrating it is out of this DIP's scope but is a named, load-bearing dependency of Phase 1 actually being safe to flip on for any space that runs nightshift (i.e., all of them).
- [DIP-0038: Action Loop & Co-Sign Policy](DIP-0038-action-loop-cosign.md) — source of the `item_id()` content-hash identity primitive (normalize, sha256, first 16 hex chars) and the fold-level "already exists at any status, skip" dedupe rule this DIP's Inbox Processing section reuses, with one corpus-driven refinement (hash the full entry, not the heading alone).

## Motivation

### The ledger, as shipped, does not touch the problem that motivated it

DIP-0034's own Motivation names two recurring failure classes: **duplicate
resurrection / ID-conflict churn** (`ENG-2026-0727-004` — the Mac and the box
each mint their own `:ID:` for headings that lack one, so the same logical
task ends up under two different IDs and every sync conflicts on pure
metadata) and **git-lock silent failure** (`ENG-2026-0423-001` — nightshift's
`git push`-as-claim failed silently for three days, reporting "Complete! 0
tasks, 0 errors"). DIP-0034's diagnosis for both was exactly right: **there is
no durable, append-only record of "what was attempted and by whom" that
survives independently of the mutable projection the write was trying to
update.**

Then DIP-0034 built that record — for a *disjoint* class of objects. Its
Source-of-Truth Boundary states plainly: "org-mode remains the coordination
layer and the system of record for GTD tasks... this DIP does not change that
and defines no migration of org state." That boundary was the right scope cut
for a first substrate DIP. But it means the actual org files that produced
`ENG-2026-0727-004` and `ENG-2026-0423-001` — `next_actions.org`, `inbox.org`
— are untouched by any of it. They are still headings mutated in place by
whichever process reads them, IDs still assigned independently per reader,
still exactly the multi-writer mutable state that caused the sync-conflict
genre in the first place. **The event ledger, as shipped in v2, does not
solve the problem that motivated it.** DIP-0034's own Open Question 1 says as
much: org-file projection was "deliberately out of v2 scope," deferred to
"v2.1," and would "itself require its own ratified DIP." This is that DIP.

The evidence that the underlying problem is still live is not hypothetical —
it is a standing directory of repair scripts, each written because org files
have no concept of "the same task, seen twice" independent of re-inferring
identity from content on every read:

- **`inbox_dedup.py`** — removes `inbox.org` entries already routed
  elsewhere, because a stale capture snapshot silently resurrects everything
  a prior `/process-inbox` run removed. Its own docstring records a concrete
  2026-07-26 incident: a routing run processed 187 entries and returned
  `inbox.org` to empty; a stale capture re-added 1,512 lines ninety minutes
  later, and because a subsequent `ensure-ids` assigns the resurrected
  copies *fresh* IDs, `dedup_ids()` could no longer see them as duplicates —
  "headings are the only reliable join key" is the tool's own stated
  fallback, which is precisely the "identity inferred from content on every
  read" failure mode DIP-0034's Motivation names.
- **`inbox_dedup_verify.py`** — a second script whose existence is itself
  evidence: the dedup logic above needed an independent verifier because
  content-keyed dedup on mutable files is not trustworthy enough to run
  unchecked.
- **`org_resolve_id_conflicts.py`** — resolves git merge conflicts that are
  *only* competing auto-assigned `:ID:` values, because two machines
  (datacore-app's daemon and `ensure-ids` on the box) each invent a different
  UUID for the same heading when it lacks one, and "the next sync conflicts
  on pure metadata — no human decision is involved," per its own docstring.
- **`reconcile_sync_merge.py`** — resolves Mac↔nightshift-server merge
  conflicts on GTD org files specifically, because "a blind union would
  resurrect archived tasks" — the server's file and the laptop's file are
  both plausible "current state," and there is no principled way to decide
  which without a human-authored heuristic (take server, re-append
  local-only capture subtrees).
- **`repair_nightshift_org.py`** — removes duplicate properties and fixes
  orphaned blocks in `nightshift.org` after concurrent writers corrupt it.

Five scripts, all solving variants of one problem: **org files are
multi-writer mutable state, and mutable shared state has no way to
distinguish "the same task, seen twice" from "two different tasks," or to
recover cleanly when two writers touch it at once.** Keeping org as source of
truth — which is exactly what DIP-0034 chose to do, correctly, for its own
scope — leaves every one of these failure classes fully intact for the actual
GTD task corpus. This DIP is not a hypothetical extension; it is the
completion the original ledger-mindset direction (`ENG-2026-0729-016`) was
always going to need, and DIP-0034's own text says so.

### This DIP engages DIP-0009 and DIP-0010 directly, not by silent omission

DIP-0009 states as a Core Principle: "Org-mode as source of truth — External
tools sync to org-mode, not vice versa." DIP-0010 states it more strongly:
"Org-mode serves as the internal coordination layer and source of truth for
all content... Single source of truth: Org-mode is authoritative, external
tools are mirrors." Both are correct descriptions of the system as built, and
neither is casually overridden here. This DIP does not declare org-mode wrong
— it proposes a **phased, reversible, evidence-gated** migration of one
specific file class (`next_actions.org`) from "source of truth" to
"generated projection of a source of truth," while leaving `inbox.org`
untouched in every phase specifically *because* DIP-0009's "single capture
point" principle is correct and this DIP has no intention of weakening it.
Where this DIP's design departs from DIP-0009/DIP-0010's current text, that
departure is argued in Specification and Compatibility, not asserted by
omission — and the amendment those two DIPs will eventually need (narrowing
"org-mode is source of truth" to "org-mode is source of truth for
unmigrated spaces/files") is named explicitly in Implementation as follow-up
work, not silently implied.

## Specification

### Schema principle: do not hand-pick fields

A field is **first-class** — subject to schema validation, folded into
`LedgerState`, queryable without parsing the payload — iff at least one of:

**(a)** two actors can conflict over it (the DIP-0034 concern: concurrent
writers racing on the same field is exactly what a fold-level precondition
check exists to arbitrate);
**(b)** the system must query or filter on it without parsing the opaque
payload (agenda views, `items_by(status=, owner=)`, tag filters);
**(c)** it drives routing or policy (queue ordering, arbitration, effect
gating).

Everything else is **opaque payload** — the projector writes it back
verbatim, unparsed, unvalidated beyond "is this valid JSON/text." This is
what stops the ledger schema becoming a reimplementation of org-mode: the
temptation, once you start modeling org tasks as events, is to model *every*
org feature as a first-class field, and the criterion above is the discipline
against that (see Rejected Alternatives).

### First-class fields

| Field | Org representation | Criterion | Real-corpus note |
|---|---|---|---|
| `id` | `:ID:` property | (a) identity conflicts, (b) primary key | 502/502 active tasks already carry one — see Round-Trip Analysis |
| `state` | TODO-keyword | (a), (b) | See "State scope" ruling below — human states only for genesis; overlay states are a known gap |
| `owner` | no current org equivalent for personal spaces; `:OWNER:` for team spaces | (a), (c) | 1 occurrence in `0-personal/org/next_actions.org` — genuinely new for personal-space usage |
| `arbiter` | none today | (c) | Only load-bearing once the claim–grant handshake (a sibling amendment in this drafting wave, out of this DIP's scope) applies to org-derived items; Phase 1 default is arbiter = the human, i.e. effectively self-arbitrated |
| `parent` | heading nesting (Tier `*` > Focus Area `**` > Task `***` > Subtask `****`, or none) | (a) tree reconstruction, (b) | **Mandatory** — see ruling below; 54/502 (10.8%) of active tasks are top-level with no task ancestor at all |
| `scheduled` | `SCHEDULED:` timestamp | (b), (c) agenda queries | 213/502 (42.4%) populated |
| `deadline` | `DEADLINE:` timestamp | (b), (c) warnings | 0/502 populated in this corpus — first-class per criterion, structurally unexercised today (see Round-Trip Analysis) |
| `tags` | `:tag1:tag2:` | (b) filtering/routing, (c) | 502/502 (100%) populated — heaviest-used field in the corpus |
| `effects` | none in org today | (c) policy (DIP-0038) | Not populated by genesis import; reserved |
| `space` | which `<space>/org/next_actions.org` the task lives in | (a), (b) | Not an org property — derived from which space's event/org tree the item belongs to |
| `title` | heading text with state-keyword and tags stripped | (a), (b), (c) | |

**Opaque payload** (written back verbatim, never validated): body text,
`:CONTEXT:`, `:KEY_FILES:`, `:CURRENT_STATUS:`, `:ACCEPTANCE_CRITERIA:`,
`:TOOLS:`, `:ROLE:`, `:SOURCE:`, `:EFFORT:`, `:WAITING_ON:`,
`:CANCEL_REASON:`, `:DEADLINE_WARNING_DAYS:`, `:EXTERNAL_ID:`,
`:EXTERNAL_URL:`, `:SYNC_STATUS:`, `:SYNC_UPDATED:`, `:DEPENDS_ON:`, and any
property not named above.

**Why `:DEPENDS_ON:` stays payload despite arguably meeting criterion (c).**
DIP-0009 Part 3.8 resolves BLOCKS/AFTER references by looking up `:ID:`
properties **"across all tasks in the current nightshift.org queue
(queue-local scope)"** — not a global, system-wide routing key. Applying the
criterion honestly: it drives ordering only within one transient queue build,
not fold-level or cross-writer routing, so it fails (c) as currently
specified and stays opaque. If queue ordering is ever promoted to a
ledger-wide concern, that is its own future amendment, not a default this
DIP takes.

**Why `:WAITING_ON:` stays payload despite DIP-0009 calling it "Required" for
the `WAITING` state.** The real corpus shows why promoting it would be
wrong today: only 2 of the 4 currently-`WAITING` tasks in
`0-personal/org/next_actions.org` actually carry a `:WAITING_ON:` value — the
"required" property is not mechanically enforced anywhere upstream. Schema
validation on a field the corpus violates 50% of the time would either reject
real data or need a permissive escape hatch that defeats the point of
validating it; opaque payload is the honest fit until upstream enforcement
exists.

### Specific rulings

**`parent` is mandatory.** Org tasks are hierarchical (Tier → Focus Area →
Task → Subtask, per DIP-0009 Part 3); without a `parent` pointer the
projector cannot rebuild that tree from the event log alone. "Mandatory"
means the field is never absent or "TBD" — including for the 10.8% of active
tasks that are genuinely top-level. This DIP's ruling on the mechanism: an
item's `parent` is either (a) the ledger id of its nearest stateful ancestor
task, or (b) a **structural sentinel** — a stable, deterministically-derived
identifier (namespaced distinctly from real item ids, e.g. `struct:<slug of
the heading path>`) for a non-stateful ancestor heading (a Tier or Focus Area
heading such as `** /Verity`, which carries no TODO keyword and is never
itself an `item.create`), or (c) `struct:root` for a task with no ancestor
heading at all. Structural sentinels nest under other structural sentinels or
`struct:root`, so the tree is always fully reconstructible with no dangling
references, and no task is ever forced to fabricate a fake parent task just
to satisfy the mandatory-field rule.

**Clock entries are events, not payload.** `item.clock.start` /
`item.clock.stop` (payload: `{item, note?}`) — clocking is genuinely
concurrent (a task can be clocked from more than one machine in principle)
and would silently conflict as an opaque blob the way a bare LOGBOOK edit
does today. **This requires DIP-0034's `EVENT_TYPES` registry to admit two
new entries it does not currently have** — DIP-0034 Invariant 6 makes payload
dicts additive per existing event type, but a wholly new event *type* is a
registry change, not a payload addition, and is out of this DIP's authority
to make by itself (see Compatibility and Implementation for how this gets
requested).

**LOGBOOK is generated, not stored.** Org's state-change/clock log is a
*rendering* of the event history — `item.clock.*` events plus state
transitions — not an independent write surface once Phase 1 lands. That the
two representations coincide today (the file already has 24 LOGBOOK drawers
and 17 CLOCK lines that are, in every case observed, exactly what a
mechanical fold of "this task was clocked from timestamp A to timestamp B"
would produce) is evidence the model fits the data, not a coincidence to
preserve as a separate hand-maintained artifact.

**Repeaters (`+1w`, `.+7d`, `++1w`) are an Open Question, not resolved
here.** Does `item.complete` on a repeating item synthesize the next
occurrence (fold-time, deterministic, matches DIP-0009 Part 3.6's
"flipping it DONE moves it forward" semantics), or does something outside
the fold do it? This DIP does not decide, and states plainly that it must be
decided **before schema freeze**, not deferred past it — see Open Questions.

### Round-trip analysis against the real corpus (required, not argued)

Run against `0-personal/org/next_actions.org` as it exists today (7,840
lines, 724 headings: 105 Tier, 547 Focus-Area/task-mixed, 61 explicit `***`
task level, 11 `****` subtasks), queried via `org_workspace.Query`
(`by_state('TODO','NEXT','WAITING')`) — not by raw grep, per this
installation's own convention that org queries go through org-workspace.

| Check | Result | Implication for this DIP |
|---|---|---|
| Active tasks (TODO/NEXT/WAITING) | **502** | The genesis-import population for this one file |
| `:ID:` coverage on active tasks | **502/502 = 100%** | `ensure-ids` has already run system-wide; the "reuse org `:ID:` as ledger id, no remapping" design has **zero** tasks needing new-id minting on this corpus — strong empirical validation, not a hopeful assumption |
| `:CREATED:` coverage on active tasks | **484/502 = 96.4%** (18 missing) | The valid-time fallback ladder is not a theoretical nicety — it resolves 18 real tasks today. Verified directly: for task `org-20260617-061332-bf14657e` (no `:CREATED:`), `git log -S"org-20260617-061332-bf14657e" --format=%ai` on the `0-personal` repo returns `2026-06-17 06:13:40 +0000` — 8 seconds after the ID's own embedded timestamp, i.e. rung 2 of the ladder works and lands almost exactly on the true event |
| Tasks with a task-level `parent` | **448/502 = 89.2%** (54 top-level) | Confirms the sentinel mechanism above is load-bearing, not a corner case — over 1 in 10 active tasks needs it |
| Depth distribution of active tasks | 54 depth-0 (top-level), 403 depth-1, 43 depth-2, 2 depth-3 | The overwhelming majority nest exactly one level under a structural (Tier/Focus-Area) ancestor — validates that structural sentinels, not real parent items, will be the common case |
| Tag coverage on active tasks | **502/502 = 100%** | Tags must round-trip losslessly; zero tolerance for drift here — this is the most heavily populated field in the corpus |
| `SCHEDULED` coverage | **213/502 = 42.4%** | Well-exercised first-class field |
| `DEADLINE` coverage | **0/502 = 0%** | First-class per the (a)/(b)/(c) criterion (query/warning behavior is specified in DIP-0009 Part 8.1), but **structurally unexercised** in this file — the projector must round-trip "field defined, never populated" cleanly, not special-case it |
| Genuine `SCHEDULED` repeater syntax | **0** occurrences in `next_actions.org` (the one grep hit on `+90d`-shaped text was inside a `:CONTEXT:` multiline property, not repeater syntax; `habits.org`, a separate file, has 30 real repeater instances) | The repeater Open Question is real but does not block Phase 0/1 for this specific file; `habits.org` is out of this DIP's initial scope |
| CLOCK/LOGBOOK on active tasks | **0/502** (all 17 CLOCK lines / 24 LOGBOOK drawers in the file are on already-DONE, out-of-scope tasks) | Genesis import (active-tasks-only) never has to convert a real CLOCK entry on day one; the clock-as-events mechanism's first real test comes from ongoing operation post-cutover, not from the import itself |
| `:WAITING_ON:` compliance on `WAITING` tasks | **2/4 = 50%** | Direct evidence that DIP-0009's "required" is aspirational, not enforced — the reason this field stays opaque payload rather than a validated first-class field (see above) |
| `:EFFORT:` property casing | **100% consistent** (`:EFFORT:`, 353/353 instances) despite DIP-0009's own text using both `:EFFORT:` and `:Effort:` across different Parts | A round-trip risk that turned out **not** to be real on this corpus — worth recording so a future author doesn't re-litigate it without checking |
| `:EXTERNAL_ID:` (DIP-0010 sync linking) | **1** occurrence file-wide | DIP-0010's external-sync properties are essentially unused in practice on this corpus; no meaningful interaction expected between this DIP and DIP-0010's sync adapters for now |
| Archive files already exist as separate sibling files | `next_actions_archive.org`, `next_actions.org_archive`, `next_actions_archive_archive.org`, three `inbox-archive-*.org` snapshots, `nightshift-parked-archive-2026-07-01.org`, `_archive/` directory | The "archives stay as files, historical not coordinated" scoping decision below is not a new imposition — it is already how this corpus behaves; the doubled `_archive_archive` filename is itself a small, ironic data point for how much this system already relies on manual/scripted file-based archiving drifting over time |

**What a Phase 0 round-trip would actually lose or change, stated plainly**
(this is a predictive analysis grounded in the numbers above, not an executed
diff — the projector does not exist yet; building it and shipping the actual
diff is Phase 0's own acceptance gate, see Migration Phases):

1. The 18 tasks missing `:CREATED:` would gain a fallback-ladder timestamp on
   projection — a rendering *addition*, not a loss, since org never had
   ground truth there either.
2. Every active task's `parent` becomes an explicit field (real id or
   `struct:` sentinel) where today it is implicit in heading nesting — no
   information lost, but the *representation* changes, and any tool that
   currently infers hierarchy from raw indentation (rather than via
   org-workspace's `NodeView.parent`) would need to read the new field
   instead.
3. **41 tasks currently in `REVIEW` state** (an execution-overlay state per
   DIP-0009 Part 2, not one of TODO/NEXT/WAITING) fall **outside** this DIP's
   declared genesis-import scope of "active tasks (TODO/NEXT/WAITING)" — see
   the known gap called out under Genesis Import below. This is a real,
   non-trivial exclusion on the actual corpus, not a hypothetical edge case,
   and it is surfaced here rather than discovered later.

### Migration phases

**Phase 0 — shadow.** The projector runs read-only against the event log and
writes `next_actions.projected.org` **alongside** the real file — zero
behavior change, nothing existing is touched. A nightly job diffs the
projected file against the real one. Flip to Phase 1 only after **N
consecutive days of exact equivalence** — the same overlap-then-cutover
discipline DIP-0035's job-contract pattern established (`job_verify.py` ran
report-only alongside every existing watchdog, and `cos_verify_morning.py`
was retired only after 7 consecutive green days, "a deliberate overlap
period rather than a flag-day cutover, so a gap does not silently
reintroduce the exact failure genre this DIP exists to close" — DIP-0035
Rollout Plan). This DIP does not pin N; it is a rollout-time operational
decision, but it must be an explicit, observed number, not a date on a
calendar.

**Phase 1 — read-only org.** `next_actions.org` becomes generated.
Enforcement is belt-and-braces, in order of how easy each layer is to
bypass:
1. A `# GENERATED — edits will be overwritten` header at the top of the file
   (advisory; the weakest layer, but the first thing a human sees).
2. `chmod 444` on the file (an actual OS-level write block; stops accidental
   saves from tools that don't check the header).
3. **The projector refuses to overwrite a file whose content has changed
   since it last wrote it.** Mechanism: the projector records the hash of
   what it last wrote (e.g. `<space>/.datacore/state/ledger/projections/
   next_actions.org.hash`) — not relying on file mtime alone, which does not
   survive git checkouts or rsync reliably. Before writing, it re-hashes the
   file on disk; if that hash does not match the recorded one, something
   other than the projector touched the file since — the projector aborts,
   writes the would-be output to a sibling conflict file (e.g.
   `next_actions.conflict.org`) instead of the real path, and surfaces the
   conflict (journal entry, `/today` briefing) rather than silently
   clobbering whatever the human or another process wrote. This is the guard
   that converts "you lost work" into "the system told you" — the single
   most load-bearing mechanism in this DIP, because layers 1 and 2 above are
   both bypassable (a human can `chmod` it back, or edit through a tool that
   doesn't respect the header) and layer 3 is not.

**Phase 2 — reconciler.** Org edits (made through the conflict path above,
or after Phase 1's enforcement is deliberately relaxed for this phase) are
diffed against the last-known projection and translated into `item.*`
events; only once that reconciler exists and is tested does org become
freely writable again. This is explicitly the hardest, least-specified phase
in this DIP — see Open Questions for what it still needs (a field-level
diff strategy consistent with the first-class/opaque split above, and
possibly its own small ledger amendment for opaque-payload updates, since
DIP-0034 has no generic "update an existing item's payload" event today).

**`inbox.org` is exempt in all three phases.** It is never projected, never
made read-only, never rewritten by the projector. The reasoning is layered:

- **Appends cannot conflict.** This is the exact same property that makes
  DIP-0034's per-writer files safe without a lock — an append-only surface
  has no overwrite hazard by construction, so there is nothing for a
  refuse-to-overwrite guard to protect against. `inbox.org` was already
  structurally safe; this DIP simply declines to "fix" something that was
  never broken.
- **The single-capture-point principle survives untouched.** DIP-0009's
  Core Principle #2 and CLAUDE.base.md's "Single capture point" both name
  `inbox.org` as sacred. Projecting or restricting it would be this DIP
  quietly overriding a principle it explicitly said (in Motivation) it was
  not trying to override.
- **Inbox→next_actions processing becomes the ledger's entry point.** Once
  Phase 1 lands for a space, `gtd-inbox-processor` routing a captured item
  out of `inbox.org` is the moment an `item.create` event is emitted — the
  existing human-triggered processing pipeline becomes the genesis point for
  every *newly* captured task, symmetrically with how genesis import (below)
  is the one-time genesis point for the *existing* corpus.
- **Requiring a CLI for capture would kill the migration on friction
  alone.** `inbox.org`'s entire value is zero-friction capture — mobile
  quick-jots, email forwards, voice notes transcribed straight into the
  file. Routing capture itself through `ledger_cli.py append` would
  reintroduce exactly the friction "single capture point, no exceptions"
  exists to eliminate, and for a system with one active owner, killing
  capture friction is existential to whether this migration gets adopted at
  all — not a nice-to-have deferred to a later phase.

### Genesis import

**Scope.** Phase 1's genesis import (the one-time fold of the *existing*
corpus into the ledger) covers **active tasks only**: `TODO`, `NEXT`,
`WAITING` per DIP-0009's canonical human-flow states. Archives (`DONE`,
`CANCELLED`, and everything already living in a sibling `*archive*.org` file
— see the round-trip table above for the actual list on this corpus) stay as
files: historical record, not coordinated state. They are not imported,
not projected, and not made read-only.

**Known gap, stated plainly rather than discovered later.** DIP-0009 Part 2's
execution-overlay states (`QUEUED`, `WORKING`, `REVIEW`, `FAILED`) are
neither "active" (TODO/NEXT/WAITING) nor terminal/archived — and the real
corpus has **41 tasks sitting in `REVIEW`** right now. As scoped, genesis
import does not touch them; they remain ordinary org rows, outside the
ledger, until they next transition to a human state (`DONE`, `NEXT` via
requeue, `CANCELLED`) — at which point Phase 2's reconciler (or a
follow-up ruling made before Phase 1 enforcement goes live, since 41 tasks
frozen mid-review by a read-only file is a real operational cost) needs to
pick them up. This DIP does not resolve that ruling; it names it as a
concrete, numbered gap rather than leaving it implicit.

**Identity: reuse the existing org `:ID:` as the ledger item id.**
`org-workspace`'s `ensure-ids` already guarantees active tasks have one — the
round-trip analysis above found **100% coverage, 502/502**, meaning genesis
import for this corpus needs to mint **zero** new ids. No remapping, stable
identity across the org/ledger boundary, and the import is idempotent
because it is keyed on an id that already exists and never changes.

**Valid-time fallback ladder**, applied in order, documented explicitly so no
timestamp is ever silently invented:
1. The task's `:CREATED:` property, if present (484/502, 96.4%, on the real
   corpus).
2. First appearance of the task's `:ID:` string in git history — `git log
   -S"<id>" --format=%aI -- <file> | tail -1` (a pickaxe search on the exact
   ID string, since ID assignment happens once at `ensure-ids` time and is
   stable thereafter). Verified directly against one of the 18 real
   `:CREATED:`-missing tasks (id `org-20260617-061332-bf14657e`): pickaxe
   returns `2026-06-17 06:13:40 +0000`, eight seconds after the id's own
   embedded assignment timestamp — the rung works and lands almost exactly
   on the true event on this corpus.
3. A single genesis timestamp — the moment the import run itself executes —
   used only when both rungs above are unavailable (e.g. a task whose
   `:CREATED:` is missing and whose file predates the space's git history,
   or was never committed before the ID was assigned). This DIP requires the
   import tool to record *which* rung produced each task's valid time, so
   "rung 3 was used" is itself an auditable fact, not a silent default.

**Emitted by a dedicated `genesis` actor.** Genesis import writes to its own
per-writer file, `<space>/.datacore/events/genesis.jsonl`, the same
per-writer convention DIP-0034 already defines — `genesis` is simply another
actor name. One property is unusual and worth documenting explicitly: this
actor writes **exactly once**, at cutover, and then never appends again.
Nothing in DIP-0034's design assumes an actor writes continuously, so this
is consistent with the substrate, not a special case bolted onto it — but a
future reader auditing "why does `genesis.jsonl` never grow" should find the
answer here, not have to infer it.

**Idempotence.** Because import is keyed on an id that already exists and is
stable, re-running the genesis importer for a task whose id already has a
genesis-authored `item.create` must be a no-op. This DIP places that guard in
the **importer itself** (skip ids already present in `genesis.jsonl`) rather
than relying solely on DIP-0034's fold-level "earliest HLC wins" behavior for
duplicate `item.create`s as the only defense — DIP-0034's fold semantics
describe earliest-wins behavior for competing operations generally but do
not explicitly specify duplicate-`item.create` handling, and this DIP
follows the substrate's own house style (guard early, don't rely solely on
downstream tolerance) rather than assume that gap resolves the way this DIP
needs it to.

**Acceptance test: round-trip equivalence.** Import the corpus, project it
back to org, diff against the original file. **Ship the diff in the DIP** —
this DIP ships the *predictive* version of that diff (the round-trip
analysis table above, built directly against the real corpus without the
projector existing yet, which is the honest ceiling of what a Draft DIP with
nothing built can demonstrate); running the projector for real and shipping
the actual byte-level diff is Phase 0's own deliverable and acceptance gate,
named explicitly in Implementation.

## Write Path

**The single most important compatibility fact in this DIP, stated
prominently rather than left to be inferred from Compatibility below: the
existing interfaces do not change. Only their implementations do.**
`datacore.gtd.add_task`, `complete_task`, `set_task_state`,
`write_clock_entry`, and the `/process-inbox` command all keep their current
names, arguments, and return shapes. What changes, once Phase 1 is live for
a space, is what happens *inside* each of them:

| Call site | Today | Once Phase 1 is live |
|---|---|---|
| `datacore.gtd.add_task` | Appends a heading to `next_actions.org` (or `inbox.org`) directly | Emits `item.create` (content-hash-keyed if the entry has no pre-existing `:ID:` — see Inbox Processing), then relies on eager projection (see Projection Timing) for the new task to appear |
| `datacore.gtd.complete_task` | Flips the state keyword to `DONE`, writes `CLOSED:` | Emits `item.complete`; the projector renders the resulting `DONE` state and `CLOSED:` timestamp |
| `set_task_state` (`WAITING`, `DEFERRED`, etc.) | Rewrites the state keyword in place | Emits the corresponding `item.*` transition event |
| `write_clock_entry` | Writes a `CLOCK:` line into the task's `:LOGBOOK:` drawer directly | Emits `item.clock.start`/`item.clock.stop` (Specification's "clock entries are events" ruling) — this is the one call site that collides head-on with a first-class ruling in this DIP, not just a plumbing change |
| `archive_tasks` | Moves a `DONE`/`CANCELLED` heading from `next_actions.org` to `archive.org`, in one file operation | Splits into two: the item's terminal state is already ledger-recorded (`item.complete`/`item.dismiss`), so the projector simply stops rendering it into the generated file; the move-to-`archive.org` half remains a direct file write, because `archive.org` is not projected or made read-only by this DIP (genesis import scope is active tasks only — see Specification) |
| `gtd-inbox-processor` / `/process-inbox` | Classifies, routes (appends to destination file), clears `inbox.org` | Classifies, emits `item.create`, clears `inbox.org` — see Inbox Processing for the identity hazard this specific call site has to handle |

**Reads are free; only writes need re-pointing, and this is the reason the
migration is affordable rather than a rewrite.** `org_workspace.Query`,
`agenda`, `deadline_warnings`, `project_health`, `duplicate_check`,
`effort_aggregate`, `list_next_actions` — every read-side GTD MCP tool and
every external reader (Emacs, orgzly, DIP-0010's sync adapters) keeps working
completely unmodified, because they all read whatever valid org-mode content
is on disk, and Phase 1's file is still valid, parseable org-mode — it simply
happens to be generated now instead of hand-written. None of the read
ecosystem this installation already depends on needs to know a projector
exists.

## Inbox Processing

Today, `/process-inbox` reads `inbox.org`, classifies each entry (DIP-0009
Part 1's Clarify stage), routes it to a destination file — almost always
`next_actions.org` — and returns `inbox.org` to empty. Under projection, the
routing half of that changes: **classify each entry → emit `item.create` →
then clear the processed lines from `inbox.org`.** `inbox.org` itself stays
exempt and append-only in every phase (Specification); what changes here is
only what "routing an entry out" means once the destination is generated
rather than hand-appended.

**The hazard is the one that already bites this installation, and this DIP
names it explicitly rather than assume the ledger fixes it for free.**
`inbox_dedup.py`'s own docstring records the 2026-07-26 incident this DIP
cites in Motivation: a routing run processed 187 entries and returned
`inbox.org` to empty, then a stale capture snapshot resurrected 1,512 lines
ninety minutes later — and because a later `ensure-ids` mints **fresh**
random ids for the resurrected copies, nothing downstream could see them as
duplicates. Naively porting today's identity behavior into `item.create`
reproduces this exactly: DIP-0009 Part 3.7 mints a fresh `uuid.uuid4()` for
any inbox entry that lacks an `:ID:` at enrichment time, and a `uuid4()` is,
by design, unrelated to its input — two machines classifying the same stale
inbox snapshot would each mint a *different* random id for the *same* real
entry and emit two `item.create`s for what is actually one task. The ledger
would then durably and verifiably record the exact duplication it exists to
prevent.

**Solution: key each `item.create` emitted from inbox processing on a
content hash of the normalized entry — the same identity primitive
[DIP-0038](DIP-0038-action-loop-cosign.md)'s `materialize()` uses for
briefing items.** DIP-0038's `item_id(text)` is a pure function: lowercase,
collapse whitespace, strip, take the first 16 hex characters of the sha256
digest — two differently-phrased descriptions of the same underlying thing
land on the same id, and (per DIP-0038's fold-level "never-resurface"
mechanism) a second `item.create` for an id already present in
`state.items`, **at any status**, is skipped rather than appended. Applied
here: processing the same stale inbox entry on two machines computes the
same content-hash id both times; whichever `item.create` reaches the fold
first wins (DIP-0034's ordinary earliest-HLC-wins semantics), and the second
becomes a recorded no-op, not a duplicate item. **This is what makes
inbox-as-append-only-forever safe on multiple machines even under
stale-snapshot resurrection** — clearing `inbox.org` after routing becomes
cosmetic tidiness rather than the sole thing standing between "processed
once" and "processed twice," which is exactly the load-bearing role it
currently, precariously, has.

**A direct corpus finding requires one refinement to DIP-0038's pattern, not
a blind reuse of it: hash the full normalized entry, not the heading
alone.** `inbox.org` as read for this DIP (2026-08-03 snapshot) contains two
genuinely different entries sharing the byte-identical heading `Daily News
Digest - Aug 03 :news:daily:` on the same day — one carrying that day's
crypto links, the other that day's AI/tech links. Hashing the heading text
alone would collide these into a single ledger item and silently drop one
digest's content on the floor the first time this mechanism ran for real.
The content hash this DIP specifies covers the normalized **heading plus
body** (whitespace-collapsed, same normalization DIP-0038 already applies),
which distinguishes these two real entries correctly.

**Ruling for entries that already carry an `:ID:`.** A small number of
`inbox.org` entries in the real corpus already have one — e.g. two
DIP-consideration entries captured on 2026-08-03, presumably enriched by an
upstream agent before ever reaching `/process-inbox`. When an entry already
carries an org `:ID:` at classify time, that id is reused directly as the
ledger item id, consistent with this DIP's identity rule everywhere else
(genesis import, Specification). The content-hash id above is the fallback
for the common case — raw captures (news digests, email forwards, quick
jots) that have no `:ID:` yet — not a replacement for the existing
"preserve an id that's already there" rule.

## Projection Timing

The projector runs on two triggers, not one, and both are required:

- **Eager, after any local `EventLog.append()`.** Once an event is appended
  to *this machine's* actor file in a way that changes a projected file's
  rendered content (a new `item.create`, a state transition, a clock event),
  the projector runs immediately — synchronously, or as an immediately
  dispatched job, not queued behind a timer. **A timer-based-only projector
  would make the system feel broken interactively**: a user who adds a task
  and doesn't see it in `next_actions.org` for up to N minutes is
  experiencing a regression relative to today's direct-write behavior, where
  the file reflects reality the instant the write returns. This DIP treats
  that regression as unacceptable, not as an acceptable cost of migration.
- **Periodic, on a fixed interval, to absorb remote events.** The eager
  trigger only fires for events appended *locally* — a sibling machine's
  `box.jsonl` arriving via the existing git-based sync has no local
  `append()` call to hook, so nothing eager fires for it. A scheduled sweep
  (the same cadence class as DIP-0010's existing sync poll interval — 10
  minutes — is a reasonable default to reuse rather than a new interval to
  invent and separately justify) re-runs the projector unconditionally,
  which is what keeps the generated file caught up with cross-machine state
  within one sync interval — the same bound DIP-0010's own sync already
  operates under today, not a new or worse latency this DIP introduces.

Both triggers call the identical projector function and are subject to the
identical refuse-to-overwrite guard (Specification, Phase 1) — there is no
"fast path" for the eager trigger that skips hash verification; eager only
changes *when* the projector runs, never *what* it checks before writing.

Neither trigger is built by this DIP — see Implementation.

## Rationale

**Why the (a)/(b)/(c) criterion instead of a fixed field list decided by
argument?** A field list defended by "these seem important" is not
reviewable — a reviewer can only disagree by counter-assertion. A criterion
lets a reviewer check each field against it (as this DIP does explicitly for
the two near-miss cases, `:DEPENDS_ON:` and `:WAITING_ON:`) and reach the
same or a different conclusion by the same method. It is also what keeps this
DIP from re-litigating every org-mode feature as a candidate field —
opaque-payload-by-default is the discipline against schema creep.

**Why a three-phase migration instead of building the reconciler first and
cutting over once?** Because the hardest phase (2, the reconciler) is the one
this DIP has the least confidence in — see Open Questions. Shipping shadow
projection first produces the actual equivalence evidence (the real diff,
not the predictive one in this DIP) that either validates the schema or
finds its gaps *before* anything becomes read-only, and shipping read-only
before the reconciler exists produces a real, observed population of
conflict-file cases that inform what the reconciler actually needs to
handle, instead of designing it from imagination.

**Why `inbox.org` is exempt rather than migrated last, after everything
else works?** It isn't a matter of sequencing — it's exempt permanently. It
is the one file in this DIP's scope that never had the mutable-shared-state
problem to begin with (append-only), and imposing ledger-mediated capture on
it would trade a real problem-free surface for a friction cost with no
compensating safety gain.

### Alternatives considered and rejected

- **Full org-semantics in events — model every org-mode feature (drawers,
  archive semantics, priority cookies, effort tracking, agenda-view sorting
  rules, habit-style repeaters) as first-class, validated ledger
  fields.** Rejected: this is the schema-creep failure mode the (a)/(b)/(c)
  criterion exists to prevent. Org-mode is a mature, feature-rich format with
  decades of Emacs-side semantics; reimplementing all of it as ledger schema
  would mean this DIP re-derives org-mode from first principles inside a
  different storage format, at enormous cost, for features (habit `:STYLE:`,
  priority cookie visual mapping, agenda column layout) that satisfy none of
  the three criteria — they are rendering concerns, not conflict/query/policy
  concerns. The opaque-payload category exists precisely so these features
  keep working, verbatim, without the ledger needing to understand them.
- **Immediate cutover — skip the shadow phase, make `next_actions.org`
  generated on day one.** Rejected: there is no reconciler yet, no
  shadow-diff evidence that the schema actually reproduces the real corpus
  byte-for-byte (the round-trip analysis above is predictive, not executed —
  it is the strongest evidence obtainable *without* building the projector,
  and it already surfaces real gaps, e.g. the 41 `REVIEW`-state tasks
  outside genesis scope). Cutting over before that evidence exists risks
  exactly the "you lost work" failure mode Phase 1's refuse-to-overwrite
  guard is designed to convert into a visible conflict instead — better to
  find schema gaps in a diff report than in a clobbered file.

## Compatibility

This DIP is **not** purely additive once Phase 1 lands for a given space —
unlike DIP-0034 and DIP-0041, which changed no runtime behavior for anyone
until a caller opted in, Phase 1 makes `next_actions.org` read-only for
*every* existing writer of that file, whether or not that writer has been
migrated. Named explicitly, per file/tool:

- **Emacs (direct org-mode editing).** Phase 0: unaffected. Phase 1: a save
  to a `chmod 444` file is refused by the OS outright — the human either
  stops editing directly (the intended outcome) or overrides the permission
  bit manually, which the projector's hash-guard then detects on its next
  run and refuses to overwrite, surfacing a conflict file rather than
  silently discarding the edit. Emacs becomes a **read-primarily** interface
  for `next_actions.org` from Phase 1 until Phase 2's reconciler exists;
  `inbox.org` is completely unaffected in every phase.
- **Orgzly (or any mobile org client syncing via file sync).** Same
  mechanism as Emacs — a mobile edit that reaches the file between projector
  runs changes its hash, and the next projector run detects drift and
  refuses to overwrite rather than silently discarding the mobile edit. This
  is the intended behavior (the guard's entire purpose), but it does mean an
  Orgzly edit made during Phase 1 sits in a conflict file, not the live
  file, until a human resolves it or Phase 2 lands.
- **`ai-task-executor` and `nightshift-orchestrator`.** This is the sharpest
  conflict. Per DIP-0009 Part 2, execution-overlay states (`QUEUED` →
  `WORKING` → `DONE`/`REVIEW`/`FAILED`) are written by nightshift **directly
  into whichever task file holds the task** — "valid in ANY task file," per
  DIP-0009's own text. Once Phase 1 makes `next_actions.org` read-only, every
  one of these direct writes is refused by the same guard that protects
  against a stray human edit — nightshift cannot distinguish "the projector
  wrote this" from "I should keep writing here." **Nightshift must migrate
  its claim/execute/complete write cycle onto event emission in the same
  wave Phase 1 goes live for a space that runs it** — this is not optional
  follow-up work, it is a Phase 1 co-requirement for any space where
  nightshift operates (i.e., all of them, per the module table in
  CLAUDE.base.md). This DIP does not perform that migration; it names it as
  a blocking dependency Phase 1's rollout plan must account for.
- **GTD MCP tools** (`datacore.gtd.add_task`, `complete_task`,
  `set_task_state`, `write_clock_entry`, `archive_tasks`, etc.). Names and
  signatures are unaffected — see Write Path for the full call-site table.
  Implementations are not: every one of these currently mutates org files
  directly, and `write_clock_entry` collides head-on with the "clock entries
  are events, LOGBOOK is generated" ruling above — it is exactly the write
  path this DIP retires. None of the re-pointing is built by this DIP.
- **`org_workspace_adapter.py` read commands** (`list`, `agenda`,
  `ensure-ids`, etc.). Read paths are unaffected in every phase — they read
  whatever is on disk, and Phase 1's file is still valid, parseable org-mode
  (just generated rather than hand-written). `ensure-ids` specifically
  becomes a no-op for a Phase-1 file, since genesis import already guarantees
  100% `:ID:` coverage on this corpus and the projector always writes the id
  it was given.
- **External sync (DIP-0010, GitHub Issues etc.).** Structurally unaffected
  — DIP-0010's adapters already read/write `next_actions.org` as a file;
  they do not care whether a human or a projector wrote it, as long as the
  format is valid org-mode, which Phase 1 preserves. The near-zero real
  usage of `:EXTERNAL_ID:` on this corpus (1 occurrence) means this
  interaction is currently more theoretical than load-bearing.

## Security Considerations

- **Public-repo constraint.** As with DIP-0034, this DIP introduces no
  secrets — `genesis.jsonl` contains task titles, timestamps, and existing
  org properties already committed in the org files it is derived from; it
  adds no new sensitive surface beyond what already exists.
- **The refuse-to-overwrite guard is a data-loss control, not an access
  control.** It stops the projector from silently discarding a concurrent
  edit; it does nothing to restrict who may write to the file at the OS
  level (`chmod 444` is advisory against the owning user, who can always
  `chmod` it back). This DIP does not claim otherwise.
- **Genesis import is a one-time, auditable, reviewable operation.** Because
  it writes to a single dedicated actor file that is never appended to
  again, the entire genesis event set for a space is one file, inspectable
  in full before Phase 1 enforcement goes live — this is a deliberate
  property, not an accident, precisely so genesis import's output can be
  reviewed (including running the real round-trip diff this DIP's Round-Trip
  Analysis only predicts) before anything becomes irreversible.

## Implementation

**Nothing in this DIP is built.** No projector, no genesis importer, no
`EVENT_TYPES` amendment, no shadow-diff job. This section states honestly
what each phase requires and its trigger, not a schedule.

- **Prerequisite, not part of this DIP:** a small amendment to DIP-0034's
  `EVENT_TYPES` registry admitting `item.clock.start`/`item.clock.stop`.
  Trigger: before Phase 0's projector can render CLOCK/LOGBOOK content at
  all, since the "clock entries are events" ruling has nowhere to write
  without it.
- **Prerequisite, not part of this DIP:** a small amendment to DIP-0034's
  Summary/Specification Source-of-Truth Boundary, narrowing "org-mode
  remains the coordination layer and system of record for GTD tasks" to
  account for this DIP's existence once ratified. Trigger: this DIP's
  ratification — `context-maintainer` owns carrying this out, per Related
  Agents, the same pattern DIP-0034 used for its own doctrine follow-up.
- **Phase 0 (shadow), unbuilt.** Requires: the projector itself
  (`ledger/projector.py`), the genesis importer (`ledger/genesis.py`), and a
  nightly diff job. Trigger to build: this DIP reaching at least Accepted
  status — building an unratified migration path against production org
  files is out of scope for a Draft.
- **Phase 0 → 1 gate.** N consecutive days of exact shadow-diff equivalence,
  N chosen at rollout time and stated explicitly when chosen (see Rationale
  for why a fixed number isn't pinned here).
- **Phase 1 (read-only), unbuilt, blocked on a named co-requirement.**
  Requires the refuse-to-overwrite guard (Specification) and, per
  Compatibility, nightshift's claim/execute/complete cycle migrated onto
  event emission for any space Phase 1 goes live in. This DIP does not
  schedule that nightshift migration; it names it as a hard blocker.
- **Phase 1 → 2 gate.** A working, tested reconciler — not a date. Given
  this DIP's own admission (Rationale) that the reconciler is its
  least-specified phase, this gate is expected to be the slowest one to
  clear.
- **Phase 2 (reconciler), unbuilt, least specified.** See Open Questions for
  what remains genuinely undecided.

## Open Questions

1. **Repeater semantics** (stated as unresolved in Specification, repeated
   here per house convention that every DIP's stated open question also
   appears in this section): does `item.complete` on a repeating item
   synthesize the next occurrence at fold time, or does something else do
   it? Must resolve before schema freeze. Not urgent for `next_actions.org`
   specifically (zero live repeater instances found in the real-corpus
   analysis), but blocking for any future extension of this DIP's scope to
   `habits.org` (30 real repeater instances there).
2. **Execution-overlay states and genesis scope** — the 41 real `REVIEW`
   tasks (and any future `QUEUED`/`WORKING`/`FAILED` population) sit outside
   "active tasks (TODO/NEXT/WAITING)" as scoped. Does a follow-up ruling
   admit them to genesis import directly, or does Phase 2's reconciler pick
   them up once they resolve to a human state? Named as a gap in
   Specification; not resolved here.
3. **Phase 2's payload-update mechanism.** DIP-0034 has `item.create` (fixed
   payload at creation) but no generic "update this item's opaque payload"
   event. A human editing `:CONTEXT:` text through the reconciler needs
   *some* event to carry that edit forward — does this reuse an existing
   event type's payload-additive property (Invariant 6), or does it need its
   own new event type (another DIP-0034 registry amendment, on top of the
   clock-events one this DIP already requires)? Unresolved.
4. **Nightshift migration ordering and ownership.** This DIP names
   nightshift's claim/execute/complete migration as a Phase 1 co-requirement
   (Compatibility) but does not scope, own, or schedule that migration —
   whether it is folded into this DIP's own Phase 1 rollout, or is DIP-0011's
   own follow-on amendment, is unresolved.
5. **Team-space `:OWNER:` semantics.** The `owner` field is first-class per
   the criterion, but this corpus (a single-user personal space) has only
   one real occurrence of `:OWNER:` to validate against. Whether the
   ledger's `owner`/claim/grant semantics (DIP-0034, and the claim–grant
   amendment in this same drafting wave) map cleanly onto team-space GTD
   task ownership, or need space-specific adjustment, is untested.

## References

- [DIP-0034: Event Ledger Substrate](DIP-0034-event-ledger-substrate.md) —
  the substrate this DIP projects onto org-mode; source of the
  Source-of-Truth Boundary this DIP is the named prerequisite to amend, and
  of the `EVENT_TYPES`/fold-semantics contract this DIP's `item.clock.*`
  addition and genesis import must respect.
- [DIP-0009: GTD System Specification](DIP-0009-gtd-specification.md) — owns
  the org state vocabulary (Part 2), file model (Part 0/3), Rich Task
  Standard (Part 3.5), and recurring-task/repeater semantics (Part 3.6, Part
  8.1) this DIP's schema and Open Question 1 engage with directly.
- [DIP-0010: External Sync Architecture](DIP-0010-external-sync-architecture.md)
  — owns the "org-mode is source of truth for all content" claim this DIP is
  the ratified proposal to narrow for GTD tasks specifically, phase by
  phase.
- [DIP-0011: Nightshift Module](DIP-0011-nightshift-module.md) — owns the
  execution-overlay write path this DIP's Phase 1 puts in direct conflict
  with the refuse-to-overwrite guard; its migration is a named, unscheduled
  Phase 1 co-requirement (Compatibility, Open Question 4).
- [DIP-0035: Job Contracts](DIP-0035-job-contracts.md) — source of the
  "report-only alongside the existing mechanism, retire only after N
  consecutive green days" pattern this DIP's Phase 0 → 1 gate reuses by
  name.
- [DIP-0038: Action Loop & Co-Sign Policy](DIP-0038-action-loop-cosign.md) —
  source of the `item_id()` content-hash identity primitive and fold-level
  never-resurface dedupe rule this DIP's Inbox Processing section adapts,
  with the full-entry (not heading-only) refinement the real `inbox.org`
  corpus required.
- `ENG-2026-0727-004` — Mac↔box sync topology and its duplicate-resurrection
  / ID-conflict-churn failure modes, the direct motivating evidence for this
  DIP alongside the five repair scripts cited in Motivation.
- `ENG-2026-0423-001` — nightshift git-lock silent failure, the other
  motivating incident DIP-0034 named and this DIP still has not closed for
  the GTD task class.
- `.datacore/lib/inbox_dedup.py`, `.datacore/lib/inbox_dedup_verify.py`,
  `.datacore/lib/org_resolve_id_conflicts.py`,
  `.datacore/lib/reconcile_sync_merge.py`,
  `.datacore/lib/repair_nightshift_org.py` — the five repair scripts cited
  as living evidence in Motivation; their docstrings are quoted directly
  where cited.
- `0-personal/org/next_actions.org` — the real corpus the Round-Trip
  Analysis and Genesis Import sections were run against, queried via
  `org_workspace.Query` per this installation's own convention against
  raw-grepping org files for task data.
- `0-personal/org/inbox.org` — the real corpus (2026-08-03 snapshot) that
  surfaced the same-heading/different-body "Daily News Digest" pair driving
  Inbox Processing's full-entry hashing refinement.
