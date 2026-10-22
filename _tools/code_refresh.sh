#!/usr/bin/env bash
# Dashboard di Controllo — refresh giornaliero, versione Claude Code (dal 22/10/2026).
#
# Da lanciare DOPO `python3 _tools/windsor_refresh.py harvest`, che ha già scritto
# i JSON Windsor in raw/ del workspace. Fa gli stessi passi della vecchia task Cowork:
#   1.5 clone fresco del repo in /tmp (mirror) e sync di data.json + snapshots nel workspace
#   2   build_data.py nel workspace → copia nel mirror
#   2B  build_aghc.py + build_actuals_monthly.py + build_budget.py nel mirror (mai bloccanti)
#   2C  commit + push SOLO dal mirror, poi verifica che origin/main sia il commit appena fatto
#        e che GitHub Pages serva il data.json nuovo.
#
# Uso:  bash _tools/code_refresh.sh            (tutto)
#       bash _tools/code_refresh.sh --skip-aghc (harvest ha stampato AGHC_OK=0: aghc_data resta quello di ieri)
#       bash _tools/code_refresh.sh --no-push   (prova: tutto tranne commit e push)
#
# Righe da leggere nell'output: MIRROR=, BUILD=, AGHC=, PUSH=, REMOTE_OK=, PAGES_OK=, ACTIONS_COUNT=

set -uo pipefail

WORKSPACE="${DASH_WORKSPACE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SKIP_AGHC=0; NO_PUSH=0
for arg in "$@"; do
  case "$arg" in
    --skip-aghc) SKIP_AGHC=1 ;;
    --no-push) NO_PUSH=1 ;;   # prova: build completa nel mirror, niente commit/push
  esac
done
MIRROR="/tmp/dashboard-mirror-$(date +%s)"
PAGES="https://advfmosca.github.io/dashboard-di-controllo"
AGHC_RAW="aghc_meta_current aghc_meta_prev aghc_meta_yoy aghc_meta_camp_current aghc_meta_camp_prev aghc_meta_camp_yoy aghc_meta_camp_monthly aghc_tiktok_current aghc_tiktok_prev aghc_meta_daily aghc_tiktok_daily aghc_monthly_meta aghc_monthly_tiktok"

# mirror dei giorni precedenti: si tengono solo gli ultimi 3 giorni
find /tmp -maxdepth 1 -name 'dashboard-mirror-*' -mtime +2 -exec rm -rf {} + 2>/dev/null || true

# ── 1.5 SYNC + MIRROR ────────────────────────────────────────────────────────
git clone --quiet --depth 5 "$(git -C "$WORKSPACE" config --get remote.origin.url)" "$MIRROR" 2>&1 \
  | sed -E 's|https://[^@]+@|https://***@|g'
if [ ! -f "$MIRROR/data.json" ]; then echo "❌ clone del repo fallito"; echo "PUSH=FAILED"; exit 1; fi
echo "MIRROR=$MIRROR"
cp "$MIRROR/data.json" "$WORKSPACE/data.json"
mkdir -p "$WORKSPACE/snapshots"
for f in "$MIRROR"/snapshots/*.json; do cp "$f" "$WORKSPACE/snapshots/" 2>/dev/null || true; done

# ── 2 BUILD data.json ────────────────────────────────────────────────────────
cd "$WORKSPACE" || exit 1
mkdir -p raw snapshots
if ! python3 build_data.py --meta raw/meta.json --google raw/google.json --tiktok raw/tiktok.json \
     --aghc-vanity raw/meta.json --aghc-budgets aghc_budgets.json --owners owners.json \
     --workspace . --retention-days 90; then
  echo "BUILD=FAILED"; echo "PUSH=FAILED"; exit 1
fi
echo "BUILD=OK"

cd "$MIRROR" || exit 1
git config user.email "moscadv@gmail.com"; git config user.name "Francesco Maria Mosca"
cp "$WORKSPACE/data.json" .; cp "$WORKSPACE/data-brief.json" . 2>/dev/null || true; cp "$WORKSPACE/actions.json" .
mkdir -p snapshots raw
cp "$WORKSPACE/snapshots/index.json" snapshots/ 2>/dev/null || true
for f in $(ls "$WORKSPACE/snapshots/" 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}\.json$' | sort -r | head -7); do
  cp "$WORKSPACE/snapshots/$f" snapshots/
done
# snapshot oltre i 90 giorni: build_data li ha tolti dal workspace, si tolgono anche dal repo
for f in $(ls snapshots/ 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}\.json$'); do
  [ -f "$WORKSPACE/snapshots/$f" ] || git rm -q "snapshots/$f" 2>/dev/null || true
done
for f in meta google tiktok; do cp "$WORKSPACE/raw/$f.json" raw/; done

# ── 2B / 2B-bis AGHC (mai bloccanti per data.json) ───────────────────────────
if [ "$SKIP_AGHC" = "1" ]; then
  echo "AGHC=SKIPPED (dati Windsor AGHC incompleti: resta aghc_data.json di ieri)"
else
  for f in $AGHC_RAW; do cp "$WORKSPACE/raw/$f.json" raw/ 2>/dev/null || true; done
  CUR=$(date +%Y-%m)
  PREV=$(python3 -c "import datetime;t=datetime.date.today().replace(day=1)-datetime.timedelta(days=1);print(t.strftime('%Y-%m'))")
  YOY=$(python3 -c "import datetime;d=datetime.date.today();print('%04d-%02d'%(d.year-1,d.month))")
  AGHC_STATUS=OK
  python3 "$MIRROR/build_aghc.py" --current-month "$CUR" --prev-month "$PREV" --yoy-month "$YOY" \
    --as-of-month "$PREV" --workspace "$MIRROR" || AGHC_STATUS="FAILED build_aghc"
  python3 "$MIRROR/build_actuals_monthly.py" "$MIRROR" || AGHC_STATUS="$AGHC_STATUS / FAILED build_actuals_monthly"
  python3 "$MIRROR/build_budget.py" --as-of-month "$PREV" --workspace "$MIRROR" || AGHC_STATUS="$AGHC_STATUS / FAILED build_budget"
  echo "AGHC=$AGHC_STATUS"
fi

# ── 2C COMMIT + PUSH (solo dal mirror) ───────────────────────────────────────
git add data.json data-brief.json actions.json snapshots/ aghc.html team.html build_aghc.py build_actuals_monthly.py \
  build_budget.py aghc_report_lib.py aghc_roster.json aghc_data.json aghc_actuals_monthly.json aghc_budget.json \
  raw/meta.json raw/google.json raw/tiktok.json 2>/dev/null || true
for f in $AGHC_RAW; do git add "raw/$f.json" 2>/dev/null || true; done

if [ "$NO_PUSH" = "1" ]; then
  git diff --cached --stat | tail -25
  echo "PUSH=SKIPPED (--no-push)"
  echo "ACTIONS_COUNT=$(python3 -c "import json;print(len(json.load(open('actions.json'))['actions']))")"
  exit 0
fi
if git diff --cached --quiet; then
  echo "PUSH=NO_CHANGES"
else
  git commit -m "Daily refresh — $(date +%Y-%m-%d)" --quiet
  if git push origin main --quiet 2>&1 | sed -E 's|https://[^@]+@|https://***@|g'; then echo "PUSH=PUSHED"; else echo "PUSH=FAILED"; fi
fi

LOCAL_HEAD=$(git rev-parse HEAD)
REMOTE_HEAD=$(git ls-remote origin main 2>/dev/null | cut -f1)
if [ "$LOCAL_HEAD" = "$REMOTE_HEAD" ]; then echo "REMOTE_OK=1"; else echo "REMOTE_OK=0 (locale $LOCAL_HEAD, remoto $REMOTE_HEAD)"; fi

# GitHub Pages ci mette di solito 1-2 minuti a ripubblicare: si aspetta fino a ~4 minuti
GEN=$(python3 -c "import json;print(json.load(open('data.json'))['generated_at'])")
PAGES_OK=0
for i in $(seq 1 12); do
  LIVE=$(curl -s -H 'Cache-Control: no-cache' "$PAGES/data.json?t=$(date +%s)" \
         | python3 -c "import json,sys;print(json.load(sys.stdin).get('generated_at',''))" 2>/dev/null || true)
  if [ "$LIVE" = "$GEN" ]; then PAGES_OK=1; break; fi
  sleep 20
done
echo "PAGES_OK=$PAGES_OK (generated_at $GEN)"

ACTIONS_N=$(python3 -c "import json;print(len(json.load(open('actions.json'))['actions']))")
echo "ACTIONS_COUNT=$ACTIONS_N"
