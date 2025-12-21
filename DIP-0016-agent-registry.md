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

This DIP introduces a machine-readable agent registry system that enables dynamic agent discovery, capability advertising, and knowledge source linking. The design is forward-compatible with [ERC-8004 Trustless Agents](https://eips.ethereum.org/EIPS/eip-8004) and [Google A2A Protocol](https://a2a-protocol.org/latest/specification/), enabling future scenarios where agents have wallets, charge for services, or operate across organizational boundaries.

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

### 5. Knowledge Pre-Fetch Pattern

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

4. **Task-Specific**: {inferred_paths}
```

### 6. Future: Agent Wallets & Monetization

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

  # Payment configuration
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

### Phase 2: Knowledge Pre-Fetch (v1.1)

1. Implement `reads.contextual` query execution
2. Add datacortex integration for semantic pre-fetch
3. Validate `writes` paths exist before agent execution

### Phase 3: Module Integration (v1.2)

1. Add install hook for module agent registration
2. Implement `module_agents` section handling
3. Update `context-maintainer` to sync module agents

### Phase 4: External Compatibility (v2.0)

1. Add AgentCard generation endpoint
2. Implement ERC-8004 registration file export
3. Add `/.well-known/agent.json` serving capability
4. Wallet integration (separate DIP)

## Open Questions

1. **Embedding agent skills**: Should skills be embedded in datacortex for semantic discovery?

2. **Reputation local storage**: Should we track agent execution success/failure locally before on-chain?

3. **Multi-agent coordination**: How do `spawns` relationships affect knowledge sharing?

4. **Privacy levels**: Should registry entries have privacy classifications per DIP-0002?

5. **Versioning**: How to handle breaking changes in agent capabilities?

## References

### External Standards

- [ERC-8004: Trustless Agents](https://eips.ethereum.org/EIPS/eip-8004) - Ethereum agent registry standard
- [Google A2A Protocol](https://a2a-protocol.org/latest/specification/) - Agent-to-Agent interoperability
- [x402 Payment Protocol](https://x402.org/) - HTTP 402 micropayments for agents
- [A-MEM: Agentic Memory](https://arxiv.org/abs/2502.12110) - Zettelkasten-inspired agent memory

### Internal References

- [DIP-0009: GTD Specification](DIP-0009-gtd-specification.md) - Agent routing and execution
- [DIP-0014: Tag Taxonomy](DIP-0014-tag-taxonomy.md) - Tag-based agent triggers
- [DIP-0002: Layered Context](DIP-0002-layered-context-pattern.md) - Privacy levels for registry

### Research

- [Agentic RAG Survey](https://arxiv.org/abs/2501.09136) - Dynamic retrieval patterns
- [GraphRAG](https://neo4j.com/blog/genai/knowledge-graph-llm-multi-hop-reasoning/) - Knowledge graph reasoning
- [ZBrain Knowledge Graphs](https://zbrain.ai/knowledge-graphs-for-agentic-ai/) - Agentic AI architecture
