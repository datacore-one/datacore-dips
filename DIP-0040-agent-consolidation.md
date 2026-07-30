# DIP-0040: Agent Consolidation

| Field | Value |
|-------|-------|
| **DIP** | 0040 |
| **Title** | Agent Consolidation |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Draft |
| **Created** | 2026-07-30 |
| **Updated** | 2026-07-30 |
| **Tags** | `agents`, `registry`, `lifecycle`, `gc`, `personas-as-data`, `datacore-v2` |
| **Affects** | `.datacore/lib/registry_gc.py`, `.datacore/lib/tests/test_registry_gc.py`, `.datacore/registry/agents.yaml`, `.datacore/registry/archive/agents-deprecated.yaml`, `.datacore/registry/evaluators.yaml`, `.datacore/agents/_deprecated/`, `.datacore/lib/agents/evaluator.md`, `.datacore/modules/nightshift/module.yaml` (deploy-side, not in this repo) |
| **Specs** | `.datacore/lib/registry_gc.py`, `.datacore/registry/evaluators.yaml` |
| **Agents** | `agent-registry-auditor`, `context-maintainer`, any agent spawned via the registry (`ai-task-executor`, `nightshift-orchestrator`) |
| **Relates to** | DIP-0016 (Agent Registry & Discoverability — the schema and both top-level sections this DIP's tooling operates on), DIP-0021 (the `[DEPRECATED]`/`superseded_by` convention `registry_gc.py` classifies against) |

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
predictable schedule.

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

### Lifecycle states

A registry entry (under either `agents:` or `module_agents:`) is in exactly
one of three lifecycle states at any time:

| State | How it's recognized | What it means |
|-------|---------------------|----------------|
| **active** | Neither deprecated nor orphaned (see below) | Live, listable, spawnable |
| **deprecated** | `status: deprecated` (case-insensitive) OR the literal string `[DEPRECATED]` appears anywhere in the entry's name or `description` | Marked for retirement; still present in the live registry until a `gc --apply` run archives it |
| **orphaned** | Not deprecated, but its `source:` file is missing or empty, or the entry has no `source:` field at all | The registry references a definition file that doesn't exist on disk; almost always a stale entry from a moved/renamed/deleted file |

`deprecated` takes strict priority over `orphaned`: an entry that is both
(marked deprecated AND missing its source file) classifies as `deprecated`
only — `apply()` archives its metadata and simply has nothing to move.

A fourth, non-lifecycle category, **unregistered**, is report-only: a
`*.md` file under a scanned agent directory that no registry entry's
`source:` points at. This is never auto-fixed — registering an agent
requires semantic judgement (skills, triggers, spawn relationships) that is
`agent-registry-auditor`'s job, not a mechanical GC pass.

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
  `source:` file is moved into `archive_dir` (unless the shared-source
  guard below fires) and its metadata staged into an in-memory merge of
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
  documented, accepted formatting-normalization consequence of using plain
  PyYAML instead of a comment-preserving library like `ruamel.yaml` (not a
  declared project dependency).
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

- **Nightshift evaluator dispatch reads the roster, but only at the deploy
  side.** `.datacore/modules/nightshift/module.yaml` — which enumerates all
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

## References

- DIP-0016: Agent Registry & Discoverability (schema, both sections)
- DIP-0021 (the `[DEPRECATED]`/`superseded_by` convention this DIP's
  tooling classifies against)
- `task-7.1-report.md`, `task-7.2-report.md`, `task-7.3-report.md`
  (`.superpowers/sdd/2026-07-29-datacore-v2/`, untracked — full verbatim
  command output for every claim made in this DIP's "Achieved vs Target"
  section)
- `.datacore/lib/registry_gc.py` (module docstring — full design rationale
  for every guard listed above)
- `.datacore/registry/evaluators.yaml`, `.datacore/lib/agents/evaluator.md`
  (the evaluator consolidation's actual deliverables)
