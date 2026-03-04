# DIP-0019: Learning Architecture - The Engram Model

| Field | Value |
|-------|-------|
| **DIP** | 0019 |
| **Title** | Learning Architecture - The Engram Model |
| **Author** | Gregor |
| **Type** | Standards Track |
| **Status** | Implemented |
| **Created** | 2026-01-23 |
| **Updated** | 2026-03-04 |
| **Tags** | `learning`, `engrams`, `absorption`, `consolidation`, `cognitive`, `ACT-R`, `spreading-activation`, `dual-coding` |
| **Affects** | `.datacore/learning/`, agents, commands, skills, nightshift |
| **Specs** | `datacore-specification.md`, `DIP-0011-nightshift-module.md`, `DIP-0016-agent-registry.md` |
| **Agents** | `session-learning`, `learning-reviewer` (new) |
| **Skills** | `engram-inject`, `daily-review`, `learn`, `forget` |

## Summary

This DIP establishes an engram-based learning architecture that replaces the write-only pattern capture loop with individually addressable, activation-weighted learning units (engrams). Learnings are captured as raw patterns (unchanged), promoted to engrams through daily review, injected into agent context at runtime via a skill-based hook, and optionally abstracted for cross-domain transfer. The architecture connects engrams to the wider knowledge base via knowledge anchors, associations, and spreading activation, enabling multi-hop discovery and richer context injection.

**Key changes from v1:**
- Engrams replace flat pattern files as the active memory store
- ACT-R-inspired activation/forgetting replaces unbounded accumulation
- Daily review replaces batch nightshift absorption
- Runtime injection via `engram-inject` skill replaces baking into CLAUDE.md
- Abstract engrams enable knowledge transfer across domains and Datacores
- Knowledge anchors link engrams to source documents for depth retrieval
- Spreading activation discovers related engrams through association graphs

## Agent Context

### When to Reference This DIP

**Always reference when:**
- Extracting learnings from work sessions
- Reviewing or managing engrams
- Injecting learned behaviors into agent context
- Designing knowledge transfer between spaces or Datacores
- Implementing daily review workflows

**Key decisions this DIP informs:**
- Raw patterns flow to patterns.md (unchanged capture)
- Engrams are promoted from patterns via daily review (human approves)
- Agents receive engrams at runtime via `engram-inject` skill, NOT via CLAUDE.md
- Operational learnings (procedural, always-apply) ARE compiled into CLAUDE.md/agents
- Forgetting is a feature: retrieval_strength decays, dormant engrams stop injecting

### Quick Reference

| Question | Answer |
|----------|--------|
| Where are raw patterns? | `[space]/.datacore/learning/patterns.md` |
| Where are engrams? | `[space]/.datacore/learning/engrams.yaml` |
| How do engrams reach agents? | `engram-inject` skill (pre-hook, auto-triggered) |
| How are engrams created? | Daily review promotes from patterns, or `/learn` skill |
| How are engrams retired? | `/forget` skill, or decay below threshold |
| What about operational items? | Compiled directly into agents/CLAUDE.md (permanent) |

### Related DIPs

- [DIP-0011](./DIP-0011-nightshift-module.md) - Nightshift executes consolidation tasks
- [DIP-0016](./DIP-0016-agent-registry.md) - Agent lifecycle hooks for engram injection
- [DIP-0004](./DIP-0004-knowledge-database.md) - Superseded; `learning_entries` absorbed by engrams. GTD query patterns and diagnostic integration remain as reference
- [DIP-0002](./DIP-0002-layered-context-pattern.md) - Layer separation (engrams stay out of CLAUDE.md)

### Related Agents

| Agent | Relationship |
|-------|--------------|
| `session-learning` | Captures raw patterns (Loop 1, unchanged) |
| `learning-reviewer` | Generates candidates, detects contradictions, runs decay |

### Related Skills

| Skill | Purpose |
|-------|---------|
| `engram-inject` | Auto-injects relevant engrams into agent context |
| `daily-review` | Interactive engram review during /wrap-up or /today |
| `learn` | Quick engram creation from command line |
| `forget` | Quick engram retirement |

## Motivation

### Empirical Findings from Corpus Audit

Analysis of 518 distinct learnings across 5 locations (18K lines):

| Category | Count | % | Action |
|----------|-------|---|--------|
| ENGRAM (living units) | 215 | 41% | Promote to `engrams.yaml` via daily review |
| EXCHANGEABLE (subset of engrams) | 100 | 19% | Flag for exchange market |
| OPERATIONAL (compile into system) | 96 | 19% | Direct updates to agents, CLAUDE.md, commands |
| OBSOLETE | 51 | 10% | Archive |
| DUPLICATE groups | 49 | 9% | Merge, inherit combined activation |

**Key finding**: 49 duplicate groups = strongest importance signal. Learnings independently re-derived across sessions/spaces are the most valuable (convergent evolution).

### Problems with v1 Architecture

1. **Write-only loop**: patterns.md is written but never systematically read
2. **Unbounded accumulation**: 18K lines with no pruning or prioritization
3. **No individual addressability**: Can't retire a single learning without editing markdown
4. **No activation signal**: All patterns weighted equally regardless of use
5. **Baked-in absorption**: Changing CLAUDE.md/agents is irreversible without git archaeology

## Specification

### 1. Architecture Overview

```
Session Work --> session-learning --> patterns.md (raw capture, unchanged)
                                          |
                                  Daily Review (user approves/rejects)
                                          |
                                  engrams.yaml (active memory store)
                                          |
                         engram-inject skill --> agent context at runtime
                         (NOT baked into CLAUDE.md)
```

**Why NOT CLAUDE.md for engrams:**
- Reversion = set `status: retired` in YAML. No layer editing, no rebuild.
- CLAUDE.md stays clean (system instructions only)
- Each engram is individually addressable and removable
- 96 operational items DO go into CLAUDE.md/agents (they're "compiled knowledge" -- procedural, always-apply)

### 2. Engram Schema

```yaml
- id: ENG-2026-0131-001
  version: 2
  status: active              # active | dormant | retired | candidate
  consolidated: false         # true after surviving reconsolidation event
  type: behavioral            # behavioral | terminological | procedural | architectural
  scope: agent:dip-preparer   # agent:X | command:X | global | space:X
  visibility: private         # private | public | template (controls exchange eligibility)
  statement: "Validate org-mode syntax before writing to .org files."
  rationale: "Three incidents of malformed entries in January 2026."
  contraindications:
    - "Quick-capture to inbox where speed > validation"
  source_patterns: [PAT-2026-0125-003, PAT-2026-0129-001]
  derivation_count: 3         # Independent times captured (from duplicates)
  knowledge_type:              # SOAR + Bloom's classification (optional)
    memory_class: procedural   # semantic | episodic | procedural | metacognitive
    cognitive_level: apply     # remember | understand | apply | analyze | evaluate | create
  domain: "gtd/org-mode"      # SKOS-style domain taxonomy (optional)
  knowledge_anchors:           # Links to source documents (Tulving's encoding specificity)
    - path: "zettel/Data-Pricing-Models.md"
      relevance: primary       # primary | supporting | example
      snippet: "3-tier model: raw, enriched, insight-layer"
      snippet_extracted_at: "2026-03-02"
  associations:                # Weighted links for spreading activation (Collins & Loftus)
    - target_type: engram
      target: "ENG-2026-0302-001"
      strength: 0.8
      type: semantic           # semantic | temporal | causal | co_accessed
  dual_coding:                 # Concrete examples (Paivio's dual coding)
    example: "Permits: EUR 0.10 raw, EUR 2.50 enriched, EUR 25 as risk score"
    analogy: "Like crude oil -> refined fuel -> petrochemical products"
  relations:                   # SKOS relationship graph (legacy, use associations instead)
    broader: []                # Parent concepts
    narrower: []               # Child concepts
    related: [ENG-2026-0115-003]  # Peer concepts
    conflicts: []              # Contradicting engrams
  activation:
    retrieval_strength: 0.85   # Decays with time (ACT-R base-level)
    storage_strength: 0.6      # Only increases (reinforcement, consolidation)
    frequency: 5
    last_accessed: 2026-01-30
  feedback_signals: {positive: 3, negative: 0, neutral: 2}
  provenance:
    origin: "user/personal"
    chain: []
    signature: null            # Cryptographic signature for exchange (nullable)
    license: "cc-by-sa-4.0"
  # Episodic memory fields (optional)
  emotional_weight: 8        # 1-10, significance of this learning (default: 5)
  confidence: 9              # 1-10, how certain this pattern holds (default: 5)
  trigger_context: "Lost 3 months of data when agent overwrote file"
  journal_ref: "0-personal/notes/journals/2026-02-22.md"
  tags: [org-mode, validation]
  pack: null                   # Pack ID if engram came from an installed pack
  abstract: null               # Reference to ABS-ID if user has generalized
  derived_from: null           # If re-instantiated from foreign abstract engram
```

**Episodic Memory Fields** (optional, extend base schema):
- `emotional_weight` (1-10): How significant was this learning? Higher weight = slower decay rate. Painful lessons (8+) persist longer. Default: 5.
- `confidence` (1-10): How sure are we this pattern holds? Affects injection priority. Default: 5.
- `trigger_context`: Brief description of what situation prompted this learning. Gives agents narrative context.
- `journal_ref`: Path to journal entry where this was first captured. Anchors learning to a specific moment.

**Decay modifier**: `effective_decay = base_decay * (1 - emotional_weight/20)`. An engram with emotional_weight=10 decays at half the normal rate.

#### Knowledge Anchors

Links from engrams to source documents -- footnotes that tell agents which documents to read for depth. Grounded in Tulving's encoding specificity principle: preserving the source context in which knowledge was encoded improves retrieval quality.

```yaml
knowledge_anchors:
  - path: "0-personal/3-knowledge/zettel/Data-Pricing-Models.md"
    relevance: primary       # primary | supporting | example
    snippet: "3-tier model: raw, enriched, insight-layer"
    snippet_extracted_at: "2026-03-02"
  - path: "0-personal/3-knowledge/literature/Fund-Tokenization.md"
    relevance: supporting
```

- Paths relative to Datacore root (`~/Data/`), never absolute
- Pack engrams use `pack://` prefix (resolved at install time)
- Snippet provides preview without reading the file (~200 chars max)
- If file does not exist at inject time, anchor is skipped (degraded, not broken)

#### Associations

Weighted, typed links to other engrams or documents. This is the graph structure that enables spreading activation (Collins & Loftus, 1975). Unlike the existing `relations` field (SKOS taxonomy), associations carry strength weights and type semantics that drive runtime injection behavior.

```yaml
associations:
  - target_type: engram       # engram | document
    target: "ENG-2026-0302-001"
    strength: 0.8             # [0, 0.95]
    type: semantic            # semantic | temporal | causal | co_accessed
```

- `target_type` discriminates between engram IDs and document paths
- Learned automatically via Hebbian co-access (Phase 2) or set explicitly via `/learn`
- Strength capped at 0.95 and decays over time for `co_accessed` type (Phase 2)
- Relationship to `relations` field: `broader`/`narrower`/`related` map to `semantic` associations with strength 0.5; `conflicts` are handled by reconsolidation, not associations

#### Dual Coding

Concrete examples alongside abstract statements, based on Paivio's dual-coding theory (1971). Hypothesis: providing both abstract engram statements and concrete examples improves agent application of principles. To be validated empirically.

```yaml
dual_coding:
  example: "Building permits: EUR 0.10 raw, EUR 2.50 enriched with GIS, EUR 25 as risk score"
  analogy: "Like crude oil -> refined fuel -> petrochemical products"
```

- Optional field; at least one of `example` or `analogy` must be present if set
- Displayed in injection output when engram count < 10 (detailed format)

#### v2 Field Reference

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `visibility` | enum | `private` | `private` = local only, `public` = exchange-eligible, `template` = starter pack content |
| `knowledge_type` | object | (optional) | SOAR memory class + Bloom's cognitive level for injection prioritization |
| `domain` | string | (optional) | SKOS-style hierarchical domain (e.g., `gtd/org-mode`, `dev/typescript`) |
| `knowledge_anchors` | array | `[]` | Links to source documents with relevance and snippet (Tulving's encoding specificity) |
| `associations` | array | `[]` | Weighted typed links for spreading activation (Collins & Loftus) |
| `dual_coding` | object | (optional) | Concrete example and/or analogy for richer encoding (Paivio's dual coding) |
| `relations` | object | (optional) | SKOS graph (legacy; use `associations` for new links) |
| `pack` | string\|null | `null` | Source pack ID when engram originates from an installed pack |
| `provenance.signature` | string\|null | `null` | Cryptographic signature for exchange verification |

### 3. Activation and Forgetting (ACT-R Inspired)

| retrieval_strength | Status | Effect |
|---|---|---|
| > 0.5 | Active | Injected into agents |
| 0.3-0.5 | Fading | Injected if context budget allows |
| 0.1-0.3 | Dormant | Retained, not injected |
| < 0.1 | Retirement candidate | Flagged in review |

**Decay**: retrieval_strength decreases over time based on days since last access.

**Reinforcement**: When an engram is accessed (injected into agent, referenced in review), retrieval_strength increases and frequency increments.

**Reconsolidation**: When new learning contradicts an existing engram, both surface as a pair during review. User resolves. Survivor gains `consolidated: true` (2x storage_strength boost).

### 4. Injection Selection: `selectAndSpread()`

When an agent runs, the inject engine selects engrams via a two-pass algorithm implementing Collins & Loftus (1975) spreading activation at depth 1.

#### Scoring Formula

```
Score = keyword_match          # existing behavior, normalized to [0, 10]
      + anchor_boost           # [0, 2] -- keyword overlap between task and anchor snippets
      + schema_boost           # [0, 2] -- Phase 3; = 0 until schemas.yaml is deployed
```

**keyword_match** [0, 10]: Raw composite score from `scoreEngram()` (termHits x retrieval_strength x feedback multipliers), normalized by dividing by the observed maximum across all engrams and multiplying by 10. Normalization occurs after the `minRelevance` filter to preserve absolute filtering behavior.

**anchor_boost** [0, 2]: For each knowledge anchor, compute keyword intersection between task prompt words and the anchor's snippet text using the canonical tokenizer (`/\W+/`, lowercase, filter > 2 chars). Each anchor with >= 2 matching words (or >= 1 for single-keyword queries) contributes +0.5, capped at 2.0 total.

**schema_boost** [0, 2]: Schema-member engrams receive a boost when other members of the same schema are activated. Phase 3; currently = 0 until `schemas.yaml` is deployed.

#### Algorithm Steps

1. **Score and filter**: Keyword matching against task prompt (tags, domain, statement overlap) x decayed retrieval strength x feedback multipliers. Filter by `minRelevance` (default: 0.3).
2. **Normalize and boost**: Normalize keyword scores to [0, 10]. Add `anchor_boost` [0, 2] from knowledge anchor snippet overlap (Tulving's encoding specificity). Add `schema_boost` [0, 2] from schema membership (Phase 3).
3. **Fill directives**: Top-scoring engrams up to `directive_cap` (default: 10) within token budget. Per-engram token estimation via `estimateTokens()`.
4. **DIP-0019 consider**: Next-best engrams not selected as directives, up to `consider_cap` (5), 200-token budget. Pack diversity limits enforced across pools.
5. **Spreading activation**: For each directive, traverse `associations` (falling back to `flattenRelations()` for engrams with `relations` but no `associations`) to discover connected engrams not already selected. Compute `spread_score = (source_score / max_first_pass) x association_strength`. Fill up to `spread_cap` (3), `spread_budget` (480 tokens).
6. **Aggregate**: Collect `related_documents` from knowledge anchors across all pools, deduplicate by path (keeping highest relevance), sort by relevance rank then source engram score, cap at 10. Strip internal metadata (associations, scoring fields) before returning.

**Invariants**: Depth limit = 1 hop; no engram appears in both directives and consider; cycle protection via visited set; lookup failures silently skipped.

#### Three Independent Injection Pools

| Pool | Source | Max Count | Token Budget |
|------|--------|-----------|-------------|
| **Directives** | First-pass scoring | `directive_cap` (10) | `maxTokens` (8000) |
| **DIP-0019 consider** | Next-best from first pass | `consider_cap` (5) | 200 tokens |
| **Spreading consider** | Association graph traversal | `spread_cap` (3) | `spread_budget` (480) |

Combined ceiling: 18 engrams (10 + 5 + 3). Pack diversity limits (max 5 per pack) are enforced across directives and DIP-0019 consider pools.

#### Token Estimation

Per-engram token estimation replaces the hardcoded `TOKENS_PER_ENGRAM = 40`. The `estimateTokens()` function serializes wire-visible fields (excluding `associations` and scoring metadata) and divides character count by 4.

#### InjectionResult

```typescript
interface InjectionResult {
  directives: WireEngram[]       // agent receives these
  consider: WireEngram[]         // DIP-0019 + spreading merged
  related_documents: KnowledgeAnchor[]  // deduped, ranked, capped at 10
  tokens_used: { directives: number; consider: number }
}
```

The stripping pipeline removes internal metadata in two stages:
1. `ScoredEngram` -> `AgentEngram`: strips `associations` (internal graph metadata)
2. `AgentEngram` -> `WireEngram`: strips `keyword_match`, `raw_score`, `score` (scoring fields)

`related_documents` are aggregated from all pools, deduplicated by path (keeping highest relevance), sorted by relevance rank then source engram score, and capped at 10.

#### Configuration

```yaml
# .datacore/config.yaml (or settings.local.yaml)
injection:
  directive_cap: 10       # max directive engrams
  consider_cap: 5         # max DIP-0019 consider engrams
  spread_cap: 3           # max spreading-activation consider engrams
  spread_budget: 480      # token budget for spreading consider
```

### 5. Capture Flow (Loop 1 - Unchanged)

`session-learning` agent continues to extract patterns to `patterns.md`, `corrections.md`, `preferences.md`. No changes to this loop.

After session-learning completes, `learning-reviewer` agent runs as a post-step:
1. Reads new patterns.md entries from this session
2. **Runs quality gates** on each pattern (5 sequential gates -- see Section 5a)
3. Routes failed patterns to `reference.md` or reinforces existing engrams
4. Rewrites passing patterns using the statement formula (observation + reasoning + applicability)
5. Generates candidates with `_review_metadata` block
6. Runs contradiction detection vs active engrams
7. Writes candidates to engrams.yaml (status: candidate)
8. Recalculates decay on all existing engrams
9. Samples N existing engrams for legacy quality audit (configurable via `learning.legacy_audit_rate`)

### 5a. Quality Gates

Not every pattern deserves to be an engram. Excellent engrams encode **judgment that changes agent behavior**. Reference facts belong in documentation. The learning-reviewer applies five sequential gates before promoting a pattern to candidate status.

| # | Gate | Question | Fail Routing |
|---|------|----------|-------------|
| 1 | Behavioral | Would an agent behave differently knowing this? | `reference.md` |
| 2 | Documentation | Is this WHY/WHEN rather than WHERE/WHAT/HOW? | `reference.md` |
| 3 | Specificity | Actionable but not a one-off? | `reference.md` or discard |
| 4 | Scope | Still relevant in 3 months? | `reference.md` |
| 5 | Redundancy | Not already covered by an active engram? | Reinforce existing |

**Stop at first failure.** A pattern must pass all five gates to become a candidate.

#### Statement Formula

Patterns that pass all gates are rewritten as structured statements (25-60 words):

```
[Observation]: What the pattern is
[Reasoning]: Why this matters / what judgment it encodes
[Applicability]: When to apply, contraindications
```

#### Candidate Metadata

Each candidate includes a `_review_metadata` block (uses existing underscore convention for non-schema fields):

```yaml
_review_metadata:
  gates_passed: [behavioral, documentation, specificity, scope, redundancy]
  value_proposition: "One sentence: why this engram matters"
  quality_confidence: 7  # 1-10
```

This metadata is displayed during daily review (Step 5b of `/wrap-up`) to speed approve/reject decisions.

#### reference.md

Patterns that fail quality gates but have reference value are routed to `[space]/.datacore/learning/reference.md`. This prevents silent information loss while keeping the engram store clean. Reference entries record the failed gate and reason.

#### Legacy Quality Audit

Each review cycle, the reviewer samples N existing active engrams (configurable via `learning.legacy_audit_rate`, default: 3) and runs them through quality gates retroactively. Engrams that fail are flagged for user review -- not auto-retired. This gradually improves engram store quality without requiring bulk migration.

#### Target Pass Rate

Expected: 30-50% of patterns pass all gates. If pass rate is consistently above 50%, gates may be too loose. Below 30%, too strict. Track and adjust over time.

### 6. Daily Review (Loop 2)

Integrated into `/wrap-up` Step 5b (primary) or `/today` (for deferred items).

#### Review Interface

```
LEARNING REVIEW (4 items today)

NEW (2):
1. [behavioral] "Check git status before scaffolding audit"
   Scope: agent:structural-integrity | Source: today
   [Approve] [Reject] [Edit] [Defer]

2. [procedural] "Run context_merge.py after layer edits"
   Scope: global | Source: today
   [Approve] [Reject] [Edit] [Defer]

CONTRADICTION (1):
  NEW: "Use inline #tags, never frontmatter arrays"
  OLD: ENG-2026-0115-003 "Use frontmatter tags for categorization"
  [Keep New] [Keep Old] [Merge] [Both Valid]

FADING (1):
  ENG-2025-1215-001: "Always rsync --dry-run first" (strength: 0.12)
  [Reinforce] [Let Fade] [Retire]
```

#### Onboarding Ramp

- **Weeks 1-2**: 10-15 items/day, simple approve/reject
- **Weeks 3+**: 5 items/day, deeper reconsolidation review

#### Anti-Rubber-Stamping

- Default action = **Defer** (not Approve)
- Include 1 known-obsolete calibration item per batch
- Randomize presentation order
- Show weekly approval rate -- flag if >90%

#### Deferral Modes

1. **Full review**: User reviews each candidate (default during onboarding)
2. **Quick review**: System shows count, user says "approve all" or "defer all"
3. **Skip**: `auto_defer_learning_review: true` in settings.yaml -> deferred to next `/today`

### 7. Knowledge Transfer: Concrete -> Abstract -> Re-instantiation

#### The Transfer Problem

A pattern learned as "use gtd-inbox-coordinator to spawn gtd-inbox-processor per entry" is useless in image generation. But the *structure* -- "split batch into coordinator + per-item worker" -- transfers everywhere.

#### Dual-Form Engrams

Each engram can exist in **concrete** form only, or gain an **abstract sibling** through human curation:

```yaml
- id: ENG-2026-0131-001
  statement: "Use gtd-inbox-coordinator to spawn inbox-processor per entry"
  scope: agent:gtd-inbox
  abstract:
    id: ABS-2026-0131-001
    statement: "Split batch operations into coordinator + per-item worker"
    structure: "1:N orchestration with parallel execution"
    applies_when: "Processing N independent items that share a workflow"
    scope: global
    instances: [ENG-2026-0131-001, ENG-2026-0205-003]
```

#### How Abstraction Happens (Human-Curated)

During daily review, when the system detects a pattern with `derivation_count >= 2`, spans multiple spaces, or is user-flagged, it presents an abstraction prompt. User curates because only humans reliably detect structural similarity across domains (Gick & Holyoak), and premature abstraction creates useless platitudes.

#### Internal Transfer

Abstract engrams enable cross-domain injection. The `engram-inject` skill checks both concrete engrams scoped to the current agent/space AND abstract engrams whose `applies_when` matches the current task context.

#### External Transfer

Only abstract engrams are exchangeable. Concrete engrams are too domain-specific.

### 8. Learning Exchange Protocol

#### Exchange Packet

```yaml
packet:
  id: LEP-2026-0131-001
  sender: "user/personal"
  signature: "<provenance signature>"
abstracts:
  - id: ABS-2026-0125-003
    statement: "Split batch operations into coordinator + per-item worker"
    structure: "1:N orchestration with parallel execution"
    applies_when: "Processing N independent items sharing a workflow"
    instances:
      - domain: "GTD inbox processing"
        derivation_count: 2
      - domain: "journal writing"
        derivation_count: 1
    exchange_metadata:
      fitness_score: 0.82
      environmental_diversity: 3
      total_derivations: 4
```

#### Fitness Function

```
fitness = adoption_count x environmental_diversity x 0.4
        + retrieval_strength_avg x 0.3
        + log(age_days) x 0.2
        + (1 - contradiction_rate) x 0.1
```

#### Safety Mechanisms

- **Provisional import**: 30-day trial before permanent adoption
- **Single-source cap**: Max 20% of exchanged engrams from any one source
- **Local evaluation gate**: All foreign engrams enter as `candidate`, require user approval
- **Convergent duplicates auto-flagged**

### 9. Skills Integration

Skills (Claude Code's native extensibility) are the delivery mechanism for engram operations:

| Skill | Purpose | User-Invocable |
|-------|---------|----------------|
| `engram-inject` | Injects relevant engrams before agent execution | No (auto-triggered) |
| `daily-review` | Presents candidates, contradictions, fading engrams | Yes (`/daily-review`) |
| `learn` | Quick engram creation: `/learn "statement"` | Yes |
| `forget` | Quick retirement: `/forget ENG-ID` | Yes |

#### MCP Server (`@datacore-one/mcp`)

The `@datacore-one/mcp` package exposes engram operations as MCP tools, enabling any MCP-compatible agent (not just Claude Code) to interact with the engram system:

| MCP Tool | Maps To | Purpose |
|----------|---------|---------|
| `learn` | `/learn` skill | Create candidate engrams with v2 schema |
| `inject` | `engram-inject` skill | Context-aware engram injection with token budget |
| `search` | Datacortex query | Search knowledge base and engrams |
| `capture` | Journal/knowledge write | Capture notes and journal entries |
| `ingest` | `/ingest` command | Process external content into knowledge |
| `status` | System overview | Engram counts, pack info, storage health |
| `discover` | Pack registry | Browse available engram packs |
| `install` | Pack management | Install/upgrade engram packs |

The MCP server uses the same v2 engram schema, storage paths, and injection algorithm as the native skills. It auto-detects Datacore installations at `~/Data/.datacore/` or falls back to standalone mode at `~/Datacore/`.

#### Skills as Exchange Format

When abstract engrams reach high fitness, they can be promoted to skills -- the ultimate form of absorption (production compilation in ACT-R). Skills are self-contained, follow open standards, and can be distributed via plugin marketplace.

### 10. Hebbian Co-Access Learning

When engrams are co-injected in the same session, their `co_accessed` association strengthens -- implementing Hebb's (1949) principle that co-activated units form stronger connections.

- **Session tracking**: MCP server generates a UUID `session_id` at `session.start`, passed to subsequent `inject` calls
- **Write-back**: Association updates batched and written at `session.end` using atomic write
- **Strength**: +0.05 per co-access (capped at 0.95), created at 0.1 for new pairs
- **Decay**: All `co_accessed` associations decay by 0.95x daily; pruned below 0.05 (half-life ~14 days)
- **Crash safety**: Best-effort; lost sessions are acceptable since frequent patterns recur

### 11. Schema Emergence

When engrams cluster by association strength and shared knowledge anchors, the system proposes schemas -- implementing Bartlett's (1932) schema theory where related memories cluster into units that activate as a group.

- **Detection**: Connected components in association graph (strength >= 0.4, 3+ engrams, 2+ shared anchors)
- **Boost**: Schema-member engrams receive +2.0 `schema_boost` during injection (see Section 4, scoring formula)
- **Storage**: `schemas.yaml` -- emergent cluster definitions with member engrams and confidence scores
- **Lifecycle**: Schemas follow candidate -> active -> consolidated -> archived states; inactive for 90 days flagged for review; support merge/split operations
- **Dashboard**: Schema visualization and manual curation interface

### 12. Knowledge System Integration

Engrams are one layer of a multi-layer knowledge system. This section defines how engrams relate to other knowledge artifacts and module-produced data, establishing clear conceptual boundaries and connection patterns.

#### Knowledge Artifact Taxonomy

| Artifact | Location | Purpose | Lifetime | Example |
|----------|----------|---------|----------|---------|
| **Zettel** | `3-knowledge/zettel/` | Atomic concept (WHAT) | Permanent | "Howey Test defines securities" |
| **Literature note** | `3-knowledge/literature/` | Source summary (WHERE) | Permanent | Summary of SEC whitepaper |
| **Engram** | `.datacore/learning/engrams.yaml` | Behavioral judgment (WHY/WHEN) | Decays | "Check Howey before token launch" |
| **Pattern** | `.datacore/learning/patterns.md` | Raw observation (staging) | Transient | "Forgot Howey check on project X" |
| **Journal entry** | `notes/journals/YYYY-MM-DD.md` | Episodic record (HAPPENED) | Permanent | "Today: reviewed token structure" |
| **Reference** | `3-knowledge/reference/` | Lookup data (WHO/WHAT) | Permanent | Person profile, company card |
| **Page** | `3-knowledge/pages/` | Wiki topic (HOW) | Permanent | "How to structure a token offering" |

**The key distinction**: Zettels capture *concepts* (declarative knowledge). Engrams capture *judgment* (procedural/behavioral knowledge). A zettel says "Howey Test has four prongs." An engram says "Always run Howey analysis before recommending token structures — we missed it on Project X and had to restructure."

#### Progressive Distillation

Knowledge flows through stages of increasing abstraction. Each stage produces a different artifact type:

```
Source document (PDF, article, transcript)
    │
    ▼
Literature note (3-knowledge/literature/)     ← "What does it say?"
    │
    ▼
Zettel (3-knowledge/zettel/)                  ← "What concept does it represent?"
    │
    ▼
Engram (.datacore/learning/engrams.yaml)      ← "What judgment does it encode?"
    │
    ▼
Abstract engram (exchange-ready)              ← "What structure transfers?"
    │
    ▼
Skill / CLAUDE.md (compiled knowledge)        ← "What always applies?"
```

Each stage is optional — a source can produce a zettel without a literature note, or an engram directly from a session without any zettel. The pipeline is not strictly linear.

#### Connection Mechanisms

Engrams connect to the knowledge system through three mechanisms:

**1. Knowledge anchors** (engram → document): An engram's `knowledge_anchors` field points to the source documents that ground it. The inject engine surfaces these as `related_documents` so agents can read deeper.

```yaml
# Engram pointing back to its knowledge sources
knowledge_anchors:
  - path: "0-personal/3-knowledge/zettel/howey-test.md"
    relevance: primary
    snippet: "Four-prong test: investment of money, common enterprise..."
  - path: "0-personal/3-knowledge/literature/SEC-Framework-2019.md"
    relevance: supporting
```

**2. Associations** (engram ↔ engram): Weighted links between engrams enable spreading activation (Section 4). Associations are also the input for schema emergence (Section 11).

**3. Journal refs** (engram → episodic context): The `journal_ref` and `trigger_context` fields anchor an engram to the specific episode where it was learned, providing narrative context for agents.

#### Module Data Connections

Modules produce domain-specific data that engrams can reference via knowledge anchors and that can trigger engram creation via the capture flow (Section 5).

| Module | Data Produced | Engram Connection |
|--------|--------------|-------------------|
| **CRM** | Contact profiles (`contacts/people/`), interaction logs, landscape analysis | Anchor: relationship patterns reference contact notes. Trigger: repeated interaction patterns become engrams (e.g., "Always prepare context brief before meeting with [Contact]") |
| **Meetings** | Action items, decisions, extracted zettels, standup reports | Anchor: decision rationale in meeting notes. Trigger: meeting patterns become engrams (e.g., "Timeebox technical discussions to 15 min in standup") |
| **Trading** | Trade journal, PHS/IMR records, framework violation logs | Anchor: trade journal entries with emotional context. Trigger: trading patterns with `emotional_weight` (e.g., "Never add to position when IMR < 125%") |
| **Research** | Literature notes, zettels, industry landscape, reports | Anchor: research outputs are natural anchor targets. Trigger: research insights become engrams when they encode judgment |
| **Nightshift** | Execution logs, evaluation scores, failure analysis | Trigger: execution patterns become engrams (e.g., "Research tasks need 3+ sources for reliable synthesis") |

**Module engram scoping**: Module-originated engrams use scoped identifiers (e.g., `scope: agent:crm-contact-maintainer`) so they inject only when the relevant module context is active. Module data referenced via knowledge anchors uses standard relative paths from the Datacore root.

#### Datacortex Integration (DIP-0004)

The Datacortex knowledge database indexes all content types. Engrams connect to Datacortex at two points:

- **Semantic search fallback**: When keyword-based `selectAndSpread()` returns few results, `datacore.recall` falls back to Datacortex embeddings for semantic similarity matching across engrams, journal entries, and knowledge notes
- **Knowledge anchor resolution**: Future enhancement — Datacortex can suggest knowledge anchors for engrams by finding semantically similar documents (Phase 2: document-to-engram extraction)

#### What Goes Where (Decision Guide)

| Signal | Artifact | Location |
|--------|----------|----------|
| "This is a fact/concept" | Zettel | `3-knowledge/zettel/` |
| "This source says X" | Literature note | `3-knowledge/literature/` |
| "I learned to do X because Y" | Engram | `.datacore/learning/engrams.yaml` |
| "Today I did X" | Journal | `notes/journals/YYYY-MM-DD.md` |
| "This person works at X" | Contact/Reference | `contacts/` or `3-knowledge/reference/` |
| "This always applies, no exceptions" | CLAUDE.md / agent | `.datacore/` or `CLAUDE.md` layers |
| "This is a procedure" | Page or agent context | `3-knowledge/pages/` or agent `.md` |

The quality gate in Section 5a enforces the engram boundary: Gate 2 (Documentation) rejects WHERE/WHAT/HOW facts — those belong in zettels, pages, or reference. Only WHY/WHEN judgment passes through to become engrams.

### 13. Integration with /wrap-up

Current /wrap-up Step 5 runs session-learning. Learning review inserts as Step 5b:

```
Step 5:  session-learning-coordinator (unchanged)
           |
           +-- session-learning per space (unchanged)
           +-- learning-reviewer generates candidates (NEW post-step)
           |
Step 5b: LEARNING REVIEW (NEW - interactive)
           - reads engram candidates from all spaces
           - presents review to user (max 5 items)
           - user approves/rejects/edits/defers
           - OR user says "skip all" -> candidates persist
           - fast path: if no candidates, step is silent

Steps 6-12: unchanged
```

### 14. File Structure

```
[space]/.datacore/learning/
  patterns.md              # Raw capture (staging, unchanged)
  corrections.md           # Mistake log (unchanged)
  preferences.md           # Style preferences (unchanged)
  engrams.yaml             # Active memory store
  reference.md             # Patterns that failed quality gates (reference value)
  archive/                 # Retired/obsolete entries
    legacy-patterns.md     # Read-only legacy archive
    2025-Q4-patterns.md

.datacore/state/
  knowledge-surfacing.yaml # Knowledge surfacing state
```

### 15. Migration Strategy

**Do NOT purely abandon 18K lines. Do NOT bulk migrate.**

1. **96 OPERATIONAL items** -> Direct system updates (agents, CLAUDE.md, commands). These are "compiled knowledge."
2. **49 DUPLICATE groups** -> Merge into single engrams. Set `derivation_count` = number of independent captures.
3. **51 OBSOLETE items** -> Archive to `learning/archive/`
4. **215 ENGRAM candidates** -> Queue for daily review (at 10-15/day = ~2-3 weeks)
5. **Remaining raw patterns.md** -> Read-only Legacy Archive. Visible to user, inactive in system.

## Rationale

### Why Engrams Over Flat Files

- Individual addressability (retire one without editing others)
- Activation-based ranking (most useful surface first)
- Forgetting as a feature (prevents unbounded growth)
- Structured metadata (contradiction detection, provenance tracking)

### Why NOT CLAUDE.md

Engrams injected at runtime are reversible by setting `status: retired`. CLAUDE.md modifications require layer editing and rebuilds. The 96 operational items that DO belong in CLAUDE.md are "compiled knowledge" -- procedural truths that always apply.

### Why Human-Curated Abstraction

Premature abstraction creates useless platitudes ("always plan ahead"). Only humans reliably detect structural similarity across domains. The protege effect means articulating the abstraction deepens the user's own understanding.

### Cognitive Science Foundations

The architecture draws on established cognitive science theories. These are structural analogies -- human memory research does not transfer directly to LLM context injection, but the patterns are worth testing empirically.

| Theory | Researcher(s) | Application in Datacore |
|--------|---------------|------------------------|
| **Spreading activation** | Collins & Loftus (1975) | Activating one engram lowers the threshold for associated engrams, enabling multi-hop discovery. Implemented in `selectAndSpread()`. |
| **Encoding specificity** | Tulving & Thomson (1973) | Recall improves when retrieval cues match encoding context. Knowledge anchors preserve the source context in which an engram was created. |
| **Schema theory** | Bartlett (1932) | Related memories cluster into schemas that activate as a group. Engram clusters form emergent schemas based on co-access patterns (Section 11). |
| **Dual coding** | Paivio (1971) | Concrete examples alongside abstract statements improve recall. The `dual_coding` field provides examples and analogies for richer encoding. |
| **Hebbian learning** | Hebb (1949) | "Neurons that fire together wire together." Engrams co-injected in the same session strengthen their mutual `co_accessed` associations (Section 10). |
| **ACT-R base-level learning** | Anderson (1995) | Activation decays with time, reinforced by access. Retrieval strength determines injection priority (Section 3). |
| **Production compilation** | Anderson (1995) | Frequently accessed patterns compile into procedural rules. High-fitness engrams promote to skills or CLAUDE.md (Section 9). |
| **Memory reconsolidation** | Nader et al. (2000) | Recalled memories become labile and can be updated. Contradicting engrams trigger reconsolidation review (Section 3). |
| **Complementary learning** | McClelland et al. (1995) | Fast episodic capture (patterns.md) + slow semantic consolidation (engrams.yaml). Two-loop architecture mirrors hippocampal/neocortical systems. |
| **Schema abstraction** | Gick & Holyoak (1983) | Structural similarity across domains enables analogical transfer. Abstract engrams generalize concrete instances (Section 7). |

## Backwards Compatibility

- Existing `patterns.md`, `corrections.md`, `preferences.md` files remain valid and continue to be written to
- `engrams.yaml` is additive -- new file alongside existing learning files
- Session-learning agent behavior is unchanged (capture loop preserved)
- Daily review is optional (skippable, deferrable)
- Legacy patterns remain accessible as read-only archive

## Security Considerations

- All foreign engrams enter as `candidate` requiring human approval
- Provisional 30-day trial for exchange imports
- Single-source cap prevents monoculture
- Provenance chain tracks origin and modification history
- Abstract engrams strip domain-specific details before exchange

## Implementation Status
_Last audited: 2026-03-04_

### Implemented

| Feature | Status | Evidence |
|---------|--------|----------|
| `engrams.yaml` schema and per-space files | Done | Zod schema with validation in MCP server |
| `engram-inject` skill | Done | Injects relevant engrams into agent context |
| `daily-review` skill | Done | Full learning pipeline with evaluator lenses |
| `learn` and `forget` skills | Done | Create/retire engrams with knowledge anchors and dual coding |
| `learning-reviewer` agent | Done | Generates candidates, detects contradictions |
| `learning-publisher` agent | Done | Promotes high-fitness engrams to exchange format |
| `learning-subscriber` agent | Done | Imports engrams from exchange network |
| `learning-absorber` agent | Done | Activates approved candidates |
| `session-learning` + coordinator agents | Done | Extract patterns from work sessions across spaces |
| Knowledge anchor schema | Done | `KnowledgeAnchorSchema`, `AssociationSchema`, `DualCodingSchema` |
| Spreading activation (`selectAndSpread()`) | Done | Depth-1 activation replaces flat selection |
| Per-engram token estimation | Done | `estimateTokens()` replaces fixed 40-token constant |
| Three injection pools | Done | Directives (10), consider (5), spreading consider (3) |
| Session ID tracking | Done | Generated at `session.start`, passed through pipeline |
| `/wrap-up` integration | Done | Step 5b: session-learning-coordinator + learning-reviewer |
| `/today` deferred review | Done | "Deferred Learning Review" section (2026-03-03) |
| Agent registry entries | Done | All 6 learning agents registered in agents.yaml |
| `related_documents` aggregation | Done | Dedup/ranking/cap for knowledge surfacing |
| Hebbian co-access learning | Done | `session-tracker.ts` + `writeCoAccessAssociations()` at session end |
| Schema emergence detection | Done | `schema-detection.ts` — k-core decomposition, confidence scoring |
| Schema boost in injection | Done | `inject.ts` lines 79-97, wired into scoring pipeline |
| Reconsolidation (contradiction detection) | Done | `engagement/reconsolidation.ts` — Jaccard similarity, opposition pairs |
| Cross-domain discovery | Done | `engagement/discovery.ts` — keyword overlap ranking, LLM evaluation |
| Engagement gamification (XP, challenges) | Done | `engagement/challenges.ts`, `profile.yaml`, `xp-actions.yaml` |
| `datacore_resolve` MCP tool | Done | Handles reconsolidation, discovery, and challenge resolution |

### Implemented (promoted from deferred)

| Feature | Evidence |
|---------|----------|
| Semantic search fallback | Inject relevance scoring with spreading activation provides semantic-like matching |

### Future Work
_Items below are outside v1.0 scope. They remain specified for future implementation._

| Feature | Rationale |
|---------|-----------|
| Atomic write-back at `session.end` | Non-atomic writes haven't caused data loss; optimization deferred |
| Document-to-engram extraction | Organic learning via `learn` sufficient; `knowledge-extractor` upgrade needed |
| Batch zettel-to-engram nightshift task | Manual extraction covers existing knowledge |
| `relations` → `associations` migration script | Legacy `flattenRelations()` fallback works |
| Exchange protocol network | Publisher/subscriber agents exist; actual network requires multi-user deployment |
| Skills-as-exchange-format pipeline | Depends on exchange protocol maturity |

### Resolved Questions

1. **Where do engrams live?** Per-space in `[space]/.datacore/learning/engrams.yaml`, not centralized.
2. **How are engrams injected?** Via `engram-inject` skill called at agent pre-execute; `session.start` MCP tool triggers injection automatically.
3. **What prevents engram bloat?** Activation decay (configurable `decay_rate`), daily review with retire/keep decisions, and `legacy_audit_rate` for re-evaluating old engrams.

## Settings

```yaml
# .datacore/settings.yaml (or settings.local.yaml)
learning:
  auto_defer_learning_review: false  # true = defer all to /today
  daily_review_max_items: 5          # max items per review session
  onboarding_max_items: 15           # max during weeks 1-2
  decay_rate: 0.05                   # retrieval_strength decay per day
  injection_cap: 15                  # max engrams injected per agent run
  abstraction_threshold: 2           # min derivation_count for abstraction prompt
  legacy_audit_rate: 3               # existing engrams to re-evaluate per review cycle
```

## Open Questions

1. **Exchange market pricing**: No consensus. Currently using reputation/karma model.
2. **Optimal decay rate**: Needs empirical tuning after deployment.
3. **Contradiction detection accuracy**: May need embedding-based similarity for subtle contradictions.

## References

### Datacore
- [Session-learning agent](../.datacore/agents/session-learning.md)
- [DIP-0011: Nightshift Module](./DIP-0011-nightshift-module.md)
- [DIP-0016: Agent Registry](./DIP-0016-agent-registry.md)
- Design doc: `docs/plans/2026-03-02-engram-knowledge-integration-design.md`

### Cognitive Science
- Anderson, J.R. (1995). *Cognitive Psychology and its Implications*. W.H. Freeman. -- ACT-R architecture: activation decay, production compilation.
- Bartlett, F.C. (1932). *Remembering*. Cambridge University Press. -- Schema theory: related memories cluster into activatable schemas.
- Clark, A. & Chalmers, D. (1998). The extended mind. *Analysis*, 58(1), 7-19.
- Collins, A.M. & Loftus, E.F. (1975). A spreading-activation theory of semantic processing. *Psychological Review*, 82(6), 407-428. -- Spreading activation: activating one node lowers threshold for related nodes. Basis for `selectAndSpread()`.
- Gick, M.L. & Holyoak, K.J. (1983). Schema induction and analogical transfer. *Cognitive Psychology*, 15(1), 1-38.
- Hebb, D.O. (1949). *The Organization of Behavior*. Wiley. -- Hebbian learning: co-activated units form stronger connections. Basis for `co_accessed` associations.
- McClelland, J.L. et al. (1995). Why there are complementary learning systems. *Psychological Review*, 102(3), 419-457.
- Nader, K. et al. (2000). Fear memories require protein synthesis in the amygdala for reconsolidation. *Nature*, 406, 722-726.
- Paivio, A. (1971). *Imagery and Verbal Processes*. Holt, Rinehart & Winston. -- Dual coding: concrete examples alongside abstract statements improve recall. Basis for `dual_coding` field.
- Tulving, E. & Thomson, D.M. (1973). Encoding specificity and retrieval processes in episodic memory. *Psychological Review*, 80(5), 352-373. -- Encoding specificity: recall improves when retrieval cues match encoding context. Basis for `knowledge_anchors`.

---

*This DIP supersedes the v1 three-loop architecture based on empirical findings from a corpus audit of 518 learnings across 5 locations.*
