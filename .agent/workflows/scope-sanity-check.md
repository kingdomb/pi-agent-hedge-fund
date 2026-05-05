---
description: Scope Sanity Check gate for implement-req. Validates Delivery Surfaces, Tenant Isolation, Pattern Reuse, and Anti-Criteria. Enforces sub-REQ creation for missing surfaces.
---

# Scope Sanity Check (BLOCKING GATE)

> [!CAUTION]
> **HARD GATE**: This step defends against narrowly scoped specs. If any check fails, the implementation MUST halt.

## Checklist

**Verify the spec (`docs/requirements/{REQ-ID}.md`) covers:**

- [ ] **Delivery Surfaces**: Evaluate all 5 delivery surface perspectives (same matrix as `/create-req` Step 2.5b):
  - (1) Tenant Self-Service, (2) Org 0 Self-Management, (3) Org 0 → Global Policy, (4) Org 0 → Per-Tenant Override, (5) SDK Exposure.
  - If any = YES and no surface in spec or sub-REQ → **HALT**.
  - If spec has no `## Delivery Surfaces` section → **HALT** (backfill it first).
- [ ] **Tenant Isolation**: If tenant-scoped data, does it differentiate Org-0 vs Tenant behavior? If not → **HALT**.
- [ ] **Pattern Reuse**: Does similar pattern exist in codebase? If yes, does the spec reference it? If new pattern duplicates existing logic → **HALT**.
- [ ] **Anti-Acceptance Criteria**: Does the spec include "Must Never" constraints? If missing → **HALT**.

## Delivery Surface Re-Evaluation (BLOCKING)

> [!CAUTION]
> During implementation you are closer to reality than during `create-req`. You MUST re-evaluate:

1. **Re-run the matrix**: Does the feature need CLI, API, or UI surfaces the spec didn't identify?
2. **Check for existing sub-REQs**: If the spec has a `## Sub-Requirements` section, verify those sub-REQs exist in the Ledger.
3. **If a surface gap is found** (e.g., UI needed but no sub-REQ exists):
   - **HALT** the current implementation
   - **Present the gap** to the user using the Halt Output Format below
   - **Run `/create-req`** for the missing sub-REQ BEFORE resuming
   - The sub-REQ MUST be registered in the parent spec and wave-sequence

This is NOT optional. Implementation without its identified UI sub-REQ being **registered** is a scope gap.

## Violation Response

```
IF any check fails:
  → ⛔ HALT: Output Scope Escalation notice (format below)
  → Reference: .agent/workflows/scope-escalation-protocol.md
  → Wait for user to select resolution (Expand / New REQ / Override)
  → Resume ONLY after user responds

IF Delivery Surface gap found:
  → ⛔ HALT: "Surface gap: {surface} identified but no sub-REQ exists"
  → Run /create-req for the sub-REQ
  → Register in parent spec ## Sub-Requirements
  → Resume implementation after sub-REQ is committed
```

## Halt Output Format

```markdown
## ⛔ SCOPE ESCALATION — {REQ-ID}

**Gap Type:** [Missing Delivery Surface | Missing User Context | Missing Pattern | Missing Anti-Criteria]
**Description:** [What is missing and why it matters]
**Impact if ignored:** [What breaks, what gets skipped, what users can't do]

**📄 Resolution options: See `.agent/workflows/scope-escalation-protocol.md`**
```
