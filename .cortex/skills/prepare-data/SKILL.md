---
name: prepare-data
description: "validate local CSV files and load them into Snowflake via PUT and COPY INTO. trigger when the user asks to validate CSV files, load data, upload to stage, or run data ingestion. do NOT use for Parquet or JSON files. do NOT use for data already loaded into Snowflake tables."
---

-> Load `references/put-command.md` before running PUT commands.
-> Load `references/copy-into-table.md` before running COPY INTO commands.

read the expected environment from AGENTS.md:
- `{database}` - target database
- `{schema}` - target schema
- `{stage}` - internal stage name

## steps

### validation phase

1. identify CSV files to validate from the AGENTS.md source files table.
   for each file read its `delimiter` (default: `,`) and expected row count.

2. for each file, run in order:
   a. file exists: `ls -lh <file>` - if missing: mark ERROR, skip remaining checks for this file.
   b. encoding check: `file <file>` - must report "ASCII text" or "UTF-8 Unicode text".
      if "UTF-8 Unicode (with BOM) text": mark WARN - BOM prefix may be read as data by COPY INTO.
      fix: `sed -i '1s/^\xEF\xBB\xBF//' <file>`.
      if Latin-1, UTF-16, or other non-UTF-8: mark ERROR.
   c. header row present: read the first line and confirm it contains non-numeric column names.
      if all-numeric: mark ERROR.
   d. column count: split header on the file's configured delimiter and count columns.
      compare against the target table's column count from AGENTS.md source table schemas.
      if mismatch: mark ERROR - COPY INTO will fail with "Number of columns in file does not match".
   e. no blank column names: split header on delimiter and check for empty strings.
      if any: mark WARN.
   f. row count: `wc -l <file>` minus 1 for header. compare against expected range from AGENTS.md.
      if outside +/-10%: mark WARN with actual count.
      note: `wc -l` counts line breaks, not CSV records. if fields contain embedded newlines,
      use: `python -c "import csv; print(sum(1 for _ in csv.reader(open('<file>')))-1)"`.
   g. no oversized rows: `awk 'length>10485760' <file>` - must return 0 lines.
      if any: mark ERROR.

3. produce a summary table: one row per file - status (OK / WARN / ERROR), row count, issues found.

4. if any file has ERROR status: stop and ask the user how to proceed. do NOT continue to load phase.

### load phase

5. for each CSV file, check if already compressed (.gz):
   - not compressed: run `gzip -k <file>` (keeps original, produces `<file>.gz`).
   - already .gz: use as-is.

6. run PUT for each compressed file:
   `snow sql -q "PUT file://<absolute-path.csv.gz> @{database}.{schema}.{stage} AUTO_COMPRESS=FALSE OVERWRITE=TRUE"`
   `AUTO_COMPRESS=FALSE` because the file is already gzip-compressed.
   expected: status = `UPLOADED`.
   if PUT fails: report the error for this file but continue with remaining files.
   common errors: file not found (check absolute path, use forward slashes), stage not found
   (run `SHOW STAGES IN SCHEMA`), permission denied (check role grants on stage).

7. run COPY INTO for each successfully uploaded file:
   `snow sql -q "COPY INTO {database}.{schema}.<table> FROM @{database}.{schema}.{stage}/<file.csv.gz> FILE_FORMAT=(TYPE=CSV SKIP_HEADER=1 FIELD_DELIMITER='<delimiter>' FIELD_OPTIONALLY_ENCLOSED_BY='\"') ON_ERROR=ABORT_STATEMENT"`
   expected: rows_loaded > 0, errors_seen = 0.
   if COPY INTO fails: report the full output for this file but continue with remaining files.
   if rows_loaded = 0 and no error: the file was likely already loaded (COPY INTO tracks load history).
   to force reload: add `FORCE=TRUE`, or `TRUNCATE TABLE` first. ask the user before force-reloading.
   common errors: column count mismatch (check delimiter and table DDL), encoding error (must be UTF-8),
   date parse error (add DATE_FORMAT to FILE_FORMAT if dates are non-ISO).

8. verify row counts:
   `snow sql -q "SELECT COUNT(*) FROM {database}.{schema}.<table>"`
   compare against AGENTS.md. if outside +/-5%: report WARN, ask user to confirm.

9. produce a final report: files uploaded, rows loaded per table, any errors or warnings.

## success criteria

- all files pass validation (no ERROR status)
- all PUT commands return status `UPLOADED`
- all COPY INTO commands return rows_loaded > 0 and errors_seen = 0
- row counts match AGENTS.md expected values within +/-5%
