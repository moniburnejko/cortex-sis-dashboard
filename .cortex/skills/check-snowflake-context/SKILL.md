---
name: check-snowflake-context
description: "verify the active Snowflake session context before starting work: role, warehouse, database, account, and whether the target schema objects exist. trigger after check-local-environment passes, or when the user asks to verify Snowflake context, check active role, or confirm schema objects are in place. do NOT use for local tooling checks (snow CLI, config.toml) - that is check-local-environment."
---

## steps

read the expected environment from AGENTS.md:
- `<role>` - expected active role
- `<warehouse>` - expected active warehouse
- `<database>` - expected active database
- `<schema>` - expected target schema
- `<stage>` - internal stage name (from source files section)

1. query the active session context:
   `snow sql -q "SELECT CURRENT_ACCOUNT(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()"`
   note all five values.

2. compare against the expected environment from AGENTS.md:
   - role must be `<role>`
   - warehouse must be `<warehouse>`
   - database must be `<database>`
   if any value does not match: set it explicitly before continuing:
   ```sql
   USE ROLE <role>;
   USE WAREHOUSE <warehouse>;
   USE DATABASE <database>;
   ```
   re-run the context query to confirm.

3. verify the target schema exists:
   `snow sql -q "SHOW SCHEMAS LIKE '<schema>' IN DATABASE <database>"`
   must return 1 row. if 0 rows: stop and tell the user the schema does not exist - it must be created before proceeding.

4. verify the internal stage exists:
   `snow sql -q "SHOW STAGES LIKE '<stage>' IN SCHEMA <database>.<schema>"`
   if 0 rows: note it as missing - `$ prepare-data` will need to create it.

5. check if logging infrastructure exists:
   `snow sql -q "SELECT COUNT(*) FROM <database>.<schema>.AUDIT_LOG LIMIT 1"`
   if this errors: note that AUDIT_LOG does not exist yet - it will be created in phase 1 using the logging infrastructure DDL from AGENTS.md. do NOT stop - continue with the remaining checks.

6. report summary:
   - account / role / warehouse / database - actual vs expected, any mismatch flagged
   - `<schema>` schema: exists / missing
   - `<stage>`: exists / missing (needs creation in phase 1)
   - AUDIT_LOG: accessible / not yet created (will be created in phase 1)

## success criteria

- role, warehouse, and database match AGENTS.md environment values
- `<schema>` schema exists
- AUDIT_LOG status reported (exists or needs creation in phase 1)
