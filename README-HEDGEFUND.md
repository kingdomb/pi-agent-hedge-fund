# Pi Agent Hedge Fund — Master Plan

> **The Comprehensive Master Plan: Zero to Autonomous Hedge Fund**

This document defines the overarching 5-phase roadmap for transforming the TradingAgents v0.2.4 framework into a fully autonomous, income-generating hedge fund system. Each phase has a concrete **Financial Milestone Gate** that must be passed before the next phase begins.

---

> [!WARNING]
> **RISK DISCLOSURE:** TradingAgents is a research framework, not financial advice.
> Algorithmic trading carries significant financial risk. Never risk capital you cannot
> afford to lose. NEVER go live until paper trading proves consistent, net-positive
> returns that mathematically outpace API overhead, slippage, and broker fees.

---

## Phase 1: Local Infrastructure & The "Zero-Cost" Loop

**Current Phase**

**Goal:** Prove the codebase works without spending a dime.

**Runtime Models:** `qwen3:8b` via Ollama (local GPU) for all nodes.

**REQ:** `REQ-HF-01`

**Actions:**
- Implement `start.sh` with Ollama server management, VRAM guard (5.7GB ceiling), and `uv` auto-install
- Implement `stop.sh` for graceful shutdown
- Implement `cost-profiler.sh` for baseline token/time profiling
- Create `.env.dev.example` with all key stubs

**Financial Milestone Gate:**
> You can type `./start.sh`, pass in ticker `AAPL` for a historical date, and the terminal outputs a fully populated Pydantic JSON trade recommendation using your local GPU — with **zero errors and zero API costs**.

---

## Phase 2: Cloud API Integration & Cost Profiling

**Goal:** Introduce smarter API models and determine your baseline operating cost.

**Runtime Models:**
- Analysts: `Gemini 3 Flash` (fast, large context, low cost)
- Debaters: `Gemini 3.1 Pro (Low)` or `Claude Sonnet 4.6`

**REQ:** `REQ-HF-02` *(create after Phase 1 gate passes)*

**Actions:**
- Plug in real API keys: Finnhub, EODHD, Reddit, Alpaca Paper
- Wire Gemini Flash to Analyst nodes in `default_config.py`
- Run `cost-profiler.sh` across 10 diverse tickers
- Calculate **Cost Per Signal** baseline

**Financial Milestone Gate:**
> Calculate your Cost Per Signal. If one trade signal costs $0.15 and the system trades 20 times/day, overhead is $3/day. Your account size and position sizing must mathematically guarantee that the average winning trade covers this cost PLUS slippage and broker fees.

---

## Phase 3: Rigorous Historical Backtesting

**Goal:** Prove the AI generates Alpha (returns better than holding SPY).

**Runtime Models:** Phase 2 models, or fast models on RunPod for volume.

**REQ:** `REQ-HF-03` *(create after Phase 2 gate passes)*

**Actions:**
- Write a batch backtester across 20 diverse stocks over 6 months
- Monitor the persistent decision log and memory learning loop
- Tune `max_debate_rounds` vs cost/accuracy tradeoff
- Measure Sharpe Ratio vs SPY benchmark

**Financial Milestone Gate:**
> Achieve **Sharpe Ratio > 1.0** and outpace the SPY baseline in backtesting.
> If it fails, tune prompts, debate rounds, and model routing. Do NOT proceed to Phase 4 on a failing backtest.

---

## Phase 4: Execution Bridging & Paper Live Market Simulation

**Goal:** Build the execution logic and test it against real-world market mechanics.

**REQ:** `REQ-HF-04` *(create after Phase 3 gate passes)*

**Actions:**
- Build `alpaca_executor.py` — intercepts Pydantic Fund Manager output, maps to Alpaca Paper orders
- Hardcode deterministic safety guardrails:
  - Rule 1: Never allocate > 10% of total capital to one asset
  - Rule 2: Hard 5% trailing stop-loss on all positions (bypasses AI entirely)
  - Rule 3: Daily API spend circuit breaker (halt if LLM bill > $X)
- Price sanity check: cancel order if AI-assumed price deviates > threshold from live price
- Set up cron job: runs 30 min before market open

**Financial Milestone Gate:**
> Run paper trading for **3–4 weeks**. Backtests are perfect; real markets are messy.
> This phase proves the AI's logic survives bid/ask spreads, order slippage, and real-time news shocks.

---

## Phase 5: Autonomous Hedge Fund Operations (Live Money)

**Goal:** Full automation and capital scaling to replace primary income.

**Runtime Models (Production Routing):**
- Analysts (data fetchers): `Gemini 3 Flash` or `DeepSeek`
- Debaters (Bull/Bear, Risk Team): `Claude Sonnet 4.6`
- Fund Manager (final decision): `Claude Opus 4.6 (Thinking)` — runs once per cycle

**REQ:** `REQ-HF-05` *(create after Phase 4 gate passes)*

**Actions:**
- Migrate infrastructure off local PC → RunPod or AWS (high availability)
- Swap Alpaca Paper API keys for Live keys
- Implement alerting: Discord/Slack webhooks for daily P&L reports
- Start with **$500 micro-account** — verify live market mechanics with minimal risk

**Financial Milestone Gate:**
> The system yields **consistent, mathematically proven, net-positive returns** over the micro-capital phase.
> Scale account size and position limits ONLY after this is proven.

---

## LLM Routing Summary (Reference)

| Phase | Analysts | Debaters | Fund Manager |
|---|---|---|---|
| **1 (Dev)** | qwen3:8b (local) | qwen3:8b (local) | qwen3:8b (local) |
| **2 (API)** | Gemini 3 Flash | Gemini 3.1 Pro Low | Gemini 3.1 Pro High |
| **3 (Backtest)** | Gemini Flash / RunPod | Same as Phase 2 | Same as Phase 2 |
| **4 (Paper)** | Gemini Flash | Claude Sonnet 4.6 | Claude Opus 4.6 |
| **5 (Live)** | Gemini Flash | Claude Sonnet 4.6 | Claude Opus 4.6 (Thinking) |

---

## Key Risk Controls (Non-Negotiable)

1. **Position Cap:** Never > 10% of account in one asset
2. **Stop-Loss:** Hard 5% trailing stop — bypasses AI entirely
3. **API Circuit Breaker:** Daily LLM spend cap — halts entire system if exceeded
4. **Price Sanity Check:** Cancel trade if AI price assumption deviates > X% from live price
5. **Paper First:** NEVER go live without ≥ 3 weeks of profitable paper trading
6. **PDT & Settlement Guard (Regulation):** Because the live account starts under $25,000, US regulations apply. If using a **Margin account**, `alpaca_executor.py` must track and strictly enforce the **Pattern Day Trader (PDT) rule** — maximum 3 day-trades per rolling 5 business days. If using a **Cash account**, the system must track **T+1 settlement** and never attempt to purchase using unsettled funds. Violating PDT results in a 90-day account restriction. This guard is non-negotiable and must be implemented before any live trading begins.
7. **Hardcoded Slippage in Backtesting:** In Phase 3, the batch backtester must artificially degrade the AI's execution price by a fixed slippage factor (default: **0.1%–0.5%** of trade value) on every simulated fill. The AI assumes it buys or sells at the exact historical close price — in reality, market orders fill worse. A backtest that ignores slippage will appear profitable but lose money live. This degradation must be a configurable constant, not optional.

---

*Master plan authored with Gemini 2.5 Pro and refined with Claude Sonnet 4.6 (Thinking).*
*Last updated: 2026-05-05*
