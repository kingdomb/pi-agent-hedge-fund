# Completeness Disclosure: REQ-L2-21
**Generated:** 2026-04-11
**Agent:** backend-specialist

## Fully Built (✅)
- **Split-screen UI**: Agent Creation UI presents Concierge Chat (Left) and Live Preview Form (Right) — already working from prior implementation
- **Tool-calling extraction**: Concierge LLM calls `update_agent_draft` with structured JSON to populate 4 form fields (role, goals, capabilities, personality) + systemRole
- **Live visual updates**: Draft form updates in real-time as LLM extracts variables via tool calls; bidirectional sync sends updated draft back to LLM on each turn
- **Manual override**: All 4 form fields remain visible and editable; user-typed changes are injected into next LLM system prompt with "do not re-ask" directive
- **Compile button**: "Finalize & Compile Profile" button calls existing `/api/interview/compile` → `PromptCompiler.compile()` → `app.agents` INSERT
- **Expert system prompt**: Multi-phase discovery interview (Discovery → Clarification → Gap Detection → Validation) replaces generic 8-line prompt
- **systemRole extraction**: LLM can infer and set `systemRole` (worker/specialist/sentinel) via tool call; validated against enum before merge; maps to `app.agents.role` column at compile time
- **SystemRoleSelector UI**: Full card-based selector in right-hand form; wired to `draft.systemRole`; required before compile
- **Sliding window**: Last 10 messages sent to LLM; currentDraft JSON injected fresh into system prompt every turn to prevent context amnesia
- **Template-aware greeting**: Dynamic opening message references selected template name/domain; different message for custom vs. template agents
- **Suggestion chips**: 3 clickable conversation starters (template-specific for known templates, universal for custom); pre-fill chat input on click
- **Progress indicator**: 4-dot indicator with tooltips showing which profile fields are populated + N/4 counter
- **Contextual typing indicator**: Phase-aware text ("Analyzing your description...", "Extracting details...", "Almost there — checking for gaps...", "Reviewing your agent profile...")
- **Anti-AC: interview_sessions preserved**: Table and all existing architecture unchanged
- **Anti-AC: form fields always visible**: Right-hand form visible at all times during chat
- **Anti-AC: no auto-compile**: Compile only triggered by explicit button click

## Stubbed / Mocked (⚠️)
- None

## Not Built (❌)
- None

## Missing Delivery Surfaces
- [x] API route exists? YES — `/api/interview/chat`, `/api/interview/compile`, `/api/interview/start`
- [x] CLI command exists? N/A — no CLI surface required
- [x] UI integration exists? YES — `InterviewWizard.tsx` with `SystemRoleSelector.tsx`

## Verdict
- **Functional:** YES
- **Stub count:** 0 items
- **Orphaned code:** NO
