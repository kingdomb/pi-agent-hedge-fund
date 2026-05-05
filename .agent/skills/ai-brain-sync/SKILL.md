---
name: ai-brain-sync
description: Manages the connection between the Node.js backend and the Python ai-os-brain. Use when handling vLLM KV cache saturation, 429 Too Many Requests errors, or inference latency issues.
---

# AI Brain Sync Skill

This skill governs the interaction between Layer 3 (Nervous System) and Layer 5 (The Brain).

## 🧠 KV Cache Management
- **Monitoring**: Before heavy inference tasks, check the vLLM cache state via the brain's health endpoint.
- **Saturation Protocol**: If the KV cache is >90% utilized, implement "Serial Vision Paging" (REQ-L5-07) to offload non-essential tensors.

## 🚦 429 "Too Many Requests" Logic (REQ-INF-3)
When an inference request returns a 429 status code:
1. **Identify the Queue**: Check if the request is from `high_priority` (Chat) or `background` (ACE).
2. **Adaptive Backoff**:
   - `high_priority`: Retry once with a 500ms jittered delay.
   - `background`: Move task back to the `Redis` queue with an exponential backoff (starting at 5s).
3. **Throttling**: Signal the `Adaptive Queue Throttling` logic (REQ-L3.5-05) to reduce the `MAX_QL` until the brain clears the 429 state.

## 🚫 Constraints
- Never bypass the `ai.ts` router when communicating with the brain.
- Ensure all brain-sync logs are stripped of PII via the `censor` utility.