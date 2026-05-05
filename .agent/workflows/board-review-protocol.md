---
description: Board of Directors review protocol for create-req Phase 3. Records votes from all 5 board members and validates quorum. Used by create-req Phase 3.
---

# Board of Directors Review Protocol

## Voting Process

Record votes from ALL 5 board members. Each vote is MANDATORY.

### 1. CSA Architect Review
**Focus:** Schema impact, scalability, North Star alignment
**Decision:** APPROVE or REJECT
```bash
npm run checkpoint:board-vote -- --req {REQ-ID} --board-vote csa --decision {APPROVE|REJECT} --notes "reason"
```

### 2. CISO Security Review
**Focus:** Attack surface, RLS, PII handling
**Decision:** APPROVE, APPROVE_WITH_CONDITIONS, or REJECT
```bash
npm run checkpoint:board-vote -- --req {REQ-ID} --board-vote ciso --decision {APPROVE|REJECT} --notes "reason"
```

### 3. CAIO Technical Review
**Focus:** AI/Prompt impact, VRAM budget, code quality
**Decision:** APPROVE or REJECT
```bash
npm run checkpoint:board-vote -- --req {REQ-ID} --board-vote caio --decision {APPROVE|REJECT} --notes "reason"
```

### 4. VP Ops Review
**Focus:** Resilience (3 AM test), deployment, monitoring
**Decision:** APPROVE or REJECT
```bash
npm run checkpoint:board-vote -- --req {REQ-ID} --board-vote vp_ops --decision {APPROVE|REJECT} --notes "reason"
```

### 5. Red Team Adversarial Review
**Focus:** Destruction. Find the failure modes the other 4 missed.
**Default State:** REJECT. Must provide documented failure scenarios to approve.
**Input:** Read ONLY `docs/requirements/{REQ-ID}.md` — no other context.

**Required Output (all mandatory):**
- [ ] ≥3 failure scenarios (security exploit, scale failure, cost/logic exploit)
- [ ] STRIDE threat assessment (all 6 categories)
- [ ] ≥2 Anti-Acceptance Criteria ("The system MUST NEVER...")

**Decision:** APPROVE, APPROVE_WITH_CONDITIONS, or REJECT
```bash
npm run checkpoint:board-vote -- --req {REQ-ID} --board-vote red_team --decision {APPROVE|APPROVE_WITH_CONDITIONS|REJECT} --notes "conditions/reasons"
```

## Tally Votes — 3-Layer Governance (v2.0)

**Quorum requirement:** 75% effective approval (at least 4 of 5).

### Layer 1: Domain Veto (ABSOLUTE BLOCK)
If a board member with **domain authority** over the REQ prefix rejects, the REQ is **hard blocked**. No quorum or Sovereign Override can bypass this.

| Board Member | Domain Veto Prefixes |
|---|---|
| CISO | `REQ-SEC-*` |
| VP Ops | `REQ-INF-*`, `REQ-OPS-*`, `REQ-PROD-*`, `REQ-HW-*` |
| CAIO | `REQ-L5-*` |
| CSA | *(no prefix veto — holistic review)* |
| Red Team | *(no prefix veto — adversarial review)* |

**Resolution:** Address the expert's concerns, update the spec, and re-run the vote.

### Layer 2: Condition Enforcement (SPEC GATE)
`APPROVE_WITH_CONDITIONS` only counts toward quorum **if** the spec file (`docs/requirements/{REQ-ID}.md`) contains a section heading matching `## ... Conditions`.

If conditions are not documented in the spec, the conditional vote is treated as **PENDING** and does NOT count as an approval.

### Layer 3: Dissent Escalation (SOVEREIGN OVERRIDE)
Any `REJECT` from a non-domain member **blocks Phase 3 sign-off** until the user provides a **Sovereign Override**:

```bash
npm run checkpoint:sign-off -- --req {REQ-ID} --sign-off 3 --agent orchestrator --sovereign-override --notes "Acknowledged: [reason]"
```

The dissenting notes are displayed prominently. The user must explicitly acknowledge the risk.

## Phase 3 Checkpoint

```bash
# Standard (no dissent):
npm run checkpoint:sign-off -- --req {REQ-ID} --sign-off 3 --agent orchestrator

# With Sovereign Override (dissent acknowledged):
npm run checkpoint:sign-off -- --req {REQ-ID} --sign-off 3 --agent orchestrator --sovereign-override --notes "reason"
```
