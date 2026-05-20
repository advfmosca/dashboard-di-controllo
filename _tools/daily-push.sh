#!/usr/bin/env bash
# Dashboard di Controllo — daily push automatico, zero-conflict.
#
# Cosa fa, in sequenza:
#   1. Sincronizza il repo locale con origin via pull --rebase
#      → in caso di conflitto vince SEMPRE la versione locale (filesystem),
#        perché è quella che contiene sia i dati freschi sia le eventuali
#        modifiche fatte da Claude direttamente sul workspace.
#   2. Rigenera tutte le pagine cea-daily-*.html dagli snapshot disponibili.
#   3. Rimuove eventuali lock di git lasciati orfani.
#   4. Stage di tutto, commit "Daily refresh — YYYY-MM-DD", push.
#
# Idempotente: se non c'è nulla da committare, il commit/push viene saltato.
# Se è già allineato a remote, il pull --rebase non fa nulla.
#
# Uso:
#   bash _tools/daily-push.sh
# Oppure tramite alias zsh:
#   alias dash-push='bash ~/"Desktop/Dashboard di Controllo/_tools/daily-push.sh"'

set -uo pipefail

# Vai nella root del repo (cartella padre di _tools)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR" || { echo "❌ Cartella repo non trovata: $REPO_DIR"; exit 1; }

echo "→ Repo: $REPO_DIR"
echo "→ Branch: $(git branch --show-current 2>/dev/null || echo 'unknown')"

# ──────────────────────────────────────────────────────────────────────────────
# Step 0 — cleanup lock orfani
# ──────────────────────────────────────────────────────────────────────────────
rm -f .git/index.lock .git/HEAD.lock .git/MERGE_HEAD.lock 2>/dev/null || true

# ──────────────────────────────────────────────────────────────────────────────
# Step 1 — pull --rebase con auto-resolve dei conflitti (sempre vince il locale)
# ──────────────────────────────────────────────────────────────────────────────
echo "→ Sync con origin/main…"
git fetch origin main 2>&1 | tail -3 || true

# Se la working tree ha modifiche, le stash prima del rebase per evitare blocchi
STASHED=0
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "→ Stash temporaneo delle modifiche locali…"
  git stash push -u -m "auto-stash-daily-push-$(date +%s)" >/dev/null 2>&1 && STASHED=1
fi

# Rebase con preferenza locale (-X theirs durante rebase = il commit
# riapplicato, che è "il nostro" lato utente). Se ancora restano conflitti,
# li risolviamo prendendo theirs manualmente.
git pull --rebase -X theirs origin main 2>&1 | tail -10 || {
  echo "→ Conflitti residui: risolvo automaticamente con 'theirs'…"
  while git status --porcelain | grep -qE '^(UU|AA|UA|AU|DU|UD)'; do
    git status --porcelain | grep -E '^(UU|AA|UA|AU|DU|UD)' | awk '{print $2}' | while read -r f; do
      git checkout --theirs -- "$f" 2>/dev/null && git add "$f" 2>/dev/null
    done
    GIT_EDITOR=true git rebase --continue 2>&1 | tail -3 || { git rebase --abort; break; }
  done
}

# Ripristina lo stash se fatto
if [ "$STASHED" = "1" ]; then
  echo "→ Ripristino stash…"
  git stash pop 2>&1 | tail -3 || true
fi

# ──────────────────────────────────────────────────────────────────────────────
# Step 2 — rigenera pagine CEA daily
# ──────────────────────────────────────────────────────────────────────────────
CEA_DATES=$(ls snapshots/2026-*.json 2>/dev/null | sed -E 's|snapshots/||;s|\.json||' | sort -u | tail -30 | tr '\n' ' ')
if [ -n "$CEA_DATES" ] && [ -f "_automation/generate_cea_daily_pages.py" ]; then
  echo "→ Rigenero pagine CEA daily per: $CEA_DATES"
  python3 _automation/generate_cea_daily_pages.py $CEA_DATES 2>&1 | tail -8 || true
fi

# ──────────────────────────────────────────────────────────────────────────────
# Step 2b — applica branding + search + filtri semafori al repo med-tech-daily-check
#           (in background, non blocca il push principale se fallisce)
# ──────────────────────────────────────────────────────────────────────────────
if [ -f "_tools/apply-medtech-patch.sh" ]; then
  echo "→ Applico branding/search/filtri al repo med-tech-daily-check…"
  bash _tools/apply-medtech-patch.sh 2>&1 | tail -25 || echo "  (apply-medtech-patch.sh fallito — non blocca il push principale)"
else
  echo "  (apply-medtech-patch.sh non trovato — skip)"
fi

# ──────────────────────────────────────────────────────────────────────────────
# Step 3 — commit + push (solo se ci sono modifiche)
# ──────────────────────────────────────────────────────────────────────────────
git add -A
if git diff --cached --quiet; then
  echo "✓ Nessuna modifica da committare — repo già allineato."
  exit 0
fi

COMMIT_MSG="Daily refresh — $(date +%Y-%m-%d)"
echo "→ Commit: $COMMIT_MSG"
git -c user.email="moscadv@gmail.com" -c user.name="Francesco Maria Mosca" \
    commit -m "$COMMIT_MSG" 2>&1 | tail -3

echo "→ Push origin main…"
# Se il push fallisce perché qualcun altro ha pushato nel frattempo, ritenta
# una volta sola facendo pull --rebase -X theirs
if ! git push origin main 2>&1 | tee /tmp/dash-push.log | tail -5; then
  if grep -q "rejected" /tmp/dash-push.log 2>/dev/null; then
    echo "→ Push rejected, retry con pull --rebase…"
    git pull --rebase -X theirs origin main 2>&1 | tail -5 || true
    while git status --porcelain | grep -qE '^(UU|AA|UA|AU|DU|UD)'; do
      git status --porcelain | grep -E '^(UU|AA|UA|AU|DU|UD)' | awk '{print $2}' | while read -r f; do
        git checkout --theirs -- "$f" 2>/dev/null && git add "$f" 2>/dev/null
      done
      GIT_EDITOR=true git rebase --continue 2>&1 | tail -3 || { git rebase --abort; break; }
    done
    git push origin main 2>&1 | tail -5
  fi
fi

echo "✅ Daily refresh completato."
