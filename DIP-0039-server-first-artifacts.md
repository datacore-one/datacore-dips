# DIP-0039: Server-First Artifacts

| Field | Value |
|-------|-------|
| **DIP** | 0039 |
| **Title** | Server-First Artifacts |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Draft |
| **Created** | 2026-07-30 |
| **Updated** | 2026-07-30 |
| **Tags** | `topology`, `box`, `mac-spof`, `installer`, `artifact-sync`, `job-verify`, `datacore-v2` |
| **Affects** | `.datacore/lib/v2_box_setup.sh`, `.datacore/lib/artifact_sync.py`, `.datacore/lib/config_plane.py`, `.datacore/lib/job_verify.py`, `.datacore/lib/jobs/manifest.yaml`, `.datacore/lib/jobs/checks.py` (regex check now `re.MULTILINE`, same-day fix), `~/.datacore/datacore.env` (box canonical env), `~/.datacore/datacore.env` (mac canonical env, new), box root crontab, `modules/chief-of-staff/server/lib/cos_verify_morning.py` (named for retirement, not yet retired) |
| **Specs** | `.datacore/lib/v2_box_setup.sh`, `.datacore/lib/artifact_sync.py` |
| **Agents** | any process that reads CoS briefing artifacts on the mac (datacore-app, `/today`); the box installer itself; `job_verify.py --machine box` as the box-side monitor this DIP puts on a cron |
| **Relates to** | `ENG-2026-0612-017` (the original Mac-SPOF finding this whole DIP answers), `ENG-2026-0727-008` (three-machine topology: mac / box (Winston) / nightshift, corrected in place, canonical role split), DIP-0034 (Event Ledger Substrate — `metric.attest` events `job_verify.py` writes), DIP-0035 (Job Contracts + Unified Verifier — the manifest and verifier this DIP puts into production on a real box for the first time), DIP-0036 (Config Plane — `config_plane.py`'s canonical/legacy env model, which `v2_box_setup.sh` and `artifact_sync.py` both consume) |

## Summary

Makes the box (`cos-server`, "Winston") the **source of truth** for
Chief-of-Staff artifacts, and the mac a **read-only puller**, closing the
Mac-single-point-of-failure gap named in `ENG-2026-0612-017`: today, nothing
protects the user if the mac's own generation path breaks or falls behind —
the mac has no canonical env of its own, no scheduled pull of the box's
briefing output, and no automated check that the box's own crons produced
anything real. This DIP ships three pieces of infrastructure and specifies
one operational contract:

1. **`v2_box_setup.sh`** — an idempotent, check-then-apply installer that
   gives the box a canonical env (`~/.datacore/datacore.env`, 0600, migrated
   from three legacy env files), a modern `cryptography>=41`, and a cron
   that runs `job_verify.py --machine box` daily.
2. **`artifact_sync.py`** — a mac-side client that pulls three box-generated
   CoS artifacts (today's `app-briefing.json`, `answers.yaml`, `facts.json`)
   over `rsync`-over-`ssh`, so the mac always has a local copy of what the
   box actually produced, independent of whether the mac's own briefing
   path is healthy.
3. **The role contract** this DIP formalizes: mac runs no autonomous
   Chief-of-Staff execution (per `ENG-2026-0727-008`); box runs all of it and
   is the one machine whose artifacts are authoritative; the mac only ever
   *reads* what the box wrote.

This DIP also records, in its Honest Status section below, the **first live
run of this installer against the real box** — what actually happened,
verbatim, not a description of intended behavior — and starts the
7-green-days retirement clock for the box's legacy morning verifier,
`cos_verify_morning.py`, which this DIP does **not** yet retire.

## Motivation

### Problem: the mac has no independent verification of the box's output, and no fallback if its own generation breaks

`ENG-2026-0612-017` identified the mac as a single point of failure: the
mac's own datacore-app can generate a CoS-style briefing locally, but
nothing pulls a copy of what the box's own, independently-scheduled,
independently-monitored crons actually produced. If the mac's local
generation path silently degrades — the exact failure genre DIP-0035 was
written to catch on the box side (missing credentials, an f-string bug, an
unset env var, all producing an "exit 0" that hides a real failure) — there
is no fallback artifact to read, because the mac never fetched one.

`ENG-2026-0727-008` (three-machine split, corrected in place 2026-07-27)
draws the canonical boundary this DIP operationalizes:

> **MAC** — the user's laptop. Runs the datacore-app... an agent-stream
> rsync that PULLS from nightshift so the app's live feed has data. **It
> must run NO autonomous execution.** **BOX / cos-server** — ALL
> Chief-of-Staff work: 10 crons (backup, news, email triage, github triage,
> briefing, inbox, research, health digest, tomorrow, cos_sync every 15
> min).

The topology rule already existed as a corrected-in-place engram. What did
not exist, before this DIP's Task 6.1/6.2 code and this DIP's Task 6.3 live
run, was: (a) a mac-side puller that actually implements "the mac only
reads," (b) a box-side installer that gives the box the canonical env and
verification cron this whole scheme depends on, and (c) evidence that any
of it works against the real box rather than only against test fixtures.

### Use cases

1. **The mac always has a recent copy of the box's briefing, independent of
   the mac's own generation health.** `artifact_sync.py --role client` pulls
   `app-briefing.json` (plus `answers.yaml` and `facts.json`, when the box
   has produced them) into the mac's own `~/.datacore/cos/` tree on the same
   cadence the box's `mac-artifact-pull` manifest entry declares.
2. **The box's canonical env exists exactly once, non-empty, mode 600,**
   regardless of how many of its three legacy env files (`~/.config/cos.env`,
   `/etc/datacored.env`, `~/.hermes/.env`) happen to exist or overlap —
   first-source-wins migration, values never leave the box.
3. **A human (or the installer itself, re-run) can always tell whether the
   box is in the target v2 state** via `--verify`, and can move it there
   idempotently via `--apply` — no step mutates anything already correct.
4. **The box's own job-manifest verifier runs unattended, daily,** the same
   mechanism DIP-0035 specified, now actually installed on a cron on the
   real machine it is supposed to protect.

## Current Workaround (pre-DIP)

- The mac has no canonical env file at all (`~/.datacore/datacore.env` did
  not exist before this DIP's Task 6.3 run created it) and no mechanism to
  acquire one short of a human hand-writing it.
- Nothing on the mac ever pulls anything from the box. The box's CoS
  artifacts (briefing, answers, facts) exist only on the box; if the mac's
  own generation is broken, degraded, or simply not run that day, the user
  has no local fallback copy of what the box actually produced.
- The box itself has no single canonical env — three legacy files
  (`~/.config/cos.env`, `/etc/datacored.env`, `~/.hermes/.env`) each hold a
  subset of required variables, with no migration path and no single file a
  new tool (`job_verify.py`, `config_plane.py`) could read.
- The box's only automated morning-pipeline check is
  `cos_verify_morning.py` (root cron, `0 8 * * *`) — a bespoke, single-
  purpose script pre-dating DIP-0035's general job-manifest verifier. It
  keeps running unchanged; this DIP does not retire it (see Honest Status).

## Specification

### Roles

Three machines, one role each, per `ENG-2026-0727-008`:

| Machine | Role under this DIP | Autonomous execution? |
|---|---|---|
| **mac** (user's laptop) | Read-only artifact puller (`artifact_sync.py --role client`); runs the datacore-app locally but that is a *view*, not the source of truth for CoS artifacts | No — must run no autonomous CoS execution |
| **box** / `cos-server` ("Winston") | Source of truth. Generates all CoS artifacts on its own crontab; runs `job_verify.py --machine box` on its own cron to self-check | Yes — all CoS work lives here |
| **nightshift** | Development/research delegation, unaffected by this DIP | Yes — its own systemd timers, out of scope here |

`artifact_sync.py`'s role gating is a hard architectural statement, not just
a CLI default: `sync_plan("server", ...)` returns an **empty plan** — the
box never pulls from itself, by construction, not by convention.

### Artifact flows

One direction only: **box → mac**, over `rsync -az --timeout=20` via SSH,
driven by `COS_SERVER_SSH` (an SSH `user@host` string) read from the mac's
own canonical env — never hardcoded, never committed. Three artifacts, all
rooted at `~/.datacore/cos/` on both ends:

| Artifact | Box path (source) | Mac path (destination) |
|---|---|---|
| Today's briefing | `~/.datacore/cos/briefings/{today}/app-briefing.json` | same, mac-local |
| Answers | `~/.datacore/cos/answers.yaml` | same, mac-local |
| Facts | `~/.datacore/cos/facts.json` | same, mac-local |

`run_sync` never raises on a sync/network failure — a missing
`COS_SERVER_SSH`, a failed rsync, a timeout, or a missing `rsync` binary all
become a human-readable error string in the returned list, so a caller (cron
or launchd) can observe a partial failure without a crash. A
`ConfigError` from a malformed (not merely missing) canonical env file is
the one thing allowed to propagate, by design — that is a configuration
defect, not a transient sync failure.

### Box installer (`v2_box_setup.sh`)

Four steps, run in order, aggregate exit code, `--verify` (assert-only) or
`--apply` (check-then-mutate) — exactly one mode required:

1. **`cryptography>=41`** — checked via `python3 -c "import cryptography..."`;
   applied via `pip3 install -q 'cryptography>=41'` if missing.
2. **Canonical env** (`~/.datacore/datacore.env`) — created 0600 if absent;
   permission re-asserted; on `--apply`, legacy `KEY=VALUE` lines from
   `~/.config/cos.env`, `/etc/datacored.env`, `~/.hermes/.env` are migrated
   in, first-source-wins, with strict key-shape validation
   (`^[A-Za-z_][A-Za-z0-9_]*$`) rejecting anything else as an explicit SKIP.
   Legacy files are never touched or deleted — kept until this DIP's
   retirement gates pass.
3. **`job_verify` cron** — installs (on `--apply`, if not already present, by
   exact fixed-string whole-line match) a root crontab line running
   `job_verify.py --machine box --alert telegram` daily at `08:00 UTC`,
   deliberately the same wall-clock slot `cos_verify_morning.sh` already
   runs at (see Honest Status — this is the intended overlap during the
   retirement window, not a scheduling accident).
4. **TODO(verify-on-box) resolution report** — a pure, non-mutating scan of
   the job manifest for `TODO(verify-on-box)` markers, reporting for each
   whether its artifact path exists on this box right now. Informational
   only; this DIP's Task 6.3 run found none present (all box-scoped TODOs
   had already been resolved in an earlier task).

### Verify cron

`0 8 * * * DATACORE_V2=1 DATACORE_ROOT=/root/Data python3 /root/Data/.datacore/lib/job_verify.py --machine box --alert telegram >> /root/.datacore/state/job_verify.log 2>&1`

Runs daily, checks every `machine: box` job in the manifest (10 jobs as of
this DIP), writes one `metric.attest` ledger event per job, and dispatches
exactly one Telegram alert per failing job (per DIP-0035).

## Honest Status (2026-07-30, Task 6.3 — first live run)

This section states exactly what ran today against the real box
(`cos-server`/Winston), not what is intended to run. Recorded in full,
verbatim, in `task-6.3-report.md` (untracked, `.superpowers/sdd/`); summary
here.

**Pre-state (read before any mutation):** box on branch `main`,
`cryptography` already at `41.0.7` (pre-satisfies step 1), no
`/root/.datacore/datacore.env` (canonical env did not exist), 11-line root
crontab (10 CoS crons + `cos_sync`), none of the v2 lib files present on the
box yet.

**Rsync:** 27 files transferred cleanly (`v2_box_setup.sh`, `job_verify.py`,
`config_plane.py`, `artifact_sync.py`, `ledger_cli.py`,
`briefing_grounded.py`, `requirements.txt`, and the `ledger/`, `jobs/`,
`briefing/` package directories, `__pycache__` excluded).

**`--verify` (pre-apply):** FAILED as expected — `env` and `cron` both
missing. `cryptography` already OK.

**`--apply`:** exit 0. Created `~/.datacore/datacore.env` (0600), migrated
~30 legacy variables from `cos.env`/`datacored.env`/`.env` (first-source-
wins; several already-set keys correctly SKIPped), installed the
`job_verify` cron line. No variable *values* appear in this DIP, this
report, or any tracked file — only variable names, matching
`config_plane.py`'s SECRETS RULE.

**`--verify` (post-apply): NOT clean — exit 1. This is a real finding, not
chased/fixed on the box.** `cron` reported OK. `env` reported FAILED with a
garbled "mode" value. Root cause, traced from the local script source
(`v2_box_setup.sh` line 110): `stat -f '%Lp' FILE 2>/dev/null || stat -c
'%a' FILE 2>/dev/null` assumes BSD `stat` semantics first (macOS, where
`-f` means "format string") with a GNU fallback — but on the box's GNU
coreutils 9.4, `-f` means "filesystem status," a different mode entirely.
GNU `stat -f '%Lp' FILE` treats `'%Lp'` as a second **file** argument, fails
on it (stderr), but *also* succeeds in filesystem-status mode on the real
`FILE` argument, printing a multi-line filesystem-info block to **stdout**
before the overall nonzero exit correctly triggers the `stat -c` fallback —
so the captured `$perm` variable ends up polluted with both outputs
concatenated, failing the string-equality check against `"600"` even though
the file's real permissions are correct. Verified independently: `ls -la
~/.datacore/datacore.env` on the box shows `-rw-------` (600), confirming
this is a verify-script portability bug in the stat probe, not an actual
permission defect.

**UPDATE (same day, after this section was first written):** fixed —
commit `7f68d7d` swapped the probe order to GNU-first (`stat -c '%a'`),
BSD (`stat -f '%Lp'`) kept only as a fallback for this Mac's local fixture
suite. Fixture suite green (21/21, including `test_verify_passes_after_apply`),
full suite green (609/609). Rsynced the fixed `v2_box_setup.sh` to the box
and re-ran `--verify`: now exits 0 clean —

```
[v2] cryptography: OK 41.0.7
[v2] env: OK /root/.datacore/datacore.env exists, 0600, non-empty
[v2] cron: OK job_verify cron already present
[v2] todo-report:
  (none)
[v2] verify: OK all v2 box-setup checks passed
EXIT_CODE:0
```

**Live `job_verify.py --machine box --alert log --no-emit`:** exit 1. 9 of
10 box jobs passed silently (no per-job output by design — only failures
print); one failed:

```
job 'box-briefing' FAILED:
  - /root/Data/0-personal/notes/journals/2026-07-30.md: regex '^##\s+(Daily Briefing|Good Morning)' did not match
alert: job.verify FAILED: box-briefing (1 failure(s))
```

**Determination (same day): this was a REGEX BUG, not a true positive.**
The box's actual journal
(`/root/Data/0-personal/notes/journals/2026-07-30.md`) contains both
`## Daily Briefing` and `## Good Morning` verbatim, confirmed by direct
inspection on the box — `cos_morning.sh` did not fail. Root cause, traced
and reproduced: `jobs/checks.py`'s `regex` check ran `re.search(pattern,
text)` **without `re.MULTILINE`**. The manifest's pattern is
`^##\s+(Daily Briefing|Good Morning)` — a line-anchored assertion by
intent ("some line in this file starts with one of these headings"). But
without `re.MULTILINE`, Python's `^` anchors only to position 0 of the
*entire file string*, and every journal file opens with a YAML frontmatter
block (`---\ndate: ...`), so position 0 is always `-`, never `#` — the
pattern could never match *any* journal file, regardless of whether the
target heading is present later in the text, exactly as it is here.
Reproduced directly (`re.search` with vs. without `re.MULTILINE` against
the real journal shape) before touching the fix.

This is ruled an Important defect, not a mere finding to log and move
past: a verifier that raises false-positive alerts erodes trust in the
verifier itself — precisely the failure mode DIP-0035 exists to prevent
(a check must be *right*, not merely *present*). **Fixed same day**:
`jobs/checks.py`'s regex check now always passes `re.MULTILINE`
(documented in both the module docstring and an inline comment at the
call site); a new fixture test
(`test_regex_matches_line_anchored_pattern_after_frontmatter_preamble`)
mirrors the real journal shape (frontmatter + a later `##` heading) and
was verified RED against the pre-fix code before the fix landed, then
GREEN after. Full suite: 610/610 (609 + 1 new test), no regressions.
Rsynced the fixed `checks.py` to the box and re-ran the live verifier:

```
$ ssh <box> "DATACORE_V2=1 DATACORE_ROOT=/root/Data python3 /root/Data/.datacore/lib/job_verify.py --machine box --alert log --no-emit"
OK 10 jobs 15 artifacts
EXIT_CODE:0
```

**10 of 10 box jobs now OK** — the false failure is gone; nothing else in
the manifest was hiding behind it. Scope note: the missing `re.MULTILINE`
was in the *generic* regex-check handler, so it could equally have
false-failed any other `check: regex` manifest entry with a `^`-anchored
pattern against a multi-line file with a preamble — this fix protects all
of them, not just `box-briefing`.

**Mac-side `artifact_sync.py --role client`:** dry-run planned 3 pairs
correctly (reading the new `COS_SERVER_SSH` from the freshly-created mac
canonical env, created 0600 in this same run). Real run: exit 1 — 1 of 3
succeeded (today's `app-briefing.json`, 16615 bytes, confirmed byte-for-byte
present against the box's own copy); 2 of 3 failed because the source files
do not exist on the box at all (`answers.yaml`, `facts.json` — confirmed by
direct `ls` on the box, not inferred). Absence, per this task's own framing,
is a finding: those two artifacts are not yet produced by any box process,
a gap for a later phase, not a sync bug.

**Retirement clock:** the 7-green-days clock for retiring
`cos_verify_morning.py` **STARTS today, 2026-07-30**. Nuance, stated
honestly rather than smoothed over: the box's *actual scheduled* `08:00
UTC` cron fired once already today, before either same-day fix (stat
probe, `re.MULTILINE`) had landed, and its logged run was not clean. A
**manual** re-run after both fixes now shows the box fully green (installer
`--verify` exit 0, `job_verify` 10/10 OK) — but that is a manual
confirmation of present health, not a second scheduled cron execution.
Whether the retirement gate should count "7 consecutive calendar days
ending clean" (in which case today could plausibly count, given the
system is demonstrably clean as of this update) or "7 consecutive
*scheduled cron* runs" (in which case today's actual 08:00 UTC firing was
not clean, and the streak has not started) is exactly the ambiguity Open
Question 4 names — this DIP still takes no position on it. Streak count,
under either reading, is **0 of 7 confirmed scheduled-runs** as of this
update; `cos_verify_morning.py` retirement and the notebook-off simulation
remain **dated follow-up gates, not claimed done here**.

## Open Questions

1. **RESOLVED (same day)**: the `stat -f`/`stat -c` portability bug in
   `v2_box_setup.sh` was fixed by swapping the probe to GNU-first,
   BSD-fallback (commit `7f68d7d`) — see Honest Status update above.
2. **RESOLVED (same day)**: `box-briefing`'s journal-heading regex
   "mismatch" was a regex bug (missing `re.MULTILINE`), not a real
   contract violation — the journal was correct all along. Fixed in
   `jobs/checks.py`; see Honest Status determination above for the full
   root-cause trace and live 10/10 re-verify.
3. **`answers.yaml` and `facts.json` do not exist on the box at all** — is
   this a not-yet-implemented producer, a naming mismatch with what some
   other process actually writes, or a manifest/sync-plan entry that should
   never have assumed these files exist yet? Needs a source-level check
   before the next `artifact_sync` run is expected to succeed on all three.
4. **When does the 7-green-days streak actually start counting?** This DIP
   takes no position on whether a streak must be 7 *consecutive* calendar
   days from an arbitrary start, or 7 consecutive **runs** of the 08:00 UTC
   cron — left to whoever evaluates the retirement gate.

## References

- `ENG-2026-0612-017` — the original Mac-SPOF finding; directly quoted in
  `artifact_sync.py`'s own module docstring as the gap it closes in the
  box→mac direction.
- `ENG-2026-0727-008` — three-machine topology (mac/box/nightshift role
  split, corrected in place 2026-07-27), the canonical statement this DIP's
  Roles table operationalizes.
- DIP-0034 — Event Ledger Substrate (`metric.attest` event schema
  `job_verify.py` writes).
- DIP-0035 — Job Contracts + Unified Verifier (the manifest format and
  `job_verify.py` itself, put into production on the real box for the first
  time by this DIP).
- DIP-0036 — Config Plane (`config_plane.py`'s canonical/legacy env model
  and SECRETS RULE, which both `v2_box_setup.sh` and `artifact_sync.py`
  depend on).
- `task-6.1-report.md`, `task-6.2-report.md`, `task-6.3-report.md` (untracked,
  `.superpowers/sdd/2026-07-29-datacore-v2/`) — the full verbatim record this
  DIP's Honest Status section summarizes.
