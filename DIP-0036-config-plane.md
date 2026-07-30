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
| **Affects** | `.datacore/lib/config_plane.py`, `.datacore/lib/job_verify.py` (`--doctor` flag, `DATACORE_CANONICAL_ENV`), `~/.datacore/datacore.env` (canonical, per machine), legacy sources: `~/.config/cos.env`, `/etc/datacored.env`, `~/.hermes/.env` |
| **Specs** | `.datacore/lib/config_plane.py`, `.datacore/lib/job_verify.py` |
| **Agents** | any process reading a job's `required_env`; `job_verify.py --doctor` as the audit surface; `cos-server-setup.sh` (Phase 6 migration) |
| **Relates to** | DIP-0034 (Event Ledger Substrate), DIP-0035 (Job Contracts + Unified Verifier — `required_env` is this DIP's own audit input), `ENG-2026-0728-001` (silent-degradation failure genre, item 1: token-refresh sync gap), `ENG-2026-0725-016` (single-refresher-owner pattern for rotating credentials) |

## Summary

Introduces a single canonical per-machine env file (`~/.datacore/datacore.env`)
as the one place process configuration is read from, replacing the ambiguous
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

**Amended same-day (2026-07-30)**: the canonical filename is
`datacore.env`, not the originally-drafted bare `env` — see Amendment,
below. The real-machine audit that this DIP's own Phase 3 close performed
found `~/.datacore/env` already occupied by a pre-existing directory; the
amendment resolves that collision rather than merely documenting it.

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
  run for real against this DIP's originally-drafted canonical path
  (`~/.datacore/env`), found that path **already occupied on the Mac** —
  not by drift between files, but by a pre-existing *directory* of
  per-service credential files (an older, different convention: one file
  per external service, under a directory of that name) rather than a
  single flat file. `config_plane.load()` had no guard against its target
  being a directory, so the literal `--doctor` CLI invocation crashed (a
  caught, clean, exit-1 failure — never a raw traceback — but mislabeled as
  a manifest error by `job_verify.py`'s then-current exception handling,
  since it wrapped the whole `doctor()` call in one `except OSError`
  clause). **Resolved same-day** by the Amendment below, not merely
  documented — see Amendment and Open Questions.

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

## Amendment (2026-07-30): canonical path moves, defense in depth

Controller adjudication of the Phase 3 close audit's directory-collision
finding (Motivation, above): **the canonical path moves, rather than the
finding being merely documented for later.** Two changes, deliberately
redundant with each other:

1. **`CANONICAL_PATH` becomes `~/.datacore/datacore.env`**, not the
   originally-drafted bare `env`. Collision-free with the pre-existing
   `~/.datacore/env` directory found on the real Mac; the filename is also
   more self-describing on its own merits (a directory listing of
   `~/.datacore/` now shows `datacore.env` unambiguously as *the* config
   file, rather than a bare `env` that reads as a generic/ambiguous name
   next to sibling directories like `keys/`, `state/`, `logs/`).
2. **`load()` and `check_permissions()` gain a non-file guard**,
   independent of the rename: if the target path exists but
   `not path.is_file()` (a directory, or anything else that isn't a
   regular file or a symlink to one), `load()` raises `ConfigError` with a
   clear, named message rather than letting `Path.read_text()`'s
   `IsADirectoryError` escape uncaught; `check_permissions()` returns an
   equivalent warning string. A symlink TO a regular file still passes
   (`Path.is_file()` follows symlinks) — the existing "canonical file is
   actually a symlink" convention some machines may use keeps working.
   This is deliberately defensive, not just a fix for the one collision
   found: it protects against *any* future path collision, on any
   machine, not only the specific `~/.datacore/env` directory this audit
   happened to find.

A related, adjacent fix in `job_verify.py --doctor` (not `config_plane.py`
itself): an `OSError`/`ConfigError` raised from *inside* `doctor()` — a
canonical or legacy env-file problem — is no longer mislabeled as a
manifest error. It is reported as its own, correctly-named failure (see
`--doctor` CLI section, below); `ManifestError` keeps its original,
still-correct label. A test-only `DATACORE_CANONICAL_ENV` environment
variable, read directly by `job_verify.py` (the CLI layer, not
`config_plane`'s pure functions — see `--doctor` CLI section), lets this
whole path be exercised and diagnosed without touching any real machine's
canonical file.

**Why rename AND add a guard, rather than just one?** The rename alone
fixes today's specific collision but leaves `load()`/`check_permissions()`
exposed to the *next* stray directory (or file-vs-symlink surprise) on some
other machine; the guard alone would have correctly turned today's crash
into a clean, named `ConfigError` without curing the awkwardness of a
canonical path a legacy convention already had a real, differently-shaped
use for. Doing both is cheap and each closes a distinct failure mode.

## Specification

### Canonical path

`~/.datacore/datacore.env` (`config_plane.CANONICAL_PATH`) — **one flat
file per machine**, not one file per service and not one file per
consuming process. Recommended `chmod 0600`; `check_permissions()` warns
(never blocks) when looser (`mode & 0o077 != 0`), and warns distinctly
(never silently passes) when the path exists but is not a regular file —
see Amendment, above.

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
- **Non-file guard** (Amendment, above): if the path exists but is not a
  regular file (e.g. a directory), `load()` raises `ConfigError` naming the
  path — never an uncaught `OSError`. A symlink to a regular file still
  passes.
- `check_permissions(path) -> list[str]`: loose-permission warnings, empty
  list when clean or the file is absent; the same non-file case returns a
  distinct warning string rather than either silently passing or raising.

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
  `ConfigError` from the non-file guard (Amendment, above), raised while
  loading the *canonical* path, also propagates uncaught — `doctor()`
  itself does not catch it (a caller decides how to report it; see the
  `--doctor` CLI section for `job_verify.py`'s answer). A legacy source
  hitting the same guard is different: doctor()'s per-source loop already
  catches `ConfigError` and surfaces it as an "unparseable" finding, so a
  directory-shaped *legacy* source degrades gracefully with no code change
  needed for that case.

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
manifest path, canonical_path=<see DATACORE_CANONICAL_ENV below>)` and
prints `report.table` to stdout. Exit code is **0 always** — doctor mode is
informational, not a pass/fail gate — **except**:

- A manifest that fails to load (`ManifestError`) — exits 1 with
  `error: invalid manifest ...`, a clean stderr message, never a
  traceback, matching the artifact-check path's existing discipline.
- Any OTHER failure inside `doctor()` — an `OSError` or `ConfigError`
  raised while reading the canonical or a legacy env file (Amendment,
  above) — exits 1 with `doctor failed: <message>` instead. This is
  deliberately a **different** message than the manifest one: the two are
  unrelated failure sources, and conflating them (as the pre-amendment
  code did, see Motivation) makes the wrong file look like the problem.
  Still a clean stderr message, never a traceback, either way.

`--alert`, `--no-emit`, and `--space` are accepted (so one uniform flag set
works across both modes of the CLI) but are irrelevant in doctor mode: no
ledger event is written, no alert is dispatched.

**`DATACORE_CANONICAL_ENV`** (advanced, primarily for tests/diagnostics):
when set, `job_verify.py --doctor` reads it directly from `os.environ` and
passes it as `doctor()`'s `canonical_path`, overriding
`config_plane.CANONICAL_PATH`. Reading an env var here does not violate
`config_plane`'s "never reads `os.environ`" rule — that rule binds
`config_plane`'s own pure functions (`load`, `check_permissions`,
`doctor`), not `job_verify.py`'s CLI layer, which is free to read whatever
environment variables it wants before calling into `config_plane` with
plain arguments.

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
(never writes) to compute a report. A machine with no `~/.datacore/datacore.env`
yet behaves exactly as before: `load()` returns `{}` and every job keeps
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
`DoctorReport`, plus the Amendment's non-file guard) + the `--doctor` flag
and `DATACORE_CANONICAL_ENV` override on `.datacore/lib/job_verify.py`,
tested by `.datacore/lib/tests/test_config_plane.py` (69 tests) and
`.datacore/lib/tests/test_job_verify.py` (24 tests, 7 of them `--doctor`-
specific). 439 tests passing at HEAD of `feat/datacore-v2` (439 total, up
from 427 immediately pre-Task-3.3: +5 for the original `--doctor` flag,
+7 for the Amendment's directory-collision fix round), zero pre-existing
or new failures.

Commit references: `feat(v2): job_verify --doctor` (the original `--doctor`
flag) and `fix(v2): canonical env path moves to datacore.env, non-file
guards` (this Amendment) — both branch `feat/datacore-v2`; the
`config_plane.py` module itself (`load`, `check_permissions`, `doctor`)
landed in prior commits on the same branch (Tasks 3.1–3.2).

### Worked example (real Mac audit, Phase 3 close, re-run after the Amendment — secrets redacted/verified per the binding rule above)

**Before the Amendment**, the literal CLI command specified for this audit
crashed when run for real:

```
$ python3 job_verify.py --machine mac --doctor
error: cannot read manifest <manifest path>: [Errno 21] Is a directory: '<canonical path>'
(exit 1)
```

No traceback — the failure was caught and reported cleanly — but the
message was **mislabeled**: the `OSError` actually originated from
`config_plane.load()` failing to `read_text()` a *directory* at the
canonical path (see Motivation), not from the manifest. This is the exact
finding that produced the Amendment above.

**After the Amendment** (canonical path moved to `datacore.env`; the
non-file guard and corrected error labeling both live), the same literal
command was re-run for real, unmodified, no workaround needed:

```
$ python3 job_verify.py --machine mac --doctor
# Config Doctor -- machine: mac
Canonical: ~/.datacore/datacore.env

## Missing (required by manifest jobs, absent from canonical)

(none)

## Conflicts (legacy value differs from canonical)

(none)

## Legacy-only (present in a legacy source, absent from canonical)

### hermes.env
- BROWSERBASE_ADVANCED_STEALTH
- BROWSERBASE_PROXIES
- BROWSER_INACTIVITY_TIMEOUT
- BROWSER_SESSION_TIMEOUT
- DISCORD_BOT_TOKEN
- ELEVENLABS_API_KEY
- EXA_API_KEY
- HERMES_SPOTIFY_CLIENT_ID
- IMAGE_TOOLS_DEBUG
- MOA_TOOLS_DEBUG
- OPENROUTER_API_KEY
- TELEGRAM_ALLOWED_USERS
- TELEGRAM_BOT_TOKEN
- TELEGRAM_HOME_CHANNEL
- TELEGRAM_HOME_CHANNEL_THREAD_ID
- TERMINAL_ENV
- TERMINAL_LIFETIME_SECONDS
- TERMINAL_MODAL_IMAGE
- TERMINAL_TIMEOUT
- VISION_TOOLS_DEBUG
- WEB_TOOLS_DEBUG

## Unparseable legacy sources

(none)

(exit 0)
```

`~/.datacore/datacore.env` does not exist yet on this Mac (migration is
Phase 6 work, not this DIP's), so `load()` returns `{}` and everything the
21 `hermes.env` variables represent shows up as `legacy_only` rather than
`missing` (the manifest currently declares no `required_env` for either
mac job, `mac-agent-stream-rsync`/`mac-lens-sync` — that is why `missing`
is `(none)`, not evidence migration is complete). `cos.env` and
`datacored.env` are both absent on this machine — `cos.env` is evidently
box-only, since only `cos_*.sh` cron scripts running there source it.
Zero secret values appear anywhere above — verified before inclusion here,
per this DIP's own SECRETS RULE (home directory redacted to `~` for the
public-repo path-hygiene convention; nothing else altered).

### Rollout Plan

**Phase 3 (this DIP): the loader + doctor audit.** `config_plane.py` +
`job_verify.py --doctor`, full test coverage including the
redaction-under-malformed-input regression. No legacy file is touched; no
machine is migrated.

**Phase 6 (DIP-0039, follow-on).** `cos-server-setup.sh` gains a v2 section
that (a) creates `~/.datacore/datacore.env` per machine from `doctor()`'s
`legacy_only`/`conflicts` findings, (b) gates each legacy generator's
retirement on `doctor()` reporting a clean (all-`(none)`) table for that
machine, (c) adds a `job_verify` cron/timer entry. Legacy files are retired
only after that migration — never by this DIP.

## Open Questions / Known Gaps

1. ~~**Canonical-path collision, found by real use, not simulated.**~~
   **RESOLVED same-day by the Amendment, above.** On the Mac,
   `~/.datacore/env` was already a pre-existing *directory* (holding
   per-service credential files under an older convention) rather than
   available as a flat file, so the pre-amendment `config_plane.load()`/
   `doctor()` had no guard against the target path being a directory and
   the literal `--doctor` invocation crashed (cleanly, but mislabeled as a
   manifest error). Fixed two ways: the canonical path moved to
   `~/.datacore/datacore.env` (collision-free with the pre-existing
   directory), and `load()`/`check_permissions()` gained a non-file guard
   (defensive against any *future* collision, not just this one). The
   real audit was re-run after the fix and now succeeds — see the Worked
   example, above. Left here, struck through rather than deleted, so the
   DIP's history shows what was actually found and how it was actually
   closed, not just the end state.
2. **`cos.env`'s legacy path is not universal across machines.** `doctor()`'s
   `LEGACY_SOURCES` constant hardcodes `~/.config/cos.env` for every
   machine; the real audit found no such file on the Mac at all (`cos.env`
   is evidently box-only, since only `cos_*.sh` cron scripts running there
   source it). Whether `LEGACY_SOURCES` should become per-machine, or
   whether "absent" is simply the correct and expected state for cos.env on
   non-box machines, is unresolved. **Still open** — the Amendment did not
   touch `LEGACY_SOURCES`.
3. **The job manifest currently declares no `required_env` for any mac
   job**, so `doctor()`'s `missing` section was empty in the real audit not
   because migration is complete, but because nothing has been declared
   required yet. Whether mac jobs should gain `required_env` entries (and
   which variables) is manifest-authoring work under DIP-0035, not this
   DIP. **Still open.**
4. **Migration mechanics** (how a human or `cos-server-setup.sh` actually
   moves a legacy-only variable into canonical, handles a conflict, and
   confirms the source file's eventual retirement) are Phase 6/DIP-0039
   scope; this DIP defines the audit that feeds that process, not the
   process itself. **Still open.**

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
