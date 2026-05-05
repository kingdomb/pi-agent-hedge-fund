#!/usr/bin/env python3
"""
REQ-OPS-12: Tests for toc_generator.py
TDD baseline — these tests must FAIL before implementation.
"""
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'toc_generator.py')


class TestTocGenerator(unittest.TestCase):
    """Tests for the TOC generator script."""

    def setUp(self):
        """Create temp directory for test files."""
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temp files."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_file(self, name, lines):
        """Helper: create a file with given lines."""
        path = os.path.join(self.tmpdir, name)
        with open(path, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        return path

    def _run_script(self, *args):
        """Helper: run toc_generator.py with args."""
        cmd = [sys.executable, SCRIPT_PATH] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result

    def test_script_exists(self):
        """toc_generator.py must exist."""
        self.assertTrue(os.path.exists(SCRIPT_PATH), f"Script not found at {SCRIPT_PATH}")

    def test_generates_toc_for_long_file(self):
        """Files >500 lines with ## headings should get a TOC."""
        lines = ['# Test Document']
        lines += ['## Section One', 'Content'] * 50
        lines += ['### Subsection A', 'More content'] * 50
        lines += ['Filler line'] * 400  # Push past 500 lines
        path = self._create_file('long_doc.md', lines)

        result = self._run_script('--file', path)
        self.assertEqual(result.returncode, 0, f"Script failed: {result.stderr}")

        with open(path) as f:
            content = f.read()
        self.assertIn('<!-- TOC -->', content)
        self.assertIn('<!-- /TOC -->', content)
        self.assertIn('Section One', content.split('<!-- /TOC -->')[0])

    def test_skips_short_file(self):
        """Files ≤500 lines should NOT get a TOC."""
        lines = ['# Short Doc', '## Heading One', 'Some content'] * 10
        path = self._create_file('short_doc.md', lines)

        result = self._run_script('--file', path)
        self.assertEqual(result.returncode, 0)

        with open(path) as f:
            content = f.read()
        self.assertNotIn('<!-- TOC -->', content)

    def test_idempotent(self):
        """Running twice on the same file produces identical output."""
        lines = ['# Test Document']
        lines += ['## Section {}'.format(i) for i in range(50)]
        lines += ['Filler line'] * 450
        path = self._create_file('idempotent_doc.md', lines)

        self._run_script('--file', path)
        with open(path) as f:
            first_run = f.read()

        self._run_script('--file', path)
        with open(path) as f:
            second_run = f.read()

        self.assertEqual(first_run, second_run, "TOC generation is not idempotent")

    def test_toc_contains_headings(self):
        """TOC must list ## and ### headings as links."""
        lines = ['# Main Title']
        lines += ['## Architecture Overview']
        lines += ['Content ' * 10] * 100
        lines += ['### Component Design']
        lines += ['More content'] * 100
        lines += ['## Security Model']
        lines += ['Content'] * 300
        path = self._create_file('heading_doc.md', lines)

        self._run_script('--file', path)
        with open(path) as f:
            content = f.read()
        toc_section = content.split('<!-- TOC -->')[1].split('<!-- /TOC -->')[0]
        self.assertIn('Architecture Overview', toc_section)
        self.assertIn('Component Design', toc_section)
        self.assertIn('Security Model', toc_section)

    def test_force_flag_overrides_line_threshold(self):
        """--force flag should generate TOC even for short files."""
        lines = ['# Short Doc', '## Heading One', '## Heading Two', 'Content']
        path = self._create_file('force_doc.md', lines)

        result = self._run_script('--file', path, '--force')
        self.assertEqual(result.returncode, 0)

        with open(path) as f:
            content = f.read()
        self.assertIn('<!-- TOC -->', content)


if __name__ == '__main__':
    unittest.main()
