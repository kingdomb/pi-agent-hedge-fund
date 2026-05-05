# REQ-INF-19: Database Migration System & Schema Baselining

## User Story

### ✨ REQ-INF-19: Database Migration System & Schema Baselining
**Status:** ✨ NEW

**As a** DevOps Engineer and Platform Architect
**I want to** replace the destructive `CREATE TABLE IF NOT EXISTS` init scripts with a version-controlled migration system, baseline the live schema as Migration 001, and standardize all primary keys to UUID
**So that** we can evolve the database schema without data loss, enable multi-tenant scalability, and maintain a single source of truth for schema state.

**Acceptance Criteria:**
- [ ] Full ERD of the running database (20 tables, 5 schemas) committed to `docs/architecture/`
- [ ] Migration tool selected and integrated (TypeScript/Postgres compatible, e.g. `node-pg-migrate` or `dbmate`)
- [ ] Migration 001 (baseline) captures the complete live schema as-is (pg_dump --schema-only)
- [ ] Migration 002 converts all SERIAL→UUID PKs with data-preserving multi-step ALTER (add column → populate → update FKs → drop old → rename)
- [ ] All FK relationships preserved during UUID migration (especially Org 0 → Tenant lineage)
- [ ] Complex types handled: JSONB, `vector(768)` embeddings, ARRAY columns
- [ ] `pgvector` extension creation managed by migrations
- [ ] Docker entrypoint updated to run migrations instead of raw `.sql` init files
- [ ] Schema integrity verified automatically on startup
- [ ] All 14 existing `backend/db/*.sql` files archived or removed after migration captures their state
- [ ] Zero data loss on existing tables (`users`, `organizations`, `agents`, `tasks`, `memories`, etc.)

**Dependencies:** REQ-INF-2 (DB Layer), REQ-SEC-03 (Dual-Connection Architecture)
**Notes:**
- 10 tables use SERIAL IDs: `organizations`, `agents`, `tasks`, `memories`, `audit_logs`, `api_keys`, `agent_procedures`, `evaluation_results`, `token_ledger`, plus `system_settings`
- 10 tables already use UUID: `users`, `auth_policies`, `auth_audit_log`, `recovery_codes`, `agent_templates`, `artifacts`, `heuristics`, `playbook`, `trajectory_buffer`, `vectors`
- 5 schemas in use: `public`, `app`, `ace`, `governance`, `usage_metrics`
- Current SQL files (00-13) may not match live DB state (schema drift suspected)

---

## Discovery Summary

### Live Database State (20 tables, 5 schemas)

| Schema | Table | PK Type | Notes |
|--------|-------|---------|-------|
| `app` | `organizations` | SERIAL INT | **Needs UUID** — root FK for most tables |
| `app` | `agents` | SERIAL INT | **Needs UUID** — FK to organizations |
| `app` | `tasks` | SERIAL INT | **Needs UUID** — FK to organizations, agents |
| `app` | `memories` | SERIAL INT | **Needs UUID** — has vector(768) column |
| `app` | `audit_logs` | SERIAL INT | **Needs UUID** — FK to organizations, agents |
| `app` | `api_keys` | SERIAL INT | **Needs UUID** — FK to organizations |
| `app` | `agent_procedures` | SERIAL INT | **Needs UUID** — has vector(768) + ARRAY |
| `app` | `evaluation_results` | SERIAL INT | **Needs UUID** — FK to organizations, agents, tasks |
| `app` | `users` | UUID | ✅ Already correct |
| `app` | `auth_policies` | UUID | ✅ Already correct |
| `app` | `auth_audit_log` | UUID | ✅ Already correct |
| `app` | `recovery_codes` | UUID | ✅ Already correct |
| `app` | `agent_templates` | UUID | ✅ Already correct |
| `app` | `artifacts` | UUID | ✅ Already correct |
| `ace` | `heuristics` | UUID | ✅ Already correct |
| `ace` | `playbook` | UUID | ✅ Already correct |
| `ace` | `trajectory_buffer` | UUID | ✅ Already correct |
| `governance` | `vectors` | UUID | ✅ Already correct |
| `usage_metrics` | `token_ledger` | BIGINT | **Needs UUID** — FK to org_id (INT) |
| `public` | `system_settings` | TEXT (key) | ✅ No change needed (KV store) |

### Effort Estimate
- **T-Shirt:** L (Large)
- **MoSCoW:** MUST HAVE
- **Phase:** Phase K (Pilot prerequisite)

### Ledger Entry
`| **REQ-INF-19** | **Database Migration System & Schema Baselining** [✨ NEW] | ✨ NEW | Replace destructive init scripts with version-controlled migrations. Baseline live schema (20 tables, 5 schemas). Convert SERIAL→UUID. ERD committed to docs/architecture/. |`
