# DIP-0002: Layered Context Pattern

| Field | Value |
|-------|-------|
| **DIP** | 0002 |
| **Title** | Layered Context Pattern |
| **Author** | Datacore Team |
| **Type** | Core |
| **Status** | Implemented |
| **Created** | 2025-12-01 |
| **Updated** | 2026-03-17 |
| **Tags** | `context`, `privacy`, `CLAUDE.md`, `layers`, `contribution` |
| **Affects** | `CLAUDE.md`, `.gitignore`, `agents/*.md`, `commands/*.md` |
| **Specs** | `privacy-policy.md` |
| **Agents** | `context-maintainer.md` |

## Summary

A universal pattern for managing context files (CLAUDE.md, agents, commands) with three layers: PUBLIC (upstream contributions), SPACE (space-specific), and PRIVATE (personal). Facilitates contributions while protecting privacy.

## Motivation

Datacore needs to:
1. Enable 1000s of users to contribute improvements back to the system
2. Protect private/sensitive information
3. Apply consistent patterns across all components (repos, modules, agents, commands)
4. Facilitate automatic learning through PRs

Current approach mixes public and private content, making contribution difficult and risking privacy leaks.

## Specification

### Core Layers

| Level | Suffix | Visibility | Git Tracking | PR Target |
|-------|--------|------------|--------------|-----------|
| PUBLIC | `.base.md` | Everyone | Tracked | Upstream repo |
| SPACE | `.space.md` | Space members | Tracked in space repo | None |
| PRIVATE | `.local.md` | Only user | Never | None |

### Future Layers (Reserved)

| Level | Suffix | Visibility | Git Tracking | PR Target |
|-------|--------|------------|--------------|-----------|
| TEAM | `.team.md` | Team members | Optional | Team repo |

> **Note**: TEAM layer is reserved for future use when spaces support multiple teams.

### File Structure

Every configurable component follows this pattern:

```
[component]/
├── [NAME].base.md          # PUBLIC - generic template (tracked upstream)
├── [NAME].space.md         # SPACE - space customizations (tracked in space)
├── [NAME].local.md         # PRIVATE - personal notes (gitignored)
└── [NAME].md               # Composed output (gitignored)
```

### Composition

Files are merged in order (later extends earlier):

```
[NAME].base.md      # Layer 1: System defaults (PUBLIC)
  + [NAME].space.md # Layer 2: Space customizations (SPACE)
  + [NAME].local.md # Layer 3: Personal notes (PRIVATE)
  ─────────────────
  = [NAME].md       # Output: Complete context
```

The composed `[NAME].md` is:
- Generated automatically (not manually edited)
- Always gitignored
- Read by AI at runtime

### Merge Behavior

Each layer can:
- **Add sections** - New headers are appended
- **Extend sections** - Content under same header is concatenated
- **Override values** - Specific key-value patterns can be overwritten

Merge utility: `.datacore/lib/context_merge.py`

### Applied Components

| Component | Base Location | Example |
|-----------|---------------|---------|
| System context | `datacore/CLAUDE.base.md` | GTD methodology |
| Org template | `datacore-org/CLAUDE.base.md` | Org structure |
| Space context | `space/CLAUDE.base.md` | Space overview |
| Module context | `modules/[name]/CLAUDE.base.md` | Trading rules |
| Agent definition | `agents/[name].base.md` | Agent prompt |
| Command definition | `commands/[name].base.md` | Command prompt |
| Mail rules | `modules/mail/rules.base.yaml` | Email classification |

### gitignore Pattern

Standard `.gitignore` for all components:

```gitignore
# Private layer - never tracked
*.local.md

# Composed output - generated at runtime
CLAUDE.md

# PUBLIC and SPACE layers are tracked:
# *.base.md   (tracked - PRable to upstream)
# *.space.md  (tracked in space repo)
```

### Contribution Flow

```
User improves something
        │
        ├─► Generic improvement ──► Edit .base.md ──► PR to upstream
        │
        ├─► Space-specific ──► Edit .space.md ──► Commit to space repo
        │
        └─► Personal ──► Edit .local.md ──► Stays local
```

### Auto-PR Triggers

When `.base.md` changes:

1. **Pre-commit hook** validates no private content
2. **CI workflow** validates no private content in PUBLIC layer
3. **Optional**: Auto-create draft PR to upstream

### Example: Trading Module

```
.datacore/modules/trading/
├── CLAUDE.base.md              # Generic trading methodology (PUBLIC)
│   └── "Position sizing rules, risk management..."
├── CLAUDE.space.md             # Space trading focus (SPACE)
│   └── "We focus on crypto perpetuals..."
├── CLAUDE.local.md             # Personal settings (PRIVATE)
│   └── "My risk tolerance: 2% per trade..."
└── CLAUDE.md                   # Composed (gitignored)
    └── [All layers merged]

├── agents/
│   ├── position-manager.base.md    # Generic agent (PUBLIC)
│   ├── position-manager.space.md   # Space risk limits (SPACE)
│   ├── position-manager.local.md   # My thresholds (PRIVATE)
│   └── position-manager.md         # Composed
```

### Example: Mail Module Classification Rules

The pattern extends to non-markdown configuration files:

```
.datacore/modules/mail/
├── rules.base.yaml             # Generic patterns (PUBLIC)
│   └── Newsletter senders, spam patterns, research sources
├── rules.local.yaml            # Personal overrides (PRIVATE, gitignored)
│   └── Personal contacts, custom ignore patterns

1-datafund/
├── mail-rules.yaml             # Space-specific rules (SPACE)
│   └── Business contacts, partner patterns, project threads

0-personal/
├── mail-rules.yaml             # Personal space rules (SPACE)
│   └── Family contacts, personal subscriptions
```

**Merge order**: `rules.base.yaml` → `{space}/mail-rules.yaml` → `rules.local.yaml`

**Key patterns**:
- Sender classification (actionable, research, newsletter, ignore)
- Subject rules (finance, calendar triggers)
- Thread rules (ongoing conversations)
- Cross-module actions (route invoices to accounting module)

This enables:
1. Generic newsletter detection (base) + space-specific business contacts (space)
2. Research extraction for AVC/HBR (base) + personal research sources (local)
3. Financial email routing (base) → accounting module integration

### Merge Utility

```python
# .datacore/lib/context_merge.py

def merge_context(component_path: str, name: str = "CLAUDE") -> str:
    """Merge layered context files into single output."""
    layers = [
        f"{name}.base.md",   # PUBLIC
        f"{name}.space.md",  # SPACE
        f"{name}.local.md",  # PRIVATE
    ]

    content = []
    for layer in layers:
        path = component_path / layer
        if path.exists():
            content.append(f"<!-- Layer: {layer} -->\n")
            content.append(path.read_text())
            content.append("\n")

    return "".join(content)
```

### Commands

```bash
# Regenerate all composed files
datacore context rebuild

# Regenerate specific component
datacore context rebuild --path .datacore/modules/trading

# Validate no private content in PUBLIC layer
datacore context validate

# Show which layer a section comes from
datacore context trace "Position Sizing"
```

## Rationale

**Why three levels (PUBLIC/SPACE/PRIVATE)?**
- PUBLIC: Generic improvements that benefit everyone → PR upstream
- SPACE: Space-specific context visible to all space members → tracked in space repo
- PRIVATE: Personal customizations → never tracked
- TEAM layer reserved for future multi-team spaces

**Why file-based (not section-based)?**
- Easier to enforce gitignore rules
- Clear ownership per file
- No parsing complexity
- Harder to accidentally leak private content

**Why composition (not inheritance)?**
- Additive model is simpler to understand
- All context visible in one file at runtime
- No need to traverse hierarchy

## Backwards Compatibility

Migration from current pattern:

| Current | New |
|---------|-----|
| `CLAUDE.template.md` | `CLAUDE.base.md` |
| `CLAUDE.md` (local) | `CLAUDE.local.md` |

Migration script provided in implementation.

## Security Considerations

1. **CI validation** - PRs checked for private content patterns in `.base.md`
2. **Pre-commit hooks** - Validates `.base.md` before commit
3. **Gitignore enforcement** - `.local.md` always ignored
4. **Content scanning** - Detect PII, secrets, sensitive patterns

### Private Content Patterns (blocked in PUBLIC layer)

```regex
# Personal identifiers
/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/  # Email
/\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/  # Phone

# Secrets
/api[_-]?key|password|secret|token/i

# Financial
/\$[\d,]+\.\d{2}/  # Dollar amounts
```

## Implementation Status
_Last audited: 2026-03-04_

### Implemented

| Feature | Status | Evidence |
|---------|--------|----------|
| `context_merge.py` utility | Done | `.datacore/lib/context_merge.py` (555 lines, rebuild/validate/trace) |
| `.gitignore` templates | Done | `*.local.md`, `CLAUDE.md` ignored across all repos |
| Pre-commit hook | Done | `.datacore/hooks/pre-commit` validates `.base.md` for PII |
| Pre-push hook | Done | `.datacore/hooks/pre-push` safety net + Git LFS integration |
| Hook symlinks | Done | `.git/hooks/pre-commit`, `.git/hooks/pre-push` |
| `datacore` repo layered context | Done | `CLAUDE.base.md` + `CLAUDE.local.md` |
| `datacore-org` template | Done | `CLAUDE.base.md` + `CLAUDE.space.md` |
| Module `CLAUDE.base.md` files | Done | 24 modules with layered context (standardized 2026-03-17) |
| `context_merge.py rebuild` | Done | CLI for rebuilding composed files |
| `context_merge.py validate` | Done | CLI for validating PUBLIC layers |
| `context_merge.py trace` | Done | CLI for finding which layer contains a section |
| Registry injection | Done | `<!-- REGISTRY:xxx -->` markers → auto-generated tables (frontmatter extraction added 2026-03-17) |
| Test suite | Done | 14 tests covering merge, validation, rebuild, discovery |
| CLAUDE.md documentation | Done | Commands, layer table, contribution flow documented |
| CONTRIBUTING.md | Done | Hook setup instructions for external contributors |

### Amendment: Frontmatter & Templates (2026-03-17)

Driven by DIP-0025 (datacore-bench) findings that CLAUDE.md was competing with engram memory rather than complementing it. Key changes:

#### YAML Frontmatter Standard

Module and space CLAUDE.base.md files now include YAML frontmatter:

```yaml
---
summary: "One-line description for root CLAUDE.md"
triggers: ["trigger phrase 1", "trigger phrase 2"]
context: on_match
---
```

`context_merge.py` extracts frontmatter during registry injection:
- `summary` enriches the modules table Description column
- `triggers` populate a new Triggers column (shows activation phrases)
- `context` overrides module.yaml context priority when present

#### Content Hierarchy Principle

**Root CLAUDE.md** = system guide (how to use Datacore, not what it knows)
- Memory system instructions, session lifecycle
- Spaces overview with projects
- Methodology framing (GTD, Zettelkasten, Engram memory)
- Discovery patterns (registries, recall, datacortex)
- Auto-injected: modules table with triggers, sources, infrastructure

**Space CLAUDE.base.md** = space orientation (~50 lines)
- What this space is for, pointer to root for system concepts
- Compact structure, key paths, space-specific conventions

**Module CLAUDE.base.md** = module usage guide (40-150 lines)
- Purpose, Quick Start, How It Works, Agents & Commands, Key Paths, Boundaries
- Engram footer: "stable config here, learned behavior in engrams"

**CLAUDE.local.md** = minimal private overrides
- Only space journal paths and routing references
- All preferences, infrastructure facts, behavioral rules live as engrams

#### Template Specs

| Template | Location | Target Size |
|----------|----------|-------------|
| Module | `.datacore/specs/module-claude-template.md` | 40-150 lines |
| Space | `.datacore/specs/space-claude-template.md` | 40-60 lines |

#### Content Boundary: CLAUDE.md vs Engrams

| Goes in CLAUDE.md | Goes in engrams |
|-------------------|-----------------|
| System structure, folder layout | Server IPs, SSH configs |
| How to use commands/agents | Past decisions, design rationale |
| Methodology overview | API quirks, bug workarounds |
| Convention syntax reference | User preferences (formatting, tone) |
| Module capability summary | Corrections and learned patterns |

**Principle**: CLAUDE.md describes HOW the system works. Engrams contain WHAT has been learned. CLAUDE.md should teach Claude to use `datacore.recall` for factual questions.

#### create-module Agent

Updated with Step 8c: CLAUDE.base.md Template Audit — checks frontmatter, required sections, size, no root duplication. References `specs/module-claude-template.md`.

### Resolved Questions

1. **Merge conflicts between layers?** — Additive model: layers are concatenated, not merged. Conflicts don't arise because each layer is a separate file. If same-named sections exist, both appear (space-specific overrides are handled by AI context at runtime).
2. **Layer markers for debugging?** — Yes. Composed files include `<!-- === Layer: BASE (PUBLIC) === -->` markers. Can be disabled with `--no-markers` flag.

## Agent Context

This section provides essential information for agents working with layered context files.

### Layer Files

| Layer | Suffix | Tracked | Purpose |
|-------|--------|---------|---------|
| PUBLIC | `.base.md` | Yes (PR upstream) | Generic, reusable content |
| SPACE | `.space.md` | Yes (space repo) | Space-specific customizations |
| PRIVATE | `.local.md` | No (gitignored) | Personal notes, secrets |
| OUTPUT | `.md` | No (generated) | Composed runtime file |

### Composition Order

```
[NAME].base.md   →  Layer 1 (PUBLIC)
  + [NAME].space.md  →  Layer 2 (SPACE)
  + [NAME].local.md  →  Layer 3 (PRIVATE)
  ─────────────────
  = [NAME].md        →  Output (composed)
```

Later layers extend/override earlier layers.

### Key Commands

```bash
# Rebuild all composed files
python .datacore/lib/context_merge.py rebuild --path .

# Rebuild specific component
python .datacore/lib/context_merge.py rebuild --path .datacore/modules/trading

# Validate no private content in PUBLIC layers
python .datacore/lib/context_merge.py validate --path .
```

### Applied To

| Component | Base Location | Example |
|-----------|---------------|---------|
| CLAUDE.md | `CLAUDE.base.md` | System context |
| Agents | `agents/[name].base.md` | Agent prompts |
| Commands | `commands/[name].base.md` | Command prompts |
| Module context | `modules/[name]/CLAUDE.base.md` | Module instructions |

### Content Rules

**PUBLIC layer (.base.md)** - MUST NOT contain:
- Email addresses
- Phone numbers
- API keys, passwords, secrets
- Dollar amounts
- Personal identifiers

**SPACE layer (.space.md)** - Can contain:
- Space-specific processes
- Team contacts (non-personal)
- Project names, work areas

**PRIVATE layer (.local.md)** - For:
- Personal preferences
- Private notes
- Local overrides
- Sensitive information

### Agent Requirements

When modifying context files:
1. Identify correct layer (PUBLIC/SPACE/PRIVATE)
2. Edit layer file directly, not composed `.md`
3. Run rebuild after edits
4. Validate before commit if PUBLIC

## References

- [DIP-0001: Contribution Model](./DIP-0001-contribution-model.md)
- [DIP-0010: External Sync Architecture](./DIP-0010-external-sync-architecture.md)
- [Privacy Policy](../specs/privacy-policy.md)
- [Ethereum EIP Process](https://eips.ethereum.org/EIPS/eip-1)

## Applications

This pattern is used by:

| Module/Component | Layer Files | Purpose |
|------------------|-------------|---------|
| Mail Module | `rules.base.yaml`, `{space}/mail-rules.yaml`, `rules.local.yaml` | Email classification rules |
| Trading Module | `CLAUDE.*.md`, `agents/*.md` | Trading methodology and agents |
| All Agents | `*.base.md`, `*.space.md`, `*.local.md` | Agent behavior customization |
