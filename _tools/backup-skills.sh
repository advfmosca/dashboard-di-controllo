#!/usr/bin/env bash
# Backup giornaliero degli SKILL.md delle scheduled task coinvolte nella dashboard.
# Retention: 30 giorni, file più vecchi vengono auto-rimossi.
#
# Lanciare dal Terminal del Mac:
#   bash "$HOME/Desktop/Dashboard di Controllo/_tools/backup-skills.sh"
#
# Oppure schedulare via cron utente (esempio: ogni notte alle 23:00):
#   0 23 * * * bash ~/Desktop/Dashboard\ di\ Controllo/_tools/backup-skills.sh

set -euo pipefail

WORKSPACE="$HOME/Desktop/Dashboard di Controllo"
SCHED_DIR="$HOME/Documents/Claude/Scheduled"
BACKUP_DIR="$WORKSPACE/_backups/skills"
TODAY=$(date +%Y-%m-%d)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Lista scheduled task da backuppare (modifica liberamente per aggiungerne altre)
TASKS=(
  refresh-dashboard-data
  dashboard-csv-update
  fmm-morning-brief
  med-tech-daily-total-lift-sculpt
  fmm-discover-other-accounts
  alert-spending-anomalie-windsor
  daily-check-beefamily
  three-day-check-aghc
  exec-fmm-dashboard-migration
)

echo "════════════════════════════════════════════════════════════════"
echo "  BACKUP SKILL — $TODAY (retention $RETENTION_DAYS gg)"
echo "════════════════════════════════════════════════════════════════"
echo ""

# 1) BACKUP — copia ogni SKILL.md con timestamp
BACKUPPED=0
for taskId in "${TASKS[@]}"; do
  SRC="$SCHED_DIR/$taskId/SKILL.md"
  DST="$BACKUP_DIR/${taskId}_${TODAY}.md"
  if [ ! -f "$SRC" ]; then
    echo "  [skip]    $taskId (SKILL.md non trovato)"
    continue
  fi
  # Se backup di oggi esiste già con stesso contenuto, skip
  if [ -f "$DST" ] && cmp -s "$SRC" "$DST"; then
    echo "  [skip]    $taskId (già backuppato oggi, contenuto identico)"
    continue
  fi
  cp "$SRC" "$DST"
  BACKUPPED=$((BACKUPPED+1))
  echo "  [ok]      $taskId → ${taskId}_${TODAY}.md ($(wc -c < "$DST") bytes)"
done

echo ""
echo "→ Backup creati/aggiornati: $BACKUPPED"

# 2) CLEANUP — rimuovi backup più vecchi di RETENTION_DAYS giorni
echo ""
echo "→ Cleanup file più vecchi di $RETENTION_DAYS giorni..."
DELETED=$(find "$BACKUP_DIR" -name "*.md" -type f -mtime +$RETENTION_DAYS -print -delete 2>/dev/null | wc -l)
DELETED=$(echo "$DELETED" | tr -d ' ')
echo "  Rimossi: $DELETED file"

# 3) STATS
echo ""
echo "→ Stato attuale di $BACKUP_DIR:"
TOT_FILES=$(find "$BACKUP_DIR" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
TOT_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
echo "  File totali: $TOT_FILES · Spazio: $TOT_SIZE"

# 4) Cleanup anche _backups/code/ (build_data.py snapshots)
CODE_DIR="$WORKSPACE/_backups/code"
if [ -d "$CODE_DIR" ]; then
  DEL_CODE=$(find "$CODE_DIR" -name "*.bak" -type f -mtime +$RETENTION_DAYS -print -delete 2>/dev/null | wc -l)
  DEL_CODE=$(echo "$DEL_CODE" | tr -d ' ')
  [ "$DEL_CODE" -gt 0 ] && echo "  Cleanup _backups/code: rimossi $DEL_CODE file"
fi

echo ""
echo "✅ Backup completato."
echo ""
echo "Per ripristinare un SKILL:"
echo "  cp \"$BACKUP_DIR/<taskId>_YYYY-MM-DD.md\" \"$SCHED_DIR/<taskId>/SKILL.md\""
