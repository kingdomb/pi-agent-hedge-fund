#!/usr/bin/env bash
# =============================================================================
# cost-profiler.sh — Pi Agent Hedge Fund / Phase 1 Cost Baseline
# =============================================================================
# Runs a single TradingAgents decision loop and reports:
#   - Wall-clock time
#   - Ollama token counts (input + output) from verbose logs
#   - GPT-4o equivalent cost estimate (for Phase 2 comparison baseline)
#
# NOTE: This script only calls local Ollama — NO paid API calls are made.
# It is safe to run as many times as needed. Cost is $0.
#
# Usage:
#   ./cost-profiler.sh                   — runs AAPL, 2024-01-15 (default)
#   ./cost-profiler.sh NVDA 2024-05-10   — custom ticker and date
#
# @REQ-HF-01
# =============================================================================

set -euo pipefail

# --- Color output ---
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

TICKER="${1:-AAPL}"
DATE="${2:-2024-01-15}"
OUTPUT_FILE="/tmp/profiler_${TICKER}_${DATE}.txt"
OLLAMA_LOG="/tmp/ollama-hedge-fund.log"

# GPT-4o pricing (as of 2025) — used ONLY for comparison baseline
# Source: https://openai.com/api/pricing
GPT4O_INPUT_PER_M=15.00   # USD per 1M input tokens
GPT4O_OUTPUT_PER_M=60.00  # USD per 1M output tokens

log()    { echo -e "${CYAN}[PROFILER]${NC} $*"; }
ok()     { echo -e "${GREEN}[PROFILER] ✅${NC} $*"; }
warn()   { echo -e "${YELLOW}[PROFILER] ⚠️ ${NC} $*"; }
err()    { echo -e "${RED}[PROFILER] ❌${NC} $*"; }

echo ""
echo -e "${BOLD}${CYAN}════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}  📊 Pi Agent Hedge Fund — Cost Profiler        ${NC}"
echo -e "${BOLD}${CYAN}════════════════════════════════════════════════${NC}"
echo -e "  Ticker: ${CYAN}${TICKER}${NC}   Date: ${CYAN}${DATE}${NC}"
echo -e "  Output: ${CYAN}${OUTPUT_FILE}${NC}"
echo ""

# =============================================================================
# Step 1: Verify Ollama is running
# =============================================================================
if ! pgrep -x ollama &>/dev/null && ! curl -s http://localhost:11434/api/tags &>/dev/null; then
  err "Ollama server is not running."
  err "Start it first: ./start.sh"
  exit 1
fi
ok "Ollama server is running"

# =============================================================================
# Step 2: Enable Ollama verbose logging for token count capture
# =============================================================================
log "Enabling OLLAMA_DEBUG for token tracking..."
export OLLAMA_DEBUG=1

# =============================================================================
# Step 3: Run the decision loop and time it
# =============================================================================
log "Running TradingAgents decision loop: $TICKER / $DATE"
log "This will take several minutes with qwen3:8b..."
echo ""

START_TIME=$(date +%s%N)

# Run main.py with the ticker and date — capture all output
uv run python main.py --ticker "$TICKER" --date "$DATE" 2>&1 | tee "$OUTPUT_FILE"

END_TIME=$(date +%s%N)
ELAPSED_MS=$(( (END_TIME - START_TIME) / 1000000 ))
ELAPSED_S=$(echo "scale=1; $ELAPSED_MS / 1000" | bc)

# =============================================================================
# Step 4: Parse token counts from Ollama logs
# =============================================================================
echo ""
log "Parsing token metrics..."

# Ollama outputs token stats in its verbose logs
# Pattern: "prompt eval count: N token(s)" and "eval count: N token(s)"
PROMPT_TOKENS=0
COMPLETION_TOKENS=0

if [ -f "$OLLAMA_LOG" ]; then
  PROMPT_TOKENS=$(grep -oP 'prompt eval count: \K[0-9]+' "$OLLAMA_LOG" 2>/dev/null | \
    awk '{s+=$1} END {print s+0}')
  COMPLETION_TOKENS=$(grep -oP 'eval count: \K[0-9]+' "$OLLAMA_LOG" 2>/dev/null | \
    grep -v "prompt" | awk '{s+=$1} END {print s+0}' || echo "0")
fi

# Fallback: try to parse from main output if Ollama log not available
if [ "$PROMPT_TOKENS" -eq 0 ]; then
  PROMPT_TOKENS=$(grep -oP 'input_tokens["\s:]+\K[0-9]+' "$OUTPUT_FILE" 2>/dev/null | \
    awk '{s+=$1} END {print s+0}' || echo "0")
  COMPLETION_TOKENS=$(grep -oP 'output_tokens["\s:]+\K[0-9]+' "$OUTPUT_FILE" 2>/dev/null | \
    awk '{s+=$1} END {print s+0}' || echo "0")
fi

TOTAL_TOKENS=$(( PROMPT_TOKENS + COMPLETION_TOKENS ))

# =============================================================================
# Step 5: Calculate GPT-4o equivalent cost (comparison only — actual cost: $0)
# =============================================================================
# Costs are in USD. bc handles floating point.
if [ "$TOTAL_TOKENS" -gt 0 ]; then
  GPT4O_COST=$(echo "scale=6; \
    ($PROMPT_TOKENS / 1000000 * $GPT4O_INPUT_PER_M) + \
    ($COMPLETION_TOKENS / 1000000 * $GPT4O_OUTPUT_PER_M)" | bc)
else
  GPT4O_COST="0.000000"
  warn "Could not parse token counts from logs — cost estimate will be $0.000000"
  warn "Enable OLLAMA_DEBUG=1 before running for accurate counts"
fi

# =============================================================================
# Step 6: Print report
# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║   📊 Cost Profiler Report                        ║${NC}"
echo -e "${BOLD}${GREEN}╠══════════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Ticker / Date:   ${CYAN}${TICKER} / ${DATE}${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Model:           ${CYAN}qwen3:8b (local Ollama)${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Wall-Clock Time: ${CYAN}${ELAPSED_S}s${NC}"
echo -e "${BOLD}${GREEN}╠══════════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Input Tokens:    ${CYAN}${PROMPT_TOKENS}${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Output Tokens:   ${CYAN}${COMPLETION_TOKENS}${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Total Tokens:    ${CYAN}${TOTAL_TOKENS}${NC}"
echo -e "${BOLD}${GREEN}╠══════════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Actual Cost:     ${GREEN}\$0.000000 (local GPU)${NC}"
echo -e "${BOLD}${GREEN}║${NC}  GPT-4o Equiv:    ${YELLOW}\$${GPT4O_COST} (comparison only)${NC}"
echo -e "${BOLD}${GREEN}╠══════════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Full output:     ${CYAN}${OUTPUT_FILE}${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Save this baseline before Phase 2 to compare paid API costs.${NC}"
echo ""
