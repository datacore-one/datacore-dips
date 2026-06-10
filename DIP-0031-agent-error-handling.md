# DIP-0031: Agent Error Classification & Recovery

| Field | Value |
|-------|-------|
| **DIP** | 0031 |
| **Title** | Agent Error Classification & Recovery |
| **Author** | Datacore Team |
| **Type** | Standards |
| **Status** | Implemented |
| **Created** | 2026-06-10 |
| **Updated** | 2026-06-10 |
| **Tags** | `errors`, `reliability`, `nightshift`, `observability` |
| **Affects** | `.datacore/modules/nightshift/lib/{execute,run,execution_recorder}.py`, failure-analyzer agent |
| **Specs** | DIP-0011 (Nightshift); CoS orchestration spec lives in the private chief-of-staff module (publication undecided) |
| **Agents** | failure-analyzer, all task executors |

## Summary

Standardizes how agent/task execution failures are captured, classified,
recorded, retried, and surfaced. Written after the 2026-06-10 gap analysis
found failures recorded with **empty error strings** (undiagnosable by
design) and ranked missing error standards 9/10 on the pain scale.

## Motivation

The 2026-04-30 and 2026-05-05 nightshift failures carried `error: ""` —
failure-analyzer had nothing to analyze, retries fired blindly, and the
operator learned nothing. Separately, fail-open code paths (`except: pass`)
hid root causes for weeks. Error handling needs a contract, not habits.

## Specification

### 1. Capture: error strings are NEVER empty (normative)

Every failure MUST carry a non-empty diagnostic string:

1. Subprocess executors build it via `_diagnostic_error()`
   (`modules/nightshift/lib/execute.py`): always includes the exit code;
   prefers stderr; falls back to the stdout tail (the claude CLI often
   reports errors on stdout); last resort `"(no stderr/stdout captured)"`.
2. Exception paths format as `f"{type(exc).__name__}: {exc}"` — never
   bare `str(e)` (some exceptions stringify empty).
3. Defense in depth: `execution_recorder.record_execution()` stamps the
   sentinel `"(empty error string — executor failed to capture
   diagnostics)"` on any failed record that still arrives empty, making
   the capture gap itself measurable.

### 2. Classification taxonomy

`analyze_failure()` (`modules/nightshift/lib/run.py`) classifies by
pattern priority; result: `{category, root_cause, retryable,
recommendation}`.

| Category | Examples | Retryable | Recovery |
|----------|----------|-----------|----------|
| `transient` | rate limit, timeout, connection | yes | retry with backoff |
| `context` | missing file, bad reference | no | fix task context |
| `capability` | permission denied, tool unavailable | no | grant access / change tooling |
| `specification` | missing CONTEXT + ACCEPTANCE_CRITERIA | no | add Rich Task Standard properties |
| `unknown` | anything else | yes (once) | retry once, then escalate to human |

Rules:
- `specification` failures MUST be detected before execution where
  possible (cheapest failure is the one that never runs).
- A task failing with the same category ≥3 consecutive runs is a
  *recurring failure* — CoS triage (orchestration spec, private module repo) escalates it as a
  decision item, and the executor MUST stop retrying it.

### 3. Recording

Every execution outcome (approved / approved_with_notes / needs_review /
failed / skipped) writes a JSON record via `record_execution()` to
`.datacore/state/nightshift/` — schema: `exec_id, task_title, space,
ai_tag, status, score, duration_seconds, tokens_used, completed_at,
error?, failure_analysis?`.

- This directory is **machine-local** (state/ is gitignored — the root
  repo is public and records carry task titles). Server→local record
  sync via a private channel (rsync) is a tracked follow-up; until then
  each machine's analytics see its own runs.
- Non-record artifacts (hygiene, structural, registry reports) go in
  `state/nightshift/maintenance/` — the root is reserved for execution
  records (CoS ingest globs `*.json` there).

### 4. Task-state side effects

- Failed org tasks move to `FAILED` and MUST carry `:NIGHTSHIFT_REASON:`
  with the diagnostic string (DIP-0009 states).
- Successful executions stamp `:NIGHTSHIFT_STATUS:`, `:NIGHTSHIFT_SCORE:`,
  `:NIGHTSHIFT_OUTPUT:` properties.

### 5. Retry semantics

- `retryable: true` → at most ONE in-run retry. Cross-run retries only
  for `transient`.
- Backoff: REQUIRED between retries of `transient` failures
  (exponential; immediate re-fire of a rate-limited call is self-harm).
  *Status: not yet implemented — tracked gap.*
- `retryable: false` → never auto-retried; routed to human review or
  CoS recommendation.

### 6. Surfacing (who learns about it, when)

| Signal | Channel | Latency |
|--------|---------|---------|
| 0 tasks completed with non-empty queue | Telegram alert | same run |
| Git state broken / repeated 0-completions | watchdog (30 min systemd timer) | ≤30 min |
| Failure rates, recurring, stale cadences | CoS System Pulse in /today | next morning |
| Individual failed outputs | Review queue (CoS orchestration spec §5, private) | next morning |
| Fallback/degraded code paths | stderr warnings (journalctl) | same run |

Normative: no `except: pass` without a stderr warning. Fail-open is
permitted for availability; fail-silent is forbidden (CoS orchestration spec §6, private).

## Implementation Status

| Component | Status |
|-----------|--------|
| Non-empty error contract | Implemented 2026-06-10 |
| Classification taxonomy | Implemented (pre-existing, now specified) |
| Synced execution records | Reverted 2026-06-10 (public-repo leak risk) — private channel pending |
| Recurring-failure stop rule | Partial (CoS detects; executor stop not enforced) |
| Exponential backoff | **Not implemented** — tracked gap |
| Review queue surfacing | Implemented 2026-06-10 |

## Backwards Compatibility

Pre-2026-06-10 execution records may carry empty/missing `error` fields;
consumers MUST treat those as `category: unknown`.
