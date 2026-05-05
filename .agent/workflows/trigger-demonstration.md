---
description: Trigger Demonstration & Delivery Surface Verification gate for implement-req. Proves the implemented feature has a usable trigger (API/CLI/UI). Used by implement-req Step 4.6.
---

# Trigger Demonstration & Delivery Surface Verification

> [!CAUTION]
> **HARD GATE**: Code that cannot be executed by a human user or an upstream client is dead code. You MUST prove the Integration / Delivery Surface is functional.

---

## Purpose

This gate forces the implementing agent to prove that the newly implemented feature can actually be **triggered by a real user or client**. A backend engine with no API route, CLI command, or UI integration is orphaned code — functionally incomplete regardless of test coverage.

---

## Step 1: Demonstrate the Trigger (MANDATORY)

**Actions:**
1. Identify the **delivery surface** for this REQ:
   - **API route** → Provide the exact `curl` command
   - **CLI command** → Provide the exact shell command
   - **UI interaction** → Open browser to the page via `browser_subagent`. ⛔ If auth is required, HALT for user authentication (see `.agent/workflows/frontend-browser-gate.md` Auth Handoff Protocol). Describe the exact click path (page → button → result).
   - **Agent integration** → Show the orchestrator/agent can invoke it
   - **Event-driven** → Show the event producer and how to trigger it

2. **Execute the trigger** and show the output:
   - For API: Run the `curl` command and show the response
   - For CLI: Run the command and show the output
   - For UI: Describe what the user sees after the interaction
   - For events: Show the event being published and consumed

---

## Step 2: Verify Against Phase 1 Scope Sanity Check (MANDATORY)

**Actions:**
1. Re-read the Phase 1 Scope Sanity Check output (from `.agent/workflows/scope-sanity-check.md`)
2. Did the scope check flag **API**, **CLI**, or **UI** as a delivery surface for this REQ?
3. For each flagged surface: **demonstrate it now**
4. For each surface flagged YES but not implemented: this is a gap — record it

---

## Step 3: Run Validation Script (BLOCKING)

```bash
bash scripts/validate-trigger-demonstration.sh {REQ-ID}
```

> [!CAUTION]
> **HARD GATE**: This script validates that `TRIGGER_DEMONSTRATION.md` exists in the checkpoint directory with all required sections. If it fails → ⛔ BLOCKED.

---

## Step 4: Generate Trigger Report

Create the file `.agent/checkpoints/{REQ-ID}/TRIGGER_DEMONSTRATION.md` using this format:

```markdown
# Trigger Demonstration: {REQ-ID}
**Generated:** {DATE}

## Delivery Surfaces

| Surface | Required? | Implemented? | Trigger Command/Path |
|---------|-----------|--------------|---------------------|
| API     | YES/NO    | YES/NO       | `curl ...` or N/A   |
| CLI     | YES/NO    | YES/NO       | `command ...` or N/A|
| UI      | YES/NO    | YES/NO       | Page → Button → ... |
| Event   | YES/NO    | YES/NO       | Event name or N/A   |

## Trigger Output
[Paste the actual output from executing the trigger]

## Verdict
- **Has usable trigger:** [YES/NO]
- **Orphaned code:** [YES/NO]
- **Missing surfaces:** [list or NONE]
```

---

## Step 5: Halt Condition (BLOCKING)

> [!CAUTION]
> If the feature has **NO delivery surface** (all surfaces show "Implemented: NO"), the feature is **ORPHANED**.

⛔ BLOCKED: You MUST halt and inform the user:

> "This feature has no delivery surface. Should I implement the API/CLI route now, or is this expected?"

**User responses:**
- **"Implement it"** → Build the missing surface before proceeding to Phase 4 checkpoint
- **"Expected"** → Document the reason in the trigger report and proceed
- **"Abort"** → Stop implementation

---

## Violation Handling

| Violation | Response |
|-----------|----------|
| No `TRIGGER_DEMONSTRATION.md` | ⛔ BLOCKED — create it |
| No trigger executed | ⛔ BLOCKED — demonstrate the trigger |
| Orphaned code not disclosed | ⛔ BLOCKED — halt for user |
| Validation script fails | ⛔ BLOCKED — fix report and re-run |
