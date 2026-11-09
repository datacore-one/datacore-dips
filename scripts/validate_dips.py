#!/usr/bin/env python3
"""Validate DIP files: naming, unique numbering, required header fields,
and content hygiene (no credentials, no private-infra or personal leakage).

Structure checks run on DIP-*.md. Content hygiene runs on every Markdown
file in the repository (DIPs, README, drafts, audits).

Content hygiene has two layers:
  1. Generic public patterns (this file): credential formats, private IP
     ranges, personal home paths, real email addresses.
  2. An optional PRIVATE patterns file with installation-specific terms
     (names, hosts, project slugs). It is never committed here, because
     naming those terms in a public file would itself be the leak. Path:
     $DATACORE_PRIVATE_DENYLIST, default
     ~/.datacore/private/customer-denylist.yaml. Skipped when missing.
     Its `forbidden_content` entries are case-insensitive regexes (an
     entry that is not a valid regex is matched literally).

Self-contained (stdlib only; PyYAML used if present) so CI needs no
Datacore installation. Run locally: python3 scripts/validate_dips.py
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r'^DIP-(\d{4})-[a-z0-9-]+\.md$')
REQUIRED_FIELDS = ['**DIP**', '**Title**', '**Status**', '**Created**']
VALID_STATUS = {'Draft', 'Review', 'Accepted', 'Implemented',
                'Superseded', 'Withdrawn'}
DEFAULT_PRIVATE_DENYLIST = '~/.datacore/private/customer-denylist.yaml'

# High-precision credential patterns + private-infra markers that must
# never appear in public specs.
HYGIENE_RE = re.compile(
    r'(AKIA[0-9A-Z]{16}'
    r'|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
    r'|ghp_[A-Za-z0-9]{36}'
    r'|github_pat_[A-Za-z0-9_]{22,}'
    r'|sk-ant-[A-Za-z0-9-]{20,}'
    r'|xox[bap]-[0-9A-Za-z-]{10,}'
    r'|\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'      # any 100.x (incl. Tailscale CGNAT 100.64.0.0/10)
    r'|\b192\.168\.\d{1,3}\.\d{1,3}\b'          # LAN IPs
    r'|\broot@\d{1,3}(?:\.\d{1,3}){3}\b)'       # root login on a literal IPv4
)

# Personal home directories. Placeholders are allowed.
HOME_PLACEHOLDERS = {'you', 'user', 'username', 'name', 'me', 'example',
                     'alice', 'bob', 'shared', 'runner', 'datacore'}
HOME_RE = re.compile(r'/(?:Users|home)/([A-Za-z0-9._-]+)')

# Email addresses. Allowed: reserved example domains (RFC 2606), git
# remotes, and Datacore role addresses.
EMAIL_RE = re.compile(r'(?<![\w.+-])([A-Za-z0-9._%+-]+)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})\b')
EXAMPLE_DOMAIN_RE = re.compile(r'(?:^|\.)example\.(?:com|org|net)$|\.(?:example|test|invalid|localhost)$',
                               re.IGNORECASE)
ROLE_LOCALPARTS = {'noreply', 'no-reply', 'hello', 'info', 'security',
                   'support', 'team', 'contact', 'privacy', 'admin', 'dev'}
ROLE_DOMAINS = {'datacore.one'}
GIT_REMOTES = {('git', 'github.com'), ('git', 'gitlab.com'), ('git', 'bitbucket.org')}


def email_allowed(local: str, domain: str) -> bool:
    domain = domain.lower()
    if EXAMPLE_DOMAIN_RE.search(domain):
        return True
    if (local.lower(), domain) in GIT_REMOTES:
        return True
    if domain in ROLE_DOMAINS and local.lower() in ROLE_LOCALPARTS:
        return True
    # Commit-trailer bot address used across the ecosystem.
    if (local.lower(), domain) == ('noreply', 'anthropic.com'):
        return True
    return False


def _parse_private_yaml(text: str) -> list[str]:
    """Return the forbidden_content list. PyYAML when available, else a
    minimal parser for a top-level `forbidden_content:` block list."""
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        return [str(p) for p in (data.get('forbidden_content') or [])]
    except ImportError:
        pass
    items, inside = [], False
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        if not raw.startswith((' ', '-')):
            inside = raw.split(':', 1)[0].strip() == 'forbidden_content'
            continue
        if inside and raw.lstrip().startswith('- '):
            val = raw.lstrip()[2:].strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in '\'"':
                val = val[1:-1]
            items.append(val)
    return items


def load_private_patterns() -> list[re.Pattern]:
    path = Path(os.path.expanduser(
        os.environ.get('DATACORE_PRIVATE_DENYLIST') or DEFAULT_PRIVATE_DENYLIST))
    if not path.is_file():
        return []
    try:
        entries = _parse_private_yaml(path.read_text(encoding='utf-8'))
    except Exception as exc:  # unreadable file must not pass silently
        raise SystemExit(f'FAIL — private denylist exists but could not be '
                         f'read ({type(exc).__name__})')
    patterns = []
    for entry in entries:
        if not entry:
            continue
        try:
            patterns.append(re.compile(entry, re.IGNORECASE))
        except re.error:
            patterns.append(re.compile(re.escape(entry), re.IGNORECASE))
    return patterns


def content_findings(text: str, private: list[re.Pattern]) -> list[tuple[int, str]]:
    """(line, category) for every hygiene hit. Never returns the value."""
    hits = []

    def line_of(pos: int) -> int:
        return text.count('\n', 0, pos) + 1

    for m in HYGIENE_RE.finditer(text):
        hits.append((line_of(m.start()),
                     'credentials and private-infra addresses must not be public'))
    for m in HOME_RE.finditer(text):
        if m.group(1).lower() not in HOME_PLACEHOLDERS:
            hits.append((line_of(m.start()),
                         'personal home path (use ~/Data or $DATACORE_ROOT)'))
    for m in EMAIL_RE.finditer(text):
        if not email_allowed(m.group(1), m.group(2)):
            hits.append((line_of(m.start()),
                         'real email address (use an example.com address)'))
    for pat in private:
        for m in pat.finditer(text):
            hits.append((line_of(m.start()),
                         'installation-specific term from the private denylist'))
    return sorted(set(hits))


def main() -> int:
    errors = []
    numbers: dict[str, str] = {}
    files = sorted(ROOT.glob('DIP-*.md'))
    if not files:
        print('No DIP files found'); return 1
    private = load_private_patterns()

    for f in files:
        if HYGIENE_RE.search(f.name):
            errors.append(f'{f.name}: filename hygiene violation')
        if not NAME_RE.match(f.name):
            errors.append(f'{f.name}: bad filename (want DIP-NNNN-kebab-slug.md)')
            continue
        num = NAME_RE.match(f.name).group(1)
        if num in numbers:
            errors.append(f'{f.name}: duplicate number with {numbers[num]}')
        numbers[num] = f.name

        head = f.read_text(encoding='utf-8')[:2500]
        for field in REQUIRED_FIELDS:
            if field not in head:
                errors.append(f'{f.name}: missing header field {field}')
        m = re.search(r'\*\*Status\*\*\s*\|\s*(\w+)', head)
        if m and m.group(1) not in VALID_STATUS:
            errors.append(f'{f.name}: invalid Status "{m.group(1)}" '
                          f'(valid: {", ".join(sorted(VALID_STATUS))})')

    scanned = sorted(p for p in ROOT.rglob('*.md')
                     if not any(part.startswith('.') for part in p.relative_to(ROOT).parts))
    for f in scanned:
        rel = f.relative_to(ROOT).as_posix()
        for line, category in content_findings(f.read_text(encoding='utf-8'), private):
            errors.append(f'{rel}: content hygiene violation: line {line} — {category}')

    if errors:
        print(f'FAIL — {len(errors)} problem(s):')
        for e in errors:
            # Filenames and malformed metadata may themselves contain a
            # detected value. Keep diagnostics useful without reproducing it.
            print(f'  ✗ {HYGIENE_RE.sub("[REDACTED]", e)}')
        return 1
    note = (f', private denylist applied ({len(private)} patterns)' if private
            else ', private denylist not found (skipped)')
    print(f'OK — {len(files)} DIPs valid, numbers unique, '
          f'{len(scanned)} files hygiene clean{note}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
