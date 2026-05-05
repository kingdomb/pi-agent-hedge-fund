#!/usr/bin/env bash
# =============================================================================
# stop.sh — Pi Agent Hedge Fund / Dev Loop Shutdown
# =============================================================================
# Gracefully shuts down the local development environment:
#   1. Reads .ollama.pid (if started by start.sh)
#   2. Terminates the recorded ollama process
#   3. Falls back to pkill if PID file is absent
#   4. Reports final status (clean or residual found)
#
# Usage: ./stop.sh
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

PID_FILE=".ollama.pid"

log()  { echo -e "${CYAN}[HF]${NC} $*"; }
ok()   { echo -e "${GREEN}[HF] ✅${NC} $*"; }
warn() { echo -e "${YELLOW}[HF] ⚠️ ${NC} $*"; }
err()  { echo -e "${RED}[HF] ❌${NC} $*"; }

echo ""
echo -e "${BOLD}${CYAN}═══════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}  🛑 Pi Agent Hedge Fund — Shutdown    ${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════${NC}"

STOPPED=false

# =============================================================================
# Step 1: Kill via PID file (clean path — started by start.sh)
# =============================================================================
if [ -f "$PID_FILE" ]; then
  STORED_PID=$(cat "$PID_FILE")
  if kill -0 "$STORED_PID" 2>/dev/null; then
    log "Stopping ollama serve (PID $STORED_PID)..."
    kill "$STORED_PID" 2>/dev/null || true
    # Wait up to 5 seconds for graceful exit
    for i in {1..5}; do
      if ! kill -0 "$STORED_PID" 2>/dev/null; then
        break
      fi
      sleep 1
    done
    # Force kill if still running
    if kill -0 "$STORED_PID" 2>/dev/null; then
      warn "Process did not exit gracefully — force killing..."
      kill -9 "$STORED_PID" 2>/dev/null || true
    fi
    ok "ollama serve stopped (PID $STORED_PID)"
    STOPPED=true
  else
    warn "PID file found but process $STORED_PID is already dead (stale file)"
  fi
  rm -f "$PID_FILE"
  log "PID file removed"
else
  log "No .ollama.pid file — may have been started externally"
fi

# =============================================================================
# Step 2: pkill fallback — catch any remaining ollama serve processes
# =============================================================================
if pgrep -f "ollama serve" &>/dev/null; then
  warn "Residual 'ollama serve' process(es) found — cleaning up..."
  pkill -f "ollama serve" 2>/dev/null || true
  sleep 1
  if pgrep -f "ollama serve" &>/dev/null; then
    warn "Still running after pkill — force killing..."
    pkill -9 -f "ollama serve" 2>/dev/null || true
  fi
  ok "Residual processes terminated"
  STOPPED=true
fi

# =============================================================================
# Step 3: Final status report
# =============================================================================
echo ""
if pgrep -x ollama &>/dev/null; then
  warn "Note: 'ollama' process (daemon) is still running — this is the system Ollama service."
  warn "If you want to stop it entirely: sudo systemctl stop ollama (or kill it manually)"
fi

if [ "$STOPPED" = true ]; then
  echo -e "${GREEN}${BOLD}✅ Shutdown complete. Environment is clean.${NC}"
else
  echo -e "${YELLOW}${BOLD}ℹ️  Nothing to stop — no start.sh-managed processes were running.${NC}"
fi
echo ""
