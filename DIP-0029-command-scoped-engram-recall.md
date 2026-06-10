# DIP-0029: Command-Scoped Engram Recall

| Field | Value |
|-------|-------|
| **DIP** | 0029 |
| **Title** | Command-Scoped Engram Recall |
| **Author** | @datacore-one |
| **Type** | Standards Track |
| **Status** | Implemented |
| **Created** | 2026-05-12 |
| **Updated** | 2026-05-12 |
| **Tags** | `engrams`, `memory`, `commands`, `modules`, `recall`, `hooks`, `plur` |
| **Affects** | `.datacore/commands/`, `.datacore/modules/*/module.yaml`, `.datacore/lib/hooks/`, `~/.claude/settings.json`, `.datacore/lib/bootstrap/setup-datacore.sh` |
| **Specs** | `datacore-specification.md` |
| **Extends** | DIP-0016 (Agent Registry), DIP-0019 (Learning Architecture), DIP-0024 (Reactive Hooks) |
| **Related Engrams** | ENG-2026-0411-001, ENG-2026-0505-029, ENG-2026-0512-038, ENG-2026-0512-039 |

## Summary

Commands, modules, workflows, agents, and skills MAY declare a `recall:` frontmatter field listing engram IDs, scopes, and tags whose content MUST be injected into the agent's context immediately before the command body is loaded. A complementary PreToolUse hook provides a fallback for harnesses that don't honor the frontmatter (vanilla Claude Code, OpenClaw without `@plur-ai/claw`, third-party agents).

The motivating failure: prose references to engrams inside command bodies (e.g. *"This is the fix for ENG-2026-0411-001"*) are systematically ignored. The agent reads the citation as descriptive text rather than as a load instruction. The engram content itself never enters context, so the lesson encoded in the engram does not steer behavior.

This DIP closes the gap by making memory load declarative and harness-enforced.

## Motivation

### The bug

On 2026-05-12, /wrap-up was invoked. The command body explicitly cited `ENG-2026-0411-001` ("Anti-compression rule: If you feel tempted to skip steps 6-9, STOP. ... This is the fix for ENG-2026-0411-001."). The agent:

1. Read the citation as prose
2. Did not retrieve the engram content
3. Created a 7-task checklist (spec requires ~17 items)
4. Compressed steps 6-9 silently — exactly the failure ENG-2026-0411-001 documents

This is the second documented occurrence of the same failure mode in /wrap-up (first was 2026-04-11). The engram existed both times. Both times it failed to influence behavior because it wasn't in context.

### Why prose citation isn't enough

Long command bodies (15K+ tokens) push individual instructions into background noise. Engram statements, by contrast, are loaded as activation-weighted memory blocks with explicit semantic priority. An engram in context steers behavior; a prose citation does not.

### Why this affects more than /wrap-up

The same pattern is present in:

- `/today` — references `ENG-2026-0411-001` (compression rules)
- `/research` — references multiple research methodology engrams
- `/megaphone-campaign` — references prospect-research learning engrams
- `/ship` — references CI-gate engrams
- Every module's `module.yaml` could similarly benefit from declaring "these engrams matter for this module's commands"

Without a declarative mechanism, every command author must remember to write "ALWAYS call plur_recall_hybrid for X before doing Y" in their command body, and every command runner must remember to do it. This is an implicit contract that fails systematically.

## Agent Context

### When to Reference This DIP

**Always reference when:**
- Authoring a new command, module, workflow, agent, or skill
- Auditing an existing command for failure-mode coverage
- Building a harness that resolves `Skill` / slash command / `Agent` invocations
- Adding hooks to `~/.claude/settings.json` or the equivalent on OpenClaw / Hermes

**Key decisions this DIP informs:**
- Memory load contract between command spec and harness
- Hook chain ordering (recall MUST fire before command body executes)
- Engram lifecycle: where authored engrams get auto-loaded vs. on-demand recalled

## Specification

### 1. The `recall:` frontmatter field

Commands and module definitions MAY declare a `recall:` block as YAML frontmatter:

```yaml
---
name: wrap-up
description: Session wrap-up before closing a Claude Code conversation
recall:
  ids:
    - ENG-2026-0411-001
    - ENG-2026-0505-029
  scopes:
    - command:wrap-up
  tags:
    - wrap-up
    - session-close
  query:                    # optional — free-text query for hybrid recall
    - "wrap-up step skipping"
  k: 8                      # optional — max results per source (default 5)
---
```

**Field semantics:**

- `ids:` — explicit engram IDs. Always loaded if they exist in the PLUR store. If missing, log a warning but do not fail.
- `scopes:` — load all engrams in any of the listed scopes. Format follows PLUR scope conventions (`command:NAME`, `module:NAME`, `project:NAME`, `global`).
- `tags:` — load top-K engrams matching any of the listed tags, ranked by recency × reinforcement count.
- `query:` — free-text queries passed to `plur_recall_hybrid` (BM25 + embeddings).
- `k:` — global cap on results per source. Default 5.

**Composition:** the harness MUST load the union of all results, deduplicate by engram ID, and rank by descending retrieval strength. Total token budget for the injected block SHOULD NOT exceed 2K tokens; truncate by lowest-ranked first if needed.

### 2. Harness contract

When a Datacore-aware harness resolves a `Skill`, slash command, `Agent` invocation, or module entrypoint with a `recall:` block:

1. Parse the frontmatter
2. Resolve all engrams via `plur_recall_hybrid` (or direct fetch for explicit IDs)
3. Format results as a markdown block titled `## Relevant memory (engrams)` with one entry per engram (statement + ID + scope)
4. Prepend the block to the command body **before** the body is loaded into agent context
5. The block MUST appear inside the same context turn as the command body, not in a separate system message that the agent might skip

**Failure mode:** if PLUR is unavailable or returns no results, the harness MUST proceed without the injected block but emit a structured warning (logged, not displayed) so the run can be reviewed post-hoc.

### 3. PreToolUse hook fallback

For harnesses that don't parse `recall:` frontmatter, a PreToolUse hook MUST fire on `Skill` / `Agent` / slash command invocations:

**Script:** `.datacore/lib/hooks/command_recall_inject.py`

**Behavior:**
1. Extract the skill/agent/command name from the tool args
2. Call `plur_recall_hybrid` with the name as query, k=8
3. Filter for `scope:command:NAME`, `tag:NAME`, or relevance score above threshold
4. Emit a structured `additionalContext` block via stdout that the harness injects before the tool runs
5. Timeout: 3 seconds. If recall fails, emit empty block and continue (fail-open, never block)

**Registration:** the hook MUST be registered in `~/.claude/settings.json` under `PreToolUse` with matchers `Skill|Agent|SlashCommand`.

**Install integration:** `.datacore/lib/bootstrap/setup-datacore.sh` MUST add the hook registration to `~/.claude/settings.json` during install / upgrade. If a user-managed `settings.json` already has hooks, the script MUST merge non-destructively (preserve existing hooks, add the recall hook idempotently).

### 4. Module-level `recall:`

`module.yaml` MAY declare a module-level `recall:` block that applies to every command in the module. Command-level `recall:` blocks compose with the module's: union of IDs, scopes, tags, queries.

```yaml
# module.yaml
name: nightshift
recall:
  scopes:
    - module:nightshift
  tags:
    - nightshift
```

### 5. Agent-level `recall:`

Agents in `.datacore/agents/*.md` and `.datacore/modules/*/agents/*.md` MAY declare `recall:` blocks. When spawned, the agent's bootstrap context includes the matching engrams in the same `## Relevant memory` block format.

### 6. Workflow / skill compatibility

The Superpowers skill system uses Markdown bodies without strict frontmatter. For skills that wish to participate:

- Place a YAML frontmatter block at the top of the skill file (same shape as commands)
- The harness treats it identically

## Implementation Plan

### Phase 0 — Hot-patch (this DIP introduction, complete)

- /wrap-up command body has `recall:` frontmatter referencing ENG-2026-0411-001, ENG-2026-0505-029, ENG-2026-0512-038, ENG-2026-0512-039
- Even before any harness honors the block, the command body's prose can reference the frontmatter ("see `recall:` block for required memory load") which sharpens the convention.

### Phase 1 — Hook (immediate)

- Build `.datacore/lib/hooks/command_recall_inject.py`
- Register in `~/.claude/settings.json` PreToolUse on `Skill|Agent|SlashCommand`
- Update `setup-datacore.sh` install/upgrade script to add the registration idempotently

### Phase 2 — Harness implementation (Datacore command runner)

- Implement `recall:` frontmatter parser in the command resolution path
- Add engram resolution via PLUR MCP tools
- Format `## Relevant memory` block injection
- Token-budget cap at 2K, truncate by rank

### Phase 3 — Migration

- Top-5 high-failure commands receive `recall:` frontmatter in this PR: /wrap-up, /today, /research, /ship, /megaphone-campaign
- Top-5 high-value commands receive `recall:` next: /continue, /tomorrow, /standup, /ingest, /create-presentation
- All module `module.yaml` files audited for module-level `recall:` (default to `scope:module:NAME`)

### Phase 4 — Cross-harness parity

Reference implementation lives in `.datacore/lib/hooks/command_recall_inject.py`.
Any compliant harness MUST replicate the following contract:

1. **Trigger surface.** Fire on every Skill / SlashCommand / Agent / module
   entrypoint invocation (or the harness's local equivalent).
2. **Discovery.** Map the tool's name to a command file:
   - `.datacore/commands/<NAME>.md`
   - `.datacore/modules/<MODULE>/commands/<NAME>.md` (including the explicit
     `<MODULE>:<NAME>` form used by Skill names)
   - `.datacore/agents/<NAME>.md` and `.datacore/modules/<MODULE>/agents/<NAME>.md`
   - `.datacore/modules/<MODULE>/module.yaml` (module-level scope)
3. **Frontmatter parse.** Read YAML frontmatter; extract the `recall:` block.
4. **Composition.** Union module-level recall and command-level recall (per §4
   of this DIP).
5. **Resolution.** Resolve `ids` directly from the local PLUR store; resolve
   `scopes`, `tags`, `query` via BM25-style retrieval against the same store.
6. **Scoring.** Weights: explicit id = 100, scope = 50, tag = 30, query keyword
   = 10 × hits. Plus implicit name match: 25 for `scope:command:<name>`, 10 for
   `name` in tags, 5 for `name` in domain.
7. **Injection.** Emit a markdown block titled `## Relevant memory for /<name>
   (DIP-0029 ...)` containing one `- **ID** — statement` line per engram, capped
   at ~2K tokens. The block MUST appear inside the same context turn as the
   command body.
8. **Fail-open.** Any error path returns empty context — never block tool
   execution.

Harness-specific notes:

- **OpenClaw plugin `@plur-ai/claw`** — honors `recall:` blocks in command files
  via its command-resolution pipeline. Same contract as above; node-side
  implementation may share the PLUR npm package's recall API directly instead
  of shelling out to Python.
- **Hermes shell hooks** — `.sh` command stubs can declare a leading comment
  block (`# recall: { ids: [...], scopes: [...] }`) parsed by a shell-side
  helper. Reuse Datacore's Python resolver via a thin `plur-recall --command
  <name>` CLI invocation.
- **Datacore desktop app** — command palette renders the recall block as a
  collapsible "Memory" section in the command preview UI, so the user can see
  what context will be loaded before running.

### Phase 5 — Audit

- `agent-registry-auditor` extended to invoke
  `.datacore/lib/audit_recall_coverage.py` and surface three drift categories:
  `missing-recall`, `empty-recall`, `failure-mode-uncovered`.
- Failure-mode uncovered: an engram whose scope/domain/tag matches the command
  name AND whose type is `behavioral` / `corrective` / `operational` is treated
  as a high-signal candidate for the command's `recall.ids`. Auto-suggest, do
  not auto-apply (false-positive risk on tag matches).
- Weekly review surfaces drift trends — the uncovered count should be flat or
  shrinking.

## Rationale

### Why declarative frontmatter (option a)

- Self-documenting — the spec author states the memory contract
- Greppable — `grep -A5 "recall:" commands/*.md` shows the memory dependency graph
- Auditable — `agent-registry-auditor` can flag commands without `recall:` blocks against the engram failure-mode index
- Version-controlled — changes to `recall:` are visible in PRs

### Why PreToolUse hook (option b)

- Catches every command, including third-party / untagged ones
- Works without harness modifications — runs in any environment that supports the hook protocol
- Lossy fallback — recall via name query is less precise than declared IDs, but never silent

### Why both

- (a) is the durable, declarative layer that compounds over time
- (b) is the safety net for the long tail
- Together they form a defense-in-depth pattern for the engram-recall failure mode

## Backwards Compatibility

- Existing commands without `recall:` continue to work; the harness skips injection
- The PreToolUse hook is opt-in via `~/.claude/settings.json` registration; agents not using it are unaffected
- No engram format changes — DIP-0019 engram schema is preserved
- Existing PreToolUse hooks (e.g. `plur_session_guard.py`) compose with the new recall hook via standard hook chain semantics

## Open Questions

- **Token budget tuning.** 2K hard cap or per-command override? Probably both — allow `recall.budget: 4000` per command for memory-heavy commands like /research.
- **Cache strategy.** Re-fetch on every command invocation or cache for the session? PLUR is local and fast (<50ms); re-fetch is acceptable.
- **Cross-space scope.** When invoked from a project folder under focus mode, should `recall:` resolve scopes from the parent space too? Default yes.
- **Conflicting injections.** If a command sets `recall:` AND the PreToolUse hook also fires, prefer declared (frontmatter wins, hook contributes only previously-unseen engrams).

## References

- ENG-2026-0411-001 — /wrap-up subagent dispatch failure mode (the bug this DIP prevents)
- ENG-2026-0505-029 — Token cost 5000x estimation error
- ENG-2026-0512-038 — session_token_count.py mandatory for /wrap-up
- ENG-2026-0512-039 — /wrap-up checklist must name coordinators
- DIP-0016 — Agent Registry & Discoverability (lifecycle hooks)
- DIP-0019 — Learning Architecture (engram model)
- DIP-0024 — Reactive Hooks Infrastructure (hook system)
- `~/.claude/settings.json` — Claude Code hook registration
- `.datacore/lib/bootstrap/setup-datacore.sh` — install script

## Changelog

- 2026-05-12: Initial draft. Authored after a documented /wrap-up failure where the engram designed to prevent the failure was not in context.
- 2026-05-12: Phases 2-5 implemented. Status → Final.
  - Phase 2: `command_recall_inject.py` rewritten to parse `recall:` frontmatter from command + module.yaml files; resolves ids/scopes/tags/queries with explicit scoring (id=100, scope=50, tag=30, query=10/hit). Composes module-level + command-level recall blocks.
  - Phase 3a: 16 top-level commands migrated to `recall:` default block (`scopes: [command:NAME]`, `tags: [NAME]`).
  - Phase 3b: 73 module commands migrated to `recall:` default block.
  - Phase 3c: 34 `module.yaml` files received module-level `recall:` declarations.
  - Phase 4: Cross-harness parity contract specified in §Implementation Plan §Phase 4 — reference implementation (`command_recall_inject.py`) is canonical; OpenClaw / Hermes / desktop app implementations follow the 8-step contract.
  - Phase 5: `audit_recall_coverage.py` ships as the audit helper. `agent-registry-auditor` extended with a "Recall Coverage Audit" section that calls the helper. Drift categories: missing-recall, empty-recall, failure-mode-uncovered.
