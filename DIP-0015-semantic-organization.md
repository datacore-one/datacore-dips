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
| **Agents** | - |

## Summary

Formalizes semantic organization in Datacore - the principle that content is organized by **role and purpose**, not by format or size. This DIP covers both folder structure conventions and file handling patterns, providing a unified approach to organizing all types of content.

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
├── org/                 # GTD system (inbox, next_actions, someday, habits)
├── notes/               # PKM (journals, pages, zettel, literature, reference)
├── code/                # Personal projects
├── content/             # Generated outputs
├── .datacore/           # Configuration
└── CLAUDE.md            # Personal context
```

**Team Space ([N]-[name]/)**
```
[N]-[name]/
├── org/                 # Task coordination (AI routing layer)
├── journal/             # Team daily log
├── 0-inbox/             # Unprocessed items
├── 1-tracks/            # Active work by department
├── 2-projects/          # Code repositories
├── 3-knowledge/         # Permanent knowledge (zettel, literature, reference)
├── 4-archive/           # Historical content
├── .datacore/           # Configuration
└── CLAUDE.md            # Space context
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
├── bochsler/
│   ├── investment-agreement.pdf    # Small → git directly
│   └── investment-agreement.md     # Optional companion
└── presentations/
    ├── ethcc-2019.key              # Large → git LFS
    └── ethcc-2019.md               # Required companion (non-AI-readable)
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
source: ethcc-2019.key
format: keynote
size: 63MB
created: 2019-07-15
status: active
ai_readable: false
---

# EthCC 2019 Presentation

## Summary
Datafund presentation at EthCC Paris 2019 covering fair data economy vision.

## Key Slides
1. Introduction to Datafund
2. Fair data economy thesis
3. Technical architecture
4. Roadmap

## Notes
- Presented by Gregor
- Well received, led to 3 follow-up meetings

## Related
- [[presentations/devcon-2019]] - Similar deck
- [[1-tracks/comms/events/ethcc-2019]] - Event notes
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

### Changes Required

1. Create `.gitattributes` in each space root with LFS patterns
2. Install Git LFS on local machines and nightshift server
3. Update existing large files to use LFS: `git lfs migrate`

### New Components

- `.gitattributes` - Git LFS configuration file
- Companion markdown files - For non-AI-readable content

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

1. **Phase 1**: Create `.gitattributes` with LFS patterns
2. **Phase 2**: Install Git LFS on nightshift server
3. **Phase 3**: Migrate existing large files (if any)
4. **Phase 4**: Document companion file pattern in CLAUDE.md

## Open Questions

1. Should `.gitattributes` be per-space or at root level?
2. What size threshold (if any) should trigger LFS for PDFs?
3. Should companion files use `.companion.md` suffix instead of same name?

## References

- [Git LFS Documentation](https://git-lfs.com/)
- DIP-0002: Layered Context Pattern
- DIP-0003: Scaffolding Pattern
- `datacore-specification.md` - Current structure documentation
