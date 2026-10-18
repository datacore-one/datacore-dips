# DIP-0017: Outbox & Archive Pattern

| Field | Value |
|-------|-------|
| **DIP** | 0017 |
| **Title** | Outbox & Archive Pattern |
| **Author** | Datacore Team |
| **Type** | Core |
| **Status** | Implemented |
| **Created** | 2025-12-22 |
| **Updated** | 2026-10-18 |
| **Tags** | `outbox`, `archive`, `organization`, `routing` |
| **Affects** | All spaces, nightshift server |
| **Specs** | `datacore-specification.md`, `DIP-0015` |
| **Agents** | `outbox-processor`, `archive-indexer` |

## Summary

Defines an **outbox pattern** for routing content out of active workspaces, with archive as the primary destination. Each space has one exit folder, `4-archive/`, the counterpart of `0-inbox/`:

- `0-inbox/` = Content coming IN (capture, import, processing queue)
- `4-archive/` = Content going OUT (finished work, kept under its original path)

The outbox processor supports modular routing destinations. Archive (permanent storage in a per-space archive repo) is implemented first; other destinations (delivery, publish, dispose) are TBD.

## Amendment 2026-10-18: one exit folder, `4-archive/`

The original text renamed `4-archive/` to `4-outbox/`, with old content in `4-outbox/archive/`. That rename was never finished: every space ended up with both folders, and five scripts kept writing to `4-archive/`. The owner decided (space-structure decisions, 2026-10-18) to keep **only `4-archive/`**, since no workflow needed a separate outbox:

1. `4-archive/` is the single exit folder. `4-outbox/` is not an allowed space folder; the structure checker, the space pre-commit hook and the conformance test refuse it.
2. Everything that was in `4-outbox/archive/` moved to the same relative path under `4-archive/` (`.datacore/lib/merge_outbox_into_archive.py`, which refuses to overwrite).
3. The outbox processor (`archive_sync.py`) reads `4-archive/`. The folder's own top-level `_index.md` and `README.md` stay in the space.
4. Shipping to archive repos stays part of the pattern, and the owner chose to set it up. A non-dry run copies content to the archive repo and **deletes the local copy**, so it is never scheduled unattended: each space gets a dry run first, and the owner says go.
5. `_routing.yaml` copies were dropped: nothing read them. Per-space routing rules return with the first destination that needs them.

Where the text below says `4-outbox/` or `4-outbox/archive/`, read `4-archive/`.

## Agent Context

This section helps agents understand when and how to apply this DIP.

### When to Reference This DIP

**Always reference when:**
- Moving content to archive
- Processing `4-archive/` folders
- Setting up archive repos on nightshift server
- Searching archived content
- Determining if content should leave active workspace

**Key decisions this DIP informs:**
- Content leaving active workspace goes through `4-archive/`, NOT direct deletion
- Archive is permanent storage, no automatic retention cleanup
- Archive repos live on server, not local machines (unless local-only deployment)
- Search archived content via datacortex snapshot

### Quick Reference for Agents

| Question | Answer |
|----------|--------|
| What is the exit folder? | `4-archive/` (amended 2026-10-18; there is no `4-outbox/`) |
| Where do archived files go? | `4-archive/<original path>` → processed to the archive repo on the owner's go |
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
| `knowledge-extractor` | Routing historical content to outbox |

### Integration Points

- **[DIP-0003: Scaffolding](./DIP-0003-scaffolding-pattern.md)** - Archive criteria per category
- **Datacortex module** - Archive search indexing (supersedes DIP-0004)
- **[DIP-0009: GTD](./DIP-0009-gtd-specification.md)** - Outbox as final processing stage
- **[DIP-0011: Nightshift](./DIP-0011-nightshift-module.md)** - Server-side archive processing
- **[DIP-0015: Semantic Org](./DIP-0015-semantic-organization.md)** - Folder structure (4-archive)
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
0-inbox/    = Content coming IN  (capture, import, processing queue)
4-archive/  = Content going OUT  (archive; delivery and publication TBD)
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
└── 4-archive/               # OUT: the single exit folder (amended 2026-10-18)
    ├── _index.md            # Stays in the space
    └── <original path>/     # Archived content, queue for the archive repo
```

**Amended 2026-10-18**: the planned rename to `4-outbox/` is withdrawn; `4-archive/` stays.

#### Numbering Convention (Updated)

| Prefix | Stage | Purpose |
|--------|-------|---------|
| `0-` | Capture | Inbox, unprocessed items |
| `1-` | Active | Current work, tracks |
| `2-` | Projects | Code repositories |
| `3-` | Knowledge | Permanent reference |
| `4-` | **Archive** | Routing OUT (the single exit folder) |

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
│   └── 4-archive/           │   └── 4-archive/
│                            ├── 0-personal-archive/  ← separate repo
├── 1-datafund/              ├── 1-datafund/
│   └── 4-archive/           ├── 1-datafund-archive/
└── ...                      └── ...

Flow: Local 4-archive/ → sync → Server processes → Archive repo
```

**Option B: Local Archive (No Server)**

```
Local machine:
~/Data/
├── 0-personal/
│   └── 4-archive/
├── .datacore/archives/      # Local archive repos
│   ├── 0-personal-archive/
│   └── 1-datafund-archive/
└── ...

Flow: Local 4-archive/ → /outbox command → Local archive repo
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

1. User moves content to `4-archive/`
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
├── Scans 4-archive/ in all spaces
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

1. ~~Rename `4-archive/` to `4-outbox/` in all spaces~~ (withdrawn 2026-10-18: `4-archive/` stays)
2. ~~Create `4-outbox/archive/` subfolder in each space~~ (withdrawn 2026-10-18)
3. Update DIP-0015 folder structure documentation
4. Add outbox configuration to `settings.yaml`
5. Create archive repos on nightshift server
6. Update sync script for archive handling

### New Components

| Component | Type | Purpose |
|-----------|------|---------|
| `4-archive/` | Folder | The single exit folder (amended 2026-10-18) |
| `[space]-archive/` | Git repo | Separate archive storage |
| `outbox-processor` | Agent | Routes outbox content |
| `archive-indexer` | Agent | Maintains searchable index |
| `/outbox` | Command | Process outbox queue |
| `/archive-search` | Command | Search archived content |
| `_datacortex/` | Folder | Archive search snapshot |

### Interface Changes

- `/outbox` - New command to process outbox queue
- `/archive-search` - New command to search archives
- `4-archive/` stays the exit folder (the rename to `4-outbox/` was withdrawn 2026-10-18)

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

**Amended 2026-10-18**: spaces that had both folders fold `4-outbox/` into `4-archive/`:

1. `python3 .datacore/lib/merge_outbox_into_archive.py <space> --dry-run`, then without `--dry-run` (it refuses to overwrite, and names any loose entry that needs a `--route`)
2. Commit the move in the space with explicit paths
3. Shipping to archive repos: `/outbox --dry-run` per space, then a real run only on the owner's go. No content leaves a space until then.

## Security Considerations

- Archive repos use same git authentication as main repos
- Datacortex snapshot contains embeddings, not raw content
- No sensitive content leaves local machine without explicit action
- Archive repos can be encrypted if needed

## Implementation

### Reference Implementation

Phases completed:

1. **Phase 1** ✓: Write DIP-0017, create outbox module skeleton
2. **Phase 2** ✗: Rename `4-archive/` → `4-outbox/` in all spaces — never finished; withdrawn 2026-10-18 (both folders folded into `4-archive/`)
3. **Phase 3** ✓: Create archive repos on nightshift server
4. **Phase 4** ✓: Implement outbox-processor agent (DIP-0016 compliant)
5. **Phase 5** ✓: Implement archive search with datacortex
6. **Phase 6** ✓: Documentation and migration guide

### Rollout Plan

1. Create DIP and module structure
2. Update DIP-0015 folder structure
3. Rename folders in existing spaces
4. Set up server-side archive repos
5. Test full archive workflow
6. Document and announce

## Implementation Status
_Last audited: 2026-03-04_

### Implemented

| Feature | Evidence |
|---------|----------|
| Module structure (v1.1.0) | `modules/outbox/module.yaml` with tools, skills, agents, commands |
| Single exit folder `4-archive/` (amended 2026-10-18) | No space has `4-outbox/`; `test_dip_0017_no_space_has_a_second_exit_folder` |
| Server-side archive repos | `nightshift:~/Data/{0-personal,1-datafund,2-datacore}-archive.git` |
| `outbox-processor` agent | `modules/outbox/agents/outbox-processor.md` — routes `4-archive/` to server repos |
| `archive-indexer` agent | `modules/outbox/agents/archive-indexer.md` — builds datacortex snapshot for search |
| `/outbox` command | `modules/outbox/commands/outbox.md` — `--dry-run`, `--space`, `--verbose` options |
| `/archive-search` command | `modules/outbox/commands/archive-search.md` — queries via datacortex snapshot |
| `archive_sync.py` library | `modules/outbox/lib/archive_sync.py` — server and local modes |
| `archive_search.py` library | `modules/outbox/lib/archive_search.py` — archive index search |
| Nightshift scheduling | `module.yaml` nightshift section: `process-outbox` nightly, `index-archives` weekly |
| MCP tools: `pending`, `archive_search` | 2 tools registered in `module.yaml` |
| Skill: `archive-search` | 1 skill registered in `module.yaml` |

### Implemented (promoted)

| Feature | Evidence |
|---------|----------|
| Datacortex snapshot verification | `archive-indexer` agent builds and verifies datacortex snapshots for archive search |

### Future Work
_Items below are outside v1.0 scope. They remain specified for future implementation._

| Feature | Rationale |
|---------|-----------|
| `delivery` routing destination | No external delivery targets defined yet |
| `publish` routing destination | Publishing handled via comms module instead |
| `dispose` routing destination | Manual deletion preferred for safety |
| Git LFS for archive repos | Not yet needed at current archive sizes |

### Resolved Questions

| Question | Resolution |
|----------|------------|
| Modular routing? | Yes — archive implemented first; other destinations as separate modules when needed |
| Server or local? | Server recommended (`archive_location: server` default); local option via `local_archive_path` |
| Datacortex snapshot bandwidth? | Open — delta-sync or size budgets not yet specified |

## References

- [DIP-0003: Scaffolding Pattern](./DIP-0003-scaffolding-pattern.md) - Archive criteria
- Datacortex module - Archive search (supersedes DIP-0004)
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
