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

- A **cadence** belongs to a **role**; a role is **assigned** to one
  principal (`role.agent`; unassigned roles default to the venture's
  space host's principal, today `miles`). `principals.yaml: owns.roles` is
  the same fact from the other side and must agree — a test enforces it.
- **The agent's own scheduler is the executor.** Every agent host already
  runs one: Hermes has a cron subsystem (`~/.hermes/cron/jobs.json`: jobs
  with `name`, `schedule {kind: cron, expr}`, `prompt`, `skills`, `deliver`,
  `last_status`, `next_run_at`), OpenClaw has `openclaw cron` (automations
  via its gateway), nightshift has `schedules.yaml` behind `nightshift
  scheduler install`, the box has managed cron (`cron_install.py`). A
  cadence, once written or edited in venture.yaml, is **picked up by its
  owner and registered there** as an ordinary scheduled job; the agent
  runs it the way it runs every other scheduled job, with its own runtime
  and channel. The cadence engine stops executing and starts *feeding*.
- **Reconciler, not heartbeat.** `cadence_schedule_sync.py --actor
  <principal> --scheduler <hermes|openclaw|nightshift|cron>` runs from
  each host's existing heartbeat timer: it reads the venture.yaml files
  of the spaces the host holds, takes the cadences of roles assigned to
  its principal, derives a schedule per cadence from its frequency (daily,
  weekly, monthly, quarterly → a cron expression, staggered so one host's
  jobs do not fire together; continuous bot loops are never registered),
  and creates / updates / removes jobs under a stable name
  (`cadence:<venture>:<role>:<name>`) so the scheduler mirrors venture.yaml
  exactly. Idempotent; CoS edits venture.yaml → git → host pulls →
  reconciler updates the jobs. A registration record per host says which
  cadences are scheduled where, so "assigned but never scheduled" is
  visible.
- **The job's prompt** is built by the engine (the same role, template,
  boundary and budget the heartbeat prompt carries today) and ends with
  the one instruction that makes completion count: record it with
  `cadence_completion` (evidence required, as now) into **this actor's
  shard**. Completions replicate by git; nothing about the storage changes.
- **Liveness counts every assigned cadence**, by owner and by
  registration: not registered, registered but not run, run and late. An
  overdue cadence names who owns it and on which scheduler.
- The **Chief of Staff** (Winston) edits assignments and cadences through
  the ordinary review path; it executes only the roles it owns
  (`8-firm:cos`), through the same reconciler on the box.
- **Takeover (later):** when an owner has missed N windows, another
  principal that holds the space may claim the cadence through the
  ledger's claim rules (one owner at a time, the claim recorded before the
  work), and the original owner's return is a release, not a conflict.

## Phases

1. **Ownership is total and visible.** Every role names an agent or
   inherits one; `SELF_AGENTS` goes; `own_cadences(overdue, roles, actor)`
   keeps the cadences of roles assigned to *this* actor; `cadence_liveness.py`
   reports every overdue cadence with its owner and fails on any of them; a
   test asserts venture.yaml and principals.yaml agree. Effect: Tris's three
   cadences become visible as overdue, owned by tris, on day one.
2. **Cadences become scheduled jobs.** The reconciler, one scheduler
   adapter per host (hermes, openclaw, nightshift, cron), the prompt
   builder, and the completion CLI that writes the actor's shard. Rolled
   out one principal at a time: Tris on hermes first (5-plur cio, 3
   cadences), then Data, then Miles (whose cadences move from the
   heartbeat's tick into nightshift's scheduler; the heartbeat keeps only
   sense-and-escalate), then Winston. Precondition per host: it holds the
   venture's space under its canonical name — hermes and plur-claw hold
   partial trees under other names (`2-plur`, `1-datacore-space`) and are
   unified first. One contract per host on the registration record and one
   on completions.
3. **Takeover.** As above, behind an owner decision on N and on which
   principals may stand in for which roles.

## Loop-design gate

- Exit condition machine-judged: a completion recorded with the evidence
  `cadence_completion` already requires; liveness counts it.
- Judge independent of executor: liveness on the box, per-actor shards.
- Boundary: an actor may execute only roles assigned to it (phase 1/2) or
  claimed through the ledger (phase 3); budget authority stays per role.
- No mid-run questions: assignment is data in venture.yaml.
- Docs: this DIP, `cadence_schedule_sync.py` (new), `venture_heartbeat.py`, `cadence_liveness.py`.

## Decisions the owner makes before phase 1 ships

1. The role → principal map for the live ventures (2-datacore: ceo, cto,
   cmo; 5-plur: ceo, cto, cmo→data?, cio→tris, bizdev; 8-firm: cos,
   coo, cio, comms). Unassigned roles default to miles today.
2. Whether Winston executes any venture role beyond `8-firm:cos`.
3. For phase 2: which hosts may hold which spaces (Tris on hermes for
   5-plur; Data on plur-claw for 8-firm and 2-datacore?), the canonical
   layout on those hosts, and the daily firing window per host (the
   stagger the reconciler uses).
4. For phase 3: N missed windows before takeover, and who may stand in.

## Implementation plan (2026-09-23)

### What the live state adds to the draft

Measured 2026-09-23 across the eight venture.yaml files:

- **62 cadences in enabled ventures** (19 daily, 27 weekly, 13 monthly, 3
  sub-daily bot loops that are never registered). 38 have no
  `agent:` and default to Miles, 21 name `nightshift` (6-meridian), 3 name
  `tris`. That is about 23
  agent runs a day, all of them going through one `claude -p` tick that picks
  one cadence per tick.
- **Assigned roles with nothing to do, and duties with no role.**
  principals.yaml gives 8-firm cos/coo/cio/comms to Winston, Miles, Tris and
  Data, but 8-firm declares no cadences. 5-plur cmo→data declares none
  either. 6-meridian quant_researcher (`agent: nightshift`) appears in no
  principal's `owns.roles`. The two files already disagree. They have to
  become one fact, not two facts kept in step.
- **The model already exists by hand, uncounted.** Tris's Hermes cron runs
  `geo-research-tris` daily at 06:00 and reports `ok`. That is the 5-plur
  cio `geo-research` cadence, running in the owner's own scheduler, and
  liveness does not see it. OpenClaw on plur-claw already runs cron
  automations with a `Declaration` column (`heartbeat:main`). That column is
  a natural ownership key for reconciled jobs.
- **Completion is tied to nightshift.** `cadence_completion.record_completion`
  accepts only an approved nightshift org task
  (`NIGHTSHIFT_STATUS`, `NIGHTSHIFT_OUTPUT`). A Hermes or OpenClaw job has no
  such task, so it has no way to record a completion. That gap blocks
  phase 2, not a detail to leave for later.

### Work items, in order

**P0 — owner decisions (below), plus one simplification.**
`principals.yaml: owns.roles` stops being maintained by hand. It is
derived from venture.yaml `role.agent`, and the registry holds only who a
principal is and where it runs. That removes the agreement test the draft
proposed, because nothing is left to disagree.

**P1 — ownership is total and visible** (core + ventures, one session)
1. `cadence_engine.owner_of(role, venture)` resolves `role.agent`, then
   the venture's `defaults.agent`, then `miles`. Aliases are normalised
   (`nightshift`/`heartbeat` → `miles`); `human` means a person owns it,
   so it is never scheduled and is reported as a reminder.
   `venture_doctor` rejects an agent that is not a principal.
2. `SELF_AGENTS` is deleted. `own_cadences(overdue, roles, actor)` keeps
   only this actor's cadences.
3. `cadence_liveness.py` counts every assigned cadence and names owner and
   state for each: `not-registered`, `registered-not-run`, or `late`.
- DONE_WHEN: box liveness lists 5-plur cio's cadences with owner `tris`.
  A test assigns a role to an unknown agent and venture_doctor fails.
- MUST NOT: change which cadences Miles executes. The heartbeat's
  behaviour is unchanged in P1.

**P2a — the shared pieces** (ventures module, one session)
1. `cadence_schedule.py plan --actor X` builds the desired job set from
   venture.yaml:
   - name `cadence:<venture>:<role>:<cadence>`
   - a cron expression from the frequency: daily `M H * * *`, weekly
     `M H * * D`, monthly `M H d * *`, quarterly `M H d 1,4,7,10 *`
   - minute, hour and day are hashed from the name inside the host's
     window, so the result is deterministic and staggered
   - the prompt
   - the venture.yaml commit it came from
2. The prompt builder is extracted from `venture_heartbeat.build_agent_prompt`
   and narrowed to one cadence (role, template, boundary, budget). It ends
   with the completion command.
3. **Completion evidence without nightshift.** `cadence_completion record
   --venture --role --cadence --output <path-in-space> --run-id <scheduler run>`
   writes the actor's shard. It requires the artifact to exist inside the
   space, to be non-empty, and to be newer than the window's start. The
   nightshift-task path stays as a second evidence kind. Liveness
   re-verifies the artifact from git on the box, so the actor reports and
   the box judges.
4. Reconciler `cadence_schedule_sync.py --actor X --scheduler S
   [--apply|--check]`. The default is dry-run. `--check` exits non-zero on
   drift. It touches only jobs whose name (or OpenClaw declaration) starts
   with `cadence:`, and never a hand-made job. It writes
   `cadence-log/registrations/<actor>.yaml` next to the completion shards,
   so it replicates the same way.
- DONE_WHEN: `plan` output for Miles equals today's set of 56 non-continuous
  Miles cadences. `sync --check` against an empty fake scheduler reports
  every one of them missing, and after `--apply` it reports none.

**P2b — rollout, one principal at a time, each soaked 3 days green**
1. **Tris / hermes (first: small and already half-true).**
   - The Hermes adapter goes through the hermes CLI in its venv, or holds
     a file lock that the ticker honours. It never does a blind write to
     jobs.json while the ticker runs, which a spike checks first.
   - The existing `geo-research-tris` job is adopted, renamed to the
     cadence name, and not duplicated.
   - Precondition: hermes holds 5-plur under its canonical name.
   - Contract: `hermes-cadence-registration` (sync --check).
2. **Miles / nightshift (the bulk, and the real change).**
   - About 56 cadences move from the heartbeat's pick-one tick into
     nightshift's scheduler.
   - While both paths exist, the heartbeat executes only cadences that
     are *not* in Miles's registration record, so no cadence runs twice.
     Once all are registered, the heartbeat keeps only sense-and-escalate.
   - Runs are serialised by a flock so one host's jobs never stack.
   - The window spans the day. The fleet's Claude plan window is shared,
     and spreading the load matters more than timing.
3. **Data / plur-claw.** Cadences: the daily X post (today seven hand-made
   OpenClaw automations, `plur-daily-x-memory-<weekday>`, adopted and not
   duplicated), plus a **daily** blog post (canonical) with a dev.to
   mirror (owner, 2026-09-23; replaces the 2026-07-29 "2-3/week" drip).
   The 07-29 publish policy is unchanged: evergreen posts publish after
   the automated fact-check, and comparison-class posts wait for cos-approval. The adapter
   drives `openclaw cron add/edit/rm` and keys ownership on the
   `Declaration` column.
4. **Winston / box.** Cadence: the Sunday weekly plan, plus the four box
   duties that `principals.yaml: owns.cadences` lists today (briefing,
   verify-daily, liveness, scoreboard). They move into venture.yaml
   (firm:cos), so there is one place for cadences. The adapter is
   `cron_install.py` managed entries.

**P2c — retire the old path.** The execution branch of
`venture_heartbeat` and `cadence_runner.py` are removed. `cadence_runner.py`
turns org tasks into nightshift work, a second executor that nothing wires
today.

**P3 — takeover.** Later, behind the owner's N and stand-in decisions.

### Whole-upgrade DONE_WHEN (machine-checkable)

- For 7 consecutive days box liveness reports 0 cadences in
  `not-registered` or `late`, and every completion is attributed to its
  owner with a verified artifact.
- **Induced failure:** `venture-heartbeat.service` is stopped on nightshift
  for a day. Tris's cadences still complete, and Miles's scheduled cadences
  still complete, because the heartbeat no longer executes anything.

### Owner decisions, 2026-09-23

1. **Every principal gets its cadences. Rollout goes one principal at a
   time**: Tris, then Miles, then Data, then Winston.
2. **No folder numbers.** `5-plur` and `8-firm` are one machine's layout. A
   venture is named by `venture.yaml: name` (`plur`, `firm`, `fds`) in job
   names, in `principals.yaml` role references (`firm:cos`, not
   `8-firm:cos`) and in `members.yaml`. Each host resolves name → local path
   with `venture_discovery`, which already scans for venture.yaml. That
   dissolves the "canonical layout on hermes/plur-claw" precondition: a host
   needs a checkout of the space repo, under any directory name. Known
   offenders to fix in P1: `3-fds/venture.yaml space: 3-fds`,
   `members.yaml space: <N-name>`, and every `N-name:role` in
   principals.yaml.
3. **Reassignment comes after execution.** Roles keep their current owners
   (unassigned → Miles) until every principal executes cadences. Then the
   existing cadences are analysed and reassigned.
4. **Clean slate.** Every 1-datafund and 3-fds cadence was parked on
   2026-09-23 (datafund c06b5fb, fds 35418d9). None had run since
   2026-08-19 and 2026-09-04 respectively. The list, with the last run
   recorded for each, is kept as comments in each venture.yaml, so they
   come back one by one.

### Winston's weekly plan: why it does not start reliably (measured 2026-09-23)

`cos_weekly_plan.sh` (box cron, Sunday 07:00) runs `claude -p "/weekly-plan …"`.
On the box, Claude Code does not know the command, because it lives in
`modules/chief-of-staff/commands/` and is not in `~/Data/.claude/commands`.
The log records `Unknown command: /weekly-plan` on 2026-09-16 and on
2026-09-20. `claude` exits 0 anyway. The script's artifact check then asks
whether *any* `fragments/*/weekly-plan.json` exists. The 2026-09-16 fragment
does, so on 2026-09-20 the script logged "draft written" and sent "Weekly plan
draft ready for review" over a plan that was four days old. The scheduler
started the job reliably; the job ran nothing, and the check was fooled.

Two causes, and neither goes away just by moving to a new scheduler:
- The command has to resolve on the host that runs it. The cadence prompt
  builder therefore inlines the command body, and does not depend on a
  slash-command lookup.
- Evidence has to be fresh. That is the P2a completion rule: the artifact
  exists and is newer than the start of the window. Under that rule, the
  2026-09-20 run would have been a failure, not a false "ready".
