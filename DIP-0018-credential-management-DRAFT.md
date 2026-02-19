# DIP-0018: Credential Management

| Field | Value |
|-------|-------|
| **DIP** | 0018 |
| **Title** | Credential Management |
| **Author** | Gregor |
| **Type** | Infrastructure |
| **Status** | Draft |
| **Created** | 2026-01-15 |
| **Updated** | 2026-01-15 |
| **Tags** | `credentials`, `security`, `portability`, `dotfiles` |
| **Affects** | `.datacore/env/`, `[space]/.env`, secrets repo |
| **Specs** | `.datacore/specs/credential-index.yaml` |
| **Agents** | - |

## Summary

Establishes a hybrid credential management system combining shared credentials (with searchable index), project-specific credentials, and portable secrets repository for multi-machine installations. Solves credential loss, duplication, and discoverability problems while maintaining security tiers and machine portability.

## Motivation

### Problem: Credential Loss and Duplication

Real incident that motivated this DIP:
- Alchemy Sepolia RPC key needed for Fairdrop demo
- Key existed only in `/Users/gregor/Data/3-fds/2-projects/fairdrop/.env`
- No index or registry made it discoverable
- Nearly lost during development, requiring extensive search
- Same credential needed by multiple FDS projects (fairdrop, fairdrive)

### Current Pain Points

1. **Discoverability**: No way to find where credentials are stored
2. **Duplication**: Same credential copied to multiple projects
3. **Loss risk**: Credentials only exist in one location
4. **No portability**: Fresh machine setup requires manual credential hunting
5. **No security tiers**: All credentials treated equally (some are more sensitive)

### Use Cases

1. **Cross-project credentials**: Sepolia RPC used by multiple blockchain projects
2. **Fresh machine setup**: Travel notebook installation needs all credentials
3. **Credential audit**: "What API keys do I have? Where are they?"
4. **Security review**: "Which credentials are high-risk?"
5. **Project onboarding**: New developer needs to know what credentials to obtain

## Specification

### Prerequisites

Before implementing this DIP, ensure:

**Software Requirements**:
- Python 3.8+ (for robust YAML parsing and command implementation)
- `yq` v4+ (YAML query tool for shell scripts)
- `git` 2.30+
- `ssh` with ed25519 key support
- `gpg` 2.2+ (optional, for encrypted secrets)

**Infrastructure Requirements**:
- SSH access to private server (nightshift) for secrets repository
- OS-level disk encryption (FileVault on macOS, LUKS on Linux)
- Git pre-commit hooks support (for secrets scanning)

**Network Requirements**:
- HTTPS access to GitHub (for Datacore clone)
- SSH access to private server (for secrets-repo sync)
- Offline mode support for air-gapped installations (manual secret transfer via encrypted USB)

### Architecture Overview

```
~/Data/
├── .datacore/
│   ├── env/                          # Shared credentials (indexed)
│   │   ├── .env                      # Master credentials file
│   │   ├── blockchain-rpc.env        # Category: Blockchain RPC endpoints
│   │   ├── ai-services.env           # Category: AI/LLM API keys
│   │   ├── analytics.env             # Category: PostHog, analytics
│   │   └── deployment.env            # Category: Server, deployment
│   └── specs/
│       └── credential-index.yaml     # Searchable credential index
│
├── [N]-[space]/
│   └── .env                          # Project-specific credentials
│
└── [N]-[space]/2-projects/[project]/
    └── .env                          # Project-specific credentials

# Secrets Repository (separate, on private server)
user@nightshift-server:Data/0-personal-secrets.git/
├── install.sh                        # Bootstrap script
├── restore.sh                        # Secrets-only restore
├── README.md                         # Documentation
├── ssh/                              # SSH keys
├── gnupg/                            # GPG keys
├── github/                           # GitHub CLI tokens
├── gitconfig                         # Git configuration
├── datacore/                         # .datacore/env/ credentials
└── project-envs/                     # Project .env files
```

### 1. Credential Index Structure

The credential index lives at `.datacore/specs/credential-index.yaml` and provides searchable metadata:

```yaml
version: "1.0"
updated: "2026-01-15"

# Index of all credentials across Datacore installation
credentials:
  # Blockchain & Web3
  - id: alchemy-sepolia-rpc
    name: "Alchemy Sepolia RPC Key"
    type: api_key
    security_tier: medium
    category: blockchain-rpc
    provider: alchemy
    locations:
      - path: ".datacore/env/blockchain-rpc.env"
        var_name: "ALCHEMY_SEPOLIA_RPC_URL"
        primary: true
      - path: "3-fds/2-projects/fairdrop/.env"
        var_name: "ALCHEMY_SEPOLIA_RPC_URL"
        primary: false
        note: "Legacy location, migrate to shared"
    used_by:
      - "3-fds/2-projects/fairdrop"
      - "3-fds/2-projects/fairdrive"
    description: "Sepolia testnet RPC endpoint for FDS projects"
    documentation: "https://docs.alchemy.com/reference/api-overview"

  - id: infura-mainnet-rpc
    name: "Infura Mainnet RPC Key"
    type: api_key
    security_tier: high
    category: blockchain-rpc
    provider: infura
    locations:
      - path: ".datacore/env/blockchain-rpc.env"
        var_name: "INFURA_MAINNET_RPC_URL"
        primary: true
    used_by:
      - "3-fds/2-projects/fairdrop"
    description: "Ethereum mainnet RPC endpoint"
    documentation: "https://docs.infura.io/"

  # AI Services
  - id: anthropic-api-key
    name: "Anthropic API Key"
    type: api_key
    security_tier: critical
    category: ai-services
    provider: anthropic
    locations:
      - path: ".datacore/env/ai-services.env"
        var_name: "ANTHROPIC_API_KEY"
        primary: true
    used_by:
      - "0-personal/code/*"
      - "3-fds/*"
    description: "Claude API access for agents and automation"
    documentation: "https://docs.anthropic.com/"
    cost_implications: "Pay-per-token, monitor usage"

  - id: openai-api-key
    name: "OpenAI API Key"
    type: api_key
    security_tier: high
    category: ai-services
    provider: openai
    locations:
      - path: ".datacore/env/ai-services.env"
        var_name: "OPENAI_API_KEY"
        primary: true
    used_by:
      - "0-personal/code/embeddings"
    description: "GPT-4 and embeddings API"
    documentation: "https://platform.openai.com/docs"

  # Analytics & Observability
  - id: posthog-api-key
    name: "PostHog API Key"
    type: api_key
    security_tier: medium
    category: analytics
    provider: posthog
    locations:
      - path: ".datacore/env/analytics.env"
        var_name: "POSTHOG_API_KEY"
        primary: true
      - path: "3-fds/2-projects/fairdrop/.env"
        var_name: "NEXT_PUBLIC_POSTHOG_KEY"
        primary: false
    used_by:
      - "3-fds/2-projects/fairdrop"
    description: "Product analytics and feature flags"
    documentation: "https://posthog.com/docs"

  - id: sentry-dsn
    name: "Sentry DSN"
    type: dsn
    security_tier: low
    category: analytics
    provider: sentry
    locations:
      - path: ".datacore/env/analytics.env"
        var_name: "SENTRY_DSN"
        primary: true
    used_by:
      - "3-fds/2-projects/fairdrop"
    description: "Error tracking and performance monitoring"
    documentation: "https://docs.sentry.io/"

  # Deployment & Infrastructure
  - id: vercel-token
    name: "Vercel Deploy Token"
    type: auth_token
    security_tier: high
    category: deployment
    provider: vercel
    locations:
      - path: ".datacore/env/deployment.env"
        var_name: "VERCEL_TOKEN"
        primary: true
    used_by:
      - "3-fds/2-projects/fairdrop"
    description: "Vercel CLI and deployment automation"
    documentation: "https://vercel.com/docs/rest-api"

  - id: docker-hub-token
    name: "Docker Hub Access Token"
    type: auth_token
    security_tier: medium
    category: deployment
    provider: docker
    locations:
      - path: ".datacore/env/deployment.env"
        var_name: "DOCKER_HUB_TOKEN"
        primary: true
    used_by:
      - "3-fds/2-projects/*"
    description: "Docker image registry authentication"
    documentation: "https://docs.docker.com/security/for-developers/access-tokens/"

  # Development Tools
  - id: github-token
    name: "GitHub Personal Access Token"
    type: auth_token
    security_tier: critical
    category: development
    provider: github
    locations:
      - path: ".datacore/env/.env"
        var_name: "GITHUB_TOKEN"
        primary: true
    used_by:
      - ".datacore/lib/*"
      - "all spaces"
    description: "GitHub CLI and API access for automation"
    documentation: "https://docs.github.com/en/authentication"
    scopes: "repo, workflow, read:org, gist"

  - id: npm-token
    name: "NPM Publish Token"
    type: auth_token
    security_tier: high
    category: development
    provider: npm
    locations:
      - path: ".datacore/env/.env"
        var_name: "NPM_TOKEN"
        primary: true
    used_by:
      - "3-fds/2-projects/fairdrop"
    description: "NPM package publishing"
    documentation: "https://docs.npmjs.com/about-access-tokens"

  # Database & Storage
  - id: postgres-url
    name: "PostgreSQL Connection URL"
    type: connection_string
    security_tier: critical
    category: database
    provider: neon
    locations:
      - path: "3-fds/2-projects/fairdrop/.env"
        var_name: "DATABASE_URL"
        primary: true
    used_by:
      - "3-fds/2-projects/fairdrop"
    description: "Fairdrop production database"
    documentation: "https://neon.tech/docs"
    note: "Contains database credentials, rotate regularly"

  - id: s3-access-key
    name: "AWS S3 Access Key"
    type: access_key
    security_tier: high
    category: storage
    provider: aws
    locations:
      - path: ".datacore/env/deployment.env"
        var_name: "AWS_ACCESS_KEY_ID"
        primary: true
      - path: ".datacore/env/deployment.env"
        var_name: "AWS_SECRET_ACCESS_KEY"
        primary: true
    used_by:
      - "0-personal/code/backup"
      - "3-fds/2-projects/fairdrop"
    description: "S3 bucket access for backups and asset storage"
    documentation: "https://docs.aws.amazon.com/IAM/"

  # Email & Communication
  - id: sendgrid-api-key
    name: "SendGrid API Key"
    type: api_key
    security_tier: medium
    category: communication
    provider: sendgrid
    locations:
      - path: "3-fds/2-projects/fairdrop/.env"
        var_name: "SENDGRID_API_KEY"
        primary: true
    used_by:
      - "3-fds/2-projects/fairdrop"
    description: "Transactional email delivery"
    documentation: "https://docs.sendgrid.com/"

  # Monitoring & Alerting
  - id: slack-webhook
    name: "Slack Webhook URL"
    type: webhook
    security_tier: low
    category: communication
    provider: slack
    locations:
      - path: ".datacore/env/.env"
        var_name: "SLACK_WEBHOOK_URL"
        primary: true
    used_by:
      - ".datacore/agents/*"
    description: "Nightshift agent notifications"
    documentation: "https://api.slack.com/messaging/webhooks"

  # Machine-Specific (Travel Pattern)
  - id: travel-laptop-ssh
    name: "Travel Laptop SSH Key"
    type: ssh_key
    security_tier: critical
    category: machine-specific
    provider: self
    locations:
      - path: "secrets-repo://ssh/travel_laptop_ed25519"
        primary: true
      - path: "~/.ssh/travel_laptop_ed25519"
        primary: false
        note: "Deployed by bootstrap script"
    used_by:
      - "travel laptop only"
    description: "SSH key for travel laptop (limited permissions)"
    documentation: "internal"
    note: "Separate key from main workstation, revokable"

# Security Tiers (descending order of sensitivity)
security_tiers:
  critical:
    description: "Database credentials, SSH keys, GitHub tokens with write access"
    storage: "secrets-repo only, never in project .env"
    rotation: "quarterly or on suspicion of compromise"
    access: "encrypted at rest, GPG-protected in secrets repo"

  high:
    description: "API keys with billing or destructive capabilities"
    storage: "secrets-repo preferred, .datacore/env/ acceptable"
    rotation: "semi-annually"
    access: "gitignored, indexed"

  medium:
    description: "Read-only API keys, development endpoints"
    storage: ".datacore/env/ preferred, project .env acceptable"
    rotation: "annually or on provider recommendation"
    access: "gitignored, indexed"

  low:
    description: "Public webhooks, non-sensitive endpoints"
    storage: "any location"
    rotation: "as needed"
    access: "gitignored, may be documented in tracked files"

# Categories (for organization)
categories:
  blockchain-rpc: "Blockchain node RPC endpoints"
  ai-services: "LLM and AI platform API keys"
  analytics: "Product analytics and observability"
  deployment: "CI/CD, hosting, infrastructure"
  development: "GitHub, NPM, dev tools"
  database: "Database connection strings"
  storage: "Object storage, file systems"
  communication: "Email, Slack, webhooks"
  machine-specific: "SSH keys, machine-tied credentials"
```

### 2. Hybrid Storage Strategy

**Decision Tree**: Where should this credential live?

```
Is it machine-specific (SSH key, GPG key)?
├─ YES → secrets-repo://ssh/ or secrets-repo://gnupg/
└─ NO → Is it critical tier (database URL, GitHub write token)?
    ├─ YES → secrets-repo://datacore/ (with index in .datacore/specs/)
    └─ NO → Is it used by multiple projects?
        ├─ YES → .datacore/env/[category].env (with index entry)
        └─ NO → [space]/.env or [project]/.env (with index entry)
```

**Three Storage Locations**:

1. **Secrets Repository** (separate git repo on private server)
   - **Location**: `user@nightshift-server:Data/0-personal-secrets.git/`
   - **Contents**: Critical credentials, SSH/GPG keys, machine configs
   - **Encryption**: GPG-encrypted at rest
   - **Sync**: Manual pull/push, never auto-synced
   - **Access**: Requires SSH to nightshift server
   - **Use case**: Travel laptop bootstrap, disaster recovery

2. **Shared Datacore Credentials** (`.datacore/env/`)
   - **Location**: `~/Data/.datacore/env/`
   - **Contents**: Medium/high credentials used across multiple projects
   - **Encryption**: Gitignored, OS-level encryption only
   - **Sync**: Not synced (gitignored)
   - **Access**: Local filesystem only
   - **Use case**: Cross-project API keys, development credentials

3. **Project-Specific Credentials** (`[space]/.env`, `[project]/.env`)
   - **Location**: Within space or project directory
   - **Contents**: Low/medium credentials used by single project
   - **Encryption**: Gitignored, OS-level encryption only
   - **Sync**: Not synced (gitignored)
   - **Access**: Local filesystem only
   - **Use case**: Project-specific API keys, service endpoints

**Migration Rules**:

- Critical credentials → migrate to secrets-repo
- Duplicate credentials → consolidate to .datacore/env/
- Project-only credentials → leave in project .env
- Lost credentials → document in index with `status: missing`

### 3. Secrets Repository Structure

**Full Directory Tree**:

```
0-personal-secrets.git/
├── README.md                         # Documentation, bootstrap instructions
├── install.sh                        # Full bootstrap script
├── restore.sh                        # Secrets-only restore (no full install)
├── verify.sh                         # Verify integrity after restore
│
├── ssh/                              # SSH keys and config
│   ├── main_workstation_ed25519      # Primary SSH key
│   ├── main_workstation_ed25519.pub
│   ├── travel_laptop_ed25519         # Travel laptop SSH key (limited)
│   ├── travel_laptop_ed25519.pub
│   ├── github_deploy_ed25519         # GitHub deploy key
│   ├── github_deploy_ed25519.pub
│   ├── config                        # SSH client config
│   └── known_hosts                   # Known SSH hosts
│
├── gnupg/                            # GPG keys
│   ├── private-keys-v1.d/            # GPG private keys (encrypted)
│   ├── pubring.kbx                   # Public keyring
│   ├── trustdb.gpg                   # Trust database
│   └── gpg.conf                      # GPG configuration
│
├── github/                           # GitHub CLI authentication
│   ├── hosts.yml                     # GitHub hosts config
│   └── config.yml                    # GitHub CLI config
│
├── gitconfig                         # Global git configuration
├── gitignore_global                  # Global gitignore
│
├── datacore/                         # Datacore shared credentials
│   ├── .env                          # Master credentials file
│   ├── blockchain-rpc.env            # Blockchain RPC endpoints
│   ├── ai-services.env               # AI/LLM API keys
│   ├── analytics.env                 # Analytics services
│   └── deployment.env                # Deployment credentials
│
├── project-envs/                     # Critical project credentials
│   └── 3-fds/
│       └── 2-projects/
│           ├── fairdrop.env          # Fairdrop production credentials
│           └── fairdrive.env         # Fairdrive production credentials
│
├── backups/                          # Backup metadata
│   ├── credential-index.yaml         # Backup of credential index
│   └── last-backup.txt               # Timestamp of last backup
│
└── meta/                             # Repository metadata
    ├── VERSION                       # Secrets repo version
    ├── MANIFEST.txt                  # List of all files (for verification)
    └── CHECKSUM.sha256               # SHA256 checksums for verification
```

**Key Design Decisions**:

- **Separate repo**: Not in main Datacore (privacy, sync control)
- **Private server**: Hosted on nightshift (not GitHub)
- **GPG encryption**: Optional encryption for critical files
- **Version controlled**: Git history for credential rotation tracking
- **Verified restores**: Checksums and manifest for integrity

### 4. Bootstrap Script

**Complete `install.sh` script** (secrets repository root):

```bash
#!/bin/bash
# install.sh - Bootstrap Datacore installation on fresh machine
# Location: 0-personal-secrets.git/install.sh
# Usage: ./install.sh [--machine-type main|travel] [--skip-datacore]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_REPO="$SCRIPT_DIR"
DATA_DIR="${HOME}/Data"
DATACORE_DIR="${DATA_DIR}/.datacore"
DATACORE_REPO="https://github.com/yourusername/datacore.git"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
MACHINE_TYPE="main"
SKIP_DATACORE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --machine-type)
      MACHINE_TYPE="$2"
      shift 2
      ;;
    --skip-datacore)
      SKIP_DATACORE=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Logging functions
log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Verification function
verify_file() {
  local src="$1"
  local dest="$2"

  if [[ ! -f "$src" ]]; then
    log_error "Source file not found: $src"
    return 1
  fi

  if [[ -f "$dest" ]]; then
    log_warn "Destination file already exists: $dest"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      log_info "Skipping: $dest"
      return 0
    fi
  fi

  return 0
}

# Step 1: Verify secrets repository
log_info "Step 1: Verifying secrets repository..."

if [[ ! -f "$SECRETS_REPO/meta/VERSION" ]]; then
  log_error "Not a valid secrets repository (missing meta/VERSION)"
  exit 1
fi

SECRETS_VERSION=$(cat "$SECRETS_REPO/meta/VERSION")
log_info "Secrets repository version: $SECRETS_VERSION"

# Step 2: Create Data directory structure
log_info "Step 2: Creating Data directory structure..."

mkdir -p "$DATA_DIR"
mkdir -p "$DATACORE_DIR/env"
mkdir -p "$DATACORE_DIR/specs"

# Step 3: Install SSH keys
log_info "Step 3: Installing SSH keys..."

mkdir -p "${HOME}/.ssh"
chmod 700 "${HOME}/.ssh"

if [[ "$MACHINE_TYPE" == "main" ]]; then
  SSH_KEY="main_workstation_ed25519"
elif [[ "$MACHINE_TYPE" == "travel" ]]; then
  SSH_KEY="travel_laptop_ed25519"
else
  log_error "Unknown machine type: $MACHINE_TYPE"
  exit 1
fi

if verify_file "$SECRETS_REPO/ssh/$SSH_KEY" "${HOME}/.ssh/id_ed25519"; then
  cp "$SECRETS_REPO/ssh/$SSH_KEY" "${HOME}/.ssh/id_ed25519"
  cp "$SECRETS_REPO/ssh/${SSH_KEY}.pub" "${HOME}/.ssh/id_ed25519.pub"
  chmod 600 "${HOME}/.ssh/id_ed25519"
  chmod 644 "${HOME}/.ssh/id_ed25519.pub"
  log_info "Installed SSH key: $SSH_KEY"
fi

# Copy SSH config and known_hosts
if verify_file "$SECRETS_REPO/ssh/config" "${HOME}/.ssh/config"; then
  cp "$SECRETS_REPO/ssh/config" "${HOME}/.ssh/config"
  chmod 600 "${HOME}/.ssh/config"
  log_info "Installed SSH config"
fi

if verify_file "$SECRETS_REPO/ssh/known_hosts" "${HOME}/.ssh/known_hosts"; then
  cp "$SECRETS_REPO/ssh/known_hosts" "${HOME}/.ssh/known_hosts"
  chmod 644 "${HOME}/.ssh/known_hosts"
  log_info "Installed SSH known_hosts"
fi

# Step 4: Install GPG keys
log_info "Step 4: Installing GPG keys..."

if [[ -d "$SECRETS_REPO/gnupg" ]]; then
  mkdir -p "${HOME}/.gnupg"
  chmod 700 "${HOME}/.gnupg"

  cp -r "$SECRETS_REPO/gnupg/"* "${HOME}/.gnupg/"
  chmod 700 "${HOME}/.gnupg/private-keys-v1.d"
  chmod 600 "${HOME}/.gnupg/gpg.conf"

  log_info "Installed GPG keys"
  log_warn "Run 'gpg --list-secret-keys' to verify GPG installation"
else
  log_warn "No GPG keys found in secrets repository"
fi

# Step 5: Install git configuration
log_info "Step 5: Installing git configuration..."

if verify_file "$SECRETS_REPO/gitconfig" "${HOME}/.gitconfig"; then
  cp "$SECRETS_REPO/gitconfig" "${HOME}/.gitconfig"
  log_info "Installed git configuration"
fi

if verify_file "$SECRETS_REPO/gitignore_global" "${HOME}/.gitignore_global"; then
  cp "$SECRETS_REPO/gitignore_global" "${HOME}/.gitignore_global"
  log_info "Installed global gitignore"
fi

# Step 6: Install GitHub CLI configuration
log_info "Step 6: Installing GitHub CLI configuration..."

if [[ -d "$SECRETS_REPO/github" ]]; then
  mkdir -p "${HOME}/.config/gh"
  cp -r "$SECRETS_REPO/github/"* "${HOME}/.config/gh/"
  log_info "Installed GitHub CLI configuration"
  log_warn "Run 'gh auth status' to verify GitHub authentication"
else
  log_warn "No GitHub CLI configuration found"
fi

# Step 7: Install Datacore credentials
log_info "Step 7: Installing Datacore credentials..."

if [[ -d "$SECRETS_REPO/datacore" ]]; then
  cp -r "$SECRETS_REPO/datacore/"* "$DATACORE_DIR/env/"
  log_info "Installed Datacore shared credentials"
else
  log_warn "No Datacore credentials found in secrets repository"
fi

# Step 8: Clone Datacore repository (optional)
if [[ "$SKIP_DATACORE" == false ]]; then
  log_info "Step 8: Cloning Datacore repository..."

  if [[ -d "$DATACORE_DIR/.git" ]]; then
    log_warn "Datacore already cloned, skipping"
  else
    git clone "$DATACORE_REPO" "$DATA_DIR"
    log_info "Cloned Datacore repository"
  fi
else
  log_info "Step 8: Skipping Datacore clone (--skip-datacore)"
fi

# Step 9: Restore credential index
log_info "Step 9: Restoring credential index..."

if verify_file "$SECRETS_REPO/backups/credential-index.yaml" "$DATACORE_DIR/specs/credential-index.yaml"; then
  cp "$SECRETS_REPO/backups/credential-index.yaml" "$DATACORE_DIR/specs/credential-index.yaml"
  log_info "Restored credential index"
fi

# Step 10: Verify installation
log_info "Step 10: Verifying installation..."

ERRORS=0

# Check SSH
if [[ ! -f "${HOME}/.ssh/id_ed25519" ]]; then
  log_error "SSH key not installed"
  ((ERRORS++))
else
  log_info "✓ SSH key installed"
fi

# Check git config
if [[ ! -f "${HOME}/.gitconfig" ]]; then
  log_error "Git configuration not installed"
  ((ERRORS++))
else
  log_info "✓ Git configuration installed"
fi

# Check Datacore credentials
if [[ ! -d "$DATACORE_DIR/env" ]] || [[ -z "$(ls -A $DATACORE_DIR/env)" ]]; then
  log_warn "Datacore credentials directory empty"
else
  log_info "✓ Datacore credentials installed"
fi

# Check credential index
if [[ ! -f "$DATACORE_DIR/specs/credential-index.yaml" ]]; then
  log_error "Credential index not installed"
  ((ERRORS++))
else
  log_info "✓ Credential index installed"
fi

# Summary
echo ""
log_info "========================================="
log_info "Bootstrap Complete!"
log_info "========================================="
echo ""
log_info "Machine Type: $MACHINE_TYPE"
log_info "Data Directory: $DATA_DIR"
log_info "Errors: $ERRORS"
echo ""

if [[ $ERRORS -gt 0 ]]; then
  log_error "Installation completed with errors. Review output above."
  exit 1
fi

log_info "Next steps:"
echo "  1. Verify SSH access: ssh -T git@github.com"
echo "  2. Verify GPG keys: gpg --list-secret-keys"
echo "  3. Verify GitHub CLI: gh auth status"
echo "  4. Clone spaces: cd $DATA_DIR && ./sync"
echo "  5. Run credential audit: datacore creds list"
echo ""

exit 0
```

### 5. Credential Management Commands

**Command Structure**: `datacore creds <subcommand> [options]`

Implemented as Python module `.datacore/lib/creds.py` with wrapper script `.datacore/commands/creds`.

**Standard Terminology**: All commands use "secrets repository" (not "secrets-repo" or "0-personal-secrets.git") for consistency.

#### Global Options

All subcommands support:
- `--help, -h`: Show command-specific help
- `--verbose, -v`: Show detailed output
- `--quiet, -q`: Suppress non-error output

#### Subcommands

**`datacore creds` (no args) or `datacore creds help`**

Show command help and subcommands.

```bash
$ datacore creds

Datacore Credential Management

Usage: datacore creds <subcommand> [options]

Subcommands:
  list      List all credentials with filters
  show      Show detailed credential information
  search    Search credentials by keyword
  add       Add new credential to index
  migrate   Migrate credential to recommended location
  audit     Audit credentials for issues
  backup    Backup credentials to secrets repository
  restore   Restore credentials from secrets repository
  rotate    Start credential rotation workflow
  help      Show this help message

Examples:
  datacore creds list --tier critical
  datacore creds show alchemy-sepolia-rpc
  datacore creds audit
  datacore creds backup

Run 'datacore creds <subcommand> --help' for detailed help.
```

**`datacore creds list [--category <cat>] [--tier <tier>] [--format json|table] [--limit N] [--offset N]`**

List all credentials with metadata.

```bash
# List all credentials (default: table format, paginated)
$ datacore creds list

ID                    NAME                        TIER      CATEGORY        LOCATIONS
--------------------------------------------------------------------------------
alchemy-sepolia-rpc   Alchemy Sepolia RPC Key     medium    blockchain-rpc  2
anthropic-api-key     Anthropic API Key           critical  ai-services     1
github-token          GitHub Personal Access...   critical  development     1
postgres-url          PostgreSQL Connection...    critical  database        1

Showing 4 of 15 credentials. Use --limit and --offset to see more.

# List by category
$ datacore creds list --category blockchain-rpc

# List by security tier
$ datacore creds list --tier critical

# Pagination
$ datacore creds list --limit 10 --offset 10

# JSON output for scripting
$ datacore creds list --format json
[
  {
    "id": "alchemy-sepolia-rpc",
    "name": "Alchemy Sepolia RPC Key",
    "tier": "medium",
    "category": "blockchain-rpc",
    "locations": [...]
  }
]
```

**`datacore creds show <credential-id> [--show-value]`**

Show detailed information about a credential.

```bash
$ datacore creds show alchemy-sepolia-rpc

Credential: alchemy-sepolia-rpc
Name: Alchemy Sepolia RPC Key
Type: api_key
Security Tier: medium
Category: blockchain-rpc
Provider: alchemy

Description:
  Sepolia testnet RPC endpoint for FDS projects

Locations:
  [PRIMARY] .datacore/env/blockchain-rpc.env
    Variable: ALCHEMY_SEPOLIA_RPC_URL

  [LEGACY] 3-fds/2-projects/fairdrop/.env
    Variable: ALCHEMY_SEPOLIA_RPC_URL
    Note: Legacy location, migrate to shared

Used By:
  - 3-fds/2-projects/fairdrop
  - 3-fds/2-projects/fairdrive

Documentation: https://docs.alchemy.com/reference/api-overview

Audit Trail:
  Created: 2025-12-01
  Last Rotated: 2025-12-15
  Next Rotation: 2026-12-15

# Show actual credential value (requires confirmation)
$ datacore creds show alchemy-sepolia-rpc --show-value

WARNING: This will display the credential value in plaintext.
Continue? (y/N): y

Credential Value:
  ALCHEMY_SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/abc123xyz...
```

**Error Examples**:

```bash
# Credential not found
$ datacore creds show nonexistent-key

ERROR: Credential 'nonexistent-key' not found in index.

Did you mean one of these?
  - alchemy-sepolia-rpc
  - infura-sepolia-rpc

Run 'datacore creds list' to see all credentials.

# Credential file missing
$ datacore creds show openai-api-key

WARNING: Credential 'openai-api-key' is indexed but file not found.

Expected location: .datacore/env/ai-services.env
Variable: OPENAI_API_KEY

This credential may have been deleted or moved.
Run 'datacore creds audit' to diagnose.
Run 'datacore creds restore' to restore from backup.
```

**`datacore creds add <credential-id>`**

Interactively add a new credential to the index.

```bash
$ datacore creds add new-api-key

Adding credential: new-api-key

Name: New Service API Key
Type (api_key, auth_token, connection_string, ssh_key, webhook): api_key
Security Tier (critical, high, medium, low): medium
Category: ai-services
Provider: new-service

Description: API key for new AI service
Documentation URL: https://docs.newservice.com

Primary Location:
  Path: .datacore/env/ai-services.env
  Variable Name: NEW_SERVICE_API_KEY

Used By (comma-separated): 0-personal/code/experiments

Save to index? (y/N): y

✓ Credential added to index
✓ Entry created in .datacore/env/ai-services.env

Next steps:
  1. Set the credential value: export NEW_SERVICE_API_KEY="your-key-here"
  2. Add to secrets backup: datacore creds backup
```

**`datacore creds search <query>`**

Search credentials by name, description, provider, or variable name.

```bash
$ datacore creds search sepolia

Found 2 credentials:

1. alchemy-sepolia-rpc
   Alchemy Sepolia RPC Key
   Locations: .datacore/env/blockchain-rpc.env, 3-fds/2-projects/fairdrop/.env

2. infura-sepolia-rpc
   Infura Sepolia RPC Key
   Locations: .datacore/env/blockchain-rpc.env
```

**`datacore creds audit`**

Audit credential usage and identify issues.

```bash
$ datacore creds audit

Credential Audit Report
=======================

✓ Indexed: 15 credentials
✗ Issues Found: 3

ISSUES:

1. Duplicate Credentials (1)
   - alchemy-sepolia-rpc: found in 2 locations
     Primary: .datacore/env/blockchain-rpc.env
     Duplicate: 3-fds/2-projects/fairdrop/.env
     Recommendation: Remove duplicate, use shared credential

2. Missing Credentials (1)
   - openai-api-key: indexed but file not found
     Expected: .datacore/env/ai-services.env
     Variable: OPENAI_API_KEY
     Recommendation: Restore from backup or re-create

3. Rotation Overdue (1)
   - github-token: last rotated 400 days ago
     Tier: critical (requires quarterly rotation)
     Recommendation: Rotate immediately

RECOMMENDATIONS:
  Run: datacore creds migrate alchemy-sepolia-rpc
  Run: datacore creds restore openai-api-key
  Run: datacore creds rotate github-token
```

**`datacore creds migrate <credential-id> [--dry-run]`**

Migrate a credential to its recommended location.

```bash
# Preview migration (dry-run)
$ datacore creds migrate alchemy-sepolia-rpc --dry-run

[DRY RUN] Migrating: alchemy-sepolia-rpc

Current locations:
  [PRIMARY] .datacore/env/blockchain-rpc.env
  [DUPLICATE] 3-fds/2-projects/fairdrop/.env

Migration plan:
  1. Keep primary location: .datacore/env/blockchain-rpc.env
  2. Update 3-fds/2-projects/fairdrop/.env to source from shared
  3. Remove duplicate entry from index

Changes (preview only, not applied):
  File: 3-fds/2-projects/fairdrop/.env
    - ALCHEMY_SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/...
    + source ${DATACORE_DIR}/env/blockchain-rpc.env

Run without --dry-run to apply changes.

# Execute migration
$ datacore creds migrate alchemy-sepolia-rpc

Migrating: alchemy-sepolia-rpc

Current locations:
  [PRIMARY] .datacore/env/blockchain-rpc.env
  [DUPLICATE] 3-fds/2-projects/fairdrop/.env

Migration plan:
  1. Keep primary location: .datacore/env/blockchain-rpc.env
  2. Update 3-fds/2-projects/fairdrop/.env to source from shared
  3. Remove duplicate entry from index

Proceed? (y/N): y

✓ Updated 3-fds/2-projects/fairdrop/.env:
  - Removed: ALCHEMY_SEPOLIA_RPC_URL=...
  - Added: source ${DATACORE_DIR}/env/blockchain-rpc.env
✓ Updated credential index
✓ Migration complete

Next steps:
  1. Test projects to ensure they still load credentials
  2. Commit index changes: git add .datacore/specs/credential-index.yaml
```

**`datacore creds backup [--gpg] [--verbose]`**

Backup credentials to secrets repository with progress indicator.

```bash
$ datacore creds backup

Backing up credentials to secrets repository...

Secrets repository: user@nightshift-server:Data/0-personal-secrets.git/

Files to backup:
  .datacore/env/.env
  .datacore/env/blockchain-rpc.env
  .datacore/env/ai-services.env
  .datacore/env/analytics.env
  .datacore/env/deployment.env
  .datacore/specs/credential-index.yaml

Proceed? (y/N): y

Connecting to secrets repository... ✓
Backing up files... [████████████████████] 6/6 files (100%)
  .datacore/env/.env                       ✓
  .datacore/env/blockchain-rpc.env         ✓
  .datacore/env/ai-services.env            ✓
  .datacore/env/analytics.env              ✓
  .datacore/env/deployment.env             ✓
  .datacore/specs/credential-index.yaml    ✓
Updating timestamp... ✓
Committing changes... ✓

Backup complete: 2026-01-15 14:32:00
Committed as: 3f2a8b9 "Backup credentials 2026-01-15"

# With GPG encryption
$ datacore creds backup --gpg

Enter GPG passphrase for encryption: ********

Encrypting files... [████████████████████] 6/6 files (100%)
Backup complete (GPG encrypted): 2026-01-15 14:32:00
```

**`datacore creds restore [--from-backup <date>]`**

Restore credentials from secrets repository.

```bash
$ datacore creds restore

Restoring credentials from secrets repository...

Available backups:
  1. 2026-01-15 14:32:00 (latest)
  2. 2026-01-10 09:15:00
  3. 2026-01-01 08:00:00

Select backup (1-3): 1

Restoring from backup: 2026-01-15 14:32:00

Files to restore:
  .datacore/env/.env
  .datacore/env/blockchain-rpc.env
  .datacore/env/ai-services.env
  .datacore/specs/credential-index.yaml

Proceed? (y/N): y

✓ Restored 4 files from backup
✓ Credential index restored

Restore complete. Run 'datacore creds audit' to verify.
```

**`datacore creds rotate <credential-id>`**

Mark a credential for rotation and generate rotation checklist.

```bash
$ datacore creds rotate github-token

Rotating credential: github-token

Current status:
  Last rotated: 2024-06-01 (400 days ago)
  Security tier: critical (requires quarterly rotation)
  Status: OVERDUE

Rotation checklist:

1. Generate new credential
   □ Go to provider: https://github.com/settings/tokens
   □ Generate new token with scopes: repo, workflow, read:org, gist
   □ Copy new token value

2. Update credential storage
   □ Update .datacore/env/.env: GITHUB_TOKEN=new-value
   □ Backup to secrets repo: datacore creds backup

3. Test new credential
   □ Test GitHub CLI: gh auth status
   □ Test API access: curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

4. Revoke old credential
   □ Go to provider: https://github.com/settings/tokens
   □ Revoke old token

5. Update index
   □ Mark rotation complete: datacore creds rotated github-token

Continue with rotation? (y/N):
```

### 6. Rationale

**Why Hybrid Storage?**

Single storage location doesn't work for three reasons:

1. **Security tiers differ**: Database URLs (critical) need different protection than read-only API keys (medium)
2. **Project boundaries**: Some credentials are truly project-specific (fairdrop DB), others are shared (Sepolia RPC)
3. **Portability needs**: Travel laptop needs subset of credentials, not all

Hybrid approach:
- Critical → secrets-repo (GPG-encrypted, backed up)
- Shared → .datacore/env/ (indexed, discoverable)
- Project-only → project .env (isolated, project-scoped)

**Why Separate Secrets Repository?**

Five reasons:

1. **Privacy**: Secrets repo never pushed to GitHub, only to private server
2. **Sync control**: Manual sync prevents accidental exposure
3. **Machine portability**: Clone once, deploy to any machine
4. **Backup strategy**: Independent backup schedule from code
5. **Access control**: SSH to nightshift required, adds security layer

Alternative (rejected): Store secrets in .datacore/env/ with gitignore
- Problem: No backup, no portability, loss risk remains

**Why YAML Index?**

Four reasons:

1. **Searchable**: `grep` and `yq` make credential discovery trivial
2. **Diffable**: Git tracks changes to credential metadata (not values)
3. **Extensible**: Add fields (rotation dates, cost tracking) without schema changes
4. **Human-readable**: Audit and review without tools

Alternative (rejected): Store metadata in .env comments
- Problem: Not structured, can't query, no validation

**Why Travel Pattern?**

Real use case: Travel laptop has:
- Separate SSH key (limited GitHub permissions, revokable)
- Subset of credentials (no production DB access)
- Same credential index (knows what's available)

Bootstrap script handles:
- Different SSH keys per machine type
- Selective credential deployment
- Same Datacore installation otherwise

Benefit: Compromise of travel laptop doesn't expose all credentials

### 7. Backwards Compatibility

**Migration Path** (4 phases):

**Phase 1: Index Creation** (Week 1)
- Create `.datacore/specs/credential-index.yaml`
- Scan all .env files across Datacore
- Document all credentials in index
- No breaking changes, purely additive

**Phase 2: Shared Credential Consolidation** (Week 2-3)
- Identify duplicate credentials (e.g., alchemy-sepolia-rpc in multiple projects)
- Move to `.datacore/env/[category].env`
- Update projects to source shared credentials
- Test all projects still work
- Mark old locations as "legacy" in index

**Phase 3: Secrets Repository Setup** (Week 4)
- Create 0-personal-secrets.git on nightshift
- Migrate critical credentials (SSH keys, GitHub tokens, DB URLs)
- Create bootstrap script
- Test fresh machine installation
- Keep old locations as fallback

**Phase 4: Deprecation** (Week 5-6)
- Remove legacy credential locations
- Update all projects to use shared/secrets
- Mark migration complete in index
- Document final state in CLAUDE.md

**Breaking Changes**: None until Phase 4

**Rollback Plan**: Index is metadata-only, credentials remain in original locations through Phase 3

### 8. Security

**Comprehensive Threat Model**:

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| **1. Laptop theft** | Medium | Critical | SSH keys passphrase-protected, disk encryption required, travel laptop uses limited-scope SSH key |
| **2. GitHub compromise** | Low | High | Secrets-repo on private server (not GitHub), .env files gitignored, credentials never in tracked files |
| **3. Credential leakage in commits** | Medium | Critical | Pre-commit hook scans for credential patterns, index contains metadata only (no values), audit command detects exposed files |
| **4. Insider threat** | Low | High | Critical credentials in secrets-repo (SSH access controlled), audit trail in git history, separate SSH keys per machine |
| **5. Malicious script reading .env** | Medium | High | Credentials in separate .env files (not in PATH), scripts must explicitly source, OS-level permissions restrict access |
| **6. Compromised dependency** | Medium | Critical | Minimal dependencies (Python stdlib, yq), no credential values in memory dumps, secrets loaded just-in-time |
| **7. Clipboard hijacking** | Low | Medium | Commands never echo credentials to stdout, `datacore creds show` only shows metadata (not values), use `--show-value` flag with confirmation |
| **8. Secrets-repo server compromise** | Low | Critical | GPG encryption for critical credentials, separate server from GitHub, firewall restricts SSH to known IPs, 2FA for server access |
| **9. Bootstrap script compromise** | Low | Critical | Verify secrets-repo git signature before bootstrap, checksum validation (meta/CHECKSUM.sha256), manual review of install.sh before execution |
| **10. Credential rotation failure** | Medium | Medium | Rotation checklist with rollback steps, test new credential before revoking old, audit command tracks overdue rotations |

**Security Tiers** (descending order):

1. **Critical**: Database URLs, SSH keys, GitHub write tokens
   - Storage: secrets-repo only
   - Encryption: GPG at rest
   - Rotation: quarterly
   - Access: SSH to nightshift required

2. **High**: API keys with billing or destructive capabilities
   - Storage: secrets-repo or .datacore/env/
   - Encryption: OS-level (FileVault/LUKS)
   - Rotation: semi-annually
   - Access: Local filesystem

3. **Medium**: Read-only API keys, development endpoints
   - Storage: .datacore/env/ or project .env
   - Encryption: OS-level
   - Rotation: annually
   - Access: Local filesystem

4. **Low**: Public webhooks, non-sensitive endpoints
   - Storage: any location
   - Encryption: optional
   - Rotation: as needed
   - Access: may be documented in tracked files

**Encryption Strategy**:

- **At rest**: OS-level disk encryption (FileVault on macOS, LUKS on Linux) required
- **In transit**: SSH for secrets-repo sync, HTTPS for API calls
- **Optional**: GPG encryption for critical credentials in secrets-repo
  - Enabled via `datacore creds backup --gpg`
  - Requires GPG key in secrets-repo://gnupg/

**GPG Key Management**:

1. **Key Generation**:
   ```bash
   # Generate master GPG key (one-time, main workstation only)
   gpg --full-generate-key --expert
   # Key type: RSA and RSA (default)
   # Key size: 4096 bits
   # Expiration: 2 years (rotate before expiry)
   # Passphrase: Strong, stored in password manager
   ```

2. **Key Backup**:
   - Export private key: `gpg --export-secret-keys --armor KEY_ID > private.asc`
   - Store encrypted on USB drive (offline backup)
   - Copy to secrets-repo://gnupg/ (for machine portability)

3. **Key Rotation** (every 2 years):
   - Generate new key
   - Re-encrypt all critical credentials with new key
   - Update secrets-repo
   - Revoke old key after transition period (90 days)

4. **Key Distribution**:
   - Main workstation: Full GPG keyring
   - Travel laptop: Encryption-only subkey (cannot decrypt critical credentials)
   - Nightshift server: Public key only (for encrypted backups)

**SSH Key Restrictions**:

1. **Main Workstation SSH Key** (main_workstation_ed25519):
   - GitHub scopes: `repo`, `workflow`, `read:org`, `gist`
   - Server access: Full access to nightshift
   - Passphrase required: Yes

2. **Travel Laptop SSH Key** (travel_laptop_ed25519):
   - GitHub scopes: `repo` (read-only), `read:org`
   - Server access: Limited to secrets-repo read-only operations
   - SSH restrictions in `~/.ssh/authorized_keys` on nightshift:
     ```
     command="git-shell -c \"$SSH_ORIGINAL_COMMAND\"",no-port-forwarding,no-X11-forwarding,no-agent-forwarding ssh-ed25519 AAAA... travel_laptop
     ```
   - Passphrase required: Yes

3. **GitHub Deploy Key** (github_deploy_ed25519):
   - Scope: Single repo deploy access
   - No passphrase (used in CI/CD)
   - Rotated every 6 months

**Access Control**:

- **Secrets repository**:
  - SSH key required (deployed by bootstrap script)
  - Server-side: `authorized_keys` enforces command restrictions
  - Two-factor auth on nightshift server (TOTP)

- **Nightshift server**:
  - Firewall restricts SSH to known IPs (home: 203.0.113.0/24, office: 198.51.100.0/24)
  - fail2ban monitors failed SSH attempts (3 strikes = 1 hour ban)
  - SSH config: `PasswordAuthentication no`, `PubkeyAuthentication yes`

- **Travel laptop**:
  - Separate SSH key with read-only access enforced via git-shell
  - No access to critical credential files (enforced by secrets-repo directory permissions)
  - Can read index to know what credentials exist, cannot read values

**Pre-commit Hook for Secrets Scanning**:

Implemented as `.git/hooks/pre-commit` in all Datacore repos:

```bash
#!/bin/bash
# Pre-commit hook: Scan for credential leaks

PATTERNS=(
  "ANTHROPIC_API_KEY"
  "OPENAI_API_KEY"
  "GITHUB_TOKEN"
  "DATABASE_URL"
  "postgres://"
  "-----BEGIN.*PRIVATE KEY-----"
  "password\s*=\s*['\"][^'\"]{8,}"
)

for pattern in "${PATTERNS[@]}"; do
  if git diff --cached --diff-filter=ACMR | grep -iE "$pattern"; then
    echo "ERROR: Potential credential leak detected: $pattern"
    echo "If this is a false positive, use: git commit --no-verify"
    exit 1
  fi
done

exit 0
```

**Secrets-Repo Replication Strategy**:

Primary strategy: Single authoritative server (nightshift) with manual backups

1. **Primary**: nightshift server (`user@nightshift-server:Data/0-personal-secrets.git/`)
2. **Backup 1**: Encrypted USB drive (monthly export, stored in safe)
3. **Backup 2**: Encrypted cloud backup (optional, via `gpg --encrypt | aws s3 cp`)

Replication procedure:
```bash
# Monthly backup to USB drive
cd /Volumes/BACKUP_USB/
git clone user@nightshift-server:Data/0-personal-secrets.git
tar czf secrets-$(date +%Y%m%d).tar.gz 0-personal-secrets.git/
gpg --encrypt --recipient your-email@example.com secrets-*.tar.gz
rm -rf 0-personal-secrets.git secrets-*.tar.gz  # Keep only .gpg file
```

Why not multi-server replication?
- Critical credentials require single source of truth
- Replication increases attack surface
- Manual sync forces deliberate credential changes
- Git history provides version control, replication not needed for recovery

**Audit Trail**:

- Credential index tracked in git (metadata changes visible)
- Secrets-repo tracks credential file history (when rotated)
- Audit command detects rotation overdue, missing credentials
- Server logs track SSH access (who accessed secrets-repo, when)
- Bootstrap script logs to `/var/log/datacore-bootstrap.log` (timestamped operations)

### 9. Implementation

**Phase 1: Index Creation** (2 weeks, ~40 hours)

Tasks:
- [ ] Create `.datacore/specs/credential-index.yaml` schema (4 hours)
- [ ] Write Python scanner to find all .env files recursively (6 hours)
- [ ] Scan all .env files in Datacore installation (2 hours)
- [ ] Document 15+ credentials in index (4 hours)
- [ ] Implement `datacore creds list` command in Python (8 hours)
- [ ] Implement `datacore creds show <id>` command (4 hours)
- [ ] Implement `datacore creds search <query>` command (4 hours)
- [ ] Implement `datacore creds audit` command (6 hours)
- [ ] Write unit tests for commands (4 hours)
- [ ] Test index completeness manually (2 hours)

Deliverables:
- `.datacore/specs/credential-index.yaml` with all credentials
- `.datacore/lib/creds.py` (Python implementation, not Bash)
- `.datacore/commands/creds` (wrapper script)
- Unit tests in `.datacore/tests/test_creds.py`
- Documentation in CLAUDE.md

Dependencies:
- Python 3.8+ installed
- `yq` v4+ installed
- Access to all spaces for scanning

**Phase 2: Shared Credential Consolidation** (2 weeks, ~50 hours)

Tasks:
- [ ] Run audit command to identify duplicates (1 hour)
- [ ] Create `.datacore/env/[category].env` files (2 hours)
- [ ] Implement `datacore creds migrate <id>` command with --dry-run (12 hours)
- [ ] Write migration script for batch updates (8 hours)
- [ ] Migrate 5-10 duplicate credentials to shared location (4 hours)
- [ ] Update projects to source shared credentials (automated script, 4 hours)
- [ ] Test all affected projects (fairdrop, fairdrive, etc.) (8 hours)
- [ ] Mark legacy locations in index (2 hours)
- [ ] Write integration tests for migration (6 hours)
- [ ] Document migration process (3 hours)

Deliverables:
- `.datacore/env/blockchain-rpc.env`
- `.datacore/env/ai-services.env`
- `.datacore/env/analytics.env`
- `.datacore/env/deployment.env`
- Updated credential index with migration status
- Migration script: `.datacore/lib/migrate_credentials.py`
- Integration tests

Dependencies:
- Phase 1 complete (index and audit command)
- Backup of all .env files before migration
- Test environment (Docker or VM) for testing

**Phase 3: Secrets Repository Setup** (2 weeks, ~60 hours)

Tasks:
- [ ] Setup nightshift server access (SSH config, authorized_keys) (4 hours)
- [ ] Create 0-personal-secrets.git on nightshift (2 hours)
- [ ] Implement directory structure (ssh/, gnupg/, datacore/, etc.) (3 hours)
- [ ] Create `install.sh` bootstrap script (~100 lines, 12 hours)
- [ ] Create `restore.sh` secrets-only restore (6 hours)
- [ ] Create `verify.sh` integrity checker (4 hours)
- [ ] Implement `datacore creds backup` command with progress bar (8 hours)
- [ ] Implement `datacore creds restore` command with backup selection (8 hours)
- [ ] Migrate critical credentials to secrets-repo (4 hours)
- [ ] Test bootstrap in VM (Ubuntu 22.04, macOS 13+) (6 hours)
- [ ] Test travel laptop bootstrap with limited SSH key (3 hours)

Deliverables:
- 0-personal-secrets.git repository on nightshift
- Bootstrap scripts (install.sh, restore.sh, verify.sh)
- Updated credential index with secrets-repo locations
- Tested installation procedure (documented with screenshots)
- VM images for testing (Ubuntu, macOS)

Dependencies:
- SSH access to nightshift configured
- Test VMs provisioned (Vagrant or Docker)
- GPG key generated (optional for encrypted backup testing)

**Phase 4: Documentation & Deprecation** (1 week, ~30 hours)

Tasks:
- [ ] Update CLAUDE.md with credential management section (4 hours)
- [ ] Document bootstrap procedure for new machines (3 hours)
- [ ] Create migration guide for existing installations (4 hours)
- [ ] Implement `datacore creds rotate <id>` command (6 hours)
- [ ] Remove legacy credential locations (2 hours)
- [ ] Final audit of all credentials (2 hours)
- [ ] Create DIP-0018 (this document) (6 hours)
- [ ] Finalize pre-commit hook for all repos (3 hours)

Deliverables:
- Complete CLAUDE.md section
- Migration guide for users (with examples)
- DIP-0018 published
- All credentials migrated to final locations
- Pre-commit hook deployed to all repos

Dependencies:
- Phases 1-3 complete
- All testing passed

**Total Timeline**: 7 weeks (~180 hours for one developer)

### Testing Strategy

**Unit Tests** (`.datacore/tests/test_creds.py`):

```python
import unittest
from datacore.lib.creds import CredentialIndex, CredentialManager

class TestCredentialIndex(unittest.TestCase):
    def test_load_index(self):
        """Test loading credential index from YAML"""
        index = CredentialIndex.load(".datacore/specs/credential-index.yaml")
        self.assertGreater(len(index.credentials), 0)

    def test_search_by_id(self):
        """Test searching credential by ID"""
        index = CredentialIndex.load_fixture("test_index.yaml")
        cred = index.get("alchemy-sepolia-rpc")
        self.assertEqual(cred.name, "Alchemy Sepolia RPC Key")

    def test_search_by_category(self):
        """Test filtering by category"""
        index = CredentialIndex.load_fixture("test_index.yaml")
        blockchain_creds = index.filter(category="blockchain-rpc")
        self.assertGreater(len(blockchain_creds), 0)

    def test_audit_duplicate_detection(self):
        """Test audit detects duplicates"""
        index = CredentialIndex.load_fixture("test_duplicates.yaml")
        issues = index.audit()
        self.assertTrue(any(i.type == "duplicate" for i in issues))

class TestCredentialManager(unittest.TestCase):
    def test_backup_command(self):
        """Test backup creates all expected files"""
        # Mock secrets-repo
        # Assert files copied
        pass

    def test_migrate_dry_run(self):
        """Test migrate --dry-run doesn't change files"""
        # Run migrate with --dry-run
        # Assert no files modified
        pass
```

**Integration Tests** (`.datacore/tests/integration/test_workflow.py`):

```python
import unittest
import tempfile
from datacore.lib.creds import CredentialManager

class TestCredentialWorkflow(unittest.TestCase):
    def test_full_bootstrap(self):
        """Test complete bootstrap workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mock secrets-repo
            # Run install.sh --machine-type main --skip-datacore
            # Assert SSH keys installed
            # Assert credentials restored
            # Assert index loaded
            pass

    def test_credential_migration(self):
        """Test migrating duplicate credential"""
        # Create duplicate credential in 2 locations
        # Run datacore creds migrate <id>
        # Assert duplicate removed
        # Assert index updated
        # Assert projects still load credential
        pass

    def test_rotation_workflow(self):
        """Test credential rotation checklist"""
        # Run datacore creds rotate <id>
        # Generate new credential
        # Update storage
        # Test new credential
        # Mark rotation complete
        pass
```

**VM Testing Matrix**:

| OS | Version | Python | SSH | GPG | Status |
|----|---------|--------|-----|-----|--------|
| macOS | 13.0+ | 3.11 | ed25519 | 2.4.0 | Required |
| Ubuntu | 22.04 LTS | 3.10 | ed25519 | 2.2.27 | Required |
| Debian | 11 | 3.9 | ed25519 | 2.2.27 | Optional |
| Fedora | 38 | 3.11 | ed25519 | 2.4.0 | Optional |

**Test Scenarios**:

1. **Fresh Machine Bootstrap**:
   - Clone secrets-repo from nightshift
   - Run `./install.sh --machine-type main`
   - Verify all credentials loaded
   - Verify SSH/GPG keys installed
   - Test credential access from sample project

2. **Travel Laptop Bootstrap**:
   - Clone secrets-repo (read-only SSH key)
   - Run `./install.sh --machine-type travel`
   - Verify limited SSH key installed
   - Verify cannot access critical credentials
   - Verify can read index

3. **Credential Migration**:
   - Setup duplicate credential scenario
   - Run `datacore creds audit` (detects duplicate)
   - Run `datacore creds migrate <id> --dry-run` (preview)
   - Run `datacore creds migrate <id>` (execute)
   - Test projects still work

4. **Secrets-Repo Backup/Restore**:
   - Modify credential in .datacore/env/
   - Run `datacore creds backup`
   - Verify file in secrets-repo
   - Delete local credential
   - Run `datacore creds restore`
   - Verify credential restored

5. **Pre-commit Hook**:
   - Attempt to commit .env file with credential
   - Verify hook blocks commit
   - Verify error message helpful
   - Test `--no-verify` override

**Performance Tests**:

- Index load time: < 100ms for 100 credentials
- Search time: < 50ms for 100 credentials
- Backup time: < 5s for 20 credential files
- Bootstrap time: < 60s on fast network

**Rollback Procedures**:

**Phase 1 Rollback**:
- Delete `.datacore/specs/credential-index.yaml`
- Remove `.datacore/lib/creds.py` and `.datacore/commands/creds`
- No credential files moved, zero risk

**Phase 2 Rollback**:
- Restore .env backups: `cp backups/.env.backup-YYYYMMDD [project]/.env`
- Delete `.datacore/env/[category].env` files
- Revert index to Phase 1 state: `git checkout HEAD~10 .datacore/specs/credential-index.yaml`
- Test all projects load credentials

**Phase 3 Rollback**:
- Keep secrets-repo (no deletion, may need later)
- Restore critical credentials from backups
- Remove secrets-repo references from index
- Test SSH/GPG keys still work from original locations

**Phase 4 Rollback**:
- Not recommended (breaking changes)
- If necessary: Restore Phase 3 state entirely
- Requires manual credential restoration

### 10. Open Questions & Decision Framework

**Decision Criteria**:
- Security: Does it improve or maintain security posture?
- Usability: Does it reduce friction for common workflows?
- Complexity: Can it be implemented and maintained reasonably?
- Cost: What's the operational overhead (time, infrastructure)?

**1. GPG Encryption for Secrets-Repo**

Should secrets-repo credentials be GPG-encrypted at rest, or is OS-level encryption sufficient?

| Aspect | GPG Encryption | OS-Level Only |
|--------|---------------|---------------|
| Security | Defense in depth, survives server compromise | Single layer (disk encryption) |
| Usability | Requires GPG passphrase entry | Transparent, no extra steps |
| Complexity | GPG key management, rotation, backup | Minimal |
| Cost | ~8 hours implementation + ongoing key management | Zero |

**Decision**: Make GPG encryption **optional** with flag `--gpg-encrypt`.
- Default: OS-level encryption only (simpler, sufficient for most users)
- Advanced: GPG encryption via `datacore creds backup --gpg` (for critical credentials)
- Rationale: Progressive security - start simple, layer on complexity as needed

**2. Credential Rotation Automation**

Should rotation be automated or manual?

| Aspect | Automated | Manual |
|--------|-----------|--------|
| Security | Enforces policy, reduces forgotten rotations | Requires discipline |
| Usability | Zero-friction once setup | Requires running command |
| Complexity | Requires provider API integration for all services | Checklist-based, low complexity |
| Cost | ~40 hours initial + provider API breakage risk | ~6 hours for checklist command |

**Decision**: Start **manual** with `datacore creds rotate` checklist, automate in Phase 2.
- Phase 1: Manual rotation with guided checklist (low risk, fast to ship)
- Phase 2: Automated rotation for select providers (GitHub, AWS) via API
- Rationale: Manual is safer during initial rollout, automation after stability proven

**3. Team Credentials Management**

How should team spaces (3-fds) handle shared credentials?

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| **A: Team Secrets-Repo** | Same pattern as personal, full control | Requires separate infrastructure, sync complexity | 6/10 |
| **B: Shared .datacore/env/** | Simple, no new infrastructure | Access control issues, all-or-nothing | 4/10 |
| **C: GitHub Secrets + Index** | Industry standard for CI/CD, documented in index | Split between GitHub and index, not DRY | 8/10 |

**Decision**: Option C (GitHub Secrets for automation, documented index for development)
- Production credentials: GitHub Secrets (used in CI/CD)
- Development credentials: Documented in index (developers obtain locally)
- Rationale: Leverages existing GitHub infrastructure, clear separation of prod/dev

**Closure Condition**: When Phase 1 complete and team credentials in use, validate approach with team

**4. Cloud Backup for Secrets-Repo**

Should secrets-repo support encrypted cloud backup?

| Aspect | Cloud Backup | USB Drive Only |
|--------|--------------|----------------|
| Security | Third-party dependency, encrypted at rest | Fully controlled, no third party |
| Usability | Automatic, accessible anywhere | Manual, requires physical access |
| Complexity | Cloud provider integration (AWS S3, etc.) | Minimal, manual copy |
| Cost | Cloud storage fees (~$5/month) | USB drive (~$30 one-time) |

**Decision**: **Manual USB backup primary**, cloud backup optional.
- Required: Monthly backup to encrypted USB drive (stored in safe)
- Optional: `datacore creds backup --cloud` for encrypted S3 upload
- Rationale: USB backup sufficient for disaster recovery, cloud adds convenience not necessity

**Closure Condition**: After 3 months, review backup usage patterns and cloud adoption

**5. Credential Generation Support**

Should `datacore creds add` support generating credentials (e.g., SSH keys, API keys)?

| Aspect | Built-in Generation | Manual Only |
|--------|---------------------|-------------|
| Security | Ensures strong generation (entropy, length) | Depends on user's method |
| Usability | One-stop-shop convenience | Requires external tools |
| Complexity | Provider-specific logic (SSH, GPG, random tokens) | Zero additional code |
| Cost | ~20 hours for 5 common types | Zero |

**Decision**: **Phase 2 feature**, start with manual generation.
- Phase 1: `datacore creds add` prompts for credential value (manual entry)
- Phase 2: Add `--generate` flag for SSH keys, random tokens
- Rationale: Manual entry is core workflow, generation is enhancement

**Supported generation types (Phase 2)**:
- SSH keys: `datacore creds add my-ssh-key --generate --type ssh_key`
- Random tokens: `datacore creds add my-token --generate --type api_key --length 32`
- GPG keys: `datacore creds add my-gpg-key --generate --type gpg_key`

**General Decision Framework for Future Questions**:

1. **Does it solve a real problem?** (user story, incident)
2. **Can it be deferred?** (ship without it, add later)
3. **What's the simplest solution?** (avoid over-engineering)
4. **Is it reversible?** (can we change course?)
5. **What's the maintenance burden?** (annual cost to maintain)

**Closure Process**:
- Open questions remain open until Phase 1 deployment
- After 30 days in production, evaluate actual usage
- Make final decision based on data, not speculation

---

## References

- [DIP-0001: Contribution Model](DIP-0001-contribution-model.md) - Fork-and-overlay pattern
- [DIP-0002: Layered Context Pattern](DIP-0002-layered-context-pattern.md) - Privacy layers
- [DIP-0009: GTD Specification](DIP-0009-gtd-specification.md) - Org-mode conventions
- [DIP-0015: Semantic Organization](DIP-0015-semantic-organization.md) - File handling patterns
- [DIP-0016: Agent Registry](DIP-0016-agent-registry.md) - Command discoverability and registry patterns

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-15 | 0.1.0 | Initial draft |
