---
name: refresh-dashboard-data
description: Refresh quotidiano Dashboard di Controllo: 06:30 — 3 fetch Windsor (Meta+Google+TikTok, 16gg) → build_data.py → snapshots/ + data.json → git push → Slack loop (anomalie spending + bf_fermo). Assorbe alert-spending-anomalie-windsor + daily-check-beefamily + fmm-discover-other-accounts (dismissione fmm-dashboard 2026-05-19). MedTech/CEA gestiti da dashboard-csv-update (CSV Alfredo). Retention 90gg.
---

Refresh giornaliero della Dashboard di Controllo + creazione eventi Calendar per alert critici + loop Slack consolidato.

REPO = github.com/advfmosca/dashboard-di-controllo
PAGES = https://advfmosca.github.io/dashboard-di-controllo/
WORKSPACE = `/Users/francescomariamosca/Desktop/Dashboard di Controllo`

## 1) FETCH WINDSOR (3 chiamate parallele — Med & Tech rimosso 2026-05-19)

Tool `mcp__c87c8c90-4665-43dd-9bf9-8a1e72f5809a__get_data`. Tutte con `date_preset=last_16d`.

- **Meta full**: `connector=facebook`, `fields=["account_id","account_name","date","campaign","campaign_effective_status","spend","clicks","impressions","actions_landing_page_view","actions_page_engagement","actions_lead","actions_onsite_conversion_lead_grouped","account_status"]`
- **Google**: `connector=google_ads`, `fields=["account_id","account_name","date","campaign","spend","clicks","impressions"]`
- **TikTok**: `connector=tiktok`, `fields=["account_id","account_name","date","spend","clicks","impressions"]`

Med & Tech NON viene più letto da Windsor (account dismessi dal 2026-05-19). La sezione `data.medtech` viene popolata dallo scheduled task `dashboard-csv-update` (08:15) che legge i CSV di Alfredo.

I campi `campaign` (Meta+Google) + `campaign_effective_status` (Meta) permettono a `build_data.py` di costruire il breakdown campagne per le card BeeFamily.

Estrai PATH del file salvato dall'errore "Output has been saved to /var/folders/.../mcp-c87c8c90-...". Se inline, usa Write tool su `<workspace>/raw/<nome>.json`. Naming: meta.json, google.json, tiktok.json.

## 2) BUILD + PUSH (un'unica pipeline)

```bash
cd "/Users/francescomariamosca/Desktop/Dashboard di Controllo"
mkdir -p raw snapshots

[ -n "$META_RAW" ]  && cp "$META_RAW"  raw/meta.json    || true
[ -n "$GOOGLE_RAW" ] && cp "$GOOGLE_RAW" raw/google.json || true
[ -n "$TIKTOK_RAW" ] && cp "$TIKTOK_RAW" raw/tiktok.json || true

# --medtech ora opzionale: build_data.py tollera path inesistente / vuoto
# --owners opzionale: se presente, popola slack_target sulle azioni bf_fermo
python3 build_data.py \
  --meta raw/meta.json --google raw/google.json \
  --tiktok raw/tiktok.json \
  --aghc-vanity raw/meta.json \
  --aghc-budgets aghc_budgets.json \
  --owners owners.json \
  --workspace . --retention-days 90

git add data.json snapshots/ actions.json
if git diff --cached --quiet; then
  echo "NO_CHANGES=1"
else
  git commit -m "Daily refresh — $(date +%Y-%m-%d)" --quiet
  git push origin main --quiet
  echo "PUSHED=1"
fi

ACTIONS_N=$(python3 -c "import json; print(len(json.load(open('actions.json'))['actions']))")
echo "ACTIONS_COUNT=$ACTIONS_N"
```

NOTA: il file `aghc_budgets.json` è gestito a mano da Francesco e contiene budget_annuale + ytd_seed per ogni cliente AGHC. Se mancante, lo speso YTD viene calcolato solo sui giorni coperti dai dataset (best effort).

NOTA owners.json: file opzionale `{"meta_id_to_slack_user": {"<meta_id>": "<U...>"}}` per il mapping referenti BeeFamily. Se assente, le azioni `bf_fermo` usano fallback DM Francesco (U0B0P0N7A2U). All'attivazione consolidata, scaricarlo una volta da https://advfmosca.github.io/fmm-dashboard/scripts/owners.json e salvarlo nel workspace.

## 3) CALENDAR per ogni azione tipo high_spending / new_fermo

Se `ACTIONS_COUNT > 0`: leggi `actions.json`, **filtra solo `type in ("high_spending","new_fermo")`** (le altre sono per Slack — vedi step 3.5). Per ciascuna → `suggest_time` (prossimi 10 min liberi 9-18 EU/Roma) + `create_event` (title=action.title, description=action.details + URL ad account, durata 10 min). Tieni traccia degli slot occupati per evitare overlap. Skip duplicati: prima di create_event, `list_events` filtra per oggi e cerca lo stesso titolo.

## 3.5) SLACK LOOP (assorbe alert-spending-anomalie-windsor + daily-check-beefamily)

Per ogni `action` in `actions.json` che ha il campo `slack_target` non-null:

- Se `action.skip_if_quiet == true` AND `action.severity != "high"` → **skip** (riduzione rumore).
- Altrimenti invia: `mcp__f0f62672-28ef-4bc4-86b1-99e4012f2081__slack_send_message` con
  - `channel_id` = `action.slack_target`
  - `text`       = `action.slack_template`

NON usare `slack_send_message_draft`. In caso di 401/403 → bypassa quel canale e prosegui.

Ordine di invio: prima `type=spending_anomaly` (riepilogo canale #anomalie-spending), poi `type=bf_fermo` priority=high (nuovi fermi), infine eventuali `bf_fermo` priority=medium se sopravvissuti al filtro skip_if_quiet.

## 4) NOTIFICA FINALE (≤8 righe)

```
🔄 Dashboard aggiornata — <reference_date_label>
Spending totale: <X> · Account attivi: <A>/<T>
Alert: BeeFamily <bf_alerts> · AGHC <aghc_alerts>
Med&Tech + CEA: gestiti dal CSV daily (08:15)
Other accounts (auto-discovery): <other_count> · spend 15gg <other_spend> €
Eventi Calendar creati: <N> (high spending: <X> · new fermi: <Y>)
Slack inviati: spending=<S> · bf_fermo=<B>
Pages: https://advfmosca.github.io/dashboard-di-controllo/
```

## REGOLE
- Cron Europa/Roma 06:30 (app deve essere aperta)
- Percorsi assoluti
- Se actions.json contiene 0 azioni, salta step 3 e 3.5
- Non leggere più medtech da Windsor: account dismessi dal 2026-05-19
- Campi `campaign` + `campaign_effective_status` (Meta) e `campaign` (Google) necessari per breakdown campagne BeeFamily
- Le 3 task vecchie (`fmm-discover-other-accounts`, `alert-spending-anomalie-windsor`, `daily-check-beefamily`) sono state disabilitate il 2026-MM-DD a seguito della consolidazione. Loro logica vive ora in `build_data.py` + Slack loop step 3.5.
