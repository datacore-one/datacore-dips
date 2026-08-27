# DIP-0027: Shared Validation Envelope for PLUR Engrams ↔ EvoMap Genes

| Field | Value |
|-------|-------|
| **DIP** | 0027 |
| **Title** | Shared Validation Envelope for PLUR Engrams ↔ EvoMap Genes |
| **Author** | @datacore-one + (proposed co-author) EvoMap maintainers |
| **Type** | Standards Track |
| **Status** | Draft — gated on Evolver-spike lift signal |
| **Created** | 2026-05-13 |
| **Updated** | 2026-05-13 |
| **Tags** | `plur`, `evomap`, `interop`, `provenance`, `fitness`, `exchange`, `angle-c` |
| **Affects** | `packages/core/src/schemas/engram.ts` (PLUR), Evolver GEP schema (EvoMap), DIP-0019 §8 (exchange protocol) |
| **Specs** | DIP-0019 (Learning Architecture), ENG-2026-0512-008 (EvoMap competitive map), ENG-2026-0221-618 (fitness function) |
| **Conditional** | This DIP only proceeds if the local-only Evolver spike (Angle A) demonstrates measurable lift over the PLUR-only baseline. See §0. |

## 0. Precondition: Spike Lift Gate

This DIP is **drafted but not promotable to Status: Proposed** until the Evolver spike (Angle A) reports against the following decision criteria:

| Signal | Threshold to proceed |
|--------|---------------------|
| Net injection quality lift (LongMemEval Hit@10 or equivalent) | ≥ +3 points over PLUR-only baseline |
| Capsule promotion rate (Evolver-validated fixes → PLUR engrams) | ≥ 1 promotion per 10 Capsules without quality regression |
| Operator overhead (manual review burden) | ≤ 1.5× current daily-review minutes |
| GPL contagion containment verified | local-only boundary holds; no Evolver code linked into PLUR core |

If two or more signals miss threshold → close this DIP as `Withdrawn`. If all pass → promote to Proposed and proceed to specification review with EvoMap maintainers.

## Summary

Define a portable **Validation Envelope** — a small, schema-stable metadata block — that PLUR engrams and EvoMap Genes/Capsules can both carry. The envelope captures provenance, fitness, validation evidence, and contraindications using shared field names and semantics, so a Capsule promoted out of Evolver and an engram exported from PLUR are mutually intelligible without lossy translation.

This is the **Angle C (co-development)** foundation: rather than each side wrapping the other's format adapter-style, both projects converge on a single envelope schema and own it jointly. PLUR and EvoMap continue to differ in their *internal* representations (engrams.yaml vs Gene templates) but share a common *exchange* representation at the boundary.

## Motivation

### The Translation-Loss Problem

PLUR and EvoMap independently arrived at the same absorption hierarchy:

| Stage | PLUR (DIP-0019) | EvoMap (GEP) |
|-------|----------------|--------------|
| Atomic capture | Engram (candidate) | Gene fragment |
| Validated unit | Engram (active, high retrieval_strength) | Capsule (validated fix) |
| Compiled rule | Skill / CLAUDE.md entry | Skill (SKILL.md) |

Both already use the **agentskills.io SKILL.md format** at the top of the stack (ENG-2026-0512-008). But the middle tier — validated, exchangeable knowledge units — has no shared schema. Today, moving a Capsule into PLUR or an engram into EvoMap means:

1. Dropping provenance chains (EvoMap chain ≠ PLUR `provenance.chain`)
2. Recomputing fitness from scratch (EvoMap's adoption signal ≠ PLUR's `adoption_count × environmental_diversity`)
3. Losing contraindications (PLUR's `contraindications` array has no EvoMap equivalent)
4. Re-running validation gates that the other side already passed

The Validation Envelope eliminates the translation loss for the metadata that actually drives trust and selection.

### Why Now

- **PLUR exchange protocol** (DIP-0019 §8) is implemented; abstract engrams are exchange-eligible and ship today
- **EvoMap Evolver** went open-source (GPL-3.0) in April 2026 with active community (~7K stars)
- **Both sides** are pre-1.0 on the validation-metadata schema — cheaper to align now than after either freezes a v1.0 schema
- **The spike (Angle A)** will surface real cross-system data shape friction; this DIP captures the lessons in a portable spec

## Specification

### 1. Validation Envelope Schema

The envelope is a YAML/JSON object embeddable inside any unit (engram, Gene, Capsule, Recipe). It MUST be parseable standalone — receivers must not need access to the host system to interpret its fields.

```yaml
validation_envelope:
  version: 1.0
  unit_id: "ENG-2026-0131-001"        # opaque to consumer; native to producer
  unit_kind: "engram"                  # engram | gene | capsule | skill
  origin_system: "plur"                # plur | evomap | datacore | other:<name>

  # --- Provenance (who, where from, what license) ---
  provenance:
    origin: "user/personal"            # producer-defined namespace
    chain:                             # ordered: oldest → newest
      - system: "plur"
        unit_id: "ENG-2026-0131-001"
        timestamp: "2026-01-31T14:22:00Z"
        event: "created"               # created | modified | promoted | imported | exported
      - system: "evomap"
        unit_id: "cap_a4f9c2"
        timestamp: "2026-04-12T09:01:11Z"
        event: "imported"
    signature: null                    # ed25519 signature of canonical envelope (nullable)
    public_key: null                   # signer public key (nullable)
    license: "cc-by-sa-4.0"            # SPDX identifier
    attribution_required: true

  # --- Fitness (quality signals across systems) ---
  fitness:
    score: 0.74                        # composite [0, 1], producer-computed
    components:                        # named, each [0, 1]; consumers can recompute weighted total
      adoption_count: 12
      environmental_diversity: 3       # distinct domains/stores where adopted
      retrieval_strength: 0.82         # PLUR-native; EvoMap maps from access frequency
      age_days: 102
      contradiction_rate: 0.05         # fraction of injections followed by user correction
    sample_size: 47                    # number of observations behind components
    computed_at: "2026-05-12T10:00:00Z"
    formula_version: "datacore-v1"     # named formula; consumers may recompute (see §3)

  # --- Validation evidence (did it pass gates?) ---
  validation:
    gates_passed:                      # named gates from producer's quality pipeline
      - name: "behavioral"
        system: "plur"
        passed_at: "2026-02-01T00:00:00Z"
      - name: "documentation"
        system: "plur"
      - name: "evomap.evolver_replay"  # EvoMap-specific gate
        system: "evomap"
        evidence_ref: "evomap://replays/cap_a4f9c2"
        passed_at: "2026-04-12T09:01:11Z"
    test_evidence:                     # optional: machine-verifiable artefacts
      - kind: "replay"
        ref: "evomap://replays/cap_a4f9c2"
        outcome: "pass"
        runs: 23
        failures: 0
      - kind: "benchmark"
        ref: "plur://bench/longmemeval/2026-04"
        score: 0.867
        baseline: 0.851
    contraindications:                 # WHERE NOT TO APPLY — required if non-empty
      - "Quick-capture flows where latency > 200ms breaks UX"
      - "Multi-tenant deployments without per-store isolation"
    confidence: 0.7                    # producer's self-assessed reliability [0, 1]

  # --- Compatibility hints (consumer routing) ---
  compatibility:
    consumable_by:                     # systems that can natively ingest the host unit
      - "plur>=0.5"
      - "evomap>=1.2"
      - "datacore>=2026-Q2"
    requires_capabilities: []          # named capability strings consumer must support
    deprecates: []                     # unit_ids superseded by this one
    deprecated_by: null                # unit_id that supersedes this one
```

### 2. Field Semantics: Shared vs. System-Specific

To prevent drift, fields fall into three tiers:

| Tier | Behavior | Examples |
|------|----------|----------|
| **Core** (MUST) | Same semantics in PLUR and EvoMap. Schema-validated. | `version`, `unit_kind`, `origin_system`, `provenance.chain`, `provenance.license`, `fitness.score`, `validation.contraindications` |
| **Standard** (SHOULD) | Same semantics, optional. Recognized by both sides if present. | `fitness.components.*`, `validation.gates_passed`, `validation.test_evidence`, `validation.confidence` |
| **Extension** (MAY) | Namespaced `x-<system>-<field>`. Producer-specific; consumers preserve verbatim but don't interpret. | `x-plur-knowledge-anchors`, `x-evomap-recipe-graph`, `x-datacore-pack` |

Extensions are how each side keeps native power without polluting the shared core. PLUR's `knowledge_anchors`, `associations`, and `dual_coding` ride along as `x-plur-*` extensions when exported.

### 3. Fitness Comparability

Each side computes `fitness.score` using its own formula but MUST publish:
- `fitness.formula_version` (named, versioned identifier)
- `fitness.components` (raw signals, not just the composite)

Consumers SHOULD recompute fitness in their own formula when ingesting. The shared formula registry (proposed: `validation-envelope/formulas/` in a jointly-maintained repo) catalogs known formulas:

| `formula_version` | Source | Weights |
|-------------------|--------|---------|
| `datacore-v1` | DIP-0019 §8 (ENG-2026-0221-618) | adoption×diversity 0.4 / strength 0.3 / log(age) 0.2 / (1−contradiction) 0.1 |
| `evomap-v1` | (placeholder — EvoMap to publish) | TBD |
| `geometric-mean-v1` | (proposed neutral) | geometric mean of normalized components |

This avoids the "two systems, two scores, no comparability" problem without forcing a single formula on either side.

### 4. Provenance Chain Rules

The `provenance.chain` is an ordered audit trail:

1. **Append-only** — receivers MUST NOT modify earlier entries
2. **Signature verification optional** — `signature` may be null; verifiers SHOULD check when present
3. **Event vocabulary** — `created | modified | promoted | imported | exported | redacted`
4. **Modification = new entry** — any change to host unit produces a new chain entry, never overwrites
5. **Roundtripping** — a unit exported PLUR→EvoMap→PLUR retains all three chain entries

This composes with the existing engram `provenance.chain` (ENG-2026-0221-621) — the envelope chain *is* the engram chain when `origin_system: plur`, with no field renaming.

### 5. Mapping Tables

#### 5.1 PLUR engram → Envelope

| Engram field (DIP-0019 §2) | Envelope path |
|---------------------------|---------------|
| `id` | `unit_id` |
| `provenance.origin` | `provenance.origin` |
| `provenance.chain` | `provenance.chain` (prefixed with `system: plur`) |
| `provenance.signature` | `provenance.signature` |
| `provenance.license` | `provenance.license` |
| `activation.retrieval_strength` | `fitness.components.retrieval_strength` |
| `derivation_count` | `fitness.components.adoption_count` |
| `feedback_signals` | `fitness.components.contradiction_rate` (derived: `negative / total`) |
| `contraindications` | `validation.contraindications` |
| `confidence` | `validation.confidence` (normalized 0–10 → 0–1) |
| `knowledge_anchors` | `x-plur-knowledge-anchors` |
| `associations` | `x-plur-associations` |
| `dual_coding` | `x-plur-dual-coding` |

#### 5.2 EvoMap Capsule → Envelope *(proposed, pending EvoMap maintainer review)*

| Capsule field (inferred from public GEP docs) | Envelope path |
|----------------------------------------------|---------------|
| `capsule_id` | `unit_id` |
| `parent_gene` | `provenance.chain[0]` |
| `replay_count` / `replay_success_rate` | `validation.test_evidence[kind: replay]` |
| `fitness` | `fitness.score` + `fitness.components` |
| `failure_modes` | `validation.contraindications` |
| `recipe_refs` | `x-evomap-recipe-graph` |

The exact mapping is part of the co-development deliverable; this table is a starting proposal.

### 6. Reference Implementation Path

| Step | Owner | Output |
|------|-------|--------|
| 1 | PLUR | Add `toValidationEnvelope()` / `fromValidationEnvelope()` to `@plur-ai/core` |
| 2 | EvoMap | Add equivalent to Evolver core (Python) |
| 3 | Joint | Publish JSON Schema for envelope v1.0 at `validation-envelope.org` (or shared GitHub repo) |
| 4 | Joint | Conformance test suite: roundtrip PLUR→Envelope→EvoMap→Envelope→PLUR, assert no Core/Standard field loss |
| 5 | PLUR | MCP tool `plur_export_envelope` / `plur_import_envelope` |
| 6 | EvoMap | Equivalent Evolver CLI subcommands |

### 7. Storage and File Format

When persisted standalone (not embedded in a host unit), the envelope is a single YAML file with extension `.env.yaml`:

```
some-capability.env.yaml
```

Multiple envelopes in a pack format (`.envpack.tar.gz`):

```
envelopes/
  ENG-2026-0131-001.env.yaml
  cap_a4f9c2.env.yaml
manifest.yaml          # pack-level metadata, signature
```

## Rationale

### Why a shared envelope, not a translation layer

A translation layer (adapter pattern) means every new system pair needs N×N adapters. An envelope means each system writes one exporter and one importer (N+N), and any pair interoperates automatically. The N×N → 2N reduction is the well-trodden "narrow waist" argument that made TCP/IP, JSON, and OCI images work.

### Why co-author with EvoMap rather than unilaterally publish

PLUR-defined "open" envelope that EvoMap doesn't adopt is just a PLUR export format. The leverage of an envelope comes from second-party buy-in. Co-authorship — even informal — buys:
- EvoMap-side semantics for `unit_kind: capsule` (we don't know their internal model)
- Endorsement signal for prospective third systems (Cofounder 2, other memory MCPs)
- A defensible neutral name (`validation-envelope.org`) instead of `plur-export-v1`

If EvoMap declines, fall back to publishing as PLUR-side only and accept reduced reach.

### Why fitness components, not just score

Two systems with different fitness formulas exchanging only the composite score creates fake comparability. Publishing components lets each side recompute under its own weighting — same data, different interpretation, intellectually honest.

### Why namespaced extensions (`x-plur-*`)

Extensions follow the HTTP/JSON Schema convention. Familiar to API maintainers; trivially preservable through middleware that doesn't understand them. Avoids "shared core slowly absorbs all of PLUR's schema" anti-pattern.

### Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| **No shared schema (status quo)** | Translation loss compounds with every roundtrip; each new partner is N more adapters |
| **PLUR-only export format** | EvoMap won't adopt; doesn't unlock Angle C |
| **Adopt EvoMap GEP wholesale** | GPL-3.0 contagion risk (ENG-2026-0512-008); cedes PLUR's local-first / permissionless principles |
| **Use W3C PROV-O directly** | PROV-O covers provenance well but has no fitness/validation semantics; would need extension anyway |
| **C2PA-style content credentials** | Designed for *content* provenance (was this AI-generated?), not *capability* provenance with fitness/contraindications |
| **One-side schema with adapter** | N×N adapter proliferation |

The chosen approach (small shared envelope + namespaced extensions) is the minimum schema needed to eliminate the documented translation losses while preserving each system's autonomy.

## Backwards Compatibility

- **PLUR**: Additive. Engrams gain an `envelope_version` field for cross-checking; existing engrams produce valid envelopes via `toValidationEnvelope()` with empty extensions where unknown.
- **EvoMap**: Equivalent additive change in Evolver; pre-envelope Capsules remain readable, envelope export is opt-in.
- **Datacore packs** (DIP-0019 §8 exchange): Existing exchange packets continue to work. The packet format gains an optional `envelope` field carrying the standardized version alongside the legacy native form during a 6-month transition.

No breaking changes are required for v1.0 of the envelope.

## Security Considerations

| Risk | Mitigation |
|------|-----------|
| **Forged provenance chain** | `signature` field supports ed25519; verifiers SHOULD check when present. Unsigned envelopes treated as `candidate` (DIP-0019 §8 safety mechanisms still apply) |
| **Fitness inflation by adversarial publisher** | Components include `sample_size`; receivers SHOULD downweight low-sample fitness. Single-source cap (DIP-0019: max 20% from any source) extends to envelopes |
| **License laundering** | `provenance.license` MUST be preserved through chain; downstream consumers cannot strip. SPDX identifiers prevent ambiguous custom licenses |
| **Extension as smuggling channel** | Extensions are preserved verbatim but never executed. PLUR/EvoMap MUST NOT auto-import `x-*` fields as native — explicit handler registration required |
| **Cross-system code injection via Capsule import** | All foreign envelopes enter as `candidate` per DIP-0019 §8. Capsules carrying executable hints (e.g. shell commands) MUST be flagged and gated through user approval |
| **Privacy: chain leaks contributor history** | `provenance.chain` entries support `redacted` event type. Redactions preserve audit trail length but blank user-identifying fields |

## Implementation

### Phased Rollout

| Phase | Trigger | Deliverable |
|-------|---------|------------|
| 0 | Spike-lift gate passes (§0) | Promote DIP to Proposed; open EvoMap-side discussion issue |
| 1 | EvoMap maintainer engagement confirmed | Co-author final envelope v1.0 schema; publish JSON Schema |
| 2 | Schema frozen | Reference implementations in PLUR + Evolver |
| 3 | Conformance suite green | First production roundtrip (PLUR engram → Capsule → engram, lossless on Core/Standard fields) |
| 4 | Two-week stability | Promote DIP to Implemented; publish envelope to `validation-envelope.org` |

If any phase stalls > 4 weeks without movement, downgrade to PLUR-only publication and document the partial outcome.

### Reference Implementation

To be added at `packages/core/src/envelope/` in the PLUR repo and `evolver/envelope/` in EvoMap. Both reference the same JSON Schema as the source of truth.

## Open Questions

1. **Hosting**: Where does the canonical schema live? Options: GitHub org `validation-envelope`, neutral domain `validation-envelope.org`, or one side's repo with cross-links.
2. **Governance**: Two-maintainer (PLUR + EvoMap) lightweight steering, or open to additional ratifying members from day one (Cofounder 2, datacortex, other memory MCPs)?
3. **Fitness formula registry**: Inline in the schema repo, or separate registry (like SPDX)?
4. **Signature algorithm**: ed25519 only (small, fast, well-supported) or also allow ECDSA / RSA for organizations with existing PKI?
5. **Versioning**: Strict semver on `validation_envelope.version`, or date-based versioning?

## References

### Datacore
- [DIP-0019: Learning Architecture](./DIP-0019-learning-architecture.md) — engram schema v2, exchange protocol §8, fitness function §8
- [DIP-0026: Architectural Primitives](./DIP-0026-architectural-primitives.md)
- ENG-2026-0512-008 — EvoMap competitive/complementary map
- ENG-2026-0221-618 — Datacore fitness function weights
- ENG-2026-0221-621 — Engram provenance fields
- ENG-2026-0221-613 — Engram → skill absorption (maps 1:1 to EvoMap Gene → Capsule → Skill)

### External
- EvoMap Evolver — https://github.com/EvoMap/evolver (GPL-3.0, ~7K stars as of 2026-05)
- agentskills.io SKILL.md format — shared top-tier format used by both sides
- W3C PROV-O — provenance vocabulary (prior art; insufficient for fitness/validation)
- C2PA — Content Credentials (prior art; output-provenance not capability-provenance)
- SPDX License List — license identifier registry

---

## Engrams Cited

Engrams referenced or relied on while drafting this DIP:

- **ENG-2026-0512-008** — EvoMap competitive map (Genes/Capsules/Skills hierarchy, GPL-3.0 license context, partnership posture: spike local Evolver first)
- **ENG-2026-0221-618** — Datacore fitness function weights (adoption×diversity 0.4 / strength 0.3 / log(age) 0.2 / 1−contradiction 0.1)
- **ENG-2026-0221-621** — Engram provenance fields: origin, chain, signature (nullable), license (default cc-by-sa-4.0)
- **ENG-2026-0221-613** — Engram → skill promotion (production compilation in ACT-R), maps to EvoMap Gene → Capsule → Skill
- **ENG-2026-0221-615** — Engram v2 schema field list (validation reference for mapping tables §5.1)
- **ENG-2026-0302-010** — Engram packs as first data products with built-in quality signals (informs envelope-as-pack format §7)

New engrams written during this drafting session: none yet. Engrams capturing the cross-system mapping decisions will be written if Phase 1 (spike-lift gate) passes — premature otherwise.

---

## Follow-up Tasks

```yaml
follow_up_tasks:
  - heading: "Define spike-lift measurement methodology for Evolver Angle A"
    tags: ":AI:technical:plur:evomap:"
    effort: "0:45"
    context: "DIP-0027 §0 gates this DIP on a measurable lift signal but the spike-evaluation harness doesn't yet exist. Need: (1) baseline PLUR-only LongMemEval Hit@10 number, (2) instrumented Evolver-integrated variant, (3) decision criteria document. Without this, §0 is unenforceable."
  - heading: "Reach out to EvoMap maintainers re: co-authoring DIP-0027 envelope schema"
    tags: ":AI:partnerships:plur:"
    effort: "1:00"
    context: "Cold/warm intro to evomap.ai maintainers. Pitch: shared validation envelope (DIP-0027 draft attached) as neutral interop spec. Test their appetite before investing in joint schema work. Time-box to 1h: short message, one follow-up, no campaign."
  - heading: "Audit DIP-0019 §8 exchange packet format for envelope-compatibility"
    tags: ":AI:technical:datacore:"
    effort: "2h"
    context: "DIP-0027 §6/§7 assumes PLUR exchange packets can carry an envelope alongside the legacy native form. Verify the existing LEP-* packet format permits this additive change without breaking learning-publisher/learning-subscriber agents. Report: compatibility status and migration cost."
```
