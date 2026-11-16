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

Four statuses, and nothing else in a header (owner, 2026-11-15):

| Status | Meaning |
|--------|---------|
| **Draft** | Proposed. Not a rule yet, whatever the code does. A qualifier may follow the word ("Draft (owner ratifies)") |
| **Ratified** | The owner approved it. It is the rule; code and other documents that disagree are wrong |
| **Superseded** | Replaced by another DIP, which the header names |
| **Retired** | No longer a rule and not replaced |

Only the owner ratifies. An agent may write a Draft or propose an amendment as a pull request left open; it never changes a status to Ratified.

**"Implemented" is not a status.** Whether a ratified DIP is built is a fact to check, not a word to type: `dip_conformance.py` in the datacore repository derives it from the files a DIP names. Headers that said Implemented or Accepted before 2026-11-16 now say Ratified.

Read each DIP header together with its amendment, rollout and future-work notes. A Ratified header does not ratify a section that is explicitly marked as proposed. Catalog rows mirror the referenced header; they do not override it.

## DIP Workflow

```
1. Copy DIP-0000-template.md to DIP-XXXX-title.md (next free number)
2. Fill in the template; status Draft
3. Open a pull request against main and leave it open
4. The owner reviews; changes are made on the same pull request
5. The owner ratifies: the header becomes Ratified and the pull request is merged
6. An amendment to a Ratified DIP is its own pull request, dated, and ratified the same way
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
| [0001](DIP-0001-contribution-model.md) | Contribution Model | Ratified |
| [0002](DIP-0002-layered-context-pattern.md) | Layered Context Pattern | Ratified |
| [0005](DIP-0005-installation-upgrade.md) | Installation & Upgrade | Ratified |
| [0014](DIP-0014-tag-taxonomy.md) | Tag Taxonomy | Ratified |
| [0016](DIP-0016-agent-registry.md) | Agent Registry & Discoverability | Ratified |

### Knowledge & Content

| DIP | Title | Status |
|-----|-------|--------|
| [0003](DIP-0003-scaffolding-pattern.md) | Scaffolding Pattern | Ratified |
| [0015](DIP-0015-semantic-organization.md) | Semantic Organization | Ratified |
| [0017](DIP-0017-outbox-archive-pattern.md) | Outbox & Archive Pattern | Ratified |
| [0019](DIP-0019-learning-architecture.md) | Learning Architecture | Ratified |

### GTD & Task Management

| DIP | Title | Status |
|-----|-------|--------|
| [0009](DIP-0009-gtd-specification.md) | GTD System Specification | Ratified |
| [0010](DIP-0010-external-sync-architecture.md) | External Sync Architecture | Ratified |
| [0011](DIP-0011-nightshift-module.md) | Nightshift Module | Ratified |

### Domain Modules

| DIP | Title | Status |
|-----|-------|--------|
| [0012](DIP-0012-crm-module.md) | CRM Module | Ratified |
| [0013](DIP-0013-meetings-module.md) | Meetings Module | Ratified |

### Process & Templates

| DIP | Title | Status |
|-----|-------|--------|
| [0000](DIP-0000-template.md) | DIP Template | Draft |

### System Architecture

| DIP | Title | Status |
|-----|-------|--------|
| [0021](DIP-0021-search-research-architecture.md) | Search & Research Architecture | Ratified |
| [0022](DIP-0022-module-specification.md) | Module Specification | Ratified |

### Infrastructure & Security

| DIP | Title | Status |
|-----|-------|--------|
| [0018](DIP-0018-credential-management.md) | Credential Management | Draft |
| [0020](DIP-0020-whatsapp-module.md) | WhatsApp Module | Ratified |

### Not yet grouped (listed 2026-11-16)

These existed without a catalogue row. They are listed by number until the catalogue is regrouped.

| DIP | Title | Status |
|-----|-------|--------|
| [0023](DIP-0023-messaging-module.md) | Messaging Module | Draft |
| [0024](DIP-0024-reactive-hooks-infrastructure.md) | Reactive Hooks Infrastructure | Draft |
| [0025](DIP-0025-datacore-bench.md) | Evaluation & Benchmarking (datacore-bench) | Draft |
| [0026](DIP-0026-architectural-primitives.md) | Architectural Primitives | Draft |
| [0027](DIP-0027-behavioural-observation-architecture.md) | Behavioural Observation Architecture | Draft |
| [0028](DIP-0028-capture-endpoint-contract.md) | Capture Endpoint Contract | Draft |
| [0029](DIP-0029-command-scoped-engram-recall.md) | Command-Scoped Engram Recall | Ratified |
| [0031](DIP-0031-agent-error-handling.md) | Agent Error Classification & Recovery | Ratified |
| [0032](DIP-0032-egress-enforcement.md) | Egress Enforcement | Draft |
| [0033](DIP-0033-delivery-verification.md) | Delivery Verification & Smoke Scenarios | Draft |
| [0034](DIP-0034-event-ledger-substrate.md) | Event Ledger Substrate | Ratified |
| [0035](DIP-0035-job-contracts.md) | Job Contracts + Unified Verifier | Ratified |
| [0036](DIP-0036-config-plane.md) | Config Plane | Ratified |
| [0037](DIP-0037-grounded-briefings.md) | Grounded Briefings | Ratified |
| [0038](DIP-0038-action-loop-cosign.md) | Action Loop + Co-sign | Ratified |
| [0039](DIP-0039-server-first-artifacts.md) | Server-First Artifacts | Ratified |
| [0040](DIP-0040-agent-consolidation.md) | Agent Consolidation | Ratified |
| [0041](DIP-0041-executor-adapters.md) | Executor Adapters | Ratified |
| [0042](DIP-0042-canonical-ledger.md) | Canonical Ledger & Finality | Draft |
| [0043](DIP-0043-org-projection.md) | Org Projection & Genesis Import | Draft |
| [0044](DIP-0044-actor-identity.md) | Actor Identity | Draft |
| [0046](DIP-0046-git-transport.md) | Git as Ledger Transport | Draft |
| [0047](DIP-0047-egress-attestation.md) | Egress Attestation — recording what agents do to the outside world | Draft |
| [0048](DIP-0048-validation-envelope.md) | Shared Validation Envelope for PLUR Engrams ↔ EvoMap Genes | Draft — gated on Evolver-spike lift signal |
| [0049](DIP-0049-module-tool-loading-architecture.md) | Module Tool Loading Architecture | Draft |
| [0050](DIP-0050-cadences-as-assigned-duties.md) | Cadences as assigned duties, executed by their owners | Draft (owner ratifies) |

### Historical / Superseded

| DIP | Title | Status |
|-----|-------|--------|
| [0004](DIP-0004-knowledge-database.md) | Knowledge Database | Superseded |
| [0006](DIP-0006-open-questions-management.md) | Open Questions Management | Superseded |
| [0007](DIP-0007-inbox-done-option.md) | Inbox DONE Option | Superseded |

---

## Historical roadmap (not current number reservations)

This older planning list is retained for traceability. Its numbers and titles
were superseded by the subsequently created DIP files and do not reserve
numbers or define current implementation requirements:

| DIP | Title | Purpose | Priority |
|-----|-------|---------|----------|
| **0023** | Sync Architecture | ./sync script, multi-repo handling | Medium |
| **0025** | Evaluation & Benchmarking | datacore-bench: A/B testing, instrumentation, session replay | High |
| **0026** | Chat Interface Architecture | Telegram, Slack, Discord, Email integrations | Medium |
| **0027** | Journal Format | Personal and team journal structure | Low |

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
| Core Concepts (Modules) | → DIP-0022 |
| Architecture | → DIP-0003, DIP-0015 |
| Knowledge Layer | → DIP-0003, DIP-0015, DIP-0019 |
| Task Management (GTD) | → DIP-0009 |
| Agents & Commands | → DIP-0016 |
| Configuration | → DIP-0021 |
| Git & Contribution | → DIP-0001, DIP-0002 |
| External Sync | → DIP-0010 |
| Operations | → DIP-0017, DIP-0018 |
| Integrations | → DIP-0010 |
| Chat Interfaces | → (future DIP) |

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
