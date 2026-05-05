---
description: Traceability gate for implement-req. Enforces @REQ annotations, audit-exclusions.json classification, and 100% audit health. Includes Stop-the-Line mandate. Used by implement-req Steps 3.4 and 4.5.
---

# Traceability Gate Protocol

> Used by `/implement-req` Steps 3.4 (Annotations) and 4.5 (Audit).
> This gate ensures every REQ implementation maintains 100% audit health.

---

## Part A: Traceability Annotations (Step 3.4)

> [!CAUTION]
> **HARD GATE**: Every file modified for the current REQ MUST have an `@REQ:` annotation at the top. The Part B audit gate will reject your PR if any annotation is missing.

### Annotation Format

**Source files** (TypeScript/JS):
```typescript
// @REQ: {REQ-ID} - {Short Description}
```

**YAML/Docker files**:
```yaml
# @REQ: {REQ-ID} - {Short Description}
```

**SQL files**:
```sql
-- @REQ: {REQ-ID} - {Short Description}
```

**Test files** (MUST match the REQ being tested):
```typescript
// @REQ: {REQ-ID} - {Short Description}
```

### The "Multiple REQ" Override Rule

If the file **already contains** an `@REQ:` annotation at the top, evaluate the status of the existing REQs:

- **Append (Default):** If the new REQ is being added alongside the existing functionality, APPEND the new REQ-ID:
  ```typescript
  // @REQ: REQ-L1-02 - Disposable Pixels / GenUI
  // @REQ: REQ-SEC-05 - Content Security Policy
  ```

- **Replace/Scrub:** If the new REQ explicitly **deprecates**, **overwrites**, or **removes** the logic of the old REQ, you MUST **REMOVE** the dead REQ-ID from the annotation string to prevent false positives in the audit scanner.

### Non-Testable REQ Classification

If this REQ is **NOT testable** (config, CI pipeline, docs-only, meta-requirement), you MUST classify it by adding an entry to `docs/requirements/audit-exclusions.json`:

```json
"{REQ-ID}": { "tag": "{TAG}", "reason": "{Why this REQ cannot be unit tested}" }
```

**Valid tags:**

| Tag | When to Use |
|-----|-------------|
| `META` | Meta-requirement (references other REQs, no direct code) |
| `SOP` | Standard operating procedure (process, not code) |
| `DOC-ONLY` | Documentation-only requirement |
| `INFRA` | Infrastructure config (docker-compose, CI pipelines) |
| `OPS` | Operations scripts (no unit test possible) |

> [!CAUTION]
> **DO NOT** edit `scripts/audit-req-coverage.sh` to add exclusions. The script reads from `audit-exclusions.json` dynamically. Editing the bash script directly is a **BLOCKING violation**.

---

## Part B: Traceability Audit (Step 4.5)

> [!CAUTION]
> **HARD GATE**: The audit script MUST return **100% HEALTH** before the Phase 4 checkpoint can be signed off.

**Run the audit and SHOW OUTPUT:**

```bash
bash scripts/audit-req-coverage.sh /tmp/audit-{REQ-ID}.md
```

**Required output:**
- `UNVERIFIED: 0`
- `GHOST: 0`
- `ORPHAN: 0`
- `HEALTH: 100%`

**If health < 100%:**
1. Check which REQs are UNVERIFIED, GHOST, or ORPHAN
2. Add missing `@REQ:` annotations to code/test files (Part A)
3. OR classify non-testable REQs in `docs/requirements/audit-exclusions.json`
4. Re-run until 100%

> [!CAUTION]
> ⛔ BLOCKED if health < 100%. **You may not proceed to Phase 4 checkpoint or open a PR.**

---

## Part C: The "Stop the Line" Mandate

> [!CAUTION]
> **GLOBAL LOCKOUT — NO EXCEPTIONS.**
>
> If the global test suite or audit script fails for **ANY reason** — even if the failing test belongs to a completely different Layer or is unrelated to the REQ you are currently implementing — you are **explicitly authorized and MANDATED** to pause your current task. Your new primary objective is to debug the failing test, fix the underlying code, and restore the project to 100% health.
>
> You may not bypass this or open a PR until the **entire project is green**.
>
> **This overrides "out of scope" reasoning.** If a test is red, the project is broken, and no PR can merge broken code. Fix it first.

---
