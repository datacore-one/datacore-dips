# DIP-0044: Actor Identity

| Field | Value |
|-------|-------|
| **DIP** | 0044 |
| **Title** | Actor Identity |
| **Author** | Datacore Team |
| **Type** | Architecture |
| **Status** | Draft |
| **Created** | 2026-08-13 |
| **Updated** | 2026-09-12 |
| **Tags** | `identity`, `actors`, `ledger`, `git`, `provenance`, `ssh` |
| **Affects** | `.datacore/registry/infrastructure.yaml`, `.datacore/registry/principals.yaml`, `.datacore/lib/actor_identity.py`, `.datacore/lib/v2_verify.py`, `.datacore/lib/fleet_status.py`, `.datacore/lib/hooks/log_ownership_guard.py`, `.datacore/lib/ledger/log.py`, every machine's `~/.datacore/identity.env`, `git config --global`, per-agent GitHub accounts |
| **Specs** | `.datacore/registry/infrastructure.yaml` (`servers.<name>.access.actor`) |
| **Relates to** | DIP-0046 (Git Transport — authorization, where this DIP is authentication), DIP-0034 (Event Ledger Substrate — per-writer logs keyed by actor), DIP-0035 (Job Contracts — `--machine` selector) |

## Summary

Every machine answers to four or five different names, and no two conventions
agreed. This DIP makes **one canonical actor per machine**, recorded in the
registry, and requires that nothing derive an actor from a hostname, an SSH
alias, or a git author name ever again.

## Motivation

Measured on 2026-08-13, before this DIP:

| machine | ssh alias | `hostname -s` | git user.name | git user.email | ledger actor |
|---|---|---|---|---|---|
| mac | (local) | `Mac` | plur9 | dev@datacore.one | `mac` |
| winston | winston | `chief-of-staff` | Winston (CoS) | winston@datacore.one | `winston` |
| nightshift | nightshift | `nightshift` | Miles | gregor+miles@datafund.io | `miles` |
| hermes | hermes | `hermes-test` | **Gregor** | **gregor@datacore.one** | `tris` |
| plur-claw | plur-claw | `plur-claw` | Data | data-on-claw@…github.com | `data` |

Five namespaces, five conventions, and every mismatch had already cost
something:

- Resolving the actor from `hostname` filed Winston's events under
  `chief-of-staff`.
- A `Mac` vs `mac` case difference broke the ownership guard.
- The guard could not map `Winston (CoS)` to `winston` at all, which is why it
  now keys on author **email** rather than name.
- Tris's commits were authored as **Gregor** — an agent's work attributed to
  the human it works for, which is a provenance failure, not a cosmetic one.
- `hermes` is named `hermes-test` while serving production.

The registry described how to **reach** a machine (`ssh_user`, `service_user`,
`data_root`) but never said who it **is**, so every caller re-derived identity
from whichever name was nearest — and they disagree.

## Specification

### 1. One canonical actor, recorded once

`servers.<name>.access.actor` is the single source of truth. Nothing may infer
an actor from `hostname`, an SSH alias, a git author name, or a directory path.

```yaml
servers:
  winston:
    access:
      actor: winston          # canonical: the ledger writer identity
      ssh_user: gregor
      service_user: gregor
      hostname: bridge
```

### 2. Names are layered, and each layer has one job

| Layer | Rule | Rationale |
|---|---|---|
| **actor** | lowercase, stable, matches `<actor>.jsonl` | the ledger's writer identity |
| **ssh alias** | the agent's name (`winston`, `miles`, `tris`, `data`) | what a human types |
| **hostname** | a machine name, never a role or an agent | roles move between boxes; a role-named host becomes a lie |
| **git user.name** | the agent's display name | commit provenance |
| **git user.email** | unique per actor | what the ownership guard keys on |

Hostnames were renamed to Star Trek locations precisely because they **cannot
be mistaken for an agent or a role**: `bridge`, `engineering`, `transporter`,
`holodeck`, `mac`.

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

They differed only on hermes, and that single divergence produced three wrong
diagnoses in one session — reading gregor-owned repos as root reported Tris's
repos as "not git repos". Both are now `gregor` fleet-wide; `/root/Data` became
`/home/gregor/Data` as a consequence, since the path existed only because the
service user was root.

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
| winston | *(under the owner's account, deliberately — Winston assists and must not post as itself)* | `Winston <winston@datacore.one>` |
| miles | `miles-on-nightshift` | `Miles <miles@datacore.one>` |
| tris | `tris-on-hermes` | `Tris <tris@datacore.one>` |
| data | `data-on-claw` | `Data <mrdata@datacore.one>` |

A failed token is worse than a missing one: `gh` fell back silently to the
owner's account for weeks, so Miles pushed as the human while `gh auth status`
showed both accounts and no error. Verify the **active** account, not that an
account exists.

### 5. Ownership is judged by authorship, not by who pushed

The pre-push guard filters commits by **author email**. Actor names cannot do
this job — `Winston (CoS)` matches no registry key — and after DIP-0046 removed
rebase, a push range legitimately contains other actors' commits. Blaming the
courier both blocks honest work and trains agents to reach for
`SKIP_PRE_PUSH=1`, disabling the check for the case it exists to catch.

### 6. One resolver, and the hostname is a lookup key, never the answer

Twenty-four sites resolved identity on their own with
`DATACORE_ACTOR or gethostname()`, disagreeing on case and on domain
stripping, and every one fell back to the hostname. One laptop wrote under
`mac`, `Mac`, `Mac.home` and `air-23.local`; the executor on nightshift wrote
under its hostname. `.datacore/lib/actor_identity.py` is the one resolver:

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
owner decides it. Two writers may belong to one principal: `miles` and
`nightshift` on the same machine are the bot's log and the executor's log,
both Miles's; the executor declares its own actor in a unit drop-in
(`Environment=DATACORE_ACTOR=nightshift`) rather than inheriting the
machine's.

### 8. Authorship is verified per log, from the day it is declared

A per-writer hash chain is tamper-evident, not authenticated: any account that
can push can append to any log. The checklist's `writer logs authored by
their principal` reads, for every `<space>/.datacore/events/<writer>.jsonl`,
the non-merge commits that touched it since 2026-09-05 and fails when an
author email is outside the principal's `emails`. Merge commits are couriers,
not authors, and are not counted. Run against the whole tree on 2026-09-05
it passed on 46 logs and found two earlier courier commits made by autosave
before the rule existed (0-personal/nightshift by winston, 6-meridian/mac by
miles); they are on the record in the architecture audit of that date and are
not re-flagged.

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
- Gitea and PLUR are **not yet aligned**: both still collapse every agent into
  a single `gregor` identity, so attribution is correct on GitHub and lost
  everywhere else. That is the next gap this DIP implies but does not close.
- A principal without a charter, a contract and a scoreboard row is a name,
  not yet a principal. The product description of 2026-09-05 ("the contract
  of being a principal") lists the ten things; sections 6–9 here cover the
  first of them.

## Open questions

1. Should Gitea gain per-agent accounts (`miles`, `tris`, `mrdata`) to match
   GitHub, or is a single owner identity acceptable for a private mirror?
2. PLUR scopes are `user:plur:gregor` / `user:plur:plur9`. Should agents write
   engrams under their own scope?
3. One SSH key (`id_rsa`, comment `gregor@plur.si`) authenticates the entire
   fleet — 94,311 logins on one box alone. Per-target keys would bound a
   compromise; is the operational cost worth it?

## Status notes

Sections 1–5 were implemented and verified on 2026-08-13. Sections 6–9 were
implemented on 2026-09-05/06 (datacore PR #106, nightshift PR #6,
chief-of-staff PR #18; identity declared on all five machines, the checklist
green on the box). The DIP stays **Draft** until owner ratification, per the
governance rule that `Implemented`/`Accepted` requires review rather than
self-certification.
