# DIP-0015: Semantic Organization

| Field | Value |
|-------|-------|
| **DIP** | 0015 |
| **Title** | Semantic Organization |
| **Author** | Datacore Team |
| **Type** | Core |
| **Status** | Draft |
| **Created** | 2025-12-21 |
| **Updated** | 2025-12-21 |
| **Tags** | `organization`, `files`, `structure`, `git-lfs`, `companion` |
| **Affects** | `.gitattributes`, all spaces |
| **Specs** | `datacore-specification.md` |
| **Agents** | `ingest-coordinator`, `ingest-processor`, `structural-integrity` |

## Summary

Formalizes semantic organization in Datacore - the principle that content is organized by **role and purpose**, not by format or size. This DIP covers:

1. **Structure** - Folder conventions for personal and team spaces
2. **File Handling** - Git LFS for large files, companion markdown for non-AI-readable formats
3. **Ingest Workflow** - Automated import with deep knowledge extraction (`/ingest`)
4. **Structural Integrity** - Maintenance and audit system (`/structural-integrity`)

## Agent Context

This section helps agents understand when and how to apply this DIP.

### When to Reference This DIP

**Always reference when:**
- Processing files from external sources (imports, migrations)
- Creating new folders or reorganizing content
- Handling non-markdown files (PDFs, presentations, images)
- Auditing or maintaining folder structure
- Answering questions about where to put things

**Key decisions this DIP informs:**
- File goes in semantic location by role, NOT in format-based folder
- Large files (video, Keynote, PSD) use Git LFS, NOT external storage
- Non-AI-readable files require companion markdown

### Quick Reference for Agents

| Question | Answer |
|----------|--------|
| Personal or org space? | Ask: "If I left, should this stay with the org?" Yes → org, No → personal |
| My notes on org topic? | Personal (0-personal/) - it's your perspective, not official |
| Official company doc? | Org space ([N]-org/) - shared team asset |
| Where does a contract go? | Org: `1-tracks/legal/contracts/[type]/` |
| Does it need a companion? | Only if non-AI-readable (Keynote, PSD, video) |
| Where do old financials go? | Org: `4-archive/finance/statements/[year]/` |
| Personal draft about work? | Personal: `notes/1-active/` - not official yet |
| General concept zettel? | Personal: broader applicability beyond org |
| Org-specific concept zettel? | Org: `3-knowledge/zettel/` - company knowledge |

### Related Agents

| Agent | Uses This DIP For |
|-------|-------------------|
| `ingest-coordinator` | Determining file destinations |
| `ingest-processor` | Creating companions, routing content |
| `structural-integrity` | Auditing organization compliance |
| `session-learning` | Routing zettels to correct space |

### Integration Points

- **[DIP-0003: Scaffolding](./DIP-0003-scaffolding-pattern.md)** - `_index.md` files for navigation
- **[DIP-0009: GTD](./DIP-0009-gtd-specification.md)** - Task capture from ingested docs
- **[DIP-0014: Tags](./DIP-0014-tag-taxonomy.md)** - Tagging ingested content

## Motivation

1. **Folder structure** is documented in multiple places (specs, CLAUDE.md files) with some inconsistencies
2. **File handling** for non-markdown files (PDFs, images, videos) lacks formal guidance
3. AI agents can now read many file formats directly (PDFs, images, spreadsheets)
4. Need clear patterns for large files without fragmenting semantic organization
5. Nightshift server generates content that needs to sync back to local

Current gaps:
- No DIP covers file handling patterns
- Existing `assets/` pattern is minimal ("put assets/ next to content")
- No guidance for large files, companion files, or AI readability

## Specification

### Part 1: Folder Structure

#### Core Principle

Content is organized by **role and purpose**, not by format:
- A contract lives with contracts (whether PDF or markdown)
- A presentation lives with presentations (whether Keynote or PDF)
- An image lives with related content (not in a separate "images" folder)

#### Space Types

**Personal Space (0-personal/)**
```
0-personal/
├── org/                       # GTD system
│   ├── inbox.org              # Single capture point
│   ├── next_actions.org       # Actionable tasks with :AI: tags
│   ├── someday.org            # Future/maybe items
│   ├── research_learning.org  # Reading queue
│   └── habits.org             # Recurring habits
├── notes/                     # PKM (Obsidian)
│   ├── journals/              # Daily journals
│   │   └── YYYY-MM-DD.md
│   ├── 1-active/              # Working notes
│   ├── 2-knowledge/           # Permanent knowledge
│   │   ├── zettel/            # Atomic concepts
│   │   ├── literature/        # Source summaries
│   │   └── reference/         # People, companies
│   ├── 3-archive/             # Old notes
│   └── pages/                 # Topic pages
├── code/                      # Personal projects
├── content/                   # Generated outputs
│   ├── blog/
│   ├── social/
│   └── presentations/
├── .datacore/                 # Configuration
└── CLAUDE.md                  # Personal context
```

**Team Space ([N]-[name]/)**
```
[N]-[name]/
├── org/                       # Task coordination (AI routing layer)
│   ├── inbox.org              # Team task capture
│   └── next_actions.org       # AI task queue
├── journal/                   # Team activity log
│   └── YYYY-MM-DD.md          # Daily entries
├── 0-inbox/                   # Unprocessed items
├── 1-tracks/                  # Active work by department
│   ├── _index.md
│   ├── ops/                   # Operations, OKRs
│   ├── product/               # Product specs, roadmaps
│   ├── dev/                   # Engineering docs
│   ├── legal/                 # Contracts, compliance
│   │   ├── contracts/
│   │   │   ├── _index.md
│   │   │   ├── investors/
│   │   │   ├── employment/
│   │   │   └── partnerships/
│   │   └── opinions/
│   ├── finance/               # Financials, grants
│   │   ├── statements/
│   │   │   ├── 2024/
│   │   │   └── 2025/
│   │   └── grants/
│   ├── research/              # Market research
│   └── comms/                 # Marketing, content
├── 2-projects/                # Code repositories (gitignored)
│   └── _index.md
├── 3-knowledge/               # Permanent knowledge (Zettelkasten)
│   ├── _index.md
│   ├── insights.md            # Strategic observations
│   ├── pages/                 # Topic pages
│   │   ├── _core/             # Vision, strategy
│   │   ├── _fundraising/
│   │   └── _partnerships/
│   ├── zettel/                # Atomic concepts
│   ├── literature/            # Source summaries
│   └── reference/             # People, companies, glossary
├── 4-archive/                 # Historical content
│   ├── _index.md
│   ├── contracts/             # Expired contracts
│   ├── finance/
│   │   └── statements/
│   │       ├── 2018/
│   │       ├── 2019/
│   │       └── ...
│   ├── pitchdecks/            # Superseded decks
│   └── product/
│       └── wireframes/
├── .datacore/                 # Configuration
└── CLAUDE.md                  # Space context
```

#### Numbering Convention

Numbers indicate processing stage:

| Prefix | Stage | Purpose |
|--------|-------|---------|
| `0-` | Capture | Inbox, unprocessed items |
| `1-` | Active | Current work, tracks |
| `2-` | Projects | Code repositories |
| `3-` | Knowledge | Permanent reference |
| `4-` | Archive | Historical content |

#### Canonical Templates

The datacore-org repository contains canonical templates for folder structures. This DIP references those templates as authoritative. Changes to structure should be made in datacore-org first, then referenced here.

### Part 2: File Handling

#### Storage Strategy

**Git LFS** for large files by type. No special folders for binaries.

```
legal/contracts/
├── _index.md
├── acme-corp/
│   ├── investment-agreement.pdf    # Small → git directly
│   └── investment-agreement.md     # Optional companion
└── presentations/
    ├── conference-2024.key         # Large → git LFS
    └── conference-2024.md          # Required companion (non-AI-readable)
```

#### Git LFS Configuration

Create `.gitattributes` in repository root:

```gitattributes
# Video/Audio → Git LFS
*.mp4 filter=lfs diff=lfs merge=lfs -text
*.mov filter=lfs diff=lfs merge=lfs -text
*.m4a filter=lfs diff=lfs merge=lfs -text
*.wav filter=lfs diff=lfs merge=lfs -text
*.mp3 filter=lfs diff=lfs merge=lfs -text

# Presentations → Git LFS
*.key filter=lfs diff=lfs merge=lfs -text
*.pptx filter=lfs diff=lfs merge=lfs -text

# Design files → Git LFS
*.psd filter=lfs diff=lfs merge=lfs -text
*.ai filter=lfs diff=lfs merge=lfs -text
*.sketch filter=lfs diff=lfs merge=lfs -text
*.graffle filter=lfs diff=lfs merge=lfs -text

# Archives → Git LFS
*.zip filter=lfs diff=lfs merge=lfs -text
*.tar.gz filter=lfs diff=lfs merge=lfs -text
```

#### Tier Summary

| Tier | Criteria | Handling |
|------|----------|----------|
| **1** | Small, AI-readable | Git directly, companion optional |
| **2** | Large by type | Git LFS, companion optional |
| **3** | Non-AI-readable | Git (or LFS), companion **required** |

#### AI Readability Reference

**AI-Readable Formats** (Claude can process directly):
- Documents: PDF, TXT, MD, RTF
- Spreadsheets: XLSX, CSV
- Images: PNG, JPG, JPEG, GIF, WebP, SVG
- Code: All text-based formats

**Non-AI-Readable Formats** (require companion):
- Apple formats: Keynote (.key), Pages, Numbers
- Design: PSD, AI, Sketch, Graffle, Figma (local)
- Video/Audio: MP4, MOV, M4A, MP3, WAV
- Archives: ZIP, TAR, DMG
- Binary: Executables, compiled files

#### Companion Markdown

When a file cannot be read by AI, create a companion markdown file with the same name:

```markdown
---
type: document-companion
source: conference-2024.key
format: keynote
size: 63MB
created: 2024-03-15
status: active
ai_readable: false
---

# Conference 2024 Presentation

## Summary
Company presentation at tech conference covering product vision and roadmap.

## Key Slides
1. Company introduction
2. Market thesis
3. Technical architecture
4. Roadmap

## Notes
- Well received, led to follow-up meetings

## Related
- [[presentations/summit-2024]] - Similar deck
- [[1-tracks/comms/events/conference-2024]] - Event notes
```

**Companion frontmatter schema:**

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Always `document-companion` |
| `source` | Yes | Filename of source file |
| `format` | Yes | File format (e.g., `keynote`, `psd`) |
| `size` | No | File size |
| `created` | No | Creation date |
| `status` | No | `active`, `superseded`, `archived` |
| `ai_readable` | No | Boolean, default false for companions |

**When companion is required:**
- Non-AI-readable formats (Keynote, PSD, video, audio)
- Complex documents with obligations to track
- Files needing context for discovery

**When companion is optional:**
- PDFs (Claude reads directly)
- Images (self-explanatory)
- Simple office documents

#### Sync Architecture

With Git LFS, bidirectional sync works automatically:

```
LOCAL                          SERVER (nightshift)
─────────────────────────────────────────────────
User adds files  ──git push──→   Server receives
                                      ↓
                              AI generates content
                              (videos, images, etc.)
                                      ↓
User receives    ←──git pull──   Server commits + pushes
```

**Server requirements:**
1. Git LFS installed
2. `.gitattributes` committed to repo
3. Server can `git add`, `git commit`, `git push` LFS files

### Part 3: Ingest Workflow

Automated import of files into Datacore with deep knowledge extraction - not just file sorting, but reading, analyzing, extracting insights, identifying forgotten opportunities, and discovering tasks.

#### Command: `/ingest`

```
/ingest [optional: folder path]
```

- **Default**: Processes `0-inbox/` folders across all spaces
- **With path**: Processes specified folder (e.g., `~/Documents/Migration/`)

#### 6-Phase Processing Methodology

Each document goes through systematic deep processing:

**Phase 1: READ**
- Read document content (Claude handles PDFs, images, spreadsheets)
- For non-AI-readable formats (Keynote, PSD): extract metadata only
- Note file size, type, date for routing decisions

**Phase 2: ASSESS**
- **Still active/binding?** → `1-tracks/` (contracts, current projects)
- **Reference value?** → `3-knowledge/` (strategic docs, concepts)
- **Historical only?** → `4-archive/` (old statements, superseded)
- **Superseded?** → `4-archive/` with note pointing to replacement

**Relevance assessment by type:**

| Document Type | Key Questions |
|---------------|---------------|
| Contracts | Still in effect? Obligations remaining? |
| Pitch decks | Unique positioning? Historical evolution? |
| Legal opinions | Still valid? Conditions changed? |
| Financial docs | Needed for audits? Pattern value? |
| Product docs | Concepts worth reviving? Lessons learned? |

**Phase 3: EXTRACT**
- Key decisions made
- Commitments/promises (check if fulfilled)
- Concepts worth capturing as zettels
- Strategic insights for `insights.md`
- **Market timing observations** - ideas from 2018 may be viable now

**Phase 4: CAPTURE**
- Tasks discovered → `org/inbox.org`
- Someday items → `org/someday.org` or notes
- Follow-ups needed → `org/inbox.org`

**Phase 5: FILE**
- Move to semantic destination (by role, not format)
- Create companion `.md` if non-AI-readable
- Update `_index.md` for new content

**Phase 6: LINK**
- Connect to related knowledge (wiki-links)
- Reference in relevant track docs
- Tag appropriately per DIP-0014

#### Agent Architecture

```
ingest-coordinator
├── Scans inbox folders or provided path
├── Inventories all items (files + folders)
├── Groups by type/context for batch efficiency
├── Spawns ingest-processor for each item
└── Aggregates results and reports summary

ingest-processor (per item)
├── Phase 1: READ - Analyze content
├── Phase 2: ASSESS - Determine destination
├── Phase 3: EXTRACT - Pull out knowledge
├── Phase 4: CAPTURE - Log tasks/items
├── Phase 5: FILE - Move and create companion
├── Phase 6: LINK - Connect to knowledge graph
└── Returns structured result to coordinator
```

#### Output Artifacts

| Artifact Type | Location | When Created |
|---------------|----------|--------------|
| Zettels | `3-knowledge/zettel/` | Atomic concepts discovered |
| Literature notes | `3-knowledge/literature/` | Significant documents analyzed |
| Insights | `3-knowledge/insights.md` | Strategic observations |
| Tasks | `org/inbox.org` | Follow-ups discovered |
| Companions | Same folder as source | Non-AI-readable files |
| Index updates | `_index.md` files | All new content |

#### Space Routing

Before determining the semantic folder, determine **which space** the content belongs to:

**Routing Decision Tree:**

```
Is this official organizational content?
├── YES → Route to org space (e.g., 1-datafund/)
│   Examples:
│   - Company contracts, agreements
│   - Official financial statements
│   - Brand assets, approved marketing
│   - Team decisions, meeting notes
│   - Product specs, roadmaps
│
└── NO → Route to personal space (0-personal/)
    ├── Personal writings/thoughts about org topics
    ├── Draft ideas not yet shared
    ├── Personal notes from meetings
    ├── Research for personal learning
    └── Any content that is "mine" not "ours"
```

**Key Distinction:**

| Attribute | Personal (0-personal/) | Organizational ([N]-space/) |
|-----------|------------------------|----------------------------|
| **Ownership** | Individual | Team/company |
| **Visibility** | Private by default | Shared with team |
| **Authority** | My perspective | Official position |
| **Examples** | My notes on strategy meeting | Approved strategy document |
| | Draft pitch ideas | Signed investor agreement |
| | Personal research on competitors | Official market analysis |
| | My writings about the company | Published blog posts |

**Routing Examples (Datafund import):**

| File | Route To | Rationale |
|------|----------|-----------|
| `investor-agreement-signed.pdf` | 1-datafund/1-tracks/legal/ | Official binding contract |
| `my-thoughts-on-fundraising.md` | 0-personal/notes/ | Personal perspective |
| `pitch-deck-v3.key` | 1-datafund/1-tracks/comms/ | Official company asset |
| `pitch-ideas-draft.md` | 0-personal/notes/1-active/ | Personal draft, not official |
| `brand-guidelines.pdf` | 1-datafund/3-knowledge/ | Official reference |
| `competitor-notes.md` | Depends on formality | If official analysis → org; if personal research → personal |
| `meeting-notes-2024-03.md` | 1-datafund/journal/ or 0-personal/ | If team meeting notes → org; if personal notes → personal |

**When Unclear:**

1. Ask: "Would this be shared in a team handoff?"
   - Yes → organizational
   - No → personal

2. Ask: "Does this represent the company's position or mine?"
   - Company → organizational
   - Mine → personal

3. Ask: "If I left, should this stay with the org?"
   - Yes → organizational
   - No → personal

**Cross-Space Knowledge:**

When extracting zettels or insights from organizational documents:
- **Zettel about org-specific concept** (e.g., "Verity tokenization model") → org space
- **Zettel about general concept** (e.g., "RWA regulatory framework") → personal space (broader applicability)
- **Personal insight about org topic** → personal space

#### Processing Decisions

| Content Type | Space | Destination | Processing Level |
|--------------|-------|-------------|------------------|
| Active contracts | Org | `1-tracks/legal/contracts/` | Full analysis, extract obligations |
| Current financials | Org | `1-tracks/finance/` | Full analysis |
| Official reference | Org | `3-knowledge/` | Extract zettels, literature notes |
| Personal writings | Personal | `notes/1-active/` or `notes/pages/` | Personal processing |
| Historical/outdated | Org | `4-archive/` | Companion only |
| Personal research | Personal | `notes/2-knowledge/` | Extract personal zettels |
| Large media | Depends | Semantic location | Companion required |

#### Quality Verification

Before marking complete, verify:
- [ ] All files moved to semantic destinations
- [ ] Non-AI-readable files have companions
- [ ] Tasks/obligations captured in inbox
- [ ] `_index.md` files updated
- [ ] Wiki-links created where relevant
- [ ] No files left in source folder

### Part 4: Structural Integrity

Maintenance and audit system for organizational structure, inspired by Star Trek's "structural integrity field."

#### Command: `/structural-integrity`

```
/structural-integrity [check|report|fix]
```

- `check` - Quick scan, return pass/fail with summary
- `report` - Detailed diagnostic of all issues found
- `fix` - Attempt automatic corrections (with confirmation)

#### Detection Rules

| Issue Type | Example | Severity |
|------------|---------|----------|
| **Misplaced files** | PDF in root instead of semantic location | Warning |
| **Missing companions** | `.key` file without `.md` companion | Warning |
| **Orphaned companions** | `.md` companion but source file missing | Error |
| **Missing indexes** | Folder without `_index.md` | Info |
| **Naming violations** | CamelCase instead of kebab-case | Info |
| **Unprocessed inbox** | Items in `0-inbox/` older than 7 days | Warning |
| **Git LFS issues** | Large file not tracked by LFS | Error |
| **Broken links** | Wiki-links to non-existent files | Warning |

#### Agent: `structural-integrity`

```
structural-integrity
├── Scans all spaces in Datacore
├── Checks each folder against expected structure
├── Validates file placement rules
├── Detects companion/source mismatches
├── Checks Git LFS tracking
├── Validates naming conventions
├── Reports findings by severity
└── Optionally auto-fixes (with confirmation)
```

#### Scheduled Runs

- **Nightshift**: Weekly structural integrity check
- **On-demand**: User runs `/structural-integrity`
- **Pre-commit hook**: Optional validation before commits

#### Enforcement

Structural Integrity enforces:
- Part 1 (Structure): Correct folder hierarchy
- Part 2 (File Handling): Companions present, LFS tracking
- Part 3 (Ingest): Inbox freshness, processing status

### Changes Required

1. Create `.gitattributes` in each space root with LFS patterns
2. Install Git LFS on local machines and nightshift server
3. Update existing large files to use LFS: `git lfs migrate`

### New Components

- `.gitattributes` - Git LFS configuration file
- Companion markdown files - For non-AI-readable content
- `/ingest` command - Automated file import with deep processing
- `/structural-integrity` command - Structure audit and maintenance
- `ingest-coordinator` agent - Orchestrates file import
- `ingest-processor` agent - Processes individual items
- `structural-integrity` agent - Audits organizational structure

### Interface Changes

None. Files remain in semantic locations. Git LFS is transparent to users.

## Rationale

**Why semantic organization?**
- Keeps related content together
- Avoids artificial `_files/` or `assets/` segregation
- Future-proof as AI reads more formats

**Why Git LFS instead of external storage?**
- Bidirectional sync (server-generated content)
- Version history preserved
- Works with existing git workflow
- No separate sync mechanism needed

**Why companion markdown?**
- Provides AI context for non-readable files
- Enables discovery and search
- Documents metadata and relationships

## Backwards Compatibility

**No breaking changes.** Existing files remain in place. Git LFS is additive.

For existing large files, run migration:
```bash
git lfs migrate import --include="*.mp4,*.key,*.psd"
```

## Security Considerations

- Git LFS stores files in same repository (same access control)
- Companion files should not contain sensitive content from source files
- `.gitattributes` should be committed (not gitignored)

## Implementation

### Reference Implementation

This branch: `dip-0015-semantic-organization`

### Rollout Plan

1. **Phase 1**: Create `.gitattributes` with LFS patterns ✓
2. **Phase 2**: Install Git LFS on nightshift server
3. **Phase 3**: Migrate existing large files (if any)
4. **Phase 4**: Create ingest agents and command
5. **Phase 5**: Create structural-integrity agent and command
6. **Phase 6**: Document patterns in CLAUDE.md
7. **Phase 7**: Run pilot migration (~/Documents/Datafund)

## Open Questions

1. Should `.gitattributes` be per-space or at root level?
2. What size threshold (if any) should trigger LFS for PDFs?
3. Should companion files use `.companion.md` suffix instead of same name?

## References

- [Git LFS Documentation](https://git-lfs.com/)
- [DIP-0002: Layered Context Pattern](./DIP-0002-layered-context-pattern.md) - Privacy layers for context files
- [DIP-0003: Scaffolding Pattern](./DIP-0003-scaffolding-pattern.md) - Index files and navigation
- [DIP-0009: GTD Specification](./DIP-0009-gtd-specification.md) - GTD workflow and agents
- [DIP-0011: Module System](./DIP-0011-module-system.md) - Module architecture
- `datacore-specification.md` - Current structure documentation

## Related Agents

- `ingest-coordinator.md` - File import orchestrator
- `ingest-processor.md` - Per-item processor
- `structural-integrity.md` - Structure auditor

## Related Commands

- `ingest.md` - `/ingest` command definition
- `structural-integrity.md` - `/structural-integrity` command definition
