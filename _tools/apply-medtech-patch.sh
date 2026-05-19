#!/usr/bin/env bash
# Applica branding + layout uniforme al repo med-tech-daily-check e fa il push.
# VERSIONE ROBUSTA: usa uno script Python idempotente (niente git am fragile).
# Lanciare dal Terminal del Mac.

set -euo pipefail

PY_SCRIPT="$HOME/Desktop/Dashboard di Controllo/_tools/apply_medtech_branding.py"
WORK="$HOME/Desktop/_medtech-tmp"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  APPLICA BRANDING + LAYOUT MED & TECH DAILY CHECK"
echo "════════════════════════════════════════════════════════════════"
echo ""

# 1. Verifica script Python
echo "→ Verifico script Python..."
if [ ! -f "$PY_SCRIPT" ]; then
    echo "❌ Script non trovato: $PY_SCRIPT"
    exit 1
fi
echo "  OK"

# 2. Pulizia workdir precedente
echo "→ Pulizia cartella temporanea..."
rm -rf "$WORK"

# 3. Clone repo (sempre fresh)
echo "→ Clono med-tech-daily-check (fresh)..."
git clone https://github.com/advfmosca/med-tech-daily-check.git "$WORK" 2>&1 | tail -3

cd "$WORK"

# 4. Identity locale
echo "→ Imposto autore commit..."
git config user.email "moscadv@gmail.com"
git config user.name "Francesco Maria Mosca"

# 5. Applica trasformazioni Python (idempotenti)
echo "→ Applico branding + layout..."
python3 "$PY_SCRIPT" .

# 6. Commit + push solo se ci sono cambiamenti
if git diff --quiet && git diff --cached --quiet; then
    echo ""
    echo "ℹ️  Nessun cambiamento rispetto allo stato remoto — già applicato."
else
    echo "→ Commit + push..."
    git add -A
    git commit -m "Branding + layout uniforme alla Dashboard di Controllo: logo Med & Tech ufficiale, palette/spacing unificati, footer 'Snapshot generato...' rimosso, signature minimale"
    git push origin HEAD
fi

# 7. Cleanup
cd "$HOME"
rm -rf "$WORK"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  ✅ FATTO"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "GitHub Pages aggiorna in 1–2 minuti."
echo ""
echo "URL da verificare:"
echo "  • https://advfmosca.github.io/med-tech-daily-check/"
echo "  • https://advfmosca.github.io/med-tech-daily-check/med-tech-daily-2026-05-18.html"
echo ""
