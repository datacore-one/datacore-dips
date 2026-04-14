# DIP-0025: Evaluation & Benchmarking (datacore-bench)

| Field | Value |
|-------|-------|
| **DIP** | 0025 |
| **Title** | Evaluation & Benchmarking (datacore-bench) |
| **Author** | Gregor |
| **Type** | Core |
| **Status** | Draft |
| **Created** | 2026-03-16 |
| **Updated** | 2026-03-16 |
| **Tags** | `evaluation`, `benchmarking`, `testing`, `transparency` |
| **Affects** | `2-datacore/2-projects/datacore-bench/`, `2-datacore/2-projects/datacore-mcp/` |
| **Specs** | DIP-0019 (Learning Architecture), DIP-0011 (Nightshift) |
| **Agents** | - |

## Summary

A three-layer evaluation system that measures whether Datacore actually improves Claude Code or just adds overhead. Provides always-on instrumentation (Scorecard), automated A/B testing (Harness), and real-world session replay (Replay). Results are public, reproducible, and fully automated — the user only sees reports.

## Motivation

Datacore adds a knowledge layer (engrams, memory, context injection) and an orchestration layer (agents, workflows, modules) on top of Claude Code. But there is no way to measure:

1. **Does it work?** — Does Claude + Datacore produce better results than Claude alone?
2. **What does it cost?** — What's the token/time overhead of Datacore's MCP calls?
3. **Is it improving?** — Do upgrades make things better or worse?
4. **Can we prove it?** — Can others verify our claims on their own setups?

Without answers, Datacore risks being an elaborate placebo. This DIP establishes the evaluation infrastructure to answer these questions with data.

## Specification

### Architecture

Three evaluation layers on a shared data foundation:

```
┌─────────────────────────────────────┐
│         datacore-bench              │
├──────────┬──────────┬───────────────┤
│  Harness │  Replay  │  Scorecard    │
│  (A)     │  (B)     │  (C)         │
│  Auto    │  Real    │  Always-on    │
│  A/B     │  world   │  metrics      │
├──────────┴──────────┴───────────────┤
│        Shared Data Layer            │
│  (session logs, token counts,       │
│   engram usage, tool calls)         │
└─────────────────────────────────────┘
```

**Build order**: C first (data foundation), then A (automated testing), then B (exploratory replay).

### Two Axes of Value

Datacore provides two distinct kinds of value, tested separately and together:

- **Knowledge layer**: Engrams, memory, context injection, learned preferences. Makes Claude "know you."
- **Orchestration layer**: DIPs, agents, commands, workflows, modules. Makes Claude "do more."

### Prerequisites & Cross-Project Dependencies

| Dependency | Required By | Status | Notes |
|------------|------------|--------|-------|
| MCP logging middleware | Layer C | New work | TypeScript, in datacore-mcp repo |
| Token usage estimation | Layer C | Unsolved | Estimate from input/output sizes |
| Claude Code CLI programmatic sessions | Layer A, B | Needs research | `claude -p` with different MCP configs |
| Versioned data schema | All layers | New work | JSON schema for session logs |

### Layer C: Scorecard (Always-On Instrumentation)

Logs every Datacore MCP interaction automatically. Zero user effort.

**Per session**:
- Every MCP tool call (name, duration, estimated tokens)
- Engrams injected at session.start (count, IDs)
- Engram feedback (positive/negative/neutral) — proxy for relevance
- Engrams created via `learn`
- Session duration

**Derived metrics**:
- **Overhead ratio**: tokens on Datacore tools vs. total session
- **Injection hit rate**: % of injected engrams with positive feedback
- **Memory growth**: created vs. retired engrams
- **Automation coverage**: % of :AI:-tagged tasks completed without human revision (numerator: tasks in DONE state whose output files had no human edits within 48 hours; denominator: all :AI:-tagged tasks that reached execution)
- **Nightshift success rate**: score >= threshold in evaluator pipeline

**Implementation**: Logging middleware in datacore-mcp writes structured JSON. Python aggregates into reports.

### Layer A: Harness (Automated A/B Testing)

Runs the same scenarios with and without Datacore, scores the delta.

**Test categories**:

| Category | Tests What | Example |
|----------|-----------|---------|
| Continuation | Memory/context | "What did we decide about X?" |
| Preference | Learned patterns | "Write a commit message" |
| Convention | Project knowledge | "Add a new agent" |
| Cold task | Overhead cost | Standard coding task |
| Orchestration | Workflow quality | "Process this inbox item" |

**Example scenario** (`scenarios/continuation/recall-decision.yaml`):
```yaml
name: recall-prior-decision
category: continuation
description: Tests whether Datacore helps recall a decision made in a prior session
prompt: "We discussed the authentication approach last week. What did we decide?"
seed_data: seed-data/auth-decision-engram.yaml
scoring:
  - type: deterministic
    check: contains
    value: "JWT with refresh tokens"
    weight: 1.0
  - type: llm-judge
    criterion: "Does the response provide specific context about why this decision was made?"
    scale: 1-5
    weight: 0.5
```

**How a test runs**:
1. Scenario defined as YAML: prompt, context, expected behaviors, scoring criteria
2. **Run A**: Fresh Claude Code session WITH Datacore
3. **Run B**: Fresh Claude Code session WITHOUT Datacore (same model, same prompt)
4. **Judge**: Separate Claude instance scores both outputs
5. Results logged as structured JSON

**Scoring** — two methods per criterion:

- **Deterministic checks** (preferred): regex match, pattern match, filesystem assertions
- **LLM-as-judge** (qualitative): comparative ratings, blind A/B order, 3 repetitions for consistency

**Orchestration test fixtures**: Each scenario includes a `fixtures/` directory, setup/teardown scripts, and filesystem assertions.

**Regression tracking**: Baseline from first run, weekly trends, automatic flagging of significant drops.

### Layer B: Replay (Real-World Proof)

**Status**: Exploratory / best-effort. Results are directional evidence, not controlled experiments.

- Captures prompts from real sessions (opt-in `capture` flag)
- Replays against clean Claude Code (no Datacore)
- Focus on first-turn comparisons (most valuable, avoids context dependency)
- Sanitization: regex-based redaction + manual review before public release
- **Known limitation**: later prompts may reference Datacore-injected context, making multi-turn replay unreliable

### Public Reproducibility

**Three tiers**:

| Tier | Visibility | Purpose |
|------|-----------|---------|
| Standard | Public | Ships with datacore-bench, tests generic value |
| Personal | Private | User's real sessions. Aggregate stats only published. |
| Community | Public (PR) | Others contribute their own scenarios |

**Requirements**:
- Each test declares: model, Datacore version, seed data, expected behavior
- Results include: model ID, timestamp, token counts, raw judge output
- `python run.py` runs the full suite
- Judge prompts in the repo — no hidden evaluation criteria
- `seed-data/` provides example engrams for reproducibility

**Private session reporting**: Aggregate stats published without content (e.g., "Across 47 private sessions, convention adherence improved 34%").

### Data Schema

Versioned JSON schema for all session logs:

```json
{
  "schema_version": "1.0",
  "session_id": "...",
  "timestamp": "...",
  "datacore_version": "...",
  "model": "...",
  "tool_calls": [...],
  "engrams_injected": [...],
  "feedback": [...],
  "duration_ms": 0
}
```

Schema changes require version bump and migration notes.

### Reports (v1)

| Report | Frequency | Trigger |
|--------|-----------|---------|
| Session | After each session | Post-session hook |
| Harness run | Per suite execution | `python run.py` or nightshift |

**Future**: weekly trends, monthly public summaries, blog-ready digests.

### Changes Required

- **datacore-mcp**: Add logging middleware (TypeScript) that writes structured JSON per session
- **datacore-bench**: New project with harness runner, judge prompts, scenarios, seed data, replay tooling

### New Components

```
2-datacore/2-projects/datacore-bench/
├── run.py                     # Main entry point
├── scenarios/                 # Harness test definitions (YAML)
│   ├── continuation/
│   ├── preference/
│   ├── convention/
│   ├── cold/
│   └── orchestration/
├── seed-data/                 # Reproducible example data
├── judge/                     # Scoring prompts and logic
├── instrumentation/           # Scorecard middleware
├── replay/                    # Capture and replay tooling
├── reports/                   # Generated (gitignored private)
│   └── public/                # Anonymized (tracked)
├── lib/                       # Shared utilities
└── tests/                     # Self-tests
```

### Interface Changes

- New nightshift task type for weekly harness runs
- Session reports appear in `/today` briefing
- `python run.py` CLI for manual runs

## Rationale

**Why three layers instead of one?**
- Scorecard gives visibility with zero effort (always-on)
- Harness gives automated proof (regression detection)
- Replay gives real-world evidence (qualitative validation)
- Each serves a different audience: developer (C), CI (A), marketing (B)

**Why LLM-as-judge + deterministic checks?**
- LLM-only judging is fragile (position bias, verbosity bias). Deterministic checks anchor the ground truth. LLM judgment covers what can't be checked mechanically.

**Why public?**
- Datacore claims to make AI better. Claims need evidence. Reproducible, transparent benchmarks are the only credible way to communicate this.

**Alternatives considered**:
- SWE-bench only: misses Datacore's value (memory, continuity, orchestration on familiar codebases)
- Manual evaluation only: doesn't scale, not reproducible
- Token counting only: measures cost but not value

## Backwards Compatibility

No breaking changes. This is a new project. The only change to existing code is adding optional logging middleware to datacore-mcp, which is additive.

## Security Considerations

- **Privacy**: Session capture logs prompts which may contain sensitive data. Private tier is gitignored. Public release requires sanitization + manual review.
- **Cost**: A/B testing doubles API usage. Estimated ~$20-40/month for weekly runs. Budget should be approved before enabling automated runs.

## Implementation

### Reference Implementation

Location: `2-datacore/2-projects/datacore-bench/`
Design spec: `2-datacore/2-projects/datacore-bench/DESIGN.md`

### Rollout Plan

1. **Phase 1**: Layer C — MCP logging middleware, session reports
2. **Phase 2**: Layer A — Harness runner, initial test scenarios, seed data
3. **Phase 3**: Layer B — Session capture, replay tooling
4. **Phase 4**: Public release — documentation, community contribution guide

## Open Questions

1. **Session isolation**: How to run Claude Code sessions programmatically with/without Datacore? Likely `claude -p` with different MCP configs.
2. **Judge model**: Same model as test subject, or different? Start with same, evaluate cross-model later.
3. **Cost budget**: ~$20-40/month estimated. Acceptable?
4. **Baseline**: Need to run standard suite without Datacore first to establish baselines.

## References

- [Claude Code Skills 2.0 Evals](https://www.pasqualepillitteri.it/en/news/341/claude-code-skills-2-0-evals-benchmarks-guide) — A/B testing framework for skills
- [Marginlab Claude Code Tracker](https://marginlab.ai/trackers/claude-code/) — Daily degradation tracking on SWE-bench subset
- [LaRA Benchmark](https://openreview.net/forum?id=CLF25dahgA) — RAG vs. long-context evaluation
- [SWE-bench Verified](https://epoch.ai/benchmarks/swe-bench-verified) — Real-world software engineering benchmark
- DIP-0019 (Learning Architecture) — Engram model being evaluated
- DIP-0011 (Nightshift Module) — Automation being measured
