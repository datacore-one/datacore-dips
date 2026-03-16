# DIP-0024: Reactive Hooks Infrastructure

| Field | Value |
|-------|-------|
| **DIP** | 0024 |
| **Title** | Reactive Hooks Infrastructure |
| **Author** | Gregor |
| **Type** | Standards Track |
| **Status** | Draft |
| **Created** | 2026-03-16 |
| **Updated** | 2026-03-16 |
| **Tags** | `hooks`, `infrastructure`, `memory`, `lifecycle` |
| **Affects** | `.datacore/registry/`, `.claude/settings.json`, all DIPs/modules |
| **Specs** | DIP-0016 (Agent Registry), DIP-0019 (Learning Architecture) |
| **Agents** | - |

## Summary

Datacore agents, commands, and engrams exist but lack systematic wiring to the moments they're needed. This DIP introduces a declarative hooks infrastructure where every DIP and module can declare reactive hooks — "when event X occurs, inject context Y / run action Z." These declarations compose into a single runtime configuration that ships with Datacore.

## Motivation

### The Session Start Problem

The Datacore MCP server instructs Claude to call `session.start` at conversation beginning. This depends on the AI remembering — which it doesn't when the task "doesn't seem like a Datacore workflow." In a real session (2026-03-15), Claude skipped `session.start`, then created a GTD task by raw-editing an org file, bypassing the entire GTD pipeline. Every safeguard was in place but none were triggered.

### The Stale Context Problem

Engram injection is one-shot at `session.start`. When conversations shift domains (research → task creation → trading), injected engrams become stale. There is no mechanism to re-inject when context changes.

### The Ad-Hoc Hooks Problem

Datacore already has hooks:
- Git pre-commit (`.datacore/hooks/pre-commit`) — DIP-0002 privacy validation
- Agent lifecycle hooks (`hooks.py`) — nightshift pre/post execution
- Org date validation hook — pre-commit date checking

But these are ad-hoc, manually installed, and not declared by the DIPs they serve. Modules cannot declare "when X happens, do Y."

### What This Enables

- **Active memory**: Engrams injected at moments of action, not just session start
- **GTD guardrails**: Org file edits routed through proper tooling automatically
- **Module autonomy**: Modules declare their own hooks without editing core config
- **Composability**: All hooks merge into a single runtime configuration
- **Robustness**: The system works because hooks fire automatically, not because the AI remembers

## Specification

### 1. Hook Families

Three hook families, unified by a single registry:

| Family | Runtime | Output | Declared By |
|--------|---------|--------|-------------|
| **Claude Code** | `.claude/settings.json` | AI behavior hooks | DIPs, modules |
| **Git** | `.git/hooks/*` | Code quality gates | DIPs, modules |
| **Datacore Internal** | `hooks.py` execution | Agent lifecycle | DIP-0016 (existing) |

This DIP focuses on Claude Code hooks (the new capability) and formalizes Git hook composition. Datacore Internal hooks are already specified in DIP-0016 §16-17.

### 2. Hook Declaration Format

DIPs and modules declare hooks in their specification or `module.yaml`:

```yaml
hooks:
  claude_code:
    - event: PreToolUse
      matcher: EnterPlanMode
      type: command
      command: "python3 .datacore/lib/active_memory.py --event plan_mode"
      purpose: "Inject architectural engrams when entering plan mode"
      declared_by: DIP-0019
      priority: 100

    - event: PreToolUse
      matcher: "Edit|Write"
      type: command
      command: "python3 .datacore/lib/org_guard.py"
      purpose: "Enforce org_workspace_adapter for org-mode files"
      declared_by: DIP-0009
      priority: 200

  git:
    - hook: pre-commit
      source: .datacore/hooks/privacy-check.sh
      purpose: "DIP-0002 privacy layer validation"
      declared_by: DIP-0002
      priority: 100
```

#### Field Definitions

| Field | Required | Description |
|-------|----------|-------------|
| `event` | Yes (claude_code) | Claude Code hook event type |
| `matcher` | No | Regex matcher for the event |
| `type` | Yes (claude_code) | `command`, `prompt`, or `agent` |
| `command` | Yes (command type) | Shell command to execute |
| `prompt` | Yes (prompt/agent type) | Prompt for LLM evaluation |
| `purpose` | Yes | Human-readable description |
| `declared_by` | Yes | DIP number or module name |
| `priority` | No | Execution order (lower = first, default 500) |
| `async` | No | Run asynchronously (default: false) |
| `timeout` | No | Timeout in seconds (default: 10) |
| `hook` | Yes (git) | Git hook name (pre-commit, pre-push, etc.) |
| `source` | Yes (git) | Path to hook script |

### 3. Registry: `.datacore/registry/hooks.yaml`

Central registry composed from all declarations:

```yaml
version: 1.0.0
protocol: datacore-hook-registry/v1

claude_code:
  SessionStart:
    - matcher: startup
      type: command
      command: "python3 .datacore/lib/session_bootstrap.py"
      purpose: "Initialize session tracker, load journal"
      declared_by: DIP-0019
      priority: 100

  UserPromptSubmit:
    - type: command
      command: "python3 .datacore/lib/session_firstmsg.py"
      purpose: "First message: session.start with task. Subsequent: skip (1ms)."
      declared_by: DIP-0019
      priority: 100

  PreToolUse:
    - matcher: EnterPlanMode
      type: command
      command: "python3 .datacore/lib/active_memory.py --event plan_mode"
      purpose: "Full engram injection for planning"
      declared_by: DIP-0019
      priority: 100

    - matcher: Skill
      type: command
      command: "python3 .datacore/lib/active_memory.py --event skill"
      purpose: "Domain engrams based on skill name"
      declared_by: DIP-0019
      priority: 200

    - matcher: Agent
      type: command
      command: "python3 .datacore/lib/active_memory.py --event agent"
      purpose: "Agent-scoped engrams"
      declared_by: DIP-0016
      priority: 200

    - matcher: "Edit|Write"
      type: command
      command: "python3 .datacore/lib/org_guard.py"
      purpose: "Enforce org_workspace for org-mode files"
      declared_by: DIP-0009
      priority: 300

    - matcher: "Write"
      type: command
      command: "python3 .datacore/lib/privacy_guard.py"
      purpose: "Validate no private content in .base.md files"
      declared_by: DIP-0002
      priority: 300

  SubagentStart:
    - matcher: ".*"
      type: command
      command: "python3 .datacore/lib/active_memory.py --event subagent"
      purpose: "Inject agent-scoped engrams into subagent context"
      declared_by: DIP-0016
      priority: 100

  PostCompact:
    - matcher: "auto|manual"
      type: command
      command: "python3 .datacore/lib/active_memory.py --event rehydrate"
      purpose: "Re-inject critical engrams after context compaction"
      declared_by: DIP-0019
      priority: 100

  SessionEnd:
    - matcher: ".*"
      type: command
      command: "python3 .datacore/lib/session_cleanup.py"
      purpose: "session.end, Hebbian write-back, cleanup state"
      declared_by: DIP-0019
      priority: 900

git:
  pre-commit:
    - source: .datacore/hooks/privacy-check.sh
      purpose: "DIP-0002 privacy + PII + secrets scan"
      declared_by: DIP-0002
      priority: 100

    - source: .datacore/hooks/org-date-fix.sh
      purpose: "Validate org-mode date accuracy"
      declared_by: DIP-0009
      priority: 200
```

### 4. Latency-Aware Design

The critical constraint: hooks add latency to every interaction. The design minimizes this.

#### UserPromptSubmit: First-Message-Only Pattern

`UserPromptSubmit` fires on every user message but must be fast on the hot path.

```python
# session_firstmsg.py — the UserPromptSubmit handler
import json, sys, os

STATE = os.path.expanduser("~/Data/.datacore/state/active_session.json")

# Hot path: session already started → exit immediately (~1ms)
if os.path.exists(STATE):
    sys.exit(0)

# Cold path: first message → full session.start
input_data = json.load(sys.stdin)
prompt = input_data.get("prompt", "")

# Create state file
with open(STATE, "w") as f:
    json.dump({"started": True, "first_prompt": prompt[:200]}, f)

# Output additionalContext with session bootstrap
# (calls engram selector, formats injection)
context = bootstrap_session(prompt)
json.dump({"additionalContext": context}, sys.stdout)
```

**Latency profile:**
- First message: ~500ms (engram selection + injection)
- Every subsequent message: ~1ms (file existence check, exit)

#### PreToolUse: Action-Time Injection

These fire only when specific tools are used — not on every message. Acceptable latency budget: 200-500ms.

```
EnterPlanMode  → ~500ms (full injection, infrequent)
Skill          → ~200ms (domain lookup by skill name)
Agent          → ~200ms (scope lookup by agent type)
Edit|Write     → ~50ms  (path pattern check, exit if not *.org)
```

#### Cost Summary

| Interaction | Added Latency |
|---|---|
| Normal message (after first) | ~1ms |
| First message of session | ~500ms |
| Entering plan mode | ~500ms |
| Invoking slash command | ~200ms |
| Spawning agent | ~200ms |
| Editing org file | ~50ms (guard check) |
| Editing non-org file | ~50ms (path check, exit) |
| Context compaction | ~500ms (re-injection) |

### 5. Hooks Composer

A Python script that reads all hook declarations and outputs runtime configuration.

```bash
# Rebuild all hooks from registry + module declarations
python3 .datacore/lib/hooks_composer.py rebuild

# Validate hooks (check for conflicts, missing scripts)
python3 .datacore/lib/hooks_composer.py validate

# Show what would be generated (dry run)
python3 .datacore/lib/hooks_composer.py rebuild --dry-run
```

#### Composition Rules

1. **Read sources**: `.datacore/registry/hooks.yaml` + all `.datacore/modules/*/module.yaml`
2. **Merge**: Group by event type and matcher
3. **Order by priority**: Lower number = runs first
4. **Conflict detection**: Warn if two hooks have same event+matcher+priority
5. **Output**: Write `.claude/settings.json` (Claude Code hooks), compose `.git/hooks/*` (Git hooks)

#### Output: `.claude/settings.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .datacore/lib/session_bootstrap.py",
            "timeout": 10
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .datacore/lib/session_firstmsg.py",
            "timeout": 5
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "EnterPlanMode",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .datacore/lib/active_memory.py --event plan_mode",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .datacore/lib/active_memory.py --event skill",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Agent",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .datacore/lib/active_memory.py --event agent",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .datacore/lib/org_guard.py",
            "timeout": 5
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .datacore/lib/active_memory.py --event subagent",
            "timeout": 5
          }
        ]
      }
    ],
    "PostCompact": [
      {
        "matcher": "auto|manual",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .datacore/lib/active_memory.py --event rehydrate",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .datacore/lib/session_cleanup.py",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

### 6. Active Memory Scripts

The hook scripts live in `.datacore/lib/` and share a common engram selection engine.

#### `active_memory.py`

The core injection script. Called by multiple hooks with different `--event` flags.

```
active_memory.py --event plan_mode    # Full injection: architecture, patterns, mistakes
active_memory.py --event skill        # Domain injection by skill name (from stdin tool_input)
active_memory.py --event agent        # Scope injection by agent type (from stdin tool_input)
active_memory.py --event subagent     # Agent-scoped injection for subagent context
active_memory.py --event rehydrate    # Re-inject all active engrams after compaction
```

Each event handler:
1. Reads JSON from stdin (Claude Code hook input)
2. Extracts relevant context (skill name, agent type, compact summary)
3. Calls engram selector (same logic as `inject-tool.ts`, ported to Python)
4. Outputs JSON with `additionalContext` to stdout

#### `org_guard.py`

The GTD guardrail. Called on `Edit|Write` PreToolUse.

```
Input: tool_input with file_path
Logic:
  1. Check if file_path matches *.org
  2. If not → exit 0 (no action, ~1ms)
  3. If yes → output additionalContext warning:
     "This is an org-mode file. Use org_workspace_adapter.py
      for task operations. Capture to inbox.org first."
  4. Optionally: exit 2 to block (strict mode)
```

#### `session_bootstrap.py`

SessionStart handler. Lightweight — no engram injection (no task context yet).

```
Logic:
  1. Clean up stale active_session.json if exists
  2. Initialize session tracker state
  3. Output additionalContext with journal + candidate count
```

#### `session_firstmsg.py`

UserPromptSubmit handler. First-message-only pattern (§4).

#### `session_cleanup.py`

SessionEnd handler. Calls session.end equivalent, cleans up state file.

### 7. Module Hook Declarations

Modules declare hooks in their `module.yaml`:

```yaml
# .datacore/modules/trading/module.yaml
name: trading
version: 1.1.0
hooks:
  claude_code:
    - event: PreToolUse
      matcher: Skill
      type: command
      command: "python3 .datacore/lib/active_memory.py --event skill --domain trading"
      purpose: "Inject trading framework engrams for trading commands"
      condition: "skill_name matches trading:*"
      priority: 150
```

The composer merges module hooks with core hooks, respecting priority ordering.

### 8. DIP Hook Audit

Every existing DIP should be audited for implicit hook points. Recommended additions:

| DIP | Hook to Add | Event | Purpose |
|-----|------------|-------|---------|
| DIP-0002 | Privacy guard | PreToolUse(Write) on `.base.md` | Block private content in public layer |
| DIP-0009 | Org guard | PreToolUse(Edit\|Write) on `*.org` | Enforce GTD pipeline |
| DIP-0009 | Date validation | PreToolUse(Write) on `*.org` | Verify day-of-week accuracy |
| DIP-0011 | Task queue check | SessionEnd | Queue pending AI tasks |
| DIP-0016 | Agent context | SubagentStart | Inject agent-scoped engrams |
| DIP-0019 | Session lifecycle | SessionStart, UserPromptSubmit, SessionEnd | Full session lifecycle |
| DIP-0019 | Active memory | PreToolUse(EnterPlanMode, Skill, Agent) | Action-time injection |
| DIP-0019 | Rehydration | PostCompact | Re-inject after compaction |

## Rationale

### Why Declarative?

Hooks could be configured manually in `.claude/settings.json`. But:
- Manual configuration doesn't scale with modules
- No way to know which DIP/module needs which hooks
- No validation that required hooks are installed
- No composition when multiple modules need the same event

### Why Command Hooks (Not Agent Hooks)?

Agent hooks spawn a subagent with full tool access — powerful but slow (seconds). Command hooks run a shell script — fast but limited to stdout output. For active memory injection:
- Speed matters more than capability
- The engram selector can run as Python without MCP access
- `additionalContext` output is sufficient for injection

Agent hooks remain available for special cases (complex validation, multi-step checks) but are not the default.

### Why Not UserPromptSubmit on Every Message?

Considered and rejected. Adding even 100ms to every interaction degrades the conversational feel. The first-message-only pattern gives us the critical bootstrap at session start, then tool-based hooks catch domain shifts at action time — zero cost on the 99% of messages between actions.

### Why Not a Plugin?

Plugins are installable packages. But hooks are core to how Datacore works — they're not optional extras. The composer ensures hooks ship with the installation, not as a separate install step.

## Backwards Compatibility

- **No breaking changes.** Existing installations have no `.claude/settings.json` — the composer creates it.
- **Existing git hooks** (`.datacore/hooks/pre-commit`) continue to work. The composer absorbs them into the composed output.
- **Existing `hooks.py`** (DIP-0016 internal hooks) is unaffected — different hook family.
- **Modules without hook declarations** simply contribute no hooks to the composition.

## Security Considerations

- Hook scripts run with the user's permissions — same as any Claude Code tool call.
- Command hooks receive tool input on stdin — may contain file paths, user prompts. Scripts must not log sensitive input.
- The org guard and privacy guard act as security boundaries — they should fail closed (block on error, not allow).
- `active_session.json` state file is in `.datacore/state/` (gitignored) — no sensitive data exposure.

## Implementation

### Phase 1: Core Infrastructure
1. Create `hooks_composer.py` — registry reader, merger, settings.json writer
2. Create `.datacore/registry/hooks.yaml` — initial core hooks
3. Create `session_firstmsg.py` — first-message-only UserPromptSubmit handler
4. Create `session_bootstrap.py` — SessionStart handler
5. Create `session_cleanup.py` — SessionEnd handler

### Phase 2: Active Memory
6. Port engram selector logic from `inject-tool.ts` to Python (`active_memory.py`)
7. Implement event handlers: plan_mode, skill, agent, subagent, rehydrate
8. Create `org_guard.py` — GTD org file guardrail

### Phase 3: Composition & Integration
9. Add `hooks:` section to core DIP registry entries
10. Add `hooks:` section to module.yaml spec (DIP-0022)
11. Integrate composer into install/update workflow
12. Audit all existing DIPs and modules for hook declarations

### Phase 4: DIP Audit
13. Update DIP-0002 with privacy guard hook declaration
14. Update DIP-0009 with org guard + date validation hooks
15. Update DIP-0016 with agent context injection hooks
16. Update DIP-0019 with full session lifecycle + active memory hooks
17. Update remaining DIPs as applicable

### Reference Implementation

Branch: `dip-0024-reactive-hooks`

### Rollout Plan

1. Implement Phase 1 (infrastructure) — no behavioral change yet
2. Implement Phase 2 (active memory) — session.start becomes automatic
3. Run for 1-2 weeks, measure latency impact, tune timeouts
4. Phase 3-4 (composition + audit) — full system integration

## Open Questions

1. **Strict vs advisory org guard**: Should the org guard block edits (exit 2) or just inject a warning (additionalContext)? Strict is safer but may frustrate when the pipeline is genuinely broken.

2. **Hook testing**: How do we test hooks? A `hooks_composer.py test` that simulates events and checks output format?

3. **Hook disable mechanism**: Should users be able to disable specific hooks via `settings.local.yaml`? E.g., disable the org guard during debugging.

4. **Cross-platform**: The scripts assume Python 3.10+ and Unix paths. Windows support needed?

## References

- [DIP-0016: Agent Registry](DIP-0016-agent-registry.md) — existing lifecycle hooks (§16-17)
- [DIP-0019: Learning Architecture](DIP-0019-learning-architecture.md) — engram injection, session lifecycle
- [DIP-0009: GTD Specification](DIP-0009-gtd-specification.md) — task management workflow
- [DIP-0002: Layered Context Pattern](DIP-0002-layered-context-pattern.md) — privacy validation
- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks.md) — hook event types and capabilities
- Karpathy autoresearch `program.md` — inspiration for autonomous agent loop pattern
- Session 2026-03-15: The failure that motivated this DIP (raw org edit bypassing GTD)
