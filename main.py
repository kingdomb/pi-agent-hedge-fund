import os
import time
from typing import Any, Dict, List
from langchain_core.callbacks import BaseCallbackHandler
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# Progress display — prints agent phase banners as each node runs
# @REQ-HF-01
# =============================================================================

# Human-readable names for LangGraph node IDs
_NODE_LABELS = {
    "market_analyst":         "📊  Market Analyst          — reading price & technical data",
    "social_analyst":         "💬  Social Analyst          — scanning sentiment signals",
    "news_analyst":           "📰  News Analyst            — processing recent headlines",
    "fundamentals_analyst":   "📋  Fundamentals Analyst    — reviewing financials",
    "bull_researcher":        "🐂  Bull Researcher         — building the BUY case",
    "bear_researcher":        "🐻  Bear Researcher         — building the SELL case",
    "research_manager":       "⚖️   Research Manager        — judging the debate",
    "trader":                 "💼  Trader                  — drafting investment plan",
    "aggressive_risk":        "🔥  Risk: Aggressive        — push harder?",
    "conservative_risk":      "🛡️   Risk: Conservative      — pull back?",
    "neutral_risk":           "⚖️   Risk: Neutral           — balanced view",
    "risk_manager":           "🧮  Risk Manager            — final risk ruling",
    "portfolio_manager":      "🏦  Portfolio Manager       — final trade decision",
}

_CYAN  = "\033[0;36m"
_GREEN = "\033[0;32m"
_BOLD  = "\033[1m"
_NC    = "\033[0m"


class ProgressCallback(BaseCallbackHandler):
    """Prints a progress banner when each LangGraph agent node starts."""

    def __init__(self):
        super().__init__()
        self._start_times: Dict[str, float] = {}
        self._run_start = time.time()
        self._step = 0

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Any, **kwargs) -> None:
        run_id = str(kwargs.get("run_id", ""))
        name = (serialized or {}).get("name", "")
        node = name.lower().replace(" ", "_")
        label = _NODE_LABELS.get(node, f"🔄  {name}")
        self._start_times[run_id] = time.time()
        self._step += 1
        elapsed = time.time() - self._run_start
        print(
            f"\n{_BOLD}{_CYAN}[{self._step:02d}] {label}{_NC}"
            f"  {_CYAN}(+{elapsed:.0f}s){_NC}",
            flush=True,
        )

    def on_chain_end(self, outputs: Any, **kwargs) -> None:
        run_id = str(kwargs.get("run_id", ""))
        if run_id in self._start_times:
            took = time.time() - self._start_times.pop(run_id)
            print(f"    {_GREEN}✓ done ({took:.1f}s){_NC}", flush=True)


# =============================================================================
# Phase 1 config — Zero-Cost Local Loop via Ollama
# @REQ-HF-01
# =============================================================================
config = DEFAULT_CONFIG.copy()

# Route ALL inference to local Ollama — no paid API calls
config["llm_provider"] = os.getenv("LLM_PROVIDER", "ollama")
config["backend_url"]  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
config["deep_think_llm"]  = os.getenv("TRADINGAGENTS_DEEP_MODEL",  "qwen3:8b")
config["quick_think_llm"] = os.getenv("TRADINGAGENTS_QUICK_MODEL", "qwen3:8b")

# Keep debate rounds minimal for Phase 1 baseline runs
config["max_debate_rounds"]      = 1
config["max_risk_discuss_rounds"] = 1

# All data via yfinance — no API keys required
config["data_vendors"] = {
    "core_stock_apis":       "yfinance",
    "technical_indicators":  "yfinance",
    "fundamental_data":      "yfinance",
    "news_data":             "yfinance",
}

# Initialize graph with progress callback
progress = ProgressCallback()
ta = TradingAgentsGraph(debug=True, config=config, callbacks=[progress])

# Phase 1 Financial Milestone Gate:
# Run a single decision loop for NVDA on 2024-05-10 using only local compute.
# Expected output: valid Pydantic JSON trade recommendation (BUY/SELL/HOLD).
print(f"\n{_BOLD}{'═'*55}{_NC}")
print(f"{_BOLD}  🚀 Starting Phase 1 Milestone Run: NVDA / 2024-05-10{_NC}")
print(f"{_BOLD}  Model: {config['deep_think_llm']} via {config['llm_provider']}{_NC}")
print(f"{_BOLD}{'═'*55}{_NC}\n")

run_start = time.time()
_, decision = ta.propagate("NVDA", "2024-05-10")

total = time.time() - run_start
print(f"\n{_BOLD}{_GREEN}{'═'*55}{_NC}")
print(f"{_BOLD}{_GREEN}  ✅ MILESTONE COMPLETE — {total:.0f}s total{_NC}")
print(f"{_BOLD}{_GREEN}{'═'*55}{_NC}\n")
print(decision)

# Memorize mistakes and reflect (enable in Phase 2+)
# ta.reflect_and_remember(1000)

