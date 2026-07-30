# DIP-0035: Job Contracts + Unified Verifier

| Field | Value |
|-------|-------|
| **DIP** | 0035 |
| **Title** | Job Contracts + Unified Verifier |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Draft |
| **Created** | 2026-07-30 |
| **Updated** | 2026-07-30 |
| **Tags** | `jobs`, `verification`, `manifest`, `artifacts`, `metric-attest`, `datacore-v2` |
| **Affects** | `.datacore/lib/jobs/` (`manifest.py`, `checks.py`, `manifest.yaml`), `.datacore/lib/job_verify.py` |
| **Specs** | `.datacore/lib/jobs/*.py`, `.datacore/lib/job_verify.py` |
| **Agents** | any process operating a scheduled job on mac/box/nightshift; `job_verify.py` itself as the verification runner |
| **Relates to** | DIP-0034 (Event Ledger Substrate — `metric.attest` sink), `ENG-2026-0729-016` (ledger-mindset direction, item 2: verification contracts), `ENG-2026-0728-001` (silent-degradation failure genre), `ENG-2026-0423-001` (nightshift git-lock silent failure — same failure genre) |

## Summary

Introduces a **declarative job manifest** (one YAML document listing every
scheduled job on the three Datacore machines, each with one or more artifact
contracts) and a **unified verifier** (`job_verify.py`) that loads the
manifest, filters to one machine, checks every declared artifact against the
filesystem, and records each job's verdict as a `metric.attest` event on the
event ledger (DIP-0034). This replaces the pattern of hand-rolling a new,
one-off watchdog script for every job that needs one — each repeating the
same "assert outputs, not exit codes" logic, at different quality, with no
shared contract format and no common durable record. This DIP is Phase 2 of
the v2 rollout DIP-0034 names in its Rollout Plan; it consumes DIP-0034's
event schema and `EventLog`/actor-resolution conventions without changing
them.

## Motivation

### Problem: the silent-degradation failure genre, and retrofitted-watchdog sprawl

Datacore's scheduled jobs (box crontab, nightshift systemd timers, mac
launchd agents) have historically been verified, if at all, by whether their
own script exited zero. That check is necessary but not sufficient — a job
can exit 0 while producing nothing useful, and every concrete failure so far
has been exactly this shape, not a crash:

- **Silent-by-degradation incidents** (`ENG-2026-0728-001`): a cron
  environment was missing Claude credentials on 2 of 3 env files, so a job
  reported "failed:" internally but the pipeline around it still exited 0;
  an f-string bug killed a briefing-generation step for days with no
  externally visible error, so downstream delivery silently sent nothing;
  and an unset `OLLAMA_MODEL` env var went unnoticed for weeks, logged only
  as `<unset>` on every run. `cos_verify_morning.py`'s own docstring
  documents this directly: *"Every morning failure so far has been
  silent-by-degradation, not a crash... `cos_morning.sh` only alerts when a
  script exits non-zero. None of the above did. The gap is that nothing ever
  checked the OUTPUTS."*
- **Git-lock silent failure** (`ENG-2026-0423-001`, the same genre in a
  different subsystem): nightshift's task-claiming mechanism failed silently
  under a broken git state and reported "Complete! 0 tasks, 0 errors" —
  indistinguishable from a genuinely empty queue, undetected for three days,
  because nothing independently checked whether the claim's *output*
  (a recorded attempt) actually existed.
- **Retrofitted-watchdog sprawl**: the fix each time has been a new,
  hand-built script scoped to one subsystem — `cos_verify_morning.py` for
  the morning briefing pipeline (four artifact assertions, one credentials
  check, ~300 lines), `cos_health_digest.sh` for health data, the
  nightshift watchdog for git-state repair and heartbeat, `hl_watchdog.py`
  for trading, `engagement_watchdog.py` for comms engagement. Each is
  correct for its own job and independently maintained, but every new
  scheduled job that deserves the same scrutiny means writing another
  one-off script from scratch, re-solving "read the artifact, check
  freshness, check content, alert on failure" every time with no shared
  format and no common place the verdicts land.

Both failure classes share a root cause with the one DIP-0034 names for
task/ownership state: **there is no durable, declared contract for what "this
job worked" means, checked independently of the job's own report of
success.**

### Use cases

1. **Declare once, verify anywhere** — a job's artifact contract (what file,
   how fresh, what content) lives in one manifest entry instead of bespoke
   logic buried in a subsystem-specific script; the same `job_verify.py`
   runner checks all of them.
2. **Assert outputs, not exit codes** — the exact lesson
   `cos_verify_morning.py` learned the hard way, generalized: `job_verify.py`
   never looks at a job's own exit status; it independently inspects the
   filesystem after the fact, so a job's own (possibly wrong) success report
   cannot mask its output's absence.
3. **A mechanical verification tier feeding the ledger** — `metric.attest`
   events (reserved by DIP-0034 explicitly for this consumer) give
   `job_verify.py`'s per-run verdict a durable, hash-chained, queryable
   record, rather than only a line in a log file that might itself be the
   artifact under test.
4. **A foundation for consolidating the box's watchdogs** — Phase 6 revisits
   whether `cos_verify_morning.sh` and similar scripts can retire once the
   manifest covers their jobs with enough confidence (see Rollout Plan);
   this DIP does not retire anything itself.

## Specification

### Manifest schema (`jobs/manifest.py`)

A manifest is a YAML document `{version: 1, jobs: [...]}`.

**Job fields:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | str | yes | unique across the manifest |
| `machine` | str | yes | one of `mac`, `box`, `nightshift` |
| `schedule` | str | yes | descriptive — cron syntax or free-text (e.g. a launchd interval description); not machine-parsed in Phase 2 |
| `cmd` | str | yes | the command the schedule invokes (documentation only — never executed by the verifier) |
| `artifacts` | list[Artifact] | yes | at least one |
| `required_env` | list[str] | no (default `[]`) | environment variable *names* the job depends on (documentation; not itself checked by `job_verify.py` in Phase 2) |
| `on_fail` | str | no (default `log`) | one of `log`, `telegram` — this job's alert routing |

**Artifact fields:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `path` | str | yes | supports `{today}` and `~` expansion (below) |
| `check` | str | no (default `exists`) | one of `exists`, `nonempty`, `json_has_keys`, `regex` |
| `max_age_hours` | float | no | freshness bound; omitted means no freshness check |
| `arg` | type depends on `check` | conditionally required | `None`/absent for `exists`/`nonempty` (an `arg` there is a validation error); a list of key strings for `json_has_keys`; a regex string for `regex` |

`load_manifest(path) -> list[Job]` is **strict about shape, tolerant about
extras**: an unknown top-level or per-job key is silently ignored (a newer
manifest can add fields an older loader doesn't know about yet); a
wrong-typed or missing *required* field is collected into a single
`ManifestError`. Validation never fails fast — the whole document is
checked, and every problem found is raised together, one per line, so a bad
manifest can be fixed in one pass rather than an error-fix-rerun loop per
field. Validation rules include: `version` must be `1`; `jobs` must be a
list; each job is validated independently with a job-scoped error reference
(`job 'name'` or `job #index` when the name itself is missing/invalid);
duplicate job names are flagged; `machine`/`on_fail`/`check` must be one of
their enumerated values; every job needs at least one artifact; an artifact's
`arg` type must match what its `check` requires (`json_has_keys` needs a list,
`regex` needs a string, `exists`/`nonempty` must carry no `arg` at all).

### Check types, path expansion, and freshness semantics (`jobs/checks.py`)

`run_check(artifact, now=None) -> list[str]` **never raises** — every
filesystem or content surprise (missing file, stale mtime, unreadable file,
binary garbage, invalid JSON, a bad regex pattern) is converted into a
human-readable error string naming the *expanded* path and the reason. An
empty list means the contract holds.

**Path expansion**: `{today}` is substituted with the local calendar date of
`now` (`%Y-%m-%d`) **before** `~` is expanded via `os.path.expanduser`. `now`
defaults to the wall clock (`time.time()`) but is always an explicit
parameter, never a second independent clock read inside the function — this
is the runner side of the job-contract system, not a deterministic fold, so
reading the wall clock here is allowed, but callers (including tests) fully
control behavior by injecting `now`.

**Check pipeline**, per artifact:

1. **File exists** (`os.stat`) — else a single "does not exist" error,
   short-circuiting the rest of the pipeline; nothing else is checkable
   without a file.
2. **Freshness** (only if `max_age_hours` is set) — the file's mtime must be
   `>= now - max_age_hours * 3600`, else a "stale" error naming the actual
   age and the configured limit.
3. **Type check** — `exists` is a no-op beyond step 1; `nonempty` requires
   `st_size > 0`; `json_has_keys` reads the file as UTF-8 (replacing
   undecodable bytes rather than raising), parses it as JSON, requires the
   root to be an object, and reports which of the required keys are missing;
   `regex` reads the file as text and requires `re.search(arg, text)` to
   match.

Steps 2 and 3 both run and **accumulate independently** — a file can be both
stale *and* missing required JSON keys, and both are reported in the same
run — only step 1 (existence) short-circuits, since nothing past it is
checkable.

### Runner behavior (`job_verify.py`)

```
job_verify.py --machine {mac,box,nightshift}
    [--manifest PATH] [--alert {log,telegram}] [--no-emit] [--space DIR]
```

`DATACORE_ROOT` resolution mirrors `ledger/keys.py`: `$DATACORE_ROOT` env var,
else `~/Data`. It sets the default `--manifest` path
(`<DATACORE_ROOT>/.datacore/lib/jobs/manifest.yaml`), the default `--space`
(events are written to `<space>/.datacore/events/`), and the location of the
Telegram alert helper script.

The runner loads the manifest, filters to the jobs declared for `--machine`,
and runs every artifact's contract check for each of those jobs.

**Per-job isolation**: an unexpected exception anywhere in one job's check
pipeline is captured as a failure string naming that job and the exception,
rather than propagating — one broken job's bug can never abort verification
of the rest of the manifest. This mirrors DIP-0034's per-writer file
isolation: a fault in one unit of work must never take down the whole run.

**`metric.attest` events**: unless `--no-emit` is passed, the runner appends
one `metric.attest` event per checked job via `EventLog(space, actor)`
(DIP-0034), with payload `{"metric": "job.verify", "job": <name>, "ok":
<bool>, "failures": [<error strings>]}`. Actor resolution matches
`ledger_cli.py`: `$DATACORE_ACTOR`, else `socket.gethostname()`.

**Alert dispatch semantics**: each job's own manifest-declared `on_fail`
(`log` or `telegram`) is the **source of truth** for which channel that
job's alert goes to. `--alert`, when passed, **overrides `on_fail` for every
job in the run** — e.g. `--alert log` silences Telegram for a run even for
jobs declared `on_fail: telegram`. `--alert` defaults to an explicit `None`
sentinel (not to `"log"`) specifically so the runner can distinguish "the
operator did not pass this flag" from "the operator explicitly chose
`log`" — left unset, each failing job uses its own `on_fail`. Exactly one
alert is dispatched per failing job:

- `log` mode is stderr-only — no external call is made.
- `telegram` mode makes a best-effort attempt via a subprocess call to the
  Telegram alert helper; if the helper script is absent on this machine, or
  the send itself fails, the runner falls back to a stderr note rather than
  silently dropping the alert — an alert attempt is never invisible.

**Stdout/stderr discipline** (matches `ledger_cli.py`): stdout carries
*only* the final summary line — `OK <n> jobs <m> artifacts`, or
`OK 0 jobs 0 artifacts` when no jobs match the requested machine; every
diagnostic (per-job failure blocks, alert notes, clean error messages) goes
to stderr.

**Exit codes**: `0` means every checked job's every artifact passed; `1`
means at least one job failed, *or* the manifest itself could not be loaded
(a `ManifestError` or an `OSError` reading the manifest file is caught and
reported as a clean one-line stderr message — never a raw traceback).

### The "assert outputs, not exit codes" principle

`job_verify.py` never inspects a job's own exit code, and never re-executes
a job's `cmd`. It is a strictly output-side, independent check run after the
fact against the filesystem — generalizing exactly the lesson
`cos_verify_morning.py`'s own docstring states about `cos_morning.sh`: a
script exiting 0 is necessary but not sufficient evidence that its intended
artifact actually exists and is fresh. Because the verifier never consults
the job's own success signal, that signal being wrong (silently swallowed
error, credentials missing, an unset env var producing a degraded-but-still-
"successful" run) cannot mask the absence of the artifact it was supposed to
produce — the exact class of failure named in `ENG-2026-0728-001` and
`ENG-2026-0423-001`.

### Changes Required

- **New**: `.datacore/lib/jobs/manifest.py` (schema + loader), `.datacore/lib/jobs/checks.py`
  (artifact contract checks), `.datacore/lib/jobs/manifest.yaml` (real manifest data for
  all three machines), `.datacore/lib/job_verify.py` (unified runner).
- **New (tests)**: `.datacore/lib/tests/test_jobs_manifest.py`,
  `.datacore/lib/tests/test_jobs_checks.py`, `.datacore/lib/tests/test_job_verify.py`.

### New Components

- `jobs.manifest` — `Job`/`Artifact` dataclasses, `load_manifest`,
  `ManifestError`, and the `MACHINES`/`CHECKS`/`ON_FAILS` enumerations.
- `jobs.checks` — `expand_path`, `run_check`.
- `job_verify.py` — the operator CLI above (`_check_job`, `_dispatch_alert`,
  `_send_telegram`, `main`).

### Interface Changes

- New operator CLI `job_verify.py`: report-only when `--no-emit` is passed
  (as used for the Phase 2 close-out live run below); without it, appends
  `metric.attest` events to the target space's event ledger.
- New declarative file `jobs/manifest.yaml`, one entry per scheduled job
  across all three machines, with its own evidence-sources header
  documenting where each artifact path was traced from.
- No existing watchdog script (`cos_verify_morning.py`,
  `cos_health_digest.sh`, the nightshift watchdog, or any other
  subsystem-specific check) is removed, modified, or superseded by this DIP
  — `job_verify.py` runs alongside them. See Rollout Plan for the retirement
  criteria that would eventually change that.

## Rationale

**Why a declarative manifest instead of another hand-rolled script per
job?** One schema, one validation pass, one runner. `cos_verify_morning.py`
is effectively a case study in what one hand-built watchdog costs to build
and maintain for a single job's four artifacts (~300 lines, its own
credentials check, its own alerting). The manifest generalizes that pattern
to every scheduled job across three machines as declarative data — adding a
new job's contract is a manifest entry, not a new script.

**Why per-job `on_fail` with a whole-run `--alert` override, rather than one
global setting?** Individual jobs carry different criticality — a missed
morning briefing deserves a Telegram alert; a missed research log does not —
but an operator running the full manifest by hand (as in this Phase 2
close-out) needs a way to silence noisy channels for one run without editing
the manifest. This was adjudicated during implementation (Task 2.3): per-job
`on_fail` is the routing source of truth, `--alert` is a whole-run override,
and the `None` sentinel default is what lets the runner tell "not passed"
apart from "explicitly chosen."

**Why never-raise / accumulate instead of short-circuit-on-first-error?**
Mirrors DIP-0034's never-raises registry reads and per-writer isolation: one
broken job's check must never abort verification of every other job in the
manifest, and a file that is simultaneously stale and missing required
content should be reported as both problems in a single run rather than
forcing a fix-rerun cycle per symptom.

**Why `metric.attest` into the ledger rather than only a log line?**
DIP-0034 reserves this event type explicitly for this consumer (its Rollout
Plan names Phase 2/DIP-0035 directly). A durable, hash-chained, queryable
record of "did job X actually produce its artifact, and when" survives
independently of whichever log file might itself be the artifact under test,
and it gives the "mechanical artifact checks" verification tier named in
`ENG-2026-0729-016` (item 2) its first real consumer and its first real
data.

### Alternatives considered

- **Keep hand-rolling a watchdog per job** — rejected; exactly the sprawl
  this DIP exists to end, and each new one-off script re-implements
  "assert outputs, not exit codes" at variable quality.
- **Verify by checking the job's own exit code** — rejected; this is
  precisely the previously-inadequate mechanism (`cos_morning.sh` alerting
  only on nonzero exit) that produced the incidents in `ENG-2026-0728-001`
  and `ENG-2026-0423-001`.
- **One global `on_fail` setting for the whole manifest instead of
  per-job + override** — rejected per the Task 2.3 adjudication; it would
  lose the ability to route routine jobs to log-only while keeping
  high-stakes jobs on Telegram by default, without also losing the
  operator's ability to silence a channel for a single manual run.

## Backwards Compatibility

Additive and non-breaking. No existing watchdog script, cron entry, systemd
timer, or launchd agent is modified, removed, or migrated by this DIP.
`jobs/manifest.yaml` documents jobs that already run on their existing
schedules; `job_verify.py` is a separate, independently-run check against
its own manifest file — it does not replace, wrap, or invoke any job's own
`cmd`. A missing or unreadable manifest fails `job_verify.py` cleanly
(nonzero exit, a clean stderr message) rather than crashing; a machine with
no jobs declared for it returns `OK 0 jobs 0 artifacts` rather than erroring.

## Security Considerations

- **Public-repo constraint.** This DIP's content and `jobs/manifest.yaml`
  contain no secrets: `required_env` names environment variable *names*
  only, never values, and every path uses `~`, `{today}`, or
  `$DATACORE_ROOT` rather than any machine-specific absolute path.
- **Telegram alert fallback.** The Telegram send helper is invoked as a
  best-effort subprocess call; a missing helper script or a failing send
  degrades to a stderr note, never a crash and never a silently dropped
  alert — the same fail-safe posture DIP-0034 uses for its registry reads.
- **`metric.attest` payload contents.** Failure strings in the emitted event
  payload include the expanded filesystem paths that failed their check —
  these are local paths on whichever machine `job_verify.py` ran on, written
  to that machine's own ledger event file; this DIP does not transmit any
  path to a different machine or a shared public artifact.
- **Not an enforcement or remediation system.** `job_verify.py` detects and
  reports; it does not restart, retry, or otherwise remediate a failing job.
  Remediation policy (auto-retry, escalation on repeated failure) is
  explicitly out of scope for Phase 2 (see Open Questions).

## Implementation

### Reference Implementation

`.datacore/lib/jobs/` (`manifest.py`, `checks.py`, `manifest.yaml`) and
`.datacore/lib/job_verify.py`, with tests under `.datacore/lib/tests/`
(`test_jobs_manifest.py`, `test_jobs_checks.py`, `test_job_verify.py`) — 70
job-contract-specific tests, 363 total in the full suite at HEAD of
`feat/datacore-v2`, zero pre-existing or new failures.

`manifest.yaml` declares all 18 real scheduled jobs across the three
machines (10 on box, 6 on nightshift, 2 on mac), each with at least one
evidence-derived artifact contract traced to a script, systemd unit,
launchd plist, or source file read directly during authoring. 4 artifacts
carry `# TODO(verify-on-<machine>)` markers where no direct code-traced
writer for a persisted artifact was found; those use the job's own
script/state-directory as an honest fallback pending Phase 6 on-machine
confirmation, rather than inventing a path.

**Live verification run** (2026-07-30, `--machine mac --alert log
--no-emit`):

```
OK 2 jobs 2 artifacts
```

exit 0 — both mac-declared jobs (`mac-agent-stream-rsync`, `mac-lens-sync`)
passed their exists-only contracts.

Commit reference: `feat(v2): populate job manifest for all machines`
(branch `feat/datacore-v2`).

### Rollout Plan

**Phase 2 (this DIP — shipped): the manifest + verifier.** Schema and
loader, artifact checks, unified runner, real manifest data for all three
machines, `metric.attest` emission, Telegram alert plugin with a log
fallback. No cron entry, systemd unit, or launchd agent is changed;
`job_verify.py` runs report-only alongside every existing watchdog.

**Phase 6 (follow-on, interface-locked at this writing).** (1) Resolve the
4 `TODO(verify-on-*)` markers by confirming actual writers and freshness
thresholds directly on box, mac, and nightshift. (2) Switch the box's own
verification step to invoke `job_verify.py` (directly, or wired into
`cos_sync`'s own health surface) once (1) is resolved. (3) Retire
`cos_verify_morning.sh` only after 7 consecutive green days of
`job_verify.py` running in its place for the jobs it covers — a deliberate
overlap period rather than a flag-day cutover, so a manifest gap does not
silently reintroduce the exact failure genre this DIP exists to close.

## Open Questions

1. **`TODO(verify-on-*)` resolution** — deferred to Phase 6 by design (see
   `manifest.yaml`'s own evidence-sources header); this DIP establishes the
   honesty convention (mark uncertainty explicitly rather than invent a
   path) but does not itself resolve the 4 currently-open markers.
2. **Remediation policy** — `job_verify.py` currently only detects and
   alerts; whether a Phase 6+ follow-on should add auto-retry or
   auto-escalation on repeated failure is unresolved.
3. **Cross-machine rollup** — each `job_verify.py` invocation covers exactly
   one `--machine`; whether a later phase wants a single view folding all
   three machines' `metric.attest` events (via `ledger.index`, DIP-0034) is
   deferred until Phase 6 produces enough real multi-day data to design
   against.
4. **Schedule-string tooling** — the mac jobs' `schedule` field is currently
   descriptive prose (a launchd interval description) rather than cron
   syntax; if a future tool wants to compute "is this job overdue" from
   `schedule` directly, it will need either a stricter per-platform schema
   or an explicit schedule-kind field (cron / launchd / systemd timer).

## References

- `ENG-2026-0728-001` — the silent-degradation failure genre this DIP
  generalizes a fix for (credentials missing on 2 of 3 env files, an
  f-string bug silently killing briefings for days, an unset env var
  logged as `<unset>` for weeks) — the same genre `cos_verify_morning.py`'s
  own docstring names as its motivation.
- `ENG-2026-0423-001` — nightshift git-lock silent failure ("Complete! 0
  tasks, 0 errors" undetected for three days); the same failure genre in a
  different subsystem, and one of the two incidents DIP-0034 cites as
  motivating durable, independently-checkable records of what actually
  happened.
- `ENG-2026-0729-016` — ledger-mindset direction; item 2 ("verification
  contracts declared at task creation") is this DIP's mandate.
- DIP-0034 — Event Ledger Substrate; reserves `metric.attest` explicitly for
  this DIP's consumer (its Rollout Plan names Phase 2/DIP-0035 directly) and
  defines the `EventLog`/actor-resolution conventions `job_verify.py` reuses
  without modification.
- `cos_verify_morning.py` — the retrofitted, hand-built watchdog whose own
  docstring documents the concrete silent-degradation incidents this DIP's
  manifest-and-runner approach generalizes a fix for.
