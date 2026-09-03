# DIP-0038: Action Loop + Co-sign

| Field | Value |
|-------|-------|
| **DIP** | 0038 |
| **Title** | Action Loop + Co-sign |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Implemented |
| **Created** | 2026-07-30 |
| **Updated** | 2026-08-27 |
| **Tags** | `action-loop`, `co-sign`, `approvals`, `briefing`, `policy`, `datacore-v2` |
| **Affects** | `.datacore/lib/briefing/actions.py`, `.datacore/lib/ledger/policy.py`, `.datacore/config/approvals_policy.yaml`, future `cos_approval_*` MCP wiring, Telegram dismiss/approve handlers |
| **Specs** | `.datacore/lib/briefing/actions.py`, `.datacore/lib/ledger/policy.py` |
| **Agents** | any process that materializes briefing items into ledger items (`briefing.actions.materialize`); any human approver granting cosign for a side-effecting item |
| **Depends** | [DIP-0034](DIP-0034-event-ledger-substrate.md) — Event Ledger Substrate. Non-functional without it: the `item.create`/`approval.grant` event schema, `EVENT_TYPES`, and the Task 5.2b cross-actor HLC ordering fix this DIP's grant→create causality relies on. |
| **Relates to** | winston-open-gaps item 7 (approvals loop built but never wired), DIP-0037 (Grounded Briefings — the upstream producer of the items this DIP materializes, soft/optional), DIP-0032 (Egress Enforcement — structural precedent for "policy file + fail-closed defaults"), DIP-0009 (GTD Specification — adjacent, disambiguated GTD task-state model, see Specification), DIP-0013 (Meetings Module §5.2 — escalation-detection pattern cited in Open Questions), DIP-0006 (Open Questions Management — superseded into DIP-0013 §4, cited for the same reason), `ENG-2026-0729-030` (signing opt-in amendment — the trust boundary this DIP's co-sign gate operates under) |

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

**Trust boundary, stated up front, not buried.** While signing is dormant,
the actor asserting a grant is self-declared, not cryptographically
authenticated — this gate is a **process-boundary control** that prevents an
*accidental* ungated side effect, not a defense against adversarial forgery
by a process that can already write to the approver's actor file. Do not read
"co-sign" as cryptographically binding until `DATACORE_LEDGER_SIGN=1` is on;
see TRUST BOUNDARY below for the exact scope.

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
| Is a co-sign grant cryptographically verified today? | No. Actor identity is self-declared, process-boundary trust only, until `DATACORE_LEDGER_SIGN=1` — see TRUST BOUNDARY. |
| Can a dismissed item be un-dismissed? | No mechanism exists in the current event vocabulary. Dismissal is fold-level terminal; the only recovery is creating an unrelated new ledger item under a new id — see Open Question 4. |
| Which event authorizes a gated `item.create`? | `approval.grant`, validated by `guarded_append`'s 8 ordered checks (actor-bound, id-bound, replay-blocked). |
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
`cosign_effects` — **only `item.create` is ever gated**; once a side-effecting
item exists with a valid grant, its downstream lifecycle events (`item.claim`,
`item.complete`, ...) are never re-checked, keeping the gate singular
(one grant, checked once, at creation) rather than requiring a fresh grant
for every event a long-running item ever emits.

`guarded_append(log, type, payload, policy=None, space_dir=None)` is the
**only sanctioned way** for gated code to append an `item.create` — calling
`EventLog.append` directly bypasses the gate entirely. Before `requires_cosign`
is even consulted, a present `effects` field is type-checked: it must be a
`list`, or `guarded_append` fails closed with `PolicyError` rather than
letting a malformed value (e.g. a bare string, which Python iterates
character-by-character) silently decide gating from garbage — **fail-closed
effects validation**.

When `requires_cosign` is `True`, ALL of the following must hold, checked in
order, each raising `PolicyError` naming exactly which failed, with nothing
later evaluated once one fails:

1. `payload["approval_ref"]` is present and non-empty.
2. It is the `hash` of an event that actually exists in the space (via
   `read_events`, which merges every actor's file).
3. That event's `type` is `"approval.grant"`.
4. That event's `actor` equals `policy.approver` — **actor-bound**: a grant
   from anyone other than the policy's named approver never counts, no
   matter how well-formed it otherwise is.
5. `payload["id"]` (the new event's own id) is a non-empty string, checked
   explicitly and *before* the comparison in (7) — so a gated create with no
   id at all can never slip through by coincidentally matching an equally
   id-less grant (two missing fields must never compare equal to each
   other). This is the **id-binding** half of the contract.
6. The matched grant's `payload["item"]` is likewise checked to be a
   non-empty string *before* being compared — a grant with no item binding
   must never validate any create, whatever that create's id is or isn't.
7. `payload["id"] == grant.payload["item"]` — the grant names *this specific*
   item id, not "any item this approver has ever blessed."
8. No event in the space is already an `item.create` for this same id — a
   granted `approval_ref` authorizes creation **exactly once**; replaying the
   same ref against a second create attempt at the same id is rejected as
   "item already created," not silently re-validated. This is the
   **replay-block**.

All eight checks run before `log.append` is ever called, so a rejected event
never touches the log file — `PolicyError` is raised on validation, not on a
partially-committed write that then has to be rolled back.

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

### The `TRUST BOUNDARY` (verbatim, from `ledger/policy.py`'s module docstring)

This is load-bearing enough to the whole gate's honesty that it is
reproduced here exactly as written in the reference implementation, not
paraphrased:

> TRUST BOUNDARY: while signing is dormant (`ENG-2026-0729-030`), actor
> strings are self-declared — `approval.grant` authenticity rests on process
> boundaries (who can write to the space's `<actor>.jsonl` file), not
> cryptography. It becomes cryptographic only when `DATACORE_LEDGER_SIGN=1`
> gives the approver a keypair (see `ledger.log.EventLog`'s `sign` parameter
> and `ledger.keys`). Until then, this gate prevents ACCIDENTAL ungated side
> effects (an item.create slipping into existence with no human ever having
> looked at it) — it does NOT defend against adversarial forgery: any
> process able to write to `policy.approver`'s actor file in this space can
> forge a self-declared grant. Do not present this gate as tamper-proof
> until signing is switched on.

Concretely: this DIP's gate is a **process-integrity control**, not (yet) a
**cryptographic-authenticity control**. It reliably prevents the failure mode
that actually motivated it — an agent's side-effecting `item.create` slipping
into existence with nobody having recorded a decision about it — because the
normal, non-adversarial path to writing `human.jsonl` is a human (or a
process acting under their direct control) doing so. It does not, today,
defend against a compromised or malicious process that has write access to
the approver's actor file forging a grant for itself. Signing
(`DATACORE_LEDGER_SIGN=1`, per DIP-0034) is the designed upgrade path for
closing that gap; it is deliberately not the default yet, per the same
opt-in-signing ruling DIP-0034 documents, because at the current single-owner
trust domain the marginal security is small relative to key-management cost.

### `approval.grant` event flow

`approval.grant` is one of DIP-0034's `EVENT_TYPES`. It is **never itself
policy-gated** — only `item.create` is — so an approver appends it via a
plain `EventLog.append("approval.grant", {"item": <item_id>})`, no
`guarded_append` involved. The flow, end to end:

1. A briefing item with side-effecting `effects` is submitted to
   `materialize`. `guarded_append` finds no valid `approval_ref` and raises
   `PolicyError`; `materialize` catches it and records
   `(item_text, error_message)` in `result.blocked`. Nothing is written to
   the log.
2. The policy's named `approver` — a human, per the default policy — reviews
   the blocked item (surfaced via whatever the Phase 6 wiring exposes it as;
   see Integration) and appends `approval.grant` with
   `payload = {"item": item_id(item_text)}` via their own actor's
   `EventLog`.
3. The SAME item is re-submitted to `materialize`, this time carrying
   `approval_ref` set to the grant event's `hash`. `guarded_append` walks the
   eight checks above; all pass; `item.create` is appended, with
   `approval_ref` forwarded into its payload (so the created item carries a
   durable pointer to the grant that authorized it).
4. A third submission of the same item (or the same `approval_ref` against a
   different item id) is rejected: either the never-resurface guarantee
   skips it outright (the id is already known, any status), or — if somehow
   the id differs but the ref is replayed — check 8 rejects the replay
   directly.

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

### `act`: lifecycle transitions are never re-gated

`act(space_dir, item_id, action, actor)` appends the `item.*` event for
`claim`, `complete`, or `dismiss` via a **plain** `EventLog.append` — no
`guarded_append`, no policy check. This is intentional and matches
`requires_cosign`'s scope exactly: the create is the single enforcement
point; an item's subsequent lifecycle is ungated by design, so a long-running
side-effecting item's `complete` event doesn't require a second grant, and a
plain (non-side-effecting) item's `dismiss` was never going to be gated in
the first place.

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

**Why gate only `item.create`, not every event a side-effecting item ever
emits?** A single, unambiguous enforcement point (creation) is easier to
reason about and to audit than "was every event in this item's lifecycle
individually authorized" — and re-checking cosign at, say, `item.complete`
would either require a *second* grant (extra friction for no real safety
gain, since the create already required a human to have looked at the
declared effects) or would need to re-derive "was this item ever properly
created" anyway, which is exactly what the create-time check already
established once. Per-event re-checking also does not compose well with
long-running items whose lifecycle spans days — a single grant at creation
is the natural unit of "a human agreed to this specific piece of work."

**Why is the grant mechanism a plain, ungated event rather than itself
requiring some meta-approval?** `approval.grant` is the exit from the gate,
not an entry into it — gating the grant itself would just relocate the
"who can create side effects unchecked" question one level up without
resolving it, and would require inventing a second policy for who may grant
grants. The trust boundary this DIP settles for is process-level (who can
write to the approver's actor file), consistent with DIP-0034's own opt-in
signing stance; a cryptographically-gated grant is exactly what turning on
signing (`DATACORE_LEDGER_SIGN=1`) upgrades this into, without requiring a
second gate mechanism invented specifically for grants.

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
- **Gate every lifecycle event on a side-effecting item, not just create** —
  rejected; see Rationale above (extra friction, no proportional safety
  gain, poor fit for long-running items).
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
- **See the TRUST BOUNDARY section above** — the substantive security caveat
  of this whole DIP: process-boundary trust, not cryptographic
  non-repudiation, until `DATACORE_LEDGER_SIGN=1` is switched on. This DIP
  does not claim tamper-proof approvals; it claims accidental-side-effect
  prevention, which is the failure mode that actually motivated it
  (an agent's ungated action slipping out with no human ever having seen the
  declared effects), not a defense against a malicious insider or a
  compromised process.
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
- **Not an authorization system beyond item creation.** This gate answers "may
  this side-effecting item come into existence" — it says nothing about who
  may later `claim` or `complete` it, which remains ungated per `act`'s
  design (see Rationale). Broader authorization, if ever needed, is future
  work layered on top, not something this DIP retrofits.

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
   here rather than built now, consistent with `act`'s dismiss path being
   deliberately ungated at the current trust level: revisit at the earlier
   of (a) an observed accidental dismissal in practice, or (b) the same
   signing-rollout trigger (`ENG-2026-0729-030`) that upgrades the trust
   boundary elsewhere in this DIP.

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
