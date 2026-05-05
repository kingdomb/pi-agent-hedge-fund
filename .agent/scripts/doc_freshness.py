#!/usr/bin/env python3
"""
REQ-OPS-12: Documentation Freshness Enforcer

Updates `last_verified` in YAML frontmatter and DOCS_MAP table for modified docs.
STRICT SCOPING: Only touches YAML frontmatter blocks and DOCS_MAP table rows.
Never modifies body text.

Usage:
    python3 doc_freshness.py --staged                           # Pre-commit mode
    python3 doc_freshness.py --files docs/guides/GUIDE-AUTH.md  # Specific files
    python3 doc_freshness.py --staged --dry-run                 # Preview changes
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import date
from typing import Dict, List


def get_staged_docs() -> List[str]:
    """Get list of staged .md files under docs/."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '--', 'docs/*.md', 'docs/**/*.md'],
        capture_output=True, text=True
    )
    files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
    # Filter to only .md files (extra safety)
    return [f for f in files if f.endswith('.md')]


def update_frontmatter_date(filepath: str, today: str, dry_run: bool = False) -> dict:
    """
    Update `last_verified` field in YAML frontmatter.
    STRICT: Only modifies content between the --- delimiters at the top of the file.
    """
    if not os.path.exists(filepath):
        return {'status': 'error', 'message': f'File not found: {filepath}'}

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    # Check for YAML frontmatter
    if not lines or lines[0].strip() != '---':
        return {'status': 'skipped', 'message': f'{os.path.basename(filepath)}: No YAML frontmatter'}

    # Find the closing ---
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break

    if end_idx == -1:
        return {'status': 'skipped', 'message': f'{os.path.basename(filepath)}: Malformed frontmatter'}

    # Update last_verified in frontmatter only
    frontmatter: List[str] = lines[1:end_idx]
    updated = False
    for i, line in enumerate(frontmatter):
        if line.startswith('last_verified:'):
            old_date = line.split(':', 1)[1].strip()
            if old_date != today:
                frontmatter[i] = f'last_verified: {today}'
                updated = True
            break

    if not updated:
        return {'status': 'skipped', 'message': f'{os.path.basename(filepath)}: Date already current'}

    if dry_run:
        return {'status': 'dry-run', 'message': f'{os.path.basename(filepath)}: Would update last_verified → {today}'}

    # Reconstruct file
    new_content = '\n'.join(lines[0:1] + frontmatter + lines[end_idx:])
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {'status': 'updated', 'message': f'{os.path.basename(filepath)}: last_verified → {today}'}


def update_docs_map(docs_map_path: str, modified_files: List[str], today: str, dry_run: bool = False) -> List[Dict[str, str]]:
    """
    Update Last Verified dates in DOCS_MAP table for modified files.
    STRICT: Only modifies table row cells matching the file's relative path.
    """
    results = []

    if not os.path.exists(docs_map_path):
        return [{'status': 'error', 'message': f'DOCS_MAP not found: {docs_map_path}'}]

    with open(docs_map_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Normalize modified file paths to relative paths from docs/
    docs_dir = os.path.dirname(os.path.abspath(docs_map_path))
    rel_paths = set()
    for fp in modified_files:
        abs_fp = os.path.abspath(fp)
        try:
            rel = os.path.relpath(abs_fp, docs_dir)
            rel_paths.add(rel)
        except ValueError:
            continue

    lines = content.split('\n')
    updated_map = False

    for i, line in enumerate(lines):
        # Match table rows with file links
        for rel_path in rel_paths:
            # Check if this table row contains a link to this file
            basename = os.path.basename(rel_path)
            if f']({rel_path})' in line or f']({basename})' in line:
                # Update the date in the Last Verified column
                # Table format: | ... | ✅ YYYY-MM-DD |
                old_line = line
                # Replace date patterns in the last column (after last |)
                line_new = re.sub(
                    r'(✅\s+)(\d{4}-\d{2}-\d{2}|\d{4}-\d{2})(.*?\|)\s*$',
                    f'\\1{today}\\3',
                    line
                )
                # Also handle version-style dates like "✅ v3.4.1 (verified 2026-03-20)"
                if line_new == line:
                    line_new = re.sub(
                        r'(✅\s+v[\d.]+\s+\(verified\s+)\d{4}-\d{2}-\d{2}(\))',
                        f'\\g<1>{today}\\2',
                        line
                    )

                if line_new != old_line:
                    lines[i] = line_new
                    updated_map = True
                    results.append({
                        'status': 'updated' if not dry_run else 'dry-run',
                        'message': f'DOCS_MAP: {basename} → {today}'
                    })
                break

    if updated_map and not dry_run:
        with open(docs_map_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    # Check for orphan files (in docs/ but not in DOCS_MAP)
    for rel_path in rel_paths:
        basename = os.path.basename(rel_path)
        if basename == 'DOCS_MAP.md':
            continue
        if basename not in content:
            results.append({
                'status': 'warning',
                'message': f'⚠️  ORPHAN: {rel_path} is not tracked in DOCS_MAP'
            })

    return results


def main():
    parser = argparse.ArgumentParser(description='Update doc freshness dates (YAML frontmatter + DOCS_MAP)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--staged', action='store_true', help='Process git-staged docs')
    group.add_argument('--files', nargs='+', help='Process specific files')
    parser.add_argument('--docs-map', default='docs/DOCS_MAP.md', help='Path to DOCS_MAP.md')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    args = parser.parse_args()

    today = str(date.today())

    if args.staged:
        files = get_staged_docs()
    else:
        files = [os.path.abspath(f) for f in args.files]

    if not files:
        print('📄 No docs to process')
        sys.exit(0)

    # Filter out DOCS_MAP itself from frontmatter updates (it doesn't have frontmatter)
    doc_files = [f for f in files if os.path.basename(f) != 'DOCS_MAP.md']

    print(f'📄 Processing {len(files)} docs (date: {today})\n')

    # Phase 1: Update YAML frontmatter in each modified doc
    for filepath in doc_files:
        abs_path = os.path.abspath(filepath)
        result = update_frontmatter_date(abs_path, today, dry_run=args.dry_run)
        symbol = {'updated': '✅', 'skipped': '⏭️', 'error': '❌', 'dry-run': '🔍'}.get(result['status'], '?')
        print(f'  {symbol} {result["message"]}')

    # Phase 2: Update DOCS_MAP table dates
    docs_map_path = os.path.abspath(args.docs_map)
    map_results = update_docs_map(docs_map_path, doc_files, today, dry_run=args.dry_run)
    for result in map_results:
        symbol = {'updated': '✅', 'skipped': '⏭️', 'warning': '⚠️', 'error': '❌', 'dry-run': '🔍'}.get(result['status'], '?')
        print(f'  {symbol} {result["message"]}')

    # Check for warnings (orphans)
    warnings = [r for r in map_results if r['status'] == 'warning']
    if warnings:
        print(f'\n⚠️  {len(warnings)} orphan file(s) detected — consider registering in DOCS_MAP')

    print('\n✅ Doc freshness complete')


if __name__ == '__main__':
    main()
