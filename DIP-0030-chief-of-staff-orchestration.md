# DIP-0030: Chief of Staff Orchestration & Agent Stream

| Field | Value |
|-------|-------|
| **DIP** | 0030 |
| **Title** | Chief of Staff Orchestration & Agent Stream |
| **Author** | Datacore Team |
| **Type** | Standards |
| **Status** | Implemented |
| **Created** | 2026-06-10 |
| **Updated** | 2026-06-10 |
| **Tags** | `chief-of-staff`, `agent-stream`, `orchestration`, `observability` |
| **Affects** | `.datacore/modules/chief-of-staff/`, `.datacore/lib/agent_emit.py`, `~/.datacore/cos/` |
| **Specs** | DIP-0011 (Nightshift), DIP-0016 (Agent Registry) |
| **Agents** | chief-of-staff (Mr Data), all agent-stream emitters |

## Summary

Specifies the Chief of Staff (CoS, "Mr Data") production contract: entry
points, run lifecycle, artifact layout, the agent-stream event schema that
all agents emit into, and the health/staleness rules that make silent
outages impossible. This DIP documents the as-built system; it was written
after a 41-day CoS outage (2026-05-01 → 2026-06-10) went unnoticed because
the component had **no production caller** and its absence was silent.

## Motivation

The 2026-06-10 gap analysis ranked "no CoS orchestration spec" as the
single most painful unspecified area (9/10). Concretely: `run_daily()`
existed and passed tests but nothing invoked it; five agents emitted
stream events with no documented schema; consumers had no contract for
detecting staleness. This DIP fixes the class of failure, not just the
instance.

## Specification

### 1. Entry points (the production contract)

The ONLY supported production entry point is the CLI:

```bash
cd .datacore/modules/chief-of-staff && python3 -m lib.cli run [--dry-run] [--force]
cd .datacore/modules/chief-of-staff && python3 -m lib.cli status
```

- `cos run` executes `lib.service.run_daily()`. **Idempotent per calendar
  day** — a same-day rerun with an identical report id skips the write
  (`skip_reason: idempotent-same-report-id`). `--force` bypasses.
- On crash, `cos run` writes an error state file so `cos status` reports
  exit 2 (last-run-failed) instead of aging into stale. Failures must be
  *distinguishable from* staleness.
- `cos status` exit codes: `0` healthy · `1` disabled (kill-switch) ·
  `2` last-run-failed · `3` stale (>25h or never ran) · `4` config error.

Invokers (both call `cos run` daily; idempotency makes double-invocation safe):

1. `/today` Python orchestrator — `gather_cos()` in
   `modules/nightshift/lib/today_orchestrator.py` (server systemd path).
2. `/today` skill hook — `modules/chief-of-staff/today_hook.md` Step -1
   (local launchd `claude -p /today` path).

Adding a third invoker requires no coordination — only `cos run`.

### 2. Run lifecycle

`run_daily()`: load policy → ingest nightshift exec state + venture
cadences → triage (rates, recurring failures, clusters, stale cadences) →
recommendations (PLUR engram recall with template fallback) → compose +
atomically write artifacts → emit stream events. It is the only function
in the module with side effects.

### 3. Artifact layout (consumer contract)

```
~/.datacore/cos/
  policies.yaml                      # kill-switch, thresholds (fail-open, warn loud)
  state/runs/{date}.json             # status: ok|skipped|error (+error string)
  briefings/{date}/
    cadence-triage.md / .jsonl / .summary.json
    morning-brief.md                 # H1 = intro line; bullets = observations;
                                     # sign-off "Truly yours, Data" — render verbatim
    review-queue.json                # overnight results batch (see §5)
  agent-stream/events-YYYY-MM-DD.jsonl
  approvals/                         # proposed approval requests
```

### 4. Agent-stream event schema

Canonical emitter: `.datacore/lib/agent_emit.py` (`emit`, `emit_message`,
`emit_task`). Event shape (one JSON object per JSONL line):

```json
{
  "id": "task-cos-cadence-triage-2026-06-10-started",
  "ts": "2026-06-10T08:18:43+00:00",
  "type": "agent.task.started",
  "agent": "data",
  "summary": "CoS daily cadence triage started (2026-06-10)",
  "severity": "info",
  "details": {}
}
```

- `type`: `agent.task.{started|completed|skipped|escalated}`,
  `agent.message`, `agent.intent`, `agent.state`.
- `severity`: `info | success | warning | error`.
- `id` SHOULD be deterministic per logical task+day so re-runs collapse
  in consumers.
- Transport: HTTP relay (`AGENT_STREAM_RELAY_URL`) with local-file
  fallback; fallback warns to stderr once per process. Consumers MUST
  tolerate unknown fields and skip malformed lines (warn, don't crash).
- Known emitters: telegram bot, miles bot, chief-of-staff service,
  cadence runner, nightshift run. Consumer: datacore-app daemon
  (`JsonlAppendWatcher` → `GET /cos/agent-stream`).

### 5. Review queue

`gather_review_queue()` (today orchestrator) merges 48h of nightshift
execution records with output files across `[space]/0-inbox/nightshift-*`
into `briefings/{date}/review-queue.json`. Items carry
`decision: null | approve | revise | reject` — any surface (briefing
conversation, app) records decisions in the same file.

### 6. Fail-loud rules (normative)

1. A configured component that does not run MUST surface as a `⚠️` line in
   the /today System Pulse — silence is reserved for the explicit
   kill-switch and legitimately empty data.
2. Fallbacks (policy defaults, no-op emit stubs, relay → local file) MUST
   warn on stderr; fail-open is allowed, fail-silent is not.
3. `cos status != 0` for >24h is an incident, not a curiosity.

## Implementation Status

| Component | Status |
|-----------|--------|
| `cos run` / `cos status` CLI | Implemented 2026-06-10 |
| /today wiring (both paths) | Implemented 2026-06-10 |
| Agent-stream schema + emitters | Implemented (5 emitters) |
| Review queue | Implemented 2026-06-10 |
| App stream consumer | Implemented (daemon); panel in progress |
| Schema validation at consumer | Future work |
| CoS execution layer (Phase 2, beyond advisory) | Future work |

## Backwards Compatibility

Documents existing behavior; no breaking changes. Pre-2026-06-10 stream
events lack `agent.task.escalated`; consumers must not assume it.
