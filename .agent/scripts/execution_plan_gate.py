#!/usr/bin/env python3
"""
EXECUTION-PLAN.md Co-Change Enforcement Gate

Ensures that any PR from a `task/REQ-*` branch also updates
docs/EXECUTION-PLAN.md. Handles both workflow types:

  /create-req    → REQ must APPEAR in Step 1 (new [ ] or [x] entry)
  /implement-req → REQ must be marked [x] in Step 2

Detection: The plan has two sections — Step 1 (/create-req) and
Step 2 (/implement-req). The script checks the /implement-req lines
in Step 2 to determine if the REQ existed before and whether it's
now marked [x]. Step 1 entries are informational (create-req adds
them), Step 2 entries are executable (implement-req completes them).

Usage:
    python3 .agent/scripts/execution_plan_gate.py . --base origin/main
    python3 .agent/scripts/execution_plan_gate.py . --branch task/REQ-L2-08-foo
"""

import argparse
import os
import re
import subprocess
import sys

EXECUTION_PLAN = 'docs/EXECUTION-PLAN.md'

# Section markers in EXECUTION-PLAN.md
STEP2_MARKER = '## Step 2:'


def get_current_branch() -> str:
    """Get the current git branch name."""
    result = subprocess.run(
        ['git', 'branch', '--show-current'],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def extract_req_id(branch_name: str) -> str | None:
    """Extract REQ-ID from a branch name like task/REQ-L2-08-agent-publishing."""
    match = re.search(r'(REQ-[A-Za-z0-9]+-[0-9a-z]+)', branch_name)
    return match.group(1).upper() if match else None


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


def get_file_from_ref(ref: str, filepath: str) -> str:
    """Get a file's content from a specific git ref (e.g. origin/main)."""
    result = subprocess.run(
        ['git', 'show', f'{ref}:{filepath}'],
        capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else ''


def split_sections(content: str) -> tuple[str, str]:
    """Split content into Step 1 and Step 2 sections."""
    idx = content.find(STEP2_MARKER)
    if idx == -1:
        return content, ''
    return content[:idx], content[idx:]


def check_req_in_section(req_id: str, section: str) -> tuple[str, str]:
    """
    Check status of a REQ in a section.
    Returns (status, line) where status is 'complete', 'incomplete', or 'not_found'.
    """
    for line in section.split('\n'):
        if req_id in line:
            if re.search(r'- \[x\]', line):
                return 'complete', line.strip()
            elif re.search(r'- \[ \]', line):
                return 'incomplete', line.strip()
    return 'not_found', ''


def req_in_content(req_id: str, content: str) -> bool:
    """Check if a REQ-ID appears anywhere in the given content."""
    return req_id in content


def main():
    parser = argparse.ArgumentParser(description='EXECUTION-PLAN.md co-change enforcement')
    parser.add_argument('project_root', help='Project root directory')
    parser.add_argument('--base', default='origin/main', help='Base branch to diff against')
    parser.add_argument('--branch', default='', help='Override branch name (for CI)')
    args = parser.parse_args()

    os.chdir(args.project_root)

    branch = args.branch if args.branch else get_current_branch()

    # Only enforce on task/REQ-* branches
    if not branch.startswith('task/REQ-'):
        print('✅ Not a task/REQ-* branch. Execution plan gate skipped.')
        sys.exit(0)

    req_id = extract_req_id(branch)
    if not req_id:
        print(f'⚠️  Could not extract REQ-ID from branch: {branch}. Skipping.')
        sys.exit(0)

    print(f'📋 Checking EXECUTION-PLAN.md for {req_id}...')

    changed_files = get_changed_files(args.base)

    # ── CHECK 1: Was EXECUTION-PLAN.md modified? ──
    if EXECUTION_PLAN not in changed_files:
        print(f'❌ EXECUTION-PLAN Gate FAILED')
        print(f'')
        print(f'   Branch: {branch}')
        print(f'   REQ:    {req_id}')
        print(f'')
        print(f'   {EXECUTION_PLAN} was NOT updated in this changeset.')
        print(f'')
        print(f'   📋 Rule: Any /create-req or /implement-req PR MUST update')
        print(f'   {EXECUTION_PLAN}.')
        print(f'')
        print(f'   Fix: Update the plan, then:')
        print(f'   git add {EXECUTION_PLAN} && git commit --amend --no-edit')
        sys.exit(1)

    # ── CHECK 2: Determine workflow type via Step 2 section ──
    base_content = get_file_from_ref(args.base, EXECUTION_PLAN)
    _, base_step2 = split_sections(base_content)

    with open(EXECUTION_PLAN, 'r') as f:
        head_content = f.read()
    head_step1, head_step2 = split_sections(head_content)

    # Check if REQ existed in Step 2 of the BASE version
    req_in_base_step2 = req_in_content(req_id, base_step2)

    if req_in_base_step2:
        # ── IMPLEMENT-REQ path ──
        # REQ was already in Step 2 before this PR → must now be [x]
        status, line = check_req_in_section(req_id, head_step2)

        if status == 'complete':
            print(f'✅ EXECUTION-PLAN Gate PASSED (implement-req)')
            print(f'   {req_id} is marked [x] in Step 2:')
            print(f'     {line}')
            sys.exit(0)
        elif status == 'incomplete':
            print(f'❌ EXECUTION-PLAN Gate FAILED')
            print(f'')
            print(f'   {EXECUTION_PLAN} was modified but {req_id} is still [ ] in Step 2:')
            print(f'     {line}')
            print(f'')
            print(f'   This is an /implement-req branch (REQ already in the plan).')
            print(f'   Mark it [x] with the PR number:')
            print(f'     - [x] `/implement-req {req_id}` — ... (**PR #NNN**)')
            sys.exit(1)
        else:
            # REQ was in Step 2 base but removed from Step 2 HEAD — unusual
            print(f'⚠️  {req_id} was in Step 2 but is now missing. Passing with warning.')
            sys.exit(0)
    else:
        # ── CREATE-REQ path ──
        # REQ was NOT in Step 2 before → this is a new REQ being added
        # It must appear in Step 1 AND have a /implement-req entry in Step 2
        if req_in_content(req_id, head_content):
            # Find the line for display
            status, line = check_req_in_section(req_id, head_step1)
            if status == 'not_found':
                status, line = check_req_in_section(req_id, head_step2)

            # ── CRITICAL: Verify /implement-req entry exists in Step 2 ──
            implement_pattern = f'/implement-req {req_id}'
            if implement_pattern not in head_step2:
                print(f'❌ EXECUTION-PLAN Gate FAILED (create-req — Step 2 MISSING)')
                print(f'')
                print(f'   {req_id} was added to Step 1 (create-req formalization):')
                if line:
                    print(f'     {line}')
                print(f'')
                print(f'   ⛔ BUT no /implement-req entry was added to Step 2!')
                print(f'   Every new REQ MUST also be added to Step 2 so it can')
                print(f'   be found and executed by /implement-req later.')
                print(f'')
                print(f'   Fix: Add this line to the correct Wave in Step 2:')
                print(f'     - [ ] `/implement-req {req_id}` — [description]')
                print(f'')
                print(f'   Then: git add {EXECUTION_PLAN} && git commit --amend --no-edit')
                sys.exit(1)

            print(f'✅ EXECUTION-PLAN Gate PASSED (create-req)')
            print(f'   {req_id} added to plan:')
            if line:
                print(f'     {line}')
            # Show the Step 2 entry too for confirmation
            for s2_line in head_step2.split('\n'):
                if implement_pattern in s2_line:
                    print(f'   Step 2: {s2_line.strip()}')
                    break
            sys.exit(0)
        else:
            print(f'❌ EXECUTION-PLAN Gate FAILED')
            print(f'')
            print(f'   {EXECUTION_PLAN} was modified but {req_id} does not appear in it.')
            print(f'')
            print(f'   This appears to be a /create-req branch (new REQ).')
            print(f'   Add the REQ to BOTH sections:')
            print(f'     Step 1: - [x] ... → {req_id}')
            print(f'     Step 2: - [ ] `/implement-req {req_id}` — [description]')
            sys.exit(1)


if __name__ == '__main__':
    main()
