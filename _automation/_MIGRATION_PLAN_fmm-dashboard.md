# Piano migrazione `fmm-dashboard` → `dashboard-di-controllo`

**Stato**: PIANIFICATO — esecuzione prevista al prossimo reset token  
**Data piano**: 2026-05-19  
**Owner**: Francesco Maria Mosca  
**Obiettivo**: ridurre da 10 → 6 scheduled task daily, eliminare doppia dashboard, risparmio token stimato 50-60%

---

## CONTESTO

Ad oggi (2026-05-19) coesistono 2 dashboard:

1. **`fmm-dashboard`** (legacy) — alimenta sezioni `spending`, `beefamily`, `aghc`, `other_roster` via 3 scheduled task separate
2. **`dashboard-di-controllo`** (master) — alimenta sezioni `overview`, `spending`, `beefamily`, `aghc`, `medtech`, `cea` via `refresh-dashboard-data` + `dashboard-csv-update`

`fmm-morning-brief` (08:00 daily) legge i manifest da `fmm-dashboard`.

Decisione: **dismettere `fmm-dashboard`** e consolidare tutto su `dashboard-di-controllo`.

---

## SCHEDULED TASK COINVOLTE

### Da consolidare (assorbite da `refresh-dashboard-data`)
- `fmm-discover-other-accounts` (cron `0 6 * * *`) → scrive `fmm-dashboard/scripts/other_roster.json`
- `alert-spending-anomalie-windsor` (cron `0 7 * * *`) → scrive `fmm-dashboard/docs/data/spending/*.json` + Slack `#anomalie-spending` (C0B2RE5KSHG)
- `daily-check-beefamily` (cron `0 7 * * *`) → scrive `fmm-dashboard/actions.json` + loop Slack DM per account BF fermo

### Da modificare (puntare al nuovo)
- `refresh-dashboard-data` (cron `30 6 * * *`) — assorbe la logica delle 3 sopra
- `fmm-morning-brief` (cron `0 8 * * *`) — legge da `dashboard-di-controllo/data.json` invece di 3 manifest

### Mantengono uguale
- `dashboard-csv-update` (07:30) — gestisce CEA + medtech via CSV
- `three-day-check-aghc` (ogni 3gg 07:00) — già scrive `dashboard-di-controllo`
- Tutte le altre weekly/monthly/marketing

---

## STEP DI ESECUZIONE

### Step 1 — Estendi `build_data.py` per gestire `data.other_roster`

In `build_data.py` aggiungere funzione `_build_other_roster(meta_rows)` che:
- Prende lista account Meta da `raw/meta.json`
- Esclude account già in BEEFAMILY + AGHC + ID medtech `533672775128363`
- Esclude account di CEA (i clienti CEA sono nei CSV di Alfredo, non in Windsor)
- Esporta `data.other_roster` = lista `{account_id, account_name, spend_window_15d, spend_y}`

### Step 2 — Estendi `build_data.py` per gestire Slack alerts BF + spending

Modificare `actions.json` output per includere:
- Account BF fermi (campagne stop, billing issue) → ogni entry ha `slack_dm_to: <user_id_cliente>` e `slack_message: <template>`
- Anomalie spending (zero anomalo + sopra soglia) → entry per Slack `#anomalie-spending` (C0B2RE5KSHG)

### Step 3 — Aggiorna SKILL `refresh-dashboard-data`

Nuova logica (sostituisce sezioni esistenti):

```markdown
## 1) FETCH WINDSOR (3 chiamate parallele)
[invariato]

## 2) BUILD + PUSH
[invariato]

## 3) SLACK LOOP (assorbe alert-spending-anomalie-windsor + daily-check-beefamily)

Per ogni azione in actions.json:
- type=spending_anomaly → slack_send_message channel=C0B2RE5KSHG con template top3
- type=bf_fermo → slack_send_message DM al user_id del cliente con messaggio standard

## 4) CALENDAR per ogni azione critica
[invariato]

## 5) NOTIFICA FINALE
[invariato]
```

### Step 4 — Aggiorna SKILL `fmm-morning-brief`

Sostituire la lettura dei 3 manifest con un'unica fetch:

```bash
curl -fsSL "https://advfmosca.github.io/dashboard-di-controllo/data.json" -o /tmp/dash.json
# Estrai sezioni: spending, beefamily, aghc, medtech, cea, overview
python3 << 'PY'
import json
d = json.load(open('/tmp/dash.json'))
# Build brief message...
PY
```

### Step 5 — Backup + disabilita le 3 vecchie

```python
# Per ognuna:
update_scheduled_task(taskId="fmm-discover-other-accounts", enabled=False,
    description="[DISABLED 2026-MM-DD] Sostituita da refresh-dashboard-data. Mantenuta per rollback.")
update_scheduled_task(taskId="alert-spending-anomalie-windsor", enabled=False, ...)
update_scheduled_task(taskId="daily-check-beefamily", enabled=False, ...)
```

### Step 6 — Verifica giorno successivo

- Confronta `dashboard-di-controllo/data.json` con vecchio `fmm-dashboard/docs/data/spending/*.json`
- Verifica messaggio morning brief contenga: spending top 3 + BF alerts + AGHC alerts
- Se differenze: rollback (riabilita le 3 vecchie)

---

## FILES DA MODIFICARE

- `build_data.py` → +2 funzioni (other_roster, slack_actions_bf, slack_actions_spending)
- `/Users/francescomariamosca/Documents/Claude/Scheduled/refresh-dashboard-data/SKILL.md` → +Step 3 Slack
- `/Users/francescomariamosca/Documents/Claude/Scheduled/fmm-morning-brief/SKILL.md` → fetch unico
- Scheduled tasks updates via MCP: 5 task

## ROLLBACK PLAN

Se qualcosa non va dopo lo switch:
1. `enabled=True` per `fmm-discover-other-accounts`, `alert-spending-anomalie-windsor`, `daily-check-beefamily`
2. Revert commit su `dashboard-di-controllo` (git revert <commit-hash>)
3. Revert SKILL.md `refresh-dashboard-data` + `fmm-morning-brief` (Git history dello SKILL repo)
4. Tempo totale rollback: ~3 minuti

## CHECKLIST PRE-ESECUZIONE

- [ ] Avere accesso a `/Users/francescomariamosca/Documents/Claude/Scheduled/` montato in Cowork
- [ ] Confermare che `daily-check-beefamily` ha logica Slack DM per cliente (vedere SKILL)
- [ ] Avere il PAT GitHub fresh (vedi `github-pat-rotation-reminder` 11/08/2026)
- [ ] Avere il channel_id Slack: #anomalie-spending = C0B2RE5KSHG; DM Francesco = U0B0P0N7A2U
- [ ] Confermare che `dashboard-di-controllo/data.json` ha già `overview/spending/beefamily/aghc/medtech/cea` (verificato 2026-05-19 ✓)

## TOKEN STIMATI

- Pre-work: ~5k token (questa scrittura)
- Esecuzione: ~30-40k token (3 SKILL writes + test + push)
- Verifica giorno successivo: ~5k token

Totale ~50k token per la migrazione completa.

## RISPARMIO POST-MIGRAZIONE

- Eliminate 3 Claude runs/giorno (~30k token/giorno)
- Brief più veloce (1 fetch invece di 3) (~5k/giorno)
- ROI: ~35k token/giorno = ~1M token/mese risparmiati

---

## COSA RIPRENDERE NELLA PROSSIMA SESSIONE

Apri una nuova sessione Cowork e dì a Claude:

> "Esegui la Fase B della dismissione fmm-dashboard come da piano in 
> `/Users/francescomariamosca/Desktop/Dashboard di Controllo/_automation/_MIGRATION_PLAN_fmm-dashboard.md`. 
> Segui gli Step 1-6, fammi confermare prima di disabilitare le 3 task vecchie."

Claude leggerà questo documento, eseguirà gli step, e ti chiederà conferma prima del punto di non ritorno (Step 5).
