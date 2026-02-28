# PUT Command Reference

Source: [PUT | Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/put)

---

## Overview

PUT uploads a local data file from the client machine to an **internal** Snowflake stage. It is only available in the `snow sql` CLI and SnowSQL - it cannot be run in a Snowflake worksheet.

---

## Syntax

```sql
PUT file://<path_to_file>/<filename>  @<internal_stage_name>
    [ PARALLEL = <integer> ]
    [ AUTO_COMPRESS = TRUE | FALSE ]
    [ SOURCE_COMPRESSION = AUTO_DETECT | GZIP | BZ2 | BROTLI | ZSTD | DEFLATE | RAW_DEFLATE | NONE ]
    [ OVERWRITE = TRUE | FALSE ]
```

### Path Format

- **Linux/macOS**: `file:///home/user/data/file.csv` (three slashes for absolute path)
- **Windows**: `file://C:/Users/user/data/file.csv` or `file:///C:/Users/user/data/file.csv`
- Wildcards are supported: `file:///data/*.csv` uploads all matching files

---

## Options

| Option | Default | Description |
|---|---|---|
| `PARALLEL` | `4` | Number of threads used to upload. Range: 1-99. Increase for large files on fast networks. |
| `AUTO_COMPRESS` | `TRUE` | If `TRUE`, Snowflake compresses the file with gzip before upload (adds `.gz` extension). If `FALSE`, uploads as-is. **Set to `FALSE` when the file is already gzip-compressed.** |
| `SOURCE_COMPRESSION` | `AUTO_DETECT` | Declares the compression of the source file. `AUTO_DETECT` inspects the file header. Explicit values: `GZIP`, `BZ2`, `BROTLI`, `ZSTD`, `DEFLATE`, `RAW_DEFLATE`, `NONE`. |
| `OVERWRITE` | `FALSE` | If `FALSE`, skips upload if a file with the same name already exists on the stage (returns status `SKIPPED`). If `TRUE`, replaces the existing file. |

---

## Output Columns

| Column | Description |
|---|---|
| `source` | Original local filename |
| `target` | Filename on the stage (may have `.gz` extension added if auto-compressed) |
| `source_size` | Size of the local file in bytes |
| `target_size` | Size of the uploaded file in bytes |
| `source_compression` | Detected or declared source compression |
| `target_compression` | Compression of the uploaded file |
| `status` | `UPLOADED` - file uploaded successfully; `SKIPPED` - file already exists and `OVERWRITE=FALSE` |
| `message` | Error message if upload failed, otherwise empty |

---

## Usage in This Project

Pre-compress CSV files with `gzip -k <file>` before PUT, then use `AUTO_COMPRESS=FALSE`:

```sql
-- correct: file is already .gz, do not compress again
PUT file:///absolute/path/to/data.csv.gz @MY_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE
```

Using `AUTO_COMPRESS=TRUE` on an already-compressed file would double-compress it, producing a file that COPY INTO cannot load.

---

## Stage Path Patterns

| Stage Type | Path Pattern |
|---|---|
| User stage | `@~` |
| Named internal stage | `@<stage_name>` or `@<database>.<schema>.<stage_name>` |
| Table stage | `@%<table_name>` |

Upload to a subdirectory on a named stage:
```sql
PUT file:///data/file.csv.gz @MY_STAGE/subdir/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE
```

---

## Notes

- PUT is **not available in Snowflake worksheets** - only in SnowSQL and `snow sql` CLI.
- The stage must already exist before running PUT. Create it with `CREATE STAGE IF NOT EXISTS`.
- After PUT, verify the file is on the stage: `LIST @<stage_name>;`
- Files uploaded with PUT are encrypted automatically using Snowflake's encryption.
