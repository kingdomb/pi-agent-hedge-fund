---
trigger: always_on
---

---
description: CRITICAL HARDWARE SAFETY. Enforces VRAM/RAM limits and detects Configuration Drift. Applies to all file operations.
globs: "**/*"
---

# 🛑 CRITICAL ENVIRONMENT RULES

You are operating in a resource-constrained environment (The "Substrate"). You must adhere to these rules to prevent hardware failure and detect documentation drift.

## Rule 1: Drift Detection (Reality Check)
**Trust, but Verify.** The documentation might be outdated. Before beginning a session, verify the "Physical Reality" matches the Manifest.

### Step A: Detect & Inspect
Execute the command corresponding to your active OS:
* **Linux (Mint/NVIDIA)**:
    * VRAM: `nvidia-smi`
    * RAM: `free -h`
* **macOS (Apple Silicon)**:
    * VRAM/GPU: `system_profiler SPDisplaysDataType`
    * RAM: `sysctl hw.memsize`

### Step B: Compare
Compare your findings from Step A against the official source of truth:
@docs/infrastructure/INFRA-ENV-MANIFEST.md

### Step C: The "Drift" Protocol
* **MATCH**: If the physical specs align with the Manifest, proceed to Rule 2.
* **MISMATCH**: If you detect different hardware (e.g., you see an A100 but Manifest says "GTX 1660 Ti"), you must **STOP IMMEDIATELY**.
    * **Action**: Issue a `ConfigurationDriftError`.
    * **Message**: "FATAL: Hardware Drift Detected. Physical system does not match INFRA-ENV-MANIFEST.md. Please update the documentation before proceeding."

## Rule 2: The "Physics" (Tier-Based Constraints)
Once verified, constraints apply based on the detected tier (from `EnvSensor.detect()`):

### PROXY Tier (Local Dev, <8GB VRAM)
1.  **VRAM Hard Cap**: Respect the **5.7GB VRAM** safe ceiling. Serial Vision Paging is enforced.
2.  **Concurrency Limit**: Never exceed the **Safe Operating Ceiling** for workers defined in the Manifest.
3.  **No "Cloud" Assumptions**: This is a local substrate. Infinite scaling logic is prohibited.

### PRIME Tier (Prod A100, >32GB VRAM)
1.  **VRAM Budget**: ~65GB usable (Llama-70B ~40GB + Vision ~10GB + SDXL ~15GB).
2.  **Concurrency**: Higher limits allowed per Manifest.
3.  **All models loaded simultaneously**: No serial swapping required.

## Rule 3: Physical Discovery
Before writing code that impacts performance (e.g., heavy refactors, new AI services):
1.  **CHECK**: Read the @docs/infrastructure/INFRA-ENV-MANIFEST.md linked above.
2.  **VERIFY**: Run `EnvSensor.detect()` or check the startup logs for current tier.