"""Stdlib-only regression checks for diagnostics emitted by CI."""
import contextlib
import io
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
                        output = io.StringIO()
                        with patch.object(validate_dips, 'ROOT', root), contextlib.redirect_stdout(output):
                            result = validate_dips.main()
                        self.assertEqual(result, 1)
                        self.assertNotIn(value, output.getvalue())
                        self.assertNotIn(value[:24], output.getvalue())
                        if location == 'body':
                            self.assertIn('line 5', output.getvalue())

    def test_valid_specification_still_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'DIP-9999-fixture.md').write_text(
                '**DIP** | 9999\n**Title** | Fixture\n**Status** | Draft\n**Created** | 2026-09-11\n')
            with patch.object(validate_dips, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(validate_dips.main(), 0)


if __name__ == '__main__':
    unittest.main()
