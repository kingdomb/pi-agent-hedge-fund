# Upstream Issue Triage — TauricResearch/TradingAgents

> Triaged against the Pi Agent Hedge Fund 5-phase roadmap.
> Source: https://github.com/TauricResearch/TradingAgents/issues
> Last reviewed: 2026-05-05

---

## 🔴 HIGH PRIORITY — Adopt now or before Phase 2

| Issue | Title | Why it matters |
|-------|-------|----------------|
| [#726](https://github.com/TauricResearch/TradingAgents/issues/726) | `load_dotenv()` doesn't find `.env` when launched via console script | Affects `cli.main run` — our primary entry point going forward |
| [#719](https://github.com/TauricResearch/TradingAgents/issues/719) | Reports are not being written to disk | `save_report_to_disk()` silently fails — we need reports saved for backtesting in Phase 3 |
| [#678](https://github.com/TauricResearch/TradingAgents/issues/678) | AI Manager structured-output invocation failed | Fund Manager output schema bug — directly related to GAP-HF-12 (TradeOrder schema) |
| [#664](https://github.com/TauricResearch/TradingAgents/issues/664) | Connection failed error when trying to use local Ollama | Same class of bug we hit — may contain fix we haven't applied |
| [#655](https://github.com/TauricResearch/TradingAgents/issues/655) | Crashes with no OpenAI key when using OpenRouter | Same root cause as our missing-api-key bug — fix applies to Ollama path too |
| [#641](https://github.com/TauricResearch/TradingAgents/issues/641) | `GOOGLE_API_KEY` is not being used | Signals provider routing bugs exist across all non-OpenAI providers |

---

## 🟡 MEDIUM PRIORITY — Adopt at Phase 2 or 3

| Issue | Title | Phase |
|-------|-------|-------|
| [#725](https://github.com/TauricResearch/TradingAgents/issues/725) | User investment context prompt (philosophy, existing position, portfolio weight) | Phase 3+ — feeds better Fund Manager decisions |
| [#718](https://github.com/TauricResearch/TradingAgents/issues/718) | Weight reflection updates by surprise_ratio to avoid over-learning from lucky wins | Phase 3 — backtesting / memory learning loop |
| [#628](https://github.com/TauricResearch/TradingAgents/issues/628) | Benchmark hardcoded to SPY — breaks reflection alpha for non-US tickers | Phase 3 — Sharpe vs SPY gate |
| [#562](https://github.com/TauricResearch/TradingAgents/issues/562) | News lookback window and article count are hardcoded | Phase 2 — configurable data vendors |
| [#561](https://github.com/TauricResearch/TradingAgents/issues/561) | Add earnings calendar awareness (next earnings date, EPS consensus, surprise history) | Phase 2/3 — major alpha signal |
| [#560](https://github.com/TauricResearch/TradingAgents/issues/560) | Add short interest data tool (% float short, days to cover) | Phase 2/3 — feeds Bear Researcher |
| [#559](https://github.com/TauricResearch/TradingAgents/issues/559) | Add options market data tool (IV, put/call ratio) | Phase 2/3 — volatility signal for Risk Manager |
| [#558](https://github.com/TauricResearch/TradingAgents/issues/558) | Global news uses 4 hardcoded search queries — make configurable | Phase 2 — improve news quality |
| [#557](https://github.com/TauricResearch/TradingAgents/issues/557) | Social Media Analyst reads Yahoo News, not social media — rename or fix | Phase 2 — data accuracy (confirmed in our Phase 1 run) |
| [#665](https://github.com/TauricResearch/TradingAgents/issues/665) | Add investment horizon config (long-term vs short-term analysis) | Phase 3 — affects hold_days in TradeOrder |
| [#699](https://github.com/TauricResearch/TradingAgents/issues/699) | Add SearXNG as self-hosted news/sentiment search vendor | Phase 2 — zero-cost news pipeline |

---

## 🟢 LOW PRIORITY / INFORMATIONAL — Monitor only

| Issue | Title | Notes |
|-------|-------|-------|
| [#710](https://github.com/TauricResearch/TradingAgents/issues/710) | Add openai-completions for LM-Studio, Llama.cpp | Same pattern as Ollama — we already solved this |
| [#651](https://github.com/TauricResearch/TradingAgents/issues/651) | DeepSeek latest models (V4 Flash / Pro) reasoning compat + CLI presets | Phase 5 model routing |
| [#556](https://github.com/TauricResearch/TradingAgents/issues/556) | Custom prompt as input | Phase 4+ — agent prompt tuning |
| [#555](https://github.com/TauricResearch/TradingAgents/issues/555) | YFRateLimitError — too many requests | Phase 2 concern when running batch backtests |
| [#627](https://github.com/TauricResearch/TradingAgents/issues/627) | PermissionError on cache dir | Docker deployment concern for Phase 5 |

---

## ❌ NOISE — Skip

Issues #712, #709, #707, #703, #696, #688, #681, #663, #642, #637, #623, #614 are spam, test posts, or completely unrelated.

---

## Strategy

**Don't blindly pull upstream.** The upstream project is moving fast with breaking changes to `langchain`/`langgraph` pins.
Instead:
1. **Cherry-pick** specific bug fixes by reading the issue + linked PR and applying the diff manually
2. **Watch** the HIGH PRIORITY issues for upstream PRs to merge
3. **Run** `git fetch upstream && git log upstream/main --oneline -20` periodically to see what changed
4. **Never** fast-forward merge upstream into `main` — always review diffs first via `upstream-sync` branch

> Next: Add `upstream` remote and set up the sync branch for periodic reviews.
