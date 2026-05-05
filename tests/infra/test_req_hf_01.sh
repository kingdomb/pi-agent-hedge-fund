#!/usr/bin/env bash
# =============================================================================
# tests/infra/test_req_hf_01.sh — Smoke Tests for REQ-HF-01
# =============================================================================
# Verifies all acceptance criteria for the Local Infrastructure & Zero-Cost
# Dev Loop requirement (REQ-HF-01). Uses --dry-run for process-safe testing.
#
# Exit codes: 0 = ALL PASS, 1 = FAILURES
# Usage: bash tests/infra/test_req_hf_01.sh
# @REQ-HF-01
# =============================================================================

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PASS=0
FAIL=0
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✅ PASS${NC}: $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}❌ FAIL${NC}: $1"; FAIL=$((FAIL + 1)); }
info() { echo -e "  ${YELLOW}ℹ️  INFO${NC}: $1"; }

echo "============================================="
echo "  REQ-HF-01 Smoke Tests"
echo "  Project: $PROJECT_ROOT"
echo "============================================="

# -----------------------------------------------------------------------------
# AC: start.sh exists and is executable
# -----------------------------------------------------------------------------
echo ""
echo "--- File Presence ---"
if [ -x "$PROJECT_ROOT/start.sh" ]; then
  pass "start.sh exists and is executable"
else
  fail "start.sh missing or not executable"
fi

if [ -x "$PROJECT_ROOT/stop.sh" ]; then
  pass "stop.sh exists and is executable"
else
  fail "stop.sh missing or not executable"
fi

if [ -x "$PROJECT_ROOT/cost-profiler.sh" ]; then
  pass "cost-profiler.sh exists and is executable"
else
  fail "cost-profiler.sh missing or not executable"
fi

if [ -f "$PROJECT_ROOT/.env.dev.example" ]; then
  pass ".env.dev.example exists"
else
  fail ".env.dev.example missing"
fi

# -----------------------------------------------------------------------------
# AC: .env.dev.example stubs all required keys
# -----------------------------------------------------------------------------
echo ""
echo "--- .env.dev.example Key Stubs ---"
ENV_FILE="$PROJECT_ROOT/.env.dev.example"
if [ -f "$ENV_FILE" ]; then
  for KEY in LLM_PROVIDER OLLAMA_BASE_URL TRADINGAGENTS_QUICK_MODEL TRADINGAGENTS_DEEP_MODEL \
             FINNHUB_API_KEY EODHD_API_KEY REDDIT_CLIENT_ID REDDIT_CLIENT_SECRET REDDIT_USER_AGENT \
             ALPACA_API_KEY ALPACA_SECRET_KEY ALPACA_BASE_URL \
             OPENAI_API_KEY ANTHROPIC_API_KEY GOOGLE_API_KEY DEEPSEEK_API_KEY OPENROUTER_API_KEY \
             MAX_POSITION_PCT STOP_LOSS_PCT DAILY_API_SPEND_CAP_USD; do
    if grep -q "^${KEY}" "$ENV_FILE"; then
      pass ".env.dev.example contains $KEY"
    else
      fail ".env.dev.example missing $KEY"
    fi
  done
fi

# -----------------------------------------------------------------------------
# AC: start.sh --dry-run exits 0 without starting processes
# -----------------------------------------------------------------------------
echo ""
echo "--- start.sh --dry-run ---"
OLLAMA_BEFORE=$(pgrep -x ollama 2>/dev/null | wc -l)
OLLAMA_BEFORE=$(pgrep -x ollama 2>/dev/null | wc -l)
DRY_RUN_EXIT=0
bash "$PROJECT_ROOT/start.sh" --dry-run 2>&1 || DRY_RUN_EXIT=$?
if [ "$DRY_RUN_EXIT" -eq 0 ]; then
  pass "start.sh --dry-run exited 0"
else
  fail "start.sh --dry-run exited $DRY_RUN_EXIT (non-zero)"
fi
OLLAMA_AFTER=$(pgrep -x ollama 2>/dev/null | wc -l)
if [ "$OLLAMA_AFTER" -eq "$OLLAMA_BEFORE" ]; then
  pass "--dry-run did not start new ollama process"
else
  fail "--dry-run started an ollama process (should not)"
fi

# -----------------------------------------------------------------------------
# AC: start.sh contains CISO trust comment for uv installer
# -----------------------------------------------------------------------------
echo ""
echo "--- Security & Board Conditions ---"
if grep -qi "trust\|astral\|ciso\|curl.*sh\|version.*drift\|SECURITY" "$PROJECT_ROOT/start.sh" 2>/dev/null; then
  pass "start.sh contains uv installer trust documentation"
else
  fail "start.sh missing CISO-required uv installer trust comment"
fi

# AC: start.sh has stale PID detection (Red Team condition)
if grep -qi "stale\|dead.*pid\|pid.*dead\|kill.*0\|process.*running\|check.*pid" "$PROJECT_ROOT/start.sh" 2>/dev/null; then
  pass "start.sh contains stale PID detection logic"
else
  fail "start.sh missing Red Team-required stale PID detection"
fi

# AC: VRAM guard present
if grep -qi "vram\|nvidia-smi\|memory\|600\|300" "$PROJECT_ROOT/start.sh" 2>/dev/null; then
  pass "start.sh contains VRAM guard logic"
else
  fail "start.sh missing VRAM guard"
fi

# -----------------------------------------------------------------------------
# AC: start.sh never touches system python
# -----------------------------------------------------------------------------
echo ""
echo "--- Anti-Criteria ---"
if grep -q "/usr/bin/python" "$PROJECT_ROOT/start.sh" 2>/dev/null; then
  fail "start.sh references /usr/bin/python (must never mutate system python)"
else
  pass "start.sh does not reference system python path"
fi

if grep -q "pip install\|pip3 install" "$PROJECT_ROOT/start.sh" 2>/dev/null; then
  fail "start.sh uses pip install (must use uv sync only)"
else
  pass "start.sh does not use bare pip install"
fi

# AC: cost profiler does not make paid API calls
# Only flag actual API call patterns — not comments referencing pricing docs
if grep -vE "^#|^[[:space:]]*#" "$PROJECT_ROOT/cost-profiler.sh" 2>/dev/null | \
   grep -qE "api\.openai\.com|api\.anthropic\.com|OPENAI_API_KEY|requests\.post.*openai|curl.*api\.openai"; then
  fail "cost-profiler.sh appears to call a paid API endpoint"
else
  pass "cost-profiler.sh contains no paid API calls"
fi

# AC: README-HEDGEFUND.md exists with master plan
echo ""
echo "--- Documentation ---"
if grep -q "Phase 1" "$PROJECT_ROOT/README-HEDGEFUND.md" 2>/dev/null && \
   grep -q "Phase 5" "$PROJECT_ROOT/README-HEDGEFUND.md" 2>/dev/null && \
   grep -q "Financial Milestone" "$PROJECT_ROOT/README-HEDGEFUND.md" 2>/dev/null; then
  pass "README-HEDGEFUND.md contains 5-phase master plan"
else
  fail "README-HEDGEFUND.md missing or incomplete"
fi

# -----------------------------------------------------------------------------
# VERDICT
# -----------------------------------------------------------------------------
echo ""
echo "============================================="
TOTAL=$((PASS + FAIL))
echo "  TOTAL: $TOTAL | ✅ PASSED: $PASS | ❌ FAILED: $FAIL"
echo "============================================="

if [ "$FAIL" -gt 0 ]; then
  echo -e "  ${RED}❌ SMOKE TESTS FAILED — $FAIL checks failed${NC}"
  echo "  Phase 2 baseline established. Implement Phase 3 to achieve green run."
  exit 1
else
  echo -e "  ${GREEN}✅ ALL SMOKE TESTS PASSED${NC}"
  exit 0
fi
