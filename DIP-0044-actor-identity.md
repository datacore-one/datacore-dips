# DIP-0044: Actor Identity

| Field | Value |
|-------|-------|
| **DIP** | 0044 |
| **Title** | Actor Identity |
| **Author** | Datacore Team |
| **Type** | Architecture |
| **Status** | Draft |
| **Created** | 2026-08-13 |
| **Updated** | 2026-09-14 |
| **Tags** | `identity`, `actors`, `ledger`, `git`, `provenance`, `ssh` |
| **Affects** | `.datacore/registry/infrastructure.yaml`, `.datacore/registry/principals.yaml`, `.datacore/lib/actor_identity.py`, `.datacore/lib/v2_verify.py`, `.datacore/lib/fleet_status.py`, `.datacore/lib/hooks/log_ownership_guard.py`, `.datacore/lib/ledger/log.py`, every machine's `~/.datacore/identity.env`, `git config --global`, per-agent GitHub accounts |
| **Specs** | `.datacore/registry/infrastructure.yaml` (`servers.<name>.access.actor`) |
| **Relates to** | DIP-0046 (Git Transport — authorization, where this DIP is authentication), DIP-0034 (Event Ledger Substrate — per-writer logs keyed by actor), DIP-0035 (Job Contracts — `--machine` selector) |


**Compatibility decision (2026-09-14, proposed audit amendment):** New workflow
policies are explicit opt-ins, disabled by default. `DATACORE_REVIEW_BEFORE_EXECUTION=1`
adds strict review freshness/contract gating; `DATACORE_CADENCE_PROPOSALS=1`
selects proposal-only cadence/heartbeat production. `DATACORE_INSTANCE_BOUND_EXECUTION=1`
selects the parked experimental allocation model, tracked in
[core issue #192](https://github.com/datacore-one/datacore/issues/192); it is not
approved for deployment or inclusion in main. Earlier audit prose that treats
these additions as mandatory must be read within that opt-in scope. Data
preservation, truthful completion, private output, operator controls and exact
authority checks remain safety invariants. Unknown-effect retry policy remains
pending a separate owner decision. No implemented/audited status is asserted for
the parked proposal or any unverified deployment.


## Summary

Every machine answers to four or five different names, and no two conventions
agreed. This DIP defines **one declared default actor per installation**, with
explicit per-process writer overrides for separately registered executors.
Actor provenance is not an authorization or OS-isolation boundary. Strict
callers require declarations; the legacy non-strict diagnostic fallback is
described separately below and cannot establish execution authority.

## Motivation

A typical multi-machine installation before this DIP (illustrative):

| machine | ssh alias | `hostname -s` | git user.name | git user.email | ledger actor |
|---|---|---|---|---|---|
| workstation | (local) | `Workstation` | owner-handle | dev@example.com | `workstation` |
| server | cos | `chief-of-staff` | CoS Agent (CoS) | cos@example.com | `cos` |
| executor host | executor | `executor` | Executor Agent | owner+executor@example.com | `executor` |
| gateway host | gateway | `gateway-test` | **Owner Name** | **owner@example.com** | `gateway` |

Several namespaces, several conventions, and every mismatch costs something:

- Resolving the actor from `hostname` files the chief-of-staff agent's events
  under the hostname instead of its actor.
- A case difference (`Workstation` vs `workstation`) breaks the ownership guard.
- A display name such as `CoS Agent (CoS)` maps to no actor key at all, which
  is why the guard keys on author **email** rather than name.
- An agent's commits authored under the owner's identity attribute an agent's
  work to the human it works for — a provenance failure, not a cosmetic one.
- A host named `*-test` while serving production misleads every reader.

The registry described how to **reach** a machine (`ssh_user`, `service_user`,
`data_root`) but never said who it **is**, so every caller re-derived identity
from whichever name was nearest — and they disagree.

## Specification

### 1. One declared default, with explicit process writers

`servers.<name>.access.actor` declares the installation default. A service may
declare a distinct registered writer through its explicit process configuration.
Resolution follows section 6; strict consumers refuse a missing declaration.
Hostname, SSH alias, Git author name and directory path do not independently
authorize an actor or grant access to a principal's credentials.

```yaml
servers:
  cos:
    access:
      actor: cos              # canonical: the ledger writer identity
      ssh_user: alice
      service_user: alice
      hostname: host-a
```

### 2. Names are layered, and each layer has one job

| Layer | Rule | Rationale |
|---|---|---|
| **actor** | lowercase, stable, matches `<actor>.jsonl` | the ledger's writer identity |
| **ssh alias** | the agent's name (e.g. `cos`, `executor`, `gateway`) | what a human types |
| **hostname** | a machine name, never a role or an agent | roles move between boxes; a role-named host becomes a lie |
| **git user.name** | the agent's display name | commit provenance |
| **git user.email** | unique per actor | what the ownership guard keys on |

Choose hostnames from a theme that **cannot be mistaken for an agent or a
role** (for example `host-a`, `host-b`, or names from any neutral theme).

### 3. Administration and runtime identities — amendment under review

**Amendment status: Proposed.** The equality requirement below described an
operational workaround. It does not establish correct access or isolation and
must not prevent least-privilege service deployment.

- `ssh_user` declares the administration/access identity. `service_user`
  declares the execution identity. They MAY differ. A machine explicitly
  configured as local (`ssh_alias: '-'`) need not declare an SSH identity.
- Both applicable identities MUST be explicit, valid account names. An empty,
  unreadable or ambiguous registry MUST NOT produce a passing declaration check.
- Runtime inspection MUST establish which OS identity actually executes the
  service and whether that identity has the intended filesystem and credential
  access. Administrative reachability is not evidence of runtime permission.
- Actor names and Git author metadata provide attribution. Neither establishes
  an OS or credential boundary. Where policy requires one security context to
  lack another's credentials or privileges, deployment MUST enforce that
  boundary independently of the actor declaration and test denied access.
- A declaration-only check MUST state its scope. Equal account names, different
  account names, and a passing registry check are each insufficient evidence of
  runtime isolation. This amendment does not require separate OS identities for
  personas that intentionally share one authorized security context.

#### Historical equality rule

The previous requirement was: **`ssh_user` and `service_user` must be equal.**
Its incident rationale is retained for traceability:

A single host where the two differed produced repeated wrong diagnoses:
probes reading user-owned repos as root reported them as "not git repos".

#### Identity amendment change record

| Field | Record |
|---|---|
| Previous requirement | SSH and service users must be equal. |
| Problem | Equality was a workaround for probes running as the wrong user, and rejects legitimate privilege separation. Missing identities could pass, while registry agreement says nothing about actual privileges. |
| Corrected requirement | Declare administration and runtime identities independently, inspect the actual runtime identity, and enforce required credential/privilege boundaries independently of actor metadata. |
| Reason | Preserve reliable diagnostics and least privilege without treating provenance as authentication or process isolation. |
| Implementation impact | The identity checklist validates applicable declarations instead of account equality; runtime probes and deployments must verify the executing identity and effective access. |
| Compatibility impact | Existing equal-user declarations remain valid. Separate service identities become supported declarations. Missing, malformed and duplicate configuration is refused rather than reported as aligned. |
| Tests affected | Separate-user declarations, explicit local-only access, missing/ambiguous registry, invalid account/actor names; actual UID and negative filesystem/credential access tests. |
| Runtime/deployment impact | No account is renamed and no existing credentials are removed by this specification change. Required isolation must be deployed and verified separately; candidate fixtures are not active-deployment evidence. |
| Status | Proposed correction; repository checks are under remediation and active deployment/isolation reconciliation remains open. |

### 4. Agents commit as themselves

Each agent holds its own GitHub account and its own git identity:

| actor | GitHub | git identity |
|---|---|---|
| cos | *(may act under the owner's account, deliberately, when it assists and must not post as itself)* | `CoS Agent <cos@example.com>` |
| executor | `executor-bot` | `Executor Agent <executor@example.com>` |
| gateway | `gateway-bot` | `Gateway Agent <gateway@example.com>` |

A failed token is worse than a missing one: `gh` can fall back silently to the
owner's account, so an agent pushes as the human while `gh auth status` shows
both accounts and no error. Verify the **active** account, not that an account
exists.

### 5. Ownership is judged by authorship, not by who pushed

The pre-push guard filters commits by **author email**. Actor names cannot do
this job — a display name like `CoS Agent (CoS)` matches no registry key — and after DIP-0046 removed
rebase, a push range legitimately contains other actors' commits. Blaming the
courier both blocks honest work and trains agents to reach for
`SKIP_PRE_PUSH=1`, disabling the check for the case it exists to catch.

### 6. One resolver, and the hostname is a lookup key, never the answer

Many call sites resolved identity on their own with
`DATACORE_ACTOR or gethostname()`, disagreeing on case and on domain
stripping, and every one fell back to the hostname. One laptop could write
under several spellings of its own name (`laptop`, `Laptop`, `Laptop.home`,
`laptop.local`); the executor wrote under its hostname. `.datacore/lib/actor_identity.py` is the one resolver:

1. `DATACORE_ACTOR` in the environment (a unit drop-in, a test);
2. `~/.datacore/identity.env` — the machine's declaration, written once by
   the host's installer;
3. `servers.<name>.access.actor` in the infrastructure registry where
   `access.hostname` or the server name equals this hostname;
4. nothing: the short hostname, said once on stderr, so an undeclared machine
   still writes (an event lost is worse than an event misfiled) but never
   silently. `this_actor(strict=True)` raises `UndeclaredActor` instead.

Every writer, sealer, verifier and adapter in `.datacore/lib` calls it; the
nightshift and chief-of-staff modules call it through the root lib and keep
the old expression only as a fallback for an older root. The daily checklist
reports `identity declared` as FAIL when the actor equals the hostname, `n-a`
when it is inferred from the registry (correct today, fragile), OK when
declared.

### 7. Principals: a writer log belongs to someone

`registry/principals.yaml` binds each writer log to a principal — human,
agent, executor or migration — with the git identities that may append to it,
its GitHub account, its host, what it owns, which executors write for it, its
charter, its contracts, its memory scope, and (when decided) its budget and
permission mode. A field not yet decided is null and stays null until the
owner decides it. Two writers may belong to one principal: an agent's bot
log and the executor log on the same machine (e.g. `executor-agent` and
`executor`) can both belong to the executor agent; the executor declares its
own actor in a unit drop-in (`Environment=DATACORE_ACTOR=executor`) rather
than inheriting the machine's.

### 8. Authorship is verified per log, from the day it is declared

A per-writer hash chain is tamper-evident, not authenticated: any account that
can push can append to any log. The checklist's `writer logs authored by
their principal` reads, for every `<space>/.datacore/events/<writer>.jsonl`,
the non-merge commits that touched it since the rule's declaration date and
fails when an author email is outside the principal's `emails`. Merge commits
are couriers, not authors, and are not counted. Commits made before the rule
was declared are recorded once and not re-flagged.

### 9. Provenance on the event

The actor says which writer; it does not say which agent definition, on which
model, through which auth path. `completed` lifecycle events from the
executor now carry `model` and `auth`. Role (the venture hat a principal
wears) and the agent's registry version follow in the same field set; an
event without them is not wrong, it is merely less answerable.


## Consequences

- A probe must read the registry, never guess. `fleet_status.py` reports `?`
  for "could not determine" and never renders it as agreement.
- Adding a machine means adding an `actor` entry; there is no fallback.
- Secondary systems (a self-hosted git mirror, the memory store) may still
  collapse every agent into a single owner identity; attribution is then
  correct on the primary forge and lost elsewhere. That is a gap this DIP
  implies but does not close.
- A principal without a charter, a contract and a scoreboard row is a name,
  not yet a principal. Sections 6–9 here cover the first of the things that
  make one.

## Open questions

1. Should a self-hosted git mirror gain per-agent accounts to match the
   primary forge, or is a single owner identity acceptable for a private
   mirror?
2. Should agents write memory (engrams) under their own scope rather than
   the owner's?
3. Should each target host use its own SSH key rather than one key shared
   across machines? Per-target keys bound a compromise; is the operational
   cost worth it?

## Status notes

The DIP stays **Draft** until owner ratification, per the governance rule
that `Implemented`/`Accepted` requires review rather than self-certification.


### Actor resolution clarification — proposed (2026-09-14)

Previous text simultaneously required one actor per machine, forbade every
inference, specified a non-strict hostname fallback, and assigned two writers
to one machine. The corrected distinction is an installation default versus
explicit process writers, and diagnostic provenance versus authority. Existing
non-strict compatibility resolution remains supported and warns on fallback;
strict admission/authorization must use independently validated declarations.
No account, key or log is renamed. Existing actor and principal resolution
regressions remain applicable; runtime authority and credential isolation must
be tested separately. This clarification remains Draft and does not promote
existing cooperative checks into an independent security boundary.
