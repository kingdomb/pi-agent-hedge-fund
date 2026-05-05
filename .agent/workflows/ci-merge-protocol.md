---
description: CI validation and PR merge protocol. Polls CI status, enforces green checks, and merges via squash. Used by implement-req Step 5.4.
---

# CI & Merge Protocol (BLOCKING GATE)

> [!CAUTION]
> **NEVER merge a PR without confirming ALL CI checks are green.**
> Merging with failing CI is a P0 violation.

> [!IMPORTANT]
> **This repo is GitHub Free (private).** `--auto` merge is NOT available.
> Branch protection rules are NOT enforceable on this plan.
> Therefore, **the agent MUST manually enforce CI green status before merging.**
> **NEVER use `gh pr merge --auto`.** It will hang.
> **NEVER use `gh pr merge` without a PR number.** Always pass it explicitly.

## Step A — Wait for CI to complete (MANDATORY)

```bash
# Poll CI status until all checks complete (max 5 min)
for i in $(seq 1 10); do
  echo "🔄 Check attempt $i/10..."
  RESULT=$(gh pr checks {PR-NUMBER} 2>&1)
  echo "$RESULT"
  if echo "$RESULT" | grep -q "pending\|in_progress"; then
    echo "⏳ Checks still running, waiting 30s..."
    sleep 30
  else
    break
  fi
done
```

## Step B — Verify ALL checks passed (MANDATORY — BLOCKING)

```bash
gh pr checks {PR-NUMBER}
```

**⛔ DECISION GATE:**
- ✅ ALL checks show `pass` or `✓` → Proceed to Step C
- ❌ ANY check shows `fail` or `X` → **STOP. DO NOT MERGE.**
  - Investigate the failure
  - Fix the code on the feature branch
  - Push the fix and re-run from Step A
  - **NEVER bypass a failing check**

## Step C — Merge ONLY after green CI (MANDATORY)

```bash
gh pr merge {PR-NUMBER} --squash --delete-branch --body "Implements {REQ-ID}"
```

**After merge, update local main:**
```bash
git checkout main && git pull origin main
```
