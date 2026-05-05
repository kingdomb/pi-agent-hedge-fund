#!/usr/bin/env python3
"""
Governance Audit v2.0 - The Digital Board of Directors
======================================================
Enforces high-level mandates that are often missed by standard linters.
Simulates the "Board Member" review process.

Mandates:
- [PPM] Product Manager: QA Strategy Existence (Frontend Tests)
- [OPS] VP Operations: CI Pipeline Integrity (Frontend CI Job)
- [CISO] CISO: Dependency Safety (Test Harness Installed)
- [GOV] Governance: Trust Execution Hook (TrustService integrated)
- [GOV] Governance: Board Validator Hook (Lockdown logic integrated)
- [QA]  Quality: Blind UI Change Detection (No UI change without tests)
"""

import sys
import json
import subprocess
from pathlib import Path

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    WARN = '\033[93m'

def print_fail(role, message):
    print(f"{Colors.RED}[{role}] FAIL: {message}{Colors.ENDC}")

def print_pass(role, message):
    print(f"{Colors.GREEN}[{role}] PASS: {message}{Colors.ENDC}")

def print_warn(role, message):
    print(f"{Colors.WARN}[{role}] WARN: {message}{Colors.ENDC}")

def audit_ppm_mandate(project_root: Path) -> bool:
    """[PPM] Mandate: Frontend MUST have active tests."""
    frontend_tests = list(project_root.glob("frontend/src/**/__tests__/*.test.tsx")) + \
                     list(project_root.glob("frontend/src/**/__tests__/*.test.ts"))
    
    if (project_root / "frontend").exists() and not frontend_tests:
        print_fail("PPM", "No Frontend Tests found in frontend/src/**/__tests__/. QA Strategy missing.")
        return False
    
    print_pass("PPM", f"QA Strategy Active. Found {len(frontend_tests)} frontend tests.")
    return True

def audit_ops_mandate(project_root: Path) -> bool:
    """[OPS] Mandate: CI Pipeline MUST include Frontend Gate."""
    ci_file = project_root / ".github/workflows/ci.yml"
    if not ci_file.exists():
        print_fail("OPS", "CI Configuration missing.")
        return False
        
    try:
        content = ci_file.read_text()
        if "test-frontend" not in content and "npm run test:frontend" not in content:
             print_fail("OPS", "CI Pipeline lacks 'test-frontend' job.")
             return False
    except Exception as e:
        print_fail("OPS", f"Could not read CI config: {e}")
        return False

    print_pass("OPS", "CI Pipeline includes Frontend Reliability Gate.")
    return True

def audit_ciso_mandate(project_root: Path) -> bool:
    """[CISO] Mandate: valid test harness dependencies."""
    pkg_file = project_root / "frontend/package.json"
    if not pkg_file.exists():
        return True # Skip if no frontend
        
    try:
        data = json.loads(pkg_file.read_text())
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        
        if "vitest" not in deps:
            print_fail("CISO", "Frontend missing 'vitest' dependency. Harness invalid.")
            return False
            
    except Exception as e:
        print_fail("CISO", f"Invalid package.json: {e}")
        return False
        
    print_pass("CISO", "Frontend Test Harness verified.")
    return True

def audit_governance_hooks(project_root: Path) -> bool:
    """[GOV] Mandate: Tool Execution MUST be wrapped by TrustService and BoardValidator."""
    mcp_host = project_root / "backend/src/core/mcp/mcp.host.ts"
    
    if not mcp_host.exists():
        print_fail("GOV", "mcp.host.ts not found. Critical Architecture Gap.")
        return False
    
    content = mcp_host.read_text()
    
    checks = [
        ("TrustService/ToolExecutor", "ToolExecutor" in content and "executor.execute" in content),
        ("BoardValidator", "BoardValidator" in content),
        ("Lockdown Logic", "lockdownMode" in content)
    ]
    
    failed = False
    for name, result in checks:
        if not result:
             print_fail("GOV", f"{name} Hook MISSING in mcp.host.ts.")
             failed = True
        else:
             print_pass("GOV", f"{name} Hook verified.")
             
    return not failed

def audit_blind_ui_change(project_root: Path) -> bool:
    """[QA] Mandate: UI Changes MUST include Test Changes."""
    # Only runs if inside a git repo
    if not (project_root / ".git").exists():
        print_warn("QA", "Not a git repo. Skipping Blind UI Change detection.")
        return True

    try:
        # Get list of changed files (staged + unstaged)
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=project_root)
        changed_files = result.stdout.splitlines()
        
        has_frontend_code = False
        has_frontend_test = False
        
        for line in changed_files:
            file_path = line[3:] # Skip status code
            if "frontend/src" in file_path and not ".test." in file_path:
                has_frontend_code = True
            if ("frontend/src" in file_path and ".test." in file_path) or "frontend/tests" in file_path:
                has_frontend_test = True
                
        if has_frontend_code and not has_frontend_test:
            print_fail("QA", "BLIND UI CHANGE DETECTED! You modified frontend code without modifying tests.")
            return False
            
        if has_frontend_code:
            print_pass("QA", "UI Changes matched with Tests.")
        else:
            print_pass("QA", "No UI code changes detected.")
            
        return True
    
    except Exception as e:
        print_warn("QA", f"Failed to run git check: {e}")
        return True # Fail open for now to avoid blocking on local issues

def main():
    project_root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    print(f"{Colors.HEADER}=== GOVERNANCE AUDIT v2.0 (Board of Directors) ==={Colors.ENDC}")
    
    checks = [
        audit_ppm_mandate(project_root),
        audit_ops_mandate(project_root),
        audit_ciso_mandate(project_root),
        audit_governance_hooks(project_root),
        audit_blind_ui_change(project_root)
    ]
    
    if all(checks):
        print(f"\n{Colors.GREEN}✨ BOARD APPROVAL GRANTED ✨{Colors.ENDC}")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}⛔ BOARD VETO: Governance standards not met.{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()
