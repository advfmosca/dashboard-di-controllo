#!/usr/bin/env bash
# Push della Dashboard di Controllo su GitHub PUBBLICO + attivazione GitHub Pages.
# Usa gh CLI già autenticato. Repo pubblico perché GitHub Pages su free plan
# richiede repo public (l'utente ha accettato questa visibilità).
#
# Lanciare con: bash push-to-github.sh

set -euo pipefail

REPO_NAME="dashboard-di-controllo"
REPO_DESC="Dashboard di Controllo FMM/AGHC — performance pubblicitarie quotidiane (snapshot 08:30 via Windsor.ai)"
COMMIT_MSG="Initial commit — Dashboard di Controllo unificata + first data.json snapshot"

cd "$(dirname "$0")"

echo "→ Verifica gh CLI autenticato…"
gh auth status >/dev/null 2>&1 || { echo "❌ gh CLI non autenticato. Lancia prima: gh auth login"; exit 1; }
GH_USER=$(gh api user --jq .login)
echo "  OK — utente: $GH_USER"

echo "→ Inizializzazione repo locale…"
if [ ! -d .git ]; then
  git init -b main
fi

git add .gitignore README.md index.html data.json push-to-github.sh build_data.py snapshots/ 2>/dev/null || git add .gitignore README.md index.html data.json push-to-github.sh build_data.py
git commit -m "$COMMIT_MSG" || echo "  (niente da committare)"

echo "→ Creazione repo PUBBLICO su GitHub e push…"
if gh repo view "$GH_USER/$REPO_NAME" >/dev/null 2>&1; then
  echo "  Repo $GH_USER/$REPO_NAME esiste già — push diretto"
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/$GH_USER/$REPO_NAME.git"
  fi
  git push -u origin main
else
  gh repo create "$REPO_NAME" \
    --public \
    --description "$REPO_DESC" \
    --source . \
    --push
fi

echo "→ Attivazione GitHub Pages (branch main, root)…"
# Tenta di creare la config Pages; se esiste già va comunque bene
gh api -X POST "repos/$GH_USER/$REPO_NAME/pages" \
  -H "Accept: application/vnd.github+json" \
  -f source[branch]=main \
  -f source[path]=/ \
  >/dev/null 2>&1 || echo "  (Pages già attiva o errore non bloccante)"

# Aspetta che la URL sia stabile e la stampa
sleep 2
PAGES_URL=$(gh api "repos/$GH_USER/$REPO_NAME/pages" --jq .html_url 2>/dev/null || echo "")
REPO_URL=$(gh repo view "$REPO_NAME" --json url -q .url)

echo ""
echo "✅ Fatto."
echo "   Repo:  $REPO_URL"
if [ -n "$PAGES_URL" ]; then
  echo "   Pages: $PAGES_URL"
  echo ""
  echo "⏱  Pages può impiegare 1–3 minuti per essere disponibile la prima volta."
  echo "   Apri Pages dal browser: $PAGES_URL"
else
  echo "   Pages: controlla manualmente Settings → Pages su $REPO_URL/settings/pages"
fi
