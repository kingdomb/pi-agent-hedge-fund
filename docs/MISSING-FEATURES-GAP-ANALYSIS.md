# Pi Agent Hedge Fund — Missing Features Gap Analysis

This file tracks identified gaps between the project vision and current implementation.

## Gap Registry

| Gap ID | Description | Status | Linked REQ |
|--------|-------------|--------|-----------|
| GAP-HF-01 | No lifecycle scripts (start/stop/profiler) | [x] Resolved → REQ-HF-01 | REQ-HF-01 |
| GAP-HF-02 | No environment key template for all phases | [x] Resolved → REQ-HF-01 | REQ-HF-01 |
| GAP-HF-03 | No master plan documentation | [x] Resolved → REQ-HF-01 | REQ-HF-01 |
| GAP-HF-04 | No broker integration (alpaca_executor.py) | [ ] Open | Pending Phase 4 |
| GAP-HF-05 | No batch backtester script | [ ] Open | Pending Phase 3 |
| GAP-HF-06 | No cloud API model routing configuration | [ ] Open | Pending Phase 2 |
| GAP-HF-07 | Fund Manager outputs no take-profit / target price — only stop loss mentioned in free text, no structured exit field | [ ] Open | Pending Phase 4 |
| GAP-HF-08 | No stop-loss hunting mitigation — current 5% fixed stop is predictable and huntable by market makers; needs ATR-based or support-level placement | [ ] Open | Pending Phase 4 |
| GAP-HF-09 | No intraday position monitoring — system is one-shot per day (cron); open positions are not tracked; no automatic sell at target; bracket orders (Alpaca OCO) not implemented | [ ] Open | Pending Phase 4 |
| GAP-HF-10 | Inference cost not factored into trade profitability — Cost Per Signal must be injected as a constraint into Fund Manager prompt so the agent only recommends trades where expected profit > (inference cost + slippage + broker fees) | [ ] Open | Pending Phase 2/3 |
| GAP-HF-11 | Fund Manager uses current market data for historical backtests — Phase 1 run used live fundamentals (2026 data) to evaluate a 2024-05-10 trade date, producing wrong price levels ($210 vs actual ~$88); historical data isolation needed for backtesting | [ ] Open | Pending Phase 3 |
| GAP-HF-12 | TradeOrder Pydantic schema is incomplete — Fund Manager should output structured fields: entry_price, target_price, stop_price, stop_type (fixed/trailing_atr/trailing_pct), position_size_pct, hold_days, exit_strategy, re_eval_trigger; currently outputs free text only | [ ] Open | Pending Phase 4 |

