---
description: Audit documentation content accuracy. Reads DOCS_MAP, verifies each doc matches its described purpose, produces DRIFT-* reports. Use for periodic doc health checks.
---

# /audit-doc-content Workflow

$ARGUMENTS

---

> [!CAUTION]
> **ADVERSARIAL AUDIT.** Every factual claim in every document MUST be verified against the codebase. "Looks correct" is not valid — you must **prove** each claim. If you cannot prove it, flag it.

---

## Invocation

```bash
# Full audit — starts with ARCH-FINAL.md, then all tracked docs
/audit-doc-content

# Target a single file
/audit-doc-content docs/backend/guides/BE-ORG0-STAFFING.md

# Category-scoped audit
/audit-doc-content architecture

# Report only — no fixes
/audit-doc-content --report-only

# Exclude files (repeatable) — skip already-audited docs
/audit-doc-content --exclude ARCH-FINAL.md --exclude BE-ORG0-STAFFING.md
```

---

## Agent Summary

| Phase | Primary Agent | Role |
|-------|---------------|------|
| 1: Manifest Loading | `docs-auditor` | Load DOCS_MAP, build inventory |
| 2: Structural Verification | `docs-auditor` | File existence, frontmatter, naming |
| 3: **Content Verification** | `project-sme` | **Adversarial claim-by-claim proof** |
| 4: Drift Report | `docs-auditor` | Compile findings, create DRIFT-* files |
| 5: Fix & Verify | `docs-auditor` + `documentation-writer` | Apply fixes, re-verify |

---

## Phase 1: Manifest Loading

### Step 1.1: Read DOCS_MAP (MANDATORY)

1. Read `docs/DOCS_MAP.md`
2. Parse all category tables — extract for each doc:
   - **ID**, **File** (relative path), **Description**, **Status**, **Last Verified**
3. Build inventory list with absolute paths
4. Report: `Loaded {N} docs across {N} categories`

### Step 1.2: Determine Scope (MANDATORY)

- **No arguments:** Full audit. Sort by priority tier. `ARCH-FINAL.md` is ALWAYS first.
- **File path argument:** Single-file audit. Skip to Phase 2 for that file only.
- **Category argument:** Restrict to that category's docs only.
- **`--exclude`:** Remove specific files from the audit. Repeatable. Matches on filename (e.g., `--exclude ARCH-FINAL.md`). Excluded files are silently skipped during inventory processing.

### Priority Tiers (execution order)

| Tier | Docs | Rationale |
|------|------|-----------|
| **T0** | `ARCH-FINAL.md` | System truth. **ALWAYS FIRST.** |
| **T1** | `ARCH-TENANT-LIFECYCLE.md`, `REQ-LEDGER.md`, `REQ-USER-STORIES.md`, `GUIDE-EXECUTION-ORDER.md` | Core architecture + REQ tracking |
| **T2** | Layer docs (L1–L6), `BE-ORG0-STAFFING.md`, `ARCH-NORTH-STAR.md` | Architecture claims, agent defs |
| **T3** | Guides, security, infrastructure, operations docs | Procedural docs |
| **T4** | Frontend, global refs, tech specs, root-level docs | Lower blast radius |

> [!IMPORTANT]
> **Process ONE file at a time.** Complete all phases (2–5) for the current file before moving to the next.

---

## Phase 2: Structural Verification (per file)

### Step 2.1: Surface Checks (MANDATORY)

| Check | Method | Severity |
|-------|--------|----------|
| **File Exists** | Path from DOCS_MAP resolves | Critical |
| **YAML Frontmatter** | Has `title`, `status`, `last_verified` fields | Advisory |
| **Title Match** | First `# ` heading matches DOCS_MAP description | Advisory |
| **Naming Convention** | `PREFIX-TOPIC.md` for categorized dirs. Root-level exempt | Advisory |
| **Placeholder Detection** | <50 real lines when status is NOT 📝 | Advisory |

### Step 2.2: Cross-Reference Checks (MANDATORY)

1. **Orphan Detection:** `.md` files in `docs/` NOT listed in DOCS_MAP
2. **Stale Entries:** DOCS_MAP entries pointing to missing files
3. **Category Mismatch:** File location vs. listed category

---

## Phase 3: Content Verification — Adversarial Proof (per file)

> [!CAUTION]
> **MANDATORY — CANNOT BE SKIPPED.** You MUST read and execute the full adversarial verification protocol defined in:
>
> **📄 `.agent/workflows/audit-content-verification.md`**
>
> That file contains Steps 3.1 through 3.4 including: chunking rules (200-line max), safe grep constraints, claim extraction, the 5 verdict types (✅ VERIFIED, ❌ DRIFT, ⚠️ STALE, 📝 FUTURE, 🔍 UNVERIFIABLE), report template, and the mandatory pause point. **You MUST read that file before proceeding.** Failure to read and follow it is a workflow violation.

---

## Phase 4: Drift Report

### Step 4.1: Generate Drift Report (MANDATORY)

```markdown
## Documentation Content Audit — {Date}

### Critical Drift (Content contradicts codebase)
| ID | File | Claim | Reality | Fix Required |
|----|------|-------|---------|-------------|

### Stale Content (Was true, now outdated)
| ID | File | Claim | Current State | Fix Required |
|----|------|-------|---------------|-------------|

### Statistics
| Metric | Count |
|--------|-------|
| Total docs audited | {N} |
| Total claims verified | {N} |
| ✅ Verified | {N} |
| ❌ Drift | {N} |
| ⚠️ Stale | {N} |
| 📝 Future | {N} |
| 🔍 Unverifiable | {N} |
| **Content Accuracy Score** | {N}% |
```

### Step 4.2: Create DRIFT Reports (MANDATORY if critical drift found)

Path: `docs/tech-debt/DRIFT-{NNN}-{TOPIC}.md`

**WAIT for user approval before proceeding to Phase 5.**

---

## Phase 5: Fix & Verify

### Step 5.1: Fix Drift Items (User-Approved Only)

> [!CAUTION]
> **HARD GATE**: MUST NOT modify doc content without user approval.

For each approved fix:
1. Apply the fix
2. **Re-verify** — grep/read codebase again to confirm new content is accurate
3. Update DOCS_MAP status and `Last Verified`
4. Update YAML frontmatter `last_verified`

### Step 5.2: Re-Verify Fixed Documents (MANDATORY)

Re-run Phase 3 on fixed documents. The fix must not introduce new drift.

### Step 5.3: Move to Next File (Full Audit Only)

Mark current file AUDITED → move to next in priority tier → return to Phase 2.

### Step 5.4: Final Report (MANDATORY — after all files)

```markdown
## Audit Complete — {Date}

**Files Audited:** {N} | **Claims Verified:** {N}
**Before:** {N} drift | **After:** {N} remaining
**Accuracy:** {Before}% → {After}%

### Changes Made
| File | Claims Fixed | Lines Modified |
|------|-------------|---------------|
```

---

## Anti-Patterns (What This Workflow Prevents)

| ❌ Old Behavior | ✅ Required Behavior |
|----------------|---------------------|
| "Title matches, looks good" | Verify every claim against code |
| Check first 100 lines only | Read the ENTIRE document (chunked) |
| Trust ⚠️ warnings in docs | Verify if the warning is still accurate |
| Mark DRIFT RESOLVED based on a plan | Only RESOLVED after verifying fix shipped |
| Batch-audit 50 files at once | One file at a time |
| "100% health" based on structure | Health score based on claim accuracy |
