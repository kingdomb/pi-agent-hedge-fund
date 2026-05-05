---
description: Spec Exhaustion & Residue Spawning gate for implement-req. Replaces blind spec deletion. Checks COMPLETENESS_DISCLOSURE, spawns follow-up REQs for gaps, then deletes spec. Used by implement-req Step 5.6.
---

# Spec Exhaustion & Residue Spawning

> [!CAUTION]
> **DO NOT blindly delete the spec file.** If the feature was only partially implemented or contains stubs, deleting the spec destroys the remaining requirements forever.

---

## Purpose

This gate replaces the old "delete spec file" step. It ensures that any unbuilt portions of a requirement spec are captured as follow-up REQs **before** the spec is deleted. This prevents the "ghost feature" problem where incomplete implementations lose their blueprint.

---

## Step 1: Read the Completeness Disclosure (MANDATORY)

**Actions:**
1. Open `.agent/checkpoints/{REQ-ID}/COMPLETENESS_DISCLOSURE.md` (generated in Step 3.5)
2. Identify all items classified as:
   - **⚠️ STUB/MOCK** — Code exists but is placeholder
   - **❌ NOT BUILT** — Spec item has no corresponding code
   - **Missing Delivery Surfaces** — Feature has no trigger
3. Count the total gaps: `STUB_COUNT + NOT_BUILT_COUNT + MISSING_SURFACES`

---

## Step 2: Decision Gate

### If gaps = 0 (100% complete)
- The spec is fully exhausted
- Proceed directly to Step 4 (delete spec)

### If gaps > 0 (partial implementation)
- You MUST proceed to Step 3 (spawn residue REQs)
- You may NOT skip to Step 4

---

## Step 3: Spawn Residue REQs (MANDATORY if gaps > 0)

For EACH gap identified in the disclosure:

**Actions:**
1. Create a follow-up REQ entry in `docs/requirements/REQ-LEDGER.md`:
   - Use the parent REQ-ID with a letter suffix (e.g., `REQ-L6-20a`, `REQ-L6-20b`)
   - Status: `✨ NEW` or `🔨 BUILDABLE`
   - Notes: Reference the parent REQ-ID

2. Create a matching entry in `docs/requirements/REQ-USER-STORIES.md`:
   - Use the same letter-suffixed ID
   - Include Acceptance Criteria extracted from the original spec
   - Include the **Completeness Definition** section
   - Include the stub prohibition clause

3. **MANDATORY: Register in `docs/EXECUTION-PLAN.md`:**
   - If the sub-REQ **needs a spec** (complex scope): add to **Step 1** under the appropriate category. Format: `- [ ] [Description] — Sub-REQ of [PARENT-ID] → /create-req **[SUB-REQ-ID]**`
   - If the sub-REQ **already has a spec**: add to **Step 2** under the appropriate wave. Format: `- [ ] /implement-req [SUB-REQ-ID] — [Description] — **sub-REQ of [PARENT-ID]**`

   > [!CAUTION]
   > **EXECUTION-PLAN.md is the user's primary tracking document.** If a sub-REQ exists in the Ledger but NOT in EXECUTION-PLAN.md, it is invisible to the user and effectively orphaned. This step is BLOCKING.

4. **Classify the required workflow** for each spawned sub-REQ:
   - **Complex scope** (new API endpoints, DB schema, multi-file UI): needs `/create-req` first, then `/implement-req`
   - **Simple scope** (single UI component, minor extension): can go directly to `/implement-req`
   - Record the classification in the disclosure file

5. Record spawned REQs in the disclosure file:
   ```markdown
   ## Spawned Follow-Up REQs
   - REQ-ID.a: [description] | Workflow: /create-req then /implement-req
   - REQ-ID.b: [description] | Workflow: /implement-req (simple scope)
   - EXECUTION-PLAN.md: Updated (Step 1 or Step 2)
   ```

---

## Step 4: Run Validation Script (BLOCKING)

```bash
bash scripts/validate-spec-exhaustion.sh {REQ-ID}
```

> [!CAUTION]
> **HARD GATE**: This script validates that either the disclosure shows 0 gaps, or follow-up REQs were spawned for all gaps. If it fails → ⛔ BLOCKED.

---

## Step 5: Delete Spec File (ONLY after validation passes)

```bash
rm docs/requirements/{REQ-ID}.md
git add docs/requirements/{REQ-ID}.md
```

> Spec file is now safe to delete because all unbuilt items have been captured as new REQs.

---

## Violation Handling

| Violation | Response |
|-----------|----------|
| Spec deleted before validation | ⛔ BLOCKED — restore with `git checkout HEAD -- docs/requirements/{REQ-ID}.md` |
| Gaps exist but no follow-up REQs spawned | ⛔ BLOCKED — create the REQs |
| Follow-up REQs spawned but NOT added to `EXECUTION-PLAN.md` | ⛔ BLOCKED — add entries to Step 1 or Step 2 |
| Follow-up REQs have no workflow classification | ⛔ BLOCKED — classify as `/create-req` or `/implement-req` |
| Validation script fails | ⛔ BLOCKED — fix and re-run |
| COMPLETENESS_DISCLOSURE.md missing | ⛔ BLOCKED — go back to Step 3.5 |
