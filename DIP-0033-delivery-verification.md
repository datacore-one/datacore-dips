# DIP-0033: Delivery Verification & Smoke Scenarios

| Field | Value |
|-------|-------|
| **DIP** | 0033 |
| **Title** | Delivery Verification & Smoke Scenarios |
| **Author** | Datacore Team |
| **Type** | Standards |
| **Status** | Draft |
| **Created** | 2026-07-29 |
| **Updated** | 2026-07-29 |
| **Tags** | `reliability`, `verification`, `observability`, `smoke-tests`, `ai-boundary` |
| **Affects** | every user-facing deliverable; `.datacore/lib/{space_sync,morning_journal}.py`; chief-of-staff verifiers; nightshift units; module cron/timer jobs |
| **Specs** | DIP-0031 (Agent Error Classification — the per-failure contract this DIP extends to whole pipelines); DIP-0011 (Nightshift); DIP-0017 (Outbox) |
| **Agents** | all producers of user-facing artifacts |

## Summary

Every user-facing deliverable gets a **verifier that checks the outcome at
the point of consumption**, a deadline, and an alert path. A **smoke-scenario
suite** exercises the most likely end-to-end flows daily and after
infrastructure changes, asserting invariants (not exact content, so
non-deterministic AI output is fine). Silent failure is banned as a matter of
standard, not habit. A normative boundary is drawn between the
**deterministic spine** (transport, storage, scheduling, publication,
verification — no LLM in the loop) and the **AI edges** (generation,
classification, prioritization — non-deterministic, always wrapped by a
deterministic gate).

## Motivation

On 2026-07-29 the morning journal failed to reach the principal for **four
stacked reasons**, none of which violated any spec:

1. nightshift wrote the journal at 03:15Z but only published it at
   batch-end 10:43Z — a 7.5h producer-side lag no consumer could see;
2. nothing on the Mac pulled `0-personal` since the 2026-07-27
   three-machine split — the morning ritual silently depended on removed
   infrastructure, and no canary ran after the change;
3. an interrupted sync at 12:42 stranded uncommitted work in a stash and
   died without alerting (actor never identified);
4. the `/today` sync recipe failed on a tree that `org_workspace.load()`
   kept re-dirtying (write-on-load), and the loop swallowed both errors.

The same investigation found **10 orphaned stashes accumulated since
2026-05-14** — real work, including journal content, lost weekly with zero
signal — and a same-day sweep found **four systemd units on nightshift in
`failed` state alerting nobody** (`nightshift-outbox` had failed nightly on a
newline-bearing filename), 11 cron jobs whose only failure surface is a
write-only log, and failure-tolerant `ExecStartPost=-` steps with no checked
surface behind them.

Every component matched its spec. DIPs are design-time documents; all of
this was **runtime drift and silent failure**. The one place instrumented
with an outcome check — the box's 08:00 `cos_verify_morning` — is the one
place failures were caught same-day. This DIP generalizes that pattern. Its
subject is *runtime truth*, not design.

## Specification

### 1. Deliverable registry (normative)

Every user-facing deliverable is registered in
`.datacore/verify/deliverables.yaml` with:

```yaml
- id: morning-journal
  producer: nightshift-today.service (03:15Z) → 0-personal push
  consumption_point: Mac, journal open in editor
  deadline: "08:35 local"
  verifier: .datacore/lib/morning_journal.py   # alerts on miss
  alert: macOS notification + non-zero exit
```

A deliverable without a registered verifier is a spec violation, not a
style choice. Initial registry: morning journal, audio briefing, TG opener,
app briefing artifact, actionable-mail section, nightshift task results,
outbox archive run.

### 2. Verify at the point of consumption (normative)

The verifier asserts the outcome **where the principal experiences it**,
not where the pipeline produces it. "The box sent the audio" is a producer
check; "the journal is on the Mac, fresh, and was opened by 08:35" is a
consumption check. Producer checks remain useful for diagnosis; only
consumption checks count as verification.

### 3. Silent-failure ban (normative)

Extends DIP-0031 §1 ("error strings are never empty") from single failures
to whole flows:

1. Every automated flow ends in **report-or-alert** — success reported to
   its log, failure alerted to a checked surface (Telegram via
   `cos_alert.sh`, macOS notification, or a verifier that will catch it by
   deadline). A write-only log is not a checked surface.
2. Failure-tolerant constructs — `|| true`, `except: pass`,
   `ExecStartPost=-`, swallowed non-zero exits — MUST carry a comment
   naming the checked surface that catches the failure, or be removed.
3. A systemd unit entering `failed` state MUST reach an alert within one
   day. (Mechanism suggestion: a `failed-units` check in the daily smoke
   run — `systemctl --failed` on each machine.)
4. Work preservation over cleanliness: on conflict, commit to a pushed
   rescue branch and alert (`cos_sync.sh`, `space_sync.py`); never stash,
   never reset without a preserved copy.

### 4. Smoke scenarios (normative)

A suite of end-to-end scenario checks, `.datacore/verify/smoke/`, runnable
as one command (`datacore-smoke`), covering the most likely flows:

| Scenario | Invariants asserted |
|----------|---------------------|
| Morning chain | journal exists, has `## Daily Briefing`, generated today, > 5k chars; audio stamp today; ≥1 TG delivery line; artifact `_meta.date` = today |
| Sync round-trip | marker file committed on machine A is visible on machine B within one sync interval; no repo left `behind` > threshold; zero stashes |
| Mail triage | audit.jsonl has an entry < 24h old; errors below threshold; actionable items present in briefing artifact |
| Task round-trip | task created via app API appears in org file with `:ID:`; org files unchanged on disk after a pure read |
| Intent graph | `intents.org` parses in every space; app `/intents` answers 200/401, not 404/5xx |
| Failed units | `systemctl --failed` empty on box + nightshift |
| LLM fallback | monthly, sandboxed: primary backend forced to fail → briefing still ships, `_meta.llm_attempts` records the chain, degraded skeleton renders |

**Non-determinism rule:** smoke checks assert **invariants** — existence,
freshness, bounds, structure, counts — never exact content. AI output may
vary; the envelope may not. This is the same design as
`briefing_quality.validate` (deterministic scoring of non-deterministic
prose), generalized.

**Cadence:** nightly on the machine that owns each scenario, plus
**post-change canary** — after any infrastructure change (machine split,
cron/timer change, sync topology, module deploy), the affected scenarios
run once before the change is considered done. The 2026-07-27 split would
have failed the morning-chain scenario within a day instead of surfacing
two days later through a lost briefing.

### 5. The AI / determinism boundary (normative)

Constraints go at the boundary, not everywhere:

1. **Deterministic spine — no LLM in the loop:** transport, storage,
   scheduling, git operations, publication, routing of knowledge to
   branches (`knowledge_commit.py`), and ALL verification. An LLM must
   never be asked "did it work?" — that is a filesystem/exit-code
   question.
2. **AI edges — non-determinism welcome:** narrative generation,
   classification, prioritization, summarization. Every AI output that
   crosses into system state passes a **deterministic gate**: schema
   check, quality score (`briefing_quality`), or invariant suppression
   (`suppress_answered`). AI proposes; deterministic code disposes.
3. **Instructions-as-code smell:** a procedure written as prose for an LLM
   to re-improvise each run (the old `/today` step-3 shell recipe) is a
   liability once stable — each execution is a fresh reimplementation
   with fresh bugs. When a recipe stops changing, promote it to a script
   and have the LLM *call* it. Prose stays for judgment; scripts own
   mechanics.
4. **Failure handling is spine, not edge:** fallback chains, rescue
   branches, alerts, retries are deterministic code paths. AI may author
   the *content* of a degraded artifact ("why this briefing is thin"
   headline), never the *decision* to degrade.

### 6. Reference implementations (existing as of 2026-07-29)

- `cos_verify_morning.py` — producer-side verifier with alerting (extend,
  don't replace)
- `.datacore/lib/morning_journal.py` — consumption-side verifier (deadline
  08:30, loud on miss)
- `.datacore/lib/space_sync.py` / `cos_sync.sh` — rescue-branch pattern
- `cos_reasoning.generate()` failure chain — `_meta.llm_attempts`,
  degraded skeleton, self-describing fallbacks
- `briefing_quality.validate` / `suppress_answered` — deterministic gates
  on AI output

## Rollout

1. **Phase 1 (mostly done 2026-07-29):** morning-chain deliverables
   registered and verified end-to-end; rescue-branch sync everywhere;
   read-only org loads.
2. **Phase 2:** `datacore-smoke` runner + the seven scenarios above;
   failed-units check wired to `cos_alert`.
3. **Phase 3:** sweep all `|| true` / `except: pass` /
   `ExecStartPost=-` sites against §3.2 (inventory from the 2026-07-29
   audit); fix or annotate.

## Open Questions

1. Where does the smoke runner live — chief-of-staff module (box-centric)
   or a new `verify` module (machine-agnostic)?
2. Should smoke results feed the app (System Pulse card) in addition to
   alerts?
3. LLM-fallback drill cadence — monthly forced-failure test worth the API
   cost, or is the live `llm_attempts` telemetry enough?
