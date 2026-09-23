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
   applies the same filter. So `5-plur cio: agent: tris` (3 cadences) has
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

- A **cadence** belongs to a **role**. A role is **assigned** to one
  principal by `role.agent` in venture.yaml, or by the venture's explicit
  `defaults.agent`. There is no implicit default. venture.yaml is the only
  record of who does what; `principals.yaml` records who each principal is
  and where it runs, and nothing else.
- **The agent's own scheduler is the executor.** Hermes cron (Tris),
  OpenClaw automations (Data), nightshift's scheduler (Miles) and managed
  cron on the box (Winston). A cadence written or edited in venture.yaml is
  registered by its owner's host as an ordinary scheduled job and run with
  that agent's own runtime and model.
- **A reconciler per host** turns venture.yaml into scheduler jobs:
  `cadence_schedule_sync.py`, run from the host's existing heartbeat timer. It
  refuses rather than guesses (see the safety rails, P1.5).
- **Completion is evidence the agent cannot author alone.** An agent's run
  ends by calling `cadence_done`, which is code. It binds three things: the
  scheduler's own run record, an artifact that satisfies the cadence's
  declared evidence schema, and the artifact's commit. The box re-verifies
  all three from the replicated record. Shards are the only record; the
  derived view is output only.
- **Liveness on the box is the judge**, keyed by venture name. It reports every
  assigned cadence in one state: `ok`, `late`, `not-registered`,
  `registered-not-run`, `tripped`, `not-held`, `pending-rollout` or
  `reminder`. Only the first six can turn a contract red, and only once the
  owner's rollout has started.
- **Escalation reuses what exists.** Liveness runs hourly. A red cadence
  becomes a repair task for its owner through the autofix delegation. Winston
  tells the owner only when that repair gives up.
- The **Chief of Staff** (Winston) edits assignments and cadences through the
  ordinary review path. It executes only `firm:cos`.
- **Takeover (phase 3, later):** after N missed windows *while the owner's
  host is up*, a principal holding the space may claim the cadence through
  the ledger's claim rules, with a cooldown so claims cannot thrash.

## Phases (summary)

P0 decisions → **P1** ownership visible, nothing red that is not real →
**P1.5** safety rails, before any scheduler is written → **P2a** shared
pieces (planner, evidence, heartbeat skip-list) → **P2b** rollout Tris →
Miles → Data → Winston → **P2c** retire the old executor → **P3** takeover.

## Loop-design gate

1. Exit condition machine-judged: `cadence_done` evidence, re-verified on
   the box. It is never "a file exists".
2. Judge independent of executor: the scheduler writes the run record, the
   box verifies it, and the agent writes neither.
3. Boundary beside every done-criterion: each work item below has a MUST NOT.
4. No mid-run questions: assignment, evidence schema and budget are data,
   read before the run.
5. Stale docs: the planner computes every count at check time, and no
   literal is trusted.

## Implementation plan v2 (2026-09-23, after the evaluator audit)

Revised from `DIP-0050-audit-2026-09-23.md`. Each item cites the findings it
answers (C = critic, T = cto, O = coo, R = taleb, P = popper, D = data).

### P0 — decisions (owner)

Closed on 2026-09-23 (details in the evidence appendix):
- every principal gets cadences, rolled out one at a time (Tris → Miles →
  Data → Winston)
- no folder numbers
- reassignment after execution
- the clean slate
- Data posts daily

Still open, with a recommendation for each:
1. **Winston's scope.** Recommended: `firm:cos` only. Winston coordinates and
   judges, so executing venture roles would make him judge his own work
   (O7). Blocks P2b-Winston only.
2. **Daily run ceiling per host** (O1, R5). Recommended to start: 20 agent
   runs a day per host, revised from measured usage after two weeks. Today's
   load is 29 enabled cadences, about 14 runs a day, plus Data's 2 daily jobs.
   Blocks P1.5.
3. **Takeover N and stand-ins.** Only for P3.

### P1 — ownership is total and visible, and nothing turns red that is not real

1. `owner_of(venture, role)`: `role.agent`, then `defaults.agent`, then
   **an error**. No hardcoded `miles` (D2). P1 writes `defaults: {agent:
   miles}` explicitly into the enabled ventures Miles's host holds, so
   today's behaviour becomes visible data. Aliases `nightshift`/`heartbeat`
   → `miles`. `human` → the `reminder` state (D4, C6).
2. Two functions, not one signature (C5): `cadences_owned_by(actor)` for
   reconcilers, and `all_assignments()` for liveness. `SELF_AGENTS` is deleted.
3. **Space declarations on every host** (C3; the draft's "any directory
   name" was wrong, because `discover_ventures` raises on undeclared numbered
   directories). hermes and plur-claw get a catalog declaration for each
   space they hold. A cadence whose owner's host does not declare its space
   is `not-held`, naming the host.
4. **Liveness re-keyed by `venture.yaml: name`** (C4), with all eight states.
   A principal's cadences are `pending-rollout` (grey, never red) until its
   host writes a registration record (O2). So Tris's cadences show, owned by
   tris, without a manufactured red before P2b-Tris.
5. **Winston's duties move into venture.yaml** under `firm:cos`: briefing,
   verify-daily, liveness, scoreboard, weekly-plan (D9). `owns.cadences`
   leaves principals.yaml.
6. **The readers of `principals.yaml: owns` migrate** (C8, P6). The ten files
   that read it are listed; each moves to `owner_of`/`all_assignments` or is
   shown not to read roles. Only then does `owns.roles` go, and
   `principals_check` asserts it is absent. The agreement test is replaced
   by `venture_doctor` failing on an owner that is not a principal, or whose
   host does not hold the space.
7. The DIP, venture.yaml `space:` fields and members.yaml use venture names
   (D3). 3-fds is `space: 3-fds` today.
- DONE_WHEN, computed at check time and never a literal (P1):
  - for every enabled venture, liveness returns exactly one state per
    declared cadence
  - no state is red while its owner is `pending-rollout`
  - `tris`'s cadences appear with owner `tris` and state `pending-rollout`
- Induced failures, each must fail loudly:
  - a role assigned to a non-principal (venture_doctor)
  - a role whose default is removed (owner_of error)
  - a host declaration deleted in a fixture (`not-held`)
  - a `human` role (`reminder`, not red)
- MUST NOT: change what Miles executes, or turn any contract red on day one.

### P1.5 — safety rails, before any live scheduler is written (R2/R3/R4/R7/R8, T2/T4/T5/T9, D1, O6)

1. **One slug**, shared by all adapters (T4):
   `cadence-<venture>-<role>-<cadence>`, `[a-z0-9-]`, at most 64 characters.
   It fits `cron_install.KEY`. The display name is separate.
2. **Input integrity** (R2). The reconciler reads venture.yaml only from a
   clean tree whose HEAD is reachable from the fetched `origin/main`. An
   unreadable, invalid or dirty input means: refuse, exit 2, write nothing.
3. **Blast bound** (R2). Removing more than max(2, 25%) of an actor's
   registered jobs in one run is refused unless `--allow-mass-removal` is
   passed, and the timer never passes it.
4. **Diff-only writes** (T9), and **a snapshot before every write**:
   `~/.datacore/state/cadence-sync/<utc>.json`. `--rollback <snapshot>`
   restores it (R4).
5. **Writes only through the scheduler's own interface** (T2): hermes CLI,
   `openclaw cron`, `nightshift scheduler`, `cron_install.install/reconcile`
   (T7). Never a direct edit of `jobs.json`. Spike S1, before P2b-Tris:
   does Hermes expose job create/update/remove? If not, the adapter holds
   Hermes's own lock, named in S1's result. No lock named means no adapter.
6. **Adoption is separate and logged** (O6): `--adopt <existing>=<slug>`,
   one time. It covers `geo-research-tris` and the seven
   `plur-daily-x-memory-*` automations. An ordinary sync never touches a
   job that is not a cadence job.
7. **Reassignment handoff** (D1, T5). Each registration record carries the
   venture.yaml commit that authorised it:
   - a host that sees a newer commit moving a cadence away removes its job
     first
   - the new owner registers only at or after that commit
   - liveness reports a cadence registered by two actors as `double`
     (red), or by none as `not-registered`
   - a short gap is accepted over a double run; this is documented
8. **Fleet pause, enforced in code** (R3): `cadence-control.yaml`
   (`paused: [all | <actor> | <slug>]`). The reconciler *disables* the
   matching jobs through the scheduler's own disable call. It never deletes
   them. `--pause` applies at once over ssh; otherwise the next reconciler run
   applies it.
9. **Circuit breaker** (R7): three consecutive scheduler runs without valid
   evidence disable the job and mark it `tripped`.
10. **Budget** (O1, R5):
    - `plan` output carries each cadence's effort class, from its template,
      and the host's daily sum
    - registration beyond the P0 ceiling is refused
    - a run whose output matches the usage-limit text
      (`venture_heartbeat.usage_limit_text`) marks the host
      `quota-exhausted`
    - liveness reports that as **one** root-cause line, not N late cadences
11. `--check` exit code is what the registration contract grades (R8, O5).
    Drift is red. Nobody reviews anything by hand.
- DONE_WHEN (fixtures, one per rail): a truncated venture.yaml leads to
  refusal and zero writes; a 30% removal is refused; a pause disables every
  job in the fake scheduler in one run; a rollback restores the snapshot
  byte for byte; a reassignment at commit N+1 leaves exactly one owner after
  both hosts sync; three runs without evidence trip; a usage-limit output
  gives one root-cause line.
- MUST NOT: write any live scheduler. P1.5 ships with fake schedulers only.

### P2a — shared pieces

1. **Planner** `cadence_schedule.py plan --actor X`:
   - the job set, with slug, cron, prompt and authorising commit
   - all schedules in **UTC**; monthly days limited to 1–28 (D5)
   - slot = hash(slug) mod the host window; collisions are allowed and are
     serialised by the host's run lock. That is a stated choice, not an
     accident (T3)
   - test: deterministic, and inside the window
2. **Prompt builder**. It reuses `heartbeat_capture.context` (T8), is
   narrowed to one cadence, and inlines the command or template text. It
   never uses a slash-command lookup (the weekly-plan diagnosis in the
   appendix).
3. **Evidence schema per cadence** (C1, P2, T1). Each template in
   `templates/cadences/<name>.md` declares
   `evidence: {path: <pattern with {date}>, require: [fields]}`. The planner
   refuses to register a cadence whose template declares none. `cadence_done
   --slug S` (code, the only writer of cadence history):
   - reads the scheduler's run record through the adapter (run id, start)
   - validates the artifact against the schema
   - requires the artifact to be committed with a commit time inside the
     window. Commit time, not mtime (P3)
   - writes the actor's shard: slug, run id, artifact path, sha256, commit
   - on `CadenceHistoryError` it retries once, then records `conflict`. That
     is a liveness state and becomes a repair task; it never propagates
     silently (T6)
   - the nightshift-task evidence path stays as a second kind
4. **Shards are the only input** (R6, V). `reduce_cadence_log` stops reading
   the derived view. First, a one-time reconciliation lists every view-only
   record per space. The real ones (6-meridian operations) move into a
   `migration-2026-09` shard; the agent junk is discarded, and the list is
   kept. The interim normalisation (ventures `266b098`) is then removed.
5. **Heartbeat skip-list** (C2). The heartbeat's sense phase excludes every
   cadence present in *any* registration record, with a test.
6. **Per-venture isolation**. One venture's sensing error never stops
   another's (P4). The heartbeat already reports per venture; the test
   asserts it.
7. **Data's mirror is a step, not a sibling** (D6). The blog cadence
   template publishes the canonical post, then the dev.to mirror, in one job
   and under the 07-29 publish policy. The X post is its own cadence.
- DONE_WHEN:
  - `plan --actor X` equals a count recomputed from venture.yaml by the
    test itself; adding or removing a cadence changes both (P1)
  - an artifact with the wrong field, no content, or an old commit is
    refused, and liveness does not count it (P2)
  - a registered cadence is not run by the heartbeat
  - a forced error in one venture's sensing leaves the others `ok`
- MUST NOT: register anything on a live scheduler.

### P2b — rollout, one principal at a time

Each step's soak lasts one full period of the longest frequency that
principal owns, capped at 7 days. Monthly cadences are verified by a forced
run through the adapter's "run now" and an evidence check, not by waiting 30
days (O4). A step is done when its host's registration contract and
liveness are green for the soak. The next step starts only then.

1. **Tris / hermes.** S1 is closed first (P1.5 item 5), then `--adopt
   geo-research-tris=cadence-plur-cio-geo-research`, then sync.
2. **Miles / nightshift.**
   - Miles's cadences, recomputed at the time, move into nightshift's
     scheduler.
   - The heartbeat skip-list (P2a item 5) prevents double runs.
   - Runs are serialised by the host lock, and the budget ceiling applies.
3. **Data / plur-claw.**
   - Adopt the seven `plur-daily-x-memory-*` automations as one daily
     cadence.
   - Add the daily blog-with-mirror cadence.
   - Soak the posting cadence itself: fact-check and cos-approval must clear
     daily, and liveness sees `blocked` rather than `late` when they don't (O9).
4. **Winston / box.** Only after P0 decision 1. Adopt the existing
   `cron_install` entries for the P1 item 5 duties.

### P2c — retire

Remove the heartbeat's execution branch (sense-and-escalate stays),
`cadence_runner.py`, and the interim view normalisation.

### P3 — takeover (later)

Claim only when the owner's host is **up** and has missed N windows. A host
outage is `not-held`/`quota-exhausted`, never neglect (D8). A claim has a
cooldown of at least one window.

### Whole-upgrade DONE_WHEN

- For 7 consecutive days no cadence is in a red state, excluding
  `reminder`. Every counted completion carries a scheduler run id and an
  artifact commit that the box re-verified.
- **One induced failure per mode that motivated this DIP** (P4, R9). Each is
  run once after P2b, and each must be contained to its venture or host and
  named in one liveness line:
  1. an invalid venture.yaml pushed
  2. a reconciler older than origin (the registration record carries the
     code version)
  3. a sensing error in one venture
  4. a simulated usage-limit exhaustion
  5. a torn pull on one host
  6. `venture-heartbeat.service` stopped for a day: nothing that is
     scheduled misses

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
