---
description: Verify a 🟡 doc against the codebase using multi-perspective agent verification and consensus protocol
---

# 🟡 Doc Verification Protocol v2.0 (Multi-Perspective Consensus)

> **Invocation:** Use the **orchestrator** role. Example:
> ```
> As orchestrator, run /verify-doc on docs/guides/GUIDE-AUTH.md
> ```

---

## Phase 0: Setup (Orchestrator)

1. **Identify the doc** and its DOCS_MAP category/audience
2. **Create the workspace:**
   ```bash
   mkdir -p /tmp/verify-doc/{doc-basename}/
   ```
3. **Select applicable roles** from the table below based on doc content:

| Role | Activated When Doc Contains | Verification Scope |
|------|---------------------------|-------------------|
| `backend-specialist` | Code paths, DB schemas, service names, queues, APIs | `grep` every class, interface, table, column, queue, file path mentioned |
| `security-auditor` | Auth, encryption, RLS, keys, censor, governance | Check actual auth implementations, hashing algorithms, RLS policies |
| `devops-engineer` | Docker, env vars, versions, ports, compose, infra | Compare against `docker-compose.yml`, `package.json`, `.env.example`, `start.sh` |
| `frontend-specialist` | Components, hooks, routes, UI framework, themes | Check `frontend/src/` for named components, hooks, routes |
| `scribe` | Always activated | TOC accuracy, cross-references, formatting, version consistency, [NOT YET IMPLEMENTED] completeness |

> **Minimum:** Every verification MUST include at least `backend-specialist` + `scribe`. Skip `frontend-specialist` only if the doc has zero UI content.

---

## Phase 1: Independent Verification (Per Role)

**⚠️ CRITICAL RULE: Each role produces its report INDEPENDENTLY. Do NOT carry conclusions from one role into another. Start each role with a fresh read of the doc.**

For EACH activated role, create a findings file:

```
/tmp/verify-doc/{doc-basename}/{role-name}.md
```

### Required Report Format (Each Role)

```markdown
# {Role Name} Verification — {doc basename}
Date: {today}

## Claims Checked
| # | Line(s) | Claim | Evidence Command | Result |
|---|---------|-------|-----------------|--------|
| 1 | L42 | "bcrypt for password hashing" | `grep -rn "bcrypt" backend/src/` | ✅ Confirmed: auth.ts:1 |
| 2 | L108 | "q_high_priority queue" | `grep -rn "q_high_priority" backend/src/` | ❌ WRONG: Code uses `q_fast_lane` |
| 3 | L215 | "Lifecycle Manager auto-upgrades" | `find backend/src -name "*lifecycle*"` | ⚠️ NOT IMPLEMENTED: No code found |

## Summary
- Claims checked: {N}
- ✅ Confirmed: {N}
- ❌ Discrepancies: {N}
- ⚠️ Not Yet Implemented: {N}
- Coverage: {%} of claims in my domain
```

### Per-Role Verification Checklist

**backend-specialist MUST check:**
- [ ] Every class/interface name → `grep` in `backend/src/`
- [ ] Every file path mentioned → `ls` or `find` to confirm existence
- [ ] Every DB table/column → `grep` in `backend/migrations/`
- [ ] Every queue name → `grep` in `backend/src/core/queue/`
- [ ] Every service name → `find backend/src -name "*{name}*"`
- [ ] Every API endpoint → `grep` in `backend/src/routes/`

**security-auditor MUST check:**
- [ ] Hashing algorithms → `grep` for actual implementation (bcrypt vs argon2 etc.)
- [ ] RLS policy names → `grep` in migrations for actual policy definitions
- [ ] Encryption claims → verify actual cipher/key management in code
- [ ] Auth flow claims → trace actual middleware chain

**devops-engineer MUST check:**
- [ ] Docker image names/tags → compare with `docker-compose.yml`
- [ ] Container names → compare with `docker-compose.yml`
- [ ] Environment variable names → compare with `.env.example` and code usage
- [ ] Version numbers → compare with `package.json` (backend AND frontend)
- [ ] Port numbers → compare with `docker-compose.yml`

**frontend-specialist MUST check:**
- [ ] Component names → `find frontend/src -name "*{name}*"`
- [ ] Hook names → `grep` in `frontend/src/`
- [ ] Framework version → `frontend/package.json`
- [ ] Route paths → `grep` in app router structure

**scribe MUST check:**
- [ ] Every `##` / `###` heading appears in TOC (if TOC exists)
- [ ] Cross-references to other docs → confirm target files exist
- [ ] Version numbers in header vs footer vs body are consistent
- [ ] Every feature described as current has code evidence (from other roles' findings)
- [ ] Features with no code evidence are tagged `[⚠️ NOT YET IMPLEMENTED]`
- [ ] No broken markdown tables (column count mismatches)
- [ ] No unclosed code fences
- [ ] **Deprecation/Future-State Classification** (see below)

### ⚠️ MANDATORY: Deprecation vs Future-State Rule

> **This rule applies to EVERY claim flagged as ⚠️ NOT IMPLEMENTED by any role.**

For each unimplemented feature found, the orchestrator MUST classify it:

| Classification | Criteria | Action |
|---------------|----------|--------|
| **DEPRECATED** | Feature was removed from code, never committed, or superseded by a different approach | **REMOVE** the claim from the doc entirely |
| **FUTURE-STATE** | Feature is planned, designed, or has stubs but isn't fully implemented | **ANNOTATE** with `⚠️ NOT YET IMPLEMENTED` inline (matching `ARCH-FINAL.md` style) |
| **STALE VALUE** | A specific value (version, queue name, config) has changed | **REPLACE** with the correct current value |

**Decision process:**
1. `grep` / `git log` to check if the feature ever existed in code
2. Check `MISSING-FEATURES-GAP-ANALYSIS.md` for prior classification
3. If the feature has a REQ-* ID in the ledger → likely **FUTURE-STATE**
4. If the feature was replaced by something else → **DEPRECATED** (remove and replace)
5. If uncertain → mark as **FUTURE-STATE** (safer default)

---

## Phase 2: Consensus (Orchestrator)

**After ALL role reports are written**, the orchestrator:

1. **Read all findings files** from `/tmp/verify-doc/{doc-basename}/`
2. **Create consensus file:**
   ```
   /tmp/verify-doc/{doc-basename}/consensus.md
   ```
3. **Merge findings** using this protocol:

### Consensus Rules

| Scenario | Action |
|----------|--------|
| All roles agree claim is ✅ | Mark as CONFIRMED |
| Any role finds ❌ discrepancy | Mark as **DISCREPANCY** — must fix |
| Any role finds ⚠️ not implemented | Mark as **NEEDS ANNOTATION** — add `[⚠️ NOT YET IMPLEMENTED]` |
| Roles disagree on a claim | Mark as **CONFLICT** — orchestrator must re-verify with a fresh `grep` |
| A role skipped a claim in their domain | Mark as **COVERAGE GAP** — role must go back and check it |

### Consensus File Format

```markdown
# Consensus Report — {doc basename}
Date: {today}
Roles: {list of activated roles}

## Coverage Matrix
| Role | Claims Checked | Coverage % | Pass? |
|------|---------------|-----------|-------|
| backend-specialist | 42 | 95% | ✅ |
| security-auditor | 12 | 100% | ✅ |
| devops-engineer | 18 | 88% | ❌ (< 90%) |

## Discrepancies (MUST FIX)
| # | Line | Wrong | Correct | Found By |
|---|------|-------|---------|----------|

## Not Yet Implemented (MUST ANNOTATE)
| # | Line | Feature | Found By |
|---|------|---------|----------|

## Conflicts (MUST RE-VERIFY)
| # | Line | Role A Says | Role B Says | Resolution |
|---|------|------------|-------------|-----------|
```

### Coverage Gate

> **⛔ BLOCKED:** If ANY role's coverage is below **90%**, send them back to check the missing claims before proceeding to Phase 3.

---

## Phase 3: Apply Corrections (Orchestrator)

Only after the consensus report is complete:

1. **Fix all DISCREPANCIES** — update the doc to match code
2. **Add all NOT YET IMPLEMENTED annotations** — `> [!WARNING]` blocks
3. **Resolve all CONFLICTS** — fresh grep, update doc
4. **Regenerate TOC** if any headings changed:
   // turbo
   ```bash
   python3 .agent/scripts/toc_generator.py --file <path> --force
   ```

---

## Phase 4: Update Tracking (Orchestrator)

1. **Update DOCS_MAP.md** — flip 🟡 → ✅ with today's date
2. **Update `docs/MISSING-FEATURES-GAP-ANALYSIS.md`** (MANDATORY):
   - For each ⚠️ NOT YET IMPLEMENTED item found:
     - If the feature is already tracked → update its description with `⚠️ annotated in {doc} ({date})`
     - If the feature is NOT tracked → add a new row with the next available `#` ID
   - If the verified doc has NO missing features → add a note under its section: `> No missing features — corrections were stale values only.`
   - Update the **total count** at the bottom
   - Add entries to the **Doc Annotation Sync Log**
3. **Update audit reports:**
   - `docs/notes/doc-content-audit_report.md`
   - `audit_report.md.resolved` (artifact copy)
4. **Clean up temp files:**
   // turbo
   ```bash
   rm -rf /tmp/verify-doc/{doc-basename}/
   ```

---

## Quick Reference: Invocation Examples

**Single doc:**
```
As orchestrator, run /verify-doc on docs/guides/GUIDE-AUTH.md
```

**Batch (multiple docs):**
```
As orchestrator, run /verify-doc on the following docs:
1. docs/guides/GUIDE-AUTH.md
2. docs/guides/GUIDE-MODEL-SWITCHING.md
3. docs/infrastructure/INFRA-CLOUD-GPU.md
```

**Re-verify after prior errors:**
```
As orchestrator, re-verify docs/architecture/ARCH-BUSINESS-STRATEGY.md using /verify-doc.
Prior verification missed queue name and version errors. Apply extra scrutiny.
```

---

## Anti-Laziness Rules

> These rules exist because previous verifications missed errors due to shortcuts.

1. **NO SKIMMING.** Every claim must have a `grep` or `find` command as evidence. "Looks right" is not evidence.
2. **NO ROLE COPYING.** Each role writes their report from a fresh doc read. They do NOT see other roles' findings first.
3. **NO AUTO-AGREE.** If a role has zero discrepancies, the orchestrator MUST challenge by picking 3 random claims and re-verifying them.
4. **NO PARTIAL COVERAGE.** If a role checks 10 claims but the doc has 50 in their domain, that's 20% coverage — BLOCKED.
5. **VERSION NUMBERS ARE MANDATORY.** Every `package.json` version, Docker image tag, and framework version MUST be checked. No exceptions.
