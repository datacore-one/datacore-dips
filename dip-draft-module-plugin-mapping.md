# DIP-DRAFT: Datacore Module to Claude Code Plugin Canonical Mapping

| Field | Value |
|-------|-------|
| **DIP** | DRAFT (pending number assignment) |
| **Title** | Datacore Module → Claude Code Plugin Canonical Mapping |
| **Author** | @datacore-one |
| **Type** | Standards Track |
| **Status** | Draft |
| **Created** | 2026-08-23 |
| **Tags** | `modules`, `plugins`, `claude-code`, `sdk`, `interop`, `portability` |
| **Affects** | `.datacore/modules/*/module.yaml`, `.datacore/modules/*/agents/`, `.datacore/modules/*/skills/`, `.datacore/modules/*/hooks/` |
| **Specs** | DIP-0022 (Module Specification), DIP-0016 (Agent Registry) |
| **Agents** | `create-module`, `module-registrar` |

---

## Summary

The Claude Agent SDK plugin system (`.claude-plugin/plugin.json`, `agents/`, `skills/`, `hooks/`, `.mcp.json`) is structurally parallel to the Datacore module layout. This DIP defines a canonical field mapping between the two formats and specifies an integration path — a generator that produces a valid `plugin.json` from an existing `module.yaml` — so that Datacore modules can be loaded as Claude Code plugins without duplicating agent definitions or maintaining a second format.

---

## Motivation

Datacore modules define agents, skills, hooks, MCP server configs, and context (CLAUDE.base.md). The Claude Code SDK independently defines a plugin system with equivalent constructs. Today these are maintained separately: `module.yaml` is the source of truth for Datacore, and `.claude-plugin/plugin.json` is the source of truth for SDK-native loading. Maintaining both in parallel has three costs:

1. **Redundancy**: Agent names, descriptions, model hints, and tool restrictions live in `module.yaml` and `agents.yaml` but must be re-expressed in any SDK-native wrapper.
2. **Drift**: Changes to module.yaml do not propagate to plugin.json. The PLUR project (5-plur workspace) already exhibits this: `.claude-plugin/plugin.json` carries only identity metadata (`name`, `version`, `description`, `author`) — no agent, skill, hook, or MCP definitions — which means SDK-native loading of PLUR does not expose any capabilities beyond the manifest.
3. **Discovery gap**: Claude Code can only load Datacore modules via `CLAUDE.md` injection and manual `mcpServers` config in `settings.json`/`.mcp.json`. A canonical plugin.json would allow SDK-native `plugins` loading, making Datacore modules first-class plugins installable by any Claude Code user without Datacore-specific setup.

---

## Current State of Both Systems

### Datacore Module Layout (DIP-0022)

```
.datacore/modules/<name>/
├── module.yaml          # Manifest — all metadata, provides, settings, hooks, deps
├── SKILL.md             # Ecosystem entry point (SKILL.md standard)
├── CLAUDE.base.md       # Context injected into CLAUDE.md (public layer)
├── tools/               # MCP tool handlers (TypeScript, compiled to index.js)
├── skills/              # SKILL.md files — methodology knowledge
│   └── <skill>/SKILL.md
├── agents/              # Agent prompts (markdown with YAML frontmatter)
│   └── <name>.md
├── commands/            # Slash command implementations
│   └── <name>.md
├── workflows/           # Multi-phase pipelines (YAML)
│   └── <name>.yaml
├── engrams/             # Starter best-practice engrams
│   └── engrams.yaml
└── hooks/               # Lifecycle hooks (referenced from module.yaml)
```

The module manifest (`module.yaml`) is YAML, versioned (`manifest_version: 2`), and declares:
- `provides.tools` — MCP tool names, descriptions, handler paths
- `provides.agents` — agent names and trigger tags
- `provides.skills` — SKILL.md paths
- `provides.commands` — slash command names
- `provides.workflows` — workflow definitions
- `requires.mcp_servers` — external MCP server configs
- `engrams.*` — engram namespace, policy, match terms
- `context.*` — CLAUDE.md inclusion priority
- `hooks.*` — event hook file references (today, wrap-up, nightshift_queue, post_install)
- `settings.*` — user-configurable flat keys
- `recall.*` — DIP-0029 engram scopes

Agent files (`.datacore/agents/<name>.md`) carry YAML frontmatter with: `name`, `description`, `model`, `tools` (allowlist), `effort`, `color`.

### Claude Code Plugin Layout (Claude Agent SDK)

```
<project>/
└── .claude-plugin/
    ├── plugin.json      # Manifest — identity + discovery metadata
    ├── agents/          # Agent definitions
    ├── skills/          # Skill files (SKILL.md standard)
    ├── hooks/           # Event handler scripts
    └── .mcp.json        # MCP server configs for this plugin
```

The `plugin.json` manifest is JSON. As observed in the PLUR workspace (the only live example in this installation), it currently carries only identity fields:

```json
{
  "name": "plur",
  "version": "0.9.13",
  "description": "...",
  "author": { "name": "...", "url": "..." },
  "homepage": "...",
  "repository": "...",
  "license": "...",
  "keywords": [...]
}
```

No `agents`, `skills`, `hooks`, or `mcp` sections are present in the observed examples. This indicates the PLUR plugin is using `.claude-plugin/` primarily as a discovery manifest (identity + npm-style metadata), not as a full capability declaration. The SDK may support additional fields that are not yet populated in these examples.

From the frontmatter schema pattern (`_patterns/frontmatter-schema.md`) and `settings.json`, the agent definition format is already SDK-native: Claude Code reads the YAML frontmatter in `.datacore/agents/<name>.md` directly. The `tools`, `model`, `name`, `description`, `effort`, and `color` fields are read natively by the Claude CLI as of claude 2.1.x.

---

## Canonical Field Mapping

### plugin.json ↔ module.yaml

| `module.yaml` field | `plugin.json` field | Notes |
|---|---|---|
| `name` | `name` | Direct 1:1. Module name becomes plugin name. |
| `version` | `version` | Direct 1:1. |
| `description` | `description` | Direct 1:1. module.yaml description → plugin.json description. |
| `author` | `author.name` | module.yaml `author` (string) → plugin.json `author.name`; `author.url` is Datacore-specific extra. |
| `repository` | `repository` | Direct 1:1. |
| `license` | `license` | Direct 1:1. |
| `engrams.match_terms` | `keywords` | Approximate mapping. Match terms double as discovery keywords. |
| `requires.mcp_servers` | `.mcp.json` | External MCP servers move to a sibling `.mcp.json` file in the plugin dir. |
| (no direct equivalent) | `homepage` | Module-specific; can be derived from repository URL if needed. |

### Agent definition mapping

| Datacore (agent frontmatter) | Claude Code plugin `agents/` | Notes |
|---|---|---|
| `name` | filename + `name` frontmatter | Identical field. Plugin agent files follow the same frontmatter schema. |
| `description` | `description` frontmatter | Identical. |
| `model` | `model` frontmatter | Identical. Values: `haiku`, `sonnet`, `opus`, `inherit`. |
| `tools` | `tools` frontmatter | Identical. Same allowlist format. |
| `effort` | `effort` frontmatter | Identical. |
| `color` | `color` frontmatter | Identical. |
| Module-level agent body (system prompt) | Agent file body | Identical markdown body. |
| `provides.agents[].trigger` | Not in plugin format | Datacore-specific `:AI:` tag routing. No SDK equivalent — stays in `agents.yaml`. |

**Key insight**: The agent file format is already identical. Datacore agent files at `.datacore/agents/<name>.md` can be symlinked or copied directly into `.claude-plugin/agents/` without modification.

### Skills mapping

| Datacore | Plugin | Notes |
|---|---|---|
| `modules/<name>/skills/<skill>/SKILL.md` | `.claude-plugin/skills/<skill>/SKILL.md` | Identical format. SKILL.md is already the SDK-standard. |
| `module.yaml provides.skills[].file` | Plugin discovers SKILL.md by directory convention | No manifest declaration needed — SDK discovers by presence. |
| `x-datacore:` frontmatter namespace in SKILL.md | Ignored by SDK (unknown namespace passthrough) | Safe. Other ecosystems skip unknown frontmatter keys. |

### Commands ↔ Skills (slash commands)

| Datacore `commands/<name>.md` | Plugin `skills/<name>/SKILL.md` | Notes |
|---|---|---|
| Slash command body (markdown, invoked via `/name`) | SKILL.md body | Conceptually equivalent but different invocation model. SDK skills are injected into context; Datacore commands are invoked interactively. |
| Command name → `/command-name` | Skill name → invoked by mention or hook | Not a clean 1:1. SDK does not have an interactive slash-command layer equivalent — skills are context-injected, not interactively executed. |

**Gap**: Datacore commands (interactive multi-step workflows) have no direct SDK plugin equivalent. Plugin skills are knowledge-injection, not execution entry points. This is the widest structural gap between the two formats.

### Hooks mapping

| Datacore (`module.yaml` hooks) | Plugin `hooks/` | Notes |
|---|---|---|
| `hooks.today` → hook file path | `hooks/SessionStart` or similar event handler | Approximate. Datacore hooks are module.yaml-declared + consumed by `hooks_composer.py`. SDK hooks are event-driven scripts in `hooks/`. |
| `hooks.post_install` → shell command string | `hooks/PostInstall` (if SDK supports) | Possible mapping if SDK supports lifecycle hooks. |
| `settings.json` `hooks.*` (SessionStart, PreToolUse, PostToolUse, etc.) | `.claude-plugin/hooks/` | System-level hooks in settings.json are project-global, not plugin-scoped. Plugin hooks, if supported, would be scoped to the plugin's session. |
| `hooks.nightshift_queue` | No SDK equivalent | Nightshift is Datacore-internal scheduling. No plugin analog. |

### MCP server configs

| Datacore | Plugin | Notes |
|---|---|---|
| `requires.mcp_servers` in module.yaml | `.claude-plugin/.mcp.json` | Direct mapping. The module's required external MCP servers become the plugin's `.mcp.json`. |
| `tools/index.js` registered via `@datacore-one/mcp` | Plugin would need its own MCP server or rely on SDK tool exposure | **Major gap**: Datacore module tools register with a shared `datacore-mcp` bus. Plugin format expects standalone MCP servers or SDK-native tool definitions. Module tools are not directly portable without wrapping each module's `tools/index.js` in its own MCP server. |

### CLAUDE.base.md → Plugin context

| Datacore | Plugin | Notes |
|---|---|---|
| `modules/<name>/CLAUDE.base.md` | No direct plugin equivalent | CLAUDE.base.md is Datacore's system context injection. SDK plugins may inject context via SKILL.md or agent system prompts, but there is no plugin-level "inject this into CLAUDE.md" hook. |
| `context.priority: always` | SKILL.md loaded by default | Approximate: a root-level SKILL.md in the plugin can serve as always-on context. |
| `context.priority: on_match` | SKILL.md match terms trigger injection | The `x-datacore` match_terms in SKILL.md frontmatter support this pattern already. |

---

## Comparison: Dual Format vs. Canonical Mapping

### Alternative: Keep formats separate

Maintain module.yaml as Datacore's internal format and plugin.json as a thin wrapper that carries only identity metadata (the current PLUR approach). Modules load via CLAUDE.md injection and settings.json mcpServers config; plugins load via SDK `plugins` option. Both coexist independently.

**Why this fails at scale**: As Datacore modules mature and the Claude Code plugin ecosystem grows, duplicate maintenance compounds. Every agent update, skill addition, or MCP server config change must be applied in two places. The PLUR example already shows the result: the plugin.json is effectively a no-op for capability loading.

### Why a canonical mapping, not a conversion script or symlinks

**Conversion scripts** produce output that immediately falls out of date. A `module.yaml → plugin.json` conversion run at install time solves the initial setup but does not solve ongoing drift.

**Symlinks** work for agent files (the formats are identical) but break for `plugin.json` itself (different serialization — YAML vs JSON) and for any generated or composed artifacts (CLAUDE.md, the compiled tools/index.js).

**A canonical mapping** (this DIP) makes `module.yaml` the single source of truth and defines a **generator** that produces `plugin.json` and any plugin-layout artifacts on demand, always from the authoritative source. The generator is idempotent — running it twice produces the same output. This is the only durable solution.

---

## Integration Path

### What would it take to make a Datacore module loadable as a Claude Code plugin?

**Step 1: Extend module.yaml with plugin metadata**

Add a `plugin` block to `module.yaml` that carries fields the SDK needs but Datacore does not currently use:

```yaml
plugin:
  homepage: "https://plur.ai"
  keywords: [gtd, tasks, org-mode]   # Augments or overrides engrams.match_terms for discovery
  sdk_min_version: "2.1"              # Minimum claude CLI version for plugin loading
  capabilities:
    agents: true      # Plugin exposes agents/
    skills: true      # Plugin exposes skills/
    hooks: false      # Plugin does not use hooks/
    mcp: true         # Plugin has .mcp.json
```

No existing module.yaml fields need to change. `plugin:` is additive.

**Step 2: Create a generator command (`/export-plugin` or `datacore.modules.export_plugin`)**

The generator reads `module.yaml` and produces the `.claude-plugin/` layout:

```
module.yaml
  → .claude-plugin/plugin.json        (generated — identity + keywords)
  → .claude-plugin/agents/<name>.md   (symlinked from modules/<name>/agents/<name>.md)
  → .claude-plugin/skills/<name>/     (symlinked from modules/<name>/skills/<name>/)
  → .claude-plugin/.mcp.json          (generated from requires.mcp_servers)
  → .claude-plugin/hooks/             (converted from module.yaml hooks — if SDK supports)
```

Agent files can be symlinked because the format is identical. `plugin.json` and `.mcp.json` must be generated (different serialization, different structure). CLAUDE.base.md has no plugin equivalent and is omitted.

**Step 3: The MCP tool gap requires a workaround**

Datacore module tools (tools/index.js) register with the shared `datacore-mcp` bus. A plugin loaded via SDK does not automatically get access to `datacore-mcp`. Two options:

- **Option A (short-term)**: List `datacore-mcp` in the plugin's `.mcp.json` so that any consumer who loads the plugin also gets `datacore-mcp`. This only works if `datacore-mcp` is installable as a standalone npm package, which it is (`@datacore-one/mcp`).
- **Option B (long-term)**: Each module bundles its own MCP server (following DIP-0028's bundled tools guidance). The module's `tools/index.js` becomes the entry point for a standalone MCP server that the plugin's `.mcp.json` references. This is the correct long-term architecture for full portability.

**Which modules are closest to plugin-ready today?**

| Module | Agent files | SKILL.md | requires.mcp_servers | tools/index.js | Plugin-readiness |
|---|---|---|---|---|---|
| `gtd` | Yes (4 agents) | Yes | None | Yes (11 tools) | High — needs Option A for tools |
| `research` | Yes (2 agents) | Yes | None (uses datacore-mcp tools) | Yes (3 tools) | High — needs Option A |
| `nightshift` | Yes (5 agents) | Yes | None | No | Very high — no tool gap |
| `crm` | Yes | Yes | None | Yes | High — needs Option A |
| `slides` | Yes | Yes | gamma (has own MCP server) | Yes | Medium — gamma server is already standalone |

The `nightshift` module has no tools layer and no external MCP dependencies — it is the closest to being plugin-ready today.

---

## Risks

**Format drift**: The Claude Code plugin format is not publicly versioned or specification-locked as of this writing. The observed `plugin.json` schema (identity-only fields) is minimal. Anthropic may extend it with `agents`, `skills`, `hooks`, or `mcp` top-level keys that conflict with Datacore's generated output. Mitigation: pin `sdk_min_version` in the `plugin:` block and test against SDK version bumps in CI.

**Scope mismatch — nightshift and scheduling**: Nightshift execution (`nightshift_queue` hook, systemd timers, multi-phase autonomous execution) has no equivalent in the plugin model. Plugin hooks are session-scoped, not scheduled. This is a hard boundary: nightshift features cannot be expressed as plugin capabilities. Any plugin export of the nightshift module should clearly exclude these capabilities from its `plugin.capabilities` declaration.

**Scope mismatch — engrams**: The engram system (DIP-0019, PLUR memory store) is Datacore-internal. Plugin consumers who do not have Datacore installed will not benefit from engram injection. Engram-dependent agent behaviors will degrade silently in plugin-only mode. Mitigation: document this explicitly in plugin README.

**Tool registration gap**: The shared `@datacore-one/mcp` bus is the primary tool delivery mechanism. Plugins that reference it via `.mcp.json` create a dependency on a Datacore-specific package. This is an acceptable dependency for Datacore users but breaks the plugin's portability for non-Datacore consumers. Option B (standalone MCP servers per module, per DIP-0028) is the correct long-term answer but requires significant migration work.

**Maintenance surface**: A generator introduces a new artifact (`plugin.json`, symlinks) that must stay in sync with `module.yaml`. The generator must be idempotent and run automatically (post-install hook or CI step) to prevent drift. Without automation, the generator output will diverge from source just as the current PLUR plugin.json has diverged.

**Symlink portability**: The `agents/` and `skills/` symlinks in `.claude-plugin/` work on Linux/macOS but may fail on Windows or in certain CI environments. The generator should offer a copy mode as a fallback.

---

## Recommendation

**Spike** this in one module before formalizing as a full DIP.

Recommended target: `nightshift` module (no tool gap, no external MCP dependencies, 5 agents, 1 SKILL.md). Steps:

1. Add the `plugin:` block to `nightshift/module.yaml`
2. Write a 50-line Python generator (`datacore.modules.export_plugin` tool or standalone script) that produces `.claude-plugin/plugin.json` from `module.yaml`
3. Symlink `nightshift/agents/*.md` → `.claude-plugin/agents/`
4. Symlink `nightshift/skills/` → `.claude-plugin/skills/`
5. Load the plugin in a test Claude Code session via `plugins` in settings.json
6. Verify agent dispatch works (spawn `nightshift-orchestrator` via Agent tool)

If the spike succeeds — agents load, SKILL.md injects correctly, no SDK format conflicts — then:

**Formalize as a numbered DIP** extending DIP-0022, adding:
- `plugin:` block to the module.yaml schema
- `datacore.modules.export_plugin` MCP tool
- Generator spec (field mapping table from this document)
- CI integration: run generator on `module.yaml` change

If the spike reveals SDK format requirements that conflict with Datacore conventions (e.g., the SDK mandates a different agent frontmatter schema), **explore** adaptation options before committing to the mapping.

Do **not** update the `module-deployment-checklist.md` until the spike validates the approach. The checklist covers server deployment; plugin loading is a local development workflow. They address different audiences and should remain separate documents.

---

## Backwards Compatibility

- All existing `module.yaml` files continue to function unchanged. The `plugin:` block is optional and additive.
- Existing Datacore module loading (via CLAUDE.md, settings.json mcpServers) is unaffected.
- The generator produces files in `.claude-plugin/` — a new directory that does not conflict with any existing module layout.
- Modules without a `plugin:` block in module.yaml are not exported as plugins.

---

## Security Considerations

- Symlinked agent files from the module directory to `.claude-plugin/agents/` inherit the same content. No new attack surface beyond the existing module code.
- The generated `plugin.json` contains only identity metadata — no secrets, no credentials.
- The generated `.mcp.json` may contain MCP server command lines. Follow the same credential handling as `.datacore/env/.env` — never embed API keys in generated files.
- Plugin consumers who install a Datacore module as a plugin without Datacore installed get tools registered via `@datacore-one/mcp`. They should be aware this is a Datacore dependency, not a neutral SDK component.

---

## Implementation

### Phase 1: Spike (1-2 days)

- [ ] Add `plugin:` block to `nightshift/module.yaml`
- [ ] Write generator script: `module.yaml → .claude-plugin/plugin.json`
- [ ] Create symlinks: `agents/*.md` → `.claude-plugin/agents/`
- [ ] Create symlinks: `skills/` → `.claude-plugin/skills/`
- [ ] Test SDK plugin loading in local Claude Code session
- [ ] Document findings

### Phase 2: Formalize (if spike succeeds)

- [ ] Assign DIP number and status: Proposed
- [ ] Add `plugin:` schema to DIP-0022 module.yaml spec
- [ ] Implement `datacore.modules.export_plugin` MCP tool in datacore-mcp
- [ ] Update `create-module` agent to scaffold `plugin:` block
- [ ] Add generator to CI pipeline (run on module.yaml change)
- [ ] Migrate highest-readiness modules: nightshift, research, gtd

### Phase 3: Tool gap resolution (long-term)

- [ ] Assess DIP-0028 bundled tools progress
- [ ] Define per-module MCP server wrapper pattern (Option B)
- [ ] Update generator to produce standalone `.mcp.json` per module
- [ ] Remove dependency on `@datacore-one/mcp` for plugin consumers

---

## Open Questions

1. Does the Claude Agent SDK `plugin.json` support `agents`, `skills`, `hooks`, or `mcp` top-level keys beyond the identity fields observed in the PLUR workspace? The current evidence (two plugin.json files, both identity-only) is insufficient to confirm the full schema. A quick SDK documentation check or Anthropic changelog review should resolve this before the spike.

2. How does the SDK load agents from `plugins/agents/`? Does it merge them with the project's own `.datacore/agents/`, or keep them namespaced? If namespaced (e.g., `Agent(nightshift:nightshift-orchestrator)`), spawning logic in existing agents (which use bare `Agent(nightshift-orchestrator)`) may need updating.

3. Is there a `plugins` config key in `settings.json` today? The observed `settings.json` has `"enabledPlugins": {}` (empty). This confirms the SDK has a plugin loading mechanism but it is not yet in use. Does enabling a plugin require listing it explicitly or is convention-based discovery sufficient?

4. Should the generator produce a copy of agent files or symlinks? Symlinks are cleaner (single source of truth) but less portable. The module-deployment-checklist may need a note on symlink behavior on target servers.

---

## References

- [DIP-0022: Module Specification](./DIP-0022-module-specification.md) — five-layer module architecture
- [DIP-0028: Module Tool Loading Architecture](./DIP-0028-module-tool-loading-architecture.md) — bundled vs runtime tool loading
- [DIP-0016: Agent Registry](./DIP-0016-agent-registry.md) — agent frontmatter schema and discovery
- [DIP-0002: Layered Context Pattern](./DIP-0002-layered-context-pattern.md) — CLAUDE.base.md privacy model
- [DIP-0019: Learning Architecture](./DIP-0019-learning-architecture.md) — engram portability constraints
- `.datacore/agents/_patterns/frontmatter-schema.md` — agent frontmatter schema (current spec)
- `5-plur/plur/.claude-plugin/` — live example of Claude Code plugin layout (identity-only)
- `5-plur/2-projects/.wt-941-engine-warn/.claude-plugin/plugin.json` — second live example (same pattern)
- `.datacore/settings.json` — `"enabledPlugins": {}` confirms SDK plugin loading mechanism exists
- `.mcp.json` — root-level MCP server config (separate from plugin-scoped `.mcp.json`)
- Claude Agent SDK plugin system (`plugins` option in settings.json)
- SKILL.md convention — emerging AI skill discovery standard
