# DIP-0006: Open Questions Management System

**Status:** Draft
**Author:** AI System
**Created:** 2025-12-03
**Type:** Process Enhancement

## Abstract

Create a systematic approach to capture, track, and resolve open questions across projects using GitHub issues and AI-assisted meeting facilitation. Includes individual preparation workflows to ensure stakeholders review relevant questions before meetings.

## Motivation

Projects generate many open questions that get lost or forgotten:

1. **Questions scattered**: In documents, chat, code comments, meeting notes
2. **No centralized tracking**: Hard to know what decisions are pending
3. **Meeting inefficiency**: Time wasted identifying what needs discussion
4. **Context loss**: Questions lack project context and stakeholder relevance
5. **No preparation time**: People first see questions during the meeting
6. **Follow-up gaps**: Decisions made but issues not updated

A structured system would provide:
- **Centralized collection**: All questions captured in GitHub issues
- **Individual preparation**: People can review questions requiring their input
- **Context-aware processing**: Questions filtered by project and attendees
- **Meeting efficiency**: Pre-populated agendas with relevant questions
- **Automatic tracking**: Issues updated based on meeting outcomes

## Specification

### 1. Question Collection Patterns

**Source Detection**: AI scans for questions in:
- Document sections ending with "Open Questions", "Unresolved", "TBD"
- Code comments with `TODO:`, `FIXME:`, `QUESTION:`
- Meeting transcripts and conversation exports
- Plan documents with decision points

**Question Format**: Standardized structure:
```
**Project**: [project-name]
**Context**: [brief context]
**Question**: [concise question]
**Stakeholders**: [@username1, @username2]
**Priority**: [high/medium/low]
**Due**: [date if time-sensitive]
```

### 2. Individual Preparation Workflow

**Command: `/my-questions [project]`**

```bash
# Examples
/my-questions verity
/my-questions --all
/my-questions datacore --upcoming-meeting
```

**Behavior**:
1. Filter all open questions where user is mentioned as stakeholder
2. Show context and background for each question
3. Group by project and priority
4. Include preparation suggestions ("Review X document", "Check with Y team")
5. Allow adding responses/notes for meeting

**Output Format**:
```markdown
# Your Open Questions - Preparation for Meeting

## High Priority (Requires Your Decision)
### VERITY - API Architecture
**Question**: Should we implement rate limiting on the API?
**Context**: Current API has no throttling, enterprise customers asking about scalability
**Background**: See docs/architecture/api-scaling.md
**Your Role**: Technical decision maker
**Suggested Prep**: Review current load patterns, check competitor approaches

**Quick Response** (optional):
- [ ] Yes, implement rate limiting
- [ ] No, handle with horizontal scaling
- [ ] Need more research

## Medium Priority (Your Input Valued)
[Additional questions where user is mentioned...]

---
*Found 5 questions requiring your input across 2 projects*
*Use `/meeting-agenda [project]` to create full agenda*
```

### 3. Meeting Agenda Generation

**Command: `/meeting-agenda [project]`**

```bash
# Examples
/meeting-agenda verity
/meeting-agenda datacore --attendees @crt,@gregor
/meeting-agenda --all
```

**Enhanced Behavior**:
1. Scan project for open questions from multiple sources
2. Check existing GitHub issues for unresolved questions
3. Include any pre-meeting responses from `/my-questions`
4. Filter by stakeholder relevance (if attendees specified)
5. Show preparation status for each attendee
6. Create/update GitHub issue with structured agenda

### 4. Meeting Workflow Integration

**Complete Workflow**:

1. **Individual Preparation** (2-3 days before):
   - Each stakeholder runs `/my-questions [project]`
   - People review questions requiring their input
   - Can add preliminary thoughts/responses
   - System tracks preparation status

2. **Agenda Creation** (1 day before):
   - Meeting organizer runs `/meeting-agenda [project]`
   - Incorporates pre-meeting input
   - Shows who has/hasn't prepared

3. **During Meeting**:
   - Use GitHub issue as structured agenda
   - Build on preparation rather than starting from scratch
   - Check off resolved questions

4. **Post-Meeting**:
   - Run `/close-questions [issue-number]`
   - Process outcomes and decisions
   - Create follow-up issues

### 5. Enhanced Command Set

| Command | Purpose | Example |
|---------|---------|---------|
| `/my-questions [project]` | Personal preparation view | `/my-questions verity` |
| `/meeting-agenda [project]` | Generate meeting agenda | `/meeting-agenda verity --attendees @crt,@gregor` |
| `/close-questions [issue]` | Process meeting outcomes | `/close-questions 123` |
| `/add-question [project]` | Quick question capture | `/add-question verity "Budget for Q1?"` |

## Example Complete Workflow

**Monday - Questions Arise**:
```markdown
## Open Questions
- Should we implement rate limiting on the API? (@gregor @crt)
```

**Wednesday - Individual Prep**:
```bash
/my-questions verity
# Shows context, suggests research, allows pre-meeting input
```

**Thursday - Agenda Creation**:
```bash
/meeting-agenda verity --attendees @crt,@gregor,@tadej
# Creates structured GitHub issue with preparation status
```

**Friday - Meeting**:
- Efficient discussion building on preparation
- Make decisions, check off questions

**Post-Meeting**:
```bash
/close-questions 142
# Creates follow-up issues, updates documents
```

## Benefits

1. **Better Preparation**: People review questions in advance with full context
2. **Meeting Efficiency**: 30-50% faster meetings with informed participants
3. **Higher Quality Decisions**: Decisions based on research, not first impressions
4. **Reduced Meeting Anxiety**: No surprises, everyone knows what to expect
5. **Clear Ownership**: Obvious who needs to provide input on what
6. **Decision Tracking**: Complete audit trail with preparation context

## Compatibility

Works with existing DIPs:
- **DIP-0001**: Uses standard GitHub contribution patterns
- **DIP-0005**: Integrates with GitHub-based onboarding questions
- **DIP-0002**: Can process questions from layered context files

## Implementation

**Phase 1**: Core commands (`/my-questions`, `/meeting-agenda`)
**Phase 2**: Preparation status tracking, pre-meeting input capture
**Phase 3**: Calendar integration, smart notifications

---

**Implementation Status**: Draft - Ready for team review and implementation planning