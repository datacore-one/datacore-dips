# DIP-0016: Agent Registry & Discoverability

| Field | Value |
|-------|-------|
| **DIP** | 0016 |
| **Title** | Agent Registry & Discoverability |
| **Author** | Gregor |
| **Type** | Standards Track |
| **Status** | Draft |
| **Created** | 2025-12-21 |
| **Updated** | 2025-12-21 |
| **Tags** | `agents`, `registry`, `discovery`, `erc-8004` |
| **Affects** | `.datacore/agents/`, `.datacore/registry/`, `tags.yaml` |
| **Specs** | `datacore-specification.md` |
| **Agents** | `ai-task-executor`, `context-maintainer` |

## Summary

This DIP introduces a machine-readable agent registry system that enables dynamic agent discovery, capability advertising, knowledge source linking, performance tracking, and agent-to-agent coordination. The design is forward-compatible with [ERC-8004 Trustless Agents](https://eips.ethereum.org/EIPS/eip-8004), [Google A2A Protocol](https://a2a-protocol.org/latest/specification/), [Virtuals Agent Commerce Protocol](https://whitepaper.virtuals.io), and [Olas Protocol](https://olas.network/), enabling future scenarios where agents have wallets, charge for services, rate each other, and operate across organizational boundaries.

## Agent Context

This section helps agents understand when and how to apply this DIP.

### When to Reference This DIP

**Always reference when:**
- Spawning or routing to another agent
- Adding a new agent to the system
- Querying agent capabilities or availability
- Tracking agent performance or interactions
- Installing modules that provide agents
- Generating external-facing agent metadata (AgentCard, ERC-8004)

**Key decisions this DIP informs:**
- Agent discovery uses registry, NOT hardcoded routing
- Agent context includes pre-fetched knowledge from `reads.required`
- Agent interactions are logged for performance tracking
- New agents must be registered before they can be routed to

### Quick Reference for Agents

| Question | Answer |
|----------|--------|
| How do I find an agent for a task? | Query `agents.yaml` by skill tags or use `datacortex agent find` |
| What knowledge should I read? | Check `reads.required` and `reads.contextual` in registry |
| Which DIPs apply to my task? | Check `references.dips` in your registry entry |
| Can I spawn another agent? | Check `spawns` field - only listed agents can be spawned |
| Where do I log my results? | Check `writes` paths and log to `execution_log` |
| How is my performance tracked? | Via `performance` metrics in registry state |

### Related Agents

| Agent | Uses This DIP For |
|-------|-------------------|
| `ai-task-executor` | Routing tasks to agents via registry lookup |
| `context-maintainer` | Syncing registry with module agents |
| `session-learning` | Recording agent interactions and outcomes |
| All agents | Reading their `reads.required` knowledge sources |

### Integration Points

- **[DIP-0009: GTD](./DIP-0009-gtd-specification.md)** - Task routing and :AI: tag processing
- **[DIP-0014: Tags](./DIP-0014-tag-taxonomy.md)** - Tag-based agent triggers
- **[DIP-0004: Knowledge Database](./DIP-0004-knowledge-database.md)** - Datacortex semantic queries
- **[DIP-0011: Nightshift](./DIP-0011-nightshift-module.md)** - Server-side performance aggregation

## Motivation

### Current Problems

1. **No Dynamic Discovery**: Agents are hardcoded in routing rules. Adding a new agent requires manual updates to `tags.yaml` and `CLAUDE.md`.

2. **Knowledge Sources Not Linked**: Agents don't know which specs, DIPs, or knowledge files are relevant to their tasks. This leads to inconsistent context and missed information.

3. **No Capability Advertisement**: There's no way to query "which agent can do X?" or "what can agent Y do?" without reading individual agent files.

4. **Module Agents Not Auto-Registered**: When a module provides agents, they must be manually registered in the routing system.

5. **No Future-Proofing**: As AI agents evolve toward autonomous economic actors (with wallets, reputation, validation), Datacore has no path to that future.

### Use Cases Enabled

1. **Semantic Agent Discovery**: Query "find an agent that can analyze URLs" returns `gtd-research-processor`.

2. **Automatic Context Gathering**: Agents pre-fetch relevant knowledge via datacortex before executing.

3. **Module Auto-Registration**: Installing a module automatically registers its agents.

4. **External Agent Interop**: Datacore agents can be discovered by external systems using standard protocols.

5. **Future Monetization**: Agents can be registered on-chain with reputation and payment capabilities.

## Specification

### 1. Agent Registry Format

Create `.datacore/registry/agents.yaml` as the single source of truth for agent metadata:

```yaml
# Agent Registry v1.0.0
# Compatible with: ERC-8004, A2A Protocol
version: "1.0.0"
protocol: "datacore-agent-registry/v1"

agents:
  gtd-research-processor:
    # === Identity (ERC-8004 compatible) ===
    name: "GTD Research Processor"
    description: "Analyzes URLs, creates literature notes and zettels with progressive summarization"
    version: "1.0.0"
    source: ".datacore/agents/gtd-research-processor.md"

    # === Capabilities (A2A AgentCard compatible) ===
    skills:
      - id: "url-analysis"
        name: "URL Analysis"
        description: "Fetches and analyzes web content"
        tags: ["research", "web", "analysis"]
        examples:
          - "Analyze this article about data tokenization"
          - "Research the latest on ZK proofs"
        inputModes: ["text/plain", "text/uri-list"]
        outputModes: ["text/markdown"]

      - id: "zettel-creation"
        name: "Zettel Creation"
        description: "Creates atomic knowledge notes from content"
        tags: ["knowledge", "zettel", "pkm"]
        examples:
          - "Create a zettel about this concept"
        inputModes: ["text/plain", "text/markdown"]
        outputModes: ["text/markdown"]

    # === Routing (Datacore-specific) ===
    triggers:
      tags: [":AI:research:", ":AI:research:url:"]
      patterns: ["analyze.*url", "research.*topic"]

    # === Knowledge Sources ===
    reads:
      required:
        - ".datacore/tags.yaml"
        - "DIP-0004-knowledge-database.md"
      contextual:
        - query: "datacortex search '{task_description}' --top 3"
          when: "before_execution"
      infers:
        - pattern: "space knowledge directories based on task category"

    writes:
      - "notes/2-knowledge/zettel/"
      - "notes/2-knowledge/literature/"

    # === References ===
    references:
      dips: ["DIP-0004", "DIP-0014"]
      specs: ["privacy-policy.md"]

    # === Future: ERC-8004 Fields (reserved) ===
    # These fields are reserved for future blockchain registration
    erc8004:
      agentId: null  # Assigned on-chain registration
      wallet: null   # Agent's Ethereum address
      supportedTrust: ["reputation"]  # Trust models supported
      chainRegistrations: []  # Multi-chain registrations

  ai-task-executor:
    name: "AI Task Executor"
    description: "Routes :AI: tagged tasks to specialized agents"
    version: "1.0.0"
    source: ".datacore/agents/ai-task-executor.md"

    skills:
      - id: "task-routing"
        name: "Task Routing"
        description: "Analyzes task tags and routes to appropriate agent"
        tags: ["routing", "orchestration", "gtd"]
        examples:
          - "Process all :AI: tasks in next_actions.org"
        inputModes: ["text/org-mode"]
        outputModes: ["text/markdown", "text/org-mode"]

    triggers:
      tags: [":AI:"]
      patterns: ["execute.*ai.*tasks"]

    reads:
      required:
        - ".datacore/tags.yaml"
        - ".datacore/registry/agents.yaml"  # Self-referential for routing
        - "org/next_actions.org"
      contextual: []

    writes:
      - "notes/journals/"
      - "org/next_actions.org"

    references:
      dips: ["DIP-0009", "DIP-0014", "DIP-0016"]
      specs: []

    # Orchestrator agents can spawn other agents
    spawns:
      - "gtd-research-processor"
      - "gtd-content-writer"
      - "gtd-data-analyzer"
      - "gtd-project-manager"

# === Module Agent Registration ===
# Modules register their agents here via install hooks
module_agents:
  # Example: campaigns module
  # campaigns:
  #   source_module: "datacore-campaigns"
  #   agents:
  #     campaign-planner:
  #       triggers:
  #         tags: [":AI:campaign:", ":AI:campaign:plan:"]
  #       ...
```

### 2. Agent Loader Enhancement

Modify the agent loading process to:

1. **Read Registry First**: Before spawning an agent, read `agents.yaml` for metadata
2. **Inject Required Knowledge**: Automatically read files listed in `reads.required`
3. **Execute Contextual Queries**: Run `reads.contextual` queries and inject results
4. **Validate References**: Ensure referenced DIPs/specs exist

```python
# Pseudocode for enhanced agent loader
def load_agent(agent_id: str, task_context: str) -> AgentContext:
    registry = load_yaml(".datacore/registry/agents.yaml")
    agent_meta = registry["agents"][agent_id]

    context = AgentContext()

    # 1. Load required knowledge sources
    for path in agent_meta["reads"]["required"]:
        context.add_file(resolve_path(path))

    # 2. Load referenced DIPs and specs
    for dip in agent_meta["references"]["dips"]:
        context.add_file(f".datacore/dips/{dip}.md")

    # 3. Execute contextual queries
    for query_spec in agent_meta["reads"]["contextual"]:
        if evaluate_condition(query_spec["when"], task_context):
            query = query_spec["query"].format(task_description=task_context)
            results = execute_query(query)
            context.add_search_results(results)

    # 4. Load agent prompt
    context.add_file(agent_meta["source"])

    return context
```

### 3. Discovery Mechanisms

#### 3.1 Capability Query

Add a discovery command for querying agents by capability:

```bash
# Find agents that can handle a task
datacortex agent find "analyze URL and create notes"

# Output:
# Matching agents (by skill similarity):
# 1. gtd-research-processor (0.92) - URL Analysis, Zettel Creation
# 2. gtd-content-writer (0.45) - Content Generation
```

#### 3.2 Tag-Based Auto-Routing

Enhance `ai-task-executor` to use the registry for routing:

```python
def route_task(task: Task) -> str:
    registry = load_registry()

    # Check tag matches
    for agent_id, meta in registry["agents"].items():
        for trigger_tag in meta["triggers"]["tags"]:
            if trigger_tag in task.tags:
                return agent_id

    # Fallback: semantic match against skill descriptions
    return semantic_match(task.description, registry)
```

#### 3.3 Module Auto-Registration

When a module is installed, its `module.yaml` agents are registered:

```yaml
# In module.yaml
provides:
  agents:
    campaign-planner:
      triggers:
        tags: [":AI:campaign:"]
      skills:
        - id: "campaign-planning"
          name: "Campaign Planning"
          # ...
```

Install hook in `context-maintainer`:

```python
def register_module_agents(module_path: str):
    module_yaml = load_yaml(f"{module_path}/module.yaml")
    registry = load_registry()

    module_name = module_yaml["name"]
    if "agents" in module_yaml.get("provides", {}):
        registry["module_agents"][module_name] = {
            "source_module": module_name,
            "agents": module_yaml["provides"]["agents"]
        }

    save_registry(registry)
```

### 4. ERC-8004 Compatibility Path

The registry format is designed for future on-chain registration:

#### 4.1 Registration File Generation

Generate ERC-8004 compatible registration JSON from registry:

```python
def generate_erc8004_registration(agent_id: str) -> dict:
    meta = load_registry()["agents"][agent_id]

    return {
        "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
        "name": meta["name"],
        "description": meta["description"],
        "endpoints": [
            {
                "name": "datacore-local",
                "endpoint": f"file://.datacore/agents/{agent_id}.md",
                "version": meta["version"],
                "capabilities": {
                    "skills": meta["skills"]
                }
            }
        ],
        "supportedTrust": meta.get("erc8004", {}).get("supportedTrust", ["reputation"])
    }
```

#### 4.2 A2A AgentCard Generation

Generate A2A-compatible AgentCard for external discovery:

```python
def generate_agentcard(agent_id: str) -> dict:
    meta = load_registry()["agents"][agent_id]

    return {
        "protocolVersion": "1.0",
        "name": meta["name"],
        "description": meta["description"],
        "version": meta["version"],
        "capabilities": {
            "streaming": False,
            "pushNotifications": False
        },
        "skills": [
            {
                "id": skill["id"],
                "name": skill["name"],
                "description": skill["description"],
                "tags": skill["tags"],
                "examples": skill.get("examples", []),
                "inputModes": skill.get("inputModes", ["text/plain"]),
                "outputModes": skill.get("outputModes", ["text/markdown"])
            }
            for skill in meta["skills"]
        ],
        "defaultInputModes": ["text/plain", "text/markdown"],
        "defaultOutputModes": ["text/markdown"]
    }
```

### 5. Think-Search-Generate Pattern

Adopt the Generate-on-Graph (GoG) cognitive pattern for agent execution:

#### 5.1 Three-Phase Execution

```markdown
## Agent Execution Pattern (inject into agent prompts)

Execute tasks using the Think-Search-Generate pattern:

### Phase 1: THINK
- Decompose the task into sub-questions
- Identify what knowledge you need
- Decide: Do I need to search, or do I already know?

### Phase 2: SEARCH
For each knowledge gap:
1. **Semantic search**: `datacortex search "{question}" --top 5`
2. **Graph traversal**: Follow wiki-links from results (multi-hop)
3. **Direct read**: Load specific files from `reads.required`

### Phase 3: GENERATE
- Synthesize answer from retrieved knowledge
- Cite sources with [[wiki-links]]
- If uncertain, return to SEARCH phase
```

#### 5.2 Agentic RAG Decision Pattern

Agents decide *when* and *what* to retrieve, not just *how*:

```yaml
# In agent execution
retrieval_decisions:
  - condition: "task mentions specific concept"
    action: "datacortex search for that concept"

  - condition: "task requires current state"
    action: "read org files directly"

  - condition: "task spans multiple topics"
    action: "multi-hop: search → follow links → search again"

  - condition: "sufficient context already loaded"
    action: "skip retrieval, generate directly"
```

### 6. Multi-Hop Reasoning via Datacortex

Leverage the knowledge graph for chained lookups:

#### 6.1 Graph Traversal Pattern

```bash
# Single-hop: direct semantic search
datacortex search "data tokenization" --top 5

# Multi-hop: follow connections from results
datacortex search "data tokenization" --top 3 --expand 1

# Output includes:
# - Direct matches (hop 0)
# - Connected documents via wiki-links (hop 1)
# - Shared tags cluster (hop 1)
```

#### 6.2 Reasoning Path Tracking

```yaml
# In execution_log.yaml
reasoning_paths:
  - execution_id: "exec-2025-12-21-001"
    hops:
      - hop: 0
        query: "data tokenization"
        results: ["Data-Tokenization.md", "RWA-Overview.md"]
      - hop: 1
        source: "Data-Tokenization.md"
        followed_links: ["Verity-Protocol.md", "SPV-Structure.md"]
      - hop: 2
        source: "Verity-Protocol.md"
        followed_links: ["Data-Marketplace.md"]
    final_context: ["Data-Tokenization.md", "Verity-Protocol.md", "SPV-Structure.md"]
```

#### 6.3 When to Use Multi-Hop

| Task Type | Hops | Example |
|-----------|------|---------|
| Factual lookup | 0 | "What is data tokenization?" |
| Contextual understanding | 1 | "How does tokenization relate to Verity?" |
| Strategic synthesis | 2+ | "What's our competitive advantage in data markets?" |

### 7. Tiered Memory Architecture

Implement MemGPT-inspired tiered retrieval:

#### 7.1 Memory Tiers

```
┌─────────────────────────────────────────────────────────┐
│ TIER 0: Working Memory (Context Window)                 │
│ - Current task description                              │
│ - CLAUDE.md base context                                │
│ - reads.required files                                  │
│ - Recent conversation history                           │
│ Capacity: ~100K tokens                                  │
└─────────────────────────────────────────────────────────┘
                          ↓ overflow
┌─────────────────────────────────────────────────────────┐
│ TIER 1: Hot Storage (Datacortex Cache)                  │
│ - Recent search results                                 │
│ - Frequently accessed zettels                           │
│ - Session memory (last 7 days)                          │
│ Access: datacortex search (< 1s)                        │
└─────────────────────────────────────────────────────────┘
                          ↓ cache miss
┌─────────────────────────────────────────────────────────┐
│ TIER 2: Warm Storage (Full Knowledge Base)              │
│ - All embedded documents                                │
│ - Literature notes, zettels, pages                      │
│ - Historical execution logs                             │
│ Access: datacortex search with embedding (1-3s)         │
└─────────────────────────────────────────────────────────┘
                          ↓ not embedded
┌─────────────────────────────────────────────────────────┐
│ TIER 3: Cold Storage (File System)                      │
│ - Non-embedded files                                    │
│ - Archive content                                       │
│ - Raw documents without companions                      │
│ Access: glob/grep/read tools (variable)                 │
└─────────────────────────────────────────────────────────┘
```

#### 7.2 Tier Selection Logic

```python
def select_tier(query: str, urgency: str) -> str:
    # Check working memory first
    if query in current_context:
        return "tier0_working"

    # Hot storage for recent/frequent
    if is_recent_query(query) or is_high_frequency_topic(query):
        return "tier1_hot"

    # Warm storage for embedded content
    if has_embedding(query):
        return "tier2_warm"

    # Cold storage fallback
    return "tier3_cold"
```

### 8. Session Memory Embedding

Agent outputs become searchable knowledge for future sessions:

#### 8.1 Memory Generation

After each agent execution, generate memory entry:

```yaml
# Auto-generated after execution
session_memories:
  - id: "mem-2025-12-21-001"
    source_execution: "exec-2025-12-21-001"
    agent_id: "gtd-research-processor"
    timestamp: "2025-12-21T10:15:32Z"

    # Searchable summary (embedded in datacortex)
    summary: |
      Researched data tokenization for RWA markets.
      Key finding: SPV structure enables fractional ownership.
      Created zettel on tokenization mechanics.

    # Structured insights
    insights:
      - "SPV structure is key enabler for data tokenization"
      - "Regulatory clarity needed for RWA data assets"

    # Tags for retrieval
    tags: ["tokenization", "rwa", "verity", "research"]

    # Links to outputs
    outputs:
      - "notes/2-knowledge/zettel/Data-Tokenization.md"
```

#### 8.2 Memory Embedding

```bash
# After execution, embed the summary
datacortex embed \
  --text "{summary}" \
  --type session-memory \
  --source "exec-2025-12-21-001" \
  --tags "tokenization,rwa"
```

#### 8.3 Future Session Retrieval

Agents can query past session insights:

```bash
# "What did we learn about tokenization?"
datacortex search "tokenization" --type session-memory --top 5

# Returns:
# 1. [session-memory] 2025-12-21: SPV structure enables fractional ownership
# 2. [session-memory] 2025-12-15: Tokenization requires clear data provenance
# 3. [zettel] Data-Tokenization.md: Core concept explanation
```

### 9. Knowledge Pre-Fetch Pattern

Standardize how agents gather context before execution:

```markdown
## Context Gathering (inject into agent prompts)

Before executing your primary task:

1. **Required Knowledge**: The following files have been pre-loaded:
   {required_files}

2. **Relevant DIPs**: These governance documents apply:
   {dip_summaries}

3. **Semantic Context**: Based on your task, these knowledge items are relevant:
   {datacortex_results}

4. **Session Memory**: Previous insights on this topic:
   {session_memory_results}

5. **Task-Specific**: {inferred_paths}
```

### 10. Performance Tracking

Track agent execution locally and sync to nightshift server for aggregation.

#### 10.1 Execution Log Format

Create `.datacore/state/execution_log.yaml` (gitignored, synced to nightshift):

```yaml
# Execution Log - Local state, synced to nightshift
version: "1.0.0"
last_sync: "2025-12-21T10:30:00Z"

executions:
  - id: "exec-2025-12-21-001"
    agent_id: "gtd-research-processor"
    timestamp: "2025-12-21T10:15:32Z"
    task_id: "next_actions:L227"

    # Execution metrics
    duration_ms: 45000
    tokens_in: 12500
    tokens_out: 3200

    # Outcome
    status: "success"  # success, partial, failed, timeout
    outputs:
      - path: "notes/2-knowledge/zettel/Data-Tokenization.md"
        type: "zettel"
      - path: "notes/2-knowledge/literature/RWA-Report-2024.md"
        type: "literature-note"

    # Quality signals (for reputation)
    quality:
      user_feedback: null  # pending, positive, negative, revised
      automated_checks:
        - check: "output_exists"
          passed: true
        - check: "links_valid"
          passed: true

    # Agent interactions
    spawned_agents: []
    called_by: "ai-task-executor"

  - id: "exec-2025-12-21-002"
    agent_id: "ai-task-executor"
    timestamp: "2025-12-21T10:14:00Z"
    task_id: "nightshift-batch-001"
    duration_ms: 180000
    status: "success"
    spawned_agents:
      - agent_id: "gtd-research-processor"
        execution_id: "exec-2025-12-21-001"
        status: "success"
      - agent_id: "gtd-content-writer"
        execution_id: "exec-2025-12-21-003"
        status: "success"
```

#### 10.2 Aggregated Performance Metrics

Add to registry as computed state (updated after each execution):

```yaml
# In agents.yaml, computed section
agents:
  gtd-research-processor:
    # ... static fields ...

    # === Performance (computed, not manually edited) ===
    performance:
      total_executions: 142
      success_rate: 0.94
      avg_duration_ms: 38500
      last_execution: "2025-12-21T10:15:32Z"

      # Per-skill breakdown
      skill_metrics:
        url-analysis:
          executions: 89
          success_rate: 0.96
        zettel-creation:
          executions: 53
          success_rate: 0.91

      # Reputation (Virtuals ACP inspired)
      reputation:
        score: 87  # 0-100, computed from feedback
        feedback_count: 28
        positive_rate: 0.89

      # Version history (Olas inspired)
      version_history:
        - version: "1.0.0"
          hash: "abc123"
          deployed: "2025-11-15"
          executions: 142
        - version: "0.9.0"
          hash: "def456"
          deployed: "2025-10-01"
          executions: 87
          retired: "2025-11-15"
```

#### 10.3 Nightshift Sync

Performance data syncs bidirectionally with nightshift server:

```
LOCAL                              NIGHTSHIFT SERVER
─────────────────────────────────────────────────────
execution_log.yaml  ──push──→     Aggregate metrics
                                        ↓
                               Compute cross-session stats
                               Update reputation scores
                                        ↓
performance stats   ←──pull──     Return aggregated data
```

**Sync triggers:**
- After each agent execution (append to local log)
- On `/wrap-up` command (push to server)
- On `/today` command (pull aggregated stats)
- Nightshift batch completion (server-side aggregation)

### 11. Agent-to-Agent Interactions

Track how agents collaborate, spawn, and evaluate each other.

#### 11.1 Interaction Registry

```yaml
# In agents.yaml
agents:
  ai-task-executor:
    # ... other fields ...

    # === Relationships ===
    spawns:
      - "gtd-research-processor"
      - "gtd-content-writer"
      - "gtd-data-analyzer"
      - "gtd-project-manager"

    can_be_called_by:
      - "nightshift"  # Scheduled execution
      - "user"        # Direct invocation

    delegates_to: []  # Passes control entirely

  gtd-research-processor:
    spawns: []
    can_be_called_by:
      - "ai-task-executor"
      - "user"
    delegates_to: []
```

#### 11.2 Inter-Agent Evaluation (Virtuals ACP Pattern)

Agents can provide feedback on other agents' outputs:

```yaml
# In execution_log.yaml
evaluations:
  - id: "eval-2025-12-21-001"
    evaluator_agent: "ai-task-executor"
    evaluated_agent: "gtd-research-processor"
    execution_id: "exec-2025-12-21-001"
    timestamp: "2025-12-21T10:20:00Z"

    # Structured evaluation
    scores:
      task_completion: 95     # Did it complete the task?
      output_quality: 88      # Quality of outputs
      efficiency: 72          # Token/time efficiency

    # Tags for categorization (ERC-8004 feedback tags)
    tags: ["research", "zettel"]

    # Optional notes
    notes: "Created high-quality zettel but took longer than expected"
```

#### 11.3 Composition Model (Olas Pattern)

Borrow from Olas: agents can be composed from reusable components.

```yaml
# Component registry (future extension)
components:
  web-fetcher:
    type: "component"
    description: "Fetches and parses web content"
    version: "1.0.0"

  markdown-writer:
    type: "component"
    description: "Generates structured markdown"
    version: "1.0.0"

agents:
  gtd-research-processor:
    type: "agent"
    # Agent is composed of components
    components:
      - "web-fetcher"
      - "markdown-writer"
    # Components + agent prompt = full capability
```

### 12. Knowledge Location Matrix

Standardize where agents read from and write to:

```yaml
# In agents.yaml, global section
knowledge_locations:
  personal:
    inbox: "0-personal/org/inbox.org"
    next_actions: "0-personal/org/next_actions.org"
    journals: "0-personal/notes/journals/"
    zettel: "0-personal/notes/2-knowledge/zettel/"
    literature: "0-personal/notes/2-knowledge/literature/"
    active_notes: "0-personal/notes/1-active/"

  org:  # Template for org spaces
    inbox: "{space}/org/inbox.org"
    next_actions: "{space}/org/next_actions.org"
    journals: "{space}/journal/"
    zettel: "{space}/3-knowledge/zettel/"
    literature: "{space}/3-knowledge/literature/"
    tracks: "{space}/1-tracks/"
    archive: "{space}/4-archive/"

  routing:
    # How to determine space
    personal_indicators:
      - "my notes"
      - "personal"
      - "draft"
    org_indicators:
      - "official"
      - "company"
      - "team"
```

### 13. Future: Agent Wallets & Monetization

Reserved fields in the registry enable future scenarios:

```yaml
# Future fields (not implemented in v1)
erc8004:
  agentId: 42  # On-chain ID from Identity Registry
  wallet: "0x1234..."  # Agent's Ethereum address
  supportedTrust:
    - reputation     # Client feedback
    - crypto-economic  # Staked validation
    - tee-attestation  # TEE proofs

  # Payment configuration (x402 protocol)
  payment:
    protocol: "x402"  # HTTP 402 Payment Required
    currency: "USDC"
    pricing:
      url-analysis: "0.01"  # Per invocation
      zettel-creation: "0.005"

  chainRegistrations:
    - chainId: "8453"  # Base
      identityRegistry: "0xABC..."
      agentId: 42

# Virtuals ACP integration (future)
virtuals:
  agent_token: null  # ERC-20 token address
  commerce_enabled: false

# Olas integration (future)
olas:
  service_id: null  # NFT ID in Olas registry
  component_hashes: []  # Version history via hash appending
  staking_enabled: false
```

## Rationale

### Why This Design?

1. **YAML over JSON**: Matches existing Datacore conventions, human-readable, supports comments.

2. **Layered Compatibility**: Works locally today, compatible with A2A/ERC-8004 tomorrow.

3. **Skills-Based Model**: Borrowed from A2A because it enables semantic discovery and clear capability advertising.

4. **Explicit Knowledge Linking**: Solves the "agents don't know what to read" problem directly.

5. **Reserved Fields**: Future-proofs without over-engineering today.

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Inline metadata in agent .md frontmatter | Harder to query, no single source of truth |
| Pure ERC-8004 JSON format | Not human-friendly, overkill for local use |
| Database-backed registry | Adds complexity, file-based is sufficient |
| MCP server for agent discovery | Good for external use, but local needs simpler solution |

## Backwards Compatibility

- **Existing agents continue to work**: Registry is additive
- **Gradual migration**: Agents without registry entries fall back to current behavior
- **`tags.yaml` still honored**: Registry extends, doesn't replace tag routing

### Migration Path

1. Generate initial `agents.yaml` from existing agent files
2. Add `reads` and `references` fields incrementally
3. Update `ai-task-executor` to prefer registry when available
4. Deprecate hardcoded routing over time

## Security Considerations

1. **Registry tampering**: Registry file should be tracked in git, changes reviewed
2. **Knowledge injection**: Pre-fetched context could include sensitive data - respect privacy levels
3. **External registration**: On-chain registration requires wallet security considerations
4. **Module trust**: Auto-registered module agents inherit module trust level

## Implementation

### Phase 1: Local Registry (v1.0)

1. Create `.datacore/registry/agents.yaml` with core agents
2. Update `ai-task-executor` to read registry for routing
3. Add `references` field and auto-inject DIPs/specs
4. Add CLI: `datacortex agent list`, `datacortex agent find`
5. Add `knowledge_locations` matrix for consistent paths

### Phase 2: Knowledge Pre-Fetch (v1.1)

1. Implement `reads.contextual` query execution
2. Add datacortex integration for semantic pre-fetch
3. Validate `writes` paths exist before agent execution
4. Add Agent Context section pattern to all agent prompts

### Phase 3: Performance Tracking (v1.2)

1. Create `.datacore/state/execution_log.yaml` structure
2. Implement execution logging after each agent run
3. Add automated quality checks (output_exists, links_valid)
4. Compute aggregated `performance` metrics in registry

### Phase 4: Module Integration (v1.3)

1. Add install hook for module agent registration
2. Implement `module_agents` section handling
3. Update `context-maintainer` to sync module agents
4. Add `spawns` and `can_be_called_by` relationship tracking

### Phase 5: Nightshift Sync (v1.4)

1. Implement execution_log push to nightshift server
2. Pull aggregated performance stats on `/today`
3. Add reputation score computation from feedback
4. Version history tracking (Olas-inspired hash appending)

### Phase 6: Agent-to-Agent Evaluation (v1.5)

1. Implement inter-agent evaluation in execution_log
2. Add evaluation scores (task_completion, output_quality, efficiency)
3. Aggregate evaluations into reputation scores
4. Enable orchestrator agents to rate spawned agents

### Phase 7: External Compatibility (v2.0)

1. Add AgentCard generation endpoint (A2A compatible)
2. Implement ERC-8004 registration file export
3. Add `/.well-known/agent.json` serving capability
4. Component registry for Olas-style composition (future)
5. Wallet integration and x402 payments (separate DIP)

### New Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `agents.yaml` | `.datacore/registry/` | Agent registry with capabilities, triggers, references |
| `execution_log.yaml` | `.datacore/state/` | Local execution history (gitignored, synced) |
| `datacortex agent` | CLI | Agent discovery commands (`list`, `find`) |

### Improvements Checklist

All improvements identified in the analysis are addressed:

| Improvement | Section | Status |
|-------------|---------|--------|
| Agent Capability Registry | §1 | Core feature |
| Semantic Pre-Fetch via Datacortex | §9 | `reads.contextual` + session memory |
| Spec Linking in Frontmatter | §1 | `references.dips`, `references.specs` |
| Module Auto-Registration | §3.3 | Install hooks |
| Knowledge Location Matrix | §12 | Standardized paths |
| Session Memory Embedding | §8 | Embedded summaries, searchable |
| Performance Tracking | §10 | Local + nightshift sync |
| Agent-to-Agent Interactions | §11 | Spawns, evaluations, composition |

**Research Patterns Implemented:**

| Pattern | Source | Section |
|---------|--------|---------|
| Think-Search-Generate | Generate-on-Graph | §5 |
| Agentic RAG Decisions | Agentic RAG Survey | §5.2 |
| Multi-Hop Reasoning | GraphRAG | §6 |
| Tiered Memory | MemGPT | §7 |
| Session Memory | A-MEM Zettelkasten | §8 |
| Agent Composition | Olas Protocol | §11.3 |
| Agent Evaluation | Virtuals ACP | §11.2 |
| Version Hash Tracking | Olas Protocol | §10.2 |

## Open Questions

1. **Embedding agent skills**: Should skills be embedded in datacortex for semantic discovery?

2. **Session memory search**: Should execution outputs be embedded for future retrieval? (e.g., "What did gtd-research-processor find about tokenization?")

3. **Multi-agent coordination**: How do `spawns` relationships affect knowledge sharing between parent/child agents?

4. **Privacy levels**: Should registry entries have privacy classifications per DIP-0002?

5. **Versioning**: How to handle breaking changes in agent capabilities?

6. **Component reuse**: When should we extract common patterns into Olas-style components?

## References

### External Standards

- [ERC-8004: Trustless Agents](https://eips.ethereum.org/EIPS/eip-8004) - Ethereum agent registry standard (Identity, Reputation, Validation registries)
- [Google A2A Protocol](https://a2a-protocol.org/latest/specification/) - Agent-to-Agent interoperability (AgentCard, skills schema)
- [Virtuals Protocol](https://whitepaper.virtuals.io) - Agent Commerce Protocol (ACP) for agent-to-agent commerce and ratings
- [Olas Protocol](https://olas.network/) - On-chain agent registry with NFT-based components, agents, and services
- [x402 Payment Protocol](https://x402.org/) - HTTP 402 micropayments for agents
- [A-MEM: Agentic Memory](https://arxiv.org/abs/2502.12110) - Zettelkasten-inspired agent memory

### Protocol Pattern Origins

| Pattern | Source | Usage in This DIP |
|---------|--------|-------------------|
| Three registries (Identity, Reputation, Validation) | ERC-8004 | Registry structure, future on-chain |
| AgentCard with skills array | A2A Protocol | Skills-based capability discovery |
| Agent-to-agent evaluation/ratings | Virtuals ACP | Inter-agent evaluation in execution_log |
| Component → Agent → Service composition | Olas | Future component registry |
| Version tracking via hash appending | Olas | version_history in performance metrics |
| Tokenized agents (ERC-20/721) | Virtuals/Olas | Reserved erc8004/virtuals/olas fields |

### Internal References

- [DIP-0009: GTD Specification](DIP-0009-gtd-specification.md) - Agent routing and execution
- [DIP-0014: Tag Taxonomy](DIP-0014-tag-taxonomy.md) - Tag-based agent triggers
- [DIP-0002: Layered Context](DIP-0002-layered-context-pattern.md) - Privacy levels for registry
- [DIP-0004: Knowledge Database](DIP-0004-knowledge-database.md) - Datacortex integration
- [DIP-0011: Nightshift Module](DIP-0011-nightshift-module.md) - Server-side execution and sync

### Research

- [Agentic RAG Survey](https://arxiv.org/abs/2501.09136) - Dynamic retrieval patterns
- [GraphRAG](https://neo4j.com/blog/genai/knowledge-graph-llm-multi-hop-reasoning/) - Knowledge graph reasoning
- [ZBrain Knowledge Graphs](https://zbrain.ai/knowledge-graphs-for-agentic-ai/) - Agentic AI architecture
- [LangChain Memory for Agents](https://blog.langchain.com/memory-for-agents/) - Agent memory patterns
- [Letta Agent Memory](https://www.letta.com/blog/agent-memory) - MemGPT virtual memory approach
