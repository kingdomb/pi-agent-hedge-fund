---
description: Cloud/Prod Blocker Classification gate for create-req. Evaluates cloud infrastructure dependencies and applies granular per-resource blocker flags. Used by create-req Step 2.4b.
---

# Cloud/Prod Blocker Classification

> [!CAUTION]
> **BLOCKING**: Every new REQ MUST be evaluated for cloud infrastructure dependencies at creation time. If ANY acceptance criterion requires cloud services that are not yet provisioned, the REQ MUST receive individual blocker flags for **each** required resource.

## Step 1: Evaluate Dependencies

Check each acceptance criterion against this resource matrix:

| Resource | Flag | Trigger Keywords | Example |
|----------|------|-----------------|---------|
| **RunPod A100** | `⛔ RunPod` | model inference, VRAM, CUDA, extraction, vLLM, steering vectors | REQ-INF-11 |
| **Neon Pro** | `⛔ Neon Pro` | PITR, branching, database backup, connection pooling, production DB | REQ-PROD-3 |
| **S3** | `⛔ S3` | backup to S3, encrypted dump, WAL archive, cloud storage | REQ-PROD-3 |
| **Railway** | `⛔ Railway` | backend deployment, cron jobs, production API, cloud hosting | REQ-INF-10 |
| **Upstash** | `⛔ Upstash` | Redis production, cache persistence, rate limiting (prod) | REQ-PROD-1 |

## Step 2: Classify

- If **ANY** cloud dependency → apply individual `⛔` flag(s) for each required resource
- If **NONE** → mark as `🔨 BUILDABLE` (can be implemented and verified locally)

**Format:** Concatenate all applicable flags. Example:
- Single dependency: `⛔ RunPod`
- Multiple dependencies: `⛔ Neon Pro ⛔ S3 ⛔ Railway`

## Step 3: Apply to ALL 6 Locations (NO EXCEPTIONS)

You MUST apply the blocker flag(s) to **every** location:

1. **Spec metadata** (`docs/requirements/{REQ-ID}.md`) — Phase line
2. **Ledger** (`docs/requirements/REQ-LEDGER.md`) — Row description
3. **User Story** (`docs/requirements/REQ-USER-STORIES.md`) — Status line
4. **Execution Order** (`docs/guides/GUIDE-EXECUTION-ORDER.md`) — Notes column
5. **Execution Plan** (`docs/EXECUTION-PLAN.md`) — Wave entry (in Step 5.3b)
6. **GitHub Issue** — Body references section (see below)

> [!CAUTION]
> **MANDATORY — DO NOT SKIP THE GITHUB ISSUE.** The GitHub issue MUST include the blocker flags in its body. If the issue already exists, update it with `gh issue edit`. If creating a new issue in Step 5.2, include the flags in the initial body. Example:
>
> ```bash
> # New issue — include flags in body
> gh issue create --body "... ⛔ Neon Pro ⛔ S3 ⛔ Railway — reason"
>
> # Existing issue — update body
> BODY=$(gh issue view {NUMBER} --json body -q '.body' | sed 's/old_tag/new_flags/') && gh issue edit {NUMBER} --body "$BODY"
> ```

> [!IMPORTANT]
> Do NOT wait for the user to ask "is this blocked?" — classify proactively and tag all 6 locations (including the GitHub issue) in a single pass. This gate exists because the user had to manually ask 3 times.
