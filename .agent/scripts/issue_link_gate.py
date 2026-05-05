#!/usr/bin/env python3
"""
GitHub Issue Link Enforcement Gate

Ensures that any PR from a `task/REQ-*` branch includes a
`Closes #NNN` reference in its body, matching the GitHub Issue
number from the requirement spec file.

When the PR is merged, GitHub automatically closes the linked issue.
This eliminates the manual `gh issue close` step entirely.

Usage:
    python3 .agent/scripts/issue_link_gate.py . --pr 451
    python3 .agent/scripts/issue_link_gate.py . --pr 451 --branch task/REQ-L2-08-foo
"""

import argparse
import json
import os
import re
import subprocess
import sys


def extract_req_id(branch_name: str) -> str | None:
    """Extract REQ-ID from a branch name."""
    match = re.search(r'(REQ-[A-Za-z0-9]+-[0-9a-z]+)', branch_name)
    return match.group(1).upper() if match else None


def get_issue_from_spec(req_id: str) -> int | None:
    """Read the spec file and extract the GitHub Issue number."""
    spec_path = f'docs/requirements/{req_id}.md'
    if not os.path.exists(spec_path):
        return None

    with open(spec_path, 'r') as f:
        content = f.read()

    # Match patterns like: **GitHub Issue:** #123 or GitHub Issue: #123
    match = re.search(r'\*?\*?GitHub Issue:?\*?\*?\s*#(\d+)', content)
    return int(match.group(1)) if match else None


def get_pr_body(pr_number: str) -> str:
    """Get the PR body via GitHub REST API (avoids gh CLI Projects Classic bug)."""
    # Try REST API first (more reliable in CI)
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN', '')
    repo = os.environ.get('GITHUB_REPOSITORY', '')

    if token and repo:
        try:
            import urllib.request
            url = f'https://api.github.com/repos/{repo}/pulls/{pr_number}'
            req = urllib.request.Request(url, headers={
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json',
            })
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                return data.get('body', '') or ''
        except Exception as e:
            print(f'   ⚠️ REST API fallback failed: {e}')

    # Fallback: gh CLI (may fail due to Projects Classic deprecation)
    result = subprocess.run(
        ['gh', 'pr', 'view', pr_number, '--json', 'body'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f'   ⚠️ gh CLI stderr: {result.stderr.strip()}')
        return ''
    try:
        data = json.loads(result.stdout)
        return data.get('body', '')
    except json.JSONDecodeError:
        return ''


def get_pr_branch(pr_number: str) -> str:
    """Get the head branch of a PR."""
    result = subprocess.run(
        ['gh', 'pr', 'view', pr_number, '--json', 'headRefName'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return ''
    try:
        data = json.loads(result.stdout)
        return data.get('headRefName', '')
    except json.JSONDecodeError:
        return ''


def body_has_close_ref(body: str, issue_num: int) -> bool:
    """Check if PR body contains Closes/Fixes #NNN."""
    pattern = rf'(?:closes|fixes|resolves)\s+#?{issue_num}\b'
    return bool(re.search(pattern, body, re.IGNORECASE))


def main():
    parser = argparse.ArgumentParser(description='GitHub issue link enforcement')
    parser.add_argument('project_root', help='Project root directory')
    parser.add_argument('--pr', required=True, help='PR number to check')
    parser.add_argument('--branch', default='', help='Override branch name')
    args = parser.parse_args()

    os.chdir(args.project_root)

    # Get branch name
    branch = args.branch if args.branch else get_pr_branch(args.pr)

    if not branch.startswith('task/REQ-'):
        print('✅ Not a task/REQ-* branch. Issue link gate skipped.')
        sys.exit(0)

    req_id = extract_req_id(branch)
    if not req_id:
        print(f'⚠️  Could not extract REQ-ID from branch: {branch}. Skipping.')
        sys.exit(0)

    print(f'🔗 Checking issue link for {req_id} in PR #{args.pr}...')

    # Get issue number from spec file
    issue_num = get_issue_from_spec(req_id)
    if issue_num is None:
        # Spec file may have been deleted by spec-exhaustion step, or
        # may not have an issue number. Warn but pass.
        print(f'⚠️  No GitHub Issue found in docs/requirements/{req_id}.md.')
        print(f'   Passing with warning — ensure issue is closed manually.')
        sys.exit(0)

    print(f'   Found GitHub Issue: #{issue_num}')

    # Get PR body
    pr_body = get_pr_body(args.pr)
    if not pr_body:
        print(f'❌ ISSUE-LINK Gate FAILED')
        print(f'')
        print(f'   Could not read PR #{args.pr} body.')
        print(f'   Ensure `gh` is authenticated and the PR exists.')
        sys.exit(1)

    # Check for closing reference
    if body_has_close_ref(pr_body, issue_num):
        print(f'✅ ISSUE-LINK Gate PASSED')
        print(f'   PR #{args.pr} body contains closing reference for #{issue_num}.')
        print(f'   Issue will auto-close on merge.')
        sys.exit(0)

    print(f'❌ ISSUE-LINK Gate FAILED')
    print(f'')
    print(f'   PR #{args.pr} body does NOT contain "Closes #{issue_num}".')
    print(f'')
    print(f'   📋 Rule: Every /implement-req PR must link its GitHub Issue')
    print(f'   so it auto-closes on merge.')
    print(f'')
    print(f'   Fix: Update your PR body to include "Closes #{issue_num}":')
    print(f'     gh pr edit {args.pr} --body "Implements {req_id}. Closes #{issue_num}"')
    sys.exit(1)


if __name__ == '__main__':
    main()
