#!/usr/bin/env python3
"""
REQ-OPS-12: Auto-TOC Generator

Generates/updates a table of contents for markdown files exceeding 500 lines.
Uses ## and ### headings to build the TOC. Idempotent — safe to run repeatedly.

Usage (from project root):
    python3 .agent/scripts/toc_generator.py --file <path>           # Process single file
    python3 .agent/scripts/toc_generator.py --file <path> --force    # Force TOC even for short files
    python3 .agent/scripts/toc_generator.py --all --docs-map <path>  # Process all tracked docs
"""

import argparse
import os
import re
import subprocess
import sys
from typing import List, Tuple

TOC_START = '<!-- TOC -->'
TOC_END = '<!-- /TOC -->'
LINE_THRESHOLD = 500


def slugify(text: str) -> str:
    """Convert heading text to GitHub-style anchor slug."""
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars
    slug = re.sub(r'[\s]+', '-', slug)     # Spaces to hyphens
    slug = re.sub(r'-+', '-', slug)        # Collapse multiple hyphens
    return slug.strip('-')


def extract_headings(lines: List[str]) -> List[Tuple[int, str]]:
    """
    Extract ## and ### headings from file lines.
    Returns list of (level, heading_text) tuples.
    Skips headings inside code blocks and the TOC itself.
    """
    headings = []
    in_code_block = False
    in_toc = False

    for line in lines:
        stripped = line.strip()

        # Track code block state (supports both ``` and ~~~)
        if stripped.startswith('```') or stripped.startswith('~~~'):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        # Skip lines inside existing TOC
        if stripped == TOC_START:
            in_toc = True
            continue
        if stripped == TOC_END:
            in_toc = False
            continue
        if in_toc:
            continue

        # FIX: Match against the raw 'line', NOT 'stripped'.
        # Valid markdown headings can only have 0 to 3 leading spaces.
        # If it has 4+ spaces, it is an indented code block, not a heading.
        match = re.match(r'^ {0,3}(#{2,3})\s+(.+)$', line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append((level, text))

    return headings


def build_toc(headings: List[Tuple[int, str]]) -> str:
    """Build markdown TOC from headings list."""
    if not headings:
        return ''

    lines = [TOC_START, '## Table of Contents', '']

    for level, text in headings:
        indent = '  ' * (level - 2)  # ## = no indent, ### = 2 spaces
        slug = slugify(text)
        lines.append(f'{indent}- [{text}](#{slug})')

    lines.append('')
    lines.append(TOC_END)
    return '\n'.join(lines)


def strip_existing_toc(content: str) -> str:
    """Remove existing TOC block and its surrounding padding if present."""
    # Match the TOC block AND the blank lines that pad it
    pattern = re.compile(
        r'\n*' + re.escape(TOC_START) + r'.*?' + re.escape(TOC_END) + r'\n*',
        re.DOTALL
    )
    return pattern.sub('\n', content)


def process_file(filepath: str, force: bool = False) -> dict:
    """
    Process a single file: generate/update TOC if criteria met.
    Returns dict with result info.
    """
    if not os.path.exists(filepath):
        return {'status': 'error', 'message': f'File not found: {filepath}'}

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.splitlines()
    line_count = len(lines)

    # Check threshold (unless forced)
    if line_count <= LINE_THRESHOLD and not force:
        return {
            'status': 'skipped',
            'message': f'{os.path.basename(filepath)}: {line_count} lines (≤{LINE_THRESHOLD}, skipped)',
            'lines': line_count
        }

    # Strip existing TOC before processing
    clean_content = strip_existing_toc(content)
    clean_lines = clean_content.splitlines()

    # Extract headings from clean content
    headings = extract_headings(clean_lines)

    if not headings:
        return {
            'status': 'skipped',
            'message': f'{os.path.basename(filepath)}: No ## or ### headings found',
            'lines': line_count
        }

    # Build new TOC
    toc = build_toc(headings)

    # Insert TOC after the first # heading and its metadata block, but before the
    # first ## content heading. Metadata includes bold key-value lines (**Key:**),
    # blockquotes (>), horizontal rules (---), and blank lines.
    output_lines: List[str] = clean_content.splitlines(keepends=True)

    insert_idx = 0
    found_h1 = False
    in_frontmatter = False

    for i, line in enumerate(output_lines):
        stripped = line.strip()
        # Handle YAML frontmatter
        if i == 0 and stripped == '---':
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == '---':
                in_frontmatter = False
                insert_idx = i + 1
            continue

        # Find first # heading
        if not found_h1 and stripped.startswith('# ') and not stripped.startswith('## '):
            found_h1 = True
            insert_idx = i + 1
            break

    if found_h1:
        # Skip past the metadata preamble (everything between H1 and first ## heading).
        # Metadata lines: blank, bold key-value (**X:**), horizontal rules (---),
        # blockquotes (>), and other non-heading content.
        while insert_idx < len(output_lines):
            stripped = output_lines[insert_idx].strip()  # type: ignore[index]
            # Stop at the first ## or ### heading — TOC goes before it
            if re.match(r'^#{2,3}\s+', stripped):
                # Also capture a preceding --- divider if present
                if insert_idx > 0 and output_lines[insert_idx - 1].strip() == '---':  # type: ignore[index]
                    insert_idx -= 1
                    # Also capture blank line before the ---
                    if insert_idx > 0 and output_lines[insert_idx - 1].strip() == '':  # type: ignore[index]
                        insert_idx -= 1
                break
            insert_idx += 1

    # Reconstruct file: before insertion + TOC + after insertion
    before = ''.join(output_lines[:insert_idx])  # type: ignore[index]
    after = ''.join(output_lines[insert_idx:])  # type: ignore[index]

    # Ensure proper spacing
    if before and not before.endswith('\n'):
        before += '\n'
    new_content = before + '\n' + toc + '\n\n' + after

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {
        'status': 'updated',
        'message': f'{os.path.basename(filepath)}: TOC generated ({len(headings)} headings)',
        'headings': len(headings),
        'lines': line_count
    }


def parse_docs_map(docs_map_path: str) -> List[str]:
    """Parse DOCS_MAP.md to extract tracked file paths."""
    if not os.path.exists(docs_map_path):
        print(f'Error: DOCS_MAP not found at {docs_map_path}', file=sys.stderr)
        sys.exit(1)

    docs_dir = os.path.dirname(docs_map_path)
    files = []

    with open(docs_map_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Match table rows with file links: | ID | [filename](path) | ...
            match = re.search(r'\[.*?\]\(([^)]+\.md)\)', line)
            if match:
                rel_path = match.group(1)
                abs_path = os.path.normpath(os.path.join(docs_dir, rel_path))
                if os.path.exists(abs_path):
                    files.append(abs_path)

    return files


def get_staged_docs() -> List[str]:
    """Get list of staged .md files under docs/."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '--', 'docs/*.md', 'docs/**/*.md'],
        capture_output=True, text=True
    )
    files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip() and f.strip().endswith('.md')]
    return [os.path.abspath(f) for f in files]


def main():
    parser = argparse.ArgumentParser(description='Generate TOC for large markdown files')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', help='Process a single markdown file')
    group.add_argument('--all', action='store_true', help='Process all tracked docs from DOCS_MAP')
    group.add_argument('--staged', action='store_true', help='Process git-staged docs only (pre-commit mode)')
    parser.add_argument('--docs-map', default='docs/DOCS_MAP.md', help='Path to DOCS_MAP.md')
    parser.add_argument('--force', action='store_true', help='Force TOC generation even for short files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')

    args = parser.parse_args()

    if args.file:
        filepath = os.path.abspath(args.file)
        result = process_file(filepath, force=args.force)
        print(result['message'])
        sys.exit(0 if result['status'] != 'error' else 1)

    elif args.staged:
        files = get_staged_docs()
        if not files:
            print('📑 No staged docs to process')
            sys.exit(0)
        print(f'📑 Processing {len(files)} staged docs\n')
        results = {'updated': 0, 'skipped': 0, 'error': 0}
        for filepath in files:
            result = process_file(filepath, force=args.force)
            results[result['status']] = results.get(result['status'], 0) + 1
            print(f"  {result['message']}")
        print(f'\nDone: {results["updated"]} updated, {results["skipped"]} skipped, {results.get("error", 0)} errors')

    elif args.all:
        docs_map_path = os.path.abspath(args.docs_map)
        files = parse_docs_map(docs_map_path)
        print(f'Found {len(files)} tracked docs in DOCS_MAP\n')

        results = {'updated': 0, 'skipped': 0, 'error': 0}
        for filepath in files:
            result = process_file(filepath, force=args.force)
            results[result['status']] = results.get(result['status'], 0) + 1
            print(f"  {result['message']}")

        print(f'\nDone: {results["updated"]} updated, {results["skipped"]} skipped, {results.get("error", 0)} errors')


if __name__ == '__main__':
    main()
