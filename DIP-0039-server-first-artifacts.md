# DIP-0039: Server-First Artifacts

| Field | Value |
|-------|-------|
| **DIP** | 0039 |
| **Title** | Server-First Artifacts |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Implemented |
| **Created** | 2026-07-30 |
| **Updated** | 2026-10-16 |
| **Depends** | [DIP-0035](DIP-0035-job-contracts.md) (manifest format + `job_verify.py`, the primary substrate this DIP puts into production); also builds on [DIP-0034](DIP-0034-event-ledger-substrate.md) (ledger events) and [DIP-0036](DIP-0036-config-plane.md) (config plane) — see Relates to |
| **Tags** | `topology`, `server`, `workstation-spof`, `installer`, `artifact-sync`, `job-verify`, `datacore-v2` |
| **Affects** | `.datacore/lib/v2_box_setup.sh`, `.datacore/lib/artifact_sync.py`, `.datacore/lib/config_plane.py`, `.datacore/lib/job_verify.py`, `.datacore/lib/jobs/manifest.yaml`, `.datacore/lib/jobs/checks.py` (regex check uses `re.MULTILINE`), `~/.datacore/datacore.env` on the server (canonical env), `~/.datacore/datacore.env` on the workstation (canonical env), the server's crontab, `.datacore/modules/chief-of-staff/server/lib/cos_verify_morning.py` (named for retirement) |
| **Specs** | `.datacore/lib/v2_box_setup.sh`, `.datacore/lib/artifact_sync.py` |
| **Agents** | any process that reads CoS briefing artifacts on the workstation (datacore-app, `/today`); the server installer itself; `job_verify.py` as the server-side monitor this DIP puts on a cron |
| **Relates to** | DIP-0034 (Event Ledger Substrate — `metric.attest` events `job_verify.py` writes), DIP-0035 (Job Contracts + Unified Verifier — the manifest and verifier this DIP puts into production on a server), DIP-0036 (Config Plane — `config_plane.py`'s canonical/legacy env model, which `v2_box_setup.sh` and `artifact_sync.py` both consume), DIP-0005 (Installation & Upgrade — install-path boundary), DIP-0009 (GTD Specification — GTD/task-state source-of-truth this DIP's Scope note defers to), DIP-0010 (External Sync Architecture — Sync Engine boundary), DIP-0011 (Nightshift Module — server-role model and source-of-truth boundary) |

> **Ratification note (2026-08-27).** Status moved `Draft` → `Implemented` on the
> owner's instruction. **No human review was performed on this DIP.** It is recorded
> here rather than left implicit, because the governance rule is that
> `Implemented`/`Accepted` require owner ratification — this satisfies that rule
> by owner instruction alone, not by review.
>
> `Implemented` here means the infrastructure this DIP specifies has landed. It does
> **not** mean every follow-up gate named in the body is closed; read the
> Implementation and Open Questions sections for the position rather than inferring
> it from this status field.

## Summary

A workstation that both generates and displays Chief-of-Staff (CoS) artifacts is
a single point of failure: if its local generation silently degrades, there is no
independent copy to fall back on. This DIP makes a **server** (the chief-of-staff
server) the **source of truth for three named CoS artifact files** — not a
general claim about the system — and the workstation a **read-only puller** of
them. It ships three pieces of infrastructure and specifies one operational
contract:

1. **`v2_box_setup.sh`** — an idempotent, check-then-apply installer that gives
   the server a canonical env (`~/.datacore/datacore.env`, 0600, migrated from
   legacy env files), a modern `cryptography>=41`, and a cron that runs
   `job_verify.py` for the server's jobs daily.
2. **`artifact_sync.py`** — a workstation-side client that pulls three
   server-generated CoS artifacts (today's `app-briefing.json`, `answers.yaml`,
   `facts.json`) over `rsync`-over-`ssh`.
3. **The role contract**: the workstation runs no autonomous Chief-of-Staff
   execution; the server runs all of it and is the one machine whose artifacts
   are authoritative; the workstation only ever *reads* what the server wrote.

The single-point-of-failure gap is closed only when **both** halves are
automated: the server self-verifies on a schedule, **and** the workstation pulls
on a schedule. An installation that runs the pull by hand has demonstrated the
gap is closeable, not closed, and must say so.

**Scope note (source of truth).** "Server is source of truth" in this DIP means,
precisely: for the three named CoS artifact files, and only for them. It does not
alter org-mode's status as the system of record for GTD/task state, as
established by [DIP-0009](DIP-0009-gtd-specification.md) and reaffirmed by
[DIP-0010](DIP-0010-external-sync-architecture.md) and
[DIP-0011](DIP-0011-nightshift-module.md) ("nightshift... is not a source of
truth, org-mode is"). See "Relationship to DIP-0005, DIP-0010, DIP-0011" in
Specification for the full boundary statement.

## Agent Context

### When to Reference This DIP

**Always reference when:**
- Installing or upgrading the chief-of-staff server — determining whether
  `v2_box_setup.sh` has been run and whether `--verify` currently passes
- Diagnosing a missing or stale CoS artifact on the workstation
  (`app-briefing.json`, `answers.yaml`, `facts.json`) — this DIP defines which
  artifacts exist, where they come from, and how to tell a missing-producer gap
  from a transient sync failure
- Adding a new server-resident producer or a new synced artifact class — this
  DIP is where the core-vs-module placement question and the
  declarative-manifest-vs-hardcoded-list question are recorded (see "Placement"
  in Specification)
- Evaluating whether `cos_verify_morning.py` can be retired — this DIP owns the
  green-streak retirement gate (Open Question 2)
- Reconciling a machine's role (workstation / chief-of-staff server / executor
  host) — this DIP is the operational contract for that topology

### Quick Reference for Agents

| Question | Answer |
|----------|--------|
| When is the workstation-SPOF gap closed? | Only when the server verify cron AND a workstation-side pull scheduler are both installed and every synced artifact has a producer. |
| What machine is source of truth for CoS artifacts? | The chief-of-staff server. The workstation only reads. This does not change org-mode's source-of-truth status for GTD/task state (DIP-0009/DIP-0010/DIP-0011). |
| How do I check if the server is in target state? | `v2_box_setup.sh --verify` — assert-only, non-mutating. |
| `artifact_sync.py` fails for one artifact — sync bug or missing producer? | Check the source path on the server directly (`ls`). Absent source = missing producer, not a sync bug. |
| What runs `job_verify.py` on the server unattended? | A cron installed by `v2_box_setup.sh --apply`, daily at 08:00 UTC. |
| What runs `artifact_sync.py --role client` on the workstation? | A scheduler the installation must install (Open Question 3). Until then, nothing — and the gap is not closed. |

### Related Agents

| Agent | Uses This DIP For |
|-------|-------------------|
| `nightshift-orchestrator` | Confirming the workstation / chief-of-staff server / executor host role boundary before routing overnight work — the executor host stays out of scope for this DIP's server role |
| `failure-analyzer` | Classifying `job_verify.py` failures (transient sync error vs. specification defect vs. missing producer vs. a defect in the check itself) |
| `context-maintainer` | Adding the chief-of-staff server role to the installation's private infrastructure table once this DIP is ratified |
| `module-registrar` | Evaluating whether `v2_box_setup.sh`/`artifact_sync.py` should move from core `.datacore/lib/` into `.datacore/modules/chief-of-staff/` — see "Placement" in Specification |

### Integration Points

- [DIP-0034](DIP-0034-event-ledger-substrate.md) — `metric.attest` events this DIP's `job_verify.py` cron writes
- [DIP-0035](DIP-0035-job-contracts.md) — manifest format + `job_verify.py` itself, put into production on a server by this DIP
- [DIP-0036](DIP-0036-config-plane.md) — canonical/legacy env model (`config_plane.py`) both `v2_box_setup.sh` and `artifact_sync.py` depend on
- [DIP-0005](DIP-0005-installation-upgrade.md) — installation boundary; `v2_box_setup.sh` is a second, additive install path for a server-role machine, not a replacement
- [DIP-0010](DIP-0010-external-sync-architecture.md) — Sync Engine/adapter architecture; `artifact_sync.py` deliberately sits outside it (see Specification)
- [DIP-0011](DIP-0011-nightshift-module.md) — server-role model and "org-mode is source of truth, the server is not"; this DIP's server role is scoped narrower (three named artifact files) and does not contradict it

## Motivation

### Problem: the workstation has no independent verification of the server's output, and no fallback if its own generation breaks

A workstation's own datacore-app can generate a CoS-style briefing locally, but
without this DIP nothing pulls a copy of what the server's own,
independently-scheduled, independently-monitored crons actually produced. If the
workstation's local generation path silently degrades — the exact failure genre
DIP-0035 was written to catch (missing credentials, an f-string bug, an unset env
var, all producing an "exit 0" that hides a real failure) — there is no fallback
artifact to read, because the workstation never fetched one.

The canonical topology this DIP operationalizes:

> **Workstation** — the user's laptop. Runs the datacore-app as a *view*. **It
> must run NO autonomous execution.** **Chief-of-staff server** — ALL
> Chief-of-Staff work on its own crontab (backup, news, email triage, github
> triage, briefing, inbox, research, digests, periodic sync). **Executor host** —
> overnight development/research delegation (DIP-0011).

The topology rule alone is not enough. It needs (a) a workstation-side puller
that actually implements "the workstation only reads," (b) a server-side
installer that gives the server the canonical env and verification cron this
scheme depends on, and (c) evidence that it works against a real server rather
than only against test fixtures.

### Use cases

1. **The workstation pulls a recent copy of the server's briefing** —
   `artifact_sync.py --role client` pulls `app-briefing.json` (and, once their
   producers exist, `answers.yaml` and `facts.json`) into the workstation's own
   `~/.datacore/cos/` tree, on a schedule.
2. **The server's canonical env exists exactly once, non-empty, mode 600,**
   regardless of how many legacy env files happen to exist or overlap —
   first-source-wins migration, values never leave the server.
3. **A human (or the installer itself, re-run) can always tell whether the
   server is in the target v2 state** via `--verify`, and can move it there
   idempotently via `--apply` — no step mutates anything already correct.
4. **The server's own job-manifest verifier runs unattended, daily,** the
   mechanism DIP-0035 specified, installed on a cron on the machine it is
   supposed to protect.

## Current Workaround (pre-DIP)

- The workstation has no canonical env file and no mechanism to acquire one short
  of a human hand-writing it.
- Nothing on the workstation pulls anything from the server; the server's CoS
  artifacts exist only on the server.
- The server has no single canonical env — several legacy files each hold a
  subset of required variables, with no migration path and no single file a new
  tool (`job_verify.py`, `config_plane.py`) could read.
- The server's only automated morning-pipeline check is a bespoke, single-purpose
  verifier (`cos_verify_morning.py`) pre-dating DIP-0035's general job-manifest
  verifier. It keeps running unchanged until the retirement gate passes.

## Specification

### Roles

Three machine roles, one role each:

| Machine role | Role under this DIP | Autonomous execution? |
|---|---|---|
| **Workstation** (user's laptop) | Read-only artifact puller (`artifact_sync.py --role client`); runs the datacore-app locally but that is a *view*, not the source of truth for CoS artifacts | No — must run no autonomous CoS execution |
| **Chief-of-staff server** | Source of truth. Generates all CoS artifacts on its own crontab; runs `job_verify.py` on its own cron to self-check | Yes — all CoS work lives here |
| **Executor host** | Development/research delegation, unaffected by this DIP | Yes — its own timers, out of scope here |

Machine ids used in the job manifest (`machine:` field, `job_verify.py
--machine`) are installation-defined; the examples below write `server`.

`artifact_sync.py`'s role gating is a hard architectural statement, not just a
CLI default: `sync_plan("server", ...)` returns an **empty plan** — the server
never pulls from itself, by construction, not by convention.

### Artifact flows

One direction only: **server → workstation**, over `rsync -az --timeout=20` via
SSH, driven by `COS_SERVER_SSH` (an SSH `user@host` string) read from the
workstation's own canonical env — never hardcoded, never committed. Three
artifacts, all rooted at `~/.datacore/cos/` on both ends:

| Artifact | Server path (source) | Workstation path (destination) |
|---|---|---|
| Today's briefing | `~/.datacore/cos/briefings/{today}/app-briefing.json` | same, workstation-local |
| Answers | `~/.datacore/cos/answers.yaml` | same, workstation-local |
| Facts | `~/.datacore/cos/facts.json` | same, workstation-local |

An artifact listed here whose producer does not yet exist on the server must be
marked "not yet produced" in the installation's status, not left implied-pending.

`run_sync` never raises on a sync/network failure — a missing `COS_SERVER_SSH`, a
failed rsync, a timeout, or a missing `rsync` binary all become a human-readable
error string in the returned list, so a caller (cron or launchd) can observe a
partial failure without a crash. A `ConfigError` from a malformed (not merely
missing) canonical env file is the one thing allowed to propagate, by design —
that is a configuration defect, not a transient sync failure.

### Server installer (`v2_box_setup.sh`)

Four steps, run in order, aggregate exit code, `--verify` (assert-only) or
`--apply` (check-then-mutate) — exactly one mode required:

1. **`cryptography>=41`** — checked via `python3 -c "import cryptography..."`;
   applied via `pip3 install -q 'cryptography>=41'` if missing.
2. **Canonical env** (`~/.datacore/datacore.env`) — created 0600 if absent;
   permission re-asserted; on `--apply`, legacy `KEY=VALUE` lines from the
   server's legacy env files (for example a CoS shell env, a system-service env
   file, an agent gateway's own `.env`) are migrated in, first-source-wins, with
   strict key-shape validation (`^[A-Za-z_][A-Za-z0-9_]*$`) rejecting anything
   else as an explicit SKIP. Legacy files are never touched or deleted — kept
   until the retirement gates pass. Only variable *names* may appear in logs or
   reports, never values (`config_plane.py` SECRETS RULE).
3. **`job_verify` cron** — installs (on `--apply`, if not already present, by
   exact fixed-string whole-line match) a crontab line running `job_verify.py`
   for the server's jobs with chat alerting daily at `08:00 UTC`, deliberately
   the same wall-clock slot as the legacy verifier (see Compatibility — this is
   the intended overlap during the retirement window, not a scheduling accident).
4. **TODO(verify-on-box) resolution report** — a pure, non-mutating scan of the
   job manifest for `TODO(verify-on-box)` markers, reporting for each whether its
   artifact path exists on this server right now. Informational only.

**Portability rule.** Probes must work on the server's userland first. In
particular, the file-mode probe is GNU-first (`stat -c '%a'`), with BSD
(`stat -f '%Lp'`) only as a fallback: on GNU coreutils `-f` means "filesystem
status", and a BSD-first probe pollutes its captured output.

### Verify cron

```
0 8 * * * DATACORE_V2=1 DATACORE_ROOT=$DATACORE_ROOT python3 $DATACORE_ROOT/.datacore/lib/job_verify.py --machine server --alert telegram >> ~/.datacore/state/job_verify.log 2>&1
```

Runs daily, checks every job in the manifest assigned to the server, writes one
`metric.attest` ledger event per job, and dispatches exactly one alert per
failing job (per DIP-0035).

**Check-correctness rule.** A verifier that raises false-positive alerts erodes
trust in the verifier itself — a check must be *right*, not merely *present*. In
particular, the generic `regex` check always passes `re.MULTILINE`, so a
line-anchored pattern (`^##\s+Heading`) matches a later line in a file that opens
with a frontmatter preamble. Every such check carries a fixture test that mirrors
the real file shape.

### Workstation-side trigger mechanism

The workstation must invoke `artifact_sync.py --role client` on a fixed cadence
(cron, launchd, or a hook off an existing workstation schedule), analogous to the
server's `job_verify` cron above. The choice of mechanism is Open Question 3.
Until one is installed, the workstation half of the contract is a manual
procedure and the installation must not report the SPOF gap as closed.

### Relationship to DIP-0005, DIP-0010, DIP-0011

**DIP-0005 (Installation & Upgrade).** `v2_box_setup.sh` is a deliberate second,
additive install path, scoped to one machine class: a headless, server-role
machine already running Chief-of-Staff crons. It does not replace DIP-0005's two
paths (MCP-only, Full System) — the server still needs a DIP-0005 Full System
install first (git clone, Python deps, module install); `v2_box_setup.sh` only
layers the server-specific canonical-env and verify-cron on top of that.
Recording it as a third install path in DIP-0005 is follow-up work.

**DIP-0010 (External Sync Architecture).** `artifact_sync.py` deliberately sits
outside DIP-0010's Sync Engine/adapter architecture (`.datacore/lib/sync/`,
adapters, conflict resolution, routing, history). This is a stated exception,
not an oversight: the three CoS artifacts are ephemeral, fully-regenerated-daily
outputs, never intended for git history or bidirectional conflict resolution, and
a one-directional rsync-over-ssh pull is proportionate to that. The cost of the
exception: none of DIP-0010's routing, history, or conflict-resolution guarantees
apply to these three files.

**DIP-0011 (Nightshift Module).** The "server is source of truth" claim in this
DIP is scoped exclusively to the three named CoS artifact files. It does not
alter DIP-0011's own declaration that nightshift "is not a source of truth
(org-mode is)" for GTD/task state — that boundary is untouched, exactly as
[DIP-0034](DIP-0034-event-ledger-substrate.md)'s own boundary statement
establishes for the event ledger `job_verify.py` writes to. The chief-of-staff
server role introduced here is distinct from the executor host role, and
DIP-0011's server-role model does not yet name a third role. Reconciling them is
future work if the two roles converge.

### Placement: core `.datacore/lib/` vs. `.datacore/modules/chief-of-staff/`

This DIP ships `v2_box_setup.sh` and `artifact_sync.py` into core
`.datacore/lib/`, alongside the payload-agnostic `job_verify.py` and
`config_plane.py` they depend on — but both new scripts are hardcoded to exactly
three chief-of-staff artifact filenames (`app-briefing.json`, `answers.yaml`,
`facts.json`) and one chief-of-staff-specific env var name (`COS_SERVER_SSH`).
That makes them CoS-specific tools living in a core location, which DIP-0022
would normally place under `.datacore/modules/chief-of-staff/`. Either (a)
generalize the artifact list into a declarative, manifest-driven set before any
second server-resident producer is added, keeping the scripts in core as a
reusable pattern, or (b) move both scripts under
`.datacore/modules/chief-of-staff/` as-is. Recorded as Open Question 4.

## Compatibility

This DIP is additive infrastructure on the server and the workstation; it removes
nothing and breaks no existing mechanism.

### Env file migration (server and workstation)

`v2_box_setup.sh --apply` migrates `KEY=VALUE` lines from the legacy env files
into the new canonical `~/.datacore/datacore.env`, first-source-wins. Legacy files
are never modified or deleted. Migration is therefore non-destructive by
construction: a value present only in a later legacy source, and shadowed by an
earlier one, is not lost — it still exists, unused, in its original legacy file.
The failure mode of overlap is a silently-unused variable, not a silently-lost
one. Legacy and canonical files coexist until the retirement gates pass and a
future DIP explicitly retires the legacy files.

### Dual verification crons during the retirement window

`v2_box_setup.sh --apply` installs the new `job_verify.py` cron at the same
wall-clock slot (`08:00 UTC`) the legacy verifier already occupies. This is
deliberate: for the duration of the retirement window (a) two processes read
overlapping server state within the same minute-scale window, and (b) a real
failure could produce two separate alerts — one per verifier — for a single
underlying incident. Neither verifier is silenced; the overlap is the point, so
the new verifier can be checked against the old one's judgment before the old
one is retired. This DIP accepts duplicate-alert risk as the known cost.

### Breaking changes

None. No existing file format, cron, or script is removed by this DIP. No prior
DIP's guarantees are altered — see "Relationship to DIP-0005, DIP-0010, DIP-0011"
above.

## Implementation

### Phases

| Phase | Scope | Gate |
|---|---|---|
| 1. Server installer + verify cron | `v2_box_setup.sh`, canonical env, `job_verify` cron | `--verify` exits 0 and `job_verify.py` for the server's jobs exits 0 |
| 2. Workstation canonical env | `~/.datacore/datacore.env` on the workstation, 0600 | file exists, 0600, contains `COS_SERVER_SSH` |
| 3. Workstation artifact pull | `artifact_sync.py --role client` | a real run reproduces each produced artifact byte-for-byte |
| 4. Workstation-side scheduler | cron/launchd invocation of `artifact_sync.py --role client` | installed and observed firing; the gate between "demonstrated closeable" and "closed" |
| 5. `answers.yaml` / `facts.json` producers | Server-side generation of every synced artifact | each source path exists on the server |
| 6. `cos_verify_morning.py` retirement | Removing the legacy verifier once the new one is proven | green streak per Open Question 2 |

### Reference implementation

- `v2_box_setup.sh`, `artifact_sync.py`, `config_plane.py`, `job_verify.py`,
  `jobs/checks.py` — `.datacore/lib/`.
- Fixture tests include a verify-passes-after-apply test for the installer and
  a line-anchored-regex-after-frontmatter test for `jobs/checks.py`.

### Rollout plan

Sequential and gated, not all-at-once. Each phase's gate is checked on the real
machines, not only against fixtures. Nothing here should be read as "generalized
and rolled out" until Open Question 4 (core vs. module placement) is resolved.

## Open Questions

1. **Missing producers.** When a synced artifact has no producer on the server,
   is it a not-yet-implemented producer, a naming mismatch with what some other
   process actually writes, or a sync-plan entry that should not exist yet? Check
   at source level before expecting the pull to succeed on all artifacts.
2. **When does the green streak for retiring the legacy verifier start
   counting?** Seven consecutive calendar days ending clean, or seven
   consecutive *scheduled cron* runs? A manual re-run confirms present health but
   is not a scheduled run. Decide before the first date at which the two readings
   could produce different retirement calls.
3. **What runs `artifact_sync.py --role client` on the workstation, and when?**
   Candidates (cron, launchd, a hook off an existing workstation schedule) are
   not yet evaluated against each other. Resolve before any status report
   upgrades the SPOF claim from "demonstrated closeable" to "closed".
4. **Does this DIP's code belong in core `.datacore/lib/` or under
   `.datacore/modules/chief-of-staff/`?** See "Placement" in Specification.
   Decide before a second server-resident producer or a second synced artifact
   class is added — whichever comes first.

## References

- [DIP-0034](DIP-0034-event-ledger-substrate.md) — Event Ledger Substrate
  (`metric.attest` event schema `job_verify.py` writes).
- [DIP-0035](DIP-0035-job-contracts.md) — Job Contracts + Unified Verifier
  (the manifest format and `job_verify.py` itself).
- [DIP-0036](DIP-0036-config-plane.md) — Config Plane (`config_plane.py`'s
  canonical/legacy env model and SECRETS RULE, which both `v2_box_setup.sh` and
  `artifact_sync.py` depend on).
- [DIP-0005](DIP-0005-installation-upgrade.md) — Installation & Upgrade;
  `v2_box_setup.sh` is a second, additive install path.
- [DIP-0009](DIP-0009-gtd-specification.md) — GTD Specification; the
  source-of-truth boundary this DIP's Scope note defers to for GTD/task state.
- [DIP-0010](DIP-0010-external-sync-architecture.md) — External Sync
  Architecture; `artifact_sync.py` deliberately sits outside its Sync
  Engine/adapter model.
- [DIP-0011](DIP-0011-nightshift-module.md) — Nightshift Module; source of the
  "org-mode is source of truth, the server is not" principle this DIP's claim is
  explicitly scoped against.
