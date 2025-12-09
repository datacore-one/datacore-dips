# DIP-0010: Task Sync Architecture

| Field | Value |
|-------|-------|
| **DIP** | 0010 |
| **Title** | Task Sync Architecture |
| **Status** | Accepted |
| **Created** | 2025-12-04 |
| **Author** | Gregor |
| **Affects** | All GTD agents, /today, /wrap-up, next_actions.org, GitHub Issues |
| **Related DIPs** | DIP-0004 (Knowledge Database), DIP-0005 (Onboarding), DIP-0009 (GTD Specification) |

## Abstract

This DIP defines how org-mode coordinates with external task management systems (GitHub Issues, Asana, Linear, etc.). Org-mode serves as the **internal coordination layer** for AI agents, while users interact with their preferred task tools. Bidirectional sync ensures changes flow both directions automatically.

**Core Principle**: Users choose their preferred interface (org-mode, GitHub, Asana, etc.). Datacore agents use org-mode. External agents use GitHub. Sync keeps them aligned.

## Motivation

### Current Pain Points

1. **Fragmented task management** - Tasks exist in org-mode AND GitHub Issues, requiring manual sync
2. **User friction** - Team members unfamiliar with org-mode can't participate in task workflows
3. **External collaboration** - Contractors, partners, clients can't access org-mode
4. **Agent coordination** - AI agents need structured data (org-mode), humans need usable UIs (GitHub/Asana)

### Why Org-mode as Coordination Layer?

| Requirement | Org-mode | GitHub Issues | Asana |
|-------------|----------|---------------|-------|
| Structured parsing by agents | Excellent | API required | API required |
| Hierarchical tasks | Native | Limited (checklists) | Native |
| Properties/metadata | Native | Labels only | Custom fields |
| Local-first | Yes | No | No |
| Git-versioned | Yes | No | No |
| Works offline | Yes | No | No |
| AI-readable | Excellent | Good | Good |
| Privacy (data stays local) | Yes | No | No |
| No vendor lock-in | Yes | No | No |

Org-mode is the **best format for AI agents** to read and manipulate tasks. External tools provide **familiar UIs for humans and external collaboration**.

### Design Goals

1. **Users choose their tool** - Org-mode directly, GitHub, Asana, Linear, Notion, etc.
2. **Datacore agents use org-mode** - Structured, local, fast, git-versioned
3. **External agents use GitHub** - Standard interface for automation and integrations
4. **Bidirectional sync** - Changes flow both ways automatically
5. **Single source of truth** - Org-mode is authoritative, external tools are mirrors
6. **Graceful degradation** - System works if external tool is unavailable

## Specification

### 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER LAYER                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ GitHub       │  │ Asana        │  │ Linear       │  │ Notion       │    │
│  │ Issues       │  │              │  │              │  │              │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │             │
│         └────────────────┬┴─────────────────┴─────────────────┘             │
│                          │                                                   │
│                  ┌───────▼───────┐                                          │
│                  │  SYNC ENGINE  │◄──── Webhooks, polling, manual trigger   │
│                  │  (adapter per │                                          │
│                  │   platform)   │                                          │
│                  └───────┬───────┘                                          │
│                          │                                                   │
└──────────────────────────┼──────────────────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────────────────┐
│                          │        COORDINATION LAYER                         │
│                  ┌───────▼───────┐                                          │
│                  │  ORG-MODE     │◄──── Source of truth                     │
│                  │  next_actions │                                          │
│                  │  inbox.org    │                                          │
│                  └───────┬───────┘                                          │
│                          │                                                   │
│         ┌────────────────┼────────────────┐                                 │
│         │                │                │                                 │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐                         │
│  │ AI Task     │  │ GTD Inbox   │  │ Project     │                         │
│  │ Executor    │  │ Processor   │  │ Manager     │                         │
│  └─────────────┘  └─────────────┘  └─────────────┘                         │
│                                                                              │
│                          AGENT LAYER                                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

#### 1.1 Module Structure

The sync engine is part of Datacore core, providing reusable infrastructure for task sync, calendar sync, and future integrations.

```
.datacore/lib/sync/
├── engine.py          # Base sync engine, orchestration
├── adapters/
│   ├── __init__.py
│   ├── base.py        # Adapter interface (TaskSyncAdapter)
│   ├── github.py      # GitHub Issues adapter
│   └── calendar.py    # Google Calendar adapter (future)
├── conflict.py        # Conflict detection and resolution
├── router.py          # Task routing rules
└── history.py         # Sync history logging
```

**Design principle:** The sync engine provides generic sync patterns (pull, push, conflict resolution, routing). Domain-specific logic (task semantics, calendar events) lives in the adapters and calling modules.

**Planned adapters:**
1. **GitHub Issues** (Phase 1) - Current priority
2. **Google Calendar** (Phase 3) - Future
3. **Asana, Linear** (Phase 4) - Optional

### 2. Sync Adapters

Each external tool has an adapter that translates between org-mode and the tool's format.

#### 2.1 Adapter Interface

```python
class TaskSyncAdapter:
    """Base interface for task sync adapters."""

    def pull_changes(self, since: datetime) -> List[TaskChange]:
        """Fetch changes from external tool since timestamp."""

    def push_changes(self, changes: List[TaskChange]) -> SyncResult:
        """Push org-mode changes to external tool."""

    def create_task(self, task: OrgTask) -> ExternalTaskRef:
        """Create new task in external tool, return reference."""

    def update_task(self, ref: ExternalTaskRef, changes: dict) -> bool:
        """Update existing task in external tool."""

    def delete_task(self, ref: ExternalTaskRef) -> bool:
        """Delete/close task in external tool."""

    def resolve_conflict(self, org_task: OrgTask, external_task: ExternalTask) -> Resolution:
        """Handle conflict when both sides changed."""
```

#### 2.2 GitHub Issues Adapter

```yaml
# .datacore/config.yaml
sync:
  adapters:
    github:
      enabled: true
      repos:
        - owner: datacore-one
          repo: datacore
          label_mapping:
            ":AI:": "ai-task"
            ":AI:research:": "ai-research"
            "[#A]": "priority-high"
            "[#B]": "priority-medium"
          state_mapping:
            TODO: open
            NEXT: open
            WAITING: open
            DONE: closed
            CANCELLED: closed
          sync_interval: 5m  # Poll interval
          webhook_secret: ${GITHUB_WEBHOOK_SECRET}  # For real-time
```

#### 2.3 Asana Adapter (Example)

```yaml
sync:
  adapters:
    asana:
      enabled: true
      workspace_id: ${ASANA_WORKSPACE_ID}
      project_mapping:
        "Datafund": "1-datafund"
        "Datacore": "2-datacore"
      custom_field_mapping:
        priority: "Priority"
        effort: "Estimated Hours"
```

### 3. Task Identity and Linking

Tasks are linked via properties in org-mode and metadata in external tools.

#### 3.1 Org-mode Task with External Link

```org
*** TODO Review Dubai pilot proposal
:PROPERTIES:
:CREATED: [2025-12-04 Wed]
:EXTERNAL_ID: github:datacore-one/datafund-space#42
:EXTERNAL_URL: [[https://github.com/datacore-one/datafund-space/issues/42][datafund-space#42]]
:SYNC_STATUS: synced
:SYNC_UPDATED: [2025-12-04 Wed 14:30]
:END:
DEADLINE: <2025-12-04 Wed>
```

Note: `:EXTERNAL_URL:` uses org-mode link format `[[url][description]]` so it's clickable for users who access org-mode directly.

#### 3.2 GitHub Issue with Org Link

```markdown
<!-- datacore:sync -->
<!-- org_file: 1-datafund/org/next_actions.org -->
<!-- org_id: dubai-pilot-proposal-2025-12-04 -->
<!-- last_sync: 2025-12-04T14:30:00Z -->

## Dubai Data RWA Pilot Proposal

**Deadline:** 2025-12-04
**Priority:** A
**Category:** Business Development

[Task description here]
```

### 4. Sync Protocol

#### 4.1 Sync Triggers

| Trigger | Direction | When |
|---------|-----------|------|
| `/today` | Pull | Morning briefing |
| `/wrap-up` | Push | Session end |
| Webhook | Pull | External change (real-time) |
| `/sync` | Both | User runs manual sync (repos + tasks + calendars) |
| Scheduled | Both | Cron job (every 10 min) |

Note: The `/sync` command replaces the legacy `./sync` shell script and planned `/sync-tasks` command. It provides unified synchronization for repositories, tasks, and calendars (future).

#### 4.2 Sync Flow: External → Org-mode

```
EXTERNAL CHANGE DETECTED
────────────────────────

1. IDENTIFY
   ├── Parse external task ID
   ├── Look up in org-mode via :EXTERNAL_ID:
   └── If not found: Create new task in inbox.org

2. COMPARE
   ├── Compare state (open/closed → TODO/DONE)
   ├── Compare properties (labels → tags, assignee, etc.)
   ├── Check for conflicts (both changed since last sync)
   └── If conflict: Apply conflict resolution strategy

3. APPLY
   ├── Update org-mode task properties
   ├── Update :SYNC_UPDATED: timestamp
   ├── Write to file (via DIP-0004 write-back engine)
   └── Log change to sync_history table

4. NOTIFY (optional)
   └── If significant change: Add to /today briefing
```

#### 4.3 Sync Flow: Org-mode → External

```
ORG-MODE CHANGE DETECTED
────────────────────────

1. IDENTIFY
   ├── Check if task has :EXTERNAL_ID:
   ├── If has external ID: Update external task
   ├── If no external ID:
   │   ├── Search external tool for matching task (by title, deadline, description hash)
   │   ├── If match found: Link existing task, set :EXTERNAL_ID:
   │   └── If no match: Create new task in external tool
   └── This prevents duplicate creation when :EXTERNAL_ID: was lost or never set

2. TRANSLATE
   ├── Map org state → external state
   ├── Map org tags → external labels
   ├── Map org priority → external priority
   └── Map org deadline → external due date

3. PUSH
   ├── Call adapter.update_task() or adapter.create_task()
   ├── Update :EXTERNAL_ID: if newly created
   ├── Update :SYNC_UPDATED: timestamp
   └── Log to sync_history

4. HANDLE FAILURE
   ├── If API error: Queue for retry
   ├── If rate limited: Back off
   └── If permanent failure: Mark :SYNC_STATUS: failed
```

#### 4.4 Conflict Resolution

```
CONFLICT DETECTED
─────────────────
Both org-mode and external tool changed since last sync.

Resolution strategies (configurable):

1. EXTERNAL_WINS (default for comments)
   └── External changes overwrite org-mode

2. ORG_WINS (default for state changes)
   └── Org-mode changes overwrite external

3. MERGE (default for description)
   └── Attempt automatic merge, flag if impossible

4. ASK (for critical conflicts)
   └── Add to "Needs Decision" in /today briefing

Configuration:
```yaml
sync:
  conflict_resolution:
    state: org_wins      # Agent decisions are authoritative
    description: merge   # Try to combine
    comments: external_wins  # Human discussion wins
    priority: org_wins   # Agent triage is authoritative
```
```

### 5. Task Routing Rules

When new tasks appear in external tools, route them appropriately.

```yaml
# .datacore/config.yaml
sync:
  routing:
    # Tasks created in GitHub with label "ai-task" → next_actions.org with :AI: tag
    - source: github
      condition: "labels contains 'ai-task'"
      destination: next_actions.org
      tags: [":AI:"]

    # Tasks assigned to @crtahlin → route to team member's view
    - source: github
      condition: "assignee == 'crtahlin'"
      destination: next_actions.org
      category: "@crt"

    # Unassigned tasks → inbox for triage
    - source: github
      condition: "assignee is null"
      destination: inbox.org

    # High priority → NEXT state
    - source: github
      condition: "labels contains 'priority-high'"
      state: NEXT
```

### 6. User Workflows

#### 6.1 Team Member (uses GitHub)

```
USER WORKFLOW (GitHub-centric)
──────────────────────────────

1. User creates issue in GitHub
   └── "Review competitor analysis"

2. Sync engine detects new issue (webhook or poll)
   └── Creates task in inbox.org

3. GTD agent processes inbox
   └── Routes to next_actions.org, sets priority

4. AI task executor picks up task
   └── Works on it, updates state to DONE

5. Sync engine pushes state change
   └── GitHub issue closed automatically

6. User sees closed issue
   └── "How did that get done?" → AI work visible in issue comments
```

#### 6.2 Admin (uses org-mode directly)

```
ADMIN WORKFLOW (org-mode-centric)
─────────────────────────────────

1. Admin adds task to next_actions.org
   └── *** TODO Create partnership proposal :AI:content:

2. Sync engine detects new task
   └── Creates GitHub issue (if configured)

3. External collaborator comments on issue
   └── "Need more details on pricing"

4. Sync engine pulls comment
   └── Adds to org-mode task notes

5. Admin sees comment in /today briefing
   └── Responds (either in org-mode or GitHub)
```

#### 6.3 External Collaborator (GitHub only)

```
EXTERNAL COLLABORATOR WORKFLOW
──────────────────────────────

1. Collaborator only has GitHub access
   └── Cannot see org-mode, cannot run Claude

2. Creates issue: "Bug in API endpoint"
   └── Sync creates inbox entry

3. GTD agent triages
   └── Routes to appropriate category, assigns priority

4. Team works on it (visible in org-mode)
   └── Progress updates sync to GitHub

5. Collaborator sees updates in GitHub
   └── Can comment, which syncs back

Collaborator never knows org-mode exists.
They just see a responsive GitHub project.
```

### 7. Implementation Roadmap

#### Phase 1: GitHub Adapter

**Status:** ✅ Complete (2025-12-09)

**Deliverables:**
- [x] Sync engine core (`engine.py`, `base.py`)
- [x] GitHub sync adapter implementation (uses `gh` CLI)
- [x] Pull: GitHub Issues → org-mode (via router)
- [x] Push: org-mode state changes → GitHub
- [ ] Webhook receiver for real-time sync (deferred - polling works)
- [x] Task identity linking (`:EXTERNAL_ID:` property)
- [x] Duplicate detection before creating external tasks
- [ ] Integration with `/today`, `/wrap-up` (commands defined, wiring pending)
- [x] `/sync` command (unified sync for repos + tasks)
- [x] Task routing rules (`router.py`)
- [x] Sync history logging (`history.py` - moved from Phase 2)

**Files created:**
```
.datacore/lib/sync/
├── __init__.py           # Module exports
├── engine.py             # SyncEngine orchestration
├── router.py             # Task routing rules
├── history.py            # SQLite sync history
├── adapters/
│   ├── __init__.py       # Adapter registry
│   ├── base.py           # TaskSyncAdapter interface
│   └── github.py         # GitHub adapter (gh CLI)
└── tests/
    ├── __init__.py
    ├── test_engine.py
    ├── test_github_adapter.py
    ├── test_router.py
    └── test_history.py
```

**Commands updated:**
- `.datacore/commands/sync.md` - New unified `/sync` command
- `.datacore/commands/diagnostic.md` - Added Section 11: External Sync Health

**Configuration:**
- `.datacore/settings.yaml` - Added `sync.tasks` and `sync.adapters` config

**To enable:** Create `.datacore/settings.local.yaml`:
```yaml
sync:
  tasks:
    enabled: true
  adapters:
    github:
      enabled: true
      repos:
        - owner: datacore-one
          repo: datacore
```

#### Phase 2: Conflict Resolution

**Status:** Partially complete

**Deliverables:**
- [ ] Conflict detection logic
- [ ] Resolution strategies implementation (org_wins, external_wins, merge, ask)
- [ ] Conflict queue in `/today` briefing
- [x] Sync history logging (completed in Phase 1)
- [ ] Manual conflict resolution UI

**Files to create:**
- `.datacore/lib/sync/conflict.py`

#### Phase 3: Calendar Adapter

**Priority:** After GitHub adapter is stable

**Deliverables:**
- [ ] Google Calendar adapter
- [ ] Deadline ↔ calendar event sync
- [ ] Calendar module using sync engine patterns

**Files created:**
- `.datacore/lib/sync/adapters/calendar.py`
- `.datacore/modules/calendar/` (calendar-specific logic)

#### Phase 4: Additional Adapters (Future)

**Deliverables:**
- [ ] Asana adapter
- [ ] Linear adapter
- [ ] Configuration UI for adapter setup

**Files created:**
- `.datacore/lib/sync/adapters/asana.py`
- `.datacore/lib/sync/adapters/linear.py`

#### Phase 5: Agent Integration

**Deliverables:**
- [ ] AI task executor reads/writes via sync engine
- [ ] GTD inbox processor creates external issues
- [ ] Project manager updates external project boards
- [ ] Automated status updates in external tools

**Agents updated:**
- `ai-task-executor` - Sync state changes to external
- `gtd-inbox-processor` - Option to create external issue
- `gtd-project-manager` - Sync project status

### 8. Configuration

#### 8.1 Full Configuration Example

```yaml
# .datacore/config.yaml
sync:
  enabled: true

  # Default sync behavior
  auto_pull: true          # Pull on /today
  auto_push: true          # Push on /wrap-up
  poll_interval: 5m        # Background polling

  # Conflict resolution defaults
  conflict_resolution:
    state: org_wins
    description: merge
    comments: external_wins
    priority: org_wins
    deadline: org_wins

  # Task routing
  routing:
    - source: "*"
      condition: "no external_id"
      destination: inbox.org

  # Adapters
  adapters:
    github:
      enabled: true
      repos:
        - owner: datacore-one
          repo: datacore
          sync_labels: ["task", "ai-task", "bug", "feature"]
          ignore_labels: ["wontfix", "duplicate"]
      label_mapping:
        ":AI:": "ai-task"
        ":AI:research:": "ai-research"
        ":AI:content:": "ai-content"
        "[#A]": "priority-high"
        "[#B]": "priority-medium"
        "[#C]": "priority-low"
      state_mapping:
        TODO: open
        NEXT: open
        WAITING: open
        DONE: closed
        CANCELLED: closed

    asana:
      enabled: false
      workspace_id: ${ASANA_WORKSPACE_ID}
      api_key: ${ASANA_API_KEY}
```

### 9. Security Considerations

- **API keys in env**: All credentials in `.datacore/env/.env`, never in config
- **Webhook validation**: Verify GitHub webhook signatures
- **Rate limiting**: Respect external API rate limits
- **Audit trail**: Log all sync operations for debugging
- **Rollback**: Org-mode is git-versioned, can always revert

### 10. Future Extensions

- **n8n integration**: Use n8n for complex sync workflows
- **Slack/Discord sync**: Tasks from messages
- **Email sync**: Tasks from email (via n8n)
- **Calendar sync**: Deadlines ↔ calendar events
- **Mobile app**: Task capture → sync to org-mode

### 11. Tag Governance

To ensure consistent tag usage and prevent tag proliferation/variants, maintain a **canonical tag registry**.

> **Cross-reference:** Tag governance is also required for GTD workflows (DIP-0009). The tag registry serves both sync mapping (this DIP) and GTD agent routing (DIP-0009).

#### 11.1 Tag Registry

**Location:** `.datacore/config/tags.yaml`

The tag registry is the single source of truth for all tags across the system:
- AI delegation tags (`:AI:*:`)
- Priority tags (`[#A/B/C]`)
- Context tags (`@person`, `@place`)
- Domain tags (datafund, verity, etc.)
- Content type tags (article, zettel, etc.)
- Action tags (read-later, watchlist, etc.)

**Each tag definition includes:**
- `description` - Human-readable purpose
- `org` - Org-mode format (`:tag:`)
- `hashtag` - Notes format (`#Tag`)
- `yaml` - Frontmatter format
- `github` - GitHub label mapping
- `agent` - Which agent handles this tag (for AI tags)
- `aliases` - Known variants to normalize

**Referenced by:**
- Sync engine (label mappings)
- GTD agents (task routing)
- Zettel processor (note classification)
- Tag validator script

See `.datacore/config/tags.yaml` for full registry.

#### 11.2 Tag Validation

**Script:** `.datacore/lib/tag_validator.py`

```bash
# Full validation report
python tag_validator.py --report

# Validate only org files
python tag_validator.py --org

# Validate only notes
python tag_validator.py --notes

# Auto-fix normalizable variants
python tag_validator.py --fix

# Show tag usage statistics
python tag_validator.py --stats
```

**Validation checks:**
1. **Unknown tags** - Flags tags not in registry
2. **Variant warnings** - Suggests canonical form for known variants
3. **Auto-normalize** - Converts known variants to canonical form (with `--fix`)
4. **New tag tracking** - Reports new tags for registry consideration

#### 11.3 Sync Label Mapping

The `sync_label_mapping` section in `tags.yaml` provides the org ↔ GitHub mapping:

| Org-mode | GitHub Label | Notes Format |
|----------|--------------|--------------|
| `:AI:` | `ai-task` | `#AI` |
| `:AI:content:` | `ai-content` | - |
| `:AI:research:` | `ai-research` | - |
| `:AI:data:` | `ai-data` | - |
| `:AI:pm:` | `ai-pm` | - |
| `[#A]` | `priority-high` | - |
| `[#B]` | `priority-medium` | - |
| `[#C]` | `priority-low` | - |

Settings reference: `settings.yaml` → `tags.registry` points to the registry file.

## Design Decisions

The following questions were resolved during review:

| Question | Decision | Rationale |
|----------|----------|-----------|
| Task hierarchies | Flatten in GitHub; org-mode handles sequencing/prioritization | GitHub Issues are flat by design. Org-mode's hierarchical structure is the coordination layer for ordering and grouping. |
| Comments sync | Out of scope for Phase 1. Notify in `/today` if open comments exist. | Comments require nuanced handling (auto-reply vs human review). Start simple, iterate later. |
| Polling interval | 10 minutes | Balance between responsiveness and API rate limits. Webhooks provide real-time for critical events. |
| Bulk operations | User-initiated only | Safety first. Bulk close/update should require explicit user action. Can automate later with safeguards. |
| Multiple external tools | Supported in architecture, only GitHub implemented now | Design for flexibility, implement what's needed. `:EXTERNAL_ID:` format (`github:owner/repo#42`) supports multiple tools. |

## References

- DIP-0004: Knowledge Database (provides write-back infrastructure)
- DIP-0005: GitHub-Based Onboarding (first use case)
- DIP-0009: GTD Specification (uses tag registry from this DIP)
- `.datacore/specs/datacore-specification.md` - Task Management section
- `.datacore/datacore-docs/org-mode-conventions.md`

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-09 | 1.2 | Implementation: Section 11 (Tag Governance) complete - tag registry, tag validator script, diagnostic integration |
| 2025-12-09 | 1.1 | Implementation: Phase 1 complete - sync engine, GitHub adapter, router, history, /sync command, tests |
| 2025-12-09 | 1.0 | Accepted: Resolved open questions, added module structure, updated design goals, added duplicate detection, replaced /sync-tasks with /sync |
| 2025-12-08 | 0.2 | Renamed from DIP-0008, added Tag Governance section |
| 2025-12-04 | 0.1 | Initial draft |
