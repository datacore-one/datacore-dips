# DIP-0010: External Sync Architecture

| Field | Value |
|-------|-------|
| **DIP** | 0010 |
| **Title** | External Sync Architecture |
| **Status** | Accepted |
| **Created** | 2025-12-04 |
| **Author** | Gregor |
| **Affects** | All GTD agents, /today, /wrap-up, org files, GitHub Issues, Google Calendar |
| **Related DIPs** | DIP-0004 (Knowledge Database), DIP-0005 (Onboarding), DIP-0009 (GTD Specification) |

## Abstract

This DIP defines how org-mode coordinates with external services (GitHub Issues, Google Calendar, Asana, Linear, etc.). Org-mode serves as the **internal coordination layer** and **source of truth** for all content. Bidirectional sync ensures changes flow both directions automatically.

The sync infrastructure is **payload-agnostic**. Different adapters sync different content types:

| Adapter | Org File | Content Type | External Service |
|---------|----------|--------------|------------------|
| GitHub | `next_actions.org` | Tasks | GitHub Issues |
| Calendar | `calendar.org` | Calendar entries | Google Calendar |
| Asana | `next_actions.org` | Tasks | Asana Tasks |

**Core Principle**: All content lives in org-mode. Adapters handle bidirectional sync with external services. Modules provide domain workflows that write to org files.

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

The sync engine is part of Datacore core, providing reusable infrastructure for external service sync.

```
.datacore/lib/sync/
├── engine.py          # Base sync engine, orchestration
├── adapters/
│   ├── __init__.py
│   ├── base.py        # Abstract SyncAdapter interface (payload-agnostic)
│   ├── github.py      # GitHub Issues adapter (tasks)
│   └── calendar.py    # Google Calendar adapter (calendar entries)
├── conflict.py        # Conflict detection and resolution
├── router.py          # Entry routing rules
└── history.py         # Sync history logging
```

**Design principle:** The sync engine provides generic sync patterns (pull, push, conflict resolution, routing). Each adapter handles a specific external service and content type. Domain workflows (modules) write to org files; adapters sync those files.

#### 1.2 Abstract Payload Architecture

The sync infrastructure is **payload-agnostic**. The base data model supports different content types:

```python
# Base class for all org entries
class OrgEntry:
    """Abstract base for any org-mode entry."""
    id: str
    title: str
    body: str
    external_id: Optional[str]
    sync_status: str
    sync_updated: datetime

# Task-specific (next_actions.org)
class OrgTask(OrgEntry):
    state: TaskState  # TODO, NEXT, DONE, etc.
    priority: Priority
    deadline: Optional[datetime]
    scheduled: Optional[datetime]
    tags: List[str]

# Calendar-specific (calendar.org)
class OrgCalendarEntry(OrgEntry):
    timestamp: datetime  # <2025-12-10 Tue 10:00-11:00>
    end_time: Optional[datetime]
    repeater: Optional[str]  # +1w, +1m, etc.
    location: Optional[str]
    attendees: List[str]
```

#### 1.3 Module → Adapter Relationship

Modules provide domain workflows. Adapters provide sync infrastructure.

```
┌─────────────────────────────────────────────────────────────┐
│                    MODULE LAYER (Domain Logic)               │
│  ┌─────────────────┐     ┌─────────────────┐                │
│  │ Meetings Module │     │ GTD Agents      │                │
│  │ - Create meeting│     │ - Process inbox │                │
│  │ - Generate agenda│    │ - Route tasks   │                │
│  └────────┬────────┘     └────────┬────────┘                │
│           │ writes to             │ writes to               │
│           ▼                       ▼                          │
│     calendar.org            next_actions.org                │
└───────────┼───────────────────────┼──────────────────────────┘
            │                       │
     ┌──────▼──────┐         ┌──────▼──────┐
     │  Calendar   │         │   GitHub    │
     │  Adapter    │         │   Adapter   │
     │  (sync)     │         │   (sync)    │
     └─────────────┘         └─────────────┘
```

**Example: Meetings module using calendar adapter**
```python
class MeetingsModule:
    def schedule_meeting(self, title, time, attendees):
        # Module writes to calendar.org
        entry = OrgCalendarEntry(
            title=title,
            timestamp=time,
            attendees=attendees
        )
        append_to_calendar_org(entry)
        # Calendar adapter syncs to Google Calendar automatically
```

**Planned adapters:**
1. **GitHub Issues** (Phase 1) - ✅ Complete
2. **Google Calendar** (Phase 3) - Next
3. **Asana, Linear** (Phase 4) - Optional

### 2. Sync Adapters

Each external service has an adapter that translates between org-mode and the service's format.

#### 2.1 Adapter Interface

```python
class SyncAdapter(ABC):
    """Abstract base interface for all sync adapters."""

    @property
    @abstractmethod
    def adapter_type(self) -> str:
        """Unique identifier (e.g., 'github', 'calendar')."""

    @property
    @abstractmethod
    def org_file(self) -> str:
        """Which org file this adapter syncs (e.g., 'next_actions.org', 'calendar.org')."""

    @abstractmethod
    def pull_changes(self, since: datetime) -> List[Change]:
        """Fetch changes from external service since timestamp."""

    @abstractmethod
    def push_changes(self, changes: List[Change]) -> SyncResult:
        """Push org-mode changes to external service."""

    @abstractmethod
    def create_entry(self, entry: OrgEntry) -> ExternalRef:
        """Create new entry in external service, return reference."""

    @abstractmethod
    def update_entry(self, ref: ExternalRef, changes: dict) -> bool:
        """Update existing entry in external service."""

    @abstractmethod
    def delete_entry(self, ref: ExternalRef) -> bool:
        """Delete/archive entry in external service."""


class TaskSyncAdapter(SyncAdapter):
    """Adapter for task-based services (GitHub, Asana, Linear)."""
    org_file = "next_actions.org"
    # Task-specific methods...


class CalendarSyncAdapter(SyncAdapter):
    """Adapter for calendar services (Google Calendar)."""
    org_file = "calendar.org"
    # Calendar-specific methods...
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

**Status:** ✅ Complete (2025-12-09)

**Deliverables:**
- [x] Conflict detection logic (`ConflictDetector`)
- [x] Resolution strategies implementation (org_wins, external_wins, merge, ask)
- [x] Conflict queue in `/today` briefing
- [x] Sync history logging (completed in Phase 1)
- [x] CLI for conflict management (`--unresolved`, `--stats`, `--resolve`)

**Files created:**
- `.datacore/lib/sync/conflict.py` - Full conflict resolution module:
  - `ConflictType` enum (state, title, description, priority, deadline, labels, comments)
  - `ConflictStrategy` enum (org_wins, external_wins, merge, ask)
  - `ConflictDetector` - Detects conflicts between org and external tasks
  - `ConflictResolver` - Resolves conflicts using configured strategies
  - `ConflictQueue` - SQLite-backed queue for unresolved conflicts
  - CLI interface for conflict management

**Configuration added to settings.yaml:**
```yaml
sync:
  conflict_resolution:
    state: org_wins
    title: org_wins
    description: merge
    priority: org_wins
    deadline: org_wins
    labels: merge
    comments: external_wins
```

#### Phase 3: Calendar Adapter

**Status:** ✅ Complete (2025-12-09)

##### calendar.org File

New file: `0-personal/org/calendar.org`

Calendar entries are org-mode entries with timestamps:

```org
#+TITLE: Calendar
#+FILETAGS: :calendar:

* Meeting with investors
  :PROPERTIES:
  :EXTERNAL_ID: calendar:primary/abc123
  :SYNC_STATUS: synced
  :SYNC_UPDATED: [2025-12-09 Mon 10:00]
  :END:
  <2025-12-10 Tue 10:00-11:00>
  Discuss Series A terms
  - Attendees: John, Sarah
  - Location: Zoom

* Weekly standup :recurring:
  :PROPERTIES:
  :EXTERNAL_ID: calendar:primary/def456
  :END:
  <2025-12-09 Mon 09:00-09:30 +1w>

* Doctor appointment
  <2025-12-12 Thu 14:00>
```

**Key differences from tasks:**
- Uses timestamps `<...>` not DEADLINE/SCHEDULED
- May or may not have TODO state
- Shows in org-agenda calendar view
- Supports time ranges `10:00-11:00`
- Supports repeaters `+1w`, `+1m`

##### Sync Mapping

| calendar.org | Google Calendar |
|--------------|-----------------|
| Heading title | Event title |
| `<timestamp>` | Event start/end time |
| Body text | Event description |
| `:recurring:` tag | Recurring event |
| `:EXTERNAL_ID:` | Event ID link |

##### Deliverables

- [x] Create `0-personal/org/calendar.org` with synced events
- [x] `OrgCalendarEntry` dataclass in `base.py`
- [x] Google Calendar adapter (`calendar.py`) using Google Calendar API
- [x] Integration with `/today` (calendar section with Python code example)
- [x] Configuration in `settings.yaml` and `settings.local.yaml`
- [x] OAuth setup via `gcal_auth.py` helper script
- [x] Tests (`test_calendar_adapter.py`) - 11 tests passing

**Files created:**
- `.datacore/lib/sync/adapters/calendar.py` - Full adapter with pull/push methods
- `.datacore/lib/sync/adapters/gcal_auth.py` - OAuth authentication helper
- `.datacore/lib/sync/tests/test_calendar_adapter.py` - Unit and integration tests
- `0-personal/org/calendar.org` - Synced calendar entries
- Updated `settings.yaml` with calendar adapter configuration
- Updated `/today` command with calendar integration

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
| 2025-12-09 | 1.5 | **Phase 3 Complete**: Google Calendar adapter implemented with full OAuth flow, pull/push methods, OrgCalendarEntry dataclass, settings configuration, /today integration, and 11 passing tests. |
| 2025-12-09 | 1.4 | **Renamed to External Sync Architecture**: Broadened scope beyond tasks to include calendar entries and future content types. Added abstract payload architecture (OrgEntry base class), calendar.org file documentation, module → adapter relationship pattern. |
| 2025-12-09 | 1.3 | Implementation: Phase 2 (Conflict Resolution) complete - conflict.py, ConflictDetector, ConflictResolver, ConflictQueue, CLI |
| 2025-12-09 | 1.2 | Implementation: Section 11 (Tag Governance) complete - tag registry, tag validator script, diagnostic integration |
| 2025-12-09 | 1.1 | Implementation: Phase 1 complete - sync engine, GitHub adapter, router, history, /sync command, tests |
| 2025-12-09 | 1.0 | Accepted: Resolved open questions, added module structure, updated design goals, added duplicate detection, replaced /sync-tasks with /sync |
| 2025-12-08 | 0.2 | Renamed from DIP-0008, added Tag Governance section |
| 2025-12-04 | 0.1 | Initial draft |
