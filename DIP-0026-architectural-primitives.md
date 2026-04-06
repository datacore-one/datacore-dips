# DIP-0026: Architectural Primitives

| Field | Value |
|-------|-------|
| **DIP** | 0026 |
| **Title** | Architectural Primitives |
| **Author** | @datacore-one |
| **Type** | Informational |
| **Status** | Draft |
| **Created** | 2026-04-06 |
| **Tags** | `architecture`, `patterns`, `modules`, `onboarding` |
| **Affects** | All modules, `.datacore/modules/*/CLAUDE.base.md` |

## Summary

Catalog of architectural patterns that repeat across Datacore modules. Instead of re-documenting the same pattern in every module, reference by name: "This module uses the Capture-Process-Archive primitive (DIP-0026)."

New module authors can browse this catalog to pick the right pattern for their domain.

## Primitives

### 1. Capture-Process-Archive (CPA)

**Description**: Three-phase content lifecycle. Raw input enters a capture point, gets processed (classified, enriched, routed), then moves to a permanent archive location.

**Flow**:
```
capture (inbox) → process (classify, enrich) → archive (permanent storage)
```

**Characteristics**:
- Single capture point per domain (inbox.org, 0-inbox/, email inbox)
- Processing enriches with metadata (tags, properties, links)
- Archive is append-only and searchable
- Inbox should always return to zero

**Modules using this**:
| Module | Capture | Process | Archive |
|--------|---------|---------|---------|
| gtd | inbox.org | inbox-triage agent | next_actions.org, someday.org |
| mail | Gmail inbox | mail-classifier agent | org tasks, archive labels |
| outbox | 4-outbox/ | outbox processor | archive/ repo |
| research | research task | research agent | 3-knowledge/ |
| whatsapp | chat export | whatsapp-importer | CRM + knowledge |

### 2. Layered Context

**Description**: Privacy-preserving context composition. Files split into layers from public to private, merged at runtime. Enables sharing methodology without leaking personal data.

**Flow**:
```
.base.md (PUBLIC) → .space.md (SPACE) → .team.md (TEAM) → .local.md (PRIVATE)
                                    ↓
                              composed .md (gitignored)
```

**Characteristics**:
- Later layers extend or override earlier ones
- PUBLIC layer validated for private content (emails, secrets)
- Composed file is gitignored — never committed
- Rebuild via `context_merge.py rebuild`

**Modules using this**: Every module with CLAUDE.base.md (all of them).

**Reference**: DIP-0002

### 3. On-Match Loading

**Description**: Demand-driven context injection. Module context only loads when the conversation matches trigger terms, keeping the default context lean.

**Characteristics**:
- Module declares `triggers:` list in CLAUDE.base.md frontmatter
- Context priority: `always` (always loaded), `on_match` (loaded when triggers match)
- Reduces token usage — 25+ modules but only relevant ones inject context
- Fallback: user can explicitly request any module

**Configuration** (in CLAUDE.base.md frontmatter):
```yaml
triggers:
  - "email"
  - "gmail"
  - "process inbox"
context: on_match
```

**Modules using this**: All non-core modules (everything except gtd).

### 4. Hook Lifecycle

**Description**: Event-driven extension points. Modules hook into system events (today briefing, session start, nightshift queue) to inject their content at the right moment.

**Flow**:
```
event fires → hooks_composer.py discovers hooks → each hook executes → output merged
```

**Characteristics**:
- Hooks declared in module.yaml under `hooks:`
- Common hook points: `today`, `wrap_up`, `nightshift_queue`, `post_install`
- Hook output is markdown — merged into the parent workflow's output
- Hooks are optional — missing hook = silent skip

**Modules using this**:
| Module | Hook | Purpose |
|--------|------|---------|
| mail | today | "You have N unread emails" |
| trading | today | Morning market briefing |
| crm | today | Dormant contacts reminder |
| news | today | News digest |
| meetings | today | Today's meetings |

**Reference**: DIP-0024

### 5. Adapter Pattern

**Description**: External service integration through a uniform interface. Each adapter wraps one API (Gmail, Telegram, GitHub) behind a consistent internal interface.

**Characteristics**:
- Adapter lives in `modules/[name]/adapters/`
- Provides: authenticate(), fetch(), send(), sync()
- Credentials managed per DIP-0018 (creds.py)
- Adapters are stateless — state lives in org files and config

**Modules using this**:
| Module | Adapter | Service |
|--------|---------|---------|
| mail | gmail.py | Gmail API |
| telegram | telegram_bot.py | Telegram Bot API |
| news | news_sources.py | Multiple RSS/API |
| slides | gamma_adapter.py | Gamma.app API |

**Reference**: DIP-0010

### 6. Engram Namespace

**Description**: Modules ship starter engrams (best practices) and accumulate user engrams (personal experience) in a namespaced scope.

**Characteristics**:
- Module declares `engrams.namespace` in module.yaml
- Starter pack: `engrams/starter-pack.yaml` — installed with module
- User engrams tagged with module namespace for scoped recall
- Injection policy: `on_match` (default) or `always`

**Configuration** (in module.yaml):
```yaml
engrams:
  namespace: trading
  starter_pack: engrams/starter-pack.yaml
  injection_policy: on_match
  match_terms: [trade, position, market, portfolio]
```

**Reference**: DIP-0019

### 7. Space-Local Data

**Description**: Module code is global (`.datacore/modules/`), but module data is per-space. This separates sharable methodology from private user data.

**Characteristics**:
- Code: `.datacore/modules/[name]/` (global, version-controlled)
- Data: `[space]/.datacore/modules/[name]/data/` (per-space, gitignored)
- Config: `[space]/[module].yaml` or `[space]/.datacore/modules/[name]/config.yaml`
- Enables: same module code, different data per workspace

**Reference**: DIP-0022

### 8. Progressive Tiers

**Description**: Module activation gated by experience level. New users see only core modules; advanced features unlock as needed.

**Tiers**:
| Tier | Modules | When |
|------|---------|------|
| starter | gtd, datacortex, outbox | New installs |
| standard | + research, mail, crm, meetings | First use of those domains |
| advanced | + nightshift, trading, health, ... | Manual enable |
| all | Everything | Existing installs (default) |

**Configuration**: `[space]/.datacore/config.yaml` → `module_tier: starter`

**Reference**: module_tiers.py

## Using Primitives in Module Documentation

When documenting a module, reference primitives by name instead of re-explaining:

```markdown
## Architecture

This module uses the **Capture-Process-Archive** primitive (DIP-0026):
- Capture: Gmail inbox via adapter
- Process: AI classification + rule matching
- Archive: GTD tasks + Gmail archive labels

Context loading follows **On-Match Loading** — triggers on "email", "gmail", "inbox".
```

## Adding New Primitives

If a pattern repeats in 3+ modules, it qualifies as a primitive. Add it here with:
1. Name and one-line description
2. Flow diagram (text or mermaid)
3. Characteristics (bullet list)
4. Table of modules using it
5. Reference to governing DIP (if any)
