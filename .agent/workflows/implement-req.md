---
description: 5-Phase Standard Operating Procedure for implementing requirements. ALL STEPS ARE MANDATORY. Checkpoint commands MUST be executed and output included.
---

# /implement-req Workflow

$ARGUMENTS

---

> [!CAUTION]
> **ALL STEPS ARE MANDATORY**. Execute every checkpoint command and include output. Skipping ANY step is a BLOCKING violation. CI rejects PRs without complete checkpoint chains.

---

> **Agents:** P1: product-manager | P2: devops-engineer | P3: backend-specialist | P4: test-engineer | P5: devops-engineer + docs-auditor
>
> **Every phase begins with:** `npm run checkpoint:validate -- --req {REQ-ID} --validate-phase {N-1}`

---

## Phase 1: Contextual Anchoring

### Step 1.1: Load Environment Constraints (MANDATORY)

**Actions** (execute ALL):
1. Read `docs/infrastructure/INFRA-ENV-MANIFEST.md`
2. Identify tier: DEV (5.7GB VRAM), QA/PROD (80GB)
3. Check `AI_TIER` env var

### Step 1.2: Load Requirement Spec & User Story (MANDATORY)

**Actions** (execute ALL):
1. **Check for `docs/requirements/{REQ-ID}.md`.**
   - **If it exists:** Read it — technical blueprint with schema, API, implementation details.
   - **If it does NOT exist:** Create it using `REQ-USER-STORIES.md`, `REQ-LEDGER.md`, codebase research, and the `/create-req` Step 2.5 template.
2. Lookup REQ-ID in `docs/requirements/REQ-USER-STORIES.md`
3. Extract ALL acceptance criteria
4. Note dependencies
5. Cross-reference spec file against user story — must be consistent

> [!CAUTION]
> Phase 1 checkpoint will **BLOCK** if `docs/requirements/{REQ-ID}.md` does not exist.

### Step 1.3: Audit Codebase (MANDATORY)

**Actions** (execute ALL):
1. Map affected files: `grep -r "{REQ-ID}" .` or `find`
2. Trace imports/exports
3. Document technical debt
4. Identify existing test files

### Step 1.4: Gap Analysis (MANDATORY)

**Actions** (execute ALL):
1. Document security gaps
2. List RLS policies needed
3. Map data entry points
4. Assess attack surface

### Step 1.5: Design Proposal (MANDATORY)

**Actions** (execute ALL):
1. Define schemas/tables
2. Specify API endpoints
3. Define queue topology (if applicable)
4. **WAIT for user approval** before Phase 2

### Step 1.6: Scope Sanity Check (MANDATORY — BLOCKING GATE)

> [!CAUTION]
> **EXECUTE:** Read `.agent/workflows/scope-sanity-check.md` and follow all steps.

### ⛔ PHASE 1 CHECKPOINT (MANDATORY)

```bash
npm run checkpoint:sign-off -- --req {REQ-ID} --sign-off 1 --agent product-manager --workflow implement-req
ls -la .agent/checkpoints/{REQ-ID}/phase1_anchoring.json
```

> [!CAUTION]
> **STOP**: Do NOT proceed to Phase 2 until user approves design, Scope Sanity Check passes, AND checkpoint exists.

---

## Phase 2: Test-Driven Setup

### Step 2.1: Create Feature Branch (MANDATORY)

```bash
git checkout main
git pull origin main
git checkout -b task/{REQ-ID}-{short-description}
```

### Step 2.2: Draft Baseline Tests (MANDATORY)

**Location**: `backend/tests/{layer}/req-{id}.test.ts`
**Template**: See `@[skills/tdd-workflow]` Section 11

**Actions** (execute ALL):
1. Write one test per acceptance criterion
2. Use AAA pattern (Arrange, Act, Assert)
3. Include edge cases

### Step 2.3: Establish Failing Baseline (MANDATORY)

```bash
npm test -- --grep "{REQ-ID}"
```

**Expected**: Tests MUST fail. If they pass, fix the tests.

### ⛔ PHASE 2 CHECKPOINT (MANDATORY)

```bash
npm run checkpoint:sign-off -- --req {REQ-ID} --sign-off 2 --agent test-engineer --workflow implement-req
ls -la .agent/checkpoints/{REQ-ID}/phase2_tdd_setup.json
```

> [!CAUTION]
> **STOP**: Do NOT proceed until tests FAIL (scientific method).

---

## Phase 3: Implementation & Hardening

### Step 3.1: Implement Core Logic (MANDATORY)

**Order**: 1. Database schemas/migrations → 2. Core business logic → 3. API endpoints → 4. Integration

**Rules**: TypeScript strict mode, no `any`, NodeNext ESM

### Step 3.2: Security Hardening (MANDATORY)

**Actions** (execute ALL):
1. Add RLS policies - See `@[skills/security-hardener]` RLS Template
2. Validate inputs at boundaries
3. Apply censor/redaction for PII
4. Add rate limiting if applicable

### Step 3.3: Update Infrastructure (MANDATORY if needed)

1. `docker-compose.yml` - new services/volumes
2. `.github/workflows/ci.yml` - new test jobs
3. `.env.example` - new vars

### Step 3.3b: Frontend Performance & Code Quality (MANDATORY if frontend modified — BLOCKING GATE)

> [!CAUTION]
> **BLOCKING GATE**: All frontend code changes must pass the Performance & Code Quality Gate.
> Enforced by `frontend_perf_gate.py`. Violations ⛔ BLOCK this checkpoint.

**Actions** (execute ALL if `frontend/src/**` modified):
1. Run the performance gate:
```bash
python3 .agent/scripts/frontend_perf_gate.py . --req {REQ-ID}
```
2. If CRITICAL violations found → fix them before proceeding
3. Profile modified components for unnecessary re-renders
4. Audit space-time complexity of all new/modified functions
5. Enforce 200-line component limit — refactor monoliths into sub-components
6. Extract duplicated JSX patterns into shared components or hooks

### Step 3.4: Traceability Annotations (MANDATORY — BLOCKING)

> [!CAUTION]
> **EXECUTE:** Read `.agent/workflows/traceability-gate.md` **Part A** and follow all steps.

### Step 3.5: Functional Completeness Disclosure (MANDATORY — HALT)

> [!CAUTION]
> **EXECUTE:** Read `.agent/workflows/completeness-disclosure.md` and follow all steps.

### ⛔ PHASE 3 CHECKPOINT (MANDATORY)

```bash
npm run checkpoint:sign-off -- --req {REQ-ID} --sign-off 3 --agent backend-specialist --workflow implement-req
ls -la .agent/checkpoints/{REQ-ID}/phase3_implementation.json
```

---

## Phase 4: Validation

### Step 4.1: Achieve Green Run (MANDATORY — BLOCKING GATE)

> [!CAUTION]
> **HARD GATE**: Run FULL test suite — MUST pass with 0 failures. Phase 4 checkpoint BLOCKED until this passes.

```bash
cd backend && npm test 2>&1 | tail -20
```

If frontend modified:
```bash
cd frontend && npm test -- --run 2>&1 | tail -20
```

**Required**: BOTH suites must show `0 failed`. Any failure = ⛔ BLOCKED.

### Step 4.2: Physical DB Verification (MANDATORY)

**Commands**: See `@[skills/substrate-audit]` Sections 2-4. Show output for schema, RLS, and role checks.

### Step 4.3: Hardware Budget Check (MANDATORY)

```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

**VRAM must be < 5.7GB on DEV tier.**

### Step 4.4: IDE Problems & Lint Verification (MANDATORY — BLOCKING GATE)

> [!CAUTION]
> **HARD GATE**: ALL TypeScript errors and lint warnings MUST be resolved. Zero tolerance.

```bash
cd backend && npx tsc --noEmit 2>&1 | tail -10
cd frontend && npx tsc --noEmit 2>&1 | tail -10   # if frontend modified
```

### Step 4.5: Frontend Visual Verification (MANDATORY if frontend modified — BLOCKING GATE)

> [!CAUTION]
> **EXECUTE:** Read `.agent/workflows/frontend-browser-gate.md` and follow all steps.
> If `frontend/src/**` files were modified, this gate is MANDATORY. Skipping = ⛔ BLOCKED.
> Enforced by `frontend_visual_gate.py` — no screenshots = no Phase 4 sign-off.

```bash
python3 .agent/scripts/frontend_visual_gate.py . --req {REQ-ID}
```

### Step 4.6: Traceability Audit (MANDATORY — BLOCKING GATE)

> [!CAUTION]
> **EXECUTE:** Read `.agent/workflows/traceability-gate.md` **Parts B and C** and follow all steps.

```bash
bash scripts/audit-req-coverage.sh /tmp/audit-{REQ-ID}.md
```

> ⛔ BLOCKED if health < 100%.

### Step 4.7: Trigger Demonstration (MANDATORY — BLOCKING)

> [!CAUTION]
> **EXECUTE:** Read `.agent/workflows/trigger-demonstration.md` and follow all steps.

### ⛔ PHASE 4 CHECKPOINT (MANDATORY)

> [!CAUTION]
> **PRE-CONDITION**: Step 4.1 green run MUST be shown above. If any test failed, this checkpoint is INVALID.

```bash
npm run checkpoint:sign-off -- --req {REQ-ID} --sign-off 4 --agent test-engineer --workflow implement-req
ls -la .agent/checkpoints/{REQ-ID}/phase4_validation.json
```

---

## Phase 5: Merge & Cleanup

### ⛔ PREREQUISITE CHECK (MANDATORY)

```bash
npm run checkpoint:validate -- --req {REQ-ID} --validate-phase 4
gh auth status
```

### Step 5.1: Atomic Commits (MANDATORY)

**Pattern**: sql → logic → tests. See `@[skills/deployment-procedures]` Section 3.

### Step 5.2: Documentation Sync (MANDATORY — CI-ENFORCED)

> [!CAUTION]
> **EXECUTE:** Read `.agent/workflows/doc-sync-gate.md` and follow all steps.

CI gates enforce that **EXECUTION-PLAN.md** (`execution_plan_gate.py`) and **CAPABILITIES.md** (`capabilities_gate.py`) are updated in the PR diff. Pre-push hook also blocks locally. Merge is impossible without these updates.

### Step 5.3: Spec Exhaustion & Residue Spawning (MANDATORY)

> [!CAUTION]
> **EXECUTE:** Read `.agent/workflows/spec-exhaustion.md` and follow all steps.

### Step 5.4: Pre-Push Test Verification (MANDATORY — BLOCKING GATE)

```bash
cd backend && npm test 2>&1 | tail -5
cd frontend && npm test -- --run 2>&1 | tail -5  # if frontend modified
```

Any failure = ⛔ BLOCKED.

### Step 5.5: Push & Create PR (MANDATORY — CI-ENFORCED)

**Extract issue number** from `docs/requirements/{REQ-ID}.md` → `**GitHub Issue:** #NNN`.

```bash
git push origin task/{REQ-ID}-{description}
gh pr create --base main --title "[{REQ-ID}] {Name}" --body "Implements {REQ-ID}. Closes #{ISSUE-NUM}"
```

> [!CAUTION]
> PR body MUST contain `Closes #NNN`. Enforced by `issue_link_gate` CI job — merge blocked without it. On merge, GitHub auto-closes the linked issue.

**Verify PR created:**
```bash
gh pr list --head task/{REQ-ID}-{description} --json number,title,state
```

### Step 5.6: CI & Merge (MANDATORY — BLOCKING GATE)

> [!CAUTION]
> **EXECUTE:** Read `.agent/workflows/ci-merge-protocol.md` and follow all steps. NEVER merge without ALL CI checks green.

### Step 5.7: Post-Merge Cleanup (MANDATORY)

```bash
git checkout main && git pull origin main
```

### ⛔ PHASE 5 CHECKPOINT (MANDATORY)

```bash
npm run checkpoint:sign-off -- --req {REQ-ID} --sign-off 5 --agent devops-engineer --workflow implement-req
npm run checkpoint:validate-all -- {REQ-ID}
ls -la .agent/checkpoints/{REQ-ID}/
```

**Expected**: All 5 checkpoint files present.

---

## Violation Handling

| Violation | Response |
|-----------|----------|
| Checkpoint missing | ⛔ BLOCKED - create checkpoint before proceeding |
| Tests still failing | ⛔ BLOCKED - fix implementation |
| VRAM exceeded | ⛔ BLOCKED - optimize or Sovereign Override |
| Step skipped | ⛔ BLOCKED - go back and execute step |
| No output shown | ⛔ BLOCKED - re-run command and show output |

---