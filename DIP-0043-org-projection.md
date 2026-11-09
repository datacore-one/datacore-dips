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


> **Published 2026-10-04 as Draft** (ledger upgrade Phase 3, audit A#13, B-F10).
> This text was written in August 2026 and is published as it stood, so that
> the code's citations of DIP-0043 resolve. Since then: a space is in Phase 1
> when its tracked `.datacore/ledger-phase` reads `1` (`ledger_project_org.py`,
> `ledger_ingest_org.py`); rollback is `ledger_phase1_flip.py --space <s>
> --reverse --apply`. The `phase1-active` marker in `ledger/phase1.py` is read
> by no live code. A profile A install (people only, ledger and verify) uses
> no projection at all. What the code does today is stated in
> [DIP-0034](DIP-0034-event-ledger-substrate.md), "Normative current state".

## Summary

DIP-0034 built an append-only, hash-chained, per-writer event ledger and then explicitly excluded GTD tasks from it, leaving org-mode files as the multi-writer mutable state they always were. This DIP finishes the job DIP-0034 started: it defines a schema for projecting `item.*` ledger events onto org-mode task files, a genesis import that folds the *existing* corpus of active org tasks into the ledger without discarding their identity, and a three-phase migration (shadow projection → read-only generated file with a refuse-to-overwrite guard → org-edit reconciler) that gets from today's hand-edited `next_actions.org` to a generated one without a flag-day cutover or an unverified leap of faith. `inbox.org` is exempt throughout — it stays the single, frictionless, append-only capture surface it already is.

> **This DIP is the normative carrier of the source-of-truth boundary**
> (promoted 2026-08-04, owner decision). [DIP-0034](DIP-0034-event-ledger-substrate.md)
> inverted its boundary on the same day — the ledger is the system of record
> for GTD task state, org files are its projection — but deliberately did not
> restate the rule in operational terms. **This DIP owns it.** Where DIP-0034,
> [DIP-0009](DIP-0009-gtd-specification.md) or
> [DIP-0010](DIP-0010-external-sync-architecture.md) and this DIP disagree
> about what is authoritative for a GTD task, this DIP governs.
>
> The rule is **per-space and per-phase, never global**: a space at Phase 1 or
> beyond has a ledger-authoritative, generated `next_actions.org`; a space
> below Phase 1 has an authoritative hand-edited one and behaves exactly as
> DIP-0009 describes. There is no global switch and no flag day. Determining
> which regime a space is in means checking that space's phase — the answer is
> never "the whole installation is on v2".
>
> Two guarantees hold in every phase, for every space: the projected file
> keeps its **original path and name** (`<space>/org/next_actions.org`), so
> existing readers — org-workspace, the GTD MCP tools, agenda queries, mobile
> clients — continue to resolve it; and **`inbox.org` is never projected**.
>
> DIP-0009 and DIP-0010 both assert org-mode as the source of truth in
> unqualified terms and are merged; each owes an amendment scoping the claim
> per-space. Until those land, this paragraph is the operative rule and the
> discrepancy is recorded rather than hidden.

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
| What form does the opaque payload take for a task? | org-mode source text, read through `org-workspace` as a `NodeView`. Task-class items only — briefing/approval/attest/spend payloads stay purely structured. See "Opaque payload grammar". |
| Can an event carry a whole re-serialised task? | **No.** Events carry deltas. A log of whole-object snapshots is last-writer-wins and destroys conflict-free merging — the normative constraint is in "Opaque payload grammar". |
| Does `ledger/` depend on org-workspace? | No, and it must not. org-workspace is a projection-boundary dependency (`projector.py`, the Phase 2 reconciler) only. |
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
resurrection / ID-conflict churn** (`ENG-2026-0727-004` — the workstation and the server
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
  (datacore-app's daemon and `ensure-ids` on the server) each invent a different
  UUID for the same heading when it lacks one, and "the next sync conflicts
  on pure metadata — no human decision is involved," per its own docstring.
- **`reconcile_sync_merge.py`** — resolves workstation↔executor merge
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

### Opaque payload grammar: org text, read as objects (owner decision, 2026-08-04)

For **task-class items only**, the opaque payload is **org-mode source text**
— the heading body, drawers, and every property the (a)/(b)/(c) criterion
excludes — and both the projector and the reconciler read it through
`org-workspace` as a `NodeView` object rather than as a string.

**Why this is the right carrier.** The opaque payload's whole job is to
survive a round trip unaltered, and `org-workspace` already guarantees
exactly that: `dumps()` over an unmodified parsed file is byte-identical to
the input (`test_unmodified_round_trip`). Giving the opaque part org grammar
therefore turns this DIP's round-trip acceptance criterion from something
*tested after the fact* into something true *by construction*. It also means
no second task-object model has to be written: `NodeView`'s accessors
(`heading`, `todo`, `tags`, `scheduled`, `deadline`, `properties`, `body`,
`parent`, `children`, `id()`) are the object API the projector and reconciler
both want, already vendored, zero-dependency, and already the mandated
interface for task queries everywhere else in Datacore.

**Normative constraints.** Four, and the first is the one that matters:

1. **Events carry operations, never whole-object snapshots.** An
   `item.update` (or any state transition) MUST carry the *delta* — the
   fields that changed — never a complete re-serialisation of the task. This
   is not a size optimisation. Per-writer logs merge without conflict
   precisely because they record small, independent operations; a log of
   whole-object snapshots is a log of *states*, and two actors each appending
   a complete representation of the same item is last-writer-wins — exactly
   the conflict class this entire design exists to eliminate. It would also
   destroy the derived LOGBOOK (see below), since "what changed" would only
   be recoverable by diffing two blobs.
2. **Org text is the remainder, never the whole payload.** First-class fields
   stay first-class and structured. No query the fold or the SQLite index
   answers today — `items_by(status=, owner=)`, agenda views, tag filters —
   may come to require an org parser.
3. **The ledger core stays org-free.** `org-workspace` is a dependency of the
   *projection boundary* (`projector.py`, the Phase 2 reconciler), never of
   `ledger/` itself. `hlc`, `events`, `log`, `verify`, `fold`, `index` and
   `policy` MUST remain parseable and foldable by an implementation that has
   never heard of org-mode — a constraint [DIP-0044](DIP-0044-actor-identity.md)'s
   portable-identity direction makes concrete, since a non-Python
   implementation would otherwise need an org parser to fold a ledger.
4. **Content-hash identity uses first-class fields, not the org text.**
   `org-workspace`'s round-trip guarantee proves parse→dump is lossless for
   text that already exists; it does **not** prove that two actors
   independently constructing the same task converge on the same bytes —
   property ordering, whitespace and drawer placement may legitimately
   differ. [DIP-0038](DIP-0038-action-loop-cosign.md)'s content-hash `item_id`
   and its never-resurface guarantee therefore hash the structured fields.
   Org text is carried, not hashed for identity.

**Scope: task-class items only.** Briefing, approval, attestation and spend
items keep purely structured payloads and gain nothing here. This is the same
per-class payload discipline DIP-0034's `metric.attest` discriminator already
established, and it is stated as a rule rather than left to be inferred so
that no future reader assumes every ledger item carries org text.

**Why this makes deferred reconciliation recoverable.** Phase 2 — translating
hand edits back into events — is deferred with no schedule, and it is the
weakest part of this migration precisely because a *textual* diff between an
edited file and a projection does not map onto events. With `NodeView`
objects on both sides the diff is object-level ("this property changed, this
state changed"), and each difference maps directly onto one delta event. The
decision recorded here is therefore not only about fidelity today; it is what
keeps Phase 2 tractable enough to un-defer later.

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
heading such as `** /Acme Project`, which carries no TODO keyword and is never
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

### Designated inbox processor

Owner decision, folded into this DIP: **inbox processing gets a single
designated processor per space, and for the personal space, the always-on
chief-of-staff host is it.** Four points, then the trade-off this decision is not free of.

1. **Ownership is enforced as data, not convention.** A `policy.set` event
   (DIP-0034's existing event type — its only current consumer is DIP-0038's
   co-sign threshold, so this is a second, distinct use and needs its own
   discriminator key in the payload, the same `metric.attest`-style
   namespacing this DIP already relies on elsewhere) names the designated
   inbox-processor actor for a space. Other automated actors check this
   before running `/process-inbox` unattended and **decline rather than
   assume** — no automated actor infers "I should probably handle this"
   from the mere fact that the inbox has entries. This makes explicit what
   already happens operationally: `.datacore/lib/cos_inbox.sh` (and its
   module-hosted twin under `chief-of-staff/server/lib/`) already runs on a
   schedule as exactly this: `cos_sync.sh` (sync) → a routed
   `inbox-processing` task invocation via `cos_route.py`/`cos_llm.sh`
   (its own routing comment: a local model by default, escalating to a
   hosted model, failing soft back to the hosted one) calling `/process-inbox` (run) → `git commit` (commit) →
   `cos_sync.sh` again (sync). The sync-run-commit-sync ordering is itself
   the fix for a past incident where the server could otherwise act on stale
   data or leave its own output unpublished — this DIP does not introduce
   that discipline, it names an actor that already follows it and makes the
   naming a ledger fact instead of an implicit assumption about which
   cron job happens to exist. Framed against DIP-0034's claim-safety policy,
   this is **case 1, partitioned**: the actor is set once, out of band, at
   `policy.set` time — "the owner executes; no claim, no grant, no race" —
   applied to a *role* (who processes this space's inbox) rather than a
   single ledger item, so there is exactly one eligible executor and nothing
   to arbitrate.
2. **Idempotence remains the safety net — single-processor ownership does
   not replace it.** A single designated processor makes collisions between
   two automated actors *improbable by design*; the content-hash keying two
   sections above makes a collision *harmless if the rule is ever violated
   anyway* — a misconfigured `policy.set`, a stale second cron job, a
   migration window where two processors briefly coexist. This DIP keeps
   both deliberately, in the same "guard early, don't rely solely on
   downstream tolerance" spirit as the genesis importer's own idempotence
   guard (Specification) and Phase 1's belt-and-braces refuse-to-overwrite
   enforcement (Migration Phases) — ownership is not a reason to drop the
   hashing.
3. **Liveness is a stated property with a contract, not an assumption.** If
   the designated processor is down, capture still works — `inbox.org`'s
   append-only exemption (Specification) guarantees this unconditionally —
   and processing is merely delayed. **That is correct behavior, not a
   fault**, the same no-single-point-of-failure shape DIP-0034's own
   sequencer-degradation design already commits to (writes continue,
   finality pauses; here, capture continues, routing pauses). But an inbox
   holding unprocessed entries older than N hours **MUST make noise** —
   this needs its own [DIP-0035](DIP-0035-job-contracts.md) job contract
   (a manifest entry whose freshness check is "does the oldest unprocessed
   `inbox.org` entry's timestamp exceed N hours," alerting through the same
   alert primitives the chief-of-staff inbox job already calls
   for its own delivery-failure case, not a new alert channel invented for
   this). The failure mode this is designed against is named explicitly:
   **silent backlog** — the same "Complete! 0 tasks, 0 errors,
   undetected for three days" shape as `ENG-2026-0423-001` (Motivation),
   here applied to capture instead of task claiming.
4. **Human override is always permitted.** The designation binds
   **automated** actors only — the owner can process the inbox in-session,
   interactively, at any time, whether or not the designated processor's scheduled run has
   or hasn't happened. An overlap (a human runs `/process-inbox` manually
   moments before the server's timer also fires) is possible and is rendered
   harmless by the same idempotent content-hash keying named in point 2, not
   by any coordination between the two.

**This is a trade-off, not a pure win, and this DIP records it as one.**
Routing an inbox entry is a judgment call, and the server runs a
lighter-weight, differently-tiered model for this task than an interactive
session does — `cos_llm.sh`'s own routing comment for the `inbox-processing`
task class states it plainly — a local model by default. Concentrating
classification onto one consistently lighter-resourced processor bounds
routing quality for every capture that goes through it, system-wide. That
bound is fine for confident, close-to-mechanical classification — "this is a
task, tag it `:AI:research:`" — and shakier for genuinely judgment-heavy
captures — "this capture is actually three tasks and a decision," where
under-decomposition silently loses structure rather than just picking a
slightly wrong tag. The mitigation this DIP specifies: the designated
processor handles confident cases directly and **escalates ambiguous ones
rather than guessing**, the same partial-automation shape DIP-0034 already
uses for its Chief-of-Staff merge gatekeeper (`metric.attest` class
`merge.review`, payload `{space, branch, verdict, reasons[]}` — a bounded
verdict-plus-reasons, never a silent unilateral action). The escalation
channel is not new: an ambiguous capture lands in the existing open-questions
loop ([DIP-0006](DIP-0006-open-questions-management.md), superseded into
[DIP-0013](DIP-0013-meetings-module.md) §4) rather than inventing a second
one. What transfers from DIP-0013 is the *shape* — a bounded confidence
check that lands unresolved items in a durable, human-reviewable queue
instead of guessing — not DIP-0013 §5.2's specific counting heuristic
("3+ appearances across 7 days of daily standups"), which is tuned for
meeting cadence and has no direct analogue for a capture seen once. This
DIP does not design that mapping; it names the reuse and the caveat, the
same honesty DIP-0038 already applied to the same heuristic for a different
consumer.

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
  `server.jsonl` arriving via the existing git-based sync has no local
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

## Projection Determinism

**Normative requirement.** The projector (`ledger/projector.py`) MUST be
bit-deterministic: given the same folded `LedgerState` (DIP-0034's `fold()`
output, itself already required to be byte-for-byte reproducible per
DIP-0034 Invariant 2) as input, two independent runs of the projector — on
any two machines, at any two times — MUST produce byte-identical output for
every file it writes. This is not an aspirational property; it is a
**tested** one: the test suite runs the projector twice over identical input
state and asserts the two output files are byte-identical, not merely
semantically equivalent (same content rendered with different incidental
whitespace does not pass). A projector that happens to be deterministic by
construction but has no test enforcing it is not compliant with this
requirement — this DIP requires the test to exist, not merely the property
to hold.

The insight this requirement exists to cash in (owner, 2026-08-04): once
determinism is real and tested, every machine holding the same events
produces byte-identical org files for the same fold — which turns a hash of
the projected output into a cheap, cross-machine consistency proof. Two
machines can confirm they agree on projected state by comparing a single
hash instead of one shipping the other a full file for a byte-diff, or both
re-running the fold and line-by-line comparing the result. This is the same
economic move DIP-0034 already makes for the event log itself (a hash chain
instead of trusting the filesystem) and DIP-0042 makes for the canonical
chain (`root_hash` instead of re-transmitting `entries[]`), applied one
layer further out — to the projector's *output* rather than its input.

**Determinism killers.** Bit-determinism is easy to assert and easy to
accidentally violate; this list exists so an implementer of
`ledger/projector.py` has a concrete checklist rather than discovering each
one the hard way as a flaky-diff bug report:

- **Any wall-clock value in the rendered output** — most obviously a
  `# Generated at <now>` header. Migration Phases already specifies a fixed
  advisory header for Phase 1 (`# GENERATED — edits will be overwritten`);
  it must stay a fixed string and never interpolate a timestamp into itself
  (`# GENERATED at 2026-08-04T09:00:03Z` would fail this requirement on its
  own). Any other wall-clock read at render time — a "last projected" line,
  a run id — is equally disqualifying.
- **Set or dict iteration order.** Python dicts are insertion-ordered since
  3.7, but a `set`, or a `dict` built by iterating a `set`, is not
  order-stable across processes or interpreter versions; if the projector
  ever collects tags, ids, or property keys into a `set` before rendering
  them, output order depends on incidental hash-seed/interpreter state, not
  on the input.
- **Locale-dependent date formatting or sorting.** `strftime` and string
  comparison/sort behavior can both depend on the process locale (month
  names, collation order); rendering must use a fixed, explicit format —
  org timestamps are already a fixed `<YYYY-MM-DD Day HH:MM>` shape — and
  any sort must be an explicit codepoint (byte) sort, never the platform's
  default, locale-aware string comparison.
- **Line-ending and trailing-whitespace drift.** `\n` vs. `\r\n`, and a
  trailing space a template leaves on some lines and not others, both
  produce a byte-level difference invisible to a casual read but fatal to a
  byte-identical hash.
- **Org property-drawer ordering.** A `:PROPERTIES:` drawer's key order
  must be fixed by the projector's own rendering logic (schema field order:
  first-class fields in a fixed order, then opaque payload keys in a fixed
  order), never "whatever order the payload dict happened to iterate in" —
  the opaque-payload dict (Specification, Schema principle) is exactly the
  kind of externally-sourced, potentially insertion-order-varying structure
  this killer targets.
- **Hostname or absolute path leaking into output.** Nothing in a rendered
  file may embed the machine that happened to run the projector (a comment,
  a generated-by field, an absolute file path baked into a link) — the
  entire point of the guarantee below is that *which machine* ran the
  projector must not be observable in its output.
- **The opaque payload must round-trip byte-exact.** Every field the
  Specification's (a)/(b)/(c) criterion excludes from first-class status is
  written back verbatim; the projector must not "clean up," re-indent,
  re-wrap, or otherwise normalize opaque payload text on the way out —
  doing so would make the same input `LedgerState` map to different output
  depending on incidental formatting decisions made at render time, rather
  than depending only on the payload bytes themselves.

**A bare hash is not comparable.** Two machines legitimately hold different
subsets of the event pool at any given moment — sync is periodic (Projection
Timing: a 10-minute sweep), not instantaneous — so "my `next_actions.org`
hashes to X" and "your `next_actions.org` hashes to Y" being unequal is not
by itself evidence of a bug; it may just mean the two machines have not
synced yet. A hash is only a meaningful consistency check when it is
anchored to a **specific, named event set** both sides can independently
confirm they are comparing against. "My projection hash is X" is not a
claim; "my projection hash over *this exact input* is X" is. Saying this
plainly because it is the difference between a working consistency check and
a false-alarm generator: comparing bare hashes between two machines at
different points in their sync cycle would report a mismatch on nearly every
comparison that doesn't happen to land on the same instant, which is worse
than not having the check at all — it trains an operator to ignore the alert.

**The anchor is a writer version vector, not a block height** (amended
2026-08-05, superseding this section's original rule). An earlier draft
anchored the claim to [DIP-0042](DIP-0042-canonical-ledger.md)'s `height`,
spoken as `projection_hash @ height N`. That rule is **withdrawn**, for two
reasons:

1. **Height is a proxy for the input set, and an imprecise one.** A snapshot
   at height N folds the events referenced by blocks `0..N`, but a projector
   runs on a 10-minute sweep and folds *everything it currently holds* —
   including the un-blocked tail. Two machines can therefore sit at the same
   height while having folded different tails, making equal heights an
   insufficient basis for comparison, and unequal heights an unnecessary
   barrier to it.
2. **It makes drift detection a hostage to block cadence.** With DIP-0042's
   daily cadence, height advances once per day, so a projector bug or a
   divergent fold introduced in the morning would not be *detectable at a
   common anchor* until that night's cut. Detection latency should be bounded
   by sync latency, not by how often the sequencer happens to run.

The anchor is instead the **writer version vector**: `{actor: max_seq}` over
every writer file the projector folded. Because each writer file is
append-only with a monotonic, gapless `seq` (DIP-0034, Event schema), this
vector identifies *exactly* which prefix of every log was consumed. Two
machines with identical vectors and identical `projector_version` MUST
produce identical output; if they do not, that is drift — immediately,
unambiguously, and without waiting for a block.

Crucially it also preserves the "not comparable" answer that height was
introduced to give, and makes it exact rather than approximate:

- **identical vectors** → comparable; hashes must match, and a mismatch is a
  real defect;
- **one vector is a strict prefix of the other** (every entry ≤, at least one
  <) → not comparable; the lagging machine simply has not synced yet, which
  is the ordinary case and MUST NOT be reported as drift;
- **vectors diverge** (each has an entry the other lacks, or a writer the
  other has never seen) → not comparable, and also a signal that neither
  machine has a complete view.

Only the first case is an alert. Height MAY still be carried as a human
convenience, but it is not the anchor and MUST NOT be used as the comparison
key.

**Projector version is part of the claim.** A projector code change (a bug
fix, a rendering-format tweak, a newly-promoted first-class field) can
change `next_actions.org`'s bytes for an input set whose underlying
`LedgerState` has not changed at all — the events are identical, only the
code turning them into text is different. If an attestation carried only
the input anchor and a hash, every projector deploy would look
indistinguishable from real state drift: the hash changes, the input set is
the same, and nothing in the claim itself says whether that is a genuine
inconsistency or an expected consequence of a code upgrade. The attestation
is therefore `{writers, projector_version, projection_hash}` — three fields,
none optional. Two attestations are only comparable when `writers` is
identical and `projector_version` matches; a mismatch on `projector_version` alone
(same input set, same underlying state, different projector code) explains a
hash difference without it being an inconsistency, and a reader that drops
`projector_version` from the comparison will generate a spurious mismatch
report on every deploy — exactly the alert-fatigue failure this section
exists to avoid.

**New event type: `projection.attest`.** Payload
`{writers: {actor: max_seq}, projector_version, projection_hash, height?}` —
an actor emits this event
after running the projector, attesting "at this height, with this projector
code, I computed this hash." Per the naming convention this DIP already
uses for its `item.clock.*` addition: **this is a DIP-0034 `EVENT_TYPES`
registry addition this DIP proposes, not one it implements or has authority
to add unilaterally** — DIP-0034 Invariant 6 makes an existing event type's
*payload* additive, but a wholly new event type is a registry change, the
same distinction this DIP already draws for `item.clock.start`/
`item.clock.stop` (Specification, Compatibility). Following DIP-0034's own
convention of marking a cited capability implemented-vs-proposed (the same
convention behind, e.g., DIP-0034 Open Question 5's explicit "RESOLVED"
marker): `projection.attest` is **proposed, not yet implemented** — no code
in `.datacore/lib/ledger/` emits, folds, or verifies it as of this writing.
It joins `item.clock.start`/`item.clock.stop` as a second `EVENT_TYPES`
registry amendment this DIP requires but does not itself have the authority
to make (see Implementation for how the `item.clock.*` amendment is
requested; this addition follows the identical path).

**Payoff.** With `projection.attest` in place, Phase 0's nightly shadow-diff
(Migration Phases: "A nightly job diffs the projected file against the real
one") becomes a hash comparison — compute the hash and its `writers` vector
on each machine and compare the two attested values — instead of
transmitting and byte-diffing a full `next_actions.projected.org` file every
night. Because the anchor is the vector rather than a block height, this
comparison is available as soon as two machines have synced to the same
point, rather than once per block. More
generally, any actor can verify another actor's state claim by recomputing
it independently — fold the same events to the same height, run the same
`projector_version`, and check the hash matches — rather than trusting the
claim on say-so. This is the identical **verify, don't trust** posture
DIP-0042 already applies to blocks ("Can a consumer trust a block just
because the sequencer produced it? No. Verify, don't trust: recompute event
hashes from your own pool copy and check `root_hash`/`prev_block_hash`
before treating a block as valid" — DIP-0042, Quick Reference), extended one
layer further out: from "don't trust a block, recompute it" to "don't trust
a projection, recompute it."

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

## Owner Decision: Projected Org Files Are Gitignored

**Owner decision, folded into this DIP** (2026-08-04): projected org files —
`next_actions.org` from Phase 1 onward, and any future file this DIP's
projection mechanism covers — are **gitignored, not committed**. Each
machine regenerates its own copy locally from the event pool (and, once
DIP-0042 lands, from the canonical chain); the file that used to be a
git-tracked artifact becomes a disposable local cache of a deterministic
computation, in exactly the same sense DIP-0034's SQLite `index.db` already
is ("never a source of truth and always safe to delete and rebuild from the
event log," DIP-0034 Specification) and DIP-0042's snapshots already are
("a snapshot is never trusted on its own; it is a cache of a reproducible
computation," DIP-0042, "Snapshots and the O(tail) fold"). This is the same
idiom applied a third time, now to the org-mode rendering itself.

Four consequences, recorded here rather than left to be discovered:

- **The conflict surface disappears entirely, not merely shrinks.** The
  duplicate-resurrection / ID-churn / stuck-rebase genre this DIP's own
  Motivation documents via five repair scripts (`inbox_dedup.py`,
  `inbox_dedup_verify.py`, `org_resolve_id_conflicts.py`,
  `reconcile_sync_merge.py`, `repair_nightshift_org.py`) exists *because*
  `next_actions.org` is multi-writer mutable state moving through git — two
  machines each produce a version of the file, git has to merge them, and a
  merge of two independently-mutated copies of the same headings is exactly
  where the ID-conflict and duplicate-resurrection failure modes live. A
  gitignored, per-machine-regenerated file was never committed by more than
  one writer in the first place, so there is nothing for git to merge — this
  is a stronger claim than "conflicts become rarer" or "conflicts become
  easier to resolve" (which is what Phase 1's still-git-tracked,
  refuse-to-overwrite design in Migration Phases already achieves); it is
  "there is no merge step for this file to conflict in," full stop.
- **`inbox.org` is unaffected.** It is not a projection — it is human,
  append-only capture, per Specification and Rationale ("It is the one file
  in this DIP's scope that never had the mutable-shared-state problem to
  begin with"), and appends do not conflict for the same reason DIP-0034's
  per-writer event files do not conflict (Rationale: "an append-only surface
  has no overwrite hazard by construction"). It stays in git, exactly as it
  does today, in every phase.
- **Mobile/external access moves to an endpoint.** With `next_actions.org`
  no longer a git-tracked file any device can pull, the file-sync model
  Orgzly and similar mobile org clients depend on stops working for this
  file by construction. **This is now an unowned gap, and that is worse than
  it was.** The earlier draft of this bullet deferred the question to
  DIP-0045 (node protocol), which was **withdrawn on 2026-08-05** — so no DIP
  currently owns mobile access to a projected org file.

  The question itself is unchanged and still consequential: Orgzly syncs
  files or speaks WebDAV; it cannot consume a plain HTTP/JSON endpoint. So
  either something serves a **WebDAV-shaped** view of the projection, in
  which case native mobile org editing survives the move to a gitignored
  projection, or it does not, in which case Orgzly stops working for this
  file permanently. **Open Question, recorded explicitly rather than left to
  default by accident.**

  Two things narrow it. First, Phase 1 already makes the projected file
  read-only, so mobile *editing* is lost at Phase 1 regardless of transport —
  what is genuinely at stake here is mobile *reading*. Second, the cheapest
  answer may not be an endpoint at all: an installation can keep a
  periodically committed, explicitly non-authoritative snapshot of the
  projection (the recovery artifact already specified in the Owner Decision
  below), which any file-syncing client can read exactly as it does today.
  That is likely sufficient for reading and requires no new component — the
  standard this DIP has applied throughout. **Trigger:** decide before the
  first space flips to Phase 1, since that is when mobile access actually
  changes.
- **Loss to mitigate: the projection is no longer an independent recovery
  copy.** Today, the committed `next_actions.org` is an artifact independent
  of any other system — if the event pool were ever corrupted or lost, the
  org file in git history is still a readable, self-contained record.
  Gitignoring the projection removes that independent copy: once this
  decision lands, the event pool (Specification, "Pool vs. chain") becomes
  the *only* copy of the state that produces `next_actions.org`, for any
  machine that has not separately preserved its own generated file. This is
  a real loss, not a hypothetical one, and this DIP does not treat it as an
  acceptable trade made silently. **Belt-and-braces mitigation — the second
  ratified decision in this section:** a projection snapshot is committed
  **periodically** — weekly, or via a [DIP-0035](DIP-0035-job-contracts.md)
  job contract on that cadence — **explicitly marked non-authoritative**
  (e.g. a `# SNAPSHOT — recovery artifact only, not source of truth,
  projector output as of height N` header, distinct from Phase 1's own
  `# GENERATED` header, so a reader can never mistake the periodic snapshot
  for the live, currently-authoritative file). Its only purpose is to give
  a future incident response something to read if the ledger itself is ever
  unavailable or corrupted — it is never regenerated *from*, never diffed
  against for Phase 0's shadow-diff, and never a second source of truth
  competing with the event pool, the same non-authoritative, disposable-cache
  posture DIP-0034's index and DIP-0042's snapshots already establish for
  their own derived artifacts.

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
- `ENG-2026-0727-004` — workstation↔server sync topology and its duplicate-resurrection
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
