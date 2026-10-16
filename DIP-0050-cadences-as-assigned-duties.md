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

## The problem

A cadence is a repeating duty of a venture role: code review, refactoring,
a blog post, comms, research, reconciliation. The intended model: once a
role is assigned to an agent, that agent executes its cadences
autonomously and reports done; the chief-of-staff agent edits cadences and
coordinates; when an agent is away, others pick up its recurring duties.

What a single-executor implementation does instead:

1. **One executor.** A single heartbeat service on the executor host,
   writing as the executor agent, is the only process that executes any
   cadence. It ticks periodically, senses each venture, and runs a headless
   agent session to "act on the highest-priority cadence". Other agents
   may have heartbeat timers of their own, but they run their frameworks'
   scripts, not the cadence engine.
2. **Assigned-away cadences vanish.** A hard-coded set of "self" agent
   names in the cadence engine drops any role whose `agent:` is not in that
   set, and liveness applies the same filter. A role assigned to any other
   agent is then executed by nobody and counted as overdue by nobody.
   Assignment becomes a way of losing work.
3. **One point of failure.** Everything the single executor runs needs one
   headless session on one host. A rejected config, a daemon running stale
   code after a deploy, an exception in the sense phase, or a spent session
   window each stops every cadence at once.

The pieces the model needs mostly exist: `role.agent` in venture.yaml,
principals in `principals.yaml`, per-actor cadence shards and heartbeat
shards, an executor registry per host, and the ledger's item claim rules.
What is missing is that only one agent ever *acts*.

## The model

- A **cadence** belongs to a **role**. A role is assigned to one principal by
  `role.agent`, or by the venture's explicit `defaults.agent`. There is no
  implicit default. venture.yaml says who does what and when;
  `principals.yaml` says who each principal is and where it runs.
- **The agent's own scheduler triggers; one wrapper runs.** Each agent's own
  scheduler (for example a Hermes cron job, an OpenClaw automation, the
  executor's scheduler, or managed cron on the server for the chief-of-staff
  agent) triggers `cadence_run <slug>`. That is code, and identical on every
  host. `cadence_run`:
  - checks the pause switch and the host budget *at run time*
  - writes a signed `cadence.run.start` event to the actor's ledger log
  - invokes the agent through its own CLI and runtime, with the cadence
    prompt
  - detects usage-limit output (quota, not breakage)
  - validates the artifact against the cadence's evidence schema, then
    commits and pushes it
  - writes `cadence.run.end` with the result, artifact sha256 and commit

  The run record is therefore ours, not the scheduler's, and not the agent's.
  Spikes confirm that each scheduler can run a command (P1.5).
  Mechanics, each a P1.5 work item:
  - the two event kinds are added to the closed ledger vocabulary
    (`ledger/events.py` EVENT_TYPES), with fold and policy handlers
  - events are written with `sign=True`. `EventLog` would silently mint a
    new key when none exists (`ledger/keys.py` `ensure_keypair`), so the
    wrapper checks **before** opening the log that the actor's local key
    exists and matches its proven entry in `principals.yaml verify_keys`, and
    refuses otherwise. Key material is versioned like the wrapper: a
    **scheduled rotation** reaches one principal, soaks one period, then the
    rest. An **emergency revocation** (a leaked key) is the opposite: it is
    fleet-wide and immediate, sets `paused: all`, and each host resumes only
    once its new key is proven in `verify_keys`
  - the agent is invoked through the existing headless executors
    (`executors/hermes.py`, `executors/openclaw.py`, `claude -p`)
  - the git step runs under the host's repo lock,
    `ledger_transport._repo_lock`. The fleet sync must take the same lock
    (reporting `BUSY` and retrying next run); P1.5 depends on that being
    deployed on every host. A push is retried with backoff; a push that
    still fails is `blocked`, never a strike
  - `cadence_run` is **version-pinned per host**. A change to it rolls to one
    principal, soaks one full period, and only then reaches the others, the
    same rule as a new adapter.
- **A reconciler per host** (`cadence_schedule_sync.py`, from the host's
  heartbeat timer) turns venture.yaml into scheduler jobs. It refuses rather
  than guesses (P1.5).
- **The judge is liveness on the server.** It runs hourly as a server job contract,
  **not as a cadence**, so no cadence failure can switch off the judge. It
  reads only the replicated ledger events and shards, re-verifies each
  counted run (the event chain, the artifact at the named commit, the sha256,
  the schema), and gives every assigned cadence exactly one state from the
  enumeration below.
- **Escalation reuses the autofix pipeline, with numbers.** A red cadence
  becomes a repair task for its owner. The owner is told when the repair
  gives up (3 failed attempts, or 24 hours without a green run, whichever
  comes first). A red on one of **the chief-of-staff agent's own** cadences
  goes straight to the owner and bypasses that agent. `tripped` escalates the same way.
  **Channel:** the installation's alert channel (e.g. a messaging bot), plus
  an entry on the owner's decision board. Every escalation is also written as
  a ledger event (`item.create` through autofix). **Delivery is verified**: a
  decision-board entry unacknowledged after 12h becomes a GitHub issue,
  **opened from a different host than the one that sends alerts**. The owner
  gets GitHub's own notification email. That second path shares no host, bot
  token or sender with the first.
  **Two repair tracks**:
  - Only **red** states escalate. Amber states (`blocked`,
    `quota-exhausted`) escalate only once they decay to `late`.
  - *Execution repair* covers `late`. The owner's agent gets a repair task,
    which may rerun `cadence_run`.
  - *Coordination repair* covers `not-held`, `double`, `not-registered`,
    `conflict` and `tripped`. The owner's reconciler, or the owner, gets a
    repair task. It **never reruns** the cadence, because a rerun of a
    `double` is a third run. One exception: after the cause of a `tripped`
    job is fixed (a template or venture.yaml change, or `--rearm`), a single
    probe run is allowed. It cannot double-run, because a second registration
    would show as `double`, which has higher precedence.
- **The chief-of-staff agent** edits cadences and coordinates, and executes
  only its own coordination cadences.
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
| 5 | `double` | grey for 2h after an `assignment_seq` bump, **red otherwise from t=0** | registered by two actors |
| 6 | `not-registered` | grey for 2h after the commit that assigned or added the cadence (an `assignment_seq` bump, or a new cadence in venture.yaml), red otherwise | the owner's host registered, but not this cadence |
| 7 | `quota-exhausted` | amber, **one line per host** | the last run hit the usage limit |
| 8 | `tripped` | red | three runs without valid evidence; the job is disabled |
| 9 | `conflict` | red | the history could not be merged; repair task |
| 10 | `blocked` | amber | the run ended `blocked` (e.g. a fact-check or approval not cleared) |
| 11 | `late` | red | no verified run within the window plus grace |
| 12 | `ok` | green | a verified run within the window |
| — | `orphan` | grey, logged | a completion for a cadence that no longer exists |

Windows: daily 24h, weekly 7d, monthly the calendar month, each with a grace
of a quarter of the window. "Red" means the contract turns red.

Two rules keep a grey or amber state from hiding a missed duty:
- **Amber decays.** `quota-exhausted` and `blocked` become `late` once the
  window plus grace passes without a verified run. A capacity crunch cannot
  pass as "green" for more than one window.
- **Pause keeps a shadow.** While `paused`, liveness still computes the
  state the cadence *would* have and logs it. On unpause it reports what was
  broken and for how long. A pause longer than 7 days reminds the owner
  daily.

## Phases (summary)

P0 decisions → **P1** ownership visible, nothing red that is not real →
**P1.5** write-gating rails and spikes, fixtures only → **P2a** wrapper, planner,
evidence → **P2b** rollout one principal at a time, each promoted by
the owner → **P2c** retire the old executor → **P1.5b** reassignment safety → reassignment → **P3** takeover.

**Calendar estimate:** computed per installation from the number of
principals, the templates each needs, and one soak period per rollout step;
published and re-dated at each promotion.

## Loop-design gate

1. Exit condition machine-judged: a verified `cadence.run.end`, re-checked
   on the server.
2. Judge independent: `cadence_run` (code) writes the run record, and the
   server verifies it. The agent writes neither. Residual: an agent acting
   deliberately against the wrapper could forge events, because it runs as
   the same OS user. The boundary is built against mistakes, which is what
   happens in practice, not against a malicious agent. Accepted and
   stated.
3. A boundary (MUST NOT) beside every done criterion.
4. No mid-run questions: assignment, schema, budget and window are data.
5. No trusted literals: every count is computed at check time, and the
   budget comes from a stated formula.

## Implementation plan

### P0 — decisions (owner)

1. **The chief-of-staff agent's scope.** Its recurring cadences are its own
   coordination duties only (briefing, verify-daily, scoreboard, weekly plan).
   It keeps every other chief-of-staff function: editing cadences and
   assignments, coordination, delegation, merge gatekeeping, approvals,
   escalation, and ad-hoc tasks. It owns no venture role's cadences, because
   it judges and reports on them.
2. **Daily run ceiling per host: an absolute number the owner sets**,
   changed only at promotion sign-offs. It never tracks the load.
   - The load is computed by `cadence_load.py`, never typed. Formula:
     daily + weekly/7 + monthly/30. Continuous classes are excluded, and a
     P1.5 fixture proves they never reach `cadence_run`.
   - **Rule, printed by the script**: ceiling = max(3, ceil(1.4 × load)).
     A host with no cadences yet has its ceiling printed at its rollout step.
     Until then its ceiling is **unset**, and `cadence_run` refuses any run
     on a host with an unset ceiling. No ceiling is typed.
3. **Rollout promotion.** When a step's soak is green, the chief-of-staff
   agent proposes promotion on a decision board, and the owner's yes starts
   the next step.
4. Takeover N and stand-ins: P3 only.

### P1 — ownership visible, nothing red that is not real


1. `owner_of(venture, role)`: `role.agent`, then `defaults.agent`, then an
   **error**. P1 writes `defaults: {agent: <executor>, defaulted: true}` into
   the enabled ventures the executor host holds. `defaulted: true` is the
   marker the later reassignment analysis looks for. Legacy aliases of the
   executor map to it; `human` → `reminder`.
2. `cadences_owned_by(actor)` and `all_assignments()`. Invariant test: the
   union over actors equals `all_assignments()`.
   **Every caller of `own_cadences` moves to `cadences_owned_by(<executor>)`
   before the hard-coded self-agent set is deleted**, with a test that the
   executor's execution set is unchanged, computed before and after on the
   current venture.yaml files.
3. Space declarations on every agent host, one per space held. Discovery
   must refuse a space reached twice (e.g. through a symlink). An
   undeclared space gives `not-held`.
4. Liveness re-keyed by `venture.yaml: name`, implementing the enumeration
   above with its precedence.
5. **Pulled forward from P2a: the one-time view→shard migration.**
   - List every view-only record per space.
   - Move the real ones into a `migration-<YYYY-MM>` shard; keep the list.
   - `reduce_cadence_log` then stops reading the view.
   - Any interim normalisation stays only until this lands, then goes.
  
6. The chief-of-staff agent's duties (briefing, verify-daily, liveness,
   scoreboard, weekly-plan) are listed in venture.yaml under its own role,
   for visibility and budget. **Liveness itself stays a server job contract,
   never a cadence run by `cadence_run`**. `owns.cadences` leaves
   principals.yaml.
7. The readers of `principals.yaml: owns` migrate, then `owns.roles` goes.
   `principals_check` asserts it is absent, and `venture_doctor` fails on an
   owner that is not a principal or does not hold the space.
8. Venture names everywhere, never folder numbers: each venture is keyed
   by `venture.yaml: name`, and a venture whose `space:` is a folder number
   gets the canonical name.
- DONE_WHEN (computed, with fixtures):
  - every enabled cadence has exactly one state
  - fixture: a late cadence reads `late`, a fresh one `ok`, a human one
    `reminder`, an undeclared space `not-held`
  - the executor's execution set is identical before and after
  - no record that exists only in the view is counted
- MUST NOT: change what the executor runs, or turn anything red on day one.

### P1.5 — rails and spikes (fixture schedulers only)

1. **Spikes, each with a written result before its adapter exists:**
   - **S1, a cron-style agent scheduler (e.g. Hermes):** can a cron job run a command? Is there a job
     create, update, remove, disable and list interface? Which lock does
     the ticker honour?
   - **S2, an automation-style agent scheduler (e.g. OpenClaw):** can an automation run a command? Does the
     `Declaration` field round-trip the slug? What are the disable and next-run
     reads? What serialises reconciler writes against OpenClaw's own
     scheduler?
   - **S3, the executor's scheduler and server cron:** confirm the command form and
     the next-fire read.

   If a scheduler **cannot run a command**, that host falls back to managed
   system cron for the trigger only; the agent still runs in its own runtime.
   That fallback needs the owner's OK and is recorded in the spike result.
2. **Slug** `cadence-<venture>-<role>-<cadence>`, `[a-z0-9-]`. Over 64
   characters, it is truncated to 55 plus `-` plus an 8-hex hash. A
   collision after truncation refuses registration.
3. **Input integrity.** The venture.yaml read comes from the **space repo**
   (not the core fork) at a clean tree whose HEAD is an ancestor-or-equal of
   the space's `origin/main`. `venture_doctor --strict` must pass.
   Otherwise refuse, exit 2, write nothing.
4. **Handoff ordering: moved to P1.5b.** No role changes owner before the
   reassignment phase (owner decision 3). The rollout moves execution, not
   ownership, so P1.5 does not need it.
5. **Blast bound**: removing more than max(2, 25%) needs either a committed
   `cadence-migration.yaml` naming exactly the slugs expected to move (the
   planned path, e.g. the executor's handoff), or `--allow-mass-removal` (the
   emergency path, never used by the timer).
6. **Diff-only writes**; **snapshot before write**; **rollback refuses** if
   the current scheduler state or the authorising commit is newer than the
   snapshot, unless `--force-stale`, which is logged.
7. **Adoption** `--adopt <existing>=<slug>`, one time and logged. An
   ordinary sync never touches a job that is not a cadence job.
8. **Pause**: `cadence-control.yaml` (`paused: all | <actor> | <slug>`).
   `cadence_run` checks it at run time, so a wedged reconciler cannot fail
   the pause open. The reconciler also disables matching jobs, and
   `--pause` over ssh works without git. Residual: git is the replication
   path for the file, so during a git outage the ssh pause is the lever
  .
9. **Circuit breaker**: three consecutive runs ending without valid evidence
   trip the job. `quota-exhausted` and `paused` runs are **not strikes**
  . It is re-armed by `--rearm <slug>`, or automatically when the
   cadence's template or venture.yaml entry changes, followed by one probe
   run.
10. **Budget**: `cadence_run` refuses a run over the host's daily ceiling and
    records it (grey, one line). Quota exhaustion is one root-cause line.
11. `--check` exit code is the registration contract. It also compares each
    job's next-fire time, read from the scheduler, with the plan.
- DONE_WHEN, one fixture per rail, and each **run twice**, with containment
  made deterministic by the host lock:
  - a truncated or invalid venture.yaml: refused, zero writes
  - a 30% removal: refused, then allowed with a matching migration file
  - pause: `cadence_run` exits without invoking the agent
  - a stale rollback: refused
  - a reassignment at commit N+1: one owner
  - three evidence-less runs: tripped
  - three quota runs: not tripped
  - a slug collision: refused
  - an event written by `cadence_run` carries a non-empty signature; a
    missing key refuses the run; an unknown event kind is rejected
  - a push failure is `blocked`, not a strike; `blocked` past the window
    plus grace is `late`
  - the **real** `git_fleet_sync.py`, not a stub, reports `BUSY` and leaves
    the repo untouched while another process holds `_repo_lock`. The holder
    in P1.5 is a minimal process taking the same primitive; the same test
    repeats in P2a with `cadence_run` as the holder
  - a cadence newly added to an existing role is grey `not-registered` for
    2h, then red
  - a run on a host with an unset ceiling is refused
  - a missing local key, or one that does not match `verify_keys`, refuses
    the run before any event is written, and no new key is minted
  - a continuous-class cadence cannot be registered or run
  - the shadow state is logged during a pause and reported on unpause
- MUST NOT: write a live scheduler.

### P1.5b — reassignment safety (before the reassignment phase of owner decision 3)

1. **`assignment_seq`**: a monotonic integer per role in venture.yaml.
   `venture_doctor` requires it to increase whenever `agent` changes. Hosts
   order handoffs by it, not by commit position, because `git_fleet_sync`
   lands commits out of decision order.
2. **An ownership edit is pushed synchronously** by whoever makes it,
   bypassing the sweep.
3. **A gap is bounded.** The old host removes its job when it sees the
   higher `assignment_seq`. If the new owner has not registered within 2h,
   the old host re-enables the job and the cadence is `double` rather than
   orphaned. **A `double` past 48h with the old host
   unreachable is resolved automatically**: the owner named by the highest
   `assignment_seq` records a ledger claim, and the old host removes its job
   when it returns and reads the claim. The owner is told, and is not asked
   to act.
4. **Schema versions** on registration records, run events and shards;
   readers refuse an unknown major version (deferred here from P1.5).
- DONE_WHEN (fixtures, each run twice): reassignment by `assignment_seq`
  out of commit order leaves one owner; a new owner that never registers
  gives `double` within 2h, not a silent gap; a `double` is grey at 1h59m and
  red at 2h01m after a bump, and red at once without a bump;
  the 48h unreachable case ends with a claim and one owner.

### P2a — wrapper, planner, evidence

1. **`cadence_run <slug>`** as specified in the model.
   - It commits and pushes the artifact **itself**; it does not wait for
     `git_fleet_sync`.
   - It writes signed `cadence.run.start`/`end` events through the
     existing `EventLog`.
   - A `last-day` schedule kind fires daily on days 28–31, and the wrapper
     runs only when tomorrow is in a new month.
   - A completion for a slug no longer in the plan is recorded as `orphan`
    .
2. **Planner** `cadence_schedule.py plan --actor X`:
   - schedules in UTC
   - slot = hash(slug) mod the host window; collisions are serialised by
     the host lock
   - carries the effort class and daily load
   - its counts are computed, never literal
3. **Prompt builder**. Uses `heartbeat_capture.context` only and inlines the
   template text; no slash-command lookup. `heartbeat_capture.enqueue` (the
   capture-proposal path) is retired with the heartbeat's execution branch
   in P2c.
4. **Templates and evidence schemas, owned per rollout step**
  .
   - Before a principal's P2b step, every cadence it owns gets a template in
     `.datacore/templates/cadences/` declaring
     `evidence: {path, require, derive}`.
   - `derive` names at least one field the server recomputes from the committed
     artifact.
   - Template bodies drop every "log the run" instruction; the wrapper
     records runs.
   - The planner refuses to register a cadence without a template.
   - Residual, stated: whether the content is *true* cannot be judged by a
     machine. The chief-of-staff agent's weekly-plan draft lists three sampled completions
     for the owner to glance at. That is information only, and no action is
     needed.
5. **Heartbeat skip-list**: the heartbeat's sense phase excludes every
   registered cadence.
6. **Per-venture isolation** of sensing errors, with a test.
7. **A publishing template** that posts to several destinations publishes
   the canonical post, then each mirror, in one job.
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
. Soak: one full period of the longest frequency owned, capped at
7 days. Monthly cadences are checked by a forced run *plus* the scheduler's
next-fire time matching the plan. Promotion follows P0 decision 3.

Rollout order is the owner's: typically principals whose scheduler and
host differ from the old executor first, the old executor's own handoff
next (with a committed `cadence-migration.yaml` and the skip-list
preventing double runs), and the chief-of-staff agent last, after P0
decision 1. Existing scheduler jobs that already perform a cadence are
adopted with `--adopt`, or disabled rather than deleted so they can be
restored. Posting cadences soak the posting itself: fact-check and approval
must clear (`blocked` otherwise).

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
  days, so it cannot hide forever. Every counted run has a verified
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

## Lessons that shaped the plan

- Never hard-code a cadence count; counts change from one day to the next.
  Every count is computed at check time.
- A check that accepts a stale or empty artifact reports success that did
  not happen: only this run's artifact counts.
- Prompt-only rules fail; a boundary an agent must not cross is held in code.
- A derived view read back as input corrupts the record it derives from.
- An unrecorded run is invisible to the judge: a run that never reached the
  replicated record is late as far as the fleet knows.
