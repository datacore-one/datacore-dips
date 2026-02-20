# DIP-0022: Module Specification

| Field | Value |
|-------|-------|
| **DIP** | 0022 |
| **Title** | Module Specification |
| **Author** | Gregor |
| **Type** | Standards Track |
| **Status** | Draft |
| **Created** | 2026-02-20 |
| **Updated** | 2026-02-20 |
| **Tags** | `modules`, `mcp`, `skills`, `agents`, `engrams`, `workflows`, `architecture` |
| **Affects** | `.datacore/modules/`, `datacore-mcp`, `module.yaml`, `SKILL.md`, `CATALOG.md` |
| **Specs** | `datacore-specification.md`, `DIP-0002`, `DIP-0009`, `DIP-0014`, `DIP-0016`, `DIP-0019` |
| **Agents** | `create-module`, `module-registrar` |
| **Skills** | `create-module` |

## Summary

This DIP defines the complete module specification for Datacore. A module is a pluggable extension that provides up to **five capability layers** — MCP tools, skills, agents, commands, and workflows — plus starter engrams. The specification covers the full module lifecycle: creation, auditing, registration, installation, data separation, and CLAUDE.md integration.

Key design principles:

1. **Discovery hierarchy**: MCP tools > Skills > Agents > Commands. Place capabilities at the right layer.
2. **Code is public, data is private**: Module methodology is shareable; user data never leaks (DIP-0002).
3. **Engrams bridge modules and users**: Modules ship best practices; users accumulate private experience; the network learns through exchange (DIP-0019).
4. **Workflows orchestrate layers**: Multi-phase pipelines compose tools, skills, agents, and commands.
5. **Single MCP server**: Modules register tools with `@datacore-one/mcp`, not separate servers.

## Agent Context

### When to Reference This DIP

**Always reference when:**
- Creating, auditing, or registering a module
- Deciding whether a capability should be a tool, skill, agent, command, or workflow
- Working on datacore-mcp tool registration
- Installing modules or configuring module scope
- Working with module data separation or privacy
- Updating CLAUDE.md for module context inclusion

**Key decisions this DIP informs:**
- Stateless deterministic operations MUST be MCP tools
- Reusable knowledge/methodology goes in SKILL.md files
- Complex multi-step reasoning stays in agents
- Interactive human-in-the-loop workflows stay in commands
- Multi-phase pipelines that compose layers are workflows
- Module code is PUBLIC; module data is PRIVATE (per-space)
- Starter engrams ship as `template` visibility, user engrams default to `private`

### Quick Reference

| Question | Answer |
|----------|--------|
| Module location (global)? | `.datacore/modules/[name]/` |
| Module location (space)? | `[space]/.datacore/modules/[name]/` |
| Manifest? | `module.yaml` |
| Entry point? | `SKILL.md` (ecosystem-discoverable) |
| Tool namespace? | `datacore.[module].[tool]` |
| Module data? | `[space]/.datacore/modules/[name]/data/` |
| Engram namespace? | Declared in module.yaml `engrams.namespace` |
| Create a module? | `/create-module` command or `create-module` agent |
| Register a module? | `module-registrar` agent or `datacore.modules.register` tool |
| CATALOG? | `2-datacore/.datacore/CATALOG.md` |

### Related DIPs

- [DIP-0002](./DIP-0002-layered-context-pattern.md) - Layered privacy (applied to module data)
- [DIP-0009](./DIP-0009-gtd-specification.md) - GTD specification (reference built-in module)
- [DIP-0014](./DIP-0014-tag-taxonomy.md) - Tag taxonomy (module tag namespacing)
- [DIP-0016](./DIP-0016-agent-registry.md) - Agent/command registries
- [DIP-0019](./DIP-0019-learning-architecture.md) - Engram model, packs, exchange (amended with `scope: module:X`)
- [DIP-0021](./DIP-0021-search-research-architecture.md) - Research module as reference

### Related Agents

| Agent | Relationship |
|-------|--------------|
| `create-module` | Creates, converts, or audits modules for spec alignment |
| `module-registrar` | Validates and registers modules in CATALOG.md |

## Motivation

### The Discovery Hierarchy

Claude Code and MCP-compatible agents discover capabilities in a priority order:

```
1. MCP TOOLS     — Always available. AI reaches for these first (availability bias).
                   Listed in tool panel. Structured I/O. Deterministic.

2. SKILLS        — SKILL.md files. Loaded into context on match. Shape how AI
                   reasons. Knowledge injection. Emerging ecosystem standard.

3. AGENTS        — Prompt templates. Loaded via CLAUDE.md or Task tool.
                   Good for complex reasoning. No structured interface.

4. COMMANDS      — Slash commands. User-invoked. Interactive multi-step.
                   Heaviest, most context-consuming.
```

Today, Datacore modules only provide layers 3 and 4 (agents and commands). All data operations — counting inbox items, adding tasks, looking up contacts — are prompt-interpreted multi-turn conversations. This is slow, fragile, and not portable to non-Claude-Code MCP clients.

### The Internal MCP Insight

The `@datacore-one/mcp` server was built as an external product (8 tools for knowledge compounding). The same architecture solves the internal problem: modules should register programmatic tools with the MCP server, turning it into Datacore's internal tool bus.

### The Data Separation Problem

Modules currently mix code and data in the same directory. The slides module has `output/` next to `agents/`. The CRM module stores contact data alongside processing logic. This makes it impossible to share methodology without leaking personal data.

### The Missing Workflow Layer

Complex operations like presentation creation span multiple agents, tools, and skills across multiple phases. Today this orchestration is implicit — spread across command and agent files. Workflows should be explicit and declarative.

## Specification

### 1. Module Structure

```
datacore-[name]/
├── SKILL.md              # Module entry point (ecosystem-discoverable)
├── module.yaml           # Module manifest (Datacore-specific)
├── CLAUDE.base.md        # Module context — PUBLIC layer (tracked)
├── CLAUDE.space.md       # Module context — SPACE layer (space-specific overrides)
├── CLAUDE.local.md       # Module context — PRIVATE layer (gitignored)
├── CLAUDE.md             # Composed from layers (gitignored)
├── .gitignore            # Ignores CLAUDE.md, CLAUDE.local.md, etc.
│
├── tools/                # MCP tool handlers (TypeScript)
│   ├── index.ts          # Tool registry — exports ModuleToolDefinition[]
│   └── [tool-name].ts    # Individual tool handlers
│
├── skills/               # SKILL.md files (knowledge/methodology injection)
│   └── [name]/SKILL.md   # Individual skills
│
├── agents/               # Agent prompts (complex reasoning)
│   └── [name].md         # Individual agents
│
├── commands/             # Slash commands (interactive entry points)
│   └── [name].md         # Individual commands
│
├── workflows/            # Multi-phase orchestrations (declarative YAML)
│   └── [name].yaml       # Individual workflow definitions
│
├── engrams/              # Starter engrams (ship with module)
│   └── engrams.yaml      # Pre-built engrams (visibility: template)
│
├── templates/            # File/folder templates (optional)
├── scripts/              # Supporting scripts (optional)
└── lib/                  # Supporting code (optional)
```

**Minimum viable module** (new modules): `SKILL.md` + `module.yaml`. All directories are optional. Existing v1 modules without `SKILL.md` continue to function but should add one during migration (see Backwards Compatibility).

### 2. Module Manifest (module.yaml)

```yaml
manifest_version: 2       # DIP-0022 format (absent = v1 assumed)
name: slides
version: 1.0.0
description: Visual content generation — presentations with AI-powered backgrounds
author: datacore-one
repository: https://github.com/datacore-one/datacore-slides
license: MIT

dependencies:
  - image-generation       # Other modules this depends on

# What this module provides — each section is optional
provides:
  tools:
    - name: compile_pdf
      description: Assemble slide images into PDF
      handler: tools/compile-pdf.ts
    - name: list_templates
      description: List available design templates
      handler: tools/list-templates.ts

  skills:
    - name: create-presentation
      file: skills/create-presentation/SKILL.md
    - name: slide-post-processing
      file: skills/slide-post-processing/SKILL.md

  agents:
    - name: presentation-generator
      trigger: ":AI:presentation:"
    - name: gamma-presentation-generator
      trigger: ":AI:presentation:gamma:"

  commands:
    - create-presentation
    - sync-gamma

  workflows:
    - name: create-presentation
      file: workflows/create-presentation.yaml
      trigger: /create-presentation

# Engram configuration
engrams:
  starter_pack: engrams/engrams.yaml
  namespace: slides                    # Engram namespace for this module
  injection_policy: on_match           # on_match | always | manual
  match_terms: [presentation, slides, deck, pitch, keynote]

# CLAUDE.md inclusion behavior
context:
  priority: minimal                    # always | minimal | on_demand
  summary: "Visual content generation — presentations with AI backgrounds"

# External requirements
requires:
  env_vars:
    required: [GEMINI_API_KEY]
    optional: [GAMMA_API_KEY, GAMMA_DEFAULT_THEME]

  mcp_servers:                         # External MCP servers this module needs
    gamma:
      command: node
      args: ["{module_path}/mcp-server/dist/index.js"]
      env:
        GAMMA_API_KEY: "${GAMMA_API_KEY}"

# User-configurable settings (flat keys, no module prefix — context is known)
settings:
  auto_export_pdf: true
  default_num_cards: 10
  default_image_model: "gemini-2.5-flash-image"

# Module I/O locations (relative to space root)
outputs:
  presentations: "presentations/"
  exports: "exports/"
inputs:
  blog: "content/blog/"
  knowledge: "3-knowledge/"

# Post-install guidance
hooks:
  post_install: |
    echo "Slides module installed."
    echo "Required: Set GEMINI_API_KEY in .datacore/env/.env"
```

### 3. SKILL.md (Module Entry Point)

Every module has a root `SKILL.md` — the ecosystem-discoverable entry point:

```yaml
---
name: Slides for Datacore
description: Visual content generation — presentations with AI backgrounds
version: 1.0.0
author: datacore-one
license: MIT
tags: [presentations, slides, visual-content, gamma, gemini]
x-datacore:
  module: slides
  tools: 2
  skills: 2
  agents: 2
  commands: 2
  workflows: 1
  engram_count: 5
  injection_policy: on_match
  match_terms: [presentation, slides, deck, pitch, keynote]
---

# Slides for Datacore

Visual content generation — create professional presentations using
Gamma.app or Gemini image composition with brand templates.

## What This Module Provides

**Tools** (MCP):
- `datacore.slides.compile_pdf` — Assemble slide images into PDF
- `datacore.slides.list_templates` — Available design templates

**Skills**:
- Create presentation wizard
- Slide post-processing (logos, formatting)

**Agents**:
- Presentation generator (Gemini image composition)
- Gamma presentation generator (Gamma.app API)

**Commands**:
- `/create-presentation` — End-to-end presentation workflow
- `/sync-gamma` — Pull presentations from Gamma

**Workflows**:
- `create-presentation` — Full pipeline: brief → content → backgrounds → composition → PDF
```

The `x-datacore:` namespace in frontmatter carries Datacore-specific metadata without breaking compatibility with other ecosystems that read SKILL.md.

> **Auto-generated:** The `x-datacore:` block is generated by tooling (`create-module` and `module-registrar`) from `module.yaml` — not manually maintained. Layer counts are computed from the `provides:` section. Running `create-module audit` will flag stale counts and offer to regenerate.

### 4. Five-Layer Capability Model

| Layer | When to Use | Properties | Example |
|-------|------------|------------|---------|
| **MCP Tool** | Stateless, deterministic, single operation | Structured I/O, Zod-validated, no reasoning | Count inbox, compile PDF, lookup contact |
| **Skill** | Reusable knowledge that shapes AI reasoning | SKILL.md format, loaded into context | Triage methodology, brand guidelines |
| **Agent** | Complex reasoning, multi-step thinking | Prompt-based, spawned via Task tool | Route inbox entries, generate content |
| **Command** | Interactive entry point, human-in-the-loop | Slash-invoked, user interaction | `/create-presentation`, `/wrap-up` |
| **Workflow** | Multi-phase orchestration across layers | Declarative YAML, composes all layers | Presentation pipeline, research pipeline |

**Decision flowchart:**

```
Is it a deterministic operation on data?
├── YES → Can a function do it without reasoning?
│   ├── YES → MCP TOOL
│   └── NO → Does it need multi-turn user interaction?
│       ├── YES → COMMAND
│       └── NO → AGENT
└── NO → Is it knowledge/methodology that shapes behavior?
    ├── YES → SKILL
    └── NO → Does it span multiple phases using different layers?
        ├── YES → WORKFLOW (orchestrates tools + skills + agents + commands)
        └── NO → Does it need user interaction?
            ├── YES → COMMAND
            └── NO → AGENT
```

**The golden rule:** If Claude is doing file I/O that a function could do deterministically, it MUST be a tool. If it requires thinking, it stays an agent. If it shapes how thinking happens, it is a skill. If it spans multiple phases, it is a workflow.

**Tools act. Skills know. Agents think. Commands interact. Workflows orchestrate.**

### 5. MCP Tool Registration

#### Tool Interface

Module tools export a standard interface:

```typescript
// tools/index.ts
import { z } from 'zod'
import type { StorageConfig } from '@datacore-one/mcp'

export interface ModuleToolDefinition {
  name: string              // Without namespace prefix
  description: string
  inputSchema: z.ZodType
  handler: (args: unknown, context: ModuleToolContext) => Promise<unknown>
}

export interface ModuleToolContext {
  storage: StorageConfig
  modulePath: string        // Path to module directory
  dataPath: string          // Path to module's private data directory
  spaceName?: string        // Active space (if space-scoped)
}

export const tools: ModuleToolDefinition[] = [
  {
    name: 'compile_pdf',
    description: 'Assemble slide images into PDF',
    inputSchema: z.object({
      slides_dir: z.string().describe('Directory containing slide PNGs'),
      output_path: z.string().describe('Output PDF path'),
      add_logo: z.string().optional().describe('Logo path to overlay'),
    }),
    handler: async (args, context) => { /* ... */ },
  },
]
```

#### Namespace Convention

All module tools use: `datacore.[module].[tool]`

```
datacore.slides.compile_pdf
datacore.slides.list_templates
datacore.gtd.inbox_count
datacore.gtd.add_task
datacore.crm.lookup
```

Core tools remain at `datacore.*`:

```
datacore.capture            # Core
datacore.learn              # Core
datacore.gtd.inbox_count    # Module
```

#### Core Module Management Tools

Module management is itself exposed as core MCP tools:

```
datacore.modules.list       — List installed modules with scope and status
datacore.modules.info       — Get module details (tools, skills, agents, engrams)
datacore.modules.register   — Register module in CATALOG.md
datacore.modules.install    — Install module from registry (future)
datacore.modules.remove     — Remove module (future)
```

These replace manual CATALOG.md editing. The `module-registrar` agent calls these tools.

**Relationship to DIP-0016 agents.yaml:** `datacore.modules.register` also updates `.datacore/registry/agents.yaml` — adding module agents to the `module_agents` section. CATALOG.md is the module-level registry (what modules exist); agents.yaml is the agent-level registry (what agents exist). Registration updates both to keep them in sync.

#### Dynamic Loading in datacore-mcp

The MCP server discovers module tools at startup:

1. Scan global modules: `.datacore/modules/*/tools/index.ts`
2. Scan space modules: `[space]/.datacore/modules/*/tools/index.ts`
3. Register all tools with namespace prefix
4. Pass `ModuleToolContext` with scope-appropriate paths

Tools load only in full Datacore mode (`detectStorage().mode === 'full'`). Standalone mode gets core tools only.

### 6. Skills (SKILL.md Files)

Module skills follow the emerging SKILL.md standard:

```
skills/
└── inbox-triage/
    └── SKILL.md
```

```yaml
---
name: GTD Inbox Triage
description: Decision tree for processing inbox items
version: 1.0.0
tags: [gtd, inbox, triage]
---

# GTD Inbox Triage

When processing inbox items, apply this decision tree:

1. **Is it actionable?** ...
2. **Will it take less than 2 minutes?** ...
3. **Am I the right person?** ...
```

Skills are loaded into AI context when:
- A command or agent explicitly references them
- The `engram-inject` mechanism matches on skill keywords
- The user invokes them by name

### 7. Workflows

Workflows are multi-phase orchestrations declared in YAML. They compose tools, skills, agents, and commands into a pipeline.

#### Workflow Definition

```yaml
# workflows/create-presentation.yaml
name: create-presentation
description: End-to-end presentation creation pipeline
version: 1.0.0
trigger: /create-presentation

phases:
  - name: brief
    description: Gather intent, audience, template selection
    type: command
    handler: commands/create-presentation.md
    interactive: true
    outputs: [brief, template, audience, reused_slides]

  - name: content
    description: Generate slide definitions from brief
    type: agent
    handler: agents/presentation-generator.md
    inputs: [brief, template]
    outputs: [slide_definitions]

  - name: backgrounds
    description: Generate Midjourney/Gemini backgrounds
    type: tool
    module: image-generation
    tool: generate
    inputs: [slide_definitions, template.style]
    outputs: [background_images]
    optional: true

  - name: composition
    description: Compose text on backgrounds using Gemini 3 Pro
    type: tool
    tool: gemini.compose_slide
    inputs: [slide_definitions, background_images]
    outputs: [slide_images]
    iterate: per_slide

  - name: post_processing
    description: Add logos, apply formatting rules
    type: skill
    handler: skills/slide-post-processing/SKILL.md
    inputs: [slide_images, brand.logo]
    outputs: [final_slides]

  - name: review
    description: Per-slide approval and iteration
    type: agent
    handler: agents/presentation-generator.md
    inputs: [final_slides]
    interactive: true
    iterate: per_slide

  - name: assembly
    description: Compile final PDF
    type: tool
    tool: slides.compile_pdf
    inputs: [final_slides]
    outputs: [pdf_path]
```

#### Workflow Properties

| Property | Description |
|----------|-------------|
| `trigger` | Command that starts this workflow |
| `phases[].type` | `tool`, `skill`, `agent`, or `command` |
| `phases[].interactive` | Requires user input (pauses for human) |
| `phases[].iterate` | Repeat phase per item (e.g., `per_slide`) |
| `phases[].optional` | Phase can be skipped |
| `phases[].inputs` | Data from previous phases |
| `phases[].outputs` | Data produced for subsequent phases |

#### How Workflows Execute

**Execution model:** The trigger command acts as the orchestrator. It reads the workflow YAML and steps through phases sequentially. A shared **workspace directory** passes data between phases.

```
User invokes /create-presentation
  → Command loads workflows/create-presentation.yaml
  → Creates workspace: [space]/.datacore/modules/slides/state/workflows/[run-id]/
  → For each phase:
      1. Read inputs from workspace (files/JSON from previous phases)
      2. Dispatch to handler by type:
         - tool  → MCP tool call (structured I/O)
         - skill → Load SKILL.md into context (shapes next agent/command phase)
         - agent → Spawn via Task tool (receives workspace path)
         - command → Interactive prompt (human-in-the-loop)
      3. Write outputs to workspace (files/JSON for next phases)
      4. If interactive: pause, present to user, await input
      5. If iterate: loop per item (e.g., per_slide)
  → On completion: final outputs in workspace
  → Workspace persisted for resume (if session interrupted)
```

**Phase dispatch by type:**

| Type | How It Executes | I/O Mechanism |
|------|----------------|---------------|
| `tool` | Direct MCP tool call via `datacore.[module].[tool]` | Structured args in, JSON result out → workspace |
| `skill` | SKILL.md loaded into conversation context | Shapes subsequent phases (no direct output) |
| `agent` | Spawned via Task tool with workspace path in prompt | Reads/writes files in workspace dir |
| `command` | Interactive: presents to user, awaits response | User input captured to workspace |

**Skill phases** do not "execute" in the traditional sense — they inject knowledge that shapes how the next agent or command phase reasons. A skill phase followed by an agent phase means: "load this methodology, then let the agent apply it."

**State persistence:** Workflow state is stored at `[space]/.datacore/modules/[name]/state/workflows/[run-id]/`. If a session is interrupted mid-workflow, the next session can resume from the last completed phase via `/continue`.

> **Status note:** The workflow execution model is functional for the patterns described above. Advanced features (conditional branching, parallel phases, error recovery) are deferred to a future DIP amendment.

Workflows are **documentation-as-orchestration** — they make implicit multi-agent pipelines explicit and discoverable.

### 8. Engram Integration

#### Starter Engrams

Modules ship engrams in `engrams/engrams.yaml` with `visibility: template`.

> **DIP-0019 Amendment:** This DIP extends DIP-0019's `scope` enum with `module:[name]` (e.g., `scope: module:slides`). This allows engrams to be scoped to a specific module's context. DIP-0019 currently defines `agent:X`, `command:X`, `global`, and `space:X` — `module:X` follows the same pattern.

Example:

```yaml
engrams:
  - id: ENG-SLIDES-STARTER-001
    version: 2
    status: candidate           # Always candidate — user must approve
    type: procedural
    scope: module:slides
    visibility: template        # Marks as starter content
    statement: "Always regenerate slides instead of editing text in images — font mismatch is inevitable."
    rationale: "Gemini bakes fonts into images. Programmatic text overlay mismatches every time."
    domain: "slides/composition"
    tags: [slides, gemini, images]
    activation:
      retrieval_strength: 0.7
      storage_strength: 0.5
      frequency: 0
      last_accessed: null
    pack: slides-starter-v1
```

#### Installation Flow

1. Module installed, `engrams/engrams.yaml` is read
2. All starter engrams enter user's store with `status: candidate`
3. They surface in next daily review (per DIP-0019)
4. User approves, rejects, or defers
5. Approved engrams become `active` and start injecting

No foreign engrams enter active memory without human approval.

#### Engram Visibility Lifecycle

```
Module ships template engrams (best practices)
  → User installs, starter engrams enter as candidates
  → User approves into private store
  → User uses module, generates new private engrams
  → Over time, user promotes high-value private → public
  → Exchange protocol distributes public engrams
  → Other users receive as candidates
  → The network learns. Privacy preserved at every step.
```

| Visibility | Where It Lives | Who Sees It | How It Gets There |
|-----------|---------------|-------------|-------------------|
| `template` | Module `engrams/` dir | Everyone (ships with module) | Module author creates |
| `private` | Space `learning/engrams.yaml` | Only you | Session-learning + user approval |
| `public` | Space `learning/engrams.yaml` + exchange | Anyone via exchange | User explicitly promotes |

**Default is always `private`.** User must consciously promote to `public`.

#### Module Engram Namespace

Each module declares a namespace in module.yaml:

```yaml
engrams:
  namespace: slides
```

Engrams generated while using the module are tagged with this namespace. This enables:
- Scoped queries: "show me all slides learnings"
- Targeted injection: slides engrams inject when slides tools/agents run
- Scoped export: "export my slides engrams as a pack"

#### Relationship to DIP-0019 Packs

A module's `engrams/` directory IS a pack. The root `SKILL.md` serves double duty:
- **Module discovery**: Any AI ecosystem sees a valid skill
- **Pack entry point**: Datacore's pack system sees a valid engram pack

**Modules distribute methodology** (tools + skills + commands). **Packs distribute experience** (engrams). They are complementary.

### 9. Data Separation and Privacy

Applying DIP-0002: **module code is public, module data is private**.

#### Structure

```
MODULE CODE — PUBLIC (shareable)            USER DATA — PRIVATE (per-space)
────────────────────────────────            ────────────────────────────────
.datacore/modules/slides/                   [space]/.datacore/modules/slides/
├── SKILL.md                                ├── settings.local.yaml
├── module.yaml                             ├── state/
├── CLAUDE.base.md                          │   └── last-run.json
├── tools/                                  └── data/
├── skills/                                     └── slide-library.json
├── agents/
├── commands/                               [space]/.datacore/learning/
├── workflows/                              └── engrams.yaml
├── engrams/   (visibility: template)           ├── (template → approved)
└── templates/                                  ├── (user → private)
                                                └── (promoted → public)
```

#### Data Classification

| Data Type | Privacy | Location | Git-Tracked? |
|-----------|---------|----------|-------------|
| Module code (tools, agents, skills, workflows) | PUBLIC | `.datacore/modules/[name]/` | Yes |
| Module manifest (module.yaml) | PUBLIC | `.datacore/modules/[name]/` | Yes |
| Module context (CLAUDE.base.md) | PUBLIC | `.datacore/modules/[name]/` | Yes |
| Private context (CLAUDE.local.md) | PRIVATE | `.datacore/modules/[name]/` | No (gitignored) |
| Starter engrams | PUBLIC | `.datacore/modules/[name]/engrams/` | Yes |
| User settings | PRIVATE | `[space]/.datacore/modules/[name]/settings.local.yaml` | No |
| Runtime state | PRIVATE | `[space]/.datacore/modules/[name]/state/` | No |
| Module output/data | PRIVATE | `[space]/.datacore/modules/[name]/data/` | No |
| User engrams | PRIVATE | `[space]/.datacore/learning/engrams.yaml` | No |
| API keys/secrets | PRIVATE | `.datacore/env/.env` | No |

**The contribution test:** Can you `git push` the module directory without leaking personal data? If yes, the separation is correct.

**The rule:** Nothing in `.datacore/modules/[name]/` should be gitignored (except CLAUDE.local.md and CLAUDE.md composed output). If it needs to be gitignored, it belongs in the space-scoped path `[space]/.datacore/modules/[name]/`.

### 10. Installation Scope

Modules can be installed at three levels:

```
~/Data/
├── .datacore/modules/                    # GLOBAL — available everywhere
│   ├── gtd/
│   ├── nightshift/
│   └── research/
│
├── 0-personal/.datacore/modules/         # PERSONAL — only in personal space
│   ├── trading/
│   └── personal-finance/
│
├── 1-teamspace/.datacore/modules/        # SPACE — only in this space
│   ├── campaigns/
│   └── crm/
```

#### When to Install Where

| Scope | When | Examples | Available In |
|-------|------|---------|-------------|
| **Global** | Core methodology, used across all spaces | GTD, nightshift, research, learning | All conversations |
| **Personal** | Personal workflows, private data | trading, health, personal-finance | Personal space only |
| **Space** | Team/org/project-specific | campaigns, CRM, grants | That space only |

#### Resolution Order

When the same module name exists at multiple scopes:

```
1. Space:    [space]/.datacore/modules/[name]/     # Most specific — wins
2. Personal: 0-personal/.datacore/modules/[name]/
3. Global:   .datacore/modules/[name]/              # Least specific
```

Most specific scope wins. A space can override a global module with a customized version.

#### Installation Commands

```bash
# Global (available everywhere)
git clone https://github.com/datacore-one/datacore-slides .datacore/modules/slides

# Personal (personal space only)
git clone https://github.com/datacore-one/datacore-trading 0-personal/.datacore/modules/trading

# Space (team/org only)
git clone https://github.com/datacore-one/datacore-campaigns 1-teamspace/.datacore/modules/campaigns
```

#### MCP Tool Scoping

Global module tools are always registered. Space module tools are registered with scope awareness:

```typescript
interface ModuleToolContext {
  storage: StorageConfig
  modulePath: string        // Path to module code
  dataPath: string          // Scope-appropriate path to module's private data
  spaceName?: string        // Active space (if space-scoped module)
}
```

When `datacore.crm.lookup` is called and CRM is installed in `1-teamspace/`, the tool handler receives `dataPath` pointing to `1-teamspace/.datacore/modules/crm/data/`.

### 11. CLAUDE.md Integration

With 20+ modules, including full context for each would bloat CLAUDE.md. Modules declare a context priority:

#### Context Priority

```yaml
# module.yaml
context:
  priority: always | minimal | on_demand
  summary: "One-line description for minimal/on_demand mode"
```

| Priority | In CLAUDE.md | When Full Context Loads |
|----------|-------------|----------------------|
| `always` | Full CLAUDE.base.md included | Always present in every conversation |
| `minimal` | Summary line in module table only | When module tool/command invoked |
| `on_demand` | Not included | Only when explicitly referenced |

**Default is `minimal`**. Only foundational modules need `always`.

#### What Each CLAUDE.md Level Contains

**Root CLAUDE.md** (`~/Data/CLAUDE.md`) — global modules:

```markdown
## Global Modules

| Module | Priority | Tools | Commands | Description |
|--------|----------|-------|----------|-------------|
| gtd | always | 4 | 3 | Getting Things Done methodology |
| nightshift | always | 2 | 1 | Overnight AI task execution |
| research | minimal | 3 | 1 | Multi-source research pipeline |
| slides | minimal | 2 | 2 | Presentation creation |
| learning | always | 0 | 2 | Engram model (DIP-0019) |

<!-- Full context for 'always' modules: -->
<!-- @include .datacore/modules/gtd/CLAUDE.base.md -->
<!-- @include .datacore/modules/nightshift/CLAUDE.base.md -->
<!-- @include .datacore/modules/learning/CLAUDE.base.md -->
```

**Space CLAUDE.md** (`1-teamspace/CLAUDE.md`) — space modules:

```markdown
## Space Modules

| Module | Priority | Tools | Description |
|--------|----------|-------|-------------|
| campaigns | always | 3 | Landing pages, A/B testing |
| crm | minimal | 4 | Contact relationship management |

<!-- @include .datacore/modules/campaigns/CLAUDE.base.md -->
```

#### Module CLAUDE.base.md Format

Must be concise — ~20-30 lines:

```markdown
# Slides Module

Visual content generation — presentations with AI backgrounds.

## Tools (MCP)

| Tool | Description |
|------|-------------|
| `datacore.slides.compile_pdf` | Assemble slide images into PDF |
| `datacore.slides.list_templates` | List available design templates |

## Commands

- `/create-presentation` — End-to-end presentation creation workflow
- `/sync-gamma` — Pull presentations from Gamma

## When to Use

Triggers: presentation, slides, deck, pitch, keynote.

## Integration

- Depends on: `image-generation` module
- Settings: flat keys in `[space]/.datacore/modules/slides/settings.local.yaml`
```

#### context_merge.py Changes

The context merge tool is extended:

1. Discover modules at all scopes (global, personal, space)
2. Read `context.priority` from each module.yaml
3. `always`: include full CLAUDE.base.md
4. `minimal`: include summary line in module table only
5. `on_demand`: include nothing
6. Compose into CLAUDE.md

### 12. Naming Convention

#### Module Names

| Scope | module.yaml `name` | GitHub Repo | Directory |
|-------|-------------------|-------------|-----------|
| Official (datacore-one) | `slides` | `datacore-one/datacore-slides` | `modules/slides/` |
| Third-party | `acme/slides` | `acme-corp/datacore-slides` | `modules/acme-slides/` |

Rules:
- **module.yaml `name`**: lowercase, hyphen-separated. No prefix for official modules. Scoped (`org/name`) for third-party.
- **GitHub repo**: `[org]/datacore-[name]`. The `datacore-` prefix makes repos discoverable.
- **Directory**: matches module name. Third-party uses hyphenated scope: `acme-slides/`.
- **Tool namespace**: `datacore.[module].[tool]`. Third-party: `datacore.acme-slides.[tool]`.

Official modules (author: `datacore-one`) have no scope — implied official.

#### Naming Rules

- Module names: lowercase, alphanumeric + hyphens. No underscores.
- Skill names: lowercase, hyphen-separated.
- Tool names: lowercase, underscores (matches TypeScript function conventions).
- Agent names: lowercase, hyphen-separated.
- Command names: lowercase, hyphen-separated.
- Workflow names: lowercase, hyphen-separated.

### 13. Module Lifecycle

#### Creation

Use the `create-module` command or agent:

```
/create-module
```

The agent guides through:

1. **Understand intent** — create new, convert existing code, or audit existing module
2. **Gather information** — name, description, what it provides, dependencies
3. **Scaffold structure** — generate module.yaml, SKILL.md, CLAUDE.base.md, .gitignore, directories
4. **Create module.yaml** — all sections filled from gathered information
5. **Create commands** — conversational style (not CLI wrappers), with auto-run settings
6. **Create CLAUDE.base.md** — concise module context for AI
7. **Create .gitignore** — ignores CLAUDE.md, CLAUDE.local.md
8. **Apply five-layer decision** — for each capability, decide: tool, skill, agent, command, or workflow

**Scaffolding checklist** (from `create-module` agent):

| Required | File | Purpose |
|----------|------|---------|
| Yes | `module.yaml` | Manifest |
| Yes | `SKILL.md` | Ecosystem entry point |
| Yes | `CLAUDE.base.md` | AI context (public layer) |
| Yes | `.gitignore` | Privacy boundary |
| If tools | `tools/index.ts` | MCP tool registry |
| If skills | `skills/[name]/SKILL.md` | Knowledge injection |
| If agents | `agents/[name].md` | Reasoning prompts |
| If commands | `commands/[name].md` | Interactive workflows |
| If workflows | `workflows/[name].yaml` | Multi-phase pipelines |
| If engrams | `engrams/engrams.yaml` | Starter best practices |

#### Auditing

Audit an existing module for spec compliance:

```
/create-module audit
```

Or use the `create-module` agent with audit intent. The audit checks:

**Structure compliance:**
- [ ] `module.yaml` exists with all required fields
- [ ] `SKILL.md` exists with proper frontmatter and `x-datacore:` namespace
- [ ] `CLAUDE.base.md` exists and is concise (~20-30 lines)
- [ ] `.gitignore` present and correct
- [ ] No personal data in module directory (privacy check)
- [ ] All referenced files exist (agents, commands, skills)

**Five-layer compliance:**
- [ ] Deterministic operations are tools, not prompt-interpreted agents
- [ ] Knowledge/methodology in SKILL.md files, not hardcoded in agents
- [ ] Commands are conversational (not CLI wrappers)
- [ ] Multi-phase operations have workflow definitions
- [ ] Agent prompts include proper Agent Context section (per DIP-0016)

**Engram compliance:**
- [ ] Starter engrams use `visibility: template`
- [ ] Starter engrams use `status: candidate`
- [ ] Engram namespace matches module name
- [ ] No `visibility: private` in module's `engrams/` (those belong in space)

**Data separation compliance:**
- [ ] No user data in module directory
- [ ] Settings that vary per-user use `.local.yaml` pattern
- [ ] Module outputs reference space-relative paths, not absolute
- [ ] Module data paths point to `[space]/.datacore/modules/[name]/data/`

**Naming compliance:**
- [ ] module.yaml `name` follows convention
- [ ] Tool names use underscores
- [ ] Agent/command/skill names use hyphens
- [ ] No `datacore-` prefix in module.yaml `name`

#### Registration

After creation and audit, register in CATALOG:

**Via MCP tool:**
```
datacore.modules.register({
  module_path: ".datacore/modules/slides",
  create_repo: true,
  catalog_pr: true
})
```

**Via agent:**
```
:AI:module:register: Register slides module
```

**Via module-registrar agent, the registration process:**

1. **Validate** — run audit checklist (above)
2. **Create GitHub repo** — `gh repo create datacore-one/datacore-[name]` (if `create_repo: true`)
3. **Update CATALOG.md** — add entry to appropriate section
4. **Create PR** — submit changes for review (if `catalog_pr: true`)

**CATALOG.md entry format:**

```markdown
| [datacore-slides](https://github.com/datacore-one/datacore-slides) | Presentations with AI backgrounds | 2 tools, 2 skills, 2 agents | Yes |
```

#### Update

```bash
cd .datacore/modules/[name] && git pull
```

On update:
- New tools registered, removed tools deregistered (requires MCP server restart)
- New starter engrams enter as candidates
- Settings schema changes validated
- CLAUDE.md recomposed if context priority changed

#### Removal

```bash
rm -rf .datacore/modules/[name]
```

On removal:
- Tools deregistered from datacore-mcp
- Module engrams optionally retained or archived (user choice)
- Commands and skills become unavailable
- CLAUDE.md recomposed

### 14. Module Registry (CATALOG.md)

The catalog at `2-datacore/.datacore/CATALOG.md` is the official module registry.

#### Catalog Structure

```markdown
# Datacore Catalog

## Core Modules (ship with Datacore)

| Module | Description | Layers | Scope |
|--------|-------------|--------|-------|
| gtd | Getting Things Done methodology | 4T 2S 3A 3C 1W | Global |
| nightshift | Overnight AI task execution | 2T 1A 1C | Global |
| learning | Engram model (DIP-0019) | 0T 4S 2A 2C | Global |
| research | Multi-source research pipeline | 3T 1S 1A 1C 1W | Global |

## Community Modules

| Module | Author | Description | Layers | Repo |
|--------|--------|-------------|--------|------|
| slides | datacore-one | Presentations with AI backgrounds | 2T 2S 2A 2C 1W | datacore-one/datacore-slides |
| crm | datacore-one | Contact relationship management | 4T 1S 4A 1C | datacore-one/datacore-crm |
| acme/analytics | acme-corp | Custom analytics module | 3T 1A | acme-corp/datacore-analytics |
```

Legend: `T`=tools, `S`=skills, `A`=agents, `C`=commands, `W`=workflows

#### Catalog MCP Tools

| Tool | Description |
|------|-------------|
| `datacore.modules.list` | List installed modules: name, scope, version, layers provided |
| `datacore.modules.info` | Module details: manifest, tools, skills, agents, engrams, health |
| `datacore.modules.register` | Validate + add to CATALOG.md + optionally create repo + PR |
| `datacore.modules.install` | Install module from registry to specified scope (future) |
| `datacore.modules.remove` | Remove module and optionally archive engrams (future) |

### 15. Built-in vs Community Modules

| Built-in (ship with Datacore) | Community (install separately) |
|------------------------------|-------------------------------|
| GTD (methodology is foundational) | CRM |
| Nightshift (AI task execution) | Meetings |
| Learning (engram model) | Slides |
| Research (knowledge gathering) | Trading |
| | Campaigns |
| | Mail |
| | WhatsApp / Telegram |

Both built-in and community modules live in `.datacore/modules/`. Built-in modules are distinguished by `builtin: true` in module.yaml — they ship with Datacore and are maintained in the core repo. Community modules are separate repos installed by the user.

```yaml
# module.yaml for a built-in module
name: gtd
builtin: true    # Ships with Datacore, maintained in core repo
version: 1.0.0
```

Built-in modules:
- Are included in the datacore repo and distributed to `.datacore/modules/` during init/install
- Cannot be removed (only disabled via settings)
- Are updated via `./sync` (core repo pull), not `git pull` per module
- Have `context.priority: always` by default

## Rationale

### Why Five Layers

A single-layer approach fails:

- **Tools cannot reason** — they execute deterministic operations
- **Agents should not do plumbing** — every file read/write is a fragility point
- **Skills are not executable** — they shape behavior, they do not act
- **Commands are too heavy** — interactive workflows are wrong for programmatic operations
- **Without workflows** — multi-phase pipelines remain implicit and undiscoverable

### Why Single MCP Server

Alternatives considered:

1. **Per-module MCP servers**: N modules = N connections. Rejected: fragmented discovery, duplicated storage.
2. **No MCP, agents only**: Status quo. Rejected: slow, fragile, not portable.
3. **Single server with module registration** (chosen): one connection, shared storage, clean namespacing.

### Why SKILL.md as Entry Point

SKILL.md is becoming the standard for AI capability discovery. Using it as the module entry point makes modules visible to Claude Code, OpenClaw, Cursor, and others without Datacore-specific discovery.

### Why Starter Engrams Enter as Candidates

DIP-0019 safety: all foreign engrams require user approval. Module authors cannot inject unwanted behaviors. This also prevents conflicting engrams from different modules.

### Why Structured Data Separation

Without structural separation (code dir vs data dir), modules inevitably accumulate personal data that gets accidentally shared. The DIP-0002 principle (methodology public, data private) must be enforced by directory structure, not just metadata.

### Why Context Priority Tiers

20 modules with full CLAUDE.base.md = 600+ lines of context per conversation. Tiered inclusion (`always`/`minimal`/`on_demand`) keeps context lean while preserving discoverability.

## Backwards Compatibility

- Existing modules with only `agents/` and `commands/` continue to work unchanged
- `tools/`, `skills/`, `workflows/`, `engrams/`, and `SKILL.md` are optional additions
- Existing module.yaml `provides.commands` and `provides.agents` format preserved
- `provides.skills` accepts both string list (short form) and object list (full form) — see migration table
- datacore-mcp core 8 tools always available regardless of module tools
- Existing CATALOG.md format is a subset of the new format
- `create-module` agent updated to scaffold new structure but accepts old structure
- Audit mode reports gaps without requiring immediate migration
- `SKILL.md` is **required for new modules**; existing modules without it continue to function but should add one during migration

### Migration from v1 module.yaml

Modules using the v1 format (pre-DIP-0022) should migrate incrementally. No forced breaking changes — the `create-module audit` command reports gaps.

| v1 Field | v2 Field | Change | Notes |
|----------|----------|--------|-------|
| `learning:` | `engrams:` | Renamed + expanded | Was informal; now has `namespace`, `injection_policy`, `match_terms` |
| `use_cases:` | `engrams.match_terms` | Restructured | Use cases that triggered context injection are now match terms |
| `provides.skills: [string]` | `provides.skills: [{name, file}]` | Extended (both accepted) | Short form `["name"]` still works; full form `[{name, file}]` adds explicit paths |
| (none) | `provides.tools:` | New | MCP tool registration — add when porting operations to tools |
| (none) | `provides.workflows:` | New | Workflow definitions — add when formalizing multi-phase pipelines |
| (none) | `engrams:` | New | Engram configuration — add when shipping starter engrams |
| (none) | `context:` | New | CLAUDE.md inclusion behavior — defaults to `minimal` if absent |
| (none) | `manifest_version: 2` | New | Declares v2 format; absent = v1 assumed |
| flat settings (e.g., `auto_export_pdf`) | flat settings (unchanged) | No change | Settings remain flat keys without module prefix |
| `provides.mcp_servers:` | `requires.mcp_servers:` | Moved | External MCP servers are requirements, not provisions |

**Migration script** (Phase 3 implementation):
1. Scan modules for v1 patterns (`learning:`, `use_cases:`, data in module dir)
2. Generate migration report showing required changes
3. Optionally auto-migrate with user confirmation
4. Move any user data from module dirs to `[space]/.datacore/modules/[name]/data/`

## Security Considerations

- Module tools run with same filesystem permissions as datacore-mcp
- Module tool code is TypeScript — auditable, version-controlled
- Starter engrams require human approval before activation (DIP-0019 safety)
- SKILL.md files should not contain sensitive information (ecosystem-discoverable)
- `x-datacore:` namespace prevents frontmatter conflicts
- Tool namespace prevents collisions between modules
- Data separation enforced by directory structure (code dir gitignored differently from data dir)
- Third-party modules should be audited before installation
- Module settings with secrets use `.datacore/env/.env` (gitignored), not module.yaml

## Implementation

### Phase 1: Module Structure + SKILL.md
- Define module.yaml v2 schema with all new fields (`manifest_version: 2`)
- Add SKILL.md to existing modules (GTD, nightshift, research, slides)
- Update `create-module` agent to scaffold new structure
- Update `create-module` agent to audit against new spec (currently references DIP-0007 — must update to DIP-0022)
- Create module validation in audit mode

### Phase 2: MCP Tool Registration
- Add dynamic module tool loading to datacore-mcp `server.ts`
- Define `ModuleToolDefinition` TypeScript interface
- Add `datacore.modules.*` core tools (list, info, register)
- Port GTD module as first proof: `datacore.gtd.inbox_count`, `datacore.gtd.add_task`
- Update `module-registrar` agent to use `datacore.modules.register` tool

### Phase 3: Data Separation
- Create space-scoped module data directories: `[space]/.datacore/modules/[name]/data/`
- **Migrate existing module data** from module dirs to space dirs:
  1. Scan modules for `output/`, `data/`, `state/`, `*.json`, `*.db` in module code dir
  2. For each file: determine target space (personal if ambiguous)
  3. Move to `[space]/.datacore/modules/[name]/data/[filename]`
  4. Update any hardcoded paths in module agents/commands
  5. Add moved paths to module `.gitignore` as safety net
  6. Verify module still functions after migration
- Update module agents to use space-scoped data paths via `ModuleToolContext.dataPath`
- Add privacy audit to `create-module` audit mode (flag any non-code files in module dir)

### Phase 4: CLAUDE.md Integration
- Add `context.priority` to module.yaml schema
- Update `context_merge.py` to handle tiered module inclusion
- Generate module tables in composed CLAUDE.md
- Set priority for all existing modules

### Phase 5: Workflows
- Define workflow YAML schema
- Add `workflows/` to module structure
- Create workflow executor (agent or orchestration layer)
- Port slides module as first proof: `create-presentation` workflow

### Phase 6: Engram Integration
- Create `engrams/` directories with starter packs per module
- Connect module `engrams.namespace` to DIP-0019 tagging
- Test installation flow: module install -> engrams enter as candidates
- Add engram compliance to audit checklist

### Phase 7: Naming + CATALOG
- Standardize all existing module names
- Fix `datacore-campaigns` directory name -> `campaigns`
- Update CATALOG.md format with layer counts
- Add third-party module support to naming convention

## Settings

```yaml
# .datacore/settings.yaml (or settings.local.yaml)
modules:
  auto_register_tools: true         # Register module tools with MCP on startup
  tool_namespace_prefix: datacore    # Prefix for all module tools
  engram_auto_import: true           # Import starter engrams on module install
  default_context_priority: minimal  # Default CLAUDE.md inclusion level
```

## Open Questions

1. **Hot-reloading**: Should datacore-mcp reload module tools without restart?
2. **Tool permissions**: Should modules declare required permissions (filesystem, network)?
3. **Skill auto-injection**: Should skills inject automatically based on context, or only on explicit reference?
4. **Workflow state**: Should workflow phase completion be persisted for resume across sessions?
5. **Module marketplace**: Discovery and distribution beyond git clone (npm, registry API).
6. **Module testing**: Should modules ship with test suites? What format?

## References

### Datacore
- [DIP-0002: Layered Context Pattern](./DIP-0002-layered-context-pattern.md)
- [DIP-0009: GTD Specification](./DIP-0009-gtd-specification.md)
- [DIP-0014: Tag Taxonomy](./DIP-0014-tag-taxonomy.md)
- [DIP-0016: Agent Registry](./DIP-0016-agent-registry.md)
- [DIP-0019: Learning Architecture](./DIP-0019-learning-architecture.md)
- [DIP-0021: Search & Research Architecture](./DIP-0021-search-research-architecture.md)
- [datacore-specification.md](../specs/datacore-specification.md) — Module section
- [CATALOG.md](../../2-datacore/.datacore/CATALOG.md) — Module registry
- [@datacore-one/mcp](../../2-datacore/2-projects/datacore-mcp/) — Reference MCP server
- `create-module` agent — Module creation and auditing
- `module-registrar` agent — Module registration

### External
- [Model Context Protocol SDK](https://github.com/modelcontextprotocol/sdk)
- SKILL.md convention — Emerging standard for AI skill discovery

---

*This DIP supersedes the module structure defined in datacore-specification.md Section "Modules" and establishes the five-layer capability model with data separation, engram integration, and workflow orchestration.*
