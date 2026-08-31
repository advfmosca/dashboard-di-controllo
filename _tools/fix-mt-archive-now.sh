#!/usr/bin/env bash
# Fix one-shot: ricostruisce l'elenco "Report disponibili" del repo
# med-tech-daily-check scannando TUTTI i file med-tech-daily-*.html
# presenti, e fa il commit + push.
#
# Si ripara l'effetto del bug in generate_cea_daily_pages.py che, quando
# rigenerava solo un sottoinsieme di date (es. 19 + 20), sovrascriveva
# l'archivio nel repo lasciandone fuori i giorni precedenti.
#
# Lanciare dal Terminal del Mac:
#   bash "$HOME/Desktop/COWORK FMM/Dashboard di Controllo/_tools/fix-mt-archive-now.sh"

set -euo pipefail

WORK="$HOME/Desktop/_mtcheck-fix-tmp"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  FIX archivio med-tech-daily-check (ripristina giorni mancanti)"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Pulizia
rm -rf "$WORK"

echo "→ Clono med-tech-daily-check..."
git clone https://github.com/advfmosca/med-tech-daily-check.git "$WORK" 2>&1 | tail -3

cd "$WORK"
git config user.email "moscadv@gmail.com"
git config user.name "Francesco Maria Mosca"

echo "→ Ricostruisco archivio leggendo TUTTI i daily file presenti..."
python3 << 'PY'
import re
from pathlib import Path
from datetime import datetime

GIORNI = ["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato","Domenica"]
MESI = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]

def date_label(iso):
    dt = datetime.strptime(iso, "%Y-%m-%d")
    return f"{GIORNI[dt.weekday()]} {dt.day} {MESI[dt.month-1]} {dt.year}"

files = sorted([p for p in Path('.').glob('med-tech-daily-*.html')
                if re.match(r'med-tech-daily-\d{4}-\d{2}-\d{2}\.html$', p.name)],
               reverse=True)
print(f'  Trovati {len(files)} file daily:')
for f in files: print(f'    - {f.name}')

def grab_count(text, cls):
    m = re.search(rf'<div class="ss-cell {cls}".*?<div class="val">(\d+)</div>', text, re.DOTALL)
    return m.group(1) if m else '0'

items_html = []
for f in files:
    iso = re.match(r'med-tech-daily-(\d{4}-\d{2}-\d{2})\.html$', f.name).group(1)
    txt = f.read_text(encoding='utf-8')
    r = grab_count(txt, 'rosso'); g = grab_count(txt, 'giallo')
    v = grab_count(txt, 'verde'); n = grab_count(txt, 'nero')
    label = date_label(iso)
    items_html.append(
        f'    <a class="report-item" href="{f.name}">\n'
        f'      <span class="day-name">{label}</span>\n'
        f'      <span class="counts"><span class="c-r">{r}R</span> · '
        f'<span class="c-g">{g}G</span> · '
        f'<span class="c-v">{v}V</span> · '
        f'<span class="c-n">{n}N</span></span>\n'
        f'      <span class="arrow">→</span>\n'
        f'    </a>'
    )

arch_path = Path('med-tech-daily-check.html')
arch = arch_path.read_text(encoding='utf-8')

m = re.search(r'<div class="report-list">.*?</div>\s*\n\s*<div class="empty', arch, re.DOTALL)
if not m:
    print('  ✗ Blocco report-list non trovato nell\'archivio'); raise SystemExit(1)
old_block = m.group(0)
new_block = '<div class="report-list">\n' + '\n'.join(items_html) + '\n  </div>\n  <div class="empty'
arch = arch.replace(old_block, new_block)
arch_path.write_text(arch, encoding='utf-8')
print(f'  ✓ Archivio ricostruito con {len(items_html)} voci')
PY

if git diff --quiet med-tech-daily-check.html; then
  echo ""
  echo "ℹ️  L'archivio era già allineato — nessuna modifica."
else
  echo "→ Commit + push del fix..."
  git add med-tech-daily-check.html
  git commit -m "fix(archive): ripristina elenco completo (auto-rebuild aveva perso giorni)"
  git push origin HEAD
fi

cd "$HOME"
rm -rf "$WORK"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  ✅ FATTO"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "GitHub Pages si aggiorna in 1–2 minuti."
echo "Verifica: https://advfmosca.github.io/med-tech-daily-check/"
echo ""
