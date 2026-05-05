---
description: Requirement spec file template for create-req Step 2.5. The single source of truth for implementation, read by implement-req Phase 1 and deleted after implementation.
---

# Requirement Spec File Template

**Path:** `docs/requirements/{REQ-ID}.md`

This file is the **single source of truth** for implementation. The `/implement-req` workflow reads it in Phase 1 as the technical blueprint. It is **deleted** after implementation is complete.

## Template (use exactly)

```markdown
# Requirement: {REQ-ID}

## Metadata
- **ID:** {REQ-ID}
- **Name:** {Name}
- **Status:** DRAFT
- **Priority:** {MUST|SHOULD|COULD}
- **Effort:** {XS|S|M|L|XL}
- **Layer:** {Layer number and name}
- **Owner:** {Primary agent}
- **GitHub Issue:** #{issue_number}

## Description
{What this requirement does and why it exists.}

## User Stories
- **As a** {Persona}
- **I want to** {Action}
- **So that** {Benefit}

## Acceptance Criteria
- [ ] {Must match the criteria in ARCH-USER-STORIES.md}

## Anti-Acceptance Criteria (Must Never)
- [ ] The system MUST NEVER {negative boundary}
- [ ] The system MUST NEVER {negative boundary}

## Technical Implementation
**Schema:**
{SQL CREATE TABLE statements, ALTER TABLE, RLS policies}

**API Endpoints:**
{Route definitions, request/response shapes}

**Components:**
{Frontend components, services, utilities}

## Delivery Surfaces (MANDATORY — Step 2.5b)
| # | Perspective | Applicable? | Justification |
|---|-------------|-------------|---------------|
| 1 | Tenant Self-Service | YES/NO | {Why or why not} |
| 2 | Org 0 Self-Management | YES/NO | {Why or why not} |
| 3 | Org 0 → Global Policy | YES/NO | {Why or why not} |
| 4 | Org 0 → Per-Tenant Override | YES/NO | {Why or why not} |
| 5 | SDK Exposure | YES/NO | {Why or why not} |

{If any YES: delivery surface acceptance criteria here or reference sub-REQ}
{If all NO: "Backend-only — no user-facing controls or SDK hooks required."}

## Sub-Requirements
{List any sub-REQs (e.g., {REQ-ID}b for UI). Use "PENDING" if not yet created.}
{If none: "None identified."}

**Dependencies:** {REQ-IDs this depends on}
**Source:** {Reference to ARCH-TENANT-LIFECYCLE.md section or other source}
```

> [!IMPORTANT]
> This file is **temporary**. It exists from creation through implementation. The `/implement-req` workflow deletes it in Phase 5 after the requirement is fully implemented and merged.
