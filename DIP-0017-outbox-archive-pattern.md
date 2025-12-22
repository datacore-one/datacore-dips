# DIP-0017: Outbox & Archive Pattern

| Field | Value |
|-------|-------|
| **DIP** | 0017 |
| **Title** | Outbox & Archive Pattern |
| **Author** | Datacore Team |
| **Type** | Core |
| **Status** | Draft |
| **Created** | 2025-12-22 |
| **Updated** | 2025-12-22 |
| **Tags** | `outbox`, `archive`, `organization`, `routing` |
| **Affects** | All spaces, nightshift server |
| **Specs** | `datacore-specification.md`, `DIP-0015` |
| **Agents** | `outbox-processor`, `archive-indexer` |

## Summary

Defines an **outbox pattern** for routing content out of active workspaces, with archive as the primary destination. Reframes `4-archive/` as `4-outbox/` to create symmetry with `0-inbox/`:

- `0-inbox/` = Content coming IN (capture, import, processing queue)
- `4-outbox/` = Content going OUT (archive, delivery, publication)

The outbox supports modular routing destinations. Archive (permanent storage on nightshift server) is implemented first; other destinations (delivery, publish, dispose) are TBD.

## Agent Context

This section helps agents understand when and how to apply this DIP.

### When to Reference This DIP

**Always reference when:**
- Moving content to archive
- Processing `4-outbox/` folders
- Setting up archive repos on nightshift server
- Searching archived content
- Determining if content should leave active workspace

**Key decisions this DIP informs:**
- Content leaving active workspace goes through `4-outbox/`, NOT direct deletion
- Archive is permanent storage, no automatic retention cleanup
- Archive repos live on server, not local machines (unless local-only deployment)
- Search archived content via datacortex snapshot

### Quick Reference for Agents

| Question | Answer |
|----------|--------|
| What replaced 4-archive? | `4-outbox/` - staging for routing OUT |
| Where do archived files go? | `4-outbox/archive/` → processed to server archive repo |
| Is archive permanent? | Yes, no automatic cleanup or retention limits |
| Can I search archives locally? | Yes, via datacortex snapshot (embeddings only) |
| Where are archive repos? | Server: `[space]-archive/` (e.g., `0-personal-archive/`) |
| What about local-only users? | Optional local archive repos at `~/.datacore/archives/` |

### Related Agents

| Agent | Uses This DIP For |
|-------|-------------------|
| `outbox-processor` | Routing content from outbox to destinations |
| `archive-indexer` | Maintaining searchable archive index |
| `structural-integrity` | Checking outbox folder structure |
| `ingest-processor` | Routing historical content to outbox |

### Integration Points

- **[DIP-0003: Scaffolding](./DIP-0003-scaffolding-pattern.md)** - Archive criteria per category
- **[DIP-0004: Datacortex](./DIP-0004-knowledge-database.md)** - Archive search indexing
- **[DIP-0009: GTD](./DIP-0009-gtd-specification.md)** - Outbox as final processing stage
- **[DIP-0011: Nightshift](./DIP-0011-nightshift-module.md)** - Server-side archive processing
- **[DIP-0015: Semantic Org](./DIP-0015-semantic-organization.md)** - Folder structure (4-outbox)
- **[DIP-0016: Agent Registry](./DIP-0016-agent-registry.md)** - New agents registration

## Motivation

1. **Inbox/Outbox Asymmetry**: We have structured intake (`0-inbox/`) but unstructured output (`4-archive/` is a dumping ground)

2. **Archive is not the only exit**: Content may leave workspace for:
   - Permanent storage (archive)
   - External delivery (contractor handoffs)
   - Publication (website, social)
   - Deletion (confirmed disposable)

3. **Archive search is difficult**: Without archives locally, no way to search historical content

4. **No formal archive criteria**: Unclear when content should move from active to archive

Current state:
- `4-archive/` exists but has no processing workflow
- Content sits there indefinitely
- No mechanism for server-side archive storage
- No search capability across archives

## Specification

### Part 1: Conceptual Model

#### Inbox/Outbox Symmetry

```
0-inbox/   = Content coming IN  (capture, import, processing queue)
4-outbox/  = Content going OUT  (archive, delivery, publication)
```

The outbox is a **staging area** for content leaving the active workspace. Like inbox items, outbox items are processed and routed to their destinations.

#### Routing Destinations

| Destination | Purpose | Status |
|-------------|---------|--------|
| **archive** | Permanent storage on server | Implemented (this DIP) |
| **delivery** | External handoff | TBD - modular |
| **publish** | Public release | TBD - modular |
| **dispose** | Deletion queue | TBD - modular |

Each destination is a separate routing module. This DIP implements archive; others are future work.

### Part 2: Folder Structure Changes

#### Space Structure (Updated from DIP-0015)

```
[N]-[name]/
├── 0-inbox/                 # IN: capture, imports
├── 1-tracks/                # Active work
├── 2-projects/              # Code repos
├── 3-knowledge/             # Permanent knowledge
└── 4-outbox/                # OUT: staging for routing (was 4-archive)
    ├── _routing.yaml        # Routing rules for this space
    └── archive/             # Queue for archive repo
```

**Rename only**: `4-archive/` → `4-outbox/`. Existing archive content moves to `4-outbox/archive/`.

#### Numbering Convention (Updated)

| Prefix | Stage | Purpose |
|--------|-------|---------|
| `0-` | Capture | Inbox, unprocessed items |
| `1-` | Active | Current work, tracks |
| `2-` | Projects | Code repositories |
| `3-` | Knowledge | Permanent reference |
| `4-` | **Outbox** | Routing OUT (was Archive) |

### Part 3: Archive Repository

Each space gets a corresponding archive repo on the nightshift server:

```
Server (nightshift):
~/Data/
├── 0-personal/              # Main space (synced)
├── 0-personal-archive/      # Archive repo (separate)
├── 1-datafund/
├── 1-datafund-archive/
└── ...
```

#### Archive Repo Structure

```
[N]-[name]-archive/
├── .git/
├── CLAUDE.md                # Archive-specific context
├── _index.md                # Searchable catalog
├── _datacortex/             # Search snapshot
│   ├── archive.db           # Embeddings
│   └── manifest.yaml        # Content manifest
│
└── [mirrors source structure]
    ├── 1-tracks/
    │   └── legal/
    │       └── contracts/
    │           └── acme-2018.pdf
    ├── 2-projects/
    └── 3-knowledge/
```

#### Deployment Options

**Option A: With Nightshift Server (Recommended)**

```
Local machine:               Nightshift server:
~/Data/                      ~/Data/
├── 0-personal/              ├── 0-personal/
│   └── 4-outbox/            │   └── 4-outbox/
│       └── archive/         ├── 0-personal-archive/  ← separate repo
├── 1-datafund/              ├── 1-datafund/
│   └── 4-outbox/            ├── 1-datafund-archive/
└── ...                      └── ...

Flow: Local 4-outbox/archive/ → sync → Server processes → Archive repo
```

**Option B: Local Archive (No Server)**

```
Local machine:
~/Data/
├── 0-personal/
│   └── 4-outbox/
├── .datacore/archives/      # Local archive repos
│   ├── 0-personal-archive/
│   └── 1-datafund-archive/
└── ...

Flow: Local 4-outbox/archive/ → /outbox command → Local archive repo
```

#### Configuration

In `.datacore/settings.yaml`:

```yaml
outbox:
  archive_location: server    # or "local"
  server_host: "nightshift.example.com"  # if server
  local_archive_path: "~/.datacore/archives"  # if local
```

### Part 4: Archive Workflow

#### Processing Flow

1. User moves content to `4-outbox/archive/`
2. Sync pushes to server (or stays local)
3. Archive processor runs (nightshift or local):
   - Moves files to archive repo
   - Creates/updates `_index.md`
   - Generates datacortex snapshot
4. Files removed from outbox
5. Datacortex snapshot syncs back for search

#### Outbox Processor Agent

```
outbox-processor
├── Scans 4-outbox/archive/ in all spaces
├── For each item:
│   ├── Determines target archive repo
│   ├── Preserves semantic path structure
│   ├── Moves file + companion (if exists)
│   ├── Updates source _index.md (removes entry)
│   └── Updates archive _index.md (adds entry)
├── Commits changes to archive repo
└── Cleans processed items from outbox
```

#### Archive Indexer Agent

```
archive-indexer
├── Runs after outbox-processor completes
├── Scans archive repo content
├── Generates embeddings for search
├── Updates _datacortex/ snapshot
└── Commits snapshot for sync
```

### Part 5: Archive Search

Local search of archived content without full archive clone.

#### Datacortex Snapshot

```
Archive repo:                    Local search:
_datacortex/                     datacortex search --include-archive
├── archive.db                   → Queries server snapshot
├── embeddings.npy               → Returns paths + summaries
└── manifest.yaml                → Can fetch specific files on-demand
```

#### Snapshot Workflow

1. Nightshift indexes archive content (nightly)
2. Creates embeddings snapshot in archive repo `_datacortex/`
3. Snapshot is small (embeddings + metadata, not full content)
4. Local datacortex can query snapshot
5. Full content fetched on-demand if needed

### Part 6: Archive Criteria

Per DIP-0003 Scaffolding categories:

| Category | Keep Active | Archive When |
|----------|-------------|--------------|
| **Identity** | Current versions | Superseded by new version |
| **Strategy** | Current + last revision | Older than 2 revisions |
| **Contracts** | Active + recently expired | Expired > 1 year |
| **Finance** | Current + 2 years | Older than 2 years (audits) |
| **Projects** | Active projects | Completed/abandoned |
| **Media** | Current assets | Superseded versions |
| **Personal** | Manual decision | User moves to outbox |

**No automatic cleanup**: Archive is permanent storage. Manual review only.

### Part 7: Module Structure

```
.datacore/modules/outbox/
├── module.yaml              # Module metadata
├── CLAUDE.base.md           # Module documentation
├── agents/
│   ├── outbox-processor.md  # Routes outbox content
│   └── archive-indexer.md   # Maintains archive index
├── commands/
│   ├── outbox.md            # /outbox - process outbox queue
│   └── archive-search.md    # /archive-search - query archives
├── templates/
│   └── outbox-routing.yaml  # Routing rules template
└── lib/
    └── archive_sync.py      # Cross-repo sync logic
```

### Changes Required

1. Rename `4-archive/` to `4-outbox/` in all spaces
2. Create `4-outbox/archive/` subfolder in each space
3. Update DIP-0015 folder structure documentation
4. Add outbox configuration to `settings.yaml`
5. Create archive repos on nightshift server
6. Update sync script for archive handling

### New Components

| Component | Type | Purpose |
|-----------|------|---------|
| `4-outbox/` | Folder | Replaces `4-archive/`, staging for routing |
| `[space]-archive/` | Git repo | Separate archive storage |
| `outbox-processor` | Agent | Routes outbox content |
| `archive-indexer` | Agent | Maintains searchable index |
| `/outbox` | Command | Process outbox queue |
| `/archive-search` | Command | Search archived content |
| `_datacortex/` | Folder | Archive search snapshot |

### Interface Changes

- `/outbox` - New command to process outbox queue
- `/archive-search` - New command to search archives
- `4-archive/` renamed to `4-outbox/`

## Rationale

**Why outbox instead of archive?**
- Reflects the full content lifecycle (in → process → out)
- Archive is just one destination; outbox supports many
- Creates symmetry with inbox pattern
- More accurate mental model

**Why server-side archive repos?**
- Reduces local storage requirements
- Archives rarely needed immediately
- Datacortex snapshot enables search without full clone
- Git LFS already handles large files

**Why no automatic retention?**
- Archive is permanent historical record
- User should consciously decide what to delete
- Compliance/audit requirements vary
- "Dispose" destination (TBD) handles deletion queue

**Why modular destinations?**
- Different workflows for different exits
- Can implement incrementally
- Each destination has unique requirements
- Keeps archive simple and focused

## Backwards Compatibility

**Rename only**: `4-archive/` → `4-outbox/`

Existing content in `4-archive/` moves to `4-outbox/archive/`. No content is lost or moved to server until explicitly processed.

Migration steps:
1. Rename `4-archive/` to `4-outbox/`
2. Move contents to `4-outbox/archive/` subfolder
3. Run `/outbox` to process to archive repos

## Security Considerations

- Archive repos use same git authentication as main repos
- Datacortex snapshot contains embeddings, not raw content
- No sensitive content leaves local machine without explicit action
- Archive repos can be encrypted if needed

## Implementation

### Reference Implementation

Phases in this branch:

1. **Phase 1**: Write DIP-0017, create outbox module skeleton
2. **Phase 2**: Rename `4-archive/` → `4-outbox/` in all spaces
3. **Phase 3**: Create archive repos on nightshift server
4. **Phase 4**: Implement outbox-processor agent
5. **Phase 5**: Implement archive search with datacortex
6. **Phase 6**: Documentation and migration guide

### Rollout Plan

1. Create DIP and module structure
2. Update DIP-0015 folder structure
3. Rename folders in existing spaces
4. Set up server-side archive repos
5. Test full archive workflow
6. Document and announce

## Open Questions

1. ~~Should routing be modular?~~ **Resolved: Yes, archive first, others TBD**
2. ~~Server or local archives?~~ **Resolved: Server recommended, local option available**
3. How should datacortex snapshot sync work with bandwidth constraints?
4. Should archive repos use Git LFS for all content or only large files?

## References

- [DIP-0003: Scaffolding Pattern](./DIP-0003-scaffolding-pattern.md) - Archive criteria
- [DIP-0004: Knowledge Database](./DIP-0004-knowledge-database.md) - Datacortex search
- [DIP-0009: GTD Specification](./DIP-0009-gtd-specification.md) - Task lifecycle
- [DIP-0011: Nightshift Module](./DIP-0011-nightshift-module.md) - Server processing
- [DIP-0015: Semantic Organization](./DIP-0015-semantic-organization.md) - Folder structure
- [DIP-0016: Agent Registry](./DIP-0016-agent-registry.md) - Agent registration

## Related Agents

- `outbox-processor.md` - Routes content from outbox to destinations
- `archive-indexer.md` - Maintains archive search index

## Related Commands

- `outbox.md` - `/outbox` command definition
- `archive-search.md` - `/archive-search` command definition
