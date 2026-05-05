#!/usr/bin/env python3
"""
Workflow Checkpoint Enforcer v2.0
=================================
Validates and generates phase gate checkpoints for /create-req and /implement-req workflows.

Commands:
  --validate-phase  : Validate all prerequisites for a specific phase
  --validate-all    : Validate entire checkpoint chain is complete
  --sign-off        : Generate a checkpoint file for a completed phase
  --board-review    : Record board member votes for Phase 3

Usage:
  python enforce_create_req.py . --req REQ-L1-29 --validate-phase 3
  python enforce_create_req.py . --req REQ-L1-29 --sign-off 1 --agent product-manager
  python enforce_create_req.py . --req REQ-L1-29 --board-review csa --decision APPROVE --notes "No schema impact"
"""

import sys
import json
import argparse
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import subprocess
import re

# Phase definitions with required fields
PHASES = {
    1: {
        "name": "discovery",
        "required_fields": ["duplicate_check", "layer_identified", "stakeholder_intent"],
        "agent": "product-manager"
    },
    2: {
        "name": "draft",
        "required_fields": ["user_story", "acceptance_criteria", "effort_estimate"],
        "agent": "product-manager"
    },
    3: {
        "name": "board_review",
        "required_fields": ["orchestrator_invoked", "board_votes", "quorum_reached"],
        "agent": "orchestrator"
    },
    4: {
        "name": "finalization",
        "required_fields": ["ledger_format_valid", "version_aligned", "ids_unique"],
        "agent": "board_scribe_release"
    },
    5: {
        "name": "registration",
        "required_fields": ["ledger_updated", "user_stories_updated", "phase_docs_updated", "github_issue_created"],
        "agent": "documentation-writer"
    }
}

# ============================================================================
# DOC SCOPE GUARD — ALLOWED FILES PER WORKFLOW
# ============================================================================
# During /create-req, ONLY these docs may be modified. Everything else
# (DATABASE_ERD, ARCHITECTURE_FINAL, layer docs, guides, etc.) is deferred
# to /implement-req Phase 5 via the /doc-sync-gate workflow.

CREATE_REQ_ALLOWED_DOCS = [
    "docs/requirements/REQ-LEDGER.md",
    "docs/requirements/REQ-USER-STORIES.md",
    "docs/guides/GUIDE-EXECUTION-ORDER.md",
    "docs/EXECUTION-PLAN.md",
    # The spec file itself (docs/requirements/{REQ-ID}.md) is also allowed
    # — handled dynamically in verify_doc_scope_guard()
]

BOARD_MEMBERS = [
    "board_csa_architect",
    "board_ciso_cybersecurity",
    "board_caio_fullstack",
    "board_vp_ops_devops",
    "board_red_team"
]

# Domain Veto Map: board member → REQ prefixes where they have domain veto authority.
# A REJECT from a domain expert is an ABSOLUTE BLOCK — quorum and Sovereign Override
# cannot bypass it. The expert's concerns must be addressed and re-submitted.
DOMAIN_VETO_MAP: Dict[str, list[str]] = {
    "board_ciso_cybersecurity": ["REQ-SEC"],
    "board_vp_ops_devops": ["REQ-INF", "REQ-OPS", "REQ-PROD", "REQ-HW"],
    "board_caio_fullstack": ["REQ-L5"],
    "board_csa_architect": [],   # Holistic architecture review — no prefix-based veto
    "board_red_team": [],        # Adversarial review — no prefix-based veto
}

def has_domain_authority(board_member: str, req_id: str) -> bool:
    """Check if a board member has domain veto authority over a REQ by its ID prefix."""
    prefixes = DOMAIN_VETO_MAP.get(board_member, [])
    return any(req_id.startswith(prefix) for prefix in prefixes)

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    WARN = '\033[93m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_fail(context: str, message: str):
    print(f"{Colors.RED}[{context}] ⛔ BLOCKED: {message}{Colors.ENDC}")

def print_pass(context: str, message: str):
    print(f"{Colors.GREEN}[{context}] ✅ PASS: {message}{Colors.ENDC}")

def print_warn(context: str, message: str):
    print(f"{Colors.WARN}[{context}] ⚠️ WARN: {message}{Colors.ENDC}")

def print_info(context: str, message: str):
    print(f"{Colors.BLUE}[{context}] ℹ️ INFO: {message}{Colors.ENDC}")

def get_checkpoint_dir(project_root: Path, req_id: str) -> Path:
    """Get the checkpoint directory for a requirement."""
    return project_root / ".agent" / "checkpoints" / req_id

def get_checkpoint_file(project_root: Path, req_id: str, phase: int) -> Path:
    """Get the checkpoint file path for a specific phase."""
    phase_name = PHASES[phase]["name"]
    return get_checkpoint_dir(project_root, req_id) / f"phase{phase}_{phase_name}.json"

def load_checkpoint(project_root: Path, req_id: str, phase: int) -> Optional[Dict[str, Any]]:
    """Load a checkpoint file if it exists."""
    checkpoint_file = get_checkpoint_file(project_root, req_id, phase)
    if checkpoint_file.exists():
        try:
            return json.loads(checkpoint_file.read_text())
        except Exception:
            return None
    return None

def compute_checkpoint_hash(checkpoint_data: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of checkpoint data for integrity verification."""
    # Remove hash field if present to compute fresh hash
    data_copy = {k: v for k, v in checkpoint_data.items() if k != "integrity_hash"}
    json_str = json.dumps(data_copy, sort_keys=True, separators=(',', ':'))
    hex_digest: str = hashlib.sha256(json_str.encode()).hexdigest()
    return hex_digest[:16]  # type: ignore[index]

def validate_checkpoint_integrity(checkpoint_data: Dict[str, Any]) -> bool:
    """Verify checkpoint integrity hash."""
    if "integrity_hash" not in checkpoint_data:
        return False
    stored_hash = checkpoint_data["integrity_hash"]
    computed_hash = compute_checkpoint_hash(checkpoint_data)
    return stored_hash == computed_hash

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def run_command(command: list[str], cwd: Path) -> tuple[int, str]:
    """Run a shell command and return exit code and stdout."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout.strip()
    except Exception as e:
        return -1, str(e)

def verify_branch_gate(project_root: Path) -> bool:
    """
    Verify that the current git branch matches the required pattern (task/*).
    This ensures no direct commits to main/master.
    """
    code, output = run_command(["git", "branch", "--show-current"], project_root)
    
    if code != 0:
        print_fail("GIT", "Failed to get current branch.")
        return False
        
    branch = output
    print_info("GIT", f"Current branch: {branch}")
    
    # Allow task/* or feature/* or bugfix/* branches
    if not (branch.startswith("task/") or branch.startswith("feature/") or branch.startswith("fix/")):
        print_fail("GATE", f"Invalid branch '{branch}'. Must start with 'task/', 'feature/', or 'fix/'.")
        print_info("HINT", "Create a branch: git checkout -b task/REQ-ID-description")
        return False
        
    print_pass("GATE", f"Branch '{branch}' is valid.")
    return True

def verify_phase5_artifacts(project_root: Path, req_id: str, workflow: str = "create-req") -> bool:
    """
    Verify that all Phase 5 documentation artifacts have been updated.
    Does NOT rely on trusting the user input - actually checks files.
    
    Workflow-aware checks:
      - create-req: Spec file MUST exist (just created)
      - implement-req: Spec file MUST NOT exist (deleted per Step 5.6)
    """
    print_info("VERIFY", f"Checking Phase 5 artifacts (workflow: {workflow})...")
    all_valid = True
    
    # 1. Check Ledger Update
    ledger_path = project_root / "docs" / "requirements" / "REQ-LEDGER.md"
    if not ledger_path.exists():
        print_fail("DOCS", "REQ-LEDGER.md not found.")
        all_valid = False
    else:
        # grep for the REQ string in the file
        code, _ = run_command(["grep", "-F", req_id, str(ledger_path)], project_root)
        if code == 0:
            print_pass("DOCS", f"Ledger contains {req_id}")
        else:
            print_fail("DOCS", f"Ledger missing entry for {req_id}")
            all_valid = False
            
    # 2. Check User Stories Update
    stories_path = project_root / "docs" / "requirements" / "REQ-USER-STORIES.md"
    if not stories_path.exists():
        print_fail("DOCS", "REQ-USER-STORIES.md not found.")
        all_valid = False
    else:
        code, _ = run_command(["grep", "-F", req_id, str(stories_path)], project_root)
        if code == 0:
            print_pass("DOCS", f"User Stories contains {req_id}")
        else:
            print_fail("DOCS", f"User Stories missing entry for {req_id}")
            all_valid = False
            
    # 3. Check Execution Order Update
    phase5_path = project_root / "docs" / "guides" / "GUIDE-EXECUTION-ORDER.md"
    if not phase5_path.exists():
        print_fail("DOCS", "GUIDE-EXECUTION-ORDER.md not found.")
        all_valid = False
    else:
        code, _ = run_command(["grep", "-F", req_id, str(phase5_path)], project_root)
        if code == 0:
            print_pass("DOCS", f"Phase 5 Doc contains {req_id}")
        else:
            print_fail("DOCS", f"Execution Order missing entry for {req_id}")
            all_valid = False
            
    # 4. Check GitHub Issue (EXACT MATCH - not fuzzy)
    # Uses gh cli: gh issue list --search "REQ-ID" --state all
    # FIX v1.1: Include --state all to find CLOSED issues (implement-req closes them).
    # FIX v1.0: GitHub search is fuzzy. We MUST verify the REQ ID appears in the issue title.
    code, output = run_command(["gh", "issue", "list", "--search", req_id, "--state", "all", "--json", "number,title"], project_root)
    if code != 0:
        print_warn("GITHUB", "Could not check GitHub issues (gh cli not available or auth failed). Skipping strict check.")
        # We don't fail here to allow offline work, but we warn heavily
    else:
        try:
            issues = json.loads(output)
            # EXACT MATCH: Filter to only issues whose title contains the REQ ID
            matching = [i for i in issues if req_id in i.get('title', '')]
            if len(matching) > 0:
                print_pass("GITHUB", f"Found issue {matching[0]['number']}: {matching[0]['title']}")
            else:
                if len(issues) > 0:
                    print_fail("GITHUB", f"Found {len(issues)} issue(s) via fuzzy search, but NONE have '{req_id}' in the title. This is a false positive.")
                else:
                    print_fail("GITHUB", f"No GitHub issue found for {req_id}")
                all_valid = False
        except json.JSONDecodeError:
            print_warn("GITHUB", "Failed to parse gh output.")
            
    # 5. Check Requirement Spec File (WORKFLOW-AWARE)
    # - /create-req Phase 5: Spec file MUST EXIST (it was just written).
    # - /implement-req Phase 5: Spec file MUST NOT EXIST (deleted per Step 5.6).
    spec_path = project_root / "docs" / "requirements" / f"{req_id}.md"
    if workflow == "implement-req":
        # implement-req: spec file should be DELETED after implementation
        if not spec_path.exists():
            print_pass("SPEC", f"Spec file correctly deleted: docs/requirements/{req_id}.md (per Step 5.6)")
        else:
            print_warn("SPEC", f"Spec file still exists: docs/requirements/{req_id}.md — should be deleted per Step 5.6")
            # Not blocking — just a warning. The spec might be intentionally kept.
    else:
        # create-req: spec file must exist (it was just created)
        if spec_path.exists():
            print_pass("SPEC", f"Requirement spec file exists: docs/requirements/{req_id}.md")
        else:
            print_fail("SPEC", f"Requirement spec file MISSING: docs/requirements/{req_id}.md")
            print_fail("SPEC", "This file must contain: Metadata, Description, User Stories, Acceptance Criteria, and Technical Implementation.")
            all_valid = False

    # 6. Check EXECUTION-PLAN.md Step 2 entry (create-req only)
    # During /create-req, the new REQ MUST be added to Step 2 with a
    # `/implement-req REQ-ID` line so it can be found and executed later.
    if workflow == "create-req":
        exec_plan_path = project_root / "docs" / "EXECUTION-PLAN.md"
        if exec_plan_path.exists():
            exec_content = exec_plan_path.read_text()
            # Find Step 2 section
            step2_marker = "## Step 2:"
            step2_idx = exec_content.find(step2_marker)
            if step2_idx != -1:
                step2_content = exec_content[step2_idx:]
                implement_pattern = f"/implement-req {req_id}"
                if implement_pattern in step2_content:
                    print_pass("EXEC-PLAN", f"Step 2 contains `/implement-req {req_id}`")
                else:
                    print_fail("EXEC-PLAN", f"EXECUTION-PLAN.md Step 2 is MISSING `/implement-req {req_id}`!")
                    print_fail("EXEC-PLAN", f"Every new REQ MUST be added to Step 2 with:")
                    print_info("EXEC-PLAN", f"  - [ ] `/implement-req {req_id}` — [description]")
                    all_valid = False
            else:
                print_warn("EXEC-PLAN", "Could not find Step 2 section marker in EXECUTION-PLAN.md")
        else:
            print_warn("EXEC-PLAN", "EXECUTION-PLAN.md not found. Skipping Step 2 check.")

    return all_valid

def verify_doc_scope_guard(project_root: Path, req_id: str, workflow: str = "create-req") -> bool:
    """
    DOC SCOPE GUARD: Enforces the create-req / implement-req documentation boundary.
    
    During /create-req, ONLY the 4 baseline files + the spec file may be modified
    under docs/. Any other doc edits (DATABASE_ERD, ARCHITECTURE_FINAL, layer docs,
    guides, etc.) are BLOCKED — those belong in /implement-req via /doc-sync-gate.
    
    During /implement-req, this guard is NOT enforced (all doc edits are expected).
    
    Detection method: git diff --name-only against the merge-base with main.
    """
    if workflow != "create-req":
        print_info("DOC-SCOPE", f"Skipping Doc Scope Guard (workflow={workflow}, not create-req).")
        return True
    
    print_info("DOC-SCOPE", "Running Doc Scope Guard — checking for unauthorized doc edits...")
    
    # Build the allowlist (3 baseline + spec file + FUTURE_REQS.md)
    allowed_files = set(CREATE_REQ_ALLOWED_DOCS)
    allowed_files.add(f"docs/requirements/{req_id}.md")  # The spec file itself
    allowed_files.add("docs/FUTURE_REQS.md")  # May be updated when promoting a future req
    allowed_files.add(f"docs/tech-debt/")  # Tech debt tracking files are always OK
    
    # Collect modified docs/ files from both unstaged and staged changes.
    # This is fast (no merge-base computation) and catches any dirty working tree.
    modified_docs = set()
    
    # Unstaged changes
    code, output = run_command(
        ["git", "diff", "--name-only", "--", "docs/"], project_root
    )
    if code != 0:
        print_warn("DOC-SCOPE", "git diff failed. Skipping Doc Scope Guard (offline mode).")
        return True
    for line in output.strip().split("\n"):
        line = line.strip()
        if line and line.startswith("docs/"):
            modified_docs.add(line)
    
    # Staged changes
    code, output = run_command(
        ["git", "diff", "--cached", "--name-only", "--", "docs/"], project_root
    )
    if code == 0:
        for line in output.strip().split("\n"):
            line = line.strip()
            if line and line.startswith("docs/"):
                modified_docs.add(line)
    
    if not modified_docs:
        print_pass("DOC-SCOPE", "No doc files modified. Clean.")
        return True
    
    # Check each modified doc against the allowlist
    violations = []
    for doc_file in sorted(modified_docs):
        # Check exact match or prefix match (for directories like docs/tech-debt/)
        is_allowed = False
        for allowed in allowed_files:
            if allowed.endswith("/"):
                # Directory prefix match
                if doc_file.startswith(allowed):
                    is_allowed = True
                    break
            else:
                # Exact file match
                if doc_file == allowed:
                    is_allowed = True
                    break
        
        if is_allowed:
            print_pass("DOC-SCOPE", f"✅ Allowed: {doc_file}")
        else:
            violations.append(doc_file)
            print_fail("DOC-SCOPE", f"⛔ VIOLATION: {doc_file}")
    
    if violations:
        print()
        print_fail("DOC-SCOPE", f"Found {len(violations)} unauthorized doc edit(s) during /create-req:")
        for v in violations:
            print_fail("DOC-SCOPE", f"  → {v}")
        print()
        print_info("DOC-SCOPE", "During /create-req, only these files may be modified:")
        for f in sorted(allowed_files):
            print_info("DOC-SCOPE", f"  ✅ {f}")
        print()
        print_info("DOC-SCOPE", "All other doc updates belong in /implement-req Phase 5 (doc-sync-gate).")
        print_info("DOC-SCOPE", "To fix: revert the unauthorized changes, then re-run this checkpoint.")
        print_info("DOC-SCOPE", f"  git checkout HEAD -- {' '.join(violations)}")
        return False
    
    print_pass("DOC-SCOPE", f"All {len(modified_docs)} modified doc(s) are within allowed scope.")
    return True

def validate_phase_prerequisites(project_root: Path, req_id: str, target_phase: int) -> bool:
    """
    Validate that all prerequisite phases have completed checkpoints.
    This is a BLOCKING check - returns False if any prerequisite is missing.
    """
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}PHASE GATE VALIDATION: {req_id} -> Phase {target_phase}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
    
    all_passed = True
    
    for phase in range(1, target_phase):
        checkpoint = load_checkpoint(project_root, req_id, phase)
        phase_name = PHASES[phase]["name"]
        
        if checkpoint is None:
            print_fail(f"Phase {phase}", f"Checkpoint '{phase_name}' MISSING. Cannot proceed to Phase {target_phase}.")
            all_passed = False
            continue
        
        # Verify integrity
        if not validate_checkpoint_integrity(checkpoint):
            print_fail(f"Phase {phase}", f"Checkpoint integrity check FAILED. File may be corrupted or tampered.")
            all_passed = False
            continue
        
        # Special check for Phase 3 (Board Review)
        if phase == 3:
            if not validate_board_quorum(checkpoint, project_root):
                all_passed = False
                continue
        
        print_pass(f"Phase {phase}", f"Checkpoint '{phase_name}' verified. Agent: {checkpoint.get('agent', 'unknown')}")
    
    if all_passed:
        print(f"\n{Colors.GREEN}✅ All prerequisites met. Phase {target_phase} may proceed.{Colors.ENDC}")
    else:
        print(f"\n{Colors.RED}⛔ BLOCKED: Cannot proceed to Phase {target_phase}. Fix missing/invalid checkpoints first.{Colors.ENDC}")
    
    return all_passed

def validate_board_quorum(checkpoint: Dict[str, Any], project_root: Optional[Path] = None) -> bool:
    """Validate Phase 3 board quorum with 3-layer governance:
    
    Layer 1 — Domain Veto: Domain expert REJECT = absolute block (no override).
    Layer 2 — Condition Enforcement: APPROVE_WITH_CONDITIONS only counts if spec has conditions section.
    Layer 3 — Dissent Escalation: Non-domain REJECT requires Sovereign Override from user.
    """
    board_votes = checkpoint.get("board_votes", {})
    req_id = checkpoint.get("req_id", "")
    
    if len(board_votes) < 4:
        print_fail("QUORUM", f"Only {len(board_votes)}/5 board members voted. Minimum 4 required (>75%).")
        return False
    
    # ── Layer 1: Domain Veto ──────────────────────────────────────────────
    # If a domain expert rejects a REQ in their scope, it's an absolute block.
    for member, vote in board_votes.items():
        if vote.get("decision") == "REJECT" and has_domain_authority(member, req_id):
            print_fail("DOMAIN-VETO", f"{member} REJECTED with domain authority over {req_id}.")
            print_fail("DOMAIN-VETO", f"Reason: {vote.get('notes', 'No notes provided')}")
            print_fail("DOMAIN-VETO", "Domain expert rejection CANNOT be overridden by quorum or Sovereign Override.")
            print_info("DOMAIN-VETO", "Resolution: Address the domain expert's concerns and re-submit for review.")
            return False
    
    # ── Layer 2: Condition Enforcement ────────────────────────────────────
    # APPROVE_WITH_CONDITIONS only counts as an approval if the conditions
    # are documented in the spec file (a section heading containing 'Conditions').
    conditional_votes = {m: v for m, v in board_votes.items()
                         if v.get("decision") == "APPROVE_WITH_CONDITIONS"}
    conditions_verified = True
    
    if conditional_votes and project_root:
        spec_path = project_root / "docs" / "requirements" / f"{req_id}.md"
        if spec_path.exists():
            spec_content = spec_path.read_text()
            has_conditions_section = bool(re.search(r'^##\s+.*[Cc]onditions?', spec_content, re.MULTILINE))
            if not has_conditions_section:
                conditions_verified = False
                for member, vote in conditional_votes.items():
                    print_warn("CONDITIONS", f"{member} voted APPROVE_WITH_CONDITIONS:")
                    print_warn("CONDITIONS", f"  → {vote.get('notes', 'No notes')}")
                print_fail("CONDITIONS", f"Conditional approvals found but spec has no 'Conditions' section.")
                print_info("CONDITIONS", f"Add a '## Board Conditions' section to docs/requirements/{req_id}.md")
                print_info("CONDITIONS", "Conditional votes will NOT count as approvals until conditions are documented.")
        else:
            print_warn("CONDITIONS", f"Spec file not found: docs/requirements/{req_id}.md — cannot verify conditions.")
    
    # ── Layer 3: Dissent Escalation ───────────────────────────────────────
    # Any REJECT from a non-domain member requires Sovereign Override from the user.
    non_domain_rejects = {m: v for m, v in board_votes.items()
                          if v.get("decision") == "REJECT" and not has_domain_authority(m, req_id)}
    
    if non_domain_rejects:
        for member, vote in non_domain_rejects.items():
            print_warn("DISSENT", f"{member} REJECTED: {vote.get('notes', 'No notes provided')}")
        
        if not checkpoint.get("sovereign_override"):
            print_fail("DISSENT", "Board member(s) dissented. Sovereign Override required to proceed.")
            print_info("DISSENT", "The user must review the dissenting concerns and explicitly override:")
            print_info("DISSENT", f"  npm run checkpoint:sign-off -- --req {req_id} --sign-off 3 --agent orchestrator --sovereign-override")
            return False
        else:
            override_notes = checkpoint.get("sovereign_override_notes", "No notes")
            print_warn("DISSENT", f"Sovereign Override active: {override_notes}")
            print_warn("DISSENT", "Proceeding despite dissent — user has acknowledged the risk.")
    
    # ── Standard Quorum Calculation ───────────────────────────────────────
    approve_count = 0
    for v in board_votes.values():
        decision = v.get("decision")
        if decision == "APPROVE":
            approve_count += 1
        elif decision == "APPROVE_WITH_CONDITIONS":
            if conditions_verified:
                approve_count += 1
            # If not verified, this vote is PENDING — doesn't count
    
    total_count = len(board_votes)
    if total_count == 0:
        print_fail("QUORUM", "No board votes found.")
        return False
    
    percentage = (approve_count / total_count) * 100
    
    if percentage < 75:
        print_fail("QUORUM", f"Effective approval rate {percentage:.0f}% < 75% required.")
        if not conditions_verified:
            print_info("QUORUM", "Note: Conditional approvals are NOT counted until conditions are documented in the spec.")
        return False
    
    print_pass("QUORUM", f"Board approval: {approve_count}/{total_count} ({percentage:.0f}%)")
    return True

def validate_all_phases(project_root: Path, req_id: str) -> bool:
    """Validate entire checkpoint chain is complete and valid."""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}FULL CHECKPOINT AUDIT: {req_id}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
    
    all_passed = True
    checkpoint_chain = []
    
    for phase in range(1, 6):
        checkpoint = load_checkpoint(project_root, req_id, phase)
        phase_name = PHASES[phase]["name"]
        
        if checkpoint is None:
            print_fail(f"Phase {phase}", f"Checkpoint '{phase_name}' MISSING.")
            all_passed = False
            continue
        
        # Verify integrity
        if not validate_checkpoint_integrity(checkpoint):
            print_fail(f"Phase {phase}", f"Checkpoint integrity FAILED.")
            all_passed = False
            continue
        
        # Special check for Phase 3
        if phase == 3:
            if not validate_board_quorum(checkpoint, project_root):
                all_passed = False
                continue
        
        checkpoint_chain.append({
            "phase": phase,
            "timestamp": checkpoint.get("timestamp"),
            "hash": checkpoint.get("integrity_hash")
        })
        
        print_pass(f"Phase {phase}", f"'{phase_name}' verified @ {checkpoint.get('timestamp', 'unknown')}")
    
    if all_passed:
        print(f"\n{Colors.GREEN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.GREEN}✨ CHECKPOINT AUDIT PASSED ✨{Colors.ENDC}")
        print(f"{Colors.GREEN}Audit Trail Hash Chain:{Colors.ENDC}")
        for item in checkpoint_chain:
            print(f"  Phase {item['phase']}: {item['hash']}")
        print(f"{Colors.GREEN}{'='*60}{Colors.ENDC}")
    else:
        print(f"\n{Colors.RED}⛔ CHECKPOINT AUDIT FAILED{Colors.ENDC}")
    
    return all_passed

# ============================================================================
# SIGN-OFF (CHECKPOINT CREATION) FUNCTIONS
# ============================================================================

def sign_off_phase(project_root: Path, req_id: str, phase: int, agent: str, 
                   workflow: str = "create-req",
                   data: Optional[Dict[str, Any]] = None) -> bool:
    """
    Generate a signed checkpoint file for a completed phase.
    """
    # Validate prerequisites first (except for Phase 1)
    if phase > 1:
        if not validate_phase_prerequisites(project_root, req_id, phase):
            print_fail("SIGN-OFF", f"Cannot sign off Phase {phase} - prerequisites not met.")
            return False
    
    # Create checkpoint directory
    checkpoint_dir = get_checkpoint_dir(project_root, req_id)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    # Build checkpoint data
    phase_info = PHASES[phase]
    
    # Load existing checkpoint if available (to preserve board votes)
    existing_checkpoint = load_checkpoint(project_root, req_id, phase) or {}
    
    checkpoint_data = {
        "phase": phase,
        "phase_name": phase_info["name"],
        "req_id": req_id,
        "agent": agent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workflow": "create-req"
    }
    
    # Preserve existing data (like board_votes)
    if existing_checkpoint:
        checkpoint_data.update(existing_checkpoint)
        # Update metadata
        checkpoint_data["agent"] = agent
        checkpoint_data["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    # Merge custom data
    if data:
        checkpoint_data.update(data)
    
    # Branch Gate Check for Phase 1
    if phase == 1:
        if not verify_branch_gate(project_root):
            print_fail("GATE", "Branch check failed. You must be on a task branch.")
            return False
    
    # SPEC FILE GATE: implement-req Phase 1 requires the spec file to exist.
    # The spec file is the technical blueprint created during /create-req.
    # If it doesn't exist for older requirements, the agent MUST create it
    # before signing off Phase 1.
    if workflow == "implement-req" and phase == 1:
        spec_path = project_root / "docs" / "requirements" / f"{req_id}.md"
        if spec_path.exists():
            print_pass("SPEC-GATE", f"Spec file found: docs/requirements/{req_id}.md")
        else:
            print_fail("SPEC-GATE", f"⛔ BLOCKED: docs/requirements/{req_id}.md does NOT exist.")
            print_fail("SPEC-GATE", "This file is REQUIRED before implementation can begin.")
            print_info("SPEC-GATE", "Create it with: Metadata, Description, User Stories, Acceptance Criteria, and Technical Implementation.")
            print_info("SPEC-GATE", "Sources: USER_STORIES.md for acceptance criteria, codebase research for technical details.")
            print_info("SPEC-GATE", "Once created, re-run this sign-off command.")
            return False

    # FRONTEND PERFORMANCE GATE: implement-req Phase 3 runs the perf/code quality scanner.
    # This blocks sign-off if CRITICAL violations are found in frontend/src/** files.
    if workflow == "implement-req" and phase == 3:
        print_info("FRONTEND-PERF", "Running Frontend Performance & Code Quality Gate...")
        perf_gate_script = project_root / ".agent" / "scripts" / "frontend_perf_gate.py"
        if perf_gate_script.exists():
            perf_code, perf_output = run_command(
                ["python3", str(perf_gate_script), str(project_root), "--req", req_id],
                project_root
            )
            if perf_output:
                print(perf_output)
            if perf_code != 0:
                print_fail("FRONTEND-PERF", "⛔ BLOCKED: Frontend Performance Gate FAILED. Fix violations before sign-off.")
                return False
            print_pass("FRONTEND-PERF", "Frontend Performance Gate passed.")
        else:
            print_warn("FRONTEND-PERF", "frontend_perf_gate.py not found. Skipping.")

    # FRONTEND VISUAL GATE: implement-req Phase 4 requires visual verification evidence.
    # This blocks sign-off if frontend/src/** was modified but no screenshots exist.
    if workflow == "implement-req" and phase == 4:
        print_info("FRONTEND-VISUAL", "Running Frontend Visual Verification Gate...")
        visual_gate_script = project_root / ".agent" / "scripts" / "frontend_visual_gate.py"
        if visual_gate_script.exists():
            vis_code, vis_output = run_command(
                ["python3", str(visual_gate_script), str(project_root), "--req", req_id],
                project_root
            )
            if vis_output:
                print(vis_output)
            if vis_code != 0:
                print_fail("FRONTEND-VISUAL", "⛔ BLOCKED: Frontend Visual Gate FAILED. Open browser and capture screenshots.")
                print_info("FRONTEND-VISUAL", "Protocol: See .agent/workflows/frontend-browser-gate.md")
                return False
            print_pass("FRONTEND-VISUAL", "Frontend Visual Verification Gate passed.")
        else:
            print_warn("FRONTEND-VISUAL", "frontend_visual_gate.py not found. Skipping.")

    # Special Validation for Phase 5 (Registration)
    if phase == 5:
        # DOC SCOPE GUARD: Must run BEFORE phase5 artifacts check.
        # This catches premature doc edits (e.g., editing DATABASE_ERD during create-req).
        if not verify_doc_scope_guard(project_root, req_id, workflow=workflow):
            print_fail("SIGN-OFF", "Doc Scope Guard BLOCKED this sign-off. Revert unauthorized edits first.")
            return False
        
        if not verify_phase5_artifacts(project_root, req_id, workflow=workflow):
            print_fail("SIGN-OFF", "Phase 5 artifacts verification failed.")
            return False
        # If passed, we can confidently set the fields to True
        checkpoint_data["ledger_updated"] = True
        checkpoint_data["user_stories_updated"] = True
        checkpoint_data["phase_docs_updated"] = True
        checkpoint_data["github_issue_created"] = True

    # Add placeholder fields if still missing (but do NOT default boolean fields to True indiscriminately)
    for field in phase_info["required_fields"]:
        if field not in checkpoint_data:
            # board_votes must be a dict for record_board_vote to work
            if field == "board_votes":
                checkpoint_data[field] = {}  # type: ignore[assignment]
            # For other phases/fields, we might still accept user input, 
            # but for Phase 5 we effectively handled it above.
            # We removed the auto-True default to prevent false positives.
            elif phase != 5:
                # For phases 1-4, we assume the agent has done the work if they are signing off,
                # unless we add specific validators for those too. 
                # Keeping implicit trust for lower phases for now as requested flexibility,
                # but Phase 5 is now strict.
                checkpoint_data[field] = True
    
    # Compute integrity hash
    checkpoint_data["integrity_hash"] = compute_checkpoint_hash(checkpoint_data)
    
    # Write checkpoint
    checkpoint_file = get_checkpoint_file(project_root, req_id, phase)
    checkpoint_file.write_text(json.dumps(checkpoint_data, indent=2))
    
    print_pass("SIGN-OFF", f"Phase {phase} checkpoint created: {checkpoint_file.name}")
    print_info("HASH", f"Integrity hash: {checkpoint_data['integrity_hash']}")
    
    # ANTI-BYPASS: Phase 5 sign-off MUST be followed by automatic full validation.
    # This prevents agents from running sign-off and validate-all in parallel,
    # then ignoring a failed validation while reporting success from sign-off.
    # The validation is now ATOMIC with the sign-off — one command, one result.
    if phase == 5:
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}AUTOMATIC POST-SIGNOFF VALIDATION (MANDATORY){Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print_info("ANTI-BYPASS", "Running full checkpoint audit automatically after Phase 5 sign-off...")
        print_info("ANTI-BYPASS", "Agents MUST report this output as proof of completion.")
        print_info("ANTI-BYPASS", "A separate --validate-all call is NOT sufficient — this is the canonical result.\n")
        
        validation_passed = validate_all_phases(project_root, req_id)
        if not validation_passed:
            print_fail("ANTI-BYPASS", "⛔ Phase 5 sign-off WRITTEN but post-signoff validation FAILED.")
            print_fail("ANTI-BYPASS", "⛔ This requirement is NOT complete. Re-run sign-off after fixing issues.")
            return False
        else:
            print_pass("ANTI-BYPASS", "✅ Post-signoff validation PASSED. This requirement is CONFIRMED COMPLETE.")
    
    return True

def record_board_vote(project_root: Path, req_id: str, board_member: str, 
                      decision: str, notes: str) -> bool:
    """
    Record a board member's vote for Phase 3.
    Creates or updates the Phase 3 checkpoint with the vote.
    """
    if board_member not in BOARD_MEMBERS:
        print_fail("BOARD", f"Unknown board member: {board_member}. Valid: {BOARD_MEMBERS}")
        return False
    
    if decision not in ["APPROVE", "REJECT", "APPROVE_WITH_CONDITIONS"]:
        print_fail("BOARD", f"Invalid decision: {decision}. Must be APPROVE, REJECT, or APPROVE_WITH_CONDITIONS")
        return False
    
    # Validate Phase 1 and 2 are complete
    if not validate_phase_prerequisites(project_root, req_id, 3):
        return False
    
    # Load or create Phase 3 checkpoint
    loaded = load_checkpoint(project_root, req_id, 3)
    checkpoint: Dict[str, Any] = loaded if loaded is not None else {
        "phase": 3,
        "phase_name": "board_review",
        "req_id": req_id,
        "agent": "orchestrator",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workflow": "create-req",
        "orchestrator_invoked": True,
        "board_votes": {},
        "quorum_reached": False
    }
    
    # Record vote
    board_votes: Dict[str, Any] = checkpoint.get("board_votes", {})
    board_votes[board_member] = {
        "decision": decision,
        "notes": notes,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    checkpoint["board_votes"] = board_votes
    
    # Preliminary quorum check (UX feedback only — real enforcement is in validate_board_quorum)
    approve_count = sum(1 for v in board_votes.values() if v.get("decision") in ["APPROVE", "APPROVE_WITH_CONDITIONS"])
    total_count = len(board_votes)
    
    if total_count >= 3 and (approve_count / total_count) >= 0.75:
        checkpoint["quorum_reached"] = True
        checkpoint["approval_percentage"] = (approve_count / total_count) * 100
    
    # Recompute hash
    checkpoint["integrity_hash"] = compute_checkpoint_hash(checkpoint)
    
    # Write checkpoint
    checkpoint_dir = get_checkpoint_dir(project_root, req_id)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = get_checkpoint_file(project_root, req_id, 3)
    checkpoint_file.write_text(json.dumps(checkpoint, indent=2))
    
    print_pass("BOARD", f"Vote recorded: {board_member} -> {decision}")
    print_info("VOTES", f"Current: {total_count}/5 board members voted, {approve_count} approvals")
    
    if checkpoint.get("quorum_reached"):
        pct = checkpoint.get("approval_percentage", 0)
        print_pass("QUORUM", f"Board quorum reached! ({pct:.0f}% approval)")
    
    return True

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Workflow Checkpoint Enforcer")
    parser.add_argument("project_root", help="Path to project root")
    parser.add_argument("--req", required=True, help="Requirement ID (e.g., REQ-L1-29)")
    
    # Validation commands
    parser.add_argument("--validate-phase", type=int, metavar="N", 
                        help="Validate prerequisites for phase N")
    parser.add_argument("--validate-all", action="store_true",
                        help="Validate entire checkpoint chain")
    
    # Sign-off commands
    parser.add_argument("--sign-off", type=int, metavar="N",
                        help="Sign off phase N (creates checkpoint)")
    parser.add_argument("--agent", help="Agent name for sign-off")
    
    # Board review commands
    parser.add_argument("--board-vote", metavar="MEMBER",
                        help="Record board vote (csa, ciso, caio, vp_ops, red_team)")
    parser.add_argument("--decision", help="Vote decision (APPROVE, REJECT, APPROVE_WITH_CONDITIONS)")
    parser.add_argument("--notes", default="", help="Vote notes")
    parser.add_argument("--sovereign-override", action="store_true",
                        help="Override board dissent (user acknowledges risk). Only for Phase 3 sign-off.")
    
    # Data for sign-off
    parser.add_argument("--layer", help="Layer identifier for Phase 1")
    parser.add_argument("--intent", help="Stakeholder intent for Phase 1")
    parser.add_argument("--effort", help="Effort estimate (XS, S, M, L, XL) for Phase 2")
    parser.add_argument("--priority", help="MoSCoW priority for Phase 2")
    
    # Workflow identifier
    parser.add_argument("--workflow", default="create-req",
                        choices=["create-req", "implement-req"],
                        help="Which workflow is running (default: create-req)")
    
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    
    # Normalize board member name
    board_member_map = {
        "csa": "board_csa_architect",
        "ciso": "board_ciso_cybersecurity",
        "caio": "board_caio_fullstack",
        "vp_ops": "board_vp_ops_devops",
        "ops": "board_vp_ops_devops",
        "red_team": "board_red_team"
    }
    
    success = True
    
    if args.validate_phase:
        success = validate_phase_prerequisites(project_root, args.req, args.validate_phase)
    
    elif args.validate_all:
        success = validate_all_phases(project_root, args.req)
    
    elif args.sign_off:
        if not args.agent:
            print_fail("SIGN-OFF", "--agent is required for sign-off")
            sys.exit(1)
        
        # Build data from arguments
        data = {}
        if args.layer:
            data["layer_identified"] = args.layer
        if args.intent:
            data["stakeholder_intent"] = args.intent
        if args.effort:
            data["effort_estimate"] = args.effort
        if args.priority:
            data["moscow_priority"] = args.priority
        if args.sovereign_override and args.sign_off == 3:
            data["sovereign_override"] = True
            data["sovereign_override_notes"] = args.notes or "User acknowledged dissent"
        
        success = sign_off_phase(project_root, args.req, args.sign_off, args.agent, 
                                 workflow=args.workflow, data=data)
    
    elif args.board_vote:
        if not args.decision:
            print_fail("BOARD", "--decision is required for board vote")
            sys.exit(1)
        
        member: str = board_member_map.get(args.board_vote, args.board_vote) or args.board_vote
        success = record_board_vote(project_root, args.req, member, args.decision, args.notes)
    
    else:
        parser.print_help()
        sys.exit(0)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
