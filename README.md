# Dashboard di Controllo — FMM Consulting / AGHC

Dashboard live per il monitoraggio quotidiano delle performance pubblicitarie sui progetti gestiti da Francesco Maria Mosca:

- **BeeFamily** — 22 hotel/villaggi, account Meta + Google Ads
- **AGHC** — 18 hotel, account Meta + TikTok

Hostata su **GitHub Pages**, aggiornata automaticamente ogni mattina da una scheduled task Cowork.

## Architettura

1. **`index.html`** — single-page responsive (desktop + mobile) con 4 tab. Legge i dati da `data.json`.
2. **`data.json`** — snapshot precomputato dei dati di ieri (KPI, alert, status, recap). Viene rigenerato ogni giorno.
3. **`build_data.py`** — aggregator Python che trasforma i 3 dataset Windsor (Meta, Google, TikTok) in `data.json`.
4. **Scheduled task Cowork** (`refresh-dashboard-data`) — esegue Windsor MCP → build_data.py → git commit/push.

## Tab

1. **Overview Generale** — spending totale ieri (Meta + Google + TikTok), account attivi vs collegati, breakdown per piattaforma e per progetto
2. **Spending** — alert anomalie spending (zero anomalo, >50€/giorno, +30% vs media 7gg)
3. **BeeFamily** — KPI ieri, alert, status performance, recap copia-incolla
4. **AGHC** — idem

Ogni tab di progetto genera un **recap pronto per Slack** in ToV asciutto data-driven con tasto di copia diretto in clipboard.

## Status logic

Per **BeeFamily** e **AGHC** (campagne hotel/brand traffic):

- 🔴 **Rosso** — spesa ieri > 1.5x media 7gg
- 🟡 **Giallo** — spesa ieri 1.3–1.5x media 7gg, oppure < 0.4x (calo anomalo)
- 🟢 **Verde** — spesa ieri in linea con media 7gg
- ⚫ **Grigio** — account fermo ieri ma con storico, o totalmente inattivo

## Setup iniziale

```bash
cd ~/Desktop/Dashboard\ di\ Controllo
bash push-to-github.sh
```

Lo script:
1. Verifica `gh auth status`
2. Inizializza il repo locale
3. Crea il repo pubblico `dashboard-di-controllo` su GitHub
4. Attiva GitHub Pages su `main` branch / root
5. Stampa l'URL Pages

## Refresh manuale

Per rigenerare il `data.json` fuori orario (es. dopo aver corretto qualcosa nelle campagne):

1. Apri Cowork
2. Lancia manualmente la scheduled task `refresh-dashboard-data` (Settings → Scheduled tasks → Run now)

In alternativa, dal terminale (se hai i raw JSON nella cartella `raw/` aggiornati a mano):

```bash
python3 build_data.py \
  --meta raw/meta.json --google raw/google.json \
  --tiktok raw/tiktok.json \
  --workspace .
git add data.json && git commit -m "manual refresh" && git push
```

## Esclusioni

- `1576344015714351` (Color HolidayAds) e `533672775128363` sono **esclusi dal check spending alert** generico (cadenza/budget irregolari, account storici non più attivi).

## Author

Francesco Maria Mosca — FMM Consulting
