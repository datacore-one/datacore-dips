# DIP-0009: GTD System Specification

> **Status**: Draft
> **Author**: Gregor
> **Created**: 2025-12-04
> **Updated**: 2026-02-21
> **Supersedes**: `.datacore/gtd-spec.md` (operational manual to be archived)

## Summary

This DIP defines the comprehensive GTD (Getting Things Done) implementation for Datacore, including:

- Core GTD workflow and methodology
- Org-mode as the coordination layer
- Task states and transitions
- File structure and routing rules
- AI agent architecture for automation
- Review cycles and commands
- Module requirements
- External system integration patterns

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
| Daily Start | `/gtd-daily-start` | Morning | Orient, plan day |
| Daily End | `/gtd-daily-end` | Evening | Process inbox, delegate to AI |
| Weekly | `/gtd-weekly-review` | Friday PM | Full system review |
| Monthly | `/gtd-monthly-strategic` | Last Friday | Strategic alignment |

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
| `CANCELED` | Will not do | Yes | `:CANCEL_REASON:` |

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
    └───────────────┴─────────▶ CANCELED
```

**Valid transitions:**
- `TODO` → `NEXT`, `WAITING`, `DEFERRED`, `DONE`, `CANCELED`
- `NEXT` → `TODO`, `WAITING`, `DONE`, `CANCELED`
- `WAITING` → `TODO`, `NEXT`, `DONE`, `CANCELED`
- `DEFERRED` → `TODO`, `CANCELED`
- `DONE` → (terminal)
- `CANCELED` → (terminal)

### Archival Behavior

Terminal states (`DONE`, `CANCELED`) trigger archival:

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
3. `/today` and `/gtd-daily-start` surface WAITING tasks for review

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
- Respect terminal states (never modify DONE/CANCELED)
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

### Daily Start (`/gtd-daily-start`)

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

### Daily End (`/gtd-daily-end`)

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
| `meetings` | Meeting lifecycle, questions | DIP-0006 |

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

## Implementation

### Phase 1: Documentation (Current)
- Finalize this DIP
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

---

## Compatibility

- **Org-mode:** Standard org-mode syntax, compatible with Emacs
- **Existing agents:** Backward compatible, adds formalization
- **gtd-spec.md:** This DIP supersedes gtd-spec.md

---

## Agent Context

This section provides essential information for agents working with GTD tasks and workflows.

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
- `DONE` and `CANCELED` are terminal - never modify these tasks
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
- DIP-0006: Meetings Module (planned)
- DIP-0010: External Sync Architecture (accepted)
- `.datacore/gtd-spec.md` - Previous operational specification (to be archived)
