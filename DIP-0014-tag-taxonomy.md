# DIP-0014: Tag Taxonomy

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Author** | Gregor |
| **Created** | 2025-12-19 |
| **Updated** | 2025-12-19 |
| **References** | DIP-0003 (Scaffolding), DIP-0009 (GTD), DIP-0012 (CRM) |

## Summary

Defines the unified tag system for Datacore: namespaces, formats, hierarchical structure, distributed registries, and cross-system integration. Tags become a coding language connecting GTD, PKM, CRM, and future modules (including financial tracking).

## Motivation

Tags are currently fragmented across systems:

- **GTD** uses `:AI:content:`, `:datafund:` (org-mode tag format)
- **PKM** incorrectly uses `tags: [ai, blockchain]` (frontmatter arrays - **wrong**)
- **CRM** uses `industries: [privacy_tech]` (snake_case arrays)
- **Industry Landscape** uses `type: technology` (enum fields)

**Note:** Org-mode priorities (`[#A]`, `[#B]`, `[#C]`) and scheduling are not tags - covered in DIP-0009.

**Problems:**
1. No canonical registry (~500+ organic tags)
2. Inconsistent naming (kebab-case vs snake_case vs PascalCase)
3. PKM notes using wrong format (arrays instead of inline hashtags)
4. No hierarchical tag structure for complex classification
5. No cross-module integration (GTD ↔ PKM ↔ CRM ↔ Financial)

**Vision:** Tags are **core to Datacore**. They become a coding language like `:verity:ops:legal:contract:` that enables:
- Holistic view of any space or project
- Precise task routing to specialized agents
- Cross-system queries (GTD ↔ PKM ↔ CRM ↔ Financial)
- Financial tracking by project/category/track
- Unified reporting across all modules
- Planning and prioritization across contexts

---

## Part 1: Tag Namespaces

### System Namespaces (Reserved)

| Namespace | Purpose | Values | Format |
|-----------|---------|--------|--------|
| `ai` | AI task delegation | content, research, data, pm, technical | `:AI:type:` |
| `status` | Document lifecycle | stub, draft, published, archived | frontmatter field |
| `maturity` | Knowledge maturity | seedling, budding, evergreen | frontmatter field |
| `type` | Document type | See Content Types below | frontmatter field |
| `context` | GTD contexts | computer, phone, call, home, errands, waiting, anywhere | `@context` |
| `category` | Scaffolding categories | identity, strategy, brand, sensing, memory, reasoning, action, learning, coordination, metrics | frontmatter/org |

### Content Types (per DIP-0003 Scaffolding)

| Type | Description | Location |
|------|-------------|----------|
| `zettel` | Atomic knowledge note | `2-knowledge/zettel/` |
| `literature-note` | Source material summary | `2-knowledge/literature/` |
| `clipping` | Web clipping | `Clippings/` |
| `journal` | Daily journal entry | `journals/` |
| `topic-note` | Topic overview | `2-knowledge/` |
| `project-note` | Project documentation | `1-active/` |
| `canvas` | Project charter | project root |
| `roadmap` | Project roadmap | project root |
| `playbook` | Operational process | `3-knowledge/action/` |

### Dynamic Namespaces

| Namespace | Purpose | Source | Governance |
|-----------|---------|--------|------------|
| `domain` | Topic classification | Space registries | User-defined |
| `industry` | CRM industry tags | CRM contacts | Auto-discovered |
| `technology` | Tech stack tags | CRM contacts | Auto-discovered |
| `project` | Project identifiers | Space registries | User-defined |
| `track` | Work tracks | Space registries | User-defined |

---

## Part 2: Tag Format

### Canonical Format

All tags use **kebab-case**: lowercase, hyphen-separated.

| Input | Normalized |
|-------|------------|
| `Privacy Tech` | `privacy-tech` |
| `privacy_tech` | `privacy-tech` |
| `PrivacyTech` | `privacy-tech` |
| `zk-STARKs` | `zk-starks` |

### System-Specific Syntax

| System | Syntax | Example | Notes |
|--------|--------|---------|-------|
| **Org-mode headings** | `:tag1:tag2:` | `:verity:ops:legal:` | Hierarchical, colon-separated |
| **Org-mode AI** | `:AI:type:` | `:AI:content:` | Case-sensitive exception |
| **Org-mode context** | `@context` | `@computer` | In task text |
| **PKM inline** | `#tag` | `#privacy-tech, #verity` | Correct format for notes |
| **PKM frontmatter** | Single values only | `type: zettel` | NOT arrays |
| **CRM inline** | `#tag` | `#privacy-tech, #partner` | Same as PKM |

### PKM Tag Format (IMPORTANT)

**Correct format** for notes/zettels:

```markdown
---
type: zettel
created: 2025-12-19
source: "[[Literature Note Name]]"
---

# Concept Name

Content here...

#privacy-tech, #verity, #compliance
```

**Incorrect format** (DO NOT USE):
```yaml
tags: [privacy-tech, verity, compliance]  # WRONG - arrays not allowed
```

### Org-mode Tag Syntax (IMPORTANT)

**Org-mode treats colons as tag separators, not hierarchy markers.**

```org
* Task heading                                    :AI:research:
```

This task has **TWO separate tags**: `AI` and `research`.

```org
* Another task                                    :verity:ops:legal:
```

This task has **THREE separate tags**: `verity`, `ops`, and `legal`.

**Key principle:** `:a:b:c:` = 3 tags, not 1 hierarchical tag.

### Hierarchical Convention (Datacore-specific)

While org-mode sees flat tags, Datacore agents **interpret adjacent tags as logical hierarchy** for filtering and reporting:

```
:verity:ops:legal:  →  Interpreted as: verity → ops → legal
```

**This is a convention, not org-mode native behavior.**

**Examples:**
- `:verity:ops:legal:` - 3 tags, interpreted as Verity/Operations/Legal
- `:datafund:product:mvp:` - 3 tags, interpreted as Datafund/Product/MVP
- `:personal:health:exercise:` - 3 tags, interpreted as Personal/Health/Exercise

**AI Delegation Tags:**

```org
* Research ZK proofs                              :AI:research:
```

- Tag 1: `AI` - Signals this task should be delegated to AI
- Tag 2: `research` - Specifies the agent type (gtd-research-processor)

Both tags are independent. A task can have `:research:` without `:AI:` (human research task).

**Benefits of this convention:**
- Org-mode filtering works on any individual tag (`+verity`, `+ops`, `+legal`)
- Datacore agents can interpret tag sequences as hierarchy
- Financial tracking: Filter by `+verity+ops` for all Verity operations
- Reporting: Aggregate by any tag or tag combination

---

## Part 3: Distributed Registries

### Registry Locations

Registries are hidden in `.datacore/` folders:

| Priority | Path | Scope |
|----------|------|-------|
| 1 (highest) | `.datacore/tags.yaml` | System-wide reserved tags |
| 2 | `[space]/.datacore/tags.yaml` | Space-specific tags |
| 3 | `.datacore/modules/[module]/tags.yaml` | Module-contributed tags |
| 4 | `[project]/.datacore/tags.yaml` | Project-specific tags |

### Registry Format

```yaml
# Example: 0-personal/.datacore/tags.yaml
version: 1
space: personal

tags:
  domain:
    - id: privacy-tech
      label: Privacy Tech
      description: Privacy-preserving technologies
      synonyms: [privacy-technology, privacy-engineering, privacy]
      similar: [security, encryption]  # Related but distinct

    - id: data-economy
      label: Data Economy
      description: Economic models for data ownership
      synonyms: [data-markets, data-ownership]

  projects:
    - id: verity
      label: Verity
      description: Institutional data marketplace
      tracks: [ops, product, research, legal]

    - id: datafund
      label: Datafund
      description: Core business operations
      tracks: [ops, product, fundraising]

  tracks:
    - id: ops
      label: Operations
      description: Operational tasks

    - id: legal
      label: Legal
      description: Legal and compliance

    - id: fundraising
      label: Fundraising
      description: Investment and funding
```

### System Registry

Location: `.datacore/tags.yaml`

```yaml
version: 1
type: system
description: Reserved system tags - referenced by all agents

namespaces:
  ai:
    description: AI task delegation tags
    prefix: ":AI:"
    discoverable: true  # Agents should read this
    tags:
      - id: content
        routes-to: gtd-content-writer
        description: Blog posts, emails, social media, documentation

      - id: research
        routes-to: gtd-research-processor
        description: URL analysis, literature notes, zettels

      - id: data
        routes-to: gtd-data-analyzer
        description: Metrics, reports, data analysis

      - id: pm
        routes-to: gtd-project-manager
        description: Project status, blockers, coordination

      - id: technical
        routes-to: cto-queue
        autonomous: false
        description: Implementation tasks (human review required)

  status:
    description: Document lifecycle
    tags:
      - id: stub
        synonyms: [placeholder, empty]
      - id: draft
        synonyms: [wip, in-progress]
      - id: published
        synonyms: [final, complete]
      - id: archived

  maturity:
    description: Knowledge maturity (Zettelkasten)
    tags:
      - id: seedling
        description: Newly captured idea
      - id: budding
        description: Growing with connections
      - id: evergreen
        description: Stable, refined knowledge

  type:
    description: Content types (per DIP-0003)
    tags:
      - id: zettel
      - id: literature-note
      - id: clipping
      - id: journal
      - id: topic-note
      - id: project-note
      - id: canvas
      - id: roadmap
      - id: playbook

  context:
    description: GTD contexts
    prefix: "@"
    tags:
      - id: computer
      - id: phone
      - id: call
      - id: home
      - id: errands
      - id: waiting
      - id: anywhere

  category:
    description: Scaffolding categories (per DIP-0003)
    tags:
      - id: identity
        description: Purpose, vision, mission, values
      - id: strategy
        description: Strategic planning, positioning
      - id: brand
        description: Brand guidelines, voice
      - id: sensing
        description: Market intelligence, competitors
      - id: memory
        description: Knowledge management
      - id: reasoning
        description: Analysis frameworks
      - id: action
        description: Playbooks, processes
      - id: learning
        description: Feedback, retrospectives
      - id: coordination
        description: Communication, handoffs
      - id: metrics
        description: KPIs, OKRs, health metrics
```

### Discoverability

The system registry MUST be discoverable by agents. Add to:

1. **CLAUDE.md** (base layer):
   ```markdown
   ## Tag System

   Tags are defined in `.datacore/tags.yaml` (system) and
   `[space]/.datacore/tags.yaml` (space-specific).

   See DIP-0014 for full specification.
   ```

2. **Agent instructions**: Each agent that uses tags should reference the registry.

### Merge Strategy

**Simple union** with synonym resolution:

1. Collect registries from all discovery locations
2. Normalize all tag IDs to kebab-case
3. Merge synonyms into canonical tags
4. On ID collision: higher priority wins, log warning
5. Result: unified tag set with synonym mappings

---

## Part 4: Examples

### Org-mode Task with Hierarchical Tags

```org
*** TODO Review partnership contract with Zama    :verity:ops:legal:contract:AI:pm:
SCHEDULED: <2025-12-20 Fri>
:PROPERTIES:
:CREATED: [2025-12-19 Thu]
:EFFORT: 2h
:END:

@computer Review the draft NDA and partnership terms.
- [ ] Check IP clauses
- [ ] Verify data handling terms
```

**Tag breakdown (6 separate tags):**
- `verity` - Project identifier
- `ops` - Operations track
- `legal` - Legal category
- `contract` - Specific aspect
- `AI` - Signals AI delegation
- `pm` - Routes to gtd-project-manager

Datacore interprets `verity:ops:legal:contract` as logical hierarchy for filtering.

### Zettel with Inline Tags (Correct Format)

```markdown
---
type: zettel
created: 2025-12-19
source: "[[Pantera Capital - Privacy Renaissance]]"
maturity: seedling
---

# Fully Homomorphic Encryption (FHE)

FHE enables computation on encrypted data while maintaining verifiability...

## Key Insight

Unlike mixers offering absolute opacity, FHE permits selective disclosure—
regulators gain visibility while public doesn't.

#privacy-tech, #fhe, #compliance, #verity, #zama
```

**Note:** Tags at end of content as `#tag, #tag`, NOT in frontmatter array.

### CRM Contact (Inline Tags)

```markdown
---
name: Zama
type: company
relationship_type: partner
---

# Zama

FHE technology company enabling privacy + compliance through encrypted computation.

## Notes

Key partner for Verity compliance layer. Evaluate SDK integration.

#privacy-tech, #cryptography, #blockchain, #fhe, #partner
```

CRM contacts use same inline tag format as PKM notes.

### Financial Transaction (Future Module)

```org
*** EXPENSE Office supplies                       :datafund:ops:admin:
SCHEDULED: <2025-12-19 Thu>
:PROPERTIES:
:AMOUNT: 150.00
:CURRENCY: EUR
:ACCOUNT: business-checking
:CATEGORY: office-supplies
:END:
```

Tags enable aggregation: "Show all :datafund:ops: expenses this quarter"

---

## Part 5: Cross-System Integration

### GTD ↔ PKM ↔ CRM ↔ Financial

Tags create a unified classification system:

```
┌─────────────────────────────────────────────────────────────────┐
│                        TAG TAXONOMY                              │
│                    (Single Source of Truth)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │   GTD   │          │   PKM   │          │   CRM   │
   │ :tag:   │  ←───→   │ #tag    │  ←───→   │ #tag    │
   │ org-mode│          │ markdown│          │ markdown│
   └─────────┘          └─────────┘          └─────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │   FINANCIAL   │
                      │   (future)    │
                      │  :tag: + amt  │
                      └───────────────┘
```

**Query examples:**
- "All tasks tagged `:verity:`" → GTD view
- "All notes tagged `#verity`" → PKM search
- "All contacts in `privacy-tech` industry" → CRM filter
- "Total expenses tagged `:verity:ops:`" → Financial report

### Org-mode ↔ PKM Mapping

| Org-mode | PKM Equivalent |
|----------|----------------|
| `:datafund:` | `#datafund` |
| `:verity:ops:legal:` | `#verity, #ops, #legal` |
| `:AI:research:` | (org-only - routing tag) |

### Migration from Array Format

Existing files with `tags: [a, b, c]` should be converted:

**Before:**
```yaml
tags: [privacy-tech, blockchain, verity]
```

**After:**
```markdown
#privacy-tech, #blockchain, #verity
```

Place at end of note content, after the main body.

---

## Part 6: Agent Compliance

### Agents Requiring Updates

| Agent | Current Issue | Required Change |
|-------|---------------|-----------------|
| `gtd-research-processor` | Uses `tags: [array]` in template | Use inline `#tag` format |
| `conversation-processor` | Uses `tags: [array]` in zettel template | Use inline `#tag` format |
| `session-learning` | Uses `tags: [array]` in output | Use inline `#tag` format |
| `gtd-inbox-processor` | No tag validation | Add registry validation |
| `gtd-content-writer` | May use wrong format | Verify and fix |
| `gtd-data-analyzer` | May use wrong format | Verify and fix |
| `archiver` | May not preserve tags | Verify tag preservation |
| `ai-task-executor` | Routes by tag | Should read system registry |
| `research-link-processor` | Uses `tags: [array]` | Use inline `#tag` format |
| `crm-contact-maintainer` | Uses array fields | Use inline `#tag` format |
| `crm-entity-extractor` | Extracts to arrays | Extract to inline format |
| `crm-interaction-extractor` | Uses array fields | Use inline `#tag` format |
| `crm-relationship-scorer` | May use arrays | Verify and fix |
| `meeting-router` | Uses tags for routing | Verify compliance |
| `agenda-generator` | May generate tags | Verify format |
| `transcription-processor` | Extracts topics/tags | Use inline format |

### Agent Template Updates

**Literature Note Template (gtd-research-processor):**
```markdown
---
type: literature-note
source: [URL]
created: [YYYY-MM-DD]
---

# [Title]

[Content...]

#category, #topic, #work-area, #auto-generated
```

**Zettel Template (all agents):**
```markdown
---
type: zettel
created: [YYYY-MM-DD]
source: "[[Source Note]]"
maturity: seedling
---

# [Concept Name]

[Content...]

#concept-tag, #work-area
```

---

## Part 7: Implementation

### Phase 1: Registry Creation

1. Create `.datacore/tags.yaml` with system namespaces
2. Create `0-personal/.datacore/tags.yaml` with discovered domain tags
3. Add registry reference to CLAUDE.base.md
4. Update CRM normalization to kebab-case

### Phase 2: Agent Compliance

1. Update `gtd-research-processor` template
2. Update `conversation-processor` template
3. Update `session-learning` output format
4. Add tag validation to `gtd-inbox-processor`
5. Update `ai-task-executor` to read system registry

### Phase 3: Migration

1. Create migration script for existing files
2. Convert `tags: [array]` → inline `#tags`
3. Normalize tag casing
4. Validate against registry

### Phase 4: Tooling (Core)

1. Tag validation in weekly review
2. Registry consolidation script
3. Tag suggestion integration

### Phase 5: Financial Integration (Future)

1. Define financial module tag requirements
2. Integrate expense/income tagging
3. Build cross-module reporting

---

## Compatibility

### Backward Compatibility

- Existing org-mode tags continue to work
- PKM/CRM array format deprecated but readable during migration

### Migration Path

1. **Immediate**: Create registries, update agent templates
2. **Gradual**: New notes use inline format
3. **Batch**: Run migration script on existing files
4. **Validation**: Weekly review flags format issues

---

## References

- DIP-0003: Scaffolding Pattern (content types, categories)
- DIP-0009: GTD Specification (AI delegation tags, contexts)
- DIP-0012: CRM Module (industry/technology tags)
- `.datacore/config/tags.yaml` - Existing tag configuration
- [Zettelkasten Method](https://zettelkasten.de/) - Maturity levels
- [GTD Contexts](https://gettingthingsdone.com/) - Context concept
