---
name: vram-budget-managent
description: Enforces tier-based VRAM constraints. DEV=5.7GB (local GPU), QA/PROD=80GB (RunPod A100). Use when running tests or configuring AI workers.
---

# VRAM Budget Management Skill

Enforces hardware memory constraints based on environment tier.

## Tier-Based VRAM Budgets

| AI_TIER | GPU | VRAM Budget | Swap Required |
|---------|-----|-------------|---------------|
| **DEV** | Local (GTX 1660 Ti) | 5.7GB | YES |
| **QA** | RunPod A100 | 80GB | NO |
| **PROD** | RunPod A100 | 80GB | NO |

> **Check Tier**: `echo $AI_TIER` or check `backend/.env`

## When to Use
* Before running AI integration tests
* When configuring BullMQ concurrency settings
* If experiencing GPU Out of Memory (OOM) crashes
* During the "Hardware Budget Verification" phase

## Phase 1: Baseline Assessment

1. **Identify Tier**: Check `AI_TIER` env var (DEV, QA, or PROD)
2. **Check VRAM**: 
   * DEV (local): `nvidia-smi --query-gpu=memory.used,memory.total --format=csv`
   * QA/PROD: Models run on remote RunPod, no local check needed
3. **Calculate Headroom** (DEV only):
   * Budget: 5.7GB
   * Minimum headroom: 500MB
   * If headroom < 500MB, do not proceed

## Phase 2: Execution & Monitoring

1. **Run Tests**: Execute test suite or worker process
2. **Monitor** (DEV only): Watch for OOM errors
3. **Capture Peak**: Log peak VRAM consumption

## Phase 3: Optimization

**DEV tier only** (QA/PROD have 80GB, rarely need optimization):

1. If peak approaches 5.7GB limit:
   * Lower BullMQ concurrency
   * Enable model swapping (`/admin/unload` before `/admin/load`)
2. Re-run and verify stability

## Success Criteria

| Tier | Criteria |
|------|----------|
| DEV | Peak VRAM < 5.7GB, no OOM |
| QA/PROD | All models load successfully on RunPod |