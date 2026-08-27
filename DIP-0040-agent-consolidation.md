# DIP-0040: Agent Consolidation

| Field | Value |
|-------|-------|
| **DIP** | 0040 |
| **Title** | Agent Consolidation |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Implemented |
| **Created** | 2026-07-30 |
| **Updated** | 2026-08-27 |
| **Tags** | `agents`, `registry`, `lifecycle`, `gc`, `personas-as-data`, `datacore-v2` |
| **Affects** | `.datacore/lib/registry_gc.py`, `.datacore/lib/tests/test_registry_gc.py`, `.datacore/registry/agents.yaml`, `.datacore/registry/archive/agents-deprecated.yaml`, `.datacore/registry/evaluators.yaml`, `.datacore/4-archive/agents/` (archive destination — corrected; see "Correction: archive destination was harness-visible" in Implementation), `.datacore/lib/agents/evaluator.md`, `.datacore/modules/nightshift/module.yaml` (deploy-side, not in this repo) |
| **Specs** | `.datacore/lib/registry_gc.py`, `.datacore/registry/evaluators.yaml` |
| **Agents** | `agent-registry-auditor`, `context-maintainer`, any agent spawned via the registry (`ai-task-executor`, `nightshift-orchestrator`) |
| **Depends** | [DIP-0016](DIP-0016-agent-registry.md) (schema and both top-level sections this DIP's tooling operates on) |
| **Relates to** | DIP-0016 (Agent Registry & Discoverability — the schema and both top-level sections this DIP's tooling operates on), DIP-0021 (origin of the `deprecated`/`superseded_by` convention adopted here as canonical; see "Proposed Amendment to DIP-0016" below), DIP-0011 (Nightshift Module — its Implementation Status table documents the 20 `evaluator-*.md` files this DIP archives), DIP-0022 (Module Specification — `module_agents:` ownership and the re-population hazard documented in Integration) |

> **Ratification note (2026-08-27).** Status moved `Draft` → `Implemented` on the
> owner's instruction. **No human review was performed on this DIP.** It is recorded
> here rather than left implicit, because the governance rule in `CLAUDE.base.md` is
> that `Implemented`/`Accepted` require owner ratification — this satisfies that rule
> by owner instruction alone, not by review.
>
> `Implemented` here means the work this DIP specifies has landed. It does **not**
> mean every follow-up named in the body is closed; several of these DIPs explicitly
> record outstanding gates as follow-up work, and those remain open. Read the
> Implementation/Rollout sections for the per-DIP position rather than inferring it
> from this status field.

## Summary

Datacore's agent registry (`.datacore/registry/agents.yaml`, DIP-0016 schema)
accumulated entries faster than it retired them: by the time this DIP's work
started, the registry carried 138 entries across its two top-level sections
(`agents:` core/built-in, `module_agents:` module-contributed) — 41 in
`agents:`, 97 in `module_agents:` — of which 28 were already marked
deprecated (by `status: deprecated` or a `[DEPRECATED]` marker) but still
physically present and still visible to anything that lists the registry.
This DIP introduces `registry_gc.py`, a lifecycle-enforcement tool that
archives deprecated entries out of the live registry (with their definition
files) into a dedicated archive directory + file, and records the first
consolidation applied through it: 22 `evaluator-*` personas collapsed into
one parameterized `evaluator` agent plus a data roster
(`registry/evaluators.yaml`). It also states, honestly, that the plan's
original "≤60 active agents" aspiration is **not** reached by this pass alone
— the real post-cleanup active count is 110 — and names the next
consolidation families as follow-up work, not as done.

## Agent Context

This section helps agents understand when and how to apply this DIP.

### When to Reference This DIP

**Always reference when:**
- Adding, removing, or deprecating an entry in `.datacore/registry/agents.yaml` (either the `agents:` or `module_agents:` section)
- Running `registry_gc.py` (deprecate → archive lifecycle transitions) or `registry_validate.py` (schema/orphan validation) against the live registry
- Consolidating a family of near-duplicate agents into one parameterized agent plus a data roster (the "personas-as-data" pattern this DIP establishes with the evaluator family)
- Installing, reinstalling, or updating a module whose `module.yaml provides.agents:` list could re-populate an already-archived `module_agents:` entry (see DIP-0022 relationship in Integration)
- Deciding which deprecation marker to write on a new entry (`deprecated: true` + `superseded_by` is canonical; see "Proposed Amendment to DIP-0016")

### Quick Reference for Agents

| Question | Answer |
|----------|--------|
| How do I check registry drift (missing sources, unregistered files)? | `python3 .datacore/lib/registry_validate.py` — report-only; also runs automatically in nightshift Phase 9.5 |
| How do I archive deprecated entries? | `python3 .datacore/lib/registry_gc.py --apply` — on-demand only, not scheduled |
| Which deprecation marker should a *new* entry use? | `deprecated: true` + `superseded_by: <agent>` (canonical, per DIP-0021). `status: deprecated` and a `[DEPRECATED]` description marker are accepted legacy aliases; tooling must keep recognizing all three |
| Is `evaluators.yaml` a second agent registry? | No — it is parameter data for the single `evaluator` agent (though that agent currently has **no** `agents.yaml` entry of its own; see Specification, "Personas-as-data" and Open Questions) |
| Where do archived agent definitions go? | Files: `.datacore/4-archive/agents/` — **outside** `.datacore/agents/**`, because the harness scans that tree recursively (`.claude` symlinks to `.datacore`). Metadata: `.datacore/registry/archive/agents-deprecated.yaml` (non-authoritative historical record, not a second registry) |
| Do `registry_gc.py` and `registry_validate.py` conflict? | Not in production today (nightshift runs the latter report-only), but their overlap on orphan handling is undeclared — see Specification and Open Questions |

### Related Agents

| Agent | Uses This DIP For |
|-------|-------------------|
| `agent-registry-auditor` | Registry compliance auditing (DIP-0016 §13); should treat `deprecated`/`orphaned`/`archived` per this DIP's lifecycle states rather than as generic non-compliance findings |
| `context-maintainer` | Syncing module-registered agents into `module_agents:` (DIP-0016 §3.3); must account for the re-population hazard this DIP documents — reinstalling a module can silently resurrect an archived entry |
| `nightshift-orchestrator` | Invokes `registry_validate.py` at nightshift Phase 9.5 (report-only registry drift check) |
| `ai-task-executor` | Routes `:AI:` tasks via `agents.yaml`; must not resolve archived entries, which is why this DIP requires physical relocation, not just a status flag |

### Integration Points

- [DIP-0016](DIP-0016-agent-registry.md) — this DIP's lifecycle/archival model amends DIP-0016's schema; see "Proposed Amendment to DIP-0016" below, drafted ready to fold in on ratification
- [DIP-0021](DIP-0021-search-research-architecture.md) — origin of the `deprecated`/`superseded_by` canonical convention this DIP adopts and generalizes with an archival step
- [DIP-0011](DIP-0011-nightshift-module.md) — Implementation Status table documents the 20 `evaluator-*.md` files this DIP's consolidation archives; needs a follow-up correction on ratification
- [DIP-0022](DIP-0022-module-specification.md) — `module_agents:` is populated by `datacore.modules.register` from a module's `module.yaml provides.agents:` list; this DIP documents the resulting re-population hazard for archival

## Motivation

### The registry is meta-tooling managing its own sprawl

DIP-0016 gave Datacore a machine-readable agent registry so agents could be
discovered, routed to, and reasoned about without hardcoding. What it didn't
give the registry was a way to retire an entry. The result, ~7 months later:
a **153-entry registry** was the figure carried in this plan's Phase 7 map
line ("153 → ≤60 agents") when this phase was scoped — a rough
plan-time estimate, not a verified count. The verified actual count, read
directly from the real file at the start of this task (see
`task-7.1-report.md`, `task-7.2-report.md`), is **138** (41 `agents:` + 97
`module_agents:`), of which **28** were already deprecated-but-listed: one
core-section entry (`youtube-transcriber`, correctly classified from the
start) and 27 module-section entries — invisible to the registry's own
tooling until this DIP's Task 7.1 extended `registry_gc.py` to read
`module_agents:` at all (see "Controller Scope Amendment" in
`registry_gc.py`'s module docstring). The discrepancy between the plan's
placeholder ("153") and the verified count ("138") is recorded here rather
than silently reconciled, matching this v2 effort's own convention of
correcting placeholder numbers against verified reality instead of
retrofitting the narrative to the estimate (the same thing happened to
Task 7.2's "20 evaluators expected" → 22 actual, and to this DIP's own "≤60
target" → 110 actual, below).

This is a recognizable genre, not a one-off: **meta-tooling built to manage
a system's own sprawl, applied to the agent roster itself.** Datacore
already has this pattern for knowledge (Zettelkasten atomic notes + archival
paths), for tasks (GTD's own inbox → clarify → archive lifecycle), and now,
via this DIP, for agents: a registry entry can be `deprecated`, and a
mechanical tool — not manual file surgery — moves it to an archive on a
predictable schedule. This is the Capture-Process-Archive primitive named
in [DIP-0026](DIP-0026-architectural-primitives.md) §1, applied here to
agents rather than knowledge or tasks — named explicitly rather than
re-derived, per DIP-0026's own stated purpose.

### Deprecated-but-listed is worse than just "large"

A registry entry marked `status: deprecated` that is still physically
present in `agents.yaml` is not a passive cost — it actively misleads:

- Anything that lists registry entries by section (a ToolSearch-style
  listing, `datacore.agent_list`, a human `grep`) surfaces the deprecated
  entry alongside live ones unless every call site remembers to filter on
  `status`. 28 such entries existed in the real registry before this DIP.
- A deprecated entry's `source:` definition file usually still sits in its
  original, "live" directory (`.datacore/agents/`, or a module's `agents/`
  dir) — indistinguishable at a glance from an active agent definition.
- Nothing enforces that a deprecated entry's replacement (`superseded_by`)
  actually exists, or that the deprecated entry is ever physically removed —
  deprecation was a label, not a lifecycle transition.

### Use cases enabled

1. **Mechanical registry hygiene** — `registry_gc.py --check` / `--apply`
   turns "archive the deprecated agents" from a manual, error-prone file
   operation into a deterministic, idempotent, crash-safe pass over the
   real registry.
2. **Personas-as-data instead of personas-as-files** — a family of agents
   that differ only in *evaluation lens*, not *mechanism* (the 22
   `evaluator-*` agents), collapses into one mechanism (`evaluator.md`) plus
   a data roster (`evaluators.yaml`) that's trivial to extend (add a row)
   instead of expensive to extend (write a new agent file, register it,
   wire it into dispatch).
3. **Honest progress tracking against an aspiration** — this DIP's own
   "Achieved vs Target" section states the real number next to the plan's
   number instead of quietly redefining the target.

## Specification

### Registry Entry Lifecycle

> Named "Registry Entry Lifecycle" to disambiguate from DIP-0016 §16's
> "Agent Execution Lifecycle" (pre/post/validate/error hooks around a
> single agent *run*). Both live under the "agent registry" domain but
> govern different things: DIP-0016 §16 governs one execution; this
> section governs the standing state of one `agents.yaml` entry across
> its entire existence.

A registry entry (under either `agents:` or `module_agents:`) is in exactly
one of three lifecycle states at any time:

| State | How it's recognized | What it means |
|-------|---------------------|----------------|
| **active** | Neither deprecated nor orphaned (see below) | Live, listable, spawnable |
| **deprecated** | Canonical: `deprecated: true` (optionally with `superseded_by: <agent>`) — the convention [DIP-0021](DIP-0021-search-research-architecture.md) established (§"DIP-0016 Schema Extension") and that already applies to 5 live registry entries. Accepted legacy aliases, recognized equivalently: `status: deprecated` (case-insensitive), OR the literal string `[DEPRECATED]` in the entry's `name`/`description`. New deprecations SHOULD use the canonical fields; existing legacy-marked entries are not required to migrate. | Marked for retirement; still present in the live registry until a `gc --apply` run archives it |
| **orphaned** | Not deprecated, but its `source:` file is missing or empty, or the entry has no `source:` field at all | The registry references a definition file that doesn't exist on disk; almost always a stale entry from a moved/renamed/deleted file |

`deprecated` takes strict priority over `orphaned`: an entry that is both
(marked deprecated AND missing its source file) classifies as `deprecated`
only — `apply()` archives its metadata and simply has nothing to move.

A fourth, non-lifecycle category, **unregistered**, is report-only: a
`*.md` file under a scanned agent directory that no registry entry's
`source:` points at. This is never auto-fixed — registering an agent
requires semantic judgement (skills, triggers, spawn relationships) that is
`agent-registry-auditor`'s job, not a mechanical GC pass.

**Known implementation gap (documented here; fixed separately, not by this
DIP's text).** `registry_gc.py`'s classifier, as it ran for this DIP's real
consolidation, checks only `status: deprecated` and the literal
`[DEPRECATED]` marker — it does not yet recognize `deprecated: true`. The 5
live entries carrying DIP-0021's `deprecated: true` + `superseded_by`
convention are therefore currently invisible to `registry_gc.py --check` /
`--apply`: a `gc --apply` run today archives 0 of those 5. This table
states the *intended* canonical three-marker recognition; a companion code
change landing separately (on `feat/datacore-v2`, outside this DIP's scope)
brings the classifier in line with it. Until that lands, treat the
`deprecated` row above as the target state, not the current running
behavior for `deprecated: true` entries specifically.

**Source of truth.** `agents.yaml` (its live `agents:` and `module_agents:`
sections) is the sole registry of agents, per DIP-0016 §1 — this DIP does
not change that. `.datacore/registry/evaluators.yaml` is not a competing
registry; it is subordinate parameter data consumed by one registered
agent (comparable in kind to DIP-0021's `sources.yaml`), analogous to how
a config file is not itself a program. `.datacore/registry/archive/agents-deprecated.yaml`
is a non-authoritative historical record — provenance for what used to be
registered, not a place anything resolves an agent from. All three facts
are stated together, once, here, rather than left to be inferred from
scattered prose across this DIP.

### `registry_gc.py` semantics

Two-phase design, both operating identically across **both** top-level
sections (`agents:` and `module_agents:` — the registry's real shape per
DIP-0016, confirmed by Task 7.1's read against the live file):

- **`audit(registry_path, agents_dirs) -> GcReport`** — read-only.
  Classifies every entry in both sections into active / deprecated /
  orphaned, globs `agents_dirs` for unregistered `*.md` files, globs the
  registry directory for stray `*.bak*` files, and scans the raw file text
  for duplicate keys (see guards below). Never writes anything, at any
  entry point.
- **`apply(report, registry_path, archive_dir) -> list[str]`** — mutates,
  in a crash-safe order: (0) unconditional duplicate-key pre-flight abort,
  before any file is opened for writing; (1) each deprecated entry's
  `source:` file is moved into `archive_dir` — the corrected concrete
  value, per the final-review fix wave, is `.datacore/4-archive/agents/`
  (this DIP's own first real run used `.datacore/agents/_deprecated/`,
  which was later found harness-visible and superseded; see "Correction:
  archive destination was harness-visible" in Implementation) — (unless
  the shared-source guard below fires) and its metadata staged into an
  in-memory merge of
  `<registry_dir>/archive/agents-deprecated.yaml`, under that entry's *own*
  section key (an `agents:` entry archives under the archive file's
  `agents:` key, a `module_agents:` entry under its `module_agents:` key —
  never flattened together); (2) each orphaned entry is staged for removal
  with a plain-text comment note (never YAML data) recording what was
  removed and when; (3) the archive file is written to disk, atomically,
  **before** the live registry is touched — this is the crash-safety
  boundary: nothing is ever dropped from the live registry before its data
  is durably archived; (4) only then is the live registry rewritten,
  popping archived/removed entries from their own section, with the
  registry's leading comment/blank header block re-prepended verbatim; (5)
  stray `.bak*` files are deleted; (6) unregistered files are never touched.
  Returns `[]` immediately, touching nothing, when the report has nothing
  actionable — this is what makes re-running `--apply` after a clean
  `--apply` a true no-op (byte-identical tree).

**Why archival moves files, not just a status flag.** Harnesses that spawn
subagents — Claude Code's Task tool, nightshift's own dispatcher — discover
subagents by scanning agent directories directly (`.datacore/agents/*.md`,
`.datacore/modules/*/agents/*.md`), independent of `agents.yaml`'s
`status`/`deprecated` field. A file left in a scanned directory remains
fully spawnable no matter what the registry says about it; only removing
it from the scanned tree closes that hole, which is why step (1) above
physically relocates the definition file instead of relying on the
registry entry's removal alone.

**Correction — a subdirectory of the scanned tree is not "removed from the
scanned tree."** An earlier draft of this section cited
`registry_validate.py`'s own `AGENT_GLOBS` scan special-casing
`.datacore/agents/_deprecated/` and `.datacore/agents/_patterns/` as
skip-directories (`SKIP_PARTS = {'_deprecated', '_patterns'}`) as
corroboration that archiving into `.datacore/agents/_deprecated/` was
safe. That reasoning was wrong, and the mistake is instructive: `SKIP_PARTS`
is *Datacore's own registry loader* choosing not to look at that
subdirectory — it does not, and cannot, bind any other harness. `.claude`
is a symlink to `.datacore`, and Claude Code's Task tool scans
`.claude/agents/**` **recursively**, with no knowledge of
`registry_validate.py`'s skip-list. Because `.datacore/agents/_deprecated/`
is still a path *inside* `.datacore/agents/`, every file placed there
remained fully discoverable and spawnable by the harness the whole time —
this was verified directly (six deprecated defs — `conversation-processor`,
`gtd-process-inbox`, `gtd-research-processor`, `ingest-coordinator`,
`ingest-processor`, `research-link-processor` — sit in
`.datacore/agents/_deprecated/` on `main` today and load into every live
session) and is why the v2 final-review pass flagged it Critical and
relocated all archived defs to `.datacore/4-archive/agents/`, a path
outside `.datacore/agents/` entirely. An internal loader's skip-list is
never sufficient protection on its own: it only affects what *that one
tool* reports or ignores, not what a harness with independent,
recursive directory-scanning discovery will load.

### Guards (hardened across two post-review passes before this real run)

- **Shared-`source:` collision guard**: two entries — same section or
  across sections — can point `source:` at the same file. If one is
  deprecated and the other survives, `apply()` computes every surviving
  entry's resolved source path across *both* sections before touching any
  deprecated entry, and skips the physical file move (archiving only the
  metadata) whenever a deprecated entry's source collides with a
  survivor's, logging a `WARNING shared source retained` line instead of
  breaking the survivor.
- **Atomic writes**: every write to `registry.yaml` or
  `agents-deprecated.yaml` goes through a temp-file-in-the-same-directory +
  `os.replace`, so a crash mid-write can never leave a half-written file in
  the real path. The target's existing file mode is read and copied onto
  the temp file before the replace (mkstemp always creates `0600`; without
  this, every rewrite of a normally-`0644` tracked file would silently
  downgrade its permissions).
- **Header preservation**: the registry's (and the archive file's) leading
  comment/blank block is captured verbatim as text before the YAML
  load/dump round-trip and re-prepended verbatim on write — a plain PyYAML
  round-trip does not preserve comments, so without this the real registry's
  DIP-0016 documentation header would be silently dropped on the first
  `apply()` that actually rewrites the file. Comments living *inside* the
  document (between sections, between profile blocks) are **not**
  preserved by this mechanism — only the single leading block is; this is a
  documented, accepted formatting-normalization consequence of `registry_gc.py`
  using plain PyYAML instead of a comment-preserving library. **Correction**:
  an earlier draft of this DIP justified that choice by calling
  `ruamel.yaml` unavailable — that was false. `.datacore/lib/registry_validate.py`,
  in the same directory, wired into the same nightshift Phase 9.5 pass,
  already imports and uses `ruamel.yaml` successfully with full comment
  preservation (see "Relationship to `registry_validate.py`" below). The
  honest framing is that `registry_gc.py` was written without it — not
  that it couldn't be — and the two registry tools now use two different
  YAML libraries for the same file, which is itself part of the case for
  consolidating them (see Open Questions).
- **Duplicate-key pre-flight**: PyYAML's loader silently keeps only the
  LAST occurrence of a duplicate mapping key, at either the top level (e.g.
  two `agents:` blocks from a bad merge) or nested within one section (e.g.
  two `evaluator-critic:` entries under the same `module_agents:` block) —
  with no error, which can silently drop half a registry. A deliberately
  simple, non-YAML-aware raw line scan detects both shapes; `audit()`
  reports them (`GcReport.duplicate_keys`, which also gates `--check`'s
  exit code); `apply()` re-runs the same scan unconditionally, as its very
  first action, and raises before any file is opened for writing if
  anything is found — no partial apply against a corrupted registry is
  possible.
- **NOT a guard, and a real gap found during this DIP's own real run (see
  "Achieved vs Target" below)**: the archive-file destination path is
  computed from the *source file's basename only*
  (`archive_dir / Path(source).name`), with no check against files
  *already present* in `archive_dir` from a prior, unrelated archival pass.
  Two different agents that happen to share a basename (one already
  archived; a second, unrelated entry newly archived under this run) will
  collide at the destination, and `apply()`'s `shutil.move` silently
  overwrites the pre-existing file. This is distinct from the shared-source
  guard above (which is about the same *source* path referenced twice, not
  two different sources landing on the same *destination* basename) and is
  not yet closed by any of the three hardening passes that preceded this
  real run.

### Amendment: Gitignored-Source Guard (final-review wave, 2026-07-30)

A fifth guard, alongside the four above: before physically moving a
deprecated entry's `source:` def file, `apply()` now checks whether that
path is itself git-ignored in the repo rooted at `base_dir`
(`git -C <base_dir> check-ignore -q <source>`). `archive_dir` is a
*tracked* location — silently moving a gitignored file into it would
either vanish the file from the disk-tracking expectations its own
`.gitignore` entry encodes, or require force-adding it against the
repo's own stated intent, and a mechanical GC pass has no business
deciding that on its own. When the source is ignored, the physical move
is skipped exactly like the shared-source collision case — the entry is
still archived as metadata (so it no longer clutters the live registry),
`entry["source"]` is left pointing at the original, unmoved location, and
a `"[gc] WARNING gitignored source retained: <path> (archive entry
created, file left in place)"` line is added to the action log.

Determining "ignored" is deliberately best-effort: if `git` isn't
installed, `base_dir` isn't inside a git working tree, or the check
otherwise fails to run, the path is treated as **not** ignored and
`apply()` falls back to its normal archival move — this keeps every
pre-existing tmp_path test fixture (none of which are git repos)
behaving exactly as before this guard was added.

### Relationship to `registry_validate.py`

`.datacore/lib/registry_validate.py` already exists, predates this DIP, and
is wired into nightshift Phase 9.5 (`modules/nightshift/lib/run.py`,
alongside `structural_integrity.py`). It is **not** the case, contrary to
an earlier draft of this DIP, that `ruamel.yaml` is unavailable in this
codebase — `registry_validate.py` itself imports and uses it for
comment-preserving reads and writes.

The two tools are scoped differently but overlap in one place:

- **`registry_validate.py`** = schema/orphan *validation*. Its `--prune`
  mode removes registry entries whose `source:` file is missing — the same
  criterion this DIP calls **orphaned** — using `ruamel.yaml`. It runs in
  nightshift Phase 9.5 **without** `--prune` (report-only in the scheduled
  path; `--prune` is a manual, human-invoked call today). It also reports a
  `deprecated_registered` list, using a *third*, looser deprecation test:
  `entry.get('deprecated')` truthy (i.e. `deprecated: true`) OR the bare
  substring `'DEPRECATED'` anywhere in `description` — no `[DEPRECATED]`
  brackets required, and it does not check `status: deprecated` at all.
- **`registry_gc.py`** (this DIP) = full lifecycle *transitions*
  (deprecate → archive), covering both orphan removal and deprecated-entry
  archival, using plain PyYAML, on demand (`--check` / `--apply`, never
  scheduled).

Both tools can independently remove orphaned entries from the same live
`agents.yaml`, via independently atomic (but not mutually coordinated)
writes, and — per the "Known implementation gap" note above — currently
disagree on which markers count as `deprecated`. Nightshift's Phase 9.5
invocation runs `registry_validate.py` without `--prune` today, so the two
tools do not currently race in production; nothing prevents a future
change from adding `--prune` to that scheduled call, which would then run
alongside any manually-triggered `registry_gc.py --apply` with no declared
sequencing between them.

This is recorded as an Open Question (below), not resolved here: **merge
the two tools before either grows a third caller**, or explicitly declare
a single owner for orphan pruning and a single owner for deprecation
archival.

### Personas-as-data: the evaluator roster

The first (and, to date, only) consolidation actually carried out through
this tooling: 22 `evaluator-*` agents (`.datacore/modules/nightshift/agents/
evaluator-{archivist,aurelius,bezos,buffett,ceo,coo,critic,cto,data,
dijkstra,feynman,hemingway,kahneman,musk,orwell,picard,popper,socrates,
taleb,tufte,twain,user}.md`), each a full agent definition differing only in
*evaluation lens* (which figure/discipline's perspective to apply, which
domains/`:AI:` tags trigger it, whether it's a core "always-runs" evaluator
or a domain-specific one), collapsed into:

- **`.datacore/registry/evaluators.yaml`** — `{version: 1, evaluators:
  {<key>: {name, focus, domains, triggers, core}}}`, one row per persona,
  `focus` lifted verbatim from each source file's own description, `core:
  true` for the 6 personas whose own body text says "Core evaluator -
  always runs for every task" (archivist, ceo, coo, critic, cto, user),
  `false` for the other 16 ("Domain evaluator - invoked for ...").
- **`.datacore/lib/agents/evaluator.md`** — one parameterized agent
  definition: load the roster by a given `persona` key, adopt that row's
  name/focus as the evaluation lens, evaluate the given artifact, return
  the standard evaluator output contract.
- 22 registry entries under `module_agents:` marked `status: deprecated`
  (pure insertions — no entries moved, deleted, or reformatted at that
  step; the actual archival happened later, in this DIP's own real
  `--apply` run).

(A 23rd file matching the `evaluator-*` glob,
`evaluator-critic-optimizer.md`, is a prompt-tuning meta-agent — not an
evaluation-lens persona — and is deliberately out of scope for this
consolidation. It is not one of the 22 personas rostered above and was not
touched, to preempt a future maintainer assuming every `evaluator-*` file
is covered.)

**Known gap, not yet closed: the new `evaluator` agent itself has no
registry entry.** Verified directly against the live `agents.yaml`: there
is no `agents: evaluator:` entry and no `module_agents:` entry for
`.datacore/lib/agents/evaluator.md` — it exists on disk unregistered. This
is a real correctness problem, not a hypothetical: once
`registry_gc.py --apply` archives the 22 `evaluator-*` entries (as it has,
per Achieved vs Target), `agents.yaml` — DIP-0016's sole source of truth
for "what agents exist and are routable" — contains **zero** record of any
evaluator agent. Any dispatcher that finds `evaluator.md` afterward does so
by hardcoded knowledge of its path, which is precisely the
"hardcoded routing" pattern DIP-0016 exists to eliminate (§1). This DIP
does not close the gap in this pass — closing it means writing a fourth
deliverable (a proper `agents: evaluator:` entry with its own `triggers`,
`skills`, `source`, `reads`, per DIP-0016's schema) before, or as part of,
wiring the deploy-side dispatcher (Integration, Open Question 3). Until
then, evaluator dispatch is registry-bypassing, in direct tension with
DIP-0016 §1, and this DIP records that tension rather than papering over
it — see Open Questions.

## Achieved vs Target

**The plan's Phase 7 acceptance criterion — "agents.yaml ≤60 active
entries" — is NOT achieved by this DIP.** Stated plainly, with the real
numbers, because "close enough" framing would misrepresent what actually
happened:

| Metric | Plan target | Verified before this DIP's `--apply` | Verified after |
|---|---|---|---|
| Total registry entries (both sections) | — | 138 (41 `agents:` + 97 `module_agents:`) | 110 |
| Deprecated-but-listed | — | 28 (1 `agents:` + 27 `module_agents:`) | 0 |
| Active entries | ≤60 | 110 | **110** |
| Orphaned entries | — | 0 | 0 |
| Duplicate keys | — | 0 | 0 |

Active count did not change between "before" and "after" (110 both times) —
`--apply` only ever archives deprecated/orphaned entries, it never touches
active ones by design. What changed is that the registry went from carrying
138 total entries (110 active + 28 deprecated-but-listed) to carrying
exactly its 110 active entries, with the 28 formerly-deprecated ones now
living in `registry/archive/agents-deprecated.yaml` instead of the live
file. **Evaluator consolidation alone — the one consolidation this DIP
actually executes — cannot reach ≤60 active from 110 active.** It already
happened (22 evaluators → 1 parameterized agent + a 22-row data roster) and
is fully reflected in the "before" active count already being 110, not 132;
the ≤60 aspiration assumed further consolidation passes this DIP does not
perform.

### Remaining consolidation families (named as follow-up gates, not consolidated here)

Grouping the 110 post-`gc` active entries by naming/domain family surfaces
several more candidates for the same personas-as-data treatment applied to
the evaluators. Per this DIP's own scope (a lifecycle-enforcement tool +
one already-completed consolidation + an honest count), **none of these are
touched in this pass** — they are named so a follow-up DIP/task can pick
them up deliberately, not discovered by re-reading the registry from
scratch:

- **`gtd-*` family** (5 active, all core `agents:`):
  `gtd-inbox-coordinator`, `gtd-inbox-processor`, `gtd-content-writer`,
  `gtd-data-analyzer`, `gtd-project-manager` — task-type-routed dispatch
  variants of one underlying pattern (an `:AI:xxx:`-tagged task routed to a
  specialized processor), structurally similar to the pre-consolidation
  evaluator family.
- **`health-*` family** (4 active, `module_agents:`, `health` module):
  `health-data-processor`, `health-analyzer`, `health-research-tracker`,
  `health-advisor` — sequential pipeline stages (ingest → analyze → track →
  advise) over the same underlying data.
- **Research pipeline** (5 active, spanning both sections):
  `research-orchestrator`, `research-synthesizer` (`agents:`),
  `question-researcher`, `insights-researcher`, `podcast-creator`
  (`module_agents:`, `research` module) — a multi-stage research pipeline
  (discover → synthesize → answer questions → generate insights → produce
  a podcast) currently expressed as five separate agent files.
- **Megaphone pipeline** (5 active, `module_agents:`, `megaphone-websites`
  module): `prospect-researcher`, `demo-builder`, `offer-generator`,
  `outreach-sender`, `pipeline-manager` — a linear cold-outreach pipeline
  (research → demo → offer → send → track) with the same one-stage-per-file
  shape as the other three families above.

Two smaller families observed but not named as primary candidates (below
the "≥5 entries" bar used above, listed for completeness):
`forge-*` (5: analyst/generator/publisher/monitor/strategist — actually
ties the largest families above; included here rather than promoted
because Forge's stages are more heterogeneous in tool access than the
evaluator/gtd/health/research/megaphone families, needing a closer read
before assuming a clean persona-as-data collapse applies), `crm-*` (4:
relationship-scorer/interaction-extractor/entity-extractor/
contact-maintainer), `knowledge-*` (3: `knowledge-extractor` (`agents:`),
`knowledge-promoter`, `knowledge-linter` (`module_agents:`)).

If every family named above (gtd, health, research pipeline, megaphone
pipeline) collapsed to one parameterized agent each, active count would
drop by roughly 4+3+4+4 = 15, from 110 to ~95 — still well short of ≤60.
Reaching ≤60 active honestly requires either a much larger set of
consolidation passes than this DIP scoped, or a revision of the ≤60 target
itself; this DIP takes no position on which, beyond stating the gap.

## Integration

- **General hazard: `module_agents:` archival can be silently undone by
  module reinstallation.** Per [DIP-0022](DIP-0022-module-specification.md)
  §"module registration", `datacore.modules.register` populates
  `agents.yaml`'s `module_agents:` section **from** a module's
  `module.yaml provides.agents:` list. If `registry_gc.py` archives a
  `module_agents:` entry but the owning module's `module.yaml` still lists
  that agent under `provides.agents:`, a later `datacore.modules.register`
  run (module update, reinstall, or a fresh install elsewhere) will
  silently re-populate the archived entry back into the live registry —
  undoing the archival without `registry_gc.py` ever knowing it happened.
  This is a standing constraint for **every** `module_agents:`-owned
  family, not just the nightshift/evaluator case below: it applies equally
  to the `health-*`, research-pipeline, and `megaphone-websites` families
  this DIP names as follow-up candidates (Achieved vs Target). Consolidating
  any of them requires updating the owning module's `module.yaml` in the
  same change as running `registry_gc.py` — not as a separate, optional
  step.
- **Nightshift evaluator dispatch reads the roster, but only at the deploy
  side.** (The one concrete instance of the general hazard above.) `.datacore/modules/nightshift/module.yaml` — which enumerates all
  22 old `evaluator-*` names under `provides.agents:` — is gitignored (module
  dirs outside the tracked allowlist `gtd/outbox/research/voice-terminal`
  are not part of this repo at all) and was not touched by this DIP or its
  preceding tasks. Whatever process actually dispatches evaluator agents at
  runtime (nightshift's own code, deploy-side) still needs to be updated to
  read `registry/evaluators.yaml` and spawn the single parameterized
  `evaluator` agent per persona, instead of dispatching 22 hardcoded agent
  names — this DIP creates the data source; it does not wire the
  consumer. Flagged in Task 7.2's own report and carried forward here,
  unresolved.
- **`registry_gc.py`'s def-file moves are invisible to `git` for
  `module_agents:` entries whose source lives under a gitignored module
  directory** (e.g. the 22 evaluator personas, under
  `.datacore/modules/nightshift/agents/`, matched by the `.datacore/
  modules/*/` gitignore rule with no allowlist entry for `nightshift`).
  `shutil.move` still physically relocates the file on disk — from git's
  perspective, an untracked file simply vanishes from one path and a new
  untracked file appears at the (tracked) archive destination, needing an
  explicit `git add` to actually land in a commit. Entries whose source is
  under a *tracked* location (the plain `agents:` section's
  `.datacore/agents/`, and the `research` module's `agents/` dir, which
  IS allowlisted) show up as ordinary git renames instead.
- **CLAUDE.base.md's "100+ agents and 40+ commands registered" line is free
  prose, not a marker-delimited generated section.** The file has three
  `<!-- REGISTRY:xxx -->` markers (`modules`, `sources`, `infrastructure`),
  regenerated by `context_merge.py`; agent/command counts have no such
  marker and were, per this task's own constraint, left as a manual note
  rather than hand-edited: the true active count is now 110 (not "100+" in
  spirit, though the round number happens to still read as compatible),
  commands.yaml carries 18 entries (not "40+" — this prose line was
  already stale before this DIP and is flagged, not fixed, here).

## Compatibility

- **Additive to the registry schema.** `registry_gc.py` introduces no new
  required fields; `agents:`/`module_agents:` entries that carry none of
  the deprecation markers are simply classified `active` and untouched.
  Entries already using DIP-0021's `deprecated: true` + `superseded_by`
  continue to parse and display exactly as before — see "Known
  implementation gap" above for the one place this DIP's own tool does not
  yet fully honor that pre-existing convention.
- **`--apply` is idempotent.** A second run against a tree with nothing
  actionable returns `[]` and writes nothing — re-running it is always
  safe (Specification, "`registry_gc.py` semantics").
- **Behavior change for anything reading a deprecated entry from the live
  file.** Before this DIP, a deprecated entry stayed in `agents.yaml`
  indefinitely and any consumer reading it directly (rather than treating
  the deprecation marker as a stop signal) would keep finding it there.
  After a `gc --apply` run, that entry is gone from the live file and only
  present in `.datacore/registry/archive/agents-deprecated.yaml`. No
  consumer that depends on this is known to exist today (per Integration),
  but this is a real behavior change, not a purely cosmetic one.
- **Breaking for hardcoded paths to archived files.** Code that hardcodes
  a path to one of the 22 `evaluator-*.md` definition files (their old
  location under `.datacore/modules/nightshift/agents/`) breaks once
  `apply()` moves them. Nightshift's deploy-side dispatcher is the one
  known instance, documented and unresolved (Integration, Open Question 3).
- **No org-mode, journal, or knowledge-base migration.** This DIP's blast
  radius is confined to the agent registry (`agents.yaml`) and agent
  definition files; it does not touch GTD state, the event ledger, or any
  DIP-0009/DIP-0034 concern.
- **DIP-0016 is unaffected until ratification.** This DIP proposes, but
  does not itself apply, a schema/section addition to DIP-0016 (see
  "Proposed Amendment to DIP-0016" below). DIP-0016's live text and
  `Status: Implemented` are untouched by this pass.

## Implementation

Honest status, matching "Achieved vs Target" above — most of what this DIP
proposes at the governance/tooling-integration level is **not yet done**;
what's marked Done below is limited to the one real `registry_gc.py` run
already executed.

| Phase | Scope | Status |
|---|---|---|
| 1. `registry_gc.py` built and guard-hardened (shared-source, atomic writes, header preservation, duplicate-key pre-flight, gitignored-source) | Tool | Done |
| 2. Evaluator consolidation executed (`evaluators.yaml` + `evaluator.md` + 22 `module_agents:` entries archived) | First real consolidation | Done — reflected in Achieved vs Target |
| 3. Registry entry for the new `evaluator` agent itself | Registry completeness | **Not done** — open gap, see Specification "Personas-as-data" and Open Question 4 |
| 4. Reconciliation with `registry_validate.py` (scoping + sequencing) | Tool overlap | **Not done in code** — scoped and documented in Specification; sequencing left as Open Question 5 |
| 5. `registry_gc.py`'s classifier recognizing `deprecated: true` | Convention alignment | **Not done in this tool** — companion code fix landing separately on `feat/datacore-v2`, out of this DIP's scope |
| 6. Nightshift deploy-side dispatcher updated to read `evaluators.yaml` | Consumer wiring | **Not started** — Open Question 3 |
| 7. Remaining consolidation families (`gtd-*`, `health-*`, research pipeline, megaphone pipeline) | Follow-up scope | **Not started** — named, not scheduled (Open Question 2) |
| 8. Fold lifecycle/archival model into DIP-0016 | Governance | Drafted below (ready to fold in as new §20); lands on ratification, not yet applied to DIP-0016's live text |
| 9. DIP-0011 Implementation Status table correction | Cross-DIP consistency | **Not done** — flagged; pending ratification |
| 10. Archive destination corrected from `.datacore/agents/_deprecated/` to `.datacore/4-archive/agents/` (harness-visibility fix) | Tool + this DIP's text | Done in code, on `feat/datacore-v2`, for the 34 defs archived by that branch's own run. **Not done for `main`** — see "Correction" below and Open Question 6 |

### Correction: archive destination was harness-visible

This DIP's own first real `--apply` run (the one recorded in "Achieved vs
Target") archived deprecated defs into `.datacore/agents/_deprecated/`,
following the Specification and §20 amendment text as originally drafted.
During the v2 final review, that destination was found to still be
harness-visible: `.claude` symlinks to `.datacore`, and Claude Code's Task
tool scans `.claude/agents/**` recursively, so every file placed in
`.datacore/agents/_deprecated/` — a subdirectory *inside* the scanned
`.datacore/agents/` tree — remained fully discoverable and spawnable
regardless of its `agents.yaml` status. This was flagged Critical, and the
fix wave relocated all archived agent definitions (34 on `feat/datacore-v2`,
covering both this DIP's evaluator consolidation and the pre-existing
DIP-0021-era deprecations) to `.datacore/4-archive/agents/`, a path
outside `.datacore/agents/` entirely, and removed `_deprecated/`.

This DIP's Specification and §20 amendment above have been corrected to
name `.datacore/4-archive/agents/` as the destination going forward. The
history is recorded here rather than silently rewritten: the first real
run's actual destination was the harmful one, and that is why the
Normative rule below is now stated as harness-tree-independent rather
than as a specific path.

### Reference Implementation

`.datacore/lib/registry_gc.py` + `.datacore/lib/tests/test_registry_gc.py`
(this repo's tracked copy). The nightshift `module.yaml` deploy-side
dispatch wiring named in Integration is out of this repo, per the
`.datacore/modules/*/` gitignore rule with no `nightshift` allowlist entry.

### Rollout Plan

On ratification, in this order: (1) fold the "Proposed Amendment to
DIP-0016" section below into DIP-0016 as new §20; (2) close Phase 3
(register `evaluator`) before any further `--apply` run touches this
registry; (3) resolve Phases 4/5 (tool overlap, marker-recognition parity)
per Open Questions 4/5; (4) correct DIP-0011's Implementation Status
table; (5) treat each of the four named follow-up families (Phase 7) as
its own separately scoped DIP/task, not opportunistic work folded into
this one.

## Open Questions

1. Should the destination-basename-collision gap in `apply()` (see
   Specification, "NOT a guard") be closed by disambiguating the archive
   filename (e.g. prefixing with the section, or the registry key, when a
   collision is detected) before any further real `--apply` runs touch this
   registry again? A second real run today already needed a manual,
   out-of-band fix for exactly this collision (`module_agents/
   gtd-research-processor-module`'s def file colliding with an unrelated,
   already-archived `gtd-research-processor.md`).
2. Which of the four named follow-up families (gtd, health, research
   pipeline, megaphone pipeline) should be consolidated first, and does the
   ≤60 target survive contact with all four, or does it need revising once
   their actual overlap/heterogeneity is assessed up close (Forge was
   deliberately not promoted to "primary candidate" for exactly this
   reason)?
3. Who owns updating `.datacore/modules/nightshift/module.yaml` (deploy-side,
   outside this repo) to dispatch the parameterized `evaluator` agent
   instead of the 22 old names, and on what timeline relative to the
   `evaluator-*` def files now living only in the archive?
4. Register `evaluator` in `agents.yaml`'s `agents:` section before any
   further `registry_gc.py --apply` run archives another `evaluator-*`
   stub, and before the deploy-side dispatcher (Open Question 3) is
   updated — wiring a dispatcher to a data roster with no matching
   registry entry perpetuates exactly the hardcoded-routing pattern
   DIP-0016 §1 was written to eliminate. Who owns writing that entry, and
   does it ship before or alongside the DIP-0016 amendment below?
5. Merge `registry_gc.py` and `registry_validate.py`, or explicitly
   declare a single owner for orphan pruning and a single owner for
   deprecation archival, **before either grows a third caller** — trigger
   this before nightshift's Phase 9.5 invocation of `registry_validate.py`
   is ever changed to pass `--prune`, since that is the change that would
   turn today's non-race into a real one. Also resolve, at the same time,
   the marker-recognition mismatch between the two tools' `deprecated`
   classifiers (Specification, "Known implementation gap").
6. `main` (as opposed to `feat/datacore-v2`, where the relocation already
   happened) still carries 6 deprecated defs in
   `.datacore/agents/_deprecated/` —
   `conversation-processor`, `gtd-process-inbox`, `gtd-research-processor`,
   `ingest-coordinator`, `ingest-processor`, `research-link-processor` —
   which, per the harness-visibility finding above, load into every live
   session on `main` today. Relocating them is out of scope for this DIP's
   branch (this DIP does not touch `main` directly), but they need the
   same `.datacore/4-archive/agents/` relocation `feat/datacore-v2`
   applied. **Trigger**: before or immediately upon `feat/datacore-v2`
   merging to `main` — whichever lands first — so `main` is never left in
   the known-harness-visible state longer than necessary once the fix is
   known.

## References

- [DIP-0016](DIP-0016-agent-registry.md): Agent Registry & Discoverability
  (schema, both sections; §1 "single source of truth" and §16 "Agent
  Execution Lifecycle" both referenced above; see "Proposed Amendment to
  DIP-0016" below for the new §20 this DIP drafts)
- [DIP-0021](DIP-0021-search-research-architecture.md) (§"DIP-0016 Schema
  Extension" — origin of the `deprecated: true` + `superseded_by`
  convention this DIP adopts as canonical, with `status: deprecated` and
  `[DEPRECATED]` as accepted legacy aliases)
- [DIP-0011](DIP-0011-nightshift-module.md) (Implementation Status table —
  documents the 20 individual `evaluator-{...}.md` files this DIP's
  consolidation archives as current architecture; needs a follow-up
  correction on ratification)
- [DIP-0022](DIP-0022-module-specification.md) (§"module registration" —
  `module_agents:` ownership and the `provides.agents:` re-population
  hazard documented in Integration)
- [DIP-0026](DIP-0026-architectural-primitives.md) (§1 Capture-Process-Archive
  — the primitive this DIP applies to agents, named rather than re-derived)
- `.datacore/lib/registry_validate.py` (pre-existing schema/orphan
  validator, wired into nightshift Phase 9.5; scoped against
  `registry_gc.py` in Specification, "Relationship to `registry_validate.py`")
- `task-7.1-report.md`, `task-7.2-report.md`, `task-7.3-report.md`
  (`.superpowers/sdd/2026-07-29-datacore-v2/`, untracked — full verbatim
  command output for every claim made in this DIP's "Achieved vs Target"
  section)
- `.datacore/lib/registry_gc.py` (module docstring — full design rationale
  for every guard listed above)
- `.datacore/registry/evaluators.yaml`, `.datacore/lib/agents/evaluator.md`
  (the evaluator consolidation's actual deliverables)

## Proposed Amendment to DIP-0016

> **Not applied in this pass.** DIP-0016 is merged (`Status: Implemented`)
> and is not edited by this DIP. The text below is drafted ready to fold
> into DIP-0016 verbatim, as a new **§20**, on ratification — following
> the in-place-amendment precedent DIP-0016's own §19 set when DIP-0027
> extended it ("Required for DIP-0016 compliance going forward"), and the
> lighter "DIP-0016 Schema Extension" precedent DIP-0021 set when it added
> the `deprecated`/`superseded_by` fields themselves. Until an owner
> ratifies this DIP and performs that fold-in, DIP-0016's live text and
> `Updated` date remain unchanged.

### 20. Agent Lifecycle: Deprecation, Archival & Garbage Collection

> Added by DIP-0040 (Agent Consolidation, 2026-07-30). Formalizes the
> registry entry lifecycle that DIP-0021's `deprecated`/`superseded_by`
> fields (§"DIP-0016 Schema Extension" in DIP-0021) introduced but never
> completed: what happens to an entry *after* it is marked deprecated.

A registry entry — under either `agents:` or `module_agents:` — moves
through exactly one lifecycle: **active → deprecated → archived**.
Independently of that chain, an entry with a missing or empty `source:`
field is classified **orphaned** (full three/four-way classification,
including the report-only **unregistered** category for on-disk files
with no registry entry, is specified in DIP-0040); `deprecated` takes
strict priority over `orphaned` when an entry is both. This section
governs the standing state of a registry entry across its existence and
is distinct from §16's Agent Execution Lifecycle, which governs one
agent *run*.

**Canonical deprecation markers.** New deprecations use `deprecated: true`
plus `superseded_by: <replacement-agent-name>` — the convention DIP-0021
established (§"DIP-0016 Schema Extension") and that already applies to
live registry entries. `status: deprecated` (case-insensitive) and the
literal string `[DEPRECATED]` in an entry's `name`/`description` are
**accepted legacy aliases**: tooling that reads deprecation state
(`registry_gc.py`, `registry_validate.py`, `agent-registry-auditor`, and
any future consumer) MUST continue to recognize all three forms
equivalently. Existing legacy-marked entries are not required to migrate
to the canonical fields.

**`deprecated` (mid-lifecycle state).** The entry stays in `agents.yaml`,
carries one of the markers above, and remains discoverable — callers still
resolve it, see the deprecation marker, and migrate to `superseded_by` at
their own pace. This is a labeling step only; no file moves and nothing
is removed from the live registry.

**`archived` (terminal state).** A garbage-collection pass (DIP-0040's
`registry_gc.py --apply`, or any future tool performing the same
transition) moves a deprecated entry's `source:` definition file
completely out of every harness-scanned agent directory
(`.datacore/agents/`, `.datacore/modules/*/agents/`) into an archive
directory that is itself outside that scanned tree, removes the entry
from the live `agents.yaml`, and records its full metadata in
`.datacore/registry/archive/agents-deprecated.yaml`, under that entry's
own top-level section key (`agents:` or `module_agents:`, never
flattened together). §1's "single source of truth" claim for
`agents.yaml` refers to its live sections only — the archive file is a
non-authoritative historical record, kept for provenance, not a second
registry.

**Normative**: archived agent definitions MUST NOT reside anywhere
within a harness-scanned tree; on this installation that means outside
`.datacore/agents/**`, because `.claude` symlinks to `.datacore` and
harnesses (e.g. Claude Code's Task tool) scan `.claude/agents/**`
**recursively** — a subdirectory of `.datacore/agents/` is still inside
that tree and does not satisfy this rule. **The concrete destination is
`.datacore/4-archive/agents/`.** An earlier version of this DIP archived
into `.datacore/agents/_deprecated/`, a subdirectory of the scanned tree;
that was found to remain fully harness-discoverable and spawnable
regardless of registry status, was flagged Critical in the v2 final
review, and was corrected (see DIP-0040's Implementation, "Correction:
archive destination was harness-visible"). An internal tool's own
skip-list (e.g. `registry_validate.py`'s `SKIP_PARTS`) is not sufficient
evidence of safety: it governs only what that one tool reports or
ignores, not what an independent, recursively-scanning harness will load.
Physical relocation *out of the scanned tree* — not a status flag, and
not merely a differently-named subdirectory within it — is what this rule
requires.

**Applies to both sections.** `agents:` and `module_agents:` entries
follow the identical state machine and the identical archive-file
sectioning. For `module_agents:` specifically, this creates a hazard
absent from `agents:`: per [DIP-0022](DIP-0022-module-specification.md),
`datacore.modules.register` re-populates `agents.yaml`'s `module_agents:`
section **from** a module's `module.yaml provides.agents:` list on every
install/reinstall. If a module's `module.yaml` still lists an agent under
`provides.agents:` after that agent's `module_agents:` entry has been
archived, a later `datacore.modules.register` run will silently
re-populate the archived entry back into the live registry — undoing the
archival without the garbage-collection tool ever knowing. Any
`module_agents:` consolidation MUST update the owning module's
`module.yaml` in the same change as the archival, not as a separate,
optional step.

**Relationship to `registry_validate.py`.** `.datacore/lib/registry_validate.py`
(pre-existing, wired into nightshift Phase 9.5) and `registry_gc.py`
(DIP-0040) are scoped differently but overlap: `registry_validate.py` is
schema/orphan *validation* — its `--prune` mode removes orphaned entries,
report-only by default in the scheduled nightshift path — while
`registry_gc.py` performs the full deprecate→archive lifecycle transition
described above and also classifies/removes orphans. Both independently
mutate `agents.yaml` via atomic writes with no declared sequencing between
them. **Ratifying owner must resolve**: merge the two tools, or declare a
single owner for orphan pruning and a single owner for deprecation
archival, before either grows a third caller (DIP-0040 Open Question 5).

**Cross-reference correction required on ratification.** [DIP-0011](DIP-0011-nightshift-module.md)'s
Implementation Status table ("Core evaluator panel (6)" / "Domain
evaluator panel (14)") names 20 individual `evaluator-{...}.md` files as
current architecture. Once this section is folded in and DIP-0040's
evaluator consolidation is treated as ratified, that table is stale and
needs a follow-up correction pointing at `.datacore/registry/evaluators.yaml`
+ `.datacore/lib/agents/evaluator.md` instead.
