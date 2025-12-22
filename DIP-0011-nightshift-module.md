# DIP-0011: Autonomous AI Task Execution with Quality Gates

| Field | Value |
|-------|-------|
| DIP | 0011 |
| Title | Autonomous AI Task Execution with Quality Gates |
| Module | nightshift |
| Status | Draft |
| Created | 2025-12-10 |
| Author | Gregor, Claude |
| Depends On | DIP-0002, DIP-0004, DIP-0009, DIP-0010 |

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

**Search Strategy** (multi-modal, per DIP-0004 and patterns.md):

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
    - "2025-12-09: Discussed Verity pricing, leaning toward usage-based"

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
| `:AI:research:` | gtd-research-processor |
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

| State | Meaning | Set By |
|-------|---------|--------|
| `TODO` | Captured, not queued | Human |
| `NEXT` | Queued for nightshift | Human/System |
| `WORKING` | Currently executing | Nightshift |
| `DONE` | Completed and approved | Nightshift |
| `REVIEW` | Needs human review | Nightshift |
| `FAILED` | Execution failed | Nightshift |

### Task Properties

```org
* TODO Research competitor X :AI:research:
  :PROPERTIES:
  :CREATED: [2025-12-10 Tue]
  :SPACE: datafund
  :PRIORITY: A
  :END:

# After queuing:
* NEXT Research competitor X :AI:research:
  :PROPERTIES:
  :NIGHTSHIFT_QUEUED: [2025-12-10 Tue 23:00]
  :NIGHTSHIFT_ID: exec-2025-12-10-001
  :END:

# During execution:
* WORKING Research competitor X :AI:research:
  :PROPERTIES:
  :NIGHTSHIFT_STARTED: [2025-12-10 Tue 02:15]
  :NIGHTSHIFT_EXECUTOR: server:personal
  :END:

# After completion:
* DONE Research competitor X :AI:research:
  :PROPERTIES:
  :NIGHTSHIFT_COMPLETED: [2025-12-10 Tue 02:27]
  :NIGHTSHIFT_SCORE: 0.85
  :NIGHTSHIFT_OUTPUT: 1-datafund/0-inbox/nightshift-001-research.md
  :END:
```

---

## Output Routing

### Output Placement

Outputs always go to `0-inbox/` of the relevant space:

```
Task with :SPACE: datafund
  → Output: 1-datafund/0-inbox/nightshift-{id}-{type}.md

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

### Space Journal Entry

`1-datafund/journal/2025-12-11.md`:

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

`0-personal/notes/journals/2025-12-11.md`:

```markdown
## Nightshift Summary

Overnight processed 5 tasks:
- 0-personal: 1 task
- 1-datafund: 4 tasks

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
    space: "1-datafund"

    timing:
      queued_at: "2025-12-10T23:00:00Z"
      started_at: "2025-12-10T02:15:00Z"
      completed_at: "2025-12-10T02:27:00Z"
      duration_seconds: 720

    resources:
      tokens_used: 45000
      cost_usd: 0.12
      agent: "gtd-research-processor"
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
| Team server (datafund) | Only 1-datafund | 0-personal, others |

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
      url: "nightshift.gregor.io"
      ssh_key: "~/.ssh/nightshift_personal"
      spaces: ["*"]
      is_default: true

# 1-datafund/.datacore/settings.local.yaml
nightshift:
  servers:
    datafund:
      url: "nightshift.datafund.io"
      spaces: ["1-datafund"]
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

## Git Synchronization Protocol

### Branch Strategy: Single Branch (main)

Local and server both work on `main` with atomic operations protocol.

**Key Principles**:
1. Pull before any operation
2. Claim tasks via commit + push (distributed lock)
3. Server only modifies designated files
4. Append-only patterns for shared files
5. Commit messages prefixed with `nightshift:`

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

### Task Claiming (Distributed Lock)

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

    git_commit(f"nightshift: claim {task.id}")
    git_push()
```

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

## References

- DIP-0002: Layered Context Pattern
- DIP-0004: Knowledge Database
- DIP-0009: GTD Specification
- DIP-0010: External Sync Architecture
- DIP-0017: Outbox & Archive Pattern (outbox processing schedules)
- Datacore Specification v1.3
- patterns.md: Multi-Source Synthesis, Coordinator-Subagent
- corrections.md: Context quality requirements

---

*"The night shift never sleeps. Your work continues while you rest."*
