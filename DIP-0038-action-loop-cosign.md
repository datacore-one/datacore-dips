# DIP-0038: Action Loop + Co-sign

| Field | Value |
|-------|-------|
| **DIP** | 0038 |
| **Title** | Action Loop + Co-sign |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Implemented |
| **Created** | 2026-07-30 |
| **Updated** | 2026-09-12 |
| **Tags** | `action-loop`, `co-sign`, `approvals`, `briefing`, `policy`, `datacore-v2` |
| **Affects** | `.datacore/lib/briefing/actions.py`, `.datacore/lib/ledger/policy.py`, `.datacore/config/approvals_policy.yaml`, future `cos_approval_*` MCP wiring, Telegram dismiss/approve handlers |
| **Specs** | `.datacore/lib/briefing/actions.py`, `.datacore/lib/ledger/policy.py` |
| **Agents** | any process that materializes briefing items into ledger items (`briefing.actions.materialize`); any human approver granting cosign for a side-effecting item |
| **Depends** | [DIP-0034](DIP-0034-event-ledger-substrate.md) — Event Ledger Substrate. Non-functional without it: the `item.create`/`approval.grant` event schema, `EVENT_TYPES`, and the Task 5.2b cross-actor HLC ordering fix this DIP's grant→create causality relies on. |
| **Relates to** | winston-open-gaps item 7 (approvals loop built but never wired), DIP-0037 (Grounded Briefings — the upstream producer of the items this DIP materializes, soft/optional), DIP-0032 (Egress Enforcement — structural precedent for "policy file + fail-closed defaults"), DIP-0009 (GTD Specification — adjacent, disambiguated GTD task-state model, see Specification), DIP-0013 (Meetings Module §5.2 — escalation-detection pattern cited in Open Questions), DIP-0006 (Open Questions Management — superseded into DIP-0013 §4, cited for the same reason), `ENG-2026-0729-030` (signing opt-in amendment — the trust boundary this DIP's co-sign gate operates under) |

> **Audit amendment status: Proposed (2026-09-11/12).** The trust-boundary,
> content-binding, lifecycle and authority-configuration corrections recorded
> below remain under review. The historical `Implemented` status does not
> ratify those amendments or certify deployed conformance.

> **Ratification note (2026-08-27).** Status moved `Draft` → `Implemented` on the
> owner's instruction. **No human review was performed on this DIP.** It is recorded
> here rather than left implicit, because the governance rule in `CLAUDE.base.md` is
> that `Implemented`/`Accepted` require owner ratification — this satisfies that rule
> by owner instruction alone, not by review.
>
> `Implemented` here means the work this DIP specifies has landed. It does **not**
> mean every follow-up named in the body is closed; several of these DIPs explicitly
> record outstanding gates as follow-up work, and those remain open. Read the
> Implementation/Rollout sections for the per-DIP position rather than inferring it
> from this status field.


**Compatibility decision (2026-09-14, proposed audit amendment):** New workflow
policies are explicit opt-ins, disabled by default. `DATACORE_REVIEW_BEFORE_EXECUTION=1`
adds strict review freshness/contract gating; `DATACORE_CADENCE_PROPOSALS=1`
selects proposal-only cadence/heartbeat production. `DATACORE_INSTANCE_BOUND_EXECUTION=1`
selects the parked experimental allocation model, tracked in
[core issue #192](https://github.com/datacore-one/datacore/issues/192); it is not
approved for deployment or inclusion in main. Earlier audit prose that treats
these additions as mandatory must be read within that opt-in scope. Data
preservation, truthful completion, private output, operator controls and exact
authority checks remain safety invariants. Unknown-effect retry policy remains
pending a separate owner decision. No implemented/audited status is asserted for
the parked proposal or any unverified deployment.


## Summary

Introduces the **action loop**: the mechanism that turns a briefing item
(grounded prose describing something that needs doing, per DIP-0037) into a
ledger item (`item.create`, per DIP-0034) exactly once, ever — and gates the
creation of any item whose declared `effects` are side-effecting (sending an
email, moving money, deploying to prod) behind a recorded human grant
(`approval.grant`) before it may be appended at all. Two modules do this:
`briefing.actions` (`item_id`, `materialize`, `act`) turns items into ledger
items and never lets a dismissed item come back, no matter how many more
times a briefing pipeline re-derives the same underlying text; `ledger.policy`
(`Policy`, `guarded_append`) is the single sanctioned gate through which any
side-effecting `item.create` must pass. This closes the specific,
long-standing gap named in the Winston deep-audit's open-gaps list: approval
machinery (`cos_approval_*` MCP tools) that existed, unwired, for months,
while cron-generated briefings kept ending in questions ("queue those into
nightshift?") nobody had a mechanical way to act on.

**Ledger items are not GTD tasks.** Ledger item states are disjoint from
org-mode's TODO/NEXT/WAITING/DONE; dismissing a briefing item never completes
an org task. `materialize()` never writes to `inbox.org` or
`next_actions.org` — briefing items are system-generated candidates for
review, not human-authored intentions, so they deliberately run outside the
single-capture-point chain rather than through it. See [DIP-0034](DIP-0034-event-ledger-substrate.md)'s
source-of-truth boundary and [DIP-0009](DIP-0009-gtd-specification.md) for
the GTD side of this; the full disambiguation and the capture-point argument
are in Specification below.

**Trust boundary.** This is a cooperative application control inside one
owner-controlled installation. An unsigned actor name is self-declared.
Signing authenticates an event against a configured key only when verification
is enforced; independent approver authority additionally requires protected
private keys, registry and policy. A shared OS identity, shared credentials or
an environment flag alone does not establish that boundary. See TRUST BOUNDARY.

## Agent Context

### When to Reference This DIP

**Always reference when:**
- Turning a briefing/candidate item into a durable ledger item — calling,
  wrapping, or reasoning about `briefing.actions.materialize`.
- Appending or evaluating an `item.create` whose declared `effects` intersect
  a cosign-gated set (`email.send`, `payment`, `prod.deploy` by default) —
  anything that must pass `ledger.policy.guarded_append`.
- Building or reasoning about Phase 6 wiring: `cos_approval_*` MCP tools,
  Telegram dismiss/approve handlers, or any new caller of
  `materialize`/`act`.
- Answering whether a dismissed briefing item can be recovered, or whether
  ledger item state overlaps `inbox.org`/`next_actions.org` GTD state.
- Adding a new event type or payload shape whose id might collide with
  `briefing.actions.item_id`'s dedupe key, or reasoning about the escalation
  path for a permanently-blocked (ungranted) item.

### Quick Reference for Agents

| Question | Answer |
|----------|--------|
| Does dismissing a briefing item touch `inbox.org` or `next_actions.org`? | No. Ledger items are a disjoint object class from org-mode GTD tasks ([DIP-0034](DIP-0034-event-ledger-substrate.md), [DIP-0009](DIP-0009-gtd-specification.md)); `materialize()`/`act()` never write to org files. |
| Is a co-sign grant cryptographically verified? | The signed policy path verifies its signature and registry binding. Unsigned paths are cooperative; independent identity also requires protected keys, policy and registry. See TRUST BOUNDARY. |
| Can a dismissed item be un-dismissed? | No mechanism exists in the current event vocabulary. Dismissal is fold-level terminal; the only recovery is creating an unrelated new ledger item under a new id — see Open Question 4. |
| Which event authorizes a gated `item.create`? | `approval.grant`, validated by `guarded_append` checks, including complete content binding, actor/space/ID binding and creation replay refusal. |
| Where does an ungranted side-effecting item go? | `MaterializeResult.blocked`; nothing is written to the log, and it reappears on every re-materialize call until granted — see Open Question 3 for the (deferred) escalation path. |
| Who can gate an `item.create`? | Only the single `policy.approver` named in `.datacore/config/approvals_policy.yaml`; per-effect approvers are Open Question 2. |

### Related Agents

| Agent | Uses This DIP For |
|-------|-------------------|
| *(none registered yet)* | No entry in `.datacore/registry/agents.yaml` calls `materialize`/`act`/`guarded_append` today. Verified absent, not omitted: Phase 6 wiring (see Rollout Plan) is what gives `cos_approval_*` MCP tools and Telegram dismiss/approve handlers a real caller. |
| `nightshift-orchestrator` | Named only as the plausible eventual consumer of materialized side-effecting items — the motivating winston-open-gaps quote ("queue those into nightshift?") points here — but no code path in this DIP or [DIP-0011](DIP-0011-nightshift-module.md) connects them yet; do not treat this as a live integration. |

### Integration Points

- [DIP-0034](DIP-0034-event-ledger-substrate.md) — hard dependency: event
  schema, `approval.grant` type, Task 5.2b cross-actor HLC ordering fix.
- [DIP-0037](DIP-0037-grounded-briefings.md) — soft/optional upstream
  producer of the items `materialize` consumes.
- [DIP-0032](DIP-0032-egress-enforcement.md) — structural precedent for
  "policy file + fail-closed defaults," not a functional dependency.
- [DIP-0009](DIP-0009-gtd-specification.md) — adjacent GTD task-state model;
  disambiguated, never integrated (see Specification).
- [DIP-0013](DIP-0013-meetings-module.md) §5.2 — escalation-detection
  pattern cited (not reused verbatim) for Open Question 3, via
  [DIP-0006](DIP-0006-open-questions-management.md) which it supersedes.

## Motivation

### Problem: the built-but-unwired approvals genre

Datacore had, before this phase, a recurring failure shape: capability that
exists in code but is never connected to the flow a human actually lives in.
The Winston 2026-07-12 deep audit named this explicitly as open gap #7:

> **Approvals loop unused** — Winston's cron runs end with questions ("queue
> those into nightshift?") that now reach Telegram but still aren't
> actionable. The `cos_approval_*` MCP tools (datacore-app) exist but aren't
> wired into inbox/tomorrow flows.

The tools existed. The Telegram delivery pipe existed. What was missing was
the connective tissue in between: a stable identity for "this specific
briefing item" that a later approval or dismissal could refer back to, and a
gate that would actually enforce "a human looked at this before it does
something with real-world consequences" rather than trusting that enforcement
would happen by convention. Without that connective tissue, "built" and
"used" stayed two different states indefinitely — the gap wasn't a missing
feature, it was a missing *wiring contract* between an already-shipped tool
surface and the daily flow.

A second, related failure shape motivates the never-resurface guarantee
specifically: **briefings ending in non-actionable questions**. A daily
briefing that surfaces "should I queue X?" with no mechanism to record "no,
don't ask again" forces the human to either (a) act on it every single day,
or (b) ignore the question, in which case it keeps reappearing — **dismissal
repetition**: the user re-dismissing the same item, worded slightly
differently each run, because nothing durable recorded that they'd already
said no. This is not a hypothetical: it is the direct, observed cost of
letting "item I've seen and rejected" live only in the human's memory instead
of in a system of record. A briefing pipeline that regenerates prose fresh
each run, with no stable identity for "the same underlying thing," makes this
structurally unavoidable — the fix has to live at the identity layer (this
DIP's `item_id`), not at the prose layer.

### Use cases

1. **A briefing item becomes a durable, actionable ledger item exactly once.**
   A human (or an agent acting for them) can `materialize` a batch of
   briefing items every day, and the same underlying item — however the
   wording drifts — never creates a second ledger item once the first has
   been handled.
2. **Dismissal is permanent, mechanically, not by convention.** Dismissing a
   briefing item removes it from every future briefing run's candidate set,
   forever, without requiring the dismissal logic to live in the briefing
   generator itself (it lives in the fold, per DIP-0034).
3. **Side-effecting actions require a recorded human grant before they can
   exist at all**, not just before they *run*. The gate is at `item.create`
   time — an item with `effects: [email.send]` cannot even be created without
   an `approval.grant`, closing the gap between "an agent decided to do
   something consequential" and "a human is on record having agreed to it."
4. **The wiring contract the audit found missing gets a concrete shape.**
   `cos_approval_*` MCP tools, Telegram dismiss/approve actions, and
   `plur_learn` capture of dismissals (Phase 6, see Integration below) all
   have a stable event-log substrate to attach to, instead of needing to
   invent their own notion of item identity.

## Current Workaround (pre-DIP)

- Cron-generated briefings surface open questions in prose, delivered via
  Telegram, with no mechanism for a reply to be interpreted as "yes, do it,"
  "no, and stop asking," or "yes, but you need my sign-off on this one
  specific consequential step."
- The `cos_approval_*` MCP tools (`cos_approval_submit`, `cos_approval_get`,
  `cos_approval_list_pending`, `cos_approval_decide`) exist in the
  `datacore-app` MCP surface but have no caller in the inbox/tomorrow flow —
  built, tested in isolation, never invoked end to end.
- "Dismissed" has no durable representation at all: a human ignoring or
  verbally rejecting a briefing suggestion has no effect on whether the next
  day's briefing surfaces the same suggestion again, because nothing records
  that rejection anywhere the next run's generation logic can see.
- Side-effecting actions (sending email, spending money, deploying) that an
  agent might take on a human's behalf have no uniform pre-execution gate —
  enforcement, where it exists at all, is ad hoc per call site.

## Specification

### Relationship to GTD, org-mode, and the single capture point

**Ledger items are a distinct object class from GTD tasks.** DIP-0034
establishes the boundary this DIP inherits: org files remain the source of
truth for GTD tasks, and the ledger tracks a *disjoint* class of objects —
briefing/delegation/verification objects, per DIP-0034's Backwards
Compatibility section and Open Questions #1 ("Org files remain the source of
truth for GTD tasks; the ledger tracks briefing/delegation/verification
objects, a distinct object class"). Concretely, for this DIP: a ledger
item's states (`created`/`claimed`/`completed`/`verified`/`dismissed`, per
`fold.py`) share no code path, no file, and no identifier space with
org-mode's GTD states (TODO/NEXT/WAITING/DEFERRED/DONE/CANCELLED, per
[DIP-0009](DIP-0009-gtd-specification.md)). `item.dismiss` never marks an
org heading DONE or CANCELLED; `item.create` never appends a heading to
`inbox.org` or `next_actions.org`; nothing in `briefing.actions` or
`ledger.policy` opens, parses, or writes any `.org` file. The vocabulary was
originally close by accident, not design — `task.create`/`task.claim`/
`task.complete` echoed TODO/NEXT/DONE, a legacy of the substrate's first
consumer being task-shaped rather than a deliberate choice (see DIP-0034's
Naming note) — and DIP-0034 OQ-5 renamed the family to `item.*` specifically
because that echo was a standing hazard, not a feature: this DIP's own text
had to disambiguate "ledger task" from "GTD task" on every use, and a reader
skimming the schema could plausibly mistake `task.create` for a GTD event.
The rename strengthens this boundary rather than merely stating it — the
ledger's event vocabulary (`item.create`/`item.claim`/`item.complete`) no
longer collides with, or reads as an alias of, org-mode's TODO/NEXT/DONE
state machine. The Motivation's "queue those into nightshift?" quote still
directly evokes DIP-0011's `nightshift.org`; this section exists
specifically so a reader of this DIP alone, without also having read
DIP-0034's Open Questions, has a textual anchor for the fact that these are
two independent systems that share adjacent subject matter, not one system
with two names.

**Why `materialize()` bypasses `inbox.org` — deliberately, not by oversight.**
The single-capture-point principle (`inbox.org` as the sacred point of entry)
is scoped to *human-initiated* capture: a person's own intentions, captured
once, then triaged. A briefing item is not that — it is a system-generated
candidate produced by a scheduled pipeline (per DIP-0037, when grounded) for
a human to *review*, not something the human is asking the system to
remember on their behalf. Routing every briefing item through `inbox.org`
before it could become a ledger item would conflate two different kinds of
"pending thing": a human's own captured intention, and a machine's proposal
awaiting human judgment. This DIP keeps them in separate systems on purpose —
`materialize()` turns a reviewed-or-reviewable candidate directly into a
ledger item (gated, if side-effecting, by `approval.grant`), never into an
inbox entry — and the never-resurface guarantee (below) gives a dismissed
machine proposal the durability that "single capture point" gives a human
capture: once rejected, either kind of pending item stops reappearing, each
by its own system's mechanism.

### `item_id`: normalization and idempotence

`briefing.actions.item_id(text) -> str` is a pure function: lowercase,
collapse any run of whitespace to a single space, strip, then take the first
16 hex characters of the sha256 digest of the normalized string. Two items
that describe the same underlying thing but are phrased slightly differently
across two briefing runs — different capitalization, different whitespace —
therefore land on the exact same id. This is the identity primitive the rest
of the DIP depends on: without a stable id that survives cosmetic rewording,
"has this already been handled" would have no reliable question to ask.
`item_id` never inspects effects, ledger state, or anything beyond the raw
text — it is deliberately the smallest possible normalization, not a
semantic-similarity match, so that its behavior stays exactly predictable
from the string alone.

### The never-resurface guarantee (fold-level, any-status skip)

`materialize(items, space_dir, actor, policy=None) -> MaterializeResult`
folds `read_events(space_dir)` **exactly once**, up front, for the whole
call — not once per item — producing one consistent snapshot of every item
id the space's ledger already knows about, regardless of that item's current
`status`. For each item, `tid = item_id(item["text"])`; if `tid` is already a
key in that snapshot's `state.items` — **created, claimed, completed,
verified, or dismissed, any status at all** — the item is skipped and
recorded in `result.skipped`, and no event is appended for it. This is the
entire mechanism behind "dismissed means gone forever": once a human
dismisses an item, its id is permanently present in every future fold, so no
future `materialize` call — no matter how many days later, no matter how the
briefing pipeline rewords the underlying text — can ever re-append its
`item.create`. The skip happens **before** `guarded_append` is even reached;
a dismissed item's re-creation is prevented at the identity-lookup layer, not
by the policy gate having some special case for "was this ever dismissed."

A second, narrower dedupe layer handles ids that repeat **within the same
call** (two items in one `materialize` invocation that normalize to the same
text): since nothing has been appended yet, the up-front fold can't see
these, so `materialize` tracks a local `seen_ids` set as it loops. Whichever
occurrence is seen first is attempted; every later occurrence of the same id
in the same call is skipped, regardless of whether the first occurrence was
created or blocked.

A single item's `PolicyError` (below) is caught inside the loop and recorded
in `result.blocked`, never propagated — one item awaiting a grant must never
prevent the rest of a batch (a whole day's other, unrelated briefing items)
from materializing.

### Policy gate semantics

`ledger.policy.Policy` names one `approver` (an actor string) and a
`cosign_effects` set (effect tags — `email.send`, `payment`, `prod.deploy` by
default). `requires_cosign(policy, event_type, payload)` is `True` iff
`event_type == "item.create"` and `payload["effects"]` intersects
`cosign_effects`. This predicate classifies effectful proposals; the enforcement
surface is broader: `guarded_append` validates creation, the complete resulting
content of updates, and current content at claim time.

The invariant is **approval binds what will be executed**. A grant can remain
valid for unchanged content. A changed title, effect, target, command, assignee,
body, property or other bound field requires a grant for the new complete
content. Removing an effect from an already approved item does not remove its
approval requirement. Claim validation must also cover imported/unguarded
historical updates and reject stale dispatch selections.

Before appending, the policy path validates:

1. Effect lists contain nonempty strings from the declared vocabulary; malformed
   values and unknown effects are refused.
2. Creation authority and declared per-principal limits apply to the actual
   writer, not a caller-controlled requester identity. Only the configured
   approver may append an `approval.grant` through the policy interface.
3. A required `approval_ref` identifies an existing `approval.grant` in the
   destination space by the configured approver. Both item identifiers must be
   nonempty and equal. Another space's grant cannot authorize this space.
4. The grant's `payload_hash` equals `approval_payload_hash` of the complete
   proposed content. The existing hash format is canonical UTF-8 JSON with
   sorted keys, compact separators and non-finite numbers refused; only
   `approval_ref` and the diagnostic `assignee_absent` are excluded, and absent
   `effects` is represented as an empty list. Conditional edit metadata is
   evaluated before hashing and is not persisted item content.
5. Signed policy operations require a valid grant signature against the
   configured actor-key registry. Unsigned grants cannot authorize that path.
6. A gated creation cannot reuse an already created ID. This is local admission
   and deterministic replay protection, not proof of cross-host exclusion.
7. Updates preserve creation authority and cannot change content after execution
   starts. Policy validation and replay use the same merge semantics. Malformed,
   stale or conflicting conditional edits are refused before local admission;
   conflicts received during replication remain visible and block execution
   until explicitly reconciled.
8. Claims require an available item, an allowed/registered writer, correct
   assignment, applicable budget/effect restrictions and a hash of the current
   content. Executor startup rechecks ownership and that hash.

Rejected local operations do not append an event. Cooperating policy operations
share a per-space local lock. Independent offline hosts are not serialized by
that lock; effects requiring exclusive execution need a separately enforced
execution/commit authority. A grant is not a distributed lock or fencing token.

### Amendment: Closed Effects Vocabulary — Precondition for Wiring (final-review wave, 2026-07-30)

Before this amendment, an effect tag that didn't match anything in
`cosign_effects` was treated as simply "not gated" — including a *typo'd*
effect (`emial.send` instead of `email.send`). That is a silent-bypass
gap: the whole point of `cosign_effects` is to force a human grant onto
specific side-effecting operations, and a misspelled effect string would
sail an `item.create` straight through ungated with no error of any kind.
Landed this wave, ahead of Phase 6 wiring (real `cos_approval_*` MCP tools
and Telegram handlers acting on `guarded_append`'s decisions): the policy
gains an optional `known_effects` list — the complete, closed vocabulary
of valid effect tags an `item.create` may declare, defaulting to
`cosign_effects` when the policy file omits it. `guarded_append` now
checks every effect named in a create's `effects` list against
`policy.effective_known_effects` and **fails closed** with `PolicyError`
naming the unknown effect if any isn't registered — unconditionally,
regardless of whether that effect would have required cosign at all. A
legitimate non-cosign effect must be explicitly added to a custom
`known_effects` list to remain usable; the tracked default
`.datacore/config/approvals_policy.yaml` now carries `known_effects` equal
to the three default `cosign_effects`.

This is a precondition for wiring, not the wiring itself: Phase 6's real
approval surfaces can now assume that every effect tag reaching
`guarded_append` is either a registered, deliberately-non-gated effect or
one of `cosign_effects` — never an unrecognized string masquerading as
"harmless because it didn't match."

### The `TRUST BOUNDARY`

Unsigned actor fields are self-declared. The application gate reduces accidental
unauthorized actions through its covered interfaces; it does not isolate an
adversarial process that can edit the same files or invoke raw tools.

`DATACORE_LEDGER_SIGN=1` enables signing and the policy path's grant-signature
verification. Signatures provide evidence of possession of a key, not an OS
security boundary. A caller who can read the approver's private key, replace the
trusted registry, weaken policy or bypass the consuming interface can defeat
independent approval. Environments promising protection against that caller
must protect those resources with separate identities/credential scopes or an
equivalent independently enforced boundary, and verify denial with negative
runtime tests. Merely creating a keypair or adding an application guard is
insufficient.

The current single-owner cooperative deployment model is distinct from such an
isolated deployment. This DIP does not claim tenant isolation, malicious-process
containment, global exactly-once effects or cross-host fencing. Deployments must
state their supported trust model rather than infer it from the word co-sign.

### `approval.grant` event flow

`approval.grant` is one of DIP-0034's `EVENT_TYPES`. The configured approver
uses the guarded interface or `ledger_cli.py approve` to record
`{"item": <item_id>, "payload_hash": <complete-content-hash>}`. Granting does not
need another grant, but the policy interface checks who grants it. A low-level
`EventLog.append` remains an import/storage primitive, not an authorization
interface. The flow is:

1. A briefing item with side-effecting `effects` is submitted to
   `materialize`. `guarded_append` finds no valid `approval_ref` and raises
   `PolicyError`; `materialize` catches it and records
   `(item_text, error_message)` in `result.blocked`. Nothing is written to
   the log.
2. The policy's named `approver` — a human, per the default policy — reviews
   the blocked item (surfaced via whatever the Phase 6 wiring exposes it as;
   see Integration) and appends `approval.grant` with
   the item ID and complete proposed content hash via the guarded approver
   interface.
3. The SAME item is re-submitted to `materialize`, this time carrying
   `approval_ref` set to the grant event's `hash`. `guarded_append` walks the
   applicable checks above; all pass; `item.create` is appended, with
   `approval_ref` forwarded into its payload (so the created item carries a
   durable pointer to the grant that authorized it).
4. A third submission of the same item (or the same `approval_ref` against a
   different item id) is rejected: either the never-resurface guarantee
   skips it outright (the id is already known, any status), or — if somehow
   the id differs but the ref is replayed — item binding rejects it directly.

### The HLC causal floor (Task 5.2b) as the ordering guarantee actions depend on

The action loop assumes that when `guarded_append` calls `read_events` to
look for a matching `approval.grant`, a grant that was genuinely written
*before* the create attempt will be found — including when the grant and the
create are written by two **different actors** (a human approver's file vs.
an agent's materializer file), which is the normal shape of this exact flow.
`read_events` sorts by `hlc` string; DIP-0034's fix in Task 5.2b (documented
in `ledger.log`'s module docstring, CROSS-ACTOR ORDERING) makes each
`append()` compute its HLC stamp from a floor that is the max across not just
the writer's own tail but every sibling actor's tail too, read under the same
lock, before stamping. Without that fix, a same-millisecond tie between two
different actors could tie-break on actor name alone — letting, in the worst
case, a create sort as if it happened before the grant that was meant to
authorize it, purely because of an alphabetical accident in actor naming, not
because of real write order. This DIP's cross-actor grant→create dependency
is precisely the shape that guarantee protects: the action loop does not
independently re-derive ordering safety, it is a direct consumer of
DIP-0034's 5.2b fix, and this phase's acceptance test (`test_briefing_actions.py`,
`test_acceptance_side_effect_cycle_blocked_then_granted_then_created`)
deliberately uses two distinct actors (`"human"` grantor, `"agent"`
materializer) to exercise that guarantee directly rather than only the
same-actor case, which the fix was never needed for.

### `act`: lifecycle validation

`act(space_dir, item_id, action, actor)` uses `guarded_append`. Claim validates
current content, assignment and authority. Completion is governed by lifecycle
ownership; dismissal/release/reassignment applies configured arbitration.
Unchanged work does not require a fresh approval for every bookkeeping event.
Caller-supplied details cannot substitute a different target item.

### Changes Required

- **New**: `.datacore/lib/briefing/actions.py` — `item_id`, `materialize`,
  `MaterializeResult`, `act`.
- **New**: `.datacore/lib/ledger/policy.py` — `Policy`, `PolicyError`,
  `load_policy`, `requires_cosign`, `guarded_append`.
- **New**: `.datacore/config/approvals_policy.yaml` — tracked, public, default
  policy (`approver: human`, `cosign_effects: [email.send, payment,
  prod.deploy]`).
- **Amended**: DIP-0034's `EVENT_TYPES` — `approval.grant` added (already
  present in the shipped `ledger.events` schema; this DIP is the first
  consumer that gives it real semantics).

### New Components

- `briefing.actions.item_id` — normalized-text identity function.
- `briefing.actions.materialize` — items → ledger items, with the
  never-resurface guarantee and in-call dedupe.
- `briefing.actions.act` — plain lifecycle transitions (`claim`, `complete`,
  `dismiss`).
- `ledger.policy.Policy` / `load_policy` — the approvals policy model and its
  YAML loader (fail-closed on a malformed file, defaults on a missing one).
- `ledger.policy.guarded_append` — the sole enforcement point for
  cosign-gated `item.create`.

### Interface Changes

- Any caller creating items from side-effecting work must now go through
  `briefing.actions.materialize` (or call `guarded_append` directly) rather
  than an ungated `EventLog.append("item.create", ...)` — direct `append`
  calls bypass the gate silently, by construction of `EventLog` itself
  (`EventLog` has no opinion about policy; that opinion lives only in this
  DIP's module).
- A new tracked config surface: `.datacore/config/approvals_policy.yaml` —
  editable by an operator to change the approver or the cosign-gated effect
  set, without code changes.

## Rationale

**Why fold-level, any-status skip rather than a "dismissed" special case in
`materialize`?** Putting the never-resurface rule at the fold layer (any
status counts as "known") rather than special-casing `status == "dismissed"`
in `materialize` means the guarantee also covers completed and verified
items for free — a briefing item that already became a completed item is
just as immune to re-creation as a dismissed one, with no separate code path
required. It also means the guarantee is exactly as strong as `fold`'s own
terminal-dismissal rule (DIP-0034: "once an item's status is dismissed, every
later event addressed to that item id is a history no-op") — the two layers
reinforce each other by construction rather than by two independently
maintained pieces of logic agreeing by convention.

**Why revalidate content at update and claim?** Creation-only validation lets
an approved item be changed into different work or imported through an unguarded
writer. Reusing a grant for unchanged content avoids unnecessary approval while
binding changed work to a new decision. The shared replay/validation merge
prevents approval of one representation followed by persistence of another.

**Why authorize the grant writer without requiring a meta-grant?** The configured
approver is the authority for this policy. Checking that writer enforces the
existing authority rather than creating an infinite hierarchy of approvals.
Independent identity protection still depends on the deployment boundary above.

**Why collect blocked items rather than raising out of `materialize`
entirely?** A real briefing batches many unrelated items in one call. One
item awaiting a human's attention (a side-effecting action nobody has
reviewed yet) has nothing to do with whether the day's other, non-gated
items should materialize. Treating `PolicyError` as fatal for the whole
batch would make the action loop as fragile as the single-writer git-lock
failure DIP-0034 was designed to move away from — one blocked thing should
never silently stop everything else.

### Alternatives considered

- **Store a `dismissed_ids` set separately from the fold** — rejected; this
  would create a second source of truth for "is this id known" that has to
  stay consistent with `fold`'s own state, exactly the shared-mutable-state
  problem DIP-0034 already solved once. The fold already has this
  information; `materialize` reuses it rather than re-deriving it.
- **Require a fresh grant for every lifecycle event** — unnecessary for
  unchanged content; update and claim validation reuse a still-matching grant.
- **A synchronous approval prompt at materialize time (block until a human
  answers)** — rejected; `materialize` is meant to run unattended (e.g. from
  a cron-triggered briefing pipeline) and cannot block on a human being
  available right now. The blocked/grant/re-materialize cycle is
  deliberately asynchronous: `materialize` always returns promptly, and a
  grant can arrive minutes, hours, or days later via whatever surface Phase
  6 wires up.

## Backwards Compatibility

Additive. No existing `EventLog`, `fold`, or `read_events` behavior changes —
`guarded_append` is a new wrapper callers opt into; code that still calls
`EventLog.append` directly continues to work exactly as before (ungated, as
it always was), it simply does not get the enforcement this DIP adds. A
space with no `.datacore/config/approvals_policy.yaml` file behaves under the
documented default policy (`approver=human`,
`cosign_effects={email.send, payment, prod.deploy}`) rather than erroring —
adopting this DIP requires no migration for spaces that have never used
side-effecting `effects` on an item. `briefing.actions.materialize` and `act`
are new functions with no prior callers to break.

## Security Considerations

- **Public-repo constraint.** Both `~/Data` and this dips repo are public (or
  public-adjacent). `.datacore/config/approvals_policy.yaml` is policy, not key
  material — it names an approver identity string and a set of effect tags,
  no secrets, and is tracked deliberately so the policy itself is auditable.
- **See TRUST BOUNDARY above.** Cooperative application checks, signature
  verification and independent OS/credential isolation are separate guarantees.
  Enabling signing alone does not provide the latter.
- **Fail-closed on malformed policy or malformed effects.** A present-but-
  broken `approvals_policy.yaml` raises `PolicyError` listing every problem
  found (never just the first), rather than silently falling back to
  permissive defaults or a partially-applied policy. Likewise, an `item.create`
  whose `effects` field is present but not a list fails closed with
  `PolicyError` rather than deciding gating from a value `requires_cosign`
  was never designed to interpret (e.g. iterating a bare string
  character-by-character).
- **Replay is explicitly rejected, not silently re-validated.** Check 8
  (no existing `item.create` for this id) means a captured, valid
  `approval_ref` cannot be reused to create a second item under the same id
  — it authorizes exactly one creation, closing an otherwise-obvious replay
  vector for anyone who can read the ledger (which, per DIP-0034, is not
  itself access-controlled).
- **Covered authorization surface.** Creation, content updates and claims
  enforce the checks above. This does not establish an independent security
  boundary around arbitrary tools or processes outside those interfaces.

## Implementation

### Reference Implementation

`.datacore/lib/briefing/actions.py` and `.datacore/lib/ledger/policy.py`,
with tests in `.datacore/lib/tests/test_briefing_actions.py` (30 tests,
including the two Phase 5 close acceptance tests — full materialize/dismiss/
re-materialize cycle, and the blocked/granted/re-materialized side-effect
cycle exercising the Task 5.2b cross-actor causal floor with distinct
actors) and `.datacore/lib/tests/test_ledger_policy.py`. 567 tests passing at
this phase's close on `feat/datacore-v2`, zero pre-existing or new failures.

Commit reference: `test(v2): phase 5 acceptance roll-up` (branch
`feat/datacore-v2`).

### Rollout Plan

**Phase 5 (this DIP — shipped): the mechanism.** `briefing.actions` +
`ledger.policy` + the tracked default policy file + full test coverage,
including end-to-end acceptance tests for both the never-resurface guarantee
and the block→grant→create cycle. No existing approval surface
(`cos_approval_*` MCP tools, Telegram) is wired to this mechanism yet.

**Phase 6 (follow-on, flagged): wiring.** `cos_approval_*` MCP tools
(`cos_approval_submit`, `cos_approval_get`, `cos_approval_list_pending`,
`cos_approval_decide`) become real callers of `materialize`/`guarded_append`
instead of standing unwired, closing winston-open-gaps item 7 directly.
Telegram gains dismiss/approve actions that call `briefing.actions.act` (for
dismiss) and append `approval.grant` (for approve) against a specific
`item_id` surfaced in the briefing message. Dismissal additionally triggers a
`plur_learn` capture — the human's rejection of a recurring suggestion
becomes a durable engram, not just a ledger-level dismissal, so the *pattern*
of "stop suggesting this" can inform future briefing generation, not only
prevent literal re-creation of the same item id.

## Open Questions

1. **Should `plur_learn` capture on dismissal be automatic or require a
   reason?** An unconditional capture risks noisy/low-signal engrams for
   routine dismissals (junk suggestions); requiring the human to supply a
   reason adds friction to what should be a one-tap action. Deferred to
   Phase 6 wiring, where real dismissal volume can inform the answer.
2. **Should the cosign policy support per-effect approvers** (e.g. a
   different approver for `payment` than for `email.send`) rather than one
   approver for the whole policy? Deferred — no observed need yet; the
   current single-approver model matches the current single-owner trust
   domain DIP-0034 already operates under, and a multi-approver model is
   easy to add later (widening `Policy.approver` to a mapping) without
   breaking the existing schema.
3. **What happens to a blocked item that never gets a grant?** Currently it
   simply stays out of `state.items` forever and reappears in every
   `result.blocked` on every re-materialize call (since it's never actually
   created, the never-resurface guard doesn't apply to it — only to created/
   dismissed ids). Whether a blocked item should eventually be surfaced
   differently (e.g. escalated, or auto-dismissed after N days of no
   decision) is Phase 6 wiring's call, not this DIP's — but that call should
   not re-derive an escalation mechanism from scratch. [DIP-0006](DIP-0006-open-questions-management.md)
   (Open Questions Management System), superseded into
   [DIP-0013](DIP-0013-meetings-module.md) §4, defines the system's one
   canonical escalation heuristic at §5.2 (Escalation Detection): an item
   appearing 3+ times across 7 days of daily standups escalates to the
   weekly meeting. The *counting shape* of that heuristic transfers directly:
   `result.blocked` already reappears, unaltered, on every re-materialize
   call for as long as an item stays ungranted, which is the same
   repeated-appearance signal DIP-0013 §5.2 counts. What does **not**
   transfer is the escalation *target* — DIP-0013 escalates to a weekly
   meeting attended by multiple stakeholders, while a blocked ledger item is
   a single-owner approval request with no meeting to escalate to. Phase 6
   should therefore reuse DIP-0013 §5.2's counting rule against
   `result.blocked` recurrence and choose a target suited to a single
   approver (e.g. more prominent Telegram resurfacing after N re-blocked
   cycles, or an explicit stale-grant flag) rather than inventing a new
   counting threshold. This DIP does not implement that; it is left open,
   now anchored to the existing mechanism instead of independent of it.
4. **Escape hatch for an accidental dismiss.** None exists today — verified
   against the reference implementation, not assumed. `fold._handle_dismiss`
   sets an item's status to `"dismissed"`, and `fold._dismissed` then turns
   every later event addressed to that id into a history no-op, **including
   the `owner.set` administrative override** (per `ledger/fold.py`'s module
   docstring: `item.dismiss` is terminal, "nothing can revive a dismissed
   item"). `materialize`'s never-resurface guarantee compounds this: because
   `item_id` hashes the item's *normalized* text, re-submitting the
   identical or cosmetically-reworded item is silently skipped forever (its
   id is already known to the fold, any status), and a manually
   hand-appended event addressed to that same id is a no-op for the same
   reason — this is not merely hard to undo, the event vocabulary has no
   operation that undoes it. The only way to get equivalent work back into
   the ledger is to make it a genuinely *different* id: either `materialize`
   naturally allocates a new one because the item's substantive wording
   changed enough to change the normalized-text hash (a new content hash,
   not a revival), or an operator hand-appends a fresh `item.create` under a
   new id directly via `EventLog.append`, bypassing `materialize` entirely
   (a new, unrelated event, not a corrective one in any mechanical sense —
   nothing links it back to the id it is meant to replace). Both routes
   produce an unrelated new ledger item; the original stays permanently
   dismissed, its history intact for audit, but nothing in the ledger marks
   the new item as "this replaces that" — a human has to track that link
   themselves, outside the system, if they want one. A fat-fingered Telegram
   dismiss of an important item is therefore, today, an unrecoverable loss of
   that specific item id. A proper undo — e.g. a new `item.undismiss` event
   type, or an admin override explicitly scoped to clear (not merely attempt
   to overwrite) a dismissed status with its own audit trail — does not exist
   in the current event vocabulary and is not designed by this DIP. Recorded
   here as deferred behavior. The current `act` dismissal path applies
   ownership/arbitration checks; it is not an ungated operation. Designing an
   explicit correction or replacement link remains separate from signing:
   enabling signatures does not provide undo or protect a shared OS identity.
   Revisit this recovery design before offering an undo action or claiming
   that a dismissed item can be restored under the same identifier.

## References

- winston-open-gaps item 7 — "Approvals loop unused... The `cos_approval_*`
  MCP tools (datacore-app) exist but aren't wired into inbox/tomorrow
  flows." The direct motivating gap this DIP closes the mechanism side of.
- DIP-0034 — Event Ledger Substrate (the `item.create`/`approval.grant` event
  schema this DIP's gate operates on; the Task 5.2b cross-actor HLC causal
  floor this DIP's grant→create ordering depends on; the opt-in-signing
  trust-boundary stance this DIP's TRUST BOUNDARY section inherits).
- DIP-0037 — Grounded Briefings (the upstream producer of the items
  `materialize` consumes; a grounded briefing is a better input to
  materialization than an ungrounded one, though this DIP does not itself
  depend on grounding having been applied).
- DIP-0032 — Egress Enforcement (structural precedent reused here for
  "policy file + fail-closed defaults" reasoning: a present-but-malformed
  policy file errors loudly, a missing one falls back to a safe default).
- DIP-0009 — GTD Specification (the org-mode TODO/NEXT/WAITING/DONE state
  vocabulary this DIP's ledger item states are disjoint from; see
  Specification's Relationship to GTD, org-mode, and the single capture
  point).
- DIP-0013 — Meetings Module (§5.2 Escalation Detection, the canonical
  count-based escalation heuristic cited in Open Question 3).
- DIP-0006 — Open Questions Management System (superseded into DIP-0013 §4;
  cited alongside DIP-0013 for provenance of the escalation mechanism Open
  Question 3 reuses rather than re-derives).
- `ENG-2026-0729-030` — signing opt-in amendment (the ruling this DIP's
  TRUST BOUNDARY section is a direct consequence of).

## Authority configuration — proposed clarification (2026-09-12)

Configuration used to select approval authority, principal limits or tool
effects must have unambiguous string-key mappings. Duplicate keys at any depth
and non-string keys are invalid; readers must not choose the last value.
Malformed principal-limit blocks cannot become empty limits. Integer protocol
and limit fields exclude booleans. Diagnostics identify the failing rule
without reproducing rejected configuration values.

A principal registry binds each canonical writer to at most one principal,
including direct principal names, writer aliases and supported run suffixes.
Principal names are canonical lowercase identities; writer aliases use the
same normalization as lookup. An invalid or ambiguous registry cannot be
treated as an empty valid registry. When execution context requires a registry
lookup, missing or failed lookup must refuse the tool call; it cannot select
an `unknown` or actor-named policy as a fallback. Explicitly supplied trusted
execution context remains subject to its deployment's independent boundary.

The low-level ledger policy's documented default for a genuinely absent policy
is retained. A dangling policy reference is a read failure, not intentional
absence. Execution-policy and allocation consumers that require configured
authority continue to require it. These rules do not authenticate a writable
configuration file or isolate processes sharing its OS identity.

| Field | Record |
|---|---|
| Previous requirement | Present malformed policy must fail closed, but ambiguity, YAML coercion, registry membership conflicts and failed-context fallback were unspecified. |
| Problem | Duplicate mappings could replace constraints or approvers; malformed limits became empty limits; multiple principal memberships depended on mapping order; identity read failure could select another policy. |
| Corrected requirement | Unique typed configuration, unique canonical writer membership and explicit refusal of failed required identity resolution, with sanitized diagnostics. |
| Reason | Parsing and lookup failures cannot create or enlarge execution authority. |
| Implementation impact | Shared strict YAML loader in policy/effects/principal/allocation readers, validated limits and memberships, fail-closed tool context construction. |
| Compatibility impact | Existing valid mappings and unambiguous YAML aliases remain supported; incomplete or ambiguous authority configuration must be repaired. No data or ledger rewrite. |
| Tests affected | Duplicate/nested mappings, false/null/list limits, boolean integer fields, conflicting writer aliases, missing/invalid registry fallback, safe diagnostic text, explicit fixtures and shipped registry template. |
| Runtime/deployment impact | Validate installed policy and private registry using the actual interpreter and execution identity before activation; qualify negative tool decisions and valid writer aliases. |
| Status | Proposed; candidate code and tests do not certify active deployment. |

## Normative change record — 2026-09-11 audit

| Previous requirement | Problem | Corrected requirement | Implementation / tests | Compatibility / deployment |
| --- | --- | --- | --- | --- |
| Creation-only approval; item-ID-only grants | Approved content could change, and imported updates bypassed the original decision | Bind complete resulting content and revalidate at update/claim | `ledger.policy`, shared `ledger.edits.update_payload`, executor startup; policy/adversarial/replicated-edit tests | Legacy ID-only grants require a new content-bound grant; existing complete-content hash format is preserved |
| Signing alone turns process trust into an independent cryptographic boundary | Same-identity processes may possess keys or change policy/registry | Verify signatures and separately protect keys, registry, policy and consuming interfaces when independent authority is required | Signed-grant rejection tests; deployment-specific isolation tests required | No assertion that enabling a flag installs OS isolation; cooperative single-owner scope remains explicit |
| Ungated grant and lifecycle interfaces | Writer/claim authority and changed content were not checked | Guarded approver and lifecycle interfaces, content-bound claims and explicit conflict reconciliation | `briefing.actions`, `ledger.policy`, `executors.base` and their regressions | Direct log append remains a storage/import primitive; callers requiring enforcement must use the covered interfaces |
| A local singular gate implied sufficient execution safety | Separate hosts may admit work concurrently | Local serialization is scoped to one host; exclusive effects need independent execution/commit authority | Local concurrency tests; cross-host deployment verification is separate | Does not introduce a lease, distributed lock or fencing promise |

These corrections retain the historical motivation and the original ratification
note. Phase 6 integration and other explicitly deferred features remain future
work. The audit changes are subject to the repository's normal review process;
the status of unrelated Draft DIPs is not changed by this amendment.
