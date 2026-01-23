# DIP-0005: GitHub-Based Onboarding System

**Status:** Draft
**Author:** AI System
**Created:** 2025-12-03
**Type:** Process Enhancement

## Abstract

Replace static onboarding with dynamic GitHub issue-based onboarding that tracks progress and integrates with existing workflows.

## Motivation

Current onboarding lacks progress tracking and customization. A GitHub-based system provides:
- Progress visibility
- Individual tracking
- Easy updates and improvements
- Integration with existing project management

## Specification

### 1. Issue Identification

**Title Convention:**
```
[ONBOARDING] @username - Datacore Setup
```

**Required Label:** `onboarding`

### 2. Detection Logic

AI system detects via GitHub API:
```
repo:datacore-one/datacore
is:issue
is:open
label:onboarding
assignee:@username
```

### 3. Daily Integration

**Enhanced `/today` command shows:**
```markdown
## Onboarding Progress
Active: Datacore Setup (Issue #123)
- [ ] 3 of 8 tasks complete
- [ ] Next: Configure GTD files

[View full checklist →](github.com/datacore-one/datacore/issues/123)
```

### 4. Simple Issue Template

```markdown
---
name: Datacore Onboarding
about: Get started with your Datacore system
title: '[ONBOARDING] @username - Datacore Setup'
labels: ['onboarding']
---

## Welcome to Datacore!

Complete these tasks to get your system running:

### System Setup
- [ ] Install Datacore (`git clone...`)
- [ ] Run `/diagnostic` - verify installation
- [ ] Create initial GTD files (inbox.org, next_actions.org)

### Learn the Basics
- [ ] Add a task to inbox.org
- [ ] Run `/gtd-daily-end` to process it
- [ ] Try `/today` for daily briefing
- [ ] Complete first `/gtd-weekly-review`

### Try AI Delegation
- [ ] Add task with `:AI:research:` tag
- [ ] Let overnight processing work
- [ ] Review AI work in morning briefing

### Customize Your Flow
- [ ] Set up daily habits in habits.org
- [ ] Organize notes/ folder for your needs
- [ ] Explore modules (optional)

**Questions?** Comment below or tag @datacore-team

---
Close this issue when you're comfortable with the basic workflow.
```

### 5. AI Behavior

**Daily briefing (`/today`):**
- Shows active onboarding issue if exists
- Displays checked/unchecked task count
- Links to GitHub issue

**Simple prompts:**
- "Update onboarding progress?"
- "Need help with any onboarding tasks?"

## Implementation

**Minimal viable version:**
1. Create issue template
2. Add onboarding detection to `/today`
3. Simple progress display

**Future enhancements:**
- Auto-create issues for new users
- Role-specific variations
- Progress analytics

## Benefits

- **Simple**: Single template, easy to understand
- **Trackable**: Clear progress visibility
- **Flexible**: Issues can be customized per user
- **Integrated**: Works with existing GitHub workflow

---

**Next Steps**: Create issue template, test with pilot users, iterate based on feedback.