# DIP-0049: Module Tool Loading Architecture

| Field | Value |
|-------|-------|
| **DIP** | 0049 |
| **Title** | Module Tool Loading Architecture |
| **Author** | @datacore-one |
| **Type** | Standards Track |
| **Status** | Draft |
| **Created** | 2026-08-16 |
| **Updated** | 2026-09-13 |
| **Tags** | `modules`, `mcp`, `tools`, `esm`, `bundling`, `health-check`, `symlinks` |
| **Affects** | `.datacore/modules/*/tools/`, `datacore-mcp/src/modules.ts`, `module.yaml` |
| **Specs** | DIP-0022 (Module Specification) |
| **Agents** | `create-module`, `system-evolver` |

## Summary

Module tools (`.datacore/modules/*/tools/index.js`) cannot reliably resolve `node_modules` at runtime because Node.js ESM resolves imports relative to the physical location of the source file, not the MCP server root. The current workaround — a `package.json` + manual `npm install` at `.datacore/modules/` — is fragile and not installed on any machine by default. This DIP formalises how module tools declare npm dependencies, establishes a policy on bundled vs. ESM-loaded tools, defines symlinked module handling, and mandates health-check reporting for tool load failures.

## Motivation

### The ESM Resolution Problem

The MCP server loads module tools via dynamic `import()`:

```typescript
// src/modules.ts  (datacore-mcp)
const toolsIndexPath = path.join(mod.modulePath, "tools", "index.js")
const toolsModule = await import(toolsIndexPath)
```

When Node.js resolves a bare specifier (`import { z } from 'zod'`) inside a dynamically imported file, it walks up the directory tree from the **physical disk path** of that file — not from the MCP server binary. A module tool at `.datacore/modules/crm/tools/index.js` therefore looks for `node_modules` starting at `.datacore/modules/crm/tools/`, then `.datacore/modules/crm/`, then `.datacore/modules/`, then `.datacore/`, and so on. It does **not** find `zod` or `js-yaml` inside `/usr/lib/node_modules/@datacore-one/mcp/node_modules/` even though both packages are bundled there.

Reproduction:

```bash
# This fails even though the MCP server ships zod
node --input-type=module \
  -e "import '/home/gregor/Data/.datacore/modules/crm/tools/index.js'"
# → ERR_MODULE_NOT_FOUND: Cannot find package 'zod' imported from
#     /home/gregor/Data/.datacore/modules/crm/tools/index.js
```

The MCP server itself does not fail — it bundles zod via esbuild at build time into `dist/index.js`. Module tools are **not** bundled; they are plain ESM files loaded at runtime.

### The Current Workaround and Why It Is a Gap

A `package.json` exists at `.datacore/modules/package.json`:

```json
{
  "name": "@datacore-one/modules-deps",
  "description": "Shared runtime deps for Datacore modules' tools/index.js.",
  "type": "module",
  "dependencies": { "js-yaml": "^4.1.0", "zod": "^3.25.76" }
}
```

This makes Node's ESM resolution succeed when `.datacore/modules/node_modules/` has been populated via `npm install`. However:

1. **Not installed by default.** Nothing in the setup flow (DIP-0005, `datacore-mcp` install) runs `npm install` here. Fresh machines have no `node_modules` and all module tools silently fail to load.
2. **Invisible to module authors.** A module's `module.yaml` has no field to declare npm dependencies. There is no contract — what belongs in this shared package is tribal knowledge.
3. **Version conflicts.** All modules share one set of packages. A module needing `zod@4.x` and another needing `zod@3.x` cannot coexist.
4. **Symlinked modules break.** A symlinked module (`health -> ../../2-datacore/2-projects/datacore-health`) may have its own `package.json` and `node_modules` at its physical path. Node ESM resolves against the real path (post-symlink), which can succeed or fail depending on whether the target project has run `npm install`. When it fails, the error is invisible — the load silently throws and the tool is skipped.
5. **Health check blindspot.** `datacore_modules_health` catches `tools/index.js does not exist` and per-tool handler mismatches, but does not detect silent import errors or report which tools failed to register.

### The Correct Long-Term Architecture

The `@datacore-one/mcp` server controls the runtime. Module tools should only import packages that the MCP server provides, or they should be **self-contained bundles**. The current ad-hoc shared `node_modules` directory is neither — it is an undocumented side-channel that breaks across environments.

## Specification

### §1. Module npm Dependency Declaration

Modules that provide tools (`provides.tools`) and require npm packages **must** declare them in `module.yaml`:

```yaml
provides:
  tools:
    - name: lookup
      description: Look up a contact by name
      handler: tools/index.js

tool_deps:
  runtime:
    zod: "^3.25.0"     # Example module requirement; verify the selected provider (§2–§4)
    js-yaml: "^4.1.0"  # A declared range is not an installed dependency
  bundled: {}           # Package → range map for dependencies included in the bundle (§3)
```

**Schema additions to `module.yaml` (DIP-0022 amendment):**

```yaml
# Top-level key, parallel to provides:
tool_deps:
  runtime:
    # Packages required in the explicitly installed module environment or
    # qualified host-provider binding. Validate actual resolved versions.
    # Map of package-name → semver range.
    <package-name>: "<semver-range>"
  bundled:
    # Packages bundled into the compiled tools/index.js.
    # These do not need to be present in any external node_modules.
    # Listed for documentation and audit purposes only.
    <package-name>: "<semver-range>"
```

Both `runtime` and `bundled` are optional maps. Omitting `tool_deps` entirely is valid for modules whose tools have zero npm dependencies (Python-delegate-only tools like the GTD module's `org_workspace_adapter.py` pattern).

**Rule**: Every `runtime` dependency must be supplied by the declared module or
host-provider profile. A listed build command alone does not establish that a
dependency was bundled or that a runtime import is satisfied.

### §2. MCP Server-Provided Package Contract

The `@datacore-one/mcp` server may expose these packages through its qualified
runtime export. Modules still require the explicit package binding in §4:

| Package | Version | How Provided |
|---------|---------|-------------|
| `zod` | Selected release manifest | Installed release export, reachable only through an explicit package resolution path (§4) |
| `js-yaml` | Selected release manifest | Installed release export, reachable only through an explicit package resolution path (§4) |

The MCP server README and `datacore_modules_health` output must list the current provided-package versions so module authors know what is available without checking the binary.

**Versioning guarantee**: The host-provided set is additive. Removing a package requires a major version bump of `@datacore-one/mcp`.

### §3. Bundled Module Tools (Recommended for New Modules)

Modules with complex dependencies or version requirements **should** pre-bundle their `tools/index.ts` into a self-contained `tools/index.js` using esbuild or tsup. This eliminates all runtime resolution problems:

```bash
# In the module's own build step (run once, commit the output)
esbuild tools/index.ts \
  --bundle \
  --platform=node \
  --format=esm \
  --outfile=tools/index.js \
  --external:fs \      # Node built-ins are always external
  --external:path \
  --external:child_process \
  --external:util
```

**When to bundle vs. use runtime deps:**

| Scenario | Approach |
|----------|----------|
| Module uses only `zod` + `js-yaml` (MCP-provided) | Declare compatible ranges and install/verify the §4 package binding, or bundle |
| Module uses any npm package beyond the MCP-provided set | Bundle everything into `tools/index.js` |
| Module is an in-development project (symlinked) | Bundle at project build time; compiled output is what the MCP server loads |
| Module's tools call only Python/shell adapters (no npm imports) | Neither runtime nor bundled — omit `tool_deps` |

**Bundled tools** must commit the compiled `tools/index.js` to source control. The source `tools/index.ts` (if any) is for authoring; the compiled `tools/index.js` is the deployable artifact. The module's `.gitignore` should NOT exclude `tools/index.js`.

### §4. Explicit ESM Package Resolution

A package export does not make a package globally discoverable. Node first
resolves `@datacore-one/mcp` from the importing module's location; only after
that succeeds does it resolve the `./runtime` export. A global npm installation
or a bundled server binary alone does not provide that first resolution step.
`NODE_PATH` is not used for ESM imports. See the
[Node ESM resolution documentation](https://nodejs.org/api/esm.html#no-node_path).

A supported release must choose and qualify one of these installation models:

1. Build a module bundle from its own declared lockfile. Record remaining
   external, native and dynamically loaded dependencies; a bundle is not proof
   that none remain.
2. Install the module's declared dependency environment, or explicitly bind its
   module-local package path to an integrity-checked, administrator-owned MCP
   provider release. Verify the binding from the physical module directory and
   actual service identity, including symlinked modules. This permits the
   `@datacore-one/mcp/runtime` export without an ambient global lookup assumption.

The re-export remains additive:

```javascript
import { z, yaml } from '@datacore-one/mcp/runtime'
```

This example is valid only after the package binding above is installed. It
must not be prescribed as a source-only fix for an unresolved import. The
provider version, module requirement ranges, effective package location and
file integrity belong to the deployment manifest. An unavailable binding is a
failed registration, not a reason to fetch packages or use unrelated globals
while processing a request.

Verification must include an unrelated clean module directory where the bare
import fails without a binding, the same module succeeding with the declared
binding, and the final installed service repeating that result with external
network access denied. ESM and CommonJS exports need separate artifact checks.

### §5. Symlinked Module Handling

A symlinked module is a directory entry in `.datacore/modules/` that is a filesystem symlink to an external project (example: `health -> ../../2-datacore/2-projects/datacore-health`). This is the standard workflow for developing a module in-tree before publishing it.

**Current behavior**: `discoverModules()` follows the symlink transparently via `readdirSync`. Node.js ESM resolves imports relative to the symlink's **real path** (the target). If the target project has its own `node_modules`, those are found; if not, resolution fails.

**Specification**:

1. **Symlinked modules must use a qualified artifact and dependency environment** (§3–§4). A bundle is preferred, but an explicit module-local binding is also valid. Resolution must be checked from the physical target, not inferred from the symlink location.

2. **`discoverModules()` must detect symlinks and annotate them**:
   ```typescript
   const stat = fs.lstatSync(modulePath)  // lstat, not stat
   const isSymlink = stat.isSymbolicLink()
   const realPath = isSymlink ? fs.realpathSync(modulePath) : modulePath
   modules.push({ ..., isSymlink, realPath, modulePath })
   ```
   `modulePath` remains the symlink path (used for UI display). `realPath` is used for all `import()` calls to avoid double-resolution ambiguity.

3. **Health check for symlinked modules** (see §6) must report:
   - Whether the target path exists
   - Whether `tools/index.js` is present at the real path
   - A `symlink_target` field in the health output

4. **Symlink presence and file size cannot prove bundling or portability.** Health reports actual registration evidence and the target path. Deployment qualification records which external dependencies remain; absence of that evidence is unverified, while a failed required import is an error.

### §6. Health Check Reporting for Tool Registration

The startup loader is the canonical execution path. It records a fresh
registration snapshot keyed by the full installed module context (space/global
scope and source location), rather than the manifest name alone. Two spaces may
install the same module without sharing failure state or a data destination.

For each declared tool, registration checks the callable name, handler,
argument schema and collisions with other advertised tools. The execution path
must enforce the same argument contract. Installed Zod 3 and Zod 4 schemas and
supported raw JSON Schema representations must either be validated correctly or
explicitly refused; accepting a representation cannot disable validation.

A health request inspects this snapshot. It does not independently import the
module, equate an unused named export with a registered array tool, or execute a
second loading path. Missing startup evidence is unverified. Failed imports and
missing registrations cannot produce a healthy result. Ambiguous name-only
selection must request a scoped selection or return the complete scoped report.

Diagnostics contain error categories and module identity, never raw exception
text, source excerpts, credentials or provider response bodies. The same rule
applies to stderr, MCP logging notifications and persisted benchmarks. Dependency
errors may recommend reconciliation of the installed module and dependency
profile, but cannot automatically expand package access.

An example scoped failure is:

```json
{
  "name": "crm",
  "scope": "space",
  "space": "example",
  "status": "error",
  "issues": [{
    "severity": "error",
    "code": "TOOLS_LOAD_FAILED",
    "message": "Tool registration failed at startup (dependency-unavailable)."
  }]
}
```

### §7. Declared Dependency Compatibility

The proposed `tool_deps.runtime` contract must compare each declared range with
the actual resolved package version in the selected module environment. Package
name membership alone is insufficient. An unmet required range is a registration
failure; an unexamined package location remains unverified. Distinct module
bundles or environments may satisfy incompatible ranges independently.

Omitting `tool_deps` preserves legacy loading compatibility but does not prove
that the module has no dependencies. Qualification must inspect and exercise the
installed artifact. Completing this declaration/enforcement feature remains
proposed work while this DIP is Draft; it is not a current conformance claim.

### §8. Setup and Installation

Install dependencies from declared, integrity-checked lockfiles into a new build
or service environment before startup. Use `npm ci --ignore-scripts`; explicitly
review and execute required native build steps in the isolated build context.
Verify the final artifact, resolved packages, runtime version and service
identity before selecting the release. Do not run an unversioned global install
or an automatic `npm install` while initializing MCP or handling tool calls.

Existing `.datacore/modules/package.json` environments are legacy installations
to inventory and reconcile without deleting user data. An environment is not
qualified merely because it happens to resolve an import on one machine. Keep
it until replacement module artifacts, package bindings and rollback procedures
have been verified. The setup wizard must not claim this migration is already
implemented solely because `./runtime` exists in package exports.

## Rationale

### Why Not Load Tools via Require + Commonjs?

CJS `require()` honours `NODE_PATH`. Converting all module tools to CJS would solve the resolution problem without bundling. Rejected because: (a) the ecosystem is moving to ESM, (b) `type: "module"` in the modules `package.json` breaks CJS semantics for all files under it, and (c) mixing CJS/ESM in the same tool directory creates confusion for module authors.

### Why Not Inject `node_modules` Path via `--experimental-vm-modules`?

VM modules require Node.js flag opt-in and different import semantics. Rejected: adds deployment complexity, breaks module tools that use top-level `await`.

### Why Prefer Bundling Over a Shared `node_modules`?

A single shared `node_modules` at `.datacore/modules/` works only when:
- All modules agree on the same version of every package.
- The user has run `npm install` at exactly that path.
- Symlinked modules do not shadow packages with different versions.

Bundling eliminates all three constraints. Each module carries its own closure. This mirrors how the MCP server itself is distributed (as a single compiled `dist/index.js`).

### Why Not Spawn Each Module Tool as a Subprocess?

Subprocess spawning would give each tool isolated `node_modules` (via a per-module `package.json`). Rejected: (a) latency per tool call would be significant, (b) `ModuleToolContext` would need IPC serialisation, (c) the MCP tool surface is already designed around in-process async handlers.

## Backwards Compatibility

- Preserve existing qualified module behavior. An installed shared `node_modules` is not sufficient evidence of compatibility: verify actual versions, resolution and schemas before an upgrade.
- The proposed `tool_deps` field is optional for legacy modules. Omission does not establish absence of dependencies or a self-contained bundle.
- The `@datacore-one/mcp/runtime` re-export is **additive**. Existing tools importing from `'zod'` directly continue to work where `node_modules` is installed; they just emit a deprecation warning in `datacore_modules_health` once DIP-0049 is implemented.
- The health check changes turn previously silent failures into reported errors. Some installations that appeared healthy will now report errors. This is intentional — they were silently broken before.

## Security Considerations

- Bundling can reduce ambient dependency lookup, but native modules, external imports and dynamic loads still require inspection. Bundling does not establish an OS or credential boundary; in-process modules remain trusted code within the MCP service context.
- Symlinked modules whose real paths are outside `DATACORE_ROOT` should be flagged by `checkModule` as an informational note (they are legitimate for development but unexpected in production).
- The `@datacore-one/mcp/runtime` re-export exposes the MCP server's own copies of `zod` and `js-yaml`. This is safe — both are non-networked, pure utility libraries.

## Implementation

### Phase 1: Health Check Fixes (Immediate — No Breaking Changes)
- [ ] Fix silent `catch {}` in `checkModule` → report `TOOLS_LOAD_FAILED` errors
- [ ] Add symlink detection (`lstatSync`) to `scanModulesDir`
- [ ] Report symlink targets and actual registration evidence without a file-size bundling heuristic
- [ ] Add `hint` field to error output with DIP-0049 link

### Phase 2: Runtime Re-Export and Explicit Package Binding
- [ ] Add `exports["./runtime"]` to `@datacore-one/mcp/package.json`
- [ ] Create `src/runtime.ts` re-exporting `zod` and `js-yaml`
- [ ] Update `create-module` agent: scaffold new tools using `@datacore-one/mcp/runtime`
- [ ] Add `tool_deps` schema to module.yaml DIP-0022 spec
- [ ] Migrate existing built-in module tools (gtd, crm, meetings, etc.) to `@datacore-one/mcp/runtime`

### Phase 3: Bundled Tools Rollout (Medium-Term)
- [ ] Document esbuild/tsup build step in `create-module` scaffolding
- [ ] Add `provides.tools[*].build` optional field to module.yaml for documenting build command
- [ ] Update `datacore_modules_health` to flag unbundled tools with `runtime` deps as warnings
- [ ] All community modules adopt bundled approach on next major version

### Phase 4: Deprecate Shared `node_modules` (Long-Term)
- [ ] All built-in modules use runtime re-export or are bundled
- [ ] Remove `.datacore/modules/package.json` (or downgrade to documentation-only)
- [ ] Retire the legacy shared environment only after qualified replacements are deployed

## Resolved Audit Questions and Remaining Proposed Work

The 2026-09-13 audit resolves these design ambiguities:

- File size is not evidence of dependency completeness. Use build manifests,
  dependency inspection and installed-runtime checks.
- Required dependency ranges apply to actual resolved versions, not package
  names or optimistic compatibility assumptions.
- A bare re-export import needs a module-visible package binding. `NODE_PATH`
  and global npm installation cannot supply an ESM guarantee.
- Symlink targets may be external in authorized development arrangements, but
  qualified production code and dependencies must remain immutable to workers.

The declaration schema, installer automation and fleet-wide module migration
remain proposed/deferred while this DIP is Draft. Existing MCP code includes a
runtime export and some health/symlink reporting; that is partial implementation,
not proof that all guarantees in this draft are deployed.

Read-only delegates may reuse the runtime's `findPython()` selection. An invalid
explicit `DATACORE_PYTHON` must fail without selecting another interpreter. The
delegate's executable path belongs to the installed module, never the data root
or tool arguments. Requests, outputs and subprocess lifetimes must be bounded;
the child receives only its required environment. Invalid evidence, missing
dependencies and execution failures must remain failed tool calls, without raw
source values in model-facing diagnostics. A Python version probe alone does
not establish dependency compatibility or a security boundary.

## Audit Change Record — 2026-09-13

**Previous requirement:** §4 described an always-resolvable global re-export;
§6 reproduced raw import errors and inferred bundling from a 20 KB threshold;
§7 checked dependency names without enforcing the claimed ranges; §8 prescribed
mutable installation during setup. Several self-references incorrectly used
DIP-0028, which is the separate Draft Capture Endpoint Contract.

**Problem and reason:** Source exports do not establish ESM package reachability;
exception text can carry credentials; byte count cannot prove dependency closure;
name membership does not prove compatible versions. These are specification
defects and ambiguities, independently checked against Node resolution behavior
and synthetic MCP registration failures.

**Corrected requirement:** Explicit installed package resolution, qualified
versioned artifacts, context-scoped registration evidence, validation on both
schema paths, content-free diagnostics and no request-time installation.

**Implementation impact:** MCP registration and health share one snapshot;
Zod upgrades preserve older installed schemas; raw JSON Schema contracts are
enforced. The runtime export remains available with an explicit package binding.

**Compatibility impact:** Existing qualified modules and data are retained.
Unsafe implicit lookup and false health success are not compatibility promises.
Draft status is unchanged; no future feature is silently declared implemented.

**Tests affected:** Module resolution with and without a local binding; real
ESM/CommonJS artifacts; scoped failure isolation; raw-diagnostic canaries;
Zod 3/4 and JSON Schema rejection; restart and installed-dependency checks.

**Runtime/deployment impact:** Reconcile and verify selected module/package
paths in each service context before cutover. This source amendment alone does
not close runtime isolation or dependency drift findings.

### Shared reader follow-up — 2026-09-13

**Previous requirement:** The runtime export supplied package bindings without a
shared interpreter selection contract. Venture tools independently parsed data.

**Problem:** Agent tools could omit retained hypothesis layouts, read a different
configured source, infer a venture from ambiguous directory suffixes or disclose
parser values. Different surfaces could therefore make inconsistent decisions.

**Corrected requirement and reason:** Use installed canonical evidence readers
and explicit failure/selection semantics above so tools observe the evidence
used by orchestration. This extends the proposed DIP-0009 evidence amendment;
it does not promote either proposal to implemented/audited status.

**Implementation impact:** MCP exposes its existing interpreter selector in
both runtime formats. Ventures delegates its four read-only tools through a
bounded isolated Python invocation, sharing discovery, configuration, hypothesis
and budget readers. No request-time dependency installation or data-root import.

**Compatibility impact:** Tool names remain stable. Unique historical selectors
remain valid; ambiguous inventories require reconciliation. The installed MCP
package must actually expose the new helper; a version label alone is no proof.

**Tests affected:** Real ESM/CommonJS exports, explicit interpreter failure,
configured sources, mixed layouts, nested spaces, ambiguous selectors, aliases,
malformed input, source diagnostic canaries and data-directory code substitution.

**Runtime/deployment impact:** Install and qualify matching core, Ventures,
Python dependencies and MCP artifacts before activation. Local tool integration
does not establish OS isolation or active fleet conformance.

### Compatibility clarification — 2026-09-14

This Draft does not require renamed module callables or migration of valid
user-space data. DIP-0022 defines default names and one selected canonical data
context with space > personal > global code precedence. Multi-scope names require
`DATACORE_SCOPED_MODULE_NAMES=1`; the default is `0`. Health may report an installed
module as not selected or overridden without claiming that its handlers loaded.
Installed Python/core coupling in full MCP mode requires matched deployment
qualification; the naming option does not remove that dependency. No draft
rollout is newly declared implemented or audited by this clarification.
