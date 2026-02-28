# COPY INTO <table> Reference

Source: [COPY INTO <table> | Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table)
Source: [Copy data from an internal stage | Snowflake Documentation](https://docs.snowflake.com/en/user-guide/data-load-local-file-system-copy)

---

## Overview

COPY INTO loads data from a stage into a Snowflake table. For CSV files uploaded via PUT, use an inline `FILE_FORMAT` clause.

---

## Syntax

```sql
COPY INTO <table>
  FROM @<stage>/<filename.csv.gz>
  FILE_FORMAT = (
    TYPE = CSV
    SKIP_HEADER = 1
    FIELD_DELIMITER = '<delimiter>'
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    [ NULL_IF = ('', 'NULL', 'null') ]
    [ EMPTY_FIELD_AS_NULL = TRUE ]
    [ DATE_FORMAT = 'AUTO' ]
    [ TIMESTAMP_FORMAT = 'AUTO' ]
    [ ENCODING = 'UTF8' ]
  )
  [ ON_ERROR = ABORT_STATEMENT | CONTINUE | SKIP_FILE | SKIP_FILE_<n> | SKIP_FILE_<n>% ]
  [ PURGE = FALSE | TRUE ]
```

---

## FILE_FORMAT Options (CSV)

| Option | Default | Description |
|---|---|---|
| `TYPE` | - | Must be `CSV` for delimited text files |
| `SKIP_HEADER` | `0` | Number of header lines to skip. Use `1` for files with a column header row. |
| `FIELD_DELIMITER` | `,` | Character separating fields. Use `'\t'` for tab-delimited. Per-file delimiter must match the source file. |
| `FIELD_OPTIONALLY_ENCLOSED_BY` | `NONE` | Character used to optionally enclose field values. Use `'"'` (double quote) for standard CSV quoting. |
| `NULL_IF` | `('\\N')` | Strings to interpret as SQL NULL. Use `('', 'NULL', 'null')` for typical CSV null representations. |
| `EMPTY_FIELD_AS_NULL` | `TRUE` | If `TRUE`, empty fields (`,,`) are loaded as NULL. |
| `DATE_FORMAT` | `'AUTO'` | Date parsing format. `AUTO` detects common formats. |
| `TIMESTAMP_FORMAT` | `'AUTO'` | Timestamp parsing format. `AUTO` detects common formats. |
| `ENCODING` | `'UTF8'` | File character encoding. |
| `TRIM_SPACE` | `FALSE` | Trim leading/trailing whitespace from fields. |

---

## ON_ERROR Options

| Value | Behavior |
|---|---|
| `ABORT_STATEMENT` | **Default.** Stop the entire COPY operation when the first error is encountered. No rows are loaded from any file that contains an error. |
| `CONTINUE` | Skip erroneous rows and continue loading. All valid rows are loaded even if errors exist. |
| `SKIP_FILE` | Skip an entire file if it contains any error. Load all other files. |
| `SKIP_FILE_<n>` | Skip a file if it contains more than `<n>` errors. |
| `SKIP_FILE_<n>%` | Skip a file if more than `<n>%` of rows have errors. |

**In this project:** use `ON_ERROR = ABORT_STATEMENT` to ensure clean loads. A partial load is harder to diagnose than a failed load.

---

## Output Columns

| Column | Description |
|---|---|
| `file` | Stage path of the loaded file |
| `status` | `LOADED` - all rows loaded; `LOAD_FAILED` - errors prevented loading; `PARTIALLY_LOADED` - some rows loaded (only with `CONTINUE`) |
| `rows_parsed` | Total rows read from the file (excluding header) |
| `rows_loaded` | Rows successfully inserted into the table |
| `error_limit` | Maximum errors allowed (from `ON_ERROR` setting) |
| `errors_seen` | Number of rows with errors |
| `first_error` | Error message for the first bad row |
| `first_error_line` | Line number (1-based) of the first error |
| `first_error_character` | Character position of the first error |
| `first_error_column_name` | Column name where the first error occurred |

**Expected values for a clean load:** `rows_loaded > 0`, `errors_seen = 0`, `status = 'LOADED'`.

---

## Usage in This Project

```sql
-- Load a pre-compressed CSV from an internal stage
COPY INTO <database>.<schema>.<table>
  FROM @<stage>/<file.csv.gz>
  FILE_FORMAT = (
    TYPE = CSV
    SKIP_HEADER = 1
    FIELD_DELIMITER = ','
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  )
  ON_ERROR = ABORT_STATEMENT;
```

Adjust `FIELD_DELIMITER` per file - see the AGENTS.md source files table for the delimiter per CSV file.

---

## Verifying the Load

After COPY INTO, confirm row counts:

```sql
SELECT COUNT(*) FROM <database>.<schema>.<table>;
```

Compare against expected values from AGENTS.md (±5% tolerance). If the count is outside that range, report a WARN and ask the user to confirm before continuing.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Number of columns in file (N) does not match that of the corresponding table (M)` | CSV column count mismatch | Check delimiter - wrong delimiter causes all columns to appear as one |
| `Numeric value '' is not recognized` | Empty numeric field not handled | Add `EMPTY_FIELD_AS_NULL = TRUE` or `NULL_IF = ('')` |
| `Date '' is not recognized` | Empty date field | Add `NULL_IF = ('')` |
| `File not found` on stage | PUT did not succeed or wrong path | Run `LIST @<stage>` to verify file exists |

---

## Notes

- Files loaded with COPY INTO are not automatically removed from the stage. Use `PURGE = TRUE` only after confirming the load succeeded.
- COPY INTO tracks loaded files in a **load history** (90-day window). Re-running COPY INTO on the same file without changes has no effect. Use `FORCE = TRUE` to override.
- The stage path in the FROM clause must match the `target` column output from the PUT command.
