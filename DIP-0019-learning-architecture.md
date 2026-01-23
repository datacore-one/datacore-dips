# DIP-0019: Learning Architecture

| Field | Value |
|-------|-------|
| **DIP** | 0019 |
| **Title** | Learning Architecture |
| **Author** | Gregor |
| **Type** | Standards Track |
| **Status** | Draft (Loop 3 partially implemented) |
| **Created** | 2026-01-23 |
| **Updated** | 2026-01-23 |
| **Tags** | `learning`, `patterns`, `absorption`, `consolidation`, `cognitive` |
| **Affects** | `.datacore/learning/`, agents, commands, nightshift |
| **Specs** | `datacore-specification.md`, `DIP-0011-nightshift-module.md`, `DIP-0016-agent-registry.md` |
| **Agents** | `session-learning`, `learning-absorber` (new), `pattern-retriever` (new) |

## Summary

This DIP establishes a three-loop learning architecture that transforms Datacore from passive pattern storage to active knowledge absorption. Currently, `patterns.md` is a write-only loop - patterns are captured but never read or applied. This specification introduces: (1) **Pattern Capture** (existing, enhanced), (2) **Absorption** (new) - consolidating patterns into system upgrades, and (3) **User Learning** (new) - bidirectional learning where users teach the system and the system surfaces knowledge for user retention.

## Agent Context

This section helps agents understand when and how to apply this DIP.

### When to Reference This DIP

**Always reference when:**
- Extracting learnings from work sessions
- Deciding whether a pattern should modify system behavior
- Implementing pattern retrieval before task execution
- Designing consolidation or absorption workflows
- Building user-facing learning features (spaced review, /teach)

**Key decisions this DIP informs:**
- Patterns flow through three loops, not just capture
- Absorption requires approval tiers based on impact
- Agents read relevant patterns BEFORE executing tasks
- Consolidation happens during nightshift, not real-time
- User learning is bidirectional (user ↔ system)

### Quick Reference for Agents

| Question | Answer |
|----------|--------|
| Where are patterns stored? | `[space]/.datacore/learning/patterns.md` |
| When do patterns get absorbed? | Weekly during nightshift consolidation |
| How do I retrieve relevant patterns? | Use `pattern-retriever` agent or datacortex query |
| What approval is needed for absorption? | Depends on target (see Absorption Types table) |
| How do I capture a new pattern? | Use `session-learning` agent |
| Where are corrections logged? | `[space]/.datacore/learning/corrections.md` |

### Related DIPs

- [DIP-0011](./DIP-0011-nightshift-module.md) - Nightshift executes consolidation
- [DIP-0016](./DIP-0016-agent-registry.md) - Agent lifecycle hooks for pattern injection
- [DIP-0004](./DIP-0004-knowledge-database.md) - Datacortex for pattern retrieval

### Related Agents

| Agent | Relationship |
|-------|--------------|
| `session-learning` | Captures patterns (Loop 1) |
| `learning-absorber` | Consolidates patterns into system (Loop 2) |
| `pattern-retriever` | Retrieves relevant patterns before tasks |
| `ai-task-executor` | Invokes pattern-retriever via hooks |

## Motivation

### The Write-Only Loop Problem

Current state analysis from 2025-12-28 session:

1. **patterns.md is write-only**: Session-learning writes patterns, but nothing reads them
2. **Documentation lies**: CLAUDE.md says "agents read patterns before tasks" but no implementation exists
3. **Unbounded accumulation**: Patterns accumulate forever with no consolidation or pruning
4. **No behavior change**: Captured patterns never modify agent behavior or system configuration
5. **One-way teaching**: User teaches system, but system never teaches user

### Cognitive Science Foundation

Research into cognitive architectures (ACT-R, SOAR, MicroPsi) reveals key principles:

| Principle | Source | Implication for Datacore |
|-----------|--------|--------------------------|
| Use strengthens memory | ACT-R base-level learning | Track pattern access; frequently-used patterns surface first |
| Chunking compresses knowledge | SOAR | Successful sequences become reusable units |
| Impasse drives learning | SOAR | Learn when current knowledge is insufficient |
| Sleep consolidates | Complementary Learning Systems | Nightshift abstracts from daily episodes |
| Extended mind | Clark & Chalmers | System is genuine cognitive extension - must be bidirectional |
| Teaching deepens learning | Protege Effect | User learns by explaining to system |

**Key Insight:** Learning should be **absorption**, not consultation. Patterns shouldn't be "read before tasks" - they should be absorbed into the system. The system evolves.

### Use Cases Enabled

1. **Pattern-Aware Execution**: Before writing a DIP, agent retrieves relevant patterns from past DIP authorship
2. **Automatic Agent Improvement**: Pattern "always validate org-mode syntax" becomes validation step in agent
3. **Documentation Auto-Update**: Terminology corrections automatically propagate to CLAUDE.md
4. **User Knowledge Retention**: Spaced review surfaces knowledge the user is likely to forget
5. **Bidirectional Teaching**: User explains concepts to system; system asks clarifying questions

## Specification

### 1. Three-Loop Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LOOP 1: CAPTURE                             │
│  ┌──────────┐    ┌─────────────────┐    ┌─────────────────────┐    │
│  │ Session  │───>│ session-learning │───>│ patterns.md         │    │
│  │ Work     │    │ agent            │    │ corrections.md      │    │
│  └──────────┘    └─────────────────┘    │ preferences.md      │    │
│                                          └─────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        LOOP 2: ABSORPTION                           │
│  ┌─────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │ patterns.md     │───>│ learning-absorber │───>│ System Change │  │
│  │ (staging area)  │    │ (weekly/nightshift)│   │ (approved)    │  │
│  └─────────────────┘    └──────────────────┘    └───────────────┘  │
│                                │                                     │
│                                ▼                                     │
│                    ┌──────────────────────┐                         │
│                    │ Absorption Targets:  │                         │
│                    │ - Agent prompts      │                         │
│                    │ - Command definitions│                         │
│                    │ - CLAUDE.md layers   │                         │
│                    │ - New DIPs           │                         │
│                    └──────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LOOP 3: USER LEARNING                          │
│  ┌─────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │ User teaches    │◄──►│ Bidirectional    │◄──►│ System teaches│  │
│  │ (/teach cmd)    │    │ Learning Engine  │    │ (spaced review│  │
│  └─────────────────┘    └──────────────────┘    └───────────────┘  │
│                                                                      │
│  Features:                                                          │
│  - Spaced repetition for knowledge retention                        │
│  - Active recall questions during reviews                           │
│  - /teach command for user explanation                              │
│  - Clarifying questions that deepen user understanding              │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. Loop 1: Pattern Capture (Enhanced)

#### 2.1 Current State (Preserved)

The `session-learning` agent extracts patterns to:
- `[space]/.datacore/learning/patterns.md` - Successful approaches
- `[space]/.datacore/learning/corrections.md` - Mistakes and fixes
- `[space]/.datacore/learning/preferences.md` - Style preferences

#### 2.2 Enhancements

**Pattern Metadata:**

Each pattern entry gains structured metadata:

```markdown
### Pattern: Validate org-mode syntax before writing

**ID:** PAT-2026-0123-001
**Created:** 2026-01-23
**Source:** Session with DIP-0019 authorship
**Category:** validation
**Frequency:** 3 (times encountered)
**Last Used:** 2026-01-23
**Absorption Status:** pending | absorbed | rejected
**Absorption Target:** agent:dip-preparer (suggested)

**Pattern:**
Always validate org-mode syntax (heading levels, property drawers, timestamps) before writing to .org files.

**Context:**
Encountered malformed org entries during inbox processing. Validation prevents downstream parsing errors.

**Evidence:**
- 2026-01-15: Fixed 3 malformed entries in inbox.org
- 2026-01-20: Caught missing :END: in property drawer
- 2026-01-23: Prevented heading level mismatch
```

**Automatic Categorization:**

| Category | Description | Typical Target |
|----------|-------------|----------------|
| `validation` | Pre-condition checks | Agent hooks |
| `workflow` | Process sequences | Commands |
| `formatting` | Output style | CLAUDE.md, agents |
| `terminology` | Naming conventions | Documentation |
| `architecture` | System structure | DIPs |
| `error-handling` | Recovery patterns | Agent error hooks |

### 3. Loop 2: Absorption

#### 3.1 Absorption Agent

New agent: `learning-absorber`

**Trigger:** Weekly during nightshift (or on-demand via `/absorb-patterns`)

**Process:**
1. Read all patterns with `absorption_status: pending`
2. Classify by category and suggested target
3. For each pattern, determine absorption type
4. Generate proposed changes
5. Apply or queue for approval based on tier

#### 3.2 Absorption Types and Approval Tiers

| Pattern Type | Target | Approval | Example |
|--------------|--------|----------|---------|
| **Documentation** | CLAUDE.md layers | Auto | Fix terminology, add clarification |
| **Terminology** | Docs + agent prompts | Auto | Consistent naming across system |
| **Validation** | Agent pre-hooks | Auto (minor) | Add syntax check before write |
| **Agent behavior** | Agent prompt rewrite | Human (major) | Change decision logic |
| **Workflow** | Command definition | Human | Alter step sequence |
| **Architectural** | Create DIP | Human required | New system capability |

#### 3.3 Absorption Targets

**Agent Modifications:**

```yaml
# In agent registry (DIP-0016)
agents:
  dip-preparer:
    hooks:
      pre:
        - action: validate_org_syntax  # <-- Absorbed from pattern
          source: PAT-2026-0123-001
          added: 2026-01-30
```

**CLAUDE.md Updates:**

```markdown
<!-- Absorbed from PAT-2026-0115-003 on 2026-01-22 -->
## Terminology

- Use "space" not "workspace" when referring to team directories
- Use "capture" not "collect" for inbox operations
```

**Command Enhancements:**

```yaml
# In command definition
commands:
  gtd-inbox-processor:
    steps:
      - name: validate_entry
        description: Validate org-mode syntax  # <-- Absorbed
        source: PAT-2026-0123-001
```

#### 3.4 Absorption Log

Track all absorptions in `.datacore/learning/absorption-log.md`:

```markdown
# Absorption Log

## 2026-01-30 (Weekly Consolidation)

### Absorbed (Auto-Approved)

| Pattern ID | Category | Target | Change |
|------------|----------|--------|--------|
| PAT-2026-0123-001 | validation | agent:dip-preparer | Added org-syntax validation hook |
| PAT-2026-0118-002 | terminology | CLAUDE.base.md | Updated "workspace" → "space" |

### Queued for Human Approval

| Pattern ID | Category | Target | Proposed Change |
|------------|----------|--------|-----------------|
| PAT-2026-0120-005 | workflow | cmd:gtd-weekly-review | Add calendar sync step |

### Rejected

| Pattern ID | Reason |
|------------|--------|
| PAT-2026-0119-003 | Contradicts existing pattern PAT-2025-1201-001 |
```

### 4. Loop 3: User Learning

#### 4.0 Knowledge Surfacing System (Implemented 2026-01-23)

**Status:** Implemented in `/today` and `/gtd-weekly-review` commands.

**Problem Solved:** Knowledge extracted during ingest (e.g., from Roam exports) sits in `3-knowledge/` folders and is never accessed. This creates "write-only" knowledge bases where valuable insights never influence future work.

**Solution:** Multi-layer surfacing with state tracking:

| Layer | Frequency | Mechanism | Effort |
|-------|-----------|-----------|--------|
| Daily Nugget | Each `/today` | Surface 1 recent item | Zero (passive) |
| Weekly Review | `/gtd-weekly-review` | Review all recent items | Low (reflection) |
| Application Tasks | GTD inbox | Create actionable tasks | Medium (intentional) |

**State Tracking:**

```yaml
# .datacore/state/knowledge-surfacing.yaml
items:
  0-personal/3-knowledge/pages/effective-meetings-guide.md:
    extracted: 2026-01-23
    last_surfaced: 2026-01-24
    surfaced_count: 1
    applied: false
    application_task: "Apply WDWBW framework in next team meeting"
```

**Daily Nugget Selection Algorithm:**
1. Scan `3-knowledge/` for files modified in past 30 days
2. Check if file has associated application task
3. Prioritize items with upcoming application tasks (contextually relevant)
4. If no upcoming tasks, surface oldest un-surfaced item
5. Update `last_surfaced` and `surfaced_count`

**Contextual Triggers** (optional calendar integration):
- Meetings today → surface meetings guide
- Project kickoff → surface project canvas methodology
- DevRel work → surface DevRel frameworks

**Application Task Pattern:**

When knowledge is extracted, create corresponding GTD tasks:

```org
* TODO Apply WDWBW framework in next team meeting :knowledge:meetings:
SCHEDULED: <2026-01-27 Mon>
:PROPERTIES:
:CREATED: [2026-01-23 Thu]
:SOURCE: 3-knowledge/pages/effective-meetings-guide.md
:END:
Use the "Who Does What By When" framework from the effective meetings guide.
```

**Key Insight:** Knowledge extraction alone is insufficient. The three-layer surfacing (daily/weekly/tasks) ensures extracted knowledge influences future decisions. This addresses the "write-only knowledge base" anti-pattern.

**Files:**
- `.datacore/commands/today.md` - Knowledge Nugget section
- `.datacore/commands/gtd-weekly-review.md` - Knowledge Review section (Step 14)
- `.datacore/state/knowledge-surfacing.yaml` - Surfacing state

#### 4.1 Spaced Repetition Engine

Track user knowledge for retention:

```yaml
# .datacore/learning/user-knowledge.yaml
knowledge_items:
  - id: UK-001
    concept: "Zettelkasten atomic note principle"
    source: "2-datacore/3-knowledge/zettel/Zettelkasten-Methodology.md"
    first_encounter: 2025-12-01
    reviews:
      - date: 2025-12-02
        recalled: true
        interval_days: 1
      - date: 2025-12-05
        recalled: true
        interval_days: 3
      - date: 2025-12-12
        recalled: false
        interval_days: 7
    next_review: 2025-12-15
    ease_factor: 2.1
    interval_days: 4
```

**Integration with `/today`:**

```markdown
## Knowledge Review (3 items due)

1. **Zettelkasten atomic note principle** (due today)
   - What is the core principle of atomic notes?
   - [Show answer] | [I remembered] | [I forgot]

2. **ACT-R base-level learning** (due today)
   - How does use frequency affect memory retrieval?
   - [Show answer] | [I remembered] | [I forgot]
```

#### 4.2 The /teach Command

New command for user-initiated teaching:

```
/teach [concept]
```

**Process:**
1. User explains concept to system
2. System asks clarifying questions (Socratic method)
3. System creates/updates zettel from explanation
4. User's understanding deepens through articulation (Protege Effect)
5. Concept added to spaced repetition queue

**Example:**

```
User: /teach production compilation

Claude: I'd like to understand your explanation of production compilation.
Please explain it as if teaching someone who knows basic programming but
not cognitive architectures.

User: It's when declarative knowledge becomes procedural through practice.
Like when you first learn to drive, you think about each step consciously,
but after enough practice it becomes automatic.

Claude: That's a clear explanation. Let me ask some clarifying questions:

1. What triggers the compilation process - is it mere repetition, or does
   successful goal achievement matter?

2. Can compiled productions ever "decompile" back to declarative form?

3. How does this relate to the "10,000 hours" concept in expertise research?

User: [answers questions, deepening their own understanding]

Claude: Based on your explanation, I've created a zettel:
- 3-knowledge/zettel/Production-Compilation.md

I've also added this concept to your spaced review queue. You'll see it
again in 1 day to reinforce retention.
```

#### 4.3 Active Recall Integration

During GTD reviews and daily briefings, surface questions rather than summaries:

**Instead of:**
> You met with John about Project X last week.

**Use:**
> What were the key outcomes from your meeting with John about Project X?
> [Tap to reveal: Budget approved, timeline shifted to Q2, need to hire contractor]

### 5. Pattern Retrieval

#### 5.1 Pattern Retriever Agent

New agent: `pattern-retriever`

**Purpose:** Fetch relevant patterns before task execution

**Trigger:** Via DIP-0016 lifecycle hooks (pre-execution)

**Process:**
1. Analyze incoming task context
2. Query patterns by:
   - Category match (e.g., "validation" for write operations)
   - Keyword similarity (via datacortex embeddings)
   - Historical relevance (patterns used in similar past tasks)
3. Return top-N relevant patterns
4. Inject into agent context

#### 5.2 Hook Integration (DIP-0016)

```yaml
# Agent registry entry
agents:
  dip-preparer:
    hooks:
      pre:
        - action: retrieve_patterns
          agent: pattern-retriever
          params:
            categories: [validation, formatting, workflow]
            limit: 5
            min_relevance: 0.7
```

#### 5.3 Pattern Relevance Scoring

```
Relevance = (category_match × 0.4) + (keyword_similarity × 0.3) +
            (recency × 0.2) + (frequency × 0.1)
```

### 6. Consolidation Schedule

| Frequency | Process | Scope |
|-----------|---------|-------|
| **Per-session** | Pattern capture | Current session only |
| **Daily** | Pattern deduplication | Remove exact duplicates |
| **Weekly** | Absorption analysis | Classify, propose changes |
| **Monthly** | Pattern pruning | Archive low-value patterns |
| **Quarterly** | Architecture review | Identify DIP-worthy patterns |

### 7. File Structure

```
[space]/.datacore/learning/
├── patterns.md              # Captured patterns (staging)
├── corrections.md           # Mistake log
├── preferences.md           # Style preferences
├── absorption-log.md        # Absorption history
├── user-knowledge.yaml      # Spaced repetition state
└── archive/                 # Pruned patterns
    └── 2025-Q4-patterns.md

.datacore/state/
├── knowledge-surfacing.yaml # Knowledge surfacing state (implemented)
└── structure_version.yaml   # Migration tracking

[space]/3-knowledge/         # Knowledge artifacts (surfacing source)
├── pages/                   # Generic methodology
├── literature/              # Book/paper notes
├── zettel/                  # Atomic concepts
└── [domain]/                # Domain-specific knowledge
```

## Rationale

### Why Three Loops?

Single-loop learning (capture only) creates write-only storage. Two-loop (capture + retrieval) still requires manual pattern application. Three-loop learning creates a complete cycle where:
- Patterns are captured from experience
- Patterns are absorbed into system behavior
- Knowledge flows bidirectionally with the user

### Why Absorption Over Retrieval?

Early design considered "read patterns before tasks" but this has problems:
1. **Cognitive load**: Agents must interpret and apply patterns each time
2. **Inconsistency**: Same pattern applied differently across executions
3. **No evolution**: System never actually changes

Absorption means patterns become part of the system. The system evolves.

### Why Approval Tiers?

Not all changes carry equal risk:
- Fixing a typo in CLAUDE.md is low-risk → auto-approve
- Changing agent decision logic could break workflows → human approval
- Architectural changes affect entire system → DIP required

### Cognitive Architecture Mapping

| Datacore Component | Cognitive Analog | Source |
|--------------------|------------------|--------|
| Pattern capture | Episodic memory encoding | Tulving |
| patterns.md | Episodic buffer (staging) | Baddeley |
| Absorption | Consolidation to semantic memory | McClelland |
| Agent modification | Production compilation | ACT-R |
| Spaced review | Distributed practice | Ebbinghaus |
| /teach command | Protege Effect | Fiorella & Mayer |

## Backwards Compatibility

- Existing `patterns.md`, `corrections.md`, `preferences.md` files remain valid
- New metadata fields are optional (agents handle missing fields gracefully)
- Absorption is additive - no existing behavior removed
- User learning features are opt-in

## Security Considerations

- **Absorption approval tiers** prevent unauthorized system modification
- **Human-in-loop** required for workflow and architectural changes
- **Audit log** tracks all absorptions for review
- **Pattern source tracking** prevents injection of malicious patterns

## Implementation

### Phase 1: Enhanced Capture (Week 1-2)
- Add pattern metadata to session-learning agent
- Implement pattern categorization
- Create absorption-log.md structure

### Phase 2: Pattern Retrieval (Week 3-4)
- Create pattern-retriever agent
- Integrate with DIP-0016 hooks
- Implement relevance scoring

### Phase 3: Absorption Engine (Week 5-8)
- Create learning-absorber agent
- Implement approval tier logic
- Build absorption targets (agents, CLAUDE.md, commands)

### Phase 4: User Learning (Week 9-12)
- ✅ **Knowledge Surfacing** (implemented 2026-01-23)
  - Daily nugget in `/today` command
  - Weekly review in `/gtd-weekly-review` command
  - State tracking in `.datacore/state/knowledge-surfacing.yaml`
  - Application task pattern for intentional first use
- ⏳ Implement full spaced repetition engine (user-knowledge.yaml)
- ⏳ Create /teach command
- ⏳ Integrate active recall questions into /today

### Reference Implementation

**Knowledge Surfacing (implemented):**
- `.datacore/commands/today.md` - Knowledge Nugget section
- `.datacore/commands/gtd-weekly-review.md` - Step 14: Knowledge Review
- `.datacore/state/knowledge-surfacing.yaml` - State tracking
- Commit: `32e904a` (2026-01-23)

**Pattern:** Selective extraction during ingest (e.g., 4,949 Roam files → 6 knowledge artifacts) combined with multi-layer surfacing ensures knowledge flows into active use rather than accumulating in folders.

### Rollout Plan

1. **Alpha**: Enable for 2-datacore space only
2. **Beta**: Enable for 0-personal space
3. **GA**: Enable for all spaces, document in CLAUDE.base.md

## Learnings from Implementation

### Knowledge Surfacing (2026-01-23)

**Context:** Processing 4,949 Roam export files during ingest revealed the "write-only knowledge base" problem acutely. Valuable methodology was extracted but would never be accessed without active surfacing.

**Key Learnings:**

1. **Selective Extraction Over Bulk Import**
   - 4,949 files → 6 knowledge artifacts (0.1% extraction rate)
   - Quality-first: only permanent insights, reusable patterns, strategic learnings
   - Operational content (meeting notes, daily journals) → archive, not knowledge base

2. **Multi-Layer Reinforcement**
   - Single-layer (extraction only) creates write-only storage
   - Three layers ensure accountability:
     - Daily: passive exposure (zero effort)
     - Weekly: reflection (low effort)
     - Tasks: intentional application (medium effort)

3. **Command Enhancement Over Agent Modification**
   - Added features at command level (markdown prompts) rather than agent code
   - Preserves agent stability while enabling workflow iteration
   - State tracking separate from command execution

4. **Contextual Surfacing Increases Relevance**
   - Calendar integration: meetings today → surface meetings guide
   - Task association: upcoming application task → prioritize that item
   - Recency weighting: newer extractions surface more frequently initially

**Patterns Captured:**
- `PAT-2026-0123-001`: Selective Knowledge Extraction Over Bulk Import
- `PAT-2026-0123-002`: Spaced Repetition for Knowledge Surfacing
- `PAT-2026-0123-003`: State-Tracked Knowledge Surfacing in Daily Workflows
- `PAT-2026-0123-004`: Command Enhancement Without Core Agent Modification

## Open Questions

1. **Pattern conflict resolution**: When two patterns contradict, which wins?
   - Proposed: More recent + higher frequency wins; flag for human review

2. **Cross-space pattern sharing**: Should patterns propagate across spaces?
   - Proposed: Only via explicit "promote to base" action

3. **Absorption rollback**: How to undo a bad absorption?
   - Proposed: Git-based rollback + absorption-log provides audit trail

4. **User learning privacy**: Is spaced repetition data sensitive?
   - Proposed: user-knowledge.yaml is gitignored by default

## References

### Datacore

- [Session-learning agent](../.datacore/agents/session-learning.md)
- [DIP-0011: Nightshift Module](./DIP-0011-nightshift-module.md)
- [DIP-0016: Agent Registry](./DIP-0016-agent-registry.md)
- [Cognitive Science of Learning](../2-datacore/3-knowledge/literature/cognitive-science-of-learning.md) - Foundation research

### Cognitive Science

- Anderson, J.R. (1995). *Cognitive Psychology and its Implications*. W.H. Freeman.
- Clark, A. & Chalmers, D. (1998). The extended mind. *Analysis*, 58(1), 7-19.
- Ebbinghaus, H. (1885). *Memory: A Contribution to Experimental Psychology*.
- Fiorella, L. & Mayer, R.E. (2013). The relative benefits of learning by teaching. *Contemporary Educational Psychology*, 38(4), 281-288.
- Laird, J.E. (2012). *The Soar Cognitive Architecture*. MIT Press.
- McClelland, J.L. et al. (1995). Why there are complementary learning systems. *Psychological Review*, 102(3), 419-457.
- Tulving, E. (1972). Episodic and semantic memory. In *Organization of Memory*.

---

*This DIP synthesizes research from the 2025-12-28 cognitive science session and addresses the write-only loop problem identified in system analysis.*
