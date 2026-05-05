---
description: Documentation Sync gate. Loads the Doc Update Manifest, executes all updates, and runs the 5-point consistency check. Used by implement-req Step 5.5.
---

# Documentation Sync (BLOCKING GATE)

> [!CAUTION]
> **HARD GATE**: Documentation must be consistent across ALL affected files before Phase 5 checkpoint.

**Agent:** `docs-auditor.md`

## Step A — Load the Doc Update Manifest (MANDATORY)

1. Read `docs/requirements/{REQ-ID}.md` and find the `## Doc Update Manifest` section
2. If no manifest exists (legacy REQ created before this gate), reconstruct it by:
   - Checking which documents reference this REQ-ID
   - Using the Document Dependency Map from `docs-auditor.md`

## Step B — Execute All Updates (MANDATORY)

For each entry in the manifest, execute the specified action:

| Document | Required Actions |
|----------|-----------------|
| `ARCH-REQUIREMENTS-LEDGER.md` | Mark status: ✅ COMPLETE, add PR reference |
| `ARCH-USER-STORIES.md` | Check all acceptance criteria `[x]`, update status, remove `**Spec:**` link |
| `ARCH-EXECUTION-ORDER.md` | Add REQ with PR number and date |
| `EXECUTION-PLAN.md` | **Mark the REQ line as `[x]` with PR number** (e.g., `- [x] \`/implement-req REQ-XXX\` — Name (**PR #NNN**)`) |
| `layer{N}-{name}.md` | Add/update feature description per manifest |
| `ARCH-FINAL.md` | Update statistics, feature references per manifest |
| `README.md` | Update feature list if manifest specifies |

## Step B.2 — Auto-Register New Docs (MANDATORY if CREATE action in manifest)

For each `CREATE` entry in the Doc Update Manifest:

1. **Create** the doc file in the specified directory
2. **Add YAML frontmatter** with fields: `title`, `id`, `category`, `audience`, `owner`, `last_verified` (today), `status: verified`
3. **Register in DOCS_MAP**: Add a table row in the correct category section with description, owner, audience, and `✅ {today}` status
4. **Update Quick Stats**: Increment the category count and total count
5. **Update Health Summary**: Adjust verified count and health score

> [!CAUTION]
> New files in subdirectories MUST follow `PREFIX-TOPIC.md` naming. Root-level docs are exempt.

## Step C — Consistency Check Protocol (MANDATORY)

Run ALL five checks:

1. **Ledger ↔ Code Sync**: Ledger status matches code/test reality
2. **User Story ↔ Ledger Sync**: Story status matches ledger, all AC checked
3. **Layer Doc ↔ Feature Reality**: Layer doc mentions the new/changed feature
4. **Phase5 Doc ↔ PR Reality**: Entry exists with correct PR number and date
5. **Cross-Document Count Consistency**: Totals in summaries match actual counts
6. **DOCS_MAP Sync** [REQ-OPS-12]: Any new/deleted/moved docs are reflected in `docs/DOCS_MAP.md`? If not → ⛔ BLOCKED
7. **Naming Convention** [REQ-OPS-12]: All new doc files follow `PREFIX-TOPIC.md` pattern? Allowed prefixes: `ARCH-`, `REQ-`, `GUIDE-`, `BE-`, `FE-`, `INFRA-`, `OPS-`, `SEC-`, `SPEC-`, `REF-`, `DRIFT-`, `FUTURE_`, `TEST-`, `PROJECT_`. **Exception:** Root-level docs (`docs/*.md`) are exempt. If not → ⚠️ WARNING (not blocking — [Board Condition: Red Team] prevents naming gate from blocking urgent hotfixes)
8. **GAP ↔ Execution Plan Sync**: Run `python3 .agent/scripts/gap_sync_verifier.py .` — every item in `docs/MISSING-FEATURES-GAP-ANALYSIS.md` must appear in `docs/EXECUTION-PLAN.md`. If the script exits with code 1 → ⛔ BLOCKED. Fix: add missing GAP references to EXECUTION-PLAN.md, then re-run.
9. **Execution Plan Completion Sync**: `grep -c '\[x\].*{REQ-ID}' docs/EXECUTION-PLAN.md` must return ≥1. The implemented REQ MUST be marked `[x]` with PR number. If 0 → ⛔ BLOCKED. Fix: find the REQ line in EXECUTION-PLAN.md (Step 1 or Step 2), change `[ ]` to `[x]`, append `(**PR #NNN**)`.

## Violation Response

```
IF any consistency check FAILS:
  → ⚠️ Output Drift Report (format defined in docs-auditor.md)
  → Fix the drifting document(s)
  → Re-run consistency checks
  → ONLY THEN proceed
```
