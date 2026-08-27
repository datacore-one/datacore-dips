# DIP-0049: Module Tool Loading Architecture

| Field | Value |
|-------|-------|
| **DIP** | 0049 |
| **Title** | Module Tool Loading Architecture |
| **Author** | @datacore-one |
| **Type** | Standards Track |
| **Status** | Draft |
| **Created** | 2026-08-16 |
| **Updated** | 2026-08-16 |
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
    zod: "^3.25.0"     # Provided by MCP server — no install needed (see §2)
    js-yaml: "^4.1.0"  # Provided by MCP server — no install needed
  bundled: []           # Packages bundled into tools/index.js (see §3)
```

**Schema additions to `module.yaml` (DIP-0022 amendment):**

```yaml
# Top-level key, parallel to provides:
tool_deps:
  runtime:
    # Packages expected to be provided by the MCP server host environment.
    # Module declares which version range it needs; the MCP server validates
    # compatibility at startup. Map of package-name → semver range.
    <package-name>: "<semver-range>"
  bundled:
    # Packages bundled into the compiled tools/index.js.
    # These do not need to be present in any external node_modules.
    # Listed for documentation and audit purposes only.
    <package-name>: "<semver-range>"
```

Both `runtime` and `bundled` are optional maps. Omitting `tool_deps` entirely is valid for modules whose tools have zero npm dependencies (Python-delegate-only tools like the GTD module's `org_workspace_adapter.py` pattern).

**Rule**: A module MUST NOT declare `runtime` dependencies that the MCP server does not provide, unless it also lists a bundling step in `provides.tools[*].build`.

### §2. MCP Server-Provided Package Contract

The `@datacore-one/mcp` server declares a set of **host-provided packages** — packages that module tools may import without installing anything:

| Package | Version | How Provided |
|---------|---------|-------------|
| `zod` | `^3.x` or `^4.x` | Bundled in `dist/index.js`, re-exported via `NODE_PATH` injection (see §4) |
| `js-yaml` | `^4.x` | Bundled in `dist/index.js`, re-exported via `NODE_PATH` injection (see §4) |

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
| Module uses only `zod` + `js-yaml` (MCP-provided) | `runtime` declaration only — no bundling |
| Module uses any npm package beyond the MCP-provided set | Bundle everything into `tools/index.js` |
| Module is an in-development project (symlinked) | Bundle at project build time; compiled output is what the MCP server loads |
| Module's tools call only Python/shell adapters (no npm imports) | Neither runtime nor bundled — omit `tool_deps` |

**Bundled tools** must commit the compiled `tools/index.js` to source control. The source `tools/index.ts` (if any) is for authoring; the compiled `tools/index.js` is the deployable artifact. The module's `.gitignore` should NOT exclude `tools/index.js`.

### §4. MCP Server: NODE_PATH Injection (Implementation)

To make host-provided packages reachable from module tool files without bundling, the MCP server sets `NODE_PATH` before dynamic imports:

```typescript
// src/modules.ts — to be added
import * as path from 'path'
import { createRequire } from 'module'
import { fileURLToPath } from 'url'

// Resolve the MCP server's own node_modules directory
const MCP_NODE_MODULES = path.join(
  fileURLToPath(import.meta.url),
  '..', '..', 'node_modules'
)

// Inject before any dynamic import of module tools
async function loadModuleTools(modules: Module[], storage: StorageConfig) {
  // Prepend MCP node_modules to NODE_PATH so module tool imports resolve there
  const existing = process.env.NODE_PATH || ''
  process.env.NODE_PATH = existing
    ? `${MCP_NODE_MODULES}${path.delimiter}${existing}`
    : MCP_NODE_MODULES
  // Note: NODE_PATH affects require() but NOT ESM import() in Node.js 18+.
  // For ESM, the correct approach is --experimental-loader or importMap.
  // See §4.1 for the ESM-safe alternative.
  ...
}
```

> **§4.1 — ESM Constraint**: `NODE_PATH` does not affect ES module `import()` in Node.js 18+. The reliable mechanism for ESM is one of:
>
> a. **Module bundle** (§3 — recommended): the import is resolved at build time, not runtime.
>
> b. **`--conditions` / package exports re-export**: The MCP server exposes a re-export entry `@datacore-one/mcp/runtime` that re-exports `{ z, yaml }` from its bundled copies. Module tools import from this path instead of bare `zod`/`js-yaml`. This works because the re-export path is resolved relative to the MCP server's package, which Node can always find.
>
> The preferred short-term path is (b). The preferred long-term path is (a) bundled modules.

**Re-export entry (Option b):**

Module tools use:
```javascript
// Instead of: import { z } from 'zod'
import { z } from '@datacore-one/mcp/runtime'
import { yaml } from '@datacore-one/mcp/runtime'
```

The MCP server `package.json` adds:
```json
{
  "exports": {
    ".": "./dist/index.js",
    "./runtime": "./dist/runtime.js"
  }
}
```

Where `dist/runtime.js` re-exports from bundled copies:
```javascript
export { z } from 'zod'          // resolved from mcp's own node_modules
export * as yaml from 'js-yaml'  // resolved from mcp's own node_modules
```

Because the re-export is resolved from `/usr/lib/node_modules/@datacore-one/mcp/`, Node can always find it. This is the **preferred runtime-deps pattern** until bundled modules are the norm.

**Migration for existing module tools**: Replace `from 'zod'` → `from '@datacore-one/mcp/runtime'`.

### §5. Symlinked Module Handling

A symlinked module is a directory entry in `.datacore/modules/` that is a filesystem symlink to an external project (example: `health -> ../../2-datacore/2-projects/datacore-health`). This is the standard workflow for developing a module in-tree before publishing it.

**Current behavior**: `discoverModules()` follows the symlink transparently via `readdirSync`. Node.js ESM resolves imports relative to the symlink's **real path** (the target). If the target project has its own `node_modules`, those are found; if not, resolution fails.

**Specification**:

1. **Symlinked modules MUST use the bundled approach** (§3). Because the real path is in an arbitrary project directory, the MCP server cannot control its `node_modules` environment. Bundling is the only safe option.

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

4. **A symlinked module with unbundled tools (using bare `import 'zod'`) is a health WARNING**, not an error — it may work locally if the target project has `node_modules`, but it will not work on other machines.

### §6. Health Check Reporting for Tool Load Failures

The `datacore_modules_health` tool currently detects missing `tools/index.js` and undeclared handlers, but silently ignores import errors (the `catch {}` block in `checkModule`). This means a module whose tools fail to load reports status `ok` — a false green.

**Required changes to `checkModule`:**

```typescript
async function checkModule(mod: Module, storage: StorageConfig) {
  const issues: HealthIssue[] = []
  const warnings: HealthWarning[] = []

  // ... existing checks ...

  if (declaredTools.length > 0) {
    const toolsIndex = path.join(mod.realPath ?? mod.modulePath, 'tools', 'index.js')

    if (!fs.existsSync(toolsIndex)) {
      issues.push({
        severity: 'error',
        code: 'TOOLS_INDEX_MISSING',
        message: `Declares ${declaredTools.length} tools but tools/index.js not found`,
      })
    } else {
      let toolsModule: unknown
      let loadError: string | null = null

      try {
        toolsModule = await import(toolsIndex)
      } catch (err) {
        // CHANGED: was `catch {}` (silent)
        loadError = err instanceof Error ? err.message : String(err)
        issues.push({
          severity: 'error',
          code: 'TOOLS_LOAD_FAILED',
          message: `tools/index.js failed to import: ${loadError}`,
          detail: loadError,
          hint: loadError.includes('Cannot find package')
            ? 'Module tool imports a package not available at runtime. '
              + 'See DIP-0028 §3 (bundle the tool) or §4 (use @datacore-one/mcp/runtime).'
            : undefined,
        })
      }

      if (toolsModule && !loadError) {
        // existing handler validation ...
      }
    }
  }

  // Symlink-specific checks
  if (mod.isSymlink) {
    if (!mod.realPath || !fs.existsSync(mod.realPath)) {
      issues.push({
        severity: 'error',
        code: 'SYMLINK_TARGET_MISSING',
        message: `Symlink target does not exist: ${mod.realPath}`,
      })
    } else {
      const hasUnbundledTools = declaredTools.length > 0
        && !isLikelyBundled(path.join(mod.realPath, 'tools', 'index.js'))
      if (hasUnbundledTools) {
        warnings.push({
          severity: 'warning',
          code: 'SYMLINK_UNBUNDLED_TOOLS',
          message: 'Symlinked module with unbundled tools — may fail on other machines',
          hint: 'See DIP-0028 §5: symlinked modules must use bundled tools.',
        })
      }
    }
  }

  return {
    name: mod.manifest.name,
    status: issues.length > 0 ? 'error' : warnings.length > 0 ? 'warning' : 'ok',
    symlink: mod.isSymlink ? { target: mod.realPath } : undefined,
    issues,
    warnings,
  }
}

// Heuristic: a bundled file is typically >20 KB (includes all deps inline)
function isLikelyBundled(filePath: string): boolean {
  try {
    const stat = fs.statSync(filePath)
    return stat.size > 20_000
  } catch {
    return false
  }
}
```

**Health output format (amended):**

```json
{
  "name": "crm",
  "status": "error",
  "symlink": null,
  "issues": [
    {
      "severity": "error",
      "code": "TOOLS_LOAD_FAILED",
      "message": "tools/index.js failed to import: Cannot find package 'zod'",
      "hint": "Module tool imports a package not available at runtime. See DIP-0028 §3 or §4."
    }
  ],
  "warnings": []
}
```

### §7. Module.yaml Validation at Startup

On startup, `loadModuleTools` must validate `tool_deps.runtime` declarations against the server's provided-package manifest:

```typescript
const MCP_PROVIDED = {
  zod: '^3.x || ^4.x',
  'js-yaml': '^4.x',
}

for (const [pkg, range] of Object.entries(mod.manifest.tool_deps?.runtime ?? {})) {
  if (!MCP_PROVIDED[pkg]) {
    warnings.push(`Module '${mod.name}' declares runtime dep '${pkg}' `
      + `which is not provided by this MCP server version. `
      + `Bundle the tool (DIP-0028 §3) or remove the dep.`)
  }
}
```

Warnings are printed to stderr and included in `datacore_modules_health` output. They do not block loading — the `import()` is still attempted so that locally-installed `node_modules` can satisfy it.

### §8. Setup and Installation

The root `.datacore/modules/package.json` introduced as a workaround is **retained** but elevated to a documented installation step.

**DIP-0005 (Installation) amendment**: After `npm install -g @datacore-one/mcp`, users must run:

```bash
cd "$DATACORE_ROOT/.datacore/modules" && npm install
```

This satisfies `runtime` deps for any unbundled module tools that import `zod` or `js-yaml` directly. It is the short-term bridge while bundled modules become the norm.

The `datacore-mcp` setup wizard (`datacore-mcp --init`) will detect and run this automatically.

**Long-term**: once all built-in modules use `@datacore-one/mcp/runtime` or are bundled, the shared `package.json` can be deprecated.

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

- All existing module tools continue to function on machines where `.datacore/modules/node_modules/` has been installed (the current workaround). No breaking change.
- The `tool_deps` field in `module.yaml` is optional. Modules that omit it are assumed to have no npm dependencies or to be self-bundled.
- The `@datacore-one/mcp/runtime` re-export is **additive**. Existing tools importing from `'zod'` directly continue to work where `node_modules` is installed; they just emit a deprecation warning in `datacore_modules_health` once DIP-0028 is implemented.
- The health check changes turn previously silent failures into reported errors. Some installations that appeared healthy will now report errors. This is intentional — they were silently broken before.

## Security Considerations

- Bundled module tools are self-contained and do not depend on ambient `node_modules` that could be tampered with. This is a security improvement.
- Symlinked modules whose real paths are outside `DATACORE_ROOT` should be flagged by `checkModule` as an informational note (they are legitimate for development but unexpected in production).
- The `@datacore-one/mcp/runtime` re-export exposes the MCP server's own copies of `zod` and `js-yaml`. This is safe — both are non-networked, pure utility libraries.

## Implementation

### Phase 1: Health Check Fixes (Immediate — No Breaking Changes)
- [ ] Fix silent `catch {}` in `checkModule` → report `TOOLS_LOAD_FAILED` errors
- [ ] Add symlink detection (`lstatSync`) to `scanModulesDir`
- [ ] Add `SYMLINK_UNBUNDLED_TOOLS` warning to health check
- [ ] Add `hint` field to error output with DIP-0028 link

### Phase 2: Runtime Re-Export (Short-Term — Deprecates Workaround)
- [ ] Add `exports["./ runtime"]` to `@datacore-one/mcp/package.json`
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
- [ ] Remove `npm install` step from DIP-0005

## Open Questions

1. **Minimum bundle size threshold**: The `isLikelyBundled()` heuristic (20 KB) is approximate. Should there be an explicit `bundled: true` flag in `module.yaml` instead?

2. **`tool_deps.runtime` version validation**: Should the MCP server enforce semver compatibility checks between declared ranges and provided versions, or just warn? Strict enforcement could block valid use if the MCP server ships `zod@3.x` but the module declares `^4.x`.

3. **Multi-module version conflicts**: If two modules need incompatible versions of the same package, bundling resolves this. Should DIP-0028 formally prohibit `runtime` declarations for packages where version conflicts are plausible (i.e., require bundling for everything except `zod` and `js-yaml`)?

4. **Symlink target path restrictions**: Should `checkModule` enforce that symlink targets remain within `DATACORE_ROOT`, or is out-of-root targeting explicitly supported for multi-repo setups?

5. **Build step integration**: Should `module.yaml` gain a `build` top-level key so that `datacore-mcp` (or a future `datacore dev` CLI) can automatically rebuild module tools on change?

## References

- [DIP-0022: Module Specification](./DIP-0022-module-specification.md) — five-layer module architecture, `module.yaml` schema
- [DIP-0005: Installation & Upgrade](./DIP-0005-installation-upgrade.md) — setup flow to be amended in Phase 2
- `datacore-mcp/src/modules.ts` — `discoverModules()`, `scanModulesDir()`, `loadModuleTools()`, `checkModule()`
- `.datacore/modules/package.json` — current shared-deps workaround
- `.datacore/modules/gtd/tools/index.ts` — reference implementation (imports `zod`, delegates to Python adapter)
- `.datacore/modules/crm/tools/index.js` — affected: `import { z } from 'zod'` fails without `node_modules`
- `.datacore/modules/health` — symlinked module example (`health -> ../../2-datacore/2-projects/datacore-health`)
- [Node.js ESM: Bare specifier resolution](https://nodejs.org/api/esm.html#resolution-and-loading-algorithm)
- [esbuild bundler](https://esbuild.github.io/) — recommended bundler for module tools
