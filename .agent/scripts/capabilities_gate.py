#!/usr/bin/env python3
"""
CAPABILITIES.md Co-Change Enforcement Gate

Ensures that any PR modifying capability-affecting files also updates
docs/CAPABILITIES.md. Uses two detection layers:

  Layer 1: Path-based — known directories that house capabilities
  Layer 2: Content-based — detects capability signals in the actual diff
           (new routes, new services, new endpoints, new components)

This is a SAFETY NET for human PRs. When an AI agent makes changes,
it should proactively update CAPABILITIES.md without needing this gate.

Usage (from project root):
    python3 .agent/scripts/capabilities_gate.py .                    # Check against main
    python3 .agent/scripts/capabilities_gate.py . --base origin/main # Custom base branch
"""

import argparse
import os
import re
import subprocess
import sys

# --- LAYER 1: Path-based detection ---
# Files in these directories are ALWAYS capability-affecting
WATCHED_PATTERNS = [
    # Backend surfaces
    'backend/src/routes/',
    'backend/src/api/',
    'backend/src/server.ts',
    'backend/src/worker.ts',
    # Backend internals that define capabilities
    'backend/src/core/',
    'backend/src/middleware/',
    'backend/src/agents/',
    # Frontend surfaces
    'frontend/src/app/dashboard/',
    'frontend/src/app/login/',
    'frontend/src/components/interview/',
    'frontend/src/components/settings/',
    'frontend/src/components/marketplace/',
    'frontend/src/components/dashboard/',
    'frontend/src/components/gen-ui/',
    # AI brain capabilities
    'ai-os-brain/src/',
    'ai-os-brain/services/',
    # Infrastructure
    'docker-compose',  # catches all docker-compose*.yml variants
]

# Files to NEVER flag (tests, docs, configs, scripts)
IGNORED_PATTERNS = [
    '__tests__/',
    '.test.',
    '.spec.',
    'node_modules/',
    '.agent/',
    'docs/',
    'package.json',
    'tsconfig',
    '.eslint',
]

CAPABILITIES_FILE = 'docs/CAPABILITIES.md'

# --- LAYER 2: Content-based detection ---
# Regex patterns that signal a new capability in a diff
CAPABILITY_SIGNALS = [
    r'router\.(get|post|put|patch|delete)\(',   # New Express route
    r'app\.use\(.*/api/',                         # New route mount
    r'export (class|function|const) \w+Service',  # New service export
    r'export default (function|class)',            # New module export
    r'new Worker\(',                               # New BullMQ worker
    r'export default function \w+Page',            # New Next.js page
    r'def (get|post|put|patch|delete)_',           # New Python endpoint
    r'@app\.(get|post|put|patch|delete)\(',        # FastAPI route
]


def get_changed_files(base: str) -> list[str]:
    """Get list of changed files compared to base branch."""
    result = subprocess.run(
        ['git', 'diff', '--name-only', base, 'HEAD'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD'],
            capture_output=True, text=True
        )
    return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]


def get_diff_content(base: str) -> str:
    """Get the actual diff content for content-based analysis."""
    result = subprocess.run(
        ['git', 'diff', base, 'HEAD', '--diff-filter=ACMR', '-U0'],
        capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else ''


def matches_watched_pattern(filepath: str) -> bool:
    """Check if a file matches any watched pattern."""
    if any(ignored in filepath for ignored in IGNORED_PATTERNS):
        return False
    return any(filepath.startswith(pattern) or pattern in filepath
               for pattern in WATCHED_PATTERNS)


def detect_capability_signals(diff_content: str) -> list[str]:
    """Scan diff for added lines that look like new capabilities."""
    signals_found = []
    for line in diff_content.split('\n'):
        if not line.startswith('+') or line.startswith('+++'):
            continue
        added_line = line[1:]  # type: ignore[index]  # Strip the leading +
        for pattern in CAPABILITY_SIGNALS:
            if re.search(pattern, added_line):
                signals_found.append(added_line.strip())
                break
    return signals_found


def main():
    parser = argparse.ArgumentParser(description='CAPABILITIES.md co-change enforcement')
    parser.add_argument('project_root', help='Project root directory')
    parser.add_argument('--base', default='origin/main', help='Base branch to diff against')
    args = parser.parse_args()

    os.chdir(args.project_root)

    changed_files = get_changed_files(args.base)

    if not changed_files:
        print('✅ No changed files detected. Gate passed.')
        sys.exit(0)

    # Layer 1: Path-based detection
    capability_changes = [f for f in changed_files if matches_watched_pattern(f)]

    # Layer 2: Content-based detection (scan diff for capability signals)
    content_signals: list[str] = []
    if not capability_changes:
        diff_content = get_diff_content(args.base)
        content_signals = detect_capability_signals(diff_content)

    has_capability_change = bool(capability_changes) or bool(content_signals)

    if not has_capability_change:
        print('✅ No capability-affecting changes detected. Gate passed.')
        sys.exit(0)

    # Check if CAPABILITIES.md was also updated
    capabilities_updated = CAPABILITIES_FILE in changed_files

    if capabilities_updated:
        print('✅ CAPABILITIES Gate PASSED')
        if capability_changes:
            print(f'   {len(capability_changes)} capability file(s) changed:')
            for f in capability_changes[:10]:  # type: ignore[index]
                print(f'     • {f}')
            if len(capability_changes) > 10:
                print(f'     ... and {len(capability_changes) - 10} more')
        if content_signals:
            print(f'   {len(content_signals)} capability signal(s) detected in diff:')
            for s in content_signals[:5]:  # type: ignore[index]
                print(f'     • {s[:80]}')
        print(f'   ✅ {CAPABILITIES_FILE} was updated in this changeset.')
        sys.exit(0)

    # FAIL
    print('❌ CAPABILITIES Gate FAILED')
    print('')
    if capability_changes:
        print('   Capability-affecting files modified:')
        for f in capability_changes:
            print(f'     • {f}')
    if content_signals:
        print('   Capability signals detected in diff (new routes/services/endpoints):')
        for s in content_signals[:5]:  # type: ignore[index]
            print(f'     • {s[:80]}')
    print('')
    print(f'   But {CAPABILITIES_FILE} was NOT updated.')
    print('')
    print('   📋 Rule: Any change that adds, removes, or modifies a system capability')
    print(f'   MUST be reflected in {CAPABILITIES_FILE}.')
    print('')
    print(f'   Fix: Update the relevant section in {CAPABILITIES_FILE} and re-push.')
    sys.exit(1)


if __name__ == '__main__':
    main()
