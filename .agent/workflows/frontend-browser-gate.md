---
description: Mandatory browser-based visual verification gate for implement-req. Enforces browser_subagent usage, auth handoff protocol, and screenshot capture for any frontend/src change. Used by implement-req Step 4.5.
---

# Frontend Browser Visual Verification Gate

> [!CAUTION]
> **HARD GATE**: If `frontend/src/**` files were modified, you MUST open a browser and visually verify the changes. Phase 4 checkpoint sign-off is BLOCKED without screenshot/recording evidence. Enforced by `frontend_visual_gate.py`.

---

## Purpose

This gate forces the implementing agent to visually verify all UI changes in a real browser before sign-off. It eliminates "blind" frontend implementations where code is committed without ever seeing what it looks like.

---

## Step 1: Detect Frontend Changes (MANDATORY)

**Actions:**
1. Check git diff for `frontend/src/**` changes
2. If no frontend files modified → **SKIP** this gate entirely
3. If frontend files modified → proceed to Step 2

```bash
git diff --name-only main -- frontend/src/ | head -20
```

---

## Step 2: Start Browser Verification (MANDATORY)

**Tool:** You MUST use `browser_subagent` — NOT headless Playwright.

> [!IMPORTANT]
> The UI is served by the `ai_os_ui` Docker container at `http://localhost:3000`. Do NOT run `npm run dev`. Navigate directly to the Docker-served URL.

**Actions:**
1. Launch `browser_subagent` with a task to navigate to `http://localhost:3000`
2. Wait for `networkidle` state
3. Observe the initial page state

---

## Step 3: Auth Handoff Protocol (MANDATORY — HALT)

> [!CAUTION]
> **⛔ ABSOLUTE RULE: You MUST NOT attempt to type credentials or interact with login/MFA forms.** You will fail. This is a known limitation.

**Detection:** If any of the following are visible, you are at an auth wall:
- Login form (username/password fields)
- MFA/2FA prompt (code input, authenticator screen)
- SSO redirect page
- "Session expired" or "Unauthorized" message

**HALT Procedure:**
1. **STOP** all browser interaction immediately
2. **Save the `SubagentId`** from the current browser_subagent invocation
3. **Present this exact message to the user:**

```
⛔ AUTH HANDOFF REQUIRED

I've opened the browser to http://localhost:3000. The page requires authentication.
Please complete login and MFA in the browser, then type "ready" so I can continue verification.

I will NOT interact with auth forms — this is your responsibility.
```

4. **WAIT** for user to respond with "ready", "done", "continue", or equivalent
5. **Resume** the browser session using `ReusedSubagentId` with the saved ID

**If user does not respond or says "skip":**
- Gate defaults to ⛔ BLOCKED — no screenshot = no Phase 4 sign-off

---

## Step 4: Visual Verification (MANDATORY)

**After auth is complete (or if no auth was needed):**

1. **Navigate** to the page(s) affected by the code changes
2. **Capture screenshots** of the modified UI elements
3. **Visual review** — verify against the spec/design commitment:
   - Does the layout match the intended design?
   - Are interactive elements responsive (hover, click)?
   - Is the content correctly rendered?
   - Are there any visual regressions?

---

## Step 5: Save Evidence (MANDATORY)

**Save all screenshots/recordings to:**
```
.agent/checkpoints/{REQ-ID}/
```

**Accepted evidence formats:** `.png`, `.jpg`, `.jpeg`, `.webp`, `.webm`, `.mp4`, `.gif`

**Naming convention:**
- `ui_verification_<page-name>.png`
- `ui_verification_<component-name>.png`
- `browser_recording.webp` (auto-saved by browser_subagent)

---

## Step 6: Run Enforcement Script (BLOCKING)

```bash
python3 .agent/scripts/frontend_visual_gate.py . --req {REQ-ID}
```

> [!CAUTION]
> **HARD GATE**: This script checks that visual artifacts exist in the checkpoint directory. If it fails → ⛔ BLOCKED. Phase 4 checkpoint sign-off will be rejected.

---

## ReusedSubagentId Mechanism (Reference)

When resuming after auth handoff, the `browser_subagent` tool accepts a `ReusedSubagentId` parameter. This resumes the browser session from the exact state where it was paused:

```
# First invocation (navigates to app, hits auth wall)
browser_subagent → returns SubagentId: "abc123" → HALT for auth

# User completes auth and says "ready"

# Second invocation (resumes where it left off)
browser_subagent(ReusedSubagentId: "abc123") → continues verification
```

This preserves:
- The same browser window and tab
- The authenticated session (cookies, tokens)
- The DOM state at the point of pause

---

## Violation Handling

| Violation | Response |
|-----------|----------|
| No frontend changes | ✅ Gate skipped |
| Frontend changed, no screenshots | ⛔ BLOCKED — open browser and capture |
| Agent attempted auth | ⛔ BLOCKED — must use handoff protocol |
| `frontend_visual_gate.py` fails | ⛔ BLOCKED — save evidence, re-run |
| User declines auth | ⛔ BLOCKED — cannot verify, cannot sign-off |
