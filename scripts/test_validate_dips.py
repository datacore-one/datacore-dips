"""Stdlib-only regression checks for diagnostics emitted by CI."""
import contextlib
import io
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import validate_dips


class HygieneDiagnostics(unittest.TestCase):
    def test_catalog_statuses_match_referenced_headers(self):
        root = Path(__file__).resolve().parents[1]
        rows = re.findall(r'\| \[\d{4}\]\((DIP-[^)]+)\) \| [^|]+\| ([^|]+)\|',
                          (root / 'README.md').read_text())
        self.assertTrue(rows)
        for filename, catalog_status in rows:
            with self.subTest(dip=filename):
                head = (root / filename).read_text()[:2500]
                status = re.search(r'\*\*Status\*\*\s*\|\s*([^|\n]+)', head).group(1).strip()
                self.assertEqual(catalog_status.strip(), status)


    def test_detected_values_never_enter_diagnostics(self):
        samples = [
            'AKIA' + 'ABCDEFGHIJKLMNOP',
            'ghp_' + 'a' * 36,
            'sk-ant-' + 'b' * 24,
            '100.' + '64.23.45',
            '192.' + '168.23.45',
        ]
        for value in samples:
            for location in ('body', 'status', 'filename'):
                with self.subTest(location=location, family=value.split('_')[0][:4]):
                    with tempfile.TemporaryDirectory() as tmp:
                        root = Path(tmp)
                        name = 'DIP-9999-fixture.md' if location != 'filename' else f'DIP-9999-{value}.md'
                        status = value if location == 'status' else 'Draft'
                        text = f'**DIP** | 9999\n**Title** | Fixture\n**Status** | {status}\n**Created** | 2026-09-11\n'
                        if location == 'body':
                            text += value + '\n'
                        (root / name).write_text(text)
                        result, out = _run(root)
                        self.assertEqual(result, 1)
                        self.assertNotIn(value, out)
                        self.assertNotIn(value[:24], out)
                        if location == 'body':
                            self.assertIn('line 5', out)

    def test_valid_specification_still_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'DIP-9999-fixture.md').write_text(
                '**DIP** | 9999\n**Title** | Fixture\n**Status** | Draft\n**Created** | 2026-09-11\n')
            self.assertEqual(_run(root)[0], 0)


def _run(root, env_denylist=None):
    """Run the validator on a fixture root; returns (exit code, output)."""
    output = io.StringIO()
    env = {'DATACORE_PRIVATE_DENYLIST': env_denylist or str(root / 'no-such-denylist.yaml')}
    with patch.object(validate_dips, 'ROOT', root), patch.dict(os.environ, env), \
            contextlib.redirect_stdout(output):
        result = validate_dips.main()
    return result, output.getvalue()


HEADER = '**DIP** | 9999\n**Title** | Fixture\n**Status** | Draft\n**Created** | 2026-09-11\n'


class PublicPatterns(unittest.TestCase):
    def check(self, body, should_fail, filename='DIP-9999-fixture.md'):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'DIP-9999-fixture.md').write_text(HEADER + (body if filename.startswith('DIP-9999') else ''))
            if not filename.startswith('DIP-9999'):
                (root / filename).parent.mkdir(parents=True, exist_ok=True)
                (root / filename).write_text(body)
            result, out = _run(root)
            self.assertEqual(result, 1 if should_fail else 0, out)
            return out

    def test_home_paths(self):
        self.check('see /Users/' + 'jdoe/Data\n', True)
        self.check('see /home/' + 'jdoe/Data\n', True)
        self.check('see /Users/you/Data and /home/user/Data and ~/Data\n', False)

    def test_emails(self):
        out = self.check('mail ' + 'jdoe' + '@' + 'realcorp.io\n', True)
        self.assertNotIn('realcorp', out)
        self.check('mail alice@example.com, bob@team.example.org, git@github.com, '
                   'security@datacore.one, noreply@anthropic.com\n', False)
        self.check('personal ' + 'jdoe' + '@' + 'datacore.one\n', True)

    def test_cgnat_and_root_ip(self):
        self.check('node ' + '100.' + '101.2.3\n', True)
        self.check('ssh ' + 'root@' + '203.0.113.7\n', True)

    def test_non_dip_markdown_is_scanned(self):
        self.check('see /Users/' + 'jdoe/x\n', True, filename='audits/report.md')
        self.check('see /Users/' + 'jdoe/x\n', True, filename='README.md')


class PrivateDenylist(unittest.TestCase):
    def test_private_terms_fail_without_echoing_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deny = root / 'private.yaml'
            deny.write_text("version: 1\nforbidden_content:\n- Zorblax Corp\n- 'host-[0-9]+'\n")
            (root / 'DIP-9999-fixture.md').write_text(HEADER + 'met zorblax corp\non host-42\n')
            result, out = _run(root, str(deny))
            self.assertEqual(result, 1)
            self.assertEqual(out.count('private denylist'), 2)
            self.assertNotIn('orblax', out.lower())
            self.assertNotIn('host-42', out)

    def test_missing_private_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'DIP-9999-fixture.md').write_text(HEADER)
            result, out = _run(root)
            self.assertEqual(result, 0)
            self.assertIn('not found (skipped)', out)

    def test_fallback_parser_matches_yaml(self):
        text = "version: 1\nforbidden_paths:\n- '**/x*'\nforbidden_content:\n- A b\n- \"c-d\"\nother:\n- e\n"
        with patch.dict('sys.modules', {'yaml': None}):
            self.assertEqual(validate_dips._parse_private_yaml(text), ['A b', 'c-d'])


if __name__ == '__main__':
    unittest.main()
