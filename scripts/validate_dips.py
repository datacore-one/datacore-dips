#!/usr/bin/env python3
"""Validate DIP files: naming, unique numbering, required header fields,
and basic content hygiene (no credentials, no private-infra leakage).

Self-contained (stdlib only) so CI needs no Datacore installation.
Run locally: python3 scripts/validate_dips.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r'^DIP-(\d{4})-[a-z0-9-]+\.md$')
REQUIRED_FIELDS = ['**DIP**', '**Title**', '**Status**', '**Created**']
VALID_STATUS = {'Draft', 'Review', 'Accepted', 'Implemented',
                'Superseded', 'Withdrawn'}
# High-precision credential patterns + private-infra markers that must
# never appear in public specs.
HYGIENE_RE = re.compile(
    r'(AKIA[0-9A-Z]{16}'
    r'|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
    r'|ghp_[A-Za-z0-9]{36}'
    r'|github_pat_[A-Za-z0-9_]{22,}'
    r'|sk-ant-[A-Za-z0-9-]{20,}'
    r'|xox[bap]-[0-9A-Za-z-]{10,}'
    r'|\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'      # Tailscale IPs
    r'|\b192\.168\.\d{1,3}\.\d{1,3}\b)'          # LAN IPs
)


def main() -> int:
    errors = []
    numbers: dict[str, str] = {}
    files = sorted(ROOT.glob('DIP-*.md'))
    if not files:
        print('No DIP files found'); return 1

    for f in files:
        if not NAME_RE.match(f.name):
            errors.append(f'{f.name}: bad filename (want DIP-NNNN-kebab-slug.md)')
            continue
        num = NAME_RE.match(f.name).group(1)
        if num in numbers:
            errors.append(f'{f.name}: duplicate number with {numbers[num]}')
        numbers[num] = f.name

        text = f.read_text(encoding='utf-8')
        head = text[:2500]
        for field in REQUIRED_FIELDS:
            if field not in head:
                errors.append(f'{f.name}: missing header field {field}')
        m = re.search(r'\*\*Status\*\*\s*\|\s*(\w+)', head)
        if m and m.group(1) not in VALID_STATUS:
            errors.append(f'{f.name}: invalid Status "{m.group(1)}" '
                          f'(valid: {", ".join(sorted(VALID_STATUS))})')
        for hit in HYGIENE_RE.finditer(text):
            errors.append(f'{f.name}: content hygiene violation: '
                          f'"{hit.group(0)[:24]}…" — credentials and '
                          f'private-infra addresses must not be public')

    if errors:
        print(f'FAIL — {len(errors)} problem(s):')
        for e in errors:
            print(f'  ✗ {e}')
        return 1
    print(f'OK — {len(files)} DIPs valid, numbers unique, hygiene clean')
    return 0


if __name__ == '__main__':
    sys.exit(main())
