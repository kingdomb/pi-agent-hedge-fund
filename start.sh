#!/usr/bin/env bash
# =============================================================================
# start.sh — Pi Agent Hedge Fund / Phase 1 Dev Loop Startup
# =============================================================================
# Manages the local development environment for TradingAgents:
#   1. Checks VRAM budget (GTX 1660 Ti, 5.7GB ceiling)
#   2. Installs uv if missing
#   3. Verifies Ollama is installed
#   4. Cleans stale PID files (Red Team condition)
#   5. Pulls qwen3:8b model if not cached
#   6. Starts ollama serve in the background
#   7. Runs uv sync to install Python deps
#   8. Prints a ready banner
#
# Usage:
#   ./start.sh              — full startup
#   ./start.sh --dry-run    — validate tooling without starting processes
#   ./start.sh --model <m>  — use a different Ollama model (VRAM check still runs)
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
DIM='\033[2m'
NC='\033[0m'

# --- Defaults ---
DRY_RUN=false
MODEL="qwen3:8b"
PID_FILE=".ollama.pid"
LOG_FILE="/tmp/ollama-hedge-fund.log"

# =============================================================================
# SECURITY NOTICE — uv installer trust decision (CISO condition)
# =============================================================================
# When uv is not found on PATH, this script installs it via the official
# Astral installer: curl -LsSf https://astral.sh/uv/install.sh | sh
#
# Trust justification:
#   - Source: astral.sh is Astral's own CDN (the company that makes uv)
#   - Protocol: HTTPS with TLS certificate validation (-L follows redirects
#     safely; -s and -S suppress progress but show errors; -f fails on HTTP
#     errors). This matches the documented install method in uv's official docs.
#   - Version drift risk: This always installs the LATEST uv release.
#     Breaking changes in uv are rare, but if uv sync fails after an upgrade,
#     pin a version by setting UV_VERSION below and using the versioned URL.
#
# To pin a specific version, set:
#   export UV_VERSION="0.6.14"
# and update the install command to use the versioned installer URL.
# =============================================================================
UV_VERSION="${UV_VERSION:-}"  # Leave empty for latest; set to pin (e.g. "0.6.14")

# =============================================================================
# Argument parsing
# =============================================================================
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)  DRY_RUN=true;  shift ;;
    --model)    MODEL="$2";    shift 2 ;;
    *)          echo -e "${RED}Unknown argument: $1${NC}" && exit 1 ;;
  esac
done

# =============================================================================
# Helpers
# =============================================================================
log()    { echo -e "${CYAN}[HF]${NC} $*"; }
ok()     { echo -e "${GREEN}[HF] ✅${NC} $*"; }
warn()   { echo -e "${YELLOW}[HF] ⚠️ ${NC} $*"; }
err()    { echo -e "${RED}[HF] ❌${NC} $*"; }
header() { echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════${NC}"; \
           echo -e "${BOLD}${CYAN}  $*${NC}"; \
           echo -e "${BOLD}${CYAN}═══════════════════════════════════════${NC}"; }

# =============================================================================
# Step 1: VRAM Check
# =============================================================================
header "VRAM Budget Check"
VRAM_FREE_MB=99999  # default if nvidia-smi unavailable (non-GPU CI)

if command -v nvidia-smi &>/dev/null; then
  VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | tr -d ' ')
  VRAM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | tr -d ' ')
  VRAM_FREE=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | tr -d ' ')
  VRAM_FREE_MB="${VRAM_FREE}"

  log "VRAM: ${VRAM_USED}MB used / ${VRAM_TOTAL}MB total / ${VRAM_FREE}MB free"

  if [ "${VRAM_FREE_MB}" -lt 300 ]; then
    err "VRAM critically low (${VRAM_FREE_MB}MB free < 300MB minimum)"
    err "Cannot safely load qwen3:8b. Free VRAM before starting."
    err "Try: close Chrome, other GPU apps, or kill other ollama instances."
    exit 1
  elif [ "${VRAM_FREE_MB}" -lt 600 ]; then
    warn "VRAM low (${VRAM_FREE_MB}MB free < 600MB recommended)"
    warn "qwen3:8b may cause OOM during inference if other processes spike VRAM."
    warn "Proceeding — monitor with: watch -n 1 nvidia-smi"
  else
    ok "VRAM OK — ${VRAM_FREE_MB}MB free (ceiling: 5734MB)"
  fi
else
  warn "nvidia-smi not found — skipping VRAM check (non-GPU environment or CI)"
fi

# =============================================================================
# Step 2: uv Check & Install
# =============================================================================
header "uv Package Manager"

if command -v uv &>/dev/null; then
  UV_PATH=$(command -v uv)
  ok "uv found at $UV_PATH ($(uv --version))"
else
  if [ "$DRY_RUN" = true ]; then
    warn "[dry-run] uv not found — would install via official Astral installer"
  else
    log "uv not found. Installing via official Astral installer (HTTPS, see SECURITY NOTICE in this file)..."
    if [ -n "${UV_VERSION}" ]; then
      log "Pinned version: UV_VERSION=${UV_VERSION}"
      curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh
    else
      warn "No UV_VERSION pinned — installing latest. Set UV_VERSION env var to pin."
      curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    # Source cargo env to pick up uv binary on this shell session
    # shellcheck source=/dev/null
    source "$HOME/.cargo/env" 2>/dev/null || true
    # Also try ~/.local/bin (uv may install there)
    export PATH="$HOME/.local/bin:$PATH"
    if command -v uv &>/dev/null; then
      ok "uv installed successfully: $(uv --version)"
    else
      err "uv install completed but binary not found on PATH."
      err "Try: source \$HOME/.cargo/env or restart your terminal, then re-run ./start.sh"
      exit 1
    fi
  fi
fi

# =============================================================================
# Step 3: Ollama Check
# =============================================================================
header "Ollama"

if ! command -v ollama &>/dev/null; then
  err "Ollama not found on PATH."
  err "Install it from: https://ollama.com/download"
  err "Then re-run: ./start.sh"
  exit 1
fi
ok "Ollama found: $(ollama --version 2>&1 | head -1)"

if [ "$DRY_RUN" = true ]; then
  ok "[dry-run] All tooling checks passed. No processes started."
  echo ""
  echo -e "${GREEN}${BOLD}✅ Dry-run complete.${NC}"
  exit 0
fi

# =============================================================================
# Step 4: Stale PID cleanup (Red Team condition)
# =============================================================================
# A stale PID file exists when: the file is present but the recorded process
# is no longer running (e.g. ollama crashed or was killed externally).
# We must detect and clean this before attempting to start a new instance.
# =============================================================================
header "PID File Cleanup"

if [ -f "$PID_FILE" ]; then
  STORED_PID=$(cat "$PID_FILE")
  if kill -0 "$STORED_PID" 2>/dev/null; then
    ok "Existing ollama serve running (PID $STORED_PID) — skipping new start"
    OLLAMA_ALREADY_RUNNING=true
  else
    warn "Stale PID file found (PID $STORED_PID is dead) — cleaning up"
    rm -f "$PID_FILE"
    OLLAMA_ALREADY_RUNNING=false
  fi
else
  OLLAMA_ALREADY_RUNNING=false
fi

# Also check if ollama is running system-wide (started externally, no PID file)
if [ "$OLLAMA_ALREADY_RUNNING" = false ] && pgrep -x ollama &>/dev/null; then
  warn "ollama is running (started externally, no PID file). Using existing instance."
  OLLAMA_ALREADY_RUNNING=true
fi

# =============================================================================
# Step 5: Start ollama serve
# =============================================================================
# Server must be running BEFORE we attempt ollama pull or ollama list.
# =============================================================================
header "Ollama Server"

if [ "$OLLAMA_ALREADY_RUNNING" = true ]; then
  ok "Using existing ollama server"
else
  log "Starting ollama serve in background..."
  log "Logs → $LOG_FILE"
  ollama serve &>"$LOG_FILE" &
  OLLAMA_PID=$!
  echo "$OLLAMA_PID" > "$PID_FILE"
  # Wait up to 10s for the server to be ready
  log "Waiting for ollama server to be ready..."
  for i in {1..10}; do
    if curl -sf http://localhost:11434/api/tags &>/dev/null; then
      ok "ollama serve ready (PID $OLLAMA_PID)"
      break
    fi
    sleep 1
    if [ "$i" -eq 10 ]; then
      err "ollama serve did not become ready in 10s. Check logs: cat $LOG_FILE"
      rm -f "$PID_FILE"
      exit 1
    fi
  done
fi

# =============================================================================
# Step 6: Model Pull
# =============================================================================
header "Model: $MODEL"

log "Checking if $MODEL is cached..."
if ollama list 2>/dev/null | grep -q "$MODEL"; then
  ok "$MODEL already cached — no download needed"
else
  log "Pulling $MODEL (this may take several minutes on first run)..."
  log "Size: qwen3:8b at Q4_K_M ≈ 5.2GB download"
  ollama pull "$MODEL"
  ok "$MODEL pull complete"
fi

# =============================================================================
# Step 7: Python Environment (uv sync)
# =============================================================================
header "Python Environment"

log "Running: uv sync"
uv sync
UV_ENV_PATH=$(uv run python -c "import sys; print(sys.executable)" 2>/dev/null || echo "unknown")
ok "Python environment ready"

# =============================================================================
# Ready Banner
# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║   🚀 Pi Agent Hedge Fund — DEV READY         ║${NC}"
echo -e "${BOLD}${GREEN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Model:   ${CYAN}${MODEL}${NC}"
echo -e "${BOLD}${GREEN}║${NC}  VRAM:    ${CYAN}${VRAM_USED:-?}MB used / ${VRAM_TOTAL:-?}MB total${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Python:  ${CYAN}${UV_ENV_PATH}${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Ollama:  ${CYAN}http://localhost:11434${NC}"
echo -e "${BOLD}${GREEN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Run:   ${CYAN}uv run python -m cli.main run${NC}  ${DIM}← interactive dashboard${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Test:  ${CYAN}uv run python main.py${NC}          ${DIM}← milestone smoke test${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Stop:  ${CYAN}./stop.sh${NC}"
echo -e "${BOLD}${GREEN}║${NC}  Cost:  ${CYAN}./cost-profiler.sh${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
