#!/usr/bin/env python3
"""
Workflow Enforcement Script v1.0
================================
Validates that the /implement-req workflow is being followed.

Checks:
- [BRANCH] Branch follows task/REQ-* naming convention
- [TDD] Failing test exists before implementation changes
- [ATOMIC] Commits are grouped by layer (sql -> logic -> tests)
"""

import sys
import subprocess
import re
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    WARN = '\033[93m'
    ENDC = '\033[0m'

def print_fail(check, message):
    print(f"{Colors.RED}[{check}] FAIL: {message}{Colors.ENDC}")

def print_pass(check, message):
    print(f"{Colors.GREEN}[{check}] PASS: {message}{Colors.ENDC}")

def print_warn(check, message):
    print(f"{Colors.WARN}[{check}] WARN: {message}{Colors.ENDC}")

def get_current_branch() -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except:
        return ""

def check_branch_naming() -> bool:
    """[BRANCH] Validate branch follows task/REQ-* convention."""
    branch = get_current_branch()
    
    # Skip check for main/develop branches
    if branch in ["main", "master", "develop", "HEAD"]:
        print_pass("BRANCH", f"On protected branch: {branch}")
        return True
    
    # Check for REQ pattern
    req_pattern = r"^(task|feature|fix)/REQ-[A-Z0-9-]+"
    research_pattern = r"^research/"
    
    if re.match(req_pattern, branch) or re.match(research_pattern, branch):
        print_pass("BRANCH", f"Valid branch naming: {branch}")
        return True
    else:
        print_warn("BRANCH", f"Branch '{branch}' doesn't follow task/REQ-* pattern. Consider renaming.")
        return True  # Warning only, not blocking

def check_tdd_baseline(project_root: Path) -> bool:
    """[TDD] Check if there are test files when there are implementation files in staged changes."""
    try:
        # Get staged files
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=project_root
        )
        staged_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        # Categorize files
        impl_files = []
        test_files = []
        
        for f in staged_files:
            if not f:
                continue
            # Skip docs and configs
            if f.startswith('docs/') or f.startswith('.agent/') or f.endswith('.md'):
                continue
            # Categorize
            if '.test.' in f or '__tests__' in f or 'tests/' in f:
                test_files.append(f)
            elif f.endswith(('.ts', '.tsx', '.js', '.jsx', '.py')):
                impl_files.append(f)
        
        # If we have implementation files, we should have test files
        if impl_files and not test_files:
            print_warn("TDD", f"Implementation files staged without tests: {impl_files[:3]}")
            return True  # Warning only
        elif impl_files:
            print_pass("TDD", f"Found {len(test_files)} test file(s) alongside {len(impl_files)} impl file(s)")
        else:
            print_pass("TDD", "No implementation files staged (docs/config only)")
        
        return True
        
    except Exception as e:
        print_warn("TDD", f"Could not check staged files: {e}")
        return True

def check_checkpoint_completeness(project_root: Path) -> bool:
    """[CHECKPOINT] Verify all 5 phases exist for any REQ with staged checkpoint files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=project_root
        )
        staged_files = result.stdout.strip().split('\n') if result.stdout.strip() else []

        # Find REQ IDs that have staged checkpoint files
        checkpoint_pattern = re.compile(r'\.agent/checkpoints/(REQ-[A-Z0-9-]+)/')
        staged_reqs = set()
        for f in staged_files:
            match = checkpoint_pattern.search(f)
            if match:
                staged_reqs.add(match.group(1))

        if not staged_reqs:
            print_pass("CHECKPOINT", "No checkpoint files staged")
            return True

        # For each REQ with staged checkpoints, verify all 5 phases exist
        required_phases = [
            "phase1_discovery.json",
            "phase2_draft.json",
            "phase3_board_review.json",
            "phase4_finalization.json",
            "phase5_registration.json",
        ]

        all_passed = True
        for req_id in sorted(staged_reqs):
            checkpoint_dir = project_root / ".agent" / "checkpoints" / req_id
            missing = []
            for phase_file in required_phases:
                if not (checkpoint_dir / phase_file).exists():
                    missing.append(phase_file)

            if missing:
                phase_names = ", ".join(m.replace(".json", "").replace("_", " ") for m in missing)
                print_fail("CHECKPOINT", f"{req_id}: Missing checkpoints: {phase_names}")
                print_fail("CHECKPOINT", f"  → Run the missing /create-req or /implement-req phase(s) before committing")
                all_passed = False
            else:
                print_pass("CHECKPOINT", f"{req_id}: All 5 phase checkpoints verified")

        return all_passed

    except Exception as e:
        print_warn("CHECKPOINT", f"Could not verify checkpoints: {e}")
        return True  # Don't block on errors in the check itself


def check_step2_promotion(project_root: Path) -> bool:
    """[STEP2] Verify that scoped REQs in EXECUTION-PLAN.md Step 1 also appear in Step 2."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=project_root
        )
        staged_files = result.stdout.strip().split('\n') if result.stdout.strip() else []

        # Only run if EXECUTION-PLAN.md is staged
        if not any('EXECUTION-PLAN.md' in f for f in staged_files):
            return True

        exec_plan = project_root / "docs" / "EXECUTION-PLAN.md"
        if not exec_plan.exists():
            return True

        content = exec_plan.read_text()

        # Find scoped items in Step 1: lines like "- [x] ... → REQ-XXX"
        step1_scoped = re.findall(r'- \[x\] .+→ \*{0,2}(REQ-[A-Z0-9-]+)\*{0,2}', content)

        if not step1_scoped:
            return True

        # Find Step 2 section and check for each scoped REQ
        step2_match = re.search(r'## Step 2:', content)
        if not step2_match:
            return True

        step2_content = content[step2_match.start():]
        missing = []
        for req_id in step1_scoped:
            if req_id not in step2_content:
                missing.append(req_id)

        if missing:
            for req_id in missing:
                print_fail("STEP2", f"{req_id} is marked SCOPED in Step 1 but NOT in Step 2 implement queue")
                print_fail("STEP2", f"  → Add '/implement-req {req_id}' to the appropriate wave in Step 2")
            return False
        else:
            print_pass("STEP2", f"All {len(step1_scoped)} scoped REQ(s) found in Step 2")
            return True

    except Exception as e:
        print_warn("STEP2", f"Could not verify Step 2 promotion: {e}")
        return True


def check_atomic_commits(project_root: Path) -> bool:
    """[ATOMIC] Suggest atomic commit structure based on staged files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=project_root
        )
        staged_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        layers = {
            "sql": [],
            "logic": [],
            "tests": [],
            "docs": [],
            "config": []
        }
        
        for f in staged_files:
            if not f:
                continue
            if f.endswith('.sql'):
                layers["sql"].append(f)
            elif '.test.' in f or '__tests__' in f or 'tests/' in f:
                layers["tests"].append(f)
            elif f.endswith('.md') or f.startswith('docs/'):
                layers["docs"].append(f)
            elif f.endswith(('.yml', '.yaml', '.json', '.env')):
                layers["config"].append(f)
            else:
                layers["logic"].append(f)
        
        # Count non-empty layers
        active_layers = [k for k, v in layers.items() if v]
        
        if len(active_layers) > 2:
            print_warn("ATOMIC", f"Consider splitting commit: touching {active_layers}. Ideal: sql -> logic -> tests")
        else:
            print_pass("ATOMIC", f"Commit scope looks good: {active_layers if active_layers else ['empty']}")
        
        return True
        
    except Exception as e:
        print_warn("ATOMIC", f"Could not analyze commit structure: {e}")
        return True

def main():
    project_root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    print(f"\n{'='*50}")
    print("📋 WORKFLOW ENFORCEMENT (implement-req compliance)")
    print(f"{'='*50}\n")
    
    checks = [
        check_branch_naming(),
        check_tdd_baseline(project_root),
        check_checkpoint_completeness(project_root),
        check_step2_promotion(project_root),
        check_atomic_commits(project_root)
    ]
    
    if all(checks):
        print(f"\n{Colors.GREEN}✅ Workflow checks passed{Colors.ENDC}")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}❌ Workflow violations detected{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()
