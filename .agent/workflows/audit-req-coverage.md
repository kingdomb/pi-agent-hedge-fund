---
description: Run a requirement coverage audit using the project-sme agent. Generates cross-reference matrix, detects ghost features, orphaned code, and REQ status mismatches. Use for periodic audits or before major releases.
---

# /audit-req-coverage Workflow

$ARGUMENTS

---

> [!IMPORTANT]
> This workflow uses the `project-sme` agent for analysis and the `docs-auditor` agent for fixes. It can be run against the entire project or scoped to a specific layer.

---

## Agent Summary

| Phase | Primary Agent | Supporting Agents |
|-------|---------------|-------------------|
| 1: Anchor Extraction | `project-sme.md` | `explorer-agent.md` |
| 2: Cross-Reference Matrix | `project-sme.md` | `code-archaeologist.md` |
| 3: Drift Report | `docs-auditor.md` | `project-sme.md` |
| 4: Fix & Verify | `docs-auditor.md` | `documentation-writer.md` |

---

## Scope Selection

**Default:** Full project audit (all layers, all requirements).

**Scoped audit:** If arguments specify a layer (e.g., `/audit-req-coverage layer 5`), restrict to that layer's requirements only.

---

## Phase 1: Anchor Extraction

### Step 1.1: Map the Real System (MANDATORY)

**Anchor sources to scan:**

| Source | What It Reveals | Command |
|--------|----------------|---------|
| `docs/requirements/REQ-LEDGER.md` | Claimed requirements and statuses | Read directly |
| `docs/requirements/REQ-USER-STORIES.md` | Acceptance criteria for each REQ | Read directly |
| `backend/src/routes/` | Exposed API capabilities | `find backend/src/routes -name '*.ts'` |
| `backend/src/db/migrations/` | Schema entities and evolution | `ls backend/src/db/migrations/` |
| `backend/tests/` | Backend tests (standard location) | `find backend/tests -name '*.test.ts'` |
| `backend/src/` | Backend tests (colocated `__tests__/`) | `find backend/src -name '*.test.ts' -path '*__tests__*'` |
| `frontend/src/` | Frontend tests (all locations) | `find frontend/src -name '*.test.ts' -o -name '*.test.tsx'` |
| `backend/src/core/` | Core business logic | `find backend/src/core -name '*.ts' -not -path '*__tests__*'` |

### Step 1.2: Extract REQ IDs from Each Source (MANDATORY)

For each anchor source:
1. Extract all REQ-IDs referenced
2. Note the file paths where each REQ-ID appears
3. Compile into a unified list

---

## Phase 2: Cross-Reference Matrix

### Step 2.1: Run the Audit Script (MANDATORY)

**The audit script is the single source of truth.** Do NOT hand-write counts or classifications.

```bash
bash scripts/audit-req-coverage.sh
```

This script:
- Extracts all COMPLETE REQ IDs from the ledger
- Searches the locked scope (defined below) for REQ-ID references
- Classifies each REQ deterministically
- Outputs the markdown matrix directly to `docs/notes/audit_cross_reference_matrix_YYYY-MM-DD.md`

### Locked Scan Scope

**Code directories (where REQ-ID must appear for "has code"):**
```
backend/src/
frontend/src/
sdk/core/src/  sdk/react/src/  sdk/gen-ui/src/  sdk/real-estate/src/
backend/scripts/
backend/migrations/
start.sh  stop.sh
docker-compose.dev.yml  docker-compose.yml  docker-compose.qa.yml  docker-compose.prod.yml
.github/workflows/
```

**Test directories (where REQ-ID must appear for "has test"):**
```
backend/tests/
backend/src/core/ace/__tests__/
backend/src/core/data/__tests__/
frontend/src/ (recursive, *.test.ts and *.test.tsx only)
```

**Excluded from scan:** `node_modules/`, `dist/`, `venv/`, `.git/`

**Matching rule:** The REQ-ID string (e.g., `REQ-L2-01`) must appear as a distinct token in the file. Matches both `@REQ: REQ-xxx` and legacy `REQ-xxx:` formats. Boundary-aware regex prevents false matches (e.g., `REQ-INF-1` does NOT match `REQ-INF-19`).

> [!IMPORTANT]
> **Do NOT modify the scan scope without updating both the workflow AND the script.** Any scope change invalidates previous audit results.

### Step 2.2: Classify Each Requirement (MANDATORY)

Apply the `project-sme` Classification Matrix:

| Docs? | Code? | Tests? | Classification |
|-------|-------|--------|----------------|
| ✅ | ✅ | ✅ | **VERIFIED** |
| ✅ | ✅ | ❌ | **UNVERIFIED** |
| ✅ | ❌ | ❌ | **GHOST FEATURE** |
| ❌ | ✅ | ✅ | **UNDOCUMENTED** |
| ❌ | ✅ | ❌ | **ORPHAN CODE** |
| ❌ | ❌ | ✅ | **ORPHAN TEST** |

### Non-Actionable REQ Exclusions

The following REQs are excluded from the "requires source code annotation" check. They are strategy docs, SOPs, or meta-requirements with no corresponding source code. Tag each with the appropriate label:

| REQ | Tag | Reason |
|-----|-----|--------|
| REQ-BUS-01 | `[DOC-ONLY]` | Usage Metering — business strategy document |
| REQ-FIX-01 | `[META]` | One-time configuration fix, no persistent code |
| REQ-OPS-02 | `[META]` | Disaster Recovery Legacy — merged into REQ-PROD-3 |
| REQ-OPS-05 | `[SOP]` | Automated Integrity Audit — `npm test` framework, no dedicated file |
| REQ-OPS-12 | `[SOP]` | Documentation Governance — agent workflow, not application code |
| REQ-PROD-3 | `[META]` | Disaster Recovery Protocol — aggregates REQ-L6-13, REQ-L6-13a/b/c |

> **Rule:** If a REQ has one of these tags, classify it as `[EXCLUDED]` instead of `GHOST FEATURE`. The audit health score should only count actionable REQs.

### Step 2.3: Output the Matrix (MANDATORY)

Save the cross-reference matrix to a temporary report file. Present summary statistics:

```markdown
## Audit Summary — {Date}

| Classification | Count |
|---------------|-------|
| VERIFIED | {N} |
| UNVERIFIED | {N} |
| GHOST FEATURE | {N} |
| UNDOCUMENTED | {N} |
| ORPHAN CODE | {N} |
| ORPHAN TEST | {N} |

**Total REQs audited:** {N}
**Health Score:** {VERIFIED / Total * 100}%
```

**WAIT for user review before proceeding to Phase 3.**

---

## Phase 3: Drift Report

### Step 3.1: Document-Level Drift Check (MANDATORY)

Using the `docs-auditor` Consistency Check Protocol, verify:

1. **Ledger ↔ Code Sync**: Every `✅ COMPLETE` in the ledger has matching code and tests
2. **User Story ↔ Ledger Sync**: Story statuses match ledger statuses
3. **Layer Doc ↔ Feature Reality**: Layer docs accurately describe implemented features
4. **Phase5 Doc ↔ PR Reality**: Entries have correct PR numbers
5. **Cross-Document Count Consistency**: Summary counts are accurate

### Step 3.2: Generate Drift Report (MANDATORY)

```markdown
## Drift Report — {Date}

### Critical Drift (Blocking)
| Document | Issue | Fix Required |
|----------|-------|-------------|

### Advisory Drift (Non-Blocking)
| Document | Issue | Recommended Fix |
|----------|-------|----------------|

### Statistics Drift
| Document | Claimed | Actual | Delta |
|----------|---------|--------|-------|
```

**WAIT for user approval before fixing.**

---

## Phase 4: Fix & Verify

### Step 4.1: Fix Critical Drift First (MANDATORY)

Address all items in the "Critical Drift" table. These are blocking issues:
- Ghost features (mark as 🌗 PARTIAL or ❌ NOT STARTED)
- Incorrect statuses (update to match reality)
- Missing entries (add them)

### Step 4.2: Fix Advisory Drift (OPTIONAL — per user approval)

Address items in the "Advisory Drift" table:
- Outdated descriptions
- Stale statistics
- Missing cross-references

### Step 4.3: Re-Run Consistency Checks (MANDATORY)

After fixes, re-run the full Consistency Check Protocol.

**Expected:** All 5 checks PASS.

### Step 4.4: Output Final Report (MANDATORY)

```markdown
## Audit Complete — {Date}

**Before:** {N} issues found ({N} critical, {N} advisory)
**After:** {N} issues remaining
**Health Score:** {Before}% → {After}%

### Changes Made
| File | Change | Lines Modified |
|------|--------|---------------|
```

---

## Quick Reference

```bash
# Full project audit
/audit-req-coverage

# Layer-scoped audit
/audit-req-coverage layer 5

# Just the cross-reference matrix (no fixes)
/audit-req-coverage --matrix-only
```