# Requirement: REQ-HF-01

## Metadata
- **ID:** REQ-HF-01
- **Name:** Local Infrastructure & Zero-Cost Dev Loop
- **Status:** DRAFT
- **Priority:** MUST
- **Effort:** M
- **Layer:** HF-1 (Hedge Fund Phase 1 — Local Infrastructure)
- **Owner:** devops-engineer
- **GitHub Issue:** N/A — GitHub Issues disabled on fork (kingdomb/pi-agent-hedge-fund). Tracked via spec file.
- **Cloud Blockers:** 🔨 BUILDABLE (no cloud dependencies)
- **Testability:** [INFRA] — smoke-tested via `./start.sh --dry-run`

## Description

Establishes the developer lifecycle protocol for the TradingAgents framework. Provides a single-command startup experience (`./start.sh`) that manages the local Ollama model server, enforces VRAM safety constraints (5.7GB ceiling for GTX 1660 Ti), auto-installs `uv` if missing, and validates the Python environment. A companion `./stop.sh` cleans up background processes. A `cost-profiler.sh` script runs a single decision loop and reports time/token metrics to baseline future API costs. A `.env.dev.example` stubs all required API keys across all 5 phases.

This is the **Phase 1 Financial Milestone Gate**: the system must output a valid Pydantic JSON trade recommendation for a historical date using only local compute, with zero API costs.

## User Stories

- **As a** developer running the hedge fund system locally
- **I want to** type `./start.sh` and have the environment fully ready with a local LLM loaded
- **So that** I can iterate on the framework without paying API costs and without manually managing background processes

## Acceptance Criteria

- [ ] `./start.sh` detects whether Ollama is installed; if not, prints install instructions and exits cleanly
- [ ] `./start.sh` installs `uv` automatically if not found on PATH, using the official installer
- [ ] `./start.sh` runs `nvidia-smi` and enforces the 5.7GB VRAM ceiling — warns and blocks if < 600MB free
- [ ] `./start.sh` pulls `qwen3:8b` via `ollama pull` if the model is not already cached
- [ ] `./start.sh` starts `ollama serve` in the background if not already running, saves PID
- [ ] `./start.sh` runs `uv sync` to install all Python dependencies from `pyproject.toml`
- [ ] `./start.sh` prints a ready banner showing: active model, VRAM used, uv env path
- [ ] `./start.sh --dry-run` completes without starting any processes (for CI/verification)
- [ ] `./stop.sh` terminates the Ollama server if it was started by `start.sh`, cleans PID file
- [ ] `./stop.sh` reports final status (clean or residual processes found)
- [ ] `cost-profiler.sh` runs a single `AAPL` decision loop and prints: wall-clock time, Ollama token count, "equivalent cost if using GPT-4o" estimate
- [ ] `.env.dev.example` contains stubs for ALL keys needed across all 5 phases: Ollama, Finnhub, EODHD, Reddit, Alpaca, OpenAI, Anthropic, Google, DeepSeek, OpenRouter
- [ ] `README-HEDGEFUND.md` contains the full 5-phase master plan with Financial Milestone Gates
- [ ] Running `uv run python main.py` after `./start.sh` produces a valid Pydantic JSON output for NVDA on 2024-05-10 using `qwen3:8b`
- [ ] No core business logic is stubbed or mocked — scripts wrap real `ollama` and `uv` CLI tools

## Anti-Acceptance Criteria (Must Never)

- [ ] The system MUST NEVER auto-load a model larger than 8B parameters without user confirmation (VRAM protection)
- [ ] The system MUST NEVER silently proceed if VRAM is critically low — it must warn and optionally block
- [ ] The system MUST NEVER modify system Python (`/usr/bin/python3`) or install packages system-wide
- [ ] `start.sh` MUST NEVER leave orphaned `ollama serve` processes if it fails mid-execution
- [ ] The cost profiler MUST NEVER make real API calls to paid endpoints — Ollama only

## Technical Implementation

**Schema:** N/A — no database

**API Endpoints:** N/A — CLI/shell only

**Components:**

### `start.sh`
```
1. Parse args: --dry-run, --model <name> (default: qwen3:8b)
2. Color output setup (GREEN/YELLOW/RED/NC)
3. VRAM check: nvidia-smi → warn if < 600MB free, block if < 300MB free
4. uv check: which uv || curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.cargo/env
5. Ollama check: which ollama || print install URL and exit 1
6. Model pull: ollama list | grep qwen3:8b || ollama pull qwen3:8b
7. Server start: pgrep -x ollama || (ollama serve &> /tmp/ollama.log & echo $! > .ollama.pid)
8. Deps install: uv sync
9. Ready banner: print model, VRAM, env path
10. --dry-run: skip steps 6-9, exit 0
```

### `stop.sh`
```
1. Read .ollama.pid if exists
2. Kill PID if running, remove .ollama.pid
3. pkill -f "ollama serve" as fallback
4. Report: clean or residual found
```

### `cost-profiler.sh`
```
1. Ensure Ollama running
2. time uv run python main.py 2>&1 | tee /tmp/profiler_output.txt
3. Parse token counts from Ollama verbose logs
4. Print: wall time, tokens, estimated cost at GPT-4o pricing ($15/1M input, $60/1M output)
```

### `.env.dev.example`
```
# === LOCAL DEV (Phase 1 — Zero Cost) ===
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
TRADINGAGENTS_QUICK_MODEL=qwen3:8b
TRADINGAGENTS_DEEP_MODEL=qwen3:8b

# === DATA APIs (Phase 2+) ===
FINNHUB_API_KEY=
EODHD_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=

# === BROKER (Phase 4+) ===
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# === REMOTE LLM APIs (Phase 2+) ===
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
DEEPSEEK_API_KEY=
OPENROUTER_API_KEY=

# === SAFETY CONTROLS (Phase 4+) ===
MAX_POSITION_PCT=0.10
STOP_LOSS_PCT=0.05
DAILY_API_SPEND_CAP_USD=10.00
```

## Delivery Surfaces (MANDATORY — Step 2.5b)

| # | Perspective | Applicable? | Justification |
|---|-------------|-------------|---------------|
| 1 | Tenant Self-Service | NO | Single-user local dev tool, no tenant model |
| 2 | Org 0 Self-Management | NO | Not a multi-org SaaS system |
| 3 | Org 0 → Global Policy | NO | No policy enforcement layer |
| 4 | Org 0 → Per-Tenant Override | NO | No tenant model |
| 5 | SDK Exposure | NO | CLI/shell scripts only |

Backend/CLI only — no user-facing web controls or SDK hooks required.

## Doc Update Manifest — REQ-HF-01

### Documents Requiring Updates
| Document | Action | Details |
|---|---|---|
| `docs/requirements/REQ-LEDGER.md` | CREATE + ADD ROW | Bootstrap ledger, add REQ-HF-01 row |
| `docs/requirements/REQ-USER-STORIES.md` | CREATE + ADD STORY | Bootstrap stories, add REQ-HF-01 |
| `docs/guides/GUIDE-EXECUTION-ORDER.md` | CREATE + ADD ENTRY | Bootstrap guide, Phase 1 entry |
| `docs/EXECUTION-PLAN.md` | CREATE + ADD | Bootstrap plan, Wave 1 entry |
| `README-HEDGEFUND.md` | CREATE | Master 5-phase hedge fund plan |
| `docs/DOCS_MAP.md` | CREATE | Track all project docs |

### Directories Evaluated — No Changes Required
| Directory | Reason |
|---|---|
| `docs/backend/` | No backend service logic added |
| `docs/security/` | No auth/RLS/PII changes — local only |
| `docs/operations/` | No cloud deployment yet |
| `docs/infrastructure/` | Local dev only — INFRA-ENV-MANIFEST not modified |
| `docs/technical_specs/` | No API contract changes |
| `README.md` | Upstream TradingAgents README — not modified |

## Sub-Requirements

None identified. Phase 2 (`REQ-HF-02`) will add cloud API integration and is gated behind Phase 1's Financial Milestone.

**Dependencies:** None (first REQ in this project)
**Source:** README-HEDGEFUND.md Phase 1, notes/Initial Chat.txt

## Board Conditions

Conditions required by APPROVE_WITH_CONDITIONS votes. Must be addressed in implementation.

### CISO Conditions
- [ ] The `start.sh` script MUST include a comment block documenting the `uv` installer trust decision (source: `astral.sh` official CDN, HTTPS). A pinned version flag (`UV_VERSION=x.y.z`) MUST be used if the installer supports it, or an inline comment documenting the version-drift risk.

### Red Team Conditions
- [ ] `start.sh` MUST detect a stale `.ollama.pid` file (PID exists in file but process is dead) and clean it up before attempting to start a new `ollama serve` instance.
- [ ] `uv` install in `start.sh` MUST use a pinned version or document the version-drift risk with a comment.
- [ ] VRAM mid-load spike risk is acknowledged as acceptable for local dev (Phase 1 only). The 600MB pre-check gate provides best-effort protection. This condition is waived for Phase 1 scope.
