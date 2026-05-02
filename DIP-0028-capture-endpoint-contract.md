# DIP-0028: Capture Endpoint Contract

| Field | Value |
|-------|-------|
| **DIP** | 0028 |
| **Title** | Capture Endpoint Contract |
| **Author** | Gregor |
| **Type** | Standards Track |
| **Status** | Draft |
| **Created** | 2026-05-01 |
| **Updated** | 2026-05-01 |
| **Tags** | `lens`, `capture`, `http`, `wire-format`, `observability`, `interface-contract` |
| **Depends On** | DIP-0027 (Behavioural Observation Architecture — sibling, storage side) |
| **Affects** | `.datacore/modules/lens/`, `2-datacore/2-projects/datacore-app/`, browser extensions, future iOS/Cursor adapters |
| **Specs** | `.datacore/modules/lens/lib/server.py` (reference implementation) |
| **Related DIPs** | DIP-0010 (External Sync Architecture), DIP-0018 (Credential Management), DIP-0027 (Behavioural Observation Architecture), DIP-0026 (Architectural Primitives) |

> **Numbering note**: The originating brief reserved DIP-0024 for this contract. By the time this draft was written, both DIP-0023 (Messaging Module) and DIP-0024 (Reactive Hooks Infrastructure) had been claimed. This contract DIP is therefore DIP-0028; its sibling Behavioural Observation Architecture DIP is DIP-0027.

## Summary

This DIP defines the HTTP wire format for behavioural-observation capture across Datacore modules and external clients. It establishes the endpoint shape (`POST /api/lens/events`), bearer-token authentication with auto-generated tokens at well-known paths, a token-discovery proxy pattern for sandboxed clients, the localhost-only CORS policy, and a structured failure-mode taxonomy.

This DIP is the sibling of the Behavioural Observation Architecture DIP. The architecture DIP specifies the storage model (disciplined-core schema, Tier-1 raw preservation, redaction policy, source enablement). This DIP specifies the on-the-wire contract for getting events into that store from external processes. Together they form the capture stack: storage on one side, ingest contract on the other.

## Motivation

Datacore is multi-process by design and increasingly so:

- The Datacore desktop app's webview runs sandboxed — it cannot read disk, cannot open SQLite, cannot import Python.
- Browser extensions need a way to emit events from web content. The web content has no filesystem access by definition.
- External tools (a future Cursor adapter, an iOS app, third-party integrations from partner spaces) want to contribute behavioural events into the same store.
- Even within the desktop app, the daemon and the lens runner are separate processes with independent lifecycles.

The Python `lens.capture()` function is fine for in-process callers but useless for any of the above. Without a stable wire-format DIP, each client invents its own auth model, its own request shape, its own failure-handling. The result is brittle integration, inconsistent guarantees, and a steady accumulation of one-off adapters that have to be updated whenever anything changes.

The reference implementation already exists (`.datacore/modules/lens/lib/server.py` — FastAPI + uvicorn, bound to loopback, bearer-token auth, redaction-aware). This DIP elevates that implementation into a contract: any client that follows it can speak to any DIP-compliant capture server, today or in the future.

### Why a separate DIP from the architecture DIP

The architecture DIP and the contract DIP have different audiences and different change cadences:

- **Architecture (sibling DIP)**: Read by people building or extending the storage layer — schema authors, redaction-policy maintainers, source authors. Changes when the storage model evolves.
- **Contract (this DIP)**: Read by people writing clients — frontend engineers, extension authors, external integrators. Changes when the wire format evolves.

Splitting them lets the storage layer evolve internally (new tables, new redaction strategies, new source plugins) without forcing every client to re-read a giant document. And it lets the wire format add fields, batching strategies, or compression without dragging the storage spec along.

## Specification

### 1. Endpoint shape

The capture server exposes four HTTP endpoints, all rooted at `/api/lens/` except for `/health`.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/health` | none | Liveness probe — confirms server is up and responding |
| `POST` | `/api/lens/events` | bearer | Single-event or batched event ingest |
| `GET` | `/api/lens/status` | bearer | Capture stats (today/week/lifetime counts, source enable state, redaction failures) |
| `GET` | `/api/lens/sources` | bearer | Per-source enabled state for UI toggles |

#### 1.1 Request body — `POST /api/lens/events`

The request body is either a single event object or a batch wrapper.

**Single-event shorthand:**

```json
{
  "event_type": "app_ui.click",
  "actor": "user",
  "surface": "app_ui",
  "target_id": "task-abc",
  "metadata": {
    "target_type": "task_row",
    "action": "click",
    "label": "Mark done"
  }
}
```

**Batch wrapper:**

```json
{
  "events": [
    { "event_type": "app_ui.click", "actor": "user", "surface": "app_ui", ... },
    { "event_type": "app_ui.scroll", "actor": "user", "surface": "app_ui", ... }
  ]
}
```

Server normalises the single-event form to a list internally. Clients may send either; the response shape is always the batched form.

**Field semantics:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `event_type` | string | yes | Dotted namespace, e.g. `app_ui.click`, `cursor.edit`, `web.tab_open` |
| `actor` | string | yes | `"user"` or `"agent"`; reserved for future actor types |
| `surface` | string | yes | The source/surface that produced the event (`app_ui`, `cursor`, `web`, etc.) |
| `target_id` | string \| null | no | Stable identifier of the thing acted upon, when meaningful |
| `metadata` | object \| null | no | Surface-specific structured payload; subject to redaction policy |

The disciplined-core schema (defined in the Behavioural Observation Architecture DIP) governs which `(surface, event_type)` pairs are valid. The contract here only defines the envelope — the schema check happens server-side.

#### 1.2 Response body — `POST /api/lens/events`

Always returns 200 OK with a structured per-event result. Network-level success does NOT imply per-event success — clients must read the body.

```json
{
  "accepted": 2,
  "rejected": 1,
  "results": [
    {"status": "ok",                "event_id": 12345, "raw_event_id": 67890, "errors": null},
    {"status": "ok",                "event_id": 12346, "raw_event_id": 67891, "errors": null},
    {"status": "redaction_failed",  "event_id": null,  "raw_event_id": 67892, "errors": "secret_detected"}
  ]
}
```

`results` is index-aligned with the input event list. `event_id` is the disciplined-core row id; `raw_event_id` is the Tier-1 raw row id. Either may be null depending on outcome (see failure taxonomy below).

#### 1.3 `GET /api/lens/status`

Returns aggregate capture stats. Used by the desktop app's settings panel and by health monitoring.

```json
{
  "capture_active": true,
  "last_event_age_seconds": 12,
  "today": 247,
  "week": 1812,
  "lifetime": 9043,
  "sources_enabled": [
    {"source": "app_ui", "today": 180},
    {"source": "cursor", "today": 67}
  ],
  "sources_disabled": ["web", "shell"],
  "redaction_failures_today": 0,
  "top_event_types_today": [
    {"type": "app_ui.click", "count": 142},
    {"type": "app_ui.scroll", "count": 38}
  ]
}
```

#### 1.4 `GET /api/lens/sources`

Returns the source-enablement state, primarily for UI toggles.

```json
{
  "sources": [
    {"source": "app_ui", "enabled": true,  "events_today": 180},
    {"source": "cursor", "enabled": true,  "events_today": 67},
    {"source": "web",    "enabled": false, "events_today": 0}
  ]
}
```

### 2. Authentication

All endpoints except `/health` require a bearer token in the `Authorization` header:

```
Authorization: Bearer 6d3f...e2b1
```

#### 2.1 Token storage

The token lives at a well-known path:

```
~/.datacore/lens/auth/token
```

On first server start, if the file does not exist, the server generates a 32-byte hex token (`secrets.token_hex(32)`), writes it with mode 0600, and uses it for the lifetime of the process. Subsequent starts read the existing token. This means tokens persist across restarts unless explicitly rotated by deleting the file.

#### 2.2 Verification

The server uses constant-time compare (`secrets.compare_digest`) when checking presented tokens. Any mismatch returns 401. A missing or malformed `Authorization` header also returns 401. If the server somehow has no token loaded (lifecycle bug), it returns 503 with `lens server token not initialised`.

#### 2.3 Why bearer over other schemes

- **Loopback-only bind** makes mTLS overkill — there is no network-level adversary on the local interface.
- **No browser cookies** — the desktop app's webview is not a real browsing context, and we want the same token to work for non-browser clients (CLI tools, Python scripts).
- **Token in file, not env** — env vars leak through process listings, shell history, and child processes. A 0600 file under `~/.datacore/` is the same trust boundary as the rest of Datacore's secrets.

### 3. Token discovery for sandboxed clients

The token-on-disk model fails for clients that cannot read the filesystem — most notably the Datacore desktop app's frontend running inside a Wails webview. Such clients need a discovery channel.

#### 3.1 Daemon proxy pattern

The Datacore-app daemon (which already exposes its own authenticated HTTP API to the frontend) proxies a single auth lookup:

```
GET /lens/auth   (daemon-side path, daemon-side bearer auth)
```

Returns:

```json
{"token": "6d3f...e2b1", "port": 51717}
```

The frontend authenticates to the daemon via its existing daemon-token mechanism, calls this endpoint once on bootstrap, then talks to the lens server directly using the returned bearer + port for the rest of its lifetime.

#### 3.2 Why a proxy and not a shared secret

The lens server lifecycle is independent of the daemon lifecycle. The lens may restart (token unchanged), the daemon may restart (token unchanged), or both may restart in either order. A shared-secret approach would couple their startup; the proxy approach is purely a lookup at request time and does not couple lifecycles.

The frontend pays one extra round-trip on app start. After bootstrap, frontend → lens traffic is direct.

#### 3.3 Compliance for non-Datacore-app clients

Sandboxed clients outside the Datacore-app (a third-party browser extension, a future iOS app) must implement their own discovery channel — typically a settings UI where the user pastes the token they read from `~/.datacore/lens/auth/token`. The server contract does not change; only the client's bootstrap differs.

### 4. CORS policy

The server explicitly enumerates allowed origins. Wildcards are rejected — localhost-only is structural, not a default.

**Allowed origin regex:**

```
^(http://(127\.0\.0\.1|localhost)(:\d+)?|wails://wails(:\d+)?|https?://wails\.localhost(:\d+)?)$
```

This covers:
- `http://127.0.0.1` and `http://localhost`, any port — for local dev tools
- `wails://wails` — the Wails webview's native scheme on macOS
- `http://wails.localhost` and `https://wails.localhost` — the Wails webview's resolved scheme on Windows/Linux

**Allowed methods:** `GET`, `POST`, `OPTIONS`
**Allowed headers:** `Authorization`, `Content-Type`

A wildcard origin (`*`) would let any web page in the user's browser POST events to the local server if the bearer were ever leaked. The enumerated list keeps the blast radius bounded.

### 5. Bind policy

The server binds to `127.0.0.1` only. Never `0.0.0.0`. Default port 51717 (configurable via `--port` to the runner).

The active port is written to a discoverable file:

```
~/.datacore/lens/auth/port
```

…so clients that don't know the port can read it. Combined with the token at the sibling path, a non-sandboxed client can fully bootstrap with just two file reads.

Loopback-only bind means the server is unreachable from any other machine on the network — even if a misconfigured firewall would otherwise expose it. This is non-negotiable: behavioural data is sensitive by definition, and a misconfigured router on a coffee-shop wifi must not leak it.

### 6. Failure-mode taxonomy

All capture failures return 200 OK at the HTTP level with a structured `status` per event. Clients distinguish outcomes by parsing the response, not by HTTP status. This is intentional: a partial-success batch should not look like a transport error.

| `status` value | Meaning | event_id | raw_event_id | Client action |
|----------------|---------|----------|--------------|---------------|
| `ok` | Event accepted, written to disciplined-core and (if applicable) Tier-1 raw | set | set | None — done |
| `disabled` | Source not enabled in the store; event discarded silently | null | null | None — respect user preference |
| `validation_error` | Disciplined-core schema mismatch; raw still preserved (Tier-1) | null | set | Optional: log for client debugging |
| `redaction_failed` | Redaction couldn't safely scrub the payload; event NOT written anywhere | null | null | Optional: log; do not retry — same payload will fail again |
| `locked` | SQLite lock contention exhausted retries | null | null | Retry later with backoff |
| `internal_error` | Anything else | null | null | Log and surface to user if persistent |

The `errors` field contains a short machine-readable string when status is non-ok (e.g. `secret_detected`, `unknown_event_type`, `lock_timeout`).

#### 6.1 Why 200 on per-event failure

Two reasons. First, batches: returning 4xx because one event in a 100-event batch failed redaction would discard 99 valid events or force complex per-event retry logic. Second, fail-soft: capture is observation, not critical-path. A redaction failure is a privacy success, not a transport failure — the client should not retry, and treating it as a 4xx invites that.

The server still returns 4xx for transport-level problems: 401 (bad/missing auth), 422 (malformed body that doesn't even parse), 503 (server not ready). 500 is reserved for unexpected exceptions in the server itself.

### 7. Batch semantics

- **Single-event shorthand**: post the event object directly. Server normalises to a list of one.
- **Batch wrapper**: `{"events": [...]}`.
- **Independence**: each event in a batch is processed independently. One event's `redaction_failed` does not affect any other event in the batch.
- **Ordering**: events are processed in array order; `results` is index-aligned with the input.
- **No partial-write rollback**: there is no transaction across batch entries. Two events in the same batch may end up with one accepted and one rejected, and there is no rollback of the accepted one. Behavioural events are append-only observations — partial writes are not a problem.

There is no upper bound on batch size in the contract itself. Clients should keep batches under a few hundred events to avoid HTTP body-size limits and to make per-event redaction failures debuggable.

### 8. Client patterns

The contract does not mandate a particular client style — different surfaces have different needs.

| Client | Pattern | Rationale |
|--------|---------|-----------|
| Frontend (webview) | Batched flush every 5s, on-blur, on-pagehide via keepalive fetch | Webview can disappear at any moment; flush opportunistically |
| CLI tools | Synchronous one-shot per invocation | Short-lived; no need for batching |
| Long-running adapters (Cursor, browser ext) | Batched with backpressure (queue cap, drop-oldest if full) | Capture is fail-soft; never block the host process on the capture server |
| Tests / fixtures | Synchronous single-event | Determinism over throughput |

The keepalive-fetch pattern for `pagehide` is important for the webview: a browser may terminate the page before async work completes, but `keepalive: true` allows a small final POST to outlive the page. Use this for the last flush only — not for every flush.

## Compliance / Implementation guidance

A client is DIP-0028-compliant if it:

1. Uses bearer-token auth, fetched from `~/.datacore/lens/auth/token` (or via daemon proxy if sandboxed).
2. Hits `POST /api/lens/events` for capture, with either single-event or batch-wrapper body.
3. Parses the per-event `status` array and respects the `disabled` / `redaction_failed` outcomes — does not retry them.
4. Treats network-level failures (connection refused, timeouts) as fail-soft. Capture is observation, not critical-path. The host application must continue functioning if the capture server is down.
5. Never logs the bearer token or includes it in user-visible error messages.

### Reference implementations

| Layer | Path |
|-------|------|
| Server | `~/Data/.datacore/modules/lens/lib/server.py` (FastAPI + uvicorn) |
| Python client | `~/Data/.datacore/modules/lens/lib/lens_client.py` (stdlib only — vendorable into other projects) |
| TypeScript client | `~/Data/2-datacore/2-projects/datacore-app/frontend/lib/lens-client.ts` |
| React hook | `~/Data/2-datacore/2-projects/datacore-app/frontend/lib/hooks/useLensCapture.ts` |
| Daemon proxy | `~/Data/2-datacore/2-projects/datacore-app/daemon/datacored/api/lens.py` |

The Python client is intentionally stdlib-only so it can be vendored into any project (a CI script, a separate Datacore module, an external integration) without dragging FastAPI as a dependency.

## Rationale

### Why not gRPC?

gRPC would give us schema enforcement and code-gen for free. But it adds a dependency that browser extensions, simple shell scripts, and curl-from-the-terminal cannot satisfy. Plain HTTP + JSON is the lowest common denominator and works in every client environment we currently care about, including those we haven't anticipated yet.

### Why not Unix domain sockets?

UDS would eliminate the bind-policy concern entirely. But the desktop app's webview cannot speak UDS, browser extensions cannot speak UDS, and any cross-machine future (a remote capture aggregator) is foreclosed. Loopback HTTP gives us the same threat model as UDS in practice (anyone with local user access can connect either way) while being universally reachable.

### Why structured per-event status instead of HTTP status codes?

A 207 Multi-Status response would be the strictly correct HTTP idiom. In practice, 207 is poorly supported by HTTP libraries and surprises every client author. Returning 200 with a structured body is the pragmatic choice and matches the conventions of, e.g., GraphQL and most JSON-RPC services.

### Why a single endpoint and not one per event type?

Per-type endpoints would couple the URL space to the event taxonomy. The taxonomy lives in the disciplined-core schema (sibling DIP) and evolves frequently. A single endpoint with `event_type` as a body field decouples URL stability from schema evolution. New event types can be added without any URL changes; deprecated event types can be rejected via `validation_error` without breaking any client.

## Backwards Compatibility

This DIP describes a contract that has no prior version. The reference server is versioned (`X-Lens-Version` header in responses, currently `0.1.0`); future contract revisions will bump this and document migration.

For schema-evolution: the disciplined-core schema is owned by the sibling Behavioural Observation Architecture DIP. This DIP defers all schema-change semantics to that DIP. The wire format itself is stable.

## Security Considerations

- **Bearer in localhost traffic**: acceptable since bind is loopback-only. An attacker with local user access can also read the token file directly — the bearer is not a stronger boundary than the file system.
- **CORS allowlist**: explicit and structural. A change to allow non-localhost origins should be a DIP amendment, not a config tweak.
- **Token rotation**: not part of v1.0 — rotation is `rm ~/.datacore/lens/auth/token && restart`. Future revisions may add a rotation endpoint.
- **Redaction is server-side**: clients never see redacted payloads, only the `redaction_failed` status. Clients must not log raw event metadata thinking "redaction will catch secrets" — redaction can fail, and the client's logs are not redacted.
- **No PII in error strings**: server-side errors must never include the offending payload. The `errors` field is short and machine-readable for this reason.

## Open Questions

1. **Compression**: should the wire format support `Content-Encoding: gzip` for high-volume batches? The server framework supports it but no client uses it today. Defer to first concrete need.
2. **WebSocket alternative**: would a WebSocket channel reduce overhead for real-time low-latency capture (e.g. live cursor tracking)? Not in v1.0 — wait until a use case demands sub-100ms ingest latency.
3. **Schema evolution across versions**: how do clients on schema v1.0 interact with servers on schema v2.0? Likely answer: server accepts v1.0 events as long as they validate, returns `validation_error` for v2.0-only fields. Codify in a future schema-versioning DIP.
4. **Published JSON Schema**: should we publish a JSON Schema document for the event shape so external clients can validate before sending? Probably yes — generated from the FastAPI/Pydantic models. Tracking item, not blocking v1.0.
5. **Per-source rate limits**: the server has no rate limiting today. A noisy client could exhaust SQLite writes. Add when it bites.

## Implementation

### Reference Implementation

The lens HTTP server in `.datacore/modules/lens/lib/server.py` is the v1.0 reference. It implements every endpoint in this DIP, the bearer auth model, the CORS policy, the failure-mode taxonomy, and the batch semantics. The companion clients (Python, TypeScript, React hook, daemon proxy) demonstrate the four canonical client styles.

### Rollout Plan

This DIP describes an existing, deployed contract. Rollout is documentation-only:

1. Mark this DIP as Draft on creation (this commit).
2. Cross-link from the Behavioural Observation Architecture DIP.
3. Cross-link from the Datacore-app daemon and frontend READMEs.
4. Promote to Active once the sibling architecture DIP is also Active.

No code changes required. Future revisions bump `X-Lens-Version` and amend this DIP.

## References

- Reference server: `~/Data/.datacore/modules/lens/lib/server.py`
- Python client: `~/Data/.datacore/modules/lens/lib/lens_client.py`
- TypeScript client: `~/Data/2-datacore/2-projects/datacore-app/frontend/lib/lens-client.ts`
- React hook: `~/Data/2-datacore/2-projects/datacore-app/frontend/lib/hooks/useLensCapture.ts`
- Daemon proxy: `~/Data/2-datacore/2-projects/datacore-app/daemon/datacored/api/lens.py`
- DIP-0027 (Behavioural Observation Architecture) — sibling DIP, storage side
- DIP-0010 (External Sync Architecture) — adjacent pattern (cross-process data flow)
- DIP-0018 (Credential Management) — token-storage practices for `~/.datacore/lens/auth/`
- DIP-0026 (Architectural Primitives) — broader Datacore process-boundary patterns

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-05-01 | 0.1 | Initial draft. Codifies the existing lens HTTP server as a contract. Originally numbered 0024; renumbered to 0027 because 0023/0024 were claimed by other DIPs in flight. |
