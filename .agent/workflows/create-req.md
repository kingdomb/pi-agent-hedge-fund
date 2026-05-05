---
description: 5-Phase Standard Operating Procedure for creating new requirements. ALL STEPS ARE MANDATORY. Checkpoint commands MUST be executed and output included.
---

# /create-req Workflow

$ARGUMENTS

---

> [!CAUTION]
> **ALL STEPS ARE MANDATORY**. You MUST execute every checkpoint command and include the output. Skipping ANY step is a BLOCKING violation. CI will reject PRs without complete checkpoint chains.

---

> **Agents:** P1: product-manager | P2: product-manager + project-planner | P3: orchestrator + all 5 board members | P4: board_scribe_release | P5: devops-engineer
>
> **Every phase begins with:** `npm run checkpoint:validate -- --req {REQ-ID} --validate-phase {N-1}`

---

## Phase 1: Discovery & Context Gathering

### Step 1.1: Understand the Request (MANDATORY)

**Actions** (execute ALL):
1. Parse issue description - extract core problem
2. Identify Who/What/Why
3. Check for duplicates in `ARCH-REQUIREMENTS-LEDGER.md`
4. Apply Socratic Gate - ASK if vague

### Step 1.2: Explore Codebase Impact (MANDATORY)

**Actions** (execute ALL):
1. Map affected files: `grep` or `find`
2. Identify dependencies
3. Assess complexity: Single-file, Multi-file, Cross-layer

### Step 1.3: Delivery Surface & Impact Radius Analysis (MANDATORY)

> [!CAUTION]
> **READ AND EXECUTE:** `.agent/workflows/scope-sanity-check.md` — evaluates delivery surfaces (CLI/API/UI), user context mapping, impact radius, and pattern reuse. Enforces sub-REQ creation for any surface flagged YES but scoped out.

**If gaps are detected** → Follow `.agent/workflows/scope-escalation-protocol.md`. HALT and present options to user.

### Step 1.4: Documentation Impact Analysis (MANDATORY)

> [!CAUTION]
> **READ AND EXECUTE:** `.agent/workflows/doc-impact-analysis.md` — scans full documentation scope, produces Doc Update Manifest, validates via 4-point verification gate. Phase 1 checkpoint is BLOCKED without all 4 checks passing.

### ⛔ PHASE 1 CHECKPOINT (MANDATORY)

```bash
npm run checkpoint:sign-off -- --req {REQ-ID} --sign-off 1 --agent product-manager
ls -la .agent/checkpoints/{REQ-ID}/phase1_discovery.json
```

> [!CAUTION]
> **STOP**: Do NOT proceed to Phase 2 until checkpoint file exists.

---

## Phase 2: Requirement & User Story Drafting

### ⛔ PREREQUISITE CHECK (MANDATORY)

```bash
npm run checkpoint:validate -- --req {REQ-ID} --validate-phase 1
```

### Step 2.1: Generate REQ ID (MANDATORY)

Assign layer prefix: `REQ-HW-*`, `REQ-INF-*`, `REQ-SEC-*`, `REQ-L1-*` through `REQ-L6-*`, `REQ-SDK-*`, `REQ-BILL-*`, `REQ-BUS-*`, `REQ-OPS-*`, `REQ-PROD-*`

Check ledger for next sequential ID.

### Step 2.2: Draft User Story (MANDATORY)

**Format** (use exactly):
```markdown
### [Status] REQ-ID: Name
**Status:** [🔨 BUILDABLE | 🚀 CLOUD READY | ✨ NEW]

**As a** [Persona]
**I want to** [Action]
**So that** [Benefit]

**Acceptance Criteria:**
- [ ] Criterion 1 (Must be behavior-driven, not structural)
- [ ] No core business logic may be stubbed or mocked in production execution.

**Completeness Definition:**
- What specific real-world value or behavior must this feature deliver to be considered "Functional"?

**Anti-Acceptance Criteria (Must Never):**
- [ ] The system MUST NEVER [negative boundary 1]
- [ ] The system MUST NEVER [negative boundary 2]

**Dependencies:** [REQ-IDs]
**Notes:** [Constraints]
```

### Step 2.3: Draft Ledger Entry (MANDATORY)

Format: `| **REQ-ID** | **Name** [✨ NEW] | ✨ NEW | Context. Notes. |`

### Step 2.4: Estimate Effort (MANDATORY)

- T-Shirt: XS, S, M, L, XL
- MoSCoW: MUST, SHOULD, COULD, WON'T
- Phase assignment

### Step 2.4b: Cloud/Prod Blocker Classification (MANDATORY)

> [!CAUTION]
> **READ AND EXECUTE:** `.agent/workflows/cloud-blocker-classification.md` — evaluates cloud dependencies (RunPod, Neon Pro, S3, Railway, Upstash) and applies granular per-resource blocker flags.

### Step 2.5: Create Requirement Spec File (MANDATORY)

> [!CAUTION]
> **READ AND EXECUTE:** `.agent/workflows/req-spec-template.md` — the spec is the single source of truth for implementation. Deleted after implementation.

**Path:** `docs/requirements/{REQ-ID}.md`

### Step 2.5b: UI Delivery Surface Evaluation (MANDATORY — BLOCKING)

> [!CAUTION]
> **HARD GATE**: Features without UI are invisible to users.

**Evaluate ALL FIVE perspectives:**

| # | Perspective | Question |
|---|-------------|----------|
| 1 | **Tenant Self-Service** | Does a Tenant Admin/User need to see/manage this? |
| 2 | **Org 0 Self-Management** | Does Org 0 need this for its own operations? |
| 3 | **Org 0 → Global Policy** | Does Org 0 set this system-wide? |
| 4 | **Org 0 → Per-Tenant Override** | Does Org 0 adjust this per-tenant? |
| 5 | **SDK Exposure** | Exposed via `@pi-agent/*` SDK? |

**If YES** → include in spec AC, or cross-reference existing sub-REQ, or ⛔ HALT to create sub-REQ.
**If all NO** → document justification in spec `## Delivery Surfaces`.

### Step 2.6: Testability Classification (MANDATORY)

Classifications: TESTABLE (default) | [META] | [SOP] | [DOC-ONLY] | [INFRA] | [OPS]
If NOT testable: add to `docs/requirements/audit-exclusions.json`

### ⛔ PHASE 2 CHECKPOINT (MANDATORY)

**Pre-condition — User Story Validation (BLOCKING):**

```bash
bash scripts/validate-user-story.sh {REQ-ID}
```

```bash
npm run checkpoint:sign-off -- --req {REQ-ID} --sign-off 2 --agent product-manager
ls -la .agent/checkpoints/{REQ-ID}/phase2_draft.json
```

---

## Phase 3: Board of Directors Review

> [!CAUTION]
> **READ AND EXECUTE:** `.agent/workflows/board-review-protocol.md` — records votes from all 5 board members (CSA, CISO, CAIO, VP Ops, Red Team), validates quorum (>75%), creates Phase 3 checkpoint.

---

## Phase 4: Documentation Finalization

### ⛔ PREREQUISITE CHECK (MANDATORY)

```bash
npm run checkpoint:validate -- --req {REQ-ID} --validate-phase 3
```

### Step 4.1: Verify Ledger Integrity (MANDATORY)

- Format validation
- Version alignment (v3.4.0)
- Cross-reference check (unique IDs)

### Step 4.2: Finalize User Story (MANDATORY)

- Style consistency
- Correct layer section
- Accurate status symbol

### ⛔ PHASE 4 CHECKPOINT (MANDATORY)

```bash
npm run checkpoint:sign-off -- --req {REQ-ID} --sign-off 4 --agent board_scribe_release
ls -la .agent/checkpoints/{REQ-ID}/phase4_finalization.json
```

---

## Phase 5: Registration & Integration

> [!CAUTION]
> **MANDATORY SUB-WORKFLOW.** You MUST read and execute every step in:
> `.agent/workflows/create-req-registration.md`
>
> This sub-workflow contains ALL Phase 5 steps: documentation updates (4 files including EXECUTION-PLAN.md Step 2), GitHub issue creation, GAP sync, and the Phase 5 checkpoint.
>
> **The Phase 5 checkpoint PROGRAMMATICALLY enforces:**
> - `REQ-LEDGER.md` contains `{REQ-ID}`
> - `REQ-USER-STORIES.md` contains `{REQ-ID}`
> - `GUIDE-EXECUTION-ORDER.md` contains `{REQ-ID}`
> - `EXECUTION-PLAN.md` Step 2 contains `/implement-req {REQ-ID}`
> - Spec file exists: `docs/requirements/{REQ-ID}.md`
> - GitHub issue exists with `{REQ-ID}` in title
> - Doc Scope Guard: no unauthorized doc edits
>
> **Skipping the sub-workflow is NOT possible — the checkpoint code will BLOCK.**
