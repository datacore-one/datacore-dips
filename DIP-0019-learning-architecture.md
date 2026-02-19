# DIP-0019: Learning Architecture - The Engram Model

| Field | Value |
|-------|-------|
| **DIP** | 0019 |
| **Title** | Learning Architecture - The Engram Model |
| **Author** | Gregor |
| **Type** | Standards Track |
| **Status** | Draft |
| **Created** | 2026-01-23 |
| **Updated** | 2026-01-31 |
| **Tags** | `learning`, `engrams`, `absorption`, `consolidation`, `cognitive`, `ACT-R` |
| **Affects** | `.datacore/learning/`, agents, commands, skills, nightshift |
| **Specs** | `datacore-specification.md`, `DIP-0011-nightshift-module.md`, `DIP-0016-agent-registry.md` |
| **Agents** | `session-learning`, `learning-reviewer` (new) |
| **Skills** | `engram-inject`, `daily-review`, `learn`, `forget` |

## Summary

This DIP establishes an engram-based learning architecture that replaces the write-only pattern capture loop with individually addressable, activation-weighted learning units (engrams). Learnings are captured as raw patterns (unchanged), promoted to engrams through daily review, injected into agent context at runtime via a skill-based hook, and optionally abstracted for cross-domain transfer.

**Key changes from v1:**
- Engrams replace flat pattern files as the active memory store
- ACT-R-inspired activation/forgetting replaces unbounded accumulation
- Daily review replaces batch nightshift absorption
- Runtime injection via `engram-inject` skill replaces baking into CLAUDE.md
- Abstract engrams enable knowledge transfer across domains and Datacores

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
- [DIP-0004](./DIP-0004-knowledge-database.md) - Datacortex for semantic retrieval
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
  statement: "Validate org-mode syntax before writing to .org files."
  rationale: "Three incidents of malformed entries in January 2026."
  contraindications:
    - "Quick-capture to inbox where speed > validation"
  source_patterns: [PAT-2026-0125-003, PAT-2026-0129-001]
  derivation_count: 3         # Independent times captured (from duplicates)
  activation:
    retrieval_strength: 0.85   # Decays with time (ACT-R base-level)
    storage_strength: 0.6      # Only increases (reinforcement, consolidation)
    frequency: 5
    last_accessed: 2026-01-30
  feedback_signals: {positive: 3, negative: 0, neutral: 2}
  provenance: {origin: "user/personal", chain: [], license: "cc-by-sa-4.0"}
  tags: [org-mode, validation]
  abstract: null               # Reference to ABS-ID if user has generalized
  derived_from: null           # If re-instantiated from foreign abstract engram
```

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

### 4. Three-Stage Injection Selection

When an agent runs, `engram-inject` skill:
1. **Relevance filter**: Semantic match against current task scope (eliminates ~80%)
2. **Activation ranking**: ACT-R base-level within relevant set
3. **Diversity penalty**: Prevent redundant injection of similar engrams

Cap: 10 directives + 5 "also consider" = 15 max per agent execution.

### 5. Capture Flow (Loop 1 - Unchanged)

`session-learning` agent continues to extract patterns to `patterns.md`, `corrections.md`, `preferences.md`. No changes to this loop.

After session-learning completes, `learning-reviewer` agent runs as a post-step:
1. Reads new patterns.md entries from this session
2. Runs contradiction detection vs active engrams
3. Writes candidates to engrams.yaml (status: candidate)
4. Recalculates decay on all existing engrams

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
  sender: "gregor/personal"
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

#### Skills as Exchange Format

When abstract engrams reach high fitness, they can be promoted to skills -- the ultimate form of absorption (production compilation in ACT-R). Skills are self-contained, follow open standards, and can be distributed via plugin marketplace.

### 10. Integration with /wrap-up

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

### 11. File Structure

```
[space]/.datacore/learning/
  patterns.md              # Raw capture (staging, unchanged)
  corrections.md           # Mistake log (unchanged)
  preferences.md           # Style preferences (unchanged)
  engrams.yaml             # Active memory store (NEW)
  archive/                 # Retired/obsolete entries
    legacy-patterns.md     # Read-only legacy archive
    2025-Q4-patterns.md

.datacore/state/
  knowledge-surfacing.yaml # Knowledge surfacing state
```

### 12. Migration Strategy

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

### Cognitive Architecture Mapping

| Datacore Component | Cognitive Analog | Source |
|--------------------|------------------|--------|
| patterns.md | Episodic memory (raw episodes) | Tulving |
| engrams.yaml | Semantic memory (consolidated) | McClelland |
| Activation decay | Base-level learning equation | ACT-R |
| Reconsolidation | Memory reconsolidation | Nader et al. |
| Abstract engrams | Schema abstraction | Bartlett |
| engram-inject | Retrieval (spreading activation) | ACT-R |
| Compiled to CLAUDE.md | Production compilation | ACT-R |

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

## Implementation

### Phase 1: Core Infrastructure
- Create `engrams.yaml` schema and per-space files
- Create `engram_selector.py` script
- Create `engram-inject` skill
- Create `daily-review` skill
- Create `learn` and `forget` skills
- Create `learning-reviewer` agent

### Phase 2: Integration
- Add Step 5b to `/wrap-up`
- Deferred review support in `/today`
- Register new agents in registry

### Phase 3: Migration
- One-time consolidation pass on existing 18K lines
- Apply 96 operational items to system
- Archive 51 obsolete entries
- Queue 215 candidates for daily review

### Phase 4: Exchange Protocol
- `learning-publisher` agent for promoting to exchange
- `learning-subscriber` agent for importing
- Skills-as-exchange-format pipeline

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

### Cognitive Science
- Anderson, J.R. (1995). *Cognitive Psychology and its Implications*. W.H. Freeman.
- Bartlett, F.C. (1932). *Remembering*. Cambridge University Press.
- Clark, A. & Chalmers, D. (1998). The extended mind. *Analysis*, 58(1), 7-19.
- Gick, M.L. & Holyoak, K.J. (1983). Schema induction and analogical transfer. *Cognitive Psychology*, 15(1), 1-38.
- McClelland, J.L. et al. (1995). Why there are complementary learning systems. *Psychological Review*, 102(3), 419-457.
- Nader, K. et al. (2000). Fear memories require protein synthesis in the amygdala for reconsolidation. *Nature*, 406, 722-726.

---

*This DIP supersedes the v1 three-loop architecture based on empirical findings from a corpus audit of 518 learnings across 5 locations.*
