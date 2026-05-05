#!/usr/bin/env python3
"""
Frontend Performance & Code Quality Gate v1.1
==============================================
Static analysis gate that scans modified frontend files for performance
anti-patterns and clean code violations. Blocks Phase 3 checkpoint
sign-off if violations are found.

Usage:
    python3 .agent/scripts/frontend_perf_gate.py . --req REQ-L2-25
    python3 .agent/scripts/frontend_perf_gate.py . --req REQ-L2-25 --strict

Gate Checks:
    [PERF-001] O(n²) nested loops in component render paths
    [PERF-002] Missing key prop on .map() JSX output
    [PERF-003] Inline object/array allocations in JSX props (re-created every render)
    [PERF-004] useEffect with empty [] dependency when referencing external state
    [CLEAN-001] Component file exceeds 200 lines (delta-aware for legacy files)
    [CLEAN-002] Duplicated JSX patterns across files (DRY violation)

Severity:
    CRITICAL → ⛔ Blocks sign-off (must fix)
    WARNING  → ⚠️  Reported but non-blocking (auto-logged to tech debt ledger)

File Exemptions:
    *.test.ts, *.test.tsx, *.spec.ts, *.spec.tsx, *.d.ts are excluded from all checks.
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


class Colors:
    HEADER = '\033[95m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    WARN = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'


def print_fail(context: str, message: str):
    print(f"{Colors.RED}[{context}] ⛔ CRITICAL: {message}{Colors.ENDC}")


def print_pass(context: str, message: str):
    print(f"{Colors.GREEN}[{context}] ✅ PASS: {message}{Colors.ENDC}")


def print_info(context: str, message: str):
    print(f"{Colors.BLUE}[{context}] ℹ️  INFO: {message}{Colors.ENDC}")


def print_warn(context: str, message: str):
    print(f"{Colors.WARN}[{context}] ⚠️  WARN: {message}{Colors.ENDC}")


@dataclass
class Violation:
    rule_id: str
    file: str
    line: int
    message: str
    severity: str  # "CRITICAL" or "WARNING"


@dataclass
class GateResult:
    violations: list[Violation] = field(default_factory=list)
    files_scanned: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "CRITICAL")

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "WARNING")


def get_modified_frontend_files(project_root: Path) -> list[Path]:
    """Get list of modified .tsx/.ts/.jsx/.js files under frontend/src/."""
    frontend_files: list[str] = []

    commands = [
        ["git", "diff", "--cached", "--name-only", "--", "frontend/src/"],
        ["git", "diff", "--name-only", "--", "frontend/src/"],
        ["git", "diff", "--name-only", "main", "--", "frontend/src/"],
    ]

    for cmd in commands:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=project_root
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line and line not in frontend_files:
                        frontend_files.append(line)
        except Exception:
            pass

    # Filter to source code files only (exclude tests, assets, configs)
    source_exts = {'.tsx', '.ts', '.jsx', '.js'}
    # Explicit exemptions: test files, spec files, type declaration files
    exempt_patterns = ['.test.', '.spec.', '__tests__', '.d.ts']
    result_paths: list[Path] = []
    for f in frontend_files:
        path = project_root / f
        if path.suffix in source_exts and path.exists():
            # Skip exempt files — they have different quality standards
            if not any(pat in f for pat in exempt_patterns):
                result_paths.append(path)

    return sorted(result_paths)


def get_all_frontend_files(project_root: Path) -> list[Path]:
    """Get ALL .tsx/.ts/.jsx/.js files under frontend/src/ for full audit."""
    frontend_dir = project_root / "frontend" / "src"
    if not frontend_dir.exists():
        return []

    source_exts = {'.tsx', '.ts', '.jsx', '.js'}
    exempt_patterns = ['.test.', '.spec.', '__tests__', '.d.ts']
    result_paths: list[Path] = []

    for path in sorted(frontend_dir.rglob('*')):
        if path.is_file() and path.suffix in source_exts:
            rel = str(path.relative_to(project_root))
            if not any(pat in rel for pat in exempt_patterns):
                result_paths.append(path)

    return result_paths


# ============================================================================
# PERFORMANCE CHECKS
# ============================================================================

def check_nested_loops_in_render(file_path: Path, lines: list[str]) -> list[Violation]:
    """[PERF-001] Detect O(n²) nested iterations in component render paths.

    Only flags truly nested iterations — where an iteration method's callback
    body contains ANOTHER iteration call. Sequential chains like
    `.filter().map()` are O(2n), not O(n²), and are NOT flagged.

    Strategy: use brace-depth tracking to determine if a new iteration call
    appears inside the callback scope of an outer iteration.
    """
    violations: list[Violation] = []

    # Patterns that create an iteration scope (callback processes all elements)
    scope_patterns = [
        re.compile(r'\.\s*map\s*\('),
        re.compile(r'\.\s*forEach\s*\('),
        re.compile(r'\.\s*filter\s*\('),
        re.compile(r'\.\s*reduce\s*\('),
        re.compile(r'\bfor\s*\('),
        re.compile(r'\bfor\s+of\b'),
    ]

    # Predicate methods — iterate but return a scalar/boolean.
    # They are flagged if nested inside a scope, but they do NOT create
    # a nesting scope themselves (you can't nest further inside .some()).
    predicate_patterns = [
        re.compile(r'\.\s*find\s*\('),
        re.compile(r'\.\s*some\s*\('),
        re.compile(r'\.\s*every\s*\('),
    ]

    in_component = False

    # Stack of (start_line, brace_depth_at_entry) for each active iteration
    iter_stack: list[tuple[int, int]] = []
    brace_depth = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments
        if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*'):
            continue

        # Detect component render body
        if 'return (' in stripped or 'return (<' in stripped:
            in_component = True

        if not in_component:
            continue

        # Count braces BEFORE checking for new iterations
        open_count = stripped.count('(') + stripped.count('{')
        close_count = stripped.count(')') + stripped.count('}')

        # Pop completed iteration scopes off the stack
        # An iteration callback is "done" when brace depth drops to or below
        # the depth recorded when the iteration started.
        while iter_stack and (brace_depth + open_count - close_count) <= iter_stack[-1][1]:
            iter_stack.pop()

        # Check for scope-creating iteration patterns on this line
        found = False
        for pat in scope_patterns:
            if pat.search(stripped):
                if len(iter_stack) >= 1:
                    outer_line = iter_stack[0][0]
                    violations.append(Violation(
                        rule_id="PERF-001",
                        file=str(file_path),
                        line=i,
                        message=f"Nested iteration detected (depth={len(iter_stack) + 1}). "
                                f"Outer loop at line {outer_line}. "
                                f"This creates O(n²) complexity in the render path.",
                        severity="CRITICAL"
                    ))
                # Scope-creating: push onto the stack
                iter_stack.append((i, brace_depth))
                found = True
                break

        # Check predicate patterns (flag if nested, but do NOT push scope)
        if not found:
            for pat in predicate_patterns:
                if pat.search(stripped):
                    if len(iter_stack) >= 1:
                        outer_line = iter_stack[0][0]
                        violations.append(Violation(
                            rule_id="PERF-001",
                            file=str(file_path),
                            line=i,
                            message=f"Nested iteration detected (depth={len(iter_stack) + 1}). "
                                    f"Outer loop at line {outer_line}. "
                                    f"This creates O(n²) complexity in the render path.",
                            severity="CRITICAL"
                        ))
                    # Predicates do NOT push — they don't create nesting scope
                    break

        # Update brace depth AFTER processing
        new_depth = brace_depth + open_count - close_count

        # Pop any iterations whose callback closed on this same line.
        # A single-line callback (e.g. `.filter(x => pred(x))`) opens and
        # closes with net 0 change — it should not create a nesting scope
        # for subsequent chained methods.
        while iter_stack and new_depth <= iter_stack[-1][1]:
            iter_stack.pop()

        brace_depth = new_depth

    return violations


def check_missing_map_keys(file_path: Path, lines: list[str]) -> list[Violation]:
    """[PERF-002] Detect .map() calls that produce JSX without key props."""
    violations: list[Violation] = []

    map_pattern = re.compile(r'\.\s*map\s*\(\s*\(')

    for i, line in enumerate(lines, 1):
        if map_pattern.search(line):
            # Look ahead for JSX output without key= in the next ~10 lines
            lookahead = '\n'.join(lines[i:min(i + 10, len(lines))])
            # If we see JSX opening tags but no key= or key={
            if re.search(r'<\w+', lookahead):
                if not re.search(r'\bkey\s*=', lookahead):
                    violations.append(Violation(
                        rule_id="PERF-002",
                        file=str(file_path),
                        line=i,
                        message="JSX output from .map() is likely missing a `key` prop. "
                                "React uses keys for efficient reconciliation.",
                        severity="CRITICAL"
                    ))

    return violations


def check_inline_object_allocations(file_path: Path, lines: list[str]) -> list[Violation]:
    """[PERF-003] Detect inline object/array literals in JSX props."""
    violations: list[Violation] = []

    # Pattern: prop={{ ... }} or prop={[ ... ]} inside JSX
    inline_obj_pattern = re.compile(r'(?<!=)\s*=\s*\{\s*\{')
    inline_arr_pattern = re.compile(r'(?<!=)\s*=\s*\{\s*\[')

    # Exceptions: style={{ }} with only simple values is common and acceptable
    # We flag complex objects (multiple keys, function calls, etc.)
    in_jsx = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Simple JSX detection
        if re.match(r'^\s*<[A-Z]', stripped) or re.match(r'^\s*<[a-z]+', stripped):
            in_jsx = True
        if stripped.startswith('/>') or stripped.startswith('</'):
            in_jsx = False

        if not in_jsx:
            continue

        # Skip style={{ }} — too many false positives
        if 'style=' in stripped:
            continue

        if inline_obj_pattern.search(stripped):
            violations.append(Violation(
                rule_id="PERF-003",
                file=str(file_path),
                line=i,
                message="Inline object `={{}}` in JSX prop creates a new reference every render. "
                        "Extract to a const, useMemo, or module-level variable.",
                severity="WARNING"
            ))
        elif inline_arr_pattern.search(stripped):
            violations.append(Violation(
                rule_id="PERF-003",
                file=str(file_path),
                line=i,
                message="Inline array `={[]}` in JSX prop creates a new reference every render. "
                        "Extract to a const, useMemo, or module-level variable.",
                severity="WARNING"
            ))

    return violations


def check_useeffect_deps(file_path: Path, lines: list[str]) -> list[Violation]:
    """[PERF-004] Detect useEffect with suspicious dependency arrays."""
    violations: list[Violation] = []

    # Look for useEffect(() => { ... }, []) where the body references state/props
    effect_pattern = re.compile(r'\buseEffect\s*\(\s*\(\s*\)\s*=>')

    for i, line in enumerate(lines, 1):
        if effect_pattern.search(line):
            # Look ahead for empty dependency array within ~20 lines
            lookahead_start = i
            lookahead_end = min(i + 20, len(lines))
            lookahead = '\n'.join(lines[lookahead_start:lookahead_end])

            # Check for empty deps: , [])
            if re.search(r',\s*\[\s*\]\s*\)', lookahead):
                # Check if body references state setters or props
                body_section = lookahead.split(', []')[0] if ', []' in lookahead else ''
                # Common signals: setState calls, prop references, fetch calls
                if re.search(r'\bset[A-Z]\w*\(', body_section):
                    violations.append(Violation(
                        rule_id="PERF-004",
                        file=str(file_path),
                        line=i,
                        message="useEffect with [] deps calls a state setter. "
                                "Verify this only needs to run on mount, not on state changes.",
                        severity="WARNING"
                    ))

    return violations


# ============================================================================
# CLEAN CODE CHECKS
# ============================================================================

def get_git_diff_delta(file_path: Path, project_root: Path) -> int | None:
    """
    Get the number of lines added to a file in the current branch vs main.
    Returns None if the file is newly created (not in main).
    """
    rel_path = file_path.relative_to(project_root)

    # Check if file exists on main
    result = subprocess.run(
        ["git", "cat-file", "-e", f"main:{rel_path}"],
        capture_output=True, text=True, cwd=project_root
    )
    if result.returncode != 0:
        return None  # File is new — doesn't exist on main

    # Get diff stat: compute NET delta (added - deleted)
    # numstat format: "added\tdeleted\tfilename"
    result = subprocess.run(
        ["git", "diff", "main", "--numstat", "--", str(rel_path)],
        capture_output=True, text=True, cwd=project_root
    )
    if result.returncode != 0 or not result.stdout.strip():
        return 0

    parts = result.stdout.strip().split('\t')
    try:
        added = int(parts[0])
        deleted = int(parts[1])
        return max(0, added - deleted)  # Net growth; floor at 0
    except (ValueError, IndexError):
        return 0


def log_tech_debt(project_root: Path, file_path: Path, line_count: int,
                  req_id: str, delta: int) -> None:
    """
    Auto-append an entry to docs/tech-debt/frontend-debt-ledger.md.
    Creates the file and directory if they don't exist.
    """
    debt_dir = project_root / "docs" / "tech-debt"
    debt_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = debt_dir / "frontend-debt-ledger.md"

    rel_path = file_path.relative_to(project_root)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Get current branch
    branch_result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, cwd=project_root
    )
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

    # Create header if file doesn't exist or is empty
    if not ledger_path.exists() or ledger_path.stat().st_size == 0:
        header = (
            "# Frontend Tech Debt Ledger\n\n"
            "> Auto-generated by `frontend_perf_gate.py`. Tracks legacy files that exceed\n"
            "> the 200-line component limit but were not blocked because the current change\n"
            "> added fewer than 20 new lines.\n\n"
            "| Date | File | Lines | Delta | REQ | Branch |\n"
            "|------|------|-------|-------|-----|--------|\n"
        )
        ledger_path.write_text(header)

    # Check for duplicate: don't re-log the same file+REQ combo
    existing = ledger_path.read_text()
    dedup_key = f"`{rel_path}` | {line_count}"
    if dedup_key in existing:
        print_info("TECH-DEBT", f"Entry for {rel_path} + {req_id} already logged. Skipping duplicate.")
        return

    entry = f"| {now} | `{rel_path}` | {line_count} | +{delta} | {req_id} | `{branch}` |\n"

    with open(ledger_path, "a") as f:
        f.write(entry)

    print_info("TECH-DEBT", f"Logged to docs/tech-debt/frontend-debt-ledger.md")


def check_file_length(file_path: Path, lines: list[str],
                      project_root: Path, req_id: str) -> list[Violation]:
    """
    [CLEAN-001] Component file exceeds 200 lines.

    Delta-aware for legacy files:
    - New file > 200 lines -> CRITICAL (hard block)
    - Existing legacy file + added > 20 lines -> CRITICAL (force extraction)
    - Existing legacy file + added <= 20 lines -> WARNING + auto-log tech debt
    - Any file > 150 lines -> WARNING (approaching limit)
    """
    violations: list[Violation] = []
    line_count = len(lines)

    if line_count > 200:
        delta = get_git_diff_delta(file_path, project_root)

        if delta is None:
            # New file — hard block, no excuse
            violations.append(Violation(
                rule_id="CLEAN-001",
                file=str(file_path),
                line=1,
                message=f"NEW file is {line_count} lines (limit: 200). "
                        f"Split into smaller sub-components before committing.",
                severity="CRITICAL"
            ))
        elif delta > 20:
            # Legacy file but you added a lot — force extraction
            violations.append(Violation(
                rule_id="CLEAN-001",
                file=str(file_path),
                line=1,
                message=f"Legacy file is {line_count} lines and you added {delta} new lines "
                        f"(threshold: 20). Extract new code into a child component.",
                severity="CRITICAL"
            ))
        else:
            # Legacy file, small change — warn + log tech debt
            violations.append(Violation(
                rule_id="CLEAN-001",
                file=str(file_path),
                line=1,
                message=f"Legacy file is {line_count} lines (+{delta} added). "
                        f"Under 20-line delta threshold — passing with tech debt logged.",
                severity="WARNING"
            ))
            log_tech_debt(project_root, file_path, line_count, req_id, delta)

    elif line_count > 150:
        violations.append(Violation(
            rule_id="CLEAN-001",
            file=str(file_path),
            line=1,
            message=f"File is {line_count} lines (approaching 200-line limit). "
                    f"Consider proactive refactoring.",
            severity="WARNING"
        ))

    return violations


def check_duplicate_jsx_patterns(files: list[tuple[Path, list[str]]]) -> list[Violation]:
    """[CLEAN-002] Detect duplicated JSX patterns across files."""
    violations: list[Violation] = []

    # Extract significant JSX blocks from each file
    jsx_blocks: dict[str, list[tuple[str, int]]] = {}  # block_hash -> [(file, line)]

    for file_path, lines in files:
        # Find multi-line JSX blocks (3+ consecutive lines starting with < or containing JSX)
        block: list[str] = []
        block_start = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r'^<[A-Za-z]', stripped) or (block and stripped):
                if not block:
                    block_start = i
                block.append(stripped)
            else:
                if len(block) >= 3:
                    block_key = '\n'.join(block)
                    if block_key not in jsx_blocks:
                        jsx_blocks[block_key] = []
                    jsx_blocks[block_key].append((str(file_path), block_start))
                block = []

    # Report blocks found in 2+ files
    for block_key, locations in jsx_blocks.items():
        if len(locations) >= 2:
            files_involved = [loc[0].split('/')[-1] for loc in locations]
            violations.append(Violation(
                rule_id="CLEAN-002",
                file=locations[0][0],
                line=locations[0][1],
                message=f"Duplicated JSX pattern found in {len(locations)} files: "
                        f"{', '.join(files_involved)}. Extract to a shared component.",
                severity="WARNING"
            ))

    return violations


# ============================================================================
# MAIN GATE
# ============================================================================

def run_gate(project_root: Path, req_id: str, strict: bool = False,
             audit: bool = False) -> bool:
    """Execute the Frontend Performance & Code Quality Gate.

    When audit=True, scans ALL frontend files (not just git diff) and
    reports all findings without blocking. Used for tech debt audits.
    """
    mode_label = "FULL AUDIT" if audit else req_id
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}FRONTEND PERFORMANCE & CODE QUALITY GATE: {mode_label}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

    # Get files to scan
    if audit:
        target_files = get_all_frontend_files(project_root)
    else:
        target_files = get_modified_frontend_files(project_root)

    if not target_files:
        msg = "No frontend source files found." if audit else "No frontend source files modified. Performance gate skipped."
        print_pass("DETECT", msg)
        return True

    scan_type = "total" if audit else "modified"
    print_info("DETECT", f"Scanning {len(target_files)} {scan_type} frontend file(s):")
    for f in target_files:
        print_info("DETECT", f"  → {f.relative_to(project_root)}")

    # Load file contents
    file_contents: list[tuple[Path, list[str]]] = []
    for f in target_files:
        try:
            content = f.read_text(encoding='utf-8')
            file_contents.append((f, content.splitlines()))
        except Exception as e:
            print_warn("IO", f"Could not read {f.name}: {e}")

    # Run all checks
    result = GateResult(files_scanned=len(file_contents))

    print(f"\n{Colors.BLUE}--- Performance Checks ---{Colors.ENDC}")
    for file_path, lines in file_contents:
        result.violations.extend(check_nested_loops_in_render(file_path, lines))
        result.violations.extend(check_missing_map_keys(file_path, lines))
        result.violations.extend(check_inline_object_allocations(file_path, lines))
        result.violations.extend(check_useeffect_deps(file_path, lines))

    print(f"\n{Colors.BLUE}--- Clean Code Checks ---{Colors.ENDC}")
    for file_path, lines in file_contents:
        if audit:
            # In audit mode, report all 200+ line files as WARNINGs (no delta logic)
            line_count = len(lines)
            if line_count > 200:
                result.violations.append(Violation(
                    rule_id="CLEAN-001",
                    file=str(file_path),
                    line=1,
                    message=f"File is {line_count} lines (limit: 200). Needs refactoring.",
                    severity="WARNING"
                ))
            elif line_count > 150:
                result.violations.append(Violation(
                    rule_id="CLEAN-001",
                    file=str(file_path),
                    line=1,
                    message=f"File is {line_count} lines (approaching 200-line limit).",
                    severity="WARNING"
                ))
        else:
            result.violations.extend(check_file_length(file_path, lines, project_root, req_id))

    # Cross-file checks
    result.violations.extend(check_duplicate_jsx_patterns(file_contents))

    # Report results
    print(f"\n{Colors.HEADER}--- Results ---{Colors.ENDC}\n")

    if not result.violations:
        print_pass("GATE", f"All {result.files_scanned} files passed. No violations found.")
        return True

    # Print violations sorted by severity
    criticals = [v for v in result.violations if v.severity == "CRITICAL"]
    warnings = [v for v in result.violations if v.severity == "WARNING"]

    for v in criticals:
        rel_path = Path(v.file).relative_to(project_root) if project_root in Path(v.file).parents else v.file
        print_fail(v.rule_id, f"{rel_path}:{v.line} — {v.message}")

    for v in warnings:
        rel_path = Path(v.file).relative_to(project_root) if project_root in Path(v.file).parents else v.file
        print_warn(v.rule_id, f"{rel_path}:{v.line} — {v.message}")

    # Summary
    print(f"\n{Colors.HEADER}--- Summary ---{Colors.ENDC}")
    print_info("SCAN", f"Files scanned: {result.files_scanned}")
    if result.critical_count > 0:
        print_fail("TOTAL", f"Critical violations: {result.critical_count}")
    if result.warning_count > 0:
        print_warn("TOTAL", f"Warnings: {result.warning_count}")

    # Gate verdict
    if audit:
        total = result.critical_count + result.warning_count
        print(f"\n{Colors.HEADER}📋 AUDIT COMPLETE — {total} finding(s) across {result.files_scanned} files.{Colors.ENDC}")
        return True  # Audit mode never blocks, it's informational
    elif result.critical_count > 0:
        print(f"\n{Colors.RED}⛔ FRONTEND PERF GATE BLOCKED — {result.critical_count} critical violation(s) must be fixed.{Colors.ENDC}")
        return False
    elif strict and result.warning_count > 0:
        print(f"\n{Colors.RED}⛔ FRONTEND PERF GATE BLOCKED (strict mode) — {result.warning_count} warning(s) must be fixed.{Colors.ENDC}")
        return False
    else:
        print(f"\n{Colors.GREEN}✅ FRONTEND PERF GATE PASSED (with {result.warning_count} warning(s)).{Colors.ENDC}")
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Frontend Performance & Code Quality Gate — blocks Phase 3 on anti-patterns'
    )
    parser.add_argument('project_root', help='Project root directory')
    parser.add_argument('--req', default='AUDIT',
                        help='Requirement ID (e.g., REQ-L2-25). Defaults to AUDIT in audit mode.')
    parser.add_argument('--strict', action='store_true',
                        help='Treat warnings as errors (block on any violation)')
    parser.add_argument('--audit', action='store_true',
                        help='Full audit mode: scan ALL frontend/src files, not just git diff. '
                             'Reports findings without blocking.')
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    success = run_gate(project_root, args.req, strict=args.strict, audit=args.audit)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
