# DIP-0012: CRM Module

| Field | Value |
|-------|-------|
| **DIP** | 0012 |
| **Title** | CRM Module |
| **Author** | Gregor |
| **Type** | Module |
| **Status** | Draft |
| **Created** | 2025-12-18 |
| **Updated** | 2025-12-19 |
| **Tags** | `crm`, `contacts`, `relationships`, `adapters`, `network-intelligence` |
| **Affects** | `/today`, `/gtd-weekly-review`, knowledge base, modules, research |
| **Specs** | - |
| **Agents** | `crm-interaction-extractor`, `crm-relationship-scorer`, `crm-entity-extractor`, `crm-contact-maintainer` |
| **Related DIPs** | DIP-0002, DIP-0009, DIP-0010 |

## Summary

The CRM module provides **Network Intelligence** for Datacore - a comprehensive system for tracking entities (people, companies, projects, events), their relationships, and industry landscape. It serves as a central hub that:

1. **Captures entities** from research, journals, calendar, and external channels
2. **Tracks relationship evolution** from discovery → lead → active → partner
3. **Aggregates interactions** from multiple sources via adapter interface
4. **Maintains contact notes** with structured metadata and interaction history
5. **Provides industry landscape** visualization and strategic insights
6. **Surfaces relationship insights** in `/today` and `/gtd-weekly-review`
7. **Supports privacy staging** between personal and team spaces

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

### 1. Entity & Relationship Taxonomy

#### Entity Types

The CRM tracks four entity types:

```yaml
entity_types:
  person:     # Individual contact
  company:    # Organization
  project:    # Product, initiative, protocol
  event:      # Conference, meetup, workshop
```

#### Relationship Status (Lifecycle)

Tracks where entities are in the relationship lifecycle:

```yaml
relationship_status:
  # Discovery phase
  discovered:     # Found in research, no contact yet
  lead:           # Identified as relevant, potential outreach

  # Engagement phase
  contacted:      # Initial outreach made
  in_discussion:  # Active conversation
  negotiating:    # Deal/partnership in progress

  # Established phase
  active:         # Ongoing relationship
  partner:        # Formal partnership
  customer:       # Paying customer
  investor:       # Has invested

  # Inactive phase
  dormant:        # No recent interaction
  churned:        # Former customer/partner
  archived:       # Closed, no longer relevant
```

#### Relationship Types

Describes the nature of the relationship:

```yaml
relationship_types:
  # Collaborative
  partner:              # Strategic/integration partner
  investor:             # Financial backer
  customer:             # Paying user
  vendor:               # Service/product provider
  advisor:              # Provides guidance
  collaborator:         # Project collaboration

  # Neutral
  peer:                 # Industry peer, neutral
  acquaintance:         # Know but no formal relationship
  press:                # Media contact

  # Competitive
  competitor:           # Direct competitor
  indirect_competitor:  # Adjacent market

  # Potential
  target_customer:      # Potential customer
  target_partner:       # Potential partner
  target_investor:      # Potential investor
```

#### Relevance Score

Strategic importance (1-5):

```yaml
relevance:
  5: critical   # Must-have relationship
  4: high       # Important for strategy
  3: medium     # Useful connection
  2: low        # Nice to have
  1: minimal    # Peripheral
```

#### Industry Tags (Dynamic Registry)

Industries are **discovered, not prescribed**. No hardcoded list - industries are registered when first used and become canonical for consistency.

**Registry location:** `.datacore/state/crm/industries.yaml`

```yaml
# Auto-generated registry
industries:
  rwa:
    label: "RWA"
    aliases: [real_world_assets]
    count: 12
    first_seen: 2025-12-18

  gold_trade_data:
    label: "Gold Trade Data"
    aliases: []
    count: 3
    first_seen: 2025-12-19
```

**Registry principles:**
1. First use creates canonical entry
2. New tags checked against existing (Levenshtein similarity)
3. Aliases map variations to canonical key
4. Normalization: `lowercase_underscores`

### 2. Architecture Overview

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
├── companies/
│   └── [Company Name].md
├── projects/
│   └── [Project Name].md
├── events/
│   └── [Event Name].md
└── landscape/
    ├── _overview.md       # Industry landscape summary
    ├── competitors.md     # Competitive analysis
    └── ecosystem.md       # Partner/vendor ecosystem
```

### 6. Contact Note Schema

#### Person Contact

```yaml
---
type: contact
entity_type: person
name: "John Smith"
status: active                    # draft | active | dormant | archived
relationship_status: active       # discovered | lead | contacted | in_discussion | active | partner | dormant | archived
relationship_type: partner        # partner | investor | customer | vendor | advisor | peer | competitor | target_*
relevance: 4                      # 1-5 (minimal to critical)
privacy: team                     # personal | team
space: 1-datafund
organization: "[[Acme Corp]]"
role: "VP of Partnerships"
industries: [defi, data_infrastructure]
channels:
  email: john@acme.com
  telegram: "@jsmith"
  linkedin: "/in/johnsmith"
  phone: "+1-555-0123"
location: "New York, USA"
tags: [crypto, web3]
introduced_by: "[[Jane Doe]]"
met_at: "ETH Denver 2024"
discovered_in: ""                 # Source: "[[Literature Note]]" | "research" | "journal"
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
entity_type: company
name: "Acme Corp"
status: active                    # draft | active | dormant | archived
relationship_status: active       # discovered | lead | contacted | in_discussion | active | partner | dormant | archived
relationship_type: partner        # partner | investor | customer | vendor | competitor | target_*
relevance: 4                      # 1-5 (minimal to critical)
industries: [defi, data_infrastructure]
market_position: competitor       # competitor | leader | emerging | adjacent
stage: "Series B"                 # seed | series_a | series_b | growth | enterprise
space: 1-datafund
website: "https://acme.com"
linkedin: "/company/acmecorp"
location: "San Francisco, USA"
tags: [web3, infrastructure]
discovered_in: ""                 # Source: "[[Literature Note]]" | "research" | "journal"
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

#### Project Contact

For tracking protocols, products, platforms, and initiatives.

```yaml
---
type: contact
entity_type: project
name: "Filecoin"
status: active                    # draft | active | dormant | archived
relationship_status: discovered   # discovered | lead | active | partner | competitor
relationship_type: peer           # partner | competitor | target_partner | peer
relevance: 3                      # 1-5 (minimal to critical)
industries: [storage, web3, data_infrastructure]
project_type: protocol            # protocol | platform | product | initiative
stage: mainnet                    # concept | development | testnet | mainnet | mature
parent_company: "[[Protocol Labs]]"
website: "https://filecoin.io"
github: "https://github.com/filecoin-project"
docs: "https://docs.filecoin.io"
tags: [decentralized_storage, ipfs]
discovered_in: "[[Research - Storage Protocols]]"
created: 2025-12-19
updated: 2025-12-19
---

# Filecoin

## Overview

Decentralized storage network built on IPFS. Major player in Web3 storage infrastructure.

**Relevance:** Potential integration partner or competitor in storage space.

## Technical Summary

<!-- Key technical details, architecture, capabilities -->

## Competitive Position

**Market position:** Leader in decentralized storage
**Strengths:**
- Large network, proven at scale
- Strong ecosystem

**Weaknesses:**
- Complex onboarding
- Storage costs

## Key People

| Name | Role | Our Status |
|------|------|------------|
| [[Juan Benet]] | Founder | Dormant |

## Related Projects

- [[IPFS]]
- [[Arweave]] (competitor)

## Notes

<!-- Strategic observations, integration possibilities -->

## Related

- [[Protocol Labs]]
- [[Storage Landscape]]
```

#### Event Contact

For tracking conferences, meetups, workshops, and industry events.

```yaml
---
type: contact
entity_type: event
name: "ETH Denver 2025"
status: active                    # draft | active | completed | archived
event_type: conference            # conference | meetup | workshop | hackathon | summit
industries: [web3, defi, ethereum]
relevance: 4                      # 1-5 (minimal to critical)
date_start: 2025-02-23
date_end: 2025-03-02
location: "Denver, Colorado, USA"
website: "https://ethdenver.com"
tags: [ethereum, crypto, networking]
discovered_in: ""
created: 2025-12-19
updated: 2025-12-19
---

# ETH Denver 2025

## Overview

Major Ethereum conference and hackathon. Key networking opportunity for Web3 projects.

**Relevance:** Priority event for partnership development and industry visibility.

## Our Goals

- [ ] Secure speaking slot
- [ ] Schedule meetings with target partners
- [ ] Host side event

## Key Contacts Attending

| Contact | Company | Meeting Status |
|---------|---------|----------------|
| [[John Smith]] | [[Acme Corp]] | Scheduled |
| [[Jane Doe]] | [[Protocol Labs]] | Requested |

## Target Introductions

People/companies we want to meet at this event:

- [[Target Company A]] - Potential partner
- [[Target Person B]] - Investor connection

## Schedule

<!-- Planned meetings, talks, side events -->

## Notes

<!-- Pre-event prep, post-event debrief -->

## Related

- [[Conference Calendar]]
- [[ETH Denver 2024]] (previous year)
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

### 13. Contact Creation Interface

Standardized interface for other agents (e.g., research processor) to create contacts.

```yaml
# Contact creation interface for other agents
contact_creation:
  required_fields:
    name: string                    # Entity name
    entity_type: person | company | project | event
    source: string                  # "[[Literature Note]]" | "research" | "journal"
    source_context: string          # Brief context where discovered

  optional_fields:
    relationship_status: discovered # Default for new entities
    relationship_type: string
    industries: []                  # Will register new industries
    tags: []
    organization: "[[Company]]"     # For persons
    relevance: 1-5                  # Default: 2
    location: string

  output:
    path: "[space]/contacts/[entity_type_plural]/[Name].md"
    status: draft                   # Requires human review
```

**Usage by research processor:**
```python
# After processing article about Filecoin
crm.create_contact({
    'name': 'Filecoin',
    'entity_type': 'project',
    'source': '[[Storage Protocols Research]]',
    'source_context': 'Decentralized storage network, competitor analysis',
    'industries': ['storage', 'web3'],
    'relationship_status': 'discovered',
    'relevance': 3
})
```

### 14. Entity Extractor Agent

**Agent:** `crm-entity-extractor`

Extracts entities (people, companies, projects, events) from research outputs and literature notes.

```yaml
trigger:
  - After gtd-research-processor creates literature note
  - After research-link-processor creates report
  - Manual: /crm extract [file]

input:
  file_path: string     # Literature note or research report
  auto_create: boolean  # Create draft contacts automatically (default: false)

process:
  1. Scan for person patterns:
     - Capitalized names followed by role/title context
     - Pattern: "[Name], [Role] at [Company]"
     - Pattern: "[Name] ([Title])"

  2. Scan for company patterns:
     - Names with Inc, Corp, Ltd, GmbH, Labs, Protocol
     - Capitalized names with company context (founded, raised, announced)
     - Domain names in URLs

  3. Scan for project patterns:
     - Protocol/platform/product + capitalized name
     - Names with "network", "protocol", "chain", "token"
     - GitHub organization names

  4. Scan for event patterns:
     - Conference/summit/meetup + name + date
     - Location + date patterns

  5. For each entity:
     - Extract surrounding context (1-2 sentences)
     - Assign confidence score (0-1)
     - Check for duplicates against existing contacts
     - Suggest industries from context

output:
  entities:
    - name: "Protocol Labs"
      type: company
      confidence: 0.95
      context: "Protocol Labs, founded by Juan Benet, created IPFS and Filecoin"
      suggested_industries: [storage, web3]
      existing_match: null  # or path to existing contact

    - name: "Juan Benet"
      type: person
      confidence: 0.85
      context: "Juan Benet, founder of Protocol Labs"
      suggested_organization: "[[Protocol Labs]]"
      existing_match: "1-datafund/contacts/people/Juan Benet.md"

  summary:
    total_extracted: 15
    high_confidence: 8    # > 0.8
    existing_matches: 3
    new_entities: 12
    created_drafts: 0     # If auto_create enabled
```

**Boundaries:**
- **CAN:** Read research files, create draft contacts, update industry registry
- **CANNOT:** Modify existing contacts, delete entities
- **MUST:** Flag all entities for human review, include confidence scores

### 15. Contact Maintainer Agent

**Agent:** `crm-contact-maintainer`

Maintains contact database quality: deduplication, merging, validation, industry registry.

```yaml
trigger:
  - Weekly via nightshift
  - Manual: /crm maintenance

input:
  scope: all | [space-name]
  actions: [dedupe, validate, merge, registry]

process:
  1. Duplicate detection:
     - Fuzzy name matching (Levenshtein distance < 3)
     - Same organization + similar role
     - Same email/linkedin across contacts
     - Flag for review, don't auto-merge

  2. Merge candidates:
     - Identify pairs with high similarity
     - Calculate field precedence (newer wins, non-empty wins)
     - Generate merge preview

  3. Validation:
     - Check wiki-links resolve to existing pages
     - Verify required fields present
     - Flag incomplete/stale contacts

  4. Industry registry maintenance:
     - Scan all contacts for industry tags
     - Normalize similar tags
     - Update counts in registry
     - Flag potential merges (Levenshtein similarity)

output:
  duplicates:
    - pair: ["John Smith", "Jon Smith"]
      similarity: 0.92
      same_org: true
      recommendation: merge
      preview:
        keep: "John Smith"
        merge_fields: [channels.phone]

  validation:
    broken_links: 3
    incomplete: 5
    stale: 12  # No interaction > 180 days

  industry_registry:
    new_industries: 2
    potential_merges:
      - ["rwa", "real_world_assets"]
      - ["ai", "ai_ml"]
    updated_counts: true

  actions_taken:
    - "Updated industry registry with 2 new entries"
    - "Flagged 3 duplicate pairs for review"
```

**Boundaries:**
- **CAN:** Read all contacts, update industry registry, create merge previews
- **CANNOT:** Auto-merge without user approval, delete contacts
- **MUST:** Always require human confirmation for merges, preserve history

### 16. Industry Landscape

Strategic view of market positioning and network intelligence.

#### Structure

```
[space]/contacts/landscape/
├── _overview.md       # Industry landscape summary
├── competitors.md     # Competitive analysis matrix
└── ecosystem.md       # Partner/vendor ecosystem
```

#### Overview Template

```markdown
# Industry Landscape

*Auto-generated: {{DATE}}*

## Industries

| Industry | Contacts | Companies | Projects |
|----------|----------|-----------|----------|
| data_infrastructure | 23 | 8 | 5 |
| rwa | 12 | 4 | 3 |
| defi | 45 | 15 | 12 |

## Relationship Distribution

| Status | Count |
|--------|-------|
| Active partners | 8 |
| Customers | 3 |
| Competitors | 12 |
| Targets | 25 |

## Network Graph

<!-- Render with datacortex visualization -->
```

#### Supported Queries

The landscape enables strategic queries:

- "Who are our competitors in [industry]?"
- "Who should we connect with at [event]?"
- "What's our position vs [competitor]?"
- "Who introduced us to [company]?"
- "What companies in [industry] are we not tracking?"

#### Landscape Compiler

```python
def compile_landscape(spaces: List[str]) -> LandscapeData:
    """Aggregate contacts into landscape view."""
    contacts = load_all_contacts(spaces)

    return {
        'industries': aggregate_by_industry(contacts),
        'relationships': aggregate_by_relationship(contacts),
        'competitors': filter_competitors(contacts),
        'ecosystem': build_network_graph(contacts),
        'coverage_gaps': identify_gaps(contacts, industry_targets)
    }
```

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

### Phase 1: Core Structure (Complete)
- [x] Create module scaffold
- [x] Implement contact note templates (person, company)
- [x] Create `contacts/` folder structure

### Phase 2: Built-in Adapters (Complete)
- [x] Implement journal adapter
- [x] Implement calendar adapter
- [x] Create interaction extraction logic

### Phase 3: Commands & Integration (Complete)
- [x] Implement `/crm` command
- [x] Add CRM section to `/today`
- [x] Add CRM section to `/gtd-weekly-review`

### Phase 4: Cross-Space Index (Complete)
- [x] Implement index compiler
- [x] Implement relationship scorer
- [x] Create privacy staging workflow

### Phase 5: Extended Entity Types
- [ ] Create project contact template
- [ ] Create event contact template
- [ ] Update person/company templates with new taxonomy
- [ ] Add projects/ and events/ to folder structure

### Phase 6: Entity Extractor Agent
- [ ] Create agent specification
- [ ] Implement entity extraction patterns
- [ ] Add research processor hook
- [ ] Test with literature notes

### Phase 7: Contact Maintainer Agent
- [ ] Create agent specification
- [ ] Implement duplicate detection (Levenshtein)
- [ ] Implement merge workflow
- [ ] Add nightshift hook for weekly maintenance

### Phase 8: Industry Registry
- [ ] Create industry registry schema
- [ ] Implement registration/normalization
- [ ] Add alias detection
- [ ] Integrate with contact creation

### Phase 9: Industry Landscape
- [ ] Create landscape templates
- [ ] Implement landscape compiler
- [ ] Add strategic query support
- [ ] Datacortex visualization integration (optional)

### Phase 10: External Adapters
- [ ] Document adapter interface for other modules
- [ ] Coordinate with meeting-notes module
- [ ] Coordinate with mail module

## Open Questions

1. ~~**Duplicate detection:** How to handle same person appearing in multiple spaces with different names?~~
   → Resolved: Contact maintainer agent with Levenshtein similarity detection
2. ~~**Merge contacts:** Workflow for merging duplicate contacts?~~
   → Resolved: Contact maintainer generates merge previews, requires human approval
3. **Calendar attendee resolution:** How to map email addresses to contact names reliably?
4. **Industry hierarchy:** Should industries support parent/child relationships (e.g., finance/rwa)?
5. **Cross-space duplicates:** How to handle same entity in personal vs team space?

## References

- [DIP-0002: Layered Context Pattern](./DIP-0002-layered-context-pattern.md) - Cross-space index compilation
- [DIP-0009: GTD Specification](./DIP-0009-gtd-specification.md) - Task integration
- [DIP-0010: External Sync Architecture](./DIP-0010-external-sync-architecture.md) - Adapter pattern inspiration
