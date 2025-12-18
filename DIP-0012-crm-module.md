# DIP-0012: CRM Module

| Field | Value |
|-------|-------|
| **DIP** | 0012 |
| **Title** | CRM Module |
| **Author** | Gregor |
| **Type** | Module |
| **Status** | Draft |
| **Created** | 2025-12-18 |
| **Updated** | 2025-12-18 |
| **Tags** | `crm`, `contacts`, `relationships`, `adapters` |
| **Affects** | `/today`, `/gtd-weekly-review`, knowledge base, modules |
| **Specs** | - |
| **Agents** | `crm-interaction-extractor`, `crm-relationship-scorer` |
| **Related DIPs** | DIP-0002, DIP-0009, DIP-0010 |

## Summary

The CRM module provides relationship management for Datacore, serving as a central hub that aggregates contact interactions from multiple channels (journal, calendar, meeting notes, email, telegram, linkedin). It maintains contact notes with interaction history, surfaces relationship insights in daily/weekly workflows, and supports privacy staging between personal and team spaces.

## Motivation

### Problem

Professional relationships are captured across fragmented channels:
- Journal entries mention people but don't aggregate to a contact view
- Calendar shows meetings but doesn't track relationship history
- Email, Telegram, LinkedIn hold valuable interaction data in silos
- No unified view of "when did I last talk to X" or "who should I follow up with"
- No preparation support before trips/conferences

### Solution

A CRM module that:
1. **Aggregates** interactions from multiple sources via adapter interface
2. **Maintains** contact notes with structured metadata and interaction log
3. **Surfaces** relationship insights in `/today` and `/gtd-weekly-review`
4. **Supports** privacy staging (personal contacts → team contacts when formalized)
5. **Prepares** users for trips/events with relevant contact context

### Use Cases

- "Show me everyone I haven't talked to in 60 days"
- "Before my flight to Abu Dhabi, who should I meet?"
- "What's the history with Animoca Brands?"
- "Add a follow-up task for John Smith"
- "Move this contact to the Datafund space"

## Specification

### 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                       CAPTURE LAYER (Adapters)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐ │
│  │ Journal  │ │ Calendar │ │ Meeting  │ │   Mail   │ │  Telegram/  │ │
│  │ (CRM)    │ │ (CRM)    │ │  Notes   │ │ (module) │ │  LinkedIn   │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬──────┘ │
│       └────────────┴────────────┴────────────┴──────────────┘        │
│                                 │                                     │
│                                 ▼                                     │
│              ┌────────────────────────────────┐                      │
│              │      CRM MODULE (HUB)          │                      │
│              │  - Contact notes               │                      │
│              │  - Interaction log             │                      │
│              │  - Relationship scoring        │                      │
│              └────────────────┬───────────────┘                      │
└───────────────────────────────┼──────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         SURFACE LAYER                                 │
│  /today            /gtd-weekly-review         Contact notes          │
│  - Follow-ups      - Relationship health      - Interaction log      │
│  - Dormant         - Follow-up queue          - Next actions         │
│  - Pre-meeting     - Contacts engaged                                │
└──────────────────────────────────────────────────────────────────────┘
```

### 2. Adapter Interface

The CRM module defines an abstract interface that other modules implement to feed interactions.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class Interaction:
    """A single interaction with a contact."""
    contact_name: str           # Resolved contact name
    channel: str                # 'journal', 'calendar', 'mail', etc.
    timestamp: datetime         # When interaction occurred
    interaction_type: str       # 'meeting', 'email', 'message', 'mention'
    summary: str                # Brief description
    source_link: str            # Link to source (journal entry, email, etc.)
    participants: List[str]     # Other people involved (optional)
    action_items: List[str]     # Follow-ups identified (optional)


class CRMAdapter(ABC):
    """Base interface for CRM interaction adapters."""

    @property
    @abstractmethod
    def adapter_type(self) -> str:
        """Unique identifier (e.g., 'journal', 'mail', 'telegram')."""

    @abstractmethod
    def extract_interactions(self, since: datetime) -> List[Interaction]:
        """Extract contact interactions from this channel since timestamp."""

    @abstractmethod
    def resolve_contact(self, identifier: str) -> Optional[str]:
        """Resolve channel-specific ID to contact name.

        Examples:
        - Email: 'john@example.com' -> 'John Smith'
        - Telegram: '@jsmith' -> 'John Smith'
        - Calendar: 'john@example.com' -> 'John Smith'
        """

    def get_contact_identifiers(self, contact_name: str) -> List[str]:
        """Get all known identifiers for a contact in this channel.

        Optional - used for matching across channels.
        """
        return []
```

### 3. Built-in Adapters

The CRM module includes two built-in adapters:

#### Journal Adapter

Extracts `[[Contact Name]]` wiki-links from daily journal entries.

```python
class JournalAdapter(CRMAdapter):
    adapter_type = "journal"

    def extract_interactions(self, since: datetime) -> List[Interaction]:
        # Scan journals from `since` date
        # Extract [[wiki-links]] that match known contacts
        # Return Interaction for each mention with context
        pass
```

#### Calendar Adapter

Extracts meeting attendees from `calendar.org` (synced via DIP-0010).

```python
class CalendarAdapter(CRMAdapter):
    adapter_type = "calendar"

    def extract_interactions(self, since: datetime) -> List[Interaction]:
        # Parse calendar.org entries since `since` date
        # Extract attendees from meetings
        # Return Interaction with type='meeting'
        pass
```

### 4. External Module Adapters

Other modules implement `CRMAdapter` to integrate:

| Module | Adapter Type | What It Extracts |
|--------|--------------|------------------|
| `meeting-notes` | `meeting-notes` | Participants, discussion points, action items |
| `mail` | `mail` | Email conversations by sender/recipient |
| `telegram` | `telegram` | Messages by chat participant |
| `linkedin` | `linkedin` | Messages, connection requests |

Modules register their adapter via `module.yaml`:

```yaml
# In telegram/module.yaml
provides:
  crm_adapter: telegram
```

### 5. Folder Structure

#### Hybrid Approach: `contacts/` + `reference/`

| Folder | Purpose | Updates |
|--------|---------|---------|
| `contacts/` | Active CRM - relationships with interaction tracking | Frequent, auto-populated |
| `reference/` | Static knowledge - people/companies as reference | Manual, occasional |

**Rationale:** Separates "how we engage" (active CRM) from "what we know" (reference knowledge). A company might exist in `reference/` as market research, but only appear in `contacts/` when there's a real relationship.

#### Per-Space Structure

```
[space]/contacts/
├── _index.md              # Contacts index for this space
├── people/
│   └── [Person Name].md
└── companies/
    └── [Company Name].md
```

### 6. Contact Note Schema

#### Person Contact

```yaml
---
type: contact
contact_type: person
name: "John Smith"
status: active              # draft | active | dormant | archived
privacy: team               # personal | team
space: 1-datafund
organization: "[[Acme Corp]]"
role: "VP of Partnerships"
channels:
  email: john@acme.com
  telegram: "@jsmith"
  linkedin: "/in/johnsmith"
  phone: "+1-555-0123"
location: "New York, USA"
tags: [investor, partner, crypto]
introduced_by: "[[Jane Doe]]"
met_at: "ETH Denver 2024"
created: 2024-03-15
updated: 2025-12-18
last_interaction: 2025-12-10
---

# John Smith

## Overview

VP of Partnerships at [[Acme Corp]]. Met at ETH Denver 2024, introduced by [[Jane Doe]].

**Relevance:** Key decision maker for potential partnership. Strong network in DeFi space.

## Goals

**What I want:**
- Partnership introduction to their data team
- Investment consideration for seed round

**What they want:**
- Data infrastructure solutions
- AI integration capabilities

## Notes

[Freeform notes, personality observations, conversation highlights]

## Interaction Log

<!-- Auto-populated by CRM adapters -->

| Date | Channel | Type | Summary |
|------|---------|------|---------|
| 2025-12-10 | calendar | meeting | Quarterly sync - discussed roadmap |
| 2025-11-28 | mail | email | Sent partnership proposal |
| 2025-11-15 | journal | mention | Noted follow-up needed |

## Next Actions

<!-- Embedded from next_actions.org with :CRM: tag -->

```org
* TODO Follow up on partnership proposal   :CRM:
  SCHEDULED: <2025-12-20 Fri>
  :PROPERTIES:
  :CONTACT: John Smith
  :END:
```

## Related

- [[Acme Corp]]
- [[Jane Doe]]
- [[Partnership Pipeline]]
```

#### Company Contact

```yaml
---
type: contact
contact_type: company
name: "Acme Corp"
status: active
category: partner           # partner | investor | customer | vendor | competitor
industry: "DeFi Infrastructure"
stage: "Series B"
space: 1-datafund
website: "https://acme.com"
linkedin: "/company/acmecorp"
location: "San Francisco, USA"
tags: [defi, infrastructure, partner]
created: 2024-03-15
updated: 2025-12-18
last_interaction: 2025-12-10
---

# Acme Corp

## Overview

DeFi infrastructure company, Series B stage. Potential strategic partner.

**Relevance:** Their data layer could integrate with our marketplace.

## Key Contacts

| Name | Role | Status |
|------|------|--------|
| [[John Smith]] | VP Partnerships | Active |
| [[Sarah Jones]] | CTO | Dormant |

## Relationship

**Type:** Strategic partner
**Stage:** In discussion
**Owner:** @gregor

## Notes

[Company strategy, competitive positioning, deal history]

## Interaction History

<!-- Aggregated from key contacts -->

## Next Actions

<!-- Aggregated from all contacts at this company -->

## Related

- [[DeFi Partnerships]]
- [[Competitor Analysis]]
```

### 7. Cross-Space Index (DIP-0002)

Following the Layered Context Pattern, a cross-space contact index aggregates contacts from all spaces.

#### Index Location

```
.datacore/state/crm/
├── contacts-index.yaml     # Generated, aggregated index
└── last-sync.yaml          # Sync metadata
```

#### Index Schema

```yaml
generated: 2025-12-18T10:00:00Z
sources:
  - space: 0-personal
    path: 0-personal/contacts/
    count: 47
  - space: 1-datafund
    path: 1-datafund/contacts/
    count: 23

contacts:
  - name: "John Smith"
    type: person
    space: 1-datafund
    path: 1-datafund/contacts/people/John Smith.md
    status: active
    last_interaction: 2025-12-10
    relationship_score: 0.85
    tags: [investor, partner]

  - name: "Personal Contact"
    type: person
    space: 0-personal
    path: 0-personal/contacts/people/Personal Contact.md
    status: active
    privacy: personal  # Not visible in team views
```

### 8. Privacy Staging Workflow

Contacts can be staged from personal to team space when relationship formalizes.

#### Promotion Flow

1. Contact exists in `0-personal/contacts/`
2. User decides to share with team
3. Run `/crm` → "Promote to team space"
4. Contact copied to `1-datafund/contacts/`
5. Personal note becomes reference with private notes preserved

```yaml
# 0-personal/contacts/people/John Smith.md (after promotion)
---
type: contact-ref
canonical: 1-datafund/contacts/people/John Smith.md
---

# John Smith

**Promoted to team space.** See: [[1-datafund/contacts/people/John Smith]]

## Personal Notes (not synced)

[Private observations stay here]
```

#### Privacy Boundaries

| Content | Personal Space | Team Space |
|---------|----------------|------------|
| Basic info | Full | Full |
| Interaction log | Full | Team-relevant only |
| Personal notes | Yes | No |
| Goals (personal) | Yes | No |
| Goals (team) | No | Yes |

### 9. GTD Integration

#### Task Tagging

CRM tasks use `:CRM:` tag in `next_actions.org`:

```org
* TODO Follow up with [[John Smith]] on partnership   :CRM:
  SCHEDULED: <2025-12-20 Fri>
  :PROPERTIES:
  :CONTACT: John Smith
  :EFFORT: 0:15
  :END:

* WAITING Response from [[Jane Doe]] on proposal      :CRM:
  :PROPERTIES:
  :CONTACT: Jane Doe
  :WAITING_FOR: Email response
  :END:
```

#### Contact Note Embedding

Contact notes display their `:CRM:` tasks:
- Filtered by `:CONTACT:` property matching contact name
- Shows TODO, NEXT, WAITING states
- Excludes DONE (history in interaction log)

### 10. `/crm` Command

Single conversational command for all CRM operations:

```markdown
# /crm

CRM - Contact Relationship Management

## Intent Detection

If user provides context, infer intent:
- "John Smith" → View/edit contact
- "trip to Dubai" → Trip preparation
- "scan" or "update" → Scan for interactions

If no context, present menu:

## Menu

What would you like to do?

1. **View network status** - Dashboard of your contacts
2. **Prepare for trip/event** - Pre-meeting briefing
3. **Scan for interactions** - Update from journals/calendar
4. **Create or update contact** - Add or edit contact

## Workflows

### 1. Network Status

Display:
- Total contacts (by space, by status)
- Recent interactions (last 7 days)
- Dormant contacts (>60 days, high value)
- Pending follow-ups

### 2. Trip Preparation

Input: Event name, location, dates

Output:
- Contacts in region (by location field)
- Contacts relevant to event (by tags)
- Dormant contacts worth reconnecting
- Suggested pre-trip tasks

### 3. Scan for Interactions

Run adapters (journal, calendar) to:
- Detect new interactions
- Update interaction logs
- Flag new potential contacts

### 4. Create/Update Contact

Guided workflow:
- Person or Company?
- Basic info
- Channel identifiers
- Initial notes
```

### 11. Integration Points

#### `/today` Additions

```markdown
### CRM Highlights

**Today's Meetings:**
Before each meeting, show attendee context:
- [[John Smith]] - Last: Dec 10, Acme Corp, partnership discussion

**Follow-ups Due:**
- [ ] Email [[Jane Doe]] re: proposal    :CRM:

**Dormant (High Value):**
- [[Investor X]] - 45 days since last contact
```

#### `/gtd-weekly-review` Additions

```markdown
### CRM Weekly Review

**Interactions This Week:**
- Total: 12 interactions
- Contacts engaged: 8
- New contacts: 2

**Relationship Health:**
- Active (<14 days): 34
- Warming (14-30): 15
- Cooling (30-60): 12
- Dormant (>60): 17

**Follow-up Queue:**
Top 5 overdue follow-ups

**Next Week:**
- 3 meetings scheduled
- Contacts to prepare for
```

### 12. Relationship Scoring

Contacts have a `relationship_score` (0-1) based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Recency | 40% | Exponential decay from last interaction |
| Frequency | 30% | Interactions per month |
| Depth | 20% | Meeting > email > mention |
| Reciprocity | 10% | Two-way vs one-way |

Score thresholds:
- `> 0.7` Active
- `0.4 - 0.7` Warming/Cooling
- `< 0.4` Dormant

## Rationale

### Why Hybrid Folder Structure?

**Alternative:** Single `reference/` folder for all entity knowledge.

**Rejected because:** Mixes static knowledge ("what we know about Acme Corp") with active relationship management ("we're in partnership discussions with Acme Corp"). The hybrid approach separates concerns and allows contact-specific workflow (interaction log, follow-ups) without cluttering reference knowledge.

### Why Adapter Interface?

**Alternative:** CRM directly integrates with each channel.

**Rejected because:** Tight coupling makes the module unwieldy and forces all channels to be in one module. The adapter interface allows:
- Separate modules for telegram, linkedin, etc.
- Clean integration contract
- Modules can exist without CRM, CRM enhances them

### Why Single `/crm` Command?

**Alternative:** Multiple commands (`/crm-scan`, `/crm-prep`, `/crm-status`).

**Rejected because:** Follows Datacore's conversational command philosophy. One entry point, guided workflow based on user intent. Reduces cognitive load ("what command do I need?").

## Backwards Compatibility

- No breaking changes to existing structure
- `contacts/` folder is new, doesn't conflict with `reference/`
- Existing `reference/` notes remain unchanged
- Optional module - system works without it

## Security Considerations

- **Privacy staging** prevents accidental sharing of personal contacts
- **Personal notes** section never syncs to team spaces
- **Channel identifiers** (email, phone) are stored in contact notes, not central index
- Cross-space index only contains metadata, not full contact content

## Implementation

### Phase 1: Core Structure
- [ ] Create module scaffold
- [ ] Implement contact note templates
- [ ] Create `contacts/` folder structure

### Phase 2: Built-in Adapters
- [ ] Implement journal adapter
- [ ] Implement calendar adapter
- [ ] Create interaction extraction logic

### Phase 3: Commands & Integration
- [ ] Implement `/crm` command
- [ ] Add CRM section to `/today`
- [ ] Add CRM section to `/gtd-weekly-review`

### Phase 4: Cross-Space Index
- [ ] Implement index compiler
- [ ] Implement relationship scorer
- [ ] Create privacy staging workflow

### Phase 5: External Adapters
- [ ] Document adapter interface for other modules
- [ ] Coordinate with meeting-notes module
- [ ] Coordinate with mail module

## Open Questions

1. **Duplicate detection:** How to handle same person appearing in multiple spaces with different names?
2. **Merge contacts:** Workflow for merging duplicate contacts?
3. **Calendar attendee resolution:** How to map email addresses to contact names reliably?

## References

- [DIP-0002: Layered Context Pattern](./DIP-0002-layered-context-pattern.md) - Cross-space index compilation
- [DIP-0009: GTD Specification](./DIP-0009-gtd-specification.md) - Task integration
- [DIP-0010: External Sync Architecture](./DIP-0010-external-sync-architecture.md) - Adapter pattern inspiration
