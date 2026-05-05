---
description: Functional Completeness Disclosure gate for implement-req. Compares implementation against spec, generates disclosure report, and enforces HALT for user approval. Used by implement-req Step 3.5.
---

# Functional Completeness Disclosure Gate

> [!CAUTION]
> **AI AGENT MANDATE:** You must explicitly evaluate the real-world usefulness of what you just built. You are strictly forbidden from passing this phase silently if you took shortcuts.

---

## Purpose

This gate forces the implementing agent to compare the actual committed code against the original requirement spec and produce a transparent disclosure of what was fully built, what was stubbed, and what delivery surfaces are missing.

---

## Step 1: Compare Code Against Spec

**Actions:**
1. Read the requirement spec: `docs/requirements/{REQ-ID}.md`
2. For EACH item in the spec's **Technical Implementation** section, classify it:
   - **✅ FULLY BUILT** — Real logic, real data flow, integrated and callable
   - **⚠️ STUB/MOCK** — Class/function exists but contains placeholder logic, mock data, or `// TODO`
   - **❌ NOT BUILT** — Spec item has no corresponding code at all

3. For EACH acceptance criterion in `REQ-USER-STORIES.md`, verify:
   - Does the test actually exercise the behavior described, or just check `.toBeDefined()`?
   - Would a real user or upstream client see value from this criterion?

---

## Step 2: Generate Disclosure Report

Create the file `.agent/checkpoints/{REQ-ID}/COMPLETENESS_DISCLOSURE.md` using this format:

```markdown
# Completeness Disclosure: {REQ-ID}
**Generated:** {DATE}
**Agent:** {AGENT-NAME}

## Fully Built (✅)
- [Item]: [brief description of what works end-to-end]

## Stubbed / Mocked (⚠️)
- [Item]: [what exists vs. what is missing]

## Not Built (❌)
- [Item]: [spec reference, reason skipped]

## Missing Delivery Surfaces
- [ ] API route exists? [YES/NO — if NO, feature is orphaned]
- [ ] CLI command exists? [YES/NO — if applicable]
- [ ] UI integration exists? [YES/NO — if applicable]

## Verdict
- **Functional:** [YES / PARTIAL / NO]
- **Stub count:** [N items]
- **Orphaned code:** [YES/NO]
```

---

## Step 3: Run Validation Script (BLOCKING)

```bash
bash scripts/validate-completeness-disclosure.sh {REQ-ID}
```

> [!CAUTION]
> **HARD GATE**: This script validates that `COMPLETENESS_DISCLOSURE.md` exists, is non-empty, contains all required sections, and is not full of placeholders. If it fails → ⛔ BLOCKED.

---

## Step 4: HALT and Present to User (MANDATORY)

> [!CAUTION]
> **YOU MUST STOP HERE AND ASK THE USER.** Do NOT silently proceed.

Present the `COMPLETENESS_DISCLOSURE.md` content to the user via `notify_user` with this message:

> "I have identified the following functional gaps in {REQ-ID}. Should I continue developing them now to make this feature fully functional, or should we sign-off as a partial implementation and generate follow-up REQs?"

**User responses:**
- **"Continue"** → Implement the missing items before proceeding to Phase 3 checkpoint
- **"Sign-off as partial"** → Proceed, but Step 5.6 (Residue Spawning) will create follow-up REQs for the gaps
- **"Abort"** → Stop implementation entirely

---

## Violation Handling

| Violation | Response |
|-----------|----------|
| No `COMPLETENESS_DISCLOSURE.md` | ⛔ BLOCKED — create it |
| Disclosure has only "✅ FULLY BUILT" items but code contains stubs | ⛔ BLOCKED — dishonest disclosure |
| Agent proceeds without user response | ⛔ BLOCKED — re-halt |
| Validation script fails | ⛔ BLOCKED — fix disclosure and re-run |
