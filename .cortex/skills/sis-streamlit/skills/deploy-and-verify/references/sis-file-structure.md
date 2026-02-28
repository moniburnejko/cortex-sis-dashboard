# SiS app file structure

source: [organize your Streamlit app files | Snowflake documentation](https://docs.snowflake.com/en/developer-guide/streamlit/app-development/file-organization)
source: [creating a Streamlit app | Snowflake documentation](https://docs.snowflake.com/en/developer-guide/snowflake-cli/streamlit-apps/manage-apps/initialize-app)

---

## required directory layout

```
<project-root>/
├── snowflake.yml                 <- Snowflake CLI project config (project root)
├── dashboard.py                  <- main Streamlit file (declared in snowflake.yml main_file)
└── environment.yml               <- package dependencies + Streamlit version pin (same level as main file)
```

### key rules

1. `snowflake.yml` lives at the **project root** - the directory from which you run `snow streamlit deploy`
2. `environment.yml` must be at the **same directory level as the main `.py` file** - for this project both are at project root
3. `main_file` in `snowflake.yml` is relative to the project root

---

## snowflake.yml and main_file path

```yaml
definition_version: 2

entities:
  renewal_radar:
    type: streamlit
    identifier:
      name: RENEWAL_RADAR
    query_warehouse: COMPUTE_WH
    main_file: dashboard.py   # <- relative to project root (dashboard.py is at root)
```

---

## what snow streamlit deploy uploads

`snow streamlit deploy` automatically uploads:
- the `main_file` declared in `snowflake.yml`
- `environment.yml` (if it exists at the same level as `main_file`)

note: the deploy uses differential upload - it only re-uploads files that changed since the
last deploy. if environment.yml is unchanged it will not appear in the deploy output, but it
is already present in the Snowflake stage from the previous deploy.

**it does NOT automatically upload:**
- Python utility modules or shared libraries (use `imports` in `snowflake.yml`)
- data files or CSVs (upload to a stage separately)
- config files in other directories

---

## common file structure mistakes

| mistake | symptom | fix |
|---|---|---|
| `environment.yml` not co-located with main `.py` | wrong Streamlit version or packages missing | move `environment.yml` to the same directory as `dashboard.py` |
| `environment.yml` deleted or missing before deploy | `user_packages` empty in `snow streamlit list`, older default Streamlit used | re-create `environment.yml` and re-deploy |
| `artifacts:` key in `snowflake.yml` | "Multiple file or directories were mapped to one output destination" | remove `artifacts` entirely |
| `main_file` path uses backslashes | deploy fails on non-Windows or in CLI | always use forward slashes: `dashboard.py` |
| wrong `main_file` path | "File not found" error on deploy | path must be relative to project root |

---

## verifying structure before deploy

```bash
# confirm snowflake.yml exists in current directory
ls snowflake.yml

# confirm main file exists at project root
ls dashboard.py

# confirm environment.yml is next to main file (both at project root)
ls environment.yml
```

## verifying environment.yml was uploaded

after deploy, run `snow streamlit list` and check the `user_packages` column for the app row.
if `user_packages` is non-empty (lists altair, streamlit=1.52.*, pandas), the upload succeeded.
if `user_packages` is empty, environment.yml was missing at deploy time - re-create and re-deploy.
