# DIP-0009: GTD System Specification

| Field | Value |
|-------|-------|
| **DIP** | 0009 |
| **Title** | GTD System Specification |
| **Author** | Gregor |
| **Type** | Core |
| **Status** | Implemented |
| **Created** | 2025-12-04 |
| **Updated** | 2026-02-22 |
| **Tags** | `gtd`, `task-management`, `org-mode`, `agents` |
| **Affects** | `org/`, `.datacore/commands/`, `.datacore/agents/`, `.datacore/modules/gtd/` |
| **Specs** | `org-mode-conventions.md` |
| **Agents** | `gtd-inbox-processor`, `ai-task-executor`, `queue-optimizer` |
| **Supersedes** | `.datacore/gtd-spec.md` |

## Summary

This DIP defines the comprehensive GTD (Getting Things Done) implementation for Datacore, including:

- Core GTD workflow and methodology (Parts 1-3)
- Task states, transitions, and Rich Task Standard (Parts 2-3.8)
- AI agent architecture for automation (Part 4)
- Review cycles and commands (Part 5)
- Module requirements and external integration (Parts 6-7)
- Org-mode full specification: CLOCK, DEADLINE, archiving (Part 8)
- Intent Graph strategy layer and Horizons of Focus (Parts 9-10)
- GTD methodology completeness: Natural Planning, trigger lists, annual review (Part 11)
- Failure recovery and strategic prioritization (Parts 12-13)
- Multi-space collaboration and task integrity (Parts 14-15)
- Event-driven reactions architecture (Part 16)
- AI task performance tracking: speed, quality, costs (Part 17)
- Metacognitive planning architecture (Part 18)
- Personal task management lifecycle: commands, interaction, wellbeing (Part 19)
- Inbox processing pipeline: multi-source, intent-based routing (Part 20)
- User analytics and five-layer capability model (Part 21)

## Motivation

Datacore uses GTD methodology with org-mode as the coordination layer. A formal specification ensures:

1. **Consistency** - All agents follow the same rules
2. **Extensibility** - Clear patterns for adding modules/integrations
3. **Clarity** - Humans and AI share the same understanding
4. **Quality** - Standardized task processing and routing

## Core Principles

1. **Augment, don't replace** - AI assists humans, humans make strategic decisions
2. **Single capture point** - inbox.org is sacred, always process to zero
3. **Org-mode as source of truth** - External tools sync to org-mode, not vice versa
4. **Progressive processing** - Inbox → triage → next_actions → archive
5. **Autonomous execution** - AI works overnight, user reviews in morning
6. **Transparent logging** - Every AI action logged for human review

---

## Part 1: GTD Workflow

### The Five Stages

```
┌─────────┐    ┌─────────┐    ┌──────────┐    ┌────────┐    ┌─────┐
│ CAPTURE │ →  │ CLARIFY │ →  │ ORGANIZE │ →  │ REVIEW │ →  │ DO  │
└─────────┘    └─────────┘    └──────────┘    └────────┘    └─────┘
  inbox.org      process       next_actions    daily/weekly   execute
                 classify      route           monthly        delegate
```

### 1. Capture

**Single entry point:** `org/inbox.org`

All tasks, ideas, and inputs go to inbox.org first. No exceptions.

```org
* Inbox
** TODO Quick capture - investor call follow-up
** Research: ZK proof performance benchmarks
** Idea: Telegram bot for daily briefings
```

**Standing items (never remove):**
- Line 1: `* TODO Do more. With less.` (guiding principle)
- The `* Inbox` heading

### 2. Clarify (Process)

For each inbox item, determine:

| Question | Options |
|----------|---------|
| Is it actionable? | Yes → Task, No → Reference/Delete |
| What's the outcome? | Define done state |
| What's the next action? | Single physical action |
| Can AI handle it? | Tag with `:AI:type:` if yes |

**Classification types:**
- `ACTION` - Single next action → next_actions.org
- `PROJECT` - Multi-step outcome → next_actions.org with subtasks
- `WAITING` - Blocked on external → next_actions.org with WAITING state
- `REFERENCE` - Information to keep → notes/knowledge
- `SOMEDAY` - Future possibility → someday.org
- `DELETE` - Not needed → remove

### 3. Organize (Route)

Route to appropriate location based on focus area and tier.

**Routing by keywords:** (see Part 3 for full routing table)

| Keywords | Destination |
|----------|-------------|
| verity, ZK, data marketplace | TIER 1 → /Verity |
| datafund, DMCC, VARA | TIER 1 → /Datafund |
| investor, pitch, fundraising | TIER 1 → /Fundraising |
| mr-data, datacore, agents | TIER 1 → /Mr Data |
| trading, position, market | RESEARCH → Trading |
| health, exercise, supplements | PERSONAL → /Health & Longevity |

### 4. Review

Regular reviews ensure system integrity.

| Cycle | Command | Frequency | Purpose |
|-------|---------|-----------|---------|
| Daily Start | `/today` | Morning | Orient, plan day |
| Daily End | `/tomorrow` | Evening | Process inbox, delegate to AI |
| Weekly | `/gtd-weekly-review` (demoted) | Friday PM | Full system review |
| Monthly | `/gtd-monthly-strategic` (demoted) | Last Friday | Strategic alignment |

### 5. Do (Execute)

**Human execution:**
- Strategic decisions
- External communications (final approval)
- Relationship-based work
- Tasks requiring judgment

**AI delegation:**
- Content generation (`:AI:content:`)
- Research and analysis (`:AI:research:`)
- Data processing (`:AI:data:`)
- Project tracking (`:AI:pm:`)

---

## Part 2: Task States

### State Definitions

**Standard GTD States** (next_actions.org, research_learning.org):

| State | Meaning | Terminal | Required Properties |
|-------|---------|----------|---------------------|
| `TODO` | Standard next action | No | - |
| `NEXT` | High priority, work today | No | - |
| `WAITING` | Blocked on external | No | `:WAITING_ON:` |
| `DONE` | Completed successfully | Yes | `CLOSED:` timestamp |
| `DEFERRED` | Someday/maybe | No | `:DEFERRED_REASON:` (optional) |
| `CANCELLED` | Will not do | Yes | `:CANCEL_REASON:` |

**Nightshift States** (nightshift.org only):

| State | Meaning | Terminal | Required Properties |
|-------|---------|----------|---------------------|
| `QUEUED` | Waiting in AI queue | No | - |
| `EXECUTING` | Currently being processed by AI | No | `:NIGHTSHIFT_EXECUTOR:`, `:NIGHTSHIFT_STARTED:` |
| `DONE` | Completed successfully with quality gates | Yes | `CLOSED:` timestamp, `:NIGHTSHIFT_SCORE:` |
| `FAILED` | Needs human review (evaluation failed) | No | `:NIGHTSHIFT_REASON:` |

### State Transitions

```
                    ┌─────────────────┐
                    │                 │
                    ▼                 │
┌──────┐       ┌────────┐       ┌──────────┐
│ TODO │──────▶│  NEXT  │──────▶│   DONE   │
└──────┘       └────────┘       └──────────┘
    │               │                 ▲
    │               │                 │
    ▼               ▼                 │
┌──────────┐   ┌──────────┐          │
│ DEFERRED │   │ WAITING  │──────────┘
└──────────┘   └──────────┘
    │               │
    └───────────────┴─────────▶ CANCELLED
```

**Valid transitions:**
- `TODO` → `NEXT`, `WAITING`, `DEFERRED`, `DONE`, `CANCELLED`
- `NEXT` → `TODO`, `WAITING`, `DONE`, `CANCELLED`
- `WAITING` → `TODO`, `NEXT`, `DONE`, `CANCELLED`
- `DEFERRED` → `TODO`, `CANCELLED`
- `DONE` → (terminal)
- `CANCELLED` → (terminal)

### Archival Behavior

Terminal states (`DONE`, `CANCELLED`) trigger archival:

1. `CLOSED:` timestamp added
2. Task moved to `org/archive.org` or `*.org_archive`
3. All properties preserved (links, metadata, history)
4. Task remains searchable in archive

### Priority Mapping

| Source | org-mode | Visual |
|--------|----------|--------|
| CRITICAL | `[#A]` + DEADLINE | Red, urgent |
| HIGH | `[#A]` | Red |
| MEDIUM | `[#B]` | Default |
| LOW | `[#C]` | Gray |

---

## Part 3: File Structure

### Org Files

| File | Path | Purpose |
|------|------|---------|
| Inbox | `org/inbox.org` | Single capture point |
| Next Actions | `org/next_actions.org` | Active tasks by focus area |
| Nightshift | `org/nightshift.org` | AI task queue (`:AI:` tagged tasks moved here) |
| Research | `org/research_learning.org` | Research and learning pipeline |
| Someday | `org/someday.org` | Future possibilities |
| Habits | `org/habits.org` | Recurring behaviors |
| Archive | `org/archive.org` | Completed/canceled tasks |

### nightshift.org Structure

The nightshift queue file mirrors the structure of next_actions.org to preserve project context:

```org
#+TITLE: Nightshift Queue
#+TODO: QUEUED EXECUTING | DONE FAILED

* TIER 1: STRATEGIC FOUNDATION
** /Verity
** /Datafund
...
* RESEARCH & LEARNING
** Verity
...
```

**Task Flow:**
1. User adds `:AI:` tag to task in next_actions.org or research_learning.org
2. `/tomorrow` command moves tagged tasks to nightshift.org with QUEUED state
3. Nightshift module processes QUEUED tasks overnight
4. Completed tasks marked DONE or FAILED
5. DONE tasks archived to next_actions.org_archive under matching heading

### next_actions.org Structure

#### Top-Level Tiers (`*` headings)

```org
* TIER 1: STRATEGIC FOUNDATION     # Core business, highest priority
* TIER 2: SUPPORTING WORK          # Support systems, operations
* PERSONAL: LIFE & DEVELOPMENT     # Personal wellbeing, growth
* RESEARCH & LEARNING              # Learning pipeline, research queues
```

#### Focus Areas (`**` headings)

**TIER 1: STRATEGIC FOUNDATION**
| Focus Area | Description | Keywords |
|------------|-------------|----------|
| `/Verity` | Data marketplace, ZK proofs | verity, zkp, institutional |
| `/Mr Data` | AI second brain development | datacore, agents, CLI |
| `/Datafund (Core Operations)` | Core business | datafund, DMCC, VARA |
| `/Fundraising` | Investment, pitch | investors, SAFT, term sheet |
| `/Network & Ecosystem` | Partnerships | partnerships, community |

**TIER 2: SUPPORTING WORK**
| Focus Area | Description | Keywords |
|------------|-------------|----------|
| `BV (Braveheart Ventures)` | Investment vehicle | braveheart, BV |
| `Swarm` | Swarm network (winding down) | swarm, ethswarm |

**PERSONAL: LIFE & DEVELOPMENT**
| Focus Area | Description | Keywords |
|------------|-------------|----------|
| `/Personal Development` | Growth, productivity | personal dev, stoicism |
| `/Health & Longevity` | Health optimization | health, supplements |
| `Home & Family` | Family, home | family, teo |
| `Financial Management` | Personal finance | budget, taxes |

**RESEARCH & LEARNING**
| Focus Area | Description | Keywords |
|------------|-------------|----------|
| `Verity` | Verity research | verity research |
| `Trading` | Market analysis | trading, strategies |
| `Technology` | Tech research | technology, innovation |

### Heading Levels

| Level | Usage | Example |
|-------|-------|---------|
| `*` | Tier | `* TIER 1: STRATEGIC FOUNDATION` |
| `**` | Focus Area | `** /Verity` |
| `***` | Task/Project | `*** TODO [#A] Ship v0.1` |
| `****` | Sub-task | `**** TODO Write tests` |

### Task Format

```org
*** TODO [#A] Verb-driven task heading           :AI:content:
SCHEDULED: <2025-12-02 Mon>
DEADLINE: <2025-12-06 Fri>
:PROPERTIES:
:CREATED: [2025-11-28 Fri]
:SOURCE: Where this came from
:EFFORT: 2h
:CATEGORY: Focus Area
:END:

Context paragraph explaining why this matters.

Action items:
- [ ] Specific step 1
- [ ] Specific step 2

Related: [[Wiki Link 1]], [[Wiki Link 2]]
```

### Part 3.5: Rich Task Standard

Nightshift tasks execute poorly when they lack context. A heading like `* TODO Create Verity roadmap :AI:` gives the executor nothing to work with. The Rich Task Standard defines the full set of properties that make tasks self-contained and executable.

#### Rich Task Format

```org
*** TODO [#B] Verb-driven specific outcome              :AI:pm:
SCHEDULED: <2026-02-22 Sun>
:PROPERTIES:
:ID:       550e8400-e29b-41d4-a716-446655440000
:CREATED:  [2026-02-21 Fri 14:30]
:SOURCE:   inbox
:EFFORT:   Moderate
:CONTEXT: |
  Why this matters. What prompted it. Background.
:KEY_FILES: |
  - path/to/relevant/file.md
  - GitHub: org/repo#42
:CURRENT_STATUS: |
  What exists already. What was last done.
  Journal 2026-02-20 ## Session 1: "Discussed roadmap scope with Crt"
:ACCEPTANCE_CRITERIA: |
  - What "done" looks like (verifiable)
  - Expected output format
:TOOLS: |
  - Read CANVAS.md before starting
  - Check GitHub issues via gh CLI
:DEPENDS_ON: |
  BLOCKS 550e8400-e29b-41d4-a716-446655440001 "Deploy CI pipeline"
  AFTER 550e8400-e29b-41d4-a716-446655440002 "Finalize MVP spec"
  WAITING "legal review of data classification"
:ROLE: |
  You are a technical project manager with deep knowledge
  of the Verity codebase and Datafund's 8-week PoC timeline.
:END:

Context paragraph with additional details.

Related: [[Wiki Link 1]], [[Wiki Link 2]]

Action items:
- [ ] Specific step 1
- [ ] Specific step 2
```

#### Field Definitions

| Field | Location | Required | Purpose |
|---|---|---|---|
| `:ID:` | PROPERTIES | When task is a dependency target | RFC 4122 v4 UUID. Format: `[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}` |
| `:CREATED:` | PROPERTIES | Always | Creation timestamp `[YYYY-MM-DD Day HH:MM]` |
| `:SOURCE:` | PROPERTIES | Always | Origin: `inbox`, `meeting`, `email`, `research`, `idea`, `conversation`, `system` |
| `:EFFORT:` | PROPERTIES | Always | Wall-clock time. Values: `Quick` (<30min), `Moderate` (30-120min), `Significant` (>2hr) |
| `:CONTEXT:` | PROPERTIES | For :AI: tasks | Why this matters, background, what prompted it |
| `:KEY_FILES:` | PROPERTIES | When applicable | Files/repos the executor should read before starting |
| `:CURRENT_STATUS:` | PROPERTIES | When applicable | What exists, what was last done, journal references |
| `:ACCEPTANCE_CRITERIA:` | PROPERTIES | When applicable | Verifiable definition of "done" |
| `:TOOLS:` | PROPERTIES | When applicable | Approach hints, specific tools/commands to use |
| `:DEPENDS_ON:` | PROPERTIES | When applicable | Task ordering (see DEPENDS_ON grammar below) |
| `:ROLE:` | PROPERTIES | Optional | Persona/expertise hint for AI executor |
| body text | After `:END:` | Optional | Additional notes, wiki-links, sub-tasks, checklist |

**Not included** (with rationale):
- ~~SKILLS~~ — Redundant with `:AI:subtype:` tag (DIP-0014). The tag IS the routing hint.
- ~~RELATED~~ — Wiki-links belong in body text per existing convention.
- ~~ENGRAMS~~ — Resolved at runtime by execution pipeline via `engram_selector.py`. Hardcoded IDs rot as engrams are consolidated/retired.

#### Multiline Property Convention

Datacore extends org-mode PROPERTIES with a multiline continuation syntax:

```org
:PROPERTY_NAME: |
  Line 1 of content
  Line 2 of content
  Indented continuation until next :KEY: or :END:
```

**Rules:**
1. The marker is a property whose stripped value is exactly `|` (just the pipe character)
2. Subsequent lines are continuation lines until the next `:KEY:` pattern or `:END:`
3. A value like `:SOURCE: inbox | meeting` is NOT multiline (stripped value is `"inbox | meeting"`, not `"|"`)
4. Empty multiline (`:CONTEXT: |` followed by `:END:`) produces an empty string
5. This is a **Datacore-specific extension** — all Datacore Python tooling MUST support it

#### DEPENDS_ON Grammar

```
DEPENDS_ON     ::= dep_line (NEWLINE dep_line)*
dep_line       ::= dep_type SPACE target
dep_type       ::= "BLOCKS" | "AFTER" | "WAITING"
target         ::= uuid_ref | free_text
uuid_ref       ::= UUID [SPACE DQUOTE label DQUOTE]
free_text      ::= DQUOTE text DQUOTE

UUID           ::= /[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/
```

**UUID generation protocol:** `:ID:` UUIDs are generated at task creation time by the enrichment agent (gtd-inbox-processor, /continue, /wrap-up). Use Python's `uuid.uuid4()` or equivalent. Tasks that are never referenced by DEPENDS_ON do not need an `:ID:`.

**Dependency types:**

| Type | Meaning | Enforcement | Missing UUID behavior |
|---|---|---|---|
| `BLOCKS` | Target task cannot start until this completes | Hard — queue builder skips blocked tasks | Skip dep, log warning |
| `AFTER` | Should run after target (ordering preference) | Soft — queue builder prefers this order | Silently ignore |
| `WAITING` | Blocked on external input (no task reference) | Hard — stays in WAITING state | N/A (no UUID) |

#### Journal Reference Format in CURRENT_STATUS

When referencing journal entries:
```
Journal YYYY-MM-DD ## Section Heading: "Brief quote or summary"
```

#### Backward Compatibility

Existing bare tasks (heading + TODO state only) remain valid. The Rich Task Standard is **additive** — fields are populated when available. A task with only CREATED and SOURCE is still a valid task. No bulk migration required. Existing bare tasks get enriched when they pass through an enrichment agent.

#### Cross-References

- Task routing via `:AI:subtype:` tags: DIP-0014 (Tag Taxonomy)
- `:recurring:` tag: registered by this DIP as a task lifecycle tag
- Agent/command discoverability: DIP-0016 (Agent Registry)
- Nightshift execution pipeline: DIP-0011 (Nightshift Module)
- Engram resolution at runtime: DIP-0019 (Learning Architecture)

### Part 3.6: Recurring Tasks

#### Types

| Type | Schedule | Example | Mechanism |
|---|---|---|---|
| **Habit** | Fixed interval | Take B12, Exercise | org-mode `:STYLE: habit` + `.+Nd` repeater (existing) |
| **Scheduled AI task** | Calendar-based | Daily research digest | `.+Nd` repeater + `:AI:` + `:recurring:` tags |
| **Event-triggered** | On condition | Process inbox when >10 items | Hook/watchdog (future, out of scope) |

#### Recurring AI Task Format

```org
*** TODO [#B] Daily research digest                   :AI:research:recurring:
SCHEDULED: <2026-02-22 Sun .+1d>
:PROPERTIES:
:CREATED:  [2026-02-01 Sat]
:SOURCE:   system
:EFFORT:   Moderate
:CONTEXT: |
  Scan configured news sources for topics relevant to
  Datafund, data economy, AI agents, tokenization.
:ACCEPTANCE_CRITERIA: |
  - Literature notes created for top 3-5 findings
  - Zettels extracted for novel concepts
  - Action items created if strategic opportunity found
:TOOLS: |
  - Use exa/perplexity for web search
  - Use research-orchestrator pipeline
:ROLE: |
  You are a research analyst for Datafund, scanning for
  competitive intelligence and strategic opportunities.
:END:
```

The `:recurring:` tag marks the task as a **template** (never directly executed). The `.+Nd` repeater defines the schedule.

#### Recurrence Lifecycle

1. Template lives in `next_actions.org` with `:recurring:` tag and `.+Nd` repeater
2. `/tomorrow` command detects templates where SCHEDULED date <= today
3. `/tomorrow` creates an **instance** in `nightshift.org`:
   - Copies all properties from template
   - Removes `:recurring:` tag (instance is not a template)
   - Injects fresh `:CURRENT_STATUS:` from journals + last execution output
4. Nightshift executes the instance
5. Template stays in `next_actions.org`; org-mode advances SCHEDULED date by repeater interval

**Hard rule:** Nightshift MUST skip tasks with `:recurring:` tag — only instances (no `:recurring:` tag) are executed.

**Instance failure:** If nightshift execution fails on an instance, mark the instance as DONE with a `FAILED` note. The template is unaffected — next scheduled date still advances, and the next instance will be created normally. Failed instances appear in the morning `/today` briefing for human review.

**Stale schedule:** If a template's SCHEDULED date is far in the past, `/tomorrow` creates ONE instance for today only — no backfill. Update template SCHEDULED to today + interval before creating the instance.

### Part 3.7: Task Creation Protocol

#### Tiered Enrichment

| Tier | When | What | Cost |
|---|---|---|---|
| **Full** | `:AI:` tagged tasks | 3-phase enrichment (Discovery, Judgment, Output) | ~30s agent time |
| **Light** | Human tasks, quick captures | Required fields only (CREATED, SOURCE, CONTEXT sentence, EFFORT) | ~2s |
| **Passthrough** | Tasks arriving with existing properties from upstream | Preserve all existing fields, do not modify or strip | 0 |

**Full enrichment phases** (for `:AI:` tagged tasks):

1. **Discovery:** Search knowledge base for related files (Glob/Grep in `3-knowledge/`). Scan existing tasks for duplicates. Query `engram_selector.py` for relevant patterns. Check journals (last 7 days) for related context.
2. **Judgment:** Filter matches by relevance. Assess EFFORT and PRIORITY. Identify KEY_FILES. Draft CURRENT_STATUS (including journal references). Write verifiable ACCEPTANCE_CRITERIA. Select ROLE if specialized domain.
3. **Output:** Write in Rich Task Standard format with all applicable fields. Generate `:ID:` UUID via `uuid.uuid4()` if task may be a dependency target. If `:ID:` already exists (re-enrichment), preserve existing UUID (idempotent).

**Passthrough explained:** Tasks from mail module arrive as bare inbox entries and will be enriched when gtd-inbox-processor processes them. `route_tasks.py` moves tasks between files without modification — it preserves whatever properties exist. Neither of these need to enrich; they are transport, not creation.

#### Task Creators and Compliance

| Creator | Enrichment tier | Notes |
|---|---|---|
| gtd-inbox-processor | Full (for :AI:), Light (for human) | Primary enrichment chokepoint |
| /wrap-up, /continue | Full+ | BOOTSTRAP format already exceeds standard |
| research-orchestrator | Partial (adds SOURCE, CONTEXT) | Downstream inbox-processor does full enrichment |
| gtd-project-manager | Partial (adds project context) | Downstream inbox-processor does full enrichment |
| transcription-processor | Partial (adds meeting context) | Creates with meeting-specific fields |
| mail module | Passthrough | Deposits in inbox; inbox-processor enriches |
| route_tasks.py | Passthrough | Transport only; preserves existing properties |

#### Fallback for Sparse Context

When discovery finds no matches (new topic area):
- Still populate all required fields
- Use CONTEXT to describe what IS known (even one sentence)
- Leave KEY_FILES, CURRENT_STATUS empty rather than fabricating
- Do NOT generate hallucinated file paths or status

### Part 3.8: Task Dependencies and Queue Ordering

#### Queue Ordering Algorithm

Nightshift `build_queue()` MUST:

1. Parse `:DEPENDS_ON:` from all queued tasks
2. Resolve UUID references: look up `:ID:` properties across all tasks **in the current nightshift.org queue** (queue-local scope). Log warning for unresolved UUIDs. Duplicate UUIDs: log warning, use first match.
3. Build directed graph (edges from dependency to dependent)
4. **Cycle detection and breaking:** Run Kahn's algorithm. If nodes remain (cycle exists):
   a. Among remaining edges, select the BLOCKS edge with lowest task priority (C < B < A)
   b. Tie-break: oldest `:CREATED:` date. Final tie-break: arbitrary (first in sorted list — deterministic, always terminates)
   c. Remove that edge, log warning
   d. Re-run Kahn's. Repeat until no nodes remain (guaranteed: each iteration removes at least one edge from a finite set)
5. **Topological sort:** Kahn's algorithm produces the execution order
6. **Within same topological level** (tasks whose longest-path-from-root distance is equal): sort by priority score (existing `calculate_priority()` in `queue_optimizer.py`)
7. Tasks with unresolved BLOCKS dependencies (UUID not found in queue): mark as WAITING with reason, exclude from queue. Tasks referencing missing UUIDs in AFTER: silently ignore (soft constraint).

#### WAITING Resolution

WAITING dependencies (external blockers) are resolved by:
1. Human removes the WAITING line from `:DEPENDS_ON:`
2. Human changes task state from WAITING to TODO/NEXT
3. `/today` surfaces WAITING tasks for review

---

## Part 4: AI Agent Architecture

### Coordination Layer

```
┌─────────────────────────────────────────────────────────┐
│                     org-mode (source of truth)          │
│  inbox.org → next_actions.org → archive.org            │
└─────────────────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  GitHub  │ │ Calendar │ │  Asana   │
        │  Issues  │ │ (Google) │ │          │
        └──────────┘ └──────────┘ └──────────┘
              ▲            ▲            ▲
              └────────────┴────────────┘
                    Bidirectional sync
                    (via DIP-0010)
```

### Core Execution Engine

**`ai-task-executor`** - 24/7 autonomous task routing

- Scans next_actions.org for `:AI:` tagged tasks
- Prioritizes by: `[#A]` → `[#B]` → `[#C]`, then SCHEDULED date
- Routes to specialized agents by tag
- Handles outcomes: SUCCESS → DONE, NEEDS_REVIEW → flag, FAILED → report
- Logs all executions to journal
- Retry logic: transient failures (1h, 3h, 6h), manual failures need human

### Specialized Agents

| Tag | Agent | Capability | Output Location |
|-----|-------|------------|-----------------|
| `:AI:content:` | `gtd-content-writer` | Blog, email, docs, social | `content/[type]/` |
| `:AI:research:` | `research-orchestrator` | URL analysis, literature notes, zettels | `3-knowledge/` |
| `:AI:data:` | `gtd-data-analyzer` | Metrics, reports, insights | `content/reports/` |
| `:AI:pm:` | `gtd-project-manager` | Status tracking, blockers | journal + org-mode |

### Inbox Processing

| Agent | Role |
|-------|------|
| `gtd-inbox-processor` | Single entry processing |
| `gtd-inbox-coordinator` | Batch orchestration (spawns processors) |

### Session Wrap-Up (Coordinator Pattern)

| Agent | Role |
|-------|------|
| `journal-entry-writer` | Per-space journal writer (spawned by coordinator) |
| `journal-coordinator` | Discovers spaces, spawns journal-entry-writer per space |
| `session-learning` | Per-space learning extraction |
| `session-learning-coordinator` | Discovers spaces, spawns session-learning per space |

**Pattern:** Commands like `/wrap-up` spawn coordinators that:
1. Discover spaces dynamically via `[0-9]-*/` pattern
2. Spawn subagents in parallel (one per space)
3. Each subagent writes to space-specific files
4. Coordinator aggregates results

**Processing flow:**
1. Read inbox entry
2. Classify (ACTION, PROJECT, REFERENCE, etc.)
3. Enhance with metadata (priority, effort, links)
4. Route to destination
5. Remove from inbox

### Agent Quality Standards

**All agents MUST:**
- Respect terminal states (never modify DONE/CANCELLED)
- Include required properties on state transitions
- Log all actions to journal
- Flag uncertain decisions for human review
- Return structured JSON status

**Success criteria:**
- Task completion rate > 80%
- Quality approval rate > 90%
- Time saved: 10-20h/week

### Nightshift Execution Context

When nightshift executes a task, `build_task_prompt()` in `execute.py` reads Rich Task Standard properties to construct a complete execution prompt. The prompt structure:

1. **Agent routing preamble** (always present) — agent type from `:AI:subtype:` tag mapping
2. **Working directory** — `data_dir` path
3. **Role** (optional) — from `:ROLE:` property
4. **Task heading + metadata** — title, priority, effort, tags
5. **Context sections** (omit if empty) — CONTEXT, CURRENT_STATUS, KEY_FILES, ACCEPTANCE_CRITERIA, TOOLS
6. **Applicable engrams** (runtime-resolved) — from `engram_selector.py` based on task description
7. **Task body** — free-text content after `:END:`

Sections with no content are omitted. This ensures bare tasks still produce valid (if minimal) prompts, while rich tasks give the executor full context.

**Runtime engram injection** happens in `execute_task()`, not `build_task_prompt()`:
```python
engrams = select_engrams(scope='global', task_desc=task.title, limit=5)
engram_text = format_injection(engrams, limit=5)
prompt = build_task_prompt(task, data_dir, engram_text=engram_text)
```

---

## Part 5: Review Cycles

### Daily Start (`/today`)

**Timing:** Morning, before work begins

**Steps:**
1. Greet and orient to the day
2. Review AI work completed overnight
3. Show org-mode agenda (SCHEDULED, DEADLINE)
4. Display active NEXT actions
5. Surface WAITING items (flag >7 days old)
6. Check inbox count
7. Set Top 3 Must-Win Battles for the day
8. Suggest time blocks
9. Write summary to journal

### Daily End (`/tomorrow`)

**Timing:** Evening, end of work day

**Steps:**
1. Process inbox systematically (one item at a time)
2. Classify and route each entry
3. Tag AI-automatable work
4. Trigger AI Task Executor for overnight execution
5. Review day's accomplishments
6. Capture gratitude and reflection
7. Preview tomorrow
8. Extract session learnings
9. Provide mental closure

### Weekly Review (`/gtd-weekly-review`)

**Timing:** Friday afternoon

**Steps:**
1. Review week's accomplishments by category
2. Assess AI delegation effectiveness
3. Process remaining inbox items
4. Review all work areas
5. Analyze WAITING items by age
6. Review all projects (status, blockers)
7. Review someday/maybe items
8. Check habit completion rates
9. Preview next week's deadlines
10. Set Top 3 priorities for next week
11. Reflect on systems (what's working, friction)
12. Health check CLAUDE.md
13. Generate weekly summary

### Monthly Strategic (`/gtd-monthly-strategic`)

**Timing:** Last Friday of month

**Steps:**
1. Review month's accomplishments
2. Aggregate AI delegation summary
3. Review project portfolio
4. Compare goals vs actuals
5. Strategic assessment per work area (START/STOP/CONTINUE)
6. Time allocation analysis
7. System health assessment
8. Set strategic priorities for next month
9. Identify process improvements
10. Create action items from insights

---

## Part 6: Module Architecture

### Core (Always Present)

| Component | Purpose |
|-----------|---------|
| GTD commands | Daily/weekly/monthly workflows |
| AI task executor | Autonomous task routing |
| Inbox processor | Entry classification and routing |
| Session learning | Extract patterns from work |

### Optional Modules

| Module | Purpose | DIP |
|--------|---------|-----|
| `task-sync` | GitHub, Asana, Calendar sync | DIP-0010 |
| `trading` | Trading-specific workflows | - |
| `meetings` | Meeting lifecycle, questions | DIP-0013 |

### Module Interface

Modules extend Datacore by providing:
- Agents in `.datacore/modules/[name]/agents/`
- Commands in `.datacore/modules/[name]/commands/`
- Config in `.datacore/modules/[name]/config.yaml`

Registration via `module-registrar` agent.

---

## Part 7: External Integration

### Sync Architecture (DIP-0010)

Org-mode is the source of truth. External tools sync bidirectionally.

**Adapter pattern:**
```
org-mode ←→ Sync Engine ←→ Adapter ←→ External Tool
                              │
                    ┌─────────┴─────────┐
                    │ GitHub Adapter    │
                    │ Calendar Adapter  │
                    │ Asana Adapter     │
                    └───────────────────┘
```

**Task identity:** `:EXTERNAL_ID:` property links org task to external item.

**Conflict resolution strategies:**
- `org_wins` - org-mode changes overwrite external
- `external_wins` - external changes overwrite org
- `merge` - field-level merge with rules
- `ask` - prompt human for resolution

### Integration Points

| Tool | Sync Type | Trigger |
|------|-----------|---------|
| GitHub Issues | Bidirectional | Webhook + polling |
| Google Calendar | Read | Polling |
| Asana | Bidirectional | Webhook |

---

## Part 8: Org-Mode Specification (Full Utilization)

Datacore uses org-mode as its coordination layer but currently leverages only a subset of org-mode's capabilities. This part formalizes which features Datacore uses and specifies adoption of previously unused features for time tracking, deadline management, and archiving.

**Current utilization:**
- Headings + TODO states (core workflow)
- Property drawers (3,259 instances across all spaces)
- Tags including `:AI:` delegation tags
- `SCHEDULED:` timestamps
- `LOGBOOK` drawers (habits module)
- `:Effort:` estimates (288 instances)

**New utilization (specified below):**
- `DEADLINE:` timestamps (distinct from SCHEDULED)
- `CLOCK` time tracking entries
- Task archiving to sibling files
- Formalized property drawer vocabulary

### 8.1 Timestamps and Scheduling

Org-mode provides two distinct timestamp types. Datacore currently uses only SCHEDULED; this section specifies both.

**SCHEDULED** — soft date, when you plan to START working on a task:
```org
SCHEDULED: <2026-03-01 Sun>
```
Used for time-blocking, recurring habits, and AI task scheduling. Appears in `/today` agenda view. Does not imply a hard commitment.

**DEADLINE** — hard date, when the task is DUE:
```org
DEADLINE: <2026-03-15 Sun>
```
Triggers warnings in `/today` briefing N days before the deadline. The warning window is configurable per task via `:DEADLINE_WARNING_DAYS:` property (default: 14 days).

```org
*** TODO [#A] Submit grant application                    :AI:content:
DEADLINE: <2026-04-01 Wed>
SCHEDULED: <2026-03-15 Sun>
:PROPERTIES:
:DEADLINE_WARNING_DAYS: 21
:END:
```

**Repeaters** (already used for habits, extended to recurring AI tasks):

| Syntax | Behavior | Example |
|--------|----------|---------|
| `.+Nd` | N days from completion date | `.+7d` = 7 days after last done |
| `++Nd` | Fixed interval, next occurrence after today | `++1w` = every Monday |
| `+Nd` | N days from scheduled date (regardless of completion) | `+30d` = 30 days from original |

**AI behavior for DEADLINE:**
- `gtd-inbox-processor`: Sets DEADLINE when task has an explicit due date (from email, meeting action item, or user instruction). Does NOT set DEADLINE speculatively.
- `/today`: Shows overdue DEADLINEs prominently at top of agenda. Shows approaching DEADLINEs (within warning window) with days remaining.
- Weekly review: Flags tasks past DEADLINE without completion.
- `strategic-prioritizer` (Part 13): Boosts urgency score for tasks within DEADLINE warning window.

### 8.2 CLOCK Time Tracking

Org-mode tracks time via CLOCK entries in LOGBOOK drawers:

```org
*** DONE Generate competitive analysis report             :AI:research:
CLOSED: [2026-02-22 Sun 02:47]
:LOGBOOK:
CLOCK: [2026-02-22 Sun 01:00]--[2026-02-22 Sun 02:47] =>  1:47
:END:
:PROPERTIES:
:NIGHTSHIFT_SCORE: 0.850
:END:
```

**For AI tasks**, nightshift writes CLOCK entries automatically:
- Clock-in = task execution start time
- Clock-out = task execution end time (after evaluation)
- Duration = computed by org-mode convention (`=> H:MM`)

This supplements (but does not replace) existing `:NIGHTSHIFT_STARTED:` and `:NIGHTSHIFT_COMPLETED:` properties. CLOCK entries enable standard org-mode time reporting; custom properties enable programmatic access.

**Parser requirement:** `org_parser.py` needs a `write_clock_entry(task, start, end)` method that:
1. Creates or appends to `:LOGBOOK:` drawer
2. Formats timestamps as `[YYYY-MM-DD Day HH:MM]`
3. Computes duration in `H:MM` format
4. Places CLOCK entry inside LOGBOOK (before any existing entries — newest first)

### 8.3 Effort Estimates

Already in use (288 `:Effort:` properties). This section formalizes the convention.

**Format:** The Rich Task Standard (Part 3.5) defines effort as categorical: `Quick` (<30min), `Moderate` (30-120min), `Significant` (>2hr). For AI tasks requiring precise tracking, a numeric `H:MM` format is also valid:

```org
:Effort: 1:30
```

**Rules:**
- All tasks SHOULD have `:Effort:` set at creation (inbox processor estimates)
- Categorical values are preferred for human tasks (less cognitive load)
- Numeric `H:MM` values are preferred for AI tasks (enables accuracy tracking)
- AI tasks: compare `:Effort:` estimate vs actual CLOCK duration → track accuracy ratio (see Part 17)
- Aggregate: effort accuracy ratio per task type feeds into better future estimates

### 8.4 Task Archiving

Completed tasks accumulate indefinitely in `next_actions.org` (currently 273KB, growing). Org-mode archiving moves DONE tasks to a sibling archive file, preserving full history while keeping the active file navigable.

**Archive target:** `org/next_actions_archive.org` (sibling file, same directory)

**What is preserved:**
- Full heading hierarchy (tier → focus area → task)
- All property drawers (metadata, NIGHTSHIFT_* properties)
- CLOCK entries and LOGBOOK
- Tags (for historical analysis and reporting)
- Body text and checklists

**Archive trigger:** During weekly review, tasks meeting ALL conditions:
1. Terminal state: `DONE` or `CANCELLED`
2. `CLOSED:` timestamp older than 30 days
3. Not a parent heading with non-archived children

**Archive rules:**
- Project headings (those with children) are kept in active file until ALL children are archived or the project itself is marked DONE
- Focus area headings (`**` level) are NEVER archived (they are structural)
- Tier headings (`*` level) are NEVER archived (they are structural)
- Archive file mirrors the heading structure: same tiers and focus areas, tasks nested under matching parents

**Parser requirement:** `org_parser.py` needs an `archive_task(task, target_file)` method that:
1. Reads or creates target archive file
2. Finds or creates matching heading hierarchy (tier → focus area)
3. Moves task (with all properties, LOGBOOK, body) under matching parent
4. Removes task from source file
5. Adds `:ARCHIVE_TIME:` property with current timestamp

**nightshift.org archiving:** Same pattern applies. Archive target: `org/nightshift_archive.org`. Tasks in DONE/FAILED state older than 7 days (shorter window since nightshift tasks are reviewed daily).

### 8.5 Property Drawer Standard

This section formalizes the complete property vocabulary across the GTD system. Properties are grouped by lifecycle phase.

**Task creation properties** (set by inbox processor or task creator):

| Property | Required | Format | Set By | Notes |
|----------|----------|--------|--------|-------|
| `:CREATED:` | Always | `[YYYY-MM-DD Day HH:MM]` | Inbox processor | Creation timestamp |
| `:Effort:` | Should | Categorical or `H:MM` | Inbox processor | Estimated effort |
| `:SOURCE:` | Always | Enum (see Part 3.5) | Creator | Origin of task |
| `:CONTEXT:` | For `:AI:` tasks | Multiline text | Enrichment | Strategic context, intent path |
| `:OWNER:` | Team spaces | `@person` | Creator/PM | Responsible person |
| `:DEADLINE_WARNING_DAYS:` | If DEADLINE set | Integer | Creator | Days before DEADLINE to warn |

**Rich Task properties** (set during enrichment, see Part 3.5 for full specification):

| Property | Required | Set By |
|----------|----------|--------|
| `:ID:` | When dependency target | Enrichment agent |
| `:KEY_FILES:` | When applicable | Enrichment agent |
| `:CURRENT_STATUS:` | When applicable | Enrichment agent |
| `:ACCEPTANCE_CRITERIA:` | When applicable | Enrichment agent |
| `:TOOLS:` | When applicable | Enrichment agent |
| `:DEPENDS_ON:` | When applicable | Enrichment agent |
| `:ROLE:` | Optional | Enrichment agent |

**Nightshift execution properties** (set during and after AI execution):

| Property | Set By | Format | Notes |
|----------|--------|--------|-------|
| `:NIGHTSHIFT_STATUS:` | Evaluator pipeline | `approved` / `approved_with_notes` / `needs_review` / `rejected` | Consensus decision |
| `:NIGHTSHIFT_SCORE:` | Evaluator pipeline | `0.000`-`1.000` | Weighted consensus score |
| `:NIGHTSHIFT_OUTPUT:` | Executor | File path | Location of generated output |
| `:NIGHTSHIFT_EXECUTOR:` | Pipeline | `server:hostname` or `local` | Where execution ran |
| `:NIGHTSHIFT_STARTED:` | Pipeline | ISO datetime | Execution start (also in CLOCK) |
| `:NIGHTSHIFT_COMPLETED:` | Pipeline | ISO datetime | Execution end (also in CLOCK) |
| `:NIGHTSHIFT_COST:` | Pipeline | USD amount (e.g., `0.42`) | Total API cost for this task |
| `:NIGHTSHIFT_TOKENS:` | Pipeline | Integer | Total tokens consumed (input + output) |
| `:NIGHTSHIFT_DURATION:` | Pipeline | Seconds (integer) | Wall-clock execution time |
| `:NIGHTSHIFT_RETRY:` | Failure analyzer | Integer (0-based) | Retry attempt number |

**Archive property** (set during archiving):

| Property | Set By | Format |
|----------|--------|--------|
| `:ARCHIVE_TIME:` | Archive process | `[YYYY-MM-DD Day HH:MM]` |

### 8.6 Custom Agenda Views

Org-mode's agenda is its most powerful feature — structured queries over all tasks. In Datacore, agenda views are exposed as **MCP tools** (per DIP-0022), making them available to any agent, command, or workflow without requiring org-mode knowledge.

**Core tool:** `gtd.agenda_view(filters) → TaskList`

**Available filters:**

| Filter | Type | Example | Description |
|--------|------|---------|-------------|
| `state` | Enum[] | `["TODO", "NEXT"]` | Task states to include |
| `tags` | String[] | `[":AI:research:"]` | Required tag match |
| `deadline_within` | Integer | `14` | Days until DEADLINE |
| `scheduled_before` | Date | `2026-03-01` | SCHEDULED before date |
| `effort_max` | String | `1:00` | Maximum effort estimate |
| `focus_area` | String | `"trading"` | Focus area heading name |
| `tier` | Integer | `1` | Priority tier (1-3) |
| `space` | String | `"0-personal"` | Target space |
| `has_property` | String | `"EXTERNAL_URL"` | Tasks with specific property |
| `created_after` | Date | `2026-02-01` | Created after date |

**Predefined views** (convenience wrappers):

| View | Filters | Used By |
|------|---------|---------|
| `today_priorities` | `state=NEXT, tier<=2, scheduled<=today` | `/today` |
| `overdue_deadlines` | `deadline < today` | `/today`, weekly review |
| `quick_wins` | `effort_max=0:30, state=TODO` | Two-minute rule (Part 11.5) |
| `ai_queue` | `tags=:AI:, state=TODO\|NEXT` | `/tomorrow` |
| `stale_projects` | Projects with no activity >14 days | Weekly review (Part 15) |
| `waiting_on` | `state=WAITING` | Weekly review |
| `focus_area_load` | Group by focus area, sum effort | User analytics (Part 21) |

**Cross-space aggregation:** When `space="all"`, the tool scans all spaces' `org/` directories and merges results. Each task includes a `space` field in the output.

**Implementation:** MCP tool in the `gtd` module (stateless, deterministic — reads org files, applies filters, returns structured data).

---

## Part 9: Intent Graph (Strategy Layer)

The Intent Graph is Datacore's strategic planning layer, connecting **why** (vision) to **what** (tasks). Every task should trace back to at least one intent. The graph lives as a document within the Datacore system space and is reviewed during GTD review cycles.

**Source document:** `2-datacore/1-tracks/ops/Intent-Graph.md`

### 9.1 Structure

The Intent Graph has five levels of granularity:

| Level | Name | Granularity | Review Cycle |
|-------|------|-------------|--------------|
| 0 | Vision | One sentence | Annual |
| 1 | Intents | Aspirational (5 max) | Quarterly |
| 2 | Strategic Goals | Measurable outcomes | Monthly |
| 3 | Initiatives | Multi-month efforts | Monthly |
| 4 | Projects | Bounded, deliverable | Weekly |

Leaves (Level 4) feed into `next_actions.org` as GTD projects and tasks. Every task ideally traces back to at least one intent via the `:CONTEXT:` property.

### 9.2 Dimensions

The five intents span complementary dimensions:

| # | Intent | Dimension |
|---|--------|-----------|
| 1 | Augments human intelligence | Product |
| 2 | Runs itself autonomously | Operations |
| 3 | Financially sustainable | Sustainability |
| 4 | Empowering and worth sharing | Experience |
| 5 | Enables collective intelligence | Ecosystem |

Each intent has success criteria at Level 2+ that make it measurable. Without criteria, an intent is aspiration, not strategy.

### 9.3 Multi-Parent Notation

Projects that serve multiple intents are marked with `[*N]` where N = number of parent intents:

```
- First-run experience [*3: Intent 1, 4, 5]
```

**Multi-parent projects are high-leverage** — each unit of work serves multiple strategic goals. They receive priority in queue ordering (see Part 13).

### 9.4 Integration with GTD

The Intent Graph connects to GTD via three mechanisms:

1. **`:CONTEXT:` property** — Tasks reference their intent path:
   ```org
   :CONTEXT: |
     Intent 5 > User base reaches critical mass > Landing page matrix
   ```

2. **`strategic-prioritizer` agent** (Part 13) — Scores tasks by intent alignment, boosting multi-intent tasks.

3. **Review cycles** — Intent Graph is reviewed at defined intervals:

   | Cycle | Actions |
   |-------|---------|
   | Weekly | Which intents got zero work? Any stale Level 4 nodes (>30 days)? |
   | Monthly | Are the 5 intents still the right 5? Update success criteria with actuals. Prune completed branches. |
   | Quarterly | Full intent review with strategic context. Idea-to-project conversion rate. Vision progress check. |

### 9.5 Idea Graph Pipeline

Ideas flow from sessions, research, and learning into the Intent Graph:

```
Sources                    Filter                    Destination
────────                   ──────                    ───────────
Session insights     →                          →  Intent Graph (new node)
Research outputs     →   Intent alignment?      →
Engram patterns      →   0 intents = noise      →  someday.org or discard
User feedback        →   1 intent = normal      →  next_actions.org
Market observation   →   2+ intents = priority  →  next_actions.org (high-leverage flag)
```

Unaligned ideas (0 intents) either reveal a missing intent (rare — update the graph) or are noise (park in `someday.org`).

**The idea graph is the input. The intent graph is the filter. GTD is the output.**

---

## Part 10: Horizons of Focus

GTD defines six horizons of perspective, from ground-level actions to life purpose. This part maps each horizon to concrete Datacore structures and specifies how they are maintained.

### 10.1 Horizon Mapping

| Horizon | GTD Name | Datacore Location | Review Cycle |
|---------|----------|-------------------|--------------|
| Ground | Next Actions | `org/next_actions.org` (TODO/NEXT items) | Daily |
| H1 | Projects | `org/next_actions.org` (headings with children) + Project Canvas | Weekly |
| H2 | Areas of Focus | Focus area headings in `next_actions.org` (e.g., `/Verity`, `/Health`) | Weekly |
| H3 | Goals (1-2yr) | Intent Graph Level 2-3 nodes with OKRs | Monthly |
| H4 | Vision (3-5yr) | Intent Graph Level 1 nodes | Quarterly |
| H5 | Purpose | Intent Graph Level 0 (Vision) + Foundations scaffolding | Annual |

### 10.2 Project Canvas (H1)

Projects with complexity beyond a simple task list use a **Project Canvas** — a structured one-page document based on the HBR/Nieto-Rodriguez methodology.

**When to create a Canvas:**
- Project has >5 tasks or >2 weeks estimated duration
- Multiple people involved (team spaces)
- Requires budget or resource allocation
- Has external dependencies or stakeholders
- `gtd-project-manager` flags it (see Part 11.6)

**Canvas location:** `CANVAS.md` in the project directory, or inline in the relevant track folder for non-code projects.

**Canvas structure (five sections):**

**1. Description** — Elevator pitch (2-3 sentences providing context and scope)

**2. Foundation**
- **Purpose**: Why is the project being done? What problem does it solve?
- **Investment**: Budget + person-hours allocated
- **Benefits**: Outcomes stakeholders gain if successful (strategic, not tactical)

**3. People**
- **Sponsor**: Who is accountable?
- **Resources**: Skills needed, who manages delivery
- **Roles**: Named roles with purpose statements and effort allocation
- **Stakeholders**: Who is affected by or benefits from the project?

**4. Creation**
- **Deliverables**: Concrete outputs the project produces
- **OKRs**: Objectives and Key Results (see 10.3)
- **Plan**: Timeline with milestones and specific dates
- **Change**: Risk management and stakeholder engagement approach

**5. References** — Links to background materials, standards, related work

**Reference implementation:** `1-datafund/2-projects/verity/CANVAS.md`

### 10.3 OKR Integration

OKRs (Objectives and Key Results) live inside the Project Canvas `Creation` section and link to Intent Graph nodes.

**Format:**
```markdown
### OKRs

**Objective 1: [Clear outcome statement]**
Intent: [Intent Graph path]
- KR1: [Measurable result] → @owner
- KR2: [Measurable result] → @owner
- KR3: [Measurable result] → @owner

**Objective 2: [Clear outcome statement]**
Intent: [Intent Graph path]
- KR1: [Measurable result] → @owner
```

**Rules:**
- Each Objective maps to one or more Intent Graph nodes
- Each Key Result has a single owner (team member or AI agent)
- Key Results must be measurable (number, date, binary)
- Maximum 3-5 Key Results per Objective
- Key Results become tasks in `next_actions.org` (or GitHub Issues for team spaces)

### 10.4 Horizon Coverage Check

During weekly review, verify that all horizons are populated:

```
H5 Purpose     [✓] Vision statement exists in Intent Graph
H4 Vision      [✓] 5 intents defined with success criteria
H3 Goals       [?] Check: do all intents have Level 2 goals?
H2 Areas       [✓] Focus areas in next_actions.org
H1 Projects    [?] Check: do all active projects have defined next actions?
Ground         [✓] NEXT items exist for today
```

Gaps surface as review items. The `gtd-project-manager` agent can generate this checklist.

---

## Part 11: GTD Methodology Completeness

This part addresses all identified gaps between David Allen's full GTD methodology and Datacore's current implementation.

### 11.1 Natural Planning Model

GTD's Natural Planning Model defines five phases for project planning. Datacore maps these to AI-assisted workflows:

| Phase | GTD | Datacore Implementation |
|-------|-----|------------------------|
| 1. Purpose/Principles | Why are we doing this? | Project Canvas `Foundation` section |
| 2. Outcome Visioning | What does success look like? | Project Canvas `Description` + OKRs |
| 3. Brainstorming | Generate ideas without filtering | Idea graph capture → Intent Graph evaluation |
| 4. Organizing | Structure ideas into plan | Task decomposition into `next_actions.org` |
| 5. Next Actions | Identify first physical actions | AI identifies and queues first actions |

**Trigger:** When a new project heading is created in `next_actions.org` (heading with `***` level under a focus area), `gtd-project-manager` runs Natural Planning:

1. Prompts user for purpose and desired outcome (if not already in `:CONTEXT:`)
2. Suggests decomposition into subtasks based on similar past projects
3. Creates Project Canvas stub if project meets complexity threshold (Part 10.2)
4. Identifies and marks first next action as `NEXT`

### 11.2 Someday/Maybe Review

**File:** `org/someday.org` (already exists)

Weekly review step already reviews someday items. This section adds AI-assisted curation:

**Weekly review additions:**
- AI suggests promotions from someday → active based on:
  - Intent alignment score (does a newly added intent make this relevant?)
  - Context changes (season, market conditions, completed prerequisites)
  - Recency of related activity

**Monthly review additions:**
- AI identifies stale someday items (>6 months since last review/modification)
- For each stale item: prompt for archive, reactivation, or keep with updated notes
- Items archived move to `org/someday_archive.org` with `:ARCHIVE_TIME:` and `:ARCHIVE_REASON:`

**Format in someday.org:**
```org
* Someday/Maybe
** Technology
*** TODO Build Obsidian plugin for Datacore
:PROPERTIES:
:CREATED: [2026-01-15 Wed]
:LAST_REVIEWED: [2026-02-21 Fri]
:INTENT_ALIGNMENT: Intent 4 > Community extensions
:END:
```

The `:LAST_REVIEWED:` property is updated during each weekly review pass.

### 11.3 Trigger Lists

Trigger lists are context-specific prompts that help surface forgotten commitments during mind sweeps (weekly review step 3).

**Location:** `.datacore/specs/trigger-lists.yaml`

**Structure:**
```yaml
trigger_lists:
  professional:
    - Projects started but not completed
    - Commitments to team members
    - Upcoming presentations or deadlines
    - Reports or documents due
    - Financial obligations or invoices
    - Professional development goals
    - Meetings to schedule or cancel

  personal:
    - Health appointments overdue
    - Home maintenance needed
    - Family commitments
    - Financial tasks (taxes, insurance, bills)
    - Personal goals started but stalled
    - Subscriptions to review or cancel

  creative:
    - Ideas captured but not evaluated
    - Content drafted but not published
    - Research started but not synthesized
    - Tools or systems to try

  datacore:
    - DIPs drafted but not finalized
    - Modules started but incomplete
    - Agent improvements identified
    - Knowledge base gaps noticed
    - Engrams that need review
```

**Usage:**
- Weekly review (step 3 — mind sweep): present relevant triggers based on current focus areas
- Inbox processing: suggest triggers when inbox reaches zero (have we captured everything?)
- Customizable: users add domain-specific triggers to the YAML file

### 11.4 Annual Review

A comprehensive yearly review that examines the highest GTD horizons (H3-H5).

**Timing:** Triggered during the December monthly review, or standalone via conversational command.

**Steps:**

1. **Purpose alignment (H5):** Is the vision statement still accurate? Has life direction shifted?
2. **Vision progress (H4):** Review each Intent Graph Level 1 node. Which intents saw meaningful progress? Which stalled?
3. **Goal completion (H3):** For all Level 2-3 nodes with success criteria: what percentage achieved? Which goals need to roll over, revise, or retire?
4. **Project retrospective (H1):** Summary of projects completed, abandoned, and carried over. Key learnings per project.
5. **System assessment:** How well did the GTD system serve this year? What friction points remain? Agent effectiveness trends.
6. **Next-year planning:** Draft Intent Graph adjustments for the coming year. Set 3-5 yearly themes.

**Outputs:**
- `content/reports/YYYY-annual-review.md` — Year-in-review report
- Updated Intent Graph with revised nodes and success criteria
- Annual themes captured as tags in `next_actions.org`

**Sources for compilation:**
- All 12 monthly review summaries
- Journal entries (yearly highlights via journal search)
- Completed Project Canvases
- AI performance dashboard data (Part 17)

### 11.5 Two-Minute Rule

David Allen's two-minute rule: if a task takes less than two minutes to do, do it immediately rather than organizing it.

**Datacore implementation:**

During inbox processing (`gtd-inbox-processor`), if a task meets ALL conditions:
1. Estimated effort is `Quick` (< 30 minutes) — not just 2 minutes, since the rule adapts to the processing context
2. No AI delegation needed (not an `:AI:` task)
3. No external dependencies (not WAITING)
4. Can be done right now (context matches)

Then: mark as `NEXT` with tag `:quick_win:` instead of routing to a focus area deep in `next_actions.org`.

**Visibility:** `/today` briefing shows `:quick_win:` items in a dedicated "Quick Wins" section, encouraging the user to knock them out early.

**Note:** For AI-powered inbox processing, the threshold extends beyond 2 minutes because the "processing overhead" of organizing a task into the system is amortized by the AI. The principle remains: don't over-organize trivially small tasks.

### 11.6 Project Definition Enforcement

Projects without clear definition drift. This section ensures all active projects have minimum structure.

**Detection rules** (checked during weekly review by `gtd-project-manager`):

| Condition | Flag |
|-----------|------|
| Heading in `next_actions.org` with >3 TODO children and no Project Canvas | "Needs Canvas" |
| Project heading with 0 TODO/NEXT children | "Stuck — no next actions" |
| Project heading where all children are DONE but project not marked DONE | "Review for completion" |
| Project heading with no activity for 14 days | "Stale — review needed" |
| Active Project Canvas with no linked tasks in `next_actions.org` | "Canvas orphan" |

**Automated remediation:**
- "Needs Canvas": `gtd-project-manager` creates a Canvas stub pre-populated from existing task context
- "Stuck — no next actions": Surfaces in weekly review for human decision (decompose, defer, or cancel)
- "Review for completion": Prompts user to mark project DONE or identify remaining work
- "Stale": Prompts for reactivation with updated context, deferral to someday, or cancellation

---

## Part 12: Failure Recovery and Re-planning

The current nightshift pipeline marks failures and moves on. This part adds intelligent failure classification and automated re-planning.

### 12.1 Failure Classification

When a task reaches FAILED status, the `failure-analyzer` agent classifies the failure into one of five types:

| Type | Description | Recovery Strategy |
|------|-------------|-------------------|
| `TRANSIENT` | API timeout, rate limit, network error | Retry with exponential backoff (1h → 3h → 6h) |
| `CONTEXT_POOR` | Task lacked sufficient context for quality output | Re-queue with enhanced context via `context-enhancer` |
| `SCOPE_TOO_LARGE` | Task too complex for single execution pass | Decompose into subtasks, re-queue each |
| `SKILL_MISSING` | Task requires capability the agent lacks | Flag for human, suggest engram acquisition |
| `EVALUATION_REJECT` | Output quality below threshold | Analyze evaluator feedback, modify approach, retry once |

### 12.2 Failure Analyzer Agent

**Agent:** `failure-analyzer` (new, in nightshift module)

**Trigger:** Called by nightshift pipeline when a task transitions to FAILED.

**Process:**
1. Parse error output, evaluator comments, and execution logs
2. Classify failure type using the taxonomy above
3. Generate modified task specification for re-queue (if recoverable)
4. Apply localized repair — modify only the affected region of the task specification, not the entire prompt
5. Write classification and recovery plan to task properties

**Properties written:**

| Property | Format | Example |
|----------|--------|---------|
| `:FAILURE_TYPE:` | Enum | `CONTEXT_POOR` |
| `:FAILURE_ANALYSIS:` | Multiline text | What went wrong and why |
| `:RECOVERY_PLAN:` | Multiline text | Specific modifications for retry |

### 12.3 Recovery Protocols

**TRANSIENT recovery:**
- Already implemented: retry with backoff in `ai-task-executor`
- Retry schedule: 1h → 3h → 6h
- Max 3 retries per task per execution cycle

**CONTEXT_POOR recovery:**
1. `context-enhancer` agent rebuilds context:
   - Searches knowledge base for additional relevant files
   - Pulls recent journal entries mentioning the task topic
   - Fetches related engrams
   - Expands `:KEY_FILES:` and `:CURRENT_STATUS:`
2. Re-queue with enhanced context
3. Mark original task with `:NIGHTSHIFT_RETRY: N`

**SCOPE_TOO_LARGE recovery:**
1. `failure-analyzer` identifies logical decomposition points
2. Creates N subtasks from the original task:
   - Each subtask inherits parent's `:CONTEXT:` and `:KEY_FILES:`
   - Each subtask has `:DEPENDS_ON:` referencing parent's `:ID:`
   - Parent task moves to WAITING state
3. Subtasks queued for next execution cycle
4. When all subtasks complete, parent marked DONE with combined output

**SKILL_MISSING recovery:**
1. Flag task for human review
2. Suggest specific engram types that might help (from exchange, if available)
3. Task remains FAILED until human provides guidance or engram is acquired

**EVALUATION_REJECT recovery:**
1. Parse evaluator feedback (which evaluators scored low, why)
2. Identify specific quality dimension that failed (accuracy, completeness, format, etc.)
3. Modify task `:ROLE:` or add `:TOOLS:` hint addressing the feedback
4. Single retry with modified approach
5. If retry also fails evaluation, mark FAILED and flag for human

### 12.4 Safety Constraints

- **Max 1 automatic retry per task per night** (prevents infinite loops)
- **Max 3 total retries** across all nights (prevents persistent waste)
- `:NIGHTSHIFT_RETRY:` counter tracks attempts (0-based)
- Decomposed subtasks count toward parent's retry budget
- SKILL_MISSING never auto-retries (requires human intervention)

**Code changes required:**
- `nightshift/lib/run.py`: After FAILED, call failure-analyzer before processing next task
- `nightshift/lib/queue.py`: Add `retry_count` and `parent_task_id` fields to `QueuedTask`
- New: `nightshift/agents/failure-analyzer.md` agent specification

---

## Part 13: Strategic Prioritization

The current priority formula (`Impact * 0.4 + Urgency * 0.3 + Readiness * 0.2 + Effort * 0.1`) does not account for strategic alignment. This part adds an Intent dimension that connects task prioritization to the Intent Graph.

### 13.1 Enhanced Priority Formula

```
Score = (Impact*0.3 + Urgency*0.2 + Readiness*0.15 + Effort*0.1 + Intent*0.25) * tag_multiplier
```

The new `Intent` factor (0-10 scale):

| Score | Meaning |
|-------|---------|
| 10 | Task directly advances a multi-parent intent node (`[*3]` or higher) |
| 8 | Task advances a multi-parent intent node (`[*2]`) |
| 7 | Task directly advances a single intent |
| 5 | Task is operational/maintenance (supports system health) |
| 3 | Task has no explicit intent linkage but is in an active focus area |
| 0 | Task conflicts with stated intents or has no discernible alignment |

### 13.2 Intent Scoring

The `strategic-prioritizer` agent scores intent alignment by:

1. Reading the `:CONTEXT:` property for explicit intent references
2. If no explicit reference, matching task title and description against Intent Graph nodes via keyword similarity
3. Checking if the task's focus area maps to an intent dimension
4. Detecting multi-parent nodes (highest leverage signal)

### 13.3 Strategic Prioritizer Agent

**Agent:** `strategic-prioritizer` (new, spawned during `/tomorrow` queue-build phase)

**Process:**
1. Read Intent Graph document
2. For each queued task, compute intent alignment score
3. Identify highest-leverage tasks (tasks that unblock the most downstream value)
4. Generate "You should consider" list for human review:
   - High-leverage tasks not yet in queue
   - Intents receiving zero work this cycle
   - Blocked tasks whose blockers could be resolved quickly

**Output:** Priority scores written to `:INTENT_SCORE:` property. Queue builder incorporates into final ordering.

### 13.4 Code Changes

- `nightshift/lib/queue.py`: Update `calculate_priority()` to include `intent_multiplier`
- New: `nightshift/agents/strategic-prioritizer.md` agent specification
- `/tomorrow` command: Invoke strategic-prioritizer after initial queue build, before final ordering

---

## Part 14: Multi-Space GTD and Team Collaboration

DIP-0009 Parts 1-7 implicitly describe single-space GTD. This part specifies how GTD works across Datacore's multi-space architecture and how teams collaborate.

### 14.1 Space Types

| Type | Example | GTD Owner | Task Source | Collaboration Model |
|------|---------|-----------|-------------|---------------------|
| Personal | `0-personal` | Individual | `org/next_actions.org` | Solo |
| Team | `1-datafund` | Team | GitHub Issues + `org/` shadow | GitHub-first |
| System | `2-datacore` | Maintainer | `org/` + GitHub Issues | Hybrid |

### 14.2 Personal Space GTD

The personal space (`0-personal`) follows full GTD methodology as specified in Parts 1-7:
- Direct org-mode access (inbox.org, next_actions.org, someday.org)
- Full property drawer enrichment
- AI delegation via `:AI:` tags processed by nightshift
- All review cycles apply

### 14.3 Team Space GTD

Team spaces (`1-datafund`, etc.) use a **GitHub-first** model:

**Source of truth:** GitHub Issues (not org files)

**Shadow coordination:** `org/next_actions.org` in team spaces is an AI coordination shadow:
- AI agents read/write org files for internal task routing
- Team members work in GitHub Issues exclusively
- DIP-0010 GitHub adapter syncs Issues ↔ org tasks bidirectionally

**Workflow:**
1. Tasks enter via GitHub Issues (created by humans or AI)
2. `org/next_actions.org` receives shadow copies (synced by DIP-0010 adapter)
3. AI processes `:AI:` tagged shadows via nightshift
4. Results posted back to GitHub Issues as comments
5. `@person` tags in org files dispatch to team members via GitHub assignment

**Hard rule:** Team members never need to touch org files directly.

### 14.4 Cross-Space Visibility

Commands aggregate across all spaces:

| Command | Cross-Space Behavior |
|---------|---------------------|
| `/today` | Aggregates agenda items from all spaces |
| Weekly review | Reviews each space sequentially |
| `/tomorrow` | Builds nightshift queue from all spaces |
| Journal | Personal journal always updated; space-specific journals for team work |

### 14.5 Project Canvas as Multi-Player Tool

For team projects, the Project Canvas (Part 10.2) becomes a collaboration instrument:

- **People section** defines roles and responsibilities for each team member
- **Each OKR Key Result has a single owner** (team member)
- Canvas translates into GitHub artifacts:
  - Project → GitHub Milestone
  - Deliverables → GitHub Issues
  - KR owners → GitHub Issue assignees
- `gtd-project-manager` generates GitHub Issues from Canvas, keeps org shadow in sync

### 14.6 Space-Specific Routing

The inbox processor routes tasks to the correct space based on keywords and context:

| Signal | Routing |
|--------|---------|
| Mentions team project (Verity, Datafund) | Team space org/ |
| Personal task (health, trading, family) | Personal space org/ |
| System task (DIP, module, agent) | System space org/ |
| Ambiguous | Personal space (default), surface for review |

Cross-space references use the format: `[space]/org/next_actions.org::heading`

---

## Part 15: Task-Level Integrity

This part specifies monitoring for task-level consistency issues: stuck projects, duplicates, and contradictions.

### 15.1 Stuck Project Detection

A project is "stuck" when it has no clear path forward. Detected during weekly review:

| Condition | Classification | Action |
|-----------|---------------|--------|
| Project heading with 0 TODO/NEXT children | No next actions | Flag for decomposition or cancellation |
| Project with all tasks WAITING | Fully blocked | Surface blockers for review |
| Project with no state changes for 14 days | Stale | Prompt for reactivation or deferral |
| Project with >50% tasks FAILED | Struggling | Trigger failure analysis (Part 12) |

The `structural-integrity` agent (currently filesystem-only) is extended to include task-level checks.

### 15.2 Duplicate Detection

Before creating new tasks, check for semantic similarity against existing tasks:

**When:** During inbox processing and task creation
**How:** Compare task title + description against existing tasks in same focus area
**Threshold:** Flag if similarity > 80% (title match) or > 60% (title + description match)

**Nightshift dedup:** Prevent the same task from executing multiple times:
- Before execution, check if an identical task (same title, same focus area) was executed in the last 7 days
- If duplicate found, skip with note: "Skipped — duplicate of task executed on YYYY-MM-DD"
- This addresses the observed bug where recurring tasks could queue multiple instances

### 15.3 Contradiction Detection

Three types of contradictions to monitor:

**Task output vs. existing knowledge:**
- After nightshift execution, evaluators check if output contradicts established knowledge in `3-knowledge/`
- Contradictions flagged in evaluator feedback, not auto-resolved

**Conflicting task goals:**
- Two active tasks in the same focus area with opposing objectives
- Detected by keyword analysis during weekly review
- Surfaced as review item: "These tasks may conflict — please review"

**Engram contradictions:**
- New engram contradicts existing active engram
- Handled by `learning-reviewer` agent (DIP-0019)
- Cross-referenced here for completeness

### 15.4 Integrity Dashboard

Weekly review includes an integrity summary:

```
Task Integrity Report
─────────────────────
Stuck projects:        2 (Verity CI/CD, Newsletter automation)
Stale tasks (>14d):    5
Potential duplicates:  1
WAITING >7 days:       3
FAILED (unreviewed):   1
```

---

## Part 16: Event-Driven Reactions (Architecture Stub)

**Status:** Architecture specification only. Implementation deferred to future DIP.

### 16.1 Motivation

Nightshift operates on a batch model (timer-triggered, processes queue). Some scenarios require faster reaction:

| Event | Desired Reaction | Current Gap |
|-------|------------------|-------------|
| CI pipeline failure | Spawn fix agent | Wait until next nightshift cycle |
| GitHub review comment | Generate response draft | Wait for human or next cycle |
| Price alert trigger | Trading reaction | Handled by separate redalert service |
| Urgent email classified | Surface immediately | Wait for next `/today` briefing |
| Nightshift task output ready | Notify user | User checks in morning |

### 16.2 Proposed Architecture

```
Event Source              Webhook/Watcher          Dispatcher         Agent
────────────              ───────────────          ──────────         ─────
GitHub Actions  ─────┐
GitHub Comments ─────┤
Email (IMAP)   ─────┼──→  Event Receiver  ──→  Priority Filter ──→ Agent Pool
Price Feeds    ─────┤        (webhook          (urgent? batch?      (same agents
Cron triggers  ─────┘         endpoint)          context?)           as nightshift)
```

**Priority Filter** determines routing:
- **Urgent** (< 5 min SLA): Execute immediately via on-demand agent
- **Soon** (< 1 hour): Add to hot queue, process at next opportunity
- **Batch** (default): Add to nightshift queue, process on schedule

### 16.3 Extension Points

Current system provides hooks for future event-driven execution:

| Hook | Location | Status |
|------|----------|--------|
| GitHub webhooks | DIP-0010 adapter | Specified, not implemented |
| Mail IMAP IDLE | Mail module | Possible via IMAP push |
| Price alerts | `redalert.service` | Running independently |
| Nightshift completion | Post-execution hook | Could trigger notification |

### 16.4 Non-Goals (This Version)

- No always-on daemon (nightshift remains timer-based)
- No real-time event bus (overengineered for current scale)
- No automatic agent spawning without human-defined rules
- No changes to existing nightshift batch model

The batch model (nightshift timers) continues as the primary execution mode. Event-driven reactions layer on top as optional acceleration.

---

## Part 17: AI Task Performance Tracking

This part specifies comprehensive tracking of speed, quality, and costs for all AI task execution. Uses org-mode CLOCK entries (Part 8.2) plus custom properties for metrics.

### 17.1 Speed Tracking

Three time metrics per task:

| Metric | Source | Format |
|--------|--------|--------|
| **Wall time** | CLOCK entry duration | `H:MM` (start to completion, includes API waits) |
| **Estimated effort** | `:Effort:` property | Categorical or `H:MM` |
| **Accuracy ratio** | `actual / estimated` | Decimal (1.0 = perfect estimate) |

**Aggregation** (computed during weekly review):
- Average duration by `:AI:` tag type (research vs content vs data vs pm)
- Effort estimation accuracy trend (are estimates improving over time?)
- Throughput: tasks completed per night, per week

### 17.2 Quality Tracking

**Existing metric:** `:NIGHTSHIFT_SCORE:` (0.000-1.000 scale, evaluator consensus)

**New aggregate metrics:**

| Metric | Computation | Purpose |
|--------|-------------|---------|
| Quality by task type | Average `:NIGHTSHIFT_SCORE:` per `:AI:` tag | Identify weak spots |
| Quality trend | Score moving average (4-week window) | Is quality improving? |
| Evaluator agreement | Score variance across evaluators | Low = clear quality, high = ambiguous |
| Human override rate | `overrides / total_evaluated` | How often user disagrees with evaluators |
| First-pass success rate | `approved_first_try / total` | % passing evaluation without retry |

### 17.3 Cost Tracking

Properties written by nightshift pipeline after execution (specified in Part 8.5):

| Property | Source | Example |
|----------|--------|---------|
| `:NIGHTSHIFT_COST:` | Sum of API call costs | `0.42` (USD) |
| `:NIGHTSHIFT_TOKENS:` | Total tokens (input + output) | `45000` |

**Cost computation requires:**
1. Token counting from API responses (available in Anthropic SDK response metadata)
2. Price lookup table in nightshift config:
   ```yaml
   # .datacore/modules/nightshift/config.yaml
   cost_per_1k_tokens:
     claude-sonnet-4-20250514:
       input: 0.003
       output: 0.015
     claude-opus-4-20250514:
       input: 0.015
       output: 0.075
   ```
3. Per-task cost = sum of all agent calls (executor + evaluators + failure-analyzer if applicable)

### 17.4 Performance Dashboard

Weekly review generates a performance summary:

```
AI Performance — Week of 2026-02-17
────────────────────────────────────
| Metric                  | This Week | Last Week | Trend |
|-------------------------|-----------|-----------|-------|
| Tasks completed         | 14        | 11        | +27%  |
| Avg duration (min)      | 23        | 31        | -26%  |
| Avg quality score       | 0.82      | 0.79      | +4%   |
| First-pass success rate | 71%       | 64%       | +7%   |
| Total cost              | $4.20     | $5.80     | -28%  |
| Cost per task           | $0.30     | $0.53     | -43%  |
| Effort accuracy         | 0.85      | 0.72      | +18%  |
```

**Data source:** CLOCK entries + NIGHTSHIFT_* properties from completed and archived tasks.

**Storage:** `org/performance/YYYY-MM.yaml` — monthly aggregates for historical analysis:

```yaml
# org/performance/2026-02.yaml
month: 2026-02
weeks:
  - week_of: 2026-02-03
    tasks_completed: 11
    avg_duration_min: 31
    avg_quality_score: 0.79
    first_pass_rate: 0.64
    total_cost_usd: 5.80
    cost_per_task_usd: 0.53
    effort_accuracy: 0.72
    by_type:
      research: { count: 4, avg_score: 0.81, avg_cost: 0.65 }
      content: { count: 3, avg_score: 0.75, avg_cost: 0.40 }
      pm: { count: 2, avg_score: 0.82, avg_cost: 0.35 }
      data: { count: 2, avg_score: 0.78, avg_cost: 0.55 }
```

### 17.5 Budget Tracking

Monthly AI spend tracked against budget:

```yaml
# .datacore/modules/nightshift/config.yaml
budget:
  monthly_usd: 50.00  # Monthly spending limit
  alert_threshold: 0.80  # Alert at 80% of budget
```

- `/today` shows current month spend vs budget
- Alert in daily briefing when approaching threshold
- Nightshift respects budget: pauses non-critical tasks when budget exceeded
- Critical tasks (`:AI:pm:` with `[#A]` priority) execute regardless of budget

### 17.6 Implementation

**Code changes to nightshift pipeline:**
- `nightshift/lib/run.py`: After task execution, write duration + token count + cost to org properties and CLOCK entry
- `nightshift/lib/evaluate.py`: Record evaluator-level metrics (individual scores, variance)
- New: `nightshift/lib/metrics.py` — aggregation functions for dashboard generation:
  - `compute_weekly_metrics(data_dir, week_start)` → metrics dict
  - `update_monthly_file(data_dir, metrics)` → writes YAML
  - `generate_dashboard(data_dir)` → formatted table string
- Parser: `org_parser.py` needs `write_clock_entry()` (Part 8.2) + cost property writing

---

## Part 18: Metacognitive Planning (Architecture Stub)

**Status:** Architecture specification only. Implementation builds on DIP-0019 (Learning Architecture).

### 18.1 Three Metacognitive Components

Research on metacognition identifies three components, each mapped to Datacore:

| Component | Definition | Datacore Mapping | Status |
|-----------|-----------|------------------|--------|
| Metacognitive Knowledge | Understanding of what the agent knows/doesn't know | DIP-0019 engrams | Implemented |
| Metacognitive Planning | Identifying skill gaps and planning acquisition | Agent identifies gaps → searches exchange | Future |
| Metacognitive Evaluation | Evaluating whether learning was useful | Engram fitness scoring → activation decay | Designed (DIP-0019) |

### 18.2 Self-Evolving Prompts

High-fitness engrams should modify agent behavior over time:

**Mechanism (specified in DIP-0019, not yet wired):**
1. Engrams with activation score > threshold are selected by `engram_selector.py`
2. Selected engrams are injected into agent system prompts via `engram-inject` skill
3. Agent behavior evolves as engram corpus changes
4. Poor-performing engrams decay and are eventually retired

**Integration point:** `nightshift/lib/execute.py` already calls `select_engrams()` and passes results to `build_task_prompt()`. The wiring exists; what is needed is:
- Engram fitness scoring running consistently (learning-reviewer agent)
- Activation decay applied during daily review
- Exchange protocol for acquiring new engrams from other installations

### 18.3 Continuous Context Reset

Nightshift's implicit pattern — fresh agent per task with structured memory channels — is a metacognitive architecture decision:

**Memory channels available to each fresh agent:**
1. **Task specification** — Rich Task Standard properties (explicit, per-task)
2. **Engrams** — Learned patterns injected at runtime (implicit, cross-task)
3. **Knowledge base** — Files discovered by context-enhancer (explicit, per-task)
4. **Evaluator feedback** — From previous attempts of same task (explicit, per-retry)

**Why fresh context matters:**
- Prevents context pollution between unrelated tasks
- Ensures each task gets a clean cognitive slate
- Engrams provide cross-task learning without cross-task contamination
- Failed task retries get focused feedback, not accumulated confusion

### 18.4 Future: Agent Skill Gap Detection

When the failure-analyzer (Part 12) classifies a failure as `SKILL_MISSING`:

1. Agent identifies the specific capability gap (e.g., "cannot generate Solidity code", "lacks knowledge of SemantiCord schema")
2. Searches engram exchange for relevant published engrams
3. Proposes acquisition to user: "Engram ENG-042 'Solidity best practices' (fitness: 0.89) may help with this task type. Acquire?"
4. If acquired, engram enters 30-day trial (per DIP-0019 exchange protocol)
5. Learning-reviewer tracks whether acquired engram improves task success rate

### 18.5 Non-Goals (This Version)

- No autonomous engram purchasing (user approval required)
- No agent self-modification beyond engram injection
- No prompt evolution without engram-based justification
- No metacognitive planning for human tasks (AI tasks only)

---

## Part 19: Personal Task Management Lifecycle

This part specifies how a human interacts with Datacore's GTD system day-to-day — the command lifecycle, interaction model, wellbeing integration, and module coordination.

### 19.1 Daily Command Lifecycle

Four commands form the daily rhythm. Each is a **command** (DIP-0022 layer 4: interactive, human-in-the-loop):

```
Morning                    Day                     Evening
┌──────────┐    ┌─────────────────────┐    ┌───────────┐    ┌────────────┐
│  /today   │ →  │  Work + /continue   │ →  │  /wrap-up  │ →  │ /tomorrow  │
│  briefing │    │  conversational     │    │  capture   │    │ delegation │
└──────────┘    └─────────────────────┘    └───────────┘    └────────────┘
     │                    │                       │                │
     ▼                    ▼                       ▼                ▼
 Vitals sync        Task execution         Learning capture   AI queue build
 Priority set       Inbox triage           Journal update     Recurring tasks
 Calendar pull      Module workflows       Task extraction    Commit + push
```

**`/today`** — Morning briefing (command spec: `.datacore/commands/today.md`)
- Syncs repos and external data (Oura, calendar, news)
- Generates prioritized task list adjusted for vitals/readiness
- Shows overdue DEADLINEs (Part 8.1), yesterday's wins, upcoming calendar
- Surfaces knowledge nuggets (spaced repetition) and Data's Observation

**`/continue`** — Mid-session resume (command spec: `.datacore/commands/continue.md`)
- Two modes: Resume (find `:continuation:` tasks) and Save (`--save` for clean exit)
- Prioritizes by `Impact × 0.6 + Ease × 0.4` for suggested next actions
- Provides bootstrap prompts for task context restoration

**`/wrap-up`** — Session close (command spec: `.datacore/commands/wrap-up.md`)
- 12-step sequence: summarize, extract learnings, extract GTD tasks, update journal
- Step 5c: GTD Task Extraction routes new tasks via intent graph (Part 9) — each extracted task gets `:CONTEXT:` property with intent path
- Engram candidate generation via learning pipeline (DIP-0019)
- Insight Verification Checklist ensures nothing is lost across 4 capture layers

**`/tomorrow`** — End-of-day delegation (command spec: `.datacore/commands/tomorrow.md`)
- Processes inbox status, runs diagnostics, creates recurring task instances (Part 3.6)
- Builds nightshift queue: moves `:AI:` tasks from `next_actions.org` → `nightshift.org`
- Displays queue with optimization preview and cost estimate
- Commits and pushes for overnight execution

### 19.2 Interaction Model

Between commands, Datacore operates as a **conversational assistant**. The user talks naturally; the system routes to the right capability layer:

| User Says | Routes To | Layer |
|-----------|-----------|-------|
| "What's on my plate?" | `gtd.agenda_view` (today_priorities) | MCP Tool |
| "Process my inbox" | `gtd-inbox-coordinator` | Agent |
| "Check my email" | `/mails` command | Command |
| "Plan the verity launch" | `gtd-project-manager` + `project-canvas` skill | Agent + Skill |
| "How am I doing this week?" | `user-analytics-generator` | Agent |
| "What's my readiness?" | `health.fetch_vitals` | MCP Tool |
| "Schedule my trading review" | Calendar integration (DIP-0010) | MCP Tool |

**Conversational triggers** are defined per module in `module.yaml` (DIP-0022 section 3.2). The GTD module's core triggers are listed in CLAUDE.md's "Conversational" table. No slash command needed — natural language intent maps to capabilities.

### 19.3 Wellbeing Integration

Wellbeing data from two sources feeds into task prioritization and daily planning:

1. **Oura API** — real-time vitals (readiness, sleep, HRV, activity)
2. **Health Dashboard** — computed domain scores, alerts, and focus area detection

**Reference:** Health Dashboard V2 Specification (`2-datacore/2-projects/datacore-health/specs/dashboard-v2-specification.md`)

#### 19.3.1 Data Sources

**MCP Tool: `health.fetch_vitals`** — Pulls readiness, sleep, activity scores from Oura API v2. Stateless, returns structured data. This is the primary real-time source, synced each morning via `/today` hook.

**MCP Tool: `health.fetch_domain_scores`** — Pulls the four computed domain scores from the health dashboard API (`/api/summary`). These scores aggregate multiple data sources into a 0-100 composite:

| Domain | Weight | Primary Metrics | Data Sources |
|--------|--------|----------------|--------------|
| Cardio | 30% | RHR, HRV, VO2max, BP, lipids | Oura, Apple Watch, labs |
| Metabolic | 25% | HbA1c, glucose, body comp, weight trend | Labs, Withings, manual |
| Physical | 25% | VO2max, activity, strength, workouts | Apple Watch, manual |
| Cognitive | 20% | Sleep quality, HRV, activity, consistency | Oura, Apple Watch |

Scoring algorithms are defined in the dashboard V2 spec (Part 5).

**MCP Tool: `health.fetch_alerts`** — Pulls active health alerts from dashboard (`/api/alerts`). Alert types:
- Missing data (e.g., "ApoB not tested in 2+ years")
- Declining trends (e.g., "HRV down 15% over 2 weeks")
- Out-of-range values (e.g., "LDL above optimal zone")
- Goal progress (e.g., "muscle mass goal behind pace")
- Reminders (e.g., "annual bloodwork due")

#### 19.3.2 Workload Adjustment

**MCP Tool: `health.workload_map`** — Deterministic lookup combining Oura readiness with domain scores:

| Readiness | Deep Work Hours | Workout | Meeting Tolerance | Priority Adjustment |
|-----------|----------------|---------|-------------------|-------------------|
| 85+ | 4-6h | Full intensity | Normal | No change |
| 70-84 | 3-4h | Moderate | Limit to 3 | Deprioritize Tier 3 |
| 55-69 | 1-2h | Light/recovery | Limit to 2 | Only Tier 1 tasks |
| <55 | Rest day | None | Cancel if possible | Only critical items |

**Domain score modifiers** (applied on top of readiness):
- Cardio score < 60 → flag "recovery needed" in `/today`, suggest lighter day
- Cognitive score < 50 → reduce deep work estimate by 1h
- Any critical health alert → surface prominently in `/today` briefing header

#### 19.3.3 Dashboard Widgets in GTD Context

The health dashboard exposes widgets that directly feed GTD workflows. Key widgets and their GTD integration:

| Widget | Dashboard Page | GTD Integration |
|--------|---------------|-----------------|
| `readiness-summary` | Today | Drives workload map (19.3.2) |
| `wellbeing-summary` | Dashboard | Composite view in `/today` Health section |
| `domain-scores-row` | Dashboard | 4-domain health status in `/today` |
| `detected-issues` | Focus | Health alerts → task creation in `inbox.org` |
| `goal-progress` | Focus | Health goal tracking alongside GTD goals |
| `training-recommendation` | Today | Readiness-adjusted workout in `/today` |
| `protocol-checklist` | Today | Morning/evening routine tracking |
| `alerts-panel` | Dashboard | Critical alerts surface in `/today` header |
| `hrv-recovery-card` | Cardio | Recovery status feeds workload adjustment |
| `pattern-detector` | Data | Correlations feed weekly analytics (Part 21) |

**Task generation from dashboard:** When the dashboard detects actionable issues (data gaps, declining trends, overdue screenings), it creates tasks in `inbox.org` with `:SOURCE: health-dashboard`. These flow through the standard inbox pipeline (Part 20) with intent routing to the health focus area.

#### 19.3.4 Integration Point

`/today` calls three health tools in sequence:
1. `health.fetch_vitals` → Oura readiness, sleep, HRV
2. `health.fetch_domain_scores` → 4 domain scores (0-100)
3. `health.fetch_alerts` → active health alerts

Then applies `health.workload_map` + domain score modifiers to adjust the briefing's Priority Tasks section. The workload map is a tool (deterministic); the priority adjustment is part of the `/today` command logic (requires judgment about which specific tasks to defer).

**Weekly review** additionally pulls `pattern-detector` and `correlation-heatmap` data to surface health-productivity correlations (e.g., "weeks with >7h sleep average had 23% higher task completion").

### 19.4 Module Integration Points

The GTD lifecycle coordinates with domain modules at defined hook points:

| Module | Hook Point | Integration |
|--------|-----------|-------------|
| **mail** | `/mails` or inbox processing | Emails → `inbox.org` tasks with `:EXTERNAL_URL:` (Part 20) |
| **meetings** | `/today` calendar section | Google Calendar events shown in briefing |
| **meetings** | `prep-for-meeting` | Context preparation triggered before calendar events |
| **health** | `/today` vitals section | Oura readiness + domain scores + alerts → workload adjustment (19.3) |
| **health** | Dashboard task generation | Health alerts → `inbox.org` tasks with `:SOURCE: health-dashboard` |
| **health** | Weekly review | Health-productivity correlations via `pattern-detector` |
| **trading** | `/start-trading` | Morning check-in with emotional state, market context |
| **news** | `/today` news section | AI-scored news digest in morning briefing |
| **crm** | `/today` CRM section | Relationship follow-up reminders |
| **nightshift** | `/tomorrow` queue section | AI task delegation and queue building |
| **research** | `:AI:research:` routing | Research tasks queued via `/tomorrow` |

Each module registers its hooks in `module.yaml` under `hooks.commands` (DIP-0022 section 3.3).

---

## Part 20: Inbox Processing Pipeline

This part specifies the unified inbox processing system — how items from multiple sources enter, get classified, routed, and become actionable tasks.

### 20.1 Inbox Sources

Tasks enter `inbox.org` from multiple sources:

| Source | Generator | `:SOURCE:` Value | Frequency |
|--------|-----------|-----------------|-----------|
| Manual capture | User (direct edit or conversational) | `manual` | On demand |
| Email | Mail module (`/mails` command) | `email` | On demand or scheduled |
| Wrap-up extraction | `/wrap-up` step 5c | `session` | End of each session |
| Nightshift output | AI task completion requiring follow-up | `nightshift` | Overnight |
| Meeting notes | Transcription processor | `meeting` | After meetings |
| GitHub notifications | External sync (DIP-0010) | `github` | Continuous |
| Calendar events | Calendar adapter | `calendar` | Sync intervals |

Each source writes tasks to `inbox.org` with at minimum: heading, `:CREATED:`, `:SOURCE:`, and relevant `:EXTERNAL_URL:` or `:EXTERNAL_ID:`.

### 20.2 Mail-to-Task Conversion

The mail module (`.datacore/modules/mail/`) converts emails to inbox tasks:

```
Gmail API → mail-classifier (agent) → Classification
                                          │
                     ┌────────────────────┼─────────────────┐
                     ▼                    ▼                  ▼
              ACTIONABLE            INFORMATIONAL        IGNORE/SPAM
                     │                    │                  │
                     ▼                    ▼                  ▼
           Create inbox.org task    Research/reference    Auto-archive
           with :EXTERNAL_URL:      note creation
```

**Task creation from email:**

```org
** TODO Reply to [Sender] re: [Subject] :email:
:PROPERTIES:
:CREATED: [2026-02-22 Sat 10:00]
:SOURCE: email
:EXTERNAL_ID: gmail:19b09952c4d344a1
:EXTERNAL_URL: https://mail.google.com/mail/u/0/#inbox/19b09952c4d344a1
:Effort: Quick
:END:
[Brief context from email body — max 2 sentences]
```

**Classification approach** (conservative — per mail module spec):
- Only auto-archive explicit spam rules + GitHub CI notifications
- ACTIONABLE emails require user decision on action type
- CRM integration: contact notes created for relationship tracking

### 20.3 Processing Workflow

Inbox processing follows a **workflow** (DIP-0022 layer 5: multi-phase orchestration):

```yaml
workflow: inbox-processing-pipeline
phases:
  - name: inventory
    type: tool
    tool: gtd.inbox_count
    description: Count and categorize inbox entries by source

  - name: classify
    type: agent
    agent: gtd-inbox-coordinator
    skills: [gtd-triage, intent-routing]
    description: Spawn processors per entry, classify and route

  - name: dedup
    type: tool
    tool: gtd.duplicate_check
    description: Check new tasks against existing for duplicates

  - name: approve
    type: human
    description: User reviews routing decisions, resolves duplicates

  - name: route
    type: tool
    tool: org_parser.route_tasks
    description: Move approved tasks to next_actions.org under correct focus area

  - name: cleanup
    type: tool
    tool: org_parser.clear_processed
    description: Remove processed entries from inbox.org
```

### 20.4 Intent-Based Routing

When `gtd-inbox-processor` classifies a task, it applies intent routing using the `intent-routing` **skill** (DIP-0022 layer 2: knowledge injection):

**Routing algorithm:**
1. Extract task keywords and context
2. Score against Intent Graph nodes (Part 9) using `gtd.intent_score` tool
3. Select highest-scoring intent path as `:CONTEXT:` value
4. Map intent → focus area in `next_actions.org`:

| Intent Dimension | Maps To Focus Area |
|-----------------|-------------------|
| Product | Technology / Product development |
| Operations | Operations / Infrastructure |
| Sustainability | Business / Finance |
| Experience | Marketing / Community |
| Ecosystem | Partnerships / Ecosystem |

5. If no intent scores above threshold (0.3): route to general inbox review
6. If multiple intents score similarly: flag for human decision

**Wrap-up routing:** Step 5c of `/wrap-up` generates tasks from session insights. These tasks MUST pass through intent routing before placement — they go to `inbox.org` first, then are processed through this pipeline (either immediately or deferred to `/tomorrow`).

### 20.5 Two-Minute Rule Integration

During inbox processing (per Part 11.5):

1. `gtd-inbox-processor` estimates effort for each task
2. If estimated effort < 2 minutes AND task doesn't require AI delegation:
   - Tag with `:quick_win:`
   - Surface in `/today` briefing's quick-wins section
   - User can execute immediately rather than routing to next_actions
3. Quick-win items that aren't executed within 24 hours lose the tag and route normally

### 20.6 Duplicate Detection

Before routing, new tasks are checked against existing tasks using `gtd.duplicate_check` (MCP tool):

**Similarity thresholds:**
- Title similarity > 80% → flag as potential duplicate
- Title > 60% AND description > 60% → flag as potential duplicate
- Same `:EXTERNAL_ID:` → auto-deduplicate (identical source)

**Resolution options** (presented to user during approve phase):
- **Merge**: Combine into existing task (add context from new entry)
- **Keep both**: Distinct tasks despite similarity
- **Discard new**: New entry is duplicate, remove
- **Replace**: New entry supersedes existing

---

## Part 21: User Analytics and Capability Model

### 21.1 User Analytics

An **agent** (`user-analytics-generator`) produces insights about the user's task patterns, time allocation, and focus area health. Generated during weekly and monthly reviews.

**Data sources:**
- CLOCK entries (Part 8.2) for time allocation
- Task state transitions for completion patterns
- `:Effort:` estimates vs actuals for accuracy tracking
- Intent Graph alignment scores for strategic coherence
- DONE/CANCELLED ratio for decision quality
- Focus area task counts for workload distribution

**Weekly analytics output:**

| Metric | Computation | Insight |
|--------|-------------|---------|
| Time by focus area | Sum CLOCK entries grouped by parent heading | Where time actually goes vs intent |
| Completion rate | DONE / (DONE + CANCELLED + active) per week | Throughput trend |
| Effort accuracy | Avg(actual_duration / estimated_effort) | Are estimates improving? |
| Focus area gaps | Intent Graph areas with 0 tasks in 2+ weeks | Strategic blind spots |
| Quick-win ratio | Quick tasks / total tasks completed | Tactical vs strategic balance |
| Delegation rate | `:AI:` tasks / total tasks | AI leverage utilization |

**Monthly analytics additions:**
- Horizon coverage check (Part 10): are all 6 levels populated?
- Intent alignment drift: how far has actual work deviated from stated intents?
- Stale focus areas: areas with no new tasks in 30+ days
- Suggested adjustments: concrete recommendations for rebalancing

**Storage:** `org/analytics/YYYY-MM.yaml` (monthly aggregates for historical comparison).

### 21.2 Five-Layer Capability Model

All GTD capabilities in this DIP decompose into DIP-0022's five layers. This table serves as the implementation registry — every capability has exactly one home layer.

**MCP Tools** (stateless, deterministic):

| Tool | Module | Purpose |
|------|--------|---------|
| `gtd.agenda_view` | gtd | Custom agenda queries with filters (Part 8.6) |
| `gtd.inbox_count` | gtd | Count inbox entries by source |
| `gtd.deadline_warnings` | gtd | Tasks within N days of DEADLINE |
| `gtd.archive_tasks` | gtd | Move old DONE/FAILED tasks to archive files |
| `gtd.write_clock_entry` | gtd | Write CLOCK start/end to LOGBOOK drawer |
| `gtd.duplicate_check` | gtd | Similarity comparison against existing tasks |
| `gtd.project_health` | gtd | Stuck/stale/blocked project detection |
| `gtd.effort_aggregate` | gtd | Sum effort and CLOCK by heading tree |
| `nightshift.task_metrics` | nightshift | Speed/quality/cost aggregates from properties |
| `nightshift.intent_score` | nightshift | Score task alignment against Intent Graph |
| `health.fetch_vitals` | health | Pull Oura readiness/sleep/activity |
| `health.fetch_domain_scores` | health | Pull 4 domain scores from dashboard API |
| `health.fetch_alerts` | health | Pull active health alerts from dashboard |
| `health.workload_map` | health | Readiness + domain scores → workload parameters |

**Skills** (knowledge injection via SKILL.md):

| Skill | Module | Injects |
|-------|--------|---------|
| `gtd-triage` | gtd | Inbox classification methodology, routing rules |
| `gtd-natural-planning` | gtd | Five-phase project planning model (Part 11.1) |
| `gtd-trigger-lists` | gtd | Capture prompts by life area (Part 11.3) |
| `gtd-horizons` | gtd | Horizons of Focus mapping, review checklists |
| `intent-routing` | gtd | Intent Graph structure + task→intent alignment rules |
| `project-canvas` | gtd | Canvas template methodology + OKR framework |

**Agents** (complex multi-step reasoning):

| Agent | Module | Trigger |
|-------|--------|---------|
| `strategic-prioritizer` | nightshift | Queue build time (`/tomorrow`) |
| `failure-analyzer` | nightshift | Task FAILED state in pipeline |
| `user-analytics-generator` | gtd | Weekly/monthly review |
| `gtd-inbox-processor` | gtd | Per-entry inbox processing (enhanced with skills) |
| `gtd-inbox-coordinator` | gtd | Batch inbox orchestration |
| `workload-adjuster` | health | `/today` vitals → priority adjustment |

**Commands** (interactive, human-in-the-loop):

| Command | Module | Lifecycle Phase |
|---------|--------|----------------|
| `/today` | core | Morning briefing |
| `/continue` | core | Mid-session resume |
| `/wrap-up` | core | Session close |
| `/tomorrow` | core | End-of-day delegation |
| `/mails` | mail | Email processing (feeds inbox pipeline) |
| Annual review | core | Yearly strategic review (Part 11.4) |

**Workflows** (multi-phase orchestrations):

| Workflow | Phases | Trigger |
|----------|--------|---------|
| Daily lifecycle | `/today` → work → `/wrap-up` → `/tomorrow` | Daily rhythm |
| Inbox processing pipeline | inventory → classify → dedup → approve → route → cleanup | On demand or `/tomorrow` |
| Weekly review | Existing 12 steps + project health + analytics + archiving | Weekly |
| Mail-to-task pipeline | classify → auto-archive → present → create tasks → inbox pipeline | `/mails` |

### 21.3 Implementation Requirements Summary

All capabilities required for this DIP to be fully active:

| Requirement | Layer | Status | Dependencies |
|-------------|-------|--------|-------------|
| `gtd.agenda_view` tool | MCP Tool | New | `org_parser.py` query methods |
| `gtd.duplicate_check` tool | MCP Tool | New | Text similarity library |
| `gtd.write_clock_entry` tool | MCP Tool | New | `org_parser.py` LOGBOOK methods |
| `gtd.archive_tasks` tool | MCP Tool | New | `org_parser.py` archive methods |
| `gtd.deadline_warnings` tool | MCP Tool | New | `org_parser.py` DEADLINE parsing |
| `nightshift.intent_score` tool | MCP Tool | New | Intent Graph parser |
| `nightshift.task_metrics` tool | MCP Tool | New | Property aggregation |
| `gtd-triage` skill | Skill | New | `.datacore/specs/trigger-lists.yaml` |
| `intent-routing` skill | Skill | New | Intent Graph document |
| `project-canvas` skill | Skill | New | Canvas template zettel |
| `strategic-prioritizer` agent | Agent | New | `intent_score` tool |
| `failure-analyzer` agent | Agent | New | Failure classification taxonomy |
| `user-analytics-generator` agent | Agent | New | `task_metrics` + `effort_aggregate` tools |
| `gtd-inbox-processor` enhancement | Agent | Update | `gtd-triage` + `intent-routing` skills |
| `/today` DEADLINE section | Command | Update | `deadline_warnings` tool |
| `/today` vitals adjustment | Command | Update | `health.workload_map` + `fetch_domain_scores` + `fetch_alerts` tools |
| `health.fetch_domain_scores` tool | MCP Tool | New | Health dashboard API (`/api/summary`) |
| `health.fetch_alerts` tool | MCP Tool | New | Health dashboard API (`/api/alerts`) |
| `/wrap-up` intent routing | Command | Update | `intent-routing` skill |
| `/tomorrow` intent-scored queue | Command | Update | `intent_score` tool |
| Inbox processing pipeline | Workflow | New | Multiple tools + agents |
| `.datacore/specs/trigger-lists.yaml` | Config | New | — |
| `org/analytics/YYYY-MM.yaml` | Storage | New | `user-analytics-generator` agent |
| `org/performance/YYYY-MM.yaml` | Storage | New | `nightshift.task_metrics` tool (Part 17) |

---

## Implementation

### Phase 1: Documentation (Current)
- Finalize this DIP (Parts 1-21)
- Archive gtd-spec.md (superseded)
- Update CLAUDE.md references

### Phase 2: Agent Compliance
- Audit existing agents against spec
- Add missing state validations
- Standardize logging format

### Phase 3: Module System
- Implement module registration
- Extract optional components to modules
- Document module creation guide

### Phase 4: External Sync (DIP-0010)
- Implement GitHub adapter
- Add Calendar read support
- Build sync engine

### Phase 5: Org-Mode Extensions (Part 8)
- Add `write_clock_entry()` to `org_parser.py`
- Add `archive_task()` to `org_parser.py`
- Implement DEADLINE warning in `/today` briefing
- Implement auto-archiving in weekly review

### Phase 6: Strategy Layer (Parts 9-10)
- Formalize Intent Graph review protocol in weekly/monthly commands
- Implement Project Canvas stub generation in `gtd-project-manager`
- Add horizon coverage check to weekly review

### Phase 7: GTD Completeness (Part 11)
- Create `.datacore/specs/trigger-lists.yaml`
- Enhance `gtd-inbox-processor` with two-minute rule
- Add Natural Planning to `gtd-project-manager`
- Implement Someday/Maybe AI-assisted curation
- Build annual review command

### Phase 8: Autonomous Execution (Parts 12-13)
- Create `failure-analyzer` agent
- Implement failure classification and recovery protocols
- Create `strategic-prioritizer` agent
- Update `calculate_priority()` with intent multiplier

### Phase 9: Collaboration + Integrity (Parts 14-15)
- Implement cross-space task aggregation in `/today`
- Extend `structural-integrity` for task-level checks
- Add duplicate detection to inbox processor
- Build integrity dashboard for weekly review

### Phase 10: Performance Tracking (Part 17)
- Add cost/token recording to nightshift pipeline
- Create `nightshift/lib/metrics.py`
- Implement performance dashboard generation
- Add budget tracking and alerts

### Phase 11: GTD MCP Tools (Parts 8, 20, 21)
- Implement `gtd.agenda_view` tool with filter API
- Implement `gtd.duplicate_check`, `gtd.deadline_warnings`
- Implement `gtd.write_clock_entry`, `gtd.archive_tasks`
- Implement `nightshift.intent_score`, `nightshift.task_metrics`

### Phase 12: Skills and Inbox Pipeline (Parts 19-20)
- Create `gtd-triage` skill (inbox classification methodology)
- Create `intent-routing` skill (Intent Graph → focus area mapping)
- Create `project-canvas` skill (template + OKR methodology)
- Build inbox processing pipeline workflow
- Enhance `gtd-inbox-processor` with triage + intent-routing skills
- Update `/wrap-up` step 5c to route via intent graph

### Phase 13: Analytics and Lifecycle (Part 21)
- Create `user-analytics-generator` agent
- Add analytics generation to weekly/monthly review
- Update `/today` with DEADLINE warnings and vitals-adjusted priorities
- Update `/tomorrow` with intent-scored queue display
- Create `.datacore/specs/trigger-lists.yaml`

### Phase 14: Future Work (Parts 16, 18)
- Event-driven reactions: deferred to future DIP
- Metacognitive planning: wire engram injection, implement skill gap detection

---

## Rationale

GTD was chosen over alternative task management methodologies (Kanban, Scrum, custom) because:

1. **Proven methodology** — GTD is well-documented with clear rules, reducing ambiguity for AI agents
2. **Org-mode alignment** — org-mode's heading hierarchy maps naturally to GTD's project/action structure
3. **Review cycles** — GTD's weekly review provides a natural checkpoint for AI delegation quality
4. **Capture-first design** — GTD's inbox-zero principle enables clean agent handoffs

Alternative designs considered:
- **Pure Kanban** — rejected because columns don't map well to multi-agent routing
- **GitHub Issues as primary** — rejected because org-mode allows richer local processing without API dependencies
- **Custom state machine** — rejected in favor of GTD's established vocabulary, which users already understand

## Backwards Compatibility

- **Org-mode syntax:** Fully compatible with standard Emacs org-mode
- **Existing agents:** Additive changes only — no existing agent behavior modified
- **Task states:** `DEFERRED` state added (Part 2); existing TODO/NEXT/WAITING/DONE/CANCELLED unchanged
- **Rich Task Standard (Part 3.5):** All new properties are optional; tasks without them use default values
- **Intent scoring (Part 9):** Default score of 5 when no INTENT_SCORE property exists — zero impact on existing task ordering
- **Migration:** No bulk migration required. New features activate as properties are added to individual tasks.
- **gtd-spec.md:** This DIP supersedes the previous `.datacore/gtd-spec.md` operational manual

## Security Considerations

- **AI task delegation:** Tasks tagged `:AI:technical:` require human review before execution, preventing autonomous changes to infrastructure or security-sensitive systems
- **Org file access:** All `.org` files are classified as PRIVATE per `privacy-policy.md` — they never sync to public repositories
- **CLOCK data:** Time tracking entries in LOGBOOK drawers contain work pattern information and are treated as private
- **Intent Graph:** Strategic intent data (`Intent-Graph.md`) reveals business priorities — restricted to personal space
- **Nightshift execution:** AI agents execute with scoped permissions per DIP-0011; no filesystem access beyond designated output directories

## Open Questions

1. **Event-driven architecture (Part 16):** Deferred to future DIP — when should reactive task creation trigger? What prevents runaway task generation?
2. **Metacognitive planning (Part 18):** How should skill gap detection interact with the engram system? Should SKILL_MISSING create learning goals automatically?
3. **Cross-space task dependencies (Part 14):** Can tasks in team spaces block tasks in personal space? What are the sync implications?

---

## Agent Context

This section provides essential information for agents working with GTD tasks and workflows.

### When to Reference This DIP

**Always reference when:**
- Processing inbox items or routing tasks
- Managing task state transitions (TODO/NEXT/WAITING/DONE/CANCELLED)
- Working with `:AI:` delegation tags
- Implementing review cycles (daily, weekly, monthly)
- Parsing or writing org-mode task files
- Building or modifying GTD-related tools or agents

### Quick Reference

| Question | Answer |
|----------|--------|
| Where do tasks live? | `org/next_actions.org` (active), `org/inbox.org` (capture) |
| What are the terminal states? | `DONE` and `CANCELLED` — never modify |
| How are AI tasks tagged? | `:AI:`, `:AI:research:`, `:AI:content:`, `:AI:data:`, `:AI:pm:` |
| What triggers archival? | Terminal state + >30 days old |
| Where is the intent graph? | `2-datacore/1-tracks/ops/Intent-Graph.md` |

### Related Agents

| Agent | Uses This DIP For |
|-------|-------------------|
| `gtd-inbox-processor` | Task classification, state assignment, routing rules (Parts 1-3, 20) |
| `ai-task-executor` | Delegation tag routing, state transitions (Part 4) |
| `queue-optimizer` | Priority scoring, intent weighting (Parts 9, 13) |
| `strategic-prioritizer` | Intent graph alignment, scoring (Part 13) |
| `failure-analyzer` | Task failure classification (Part 12) |
| `context-enhancer` | Rich task context building (Part 3.5-3.8) |

### Integration Points

- [DIP-0010](DIP-0010-external-sync-architecture.md) - External sync: org-mode as source of truth
- [DIP-0011](DIP-0011-nightshift-module.md) - Nightshift: execution pipeline and evaluators
- [DIP-0013](DIP-0013-meetings-module.md) - Meetings: lifecycle and question management
- [DIP-0014](DIP-0014-tag-taxonomy.md) - Tags: `:AI:` routing namespace
- [DIP-0019](DIP-0019-learning-architecture.md) - Learning: engram injection into task context
- [DIP-0022](DIP-0022-module-specification.md) - Modules: five-layer capability model (co-dependency)

### Key Files

| File | Purpose | Agent Access |
|------|---------|--------------|
| `org/inbox.org` | Single capture point | Read/Write (inbox-processor) |
| `org/next_actions.org` | Active tasks by focus area | Read/Write (all GTD agents) |
| `org/nightshift.org` | AI task queue | Read/Write (nightshift, ai-task-executor) |
| `org/research_learning.org` | Research pipeline | Read/Write (research-processor) |
| `org/archive.org` | Completed/canceled tasks | Read only (for context) |

### Task State Rules

**CRITICAL**: Agents MUST respect terminal states:
- `DONE` and `CANCELLED` are terminal - never modify these tasks
- Always add `CLOSED:` timestamp when transitioning to terminal state
- Include required properties on state transitions (e.g., `:WAITING_ON:` for WAITING)

### AI Delegation Tags

| Tag | Routes To | Autonomous |
|-----|-----------|------------|
| `:AI:content:` | gtd-content-writer | Yes |
| `:AI:research:` | research-orchestrator | Yes |
| `:AI:data:` | gtd-data-analyzer | Yes |
| `:AI:pm:` | gtd-project-manager | Yes |
| `:AI:technical:` | CTO queue | No (human review) |

### Task Processing Pattern

```python
# Standard task processing flow
1. Parse task from org-mode (heading, properties, tags)
2. Validate state transition is allowed
3. Execute task (agent-specific work)
4. Update task state and properties
5. Add CLOSED timestamp if terminal
6. Log execution to journal
7. Return structured JSON status
```

### Quality Standards

All GTD agents MUST:
- Log all actions to journal (`journal/YYYY-MM-DD.md`)
- Flag uncertain decisions for human review
- Return JSON with `{status, message, outputs, needs_review}`
- Respect focus area hierarchy (TIER 1 > TIER 2 > PERSONAL > RESEARCH)

## References

- [GTD Methodology](https://gettingthingsdone.com/) - David Allen's original work
- [Org-mode Manual](https://orgmode.org/manual/) - Org-mode documentation
- [HBR Project Canvas](https://hbr.org/2016/11/the-project-economy-has-arrived) - Nieto-Rodriguez project canvas methodology
- DIP-0013: Meetings Module (implemented)
- DIP-0010: External Sync Architecture (accepted) — GitHub adapter, bidirectional sync (Part 14)
- DIP-0011: Nightshift Module — execution pipeline, evaluator matrix (Parts 12, 17)
- DIP-0014: Tag Taxonomy — `:AI:` routing tags, namespace conventions (Parts 3, 13)
- DIP-0019: Learning Architecture — engram system, three-loop learning (Parts 13, 18)
- `2-datacore/1-tracks/ops/Intent-Graph.md` — Intent Graph source document (Part 9)
- `1-datafund/2-projects/verity/CANVAS.md` — Project Canvas reference implementation (Part 10)
- `0-personal/3-knowledge/zettel/project-canvas-template.md` — Canvas template (Part 10)
- DIP-0022: Module Specification — five-layer capability model (Part 21) (**co-dependency**: both DIPs reference each other)
- `2-datacore/2-projects/datacore-health/specs/dashboard-v2-specification.md` — Health Dashboard V2 (Part 19.3)
- `.datacore/commands/today.md` — `/today` command implementation (Part 19)
- `.datacore/commands/tomorrow.md` — `/tomorrow` command implementation (Part 19)
- `.datacore/commands/wrap-up.md` — `/wrap-up` command implementation (Part 19)
- `.datacore/commands/continue.md` — `/continue` command implementation (Part 19)
- `.datacore/modules/mail/commands/mails.md` — Mail processing command (Part 20)
- `.datacore/gtd-spec.md` - Previous operational specification (to be archived)
