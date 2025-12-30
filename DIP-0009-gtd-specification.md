# DIP-0009: GTD System Specification

> **Status**: Draft - NEEDS REVIEW
> **Author**: Gregor
> **Created**: 2025-12-04
> **Updated**: 2025-12-04
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
| `:AI:research:` | `gtd-research-processor` | URL analysis, literature notes, zettels | `3-knowledge/` |
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

## References

- [GTD Methodology](https://gettingthingsdone.com/) - David Allen's original work
- [Org-mode Manual](https://orgmode.org/manual/) - Org-mode documentation
- DIP-0006: Meetings Module (planned)
- DIP-0010: External Sync Architecture (accepted)
- `.datacore/gtd-spec.md` - Previous operational specification (to be archived)
