# DIP-0013: Meetings Module

| Field | Value |
|-------|-------|
| **DIP** | 0013 |
| **Title** | Meetings Module |
| **Author** | Gregor |
| **Type** | Module |
| **Status** | Draft |
| **Created** | 2025-12-18 |
| **Updated** | 2025-12-19 |
| **Tags** | `meetings`, `gtd`, `calendar`, `standup` |
| **Affects** | `/today`, `journal`, `next_actions.org`, `calendar.org` |
| **Depends On** | DIP-0006 (Open Questions), DIP-0010 (External Sync) |
| **Agents** | `standup-generator`, `agenda-generator`, `transcription-processor`, `question-researcher` |

## Summary

A comprehensive meetings module that automates the full meeting lifecycle: preparation, agenda generation, standup reports, transcription processing, and action item extraction. Integrates with calendar sync (DIP-0010) and open questions management (DIP-0006) to minimize manual work while maximizing meeting effectiveness.

## Motivation

### Current Pain Points

1. **Manual standup preparation** - Team members manually compile what they did yesterday
2. **Scattered meeting context** - Agendas created from memory, missing relevant items
3. **Lost transcription value** - Meeting recordings exist but action items aren't extracted
4. **No preparation workflow** - People discover discussion topics during the meeting
5. **Daily/weekly overlap** - Same items discussed multiple times without resolution
6. **Disconnected systems** - Calendar, tasks, journal, and GitHub issues don't inform each other

### Design Goals

1. **Zero-input standups** - Generate from journal and scheduled tasks automatically
2. **Pre-researched questions** - AI prepares context before meetings
3. **Automatic action items** - Extract tasks from transcriptions to org-mode
4. **Smart routing** - Suggest daily vs weekly placement for agenda items
5. **Unified flow** - Calendar -> Preparation -> Meeting -> Processing -> Tasks

## Specification

### 1. Architecture Overview

```
                         MEETINGS MODULE

   calendar.org <----> journal (notes) <----> GitHub Issues
         |                   |                     |
         +-------------------+---------------------+
                             |
                    Meeting Engine
                    - Standup gen
                    - Agenda gen
                    - Transcription
                    - Action items
                             |
         +-------------------+---------------------+
         |                   |                     |
   next_actions.org      inbox.org          open_questions
                                             (GitHub)

External Integrations:
- Google Calendar -> calendar.org (DIP-0010)
- Google Meet transcription -> Google Drive -> Import
- Granola -> .md export -> Import
```

### 2. Meeting Types

| Meeting | Cadence | Input Sources | Output |
|---------|---------|---------------|--------|
| **Daily Standup** | Daily (sync) | Journal, /today schedule, blocked tasks | Standup in journal |
| **Weekly Exec** | Weekly | Escalated items, metrics, strategic questions | Decisions, priorities |
| **Comms Weekly** | Weekly | Content pipeline, campaigns | Content assignments |
| **Verity Product** | Weekly | GitHub issues, PRs, technical questions | Issue updates, tech decisions |

#### 2.1 Daily Standup

**Purpose**: 15-minute sync on progress and blockers

**Input**:
- Yesterday's accomplishments (parsed from previous journal)
- Today's scheduled tasks (from /today output)
- Blocked/waiting tasks (from next_actions.org)

**Output**: Standup report posted to today's journal

**Automation level**: 95% automated

#### 2.2 Weekly Exec

**Purpose**: 45-minute strategic alignment

**Input**:
- Items escalated from dailies (appeared 3+ times without resolution)
- Strategic questions requiring multiple stakeholders
- Key metrics and dashboards
- Open questions tagged for weekly discussion

**Output**: Decisions documented, priorities updated, action items created

#### 2.3 Verity Product Call

**Purpose**: Working session on product development

**Input**:
- GitHub issues from verity repo (bugs, features, blocked items)
- PRs needing review or discussion
- Technical decisions requiring team input
- Architecture questions

**Output**:
- GitHub issues updated with decisions
- New issues created for follow-ups
- Technical decisions documented

### 3. Standup Generation

The key insight: **journal already contains yesterday's work**.

```
Standup = Journal(yesterday) + Schedule(today) + Blockers(waiting)
```

#### 3.1 Algorithm

```python
def generate_standup(date: date) -> StandupReport:
    # Yesterday's accomplishments
    yesterday_journal = parse_journal(date - 1)
    accomplishments = extract_accomplishments(yesterday_journal)

    # Today's plan
    today_schedule = get_scheduled_tasks(date)

    # Current blockers
    blockers = get_tasks_with_state(["WAITING", "BLOCKED"])

    return StandupReport(
        yesterday=accomplishments,
        today=today_schedule,
        blockers=blockers
    )
```

#### 3.2 Output Format

```markdown
## Standup - 2025-12-18

### Yesterday
- Completed Dubai pilot proposal review
- Fixed Verity API authentication bug
- Investor meeting (notes in [[2025-12-17]])

### Today
- [ ] Follow up on DSSC partnership
- [ ] Review calendar sync PR #42
- [ ] Prepare weekly exec agenda

### Blockers
- WAITING: Legal review for Dubai contract (since Dec 15)
- NEED: Design input from @andrej for landing page
```

#### 3.3 /today Integration

After `/today` schedules the day:

```
/today
  ... existing briefing ...
  Schedule day (interactive)

  [If daily standup in calendar.org for today]
    Generate standup report
      Parse yesterday's journal
      Use just-scheduled tasks
      Identify blockers
      Append to today's journal
```

#### 3.4 Audience-Aware Filtering

Standups are filtered based on audience context:

| Context | Filter Level | Content |
|---------|--------------|---------|
| Personal (`/standup --personal`) | None | Full detail, all metrics |
| Team Daily | Team-relevant | Outcomes only, team blockers |
| Team Weekly | Team-strategic | Strategic progress, all team blockers |
| Investor | External | Milestones, metrics, critical blockers |
| Product | Technical | Features, technical decisions, deps |

**Content Filters:**

1. **Relevance Filter** - Include only team-relevant items
   - Exclude: Personal finance, health, family items
   - Include: Shared projects, team infrastructure

2. **Outcome Framing** - Transform activities to outcomes
   - "Processed 213 emails" → "Inbox zero achieved" (or omit)
   - "Created 22 tasks" → OMIT (internal process)

3. **Anti-Anxiety Filter** - Remove worry-inducing metrics
   - Task counts, issue counts, backlog numbers
   - Overdue counts (creates pressure)

4. **Blocker Relevance** - Team blockers only
   - Keep: Team can help unblock
   - Remove: Personal admin blockers

#### 3.5 Meeting Type Presets

| Preset | Max Items | Blocker Filter | Tone |
|--------|-----------|----------------|------|
| `--meeting daily` | 5 | team_actionable | Brief, operational |
| `--meeting weekly` | 7 | all_team | Strategic, comprehensive |
| `--meeting investor` | 5 | critical_only | Professional, outcome-focused |
| `--meeting product` | 7 | technical | Technical, feature-focused |

#### 3.6 Team Project Detection

Auto-detect project/space attribution:

| Project | Keywords | Space |
|---------|----------|-------|
| Verity | verity, data marketplace, data RWA | datafund |
| Santorio | santorio, health data, longevity | datafund |
| Datacore | datacore, module, agent, GTD | datacore |
| Fair Data Society | FDS, fair data, swarm | datafund |

Detection sources:
- Wiki-links: `[[Verity]]`, `[[Santorio]]`
- Explicit tags: `[Datafund]`, `(verity)`
- Keywords in accomplishment text
- File paths: `/1-datafund/`, `/2-datacore/`

#### 3.7 Confidence Indicator

Show data quality warning when standup data is sparse:

| Confidence | Criteria | Display |
|------------|----------|---------|
| HIGH | 4+ items, fresh journal, scheduled tasks | ✓ |
| MEDIUM | 2-3 items OR fallback task source | ⚡ |
| LOW | <2 items OR stale journal (>2 days) | ⚠️ |

```
⚠️ Data confidence: LOW
   - Yesterday's journal was sparse (1 item found)
   - Consider reviewing session work sections
```

#### 3.8 Output Formats

**Full format (default):** Markdown with headers for journal posting

**Chat format (`--format chat`):** Compact for Slack/Discord:
```
📋 *Standup - Dec 19*

*Yesterday:*
• Shipped mail module v1.1.0
• Completed competitive analysis

*Today:*
• POC sprint planning
• Comms Weekly

*Blockers:* ERC-3643 eval (need legal)
```

**Brief format:** One-liner summary

#### 3.9 Historical Comparison (Future)

Planned for Phase 3:
- Week-over-week pattern detection
- Shipping streak tracking
- Blocker aging alerts
- Anomaly detection (unusual topic mix)

### 4. Open Questions Pre-Processing

Extends DIP-0006 with AI-assisted preparation.

#### 4.1 Question Classification

```
Question captured
    |
    +-> Factual question
    |     AI researches, provides summary with sources
    |
    +-> Needs specific person's input
    |     Create task: "@person provide X by [meeting date - 1 day]"
    |
    +-> Decision requiring discussion
          Identify stakeholders, add to agenda with context
```

#### 4.2 Pre-Research Agent

For questions that can be researched:

```markdown
**Question**: Should we use JWT or session-based auth for Verity API?

**AI Research Summary**:
- JWT: Stateless, scales horizontally, standard for microservices
- Sessions: Simpler revocation, better for monoliths
- Verity architecture: Microservices (from codebase analysis)

**Recommendation**: JWT aligns with architecture

**Decision needed from**: @tadej (security), @gregor (architecture)

**Sources**: [links to relevant docs/articles]
```

### 5. Daily vs Weekly Routing

Items should be routed to appropriate meeting scope.

#### 5.1 Routing Rules

| Condition | Route To |
|-----------|----------|
| Blocking someone TODAY | Daily |
| Needs multiple stakeholders | Weekly |
| Individual status update | Daily |
| Strategic/planning decision | Weekly |
| Quick tactical unblock | Daily |
| Cross-team coordination | Weekly |
| Appeared in daily 3+ times | Escalate to weekly |

#### 5.2 Escalation Detection

```python
def should_escalate_to_weekly(item: AgendaItem) -> bool:
    # Count appearances in recent dailies
    daily_appearances = count_appearances(item, days=7)

    if daily_appearances >= 3:
        return True

    # Check if multiple stakeholders needed
    if len(item.required_stakeholders) > 2:
        return True

    return False
```

### 6. Transcription Processing

#### 6.1 Import Sources

| Source | Format | Location | Import Method |
|--------|--------|----------|---------------|
| Google Meet | TBD | Google Drive | API or manual |
| Granola | Markdown | Export | File import |

#### 6.2 Processing Pipeline

```
Transcription imported
    |
    +-> Extract action items
    |     Create tasks in next_actions.org
    |       - Parse "I'll do X" / "@person will do Y"
    |       - Set assignee from context
    |       - Link to meeting source
    |
    +-> Extract decisions
    |     Add to journal entry
    |       - "We decided to..."
    |       - "The plan is..."
    |
    +-> Resolve open questions
    |     Close/update GitHub issues
    |       - Match discussed questions
    |       - Add resolution summary
    |
    +-> Capture new questions
          Create GitHub issues
            - New questions raised
            - Items needing follow-up research
```

#### 6.3 Action Item Extraction

Pattern matching for commitments:

```python
ACTION_PATTERNS = [
    r"(?:I'll|I will|I'm going to) (?P<action>.+)",
    r"@(?P<person>\w+) (?:will|should|needs to) (?P<action>.+)",
    r"(?:Action item|TODO|Task): (?P<action>.+)",
    r"(?:Let's|We should|We need to) (?P<action>.+)",
]
```

Output:
```org
*** TODO Review API rate limiting proposal :meeting:
:PROPERTIES:
:CREATED: [2025-12-18 Thu]
:SOURCE: [[Weekly Exec 2025-12-18]]
:ASSIGNEE: @tadej
:END:
From weekly exec: Tadej will review the rate limiting proposal by Friday.
```

### 7. Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `/standup` | Generate standup report | `/standup` |
| `/meeting-prep <type>` | Prepare for specific meeting | `/meeting-prep weekly-exec` |
| `/meeting-agenda <type>` | Generate full agenda | `/meeting-agenda verity-product` |
| `/meeting-process` | Process transcription | `/meeting-process ~/transcript.md` |
| `/my-questions` | Personal prep view (DIP-0006) | `/my-questions verity` |

#### 7.1 /standup

Generate standup report from journal and scheduled tasks.

**Usage**: `/standup [--date YYYY-MM-DD] [--team SPACE] [--meeting TYPE] [--format FORMAT] [--no-post]`

**Options**:
- `--date`: Generate for specific date (default: today)
- `--team`: Filter for specific team/space (e.g., `datafund`, `datacore`)
- `--meeting`: Meeting type preset: `daily`, `weekly`, `investor`, `product`
- `--format`: Output format: `full` (default), `chat` (Slack/Discord), `brief`
- `--personal`: Force personal mode (include all items)
- `--no-post`: Display without posting to journal

**Output**: Standup report with Yesterday/Today/Blockers sections, filtered by audience context.

#### 7.2 /meeting-prep

Prepare for a specific meeting type.

**Usage**: `/meeting-prep <meeting-type> [--date YYYY-MM-DD]`

**Meeting Types**:
- `daily`: Daily standup
- `weekly-exec`: Weekly executive meeting
- `comms-weekly`: Communications team weekly
- `verity-product`: Verity product working session

**Actions**:
1. Pull relevant context from calendar.org
2. Generate agenda from open questions, escalated items
3. Run pre-research on factual questions
4. Show preparation status for attendees
5. Create/update GitHub issue if applicable

#### 7.3 /meeting-process

Process meeting transcription to extract action items and decisions.

**Usage**: `/meeting-process <transcript-file> [--meeting-type TYPE]`

**Actions**:
1. Parse transcription (supports .md, .txt)
2. Extract action items -> create tasks in next_actions.org
3. Extract decisions -> add to journal
4. Resolve discussed open questions
5. Create new issues for follow-up items

**Options**:
- `--dry-run`: Show what would be created without making changes
- `--meeting-type`: Hint for context (daily, weekly, product)

### 8. Module Structure

```
.datacore/modules/meetings/
├── README.md                    # Module documentation
├── CLAUDE.md                    # AI context
├── commands/
│   ├── standup.md              # /standup command
│   ├── meeting-prep.md         # /meeting-prep command
│   ├── meeting-agenda.md       # /meeting-agenda command
│   ├── meeting-process.md      # /meeting-process command
│   └── my-questions.md         # /my-questions (from DIP-0006)
├── agents/
│   ├── standup-generator.md    # Generate standup from journal
│   ├── agenda-generator.md     # Generate meeting agendas
│   ├── transcription-processor.md  # Extract action items/decisions
│   └── question-researcher.md  # Pre-research open questions
├── templates/
│   ├── standup.md              # Standup report template
│   ├── agenda-daily.md         # Daily meeting agenda
│   ├── agenda-weekly.md        # Weekly meeting agenda
│   └── agenda-product.md       # Product working session
└── lib/
    ├── meeting_types.py        # Meeting type definitions
    ├── journal_parser.py       # Parse journal for standup
    ├── transcription.py        # Transcription import/processing
    └── action_extractor.py     # Extract action items from text
```

### 9. Configuration

```yaml
# .datacore/modules/meetings/config.yaml
meetings:
  types:
    daily-standup:
      name: "Daily Standup"
      duration: 15
      attendees: ["@gregor", "@crt", "@tadej"]
      calendar_match: "Daily"  # Match calendar.org entries
      generate_standup: true

    weekly-exec:
      name: "Weekly Exec"
      duration: 45
      attendees: ["@gregor", "@crt", "@tadej"]
      calendar_match: "Weekly Exec"
      escalate_from_daily: true

    comms-weekly:
      name: "Comms Weekly"
      duration: 45
      attendees: ["@gregor", "@crt", "@andrej"]
      calendar_match: "Comms Weekly"

    verity-product:
      name: "Verity Product Call"
      duration: 60
      attendees: ["@gregor", "@crt", "@tadej"]
      calendar_match: "Verity"
      github_repo: "datacore-one/verity"
      pull_issues: true

  transcription:
    sources:
      google-drive:
        enabled: true
        folder_id: "${GOOGLE_DRIVE_MEETINGS_FOLDER}"
      granola:
        enabled: true
        export_path: "~/Downloads"

  standup:
    auto_generate: true  # Generate during /today
    post_to_journal: true
    blockers_threshold_days: 3  # Highlight blockers older than N days

  escalation:
    daily_appearance_threshold: 3  # Escalate after N daily appearances
    auto_suggest: true
```

## Rationale

### Why a Separate Module from DIP-0006?

DIP-0006 focuses specifically on open questions management. A full meetings module encompasses:
- Multiple meeting types with different workflows
- Standup generation (not question-based)
- Transcription processing
- Calendar integration
- Action item extraction

These are related but distinct concerns. DIP-0006 becomes a component of this larger module.

### Why Journal-Based Standups?

The journal already captures work done. Requiring manual standup preparation:
1. Duplicates information
2. Relies on memory (less accurate)
3. Takes time each morning
4. Often gets skipped

Automated extraction is more accurate and requires zero effort.

### Why Route Daily vs Weekly?

Team context: With a small team, daily and weekly meetings can overlap. Explicit routing rules:
1. Prevent rehashing same items
2. Ensure strategic items get proper time
3. Keep daily meetings focused and short
4. Create clear escalation path for stuck items

## Backwards Compatibility

- New module, no breaking changes
- DIP-0006 commands (`/my-questions`, `/meeting-agenda`) are incorporated
- Existing calendar.org format unchanged
- Journal format extended but backwards compatible

## Security Considerations

- Transcriptions may contain sensitive information
- Google Drive access requires OAuth credentials
- Meeting attendee lists should respect privacy settings
- Action items with assignees visible to team

## Implementation

### Phase 1: Core Standup (MVP)
- [ ] `/standup` command
- [ ] Journal parser for yesterday's accomplishments
- [ ] Integration with `/today`
- [ ] Standup template

### Phase 2: Meeting Preparation
- [ ] `/meeting-prep` command
- [ ] Agenda generation from open questions
- [ ] Calendar.org integration for meeting context
- [ ] Question pre-research agent

### Phase 3: Transcription Processing
- [ ] Google Drive integration for transcripts
- [ ] Granola .md import
- [ ] Action item extraction
- [ ] Decision capture to journal

### Phase 4: Smart Routing
- [ ] Daily/weekly routing rules
- [ ] Escalation detection
- [ ] Cross-meeting deduplication

## Open Questions

1. **Google Meet transcript format** - Need to investigate export format from Google Drive
2. **Attendee matching** - How to match calendar attendees to @mentions in tasks?
3. **Meeting detection** - Should we auto-detect meeting type from calendar.org title, or require explicit tagging?

## References

- DIP-0006: Open Questions Management System
- DIP-0010: External Sync Architecture (Calendar Adapter)
- DIP-0009: GTD Specification

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-18 | 0.1 | Initial draft |
| 2025-12-19 | 0.2 | Added: Audience-aware filtering (3.4), Meeting type presets (3.5), Team project detection (3.6), Confidence indicator (3.7), Chat export format (3.8), Historical comparison spec (3.9). Updated /standup command with new options. |
