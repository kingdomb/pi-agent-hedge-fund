# Pi Agent Hedge Fund — Execution Plan
**Version:** v1.0.0

---

## Step 1: Gap Identification

| Gap | Status | Linked REQ |
|-----|--------|-----------|
| No lifecycle scripts (start/stop/profiler) | [x] Identified → REQ-HF-01 |
| No env key template | [x] Identified → REQ-HF-01 |
| No master plan doc | [x] Identified → REQ-HF-01 |
| No broker integration (alpaca_executor.py) | [ ] Pending Phase 4 |
| No batch backtester | [ ] Pending Phase 3 |

---

## Step 2: Implementation Queue

### Wave 1 — Phase 1 (Local Dev)
- [x] `/implement-req REQ-HF-01` — Local Infrastructure & Zero-Cost Dev Loop *(smoke tests: 33/33 PASS)*

### Wave 2 — Phase 2 (Cloud APIs) *(locked — awaiting Phase 1 gate)*
- [ ] `/implement-req REQ-HF-02` — Cloud API Integration & Cost Profiling *(pending)*

### Wave 3 — Phase 3 (Backtesting) *(locked)*
- [ ] `/implement-req REQ-HF-03` — Historical Backtesting *(pending)*

### Wave 4 — Phase 4 (Execution Bridge) *(locked)*
- [ ] `/implement-req REQ-HF-04` — Execution Bridging & Paper Trading *(pending)*

### Wave 5 — Phase 5 (Live Operations) *(locked)*
- [ ] `/implement-req REQ-HF-05` — Autonomous Hedge Fund Operations *(pending)*
