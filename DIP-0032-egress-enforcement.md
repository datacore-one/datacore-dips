# DIP-0032: Egress Enforcement

| Field | Value |
|-------|-------|
| **DIP** | 0032 |
| **Title** | Egress Enforcement |
| **Author** | @datacore-one |
| **Type** | Infrastructure |
| **Status** | Partial |
| **Created** | 2026-07-25 |
| **Updated** | 2026-07-25 |
| **Tags** | `security`, `egress`, `agent-safety`, `chief-of-staff`, `approvals` |
| **Affects** | `datacore-app/daemon/datacored/adapters/`, `datacore-app/daemon/datacored/api/mail.py`, `~/.datacore/egress-policy.yaml`, `~/.datacore/cos/approvals/`, `/usr/local/lib/hermes-agent` (Phase 2) |
| **Specs** | `~/.datacore/egress-policy.yaml` |
| **Agents** | `chief-of-staff`, `hermes` (Telegram Winston) |
| **Relates to** | `datacore-one/datacore#30` (guardrails); `2026-07-25-winston-deep-audit.md` (Security §, HIGH); `2026-07-25-winston-egress-enforcement-design.md` (design proposal); DIP-0023 (messaging/trust tiers); DIP-0031 (agent error handling); ENG-2026-0718-024 |

## Summary

Establishes a **technical egress boundary** for autonomous agents (Winston /
chief-of-staff / hermes). Every action that leaves the box or affects the
outside world — email send, social post, Telegram, arbitrary HTTP, remote
code execution — must pass through an in-process enforcement gate that
classifies it against an owner-editable policy as **ALLOW / DENY / ASK**
before it can execute. ASK actions are **held as drafts** and queued for
owner approval on **both** the desktop app and Telegram; they leave the box
only when approved, delivering the *exact* held payload. Every decision is
written to an audit log. This turns "drafts only, never sends without
approval" from a **prompt-level instruction** into an **enforced boundary a
prompt cannot bypass**, directly implementing the open guardrails issue
`datacore-one/datacore#30` and closing the audit's #1 HIGH finding.

## Motivation

### Problem: "no autonomous egress" is a prompt, not a boundary

The Winston deep audit (`2026-07-25-winston-deep-audit.md`, Security §,
HIGH) found that **"Winston has no autonomous external egress" is a
prompt-level policy, not a technical boundary.** In reality the hermes agent
that drives Winston holds live capability to reach the outside world:

- **Gmail `send()` / reply** (Late API / SMTP)
- **Social posting** (Late API)
- **Telegram** outbound
- **Browserbase** (headless browser + proxies) / arbitrary HTTP
- **Modal** remote sandboxes (remote code execution)

The only "never send autonomously" control was a **string in a prompt**
(`queue_ai_tasks.py`: *"produce a ready-to-send draft, never send/publish"*).
An agent that ignores that instruction, is prompt-injected through content it
reads (an email body, a web page, a calendar invite), or is otherwise
manipulated past the prompt can **email, post, browse, and execute
remotely** on the principal's behalf.

For a product with **broad read access over a user's entire personal and
business life**, "drafts only, never sends without approval" must be a **hard
technical boundary**, not an instruction. This is exactly the open proposal
in `datacore-one/datacore#30` — per-action ALLOW / DENY / ASK guardrails with
cost caps, external-action approval, and risk escalation.

### Use cases

1. **Prompt-injection containment** — a poisoned email/web page instructs the
   agent to exfiltrate data or send on the user's behalf; the gate denies or
   holds it regardless of what the prompt now "believes".
2. **Autonomous draft-and-approve** — the overnight agent drafts a reply; the
   draft is queued; the owner approves it in the morning from the app or from
   Telegram, and only then does it send.
3. **Auditable egress** — "what did the agent try to send/post/execute, and
   what was allowed?" answerable from a single append-only log.
4. **Safe research browsing** — the agent may fetch web content for research
   (allow-with-log) without opening a general-purpose exfiltration channel to
   arbitrary hosts once an owner opts into a host allowlist.

## Current Workaround (pre-DIP)

- A prompt string in the nightshift task-queuer asks agents to draft, never
  send. No enforcement; no audit; no approval substrate wired to egress.
- The daemon's approval queue (`~/.datacore/cos/approvals/`, DIP-0030 CoS
  orchestration) exists and is surfaced to the app and Telegram, but **no
  egress action is routed through it** — agents can send directly.

This workaround is a single point of failure: one ignored or subverted
instruction and the boundary is gone with no record.

## Owner Decisions (folded into this DIP)

The design proposal (`2026-07-25-winston-egress-enforcement-design.md`) raised
three open questions. The owner's decisions, now normative:

1. **Approval surface = BOTH.** ASK actions surface on the **desktop app AND
   Telegram**. This is achieved by enqueueing to the single shared approval
   substrate both surfaces already read (§ Both Surfaces below) — no new
   channel is built.
2. **`browser.fetch` = ALLOW-with-log** (not deny-by-allowlist) by default.
   Research browsing stays low-friction; every fetch is audited. An owner may
   opt into deny-by-allowlist by adding an `allow_hosts` list to the rule.
3. **This is its own DIP** (DIP-0032), not an extension of the DIP-0023
   messaging/trust work. DIP-0023's trust tiers (owner > team > trusted >
   unknown) are referenced for ASK-eligibility (§ Security Considerations) but
   egress enforcement stands alone.

## Specification

### Enforcement surface

The set of actions treated as egress, and their default policy:

| Capability | Action id | Default policy | Rationale |
|---|---|---|---|
| Gmail send / reply | `email.send` | **ask** | Human approval; draft held until released |
| Social post (Late API) | `social.post` | **ask** | Human approval |
| Telegram outbound (to owner) | `telegram.send` | **allow** | Owner channel, allowlisted user; not third-party egress |
| Browserbase / arbitrary HTTP | `browser.fetch` | **allow (logged)** | Research browsing; owner may restrict via `allow_hosts` |
| Modal remote exec | `modal.exec` | **deny** | Remote code execution — never autonomous in v1 |
| Reads (email/calendar/repos/web-fetch) | `*.read` | **allow** | Read-only, no egress effect |
| *anything else* | (default) | **deny** | Fail closed — unknown actions never egress |

### Policy file

`~/.datacore/egress-policy.yaml` — owner-editable, shipped default written on
first load if absent (mode `0600`). Loaded mtime-cached so edits take effect
without a daemon restart. A malformed policy file **fails closed** (falls back
to the deny-default shipped policy and records an error), never open.

```yaml
version: 1
default: deny                 # unknown / unlisted action → DENY (fail closed)
rules:
  - action: email.send        # Gmail send / reply
    policy: ask
  - action: social.post       # Late API social posting
    policy: ask
  - action: telegram.send     # outbound to the allowlisted owner channel
    policy: allow
  - action: browser.fetch     # Browserbase / arbitrary HTTP — allow-with-log
    policy: allow
    # allow_hosts:            # uncomment to switch to deny-by-allowlist
    #   - github.com
    #   - api.openrouter.ai
  - action: modal.exec        # Modal remote code execution
    policy: deny
  - action: "*.read"          # non-egress reads (email/calendar/repos/web)
    policy: allow
cost_caps:                    # issue #30 — parsed now, enforced in v2
  daily_external_actions: 50
  escalate_after_denials: 3
```

Matching precedence: exact action id → first glob (`fnmatch`) rule → policy
`default`. A decision value that is not `allow`/`deny`/`ask` is coerced to
`deny`.

### Classification API

```python
classify(action: str) -> "allow" | "deny" | "ask"
```

Payload-independent. Host-allowlist refinement for `browser.fetch` is applied
in `enforce`/`decide` (which have the payload). Unknown actions resolve to
the policy `default` (`deny`).

`decide(action, payload) -> (decision, reason)` adds the host-allowlist
refinement: when `browser.fetch` has an `allow_hosts` list, a fetch whose host
is not in the list (or that carries no host) is denied; with no list it is
allow-with-log. Host match includes subdomains (`api.github.com` ⊂
`github.com`).

### The gate

```python
enforce(action, payload, *, on_ask,
        on_allow=None, requester_agent="cos.agent",
        risk=None, preview=None, idempotency_key=None) -> EgressResult
```

Behaviour:

- **allow** → run `on_allow(payload)` (the real egress) and return its result.
  If no `on_allow` is given the caller inspects `result.decision` and performs
  the action itself.
- **deny** → execute nothing, return a denied result.
- **ask** → build an approval request embedding the **exact payload**, hand it
  to `on_ask` (enqueue onto the shared approval substrate), and return an
  `EgressResult` with `decision="ask"`, `queued=True`, and the held draft.
  **Nothing is sent** until release.

Fail-closed guarantees:
- unknown action → `deny`;
- malformed policy → deny-default;
- if `on_ask` raises (queue unavailable) the exception **propagates** — an
  action that cannot be safely held is not sent.

Every call to `enforce` writes one record to the audit log (`allow` / `deny` /
`ask`), and `release` writes a `released` record. Payloads are **redacted** in
the audit log to key names plus a short (≤120 char) preview — recipients and
bodies are never logged.

### Release (approve → send the exact draft)

```python
release(approval, deliver) -> Any
```

Given an **approved** approval request, delivers `approval['action']
['payload']` — the exact payload that was held — via `deliver`. Raises
`EgressDenied` if the draft is not in state `approved`, so a pending, denied,
or expired draft can never be released. Approval never re-generates the
action; the released payload is byte-for-byte what was drafted.

### Both surfaces (app + Telegram) — one substrate

ASK reaches both approval surfaces because the gate enqueues onto the **single
shared approval store** both surfaces already read:

```
~/.datacore/cos/approvals/<YYYY-MM-DD>/queue.jsonl   (append-only, mode 0600)
```

- **App** reads it via the daemon route `GET /cos/approvals/pending` and
  decides via `POST /cos/approvals/{id}/decide`
  (`datacored/api/approvals.py`).
- **Telegram** reads it via the chief-of-staff module
  (`lib/cli_approvals.py` `list`, `lib/service.py`) over the same JSONL store.

No new notification channel is built. Enqueueing to this substrate — exactly
what `datacored/api/approvals.py` and the CoS CLI already use — is what
satisfies the owner's "BOTH" decision. Approving on either surface writes the
`approved` snapshot the same store; the gate's `release` then delivers.

### The regression guard ("prompt-only" can't creep back in)

The daemon maintains a registry of egress-capable actions
(`EGRESS_ACTIONS`). A test enumerates it and **fails** if any registered
action does not resolve to an *explicit* policy rule (exact or glob) rather
than the deny-default fallback. Adding a new egress-capable call site
therefore forces (a) registering its action, and (b) giving it a policy entry
— a prompt-only egress path fails the build.

### Changes Required

- **New**: `datacore-app/daemon/datacored/adapters/egress_policy.py` — policy
  loader, `classify`/`decide`, `enforce`, `release`, audit log, action
  registry, `default_enqueue` (writes to the shared approval store).
- **New shipped default**: `~/.datacore/egress-policy.yaml` (written on first
  load).
- **New audit log**: `~/.datacore/egress/audit.jsonl`.
- **Modified**: `datacored/adapters/mail.py` — gains an egress-gated `send()`
  and `release_send()` (reference integration; the mail adapter was
  previously read-only).
- **Modified**: `datacored/api/mail.py` — `POST /mail/send` route routes
  outbound mail through the gate (an autonomous send returns a queued draft,
  not a send).
- **Phase 2 (box, not this repo)**: `/usr/local/lib/hermes-agent` tool
  registry routed through the same policy (§ Phase 2).

### New Components

- `egress_policy.py` module (see APIs above).
- `EGRESS_ACTIONS` registry + `known_egress_actions()` / `has_explicit_policy()`.
- Reference integration on the mail send path.

### Interface Changes

- New owner-editable file `~/.datacore/egress-policy.yaml`.
- New daemon route `POST /mail/send` returning `{decision, sent, queued,
  approval, reason}` — under the default policy `decision="ask"`,
  `sent=false`, `queued=true`.
- No change to the existing `/cos/approvals/*` contract (reused as-is).

## Rationale

**Why an in-process per-tool gate first (layer 1), not network isolation
first?** The risk lives in the agent's tool calls. A wrapper the tool call
must pass through cannot be talked around by a prompt, and it directly
implements issue #30 with the smallest surface. OS/network egress restriction
(layer 3) is defense-in-depth for a *compromised* process and is deferred to
v2 — it hardens layer 1 rather than replacing it.

**Why reuse the existing approval substrate rather than build a new
approval/notification path?** The daemon already has a file-backed approval
queue surfaced to both the app and Telegram (DIP-0030). The owner's "BOTH"
decision is satisfied for free by enqueueing there. Building a second channel
would duplicate the surface and add drift risk (over-engineering guardrail).

**Why `browser.fetch = allow-with-log` by default (owner decision)?**
Deny-by-allowlist is safer but high-friction for legitimate research
browsing, and the primary exfiltration vectors (email, social, code exec) are
already `ask`/`deny`. Allow-with-log keeps research usable while making every
fetch auditable; owners who want stricter control add `allow_hosts`.

**Why hold the exact payload and release verbatim, rather than re-run the
action on approval?** Re-generating on approval reintroduces the injection
risk the gate exists to close (the model could produce a different, poisoned
action at release time). Approving must bind to precisely what was reviewed.

### Alternatives considered

- **Prompt-only (status quo)** — rejected; the audit's HIGH finding is
  precisely that a prompt is not a boundary.
- **Network egress proxy only** — rejected as the *first* layer; it does not
  gate per-action semantics (which email, to whom) and cannot express
  ALLOW/ASK/DENY per action. Retained as v2 defense-in-depth.
- **Fold into DIP-0023 (messaging/trust)** — rejected per owner decision;
  egress enforcement is a distinct concern with its own policy file and gate,
  though it references DIP-0023 trust tiers for ASK-eligibility.

## Backwards Compatibility

Non-breaking. The policy file is created with safe defaults on first load;
absent the file, behaviour is the shipped default (which preserves reads and
Telegram-to-owner, holds email/social, denies remote exec). The mail adapter
gains a send path where none existed (no existing caller relied on autonomous
send). The `/cos/approvals/*` contract is unchanged. Existing agents that were
"drafting only" by prompt now have that behaviour enforced rather than
requested.

## Security Considerations

- **Fail closed everywhere** — unknown action → deny; malformed policy →
  deny-default (logged error, never open); un-enqueueable ASK → propagate
  (not sent).
- **Audit is privacy-preserving** — recipients/bodies are redacted to key
  names + a short preview; the audit log is mode `0600`.
- **Exact-payload binding** — approval releases only the reviewed payload.
- **Trust tiers (DIP-0023 / ENG-2026-0718-024)** — ASK-eligibility is gated by
  initiator trust: **owner > team > trusted > unknown**. Unknown-initiated
  egress is never ASK-eligible, only DENY. v1 ships the policy gate and
  approval flow; richer per-initiator tier logic is v2.
- **Not a sandbox** — the in-process gate assumes the daemon/agent process is
  not itself compromised at the memory level. Layer 3 (network isolation)
  addresses that and is deferred to v2.
- **Cost / risk escalation** — `cost_caps` (daily external-action cap,
  escalate-after-N-denials) are parsed from the policy now and enforced in v2
  (issue #30).

## Implementation

### Reference Implementation

`datacore-app/daemon`:
- `datacored/adapters/egress_policy.py` — the gate, policy loader, audit log,
  action registry, shared-store enqueue.
- `datacored/adapters/mail.py` — `send()` / `release_send()` (reference
  integration).
- `datacored/api/mail.py` — `POST /mail/send`.
- Tests: `tests/test_egress_policy.py` (classifier, regression guard, host
  allowlist, audit, enforce semantics, mail gate, approve→release, both
  surfaces) and `tests/test_mail_crm.py` (`/mail/send` route + app-surface
  visibility).

Commit: `feat(egress): DIP + daemon-side egress policy gate + approval queue`.

### Rollout Plan

**Phase 1 (this DIP — daemon-side, shipped): layers 1 + 2.**
Per-tool gate + policy file + audit log + approval queue (both surfaces) +
the mail reference integration + the "no unpoliced egress tool" regression
guard. This is the reusable core: any daemon egress call site adopts it by
routing through `enforce`.

**Phase 2 (box / hermes side — follow-on, NOT in this repo).**
The hermes agent (Telegram Winston) has its **own** send/browse/exec tools in
the **box-installed** `/usr/local/lib/hermes-agent` package (not in
datacore-app). Fully routing Winston's autonomous egress through the boundary
requires wiring **hermes's tool registry** through this same policy: each
egress-capable hermes tool (`gmail.send`, `late.post`, `browserbase.fetch`,
`modal.run`, `telegram.send`) calls `enforce(...)` with the shared
`~/.datacore/egress-policy.yaml` and enqueues ASKs to the same
`~/.datacore/cos/approvals/` store — so the app and Telegram surfaces, and the
audit log, are identical to Phase 1. This is a box/hermes deployment task
(requires access to the box-installed package and its release process) and is
tracked separately. Until Phase 2 lands, hermes-initiated egress remains
prompt-gated; the daemon-side boundary (Phase 1) is enforced.

**Phase 3 (v2 — defense-in-depth).**
Network-level egress restriction (egress proxy with allowlist, or a network
namespace) so a compromised agent cannot reach arbitrary hosts even if the
in-process gate is subverted; enforcement of `cost_caps`; richer trust-tier
logic; cost/risk-escalation dashboards.

## Open Questions

1. **v2 network layer shape** — egress proxy vs netns vs per-tool outbound
   allowlist. Deferred to the v2 DIP/issue.
2. **Cost-cap enforcement semantics** — hard block vs escalate-to-ASK once the
   daily external-action cap is hit. Parsed now; decided in v2.
3. **Per-initiator trust tiers** — how finely to distinguish team/trusted
   initiators for ASK-eligibility beyond the owner/unknown split shipped in
   v1 (coordinate with DIP-0023).

## References

- `datacore-one/datacore#30` — per-action ALLOW/DENY/ASK guardrails (cost caps,
  external-action approval, risk escalation). This DIP implements layers 1+2.
- `2026-07-25-winston-deep-audit.md` — Security §, HIGH finding (egress is a
  prompt, not a boundary).
- `2026-07-25-winston-egress-enforcement-design.md` — design proposal this DIP
  formalizes.
- DIP-0023 — Messaging module & trust tiers (owner > team > trusted > unknown).
- DIP-0030 (chief-of-staff module) — the approval substrate reused here.
- DIP-0031 — Agent error handling.
- ENG-2026-0718-024 — trust-tier direction.
- Prior art: OpenAI/Anthropic tool-use approval patterns; capability-based
  security; principle of least authority (POLA).
