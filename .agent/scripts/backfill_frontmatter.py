#!/usr/bin/env python3
"""
One-time YAML frontmatter backfill for all docs tracked in DOCS_MAP.

Reads DOCS_MAP.md, extracts metadata for each doc, and inserts YAML
frontmatter at the top of files that don't already have it.

Usage:
    python3 backfill_frontmatter.py --docs-map docs/DOCS_MAP.md
    python3 backfill_frontmatter.py --docs-map docs/DOCS_MAP.md --dry-run
"""

import argparse
import os
import re
import sys
from datetime import date


# Map directory paths to category values
DIR_TO_CATEGORY = {
    'architecture': 'architecture',
    'requirements': 'requirements',
    'guides': 'guides',
    'backend': 'backend',
    'frontend': 'frontend',
    'infrastructure': 'infrastructure',
    'operations': 'operations',
    'security': 'security',
    'technical_specs': 'technical_specs',
    'global_references': 'global_references',
    'tech-debt': 'tech-debt',
}


def parse_docs_map(docs_map_path: str) -> list[dict]:
    """
    Parse DOCS_MAP.md and extract metadata for each tracked doc.
    Returns list of dicts with: id, file, description, owner, audience, status, last_verified
    """
    docs_dir = os.path.dirname(os.path.abspath(docs_map_path))
    entries = []

    with open(docs_map_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_category = ''

    for line in lines:
        stripped = line.strip()

        # Detect category headers like "## 📐 Architecture (`architecture/`)"
        cat_match = re.match(r'^##\s+.+\(`?(\w[\w-]*)/?`?\)', stripped)
        if cat_match:
            current_category = cat_match.group(1).rstrip('/')
            continue

        # Detect "Root-Level Docs" section
        if '## 📄 Root-Level Docs' in stripped:
            current_category = 'root'
            continue

        # Parse table rows: | ID | [File](path) | Description | Owner | Audience | Status |
        row_match = re.match(
            r'\|\s*([^|]*?)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|',
            stripped
        )
        if row_match:
            doc_id = row_match.group(1).strip()
            # filename = row_match.group(2).strip()
            rel_path = row_match.group(3).strip()
            description = row_match.group(4).strip()
            owner = row_match.group(5).strip()
            audience = row_match.group(6).strip()
            last_verified_raw = row_match.group(7).strip()

            # Skip header rows
            if doc_id in ('ID', '----', '---'):
                continue

            # Parse status and date from last_verified column
            status = 'verified'
            last_verified = str(date.today())
            if '✅' in last_verified_raw:
                status = 'verified'
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', last_verified_raw)
                if date_match:
                    last_verified = date_match.group(1)
                else:
                    date_match = re.search(r'(\d{4}-\d{2})', last_verified_raw)
                    if date_match:
                        last_verified = date_match.group(1) + '-01'
            elif '🟡' in last_verified_raw:
                status = 'needs-review'
            elif '🔴' in last_verified_raw:
                status = 'drift'
            elif '📝' in last_verified_raw:
                status = 'placeholder'

            # Determine category from directory
            category = current_category
            if category == 'root':
                category = 'root'
            elif category in DIR_TO_CATEGORY:
                category = DIR_TO_CATEGORY[category]

            # Parse audience into list
            audience_list = [a.strip() for a in audience.split(',')]

            abs_path = os.path.normpath(os.path.join(docs_dir, rel_path))

            entries.append({
                'id': doc_id if doc_id != '—' else os.path.splitext(os.path.basename(rel_path))[0],
                'file': abs_path,
                'rel_path': rel_path,
                'description': description,
                'owner': owner,
                'audience': audience_list,
                'status': status,
                'last_verified': last_verified,
                'category': category,
            })

    return entries


def has_frontmatter(filepath: str) -> bool:
    """Check if a file already has YAML frontmatter."""
    with open(filepath, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
    return first_line == '---'


def generate_frontmatter(entry: dict) -> str:
    """Generate YAML frontmatter block for a doc entry."""
    # Escape quotes in description
    desc = entry['description'].replace('"', '\\"')
    title = desc.split('—')[0].strip() if '—' in desc else desc[:80]

    audience_yaml = '\n'.join(f'  - {a}' for a in entry['audience'])

    return f"""---
title: "{title}"
id: {entry['id']}
category: {entry['category']}
audience:
{audience_yaml}
owner: {entry['owner']}
last_verified: {entry['last_verified']}
status: {entry['status']}
---
"""


def backfill_file(entry: dict, dry_run: bool = False) -> dict:
    """Add frontmatter to a single file. Returns result dict."""
    filepath = entry['file']

    if not os.path.exists(filepath):
        return {'status': 'error', 'message': f"File not found: {filepath}"}

    if has_frontmatter(filepath):
        return {'status': 'skipped', 'message': f"Already has frontmatter: {os.path.basename(filepath)}"}

    frontmatter = generate_frontmatter(entry)

    if dry_run:
        return {'status': 'dry-run', 'message': f"Would add frontmatter to: {os.path.basename(filepath)}"}

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter + content)

    return {'status': 'updated', 'message': f"Added frontmatter: {os.path.basename(filepath)}"}


def main():
    parser = argparse.ArgumentParser(description='Backfill YAML frontmatter to tracked docs')
    parser.add_argument('--docs-map', default='docs/DOCS_MAP.md', help='Path to DOCS_MAP.md')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    args = parser.parse_args()

    docs_map_path = os.path.abspath(args.docs_map)
    if not os.path.exists(docs_map_path):
        print(f"Error: DOCS_MAP not found at {docs_map_path}", file=sys.stderr)
        sys.exit(1)

    entries = parse_docs_map(docs_map_path)
    print(f"Found {len(entries)} tracked docs in DOCS_MAP\n")

    counts = {'updated': 0, 'skipped': 0, 'error': 0, 'dry-run': 0}

    for entry in entries:
        result = backfill_file(entry, dry_run=args.dry_run)
        counts[result['status']] = counts.get(result['status'], 0) + 1
        symbol = {'updated': '✅', 'skipped': '⏭️', 'error': '❌', 'dry-run': '🔍'}.get(result['status'], '?')
        print(f"  {symbol} {result['message']}")

    print(f"\nDone: {counts['updated']} updated, {counts['skipped']} already had frontmatter, {counts.get('error', 0)} errors")


if __name__ == '__main__':
    main()
