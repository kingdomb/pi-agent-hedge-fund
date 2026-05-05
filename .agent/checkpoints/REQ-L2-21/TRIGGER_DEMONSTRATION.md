# Trigger Demonstration: REQ-L2-21
**Generated:** 2026-04-11

## Delivery Surfaces

| Surface | Required? | Implemented? | Trigger Command/Path |
|---------|-----------|--------------|----------------------|
| API     | YES       | YES          | `POST /api/interview/start`, `POST /api/interview/chat`, `POST /api/interview/compile` |
| CLI     | NO        | N/A          | N/A |
| UI      | YES       | YES          | Dashboard → Agent Marketplace → Select Template → "Create Agent" → InterviewWizard split-screen |
| Event   | NO        | N/A          | N/A |

## Trigger Output

### API Surface (backend test suite proves it):
```
✓ AC1: POST /api/interview/chat stores tool-called parameters via shallow merge (437 ms)
✓ AC2: POST /api/interview/compile takes frontend answers payload as source of truth (164 ms)
✓ AC3: POST /api/interview/chat extracts systemRole via tool call with enum validation (66 ms)
✓ AC4: POST /api/interview/chat includes template context in LLM system prompt (44 ms)
✓ AC5: POST /api/interview/chat handles empty draft gracefully (46 ms)
✓ AC6: POST /api/interview/chat applies sliding window but preserves draft state (45 ms)
```

### UI Surface:
1. User navigates to Dashboard → Agent Marketplace
2. Selects a template (e.g., "Sales Agent") or "Custom Agent"
3. Clicks "Create Agent" → InterviewWizard opens in split-screen mode
4. Left panel: Chat with Concierge (discovery interview, suggestion chips, contextual typing)
5. Right panel: Live form with Agent Name, SystemRoleSelector, Role, Goals, Capabilities, Personality
6. Progress dots (4) update as fields are populated
7. "Finalize & Compile Profile" button triggers compile when all fields + systemRole are set

## Verdict
- **Has usable trigger:** YES
- **Orphaned code:** NO
- **Missing surfaces:** NONE
