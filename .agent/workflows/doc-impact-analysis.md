---
description: Documentation Impact Analysis gate for create-req. Scans full documentation scope, produces Doc Update Manifest, and validates via 4-point verification gate. Used by create-req Step 1.4.
---

# Documentation Impact Analysis (MANDATORY — BLOCKING)

> [!IMPORTANT]
> This step prevents documentation drift. The `docs-auditor` MUST complete this analysis before Phase 2 drafting.
> The 3 baseline files (Ledger, User Stories, Phase5 Updates) were ALREADY mandatory in Phase 5. This step catches EVERYTHING ELSE across the full documentation scope.

**Agent:** `docs-auditor.md`

## Step A — Scan the Full Documentation Scope (MANDATORY)

Evaluate the requirement against ALL documentation directories:

| Directory | Contains | Always Check? |
|-----------|----------|--------------|
| `docs/architecture/` | Ledger, User Stories, Phase5, ARCHITECTURE_FINAL, layer docs, TENANT_LIFECYCLE, ERD, steering vector docs | ✅ Always |
| `docs/backend/` | Interaction runbook, Org-0 staffing manual, ops SOPs | If backend logic changes |
| `docs/guides/` | Auth, governance protocols, sandbox guide, model switching, steering vectors | If user-facing behavior changes |
| `docs/infrastructure/` | Environment manifest, cloud specs, tier orchestration | If infra/deployment changes |
| `docs/security/` | Security documentation | If auth/RLS/PII changes |
| `docs/operations/` | Deployment protocol, disaster recovery, tenant migration | If ops procedures change |
| `docs/global_references/` | Infrastructure guide, testing guide, troubleshooting | If cross-cutting concerns change |
| `docs/technical_specs/` | Technical specifications | If API contracts change |
| `README.md` (root) | Project overview, feature list, quick start | If user-visible capabilities change |

## Step A.2 — New Document Evaluation (MANDATORY)

For requirements introducing **new concepts**, evaluate whether a new doc file is needed:

| Question | If YES → Action |
|----------|-----------------|
| Introduces a new layer or subsystem? | Create `ARCH-LAYER*` or `SPEC-*` in `docs/architecture/` or `docs/technical_specs/` |
| Creates a user-facing workflow? | Create `GUIDE-*` in `docs/guides/` |
| Adds ops/deployment procedures? | Create `OPS-*` in `docs/operations/` |
| Changes security posture? | Create `SEC-*` in `docs/security/` |
| Adds backend SOP or runbook? | Create `BE-*` in `docs/backend/ops/` or `docs/backend/guides/` |

If a new doc is needed:
1. Add it to the Doc Update Manifest with action `CREATE`
2. Specify the target directory and filename (following `PREFIX-TOPIC.md` for subdirectories; root-level docs are exempt)
3. Include YAML frontmatter fields: `title`, `id`, `category`, `audience`, `owner`, `last_verified`, `status`

## Step B — Produce the Doc Update Manifest (MANDATORY)

For EACH affected document, add a row specifying the action. For each directory evaluated and found NOT affected, add an explicit `NO CHANGE` row with justification.

Write the manifest to `docs/requirements/{REQ-ID}.md` as a `## Doc Update Manifest` section.

**Format:**
```markdown
## Doc Update Manifest — {REQ-ID}

### Documents Requiring Updates
| Document | Action | Details |
|----------|--------|---------|
| `ARCH-REQUIREMENTS-LEDGER.md` | ADD ROW | Layer X table, status ✨ NEW |
| `ARCH-USER-STORIES.md` | ADD STORY | Section: Layer X, with AC from spec |
| `ARCH-EXECUTION-ORDER.md` | ADD ENTRY | Phase section, execution sequence |

### Directories Evaluated — No Changes Required
| Directory | Reason |
|-----------|--------|
| `docs/security/` | No auth/RLS/PII impact |
```

## ⛔ Verification Gate (MANDATORY — BLOCKING)

> [!CAUTION]
> **HARD GATE**: The manifest MUST exist, cover baseline docs, AND prove the full documentation scope was evaluated.

**Check 1 — Manifest exists:**
```bash
grep -c "Doc Update Manifest" docs/requirements/{REQ-ID}.md
```
Expected: `1` or higher.

**Check 2 — 3 baseline docs present:**
```bash
grep -c "REQUIREMENTS_v3.4.0_LEDGER\|USER_STORIES\|PHASE5_DOCUMENTATION_UPDATES" docs/requirements/{REQ-ID}.md
```
Expected: `3` or higher.

**Check 3 — Full scope was evaluated:**
```bash
grep -c "No Changes Required\|Directories Evaluated" docs/requirements/{REQ-ID}.md
```
Expected: `1` or higher.

**Check 4 — Beyond-baseline docs were considered:**
```bash
grep -cE "layer.*\.md|ARCHITECTURE_FINAL|TENANT_LIFECYCLE|DATABASE_ERD|README|guides/|runbook|operations/" docs/requirements/{REQ-ID}.md
```
Expected: `1` or higher.

**Violation:** If any check fails → ⛔ BLOCKED. Return to Step A and re-scan ALL directories.
