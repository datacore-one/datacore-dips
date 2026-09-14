# DIP-0011: Autonomous AI Task Execution with Quality Gates

| Field | Value |
|-------|-------|
| **DIP** | 0011 |
| **Title** | Autonomous AI Task Execution with Quality Gates |
| **Author** | User, Claude |
| **Type** | Module |
| **Status** | Implemented |
| **Created** | 2025-12-10 |
| **Updated** | 2026-09-12 |
| **Module** | nightshift |
| **Depends On** | DIP-0002, DIP-0009, DIP-0010, Datacortex module |

## Summary

Nightshift is an autonomous task execution module that processes `:AI:` tagged tasks with quality gates, multi-persona evaluation, context enhancement, and comprehensive analytics. It runs locally or on a server, with identical user experience.

**Tagline**: *"Tag tasks before bed. Wake up to completed work."*

## Motivation

### Current State

- `:AI:` tagged tasks exist in `next_actions.org`
- `ai-task-executor` can process them
- No scheduled/autonomous execution
- No quality validation before delivery
- No analytics on execution patterns
- No learning feedback loop

### Problems

1. User wakes up to unreviewed outputs of variable quality
2. No way to prioritize or sequence tasks intelligently
3. No visibility into what works and what doesn't
4. Agents don't leverage full knowledge base context
5. No continuous improvement through pattern extraction

## Specification

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     /tomorrow (evening)                         │
│  - Scan for :AI: tasks in next_actions.org, research_learning  │
│  - Move :AI: tasks to nightshift.org with QUEUED state          │
│  - Show execution preview                                       │
│  - Commit/push to make available to server                      │
│  - Trigger server (optional)                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               NIGHTSHIFT ORCHESTRATOR                           │
│               (Local or Server)                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. QUEUE OPTIMIZER                                       │   │
│  │    - Parse QUEUED tasks from nightshift.org              │   │
│  │    - Analyze dependencies                                │   │
│  │    - Score by impact/effort/urgency                      │   │
│  │    - Build execution plan                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 2. CONTEXT ENHANCER (per task)                           │   │
│  │    - datacortex RAG search                               │   │
│  │    - Index page discovery                                │   │
│  │    - Wiki-link traversal                                 │   │
│  │    - Learning files (patterns, corrections)              │   │
│  │    - Recent journal context                              │   │
│  │    - Quality scoring                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 3. EXECUTION ENGINE                                      │   │
│  │    - Receives task + context_package                     │   │
│  │    - Specialized agent executes                          │   │
│  │    - Self-reflection loop                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 4. EVALUATION PANEL                                      │   │
│  │    Core: User, Critic, CEO, CTO, COO, Archivist          │   │
│  │    Domain: (selected by task type)                       │   │
│  │    Consensus engine aggregates scores                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 5. LEARNING EXTRACTOR                                    │   │
│  │    - Extract patterns from success                       │   │
│  │    - Log corrections from failures                       │   │
│  │    - Update analytics                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     /today (morning)                            │
│  - Show completed work with quality scores                      │
│  - Surface items needing human review                           │
│  - Display insights and recommendations                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Queue Optimizer Agent

**Purpose**: Analyze pending tasks and create optimal execution plan.

**Inputs**:
- QUEUED tasks from `nightshift.org` (primary source)
- Task metadata (priority, tags, dependencies)
- Historical execution data

**Note**: Tasks are moved from `next_actions.org` and `research_learning.org` to `nightshift.org` by the `/tomorrow` command before queue optimization runs.

**Logic**:

> **Note:** Priority scoring follows the canonical formula in DIP-0009 Part 13 (includes Intent Graph alignment). The composite below is a simplified queue-ordering heuristic for nightshift execution order.

```
For each task:
  1. Parse task content and metadata
  2. Identify dependencies (explicit or inferred)
  3. Calculate scores:
     - Impact: How valuable is this? (1-10)
     - Effort: How complex? (1-10, inverse)
     - Urgency: Time-sensitive? (1-10)
     - Readiness: Are dependencies met? (0 or 1)
  4. Composite = (Impact × 0.4) + (Effort × 0.2) + (Urgency × 0.3) + (Readiness × 0.1)

Sort by composite score, respecting dependency order.
```

**Outputs**:
- Ordered execution queue
- Dependency graph
- Estimated completion times

---

### 2. Context Enhancer Agent

**Purpose**: Build comprehensive context package before task execution.

**Search Strategy** (multi-modal, per Datacortex module and patterns.md):

| Method | Tool | Best For |
|--------|------|----------|
| RAG Search | `datacortex search` | Semantic similarity |
| Index Pages | Read `_index.md` files | Structure, entry points |
| Grep/Glob | Pattern matching | Specific terms, files |
| Wiki-link Traversal | Follow `[[links]]` | Connected concepts |
| Learning Files | `patterns.md`, `corrections.md` | Past approaches |
| Recent Journal | Last 7 days | Current context |

**Context Package Structure**:
```yaml
context_package:
  task_id: "exec-2025-12-10-001"
  task: "Research competitor X pricing strategies"
  task_type: ":AI:research:"

  semantic_matches:
    - source: "3-knowledge/zettel/competitive-analysis.md"
      relevance: 0.92
      excerpt: "When analyzing competitors..."

  relevant_indexes:
    - "1-tracks/research/_index.md"

  connected_concepts:
    - "[[Pricing Models]]"
    - "[[Data Marketplace Competitors]]"

  applicable_patterns:
    - id: "research-citation-format"
      content: "Always cite sources with URLs and dates"

  relevant_corrections:
    - "Research tasks should include pricing comparison table"

  recent_context:
    - "2025-12-09: Discussed Project Alpha pricing, leaning toward usage-based"

  context_quality: 0.85
  gaps_identified:
    - "No recent data on Competitor Y (last update 3 months ago)"
```

**Quality Threshold**: If `context_quality < 0.6`, flag for expanded search or human input.

---

### 3. Execution Engine

**Purpose**: Execute tasks with quality-focused workflow.

**Per-task workflow**:
```
1. PREPARE
   - Load task context
   - Load context_package from Context Enhancer
   - Select appropriate specialized agent

2. EXECUTE
   - Run specialized agent with full context
   - Capture output and metadata

3. REFLECT (self-critique)
   - Agent reviews own output
   - Identifies potential issues
   - If significant issues → retry with self-feedback (max 2 retries)

4. RECORD
   - Log execution data to analytics
   - Store output for evaluation
```

**Specialized Agents** (per DIP-0009):

| Tag | Agent |
|-----|-------|
| `:AI:` | ai-task-executor (routes) |
| `:AI:research:` | research-orchestrator |
| `:AI:content:` | gtd-content-writer |
| `:AI:data:` | gtd-data-analyzer |
| `:AI:pm:` | gtd-project-manager |

---

### 4. Evaluation Panel

**Purpose**: Multi-perspective quality assessment.

#### Core Evaluators (always run)

| Persona | Focus | Questions |
|---------|-------|-----------|
| **The User** | Practical utility | Does it solve my problem? Would I use this? |
| **The Critic** | Devil's advocate | What's wrong? What's missing? What could fail? |
| **CEO** | Strategic value | Does this move the needle? Worth the time spent? |
| **CTO** | Technical quality | Is this correct? Scalable? Best practices? |
| **COO** | Operational fit | Is this feasible? Does it fit our processes? |
| **The Archivist** | Knowledge usage | Was the KB used well? Patterns applied? |

#### Domain Evaluators (selected by task type)

**Writing & Communication**:

| Persona | Focus | Invoked For |
|---------|-------|-------------|
| Mark Twain | Clarity, cut the fluff | All writing |
| Hemingway | Brevity, strong verbs | Short-form |
| Orwell | Plain language, no jargon | Public-facing |

**Business & Strategy**:

| Persona | Focus | Invoked For |
|---------|-------|-------------|
| Bezos | Customer obsession, data | Product strategy |
| Musk | First principles, 10x | Technical innovation |
| Buffett | Long-term value, moats | Investment, strategy |

**Philosophy & Ethics**:

| Persona | Focus | Invoked For |
|---------|-------|-------------|
| Socrates | Question assumptions | Decisions |
| Marcus Aurelius | Virtue, what's in control | Leadership |
| Feynman | Explain simply | Technical docs |

**Technical**:

| Persona | Focus | Invoked For |
|---------|-------|-------------|
| Dijkstra | Correctness, elegance | Code |
| Tufte | Data clarity | Reports, dashboards |

**Research**:

| Persona | Focus | Invoked For |
|---------|-------|-------------|
| Popper | Falsifiability | Research |
| Kahneman | Cognitive biases | Decisions |
| Taleb | Black swans, fragility | Risk analysis |

#### Persona Selection Matrix

```yaml
task_type_evaluators:
  ":AI:content:":
    required: [user, critic, ceo, cto, coo, archivist]
    domain: [twain, hemingway]

  ":AI:research:":
    required: [user, critic, ceo, cto, coo, archivist]
    domain: [popper, kahneman]

  ":AI:data:":
    required: [user, critic, ceo, cto, coo, archivist]
    domain: [tufte, feynman]

  ":AI:pm:":
    required: [user, critic, ceo, cto, coo, archivist]
    domain: [grove, bezos]
```

#### Consensus Engine

```
For each evaluator:
  1. Review output with persona-specific lens
  2. Score 0.0-1.0
  3. Provide brief feedback (1-2 sentences)

Aggregate:
  1. Calculate weighted average (weights by task type)
  2. Check variance (disagreement indicator)
  3. Decision:
     - Score >= 0.80, variance < 0.15 → Approved
     - Score >= 0.70, variance < 0.20 → Approved with notes
     - Score < 0.70 OR variance >= 0.20 → Needs revision or human review
```

#### Revision Loop

```
If needs_revision:
  1. Aggregate feedback from evaluators
  2. Re-run execution with feedback as context
  3. Re-evaluate (max 2 revision cycles)
  4. If still failing → escalate to human review
```

---

### 5. Learning Extractor

**Purpose**: Continuous improvement through pattern extraction.

**After each execution**:
```
1. If approved with high score (>0.85):
   - Extract successful patterns
   - Add to patterns.md if novel

2. If revised or failed:
   - Log correction to corrections.md
   - Tag with task type and evaluator feedback

3. Update analytics:
   - Execution stats
   - Tag performance
   - Evaluator calibration
```

---

## Org-mode Integration

### Task States (extends DIP-0009)

> **Note:** Task states follow the canonical state machine defined in DIP-0009 Part 2. Nightshift extends the base GTD states with execution-specific states.

| State | Meaning | Set By |
|-------|---------|--------|
| `TODO` | Captured, not queued | Human |
| `NEXT` | Queued for nightshift | Human/System |
| `QUEUED` | In nightshift queue (alias: `NEXT` with `:NIGHTSHIFT_QUEUED:`) | System |
| `WORKING` | Currently executing | Nightshift |
| `DONE` | Completed and approved | Nightshift |
| `REVIEW` | Needs human review (nightshift extension) | Nightshift |
| `FAILED` | Execution failed | Nightshift |

> **Implementation note (updated 2026-07-25, DIP-0009 v1.1):** `WORKING` is the
> canonical in-progress keyword; `EXECUTING` is **retired** — parsers may still
> read it for legacy files, but no writer may emit it. Execution states are
> valid in ANY task file (the nightshift.org-only scoping is retired) and every
> state write goes through the shared chokepoint writer that strips stacked
> keywords — see DIP-0009 Part 2 "Writer and Coverage Requirements".

### Task Properties

```org
* TODO Research competitor X :AI:research:
  :PROPERTIES:
  :CREATED: [2025-12-10 Wed]
  :SPACE: 1-teamspace
  :PRIORITY: A
  :END:

# After queuing:
* NEXT Research competitor X :AI:research:
  :PROPERTIES:
  :NIGHTSHIFT_QUEUED: [2025-12-10 Wed 23:00]
  :NIGHTSHIFT_ID: exec-2025-12-10-001
  :END:

# During execution:
* WORKING Research competitor X :AI:research:
  :PROPERTIES:
  :NIGHTSHIFT_STARTED: [2025-12-10 Wed 02:15]
  :NIGHTSHIFT_EXECUTOR: server:personal
  :END:

# After completion:
* DONE Research competitor X :AI:research:
  :PROPERTIES:
  :NIGHTSHIFT_COMPLETED: [2025-12-10 Wed 02:27]
  :NIGHTSHIFT_SCORE: 0.85
  :NIGHTSHIFT_OUTPUT: [space]/0-inbox/nightshift-001-research.md
  :END:
```

---

## Output Routing

### Output Placement

Outputs always go to `0-inbox/` of the relevant space:

```
Task with :SPACE: teamspace
  → Output: 1-teamspace/0-inbox/nightshift-{id}-{type}.md

Task in 0-personal/org/next_actions.org
  → Output: 0-personal/0-inbox/nightshift-{id}-{type}.md
```

### Output File Format

```markdown
---
nightshift_id: exec-2025-12-10-001
task: "Research competitor X"
task_type: ":AI:research:"
executed_at: 2025-12-10T02:27:00Z
score: 0.85
status: approved
evaluators:
  user: 0.88
  critic: 0.80
  ceo: 0.85
  cto: 0.92
  coo: 0.81
  archivist: 0.83
requires_action: acknowledge
---

# Research: Competitor X Analysis

[Actual output content here]

---

## Nightshift Metadata

**Execution**: 12 min, 45k tokens, $0.12
**Patterns applied**: research-citation-format, executive-summary-first

### Evaluator Feedback

> **CEO**: Good strategic relevance. Actionable insights.
> **Critic**: Could use more recent data.
> **Twain**: Clear enough. Methodology section is dry.
```

### Processing Outputs

| Status | Action | Result |
|--------|--------|--------|
| `approved`, `requires_action: none` | Auto-archive | Logged to journal |
| `approved`, `requires_action: acknowledge` | Surface in `/today` | User clicks acknowledge |
| `needs_review` | Create review task | User provides feedback |

---

## Journal Integration

### Preservation and concurrent writers — amendment under review

**Amendment status: Proposed (2026-09-12).** The examples below describe
execution reports, not permission to replace unrelated journal content. This
clarification makes their preservation requirements explicit. It does not
certify an installed writer or convert local locking into cross-host safety.

1. Appending an execution report MUST retain prior authored content. A report
   is stored completely or the writer reports failure. Metadata, code examples,
   quotations and unrelated sections MUST NOT be reinterpreted as the target
   section merely because they contain its name.
2. A generated daily briefing may replace its own exact section. Capture that
   section before generation; if another writer changes it before publication,
   refuse the stale replacement. Concurrent changes to unrelated sections must
   be preserved. Ambiguous duplicate target sections require reconciliation,
   not deletion by heuristic. The briefing producer owns this generated
   section; authored session notes belong in separate sections.
3. Section extraction for delivery MUST stop at the next actual top-level
   section. It must not send later journal notes as part of a briefing. The
   implementation uses CommonMark heading boundaries and leading YAML
   frontmatter; literal headings inside code, quotations and HTML are content.
4. All writers of the same installed source MUST share a transaction and
   recovery protocol, or an equivalent independently enforced writer boundary.
   Core wrap-up, write-back, Nightshift summaries and daily briefings cannot use
   independent locks and claim mutual exclusion. Current local transactions
   require one shared `DATACORE_STATE`; this is a deployment prerequisite, not
   a distributed lock. Other hosts and direct file editors need an enforced
   ownership/synchronization arrangement before concurrent safety is claimed.
5. Publication MUST preserve complete previous data across interrupted writes
   and participate in recovery before another mutation. An unacknowledged
   transaction can be rolled back; recovery MUST refuse to overwrite a third
   version written outside that transaction. Failed durability checks must be
   surfaced. Local durable publication is distinct from a verified Git push.

### Journal amendment change record

| Field | Record |
|-------|--------|
| Previous requirement | Execution reports are appended to space/personal journals; replacement, syntax boundaries and writer coordination were implicit. |
| Problem | Whole-file writes lost updates; substring/fence heuristics dropped summaries, damaged metadata/examples and selected later notes for briefing delivery. Separate locks did not coordinate core and module writers. |
| Corrected requirement | Preserve source outside the owned section, reject stale/ambiguous replacements, parse actual Markdown boundaries, and share recoverable writer coordination. |
| Reason | Journals contain authored source data, not disposable generated output. |
| Implementation impact | Core `markdown_sections.py` and `journal_store.py`; Nightshift summary/briefing writers use the existing core transaction protocol. Fully derived doing-journal output uses atomic replacement. |
| Compatibility impact | Existing files are retained. Duplicate sections, malformed metadata, unclosed generated blocks and stale replacements now require correction/retry instead of heuristic rewriting. Core and Nightshift must be upgraded together. |
| Tests affected | Literal headings, exact source preservation, section extraction, stale-generation preconditions, independent-process coordination, interrupted publication and crash/restart recovery. |
| Runtime/deployment impact | Reconcile writer identities, shared transaction state and all direct write paths; qualify actual filesystem durability and recovery. Noncooperating/cross-host writers remain an open enforcement requirement. |
| Status | Proposed clarification with candidate code; no deployed-conformance or global-concurrency claim. |

### Space Journal Entry

`1-teamspace/journal/2025-12-11.md`:

```markdown
## Nightshift Report

**Window**: 2025-12-10 23:00 - 2025-12-11 05:30
**Tasks**: 5 queued, 4 completed, 1 needs review

### Completed

| Task | Score | Output |
|------|-------|--------|
| Research competitor X | 0.85 | [[nightshift-001-research.md]] |
| Q4 metrics analysis | 0.92 | [[nightshift-002-data.md]] |

### Needs Review

| Task | Score | Reason |
|------|-------|--------|
| Blog post draft | 0.68 | Evaluator disagreement on tone |

### Resource Usage

- Tokens: 180,000
- Cost: $0.48
- Duration: 2h 15m
```

### Personal Journal Entry

`0-personal/journal/2025-12-11.md`:

```markdown
## Nightshift Summary

Overnight processed 5 tasks:
- 0-personal: 1 task
- 1-teamspace: 4 tasks

**Action needed**: 1 item requires review

See space journals for details.
```

---

## Analytics Schema

**Location**: `.datacore/state/nightshift/`

### Execution Record

```yaml
executions:
  - id: "exec-2025-12-10-001"
    task_id: "abc123"
    task_type: ":AI:research:"
    space: "1-teamspace"

    timing:
      queued_at: "2025-12-10T23:00:00Z"
      started_at: "2025-12-10T02:15:00Z"
      completed_at: "2025-12-10T02:27:00Z"
      duration_seconds: 720

    resources:
      tokens_used: 45000
      cost_usd: 0.12
      agent: "research-orchestrator"
      executor: "server:personal"

    evaluations:
      - evaluator: "ceo"
        score: 0.85
        feedback: "Good strategic relevance"
      - evaluator: "critic"
        score: 0.80
        feedback: "Missing competitor comparison"

    consensus:
      raw_score: 0.84
      weighted_score: 0.84
      variance: 0.05
      status: "approved"

    context:
      quality_score: 0.85
      sources_used: 5
      patterns_applied: ["research-citation-format"]

    learnings_extracted:
      - type: "correction"
        content: "Include competitor comparison for market research"
```

### Aggregate Stats

```yaml
daily_stats:
  "2025-12-10":
    tasks_queued: 8
    tasks_completed: 6
    tasks_failed: 1
    tasks_human_review: 1
    avg_quality_score: 0.82
    total_tokens: 380000
    total_cost_usd: 0.95

tag_performance:
  ":AI:research:":
    total_executions: 45
    avg_score: 0.89
    success_rate: 0.93
    common_feedback: ["needs citations", "good depth"]

evaluator_calibration:
  critic:
    avg_score: 0.72
    correlation_with_human: 0.91
```

---

## Server Architecture

### Server is NOT an External Service

Unlike DIP-0010 external services (GitHub, Calendar), the Nightshift server:
- Uses **Datacore's data model** (org-mode)
- Is **not** a source of truth (org-mode is)
- Has **no UI** humans interact with
- Is just a **remote execution environment**

```
Datacore (local OR server) = Same brain, same methodology
External Services (GitHub, Calendar) = Different systems, need sync
```

### Space Isolation

| Server Type | Can Execute | Cannot Execute |
|-------------|-------------|----------------|
| Personal server | All spaces | - |
| Team server (teamspace) | Only 1-teamspace | 0-personal, others |

### Configuration

```yaml
# .datacore/settings.yaml (defaults)
nightshift:
  enabled: true
  execution_preference:
    - server
    - local

# .datacore/settings.local.yaml (personal)
nightshift:
  servers:
    personal:
      url: "nightshift.example.com"
      ssh_key: "~/.ssh/nightshift_personal"
      spaces: ["*"]
      is_default: true

# 1-teamspace/.datacore/settings.local.yaml
nightshift:
  servers:
    teamspace:
      url: "nightshift.team.example.com"
      spaces: ["1-teamspace"]
      is_default: true
```

### Task Routing

Users can override per-task:

```org
* TODO Generate report :AI:data:
  :PROPERTIES:
  :NIGHTSHIFT_TARGET: local
  :END:

* TODO Research competitor :AI:research:
  :PROPERTIES:
  :NIGHTSHIFT_TARGET: server:personal
  :END:
```

---

## Approved Allocation and Execution Receipts — amendment under review

This section specifies the allocation lifecycle added after the historical implementation inventory below. It preserves DIP-0034's owner-only completion rule and distinguishes approval from execution ownership. It does not certify deployed conformance or replace the cross-host coordination requirement.

1. An approved allocation binds its complete payload: budget, slot total, per-space slots and task IDs, exclusions, build time and night. Protocol 2 uses a SHA-256 content identity and a matching approval claim hash. Changed content requires a new approval; an old ID cannot authorize changed work.
2. Approval authority comes from an explicit, valid arbitration policy. Missing or malformed policy MUST NOT supply default approvers. N1 actor identity remains cooperative; a ledger claim alone is not an independent credential or OS boundary (DIP-0038).
3. The newest authorized allocation is selected by timestamp instant, with deterministic ledger order for ties. A consumed, expired, changed or invalid newest allocation MUST NOT cause fallback to an older plan. When allocation is configured, absence MUST NOT authorize an unrestricted queue. The initial protocol-2 proposal allowed an explicit unallocated mode on new installations. The later mandatory-admission amendment below supersedes that exception; this sentence preserves its change history, not a current execution allowance.
4. A task ID is bound to its approved space. Duplicate queue identities, relocation to another space and slot/budget overflow MUST refuse admission. Budget evidence is structured spend; unreadable evidence MUST NOT expand the available budget.
5. Before executing a task from an allocation, create and claim a deterministic **run receipt** as the actual executor. The original allocation remains owned by the approver. Any receipt consumes the allocation, including a partially written or interrupted receipt; a retry MUST NOT start another run silently.
6. Completion addresses the executor's receipt, never the approver's allocation. Acknowledgement requires readback of the accepted owner-only transition. Repeating the exact acknowledgement is idempotent; changing the outcome or receipt identity is not. Interruption requires effect reconciliation before a new allocation is approved.
7. Receipt ownership has no automatic expiry or transfer. A local admission lock only serializes writers sharing that local ledger. Cross-host execution and external effects still require the coordination/fencing or duplicate-safe effect model demanded by the deployment. Neither the local lock nor eventual ledger replay establishes exclusive execution across hosts.

### Allocation amendment change record

| Field | Record |
|---|---|
| Previous requirement | The DIP had no allocation approval/consumption protocol. The implementation claimed allocations as the approver, then attempted completion as an executor; missing/error states fell back to the ordinary queue. |
| Problem | Owner-only replay rejected completion while the caller reported success. Plans could be reused, changed content could share an ID, and policy failures expanded admissible work. |
| Corrected requirement | Immutable explicit approval, separately owned one-use execution receipt, strict space/budget validation, verified acknowledgement and fail-closed configured admission. |
| Reason | Preserve ownership integrity, approved intent, data and visible failure semantics without impersonating another actor or weakening the core fold. |
| Implementation impact | `night_manifest.py` allocation protocol 2; `run.py` validates before queue mutation and consumes before execution. Producer uses explicit approver policy. |
| Compatibility impact | Existing ledger records are retained. Legacy allocations must be republished after producer/executor upgrade; there is no destructive migration or implicit old-plan fallback. |
| Tests affected | Payload identity, malformed policy, owner substitution, interrupted admission, concurrent local admission, exact acknowledgement retry, stale plans, task-space substitution and budget failure. |
| Runtime/deployment impact | Upgrade producer and executor together; configure allocation requirement and qualify restart/recovery. Establish cross-host coordination separately before relying on exclusivity. |
| Status | Candidate implementation and local adversarial tests exist; deployed reconciliation and independent re-audit remain pending. |

### Allocation space identity — proposed clarification

**Amendment status: Proposed (2026-09-12).** Following DIP-0015 Part 0,
allocation storage resolves the logical `datacore` space through the canonical
discovery API. A local ordinal or directory label cannot override an explicit
marker. The space may be at the installation root, renamed, or nested within
the supported discovery bound. Unmarked legacy spaces remain discoverable
during the migration specified by DIP-0015.

Admission requires a unique allocation-space identity. Malformed markers,
missing or blank explicit names, leading or trailing name whitespace, space
aliases without an independently discovered canonical target, and incomplete
directory traversal must stop automated admission.
They cannot be interpreted as an optional installation without an allocation
ledger. A redundant compatibility link to an independently discovered space
inside the root does not add an identity or another allocation store. Discovery
returns the canonical path once, preserves the link and never traverses it to
extend the walk bound or reach a skipped directory. Read-only diagnostic discovery may continue to report valid neighbors
and older incomplete markers; its partial result is not admission authority.
Configured allocation deployments must still require their allocation ledger:
canonical discovery alone cannot distinguish a deliberately removed valid
identity from a new installation.

| Field | Record |
|---|---|
| Previous requirement | DIP-0015 defines stable marker identity and local ordinals, but the allocation amendment did not specify lookup or incomplete-discovery failure semantics. |
| Problem | A fixed directory label could select the wrong ledger or treat a renamed allocation as absent. Invalid or unreadable identity evidence could expand admission. |
| Corrected requirement | Resolve the unique logical space canonically and refuse incomplete identity evidence before admission or ledger mutation. |
| Reason | An installation's sort order and discovery failures cannot change approved execution authority. |
| Implementation impact | Canonical named-space lookup, strict discovery for Nightshift admission and automated projection/review discovery. |
| Compatibility impact | No ledger migration or deletion; unmarked legacy discovery and read-only diagnostic behavior remain supported. Incomplete explicit markers require repair before automation proceeds. |
| Tests affected | Renamed, nested and root spaces; explicit identity overriding an old label; duplicate, malformed, incomplete and aliased identities; directory-read interruption; unchanged ledger bytes after refusal. |
| Runtime/deployment impact | Verify marker identities and complete traversal using the actual executor identity. This change does not establish cross-host ownership or independent OS isolation. |

### Canonical alias compatibility — proposed correction

**Amendment status: Proposed (2026-09-12).** This corrects the blanket alias
refusal in the preceding discovery amendment, preserving its boundary invariant.

| Field | Record |
|---|---|
| Previous requirement | The earlier audit amendment refused every space alias during automated discovery. |
| Problem | A legacy link to the same independently discovered canonical space stopped automation despite adding neither data nor authority. Removing the link could break existing references unnecessarily. |
| Corrected requirement | Ignore redundant links to already validated canonical spaces inside discovery bounds; return each canonical path once. Refuse aliases whose work would otherwise be missed or whose target crosses the root, skipped-directory or depth boundary. Never traverse an alias to discover new spaces. |
| Reason | Preserve DIP-0015 stable identity and nonbreaking discovery without allowing an alias to supply authority or hide work. |
| Implementation impact | Complete canonical discovery before classifying collected aliases; all automated users share that result. |
| Compatibility impact | Retain legacy compatibility links and all underlying data; unsupported aliases still require repair. |
| Tests affected | Redundant links, canonical identity/count and containing-space resolution; external, skipped-directory and beyond-depth targets; allocation and projection behavior. |
| Runtime/deployment impact | Verify affected installed layouts and consumer access without deleting aliases or moving valid space data. |

### Designated execution installation — proposed protocol 3

**Amendment status: Proposed (2026-09-12), not ratified or deployed.** This
proposal extends the preceding protocol-2 amendment. Its execution boundary
is separate from DIP-0034's offline event ledger: replay continues to reconcile
attribution, while an approved allocation names exactly one execution
installation. It does not introduce a live coordinator into the ledger.

1. The complete approval payload includes a canonical installation UUID.
   Changing that target changes the allocation identity and requires a new
   approval. An actor name, hostname, environment variable or copied Data
   configuration cannot provision the named installation.
2. An administrator provisions a fresh installation identity, binds it to the
   host and controller OS identity, and keeps its admission database outside
   synced Data. The configuration is administrator controlled. Only the trusted
   controller can write admission state; untrusted workers cannot read or modify
   it or obtain administration credentials. Application checks do not supply
   this required OS boundary.
3. Before queue GC, sprint synchronization, speculative queue advancement or
   task invocation, the designated controller durably consumes the approval
   in its local admission database. Concurrent
   controllers and separate Data checkouts on that installation share this
   state. A copied checkout on another installation must refuse the approval.
4. Missing, corrupt, mismatched or inaccessible admission state is a refusal,
   never an empty new database. Neither installation nor runtime automatically
   overwrites or resets existing state. Restoring Data cannot restore permission
   to execute an already consumed allocation.
5. A crash after durable consumption but before a ledger receipt still consumes
   the approval. Completion requires both that consumption record and the exact
   executor-owned ledger receipt. Retrying the same acknowledgement may succeed;
   retrying execution may not. A crash before consumption commits returns no
   execution grant, allowing a later controller to attempt admission safely.
6. There is no lease expiry, automatic transfer, release or takeover. Recovery
   requires the operator to stop/quiesce the old execution context, reconcile
   pending and completed effects, and issue a fresh approval. Lost host state
   requires a fresh installation identity; cloning/restoring the same identity
   onto two active hosts is not a supported recovery procedure. External effects
   that may still be in flight require effect-specific reconciliation before
   reapproval; ledger convergence cannot fence them retroactively.
7. Every task-mode run requires an allocation, including first installations,
   direct Python entry and single-task test mode. `require_manifest` defaults
   to true; false and malformed values are refused. There is no unallocated
   execution fallback. Every task/executor entry point in a protected deployment
   must enter through its designated controller; verification must challenge
   alternate launch and stale-receipt paths.

| Field | Record |
|---|---|
| Previous requirement | Protocol 2 serialized consumption only in each local ledger and explicitly left cross-host effect safety unresolved. |
| Problem | Two disconnected Data copies could each consume one approval, execute an effect and acknowledge completion before event replay rejected one receipt. |
| Corrected requirement | Approval-bound designated installation plus durable controller-owned consumption outside Data, with no automatic ownership transfer. |
| Reason | Establish a verifiable conservative execution model while preserving offline event-ledger semantics and existing data. |
| Implementation impact | Protocol 3 target binding; canonical core `execution_admission.py` administrator provisioning, host/controller verification and existing-only transactional consumption (`execution_site.py` is the module compatibility entrypoint); allocation begin/completion checks. |
| Compatibility impact | Retain all old events and data. Upgrade producer/controller together and explicitly republish protocol-2 approvals. Unprovisioned hosts refuse protocol-3 execution. No automatic old-identity reuse after state loss. |
| Tests affected | Disconnected hosts, identical actor names, multiple local checkouts/processes, target tampering, copied receipts, database loss/corruption, interruption before and after durable consumption, independent OS access and real controller configuration. |
| Runtime/deployment impact | Provision a unique designated installation, protect its configuration/state, separate workers from controller credentials, require allocations and qualify all entry points. Stale active work must be reconciled before cutover. |
| Current evidence | Candidate code and initial local adversarial tests; OS/deployment reconciliation and complete independent re-audit remain pending. |

### Mandatory admission before preparation — proposed clarification

**Amendment status: Proposed (2026-09-12), not ratified or deployed.** This
supersedes the historical unallocated exception and the weaker timing that
consumed only before task invocation. Syncing existing repositories and
rebuilding verified derived projections precede admission so the controller
can read current approvals. GC, sprint application and queue advancement can
change authoritative task state and therefore follow durable consumption.

An admitted run that finds no tasks, or no eligible tasks, records an empty
completion receipt. A crash during preparation keeps the approval consumed.
An unacknowledged empty completion is an error; it must not look like a clean
run or reset admission. Missing or invalid loader results never authorize
preparation. The later queue filter applies the same admitted allocation,
without attempting to load it again as an unused approval.

| Field | Record |
|---|---|
| Previous requirement | The initial amendment permitted unallocated first-installation runs; configured runs checked approval before GC but consumed only after queue preparation. |
| Problem | An omitted/false setting bypassed installation admission. Another host or a restarted preparation could mutate task state before durable consumption failed. |
| Corrected requirement | Mandatory allocation, consumed at the designated installation before authoritative queue preparation; exact empty-run acknowledgement and visible consumed state on interruption. |
| Reason | All mutation-capable paths must enter the same admission boundary. |
| Implementation impact | Secure setting default and rejection of false; move begin before GC/sprint/queue; apply the admitted plan and acknowledge empty runs. |
| Compatibility impact | Preserve existing tasks, approvals and receipts. Unallocated runs now refuse; provisioning and a current approval are required. No automatic conversion or replay of legacy work. |
| Tests affected | Unset/disabled settings, malformed loader results, wrong installation before GC, stale Data after interrupted preparation, and empty-run acknowledgement/publication failures. |
| Runtime/deployment impact | Update settings and approved routing, provision the controller, separate worker privileges, and verify actual scheduled entrypoints before re-enabling unattended work. |


## Git Synchronization Protocol

### Publication and workspace ownership — amendment under review

**Amendment status: Proposed.** This amendment corrects the unsafe checkout and
claim assumptions in the historical procedure below. Candidate implementations
exist for publication and workspace retirement; startup integration, effect
coordination and deployed conformance remain to be verified. DIP-0046 is design
context, not an independent assertion that its proposed features are current.

1. The destination of a publication is explicit and independent of the shared
   checkout's current branch. A health check MUST NOT take ownership of another
   writer's branch, index or working files. Startup, retry and recovery MUST NOT
   stage unrelated work, switch a shared checkout, bypass hooks, or delete data
   merely to make an execution or synchronization attempt proceed.
   Task-run preparation captures each selected repository's default branch and
   acknowledged commit after synchronization. It does not cut a day branch or
   implicitly approve older run refs. Task, batch and report publication share
   that captured parent or a successor verified as the same run's own output;
   an unrelated local commit cannot become an implicitly approved ancestor.
   Per-run destination bindings are released on normal exit and failure.
2. Publication binds immutable source and destination commit identities. An
   integration uses a private index/worktree, preserves configured hooks, and
   verifies the resulting content and parents before a conditional remote
   update. Another writer advancing the destination causes refusal or a fresh
   integration/review; it MUST NOT cause replacement of that writer's history.
   File publication validates and commits the same captured bytes, applying the
   destination's configured Git encoding and clean filters. A declared output
   that is missing is a failure, not an implicit successful deletion or omission.
3. Repository category and publication destination are validated independently
   of the hosting provider. Code requiring review MUST NOT enter an automatic
   knowledge-publication path because its remote does not support that review
   mechanism. Review/approval binds the reviewed commit, and merge revalidates
   that identity. Opening a review is not an acknowledgement of a merge.
4. Failure to publish, including an uncertain push acknowledgement, remains
   visible and retryable without discarding local work. An empty task queue does
   not imply that all earlier work was published. A commit count or elapsed time
   is insufficient authority to delete a run ref; any authorized consumption
   must be conditional on the exact generation being consumed.
5. A clean Git status is not proof of writer quiescence and does not account for
   late ignored files. Automatic workspace retirement MUST preserve uncertain
   files and commits. Permanent reclamation requires established writer
   quiescence and an explicit disposition of retained data. Deployments MUST
   account for retained workspace storage instead of treating retirement as
   completed reclamation. Recovery data MUST reside in persistent private
   storage associated with the repository; an OS temporary directory alone
   does not meet restart/recovery retention requirements.
6. Git publication and task execution ownership are distinct. A task timestamp,
   local lock, or a successful push to an executor's branch MUST NOT be described
   as cross-host exclusive execution. A supported deployment must specify and
   verify either exclusive effects/commits or duplicate-safe effects/commits.
   Expiry alone cannot authorize transfer while the old executor can still
   affect protected state. Transfer requires fencing or verified quiescence;
   deployments without either MUST NOT automatically reclaim execution ownership.

### Publication amendment change record

The startup clarification above is also **Proposed**; it does not certify
current deployed behavior or approve retained historical branches.

| Field | Task-run preparation clarification |
|---|---|
| Previous requirement | Startup selected a shared day branch, parked existing changes, and merged earlier runs into the default branch. File-level publication checks did not define ownership of already-unpublished parent commits. |
| Problem | Preparation could publish another writer's draft, bypass hooks, or merge code before review; a batch publisher could bypass the task publisher's captured parent. |
| Corrected requirement | Read-only preparation, explicit acknowledged default destinations, one parent-ownership check for task/batch/report publication, and explicit review/recovery of historical refs. |
| Reason | A path list describes a new tree delta; it does not authorize every ancestor that a Git push would also disclose. |
| Implementation impact | Remove automatic parking/checkout/merge/ref-pruning paths. Bind run destinations and their verified tips through a shared publication primitive. |
| Compatibility impact | Dirty, unsynchronized or unexpected source history is preserved and requires reconciliation. Startup no longer resumes or publishes historical run branches implicitly. Explicit verified recovery remains supported. |
| Tests affected | Preserve the historical dirty-work, conflict, repeated-run, remote-only, dangling-ref and rejected-push scenarios; assert unchanged original files/index/refs. Add late-checkout, unpublished-parent, batch-bypass and failed-scope tests. |
| Runtime/deployment impact | All publication callers must use the same installed binding contract. Active installations and pending history require separate qualification and reconciliation; this is not an OS boundary or cross-host execution fence. |

| Field | Record |
|---|---|
| Previous requirement | Shared HEAD on the default branch, automatic stash/checkout repair, and timestamp-based claim/commit/push described as a distributed lock. |
| Problem | Checkout/index ownership was not established; unrelated writes could be included or removed. Per-executor branches and elapsed time do not exclude another host or fence a delayed worker. Relative hook paths could stop applying in a private checkout. Re-reading validated paths could publish different bytes, and temporary recovery directories could be removed by the OS. |
| Corrected requirement | Explicit destinations, captured generations, isolated integration, preserved hooks, conditional publication, visible retry outcomes, data-preserving retirement and an independently specified execution/effect ownership model. |
| Reason | Preserve data and authorization while separating repository transport from executor ownership. The existing single-branch procedure cannot provide those guarantees by itself. |
| Implementation impact | Shared Git lifecycle helpers, private Nightshift/Chief of Staff publication, immutable knowledge-file capture and persistent private recovery storage; startup, transport and executor coordination must conform independently. |
| Compatibility impact | Existing commits, run refs and retained work remain recoverable. Shared-HEAD repair and implicit hook bypass cease to be supported recovery behavior. Pending work may require explicit reconciliation. |
| Tests affected | Shared index/checkout preservation, simultaneous independent clones, stale source/base, rejected or uncertain push, hook refusal/mutation/path resolution, late ignored writes, open descriptors, retry and recovery; file substitution, clean filters, missing outputs, persistent recovery location and ownership. |
| Runtime/deployment impact | Qualify supported Git and hook configuration, executor/effect ownership and retained-storage reclamation. Repository tests and isolated host fixtures do not establish active deployment conformance. |
| Status | Proposed correction with partial candidate implementation; remaining startup, coordination and deployment gaps are not waived. |

### Historical branch strategy: single branch (main)

The following procedure records the former implementation and its rationale.
Its shared-checkout mutation requirements conflict with the proposed ownership
amendment above and must not be used as a justification for unsafe recovery.

Local and server both work on `main` with atomic operations protocol.

**Key Principles**:
1. **HEAD MUST be on the repo's default branch — enforced, not assumed** (see below)
2. Pull before any operation
3. Claim tasks via commit + push (distributed lock)
4. Server only modifies designated files
5. Append-only patterns for shared files
6. Commit messages prefixed with `nightshift:`

### The default-branch invariant (added 2026-07-13)

Principle 1 used to be implicit. This DIP said "local and server both work on
`main`" and then specified `git_commit(...)` / `git_push()` with no branch
argument — an invariant stated in prose and enforced nowhere. It cost two months
of work.

**What happened.** `~/Data/5-plur` on the nightshift server was left checked out
on `ops/b17-sprint-claim` after a sprint claim in May. Nobody ran
`git checkout main`. Every claim, cadence run, journal entry and zettel since
went to that branch: **610 commits — 52 zettels, 19 literature notes, every
weekly content calendar since mid-June, 15 journal entries — none of it on
`main`, none of it visible to anyone.**

**Why nothing caught it.** `check_and_repair_git()` ran a health check before
every run and guarded three failure modes: stuck rebase, detached HEAD, missing
upstream tracking. A stray branch passes all three — it is not detached, has no
rebase in flight, and tracks its upstream cleanly. The health check inspected
that branch every night for two months and correctly reported nothing wrong.

> **A health check that only tests for BROKEN states will not catch a VALID
> state that is simply WRONG.** This generalises well beyond git.

**Enforcement.** `check_and_repair_git()` now resolves the default branch from
`origin/HEAD` and adds a fourth check: if HEAD is on any other branch, stash any
dirty tree and check out the default. No `reset --hard` — unlike the rebase and
detached-HEAD cases the tree is not broken, only pointed at the wrong branch, so
the stray branch and its commits are left intact on origin. Shipped in
`datacore-nightshift@9f56c49`.

**Known gap.** This guard lives in nightshift's `run.py`, so it protects Miles
only. Tris (Hermes/hermes) and Mr Data (OpenClaw/plur-claw) run different
runtimes with no equivalent, and at the time of writing neither host had any
cron or timer touching git at all — which is how Tris accumulated 53 uncommitted
competitor scans over two months that reached nobody, and how Mr Data's `~/Data`
came to sit on stray branch `openclaw/manual-install-adaptations` with no PR.

The runtime-independent fix is a commit path that resolves its own destination
rather than inheriting whatever HEAD happens to be — `git hash-object` /
`commit-tree` / `update-ref` can land a knowledge write on the default branch
while HEAD sits on a feature branch, with no checkout and no worktree. Until
that exists, `.datacore/lib/git_fleet_audit.py` (read-only detector) and
`.datacore/lib/git_fleet_sync.py` (bidirectional lander) are the backstop and
are intended to run on a timer on **every** agent host, not just nightshift.

### Sync Flow

```
                    LOCAL                          SERVER
                    ─────                          ──────

 17:00  /tomorrow ──────┐
        - validate tasks │
        - git push       │
        - trigger server ├──────► webhook/ssh ─────────┐
                         │                             │
                                                       ▼
 00:00                                        ┌────────────────┐
 (midnight guarantee)                         │ Server pulls   │
                                              │ Executes tasks │
                                              │ Pushes results │
                                              └───────┬────────┘
                                                      │
 07:00  /today ◄──────────────────────────────────────┘
        - git pull
        - show results
```

### Commit Convention

```bash
nightshift: claim <task-id>           # Starting execution
nightshift: complete <task-id>        # Finished
nightshift: fail <task-id>            # Failed
nightshift: batch-start 2025-12-10    # Beginning run
nightshift: batch-end 2025-12-10      # Run complete
```

### Historical task claiming (does not establish a distributed lock)

This sketch does not establish a cross-host coordination primitive. In
particular, the two-hour age check does not stop or fence the previous worker.
The execution/effect ownership requirement above replaces that assumption;
retaining this sketch is historical traceability, not a conformance claim.

```python
def can_execute(task: Task) -> bool:
    status = task.properties.get('NIGHTSHIFT_STATUS')

    if status == 'executing':
        started = task.properties.get('NIGHTSHIFT_STARTED')
        if started and age(started) < timedelta(hours=2):
            return False  # Someone else working

    if status == 'completed':
        return False

    return True

def claim_task(task: Task, executor_id: str):
    task.state = 'WORKING'
    task.properties['NIGHTSHIFT_STATUS'] = 'executing'
    task.properties['NIGHTSHIFT_EXECUTOR'] = executor_id
    task.properties['NIGHTSHIFT_STARTED'] = now()

    # The branch is NOT optional. A bare commit+push inherits whatever HEAD
    # happens to be, which is exactly how 610 commits landed on a stale sprint
    # branch and were never seen again. Assert the destination, do not inherit it.
    assert_on_default_branch(repo)          # raise, do not guess

    git_commit(f"nightshift: claim {task.id}")
    git_push()
```

> **Anti-pattern — do not reintroduce.** The real `claim.py` shipped
> `git_commit_push()` as `git add -A` → `git commit` → `git push`, with no branch
> argument and no assertion, called from five sites in `run.py`. That is the
> defect. An agent writes the *file*; deterministic code commits it — so there is
> no point in the call stack where an LLM chooses a branch, and therefore no
> point where memory, prompting, or a knowledge pack could have prevented this.
> **Invariants belong where they can be enforced, not where they can be
> remembered.**

### Files Modified by Server

```yaml
server_writes:
  - org/next_actions.org      # Task state changes
  - "[space]/0-inbox/*"       # Output files (creates)
  - "[space]/journal/*"       # Append to daily log

server_reads_only:
  - "**/*.md"                 # Knowledge base
  - ".datacore/learning/*"    # Patterns, corrections
```

### The Midnight Guarantee

Even without `/tomorrow`, server runs at scheduled times:

```
00:00 → Server pulls
      → Checks for :AI: tasks
      → Executes if any exist
      → Pushes results
```

---

## Trigger Mechanisms

| Trigger | Initiator | When |
|---------|-----------|------|
| Manual | `/tomorrow` | User runs command |
| Scheduled | Cron | Midnight, 6am |
| Continuous | Daemon | Polling (24/7 mode) |
| Wake | `/today` | User pulls results |

### Server Operation Modes

```yaml
operation:
  mode: hybrid  # manual | scheduled | continuous | hybrid

  scheduled:
    times: ["00:00", "06:00"]

  continuous:
    enabled: false
    poll_interval: 30m

  manual:
    webhook_enabled: true
    ssh_trigger_enabled: true
```

---

## Platform-Agnostic Scheduling

### Command admission — proposed clarification

**Amendment status: Proposed (2026-09-12).** Unattended command execution must
establish a supported installed adapter, output ownership and recovery behavior
before any Git synchronization or executor effects. A command-definition file
found inside selected data does not establish this contract. Unknown commands,
argument-bearing variants without a declared adapter, and missing required
adapters fail admission. They must not execute and only afterward discover that
publication cannot be acknowledged.

| Field | Record |
| --- | --- |
| Previous requirement | The scheduler invoked commands, while the generic slash-command fallback had no producer-owned output or retry contract. |
| Problem | The executor could perform effects and report success, followed by unavoidable publication failure; a retry could repeat those effects. Prompt lookup also chose executable instructions from selected data. |
| Corrected requirement | Establish the installed command adapter and its output/recovery contract before effects; otherwise report an admission refusal. |
| Reason | Failure known before execution must not be delayed until after irreversible or duplicate effects. |
| Implementation impact | Remove generic tool-session fallback and data-root prompt discovery from scheduled command dispatch. |
| Compatibility impact | Existing dedicated `/today` and `/research-daily` adapters remain. Other slash commands require an explicit supported adapter before unattended execution; a timeout-table entry alone does not authorize execution. |
| Tests affected | Unknown, known-name-without-adapter and argument-bearing command variants perform no Git or executor work; installed adapter selection and required-adapter refusal remain covered. |
| Runtime/deployment impact | Reconcile configured schedules with installed adapters before activation. This admission control does not itself prove adapter credential isolation or exactly-once external effects. |

### Briefing preview — proposed clarification

**Amendment status: Proposed (2026-09-12).** A briefing preview may retrieve
information, but must not execute CoS maintenance or mail actions, write or
publish review queues, refresh persisted news artifacts, generate model prose,
or deliver audio/messages. Omitted refreshes are identified as omitted; absence
of a refresh is not evidence of current operational health. News preview uses
available cached data, and review items can be computed without persisting them.
This contract is not a network sandbox or an assertion of independent OS isolation.

| Field | Record |
| --- | --- |
| Previous requirement | The dry-run option gathered data and skipped prose/audio generation, without separating effectful gatherers from preview reads. |
| Problem | Preview could run maintenance, invoke mail scanning with execution enabled, refresh news files and publish review queues before returning. |
| Corrected requirement | Separate preview collection from these actions and refuse generation/delivery in preview mode. |
| Reason | A preview must not apply the changes it is being used to inspect. |
| Implementation impact | Non-persisting review collection, cached-news collection, and omission of CoS/mail actions in preview dispatch. |
| Compatibility impact | Normal briefing execution retains its existing actions. Preview explicitly labels omitted actions and may show cached or unavailable data. |
| Tests affected | Pipeline action refusal, unchanged cache/index/remote state, and news preview without refresh or external search. |
| Runtime/deployment impact | Installed gatherers and dispatch must agree on preview behavior. Code provenance and the remaining adapter boundaries require independent verification. |

### Schedule Definition

```yaml
# .datacore/modules/nightshift/schedules.yaml
schedules:
  - id: nightly-execution
    schedule: "0 2 * * *"
    command: "nightshift run"
    enabled: true

  - id: morning-briefing
    schedule: "0 7 * * *"
    command: "nightshift today"
    enabled: true
```

### Platform Adapters

```
nightshift/lib/scheduler/
├── base.py              # Abstract interface
├── cron_adapter.py      # Unix cron
├── launchd_adapter.py   # macOS
├── systemd_adapter.py   # Linux
└── daemon_adapter.py    # In-process
```

### CLI

```bash
nightshift scheduler install          # Auto-detect platform
nightshift scheduler install --backend=cron
nightshift scheduler status
```

---

## Command Updates

### /tomorrow (expand)

```
AI DELEGATION
─────────────
Current :AI: tagged tasks:
- [Task 1] :AI:research: - Research competitor X
- [Task 2] :AI:content: - Draft blog post

Queue Optimization Preview:
  1. [Task 1] - Impact: 9, Effort: 3
  2. [Task 2] - Impact: 6, Effort: 4

Estimated: 2 tasks, ~30 min, $0.25

Confirm queue for nightshift? [Y/n]
> y

Pushing to server... Done.
Results in tomorrow's /today briefing.
```

### /today (expand)

```
NIGHTSHIFT RESULTS
──────────────────
✓ Completed (2 tasks)
  - Research competitor X   [Score: 0.85] → Ready
  - Q4 metrics analysis     [Score: 0.92] → Ready

⚠ Needs Review (1 task)
  - Blog post draft         [Score: 0.68]
    CEO: 0.82 "Good message"
    Editor: 0.55 "Tone inconsistent"

Cost: $0.32 | Duration: 38 min
```

---

## Module Structure

```
.datacore/modules/nightshift/
├── README.md
├── module.yaml
├── CLAUDE.md
├── commands/
│   └── nightshift-status.md
├── agents/
│   ├── nightshift-orchestrator.md
│   ├── queue-optimizer.md
│   ├── context-enhancer.md
│   ├── evaluator-user.md
│   ├── evaluator-critic.md
│   ├── evaluator-ceo.md
│   ├── evaluator-cto.md
│   ├── evaluator-coo.md
│   ├── evaluator-archivist.md
│   ├── evaluator-twain.md
│   ├── evaluator-bezos.md
│   └── learning-extractor.md
├── lib/
│   ├── queue.py
│   ├── context.py
│   ├── execute.py
│   ├── evaluate.py
│   ├── analytics.py
│   └── scheduler/
│       ├── base.py
│       ├── cron_adapter.py
│       ├── launchd_adapter.py
│       └── daemon_adapter.py
└── server/
    ├── config.yaml
    ├── run.sh
    └── Dockerfile
```

---

## Implementation Phases

### Phase 1: Local Foundation
- Queue optimizer (analysis only)
- Single evaluator (composite)
- Basic analytics
- Expand `/tomorrow` with preview

### Phase 2: Multi-Evaluator
- Implement evaluator personas
- Consensus engine
- Revision loops

### Phase 3: Context Enhancement
- Context Enhancer agent
- datacortex integration
- Learning file integration

### Phase 4: Server Execution
- Server setup (DigitalOcean)
- Git sync protocol
- Cron-based execution

### Phase 5: Continuous & Learning
- 24/7 daemon mode
- Pattern extraction
- Weekly insights
- Evaluator calibration

---

## Security Considerations

- Server needs git access (deploy key)
- API keys stored in `.datacore/env/` (gitignored)
- Execution logs may contain sensitive data
- Cost controls (daily/weekly budget limits)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Tasks completed overnight | 80%+ |
| Avg quality score | >0.80 |
| Human revision rate | <20% |
| Evaluator-human correlation | >0.85 |
| Cost per task | <$0.50 avg |

---

## Open Questions

1. Should evaluators run in parallel or sequence?
2. How to handle tasks needing external data (APIs)?
3. User customization of evaluator personas?
4. Notification for completed work (email, push)?
5. Budget enforcement mechanism?

---

## Agent Context

This section provides essential information for agents involved in nightshift task execution.

### Key Files

| File | Purpose | Agent Access |
|------|---------|--------------|
| `org/nightshift.org` | Task queue (QUEUED/EXECUTING/DONE/FAILED) | Read/Write |
| `[space]/0-inbox/nightshift-*.md` | Output files | Write only |
| `[space]/journal/*.md` | Execution reports | Append |
| `.datacore/state/nightshift/` | Analytics, execution records | Read/Write |
| `.datacore/learning/patterns.md` | Extracted success patterns | Read |
| `.datacore/learning/corrections.md` | Failure learnings | Read |

### Nightshift States

| State | Meaning | Transitions To |
|-------|---------|----------------|
| `QUEUED` | Waiting in queue | EXECUTING |
| `EXECUTING` | Currently processing | DONE, FAILED |
| `DONE` | Completed with quality gates passed | (terminal) |
| `FAILED` | Needs human review | QUEUED (retry) |

### Context Enhancement

Before executing any task, Context Enhancer provides:
```yaml
context_package:
  semantic_matches: []      # datacortex RAG results
  relevant_indexes: []      # _index.md files
  connected_concepts: []    # Wiki-linked notes
  applicable_patterns: []   # From patterns.md
  relevant_corrections: []  # From corrections.md
  recent_context: []        # Last 7 days journal
  context_quality: 0.0-1.0  # Quality score
```

**Quality threshold**: If `context_quality < 0.6`, flag for expanded search.

### Evaluation Thresholds

| Outcome | Score | Variance | Action |
|---------|-------|----------|--------|
| Approved | ≥0.80 | <0.15 | Mark DONE |
| Approved with notes | ≥0.70 | <0.20 | Mark DONE, log feedback |
| Needs revision | <0.70 | ≥0.20 | Retry (max 2) or escalate |

### Output File Format

```markdown
---
nightshift_id: exec-YYYY-MM-DD-NNN
task: "Task description"
score: 0.85
status: approved|needs_review
---
[Output content]
```

### Git Sync Protocol

- Pull before any operation
- Claim tasks via commit: `nightshift: claim <task-id>`
- Complete tasks via commit: `nightshift: complete <task-id>`
- Server only modifies: `org/next_actions.org`, `[space]/0-inbox/*`, `[space]/journal/*`

## Implementation Status
_Last audited: 2026-03-04_

### Implemented

| Component | Location | Notes |
|-----------|----------|-------|
| Nightshift orchestrator agent | `modules/nightshift/agents/nightshift-orchestrator.md` | Core pipeline coordinator |
| Queue optimizer agent | `modules/nightshift/agents/queue-optimizer.md` | Priority scoring and ordering |
| Context enhancer agent | `modules/nightshift/agents/context-enhancer.md` | RAG + wiki-link context packaging |
| Learning extractor agent | `modules/nightshift/agents/learning-extractor.md` | Pattern and correction extraction |
| Core evaluator panel (6) | `modules/nightshift/agents/evaluator-{user,critic,ceo,cto,coo,archivist}.md` | Always-run evaluation |
| Domain evaluator panel (14) | `modules/nightshift/agents/evaluator-*.md` | Bezos, Buffett, Dijkstra, Feynman, etc. |
| Execution library | `modules/nightshift/lib/` | queue, execute, evaluate, claim, org_parser, output, journal, run, route_tasks, status, summary, metrics, execution_recorder |
| Execution recording | `modules/nightshift/lib/execution_recorder.py` | Writes JSON records to `.datacore/state/nightshift/` for analytics |
| 5-factor priority formula | `modules/nightshift/lib/queue.py` + `queue-optimizer.md` | Aligned with DIP-0009 Part 13 canonical formula (Impact/Urgency/Readiness/Effort/Intent) |
| Dynamic journal path | `modules/nightshift/lib/journal.py` | Detects `notes/journals/` vs `journal/` per space |
| Scheduler (cron + systemd) | `modules/nightshift/lib/scheduler/` | `cron_adapter.py`, `systemd_adapter.py` |
| Server deployment | `modules/nightshift/server/` | Systemd service/timer files, setup script |
| Nightshift status skill | `modules/nightshift/skills/nightshift-status/` | Queue and execution status |
| Test suite | `modules/nightshift/tests/` | 4 test files: failure, intent, metrics, route_config |
| `module.yaml` | `modules/nightshift/module.yaml` (v0.2.0) | Full manifest with tools, schedules, agents |

### Future Work
_Items below are outside v1.0 scope. They remain specified for future implementation._

| Feature | Rationale |
|---------|-----------|
| `launchd_adapter.py` | macOS scheduling; cron covers local development needs |
| Daemon mode (24/7) | Timer-based execution sufficient for overnight tasks |
| Evaluator calibration | Correlation tracking with human judgement; needs evaluation data first |
| Weekly insights report | Aggregate pattern analysis; user-analytics-generator covers basics |
| Cost/budget enforcement | Token tracking exists in metrics; budget limits not yet wired |
| Completion notifications | Email/push notification on task completion |

### Resolved Questions

1. **Server or local?** Both supported. Server uses systemd timers; local uses cron. Same pipeline code.
2. **How many evaluators?** 6 core (always run) + configurable domain evaluators. Task can specify which domain evaluators to include.
3. **State machine?** `TODO→QUEUED→EXECUTING→DONE|FAILED`. Canonical definition in DIP-0009 Part 2.

## References

- DIP-0002: Layered Context Pattern
- DIP-0004: Knowledge Database (Superseded — see Datacortex module)
- DIP-0009: GTD Specification
- DIP-0010: External Sync Architecture
- DIP-0017: Outbox & Archive Pattern (outbox processing schedules)
- Datacore Specification v1.3
- patterns.md: Multi-Source Synthesis, Coordinator-Subagent
- corrections.md: Context quality requirements

---

*"The night shift never sleeps. Your work continues while you rest."*


### Durable task-attempt recovery — proposed audit amendment (2026-09-14)

This amendment is proposed; the historical Implemented status does not ratify
it or assert active deployment. Allocation consumption alone does not prevent
one controller from retrying a partially executed task inside the allocation.

Before invoking a task provider, the controller durably records a unique
`NIGHTSHIFT_ATTEMPT` pending token through the canonical task transaction.
Concurrent or stale snapshots cannot replace an existing attempt. A pending
attempt after restart, or an unknown outcome after invocation, requires explicit
reconciliation. Missing output, a timeout, an authentication/quota message, and
absence of an acknowledgement are not evidence that no effects occurred.
Queue selection, direct task invocation and stalled-task GC preserve that hold.

Only a verified terminal provider result may mark an attempt completed. A
failure to persist the completion acknowledgement leaves the attempt held.
CLI task results use the structured success envelope. Batch submission disables
SDK automatic retries and cannot fall back to another provider after submission
has been attempted. A completed read-only proposal may subsequently enter the
normal approval gate for full execution; it cannot automatically rerun as a
proposal. Explicit operator reconciliation may clear the attempt only after
checking pending and completed effects and preserving the original evidence.

| Field | Record |
|---|---|
| Previous requirement | Allocation is consumed before work; legacy task recovery infers non-execution from missing output and permits transport-error retries. |
| Problem | A worker can cause an effect, lose its acknowledgement, and run again through fallback, retry or stalled-task recovery. |
| Corrected requirement | Persist the attempt before invocation; hold uncertain outcomes across restart and all task admission/recovery paths. |
| Reason | Failure to observe completion cannot safely authorize duplicate effects. |
| Implementation impact | Canonical task-property transaction; typed unknown outcome; strict provider acknowledgement; queue/GC hold. |
| Compatibility impact | Existing untouched tasks need no migration. Uncertain new attempts require explicit reconciliation. Automatic quota fallback after invocation is removed. |
| Tests affected | Concurrent stale snapshots, interrupted process, failed acknowledgement, quota/timeout/error-envelope variants, queue and GC refusal, proposal-to-approved-work transition. |
| Runtime/deployment impact | Qualify the real controller and worker path. This marker is not an OS boundary and does not replace the designated-installation authority or protect against two independent restored controller stores. |
