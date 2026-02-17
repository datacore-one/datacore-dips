# DIP-0021: Search & Research Architecture

| Field | Value |
|-------|-------|
| **DIP** | 0021 |
| **Title** | Search & Research Architecture |
| **Author** | Gregor, Claude (AI-assisted) |
| **Type** | Core |
| **Status** | Draft |
| **Created** | 2026-02-18 |
| **Updated** | 2026-02-18 |
| **Tags** | `search`, `research`, `agents`, `ingest`, `mcp`, `architecture` |
| **Affects** | `/search`, `/research`, `/ingest`, all research agents, datacortex module, research module |
| **Specs** | DIP-0004, DIP-0015, DIP-0016 |
| **Agents** | `knowledge-extractor`, `research-orchestrator`, `ingest-orchestrator`, `research-synthesizer`, `podcast-creator` |

## Summary

Unifies search, research, and ingest into a coherent three-layer architecture with clear boundaries, consolidated agents, and external tool integrations (Perplexity, Exa, Jina, Google Scholar, Gemini). Reduces 9 fragmented agents to 5 with consistent naming, eliminates duplicate content-to-knowledge processing logic, and introduces a pluggable source registry for extensible data source integration. Defines two standard research workflows: daily news monitoring and topical deep research.

## Motivation

### Current Problems

**1. Agent Fragmentation**

Nine agents handle overlapping concerns with inconsistent naming:

| Agent | Problem |
|-------|---------|
| `gtd-research-processor` | "gtd" prefix misleading; not GTD-specific |
| `research-link-processor` | Overlaps with above; both process URLs |
| `daily-research-processor` | Orchestrator named as processor |
| `research-post-processor` | Housekeeping step elevated to agent |
| `action-item-extractor` | Thin extraction step; unclear scope |
| `nlm-podcast-creator` | Implementation detail (NotebookLM) in name |
| `conversation-processor` | Same core operation as gtd-research-processor |
| `ingest-processor` | Same core operation from files instead of URLs |
| `ingest-coordinator` | Only agent with correct orchestrator naming |

**2. Duplicate Core Operation**

Three agents independently implement "content to knowledge":
- `gtd-research-processor`: URL → literature note + zettels
- `ingest-processor`: file → literature note + zettels
- `conversation-processor`: conversation export → zettels + topic notes

Same output pattern, different input adapters, no shared logic.

**3. No External Discovery**

The current system only processes URLs you already have. There is no capability to discover sources — no semantic web search, no academic paper search, no AI-synthesized research. The `/search` command only queries local knowledge (Datacortex).

**4. No Search/Research Distinction**

Quick lookups and deep research use the same entry point or ad-hoc workflows. There's no clear UX for "I want a quick answer" vs. "I want to deeply research this topic."

### What This Enables

- **Enriched search**: Local knowledge + web intelligence in one query
- **AI-powered discovery**: Find sources by meaning, not just keywords
- **Deep research pipelines**: Multi-step, multi-source research with synthesis
- **Unified knowledge processing**: Coordinator agent with specialized sub-agents
- **Clean agent taxonomy**: 5 agents with clear roles instead of 9 with overlap
- **Pluggable sources**: Add new data sources via YAML registry, no code changes
- **Standard workflows**: Daily news monitoring + topical deep research

## Agent Context

This section helps agents understand when and how to apply this DIP.

### When to Reference This DIP

**Always reference when:**
- Processing search queries (`/search`)
- Running research pipelines (`/research`, `:AI:research:`)
- Ingesting content (`/ingest`)
- Adding or configuring external data sources
- Creating or modifying research agents
- Working with the source registry (`sources.yaml`)

**Key decisions this DIP informs:**
- Which agents handle content-to-knowledge processing
- How external sources are queried (source registry)
- Research output format (summary + knowledge + action items)
- Hook firing order during search/research/ingest pipelines

### Quick Reference

| Question | Answer |
|----------|--------|
| Search command? | `/search <query>` (Datacortex + Perplexity) |
| Research command? | `/research <topic\|url>` |
| Content-to-knowledge agent? | `knowledge-extractor` (coordinator) |
| Research orchestrator? | `research-orchestrator` |
| Source registry? | `.datacore/registry/sources.yaml` |
| Research output location? | `content/reports/`, `3-knowledge/literature/`, `3-knowledge/zettel/` |
| Overnight research queue? | `org/research_learning.org` |

### Related Agents

| Agent | Relationship |
|-------|-------------|
| `ai-task-executor` | Routes `:AI:research:` tags to `research-orchestrator` |
| `tag-suggester` | Called by `knowledge-extractor` for tag generation |
| `research-orchestrator` | Spawns `knowledge-extractor`, `research-synthesizer`, `podcast-creator` |
| `knowledge-extractor` | Spawns sub-agents: `url-fetcher`, `pdf-extractor`, `conversation-parser`, `file-reader` |

### Integration Points

- **DIP-0004** — Datacortex for semantic search + embeddings
- **DIP-0009** — GTD task routing (`:AI:research:` tag)
- **DIP-0011** — Nightshift for overnight research execution
- **DIP-0015** — Ingest workflow, six-phase methodology
- **DIP-0016** — Agent registry, hook profiles

## Specification

### 1. Three-Layer Architecture

```
SEARCH (synchronous, quick — seconds)
│   "What do I know?" + "What does the web say?"
│
RESEARCH (asynchronous, deep — minutes to overnight)
│   "Deeply explore this topic across all sources"
│
INGEST (content you already have)
    "Process this file/URL into knowledge"
```

**Key relationship**: Research uses Search for discovery. Research uses Ingest for processing. Ingest is the atomic content-to-knowledge operation.

```
┌─────────────────────────────────────────────────────┐
│                    RESEARCH                          │
│  discover ──→ gather ──→ process ──→ synthesize      │
│     │            │          │                        │
│  [SEARCH]   [fetch/read] [INGEST]    [reports,      │
│  layer       Jina Reader  layer      podcasts,      │
│                                      Gemini]        │
└─────────────────────────────────────────────────────┘
```

### 2. Search Layer

#### 2.1 Command: `/search <query>`

Upgraded from Datacortex-only to multi-source:

```
/search <query>
  ├── Datacortex        → internal knowledge (existing)
  ├── Perplexity        → AI-synthesized web results (new)
  └── Synthesize        → grounded answer combining both
```

**Behavior:**
1. Run Datacortex and Perplexity queries in parallel
2. Synthesize a combined answer:
   - Lead with internal knowledge when available ("You have notes on this...")
   - Enrich with web intelligence ("Recent developments include...")
   - Flag contradictions between internal notes and current web info
3. List sources from both (internal marked with `[local]` prefix)
4. Offer actions: Save as zettel, Go deeper (`/research`), Done

**Latency contract**: `/search` must respond within 5 seconds. Only sources with `max_latency_ms` under 5000 are eligible for the search layer. Slow sources are skipped with a note ("Perplexity timed out; showing local results only").

**When Perplexity is unavailable** (no API key, rate limited, timed out): falls back to Datacortex-only (current behavior). Search must never fail because an external service is down.

#### 2.2 MCP Server: Perplexity

| Setting | Value |
|---------|-------|
| Server | `perplexity-mcp` (community or custom) |
| API Key | `.datacore/env/PERPLEXITY_API_KEY` |
| Models | `sonar` (quick search), `sonar-pro` (deeper) |
| Tools exposed | `perplexity_search`, `perplexity_research` |

### 3. Research Layer

#### 3.1 Research Domains

Research is used broadly — from medical literature reviews to crypto market analysis to competitive intelligence. The system must support diverse research types without hardcoding domain assumptions.

**Example research domains and their source ecosystems:**

| Domain | Example queries | Specialized sources |
|--------|----------------|-------------------|
| **Medical/longevity** | "Rapamycin dosing protocols", "GLP-1 agonists and aging" | PubMed, ClinicalTrials.gov, Cochrane, Google Scholar |
| **Crypto markets** | "SOL sentiment analysis", "DeFi regulatory outlook" | CoinGlass, DeFiLlama, Dune Analytics, crypto Twitter/X, on-chain data |
| **Product/competitive** | "Data tokenization market size", "RWA competitors" | Crunchbase, PitchBook, Product Hunt, G2, SEC/EDGAR filings |
| **Academic** | "Zero-knowledge proofs for healthcare", "FHE benchmarks" | arXiv, Semantic Scholar, Google Scholar, SSRN |
| **Legal/regulatory** | "MiCA compliance requirements", "VARA licensing" | EUR-Lex, regulatory agency sites, legal databases |
| **Technology** | "Swarm storage benchmarks", "ERC-3643 implementations" | GitHub, Stack Overflow, technical blogs, documentation |

The research orchestrator does **not** hardcode which sources to query for which domain. Instead, it uses a **pluggable source registry** (see Section 3.6).

#### 3.2 Research Workflows

Two standard workflows cover the most common research patterns:

##### Workflow 1: Daily News & Monitoring

Runs overnight via nightshift. Processes URLs accumulated during the day from Readwise, bookmarks, and manual saves to `research_learning.org`.

```
research_learning.org (accumulated URLs)
  → research-orchestrator (nightshift mode)
    → Group by topic (daily news batch + topical deep-dives)
    → knowledge-extractor (per URL, parallel)
    → research-synthesizer (per topic group)
    → podcast-creator (daily news + topical podcasts)
    → Post-process: mark DONE, update journal, extract action items
  → Morning briefing (content/reports/research-briefing-YYYY-MM-DD.md)
```

**Constraints:**
- Max 20 URLs per night (quality over quantity)
- Minimum 2 podcasts: 1 daily news roundup + 1 topical deep-dive
- Must complete by 6am for morning briefing
- Landscape YAML updated with new entities/companies

**Proven pattern**: The Readwise research workflow (Feb 2026) processed 1,797 accumulated clippings into strategic insights across 5 projects, generating footnoted gap analyses and competitive landscape reports. This validated the accumulate → batch process → synthesize model.

##### Workflow 2: Topical Deep Research

Interactive or on-demand. User initiates with `/research <topic>`.

```
User: /research rapamycin dosing protocols for longevity
  → research-orchestrator (interactive mode)
    → Phase 1: Discover (parallel fan-out to all configured sources)
    → Present sources, user selects which to process
    → Phase 2-6: Gather, Process, Synthesize, Audio, Store
  → Research output presented inline
```

Can also be triggered via `:AI:research:` tag for overnight processing of complex topics.

#### 3.3 Command: `/research <topic|url|urls>`

New command. Entry point for deep, multi-step research.

**Usage:**
```
/research rapamycin dosing protocols for longevity
/research SOL market sentiment and whale accumulation
/research --topic "data tokenization competitors" --depth deep
/research https://example.com/paper.pdf
```

**Parameters:**
- `topic` — free-text research query (triggers discovery phase)
- `url(s)` — specific URLs to process (skips discovery, goes straight to gather+process)
- `--depth` — `quick` (Perplexity only), `standard` (default), `deep` (all sources + Gemini synthesis)
- `--podcast` — generate audio overview when done
- `--space` — target space for outputs (default: 0-personal)

**Phases:**

| Phase | What happens | Tools (varies by available sources) |
|-------|-------------|-------------------------------------|
| 1. Discover | Find relevant sources across configured providers | Datacortex + any configured source providers |
| 2. Gather | Extract clean content from discovered sources | Jina Reader → WebFetch → archive.org (fallback chain) |
| 3. Process | Create knowledge artifacts per source | `knowledge-extractor` (coordinator with sub-agents) |
| 4. Synthesize | Combine into research report | `research-synthesizer`, optionally Gemini Pro |
| 5. Audio (optional) | Generate audio overview | `podcast-creator` |
| 6. Store | Persist all artifacts | Existing pipeline (zettels, literature, tasks, landscape) |

**Interactive mode**: After discovery (phase 1), present found sources with deduplication report and let user select which to process. For overnight/nightshift mode, process all above relevance threshold.

#### 3.4 Agent: `research-orchestrator`

Replaces: `daily-research-processor`, `research-post-processor`, `action-item-extractor`

**Role**: Coordinates the full research pipeline. Handles both interactive (`/research`) and overnight (nightshift `:AI:research:`) execution.

**Input:**
- Topic string (triggers discovery), or
- URL(s) (skips discovery), or
- Org-mode task with `:AI:research:` tag (nightshift)

**Responsibilities:**
- Read source registry to determine which providers to query
- Discovery phase: fan out to all configured sources with `layers` containing `research`, in parallel
- Source ranking: merge results, apply deduplication (Section 3.7), rank by relevance
- Source selection: present to user (interactive) or filter by `relevance_threshold` (nightshift)
- Spawn `knowledge-extractor` per selected source (parallel, max concurrency TBD)
- Spawn `research-synthesizer` for multi-source synthesis
- Spawn `podcast-creator` when `--podcast` flag or `auto_generate` setting
- Post-processing (absorbed steps, no longer standalone agents):
  - Extract action items from synthesis report → route to org
  - Mark source org items DONE, set `:OUTPUT:` and `:ZETTELS:` properties
  - Update journal with research summary
  - Update industry landscape YAML with new entities
- Morning briefing generation (nightshift mode only)

**Error handling:**
- If a source provider times out or fails: skip it, note in output ("Exa unavailable, using remaining sources")
- If a sub-agent (`knowledge-extractor`) fails on one URL: log error, continue with remaining URLs
- If all sources fail: return error with suggestion to retry or use `--depth quick` (Perplexity only)

**Output:** Delegates to research output format (Section 3.5).

**Model:** sonnet

#### 3.5 Research Output

Every research run produces a consistent output structure:

**1. Summary** (always, inline in conversation or morning briefing):
```markdown
## Research: [Topic]

### Key Findings
- Finding 1 with [source citation]
- Finding 2 with [source citation]
- ...

### Knowledge Created
- Literature notes: [list with paths]
- Zettels: [list with paths]
- [N] sources processed, [M] zettels created

### Suggested Next Actions
- [ ] [Specific actionable item derived from research]
- [ ] [Follow-up research suggestion if gaps found]
- [ ] [Decision point requiring human judgment]
```

**2. Detailed report** (for standard/deep depth):
- `content/reports/YYYY-MM-DD-[topic]-report.md`
- Podcast-ready format with narrative transitions

**3. Knowledge artifacts** (always):
- Literature notes in `[space]/3-knowledge/literature/`
- Atomic zettels in `[space]/3-knowledge/zettel/`
- Tags applied, Datacortex embeddings computed

**4. GTD integration** (always):
- Action items routed to `org/inbox.org` or `org/next_actions.org`
- Research item marked DONE in source org file

#### 3.6 Source Registry (Pluggable Data Sources)

External sources are registered in a YAML registry, not hardcoded in agents. New sources can be added by installing an MCP server and adding a registry entry — no agent changes required.

**Registry file**: `.datacore/registry/sources.yaml`

```yaml
# Source Registry — pluggable data sources for search and research
# Each source is an MCP server tool or API that provides search/discovery

sources:
  # === INTERNAL ===
  datacortex:
    type: internal
    description: "Semantic search over local Datacore knowledge base"
    tool: datacortex search
    layers: [search, research]
    content_type: documents
    always_available: true

  # === GENERAL WEB ===
  perplexity:
    type: mcp
    description: "AI-synthesized web search with citations"
    tool: perplexity_search
    layers: [search, research]
    api_key: PERPLEXITY_API_KEY
    max_latency_ms: 4000
    content_type: documents
    models:
      quick: sonar
      deep: sonar-pro
    good_for: [general, technology, news, market-analysis]

  exa:
    type: mcp
    description: "Semantic web discovery — finds content by meaning"
    tool: exa_search
    layers: [research]
    api_key: EXA_API_KEY
    content_type: documents
    good_for: [general, technology, companies, papers, blogs]

  # === ACADEMIC ===
  google-scholar:
    type: mcp
    description: "Academic papers, citation graphs, peer review"
    tool: scholar_search
    layers: [research]
    api_key: SERPAPI_KEY
    content_type: documents
    authority: high  # Peer-reviewed sources
    good_for: [medical, academic, scientific, longevity]

  # === CONTENT EXTRACTION ===
  jina-reader:
    type: mcp
    description: "Clean content extraction from any URL or PDF"
    tool: jina_read
    layers: [gather]
    api_key: JINA_API_KEY
    content_type: documents

  # === SYNTHESIS ===
  gemini:
    type: mcp
    description: "Large-context synthesis (2M tokens)"
    tool: gemini_generate
    layers: [synthesize]
    api_key: GEMINI_API_KEY
    content_type: documents
    opt_in: true  # Sends content to Google; requires explicit enable

  # === EXAMPLES OF FUTURE SOURCES ===
  # Uncomment and configure as needed:
  #
  # pubmed:
  #   type: mcp
  #   description: "Biomedical literature database"
  #   tool: pubmed_search
  #   layers: [research]
  #   api_key: NCBI_API_KEY
  #   content_type: documents
  #   authority: high
  #   good_for: [medical, longevity, clinical-trials]
  #
  # crunchbase:
  #   type: mcp
  #   description: "Company and startup database"
  #   tool: crunchbase_search
  #   layers: [research]
  #   api_key: CRUNCHBASE_API_KEY
  #   content_type: structured_data
  #   good_for: [market-analysis, competitors, fundraising]
  #
  # defillama:
  #   type: mcp
  #   description: "DeFi protocol TVL, yields, analytics"
  #   tool: defillama_query
  #   layers: [research]
  #   content_type: structured_data
  #   good_for: [crypto, defi, market-analysis]
  #   note: "Free API, no key required"
  #
  # coinglass:
  #   type: mcp
  #   description: "Crypto derivatives data, funding rates, OI"
  #   tool: coinglass_query
  #   layers: [research]
  #   api_key: COINGLASS_API_KEY
  #   content_type: structured_data
  #   good_for: [crypto, trading, derivatives]
  #
  # semantic-scholar:
  #   type: mcp
  #   description: "AI-powered academic search with citation context"
  #   tool: s2_search
  #   layers: [research]
  #   api_key: S2_API_KEY
  #   content_type: documents
  #   authority: high
  #   good_for: [academic, ai, computer-science]
```

**Source registry fields:**

| Field | Required | Purpose |
|-------|----------|---------|
| `type` | Yes | `internal`, `mcp`, or `api` |
| `description` | Yes | Human-readable description of the source |
| `tool` | Yes | MCP tool name or command to invoke |
| `layers` | Yes | Which phases use this source: `search`, `research`, `gather`, `synthesize` |
| `api_key` | No | Environment variable name in `.datacore/env/` |
| `content_type` | Yes | `documents` (articles, papers) or `structured_data` (metrics, APIs) |
| `max_latency_ms` | No | Max acceptable response time; sources exceeding this are skipped for `/search` |
| `authority` | No | `high` (peer-reviewed, institutional), `medium` (established media), `low` (blogs, social) |
| `good_for` | No | Advisory domain tags for source prioritization |
| `models` | No | Named model variants (e.g., `quick: sonar`, `deep: sonar-pro`) |
| `opt_in` | No | If `true`, requires explicit enable in settings (privacy-sensitive sources) |
| `always_available` | No | If `true`, never skipped (internal sources) |
| `enabled` | No | Set to `false` to disable a source without removing it |
| `note` | No | Advisory annotation for humans |

Note: The `layers` field refers to **phases** of the search/research pipeline, not the three architectural layers. A source participates in whichever phases it is listed under.

**How the orchestrator uses the registry:**

1. Load `sources.yaml` at startup
2. Filter to sources that have valid API keys configured (graceful degradation)
3. For the **search layer**: query all sources with `layers` containing `search` and `max_latency_ms` within budget
4. For the **research layer**: query all sources with `layers` containing `research`
5. The `good_for` field is advisory — agents can use it for source prioritization but all available sources are queried by default
6. `content_type: structured_data` sources return metrics/data that feeds into reports rather than literature notes

**Adding a new source:**
1. Install or build the MCP server
2. Add API key to `.datacore/env/`
3. Add entry to `sources.yaml`
4. Source is immediately available to `/search` and `/research` — no agent changes needed

**Note on `type: api` sources**: Sources with `type: api` (DeFiLlama, CoinGlass) require a lightweight MCP wrapper that translates the API into MCP tools. These wrappers are simple HTTP-to-MCP bridges and can be auto-generated from OpenAPI specs. Until a wrapper exists, the source remains commented out.

#### 3.7 Deduplication and Convergence

When multiple sources return the same content, the orchestrator deduplicates before processing:

**Deduplication strategy:**
1. **URL normalization** — strip tracking params, normalize domains (www vs. non-www)
2. **Title fuzzy match** — Levenshtein distance < 0.2 on normalized titles
3. **Content hash** — for gathered content, hash first 500 chars to detect mirrors

**Convergence as signal**: When multiple independent sources surface the same finding, this is a valuable signal — not just noise to filter. The research-synthesizer should:
- Track convergence count per finding ("3 out of 5 sources mention X")
- Surface high-convergence findings prominently in the synthesis
- Distinguish between genuine convergence (independent sources reaching same conclusion) and echo-chamber effects (same source republished across sites)
- Flag when internal knowledge (Datacortex) contradicts web convergence — this is especially interesting

**In the research output:**
```markdown
### High Convergence Findings
- [Finding X] — confirmed by 4 independent sources (Scholar, Exa, Perplexity)
- [Finding Y] — contradicts your existing zettel [link]; worth re-evaluating
```

#### 3.8 MCP Servers: Initial Set

The initial deployment includes these MCP servers:

| Server | Purpose | API Key | Tools Exposed |
|--------|---------|---------|---------------|
| `perplexity-mcp` | AI web search | `PERPLEXITY_API_KEY` | `perplexity_search`, `perplexity_research` |
| `exa-mcp` | Semantic discovery | `EXA_API_KEY` | `exa_search`, `exa_find_similar`, `exa_contents` |
| `google-scholar-mcp` | Academic papers | `SERPAPI_KEY` | `scholar_search`, `scholar_cite` |
| `jina-mcp` | Content extraction | `JINA_API_KEY` | `jina_read`, `jina_embed`, `jina_rerank` |
| `gemini-mcp` | Large-context synthesis | `GEMINI_API_KEY` | `gemini_generate` (2M context) |

**Graceful degradation**: Each external tool is optional. Research works with whatever is configured. Minimum viable: Perplexity only. Full stack: all services.

### 4. Ingest Layer (Unified Knowledge Processing)

#### 4.1 Agent: `knowledge-extractor`

Replaces: `gtd-research-processor`, `ingest-processor`, `conversation-processor`

**Role**: Coordinator agent that routes content to specialized sub-agents via the Task tool. Takes any content type and produces structured knowledge artifacts through a team of specialists.

**Architecture — Coordinator with Sub-Agents:**

```
knowledge-extractor (coordinator)
  │
  ├── Detect input type
  ├── Spawn appropriate sub-agent(s) via Task tool:
  │   ├── url-fetcher        → fetch and structure web content
  │   ├── pdf-extractor      → extract text/structure from PDFs
  │   ├── conversation-parser → parse dialogue, cluster topics, extract insights
  │   └── file-reader        → read and classify local files
  │
  ├── Receive extracted content from sub-agent
  ├── Check Datacortex for existing related notes (prevent duplicates)
  ├── Generate knowledge artifacts:
  │   ├── Literature note (L1 summary + L2 key insights)
  │   ├── Atomic zettels (when novel concepts found)
  │   └── Action items (when actionable insights found)
  ├── Call tag-suggester for tagging
  └── Return structured JSON result
```

**Why a coordinator pattern?** Each content type requires genuinely different processing logic:
- **URL fetching** needs retry logic, archive.org fallback, paywall detection
- **PDF extraction** needs structure preservation, table handling, OCR awareness
- **Conversation parsing** needs speaker attribution, topic clustering, multi-turn reasoning extraction — this is fundamentally different from document processing, not just a format adapter
- **File reading** needs MIME detection, companion file handling (per DIP-0015)

The coordinator provides unified output format and shared logic (dedup checking, zettel creation, tagging) while sub-agents handle input-specific complexity. Sub-agents can use fast models (haiku) for extraction; the coordinator uses a capable model for synthesis and zettel creation.

**Input routing:**

| Type | Detection | Sub-agent | Model |
|------|-----------|-----------|-------|
| URL | Starts with `http(s)://` | `url-fetcher` | haiku |
| PDF | `.pdf` extension or URL ending in `.pdf` | `pdf-extractor` | haiku |
| Conversation export | JSON with message array structure | `conversation-parser` | sonnet |
| Local file | File path, any other format | `file-reader` | haiku |
| Raw text | Passed directly (no path/URL) | None (coordinator handles directly) | — |

**Gather fallback chain** (for URLs, used by `url-fetcher`):
1. Jina Reader (if configured) — best for complex pages and PDFs
2. WebFetch — built-in, always available
3. archive.org — last resort for inaccessible pages

**Output** (consistent across all input types):

| Artifact | Location | Condition |
|----------|----------|-----------|
| Literature note | `[space]/3-knowledge/literature/` | Always (L1 summary + L2 key insights) |
| Atomic zettels | `[space]/3-knowledge/zettel/` | When novel, reusable concepts found |
| Action items | Returned in JSON (caller routes to org) | When actionable insights found |
| Tags | Via `tag-suggester` | Always |
| Datacortex embedding | Via `embed-outputs` hook | Always (post-hook) |

**Return format** (JSON):
```json
{
  "status": "success",
  "input_type": "url|file|pdf|conversation|text",
  "literature_note": "path/to/note.md",
  "zettels_created": ["path/to/zettel1.md", "path/to/zettel2.md"],
  "action_items": ["Review dosing protocol", "Check clinical trial NCT..."],
  "summary": "Brief summary of what was extracted",
  "relevance": {"health-longevity": 0.9, "trading": 0.1},
  "source_authority": "high|medium|low"
}
```

**Key behaviors preserved from existing agents:**
- Progressive summarization (L1/L2) from `gtd-research-processor`
- Zettel atomicity criteria (atomic, reusable, novel) from `gtd-research-processor`
- Datacortex search for existing related notes (prevent duplicates)
- Relevance assessment across work areas
- Fallback to archive.org for failed URL fetches
- Six-phase methodology from `ingest-processor` (for files)
- Topic clustering and dialogue-specific extraction from `conversation-processor`

#### 4.2 Agent: `ingest-orchestrator`

Rename of: `ingest-coordinator`

Unchanged in function. Routes to `knowledge-extractor` instead of `ingest-processor`.

#### 4.3 Command: `/ingest`

Unchanged. Calls `ingest-orchestrator` which now uses `knowledge-extractor`.

### 5. Synthesis Agents

#### 5.1 Agent: `research-synthesizer`

Replaces: `research-link-processor`

**Role**: Takes multiple `knowledge-extractor` outputs and produces synthesized reports with convergence analysis.

**Outputs:**
- Summary: `content/summaries/YYYY-MM-DD-[topic]-summary.md`
- Detailed report: `content/reports/YYYY-MM-DD-[topic]-report.md`
- Optionally uses Gemini Pro for large-context synthesis (20+ sources)

**Capabilities:**
- Podcast-ready report format (narrative transitions, hooks)
- Quality/credibility scoring using source `authority` metadata
- Convergence analysis across sources (see Section 3.7)
- Redundancy detection and deduplication
- GTD action item generation
- Structured data integration (metrics from API sources presented as data tables, not prose)

#### 5.2 Agent: `podcast-creator`

Replaces: `nlm-podcast-creator`

**Role**: Generates audio overviews from curated sources via NotebookLM.

Unchanged in function. Name drops implementation detail prefix. If podcast backend changes (e.g., to a different service), the agent name remains stable.

### 6. Naming Convention

All agents follow `[role]-[scope]` pattern:

| Pattern | Examples |
|---------|----------|
| `*-extractor` | Pulls structured data from content |
| `*-orchestrator` | Coordinates multi-step pipelines |
| `*-synthesizer` | Combines multiple inputs into unified output |
| `*-creator` | Produces new content artifacts |

Sub-agents (within knowledge-extractor team) use `[content-type]-[verb]`:
- `url-fetcher`, `pdf-extractor`, `conversation-parser`, `file-reader`

No prefixes for:
- Implementation details (`nlm-`, `gtd-`)
- Input types (`link-`, `url-`, `file-`) at the top-level agent name
- Scheduling context (`daily-`)

### 7. Configuration

#### 7.1 Settings

The source registry (`sources.yaml`) is the single source of truth for which sources are available. Settings only control behavior that isn't source-specific:

```yaml
# settings.yaml / settings.local.yaml
search:
  timeout_ms: 5000            # Max wait for search-layer sources

research:
  podcast:
    auto_generate: true       # Generate podcast for overnight research
  max_sources_per_night: 20   # Preserved from current config
  relevance_threshold: 0.6    # Minimum score for auto-processing in nightshift

ingest:
  content_reader: "jina"      # jina | webfetch (fallback for URL fetching)
```

To disable a specific source, set `enabled: false` in `sources.yaml` rather than duplicating source toggles in settings.

#### 7.2 MCP Server Configuration

```json
// .claude/settings.json (project-level mcpServers)
{
  "mcpServers": {
    "perplexity": {
      "command": "npx",
      "args": ["-y", "perplexity-mcp"],
      "env": { "PERPLEXITY_API_KEY_FILE": ".datacore/env/PERPLEXITY_API_KEY" }
    },
    "exa": {
      "command": "npx",
      "args": ["-y", "exa-mcp-server"],
      "env": { "EXA_API_KEY_FILE": ".datacore/env/EXA_API_KEY" }
    },
    "jina": {
      "command": "npx",
      "args": ["-y", "jina-mcp"],
      "env": { "JINA_API_KEY_FILE": ".datacore/env/JINA_API_KEY" }
    }
  }
}
```

API keys are stored in `.datacore/env/` (gitignored) and referenced by MCP server config.

### 8. Hooks

Each layer defines hooks that fire at key points, enabling extensibility without modifying agents.

#### 8.1 Search Hooks

| Hook | When | Use case |
|------|------|----------|
| `pre_search` | Before any search queries fire | Inject context (e.g., current project focus), modify query |
| `post_search` | After results synthesized, before presenting to user | Log search queries for analytics, cache results |
| `search_save` | When user saves a search result as zettel | Trigger Datacortex embedding, update knowledge graph |

#### 8.2 Research Hooks

| Hook | When | Use case |
|------|------|----------|
| `pre_research` | Before discovery phase starts | Inject research context (active projects, recent research), check budget |
| `post_discover` | After discovery, before gathering | Filter sources, apply custom relevance rules, check dedup against recent research |
| `post_extract` | After each `knowledge-extractor` completes | Embed outputs in Datacortex, trigger CRM entity extraction, update landscape YAML |
| `post_synthesize` | After research-synthesizer produces report | Notify user, update morning briefing, route action items to GTD |
| `research_complete` | After full pipeline finishes | Mark org items DONE, update journal, trigger podcast if configured, cost logging |

#### 8.3 Ingest Hooks

| Hook | When | Use case |
|------|------|----------|
| `pre_ingest` | Before processing starts | Validate file, check for duplicates in Datacortex |
| `post_ingest` | After knowledge-extractor completes | Embed outputs in Datacortex (existing `embed-outputs` hook), clean up source file |
| `ingest_complete` | After full batch finishes | Report summary, update folder indexes |

#### 8.4 Existing Hooks Preserved

The current `research` hook profile (from agents.yaml) is preserved and maps to the new architecture:

| Current Hook | Maps To | Behavior |
|-------------|---------|----------|
| `inject_session_memory` | `pre_research`, `pre_ingest` | Load learning patterns before processing |
| `embed-outputs` | `post_extract`, `post_ingest` | Embed zettels and literature notes into Datacortex |
| `output-exists` | `post_extract` validation | Verify output files were created |
| CRM `research_complete` | `post_extract` | Extract people/companies from research outputs |

### 9. Tag Routing

The `:AI:research:` tag continues to route through `ai-task-executor` but now targets `research-orchestrator` instead of `gtd-research-processor`:

```
:AI:research: → ai-task-executor → research-orchestrator
                                     → knowledge-extractor (per URL)
                                     → research-synthesizer (if batch)
                                     → podcast-creator (if configured)
```

### 10. Agent Summary

**Final agent inventory (5 top-level agents + 4 sub-agents):**

| Agent | Role | Replaces | Model |
|-------|------|----------|-------|
| `knowledge-extractor` | Coordinator: content → knowledge | `gtd-research-processor`, `ingest-processor`, `conversation-processor` | sonnet |
| `research-orchestrator` | Full research pipeline | `daily-research-processor`, `research-post-processor`, `action-item-extractor` | sonnet |
| `ingest-orchestrator` | File/folder ingestion | `ingest-coordinator` (rename) | sonnet |
| `research-synthesizer` | Multi-source synthesis | `research-link-processor` | sonnet |
| `podcast-creator` | Audio overviews | `nlm-podcast-creator` | haiku |

| Sub-agent (within knowledge-extractor) | Role | Model |
|-----------------------------------------|------|-------|
| `url-fetcher` | Fetch and structure web content | haiku |
| `pdf-extractor` | Extract text/structure from PDFs | haiku |
| `conversation-parser` | Parse dialogue, cluster topics | sonnet |
| `file-reader` | Read and classify local files | haiku |

## Rationale

### Why Consolidate?

Three agents doing "content → knowledge" with different input adapters means three places to fix bugs, update output formats, or add capabilities. A coordinator with sub-agents means shared output logic with specialized input handling.

### Why Coordinator + Sub-Agents, Not a Monolith?

A single agent handling URL fetching, PDF extraction, conversation parsing, AND zettel creation would be a god-agent with a massive prompt. The coordinator pattern:
- Keeps each sub-agent focused (small prompt, specific tools)
- Allows fast models (haiku) for extraction, capable models (sonnet) for synthesis
- Sub-agents can be improved independently
- New content types = new sub-agent, no coordinator changes

### Why Not Claude Code Agent Teams?

Agent Teams (experimental) coordinate independent sessions with direct messaging. The knowledge-extractor needs sequential processing (fetch → extract → create zettels), not parallel independent work. The Task tool subagent pattern is production-ready and fits the coordinator model better.

### Why Not Just Add MCP Servers?

Adding external tools without architectural changes would increase fragmentation. A Perplexity search bolted onto the current `/search` without rethinking the research pipeline creates more agents, more naming confusion, more overlap.

### Why Keep Orchestrators Separate?

`research-orchestrator` and `ingest-orchestrator` have fundamentally different workflows. Research has a discovery phase; ingest doesn't. Research produces synthesis; ingest processes individual items. Merging them would create a god-agent.

### Why Not Use Gemini for Everything?

Gemini's 2M context is valuable for large-scale synthesis but adds latency, cost, and an external dependency. It's opt-in for specific use cases (20+ source synthesis), not a replacement for Claude-based processing.

### Alternatives Considered

**1. Keep all agents, just add MCP servers**: Rejected — fragmentation worsens.

**2. Single mega-agent**: Rejected — one agent doing discovery + extraction + synthesis + podcast + housekeeping violates separation of concerns.

**3. Build custom search aggregator instead of MCP servers**: Rejected — MCP servers are the standard pattern for tool integration in Claude Code. Custom aggregators add maintenance burden.

**4. Merge conversation-processor directly**: Considered but conversation parsing is genuinely different from document processing. Kept as specialized sub-agent within the coordinator.

## Backwards Compatibility

### Migration Path

| Phase | Changes | Risk |
|-------|---------|------|
| 1. MCP servers | Add Perplexity, Exa, Jina configs | None — additive |
| 2. knowledge-extractor | Create coordinator + sub-agents, test alongside existing | None — parallel |
| 3. Upgrade /search | Add Perplexity source | Low — falls back gracefully |
| 4. Create /research | New command + research-orchestrator | None — additive |
| 5. Wire orchestrators | Point to new agents, test overnight pipeline | Medium — needs testing |
| 6. Retire old agents | Add aliases, mark deprecated | Low — aliases preserve routing |

### Agent Aliases

During transition, old names route to new agents:

```yaml
# registry/agents.yaml
gtd-research-processor:
  deprecated: true
  alias: knowledge-extractor

ingest-processor:
  deprecated: true
  alias: knowledge-extractor

conversation-processor:
  deprecated: true
  alias: knowledge-extractor
  note: "Routes to conversation-parser sub-agent"

daily-research-processor:
  deprecated: true
  alias: research-orchestrator

research-link-processor:
  deprecated: true
  alias: research-synthesizer

nlm-podcast-creator:
  deprecated: true
  alias: podcast-creator

research-post-processor:
  deprecated: true
  removed: true
  note: "Absorbed into research-orchestrator pipeline"

action-item-extractor:
  deprecated: true
  removed: true
  note: "Absorbed into research-orchestrator pipeline"
```

### DIP-0016 Schema Extension

The alias mechanism introduces new fields to the agent registry schema:

| Field | Purpose |
|-------|---------|
| `deprecated` | `true` if agent is replaced by a newer agent |
| `alias` | Name of the replacement agent |
| `removed` | `true` if agent no longer exists (absorbed into another) |
| `note` | Migration guidance |

These fields should be formally added to DIP-0016's registry schema in a follow-up amendment.

### `:AI:research:` Routing

Unchanged externally. `ai-task-executor` routes to `research-orchestrator` (or via alias from `gtd-research-processor`).

## Security Considerations

### API Keys

All external service API keys stored in `.datacore/env/` (gitignored). MCP servers reference these via environment variables. Keys never appear in agent prompts, logs, or knowledge artifacts.

### Data Sent to External Services

| Service | What's sent | Privacy impact |
|---------|------------|---------------|
| Perplexity | Search queries | Low — queries only, no documents |
| Exa | Search queries | Low — queries only |
| Google Scholar | Search queries | Low — queries only |
| Jina Reader | URLs to extract | Low — public URLs only |
| Gemini | Document content for synthesis | **Medium** — full content sent to Google |

**Gemini opt-in**: Because Gemini synthesis sends full document content to Google, it's disabled by default and requires explicit opt-in via settings.

### Rate Limiting

Each MCP server should implement rate limiting to prevent accidental cost spikes. Recommended: configurable per-minute and per-day limits in source registry.

## Implementation

### Reference Implementation

TBD — branch `dip-0021-search-research`

### Rollout Plan

**Phase 1: Foundation (Week 1)**
- Set up MCP servers (Perplexity first, then Exa, Jina)
- Store API keys in `.datacore/env/`
- Create `sources.yaml` registry
- Verify tools are accessible from Claude Code

**Phase 2: Search Upgrade (Week 2)**
- Upgrade `/search` command to fan out to Datacortex + Perplexity
- Implement latency-based source selection
- Test graceful degradation when Perplexity unavailable

**Phase 3: Knowledge Extractor (Week 3)**
- Create `knowledge-extractor` coordinator agent
- Create sub-agents: `url-fetcher`, `pdf-extractor`, `conversation-parser`, `file-reader`
- Test with URLs, files, PDFs, conversations
- Verify output parity with existing agents

**Phase 4: Research Command (Week 4)**
- Create `/research` command and `research-orchestrator`
- Wire discovery phase (Exa, Scholar, Perplexity)
- Implement deduplication and convergence tracking
- Test interactive and nightshift modes
- Define research output format

**Phase 5: Synthesis & Consolidation (Week 5)**
- Create `research-synthesizer`, rename `podcast-creator`, `ingest-orchestrator`
- Add Gemini integration (opt-in)
- Wire overnight pipeline to new agents (daily news + topical workflows)
- Add aliases for deprecated agent names

**Phase 6: Cleanup (Week 6)**
- Update registry entries (agents.yaml, commands.yaml, sources.yaml)
- Update CLAUDE.md documentation
- Remove deprecated agent files (keep aliases)
- Update DIP-0004, DIP-0009, DIP-0011, DIP-0015, DIP-0016 cross-references

## Open Questions

1. **Google Scholar access**: SerpAPI vs. scholarly (Python library) vs. custom scraping? SerpAPI is cleanest but adds another paid service.

2. **Jina vs. WebFetch**: Is Jina Reader worth the API cost for content extraction, or is WebFetch sufficient for most cases? Jina excels at PDFs and complex pages.

3. **Gemini model selection**: Gemini 2.0 Pro vs. 2.0 Flash for synthesis? Flash is cheaper and faster; Pro is more capable. Could be configurable.

4. **NotebookLM automation**: The `nlm` CLI currently drives NotebookLM. Is this stable enough for production, or should podcast creation have an alternative backend?

5. **research_learning.org**: Should this file continue as the research queue, or should research tasks move to `next_actions.org` with `:AI:research:` tags (single queue)?

6. **Cost monitoring**: With potentially many external APIs, how should cost tracking work? Per-source limits? Monthly budget caps? Dashboard in `/research-status`?

7. **Domain-specific source routing**: Should the orchestrator auto-detect query domain (medical, crypto, competitive) and prioritize relevant sources? Or always fan out to all available sources and let relevance scoring handle it?

8. **Structured data sources**: Sources like CoinGlass and DeFiLlama return metrics/JSON, not documents. Should `knowledge-extractor` have a `data-analyzer` sub-agent, or should structured data bypass knowledge extraction entirely and feed directly into reports?

9. **Source authority weighting**: The `authority` field in source registry enables weighted synthesis. How aggressively should this weight findings? A peer-reviewed paper vs. a blog post might both contain valuable information.

## References

- **DIP-0004**: Knowledge Database (Datacortex) — search infrastructure this builds on
- **DIP-0009**: GTD Specification — task routing and `:AI:` tag system
- **DIP-0011**: Nightshift Module — overnight execution context
- **DIP-0015**: Semantic Organization — ingest workflow this consolidates with
- **DIP-0016**: Agent Registry — naming and registration patterns
- **Agentic Search zettel**: `0-personal/3-knowledge/zettel/agentic-search.md`
- **Index Layer zettel**: `0-personal/3-knowledge/zettel/index-layer-for-search.md`
- **Exa Integration Plan**: `1-datafund/1-tracks/research/Datafund Exa Integration Plan.md`
- **Jina Integration Plan**: `1-datafund/1-tracks/research/Datafund Jina Integration Plan.md`
- **Readwise Research** (Feb 2026): Validated accumulate→batch→synthesize pattern with 1,797 clippings
- [Perplexity API docs](https://docs.perplexity.ai/)
- [Exa API docs](https://docs.exa.ai/)
- [Jina API docs](https://jina.ai/reader/)
- [Google Gemini API](https://ai.google.dev/)
