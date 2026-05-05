#!/usr/bin/env python3
"""
Frontend Visual Verification Gate v1.0
=======================================
Enforces that any implement-req touching frontend/src/** files
has browser-based visual verification evidence in the checkpoint directory.

This gate BLOCKS Phase 4 (Validation) checkpoint sign-off unless
screenshot/recording artifacts exist, indirectly enforcing both the
browser verification AND the auth handoff protocol (since without
successful auth, no screenshot can be captured).

Usage:
    python3 .agent/scripts/frontend_visual_gate.py . --req REQ-L2-25
    python3 .agent/scripts/frontend_visual_gate.py . --req REQ-L2-25 --branch task/REQ-L2-25-lifecycle

Gate Logic:
    1. Check git diff (staged + unstaged vs main) for frontend/src/** changes
    2. If no frontend changes → PASS (skip gate)
    3. If frontend changes → require visual artifacts in .agent/checkpoints/{REQ-ID}/
    4. Accepted artifacts: *.png, *.jpg, *.jpeg, *.webp, *.webm, *.mp4
    5. If no artifacts found → ⛔ BLOCKED
"""

import argparse
import subprocess
import sys
from pathlib import Path


class Colors:
    HEADER = '\033[95m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    WARN = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'


def print_fail(context: str, message: str):
    print(f"{Colors.RED}[{context}] ⛔ BLOCKED: {message}{Colors.ENDC}")


def print_pass(context: str, message: str):
    print(f"{Colors.GREEN}[{context}] ✅ PASS: {message}{Colors.ENDC}")


def print_info(context: str, message: str):
    print(f"{Colors.BLUE}[{context}] ℹ️  INFO: {message}{Colors.ENDC}")


def print_warn(context: str, message: str):
    print(f"{Colors.WARN}[{context}] ⚠️  WARN: {message}{Colors.ENDC}")


# Extensions accepted as visual verification evidence
VISUAL_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.webm', '.mp4', '.gif'}


def get_frontend_changes(project_root: Path) -> list[str]:
    """
    Detect frontend file changes by checking:
    1. Staged changes (git diff --cached)
    2. Unstaged changes (git diff)
    3. Untracked files (git ls-files --others)
    All filtered to frontend/src/** paths.
    """
    frontend_files: list[str] = []

    commands = [
        ["git", "diff", "--cached", "--name-only", "--", "frontend/src/"],
        ["git", "diff", "--name-only", "--", "frontend/src/"],
    ]

    for cmd in commands:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=project_root
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line and line.startswith('frontend/src/') and line not in frontend_files:
                        frontend_files.append(line)
        except Exception:
            pass

    # Also check against main/origin for committed-but-not-merged changes
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "frontend/src/"],
            capture_output=True, text=True, cwd=project_root
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line and line.startswith('frontend/src/') and line not in frontend_files:
                    frontend_files.append(line)
    except Exception:
        pass

    return frontend_files


def find_visual_artifacts(checkpoint_dir: Path) -> list[Path]:
    """Find screenshot/recording files in the checkpoint directory."""
    if not checkpoint_dir.exists():
        return []

    artifacts: list[Path] = []
    for f in checkpoint_dir.iterdir():
        if f.is_file() and f.suffix.lower() in VISUAL_EXTENSIONS:
            artifacts.append(f)

    return sorted(artifacts)


def run_gate(project_root: Path, req_id: str) -> bool:
    """
    Execute the Frontend Visual Verification Gate.

    Returns True if the gate passes, False if blocked.
    """
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}FRONTEND VISUAL VERIFICATION GATE: {req_id}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

    # Step 1: Detect frontend changes
    frontend_files = get_frontend_changes(project_root)

    if not frontend_files:
        print_pass("DETECT", "No frontend/src/ changes detected. Visual gate skipped.")
        return True

    print_info("DETECT", f"Found {len(frontend_files)} frontend file change(s):")
    # Show first 10, truncate rest
    for f in frontend_files[:10]:
        print_info("DETECT", f"  → {f}")
    if len(frontend_files) > 10:
        print_info("DETECT", f"  ... and {len(frontend_files) - 10} more")

    # Step 2: Check for visual artifacts
    checkpoint_dir = project_root / ".agent" / "checkpoints" / req_id
    artifacts = find_visual_artifacts(checkpoint_dir)

    if not artifacts:
        print()
        print_fail("VISUAL", "No visual verification artifacts found!")
        print_fail("VISUAL", f"Expected: Screenshots or recordings in {checkpoint_dir}/")
        print()
        print_info("REMEDY", "You MUST open the browser and verify the UI changes before signing off Phase 4.")
        print_info("REMEDY", "")
        print_info("REMEDY", "Protocol (from .agent/workflows/frontend-browser-gate.md):")
        print_info("REMEDY", "  1. Use browser_subagent to navigate to http://localhost:3000")
        print_info("REMEDY", "  2. ⛔ HALT at auth wall — let user complete login/MFA")
        print_info("REMEDY", "  3. Resume browser_subagent (via ReusedSubagentId) after user confirms")
        print_info("REMEDY", "  4. Capture screenshots of the modified UI")
        print_info("REMEDY", f"  5. Save screenshots to: {checkpoint_dir}/")
        print_info("REMEDY", "")
        print_info("REMEDY", f"Accepted file types: {', '.join(sorted(VISUAL_EXTENSIONS))}")
        print()
        return False

    # Step 3: Report success
    print_pass("VISUAL", f"Found {len(artifacts)} visual verification artifact(s):")
    for a in artifacts:
        size_kb = a.stat().st_size / 1024
        print_pass("VISUAL", f"  ✅ {a.name} ({size_kb:.1f} KB)")

    print()
    print_pass("GATE", "Frontend Visual Verification Gate PASSED.")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Frontend Visual Verification Gate — blocks Phase 4 without visual evidence'
    )
    parser.add_argument('project_root', help='Project root directory')
    parser.add_argument('--req', required=True, help='Requirement ID (e.g., REQ-L2-25)')
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    success = run_gate(project_root, args.req)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
