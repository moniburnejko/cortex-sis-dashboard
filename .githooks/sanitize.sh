#!/usr/bin/env bash
# sanitize.sh - replace sensitive snowflake object names with placeholders
#
# usage:
#   .githooks/sanitize.sh [OPTIONS] [FILE...]
#
# options:
#   --check     check for sensitive names without modifying (exit 1 if found)
#   --staged    operate on git-staged files only
#   --reverse   replace placeholders with real names (for local work)
#   --dry-run   show what would be changed without modifying files
#
# if no files are specified and --staged is not used, operates on all
# tracked files in the repository.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MAP_FILE="$SCRIPT_DIR/.sanitize-map"

# --- helpers ----------------------------------------------------------------

die() { echo "error: $1" >&2; exit 1; }

load_map() {
    [[ -f "$MAP_FILE" ]] || die ".sanitize-map not found. copy .githooks/sanitize-map.example to .githooks/.sanitize-map and fill in real values."

    REAL_NAMES=()
    PLACEHOLDERS=()

    while IFS= read -r line; do
        # skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// /}" ]] && continue

        local real="${line%%=*}"
        local placeholder="${line#*=}"

        [[ -z "$real" || -z "$placeholder" ]] && continue

        REAL_NAMES+=("$real")
        PLACEHOLDERS+=("$placeholder")
    done < "$MAP_FILE"

    [[ ${#REAL_NAMES[@]} -gt 0 ]] || die "no mappings found in .sanitize-map"
}

get_files() {
    if [[ "$USE_STAGED" == true ]]; then
        git -C "$REPO_ROOT" diff --cached --name-only --diff-filter=ACMR
    elif [[ ${#FILE_ARGS[@]} -gt 0 ]]; then
        printf '%s\n' "${FILE_ARGS[@]}"
    else
        git -C "$REPO_ROOT" ls-files
    fi
}

is_binary() {
    local file="$1"
    # skip binary files
    if file --mime-encoding "$file" 2>/dev/null | grep -q "binary"; then
        return 0
    fi
    return 1
}

# --- modes ------------------------------------------------------------------

do_check() {
    local found=0
    local files_with_issues=()

    while IFS= read -r filepath; do
        [[ -z "$filepath" ]] && continue
        local fullpath="$REPO_ROOT/$filepath"
        [[ -f "$fullpath" ]] || continue
        is_binary "$fullpath" && continue

        for i in "${!REAL_NAMES[@]}"; do
            if grep -qF "${REAL_NAMES[$i]}" "$fullpath" 2>/dev/null; then
                echo "  found '${REAL_NAMES[$i]}' in $filepath"
                found=1
                files_with_issues+=("$filepath")
                break
            fi
        done
    done < <(get_files)

    if [[ $found -eq 1 ]]; then
        echo ""
        echo "sensitive names detected in ${#files_with_issues[@]} file(s)."
        echo "run '.githooks/sanitize.sh --staged' to replace them."
        return 1
    else
        echo "no sensitive names found."
        return 0
    fi
}

do_replace() {
    local direction="$1"  # "sanitize" or "reverse"
    local modified_files=()

    while IFS= read -r filepath; do
        [[ -z "$filepath" ]] && continue
        local fullpath="$REPO_ROOT/$filepath"
        [[ -f "$fullpath" ]] || continue
        is_binary "$fullpath" && continue

        local file_changed=false

        for i in "${!REAL_NAMES[@]}"; do
            local from to
            if [[ "$direction" == "sanitize" ]]; then
                from="${REAL_NAMES[$i]}"
                to="${PLACEHOLDERS[$i]}"
            else
                from="${PLACEHOLDERS[$i]}"
                to="${REAL_NAMES[$i]}"
            fi

            if grep -qF "$from" "$fullpath" 2>/dev/null; then
                if [[ "$DRY_RUN" == true ]]; then
                    echo "  would replace '$from' -> '$to' in $filepath"
                    file_changed=true
                else
                    # use perl for reliable in-place replacement (works on windows git bash too)
                    perl -pi -e "s/\Q$from\E/$to/g" "$fullpath"
                    file_changed=true
                fi
            fi
        done

        if [[ "$file_changed" == true ]]; then
            modified_files+=("$filepath")
        fi
    done < <(get_files)

    if [[ ${#modified_files[@]} -gt 0 ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            echo ""
            echo "would modify ${#modified_files[@]} file(s)."
        else
            echo "replaced names in ${#modified_files[@]} file(s):"
            printf '  %s\n' "${modified_files[@]}"
        fi
    else
        echo "no replacements needed."
    fi

    # return the list of modified files via global var (for pre-commit hook)
    MODIFIED_FILES=("${modified_files[@]+"${modified_files[@]}"}")
}

# --- main -------------------------------------------------------------------

MODE="sanitize"
USE_STAGED=false
DRY_RUN=false
FILE_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --check)    MODE="check";   shift ;;
        --staged)   USE_STAGED=true; shift ;;
        --reverse)  MODE="reverse"; shift ;;
        --dry-run)  DRY_RUN=true;   shift ;;
        --help|-h)
            head -14 "$0" | tail -13
            exit 0
            ;;
        *)          FILE_ARGS+=("$1"); shift ;;
    esac
done

load_map

case "$MODE" in
    check)    do_check ;;
    sanitize) do_replace "sanitize" ;;
    reverse)  do_replace "reverse" ;;
esac
