# snowflake.yml Reference - Streamlit in Snowflake

Source: [Deploying a Streamlit app | Snowflake Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-cli/streamlit-apps/manage-apps/deploy-app)
Source: [About project definition files | Snowflake Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-cli/project-definitions/about)

---

## Supported versions

| `definition_version` | Status |
|---|---|
| `1` | Legacy - works but deprecated for new projects |
| `2` | Current - use for all new Streamlit deployments |

---

## definition_version: 2 - Full Schema

```yaml
definition_version: 2

entities:
  <app_name>:                          # arbitrary identifier, becomes the CLI handle
    type: streamlit
    identifier:
      name: <STREAMLIT_OBJECT_NAME>    # the SQL object name in Snowflake
      # schema: <schema>               # optional - overrides connection default
      # database: <database>           # optional - overrides connection default
    query_warehouse: <warehouse>       # warehouse used for SQL queries in the app
    main_file: <path/to/app.py>        # path relative to project root (e.g. dashboard.py if at root)
    # pages_dir: <path/>               # optional - directory containing multi-page app pages
    # stage: <stage_name>              # optional - internal stage for app files
    # external_access_integrations:    # optional - list of EAIs for outbound network access
    #   - <integration_name>
    # secrets:                         # optional - Snowflake secrets to inject
    #   <env_var>: <secret_name>
    # imports:                         # optional - additional files/stages to import
    #   - <path_or_stage>
    # grants:                          # optional - RBAC grants on the app object
    #   - privilege: USAGE
    #     role: <role_name>
```

---

## Fields Reference

| Field | Required | Description |
|---|---|---|
| `type: streamlit` | Yes | declares this entity as a Streamlit app |
| `identifier.name` | Yes | SQL object name (visible in Snowsight) |
| `identifier.database` | No | overrides active database from connection |
| `identifier.schema` | No | overrides active schema from connection |
| `query_warehouse` | Yes | warehouse for SQL queries within the app |
| `main_file` | Yes | path to the main Python file, relative to project root |
| `pages_dir` | No | directory with additional pages (auto-deployed) |
| `stage` | No | internal stage to store app files (auto-created if omitted) |
| `external_access_integrations` | No | required for any outbound HTTP calls from the app |
| `secrets` | No | Snowflake secrets injected as env vars |
| `imports` | No | additional files or stages mounted into the app runtime |
| `grants` | No | RBAC grants applied to the Streamlit object after creation |

---

## ⚠️ Do NOT add `artifacts`

The `artifacts` key causes the error:

```
Multiple file or directories were mapped to one output destination
```

This happens because `snow streamlit deploy` already maps `main_file` to the stage automatically. Adding `artifacts` creates a conflicting mapping. **Remove `artifacts` entirely.**

---

## Minimal Working Example

```yaml
definition_version: 2

entities:
  renewal_radar:
    type: streamlit
    identifier:
      name: RENEWAL_RADAR
    query_warehouse: COMPUTE_WH
    main_file: dashboard.py
```

---

## definition_version: 1 (Legacy)

```yaml
definition_version: 1
streamlit:
  name: <STREAMLIT_OBJECT_NAME>
  stage: <stage_name>
  query_warehouse: <warehouse>
  main_file: <path/to/app.py>
```

The v1 format uses a flat `streamlit:` key, not an `entities:` block. It does not support multiple entities, grants, or external access integrations.

---

## Notes

- The `definition_version: 2` format requires Snowflake CLI 3.0 or later.
- `snow streamlit deploy --replace` works with both v1 and v2 formats.
- The Streamlit object name in Snowflake is `identifier.name`, not the entity key (e.g. `renewal_radar` vs. `RENEWAL_RADAR`).
- If `stage` is omitted, Snowflake CLI creates a stage named after the app automatically.
