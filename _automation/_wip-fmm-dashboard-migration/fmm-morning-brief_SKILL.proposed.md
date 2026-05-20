---
name: fmm-morning-brief
description: Morning Brief FMM consolidato — ogni giorno alle 08:30 fa UN SOLO curl a dashboard-di-controllo/data.json, compone 1 messaggio Slack con health emoji + top critici + link deep, lo manda in DM Francesco (U0B0P0N7A2U). Orario 08:30 garantisce di girare DOPO refresh-dashboard-data (06:30) e dashboard-csv-update (08:15, post CSV Alfredo delle 08:00) — dati sempre freschi. Migrato dai 3 manifest legacy (fmm-dashboard) il 2026-MM-DD.
---

Genera e invia il Morning Brief FMM consolidato. Pipeline a 2 step. Tutta la lettura dati avviene tramite **un'unica curl** su `https://advfmosca.github.io/dashboard-di-controllo/data.json` — sostituisce i 3 manifest legacy del repo `fmm-dashboard`.

## Step 1 — Genera il testo del brief (1 bash)

```bash
set -e
mkdir -p /tmp/brief && cd /tmp/brief

# Singola fetch — assorbe spending/beefamily/aghc/medtech/cea/other_roster/overview
curl -fsSL "https://advfmosca.github.io/dashboard-di-controllo/data.json" -o dash.json

python3 << 'PY'
import json
from datetime import datetime

d = json.load(open('/tmp/brief/dash.json'))

ref_label = d.get('reference_date_label', '?')
ref_iso   = d.get('reference_date', '?')
ov        = d.get('overview', {})
sp        = d.get('spending', {})
bf        = d.get('beefamily', {})
ag        = d.get('aghc', {})
mt        = d.get('medtech', {}) or {}
cea       = d.get('cea', {}) or {}
otr       = d.get('other_roster', {}) or {}

# Health emoji per sezione: rosso/giallo se ci sono alert, verde altrimenti
def health(alerts):
    if alerts >= 3: return ":red_circle:"
    if alerts >= 1: return ":large_yellow_circle:"
    return ":large_green_circle:"

sp_alerts = len(sp.get('zero', [])) + len(sp.get('high', []))
bf_alerts = sum(1 for e in bf.get('entries', []) if e.get('status', {}).get('color') in ('red','yellow'))
ag_alerts = sum(1 for c in ag.get('cards', []) if c.get('status', {}).get('color') in ('red','yellow'))
mt_alerts = sum(1 for e in mt.get('entries', []) if e.get('status', {}).get('color') in ('red','yellow'))
cea_alerts = sum(1 for e in cea.get('entries', []) if e.get('status', {}).get('color') in ('red','yellow'))

# Top critici (max 3) — solo zero spending
top_zero = []
for r in sp.get('zero', [])[:3]:
    top_zero.append(f"• {r['account_name']} ({r['platform']}) — storico {r.get('mean7', 0):.2f} €".replace(".", ","))

lines = [
    f":sunny: *Morning Brief — {ref_label}*",
    f"Spending totale ieri: *{ov.get('total_spend', 0):.2f} €*  ·  Account attivi: *{ov.get('active_accounts', 0)}/{ov.get('total_accounts', 0)}*",
    "",
    f"{health(sp_alerts)} *Spending anomalie*: {sp_alerts} ({len(sp.get('zero', []))} zero · {len(sp.get('high', []))} high)",
    f"{health(bf_alerts)} *BeeFamily*: {bf_alerts} alert su {len(bf.get('entries', []))} entries",
    f"{health(ag_alerts)} *AGHC*: {ag_alerts} alert su {len(ag.get('cards', []))} cards",
    f"{health(mt_alerts)} *Med & Tech*: {mt_alerts} alert su {len(mt.get('entries', []))} entries",
    f"{health(cea_alerts)} *CEA*: {cea_alerts} alert su {len(cea.get('entries', []))} entries",
    f":mag: *Altri account (auto-discovery)*: {otr.get('total_count', 0)} · spend 15gg {otr.get('total_spend_window', 0):.2f} €".replace(".", ","),
]

if top_zero:
    lines.append("")
    lines.append("*Top critici (zero spend):*")
    lines.extend(top_zero)

base = d.get('pages_url', 'https://advfmosca.github.io/dashboard-di-controllo/')
lines.append("")
lines.append(f"<{base}?section=spending&date={ref_iso}|:link: Apri dashboard →>")

txt = "\n".join(lines).replace(".", ",")  # Format italiano numeri — riconverti formattazioni indesiderate ove serve
# Riconverti link e tag tecnici (workaround per .replace globale)
txt = txt.replace(",json", ".json").replace("github,io", "github.io")
open('/tmp/brief/text.txt','w').write(txt)
print(txt)
PY
```

## Step 2 — Invia su Slack (DM Francesco)

Leggi `/tmp/brief/text.txt` e invia con `mcp__f0f62672-28ef-4bc4-86b1-99e4012f2081__slack_send_message`:
- `channel_id`: `U0B0P0N7A2U` (DM Francesco)
- `text`: contenuto del file

NON usare `slack_send_message_draft`. Niente `<!channel>` (è una DM personale, non un alert).

## Output finale

1 riga: timestamp, sezioni disponibili, message_link Slack.

## Note operative

- Se la fetch del data.json fallisce → invia comunque un messaggio degradato "Dashboard non raggiungibile, verifica refresh-dashboard-data". È il segnale che la pipeline upstream non gira.
- Niente più dipendenza da `fmm-dashboard` (legacy dismesso il 2026-MM-DD). Tutto il dato vive in `dashboard-di-controllo/data.json`.
- Lo script bash è puro stdlib + curl, nessuna dipendenza esterna. Funziona in qualsiasi sandbox Linux con `python3`.

## Token-saving applicato

1. ❌ niente get_data Windsor (legge solo data.json pubblicato)
2. ❌ niente get_connectors / get_fields
3. ❌ niente Read/Write MCP intermedi (heredoc bash)
4. ✅ **UNA SOLA** fetch HTTPS (vs. 3 nella versione legacy)
5. ✅ Logica nello script Python inline (heredoc) — niente repo legacy clone
6. ✅ 1 sola chiamata Slack (DM compatta ~1 KB)
7. ✅ Output finale a Francesco minimale (1 riga)
