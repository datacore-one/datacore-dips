# DIP-0004: Knowledge Database

| Field | Value |
|-------|-------|
| **DIP** | 0004 |
| **Title** | Knowledge Database |
| **Status** | Implemented |
| **Created** | 2025-12-02 |
| **Author** | Claude (AI-assisted) |
| **Affects** | All agents, /today, /wrap-up, /tomorrow, /diagnostic |

## Abstract

This DIP specifies a SQLite-based knowledge database that indexes all Datacore content (markdown, org-mode, YAML configs) to enable fast queries, cross-referencing, and agent intelligence. The database supports bidirectional synchronization—agents can both read from and write to the database, with changes syncing back to source files.

**Core Principle**: Markdown/org files remain the source of truth. The database is a derived index that can always be rebuilt from source files.

## Motivation

Current limitations:
1. **Agents parse files repeatedly** - Each agent greps/reads files from scratch
2. **No cross-referencing** - Can't query "what links to this?" without scanning all files
3. **No temporal queries** - Can't ask "tasks completed this week" without parsing org history
4. **No aggregate insights** - Manual calculation for metrics, patterns, trends
5. **Context sync is manual** - context-maintainer counts files instead of querying

Benefits of database indexing:
1. **Sub-second queries** - Agents get instant results instead of file scanning
2. **Relationship tracking** - Links, tags, references all queryable
3. **Temporal analytics** - Date-range queries, trends, patterns
4. **Aggregate metrics** - SUM, AVG, COUNT by category/time/space
5. **Automated validation** - Context drift detection, scaffolding coverage

## Specification

### 1. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SOURCE OF TRUTH                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ *.md     │  │ *.org    │  │ *.yaml   │  │ CLAUDE.md    │    │
│  │ notes    │  │ tasks    │  │ configs  │  │ contexts     │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘    │
│       │             │             │                │            │
│       └─────────────┴─────────────┴────────────────┘            │
│                             │                                   │
│                     ┌───────▼───────┐                           │
│                     │   INDEXER     │◄─────── Rebuild anytime   │
│                     │  (parsers)    │                           │
│                     └───────┬───────┘                           │
│                             │                                   │
│                     ┌───────▼───────┐                           │
│                     │ knowledge.db  │◄─────── Derived index     │
│                     │   (SQLite)    │                           │
│                     └───────┬───────┘                           │
│                             │                                   │
│        ┌────────────┬───────┴───────┬────────────┐             │
│        ▼            ▼               ▼            ▼             │
│    ┌───────┐   ┌─────────┐   ┌──────────┐   ┌────────┐        │
│    │Agents │   │Commands │   │Diagnostic│   │ CLI    │        │
│    │ (R/W) │   │ (query) │   │ (health) │   │(admin) │        │
│    └───┬───┘   └─────────┘   └──────────┘   └────────┘        │
│        │                                                        │
│        │ write-back                                             │
│        ▼                                                        │
│    ┌───────────────┐                                           │
│    │ SYNC ENGINE   │──────────► Update source files            │
│    └───────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Database Locations

| Database | Path | Scope |
|----------|------|-------|
| Root | `~/.datacore/knowledge.db` | All spaces, cross-space queries |
| Personal | `0-personal/.datacore/knowledge.db` | Personal space only |
| Datafund | `1-datafund/.datacore/knowledge.db` | Datafund space only |
| Datacore | `2-datacore/.datacore/knowledge.db` | Datacore space only |

Space databases sync to root database, enabling both isolated and cross-space queries.

### 3. Schema

#### 3.1 Core Tables

```sql
-- All indexed files
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    space TEXT,                          -- personal, datafund, datacore
    type TEXT NOT NULL,                  -- zettel, page, journal, task, agent, etc.
    subtype TEXT,                        -- Further classification
    title TEXT,
    content TEXT,
    summary TEXT,                        -- AI-generated or first paragraph
    word_count INTEGER,
    maturity TEXT,                       -- seedling, budding, evergreen
    is_stub BOOLEAN DEFAULT FALSE,
    author TEXT,                         -- human, ai, ai-assisted, unknown
    source_file TEXT,                    -- For DB→file sync tracking
    checksum TEXT,                       -- For change detection
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full-text search (FTS5)
CREATE VIRTUAL TABLE files_fts USING fts5(
    title, content, summary,
    content='files',
    content_rowid='id'
);

-- References between files
CREATE TABLE links (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    target_id INTEGER REFERENCES files(id) ON DELETE SET NULL,
    target_title TEXT NOT NULL,          -- Original link text
    link_type TEXT,                      -- reference, extends, implements, supersedes
    syntax TEXT,                         -- wiki-link, hashtag, org-link
    context TEXT,                        -- Surrounding text
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags extracted from files
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    normalized_tag TEXT NOT NULL,        -- Lowercase, singular, hyphenated
    source TEXT                          -- frontmatter, inline, org-tag
);

-- Extracted terms for similarity matching
CREATE TABLE terms (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    term TEXT NOT NULL,
    frequency INTEGER DEFAULT 1,
    is_entity BOOLEAN DEFAULT FALSE,
    entity_type TEXT                     -- person, org, concept
);
```

#### 3.2 GTD Tables

```sql
-- Org-mode TODO items
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    org_id TEXT,                         -- Org-mode ID property
    state TEXT NOT NULL,                 -- TODO, NEXT, WAITING, DONE, CANCELLED
    heading TEXT NOT NULL,
    level INTEGER,                       -- Heading level (1, 2, 3...)
    priority TEXT,                       -- A, B, C
    scheduled DATE,
    deadline DATE,
    closed_at TIMESTAMP,
    category TEXT,                       -- CATEGORY property
    effort INTEGER,                      -- EFFORT in minutes
    tags TEXT,                           -- :tag1:tag2: format
    properties JSON,                     -- All properties as JSON
    parent_id INTEGER REFERENCES tasks(id),
    project_id INTEGER REFERENCES projects(id),
    space TEXT,
    source_file TEXT NOT NULL,           -- inbox.org, next_actions.org, etc.
    line_number INTEGER,                 -- For write-back positioning
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- PROJECT entries
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES files(id),
    org_id TEXT,
    name TEXT NOT NULL,
    status TEXT,                         -- ACTIVE, SOMEDAY, COMPLETED, CANCELLED
    category TEXT,
    outcome TEXT,                        -- Desired outcome
    next_action_id INTEGER REFERENCES tasks(id),
    oldest_task_date DATE,               -- For stale project detection
    space TEXT,
    source_file TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Inbox entries (before processing)
CREATE TABLE inbox_entries (
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    source TEXT,                         -- capture method: voice, email, manual
    raw_content TEXT,                    -- Original unprocessed
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    routed_to TEXT,                      -- next_actions, calendar, reference, trash
    routed_task_id INTEGER REFERENCES tasks(id),
    space TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Habit tracking
CREATE TABLE habits (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES files(id),
    name TEXT NOT NULL,
    frequency TEXT,                      -- daily, weekly, .+2d (org syntax)
    scheduled_days TEXT,                 -- Mon,Wed,Fri
    last_completion DATE,
    streak INTEGER DEFAULT 0,
    total_completions INTEGER DEFAULT 0,
    space TEXT,
    source_file TEXT,
    created_at TIMESTAMP
);
```

#### 3.3 Journal Tables

```sql
-- Daily journal entries
CREATE TABLE journal_entries (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES files(id),
    date DATE NOT NULL,
    space TEXT,                          -- personal, datafund, datacore
    type TEXT,                           -- daily, team-journal
    content TEXT,
    word_count INTEGER,
    session_count INTEGER,
    source_file TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Work sessions within journals
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    journal_id INTEGER REFERENCES journal_entries(id) ON DELETE CASCADE,
    title TEXT,                          -- Session: [title]
    goal TEXT,                           -- Extracted from **Goal:** line
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    duration_minutes INTEGER,
    space TEXT,
    session_type TEXT,                   -- coding, research, meeting, admin
    content TEXT,                        -- Full session content
    created_at TIMESTAMP
);

-- Accomplishments per session
CREATE TABLE accomplishments (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    category TEXT,                       -- feature, fix, docs, refactor
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Files modified per session
CREATE TABLE files_modified (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    change_type TEXT,                    -- created, modified, deleted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Decisions captured
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id),
    file_id INTEGER REFERENCES files(id),
    description TEXT NOT NULL,
    rationale TEXT,
    reversible BOOLEAN DEFAULT TRUE,
    affects TEXT,                        -- What this decision impacts
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trading journal entries
CREATE TABLE trading_entries (
    id INTEGER PRIMARY KEY,
    journal_id INTEGER REFERENCES journal_entries(id),
    date DATE NOT NULL,
    session_type TEXT,                   -- pre-market, during, post-market
    emotional_state INTEGER,             -- 1-10 scale
    emotional_notes TEXT,
    framework_violations JSON,           -- Array of violations
    position_changes JSON,               -- Array of changes
    pnl_realized DECIMAL,
    pnl_unrealized DECIMAL,
    imr DECIMAL,                         -- Initial Margin Ratio
    phs INTEGER,                         -- Position Health Score
    notes TEXT,
    created_at TIMESTAMP
);
```

#### 3.4 System Tables

```sql
-- Agents, commands, modules, workflows
CREATE TABLE system_components (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,                  -- agent, command, module, workflow
    name TEXT NOT NULL,
    description TEXT,
    path TEXT NOT NULL,
    module TEXT,                         -- Parent module if applicable
    provides JSON,                       -- What this component provides
    dependencies JSON,                   -- What this depends on
    triggers JSON,                       -- Natural language triggers (commands)
    when_to_use TEXT,
    space TEXT,                          -- NULL = core, else space-specific
    version TEXT,
    source_file TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(type, name, space)
);

-- Datacore Improvement Proposals
CREATE TABLE dips (
    id INTEGER PRIMARY KEY,
    number INTEGER UNIQUE NOT NULL,
    title TEXT NOT NULL,
    status TEXT,                         -- Draft, Proposed, Accepted, Implemented, Rejected
    abstract TEXT,
    affects JSON,                        -- Components affected
    related_specs JSON,                  -- Related specifications
    related_dips JSON,                   -- Related DIPs
    author TEXT,
    source_file TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Specifications
CREATE TABLE specs (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,                       -- agent, workflow, schema, integration
    version TEXT,
    content TEXT,
    related_dips JSON,
    source_file TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Learning entries (patterns, corrections, preferences)
CREATE TABLE learning_entries (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,                  -- pattern, correction, preference
    title TEXT,
    content TEXT NOT NULL,
    source_session INTEGER REFERENCES sessions(id),
    source_file TEXT,
    tags JSON,
    applies_to JSON,                     -- Which agents/contexts this applies to
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Scaffolding requirements (DIP-0003)
CREATE TABLE scaffolding_requirements (
    id INTEGER PRIMARY KEY,
    space TEXT NOT NULL,
    category TEXT NOT NULL,              -- gtd, knowledge, projects, etc.
    document TEXT NOT NULL,              -- zettel, overview, process, etc.
    status TEXT,                         -- exists, missing, stub, outdated
    file_path TEXT,                      -- Path if exists
    coverage_score DECIMAL,              -- 0-100
    last_checked TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Context metadata (CLAUDE.md sync state)
CREATE TABLE context_metadata (
    id INTEGER PRIMARY KEY,
    space TEXT,                          -- NULL = root
    file_path TEXT NOT NULL,
    line_count INTEGER,
    agent_count INTEGER,
    command_count INTEGER,
    module_count INTEGER,
    checksum TEXT,
    verified_date TIMESTAMP,
    sync_status TEXT,                    -- current, stale, drift
    issues JSON,                         -- Array of detected issues
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Topic clusters (for future topic-weaver)
CREATE TABLE topics (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES topics(id),
    file_count INTEGER DEFAULT 0,
    status TEXT,                         -- active, archived
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE topic_members (
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    relevance_score DECIMAL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (topic_id, file_id)
);
```

#### 3.5 Sync Tracking Tables

```sql
-- Track pending write-backs to source files
CREATE TABLE pending_writes (
    id INTEGER PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    operation TEXT NOT NULL,             -- insert, update, delete
    changes JSON,                        -- What changed
    target_file TEXT NOT NULL,
    status TEXT DEFAULT 'pending',       -- pending, applied, failed, conflict
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_at TIMESTAMP
);

-- File change detection
CREATE TABLE file_checksums (
    path TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    indexed_at TIMESTAMP NOT NULL,
    modified_at TIMESTAMP                -- File system mtime
);

-- Sync history
CREATE TABLE sync_history (
    id INTEGER PRIMARY KEY,
    sync_type TEXT,                      -- full, incremental, write-back
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    files_scanned INTEGER,
    files_updated INTEGER,
    writes_applied INTEGER,
    errors JSON,
    status TEXT                          -- success, partial, failed
);
```

### 4. Bidirectional Sync Protocol

#### 4.1 File → Database (Indexing)

```
INDEXING PIPELINE
─────────────────

1. SCAN
   ├── Glob for *.md, *.org, *.yaml files
   ├── Compare checksums with file_checksums table
   └── Identify: new, modified, deleted

2. PARSE (per file type)
   ├── Markdown: frontmatter, content, links, tags
   ├── Org-mode: headings, properties, states, timestamps
   ├── YAML: structured config data
   └── Extract: type, author, relationships

3. INDEX
   ├── Upsert to appropriate tables
   ├── Update FTS index
   ├── Resolve links where possible
   └── Update file_checksums

4. POST-PROCESS
   ├── Calculate derived fields (oldest_task_date, session_count)
   ├── Update topic memberships
   └── Sync space DB to root DB
```

**Incremental sync** (default): Only process changed files
**Full sync**: Rebuild entire database from scratch

#### 4.2 Database → File (Write-back)

```
WRITE-BACK PROTOCOL
───────────────────

1. AGENT WRITES TO DB
   ├── Agent calls: INSERT/UPDATE/DELETE on task/inbox/etc.
   ├── Trigger creates entry in pending_writes
   └── Returns immediately (async write-back)

2. WRITE-BACK ENGINE
   ├── Process pending_writes queue
   ├── For each pending write:
   │   ├── Read current file content
   │   ├── Validate no conflicts (checksum match)
   │   ├── Apply change to file content
   │   ├── Write file atomically
   │   └── Update pending_writes status

3. CONFLICT RESOLUTION
   ├── If checksum mismatch:
   │   ├── Re-index file to get current state
   │   ├── Attempt merge if possible
   │   ├── Else: mark as conflict, require manual resolution
   │   └── Log to sync_history.errors

4. ORG-MODE SPECIFIC
   ├── State changes: Update TODO keyword
   ├── Property changes: Modify :PROPERTIES: drawer
   ├── New task: Insert at correct hierarchy level
   ├── Task move: Update both source and target files
   └── Preserve formatting, blank lines, structure
```

#### 4.3 Write-Back Triggers

Agents that can write to DB:

| Agent | Write Operations |
|-------|------------------|
| `gtd-inbox-processor` | INSERT task, UPDATE inbox_entry.processed |
| `gtd-inbox-coordinator` | UPDATE inbox_entry.processed (batch) |
| `ai-task-executor` | UPDATE task.state (TODO→DONE) |
| `gtd-project-manager` | UPDATE project.status, task.state |
| `session-learning` | INSERT learning_entry |

#### 4.4 Transaction Safety

```sql
-- Example: Process inbox entry atomically
BEGIN TRANSACTION;

-- 1. Insert new task
INSERT INTO tasks (state, heading, category, source_file, ...)
VALUES ('TODO', 'Review proposal', 'Work', 'next_actions.org', ...);

-- 2. Mark inbox entry as processed
UPDATE inbox_entries
SET processed = TRUE,
    routed_to = 'next_actions',
    routed_task_id = last_insert_rowid()
WHERE id = ?;

-- 3. Queue write-back
INSERT INTO pending_writes (table_name, record_id, operation, target_file, changes)
VALUES
    ('tasks', last_insert_rowid(), 'insert', 'next_actions.org', '{"heading": "Review proposal", ...}'),
    ('inbox_entries', ?, 'delete', 'inbox.org', '{"id": ?}');

COMMIT;
```

### 5. Agent Integration

#### 5.1 Agent Query Patterns

| Agent | Current Approach | DB Query |
|-------|-----------------|----------|
| **ai-task-executor** | `grep -r ":AI:" *.org` | `SELECT * FROM tasks WHERE tags LIKE '%:AI:%' AND state='TODO' ORDER BY priority` |
| **gtd-inbox-coordinator** | Read inbox.org, count entries | `SELECT COUNT(*) FROM inbox_entries WHERE processed=false` |
| **gtd-inbox-processor** | Parse org, find category section | `SELECT * FROM tasks WHERE category=? AND heading LIKE ?` |
| **gtd-data-analyzer** | Grep journals, manual math | `SELECT category, COUNT(*), SUM(effort) FROM tasks WHERE closed_at BETWEEN ? AND ? GROUP BY category` |
| **gtd-project-manager** | Parse org for PROJECT + WAITING | `SELECT p.*, t.heading as blocker FROM projects p LEFT JOIN tasks t ON t.project_id=p.id AND t.state='WAITING'` |
| **gtd-research-processor** | Glob zettels, grep content | `SELECT * FROM files WHERE type='zettel' AND content_fts MATCH ?` |
| **session-learning** | Read journals, grep patterns | `SELECT * FROM learning_entries WHERE type='pattern' AND tags @> ?` |
| **context-maintainer** | Count files, parse CLAUDE.md | `SELECT * FROM context_metadata WHERE space IS NULL` |
| **scaffolding-auditor** | Multi-file scan | `SELECT * FROM scaffolding_requirements WHERE space=? AND status='missing'` |

#### 5.2 Agent Migration Path

```
PHASE 1: Read-only queries (no behavior change)
├── Add DB query as alternative to file parsing
├── Validate results match existing approach
├── Log discrepancies for debugging

PHASE 2: Primary DB, file fallback
├── Query DB first
├── Fall back to file parsing if DB unavailable
├── Remove file parsing after confidence period

PHASE 3: Full DB integration
├── Use DB for all reads
├── Use write-back for modifications
├── File access only for rebuild/validation
```

#### 5.3 Query Library

```python
# .datacore/lib/db_queries.py

class DatacoreDB:
    """Standard queries for agent use."""

    def get_ai_tasks(self, space=None):
        """Tasks tagged with :AI: awaiting processing."""

    def get_inbox_entries(self, processed=False):
        """Inbox entries, optionally filtered."""

    def get_tasks_by_category(self, category, states=['TODO', 'NEXT']):
        """Tasks in a specific category."""

    def get_project_status(self, project_id):
        """Project with related tasks and blockers."""

    def search_content(self, query, types=None, spaces=None):
        """Full-text search across all content."""

    def get_similar_notes(self, file_id, limit=5):
        """Notes similar to given file (shared terms)."""

    def get_session_stats(self, date_from, date_to):
        """Aggregate session statistics."""

    def get_learning_patterns(self, tags=None, limit=10):
        """Recent learning patterns, optionally by tag."""
```

### 6. Workflow Integration

#### 6.1 /today (Morning Briefing)

```
/today WORKFLOW
───────────────

1. Git pull (existing)

2. DB SYNC (NEW)
   python zettel_db.py sync --incremental

   Output:
   ├── Files scanned: 847
   ├── Files updated: 12
   ├── New since yesterday: 3
   └── Sync time: 2.3s

3. QUERY INSIGHTS (NEW)
   ├── Pending AI tasks: SELECT COUNT(*) FROM tasks WHERE tags LIKE '%:AI:%'
   ├── Inbox size: SELECT COUNT(*) FROM inbox_entries WHERE processed=false
   ├── Sessions yesterday: SELECT * FROM sessions WHERE date = DATE('now', '-1 day')
   ├── Patterns to apply: SELECT * FROM learning_entries WHERE created_at > DATE('now', '-7 days')
   └── Stale projects: SELECT * FROM projects WHERE oldest_task_date < DATE('now', '-14 days')

4. Generate briefing (existing + DB insights)
```

#### 6.2 /wrap-up (Session Close)

```
/wrap-up WORKFLOW
─────────────────

1-5. Existing steps (continuation, learning, journal)

6. INDEX SESSION (NEW)
   python zettel_processor.py --session

   ├── Parse journal for ## Session: headers
   ├── Extract goals, accomplishments, files modified
   ├── INSERT INTO sessions, accomplishments, files_modified
   └── Update journal_entries.session_count

7. EXTRACT LEARNINGS (NEW)
   ├── Parse session for patterns, corrections
   ├── INSERT INTO learning_entries
   └── Update learning files (write-back)

8. Git push (existing)
```

#### 6.3 /tomorrow (End of Day)

```
/tomorrow WORKFLOW
──────────────────

1. Git verify (existing)

2. DAY SUMMARY (NEW)
   SELECT
     COUNT(*) as tasks_completed,
     SUM(effort) as total_effort,
     COUNT(DISTINCT session_id) as sessions
   FROM tasks t
   JOIN sessions s ON DATE(t.closed_at) = s.date
   WHERE DATE(t.closed_at) = DATE('now')

3. AI DELEGATION (existing + DB routing)
   ├── Query pending AI tasks
   ├── Route based on task_routing_rules
   └── Update task properties (AI_SCHEDULED, AI_AGENT)

4. Git push if needed (existing)
```

### 7. Diagnostic Integration

Add new section to `/diagnostic`:

```
KNOWLEDGE DATABASE
──────────────────
Root DB: ~/.datacore/knowledge.db
  Size................... 12.4 MB
  Last sync.............. 2025-12-02 14:30:22
  Age.................... 2 hours
  Status: CURRENT

Sync History (last 7 days):
  Full syncs............ 1
  Incremental syncs..... 14
  Write-backs........... 23
  Conflicts............. 0

Index Statistics:
  ┌─────────────────────────────────────────────┐
  │ Content          │ Count  │ Δ 7d │ Space   │
  ├─────────────────────────────────────────────┤
  │ Files            │    847 │  +12 │ all     │
  │ Tasks            │    234 │  -18 │ all     │
  │ Sessions         │    156 │   +7 │ all     │
  │ Learning entries │     89 │   +3 │ all     │
  │ Links            │   2341 │  +45 │ all     │
  └─────────────────────────────────────────────┘

Health Checks:
  FTS index.............. OK (last rebuild: 2025-12-01)
  Link resolution........ 94% (143 unresolved)
  Orphan notes........... 7
  Pending write-backs.... 0
  Failed write-backs..... 0

Space Coverage:
  ┌─────────────────────────────────────────────┐
  │ Space     │ Files │ Tasks │ Last Sync      │
  ├─────────────────────────────────────────────┤
  │ personal  │   423 │   156 │ 2 hours ago    │
  │ datafund  │   298 │    52 │ 2 hours ago    │
  │ datacore  │   126 │    26 │ 2 hours ago    │
  └─────────────────────────────────────────────┘

Alerts:
  ⚠ 2 specs not updated in >180 days
  ⚠ 143 unresolved wiki-links
```

#### 7.1 Alert Thresholds

| Metric | OK | Warning | Critical |
|--------|-----|---------|----------|
| DB age | ≤4 hours | 4-24 hours | >24 hours |
| Unresolved links | <50 | 50-100 | >100 |
| Orphan notes | <10 | 10-25 | >25 |
| Pending writes | 0 | 1-5 | >5 |
| Failed writes | 0 | 1 | >1 |
| Stale specs | 0 | 1-3 | >3 |

### 8. CLI Interface

#### 8.1 zettel_db.py Commands

```bash
# Sync operations
python zettel_db.py sync [--space SPACE] [--full]
python zettel_db.py rebuild [--space SPACE]
python zettel_db.py write-back [--dry-run]

# Query operations
python zettel_db.py search <query> [--type TYPE] [--space SPACE]
python zettel_db.py stats [--space SPACE] [--json]
python zettel_db.py unresolved [--space SPACE]
python zettel_db.py orphans [--space SPACE]
python zettel_db.py stale [--days DAYS] [--type TYPE]

# Validation
python zettel_db.py validate [--fix]
python zettel_db.py integrity
python zettel_db.py diff [--since TIMESTAMP]

# Maintenance
python zettel_db.py vacuum
python zettel_db.py reindex-fts
python zettel_db.py clear-pending
```

#### 8.2 New zettel_processor.py Commands

```bash
# Content processing
python zettel_processor.py --full-process [--space SPACE]
python zettel_processor.py --session [--date DATE]
python zettel_processor.py --org-sync [--file FILE]
python zettel_processor.py --learning-extract [--session-id ID]

# Stubs and backlinks
python zettel_processor.py --create-stubs [--min-refs N]
python zettel_processor.py --inject-backlinks
```

### 9. Rebuild Guarantee

The database can always be completely rebuilt from source files:

```bash
# Full rebuild (drops all data, re-indexes everything)
python zettel_db.py rebuild

# Output:
Rebuilding knowledge database...
  Dropping existing tables... done
  Initializing schema... done
  Scanning files...
    personal: 423 files
    datafund: 298 files
    datacore: 126 files
  Parsing content... 847/847
  Resolving links... 2341 links, 94% resolved
  Building FTS index... done
  Calculating statistics... done

Rebuild complete in 28.4 seconds
  Files indexed: 847
  Tasks parsed: 234
  Sessions extracted: 156
  Links resolved: 2198/2341 (94%)
```

**Rebuild triggers:**
- Schema migration (new DIP version)
- Database corruption detected
- Integrity check failures
- Manual request (`zettel_db.py rebuild`)
- First run in new environment

**What is NOT lost on rebuild:**
- All source files (markdown, org, yaml)
- Learning patterns (in markdown files)
- All content (preserved in source)

**What IS lost on rebuild:**
- Computed statistics (recalculated)
- Resolved link cache (re-resolved)
- Sync history (fresh start)

### 10. Implementation Roadmap

#### Phase 1: GTD/Org-mode (Week 1-2)

**Deliverables:**
- [ ] Org-mode parser for tasks, projects, inbox
- [ ] tasks, projects, inbox_entries, habits tables
- [ ] Basic sync: file → DB
- [ ] Query library for GTD agents
- [ ] Update ai-task-executor to use DB

**Agent impact:** ai-task-executor, gtd-inbox-*, gtd-project-manager

#### Phase 2: Journals (Week 2-3)

**Deliverables:**
- [ ] Journal parser (session extraction)
- [ ] journal_entries, sessions, accomplishments, files_modified tables
- [ ] trading_entries table (trading module)
- [ ] Session indexing in /wrap-up
- [ ] Update gtd-data-analyzer to use DB

**Agent impact:** session-learning, gtd-data-analyzer

#### Phase 3: System (Week 3-4)

**Deliverables:**
- [ ] system_components table (agents, commands, modules)
- [ ] dips, specs tables
- [ ] learning_entries table
- [ ] scaffolding_requirements table
- [ ] context_metadata table
- [ ] Update context-maintainer, scaffolding-auditor

**Agent impact:** context-maintainer, scaffolding-auditor

#### Phase 4: Integration (Week 4-5)

**Deliverables:**
- [ ] Bidirectional sync engine
- [ ] pending_writes table and write-back processor
- [ ] /today DB sync integration
- [ ] /wrap-up session indexing
- [ ] /tomorrow day summary queries
- [ ] /diagnostic database section

**Workflow impact:** /today, /wrap-up, /tomorrow, /diagnostic

#### Phase 5: Polish (Week 5-6)

**Deliverables:**
- [ ] CLI improvements
- [ ] Error handling and logging
- [ ] Performance optimization
- [ ] Documentation
- [ ] Migration guide for existing data

### 11. Security Considerations

- **No secrets in DB**: Env files, credentials excluded from indexing
- **Space isolation**: Space DBs don't leak to other spaces
- **Write-back validation**: Checksums prevent stale writes
- **Backup**: DB is derivable, but recommend backing up for speed

### 12. Performance Considerations

- **Incremental sync**: Only process changed files (checksum-based)
- **FTS optimization**: Separate FTS table with triggers
- **Index on common queries**: space, type, state, date columns
- **Connection pooling**: Reuse connections across agent calls
- **Async write-back**: Don't block agents on file writes

### 13. Future Extensions

- **Vector embeddings**: Semantic search via embeddings table
- **Graph queries**: Relationship traversal for knowledge graph
- **Analytics dashboard**: Web UI for metrics visualization
- **Multi-device sync**: Conflict resolution across devices
- **AI query interface**: Natural language to SQL translation

## References

- DIP-0002: Layered Context Pattern
- DIP-0003: Space Scaffolding
- Existing implementation: `.datacore/lib/zettel_db.py`, `.datacore/lib/zettel_processor.py`

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-02 | 0.1 | Initial draft |
