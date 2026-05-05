# Pi Agent Hedge Fund — User Stories
**Version:** v1.0.0

---

## HF Layer — Hedge Fund Phases

### [✨ NEW] REQ-HF-01: Local Infrastructure & Zero-Cost Dev Loop
**Status:** 🔨 BUILDABLE

**As a** developer running the hedge fund system locally
**I want to** type `./start.sh` and have the environment fully ready with a local LLM loaded and VRAM-safe
**So that** I can iterate on the TradingAgents framework without paying API costs and without manually managing background processes

**Acceptance Criteria:**
- [ ] `./start.sh` detects Ollama; prints install instructions and exits if missing
- [ ] `./start.sh` auto-installs `uv` if not on PATH using the official installer
- [ ] `./start.sh` enforces 5.7GB VRAM ceiling — warns if < 600MB free, blocks if < 300MB free
- [ ] `./start.sh` pulls `qwen3:8b` if not cached; starts `ollama serve` background process
- [ ] `./start.sh` runs `uv sync` and prints a ready banner (model, VRAM, env path)
- [ ] `./start.sh --dry-run` exits cleanly without starting any processes
- [ ] `./stop.sh` terminates the Ollama server started by `start.sh` and cleans PID file
- [ ] `cost-profiler.sh` prints wall time, token count, and GPT-4o equivalent cost estimate
- [ ] `.env.dev.example` stubs all keys for all 5 phases (Ollama, Finnhub, EODHD, Reddit, Alpaca, LLM APIs)
- [ ] `README-HEDGEFUND.md` contains the full 5-phase master plan
- [ ] `uv run python main.py` produces valid Pydantic JSON for NVDA 2024-05-10 using `qwen3:8b`
- [ ] No core business logic may be stubbed or mocked in production execution

**Completeness Definition:**
The Phase 1 Financial Milestone Gate is met: `./start.sh` → `uv run python main.py` → valid Pydantic JSON trade recommendation for a historical date, using only local GPU compute, with zero API costs and zero errors.

**Anti-Acceptance Criteria (Must Never):**
- [ ] The system MUST NEVER auto-load a model larger than 8B parameters without user confirmation
- [ ] The system MUST NEVER silently proceed with critically low VRAM (< 300MB free)
- [ ] The system MUST NEVER install packages to system Python or modify `/usr/bin/python3`
- [ ] `start.sh` MUST NEVER leave orphaned `ollama serve` processes on failure
- [ ] The cost profiler MUST NEVER make real paid API calls

**Dependencies:** None
**Notes:** GTX 1660 Ti, 6GB VRAM. qwen3:8b at Q4_K_M ≈ 5.2GB — within 5.7GB ceiling.
