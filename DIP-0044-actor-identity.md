# DIP-0044: Actor Identity

| Field | Value |
|-------|-------|
| **DIP** | 0044 |
| **Title** | Actor Identity |
| **Author** | Datacore Team |
| **Type** | Architecture |
| **Status** | Draft |
| **Created** | 2026-08-13 |
| **Updated** | 2026-08-13 |
| **Tags** | `identity`, `actors`, `ledger`, `git`, `provenance`, `ssh` |
| **Affects** | `.datacore/registry/infrastructure.yaml`, `.datacore/lib/fleet_status.py`, `.datacore/lib/hooks/log_ownership_guard.py`, `.datacore/lib/ledger/log.py`, every machine's `~/.ssh/config`, `git config --global`, per-agent GitHub accounts |
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

### 3. `ssh_user` and `service_user` must be equal

They differed only on hermes, and that single divergence produced three wrong
diagnoses in one session — reading gregor-owned repos as root reported Tris's
repos as "not git repos". Both are now `gregor` fleet-wide; `/root/Data` became
`/home/gregor/Data` as a consequence, since the path existed only because the
service user was root.

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

## Consequences

- A probe must read the registry, never guess. `fleet_status.py` reports `?`
  for "could not determine" and never renders it as agreement.
- Adding a machine means adding an `actor` entry; there is no fallback.
- Gitea and PLUR are **not yet aligned**: both still collapse every agent into
  a single `gregor` identity, so attribution is correct on GitHub and lost
  everywhere else. That is the next gap this DIP implies but does not close.

## Open questions

1. Should Gitea gain per-agent accounts (`miles`, `tris`, `mrdata`) to match
   GitHub, or is a single owner identity acceptable for a private mirror?
2. PLUR scopes are `user:plur:gregor` / `user:plur:plur9`. Should agents write
   engrams under their own scope?
3. One SSH key (`id_rsa`, comment `gregor@plur.si`) authenticates the entire
   fleet — 94,311 logins on one box alone. Per-target keys would bound a
   compromise; is the operational cost worth it?

## Status notes

The specification above is implemented and verified as of 2026-08-13. It stays
**Draft** until owner ratification, per the governance rule that
`Implemented`/`Accepted` requires review rather than self-certification.
