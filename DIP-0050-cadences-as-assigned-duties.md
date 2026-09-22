# DIP-0050: Cadences as assigned duties, executed by their owners

- **Status:** Draft (owner ratifies)
- **Created:** 2026-09-22
- **Depends on:** DIP-0034/0046 (per-writer ledger and cadence shards), DIP-0044 (principals, authorship), DIP-0035 (job contracts)
- **Supersedes in part:** the single-executor behaviour of `venture-heartbeat.service`

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
- Each agent principal runs **its own heartbeat on its own host**, as its
  own actor, executing only the cadences of roles assigned to it, with
  that host's runtime (executor registry: `claude-code`, `hermes`,
  `openclaw`, `openrouter`). Completions land in that actor's shard and
  replicate by git. Nothing about the storage changes.
- **Liveness counts every assigned cadence**, by owner. An overdue
  cadence names who owns it and on which host. "Assigned to an agent that
  has no heartbeat" is a finding, not silence.
- The **Chief of Staff** (Winston) edits assignments and cadences through
  the ordinary review path; it does not execute ventures' cadences itself
  except the roles it owns (`8-firm:cos`).
- **Takeover (later, not this DIP's first phase):** when an owner has
  missed N windows of a cadence, another principal that holds the space
  may claim it through the ledger's claim rules (one owner at a time, the
  claim recorded before the work), and the original owner's return is a
  release, not a conflict.

## Phases

1. **Ownership is total and visible.** Every role names an agent or
   inherits one; `SELF_AGENTS` goes; `own_cadences(overdue, roles,
   actor)` keeps the cadences of roles assigned to *this* actor;
   `cadence_liveness.py` reports every overdue cadence with its owner and
   fails on any of them; a test asserts venture.yaml and principals.yaml
   agree. Effect: Tris's three cadences become visible as overdue, owned
   by tris, today.
2. **Each principal executes its own.** `venture_heartbeat.py --actor
   <principal>` runs from each agent host's existing heartbeat timer
   (hermes, plur-claw, the box) with that host's executor. Precondition:
   the host holds the venture's space under its canonical name — hermes
   and plur-claw currently hold partial trees under other names
   (`2-plur`, `1-datacore-space`); that layout is unified first. One
   contract per principal (`<host>-venture-heartbeat`, `0 failed`), on
   the tick record DIP-0035 now reads.
3. **Takeover.** As above, behind an owner decision on N and on which
   principals may stand in for which roles.

## Loop-design gate

- Exit condition machine-judged: a completion recorded with the evidence
  `cadence_completion` already requires; liveness counts it.
- Judge independent of executor: liveness on the box, per-actor shards.
- Boundary: an actor may execute only roles assigned to it (phase 1/2) or
  claimed through the ledger (phase 3); budget authority stays per role.
- No mid-run questions: assignment is data in venture.yaml.
- Docs: this DIP, `venture_heartbeat.py`, `cadence_liveness.py`.

## Decisions the owner makes before phase 1 ships

1. The role → principal map for the live ventures (2-datacore: ceo, cto,
   cmo; 5-plur: ceo, cto, cmo→data?, cio→tris, bizdev; 8-firm: cos,
   coo, cio, comms). Unassigned roles default to miles today.
2. Whether Winston executes any venture role beyond `8-firm:cos`.
3. For phase 2: which hosts may hold which spaces (Tris on hermes for
   5-plur; Data on plur-claw for 8-firm and 2-datacore?), and the
   canonical layout on those hosts.
4. For phase 3: N missed windows before takeover, and who may stand in.
