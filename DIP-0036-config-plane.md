# DIP-0036: Config Plane

| Field | Value |
|-------|-------|
| **DIP** | 0036 |
| **Title** | Config Plane |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Draft |
| **Created** | 2026-07-30 |
| **Updated** | 2026-07-30 |
| **Tags** | `config`, `env`, `secrets`, `doctor`, `datacore-v2` |
| **Affects** | `.datacore/lib/config_plane.py`, `.datacore/lib/job_verify.py` (`--doctor` flag), `~/.datacore/env` (canonical, per machine), legacy sources: `~/.config/cos.env`, `/etc/datacored.env`, `~/.hermes/.env` |
| **Specs** | `.datacore/lib/config_plane.py`, `.datacore/lib/job_verify.py` |
| **Agents** | any process reading a job's `required_env`; `job_verify.py --doctor` as the audit surface; `cos-server-setup.sh` (Phase 6 migration) |
| **Relates to** | DIP-0034 (Event Ledger Substrate), DIP-0035 (Job Contracts + Unified Verifier — `required_env` is this DIP's own audit input), `ENG-2026-0728-001` (silent-degradation failure genre, item 1: token-refresh sync gap), `ENG-2026-0725-016` (single-refresher-owner pattern for rotating credentials) |

## Summary

Introduces a single canonical per-machine env file (`~/.datacore/env`) as
the one place process configuration is read from, replacing the ambiguous
"which of three env files does this cron job actually source" state that
caused `ENG-2026-0728-001` item 1. A pure loader (`config_plane.load()`)
parses `KEY=VALUE` files with zero `os.environ` side effects; a `doctor()`
audit (`config_plane.doctor()`, surfaced on the CLI via `job_verify.py
--doctor`) diffs the canonical file against a machine's jobs'
manifest-declared `required_env` (DIP-0035) and against the known legacy
sources, producing a names-only migration checklist — variable and source
names, never a value. This is Phase 3 of the v2 rollout DIP-0034 names in
its Rollout Plan; it consumes DIP-0035's manifest schema (`required_env`)
directly and has no event type of its own on DIP-0034's ledger.

## Motivation

### Problem: which env file a process actually reads is not obvious, and that ambiguity already caused an outage

- **The incident this DIP exists to prevent a repeat of**
  (`ENG-2026-0728-001`, item 1): `cos_token_refresh.py` synced
  `/etc/datacored.env` and `~/.hermes/.env` with a rotated credential, but
  **not** `~/.config/cos.env` — the file every `cos_*.sh` cron script
  actually sources (`/etc/datacored.env` is a systemd `EnvironmentFile`
  handed to `datacored` alone). Cron then ran credential-less for days:
  `claude -p` returned "Not logged in" on **empty stderr**, surfacing only
  as `"claude -p failed:"` with nothing after the colon, while the same
  call succeeded from the daemon process — so it read as a flaky model, not
  a missing credential in one specific file among three no one file was
  authoritative over.
- **Three-env-file sprawl, no single source of truth**: `cos.env`
  (`~/.config/cos.env`, sourced by every `cos_*.sh` cron script),
  `datacored.env` (`/etc/datacored.env`, a systemd `EnvironmentFile` for
  `datacored` only), and `hermes.env` (`~/.hermes/.env`, hermes chat's own
  env). Each is written independently by a different setup step or
  refresher; nothing previously asserted "the credential a consumer needs
  is present in the file that consumer actually reads" — the same failure
  genre DIP-0035 names for job outputs (assert the real thing, not a proxy
  for it), applied here to configuration instead of artifacts.
- **A fourth, previously undocumented collision, found by the real audit at
  this DIP's own Phase 3 close**: `job_verify.py --machine mac --doctor`,
  run for real against this DIP's own canonical path, found that
  `~/.datacore/env` was **already occupied on the Mac** — not by drift
  between files, but by a pre-existing *directory* of per-service
  credential files (an older, different convention: one file per external
  service, e.g. a coinglass credentials file and a hyperliquid credentials
  file, under a directory of that name) rather than a single flat file.
  `config_plane.load()` has no guard against its target being a directory,
  so the literal `--doctor` CLI invocation crashed (a caught, clean, exit-1
  failure — never a raw traceback — but mislabeled as a manifest error by
  `job_verify.py`'s current exception handling, since it wraps the whole
  `doctor()` call in one `except OSError` clause). See Open Questions.

### Use cases

1. **One canonical place per machine** — a script or a human asks "is `FOO`
   set" by reading exactly one file, never by first having to know which of
   three sync targets its particular consumer happens to source.
2. **A mechanical migration checklist** — `doctor()` diffs `required_env`
   (sourced from the job manifest, DIP-0035) against canonical and
   enumerates every legacy-only variable per source — the literal input
   Phase 6's `cos-server-setup.sh` migration consumes, rather than a human
   re-deriving "which vars live where" from memory or by diffing three
   files by hand.
3. **Conflict detection before consolidation** — a variable present in both
   a legacy source and canonical with a *different* value is flagged (name
   + source only, never the value) — catching the "which one is actually
   current" question a manual three-way merge would otherwise answer
   silently, and possibly wrong.
4. **Secrets-safe auditing, by construction and by test** — the entire audit
   surface (`DoctorReport`, its `table`, `--doctor`'s stdout) never carries
   a value, so it is safe to run, log, and paste into a public report or
   DIP. The worked example below is exactly that: a real audit result with
   zero secret values, verified before being pasted in.

## Specification

### Canonical path

`~/.datacore/env` (`config_plane.CANONICAL_PATH`) — **one flat file per
machine**, not one file per service and not one file per consuming process.
Recommended `chmod 0600`; `check_permissions()` warns (never blocks) when
looser (`mode & 0o077 != 0`).

### Loader semantics (`config_plane.load()`)

- **Pure**: never reads or writes `os.environ`; merging the returned dict
  with the process environment, and deciding precedence, is the caller's
  job. Missing file → `{}` (not an error — an unconfigured machine is a
  normal state, not a fault).
- `KEY=VALUE`, one per line; leading `export ` tolerated and discarded;
  split on the **first** `=` only (values may themselves contain `=`); the
  key must match `[A-Za-z_][A-Za-z0-9_]*`; one layer of matching
  (`'`/`"`) surrounding quotes is stripped; an inline `#` is **not** a
  comment marker (kept as part of the value — env files don't reliably
  support inline comments, so no guess is made).
- Malformed lines are never raised one at a time: every malformed line in
  the whole file is collected into a single `ConfigError` naming each
  line's 1-based number and reason, so a caller sees the full picture in
  one pass.
- `check_permissions(path) -> list[str]`: loose-permission warnings, empty
  list when clean or the file is absent.

### Doctor semantics (`config_plane.doctor()`)

`doctor(machine, manifest_path=None, canonical_path=None,
legacy_sources=None) -> DoctorReport(missing, conflicts, legacy_only,
table)`:

- **`missing`**: union of `required_env` across `machine`'s jobs in the
  manifest (DIP-0035), minus canonical's keys — sorted.
- **`conflicts`**: `(var, source, "differs from canonical")` for every key
  present in *both* canonical and a legacy source whose values differ —
  sorted; the differing values are compared internally and then discarded,
  never carried into the result.
- **`legacy_only`**: per legacy source, the sorted variable names present
  there and absent from canonical.
- **`table`**: a markdown rendering of all four sections (missing /
  conflicts / legacy-only / unparseable), each rendering `(none)` when
  empty.
- A legacy source file that doesn't exist is skipped silently (nothing to
  migrate from it). A legacy source that exists but fails to parse is
  reported as a table finding ("unparseable legacy sources") — never a
  crash, and never a leaked fragment of the malformed line (see Security
  Considerations).
- `ManifestError`/`OSError` raised while loading the *manifest* propagate —
  the manifest is validated infrastructure, and a missing/invalid manifest
  means `doctor()` has nothing to audit `required_env` against.

### SECRETS RULE (binding, test-pinned)

Every `DoctorReport` field carries variable **names** and source **names**
only — never a value, a value length, or a value prefix. This is enforced
as a property, not a convention: `test_config_plane.py` plants a
distinctive secret string inside a **malformed** legacy line specifically
to exercise the unparseable-source code path (not just the happy path,
where redaction is easy), and pins that the secret substring appears
**nowhere** — not in the report, its `table`, nor its `repr`.

### `--doctor` CLI (`job_verify.py --doctor`)

Adds `--doctor` to `job_verify.py`: instead of running artifact checks, it
calls `doctor(args.machine, manifest_path=args.manifest or the default
manifest path)` and prints `report.table` to stdout. Exit code is **0
always** — doctor mode is informational, not a pass/fail gate — **except**
a manifest that fails to load (`ManifestError`/the manifest-load `OSError`
path), which still exits 1 with a clean stderr message, never a traceback,
matching the artifact-check path's existing discipline. `--alert`,
`--no-emit`, and `--space` are accepted (so one uniform flag set works
across both modes of the CLI) but are irrelevant in doctor mode: no ledger
event is written, no alert is dispatched.

## Rationale

**Why one flat file instead of one file per service?** `doctor()`'s
migration-checklist use case only works if there is exactly one
convergence target; a directory of per-service files — the very pattern
this DIP's own real-machine audit found already occupying the canonical
path (see Motivation, Open Questions) — reintroduces the "which file does
this consumer actually read" ambiguity this DIP exists to remove, just at
finer grain.

**Why does `doctor()` read `required_env` from the job manifest rather than
declaring its own list?** DIP-0035 already gives every job a declared
`required_env`; duplicating that list in a second, config-plane-specific
manifest would recreate the exact two-sources-of-truth drift this DIP is
designed to close elsewhere.

**Why report-only — why doesn't `doctor()` ever write canonical from
legacy?** An automatic three-way merge that guesses which of several
conflicting values is "the real one" is exactly the kind of silent,
unverified assumption that produced `ENG-2026-0728-001`. `doctor()`
surfaces the conflict for a human (or the Phase 6 migration script) to
resolve deliberately, once — it never encodes a guess.

### Alternatives considered

- **Auto-migrate canonical from legacy on `doctor()` run** — rejected; see
  Rationale (silent-merge risk is the exact failure mode this DIP exists to
  close, not one to reintroduce in the migration tool itself).
- **Keep the three legacy files, add a script that cross-checks them
  pairwise** — rejected; pairwise cross-checks are `O(n²)` in the number of
  sources and still leave no single file a new consumer can simply point
  at; every additional legacy source (as the real audit found a fourth)
  makes this worse, not better.
- **Store canonical config in the event ledger (DIP-0034) as `config.set`
  events** — rejected for this DIP; env values are read synchronously by
  shell scripts and cron at process-start time, before any ledger tooling
  is guaranteed available, and a value-bearing event type would sit outside
  the ledger's current "safe to log, sync, and paste" assumptions (the
  SECRETS RULE above). Revisit only if a signed, access-controlled event
  store becomes an actual requirement.

## Backwards Compatibility

Additive. No legacy file (`cos.env`, `datacored.env`, `hermes.env`) is
deleted, modified, or migrated by this DIP — `doctor()` only *reads* them
(never writes) to compute a report. A machine with no `~/.datacore/env` yet
behaves exactly as before: `load()` returns `{}` and every job keeps
reading whatever it reads today; `doctor()` simply reports every
`required_env` var as "missing" until migration happens. Migrating
variables onto the canonical file, and retiring the legacy files, is
explicitly Phase 6 (`cos-server-setup.sh`) work — not this DIP's.

## Security Considerations

- **Public-repo constraint.** Both `~/Data` and the dips repo are
  public/public-adjacent. This DIP's own content, `config_plane.py`'s test
  suite, and the worked example below all enforce that no secret value —
  full, partial, or length-implying — ever appears in a `doctor()` report,
  its `table`, or a `--doctor` stdout dump. Names only, by construction and
  by test.
- **Permission hygiene.** `check_permissions()` warns (the `0o077` mask) on
  a canonical file looser than `0600`, since it may hold every credential a
  machine's scheduled jobs need. It warns, never blocks — matching the
  "audit, don't gate" posture of `doctor()` itself.
- **Malformed-line redaction is a specifically tested path, not just the
  happy path.** A `ConfigError`'s message embeds the raw offending line
  verbatim (needed for a human fixing *that* file directly), so
  `doctor()`'s `except ConfigError:` around a legacy `load()` call is
  deliberately **unbound** (no `as e`) — binding and stringifying it into
  the report would leak exactly the secret fragment a malformed line is
  likely to contain. `test_doctor_malformed_legacy_line_never_leaks_fragment_into_report`
  pins this regression directly.

## Implementation

### Reference Implementation

`.datacore/lib/config_plane.py` (`load`, `check_permissions`, `doctor`,
`DoctorReport`) + the `--doctor` flag on `.datacore/lib/job_verify.py`,
tested by `.datacore/lib/tests/test_config_plane.py` (64 tests) and
`.datacore/lib/tests/test_job_verify.py` (22 tests, 5 of them `--doctor`-
specific). 432 tests passing at HEAD of `feat/datacore-v2` (432 total, up
from 427 immediately pre-Task-3.3), zero pre-existing or new failures.

Commit references: `feat(v2): job_verify --doctor` (branch
`feat/datacore-v2`); the `config_plane.py` module itself (`load`,
`check_permissions`, `doctor`) landed in prior commits on the same branch
(Tasks 3.1–3.2).

### Worked example (real Mac audit, Phase 3 close — secrets redacted per the binding rule above)

The literal CLI command specified for this audit, run for real:

```
$ python3 job_verify.py --machine mac --doctor
error: cannot read manifest <manifest path>: [Errno 21] Is a directory: '<canonical path>'
(exit 1)
```

No traceback — the failure was caught and reported cleanly, per this file's
existing discipline — but the message is **mislabeled**: the `OSError`
actually originates from `config_plane.load()` failing to `read_text()` a
*directory* at the canonical path (see Motivation), not from the manifest.
`job_verify.py`'s current `_run_doctor()` wraps the entire `doctor()` call
in one `except OSError` clause inherited from the artifact-check path's
existing pattern, where that clause genuinely only ever meant "manifest
file missing." This DIP does not fix that mislabeling (report-only per this
DIP's own audit step); it is recorded here as a real, load-bearing finding
— see Open Questions.

A second, diagnostic run of `config_plane.doctor()` directly (real legacy
sources, canonical path substituted with a nonexistent placeholder to
sidestep the directory collision above — equivalent to "canonical file not
yet created," the true pre-migration state) produced:

```
missing:      (none)   -- the manifest currently declares no required_env
                            for any mac job
conflicts:    (none)
legacy_only:  hermes.env: 21 variable names (~/.hermes/.env exists, 600
                            perms, 486 lines)
              cos.env, datacored.env: absent on this machine (cos.env is
                            evidently box-only — every cos_*.sh cron script
                            that sources it runs there, not on the Mac)
unparseable:  (none)
```

Zero secret values appear in either transcript above — verified before
inclusion here, per this DIP's own SECRETS RULE.

### Rollout Plan

**Phase 3 (this DIP): the loader + doctor audit.** `config_plane.py` +
`job_verify.py --doctor`, full test coverage including the
redaction-under-malformed-input regression. No legacy file is touched; no
machine is migrated.

**Phase 6 (DIP-0039, follow-on).** `cos-server-setup.sh` gains a v2 section
that (a) creates `~/.datacore/env` per machine from `doctor()`'s
`legacy_only`/`conflicts` findings, (b) gates each legacy generator's
retirement on `doctor()` reporting a clean (all-`(none)`) table for that
machine, (c) adds a `job_verify` cron/timer entry. Legacy files are retired
only after that migration — never by this DIP.

## Open Questions / Known Gaps

1. **Canonical-path collision, found by real use, not simulated.** On the
   Mac, `~/.datacore/env` was already a pre-existing *directory* (holding
   per-service credential files under an older convention) rather than
   available as a flat file. `config_plane.load()`/`doctor()` have no guard
   against the target path being a directory — `Path.read_text()` raises
   `IsADirectoryError` (an `OSError`), which propagates uncaught through
   `doctor()` and is then mislabeled by `job_verify.py --doctor`'s current
   exception handling as a manifest error. Resolving this (either a
   directory guard in `config_plane.load()`, or resolving the collision as
   part of Phase 6 migration, or both) is deferred — this DIP documents the
   gap rather than closing it, per the report-only discipline of the audit
   step that found it.
2. **`cos.env`'s legacy path is not universal across machines.** `doctor()`'s
   `LEGACY_SOURCES` constant hardcodes `~/.config/cos.env` for every
   machine; the real audit found no such file on the Mac at all (`cos.env`
   is evidently box-only, since only `cos_*.sh` cron scripts running there
   source it). Whether `LEGACY_SOURCES` should become per-machine, or
   whether "absent" is simply the correct and expected state for cos.env on
   non-box machines, is unresolved.
3. **The job manifest currently declares no `required_env` for any mac
   job**, so `doctor()`'s `missing` section was empty in the real audit not
   because migration is complete, but because nothing has been declared
   required yet. Whether mac jobs should gain `required_env` entries (and
   which variables) is manifest-authoring work under DIP-0035, not this
   DIP.
4. **Migration mechanics** (how a human or `cos-server-setup.sh` actually
   moves a legacy-only variable into canonical, handles a conflict, and
   confirms the source file's eventual retirement) are Phase 6/DIP-0039
   scope; this DIP defines the audit that feeds that process, not the
   process itself.

## References

- `ENG-2026-0728-001` — silent-degradation failure genre; item 1 is this
  DIP's originating incident (token-refresh sync missed `cos.env`).
- `ENG-2026-0725-016` — single-refresher-owner pattern for a rotating
  credential consumed by multiple independent processes; the underlying
  discipline `cos_token_refresh.py`'s incident (above) violated by writing
  to two of three consumer files instead of one canonical one.
- DIP-0034 — Event Ledger Substrate (this DIP has no event type of its own;
  referenced for the `feat/datacore-v2` rollout numbering and the
  public-repo / no-secrets discipline it establishes for the whole v2
  effort).
- DIP-0035 — Job Contracts + Unified Verifier (source of the
  `required_env` field `doctor()`'s `missing` section audits against, and
  of the "assert the real thing, not a proxy for it" verification
  discipline this DIP applies to configuration).
