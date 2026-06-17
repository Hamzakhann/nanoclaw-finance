#!/usr/bin/env bash
# organizer.sh — survey, backup, classify, and organise expense files
# Usage: ./tools/organizer.sh <source_dir> [--dry-run]

set -euo pipefail

# ── constants ────────────────────────────────────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORGANISED_DIR="$PROJECT_ROOT/data/organised"
BACKUP_BASE="$PROJECT_ROOT/data/backup"
LOG_FILE="$PROJECT_ROOT/docs/ORGANIZER-LOG.md"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
DATE_STAMP="$(date '+%Y-%m-%d_%H%M%S')"

# ── argument parsing ──────────────────────────────────────────────────────────
DRY_RUN=false
SOURCE_DIR=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    *)         SOURCE_DIR="$arg" ;;
  esac
done

if [[ -z "$SOURCE_DIR" ]]; then
  echo "Usage: $0 <source_dir> [--dry-run]"
  exit 1
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "ERROR: source directory '$SOURCE_DIR' does not exist."
  exit 1
fi

SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"

# ── helpers ───────────────────────────────────────────────────────────────────
log() {
  local level="$1"
  local message="$2"
  local line="| $TIMESTAMP | $level | $message |"
  echo "$line"
  if [[ "$DRY_RUN" == false ]]; then
    echo "$line" >> "$LOG_FILE"
  fi
}

dry_prefix() {
  if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY-RUN] "
  else
    echo ""
  fi
}

# ── classify a single file ────────────────────────────────────────────────────
# Returns the subfolder name for the file based on extension + content sniff.
classify_file() {
  local filepath="$1"
  local filename
  filename="$(basename "$filepath")"
  local ext="${filename##*.}"

  # files with no extension (filename == ext means no dot found)
  if [[ "$filename" == "$ext" ]]; then
    ext=""
  fi

  local lower_ext
  lower_ext="$(echo "$ext" | tr '[:upper:]' '[:lower:]')"

  case "$lower_ext" in
    csv)
      # peek at header/content to sub-classify if possible
      local content
      content="$(tr '[:upper:]' '[:lower:]' < "$filepath" 2>/dev/null || true)"
      if echo "$content" | grep -qiE 'petrol|fuel|diesel|uber|careem|transport|pump|pso|shell|toll|parking'; then
        echo "csv/transport"
      elif echo "$content" | grep -qiE 'restaurant|cafe|dhaba|foodpanda|biryani|pizza|burger'; then
        echo "csv/dining"
      elif echo "$content" | grep -qiE 'grocery|groceries|kiryana|supermarket|imtiaz|carrefour|metro|mart'; then
        echo "csv/groceries"
      elif echo "$content" | grep -qiE 'electricity|wapda|k-electric|sui gas|ssgc|sngpl|water|ptcl|internet|bill|utility'; then
        echo "csv/utilities"
      elif echo "$content" | grep -qiE 'pharmacy|medical|clinic|hospital|doctor|medicine|lab'; then
        echo "csv/health"
      else
        echo "csv"
      fi
      ;;
    pdf)
      echo "pdf"
      ;;
    txt)
      echo "docs"
      ;;
    xlsx|xls)
      echo "spreadsheets"
      ;;
    jpg|jpeg|png|gif|webp)
      echo "images"
      ;;
    "")
      # no extension — sniff first bytes for known magic numbers
      local mime
      mime="$(file --mime-type -b "$filepath" 2>/dev/null || echo "unknown")"
      case "$mime" in
        text/plain)  echo "misc/text" ;;
        text/csv)    echo "csv" ;;
        application/pdf) echo "pdf" ;;
        image/*)     echo "images" ;;
        *)           echo "misc" ;;
      esac
      ;;
    *)
      echo "misc"
      ;;
  esac
}

# ── step 1: survey ────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo " nanoclaw-finance organizer.sh"
if [[ "$DRY_RUN" == true ]]; then
  echo " MODE: DRY-RUN (no files will be moved)"
fi
echo " Source : $SOURCE_DIR"
echo " Date   : $TIMESTAMP"
echo "══════════════════════════════════════════════"
echo ""

FILES=()
while IFS= read -r line; do
  FILES+=("$line")
done < <(find "$SOURCE_DIR" -maxdepth 1 -type f | sort)
SOURCE_COUNT="${#FILES[@]}"

echo "── Step 1: Survey ───────────────────────────"
echo "  Found $SOURCE_COUNT file(s) in $SOURCE_DIR"
if [[ ${#FILES[@]} -gt 0 ]]; then
  for f in "${FILES[@]}"; do
    echo "    $(basename "$f")  ($(du -h "$f" | cut -f1))"
  done
else
  echo "  (no files found — nothing to process)"
fi
echo ""

if [[ "$DRY_RUN" == false ]]; then
  # initialise log file with header if it doesn't exist
  if [[ ! -f "$LOG_FILE" ]]; then
    {
      echo "# ORGANIZER LOG"
      echo ""
      echo "| Timestamp | Level | Message |"
      echo "|-----------|-------|---------|"
    } > "$LOG_FILE"
  fi
  log "INFO" "Run started — source: $SOURCE_DIR — $SOURCE_COUNT file(s) found"
fi

# ── step 2: backup ────────────────────────────────────────────────────────────
BACKUP_DIR="$BACKUP_BASE/$DATE_STAMP"
echo "── Step 2: Backup ───────────────────────────"
echo "  $(dry_prefix)Backup destination: $BACKUP_DIR"

if [[ "$DRY_RUN" == false ]]; then
  mkdir -p "$BACKUP_DIR"
  cp -a "$SOURCE_DIR/." "$BACKUP_DIR/"
  BACKUP_COUNT="$(find "$BACKUP_DIR" -maxdepth 1 -type f | wc -l | tr -d ' ')"
  if [[ "$BACKUP_COUNT" -ne "$SOURCE_COUNT" ]]; then
    log "ERROR" "Backup count mismatch — expected $SOURCE_COUNT, got $BACKUP_COUNT"
    echo "ERROR: backup file count ($BACKUP_COUNT) does not match source ($SOURCE_COUNT). Aborting."
    exit 1
  fi
  log "INFO" "Backup complete — $BACKUP_COUNT file(s) copied to $BACKUP_DIR"
  echo "  Backup verified: $BACKUP_COUNT/$SOURCE_COUNT files confirmed"
else
  echo "  [DRY-RUN] Would copy $SOURCE_COUNT file(s) to $BACKUP_DIR"
fi
echo ""

# ── step 3: classify + show plan ─────────────────────────────────────────────
echo "── Step 3: Classification plan ──────────────"
# parallel index array — bash 3.2 compatible (no associative arrays)
PLAN_FOLDERS=()

for filepath in "${FILES[@]}"; do
  filename="$(basename "$filepath")"
  subfolder="$(classify_file "$filepath")"
  PLAN_FOLDERS+=("$subfolder")
  dest_path="$ORGANISED_DIR/$subfolder/$filename"
  echo "  $filename"
  echo "    SOURCE : $filepath"
  echo "    DEST   : $dest_path"
  echo "    RULE   : extension/content → $subfolder"
  echo ""
done

# ── step 4: execute moves ─────────────────────────────────────────────────────
echo "── Step 4: $(if [[ "$DRY_RUN" == true ]]; then echo "Moves (skipped — dry-run)"; else echo "Moving files"; fi) ──────────────────────"

MOVED=0
for i in "${!FILES[@]}"; do
  filepath="${FILES[$i]}"
  filename="$(basename "$filepath")"
  subfolder="${PLAN_FOLDERS[$i]}"
  dest_dir="$ORGANISED_DIR/$subfolder"
  dest_path="$dest_dir/$filename"

  if [[ "$DRY_RUN" == true ]]; then
    echo "  [DRY-RUN] mv $filepath → $dest_path"
  else
    mkdir -p "$dest_dir"
    mv "$filepath" "$dest_path"
    log "MOVE" "$filename → $subfolder/$filename"
    echo "  MOVED: $filename → $subfolder/$filename"
    MOVED=$((MOVED + 1))
  fi
done
echo ""

# ── step 5: verify count ──────────────────────────────────────────────────────
echo "── Step 5: Verification ─────────────────────"

if [[ "$DRY_RUN" == true ]]; then
  echo "  [DRY-RUN] Would verify $SOURCE_COUNT file(s) moved to $ORGANISED_DIR"
else
  ORGANISED_COUNT="$(find "$ORGANISED_DIR" -type f | wc -l | tr -d ' ')"
  echo "  Files moved this run : $MOVED"
  echo "  Total in organised/  : $ORGANISED_COUNT"

  if [[ "$MOVED" -eq "$SOURCE_COUNT" ]]; then
    log "INFO" "Verification passed — $MOVED/$SOURCE_COUNT files moved successfully"
    echo "  PASS: all $SOURCE_COUNT files moved successfully"
  else
    log "ERROR" "Verification FAILED — moved $MOVED, expected $SOURCE_COUNT"
    echo "  FAIL: moved $MOVED but expected $SOURCE_COUNT"
    exit 1
  fi

  REMAINING="$(find "$SOURCE_DIR" -maxdepth 1 -type f | wc -l | tr -d ' ')"
  if [[ "$REMAINING" -eq 0 ]]; then
    log "INFO" "Source directory is now empty — $SOURCE_DIR"
    echo "  PASS: source directory is empty"
  else
    log "WARN" "Source directory still has $REMAINING file(s) — $SOURCE_DIR"
    echo "  WARN: $REMAINING file(s) remain in source directory"
  fi

  log "INFO" "Run complete"
fi

echo ""
echo "══════════════════════════════════════════════"
if [[ "$DRY_RUN" == true ]]; then
  echo " Dry-run complete. No files were moved."
else
  echo " Done. Log appended to $LOG_FILE"
fi
echo "══════════════════════════════════════════════"
echo ""
