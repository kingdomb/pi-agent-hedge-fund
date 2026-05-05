#!/usr/bin/env python3
"""
Local Preflight — Simulates ALL CI governance gates before push.

Runs the same checks that GitHub Actions runs on pull_request events,
but locally, so you catch failures before wasting CI time.

Usage:
    python3 .agent/scripts/preflight.py .
    python3 .agent/scripts/preflight.py . --pr 454       # include issue-link check
    npm run preflight                                     # via npm script
    npm run preflight -- --pr 454                         # with PR number

Gates (mirrors ci.yml):
    1. governance-audit     — Board of Directors structural check
    2. capabilities-gate    — CAPABILITIES.md co-change rule
    3. execution-plan-gate  — EXECUTION-PLAN.md updated for REQ branches
    4. checkpoint-audit     — Full checkpoint chain validation
    5. issue-link-gate      — PR body has Closes #NNN (requires --pr)
"""

import argparse
import os
import re
import subprocess
import sys
import time


# ── ANSI colors ──────────────────────────────────────────────────────────────

class C:
    BOLD  = '\033[1m'
    GREEN = '\033[92m'
    RED   = '\033[91m'
    YELLOW = '\033[93m'
    CYAN  = '\033[96m'
    DIM   = '\033[2m'
    RESET = '\033[0m'


def header(msg: str) -> None:
    print(f'\n{C.BOLD}{C.CYAN}{"═" * 60}{C.RESET}')
    print(f'{C.BOLD}{C.CYAN}  {msg}{C.RESET}')
    print(f'{C.BOLD}{C.CYAN}{"═" * 60}{C.RESET}\n')


def section(num: int, total: int, name: str) -> None:
    print(f'{C.BOLD}[{num}/{total}] {name}{C.RESET}')


def passed(msg: str) -> None:
    print(f'  {C.GREEN}✅ PASS:{C.RESET} {msg}')


def failed(msg: str) -> None:
    print(f'  {C.RED}❌ FAIL:{C.RESET} {msg}')


def skipped(msg: str) -> None:
    print(f'  {C.YELLOW}⏭️  SKIP:{C.RESET} {msg}')


def info(msg: str) -> None:
    print(f'  {C.DIM}ℹ️  {msg}{C.RESET}')


# ── Utilities ────────────────────────────────────────────────────────────────

def get_branch() -> str:
    """Get current git branch name."""
    result = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def extract_req_id(branch: str) -> str | None:
    """Extract REQ-ID from branch name."""
    match = re.search(r'(REQ-[A-Za-z0-9]+-[0-9a-z]+)', branch, re.IGNORECASE)
    return match.group(1).upper() if match else None


def is_req_branch(branch: str) -> bool:
    """Check if this is a task/REQ-* branch."""
    return branch.startswith('task/REQ-')


def run_gate(name: str, cmd: list[str], cwd: str) -> bool:
    """Run a gate command and return True if it passed."""
    result = subprocess.run(
        cmd, cwd=cwd,
        capture_output=True, text=True
    )

    # Print output (indented)
    for line in result.stdout.strip().split('\n'):
        if line.strip():
            print(f'  {C.DIM}{line}{C.RESET}')

    if result.returncode != 0:
        # Print stderr too if there's relevant info
        for line in result.stderr.strip().split('\n'):
            if line.strip() and 'ExperimentalWarning' not in line:
                print(f'  {C.RED}{line}{C.RESET}')
        return False
    return True


# ── Gate runners ─────────────────────────────────────────────────────────────

def gate_governance(root: str) -> bool:
    """Gate 1: Governance Audit (always runs)."""
    return run_gate(
        'governance-audit',
        ['python3', '.agent/scripts/governance_audit.py', '.'],
        root
    )


def gate_capabilities(root: str) -> bool:
    """Gate 2: CAPABILITIES.md co-change (PR-only, all branches)."""
    return run_gate(
        'capabilities-gate',
        ['python3', '.agent/scripts/capabilities_gate.py', '.', '--base', 'origin/main'],
        root
    )


def gate_execution_plan(root: str, branch: str) -> bool:
    """Gate 3: EXECUTION-PLAN.md updated (REQ branches only)."""
    return run_gate(
        'execution-plan-gate',
        ['python3', '.agent/scripts/execution_plan_gate.py', '.', '--base', 'origin/main', '--branch', branch],
        root
    )


def gate_checkpoint(root: str, req_id: str) -> bool:
    """Gate 4: Full checkpoint chain validation (REQ branches only)."""
    return run_gate(
        'checkpoint-audit',
        ['python3', '.agent/scripts/enforce_create_req.py', '.', '--req', req_id, '--validate-all'],
        root
    )


def gate_issue_link(root: str, pr_number: str, branch: str) -> bool:
    """Gate 5: PR body Closes #NNN reference (REQ branches only, needs --pr)."""
    return run_gate(
        'issue-link-gate',
        ['python3', '.agent/scripts/issue_link_gate.py', '.', '--pr', pr_number, '--branch', branch],
        root
    )


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Local preflight — simulate CI governance gates before push'
    )
    parser.add_argument('project_root', help='Project root directory')
    parser.add_argument('--pr', default='', help='PR number (enables issue-link gate)')
    args = parser.parse_args()

    root = os.path.abspath(args.project_root)
    os.chdir(root)

    branch = get_branch()
    req_id = extract_req_id(branch)
    is_req = is_req_branch(branch)

    # Determine how many gates will run
    total_gates = 2  # governance + capabilities always run
    if is_req:
        total_gates += 2  # execution-plan + checkpoint
    if is_req and args.pr:
        total_gates += 1  # issue-link

    header(f'PREFLIGHT — {branch}')
    info(f'Branch:  {branch}')
    info(f'REQ:     {req_id or "(none)"}')
    info(f'PR:      #{args.pr}' if args.pr else 'PR:      (not specified — use --pr N for issue-link gate)')
    info(f'Gates:   {total_gates}')
    print()

    start = time.time()
    results: list[tuple[str, bool | None]] = []
    gate_num = 0

    # ── Gate 1: Governance Audit ──
    gate_num += 1
    section(gate_num, total_gates, '🏛️  Governance Audit')
    ok = gate_governance(root)
    results.append(('Governance Audit', ok))
    passed('Structural checks passed') if ok else failed('Governance audit failed — fix before proceeding')
    print()

    # ── Gate 2: Capabilities Gate ──
    gate_num += 1
    section(gate_num, total_gates, '📋 Capabilities Gate')
    ok = gate_capabilities(root)
    results.append(('Capabilities Gate', ok))
    passed('CAPABILITIES.md up to date') if ok else failed('CAPABILITIES.md not updated — add new capabilities')
    print()

    # ── Gate 3: Execution Plan Gate (REQ branches only) ──
    if is_req:
        gate_num += 1
        section(gate_num, total_gates, '📋 Execution Plan Gate')
        ok = gate_execution_plan(root, branch)
        results.append(('Execution Plan Gate', ok))
        passed('EXECUTION-PLAN.md updated') if ok else failed('EXECUTION-PLAN.md not in changeset')
        print()

    # ── Gate 4: Checkpoint Audit (REQ branches only) ──
    if is_req and req_id:
        gate_num += 1
        section(gate_num, total_gates, f'🔐 Checkpoint Audit ({req_id})')
        ok = gate_checkpoint(root, req_id)
        results.append(('Checkpoint Audit', ok))
        passed('All checkpoint phases verified') if ok else failed('Checkpoint chain incomplete')
        print()

    # ── Gate 5: Issue Link Gate (REQ branches + PR number) ──
    if is_req and args.pr:
        gate_num += 1
        section(gate_num, total_gates, f'🔗 Issue Link Gate (PR #{args.pr})')
        ok = gate_issue_link(root, args.pr, branch)
        results.append(('Issue Link Gate', ok))
        passed('PR body contains Closes #NNN') if ok else failed('PR body missing issue reference')
        print()
    elif is_req and not args.pr:
        results.append(('Issue Link Gate', None))
        info('⏭️  Issue Link Gate skipped — pass --pr <number> to check')
        print()

    # ── Summary ──
    elapsed = time.time() - start
    header('PREFLIGHT RESULTS')

    all_passed = True
    for name, result in results:
        if result is True:
            print(f'  {C.GREEN}✅{C.RESET} {name}')
        elif result is False:
            print(f'  {C.RED}❌{C.RESET} {name}')
            all_passed = False
        else:
            print(f'  {C.YELLOW}⏭️{C.RESET}  {name} {C.DIM}(skipped){C.RESET}')

    print(f'\n  {C.DIM}Completed in {elapsed:.1f}s{C.RESET}')

    if all_passed:
        print(f'\n  {C.GREEN}{C.BOLD}🚀 ALL GATES PASSED — safe to push.{C.RESET}\n')
        sys.exit(0)
    else:
        fail_count = sum(1 for _, r in results if r is False)
        print(f'\n  {C.RED}{C.BOLD}⛔ {fail_count} GATE(S) FAILED — fix before pushing.{C.RESET}\n')
        sys.exit(1)


if __name__ == '__main__':
    main()
