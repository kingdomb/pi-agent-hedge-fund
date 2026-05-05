---
description: Scope Escalation Protocol. Reference file for agents when a Delivery Surface gap or Scope Sanity Check failure triggers a halt. Defines the user's options and the agent's required output format.
---

# Scope Escalation Protocol

> This file is referenced by `/create-req` (Step 1.3) and `/implement-req` (Step 1.6) when a scope gap is detected.

---

## When This Protocol Is Triggered

An agent has determined that the requirement spec is **incomplete** in one or more of:

- **Missing Delivery Surface**: Feature should be available via UI/API/CLI but the spec only covers one.
- **Missing User Context**: Feature behaves differently for Org-0 (Superadmin) vs. Tenant but the spec only covers one.
- **Missing Pattern Reference**: A similar pattern exists in the codebase but the spec doesn't reference or extend it.
- **Adjacent Requirement Detected**: The feature creates a need for a separate capability not covered by the current REQ.

---

## Agent Halt Output Format

When halting, the agent MUST output the following structured notice:

```markdown
## ⛔ SCOPE ESCALATION — {REQ-ID}

**Gap Type:** [Missing Delivery Surface | Missing User Context | Missing Pattern | Adjacent Requirement]
**Description:** [What is missing and why it matters]
**Impact if ignored:** [What breaks, what gets skipped, what users can't do]

**📄 Resolution options: See `.agent/workflows/scope-escalation-protocol.md`**
```

---

## Resolution Options

The **user** selects one of the following:

### Option A: Expand the Current REQ

**When to choose**: The missing piece is inherently part of the same feature (e.g., "create agents" needs a UI — it's the same capability, different surface).

**Action**: The agent (or PM) updates `docs/requirements/{REQ-ID}.md` to include the missing surface, context, or pattern. The user story and acceptance criteria in `docs/requirements/REQ-USER-STORIES.md` are updated to match.

**Resume**: The workflow continues from the same step after the spec is updated.

### Option B: Create a Separate REQ

**When to choose**: The missing piece is a distinct capability that the current REQ exposed (e.g., "agent creation" reveals a need for an "agent template marketplace").

**Action**:
1. Document the dependency in the current REQ's spec: `**Dependencies:** REQ-XX-YY (pending — [brief description])`
2. The current workflow continues with the scope it has.
3. The user invokes `/create-req` separately for the new requirement after this one completes.

**Resume**: The current workflow continues immediately. The new REQ is handled independently.

### Option C: Sovereign Override

**When to choose**: The user determines the flagged gap is intentionally out of scope (e.g., "Tenant differentiation is not needed for this admin-only feature").

**Action**: The agent documents the override in the current REQ's spec:
```markdown
**Sovereign Override:** [Gap description] — Intentionally excluded per user decision on [date].
```

**Resume**: The workflow continues immediately. The override is recorded for audit trail.

---

## Post-Resolution

After the user selects an option:

| Option | Agent Action |
|--------|-------------|
| **A (Expand)** | Update spec file → re-read spec → resume from the halted step |
| **B (New REQ)** | Add dependency note to current spec → resume from the halted step |
| **C (Override)** | Add override note to current spec → resume from the halted step |

> **Rule**: The agent MUST NOT resume without an explicit user selection. Silent continuation is a workflow violation.
