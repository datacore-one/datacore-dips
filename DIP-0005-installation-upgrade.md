# DIP-0005: Installation & Upgrade

| Field | Value |
|-------|-------|
| **DIP** | 0005 |
| **Title** | Installation & Upgrade |
| **Author** | Gregor |
| **Type** | Core |
| **Status** | Implemented |
| **Created** | 2025-12-03 |
| **Updated** | 2026-03-04 |
| **Tags** | `installation`, `bootstrap`, `upgrade`, `onboarding` |
| **Affects** | `install.yaml`, `datacore.lock.yaml`, `sync`, `.mcp.json`, `.datacore/` |
| **Specs** | DIP-0002 (Layered Context), DIP-0016 (Agent Registry), DIP-0022 (Module Spec) |
| **Agents** | `create-space` |
| **Absorbs** | DIP-0005-github-onboarding.md (original, withdrawn) |

## Summary

Specifies two installation paths for Datacore: **MCP-only** (lightweight, `npm install -g @datacore-one/mcp`) and **Full System** (fork-and-clone with spaces, modules, and GTD). Covers bootstrap, configuration, module installation, upgrades, and first-run onboarding.

## Agent Context

### When to Reference

- **`create-space`**: When scaffolding new spaces — follow Section 3.7 for team space setup and DIP-0003 for internal structure
- **`context-maintainer`**: When rebuilding CLAUDE.md — follow Section 3.4 for the `context_merge.py` workflow
- **`scaffolding-auditor`**: When validating installation completeness — check Section 3.3 templates and Section 3.9 verification

### Quick Reference

- Core install: `npm install -g @datacore-one/mcp` (Section 2)
- Full install: fork + clone + configure (Section 3)
- Upgrade: `npm update` (core) or `git merge upstream/main` (full) (Section 6)
- Env vars: Section 4
- Config files: Section 5

### Related Agents

| Agent | Relationship |
|-------|-------------|
| `create-space` | Implements Section 3.7 (space creation) |
| `context-maintainer` | Implements Section 3.4 (context rebuild) |
| `scaffolding-auditor` | Validates Section 3.3 (template activation) |
| `module-registrar` | Implements Section 3.5 (module installation) |

## Motivation

Datacore has two audiences with different needs:

1. **MCP users** want persistent memory for Claude Code/Desktop with zero setup friction. They install one npm package and get engrams, journal, and knowledge tools immediately.

2. **Full system users** want the complete second brain: GTD workflows, multi-space organization, nightshift execution, research pipelines, and modular extensibility. This requires a multi-repo setup with configuration.

Currently there is no documented install process for either path. New users must reverse-engineer the setup from CLAUDE.md and scattered README files. This DIP provides a single authoritative specification.

## Specification

### 1. Installation Paths

```
                    ┌─────────────────┐
                    │   New User       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Which path?     │
                    └────┬───────┬────┘
                         │       │
              ┌──────────▼┐   ┌──▼──────────┐
              │  MCP-Only  │   │ Full System  │
              │  (Core)    │   │ (Full)       │
              └──────────┬┘   └──┬───────────┘
                         │       │
              npm install     fork + clone
              auto-init       configure
              ready            install modules
                               add spaces
                               ready
```

### 2. MCP-Only Installation (Core Mode)

**Prerequisites:** Node.js >= 22

**Install:**

```bash
npm install -g @datacore-one/mcp
```

**Configure MCP client:**

Claude Code (`.mcp.json` in project root or `~/.claude/mcp.json`):
```json
{
  "mcpServers": {
    "datacore": {
      "command": "datacore-mcp"
    }
  }
}
```

Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "datacore": {
      "command": "datacore-mcp"
    }
  }
}
```

**Auto-initialization:** On first connection, the server creates `~/Datacore/` with:

```
~/Datacore/
├── engrams.yaml          # Learned knowledge
├── config.yaml           # Server configuration
├── journal/              # Daily journal entries
├── knowledge/            # Knowledge notes
├── packs/                # Engram packs (starter packs auto-installed)
├── archive/              # Archived content
├── exchange/             # Engram exchange (inbox/outbox)
├── state/                # Runtime state
├── CLAUDE.md             # Context for Claude Code
├── AGENTS.md             # Agent instructions
├── .cursorrules          # Context for Cursor
└── .github/copilot-instructions.md  # Context for Copilot
```

**Override path:** Set `DATACORE_CORE_PATH` env var to use a different directory.

**No API keys required.** The MCP server has no external dependencies.

### 3. Full System Installation

#### 3.1 Prerequisites

| Requirement | Purpose |
|-------------|---------|
| Git + Git LFS | Version control, large file handling |
| GitHub CLI (`gh`) | Repo management, authenticated |
| Python 3.8+ | System scripts (`pip install pyyaml`) |
| Node.js >= 22 | MCP servers, module tools |
| Claude Code CLI | AI agent interface |

Optional: Emacs (org-mode editing), Obsidian (PKM vault).

#### 3.2 Fork and Clone

```bash
# Fork the template repo
gh repo fork datacore-one/datacore --clone=false

# Clone YOUR fork into ~/Data
git clone https://github.com/YOUR-USERNAME/datacore.git ~/Data
cd ~/Data

# Track upstream for updates
git remote add upstream https://github.com/datacore-one/datacore.git
```

> **Important:** The target directory (`~/Data`) must not already exist. Git clones directly into it. If you need a different path, set `DATACORE_PATH` accordingly.

#### 3.3 Activate Templates

```bash
# System manifest
cp install.yaml.example install.yaml

# GTD org files
cp 0-personal/org/inbox.org.example 0-personal/org/inbox.org
cp 0-personal/org/next_actions.org.example 0-personal/org/next_actions.org
cp 0-personal/org/someday.org.example 0-personal/org/someday.org
cp 0-personal/org/habits.org.example 0-personal/org/habits.org

# MCP server config
cp .mcp.json.example .mcp.json

# User preferences (optional — customize editor, sync, journal behavior)
cp .datacore/settings.yaml .datacore/settings.local.yaml
# Edit .datacore/settings.local.yaml with your overrides

# API keys (optional — for research, search, slides)
cp .datacore/env/.env.example .datacore/env/.env
# Edit .datacore/env/.env with your keys
```

#### 3.4 Build Context

```bash
# Generate CLAUDE.md from layered sources + registry injection
python .datacore/lib/context_merge.py rebuild --path .
```

This reads `CLAUDE.base.md` + `CLAUDE.local.md` (if exists) and injects auto-generated tables from `.datacore/registry/` (agents, commands, modules, sources).

#### 3.5 Install Modules

Modules are separate git repos cloned into `.datacore/modules/`:

```bash
# Example: install trading module
git clone https://github.com/datacore-one/module-trading .datacore/modules/trading

# Rebuild context to pick up new module
python .datacore/lib/context_merge.py rebuild --path .
```

Built-in modules (gtd, comms, outbox, etc.) ship with the root repo and are already present.

Each module has a `module.yaml` manifest declaring its tools, skills, agents, and commands (see DIP-0022).

#### 3.6 Configure MCP Servers

Edit `.mcp.json` to register the datacore MCP server. In full mode, the server auto-detects `~/Data/.datacore/` and uses full-mode storage:

```json
{
  "mcpServers": {
    "datacore": {
      "command": "datacore-mcp"
    }
  }
}
```

The server detects full mode when `DATACORE_PATH` points to a directory containing `.datacore/`, or when `~/Data/.datacore/` exists.

**Full-mode storage layout:**

```
~/Data/.datacore/learning/engrams.yaml    # Engrams
~/Data/0-personal/journal/                # Journal (in personal space)
~/Data/0-personal/3-knowledge/            # Knowledge notes
~/Data/.datacore/learning/packs/          # Engram packs
~/Data/.datacore/state/                   # Runtime state
```

#### 3.7 Add Team Spaces (Optional)

```bash
# Clone an existing team space
git clone https://github.com/org/team-space.git 1-teamname

# Or create a new one via agent
# In Claude Code: "create a new space called teamname"
```

Register in `install.yaml` under `spaces:`. See DIP-0003 for space structure.

#### 3.8 Initialize Knowledge Index (Optional)

```bash
python .datacore/lib/zettel_db.py init-all
```

Creates SQLite indexes for semantic search via Datacortex module.

#### 3.9 Verify

```bash
./sync status          # All repos clean
cd ~/Data && claude    # Launch Claude Code
```

Try `/today` to generate the first daily briefing.

### 4. Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATACORE_PATH` | `~/Data` | Full installation root |
| `DATACORE_CORE_PATH` | `~/Datacore` | Core-mode storage |
| `DATACORE_TIMEZONE` | system | IANA timezone |
| `DATACORE_LOG_LEVEL` | `warning` | MCP server log level |
| `DATACORE_CACHE_TTL` | `60` | File cache TTL (seconds) |
| `DATACORE_TRANSPORT` | `stdio` | `stdio` or `http` |
| `DATACORE_HTTP_PORT` | `3100` | HTTP transport port |
| `DATACORE_HTTP_HOST` | `127.0.0.1` | HTTP bind address |

### 5. Configuration Files

#### 5.1 install.yaml (Manifest)

Declarative description of the installation. Edited by the user.

```yaml
meta:
  name: "My Datacore"
  root: ~/Data
  version: 1.0.0

personal:
  path: 0-personal
  modules: []

spaces:
  teamname:
    repo: org/team-space
    path: 1-teamname
```

#### 5.2 datacore.lock.yaml (Lock File)

Auto-generated record of actual installed state. Used for reproducible restores and drift detection.

```yaml
generated: "2026-03-03T10:00:00Z"
system:
  repo: datacore-one/datacore
  commit: abc1234
  branch: main

modules:
  trading:
    repo: datacore-one/module-trading
    commit: def5678
    path: .datacore/modules/trading
  research:
    repo: datacore-one/module-research
    commit: ghi9012
    path: .datacore/modules/research

spaces:
  0-personal:
    origin: self-hosted
    path: 0-personal
  1-teamname:
    repo: org/team-space
    commit: jkl3456
    path: 1-teamname
```

Updated by `./sync` after successful pulls. Not manually edited.

#### 5.3 settings.yaml (User Preferences)

Controls editor behavior, sync automation, and journal options. Base defaults ship tracked; user overrides are gitignored.

```yaml
# .datacore/settings.yaml (tracked — base defaults)
# .datacore/settings.local.yaml (gitignored — user overrides)

editor:
  open_markdown_on_generate: true
  open_command: ""

sync:
  pull_on_today: true
  push_on_wrap_up: true

journal:
  open_after_update: false
```

To customize, create `.datacore/settings.local.yaml` with only the keys you want to override.

#### 5.4 config.yaml (MCP Server Config)

Optional. Located at `~/Datacore/config.yaml` (core) or `~/Data/.datacore/config.yaml` (full). Created automatically with defaults if absent.

```yaml
engrams:
  auto_promote: false
packs:
  trusted_publishers: []
search:
  max_results: 20
engagement:
  enabled: true
```

### 6. Upgrade Process

#### 6.1 Core Mode Upgrade

```bash
npm update -g @datacore-one/mcp
```

The server handles data migrations automatically on startup. User data in `~/Datacore/` is preserved.

#### 6.2 Full System Upgrade

```bash
cd ~/Data

# Pull upstream changes
git fetch upstream
git merge upstream/main

# Update modules
cd .datacore/modules/trading && git pull
cd .datacore/modules/research && git pull
# ... repeat for each module

# Rebuild context
python .datacore/lib/context_merge.py rebuild --path .
```

The `sync` script automates multi-repo pulls:

```bash
./sync          # Pull all repos (root + spaces + projects)
```

#### 6.3 Breaking Changes

When upstream introduces breaking changes:

1. Release notes document required migration steps
2. `context_merge.py` warns if CLAUDE.md is stale
3. Module `module.yaml` declares minimum system version via `requires.datacore`

### 7. First-Run Onboarding

After installation, the recommended learning path:

#### Core Mode

1. Start a Claude Code session — `datacore.session.start` runs automatically
2. Work normally — the system learns your patterns via `datacore.learn`
3. End sessions with `datacore.session.end` to preserve learnings
4. Engrams accumulate automatically over time

#### Full System

- [ ] Run `/today` — see the daily briefing format
- [ ] Add a task to `inbox.org` — experience GTD capture
- [ ] Say "process inbox" — watch AI triage and routing
- [ ] Try `/research "topic"` — multi-source research pipeline
- [ ] Add a task with `:AI:research:` tag — overnight AI execution
- [ ] Run `/today` next morning — see AI work in the briefing
- [ ] Customize `CLAUDE.local.md` — add your preferences

### 8. Uninstallation

#### Core Mode

```bash
npm uninstall -g @datacore-one/mcp
rm -rf ~/Datacore    # Remove data (optional)
```

#### Full System

Remove the `~/Data` directory and MCP client configuration. Team spaces are independent git repos that can be preserved separately.

## Rationale

**Two paths** because the MCP server is useful standalone — many users want persistent memory without GTD methodology. Forcing the full install would reduce adoption.

**Fork-and-clone** (not `npm init`) for the full system because Datacore is a living system, not a library. Users need their own git history for personal data while tracking upstream for system updates.

**No installer script** for the full system because each step involves user decisions (which modules, which spaces, which API keys). A guided manual process produces better understanding than a wizard that hides decisions.

## Backwards Compatibility

This DIP documents the existing install process — no breaking changes. Future versions may add automated tooling (e.g., `datacore init` CLI command) that follows this specification.

## Security Considerations

- API keys stored in `.datacore/env/.env` (gitignored)
- `CLAUDE.local.md` is gitignored (private layer)
- `context_merge.py validate` prevents accidental PII in public layers
- Module credentials use separate env files per DIP-0018

## Implementation

### Current State

Both installation paths are functional but undocumented before this DIP:

| Component | Status |
|-----------|--------|
| MCP npm package (`@datacore-one/mcp`) | Published, auto-init works |
| Full system fork-and-clone | Works, documented here for the first time |
| `context_merge.py` | Implemented (555 lines), handles rebuild + validate |
| `create-space` agent | Implements space scaffolding |
| `sync` script | Implements multi-repo pull/push |
| `install.yaml` | Template exists (`install.yaml.example`) |
| `datacore.lock.yaml` | File exists, generation not yet automated |

### Rollout Plan

1. **Phase 1 (current):** Document existing manual process (this DIP)
2. **Phase 2:** Automate lock file generation in `sync` script
3. **Phase 3:** Optional `datacore init` CLI command that follows this specification interactively

### Reference Implementation

- MCP auto-init: `datacore-mcp/src/server.ts` (core mode bootstrap)
- Context rebuild: `.datacore/lib/context_merge.py`
- Space scaffolding: `.datacore/agents/create-space.md`
- Sync script: `./sync`

## Implementation Status
_Last audited: 2026-03-04_

### Implemented

| Feature | Status | Evidence |
|---------|--------|----------|
| `install.yaml` manifest | Done | Root-level manifest listing all modules, spaces, repos |
| `datacore.lock.yaml` format | Done | Lock file format specified and in use |
| `./sync` script | Done | Pull/push/status for all repos |
| `create-space` agent | Done | Scaffolds spaces with folder structure and templates |
| MCP-only installation path | Done | `npm install -g @datacore-one/mcp` documented |
| Full system clone workflow | Done | Fork-and-clone with space setup documented |
| Module installation in `install.yaml` | Done | 21 modules tracked with paths and versions |

### Future Work
_Items below are outside v1.0 scope. They remain specified for future implementation._

| Feature | Rationale |
|---------|-----------|
| `datacore init` CLI wizard | Manual process ensures understanding; CLI adds complexity for marginal benefit |
| Core-to-Full migration path | Few users will migrate; document when needed, not before |
| Lock file auto-generation | Manual lock file sufficient at current scale |
| Module version pinning | All modules track `main`; version constraints premature without registry |
| First-run onboarding wizard | `create-space` agent covers scaffolding; wizard is polish |

### Resolved Questions

_No resolved questions._

## Open Questions

1. **Should `datacore init` be a CLI command?** The current manual process ensures users understand each decision. A CLI wizard would reduce friction but hide complexity. If built, it should follow the specification in this DIP exactly.

2. **Core-to-Full migration path:** A user who starts with MCP-only may later want the full system. Should there be a documented upgrade path that preserves existing engrams and journal entries from `~/Datacore/` into `~/Data/.datacore/`?

3. **Lock file automation:** `datacore.lock.yaml` format is specified (Section 5.2) but generation is not yet automated. Should `./sync` generate it after every successful pull, or should it be a separate command?

4. **Full-mode detection reliability:** The MCP server detects full mode via `DATACORE_PATH` env var or by checking for `~/Data/.datacore/`. What happens if both `~/Datacore/` and `~/Data/.datacore/` exist? Priority order should be explicit.

5. **Module version pinning:** Currently modules track `main` branch. Should `install.yaml` support version constraints (e.g., `version: ">=1.0.0"`) with lock file recording exact commits?

## References

- DIP-0002: Layered Context Pattern (context file management)
- DIP-0003: Scaffolding Pattern (space structure)
- DIP-0018: Credential Management (secrets handling)
- DIP-0022: Module Specification (module.yaml format)
- Original DIP-0005: GitHub-Based Onboarding (withdrawn, onboarding section absorbed)
