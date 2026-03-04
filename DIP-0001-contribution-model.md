# DIP-0001: Contribution Model

| Field | Value |
|-------|-------|
| **DIP** | 0001 |
| **Title** | Contribution Model |
| **Author** | Datacore Team |
| **Type** | Process |
| **Status** | Implemented |
| **Created** | 2025-12-01 |
| **Updated** | 2026-03-04 |
| **Tags** | `contribution`, `git`, `privacy`, `fork` |
| **Affects** | `.gitignore`, `INSTALL.md`, `CATALOG.md` |
| **Specs** | `privacy-policy.md` |
| **Agents** | - |

## Summary

Defines the repository structure and contribution model that enables thousands of users to improve Datacore while keeping their content private.

## Motivation

Datacore needs to scale to thousands of contributors who:
1. Want to improve agents, commands, and system features
2. Must keep their personal/organizational content private
3. Need a clear path to contribute back improvements

Current mixed system+content repos make contribution difficult and risk exposing private data.

## Specification

### Repository Types

**Public Template Repos** (Forkable):
- `datacore` - Personal space framework
- `datacore-org` - Organization space template
- `datacore-[module]` - Domain modules

**Private Content Repos** (Per-user/org):
- Content stays local, gitignored
- Or in private repo if team sync needed

### Contribution Flow

```
1. User forks template repo (e.g., datacore-org)
2. User clones fork to ~/Data/N-orgname/
3. User works - content is auto-gitignored
4. User improves agent/command/structure
5. User commits system files to fork
6. User opens PR to upstream
7. Maintainers review and merge
8. All users get improvement via git pull
```

### .gitignore Structure

Template repos use strict .gitignore that:

**Tracks (contributable):**
- `.datacore/agents/*.md`
- `.datacore/commands/*.md`
- `CLAUDE.md` / `CLAUDE.template.md`
- `*/_index.md`, `*/README.md`
- Folder structure

> **Note:** Context file management (CLAUDE.md) follows DIP-0002 Layered Context Pattern. The `.base.md` layer is the contributable public layer.

**Ignores (stays local):**
- `org/*.org` (tasks)
- `journal/*.md` (activity)
- `*-knowledge/**/*.md` (knowledge)
- `*-departments/**/*.md` (work)
- `*.db` (databases)

### Upstream Sync

Users keep in sync with upstream improvements:

```bash
# Add upstream remote (once)
git remote add upstream https://github.com/datacore-one/datacore-org.git

# Sync with upstream
git fetch upstream
git merge upstream/main
```

### Significant Changes: DIP Process

For non-trivial changes:
1. Submit DIP (this process)
2. Community discussion
3. Maintainer review
4. Accept/Reject
5. Implementation

## Rationale

**Why Overlay Pattern (vs Submodules)?**
- Simpler for users
- Single folder to work in
- Easier contribution (just PR)
- Submodules add complexity

**Why .gitignore (vs separate repos)?**
- Lower barrier to entry
- No repo management overhead
- Natural content/system separation

## Backwards Compatibility

Existing spaces need migration:
1. Update .gitignore
2. Remove content files from git tracking
3. Keep content locally
4. Only system files remain tracked

## Security Considerations

- Private content never tracked
- Users must not `git add -f` content files
- CI can check for content file patterns in PRs

## Implementation Status

_Last audited: 2026-03-04_

### Implemented

| Feature | Evidence |
|---------|----------|
| Fork-and-overlay contribution model | Public template repos → private forks → system files tracked, content gitignored |
| Layered context pattern (DIP-0002) | `.base.md` (public), `.org.md`, `.team.md`, `.local.md` (private) with merge script |
| `.gitignore` strategy | Tracks agents/commands/specs, ignores `.org`, `journal/`, `*-knowledge/`, `*.db` |
| CONTRIBUTING.md | 114 lines with privacy checklist, hook setup, layered context guide |
| LICENSE (MIT) | Root-level MIT license for open-source distribution |
| PR template | `.github/pull_request_template.md` with privacy/structural checklists |
| Layer 1 Safety Gate | `.github/workflows/validate-layers.yml` validates `.base.md` for PII on PR/push |
| Pre-commit hook | `.datacore/hooks/pre-commit` validates staged `.base.md` for PII before commit |
| Pre-push hook | `.datacore/hooks/pre-push` validates all `.base.md` in push range + git-lfs check |
| `context_merge.py validate` | PII detection for emails, phones, APIs, dollar amounts in PUBLIC layers |
| Privacy policy | `.datacore/specs/privacy-policy.md` with data classification and sharing guidelines |
| Autonomous PR review script | `.datacore/lib/pr_review.py` (244 lines) for Layer 3 deep review |
| DIP process infrastructure | Template, README, submission workflow in `dips/` |

### Implemented (promoted from deferred)

| Feature | Evidence |
|---------|----------|
| Layer 3 Deep Review | `pr_review.py` exists and is manually invocable for comprehensive PR review |

### Future Work
_Items below are outside v1.0 scope. They remain specified for future implementation._

| Feature | Rationale |
|---------|-----------|
| Shared composite actions repo (`datacore-one/.github`) | Requires GitHub org setup; can be added post-publication |
| Layer 2 Structural Validation CI | Would validate module.yaml, agent registry, DIP templates |
| Layer 3 Deep Review webhook | pr_review.py ready; needs nightshift webhook trigger for automation |
| Contributor rewards/points system | Future feature; infrastructure stable without it |
| CATALOG.md enrichment | Basic module listing sufficient for MVP |

### Resolved Questions

1. **What gets tracked vs ignored?** Methodology (agents, commands, specs) tracked. Content (org files, journals, knowledge) ignored.
2. **How do hooks get installed?** Symlink from `.datacore/hooks/` to `.git/hooks/`. Documented in CONTRIBUTING.md.
3. **What prevents PII in public layers?** Pre-commit hook + `context_merge.py validate` scan for emails, phone numbers, API keys, dollar amounts.

### Migration Guide

For existing spaces:
```bash
cd ~/Data/N-space/

# Fetch updated .gitignore
git fetch origin
git checkout origin/main -- .gitignore

# Remove content from tracking (keeps local files)
git rm -r --cached org/*.org
git rm -r --cached journal/*.md
git rm -r --cached 2-knowledge/

# Commit
git commit -m "Migrate to overlay contribution model"
```

## References

- [Ethereum EIP Process](https://eips.ethereum.org/EIPS/eip-1)
- [Architecture Doc](https://github.com/datacore-one/datacore-space/blob/main/1-departments/dev/architecture/repo-contribution-architecture.md)
