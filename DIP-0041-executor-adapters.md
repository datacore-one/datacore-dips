# DIP-0041: Executor Adapters

| Field | Value |
|-------|-------|
| **DIP** | 0041 |
| **Title** | Executor Adapters |
| **Author** | Datacore Team |
| **Type** | Infrastructure |
| **Status** | Draft |
| **Depends** | DIP-0034 (Event Ledger Substrate) — hard dependency for the shadow-accounting half only (`ledger.log.EventLog`, the `spend.record` event type, its fold handler); the executor-abstraction half and the generator half are each independently functional without it — see Compatibility |
| **Created** | 2026-07-30 |
| **Updated** | 2026-08-03 |
| **Tags** | `executors`, `provider-registry`, `shadow-accounting`, `spend.record`, `harness-generation`, `datacore-v2` |
| **Affects** | `.datacore/lib/executors/__init__.py`, `.datacore/lib/executors/base.py`, `.datacore/lib/executors/claude_code.py`, `.datacore/lib/executors/hermes.py`, `.datacore/lib/executors/api.py`, `.datacore/lib/tests/test_executors.py`, `.datacore/lib/gen_claude_agents.py`, `.datacore/lib/tests/test_gen_claude_agents.py`, `.datacore/lib/ledger/fold.py` (`_handle_spend`, consumed not modified), `cos_generate.py`/`cos_reasoning.py` + one nightshift call site (deploy-side, not in this repo — named as follow-up below), `.datacore/modules/nightshift/module.yaml` (deploy-side, stale evaluator names — named as follow-up below) |
| **Specs** | `.datacore/lib/executors/base.py`, `.datacore/lib/gen_claude_agents.py` |
| **Agents** | any process that currently shells out to a specific harness CLI directly (candidates for migrating to `get_executor()`: `cos_generate.py`, `cos_reasoning.py`, the nightshift briefing call site owned by the registered `nightshift-orchestrator` agent, and datacore-bench's Layer A/B harness calls per DIP-0025); `registry_gc.py` and `gen_claude_agents.py` as the registry's two lifecycle/build tools; `agent-registry-auditor` as the registered agent that audits DIP-0016 compliance of the generator's own output surface (`.datacore/agents/*.md`) |
| **Relates to** | `ENG-2026-0718-002` (provider-registry directive this DIP generalizes one layer up), `ENG-2026-0729-016` (ledger-mindset direction — shadow accounting item 3, conservation invariant item 4), DIP-0034 (Event Ledger Substrate — `spend.record` event this DIP is the first live producer of), DIP-0016 (Agent Registry — the schema `gen_claude_agents.py` reads), DIP-0040 (Agent Consolidation — the registry GC pass and evaluator roster this DIP's generator runs downstream of), DIP-0018 (Credential Management — governs executor provider credentials; deferred to, not defined by, this DIP), DIP-0026 (Architectural Primitives — `get_executor()`/`register()` is a named instance of the Adapter Pattern catalogued there), DIP-0036 (Config Plane — the runtime credential/config materialisation surface this DIP's adapters read), DIP-0025 (datacore-bench — named migration candidate) |

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

## Agent Context

### When to Reference This DIP

**Always reference when:**
- Adding a fourth (or later) LLM/harness provider to Datacore — the
  seam is `@register` + `Executor._invoke`, never a new `elif` on an
  existing caller.
- Writing or reviewing code that would otherwise shell out to `claude -p`,
  `hermes chat`, or the Anthropic SDK directly — it should call
  `get_executor(name).run(...)` instead.
- Reading, reasoning about, or building tooling over per-actor spend data
  in the ledger (`spend.record` events and their `:est` / `:clamped` /
  `:err` ref markers) — see Specification for what each marker does and
  does not guarantee.
- Regenerating or auditing `.claude/agents/*.md` / `.datacore/agents/*.md`
  — check the Architecture Finding below before running
  `gen_claude_agents.py` against any real tree; on this installation it
  must never be run against the live `.claude/` symlink.
- Migrating `cos_generate.py`, `cos_reasoning.py`, the nightshift briefing
  call site, or datacore-bench's Layer A/B harness calls onto this DIP's
  executor seam (see Integration).

### Quick Reference for Agents

| Question | Answer |
|----------|--------|
| How do I call an LLM/harness from new code? | `get_executor(name).run(prompt, schema=..., timeout_s=...)` — resolution order: explicit `name`, else `$DATACORE_EXECUTOR`, else `"claude-code"`. Never shell out directly. |
| Which adapters ship today? | `claude-code` (subprocess `claude -p ... --output-format json`), `hermes` (subprocess `hermes chat -q`), `api` (direct Anthropic SDK, import deferred to call time) |
| Does `run()` ever raise? | No — every `_invoke` exception becomes `ExecResult.error`; see the never-raise guarantee in Specification |
| Where do executor credentials live? | Governed entirely by DIP-0018 (credential index), materialised at runtime per DIP-0036 (`~/.datacore/datacore.env`) or the CLI's own pre-authenticated session — this DIP defines no credential handling of its own |
| What does a `:est` / `:clamped` / `:err` ref suffix mean? | `:est` = cost figure was estimated (chars/4), not measured; `:clamped` = `cost_cents` failed to coerce or was negative and was floored to `0`; `:err` = transport succeeded and spend was incurred, but the response content itself reported failure |
| Does "not `:est`" mean the cost is a real invoice figure? | Not always — see Specification's per-adapter cost table; only `claude-code`'s `total_cost_usd`/`cost_usd` path is a directly measured dollar figure, other non-`:est` paths price a real token count at a shared placeholder rate |
| Is `.datacore/registry/agents.yaml` still the single source of truth after generation? | Yes — `gen_claude_agents.py` output is a disposable, regenerable build artifact; the registry (and, indirectly, each entry's `source:` file) is the only place an agent's identity is authored |
| Can this DIP's shadow accounting hard-block overspend? | No — observation only in this release; see Open Questions |

### Related Agents

| Agent | Uses This DIP For |
|-------|-------------------|
| `nightshift-orchestrator` (`.datacore/modules/nightshift/agents/nightshift-orchestrator.md`) | Named migration candidate — its briefing call site currently invokes a harness directly rather than through `get_executor()`; once migrated it becomes the first live `spend.record` producer in the nightshift pipeline |
| `agent-registry-auditor` (`.datacore/agents/agent-registry-auditor.md`) | Audits `.datacore/registry/agents.yaml` and `.datacore/agents/*.md` for DIP-0016 compliance; must respect this DIP's Architecture Finding that `gen_claude_agents.py` is never run against the real, symlinked `.claude/` tree, since a real run would overwrite the hand-authored `source:` files it audits |

### Integration Points

- [DIP-0016](DIP-0016-agent-registry.md) — the generator half consumes the agent-registry schema this DIP defines; `source:` files remain DIP-0016's hand-authored canon
- [DIP-0018](DIP-0018-credential-management.md) — governs where executor provider credentials live; this DIP defines none of its own (see Specification)
- [DIP-0026](DIP-0026-architectural-primitives.md) — `get_executor()`/`register()`/`Executor` is a named instance of the catalogued Adapter Pattern (§5)
- [DIP-0034](DIP-0034-event-ledger-substrate.md) — hard dependency for the shadow-accounting half: `spend.record` event type, `EventLog`, fold conservation handling
- [DIP-0036](DIP-0036-config-plane.md) — runtime materialisation surface this DIP's adapters read credentials/config from
- [DIP-0040](DIP-0040-agent-consolidation.md) — registry GC pass and evaluator roster the generator runs downstream of

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

This shape is not new to Datacore: it is a named instance of the
**Adapter Pattern** catalogued in [DIP-0026](DIP-0026-architectural-primitives.md)
§5 — a provider registry behind one uniform interface — and structurally
the same family as [DIP-0010](DIP-0010-external-sync-architecture.md)'s
sync-adapter architecture (one contract, many interchangeable backends).
This DIP is a new instance of that primitive, not a new primitive; per
DIP-0026's own convention for new work, it is named here explicitly
rather than re-derived.

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

### Credential handling — deferred, not defined here

This DIP defines no credential handling of its own. `ApiExecutor`'s direct
Anthropic SDK call (`anthropic.Anthropic()`, which resolves
`ANTHROPIC_API_KEY` / an auth profile from the process environment), and
the `ClaudeCodeExecutor`/`HermesExecutor` subprocess adapters' own CLI
authentication, both require a credential already present when `_invoke`
runs. Where that credential lives is governed entirely by
[DIP-0018](DIP-0018-credential-management.md) — the `anthropic-api-key`
entry in its credential index (`.datacore/env/ai-services.env`,
`ANTHROPIC_API_KEY`, `security_tier: critical`) — and made available to
this DIP's adapters at runtime the same way any other process
configuration is: materialised onto the machine per
[DIP-0036](DIP-0036-config-plane.md)'s canonical `~/.datacore/datacore.env`,
or by whatever pre-authenticated session state the `claude`/`hermes` CLIs
already maintain on their own (outside either DIP). No adapter reads a
credential path or env var name that isn't already declared in DIP-0018's
index; a future adapter needing a new provider credential registers it
there first, per DIP-0018's existing convention, rather than inventing a
new credential surface in this DIP.

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
- **Cost clamp (conservation invariant, producer-side).** `cost_cents`
  returned by `_invoke` is coerced via `int(cost_cents)` inside a broad
  exception catch (deliberately broad: `int(float("inf"))` raises
  `OverflowError`, which a narrower `except (TypeError, ValueError)` would
  miss and let escape). A value that fails to coerce, or coerces negative,
  is floored to `0`, and the emitted ledger ref gains a `:clamped` suffix.
  This is a **complementary, producer-side** layer, not the system's only
  defense — see the corrected Conservation note below for how it relates
  to `ledger/fold.py::_handle_spend`'s own, independent substrate-side
  validation.
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
  cost was actually spent regardless of what the content says. No fourth
  marker exists to distinguish a genuinely measured dollar figure from a
  real-token-count-at-placeholder-price figure — see the per-adapter table
  below for that distinction; the ref alone cannot make it.

### Per-adapter cost measurement — measured vs. estimated, per shipped adapter

`:est` fires only when an adapter falls all the way through to
`estimate_cost_cents()`. Each adapter's actual behavior:

| Adapter | `name` | Cost source, in priority order | When `:est` fires |
|---|---|---|---|
| `ClaudeCodeExecutor` | `claude-code` | 1) `total_cost_usd`/`cost_usd` parsed straight from the `claude -p --output-format json` envelope (top-level or under `usage`) — the **only** path across all three adapters that is a directly measured billing figure, not a derived one. 2) Failing that, real `usage.input_tokens`/`usage.output_tokens` counts priced at the shared placeholder rate (`ESTIMATE_CENTS_PER_MILLION_TOKENS = 300`) — the token *count* is real, the price-per-token is not; this fallback branch is marked speculative in the adapter's own source (never exercised by the live envelope that validated path 1). | Neither of the above is present in the envelope, or there is no parseable JSON envelope at all (falls back to raw stdout as `text`, cost `None` going into `estimate_cost_cents`) |
| `HermesExecutor` | `hermes` | None — `hermes chat -q` returns plain text with no cost/usage envelope of any kind | Always. Every `hermes` call is `:est`; `self._cost_estimated` is unconditionally set |
| `ApiExecutor` | `api` | The Anthropic SDK response's `usage.input_tokens`/`usage.output_tokens`, priced at the same shared placeholder rate as `claude-code`'s fallback branch — real token count, not a real dollar figure | Only if the SDK response carries no `usage` object at all (not expected in normal operation, but the adapter does not assert against it) |

**Honesty note carried over from the marker definitions above**: the
*absence* of `:est` does not uniformly mean "a real Anthropic invoice
figure." Only `claude-code`'s top-tier `total_cost_usd`/`cost_usd` path
is that. Every other non-`:est` path — `claude-code`'s token-count
fallback, and every `api` call — still prices a real token *count* at the
same fixed `ESTIMATE_CENTS_PER_MILLION_TOKENS = 300` placeholder rate used
for the full `:est` estimate; `cost_cents` there is "real tokens, invented
price," not a genuine invoice number either. A reader who needs to
distinguish those two cases today has to consult this table — the ledger
ref alone cannot make the distinction.

No formal error bound is stated or measured for the chars/4 `:est`
heuristic; treat it as a rough order-of-magnitude proxy only. It is least
reliable for inputs where the chars-per-token ratio deviates furthest from
English prose — dense code and non-English text in particular — and no
adapter adjusts the ratio for either case.

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

Fold-time handling (`ledger/fold.py::_handle_spend`, defined by DIP-0034
Phase 1 and hardened same-day by DIP-0034's "Poison-Event Defense"
final-review amendment, consumed unmodified here) accumulates
`payload["cents"]` into `state.spend[actor]` with no task association —
pure per-actor accounting, the shadow-accounting substrate named in
`ENG-2026-0729-016` item 3 — **and** now independently rejects an invalid
`cents` (missing, non-`int`, a `bool` — `bool` is an `int` subclass in
Python — or negative) at the substrate level: the event is skipped (no
balance mutation) and recorded as an orphan (`"{hlc} spend.record
invalid"`) instead of ever being allowed to corrupt a balance.

**Conservation note (corrected from this DIP's earlier draft).** An
earlier version of this section claimed the fold "doesn't enforce [the
conservation invariant] itself" and that `_handle_spend` has "zero
validation of its own." That was accurate against DIP-0034 as originally
drafted, but DIP-0034's same-day final-review wave landed exactly this
validation before this DIP closed — the claim is now stale and is
corrected here. What actually ships, across both layers:

- **Fold-side (`ledger/fold.py::_handle_spend`, DIP-0034)** is the
  substrate-side floor. It protects every `spend.record` writer on the
  ledger — not only this DIP's `run()` — by refusing to ever apply a
  malformed `cents` value: on an invalid value it **skips and orphans**
  the event (no balance mutation, and that event's cost disappears from
  any per-actor total; it is visible only in `LedgerState.orphans`).
  DIP-0034 describes this as "the substrate-side half of the ledger's
  conservation floor."
- **Producer-side (this DIP's `run()`, the cost clamp above)** is
  defense in depth specific to this adapter layer, not the sole
  enforcement point. It normalizes `_invoke`'s return value *before* it
  ever becomes a ledger event, and — unlike the fold's skip-and-orphan
  strategy — **coerces and still emits**: a malformed local measurement
  is floored to `0` and the event is written with an auditable `:clamped`
  ref suffix, so the anomaly stays visible in the actor's own spend
  history instead of disappearing into `orphans`.

Neither layer alone is redundant with the other: the fold-side floor
exists because not every `spend.record` writer on the ledger is this
DIP's `run()`; the producer-side clamp exists because a silently-orphaned
local measurement bug is a worse debugging experience for this adapter's
own caller than a floored-and-flagged one. Budget-ceiling enforcement
(hard-blocking overspend, vs. today's pure observation) remains future
work, per DIP-0034's own Open Question 4 — this DIP does not change that
scope.

### Generator one-way rule

`gen_claude_agents.py` turns the DIP-0016 agent registry into harness
build artifacts (in this section, "artifact" always means a generated
harness-discovery stub file under `out_dir` — a distinct, looser sense
than DIP-0039's `artifact.attest`, which names a specific
content-addressed ledger object; the two are unrelated concepts that
happen to share a word):

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
- **datacore-bench (DIP-0025).** Layer A/B of datacore-bench shells out to
  `claude -p` directly with different MCP configs to run its A/B sessions
  — the same "shells out to a specific harness CLI directly" pattern this
  DIP's own Motivation names as the problem it solves — and is therefore a
  named migration candidate alongside the three above, not previously
  called out. There is also an unclaimed synergy worth recording: DIP-0025's
  own Prerequisites table lists "token usage estimation" as `Unsolved`;
  this DIP's `ExecResult.cost_cents` (real-or-`:est`-marked, per the
  per-adapter table in Specification) is a ready-made candidate answer to
  that open problem once `get_executor()` is wired into bench's harness
  calls. Not claimed done here — named as follow-up, same as the other
  three items.
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

None of these five items block this DIP's Status as Draft — they are
scoped, dated follow-ups on deploy-side files (or, for datacore-bench, a
sibling project) this repo's Phase 8 tasks were never asked to touch,
consistent with how DIP-0037/0039/0040 each recorded their own deploy-side
gates rather than silently claiming integration that hadn't happened.

## Relationship to other DIPs

- **DIP-0034 (Event Ledger Substrate)** defines the `spend.record` event
  type and its Phase 1 fold handler (`_handle_spend`). Its same-day
  final-review "Poison-Event Defense" amendment independently added
  substrate-level rejection of a malformed `cents` value (missing,
  non-`int`, `bool`, or negative) — see the corrected Conservation note
  in Specification. This DIP remains the first concrete `spend.record`
  **producer** whose input is unvalidated upstream data (subprocess/SDK
  output, not hand-constructed ledger data); its producer-side cost clamp
  is a complementary, defense-in-depth layer on top of DIP-0034's
  substrate-side floor, not the sole enforcement point.
- **DIP-0018 (Credential Management)** governs where the credentials this
  DIP's adapters need at runtime (`ANTHROPIC_API_KEY` and any future
  provider credential) are stored and indexed. This DIP defines no
  credential handling of its own — see Specification.
- **DIP-0036 (Config Plane)** is the runtime materialisation surface for
  DIP-0018-governed credentials on a given machine (`~/.datacore/datacore.env`).
  This DIP's adapters consume whatever DIP-0036 (or a CLI's own
  pre-authenticated session) has already made available in the process
  environment; it introduces no config-plane state of its own.
- **DIP-0026 (Architectural Primitives)** catalogues the Adapter Pattern
  (§5) this DIP's `get_executor()`/`register()`/`Executor` is a named
  instance of — see Motivation.
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

## Compatibility

This DIP is **purely additive**; nothing existing changes behavior as a
result of it shipping.

- **Executor registry.** `get_executor()`/`Executor`/the three adapters are
  new modules with zero existing callers (see Integration) — merging this
  DIP changes no runtime behavior anywhere in the repo until a caller is
  migrated onto it, one call site at a time, on its own schedule. The
  direct-CLI call sites this DIP is meant to eventually replace
  (`cos_generate.py`, `cos_reasoning.py`, the nightshift briefing call
  site, datacore-bench's Layer A/B harness calls) keep working completely
  unmodified for as long as they are not migrated; there is no flag-day
  cutover and no deprecation timer attached to this DIP.
- **`spend.record` events.** A new event type on an already-extensible
  substrate — DIP-0034's `fold()` silently ignores event types it has no
  handler for, by design. Emitting `spend.record` events does not change
  how any existing event type folds, and `$DATACORE_NO_SPEND=1` opts a
  process out entirely with no other side effect.
- **`gen_claude_agents.py`.** A new, standalone, mostly-read tool
  (`--check` is fully read-only; `generate` only ever writes inside an
  explicitly-passed `out_dir`, never a default). This DIP's own ruling
  forbids pointing it at this installation's real, symlinked `.claude/`
  tree, so on this installation specifically there is no code path today
  that writes a generated file anywhere the harness would read it. No
  existing file's content or format changes as a result of this DIP.
- **Migration.** None required to adopt this DIP as shipped. Migration
  work exists only on the far side of the separately-scheduled, not-yet-
  started per-caller integration named in Integration above — and even
  then, "migration" for each caller is additive (swap one subprocess call
  for `get_executor(...).run(...)`), not a breaking schema or data change.
- **If DIP-0034 is rejected.** The shadow-accounting half of this DIP has
  nothing to call (`ledger.log.EventLog` and `spend.record`'s fold handler
  both live in DIP-0034) and would need to be withdrawn or re-scoped. The
  executor-abstraction half (`get_executor`/adapters/never-raise/
  `parse_ok`) and the generator half are both independent of DIP-0034's
  fate and remain fully functional either way — see the Rollout Plan in
  Implementation below, which tracks the two halves separately for exactly
  this reason.

## Security Considerations

- **Credentials.** This DIP defines none of its own — see "Credential
  handling — deferred, not defined here" in Specification. `ApiExecutor`
  reads `ANTHROPIC_API_KEY` from the process environment via the Anthropic
  SDK's own resolution; the CLI adapters rely on `claude`/`hermes`'s own
  pre-existing authenticated session. No adapter writes, logs, or echoes a
  credential value; `ExecResult` and the emitted ledger event carry
  prompt-derived text and cost figures only.
- **Never-raise as a hardening property, not only an ergonomics one.**
  Every adapter exception (subprocess failure, timeout, malformed JSON,
  missing binary, missing SDK) is caught inside `run()` and converted to
  `ExecResult.error` — a caller that forgets to wrap a `get_executor()`
  call in its own `try`/`except` cannot crash its own process via this
  seam.
- **Cost clamp as a data-integrity control, not only an accounting
  nicety.** The producer-side clamp (Specification) prevents a malformed
  `_invoke` return value from writing a negative or unparseable `cents`
  figure into the shared ledger; combined with DIP-0034's independent
  substrate-side floor (see the corrected Conservation note in
  Specification), one buggy adapter cannot corrupt another actor's balance
  or the ledger's own conservation invariant.
- **`gen_claude_agents.py` as a write surface.** Its only destructive
  capability is overwriting files under an explicitly-passed `out_dir`; it
  takes no other input, reads only `agents.yaml`, and this DIP's own
  Architecture Finding rules out its only currently-known misuse mode
  (pointing it at the symlinked real `.claude/` tree) in the DIP text
  itself, not merely as an operational aside.
- **Not addressed by this DIP.** Prompt/response content is not
  sanitized, redacted, or rate-limited by any adapter — that remains the
  caller's responsibility, unchanged from before this DIP existed.

## Implementation

### Reference Implementation

Implemented on branch `feat/datacore-v2`, Phase 8 (the release's final
phase), Tasks 8.1–8.3: `.datacore/lib/executors/` (`base.py`,
`claude_code.py`, `hermes.py`, `api.py`, `__init__.py`) and
`.datacore/lib/gen_claude_agents.py`, with their test suites
(`tests/test_executors.py`, `tests/test_gen_claude_agents.py`). See Honest
Status below for the exact gate commands and results this DIP shipped
against.

### Rollout Plan

This DIP bundles two independently rollout-able halves with different
dependency graphs (see the `Depends` metadata field and Compatibility
above):

1. **Executor abstraction + shadow accounting** — depends on DIP-0034
   (unratified Draft). Code is complete and tested against synthetic
   fixtures but has zero real production callers as of this DIP's own
   Draft status (see Integration). Rollout is per-caller migration
   (`cos_generate.py`, `cos_reasoning.py`, the nightshift briefing call
   site, datacore-bench), each swapped onto `get_executor()`
   independently; no flag-day cutover is proposed or required, since every
   unmigrated call site keeps working unmodified.
2. **Generator one-way rule** — depends only on merged DIP-0016. Code is
   complete, tested, and safe to run on any deploy target with its own,
   separate `.claude/` directory (a fresh install, a server deploy without
   this installation's symlink). On this installation specifically it must
   NOT be run against the real tree — see Architecture Finding — so its
   practical rollout here is gated on Open Question 1, not on this DIP's
   own readiness.

The owner's ratification decision should treat these two halves
separately: rejecting DIP-0034 strands only the first, not the second.

### Honest Status (2026-07-30, Task 8.3 — release close)

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

All five Integration items above remain open as of this release. This DIP
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
   `cos_reasoning.py`, the nightshift call site, and datacore-bench are
   named together as "the migration" but not sequenced or scheduled; a
   follow-up task should decide whether they migrate together or
   independently.
3. **Budget-ceiling enforcement** — restated from DIP-0034 Open Question 4:
   shadow accounting is purely observational in this release; whether/how
   overspend should hard-block or escalate is future work once real spend
   data has accumulated.

## References

- `ENG-2026-0718-002` — provider-registry directive (2026-07-18)
- `ENG-2026-0729-016` — ledger-mindset direction (2026-07-29)
- `ENG-2026-0729-030` — signing opt-in amendment (2026-07-30)
- DIP-0016 — Agent Registry & Discoverability
- DIP-0018 — Credential Management
- DIP-0025 — datacore-bench
- DIP-0026 — Architectural Primitives
- DIP-0034 — Event Ledger Substrate
- DIP-0036 — Config Plane
- DIP-0037 — Grounded Briefings (`COS_GROUNDED=1`)
- DIP-0039 — Server-First Artifacts
- DIP-0040 — Agent Consolidation
- Task 8.1 report, Task 8.2 report — implementation detail and the original
  symlink finding this DIP restates and rules on
