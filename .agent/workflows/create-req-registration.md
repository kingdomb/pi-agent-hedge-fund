---
description: Phase 5 Registration & Integration sub-workflow for /create-req. MANDATORY — cannot be skipped. Invoked programmatically by the Phase 5 checkpoint.
---

# /create-req Phase 5: Registration & Integration

> [!CAUTION]
> **THIS SUB-WORKFLOW IS MANDATORY.** It is programmatically enforced by the Phase 5 checkpoint. Every step below produces artifacts that are **validated by code** — the checkpoint will BLOCK if any are missing.

---

### ⛔ PREREQUISITE CHECK (MANDATORY)

```bash
npm run checkpoint:validate -- --req {REQ-ID} --validate-phase 4
```

---

### Step 5.1: Update Documentation (MANDATORY — 4 FILES)

> [!CAUTION]
> **DOC SCOPE GUARD (ENFORCED BY CI):** During `/create-req`, you may ONLY modify these 4 docs + the spec file. The Phase 5 checkpoint will BLOCK if any other `docs/` file has been edited. All other doc updates belong in `/implement-req` Phase 5 via `/doc-sync-gate`.

**File 1:** `docs/requirements/REQ-LEDGER.md`
- Add requirement row to layer table

**File 2:** `docs/requirements/REQ-USER-STORIES.md`
- Add full user story with acceptance criteria

**File 3:** `docs/guides/GUIDE-EXECUTION-ORDER.md`
- Add requirement to phase section

**File 4:** `docs/EXECUTION-PLAN.md` ⚠️ **#1 MOST SKIPPED STEP**

> [!CAUTION]
> **TWO UPDATES REQUIRED — BOTH ARE ENFORCED BY CODE:**
> 1. **Step 1:** Mark the corresponding GAP item as `[x]` and append `→ {REQ-ID}` (if a Step 1 item exists)
> 2. **Step 2:** Add `/implement-req {REQ-ID}` to the appropriate Wave
>    - Format: `- [ ] \`/implement-req {REQ-ID}\` — {Short Name}`
>
> **The Phase 5 checkpoint WILL BLOCK if the Step 2 entry is missing.**

---

### Step 5.2: Create GitHub Issue (MANDATORY)

```bash
gh issue create \
  --title "[{REQ-ID}] {Name}" \
  --body "## Requirement
{Description}

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## References
- Ledger: {REQ-ID}
- Phase: {Phase}"
```

Apply labels: `requirement`, layer label, priority label

---

### Step 5.3: Programmatic Verification (MANDATORY — ALL ENFORCED BY CODE)

> [!CAUTION]
> **Every check below is enforced by the Phase 5 checkpoint script.** If any fails, the checkpoint BLOCKS sign-off. You cannot bypass these.

**Automated checks (run by checkpoint):**
- ✅ `REQ-LEDGER.md` contains `{REQ-ID}`
- ✅ `REQ-USER-STORIES.md` contains `{REQ-ID}`
- ✅ `GUIDE-EXECUTION-ORDER.md` contains `{REQ-ID}`
- ✅ `EXECUTION-PLAN.md` Step 2 contains `/implement-req {REQ-ID}` ← **NEW GATE**
- ✅ Spec file exists: `docs/requirements/{REQ-ID}.md`
- ✅ GitHub issue exists with `{REQ-ID}` in title
- ✅ Doc Scope Guard: no unauthorized doc edits

---

### Step 5.4: GAP Sync Integrity (MANDATORY — BLOCKING)

```bash
python3 .agent/scripts/gap_sync_verifier.py .
```

> [!CAUTION]
> **BLOCKED** if `gap_sync_verifier.py` exits with code 1. Fix missing references before proceeding.

---

### Step 5.5: Documentation Governance Gate (MANDATORY) [REQ-OPS-12]

> Only required if this REQ creates, deletes, or moves any doc file in `docs/`.

**Check 1: DOCS_MAP Sync** — New `.md` files in `docs/` must be in `docs/DOCS_MAP.md`.
**Check 2: Naming Convention** — `PREFIX-TOPIC.md` pattern required.
Allowed prefixes: `ARCH-`, `REQ-`, `GUIDE-`, `BE-`, `FE-`, `INFRA-`, `OPS-`, `SEC-`, `SPEC-`, `REF-`, `DRIFT-`, `FUTURE_`, `TEST-`, `PROJECT_`

---

### ⛔ PHASE 5 CHECKPOINT (MANDATORY)

```bash
npm run checkpoint:sign-off -- --req {REQ-ID} --sign-off 5 --agent devops-engineer
```

> [!CAUTION]
> This checkpoint runs ALL automated verification checks. If ANY check fails, sign-off is BLOCKED. The checkpoint output IS the audit trail — include it in your response.

**Expected:** All 5 checkpoint files present. Doc Scope Guard PASS. Step 2 entry verified.

---

## Violation Handling

| Violation | Response |
|-----------|----------|
| Checkpoint missing | ⛔ BLOCKED — create checkpoint before proceeding |
| Board quorum < 75% | ⛔ BLOCKED — get additional approvals |
| Step skipped | ⛔ BLOCKED — go back and execute step |
| No output shown | ⛔ BLOCKED — re-run command and show output |
| **Doc Scope Guard violation** | ⛔ BLOCKED — revert unauthorized doc edits with `git checkout HEAD -- <files>`, then re-run checkpoint |
| **Step 2 entry missing** | ⛔ BLOCKED — add `/implement-req {REQ-ID}` to EXECUTION-PLAN.md Step 2 |
