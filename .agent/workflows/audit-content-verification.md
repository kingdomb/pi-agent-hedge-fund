---
description: "Phase 3 adversarial content verification protocol for /audit-doc-content. MANDATORY — cannot be skipped. Read by the main audit-doc-content.md workflow."
---

# ⛔ HARD ENFORCEMENT PRE-FLIGHT CHECK (READ BEFORE ANYTHING ELSE)

> [!CAUTION]
> **STOP. Before you process ANY document through this workflow, confirm you are NOT doing any of the following. If you are doing ANY of these, you are in VIOLATION. Stop immediately and correct course.**
>
> **BANNED PATTERNS (ZERO TOLERANCE):**
> 1. ❌ **Reading more than 200 lines at once** — If your `view_file` call spans >200 lines, you are violating the chunking rule. STOP.
> 2. ❌ **Batch-reading multiple files in parallel** — Each file must be audited SEQUENTIALLY and COMPLETELY before moving to the next. STOP.
> 3. ❌ **Spot-checking "high-risk claims" only** — You must extract and verify EVERY factual claim, not just the ones you think matter. STOP.
> 4. ❌ **Writing a DRIFT report without per-claim evidence** — Every ✅ VERIFIED must cite a file path and line number. "Looks clean" is NOT evidence. STOP.
> 5. ❌ **Skipping claim extraction because the doc "looks fine"** — Your opinion of the doc is irrelevant. PROVE it with codebase evidence. STOP.
> 6. ❌ **Using full-file reads (no StartLine/EndLine) for files >200 lines** — This is the #1 violation pattern. You MUST use StartLine/EndLine with ≤200 line ranges. STOP.
> 7. ❌ **Combining multiple files into one "batch" DRIFT report without individual per-file claim tables** — Each file gets its own claim verification table. STOP.
>
> **IF YOU VIOLATED ANY OF THE ABOVE:** The resulting DRIFT report is INVALID and must be re-done. There are NO exceptions. There is NO "faster approach." There is NO "spot-check mode." The protocol is the protocol.

---

# Phase 3: Content Verification — Adversarial Proof Protocol

> [!CAUTION]
> **THIS FILE IS MANDATORY.** It is referenced by `/audit-doc-content` Phase 3. You MUST read and execute every step in this file. Skipping any step is a workflow violation.

> [!CAUTION]
> **THIS PHASE IS MANDATORY AND NON-NEGOTIABLE.** You MUST verify every factual claim in the document against the codebase. Do NOT trust the document at face value. Do NOT skip claims because they "seem right." PROVE each one or FLAG it.

---

## Step 3.1: Extract All Factual Claims (MANDATORY — CHUNKED)

> [!CAUTION]
> **CHUNKING RULE:** Read the document in strict chunks of **200 lines maximum**. Do NOT read the next chunk until you have completely extracted, verified, and reported the claims for the current chunk. If the document is large, you MUST loop this process: read chunk → extract claims → verify claims → report → read next chunk. This prevents context window collapse on large files like `ARCH-FINAL.md` (3,300+ lines, ~400 claims).

**Process per chunk:**
1. Read lines N to N+199
2. Extract every verifiable claim into a checklist
3. Verify each claim (Step 3.2)
4. Record results in the Claim Verification Report (Step 3.3)
5. Only THEN read the next 200-line chunk
6. Repeat until EOF

**Claim types to extract:**

| Claim Type | Example | How to Prove |
|------------|---------|--------------|
| **REQ Status** | "REQ-INF-3: ✅ COMPLETE" | Check `REQ-LEDGER.md` + grep code for implementation |
| **Agent Names/Roles** | "Founding team: CDO, Sales Wolf..." | Check seed scripts, `app.agents` schema, `01_founding_team.ts` |
| **Feature Existence** | "MFA is implemented" | Grep routes, check test files |
| **File/Path References** | "See `backend/src/core/db.ts`" | Verify file exists at that path |
| **Table/Column Names** | "The `governance.vectors` table..." | Grep migrations/schema SQL |
| **Endpoint Paths** | "`POST /api/auth/login`" | Grep route definitions |
| **Agent/Feature Counts** | "12 agents defined" | Count actual entries |
| **Status Claims** | "Only Concierge is seeded" | Check seed scripts for all seeded agents |
| **Dependency Claims** | "Depends on REQ-L6-33" | Verify in REQ spec files |
| **Architecture Descriptions** | "Layer 2 handles agent lifecycle" | Cross-reference layer doc content |

---

## Step 3.2: Verify Each Claim (MANDATORY)

> [!CAUTION]
> **SAFE SEARCH RULE:** When using grep or any search tool, you MUST restrict the search to relevant directories (e.g., `grep -rn "claim" backend/src/ frontend/src/`) or explicitly exclude massive folders (e.g., `--exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.next --exclude-dir=venv`). Do NOT run unbounded root-level searches. Unbounded grep will hang, time out, and crash the workflow.

**Safe search targets by claim type:**

| Claim Type | Search Scope |
|------------|--------------|
| Routes/Endpoints | `backend/src/routes/` |
| Core logic | `backend/src/core/` |
| Schema/Tables | `backend/sql/`, `backend/db/` |
| Seed scripts | `backend/scripts/seeds/` |
| Frontend components | `frontend/src/` |
| Tests | `backend/tests/` |
| Agent definitions | `.agent/agents/` |
| REQ specs | `docs/requirements/` |
| Migrations | `backend/db/migrations/` |

For EACH claim extracted in Step 3.1:

```
1. STATE the claim (quote from the document, with line number)
2. SEARCH the codebase (scoped grep, file read, schema check)
3. VERDICT:
   ✅ VERIFIED — Claim matches code reality (cite evidence)
   ❌ DRIFT — Claim contradicts code reality (cite evidence)
   ⚠️ STALE — Claim was once true but is now outdated (cite evidence)
   📝 FUTURE — Claim describes a planned/future feature NOT yet in code.
      CORRECT if doc explicitly marks it as planned/future/not-yet-implemented.
      DRIFT if doc presents it as already implemented.
   🔍 UNVERIFIABLE — Cannot prove or disprove (explain why)
```

> [!IMPORTANT]
> **Minimum evidence standard:** Each ✅ VERIFIED verdict MUST cite at least one file path, line number, or command output as proof. "Looks correct" is NOT acceptable evidence.

---

## Step 3.3: Produce Claim Verification Report (MANDATORY)

For each audited file, output:

```markdown
## Content Audit: {filename}

**Date:** {date}
**Claims Extracted:** {N}
**Verified:** {N} | **Drift:** {N} | **Stale:** {N} | **Future:** {N} | **Unverifiable:** {N}

### Claim Verification Table
| # | Claim (quoted) | Line | Type | Verdict | Evidence |
|---|---------------|------|------|---------|----------|
| 1 | "The founding team consists of CDO..." | L42 | Agent Names | ❌ DRIFT | `01_founding_team.ts` seeds Concierge, Radar, CAIO, Security Auditor |
| 2 | "POST /api/auth/login" | L88 | Endpoint | ✅ VERIFIED | `backend/src/routes/auth.ts:150` |
| 3 | "System Expert will provide..." | L200 | Feature | 📝 FUTURE | Marked as planned, REQ-L2-19 not yet implemented |
```

## Step 3.4: Pause Point — Notify User (MANDATORY)

After completing Phase 3 for EACH file:
1. Present the Claim Verification Report to the user
2. **WAIT** for user to review before proceeding to fixes
3. User may approve fixes, skip fixes, or redirect to a different file
