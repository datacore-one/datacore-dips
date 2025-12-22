# Datacore Improvement Proposals (DIPs)

DIPs are the primary mechanism for proposing new features, collecting community input, and documenting design decisions for Datacore.

## What is a DIP?

A DIP is a design document providing information to the Datacore community about a proposed change. The DIP author is responsible for building consensus within the community and documenting dissenting opinions.

## DIP Types

| Type | Description |
|------|-------------|
| **Core** | Changes to the main `datacore` repo (personal spaces) |
| **Org** | Changes to `datacore-org` template (team spaces) |
| **Module** | New module proposals or module standards |
| **Process** | Changes to the DIP process itself |

## DIP Status

| Status | Description |
|--------|-------------|
| **Draft** | Initial proposal, open for feedback |
| **Review** | Under formal review by maintainers |
| **Accepted** | Approved for implementation |
| **Implemented** | Merged and released |
| **Rejected** | Not accepted (with rationale) |
| **Withdrawn** | Withdrawn by author |
| **Deferred** | Postponed for future consideration |

## DIP Workflow

```
1. Fork datacore-dips repo
2. Copy DIP-0000-template.md to DIP-XXXX-title.md
3. Fill in the template
4. Submit PR with status: Draft
5. Community discussion on PR
6. Maintainers move to Review
7. Accept/Reject decision
8. Implementation PR(s) to relevant repos
9. Status updated to Implemented
```

## When to Create a DIP

**Always create a DIP for:**
- New patterns or conventions (like DIP-0002 Layered Context)
- Changes affecting multiple repos or components
- New agent types or command categories
- Privacy or security model changes
- Breaking changes to existing workflows

**Small changes that DON'T need DIPs:**
- Bug fixes
- Documentation typos
- Single-file improvements
- Performance optimizations

**AI agents should automatically create DIPs** when implementing significant system changes. This ensures all architectural decisions are documented and reviewable.

## Before Submitting

1. **Search existing DIPs** - Your idea may already exist
2. **Discuss first** - Open a GitHub Discussion for initial feedback
3. **Small changes** - Bug fixes and minor improvements don't need DIPs

## DIP Template

See [DIP-0000-template.md](DIP-0000-template.md) for the template.

## Current DIPs

### Core Infrastructure

| DIP | Title | Status |
|-----|-------|--------|
| [0001](DIP-0001-contribution-model.md) | Contribution Model | Implemented |
| [0002](DIP-0002-layered-context-pattern.md) | Layered Context Pattern | Implemented |
| [0014](DIP-0014-tag-taxonomy.md) | Tag Taxonomy | Implemented |
| [0016](DIP-0016-agent-registry.md) | Agent Registry & Discoverability | Implemented |

### Knowledge & Content

| DIP | Title | Status |
|-----|-------|--------|
| [0003](DIP-0003-scaffolding-pattern.md) | Scaffolding Pattern | Implemented |
| [0004](DIP-0004-knowledge-database.md) | Knowledge Database | Implemented |
| [0015](DIP-0015-semantic-organization.md) | Semantic Organization | Implemented |

### GTD & Task Management

| DIP | Title | Status |
|-----|-------|--------|
| [0007](DIP-0007-inbox-done-option.md) | Inbox DONE Option | Draft |
| [0009](DIP-0009-gtd-specification.md) | GTD System Specification | Implemented |
| [0010](DIP-0010-external-sync-architecture.md) | External Sync Architecture | Implemented |
| [0011](DIP-0011-nightshift-module.md) | Nightshift Module | Implemented |

### Domain Modules

| DIP | Title | Status |
|-----|-------|--------|
| [0012](DIP-0012-crm-module.md) | CRM Module | Implemented |
| [0013](DIP-0013-meetings-module.md) | Meetings Module | Implemented |

### Process & Templates

| DIP | Title | Status |
|-----|-------|--------|
| [0000](DIP-0000-template.md) | DIP Template | Implemented |

### Historical / Superseded

| DIP | Title | Status |
|-----|-------|--------|
| 0005 | GitHub-Based Onboarding | Draft (unfinished) |
| 0006 | Open Questions Management | Superseded by DIP-0013 |

---

## DIP Roadmap

The following DIPs are planned to complete full specification coverage:

| DIP | Title | Purpose | Priority |
|-----|-------|---------|----------|
| **0017** | Installation & Upgrade | Bootstrap, upgrades, migrations | Medium |
| **0018** | Sync Architecture | ./sync script, multi-repo handling | Medium |
| **0019** | Journal Format | Personal and team journal structure | Low |
| **0020** | External Services | n8n, Gamma, and service integration patterns | Low |
| **0021** | Module Specification | module.yaml schema, installation, hooks, lifecycle | High |

### Relationship to `datacore-specification.md`

With DIP-0017 through DIP-0021 complete, the monolithic `datacore-specification.md` can be reduced to a ~10KB overview document that:
1. Introduces Datacore philosophy and concepts
2. Links to specific DIPs for detailed specifications
3. Provides quick-start guidance

**Current spec section → DIP mapping:**

| Spec Section | Covered By |
|--------------|------------|
| Overview & Philosophy | Remains in spec (unique) |
| Core Concepts (Spaces) | Remains in spec (unique) |
| Core Concepts (Modules) | → DIP-0021 |
| Architecture | → DIP-0003, DIP-0015 |
| Knowledge Layer | → DIP-0003, DIP-0004, DIP-0015 |
| Task Management (GTD) | → DIP-0007, DIP-0009 |
| Agents & Commands | → DIP-0016 |
| Configuration | → DIP-0021 |
| Git & Contribution | → DIP-0001, DIP-0002 |
| External Sync | → DIP-0010 |
| Operations | → DIP-0017, DIP-0018 |
| Integrations | → DIP-0010, DIP-0020 |

## Contributing

1. DIPs must use the template
2. One DIP per PR
3. DIP numbers assigned by maintainers
4. Use clear, concise language
5. Include rationale and alternatives considered

## Inspiration

This process is inspired by:
- [Ethereum Improvement Proposals (EIPs)](https://eips.ethereum.org/)
- [Python Enhancement Proposals (PEPs)](https://peps.python.org/)
- [Rust RFCs](https://rust-lang.github.io/rfcs/)
