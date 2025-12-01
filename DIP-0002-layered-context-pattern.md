# DIP-0002: Layered Context Pattern

| Field | Value |
|-------|-------|
| **DIP** | 0002 |
| **Title** | Layered Context Pattern |
| **Author** | Datacore Team |
| **Type** | Core |
| **Status** | Implemented |
| **Created** | 2025-12-01 |
| **Updated** | 2025-12-01 |
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

## Implementation

### Phase 1: Core Pattern (Complete)
- [x] Create `context_merge.py` utility
- [x] Update `.gitignore` templates
- [x] Create pre-commit hooks

### Phase 2: Apply to Repos (Complete)
- [x] Update `datacore` repo
- [x] Update `datacore-org` template

### Phase 3: Tooling (In Progress)
- [ ] Add `datacore context` CLI commands
- [x] Create pre-commit hooks
- [x] Add CI validation workflow

### Phase 4: Documentation
- [ ] Update INSTALL.md
- [ ] Update CONTRIBUTING.md

## Open Questions

1. How to handle merge conflicts between layers?
2. Should composed files include layer markers for debugging? (Currently: yes)

## References

- [DIP-0001: Contribution Model](./DIP-0001-contribution-model.md)
- [Privacy Policy](../.datacore/specs/privacy-policy.md)
- [Ethereum EIP Process](https://eips.ethereum.org/EIPS/eip-1)
