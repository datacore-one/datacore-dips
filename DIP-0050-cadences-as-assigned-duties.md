# DIP-0050: Cadences as assigned duties, executed by their owners

| Field | Value |
|-------|-------|
| **DIP** | 0050 |
| **Title** | Cadences as assigned duties, executed by their owners |
| **Author** | Datacore Team |
| **Type** | Architecture |
| **Status** | Draft (owner ratifies) |
| **Created** | 2026-09-22 |
| **Depends on** | DIP-0034/0046 (per-writer ledger and cadence shards), DIP-0044 (principals, authorship), DIP-0035 (job contracts) |
| **Supersedes in part** | the single-executor behaviour of `venture-heartbeat.service` |

## The problem, measured on 2026-09-22

A cadence is a repeating duty of a venture role: code review, refactoring,
a blog post, comms, research, reconciliation. The owner's model: once a
role is assigned to an agent, that agent executes its cadences
autonomously and reports done; the Chief of Staff edits cadences and
coordinates; when an agent is away, others pick up its recurring duties.

What runs is different:

1. **One executor.** `venture-heartbeat.service` on nightshift, writing as
   `miles`, is the only process that executes any cadence. It ticks every
   30 minutes, senses each venture, and runs `claude -p` on nightshift to
   "act on the highest-priority cadence". Tris (hermes) and Data
   (plur-claw) have heartbeat timers of their own, but they run their
   frameworks' scripts, not the cadence engine; Winston executes none.
2. **Assigned-away cadences vanish.** `cadence_engine.SELF_AGENTS = {None,
   "", "nightshift", "miles", "heartbeat"}`; `own_cadences()` drops any
   role whose `agent:` is not in that set, and `cadence_liveness.py`
   applies the same filter. So `plur cio: agent: tris` (3 cadences) has
   been executed by nobody and counted as overdue by nobody since
   2026-09-04 — no shard `cadence-log/tris.yaml` exists. Assignment is a
   way of losing work.
3. **One point of failure, and it failed.** Everything Miles executes
   needs `claude -p` on nightshift. In one week the venture was skipped
   (config rejected), the daemon ran stale code after a deploy, a
   TypeError broke the sense phase, and the plan's session window was
   spent — each stopped every cadence, and the box reported "13 overdue"
   a day later.

The pieces the owner's model needs mostly exist: `role.agent` in
venture.yaml, `principals.yaml: owns.roles`, per-actor cadence shards and
heartbeat shards, an executor registry per host, and the ledger's item
claim rules. What is missing is that nothing but Miles ever *acts*.

## The model

- A **cadence** belongs to a **role**. A role is assigned to one principal by
  `role.agent`, or by the venture's explicit `defaults.agent`. There is no
  implicit default. venture.yaml says who does what and when;
  `principals.yaml` says who each principal is and where it runs.
- **The agent's own scheduler triggers; one wrapper runs.** Hermes cron
  (Tris), OpenClaw automations (Data), nightshift's scheduler (Miles) and
  managed cron on the box (Winston) each trigger `cadence_run <slug>`. That
  is code, and identical on every host. `cadence_run`:
  - checks the pause switch and the host budget *at run time*
  - writes a signed `cadence.run.start` event to the actor's ledger log
  - invokes the agent through its own CLI and runtime, with the cadence
    prompt
  - detects usage-limit output (quota, not breakage)
  - validates the artifact against the cadence's evidence schema, then
    commits and pushes it
  - writes `cadence.run.end` with the result, artifact sha256 and commit

  The run record is therefore ours, not the scheduler's, and not the agent's.
  Spikes S1 and S2 confirm that each scheduler can run a command (P1.5).
- **A reconciler per host** (`cadence_schedule_sync.py`, from the host's
  heartbeat timer) turns venture.yaml into scheduler jobs. It refuses rather
  than guesses (P1.5).
- **The judge is liveness on the box.** It runs hourly as a box job contract,
  **not as a cadence**, so no cadence failure can switch off the judge. It
  reads only the replicated ledger events and shards, re-verifies each
  counted run (the event chain, the artifact at the named commit, the sha256,
  the schema), and gives every assigned cadence exactly one state from the
  enumeration below.
- **Escalation reuses the autofix pipeline, with numbers.** A red cadence
  becomes a repair task for its owner. The owner is told when the repair
  gives up (3 failed attempts, or 24 hours without a green run, whichever
  comes first). A red on one of **Winston's own** cadences goes straight to
  the owner and bypasses Winston.
- **Winston** edits cadences and coordinates, and executes only `firm:cos`.
- **Takeover (phase 3, later):** only while the owner's host is up and has
  missed N windows, with a cooldown.

### Liveness states (the one enumeration)

Precedence runs top to bottom: the first state that applies wins, so each
cadence has exactly one.

| # | State | Colour | Meaning |
|---|-------|--------|---------|
| 1 | `paused` | grey | matched by cadence-control |
| 2 | `reminder` | grey | human-owned; never scheduled |
| 3 | `not-held` | red | the owner's host does not declare the space |
| 4 | `pending-rollout` | grey, **red after 14 days** | the owner's host has no registration record yet |
| 5 | `double` | red | registered by two actors (red after 48h of the old host being unreachable) |
| 6 | `not-registered` | red | the owner's host registered, but not this cadence |
| 7 | `quota-exhausted` | amber, **one line per host** | the last run hit the usage limit |
| 8 | `tripped` | red | three runs without valid evidence; the job is disabled |
| 9 | `conflict` | red | the history could not be merged; repair task |
| 10 | `blocked` | amber | the run ended `blocked` (e.g. a fact-check or approval not cleared) |
| 11 | `late` | red | no verified run within the window plus grace |
| 12 | `ok` | green | a verified run within the window |
| — | `orphan` | grey, logged | a completion for a cadence that no longer exists |

Windows: daily 24h, weekly 7d, monthly the calendar month, each with a grace
of a quarter of the window. "Red" means the contract turns red.

## Phases (summary)

P0 decisions → **P1** ownership visible, nothing red that is not real →
**P1.5** safety rails and spikes, fixtures only → **P2a** wrapper, planner,
evidence → **P2b** rollout Tris → Miles → Data → Winston, each promoted by
the owner → **P2c** retire the old executor → **P3** takeover.

**Calendar estimate:**
- build: P1 2 sessions, P1.5 2, P2a 3
- soaks: Tris 7 days (weekly geo-sov-scan), Miles 7, Data 1 (daily only),
  Winston 7
- worst case about 5 weeks from P0 sign-off, published and re-dated at
  each promotion (O-r2-1)

## Loop-design gate

1. Exit condition machine-judged: a verified `cadence.run.end`, re-checked
   on the box.
2. Judge independent: `cadence_run` (code) writes the run record, and the box
   verifies it. The agent writes neither. Residual: an agent acting
   deliberately against the wrapper could forge events, because it runs as
   the same OS user. The boundary is built against mistakes, which is what
   happened twice on 2026-09-23, not against a malicious agent. Accepted and
   stated.
3. A boundary (MUST NOT) beside every done criterion.
4. No mid-run questions: assignment, schema, budget and window are data.
5. No trusted literals: every count is computed at check time, and the
   budget comes from a stated formula.

## Implementation plan v3 (2026-09-23, after audit round 2)

Answers `DIP-0050-audit-2026-09-23.md` rounds 1 and 2. The tags are the
findings each item answers. Round-2 tags carry `r2`: C-r2 1 is the critic's
round-2 finding 1.

### P0 — decisions (owner)

Closed on 2026-09-23: see the appendix. Still open:
1. **Winston's scope.** Recommended: `firm:cos` only (O7).
2. **Daily run ceiling per host.**
   - Formula: runs/day = Σdaily + Σweekly/7 + Σmonthly/30. Continuous
     classes (`every_15min`, `every_4h`) are bot loops, not agent runs, so
     they are excluded.
   - Today, for the enabled ventures: 13 + 8/7 + 5/30 ≈ 14.3, all Miles's.
     Data adds 2, Tris about 2.1.
   - Recommended ceiling: 1.4 × the host's computed load, rounded up, which
     is 21 for nightshift today. It is recomputed at every registration
     (P-r2-8).
3. **Rollout promotion.** Recommended: when a step's soak is green, Winston
   proposes promotion on a decision board, and the owner's yes starts the
   next step (O-r2-5).
4. Takeover N and stand-ins: P3 only.

### P1 — ownership visible, nothing red that is not real

1. `owner_of(venture, role)`: `role.agent`, then `defaults.agent`, then an
   **error**. P1 writes `defaults: {agent: miles, defaulted: true}` into the
   enabled ventures Miles's host holds. `defaulted: true` is the marker the
   later reassignment analysis looks for (D-r2-4). Aliases
   `nightshift`/`heartbeat` → `miles`; `human` → `reminder`.
2. `cadences_owned_by(actor)` and `all_assignments()`. Invariant test: the
   union over actors equals `all_assignments()` (C-r2-4).
   **`cadence_runner.py:216-222,338` and every other caller of `own_cadences`
   moves to `cadences_owned_by('miles')` before `SELF_AGENTS` is deleted**,
   with a test that Miles's execution set is unchanged, computed before and
   after on today's venture.yaml files (C-r2-1).
3. Space declarations on hermes and plur-claw, one per space held. An
   undeclared space gives `not-held` (C3).
4. Liveness re-keyed by `venture.yaml: name`, implementing the enumeration
   above with its precedence (C4, D-r2-1/2/8, C-r2-2).
5. **Pulled forward from P2a: the one-time view→shard migration.**
   - List every view-only record per space.
   - Move the real ones (meridian's operations cadences) into a
     `migration-2026-09` shard; keep the list.
   - `reduce_cadence_log` then stops reading the view.
   - The interim normalisation (ventures `266b098`) stays only until this
     lands, then goes.
   (O-r2-4, R6)
6. Winston's duties (briefing, verify-daily, liveness, scoreboard,
   weekly-plan) are listed in venture.yaml under `firm:cos`, for visibility
   and budget. **Liveness itself stays a box job contract, never a cadence
   run by `cadence_run`** (O-r2-3, R-r2-4). `owns.cadences` leaves
   principals.yaml.
7. The readers of `principals.yaml: owns` migrate, then `owns.roles` goes.
   `principals_check` asserts it is absent, and `venture_doctor` fails on an
   owner that is not a principal or does not hold the space (C8, P6).
8. Venture names everywhere, including this DIP. `3-fds` gets
   `space: fds-space` or the canonical name (D3, D-r2-7).
- DONE_WHEN (computed, with fixtures):
  - every enabled cadence has exactly one state
  - fixture: a late cadence reads `late`, a fresh one `ok`, a human one
    `reminder`, an undeclared space `not-held` (P-r2-4)
  - Miles's execution set is identical before and after
  - no record that exists only in the view is counted (R-r2 R6)
- MUST NOT: change what Miles executes, or turn anything red on day one.

### P1.5 — rails and spikes (fixture schedulers only)

1. **Spikes, each with a written result before its adapter exists:**
   - **S1, Hermes (Tris):** can a cron job run a command? Is there a job
     create, update, remove, disable and list interface? Which lock does
     the ticker honour?
   - **S2, OpenClaw (Data):** can an automation run a command? Does the
     `Declaration` field round-trip the slug? What are the disable and next-run
     reads? (C-r2-3, C7)
   - **S3, nightshift scheduler and box cron:** confirm the command form and
     the next-fire read.

   If a scheduler **cannot run a command**, that host falls back to managed
   system cron for the trigger only; the agent still runs in its own runtime.
   That fallback needs the owner's OK and is recorded in the spike result.
2. **Slug** `cadence-<venture>-<role>-<cadence>`, `[a-z0-9-]`. Over 64
   characters, it is truncated to 55 plus `-` plus an 8-hex hash. A
   collision after truncation refuses registration (D-r2-6).
3. **Input integrity.** The venture.yaml read comes from the **space repo**
   (not the core fork) at a clean tree whose HEAD is an ancestor-or-equal of
   the space's `origin/main`. `venture_doctor --strict` must pass (R1).
   Otherwise refuse, exit 2, write nothing.
4. **Ordering for handoff.** The authorising commit is compared by
   first-parent position on the **space repo's** `origin/main`, which is
   linear. Agent hosts run forks of the core repo, not of space repos, so
   this ordering is defined on every host (D-r2-3). A host removes its job
   before a newer commit's new owner registers. A `double` for more than
   48 hours with the old host unreachable alerts the owner (R-r2-8).
5. **Blast bound**: removing more than max(2, 25%) needs either a committed
   `cadence-migration.yaml` naming exactly the slugs expected to move (the
   planned path, e.g. Miles's handoff), or `--allow-mass-removal` (the
   emergency path, never used by the timer) (R-r2-7).
6. **Diff-only writes**; **snapshot before write**; **rollback refuses** if
   the current scheduler state or the authorising commit is newer than the
   snapshot, unless `--force-stale`, which is logged (R-r2-3).
7. **Adoption** `--adopt <existing>=<slug>`, one time and logged. An
   ordinary sync never touches a job that is not a cadence job.
8. **Pause**: `cadence-control.yaml` (`paused: all | <actor> | <slug>`).
   `cadence_run` checks it at run time, so a wedged reconciler cannot fail
   the pause open (R-r2-2). The reconciler also disables matching jobs, and
   `--pause` over ssh works without git. Residual: git is the replication
   path for the file, so during a git outage the ssh pause is the lever
   (R-r2-5, accepted).
9. **Circuit breaker**: three consecutive runs ending without valid evidence
   trip the job. `quota-exhausted` and `paused` runs are **not strikes**
   (R-r2-1). It is re-armed by `--rearm <slug>`, or automatically when the
   cadence's template or venture.yaml entry changes, followed by one probe
   run (C-r2-5).
10. **Budget**: `cadence_run` refuses a run over the host's daily ceiling and
    records it (grey, one line). Quota exhaustion is one root-cause line.
11. `--check` exit code is the registration contract. It also compares each
    job's next-fire time, read from the scheduler, with the plan (P-r2-3).
12. **Schema versions** on registration records, run events and shards.
    Readers refuse an unknown major version (T10).
- DONE_WHEN, one fixture per rail, and each **run twice**, with containment
  made deterministic by the host lock (P-r2-6):
  - a truncated or invalid venture.yaml: refused, zero writes
  - a 30% removal: refused, then allowed with a matching migration file
  - pause: `cadence_run` exits without invoking the agent
  - a stale rollback: refused
  - a reassignment at commit N+1: one owner
  - three evidence-less runs: tripped
  - three quota runs: not tripped
  - a slug collision: refused
- MUST NOT: write a live scheduler.

### P2a — wrapper, planner, evidence

1. **`cadence_run <slug>`** as specified in the model.
   - It commits and pushes the artifact **itself**; it does not wait for
     `git_fleet_sync` (T-r2-2).
   - It writes signed `cadence.run.start`/`end` events through the
     existing `EventLog` (T-r2-1).
   - A `last-day` schedule kind fires daily on days 28–31, and the wrapper
     runs only when tomorrow is in a new month (D-r2-5).
   - A completion for a slug no longer in the plan is recorded as `orphan`
     (D7).
2. **Planner** `cadence_schedule.py plan --actor X`:
   - schedules in UTC
   - slot = hash(slug) mod the host window; collisions are serialised by
     the host lock
   - carries the effort class and daily load
   - its counts are computed, never literal
3. **Prompt builder**. Uses `heartbeat_capture.context` only and inlines the
   template text; no slash-command lookup. `heartbeat_capture.enqueue` (the
   capture-proposal path) is retired with the heartbeat's execution branch
   in P2c (T8).
4. **Templates and evidence schemas, owned per rollout step**
   (T-r2-3/5, and the heartbeat's "no installed template" warnings).
   - Before a principal's P2b step, every cadence it owns gets a template in
     `.datacore/templates/cadences/` declaring
     `evidence: {path, require, derive}`.
   - `derive` names at least one field the box recomputes from the committed
     artifact (P-r2-1).
   - Template bodies drop every "log the run" instruction; the wrapper
     records runs.
   - The planner refuses to register a cadence without a template.
   - Residual, stated: whether the content is *true* cannot be judged by a
     machine. Winston's weekly-plan draft lists three sampled completions
     for the owner to glance at. That is information only, and no action is
     needed.
5. **Heartbeat skip-list**: the heartbeat's sense phase excludes every
   registered cadence (C2).
6. **Per-venture isolation** of sensing errors, with a test (P4).
7. **Data's blog template** publishes the canonical post, then the dev.to
   mirror, in one job (D6).
- DONE_WHEN:
  - `plan` counts equal a recount taken from venture.yaml by the test
  - an artifact with the wrong field, no content, an old commit, or a
    `derive` mismatch is refused, and liveness does not count it
  - pause and budget stop `cadence_run` before the agent is invoked
  - the heartbeat never runs a registered cadence
  - a forced error in one venture's sensing leaves the others `ok`
- MUST NOT: register on a live scheduler.

### P2b — rollout, one principal at a time, promoted by the owner

Before a principal's adapter goes live, the P1.5 fixtures are re-run against
the real adapter in dry-run (`--check` against a scratch job, then removed)
(P-r2-5). Soak: one full period of the longest frequency owned, capped at
7 days. Monthly cadences are checked by a forced run *plus* the scheduler's
next-fire time matching the plan (P-r2-3). Promotion follows P0 decision 3.

1. **Tris / hermes.** S1 closed. Templates and schemas for geo-research,
   geo-methodology and geo-sov-scan. `--adopt geo-research-tris`. Sync.
2. **Miles / nightshift.** Templates for every Miles cadence (computed
   list). A committed `cadence-migration.yaml` for the handoff from the
   heartbeat. The skip-list prevents double runs.
3. **Data / plur-claw.** S2 closed. Adopt the seven `plur-daily-x-memory-*`
   automations as one daily X cadence. Add the daily blog-with-mirror. Soak
   the posting itself: fact-check and cos-approval must clear daily
   (`blocked` otherwise).
4. **Winston / box.** After P0 decision 1. Adopt the existing
   `cron_install` entries for the firm:cos duties, except liveness, which
   stays a job contract (P1 item 6).

### P2c — retire

Remove the heartbeat's execution branch (sense-and-escalate stays),
`heartbeat_capture.enqueue`, `cadence_runner.py`, and the interim
normalisation if P1 item 5 did not already remove it.

### P3 — takeover (later)

A claim only while the owner's host is up and has missed N windows. An
outage is `not-held`/`quota-exhausted`, never neglect. A cooldown of at
least one window.

### Whole-upgrade DONE_WHEN

- For 7 consecutive days, no cadence is in a red state. `reminder`,
  `paused` and `orphan` do not count; `pending-rollout` turns red after 14
  days, so it cannot hide forever (P-r2-2). Every counted run has a verified
  `cadence.run.end`.
- One induced failure per motivating mode, each run twice, each contained
  to its venture or host and named in one liveness line:
  1. an invalid venture.yaml pushed
  2. a reconciler or wrapper older than origin (the events carry the code
     version)
  3. a sensing error in one venture
  4. a simulated usage limit (not a strike; one line)
  5. a torn pull on one host
  6. `venture-heartbeat.service` stopped for a day: nothing scheduled misses
  7. a wedged reconciler while pause is set: `cadence_run` still refuses

## Appendix — evidence behind the plan

### Measured 2026-09-23 (morning)

- 62 cadences in enabled ventures before the clean slate, 29 after it. That
  one morning is why v2 never hardcodes a count.
- Tris's Hermes cron already runs `geo-research-tris` (daily, 06:00, `ok`).
  Liveness does not see it.
- OpenClaw runs cron automations with a `Declaration` column.
  cron_install's KEY forbids `:`, hence the dash slug.
- `cadence_completion.record_completion` is nightshift-shaped end to end.
  Hence the new evidence path.

### Owner decisions, 2026-09-23

1. Every principal gets its cadences; rollout one at a time, in the order
   Tris, Miles, Data, Winston.
2. No folder numbers: ventures are named by `venture.yaml: name` (`plur`,
   `firm`, `fds`, `datacore`, `meridian`).
3. Reassignment comes after every principal executes; then existing cadences
   are analysed and reassigned.
4. Clean slate: every datafund and fds cadence was parked (datafund c06b5fb,
   fds 35418d9) with its last recorded run, as comments in its venture.yaml.
5. Data posts daily: the X post, plus a blog post with a dev.to mirror. The
   07-29 publish policy is unchanged.

### Winston's weekly plan (measured 2026-09-23)

`cos_weekly_plan.sh` ran `claude -p "/weekly-plan …"`, got `Unknown command`
with exit 0 on 2026-09-16 and 2026-09-20, and its check accepted the
2026-09-16 fragment. The owner was told a four-day-old plan was ready. Fixed
separately (chief-of-staff `a87520a`): the command text is the prompt, and
only this run's fragment counts. Both rules carry into P2a items 2 and 3.

### Findings, 2026-09-23 afternoon

- **Prompt-only rules fail.** The inbox agent cancelled 654 live tasks while
  reporting that it changed nothing. The ledger refused, and a code guard
  now holds the boundary (chief-of-staff `ac39961`). The pr-review agent
  wrote its report into the "never edit" cadence view, twice.
- **The derived view is read back as input**, and every save copies it into
  tracked shards. The view held records missing from the shards in five
  spaces on nightshift. Interim: prose outcomes are read as the run they
  claim, and differing notes on one run combine (ventures `5d0a96a`,
  `266b098`). The fix is P2a item 4.
- **An unrecorded run is invisible to the judge.** The box reads shards; a
  run that only reached a host's view is late as far as the fleet knows.
