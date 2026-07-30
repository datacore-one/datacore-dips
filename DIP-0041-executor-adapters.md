# DIP-0041: Executor Adapters

| Field | Value |
|-------|-------|
| **DIP** | 0041 |
| **Title** | Executor Adapters |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Draft |
| **Created** | 2026-07-30 |
| **Updated** | 2026-07-30 |
| **Tags** | `executors`, `provider-registry`, `shadow-accounting`, `spend.record`, `harness-generation`, `datacore-v2` |
| **Affects** | `.datacore/lib/executors/__init__.py`, `.datacore/lib/executors/base.py`, `.datacore/lib/executors/claude_code.py`, `.datacore/lib/executors/hermes.py`, `.datacore/lib/executors/api.py`, `.datacore/lib/tests/test_executors.py`, `.datacore/lib/gen_claude_agents.py`, `.datacore/lib/tests/test_gen_claude_agents.py`, `.datacore/lib/ledger/fold.py` (`_handle_spend`, consumed not modified), `cos_generate.py`/`cos_reasoning.py` + one nightshift call site (deploy-side, not in this repo — named as follow-up below), `.datacore/modules/nightshift/module.yaml` (deploy-side, stale evaluator names — named as follow-up below) |
| **Specs** | `.datacore/lib/executors/base.py`, `.datacore/lib/gen_claude_agents.py` |
| **Agents** | any process that currently shells out to a specific harness CLI directly (candidates for migrating to `get_executor()`: `cos_generate.py`, `cos_reasoning.py`, the nightshift briefing call site); `registry_gc.py` and `gen_claude_agents.py` as the registry's two lifecycle/build tools |
| **Relates to** | `ENG-2026-0718-002` (provider-registry directive this DIP generalizes one layer up), `ENG-2026-0729-016` (ledger-mindset direction — shadow accounting item 3, conservation invariant item 4), DIP-0034 (Event Ledger Substrate — `spend.record` event this DIP is the first live producer of), DIP-0016 (Agent Registry — the schema `gen_claude_agents.py` reads), DIP-0040 (Agent Consolidation — the registry GC pass and evaluator roster this DIP's generator runs downstream of) |

## Summary

Datacore v2's final phase (Phase 8) does two things that close out the
release: it gives every future model/harness call a single seam —
`get_executor(name) -> Executor`, an extensible provider registry instead of
a hardcoded branch — with **live shadow accounting** (`spend.record` ledger
events emitted on every call, per DIP-0034's event schema); and it gives the
agent registry (DIP-0016) a one-way build step, `gen_claude_agents.py`, that
turns `.datacore/registry/agents.yaml` into harness-consumable artifacts
instead of letting the harness's own config drift out of sync with the
registry by hand. Both pieces are complete and tested against synthetic
fixtures. Neither is wired into its real call sites yet in this repo, and
this DIP records that honestly rather than claiming integration that hasn't
happened — plus one machine-specific architecture finding (a symlink) that
changes what "the real call site" even means for the generator on this
installation.

## Motivation

`ENG-2026-0718-002` (user directive, 2026-07-18) named the actual problem
one layer up from where this DIP sits: Chief-of-Staff's LLM provider choice
was heading toward a hardcoded three-way branch (`COS_LLM_BACKEND` /
`COS_CHAT_BACKEND` picking between Claude subscription, OpenRouter, local
Gemma) at the exact moment more providers (OpenAI, a possible Hermes
subscription) were coming. The directive: architect provider choice as an
**extensible registry** — "add a provider = one adapter + one wizard card +
one `COS_*` block" — not a branch that grows a new `elif` per provider,
because a branch is exactly the shape that produces harness/executor
lock-in: whichever provider got wired in first becomes structurally
privileged, and every later addition is a bigger diff than the first one
was.

This DIP is the substrate that directive needs, generalized past the
CoS-specific wizard/chat-backend framing: any code in Datacore that
currently invokes "the AI" by shelling out to a specific CLI or SDK
directly is doing the same hardcoding `ENG-2026-0718-002` flagged, just
without a user-facing wizard around it yet. `get_executor()` is the one
seam: callers ask for "an executor" (by explicit name, by
`$DATACORE_EXECUTOR`, or by falling through to a documented default) and
get back an object with one contract (`run()`), regardless of which
subprocess or SDK actually backs it. Adding a fourth provider is one new
adapter module plus one `@register` decorator — never a change to any
existing caller.

The second half of this DIP — `gen_claude_agents.py` — answers a narrower
but related lock-in question: Claude Code's own harness config
(`.claude/agents/*.md`) is currently a second, hand-maintained copy of
information the agent registry (DIP-0016) already owns authoritatively.
Two sources of truth for the same fact (what agents exist, what they do)
drift; a generator with a `# GENERATED -- do not edit` header and a
`--check` drift-detector makes the registry the only place that fact is
ever authored, with the harness artifact as a disposable, regenerable
build output — the same "registry is the source, artifact is derived"
shape DIP-0016 already established for other consumers.

## Specification

### Executor contract

```python
@dataclass
class ExecResult:
    text: str
    parsed: dict | None
    cost_cents: int
    error: str | None
    parse_ok: bool | None = None  # None = no schema requested; True/False = schema parse outcome

class Executor:
    name: str
    def _invoke(self, prompt: str, timeout_s: int) -> tuple[str, int]: ...  # subclass override point
    def run(self, prompt: str, *, schema: dict | None = None, timeout_s: int = 300) -> ExecResult: ...

def get_executor(name: str | None = None) -> Executor: ...
def register(cls: type[Executor]) -> type[Executor]: ...          # class decorator
def registered_executors() -> dict[str, type[Executor]]: ...
```

Three adapters ship in this DIP, each a thin `_invoke` implementation over
`run()`'s shared contract: `ClaudeCodeExecutor` (`name = "claude-code"`,
subprocess `claude -p <prompt> --output-format json`), `HermesExecutor`
(`name = "hermes"`, subprocess `hermes chat -q <prompt>`), and
`ApiExecutor` (`name = "api"`, direct Anthropic SDK call, import deferred
into `_invoke` so a missing SDK fails at call time, not import time).

**Registry precedence** (`get_executor`): explicit `name` argument, else
`$DATACORE_EXECUTOR`, else the literal default `"claude-code"`. An
unrecognized name raises `ValueError` naming every registered executor —
resolution never silently falls back to a default on a typo.

### `run()` guarantees — never-raise, `parse_ok`, cost clamp, ref markers

`run()` owns everything an adapter must not have to reimplement itself:

- **Never-raise.** Every exception `_invoke` can raise — including
  `subprocess.TimeoutExpired`, mapped to a dedicated message — becomes
  `ExecResult.error` instead of propagating. (Precisely: anything
  `except Exception` catches; `BaseException` siblings such as
  `KeyboardInterrupt`/`SystemExit` are outside this guarantee's scope.)
- **Schema contract + `parse_ok`.** When `schema` is passed, a JSON-contract
  instruction is appended to the prompt and the response is parsed as JSON.
  A parse failure is not treated as an execution failure — it sets
  `parsed=None, parse_ok=False` and leaves `error` untouched, because a
  schema miss is a normal content outcome, not a transport failure.
  `parse_ok` stays `None` when no schema was requested at all, so a caller
  can distinguish "didn't ask" from "asked and it parsed/didn't."
- **Cost clamp (conservation invariant).** `cost_cents` returned by
  `_invoke` is coerced via `int(cost_cents)` inside a broad exception
  catch (deliberately broad: `int(float("inf"))` raises `OverflowError`,
  which a narrower `except (TypeError, ValueError)` would miss and let
  escape). A value that fails to coerce, or coerces negative, is floored
  to `0`, and the emitted ledger ref gains a `:clamped` suffix. This exists
  because `ledger/fold.py::_handle_spend` sums `cost_cents` onto an actor's
  balance with zero validation of its own (`state.spend[actor] =
  state.spend.get(actor, 0) + cents`) — the conservation guarantee that
  `spend.record` events only ever increase a balance (`ENG-2026-0729-016`
  item 4, restated in DIP-0034 Rationale point 4) has to be enforced at the
  producer, since the fold doesn't enforce it itself.
- **Ref markers, composable.** The ledger event's `ref` field is built
  incrementally, never via a single ternary, so multiple conditions stack:
  `executor:<name>` as the base, `:est` appended when the adapter had no
  real usage/cost figure and fell back to `estimate_cost_cents()` (chars/4
  tokens at `ESTIMATE_CENTS_PER_MILLION_TOKENS = 300` — an explicit shadow-
  ledger placeholder rate, not a real Anthropic billing figure), `:clamped`
  appended when the cost clamp above fired, and `:err` appended when the
  adapter flagged an **in-band** error (transport succeeded, cost was
  genuinely incurred, but the response content itself reports failure —
  e.g. `claude-code`'s JSON envelope carrying `is_error: true` and/or
  `subtype != "success"`). An in-band error surfaces as `ExecResult.error`
  but — unlike a raised exception — does **not** skip spend emission: real
  cost was actually spent regardless of what the content says.

### `spend.record` shadow accounting — semantics and the conservation note

Every successful `_invoke` (anything that didn't raise) emits exactly one
`spend.record` ledger event via `ledger.log.EventLog(space_dir, actor)`,
unless `$DATACORE_NO_SPEND=1`. Resolution mirrors the rest of the ledger
tooling for consistency: `actor` = `$DATACORE_ACTOR` else
`socket.gethostname()`; `space_dir` = `$DATACORE_ROOT` else `~/Data`,
resolved at **call time** (not cached at import time), matching
`ledger_cli.py` / `job_verify.py` and letting tests monkeypatch
`DATACORE_ROOT` per-test in a long-lived process. Signing follows
`EventLog`'s own default — opt-in via `$DATACORE_LEDGER_SIGN=1`
(`ENG-2026-0729-030`) — so a bare executor run is unsigned by default, same
as every other ledger writer in this release.

Fold-time handling (`ledger/fold.py::_handle_spend`, already defined by
DIP-0034 Phase 1, consumed unmodified here) is deliberately simple: it
accumulates `payload["cents"]` into `state.spend[actor]` with no task
association — pure per-actor accounting, the shadow-accounting substrate
named in `ENG-2026-0729-016` item 3. **Conservation note**: DIP-0034 states
the invariant ("`spend.record` events only ever *add* to a balance — there
is no debit/credit pair and no event type that decreases it") but does not
itself enforce it against a malformed producer; this DIP's `run()` is the
first concrete place that invariant actually gets enforced end-to-end
(the cost clamp above), because it is the first `spend.record` producer
whose input (`_invoke`'s return value) is not already known-good ledger
data — it comes from parsing subprocess/SDK output, which can be malformed
in ways a hand-written ledger CLI call never would be. Budget-ceiling
enforcement (hard-blocking overspend, vs. today's pure observation) remains
future work, per DIP-0034's own Open Question 4 — this DIP does not change
that scope.

### Generator one-way rule

`gen_claude_agents.py` turns the DIP-0016 agent registry into harness
build artifacts:

```python
def generate(registry_path, out_dir, sections=("agents",)) -> GenReport
    # GenReport(written: list[str], skipped_deprecated: int)
def check(registry_path, out_dir, sections=("agents",)) -> CheckResult
    # CheckResult(clean: bool, missing: list, extra: list, drifted: list, skipped_deprecated: int)
```

Every active entry (an entry without `status: deprecated`, case-insensitive
— deliberately narrower than `registry_gc.py`'s classification, which also
treats a `[DEPRECATED]` name/description marker as deprecated; that
broader classification is `registry_gc`'s job at GC time, not this
generator's) becomes `<out_dir>/<name>.md`: a fixed
`# GENERATED from .datacore/registry/agents.yaml -- do not edit` header
line, a YAML frontmatter block (`name`, `description`, rendered via
`yaml.safe_dump` rather than string interpolation so quotes/colons/embedded
newlines round-trip losslessly), and a body line pointing at the entry's
`source:` definition file. Generation is deterministic and idempotent —
sorted-name order, no timestamps — so re-running against an unchanged
registry produces a byte-identical result. `--check` is fully read-only:
it regenerates to memory and diffs by stem name against `out_dir`'s current
files (missing / extra / content-changed), never creating `out_dir` if
absent, exiting 1 on any drift. **The one-way rule is the point**: the
registry is the only place an agent's name, description, or (indirectly,
via `source:`) definition file location is authored; `.claude/agents/*.md`
is a disposable output regenerated from it, never hand-edited — the same
"registry is the source, artifact is derived" shape DIP-0016 established
for other consumers of the registry, now extended to the harness's own
config.

## Architecture Finding: the `.claude` symlink, and the ruling on real generation

Task 8.2 (`.claude` artifact generation from registry) surfaced a finding
specific to **this installation** that the generator's own design does not
assume and must not be run against blind: `~/Data/.claude` is a **symlink
to `.datacore`**, verified directly —

```
$ ls -la ~/Data/.claude
lrwxr-xr-x@ 1 gregor  staff  9 10 maj  15:26 /Users/gregor/Data/.claude -> .datacore
```

— which means `.datacore/agents/*.md` are not a separate, hand-authored
harness config sitting next to the registry; they **are**
`.claude/agents/*.md`, literally the same files, reached through the
symlink. Confirmed byte-identical in Task 8.2's own investigation
(`.claude/agents/ai-task-executor.md` and
`.datacore/agents/ai-task-executor.md` are the same inode). Those files
are also the real `source:` targets the registry's own entries point at —
they are canonical, git-tracked, hand-authored agent definitions, not
generated stubs.

Running `gen_claude_agents.py --out .claude/agents/` for real on this
machine would therefore not populate an empty or generated directory — it
would **overwrite every core agent's real hand-authored definition with a
seven-line generated stub that points back at itself**, a silent,
severe (though git-recoverable) data-loss event.

**Ruling (controller, this task, supersedes the brief's original
conditional "run it for real if `.claude/agents` exists and isn't
gitignored")**: do **not** run `gen_claude_agents.py` against the real
`~/Data/.claude` tree. The generator itself is unaffected by this
ruling — it is complete, tested against synthetic `tmp_path` fixtures
(27 tests, all passing, none touching the real tree), and this task
re-verified it with a scratch-directory smoke run
(`--out /tmp/gen-check-scratch`, 40 files written, exit 0) rather than
against `.claude/`. What the ruling establishes is a scoping fact about
**this deploy target**, recorded here as an architecture finding rather
than silently worked around: the generator's premise — "registry is
source, harness artifact is a separate derived build output" — applies
cleanly to a deploy target with its own, separate `.claude/` directory
(a fresh install, a server deploy without this symlink). On a machine
where `.claude` is symlinked to `.datacore`, the registry sources and the
harness-visible artifacts are **the same files already**, and there is no
separate derived output to regenerate into without destroying the source.
Any future real invocation of this generator against a symlinked `.claude`
must first either point `out_dir` at a different, harness-discoverable
directory (e.g. `.claude/agents-generated/`, if Claude Code supports a
secondary agent directory) or reconsider whether the generator's premise
applies to this topology at all — this DIP does not resolve that question,
it only names it precisely enough that nobody re-runs the generator
against the real tree by accident.

## Integration

Named, dated as follow-up work — **not** claimed done by this DIP:

- **Executor call sites.** `cos_generate.py`, `cos_reasoning.py`, and one
  nightshift briefing call site currently invoke a harness directly rather
  than through `get_executor()`. Migrating them is deploy-side work (these
  files live outside this repo's touch-list for Phase 8) flagged for a
  dedicated integration task; until it lands, the executor registry exists
  and is fully tested but has zero real production callers.
- **`COS_GROUNDED=1`.** DIP-0037's grounded-briefing pipeline (fact table,
  token contract, validator) is implemented behind this flag but the flag
  itself is not yet flipped on anywhere; wiring it into `cos_reasoning.py`
  for real is the named Phase 6 follow-up gate DIP-0037/DIP-0039 already
  recorded, restated here because it shares the same "executor/LLM call
  site not yet migrated" shape as the item above.
- **Nightshift roster dispatch.** DIP-0040 consolidated 22 `evaluator-*`
  agents into one `evaluator` agent plus a data roster
  (`registry/evaluators.yaml`); nightshift's own evaluator-dispatch code
  has not yet been updated to read that roster instead of dispatching to
  the (now archived) individual `evaluator-*` names. Named in DIP-0040 as
  a deploy-side integration item; restated here because it directly
  affects whether `.datacore/modules/nightshift/module.yaml` (next item)
  is currently correct.
- **`module.yaml` stale names.** `.datacore/modules/nightshift/module.yaml`
  (deploy-side, not in this repo) still names pre-consolidation
  `evaluator-*` agents that Task 7.3 archived out of the live registry.
  Until the roster-dispatch wiring above lands, this file is stale
  documentation of the module's agent surface, not a functional break (the
  archived definitions still exist on disk under the archive directory),
  but it should be corrected in the same pass as the roster-dispatch
  integration rather than independently.

None of these four items block this DIP's Status as Draft — they are
scoped, dated follow-ups on deploy-side files this repo's Phase 8 tasks
were never asked to touch, consistent with how DIP-0037/0039/0040 each
recorded their own deploy-side gates rather than silently claiming
integration that hadn't happened.

## Relationship to other DIPs

- **DIP-0034 (Event Ledger Substrate)** defines the `spend.record` event
  type and its Phase 1 fold handler (`_handle_spend`, pure accumulation,
  no validation) and states the conservation invariant in its Rationale
  (point 4) without itself enforcing it against a malformed producer.
  This DIP is the first concrete `spend.record` producer with unvalidated
  upstream input (subprocess/SDK output, not hand-constructed ledger data)
  and is therefore the first place that invariant is actually enforced,
  via the cost clamp described above.
- **`ENG-2026-0729-016`** (owner decision, 2026-07-29) is the ledger-mindset
  direction this entire Phase 1–8 arc implements: adopt the mindset now
  (signed logs, verification contracts, shadow accounting, co-sign,
  ownership-as-data, content-addressing) without building a blockchain.
  Item 3 ("shadow accounting — meter real spend per agent/task against
  notional budgets, observe before enforcing") is this DIP's `spend.record`
  emission end-to-end; item 4's conservation invariant ("never let a spend
  event net to a decrease") is this DIP's cost clamp.
- **`ENG-2026-0718-002`** (user directive, 2026-07-18) is the provider-
  registry request one layer up (CoS-specific: wizard model-choice step,
  `COS_LLM_BACKEND`/`COS_CHAT_BACKEND`) that this DIP's `get_executor()`
  generalizes into a repo-wide substrate any caller can use, not only CoS.

## Honest Status (2026-07-30, Task 8.3 — release close)

Final gates run for this release, verbatim:

- `python3 -m pytest tests/ -q` — **773 passed, 1 skipped** (the
  `RUN_LIVE=1`-gated claude-code smoke, correctly skipped).
- `python3 registry_gc.py --registry ../registry/agents.yaml --check` —
  exit 0, 110 active / 0 deprecated / 0 orphaned / 0 duplicate keys (the
  ≤60-active aspiration named in DIP-0040 remains an open follow-up, not
  reached by this release; recorded there, restated here for continuity).
- `python3 job_verify.py --machine mac --alert log --no-emit` —
  `OK 3 jobs 3 artifacts`.
- `python3 gen_claude_agents.py --registry ../registry/agents.yaml --out
  /tmp/gen-check-scratch --sections agents` — exit 0, 40 files written,
  0 skipped_deprecated; scratch-directory smoke only, per the symlink
  ruling above — never run against the real `.claude/`.

All four Integration items above remain open as of this release. This DIP
ships as Draft with those gaps named rather than closed, consistent with
this release's own convention (DIP-0037/0039/0040 each did the same) of
recording actual status over claimed status.

## Open Questions

1. **Symlinked-`.claude` generation target** — this DIP names the problem
   (no separate derived-output directory exists to regenerate into without
   destroying the source) but does not resolve it. A future task must
   either identify a second harness-discoverable agent directory or decide
   this generator's premise doesn't apply to this topology.
2. **Executor call-site migration order** — `cos_generate.py`,
   `cos_reasoning.py`, and the nightshift call site are named together as
   "the migration" but not sequenced or scheduled; a follow-up task should
   decide whether they migrate together or independently.
3. **Budget-ceiling enforcement** — restated from DIP-0034 Open Question 4:
   shadow accounting is purely observational in this release; whether/how
   overspend should hard-block or escalate is future work once real spend
   data has accumulated.

## References

- `ENG-2026-0718-002` — provider-registry directive (2026-07-18)
- `ENG-2026-0729-016` — ledger-mindset direction (2026-07-29)
- `ENG-2026-0729-030` — signing opt-in amendment (2026-07-30)
- DIP-0016 — Agent Registry & Discoverability
- DIP-0034 — Event Ledger Substrate
- DIP-0037 — Grounded Briefings (`COS_GROUNDED=1`)
- DIP-0039 — Server-First Artifacts
- DIP-0040 — Agent Consolidation
- Task 8.1 report, Task 8.2 report — implementation detail and the original
  symlink finding this DIP restates and rules on
