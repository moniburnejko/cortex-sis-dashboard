# snow streamlit CLI Reference

Source: [snow streamlit deploy | Snowflake Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-cli/command-reference/streamlit-commands/deploy)
Source: [Deploying a Streamlit app | Snowflake Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-cli/streamlit-apps/manage-apps/deploy-app)

---

## snow streamlit deploy

Uploads local files to the internal stage and creates or replaces the Streamlit object in Snowflake.

### Syntax

```bash
snow streamlit deploy [ENTITY_ID] [OPTIONS]
```

| Parameter | Description |
|---|---|
| `ENTITY_ID` | Optional. The entity key from `snowflake.yml` (e.g. `renewal_radar`). Required only if `snowflake.yml` defines multiple Streamlit entities. |

### Key Flags

| Flag | Description |
|---|---|
| `--replace` | Replace the existing Streamlit app if it already exists. **Always use this flag for re-deployments.** |
| `--open` | Open the app URL in a browser after deploy. |
| `--connection <name>` | Use a named connection from `config.toml` instead of the default. |
| `--project <path>` | Path to the project directory containing `snowflake.yml`. Defaults to current directory. |

### Example

```bash
snow streamlit deploy --replace
```

### Successful Output

```
Uploading dashboard.py to @<stage>...
Deploying streamlit app <app_name>...
Streamlit successfully deployed and available at <url>
```

The URL is printed on the last line - capture it for sharing with the user.

### Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Multiple file or directories were mapped to one output destination` | `artifacts` key in `snowflake.yml` conflicts with auto-mapping of `main_file` | Remove the `artifacts` key entirely |
| `Object does not exist` for warehouse/schema | Active role lacks privilege or object name is wrong | Verify `USE WAREHOUSE` and `USE SCHEMA` match AGENTS.md values |
| `Python runtime error` on deploy | Syntax error or import error in the Python file | Run `python -m py_compile dashboard.py` first |
| `Cannot create streamlit: insufficient privileges` | Active role lacks CREATE STREAMLIT privilege | Check `SELECT CURRENT_ROLE()` matches expected role |

---

## snow streamlit list

Lists all Streamlit apps accessible to the current role.

### Syntax

```bash
snow streamlit list [OPTIONS]
```

### Output Columns

| Column | Description |
|---|---|
| `name` | Streamlit object name (matches `identifier.name` in snowflake.yml) |
| `database_name` | Database containing the app |
| `schema_name` | Schema containing the app |
| `title` | Display title (defaults to object name) |
| `owner` | Role that owns the app |
| `url_id` | URL fragment used to access the app |
| `default_packages` | Whether default Snowflake packages are included |
| `user_packages` | Additional packages specified in environment.yml |

### Example

```bash
snow streamlit list
```

Use to verify the app was deployed: the `name` column must contain the expected app name.

---

## snow streamlit get-url

Returns the URL for an existing Streamlit app.

### Syntax

```bash
snow streamlit get-url <APP_NAME> [OPTIONS]
```

### Example

```bash
snow streamlit get-url RENEWAL_RADAR
```

Returns the full HTTPS URL to open the app in a browser.

---

## Notes

- All commands respect the active connection from `config.toml` (or `--connection` flag).
- `snow streamlit deploy --replace` is idempotent - safe to run multiple times.
- The deploy command automatically uploads the `main_file` and any `pages_dir` content.
- Snowflake CLI 3.14+ uses the modern `CREATE OR REPLACE STREAMLIT` SQL syntax by default.
