#!/bin/bash
# =============================================================================
# validate-user-story.sh — Enforces Definition of Done in User Stories
# =============================================================================
# Validates that a REQ's user story in REQ-USER-STORIES.md contains all
# mandatory fields introduced by the create-req Step 2.2 template.
#
# Usage: bash scripts/validate-user-story.sh <REQ-ID>
# Exit codes: 0 = PASS, 1 = FAIL
# =============================================================================

set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "❌ Usage: bash scripts/validate-user-story.sh <REQ-ID>"
  echo "   Example: bash scripts/validate-user-story.sh REQ-L6-20"
  exit 1
fi

REQ_ID="$1"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STORIES_FILE="$PROJECT_ROOT/docs/requirements/REQ-USER-STORIES.md"

if [ ! -f "$STORIES_FILE" ]; then
  echo "❌ FATAL: $STORIES_FILE not found"
  exit 1
fi

# =============================================================================
# Extract the user story block for this REQ-ID
# Range: from the heading containing REQ-ID to the next "---" separator
# =============================================================================
STORY_BLOCK=$(awk -v req="$REQ_ID" '
  BEGIN { found=0 }
  /^###/ && index($0, req) { found=1 }
  found && /^---$/ && NR>1 { exit }
  found { print }
' "$STORIES_FILE")

if [ -z "$STORY_BLOCK" ]; then
  echo "❌ FAIL: No user story found for $REQ_ID in REQ-USER-STORIES.md"
  exit 1
fi

echo "============================================="
echo "  USER STORY VALIDATION — $REQ_ID"
echo "============================================="

FAILURES=0

# =============================================================================
# CHECK 1: Completeness Definition exists and is non-empty
# =============================================================================
if echo "$STORY_BLOCK" | grep -q "^\*\*Completeness Definition:\*\*"; then
  # Check that the line after the heading is not empty/placeholder
  COMP_DEF=$(echo "$STORY_BLOCK" | awk '/^\*\*Completeness Definition:\*\*/{found=1; next} found && /^-/{print; exit}')
  if [ -z "$COMP_DEF" ] || echo "$COMP_DEF" | grep -qiE '(n/a|tbd|todo|placeholder)'; then
    echo "  ❌ CHECK 1: Completeness Definition is empty or placeholder"
    FAILURES=$((FAILURES + 1))
  else
    echo "  ✅ CHECK 1: Completeness Definition present"
  fi
else
  echo "  ❌ CHECK 1: Missing **Completeness Definition:** section"
  FAILURES=$((FAILURES + 1))
fi

# =============================================================================
# CHECK 2: Acceptance Criteria exist and are behavior-driven (not structural)
# =============================================================================
AC_LINES=$(echo "$STORY_BLOCK" | grep -E '^\s*- \[[ x]\]' || true)
AC_COUNT=$(echo "$AC_LINES" | grep -c '.' || echo 0)

if [ "$AC_COUNT" -lt 2 ]; then
  echo "  ❌ CHECK 2: Fewer than 2 Acceptance Criteria found ($AC_COUNT)"
  FAILURES=$((FAILURES + 1))
else
  # Detect structural-only AC (class/file existence checks)
  STRUCTURAL=$(echo "$AC_LINES" | grep -ciE '(class exists|file exists|table exists|component exists|service exists|.toBeDefined)' || echo 0)
  if [ "$STRUCTURAL" -gt 0 ]; then
    echo "  ⚠️  CHECK 2: $STRUCTURAL AC line(s) appear structural, not behavioral"
    echo "            Structural AC (e.g., 'class exists') are not sufficient."
    echo "            AC must test end-to-end behavior or data flow."
    FAILURES=$((FAILURES + 1))
  else
    echo "  ✅ CHECK 2: Acceptance Criteria present ($AC_COUNT) and behavioral"
  fi
fi

# =============================================================================
# CHECK 3: Anti-Acceptance Criteria section exists
# =============================================================================
if echo "$STORY_BLOCK" | grep -q "^\*\*Anti-Acceptance Criteria"; then
  echo "  ✅ CHECK 3: Anti-Acceptance Criteria present"
else
  echo "  ❌ CHECK 3: Missing **Anti-Acceptance Criteria** section"
  FAILURES=$((FAILURES + 1))
fi

# =============================================================================
# CHECK 4: Stub prohibition line exists
# =============================================================================
if echo "$STORY_BLOCK" | grep -qi "stub.*mock.*production\|no core business logic.*stub"; then
  echo "  ✅ CHECK 4: Stub prohibition clause present"
else
  echo "  ⚠️  CHECK 4: No explicit stub prohibition clause found"
  echo "            Expected: 'No core business logic may be stubbed or mocked in production execution.'"
  FAILURES=$((FAILURES + 1))
fi

# =============================================================================
# VERDICT
# =============================================================================
echo "============================================="
if [ "$FAILURES" -gt 0 ]; then
  echo "  ❌ VALIDATION FAILED — $FAILURES check(s) failed"
  echo "  ⛔ Phase 2 checkpoint is BLOCKED."
  echo "  Fix the user story in REQ-USER-STORIES.md"
  echo "  and re-run: bash scripts/validate-user-story.sh $REQ_ID"
  echo "============================================="
  exit 1
else
  echo "  ✅ ALL CHECKS PASSED"
  echo "  Phase 2 checkpoint may proceed."
  echo "============================================="
  exit 0
fi
