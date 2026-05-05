---
name: substrate-audit
description: Performs "Physical Reality Checks" on the database substrate. Verifies RLS policies, table ownership, and schema isolation via direct docker exec commands. Use to validate that applied SQL changes are physically present and correct.
---

# Substrate Audit Skill

This skill prevents the agent from assuming SQL migrations were successful by enforcing "Physical Reality Checks." It mandates the use of direct CLI inspection to verify the actual state of the database infrastructure.

## When to use this skill
* After applying database migrations or schema changes.
* When validating security requirements (RLS, permissions).
* During the "Physical Check" phase of the implementation workflow.
* To verify schema isolation and table ownership.
* Whenever a "Gold Master" verification is required.

## Instructions

### 1. Identify the Target
Locate the running database container.
* *Common Command*: `docker ps | grep db` or `docker ps | grep postgres`

### 2. Verify Schema Isolation
Do not rely on code reviews. Check the live database to ensure schemas are isolated and permissions are correct.
* **Command**: `docker exec -it <container_id> psql -U <user> -d <dbname> -c "\dn+"`
* **Validation**: 
    * Ensure the specific requirement schemas exist.
    * Verify that the `owner` is the correct service role, not the superuser.

### 3. Verify Table Ownership & Permissions
Confirm that tables belong to the correct role and have strict access controls.
* **Command**: `docker exec -it <container_id> psql -U <user> -d <dbname> -c "\dt <schema>.*"`
* **Command**: `docker exec -it <container_id> psql -U <user> -d <dbname> -c "\z <schema>.<table_name>"`
* **Validation**:
    * **Owner**: Must match the specific service role (e.g., `app_owner`).
    * **Grants**: Must be least-privilege.

### 4. Verify RLS (Row-Level Security)
RLS must be enabled explicitly. A table without RLS is a critical vulnerability.
* **Command**: `docker exec -it <container_id> psql -U <user> -d <dbname> -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = '<schema>';"`
* **Validation**:
    * `rowsecurity` must be `true` for all sensitive tables.
    * If `rowsecurity` is `false`, the audit **FAILS**.
* **Policy Check**: Verify the actual logic of the policies.
    * **Command**: `docker exec -it <container_id> psql -U <user> -d <dbname> -c "select * from pg_policies where schemaname = '<schema>';"`

### 5. Pass/Fail Standard
* **PASS**: The CLI output strictly matches the architectural requirements and Security Mandates.
* **FAIL**: If any table lacks RLS, has incorrect ownership, or if the schema is missing. **Do not proceed** until fixed.