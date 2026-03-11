# DIP-0023: Messaging Module

| Field | Value |
|-------|-------|
| **DIP** | 0023 |
| **Title** | Messaging Module |
| **Author** | Gregor |
| **Type** | Module |
| **Status** | Draft |
| **Created** | 2026-03-10 |
| **Updated** | 2026-03-11 |
| **Tags** | `messaging`, `federation`, `identity`, `agents`, `inbox` |
| **Depends On** | DIP-0009 (GTD), DIP-0011 (Nightshift), DIP-0016 (Agent Registry), DIP-0022 (Module Spec) |
| **Affects** | `modules/messaging/`, `.datacore/agents/`, `.datacore/registry/`, `org/` |
| **Agents** | `message-task-intake`, `message-digest`, `message-router`, `inbox-aggregator` |

## Agent Context

### When to Reference This DIP

- When implementing messaging between Datacore users or agents
- When building inbox feeds for new modules
- When working with agent task delegation via ActivityPub
- When integrating Fairdrop/Fairdrive file delivery
- When implementing the Universal Inbox aggregation layer

### Quick Reference for Agents

- **Universal Inbox**: Query layer across all inbox feeds — not a storage location
- **Agent Inbox**: Per-agent org-mode file at `org/messaging/agents/{name}.org`
- **Message storage**: `org/messaging/inbox.org` (org-workspace managed, FileLock protected)
- **Task states**: Uses DIP-0009 GTD states + nightshift states; `WAITING` with `:AWAITING: owner-approval` for unapproved tasks
- **Org keywords**: `#+TODO: TODO WAITING QUEUED WORKING | DONE CANCELLED ARCHIVED`
- **Feed registration**: Modules declare `inbox_feeds` in `module.yaml` (proposed extension to DIP-0022)
- **Trust tiers**: owner > team > trusted > unknown (controls auto_accept, budgets, rate limits)

### Related Agents

| Agent | Relationship |
|-------|-------------|
| `message-router` | Receives AP activities, validates, routes to inbox or task pipeline |
| `message-task-intake` | Validates task messages against governance, creates entries in agent inbox |
| `message-digest` | Generates unread/thread summaries for `/today` |
| `inbox-aggregator` | Queries all registered feeds for `/inbox` and `/today` |
| `gtd-inbox-processor` | Downstream: processes refiled task-messages in `org/inbox.org` |
| `ai-task-executor` | Downstream: executes accepted tasks via nightshift pipeline |
| `strategic-prioritizer` | Downstream: scores task priority for agent inbox ordering |

### Integration Points

- **DIP-0009**: Extends GTD state machine with messaging-specific properties; refiles task-messages to `org/inbox.org`
- **DIP-0011**: Message-triggered tasks enter nightshift queue; compute budgets extend nightshift budget tracking
- **DIP-0016**: Four new agents registered in `.datacore/registry/agents.yaml`
- **DIP-0022**: Proposes `inbox_feeds` extension to `module.yaml` schema (Section 4.2)

## Summary

Federated messaging for Datacore installations with a Universal Inbox model. Users and AI agents communicate across instances via ActivityPub, authenticated with fds-id keypairs, with messages stored as org-mode entries managed by org-workspace. Introduces a Universal Inbox — a single triage interface that aggregates items from all sources (messages, agent results, file deliveries via Fairdrop/Fairdrive, email, notifications). Each Claude agent has its own dedicated inbox store, visible to the owner through the Universal Inbox view. Task governance (priority scoring, compute budgets, sender trust tiers) controls what work agents accept and execute.

## Motivation

### Problem

The existing `datacore-messaging` prototype (v0.1.0) demonstrates the concept but has fundamental issues:

1. **Centralized relay** — A single WebSocket server at `datafund.ai` sees all messages in plaintext. This contradicts Datafund's data sovereignty principles.
2. **No real identity** — Shared-secret auth means everyone uses the same key. No per-user authentication, no message signing, no encryption.
3. **Fragile org-mode handling** — Raw string manipulation with regex causes race conditions, cross-message matching errors, and silent data loss under concurrent access.
4. **No task governance** — Anyone can flood your Claude agent with unbounded work. No prioritization, no quotas, no cost tracking.
5. **Spec-code divergence** — Agent docs describe workflows that don't match the implementation (wrong file paths, nonexistent tags, broken hooks).
6. **Fragmented inboxes** — Every integration creates its own inbox with its own processing path. Nightshift outputs land in `0-inbox/`, messages in `org/inboxes/`, email in its own store. The owner must check multiple places, violating GTD's single-capture-point principle.
7. **No agent inbox** — Claude agents have no persistent, structured inbox. Tasks arrive ad-hoc via hooks. No way for the owner to see what's queued for their agent, approve/reject pending work, or monitor execution from a single view.

### Value

A well-designed messaging module enables:

- **Async AI delegation** — Team members message your Claude agent; tasks queue and execute without you being present
- **Federated teams** — Each Datacore installation runs its own relay; instances discover each other via ActivityPub without a central authority
- **Accountable compute** — Token budgets, sender trust tiers, and priority scoring prevent abuse and ensure high-value work runs first
- **Messages as GTD artifacts** — Every message is an org-mode entry that flows through the existing GTD pipeline (inbox → triage → execute → archive)
- **Universal Inbox** — One triage interface for everything: messages, agent results, file deliveries, email, notifications. Process to zero from a single view.
- **Agent inbox with governance** — Each Claude agent has a structured inbox with visibility, approval gates, and budget controls. The owner sees agent work in their Universal Inbox.

## Specification

### Architecture

```
┌──────────────────────────────────┐
│        ActivityPub Layer         │  Federation, discovery, routing
│  (WebFinger + Actor model)       │
├──────────────────────────────────┤
│        fds-id Layer              │  Per-user keypairs, message signing,
│  (sign/verify, E2E encryption)   │  E2E encryption
├──────────────────────────────────┤
│        Transport Layer           │  WSS for real-time, HTTP for
│  (WebSocket + HTTP fallback)     │  store-and-forward
├──────────────────────────────────┤
│        Universal Inbox           │  Aggregated triage view across all
│  (feed registry, /inbox cmd)     │  sources — messages, files, results
├──────────────────────────────────┤
│        org-workspace Layer       │  Concurrent-safe org-mode storage,
│  (FileLock, TaskClaim, Query)    │  GTD state machine, dependency DAG
├──────────────────────────────────┤
│        Task Governor             │  Priority scoring, token budgets,
│  (trust tiers, rate limits)      │  sender quotas, cost tracking
├──────────────────────────────────┤
│        Agent Inbox               │  Per-agent task store with lifecycle
│  (queued → working → done)       │  Owner visibility + approval gates
├──────────────────────────────────┤
│        Agent Execution           │  Claude agents as ActivityPub actors
│  (existing nightshift pipeline)  │
├──────────────────────────────────┤
│   Fairdrop/Fairdrive Feed        │  Decentralized file delivery via
│   (Swarm storage, E2E)           │  Swarm — lazy fetch, auto-ingest
└──────────────────────────────────┘
```

### 1. Identity: fds-id Integration

Replace shared-secret authentication with per-user cryptographic identity.

**Key management:**
- Each user generates a keypair via `fds-id` MCP server (`npx @fairdatasociety/fds-id-mcp`)
- Public key published in user's ActivityPub actor profile
- Private key never leaves the local machine
- Key stored in `.datacore/env/messaging.key` (gitignored)

**Message signing:**
- Every outbound message is signed with sender's private key
- Recipients verify signature against sender's published public key
- Relay cannot forge messages

**End-to-end encryption:**
- Messages encrypted with recipient's public key before transmission
- Relay sees only opaque ciphertext + routing metadata (sender, recipient, timestamp)
- Group messages use per-group symmetric key, distributed via individual encryption

**Authentication flow:**
```
1. Client connects to relay via WSS
2. Relay sends challenge (random nonce)
3. Client signs nonce with private key
4. Relay verifies signature against known public key
5. Session authenticated — no shared secrets
```

### 2. Federation: ActivityPub Protocol

Replace the centralized relay with a federated model inspired by Mastodon/ActivityPub.

**Actor model:**
- Each Datacore user is an ActivityPub actor: `@gregor@datacore.example.com`
- Each Claude agent is also an actor: `@gregor-claude@datacore.example.com`
- Actors have inbox (receive) and outbox (send) endpoints
- Discovery via WebFinger: `GET /.well-known/webfinger?resource=acct:gregor@datacore.example.com`

**Activities mapping:**

| Activity | Messaging Action |
|----------|-----------------|
| `Create(Note)` | Send message |
| `Create(Note, inReplyTo)` | Threaded reply |
| `Create(Note, tag: #task)` | AI task delegation |
| `Announce` | Broadcast to all followers |
| `Accept` | Task acknowledged |
| `Reject` | Task rejected (quota/trust) |
| `Update(Note)` | Status change (working → done) |
| `Delete` | Message retraction |
| `Follow` | Subscribe to actor's updates |

**Relay becomes ActivityPub server:**
- Each Datacore installation runs a lightweight ActivityPub server
- Server handles federation (deliver to remote inboxes, accept from remote outboxes)
- WSS used for real-time delivery between local actors on the same instance
- HTTP POST to remote inboxes for cross-instance delivery (store-and-forward)
- No central relay needed — instances federate peer-to-peer

**Offline delivery solved:**
- ActivityPub uses HTTP POST to inbox endpoints
- If recipient's server is down, sender retries with exponential backoff (standard AP behavior)
- Messages delivered when server comes back online
- No messages lost (unlike current stateless relay)

### 3. Storage: org-workspace Integration

Replace raw string manipulation with org-workspace's concurrent-safe API.

**Org-mode keyword configuration:**

All messaging org files use this header:

```org
#+TODO: TODO WAITING QUEUED WORKING | DONE CANCELLED ARCHIVED
```

This extends the DIP-0009 GTD states (`TODO`, `WAITING`, `DONE`, `CANCELLED`) with nightshift-compatible states (`QUEUED`, `WORKING`) and adds `ARCHIVED` for message lifecycle. No new states are invented — all keywords are drawn from the existing DIP-0009/DIP-0011 vocabulary.

**Message storage:**
```org
* TODO [2026-03-10 Tue 14:30] :unread:message:
:PROPERTIES:
:ID: msg-20260310-143000-a1b2c3d4
:FROM: gregor@datacore.example.com
:TO: tex@team.example.com
:THREAD: thread-msg-20260310-142500-e5f6g7h8
:REPLY_TO: msg-20260310-142500-e5f6g7h8
:SIGNATURE: ed25519:base64...
:ENCRYPTED: true
:CREATED: [2026-03-10 Tue 14:30]
:END:
Encrypted message body (base64)
```

Messages use standard `TODO` keyword with `:message:` tag to distinguish from regular tasks. Lifecycle: `TODO` (unread) → `DONE` (read/processed) → `ARCHIVED`.

**File delivery storage:**
```org
* TODO [2026-03-10 Tue 16:00] :unread:file_delivery:
:PROPERTIES:
:ID: file-20260310-160000-c4d5e6f7
:FROM: tex@team.example.com
:FILENAME: quarterly-report.pdf
:SIZE: 2400000
:CONTENT_TYPE: application/pdf
:SWARM_REF: a1b2c3d4e5f6...
:FAIRDROP_REF: encrypted-ref-hash
:DOWNLOADED: false
:CREATED: [2026-03-10 Tue 16:00]
:END:
File delivery via Fairdrop. Download to process.
```

File deliveries use `TODO` with `:file_delivery:` tag. Lifecycle: `TODO` (not downloaded) → `DONE` (downloaded/processed) → `ARCHIVED`.

**org-workspace usage:**

| Operation | org-workspace API |
|-----------|-------------------|
| Store incoming message | `ws.create_node(inbox_file, heading, state="TODO", tags=["unread", "message"], **props)` |
| Find unread messages | `ws.find_by_tag("unread")` |
| Mark as read/done | `ws.transition(node, "DONE")` |
| Thread resolution | `ws.find_by_id(reply_to_id)` |
| Concurrent file access | `FileLock(inbox_path)` with timeout |
| Task claiming | `TaskClaim(ws).claim(node, agent_id)` |
| Archive old messages | `archive_done(ws, older_than_days=30)` |

**Content-addressed message IDs:**
- Format: `msg-YYYYMMDD-HHMMSS-{sha256(from+to+content)[:8]}`
- Collision-resistant (includes content hash, not just timestamp)
- Grep-friendly, location-independent

**File layout:**
```
[space]/org/messaging/
├── inbox.org          # Incoming messages (unread, active threads)
├── outbox.org         # Sent messages (for threading context)
├── archive.org        # Archived conversations
└── contacts.yaml      # Known actors (replaces USERS.yaml)
```

**Contacts schema** (`contacts.yaml`):
```yaml
# Known ActivityPub actors
actors:
  - id: "tex@team.example.com"
    name: "Tex"
    public_key: "ed25519:base64..."
    trust_tier: team
    added: 2026-03-10
    notes: "Datafund team member"

  - id: "alice@external.org"
    name: "Alice"
    public_key: "ed25519:base64..."
    trust_tier: trusted
    added: 2026-03-10
    notes: "External collaborator"

  - id: "tex-claude@team.example.com"
    name: "Tex's Claude Agent"
    type: agent
    public_key: "ed25519:base64..."
    trust_tier: team
    capabilities: ["research", "content"]
    added: 2026-03-10
```

Separation from GTD inbox (`org/inbox.org`) is intentional — messages have their own lifecycle. Task-messages that need GTD processing are refiled to `org/inbox.org` via org-workspace's `ws.refile()`.

### 4. Universal Inbox

The Universal Inbox is a **query layer**, not a storage location. Each source stores items in its native format. The inbox aggregates across all sources into a single triage view.

#### 4.1 Inbox Feeds

Every source that produces items needing owner attention registers as an inbox feed:

| Feed | Store Location | Item Type | Source Module |
|------|---------------|-----------|---------------|
| Messages | `org/messaging/inbox.org` | Unread messages, threads | messaging |
| Agent inbox | `org/messaging/agents/{name}.org` | Tasks queued/running/completed for Claude | messaging |
| GTD captures | `org/inbox.org` | Manual captures, ideas | core (GTD) |
| Nightshift results | `[space]/0-inbox/nightshift-*.md` | AI task outputs awaiting review | nightshift |
| File deliveries | `[space]/0-inbox/fairdrop/` | Files received via Fairdrop/Fairdrive | messaging |
| Email | Module-specific store | Incoming mail | mail |
| Meeting notes | Module-specific store | Post-meeting transcripts | meetings |
| WhatsApp | Module-specific store | Imported conversations | whatsapp |

#### 4.2 Feed Registration

Modules register their inbox feeds in `module.yaml` via a proposed `inbox_feeds` field.

**Note:** This field is a proposed extension to the DIP-0022 module.yaml schema. If this DIP is accepted, DIP-0022 Section 2 must be updated to include `inbox_feeds` as an optional top-level field. Until then, implementations should treat this as module-specific configuration under the existing `settings` field.

```yaml
# Proposed inbox_feeds extension to module.yaml
inbox_feeds:
  - name: messaging
    store: org/messaging/inbox.org
    item_type: message
    query: "tags:unread"
    count_command: "python .datacore/lib/org_workspace_adapter.py count --file org/messaging/inbox.org --tags unread"
    triage_actions:
      - read       # Mark as read (transition to DONE)
      - reply      # Reply in thread
      - to_task    # Refile to org/inbox.org as GTD task
      - archive    # Transition to ARCHIVED
      - delete     # Remove node

  - name: agent-inbox
    store: org/messaging/agents/
    item_type: agent_task
    query: "state:QUEUED OR state:WORKING OR state:DONE"
    count_command: "python .datacore/lib/org_workspace_adapter.py count --file org/messaging/agents/ --states QUEUED,WORKING,DONE"
    triage_actions:
      - approve    # Accept completed result
      - revise     # Return to QUEUED with feedback
      - reject     # Cancel and notify sender
      - archive    # Transition to ARCHIVED

  - name: file-deliveries
    store: org/messaging/inbox.org
    item_type: file_delivery
    query: "tags:file_delivery AND tags:unread"
    triage_actions:
      - download   # Fetch from Swarm to 0-inbox/fairdrop/
      - reject     # Decline delivery
      - archive    # Transition to ARCHIVED
```

#### 4.3 `/inbox` Command

Single command to triage everything. Note: `/inbox` is a core command (not module-scoped) because it aggregates across all modules. It is defined in this DIP but should be registered in `.datacore/commands/` rather than `modules/messaging/commands/`.

```
/inbox              # Show all feeds with unread counts
/inbox messages     # Show only messaging feed
/inbox agents       # Show agent inbox items
/inbox files        # Show Fairdrop file deliveries
/inbox process      # Interactive triage (item by item)
```

**`/inbox` output:**

```
Universal Inbox — 14 items

  Messages (3)        2 unread, 1 pending approval
  Agent: gregor-claude (5)   2 completed, 1 running, 2 queued
  Nightshift results (2)     2 awaiting review
  File deliveries (1)        1 new file via Fairdrop
  GTD captures (3)           3 unprocessed

Process all? [y/feed/skip]
```

**Triage flow:**

```
For each item across all feeds:
  → Display item summary (source, sender, timestamp, preview)
  → Present feed-specific actions
  → User picks action → org-workspace executes
  → Item removed from inbox view
  → Next item
  → When all processed: "Inbox zero."
```

#### 4.4 Inbox Aggregator Agent

The `inbox-aggregator` agent queries all registered feeds and produces:
- Counts for `/today` briefing
- Priority-sorted item list for `/inbox`
- Stale item alerts (items sitting untriaged for >24h)

It uses org-workspace `Query` for org-mode feeds and module-specific adapters for non-org stores. Each module that registers a non-org feed must provide a `count_command` that returns a JSON count to stdout.

### 5. Agent Inbox

Each Claude agent has a dedicated inbox — a structured org-mode file that tracks all work assigned to it.

#### 5.1 Agent Inbox Store

```
org/messaging/agents/
├── gregor-claude.org      # Owner's Claude agent inbox
├── research-claude.org    # Specialized research agent (optional)
└── _agent-index.yaml      # Agent registry with capabilities
```

All agent inbox files use the same `#+TODO:` header as messaging files (see Section 3).

**Agent inbox entry format:**

```org
#+TODO: TODO WAITING QUEUED WORKING | DONE CANCELLED ARCHIVED

* QUEUED Research fair data economy competitors [#B] :AI:research:
:PROPERTIES:
:ID: task-20260310-150000-b3c4d5e6
:FROM: tex@team.example.com
:TRUST_TIER: team
:SUBMITTED: [2026-03-10 Tue 15:00]
:ESTIMATED_TOKENS: 25000
:ESTIMATED_COST: $0.38
:APPROVAL: auto_accepted
:CREATED: [2026-03-10 Tue 15:00]
:END:
Please research the main competitors in the fair data economy space.
Focus on technical approaches and funding status.

* WORKING Draft blog post about Swarm incentives [#A] :AI:content:
:PROPERTIES:
:ID: task-20260310-143000-a1b2c3d4
:FROM: gregor@datacore.example.com
:TRUST_TIER: owner
:SUBMITTED: [2026-03-10 Tue 14:30]
:STARTED: [2026-03-10 Tue 14:35]
:TOKENS_USED: 12000
:CREATED: [2026-03-10 Tue 14:30]
:END:

* DONE Summarize weekly metrics [#C] :AI:data:
:PROPERTIES:
:ID: task-20260310-090000-f7g8h9i0
:FROM: gregor@datacore.example.com
:TRUST_TIER: owner
:SUBMITTED: [2026-03-10 Tue 09:00]
:STARTED: [2026-03-10 Tue 09:05]
:COMPLETED: [2026-03-10 Tue 09:12]
:TOKENS_USED: 8500
:COST: $0.13
:QUALITY_SCORE: 0.87
:RESULT_PATH: 0-personal/0-inbox/nightshift-task-20260310-data.md
:CREATED: [2026-03-10 Tue 09:00]
:END:
```

#### 5.2 Agent Inbox State Machine

Agent inbox entries use the standard DIP-0009/DIP-0011 state vocabulary. No new states are introduced.

**State transition table:**

```
WAITING (awaiting owner approval)
  ├── → QUEUED    (owner approves)
  └── → CANCELLED (owner rejects → send AP Reject to sender)

QUEUED (accepted, waiting for execution)
  ├── → WORKING   (agent claims via TaskClaim)
  └── → CANCELLED (owner cancels before execution)

WORKING (agent executing)
  ├── → DONE      (execution complete)
  └── → QUEUED    (execution failed, retryable → back to queue)

DONE (completed)
  ├── → ARCHIVED  (owner approves result)
  └── → QUEUED    (owner requests revision)
```

**Approval flow:**
- Tasks from `owner` and `team` trust tiers: created directly as `QUEUED` (auto_accept)
- Tasks from `trusted` and `unknown` tiers: created as `WAITING` with `:AWAITING: owner-approval`
- Owner sees `WAITING` items in Universal Inbox → approve (→ `QUEUED`) or reject (→ `CANCELLED`)

#### 5.3 Agent Inbox Lifecycle

```
Message arrives with #task tag
  → message-router validates signature, checks trust tier
  → Task Governor checks: rate limit, budget, effort cap
  → If auto_accept (owner/team): create QUEUED entry in agent inbox
  → If !auto_accept (trusted/unknown): create WAITING entry with :AWAITING: owner-approval
  → Owner sees WAITING items in Universal Inbox → approve/reject
  → Approved: transition WAITING → QUEUED
  → Rejected: transition WAITING → CANCELLED, send ActivityPub Reject to sender

Agent picks up work:
  → TaskClaim(ws).claim(node, agent_id) — atomic claim with timeout
  → Transition QUEUED → WORKING, record STARTED timestamp
  → Execute via nightshift pipeline (or inline if Claude Code is active)
  → On completion: WORKING → DONE, record results, tokens, cost
  → Send ActivityPub Update to sender with result summary
  → Result file written to 0-inbox/ (appears in Universal Inbox for owner review)

Owner reviews in Universal Inbox:
  → See completed agent tasks with quality scores
  → Approve result → transition DONE → ARCHIVED
  → Request revision → transition DONE → QUEUED with feedback
```

#### 5.4 Owner Visibility

The owner always has full visibility into their agent's inbox:

- `/inbox agents` — show all agent inbox items (queued, working, done, waiting for approval)
- `/inbox agents gregor-claude` — show specific agent
- `/msg-budget` — token/cost usage per sender, per agent
- `/today` briefing — includes agent inbox summary (X completed overnight, Y queued, Z awaiting approval)

The agent inbox appears as a feed in the Universal Inbox, so the owner doesn't need to check a separate place — it surfaces alongside messages, files, and captures.

### 6. Fairdrop/Fairdrive Inbox Feed

Fairdrop and Fairdrive provide decentralized file delivery. When someone sends a file via Fairdrop, it should appear in the Universal Inbox as a file delivery.

#### 6.1 File Delivery Flow

```
Sender uploads file via Fairdrop
  → Fairdrop stores on Swarm, returns reference hash
  → Sender sends ActivityPub Create(Document) to recipient
     with swarm_reference, filename, size, content_type
  → Recipient's AP server receives activity
  → message-router validates sender identity (fds-id signature)
  → File metadata written to org/messaging/inbox.org as TODO :file_delivery: entry
  → File NOT downloaded yet (lazy fetch)

Owner triages in Universal Inbox:
  → Sees: "File delivery from tex@team — quarterly-report.pdf (2.3MB)"
  → Actions: download, preview metadata, reject, archive
  → On download: fairdrop_download(reference) → [space]/0-inbox/fairdrop/
  → Downloaded file becomes a standard ingest candidate
  → Process via knowledge-extractor or file-reader as needed
```

#### 6.2 Fairdrive as Persistent Inbox

For ongoing collaboration, Fairdrive can serve as a shared folder inbox:

```yaml
# messaging.fairdrive in settings.local.yaml
fairdrive:
  enabled: true
  inbox_pod: "datacore-inbox"        # Fairdrive pod name
  poll_interval_minutes: 15          # Check for new files
  auto_download_under_mb: 5          # Auto-fetch small files
  quarantine_above_mb: 50            # Flag large files for manual approval
```

- Fairdrive pod acts as a persistent receive buffer
- New files in the pod appear as Universal Inbox items
- Unlike Fairdrop (one-shot send), Fairdrive enables ongoing shared folders between collaborators
- Files are E2E encrypted at rest on Swarm — only the pod owner can decrypt

### 7. Task Governance

Control what work Claude agents accept and at what cost.

#### 7.1 Sender Trust Tiers

```yaml
# messaging.trust_tiers in settings.local.yaml
trust_tiers:
  owner:          # The installation owner
    priority_boost: 2.0
    daily_token_limit: 0        # unlimited
    max_task_effort: 0          # unlimited
    auto_accept: true
  team:           # Known team members
    priority_boost: 1.5
    daily_token_limit: 100000
    max_task_effort: 8          # max effort score 1-10
    auto_accept: true
  trusted:        # External contacts approved by owner
    priority_boost: 1.0
    daily_token_limit: 50000
    max_task_effort: 5
    auto_accept: false          # queue for owner approval
  unknown:        # Anyone who can reach you via federation
    priority_boost: 0.5
    daily_token_limit: 10000
    max_task_effort: 3
    auto_accept: false

# Per-actor overrides
trust_overrides:
  "tex@team.example.com": team
  "alice@external.org": trusted
```

#### 7.2 Task Priority Integration

Messages tagged as tasks (`#task` in ActivityPub, `:AI:` in org-mode) enter the existing priority pipeline:

```
Incoming task message
  → org-workspace creates node in agent inbox
  → Task Governor checks sender trust tier
  → If auto_accept=false: create as WAITING with :AWAITING: owner-approval
  → If accepted: create as QUEUED, refile copy to org/inbox.org
  → gtd-inbox-processor enriches with Rich Task Standard
  → strategic-prioritizer scores Intent Graph alignment
  → Priority = standard 5-factor score × trust_tier.priority_boost
  → Route to nightshift.org for execution
  → Execute via existing nightshift pipeline
  → Result sent back as ActivityPub Update to sender
```

#### 7.3 Compute Budgets

This module introduces its own per-sender budget tracking for message-triggered tasks. It is designed to integrate with the nightshift budget system (DIP-0011) when that system implements `budget_daily_usd` (currently listed as future work in DIP-0011). Until then, messaging budgets operate independently.

```yaml
# messaging.compute in settings.local.yaml
compute:
  daily_budget_tokens: 500000     # total daily token budget for message-triggered tasks
  per_sender_daily_max: 100000    # per sender (overridden by trust tier)
  per_task_max_tokens: 50000      # single task ceiling
  per_task_timeout_minutes: 30    # execution timeout (matches nightshift)
  cooldown_between_tasks: 60      # seconds between task executions
  max_queue_depth: 20             # reject new tasks when queue is full
```

**Budget tracking:**
- Token usage logged per-sender per-day in `.datacore/state/messaging/budget-YYYY-MM-DD.json`
- When sender exceeds limit: `Reject` activity sent back with reason and reset time
- When global budget exceeded: all new tasks created as `WAITING` state, resume next day
- Future: when DIP-0011 implements `budget_daily_usd`, message budgets should merge into the shared pool

#### 7.4 Rate Limiting

```yaml
# messaging.rate_limits in settings.local.yaml
rate_limits:
  messages_per_minute: 10         # per sender
  tasks_per_hour: 5               # per sender
  tasks_per_day: 20               # per sender (soft limit, trust tier overrides)
```

Exceeding rate limits returns `429 Too Many Requests` equivalent via ActivityPub `Reject` with `retryAfter` property.

### 8. Agent Architecture

#### 8.1 Agents

| Agent | Purpose |
|-------|---------|
| `message-router` | Receives ActivityPub activities, validates signatures, applies trust/rate checks, routes to inbox or task pipeline |
| `message-task-intake` | Validates `#task` messages against governance rules, creates entries in agent inbox, sends rejection notices |
| `message-digest` | Generates unread/thread summaries for `/today` briefing |
| `inbox-aggregator` | Queries all registered inbox feeds, produces counts and priority-sorted lists for `/inbox` and `/today` |

**Registry entries** (to be added to `.datacore/registry/agents.yaml`):

```yaml
message-router:
  module: messaging
  description: "Routes incoming ActivityPub activities to messaging inbox or agent task pipeline"
  triggers:
    - "incoming ActivityPub activity"
    - "WebSocket message received"
  skills: ["signature-validation", "trust-tier-check", "rate-limit-check"]
  spawns: ["message-task-intake"]
  spawned_by: ["activitypub-server"]

message-task-intake:
  module: messaging
  description: "Validates task messages against governance, creates agent inbox entries"
  triggers:
    - "task message received from message-router"
  skills: ["budget-check", "effort-estimation", "approval-routing"]
  spawns: []
  spawned_by: ["message-router"]

message-digest:
  module: messaging
  description: "Generates unread message and thread summaries for /today briefing"
  triggers:
    - "/today command"
    - "inbox-aggregator query"
  skills: ["thread-summarization", "priority-sorting"]
  spawns: []
  spawned_by: ["inbox-aggregator"]

inbox-aggregator:
  module: messaging
  description: "Queries all registered inbox feeds, produces unified counts and item lists"
  triggers:
    - "/inbox command"
    - "/today command"
  skills: ["feed-query", "priority-aggregation", "stale-detection"]
  spawns: ["message-digest"]
  spawned_by: []
```

#### 8.2 Claude as ActivityPub Actor

Each Claude agent instance is a full ActivityPub actor:

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    {"datacore": "https://datacore.one/ns/messaging#"}
  ],
  "type": "Service",
  "id": "https://datacore.example.com/actors/gregor-claude",
  "preferredUsername": "gregor-claude",
  "name": "Gregor's Claude Agent",
  "inbox": "https://datacore.example.com/actors/gregor-claude/inbox",
  "outbox": "https://datacore.example.com/actors/gregor-claude/outbox",
  "publicKey": {
    "id": "https://datacore.example.com/actors/gregor-claude#main-key",
    "publicKeyPem": "..."
  },
  "datacore:capabilities": ["research", "content", "data", "pm"],
  "datacore:maxEffort": 8,
  "datacore:acceptsTasksFrom": "followers"
}
```

Custom extensions use the `datacore:` namespace to avoid conflicts with the ActivityPub specification. The `datacore:capabilities` field advertises what task types the agent handles, enabling sender-side validation before submission.

#### 8.3 Commands

| Command | Scope | Description |
|---------|-------|-------------|
| `/inbox` | core | Universal Inbox — show all feeds with unread counts |
| `/inbox process` | core | Interactive triage across all feeds |
| `/inbox agents` | core | Show agent inbox items (queued, working, done, waiting) |
| `/msg @actor message` | messaging | Send message to local or remote actor |
| `/reply` | messaging | Reply in thread |
| `/msg-trust @actor tier` | messaging | Set trust tier for an actor |
| `/msg-budget` | messaging | Show compute budget usage (today, by sender) |
| `/broadcast message` | messaging | Send to all followers |

Note: `/inbox` is a core command because it aggregates across all modules. It is defined in this DIP but registered in `.datacore/commands/inbox.md`. Module-specific commands (`/msg`, `/reply`, etc.) are registered in `modules/messaging/commands/`.

### 9. Transport

**Local (same instance):**
- Direct org-workspace write for CLI/hook interactions
- FileLock ensures concurrent safety
- WSS optional for real-time notifications to external clients

**Remote (cross-instance):**
- HTTP POST to recipient's ActivityPub inbox endpoint
- HTTP Signatures (draft-cavage) for server-to-server auth
- Retry with exponential backoff for failed deliveries
- Optional WSS upgrade for persistent connections between frequently-communicating instances

**Primary interfaces:**
- **CLI**: `/inbox`, `/msg`, `/reply` commands in Claude Code (power user interface)
- **Basic GUI**: Lightweight message window for getting started (see Section 10)
- **ActivityPub clients**: Any Mastodon-compatible client (Elk, Ivory, Ice Cubes, toot)
- **Platform bridges**: Telegram bot, Slack webhook, ntfy.sh for notifications
- **`/today` briefing**: Inbox summary included automatically

### 10. Basic GUI

A minimal message window for onboarding and quick interactions. Not a Slack replacement — just enough to get started without the terminal.

**Scope:**
- Send/receive messages
- Inbox count badge (pulls from Universal Inbox aggregator)
- Message notifications (system tray)
- Online/offline presence

**Explicitly NOT in scope:**
- File sharing, previews, emoji reactions, search
- Thread visualization, channels, workspaces
- Task governance dashboard (use `/inbox agents`, `/msg-budget` in CLI)
- Mobile (use Telegram adapter or AP client instead)

**Implementation:**
- PyQt6 floating window (reuse prototype's dark theme as starting point)
- Connects to local ActivityPub server via WSS for real-time
- Signs messages client-side via fds-id
- Shows Universal Inbox badge count — clicking opens Claude Code with `/inbox`

The GUI is a **bridge to the CLI**, not a replacement. Power features live in `/inbox`, `/msg-budget`, `/msg-trust`. The GUI handles "I just want to send a quick message without opening a terminal."

### 11. Platform Adapters

The module provides adapters for existing platforms:

| Adapter | Direction | Purpose |
|---------|-----------|---------|
| Telegram bot | Bidirectional | Send/receive messages, approve tasks, check inbox from mobile |
| ntfy.sh | Outbound | Push notifications for urgent items (task completions, pending approvals) |
| Slack webhook | Outbound | Post agent results and inbox summaries to team Slack |
| ActivityPub | Bidirectional | Native federation — any AP client works |

Adapters are optional and configured in `settings.local.yaml`:

```yaml
messaging:
  adapters:
    telegram:
      enabled: true
      bot_token_env: TELEGRAM_BOT_TOKEN
      chat_id_env: TELEGRAM_CHAT_ID
      notify_on: [task_complete, pending_approval, urgent_message]
    ntfy:
      enabled: true
      topic: "datacore-inbox"
      server: "https://ntfy.sh"
      notify_on: [pending_approval, budget_exceeded]
```

### 12. Module Manifest

```yaml
# modules/messaging/module.yaml
manifest_version: 2
name: messaging
version: 0.1.0
description: >
  Federated messaging with Universal Inbox, agent task delegation,
  and Fairdrop/Fairdrive file delivery. ActivityPub federation,
  fds-id identity, org-workspace storage.
license: MIT
author: Datafund
repository: https://github.com/datafund/datacore-messaging

requires:
  datacore: ">=0.1.0"
  modules:
    - core@>=0.1.0

context:
  priority: on_match
  files:
    - CLAUDE.base.md

agents:
  - message-router
  - message-task-intake
  - message-digest
  - inbox-aggregator

commands:
  - msg
  - reply
  - msg-trust
  - msg-budget
  - broadcast

# Core command (registered in .datacore/commands/, not module commands/)
core_commands:
  - inbox

hooks:
  today:
    handler: lib/inbox_aggregator.py
    args: ["--counts-only"]
  user_prompt_submit:
    handler: hooks/inbox-watcher.py

settings:
  identity:
    name: ""                       # User display name
  messaging:
    default_space: "0-personal"
    mode: federation               # "legacy" | "federation"
    relay_url: ""                  # Legacy mode only
    trust_tiers: {}               # See Section 7.1
    trust_overrides: {}           # Per-actor tier overrides
    compute: {}                   # See Section 7.3
    rate_limits: {}               # See Section 7.4
    fairdrive: {}                 # See Section 6.2
    adapters: {}                  # See Section 11

# Proposed DIP-0022 extension (see Section 4.2)
inbox_feeds:
  - name: messaging
    store: org/messaging/inbox.org
    item_type: message
    query: "tags:unread AND tags:message"
    triage_actions: [read, reply, to_task, archive, delete]
  - name: agent-inbox
    store: org/messaging/agents/
    item_type: agent_task
    query: "state:QUEUED OR state:WORKING OR state:DONE OR state:WAITING"
    triage_actions: [approve, revise, reject, archive]
  - name: file-deliveries
    store: org/messaging/inbox.org
    item_type: file_delivery
    query: "tags:file_delivery AND tags:unread"
    triage_actions: [download, reject, archive]
```

### 13. Module Structure

```
modules/messaging/
├── module.yaml
├── CLAUDE.base.md
├── lib/
│   ├── activitypub_server.py    # Lightweight AP server (aiohttp)
│   ├── actor.py                 # Actor management (create, update, delete)
│   ├── federation.py            # Remote inbox delivery, retry, backoff
│   ├── webfinger.py             # /.well-known/webfinger handler
│   ├── signing.py               # fds-id integration (sign, verify, encrypt, decrypt)
│   ├── governor.py              # Trust tiers, budgets, rate limits
│   ├── message_store.py         # org-workspace wrapper for message CRUD
│   ├── task_bridge.py           # Message→GTD task refile and result routing
│   ├── inbox_aggregator.py      # Universal Inbox feed query engine
│   ├── fairdrop_feed.py         # Fairdrop/Fairdrive inbox feed adapter
│   ├── gui.py                   # Basic PyQt6 message window
│   └── adapters/
│       ├── telegram.py          # Telegram bot adapter
│       ├── ntfy.py              # ntfy.sh push notifications
│       └── slack.py             # Slack webhook adapter
├── agents/
│   ├── message-router.md
│   ├── message-task-intake.md
│   ├── message-digest.md
│   └── inbox-aggregator.md
├── commands/
│   ├── msg.md
│   ├── reply.md
│   ├── msg-trust.md
│   ├── msg-budget.md
│   └── broadcast.md
├── hooks/
│   ├── inbox-watcher.py         # Claude Code hook: check for pending tasks
│   └── task-complete.py         # Send result back to sender via AP
├── templates/
│   └── contacts.yaml
├── install.sh
└── tests/
    ├── test_governor.py
    ├── test_message_store.py
    ├── test_inbox_aggregator.py
    ├── test_signing.py
    ├── test_federation.py
    ├── test_fairdrop_feed.py
    ├── test_task_bridge.py
    ├── test_adapters.py
    └── test_gui.py
```

Note: `/inbox` command is registered as a core command at `.datacore/commands/inbox.md`, not in the module's `commands/` directory.

## Rationale

### Why ActivityPub over custom protocol

- **Established standard** (W3C Recommendation) with proven federation at scale (Mastodon, Lemmy, PeerTube)
- **Actor model maps naturally** to users + Claude agents
- **WebFinger solves discovery** — no manual contact management
- **Store-and-forward built in** — offline delivery works by design
- **Interoperability potential** — Datacore actors could theoretically interact with Mastodon users (future)
- Rejected: custom WebSocket protocol (no federation), Matrix (heavyweight), XMPP (declining ecosystem)

### Why fds-id over other identity solutions

- **Already exists as MCP server** — immediate integration path
- **Keypair-based** — no blockchain dependency for basic identity
- **Sign-submit pattern** — well-tested in Fairdrop MCP
- **Datafund ecosystem alignment** — same organization, compatible philosophy
- Rejected: DID:web (requires web infrastructure), PGP (poor UX), OAuth (requires central IdP)

### Why org-workspace over raw file manipulation

- **Concurrent-safe** — FileLock and OptimisticLock prevent the race conditions found in the prototype
- **Content-addressed IDs** — collision-resistant, grep-friendly
- **GTD state machine** — validated transitions, not arbitrary string replacement
- **TaskClaim** — distributed task claiming with timeout detection (exactly what agent inbox needs)
- **Already integrated** — `org_workspace_adapter.py` is live in Datacore at `.datacore/lib/org_workspace_adapter.py`
- Rejected: SQLite (loses org-mode portability), custom file locking (reinventing the wheel)

### Why Universal Inbox over per-module inboxes

- **GTD principle** — Single capture point, process to zero. Multiple inboxes fragment attention and guarantee items get missed.
- **Query, not location** — The inbox is a view that aggregates feeds, not a file that stores everything. Each module keeps its native format. No forcing emails into org-mode.
- **Feed registration** — Modules declare their inbox feed in `module.yaml`. The aggregator discovers feeds automatically. Adding a new integration doesn't require changing core code.
- **Agent inbox as first-class feed** — The owner sees their agent's pending/completed work alongside their own messages and files. No separate dashboard to check.
- Rejected: single `org/inbox.org` for everything (mixes different lifecycles), separate dashboard app (adds maintenance burden)

### Why minimal GUI, not Slack

A basic GUI lowers the barrier to entry — not everyone starts in the terminal. But it should stay minimal:

- **Bridge to CLI, not replacement** — The GUI handles quick messages and shows inbox badges. Power features (governance, budgets, triage) live in `/inbox` and `/msg-budget` commands. The GUI's job is to make the system approachable, then get out of the way.
- **Don't compete with Slack** — Emoji reactions, file previews, search, threads, channels — these are table-stakes in chat apps with thousands of engineers. Building them is a trap. The differentiated value is AI delegation, not chat.
- **ActivityPub clients cover the rest** — For users who want a richer chat experience, any Mastodon-compatible client works. Elk, Ivory, Ice Cubes, toot — free, maintained, polished.
- **Mobile is solved by adapters** — Telegram bot gives bidirectional messaging from any phone. No custom mobile app needed.
- Rejected: Electron (heavy), full-featured chat app (maintenance trap), no GUI at all (too high a barrier for onboarding)

### Why Fairdrop/Fairdrive as inbox feed

- **Decentralized file delivery** — Files arrive via Swarm, encrypted at rest, no central server sees content. Aligns with Datafund's data sovereignty principles.
- **Lazy fetch** — File metadata arrives immediately; actual download happens on owner's triage action. No storage surprise from large unsolicited files.
- **Fairdrive for ongoing collaboration** — Unlike Fairdrop (one-shot), Fairdrive pods enable persistent shared folders. Collaborators drop files in a pod; they appear in Universal Inbox.
- **Already in the ecosystem** — Fairdrop MCP server is available, fds-id handles the identity layer. The integration path is short.

### Why governance matters

Without governance, the messaging module creates an unbounded compute liability. Anyone who discovers your Claude agent's address can submit expensive research tasks. The trust tier + budget system ensures:
- Owner always has priority
- Team gets generous but bounded quotas
- External senders are throttled and require approval
- Total daily spend is capped

## Backwards Compatibility

### Migration from prototype

The prototype (`datafund/datacore-messaging` v0.1.0) stores messages in `[space]/org/inboxes/*.org`. Migration path:

1. Read existing `.org` files in `org/inboxes/`
2. Parse messages using org-workspace
3. Re-create in new `org/messaging/inbox.org` with updated properties (add `:SIGNATURE:`, `:ENCRYPTED:`, content-addressed IDs, `TODO` keyword, `:message:` tag)
4. Convert `USERS.yaml` to `contacts.yaml` with ActivityPub actor references (see Section 3 for schema)
5. Archive old `org/inboxes/` directory

A migration script (`lib/migrate_v1.py`) should be provided.

### Coexistence

During rollout, the module should support both:
- Legacy mode: direct WSS relay (no ActivityPub, no encryption) for backwards compat
- Federation mode: full ActivityPub with fds-id

Configuration flag in `settings.local.yaml`:
```yaml
messaging:
  mode: federation    # "legacy" | "federation"
```

### DIP-0022 Extension

This DIP proposes adding `inbox_feeds` as an optional top-level field in the DIP-0022 module.yaml schema. Until DIP-0022 is updated, implementations should store feed configuration under the existing `settings` field as a fallback.

## Security Considerations

### Improvements over prototype

| Concern | Prototype | This DIP |
|---------|-----------|----------|
| Authentication | Shared secret | Per-user keypair (fds-id) |
| Message confidentiality | Plaintext | E2E encrypted |
| Message integrity | None | Ed25519 signatures |
| Relay visibility | Sees everything | Sees routing metadata only |
| User enumeration | `/status` endpoint leaks usernames | Actor discovery via WebFinger (opt-in) |
| Abuse prevention | None | Trust tiers, rate limits, compute budgets |

### Remaining risks

- **Metadata leakage** — ActivityPub federation exposes who talks to whom (sender/recipient/timestamp visible to relaying servers). Mitigation: onion routing is out of scope but could be layered on later.
- **Key compromise** — If fds-id private key is stolen, attacker can impersonate user. Mitigation: key rotation support, revocation via actor profile update.
- **Spam via federation** — Open federation means unknown actors can send messages. Mitigation: `unknown` trust tier with strict rate limits and manual approval.
- **Denial of service** — Flooding with large messages. Mitigation: max message size (configurable, default 64KB), rate limiting at transport layer.

## Implementation

### Reference Implementation

Not yet implemented. The prototype at `github.com/datafund/datacore-messaging` serves as a starting point for the GUI and basic message flow.

### Rollout Plan

**Phase 1: Foundation** (org-workspace + Universal Inbox + governance)
- Replace raw file manipulation with org-workspace
- Implement Universal Inbox with feed registration and `/inbox` command
- Implement Agent Inbox store (`org/messaging/agents/`)
- Implement Task Governor (trust tiers, budgets, rate limits)
- Fix all CRITICAL and HIGH audit issues from prototype
- Keep single relay (no federation yet)
- Add tests

**Phase 2: Identity** (fds-id integration)
- Per-user keypair generation and storage
- Message signing and verification
- E2E encryption
- Challenge-response authentication (replace shared secret)

**Phase 3: Federation** (ActivityPub)
- Lightweight ActivityPub server per instance
- WebFinger discovery
- Claude agents as Service actors
- HTTP-based cross-instance delivery
- Remove dependency on central relay

**Phase 4: GUI, Adapters & Fairdrop**
- Basic PyQt6 message window (send/receive, inbox badge, notifications)
- Telegram bot adapter (bidirectional messaging + inbox triage from mobile)
- ntfy.sh push notifications for urgent items
- Slack webhook for team integration
- Fairdrop/Fairdrive inbox feed (decentralized file delivery)
- Documentation for using existing ActivityPub clients with Datacore actors

## Open Questions

1. **ActivityPub compliance level** — Full W3C compliance or minimal subset? Full compliance enables Mastodon interop but adds complexity. Minimal subset (Create, Accept, Reject, Follow + WebFinger) covers messaging needs.

2. **Key storage** — fds-id manages keys, but should the messaging module also support system keychain integration (macOS Keychain, GNOME Keyring) for defense in depth?

3. **Group messaging** — ActivityPub supports addressing multiple actors. Should group conversations use per-group symmetric keys (complex key management) or individual encryption per recipient (message size scales with group size)?

4. **Cost attribution** — When a remote user triggers a task on your Claude, who "pays"? Current design: the Claude owner bears the cost, governed by budgets. Alternative: require remote senders to provide their own API key.

5. **Universal Inbox scope** — Should the Universal Inbox be part of this DIP or a separate DIP? It affects core GTD (DIP-0009) and every module that produces items needing triage. Keeping it here ties it to messaging; splitting it makes it a first-class system concept. Current decision: keep it here since messaging motivates it, but the feed registration pattern is designed to be module-agnostic.

6. **Inbox feed for non-org stores** — Modules like email and WhatsApp don't store in org-mode. The inbox aggregator needs adapters for non-org stores. Should these adapters live in the messaging module or in each source module?

7. **Fairdrive pod sharing model** — Should Fairdrive inbox pods be per-sender (isolation) or shared (simpler)? Per-sender means a separate pod per collaborator; shared means one inbox pod that anyone can write to.

## References

- [ActivityPub W3C Recommendation](https://www.w3.org/TR/activitypub/)
- [WebFinger RFC 7033](https://tools.ietf.org/html/rfc7033)
- [HTTP Signatures (draft-cavage)](https://datatracker.ietf.org/doc/html/draft-cavage-http-signatures)
- [fds-id MCP Server](https://www.npmjs.com/package/@fairdatasociety/fds-id-mcp)
- [datacore-messaging prototype](https://github.com/datafund/datacore-messaging)
- [org-workspace](https://github.com/datacore-one/org-workspace)
- DIP-0009: GTD Specification
- DIP-0011: Nightshift Module
- DIP-0016: Agent Registry
- DIP-0022: Module Specification
