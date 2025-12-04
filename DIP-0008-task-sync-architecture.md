# DIP-0008: Task Sync Architecture

| Field | Value |
|-------|-------|
| **DIP** | 0008 |
| **Title** | Task Sync Architecture |
| **Status** | Draft - NEEDS REVIEW |
| **Created** | 2025-12-04 |
| **Author** | Gregor |
| **Affects** | All GTD agents, /today, /wrap-up, next_actions.org, GitHub Issues |
| **Related DIPs** | DIP-0004 (Knowledge Database), DIP-0005 (Onboarding) |

> **NOTE**: This is a draft requiring review before implementation. See task in `2-datacore/org/next_actions.org`.

## Abstract

This DIP defines how org-mode coordinates with external task management systems (GitHub Issues, Asana, Linear, etc.). Org-mode serves as the **internal coordination layer** for AI agents, while users interact with their preferred task tools. Bidirectional sync ensures changes flow both directions automatically.

**Core Principle**: Users never need to touch org-mode directly. They use GitHub/Asana/etc. Agents use org-mode. Sync keeps them aligned.

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

Org-mode is the **best format for AI agents** to read and manipulate tasks. External tools are the **best format for humans**.

### Design Goals

1. **Users choose their tool** - GitHub, Asana, Linear, Notion, etc.
2. **Agents use org-mode** - Structured, local, fast, git-versioned
3. **Bidirectional sync** - Changes flow both ways automatically
4. **Single source of truth** - Org-mode is authoritative, external tools are mirrors
5. **Graceful degradation** - System works if external tool is unavailable

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
:EXTERNAL_URL: https://github.com/datacore-one/datafund-space/issues/42
:SYNC_STATUS: synced
:SYNC_UPDATED: [2025-12-04 Wed 14:30]
:END:
DEADLINE: <2025-12-04 Wed>
```

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
| Manual | Both | User runs `/sync-tasks` |
| Scheduled | Both | Cron job (every 5 min) |

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
   ├── If no external ID: Create in external tool
   └── If has external ID: Update external task

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

> **TODO**: Review and refine phases based on priority and resources.

#### Phase 1: GitHub Adapter (Week 1-2)

**Deliverables:**
- [ ] GitHub sync adapter implementation
- [ ] Pull: GitHub Issues → inbox.org
- [ ] Push: org-mode state changes → GitHub
- [ ] Webhook receiver for real-time sync
- [ ] Task identity linking (:EXTERNAL_ID: property)
- [ ] Integration with /today, /wrap-up

**Files created:**
- `.datacore/lib/sync_engine.py`
- `.datacore/lib/adapters/github_adapter.py`
- `.datacore/lib/task_router.py`

**Commands updated:**
- `/today` - Pull external changes before briefing
- `/wrap-up` - Push org changes before session end

#### Phase 2: Conflict Resolution (Week 2-3)

**Deliverables:**
- [ ] Conflict detection logic
- [ ] Resolution strategies implementation
- [ ] Conflict queue in /today briefing
- [ ] Sync history logging
- [ ] Manual conflict resolution command

**Commands created:**
- `/sync-tasks` - Manual bidirectional sync
- `/resolve-conflict` - Handle sync conflicts

#### Phase 3: Additional Adapters (Week 3-4)

**Deliverables:**
- [ ] Adapter plugin architecture
- [ ] Asana adapter (reference implementation)
- [ ] Linear adapter (optional)
- [ ] Configuration UI for adapter setup

**Files created:**
- `.datacore/lib/adapters/asana_adapter.py`
- `.datacore/lib/adapters/linear_adapter.py`

#### Phase 4: Agent Integration (Week 4-5)

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

## Open Questions

> **TODO**: Address these during review.

1. How to handle task hierarchies? GitHub Issues are flat, org-mode is hierarchical.
2. Should comments sync bidirectionally or just external → org?
3. What's the right polling interval vs webhook priority?
4. How to handle bulk operations (close 50 issues at once)?
5. Should we support multiple external tools per task?

## References

- DIP-0004: Knowledge Database (provides sync infrastructure)
- DIP-0005: GitHub-Based Onboarding (first use case)
- `.datacore/specs/datacore-specification.md` - Task Management section
- `.datacore/datacore-docs/org-mode-conventions.md`

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-04 | 0.1 | Initial draft - needs review |
