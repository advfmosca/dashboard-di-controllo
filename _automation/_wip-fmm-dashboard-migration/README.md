# WIP — Migrazione Fase B `fmm-dashboard` → `dashboard-di-controllo`

**Data**: 2026-05-19
**Owner**: Francesco Maria Mosca
**Esecuzione**: scheduled task `exec-fmm-dashboard-migration` (run automatico, utente non presente per conferma allo Step 6)

---

## STATO

Migrazione completata **in modalità WIP** secondo la regola:

> "Se utente non conferma allo Step 6, salva tutto come WIP in `_automation/_wip-fmm-dashboard-migration/` e termina senza disabilitare niente."

**Le 3 task vecchie restano abilitate.** Nessun push GitHub effettuato. Nessuna regressione possibile.

---

## COSA È STATO FATTO

### 1. Backup (Step 0) ✅ COMMITTED su disco
- `_backups/skills/*_2026-05-19.md` — 9 SKILL backuppati (eseguito in sessione precedente alle 14:48)
- `_backups/code/build_data.py.pre-migration.2026-05-19.bak` — snapshot di sicurezza creato adesso

### 2. `build_data.py` esteso ✅ APPLICATO E TESTATO
Modifiche live (già nel file `build_data.py` del workspace):

- Nuova costante `CEA_META_IDS` (set vuoto, placeholder esplicito per esclusione)
- Nuove costanti `SLACK_CHANNEL_ANOMALIE_SPENDING = "C0B2RE5KSHG"`, `SLACK_DM_FRANCESCO = "U0B0P0N7A2U"`
- Nuova funzione `_build_other_roster(meta_rows, meta_map, exclude_ids, y_iso, window_days=15)` che ritorna `{reference_date, window_days, accounts:[…], total_count, total_spend_window}`. Output esposto in `data.other_roster`.
- Esclude: BeeFamily meta_ids + AGHC meta_ids + MEDTECH_META_ACCOUNT + CEA_META_IDS + EXCLUDED_SPENDING
- Nuovo flag CLI `--owners <path>` per caricare mapping `meta_id → slack_user_id` (formato accettato: `{"meta_id_to_slack_user": {…}}` o root flat)
- `actions.json` ora include 2 nuovi tipi di action:
  - `spending_anomaly` (1 entry aggregata) → `slack_target=C0B2RE5KSHG`, `slack_template` pre-formattato con top 3 zero+spike
  - `bf_fermo` (N entry) → `slack_target=<owners[meta_id] or fallback U0B0P0N7A2U>`, `slack_template` con dettagli account
  - Le action esistenti `high_spending`/`new_fermo` restano invariate (no slack_target — vanno solo nel Calendar)

**Test eseguito sul dataset di oggi** (2026-05-18):
- 10 azioni totali: 5 high_spending, 2 new_fermo, 1 spending_anomaly, 2 bf_fermo
- `other_roster`: 3 account · 1.804,37 € spend 15gg (CIA ADV, Adv_maison rosabianca, PLAYAMAR SRLS)
- `data.json` 181KB, schema retrocompatibile

**Retrocompatibilità garantita**: nessun consumer attuale legge `spending_anomaly`/`bf_fermo`/`other_roster`, quindi build_data.py modificato NON rompe niente. I duplicati legacy (`fmm-discover-other-accounts` continua a popolare `fmm-dashboard/scripts/other_roster.json`, `alert-spending-anomalie-windsor` continua a mandare Slack, ecc.) restano attivi: zero regressioni.

### 3. SKILL.md proposti ⚠️ DA APPLICARE A MANO

Salvati in questa cartella per copia-incolla:

- `refresh-dashboard-data_SKILL.proposed.md` — aggiunge **Step 3.5 SLACK LOOP** + flag `--owners` nel comando build + nuova riga "Slack inviati" nella notifica finale
- `fmm-morning-brief_SKILL.proposed.md` — sostituisce 3 manifest legacy con **1 sola curl** a `dashboard-di-controllo/data.json`

**Motivo del rinvio**: la cartella `~/Documents/Claude/Scheduled/` NON è dentro le connected folders di questa sessione. L'agent ha potuto leggere le SKILL ma non scriverle. Per applicarle servono 2 file copy manuali (vedi sotto).

### 4. Disabilitazione 3 task vecchie ❌ NON ESEGUITA
Per regola WIP. Restano attive:
- `fmm-discover-other-accounts` (cron 06:00)
- `alert-spending-anomalie-windsor` (cron 07:00)
- `daily-check-beefamily` (cron 07:00)

### 5. Git push ❌ NON ESEGUITO
Per regola WIP.

---

## COSA FARE PER FINIRE LA MIGRAZIONE

In una nuova sessione Cowork con Francesco presente:

```bash
# 1. Applica gli SKILL proposti (terminale Mac):
cp "$HOME/Desktop/Dashboard di Controllo/_automation/_wip-fmm-dashboard-migration/refresh-dashboard-data_SKILL.proposed.md" \
   "$HOME/Documents/Claude/Scheduled/refresh-dashboard-data/SKILL.md"

cp "$HOME/Desktop/Dashboard di Controllo/_automation/_wip-fmm-dashboard-migration/fmm-morning-brief_SKILL.proposed.md" \
   "$HOME/Documents/Claude/Scheduled/fmm-morning-brief/SKILL.md"
```

```text
# 2. Chiedi a Claude in chat:
"Disabilita le 3 task vecchie post-migrazione fmm-dashboard:
 fmm-discover-other-accounts, alert-spending-anomalie-windsor, daily-check-beefamily
 con descrizione [DISABLED 2026-MM-DD] Sostituita da refresh-dashboard-data consolidato.
 Backup SKILL in _backups/skills/."

# 3. Chiedi a Claude di fare commit + push:
"Commit + push delle modifiche build_data.py della migrazione fase B con messaggio
 'feat: consolida other_roster + Slack alerts in refresh-dashboard-data (dismissione fmm-dashboard)'"
```

```bash
# 4. (Opzionale ma raccomandato) scarica owners.json una sola volta:
curl -fsSL "https://advfmosca.github.io/fmm-dashboard/scripts/owners.json" \
     -o "$HOME/Desktop/Dashboard di Controllo/owners.json"
```

Poi osserva il morning brief delle 08:30 del giorno successivo per validazione.

---

## ROLLBACK COMPLETO (se qualcosa non va dopo lo switch)

```bash
# 1. Ripristina SKILL dai backup
cp "$HOME/Desktop/Dashboard di Controllo/_backups/skills/refresh-dashboard-data_2026-05-19.md" \
   "$HOME/Documents/Claude/Scheduled/refresh-dashboard-data/SKILL.md"
cp "$HOME/Desktop/Dashboard di Controllo/_backups/skills/fmm-morning-brief_2026-05-19.md" \
   "$HOME/Documents/Claude/Scheduled/fmm-morning-brief/SKILL.md"

# 2. Ripristina build_data.py
cp "$HOME/Desktop/Dashboard di Controllo/_backups/code/build_data.py.pre-migration.2026-05-19.bak" \
   "$HOME/Desktop/Dashboard di Controllo/build_data.py"

# 3. Riabilita le 3 task vecchie (via Claude chat):
"Riabilita fmm-discover-other-accounts, alert-spending-anomalie-windsor, daily-check-beefamily"
```

Tempo totale rollback: ~3 minuti.

---

## VALIDAZIONE PRE-MIGRAZIONE GIÀ FATTA

- ✅ Backup SKILL pre-esistenti (9 file in `_backups/skills/`)
- ✅ Backup build_data.py creato (`_backups/code/build_data.py.pre-migration.2026-05-19.bak`, 86369 bytes)
- ✅ Sintassi `build_data.py` valida (ast.parse OK)
- ✅ Dry-run build_data.py con dati reali: actions=10, other_roster=3, JSON 181KB
- ⚠️ `data.json` online attuale **non contiene** sezioni `medtech`/`cea` (CSV Alfredo presumibilmente non popolato in tempo per la fetch del check); dopo la prossima run di `dashboard-csv-update` torneranno popolate
- ❌ `owners.json` non disponibile nel sandbox (repo `fmm-dashboard` legacy non montato); scaricarlo manualmente come da step 4 sopra

---

## FILE COINVOLTI

| File | Stato |
|---|---|
| `/Users/francescomariamosca/Desktop/Dashboard di Controllo/build_data.py` | MODIFICATO LIVE (retrocompatibile) |
| `/Users/francescomariamosca/Documents/Claude/Scheduled/refresh-dashboard-data/SKILL.md` | NON modificato (proposta in WIP) |
| `/Users/francescomariamosca/Documents/Claude/Scheduled/fmm-morning-brief/SKILL.md` | NON modificato (proposta in WIP) |
| `/Users/francescomariamosca/Documents/Claude/Scheduled/fmm-discover-other-accounts/SKILL.md` | NON modificato (rimane attivo) |
| `/Users/francescomariamosca/Documents/Claude/Scheduled/alert-spending-anomalie-windsor/SKILL.md` | NON modificato (rimane attivo) |
| `/Users/francescomariamosca/Documents/Claude/Scheduled/daily-check-beefamily/SKILL.md` | NON modificato (rimane attivo) |
