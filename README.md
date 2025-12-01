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
1. Fork datacore repo
2. Copy dips/DIP-0000-template.md to dips/DIP-XXXX-title.md
3. Fill in the template
4. Submit PR with status: Draft
5. Community discussion on PR
6. Maintainers move to Review
7. Accept/Reject decision
8. Implementation PR(s)
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

| DIP | Title | Type | Status |
|-----|-------|------|--------|
| [0000](DIP-0000-template.md) | DIP Template | Process | Implemented |
| [0001](DIP-0001-contribution-model.md) | Contribution Model | Process | Implemented |
| [0002](DIP-0002-layered-context-pattern.md) | Layered Context Pattern | Core | Implemented |

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
