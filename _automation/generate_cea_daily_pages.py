#!/usr/bin/env python3
"""
Genera pagine HTML cea-daily-YYYY-MM-DD.html dagli snapshot data.cea della
dashboard di controllo. Stessa palette e layout di med-tech-daily-XX.html.

Uso:
  python3 _automation/generate_cea_daily_pages.py 2026-05-15 2026-05-16 2026-05-17

Output:
  - cea-daily-<data>.html nel root del repo Dashboard di Controllo
  - cea-daily-check.html  (indice archivio, sostituito ogni run)
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Orario di esecuzione (= orario di lettura/processing dei CSV di Alfredo)
EXECUTION_DT = datetime.now()
EXECUTION_LABEL = EXECUTION_DT.strftime("%H:%M")
EXECUTION_DATE_LABEL = EXECUTION_DT.strftime("%d/%m/%Y")

ROOT = Path(__file__).resolve().parent.parent  # /Dashboard di Controllo
SNAP_DIR = ROOT / "snapshots"

LOGO_CEA = None  # Loghi disabilitati su richiesta utente — header solo testo

# Mappa color → classe italiana (replica medtech style)
COL2CLS = {"red": "rosso", "yellow": "giallo", "green": "verde", "gray": "nero", "black": "nero"}

WEEKDAYS_IT = ["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato","Domenica"]
MONTHS_IT   = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]

CSS_BLOCK = """
:root {
  color-scheme: light;
  --bg: #ffffff;
  --bg-soft: #fafafa;
  --bg-card: #ffffff;
  --border: #ececef;
  --border-soft: #f4f4f5;
  --text: #1c1c1e;
  --text-muted: #6b6b70;
  --text-dim: #8a8a90;
  --red: #d93025;
  --yellow: #f5a623;
  --green: #1e8e3e;
  --gray: #9a9aa0;
  --black: #1a1a1a;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); }
body {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  font-size: 14px;
  line-height: 1.45;
}
.wrap { max-width: 1080px; margin: 0 auto; padding: 18px 20px 60px; }

.brand-header { text-align: center; margin: 4px 0 14px; padding: 14px 18px; background: var(--bg-soft); border: 1px solid var(--border); border-radius: 12px; }
h1 { font-size: 22px; font-weight: 700; letter-spacing: -0.01em; margin: 0 0 4px; }
.subtitle { color: var(--text-muted); font-size: 12.5px; margin: 0 0 18px; }

/* KPI in alto */
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin-bottom: 14px; }
.kpi { background: var(--bg-soft); border: 1px solid var(--border); border-radius: 10px; padding: 13px 15px; min-width: 0; }
.kpi .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 6px; font-weight: 600; }
.kpi .value { font-size: 24px; font-weight: 700; line-height: 1.1; color: #0f0f10; font-variant-numeric: tabular-nums; }
.kpi.total { background: #1c1c1e; border-color: #1c1c1e; }
.kpi.total .label { color: #b8b8bf; }
.kpi.total .value { color: #fff; }

/* Conteggi semafori 4 colonne — CLICCABILI come filtro */
.sem-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; }
.sem-grid .kpi { padding: 11px 13px; cursor: pointer; user-select: none; transition: transform .15s, box-shadow .15s, opacity .15s; }
.sem-grid .kpi:hover { transform: translateY(-1px); box-shadow: 0 2px 6px rgba(0,0,0,.08); }
.sem-grid .kpi.active-filter { outline: 3px solid #1c1c1e; outline-offset: -3px; }
.sem-grid.has-active .kpi:not(.active-filter) { opacity: 0.42; }
.sem-grid .kpi.rosso  { background: #fee2e2; border-color: #fca5a5; }
.sem-grid .kpi.rosso  .label { color: #991b1b; }
.sem-grid .kpi.rosso  .value { color: #991b1b; }
.sem-grid .kpi.giallo { background: #ffedd5; border-color: #fed7aa; }
.sem-grid .kpi.giallo .label { color: #9a3412; }
.sem-grid .kpi.giallo .value { color: #9a3412; }
.sem-grid .kpi.verde  { background: #d1fadf; border-color: #86efac; }
.sem-grid .kpi.verde  .label { color: #14532d; }
.sem-grid .kpi.verde  .value { color: #14532d; }
.sem-grid .kpi.nero   { background: #1a1a1a; border-color: #1a1a1a; }
.sem-grid .kpi.nero   .label { color: #b8b8bf; }
.sem-grid .kpi.nero   .value { color: #fff; }

/* Search bar */
.search-bar { display: flex; align-items: center; gap: 10px; margin: 0 0 14px; padding: 10px 14px; background: var(--bg-soft); border: 1px solid var(--border); border-radius: 10px; flex-wrap: wrap; }
.search-bar .search-ico { font-size: 14px; color: var(--text-muted); flex-shrink: 0; }
.search-bar input[type="search"] { flex: 1; font: inherit; font-size: 13px; padding: 6px 8px; border: 0; background: transparent; color: var(--text); outline: none; min-width: 160px; }
.search-bar input[type="search"]::placeholder { color: var(--text-dim); }
.search-bar .filter-count { font-size: 11.5px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.search-bar .clear-btn { font: inherit; font-size: 11px; padding: 4px 10px; border-radius: 999px; border: 1px solid #d2d2d7; background: #fff; color: var(--text-muted); cursor: pointer; flex-shrink: 0; }
.search-bar .clear-btn:hover { background: #f5f5f7; color: var(--text); }
.search-bar .clear-btn.hidden { display: none; }
.empty-result { padding: 20px; text-align: center; color: var(--text-dim); font-style: italic; font-size: 13px; background: var(--bg-soft); border-radius: 10px; border: 1px dashed var(--border); }

/* ─── HERO STATO SALUTE ─── */
.smart-summary { display: grid; grid-template-columns: 1.4fr 1fr 1fr 1fr 1fr; gap: 12px; padding: 16px; background: #fff; border: 1px solid var(--border); border-radius: 14px; margin-bottom: 14px; align-items: stretch; }
.smart-summary .ss-hero { background: linear-gradient(135deg, #1c1c1e 0%, #2c2c2e 100%); border-radius: 10px; padding: 14px 16px; color: #fff; display: flex; flex-direction: column; justify-content: center; }
.smart-summary .ss-hero .lbl { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #b8b8bf; }
.smart-summary .ss-hero .val { font-size: 32px; font-weight: 800; line-height: 1.05; margin: 2px 0 1px; font-variant-numeric: tabular-nums; }
.smart-summary .ss-hero .sub { font-size: 11.5px; color: #d1d5db; }
.smart-summary .ss-cell { padding: 10px 12px; border-radius: 10px; cursor: pointer; user-select: none; transition: transform .15s, box-shadow .15s, opacity .15s; display: flex; flex-direction: column; gap: 3px; }
.smart-summary .ss-cell:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.smart-summary .ss-cell.active-filter { outline: 3px solid #1c1c1e; outline-offset: -3px; }
.smart-summary.has-active .ss-cell:not(.active-filter):not(.ss-hero) { opacity: 0.42; }
.smart-summary .ss-cell .ico { font-size: 16px; line-height: 1; }
.smart-summary .ss-cell .lbl { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
.smart-summary .ss-cell .val { font-size: 24px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.smart-summary .ss-cell .micro { font-size: 10.5px; opacity: 0.85; }
.smart-summary .ss-cell.rosso  { background: #fee2e2; color: #991b1b; }
.smart-summary .ss-cell.giallo { background: #ffedd5; color: #9a3412; }
.smart-summary .ss-cell.verde  { background: #d1fadf; color: #14532d; }
.smart-summary .ss-cell.nero   { background: #1a1a1a; color: #fff; }
@media (max-width: 820px) {
  .smart-summary { grid-template-columns: 1fr 1fr; }
  .smart-summary .ss-hero { grid-column: 1 / -1; }
}

/* ─── CARD RIPROGETTATA ─── */
.card-new { background: #fff; border: 1px solid var(--border); border-radius: 14px; padding: 0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.04); display: flex; flex-direction: column; margin-bottom: 12px; }
.card-new.rosso  { border-top: 5px solid var(--red); }
.card-new.giallo { border-top: 5px solid var(--yellow); }
.card-new.verde  { border-top: 5px solid var(--green); }
.card-new.nero   { border-top: 5px solid var(--black); }
.card-new .nc-hero { padding: 14px 16px 10px; }
.card-new.rosso  .nc-hero { background: linear-gradient(180deg, #fff5f5 0%, #fff 100%); }
.card-new.giallo .nc-hero { background: linear-gradient(180deg, #fffaf0 0%, #fff 100%); }
.card-new.verde  .nc-hero { background: linear-gradient(180deg, #f0fdf4 0%, #fff 100%); }
.card-new.nero   .nc-hero { background: linear-gradient(180deg, #f5f5f7 0%, #fff 100%); }
.card-new .nc-status-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
.card-new .nc-status { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 700; letter-spacing: 0.02em; padding: 4px 10px; border-radius: 999px; }
.card-new.rosso  .nc-status { background: #fee2e2; color: #991b1b; }
.card-new.giallo .nc-status { background: #ffedd5; color: #9a3412; }
.card-new.verde  .nc-status { background: #d1fadf; color: #14532d; }
.card-new.nero   .nc-status { background: #1a1a1a; color: #fff; }
.card-new .nc-status .ico { font-size: 13px; }
.card-new .nc-since { font-size: 11px; color: var(--text-muted); margin-left: auto; }
.card-new .nc-name { font-size: 15px; font-weight: 700; line-height: 1.25; margin: 0; word-break: break-word; }
.card-new .nc-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(105px, 1fr)); gap: 8px; padding: 0 16px 14px; }
.card-new .nc-kpi { background: var(--bg-soft); border-radius: 8px; padding: 8px 10px; }
.card-new .nc-kpi .lbl { font-size: 9.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }
.card-new .nc-kpi .val { font-size: 17px; font-weight: 800; color: #0f0f10; line-height: 1.1; margin-top: 2px; font-variant-numeric: tabular-nums; }
.card-new .nc-kpi .delta { font-size: 11px; font-weight: 600; margin-top: 2px; color: var(--text-muted); }
.card-new .nc-kpi .delta.up   { color: var(--red); }
.card-new .nc-kpi .delta.down { color: var(--green); }
.card-new .nc-kpi.highlight   { background: linear-gradient(135deg, #1c1c1e 0%, #2c2c2e 100%); }
.card-new .nc-kpi.highlight .lbl { color: #b8b8bf; }
.card-new .nc-kpi.highlight .val { color: #fff; }
.card-new .nc-kpi.highlight .delta { color: #d1d5db; }
.card-new .nc-body { padding: 12px 16px 0; border-top: 1px solid var(--border-soft); }
.card-new .nc-section-lbl { font-size: 9.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin: 6px 0 4px; }
.card-new .nc-story { font-size: 13px; line-height: 1.55; color: #2c2c2c; margin: 0; }
.card-new .nc-action { display: flex; gap: 10px; padding: 12px 16px; background: var(--bg-soft); border-top: 1px solid var(--border-soft); margin-top: 12px; }
.card-new .nc-action .arrow { font-size: 16px; line-height: 1.2; flex-shrink: 0; }
.card-new.rosso  .nc-action .arrow { color: var(--red); }
.card-new.giallo .nc-action .arrow { color: var(--yellow); }
.card-new.verde  .nc-action .arrow { color: var(--green); }
.card-new.nero   .nc-action .arrow { color: #555; }
.card-new .nc-action .text { font-size: 13px; line-height: 1.5; color: #2c2c2c; flex: 1; }
.card-new .nc-action .text b { color: #1c1c1e; }
.card-new details { padding: 8px 16px 14px; font-size: 12.5px; color: var(--text-muted); border-top: 1px dashed var(--border-soft); }
.card-new details summary { cursor: pointer; user-select: none; font-weight: 600; color: var(--text); list-style: none; padding: 4px 0; }
.card-new details summary::-webkit-details-marker { display: none; }
.card-new details summary::before { content: "▸ "; color: var(--text-dim); display: inline-block; transition: transform .15s; }
.card-new details[open] summary::before { transform: rotate(90deg); }
.card-new details .det-content { padding: 6px 0 0; line-height: 1.55; }
.card-new details .det-content b { color: var(--text); }

.legend { display: flex; flex-wrap: wrap; gap: 8px 14px; font-size: 12px; color: var(--text-muted); background: var(--bg-soft); border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; margin-bottom: 18px; }
.legend .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.dot-rosso { background: var(--red); }
.dot-giallo { background: var(--yellow); }
.dot-verde { background: var(--green); }
.dot-nero  { background: var(--black); }

.cards { display: flex; flex-direction: column; gap: 12px; }
.card { background: var(--bg-card); border: 1px solid var(--border); border-left-width: 4px; border-radius: 12px; padding: 14px 16px; }
.card.rosso  { border-left-color: var(--red); }
.card.giallo { border-left-color: var(--yellow); }
.card.verde  { border-left-color: var(--green); }
.card.nero   { border-left-color: var(--black); }
.card-head { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.tag { display: inline-block; font-size: 10.5px; font-weight: 700; letter-spacing: .04em; padding: 2px 8px; border-radius: 999px; color: #fff; flex-shrink: 0; }
.tag.rosso  { background: var(--red); }
.tag.giallo { background: var(--yellow); color: var(--text); }
.tag.verde  { background: var(--green); }
.tag.nero   { background: var(--black); }
.camp-name { font-weight: 700; font-size: 14px; flex: 1; }
.meta { color: var(--text-muted); font-size: 12.5px; margin-top: 6px; }
.reason { font-size: 12.5px; color: #2c2c2c; margin-top: 8px; line-height: 1.55; padding: 9px 11px; background: var(--bg-soft); border-radius: 8px; }
.r-cpl  { font-size: 12.5px; color: #2c2c2c; line-height: 1.55; margin-top: 8px; padding: 9px 11px; background: var(--bg-soft); border-radius: 8px; border-left: 3px solid #0866FF; }
.r-perf { font-size: 12.5px; color: #2c2c2c; line-height: 1.55; margin-top: 8px; padding: 9px 11px; background: #fffaf0; border-radius: 8px; border-left: 3px solid var(--yellow); }
.r-perf strong { color: #1c1c1e; }

/* Index list */
.section-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin: 14px 0 10px; }
.report-list { display: flex; flex-direction: column; gap: 4px; list-style: none; padding: 0; }
.report-list a.report-item { display: flex; align-items: center; gap: 10px; padding: 11px 14px; border-radius: 10px; text-decoration: none; color: var(--text); border: 1px solid var(--border); background: #fff; transition: background .15s, border-color .15s; }
.report-list a.report-item:hover { background: var(--bg-soft); border-color: #d2d2d7; }
.report-list .day-name { font-weight: 600; font-size: 13.5px; }
.report-list .day-counts { font-size: 12.5px; color: var(--text-muted); margin-left: 12px; font-variant-numeric: tabular-nums; }
.report-list .day-counts .c-rosso  { color: var(--red);   font-weight: 700; }
.report-list .day-counts .c-giallo { color: #b88a00;      font-weight: 700; }
.report-list .day-counts .c-verde  { color: var(--green); font-weight: 700; }
.report-list .day-counts .c-nero   { color: #444;         font-weight: 700; }
.report-list .arrow { margin-left: auto; color: var(--text-dim); font-size: 18px; }

.signature { font-size: 11.5px; color: var(--text-dim); margin-top: 28px; padding-top: 14px; border-top: 1px solid var(--border-soft); text-align: center; letter-spacing: 0.02em; }
"""

def fmt_eur(v):
    if v is None: return "—"
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " €"

def fmt_int(n):
    if n is None: return "0"
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)

def fmt_date_long(iso):
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{WEEKDAYS_IT[d.weekday()]} {d.day} {MONTHS_IT[d.month - 1]} {d.year}"

def escape_html(s):
    if s is None: return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))

# Etichette "umane" per stato e fase campagna
STATE_LABEL = {
    "rosso":  ("Da rivedere",  "🔴"),
    "giallo": ("Da monitorare","🟡"),
    "verde":  ("In linea",     "🟢"),
    "nero":   ("Spenta",       "⚫"),
}

def render_daily(date_iso, cea):
    kpi = cea.get("kpi", {})
    entries = cea.get("entries", [])
    title_date = fmt_date_long(date_iso)
    rosso = kpi.get("rosso", 0); giallo = kpi.get("giallo", 0)
    verde = kpi.get("verde", 0); nero   = kpi.get("nero", 0)
    total_camp = len(entries) if entries else (rosso + giallo + verde + nero)
    # Stato salute = verde / totale
    salute_pct = int(round(verde / total_camp * 100)) if total_camp > 0 else 0

    cards_html = []
    for e in entries:
        col = e.get("status", {}).get("color", "gray")
        cls = COL2CLS.get(col, "nero")
        human_label, icon = STATE_LABEL.get(cls, ("—", "·"))
        reason = e.get("status", {}).get("reason", "")
        name = e.get("name", "—")
        spend = e.get("spend_y", 0)
        lead = e.get("lead_y", 0)
        cpl = e.get("cpl_y")
        cpl_m3 = e.get("cpl_mean_3d")
        narrative = e.get("cpl_narrative") or ""
        perf_eval = e.get("performance_eval") or ""

        # Δ CPL vs media 3gg
        delta_html = ""
        if cpl is not None and cpl_m3 is not None and cpl_m3 > 0:
            delta_pct = (cpl - cpl_m3) / cpl_m3 * 100
            if delta_pct >= 5:
                delta_html = f'<div class="delta up">+{delta_pct:.0f}% vs media 3gg</div>'
            elif delta_pct <= -5:
                delta_html = f'<div class="delta down">{delta_pct:.0f}% vs media 3gg</div>'
            else:
                delta_html = f'<div class="delta">In linea con media 3gg</div>'

        # KPI in evidenza: il primo box è "Lead ieri" (sfondo nero) per tutte le card
        kpis_inner = [
            f'<div class="nc-kpi highlight"><div class="lbl">Lead ieri</div><div class="val">{fmt_int(lead)}</div><div class="delta">su {fmt_eur(spend)} spesi</div></div>',
            f'<div class="nc-kpi"><div class="lbl">CPL</div><div class="val">{fmt_eur(cpl)}</div>{delta_html}</div>',
            f'<div class="nc-kpi"><div class="lbl">Spesa</div><div class="val">{fmt_eur(spend)}</div></div>',
        ]
        if cpl_m3 is not None:
            kpis_inner.append(
                f'<div class="nc-kpi"><div class="lbl">Media CPL 3gg</div><div class="val">{fmt_eur(cpl_m3)}</div></div>'
            )

        # Storia + azione: usiamo cpl_narrative per "cosa è successo" e performance_eval per "cosa faremo"
        story_html = ""
        if narrative:
            story_html = f'<div class="nc-body"><div class="nc-section-lbl">Cosa è successo</div><p class="nc-story">{escape_html(narrative)}</p></div>'
        action_html = ""
        if perf_eval:
            action_html = f'<div class="nc-action"><div class="arrow">→</div><div class="text"><b>Cosa faremo.</b> {escape_html(perf_eval)}</div></div>'

        # Reason in details (più tecnico)
        details_html = ""
        if reason:
            details_html = f'<details><summary>Dettaglio tecnico</summary><div class="det-content">{escape_html(reason)}</div></details>'

        cards_html.append(f"""
<div class="card-new {cls}" data-name="{escape_html(name).lower()}" data-color="{cls}">
  <div class="nc-hero">
    <div class="nc-status-row">
      <span class="nc-status"><span class="ico">{icon}</span> {human_label}</span>
    </div>
    <div class="nc-name">{escape_html(name)}</div>
  </div>
  <div class="nc-kpis">
    {''.join(kpis_inner)}
  </div>
  {story_html}
  {action_html}
  {details_html}
</div>""")

    if not cards_html:
        cards_html = ['<div class="reason">Nessuna campagna registrata in questo giorno.</div>']

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#1c1c1e">
<title>CEA — Daily Check {date_iso}</title>
<style>{CSS_BLOCK}</style>
</head>
<body>
<div class="wrap">
  <div class="brand-header">
    <h1>CEA — Daily Check</h1>
    <p class="subtitle">Snapshot del {title_date} · {len(entries)} clienti con spend nel periodo · soglia semaforica su media 3gg (campagne brevi)</p>
    <p class="subtitle" style="margin-top:4px;font-size:11.5px;">Lead aggiornati alle <b>{EXECUTION_LABEL}</b> del {EXECUTION_DATE_LABEL}</p>
  </div>

  <div class="kpis">
    <div class="kpi"><div class="label">Clienti attivi</div><div class="value">{kpi.get('actives', '–')}</div></div>
    <div class="kpi total"><div class="label">Spending</div><div class="value">{fmt_eur(kpi.get('total_spend'))}</div></div>
    <div class="kpi"><div class="label">Lead generati</div><div class="value">{fmt_int(kpi.get('total_lead'))}</div></div>
    <div class="kpi"><div class="label">CPL medio</div><div class="value">{fmt_eur(kpi.get('cpl_y'))}</div></div>
  </div>

  <div class="smart-summary" id="sem-grid">
    <div class="ss-hero">
      <div class="lbl">Stato salute portafoglio</div>
      <div class="val">{salute_pct}%</div>
      <div class="sub">{verde} di {total_camp} campagne in linea</div>
    </div>
    <div class="ss-cell rosso"  data-filter="rosso"><div class="ico">🔴</div><div class="lbl">Da rivedere</div><div class="val">{rosso}</div><div class="micro">in zona critica</div></div>
    <div class="ss-cell giallo" data-filter="giallo"><div class="ico">🟡</div><div class="lbl">Da monitorare</div><div class="val">{giallo}</div><div class="micro">scostamento lieve</div></div>
    <div class="ss-cell verde"  data-filter="verde"><div class="ico">🟢</div><div class="lbl">In linea</div><div class="val">{verde}</div><div class="micro">o sotto media</div></div>
    <div class="ss-cell nero"   data-filter="nero"><div class="ico">⚫</div><div class="lbl">Spente</div><div class="val">{nero}</div><div class="micro">nessuna spesa</div></div>
  </div>

  <div class="search-bar">
    <span class="search-ico">🔎</span>
    <input id="search-input" type="search" autocomplete="off" spellcheck="false" placeholder="Cerca campagna o cliente…" />
    <span class="filter-count" id="filter-count"></span>
    <button type="button" class="clear-btn hidden" id="search-clear" title="Pulisci">Pulisci</button>
  </div>

  <div class="legend">
    <span><span class="dot dot-verde"></span><b>In linea</b> — sotto o pari alla media 3gg</span>
    <span><span class="dot dot-giallo"></span><b>Da monitorare</b> — CPL fino a +50% vs media</span>
    <span><span class="dot dot-rosso"></span><b>Da rivedere</b> — 0 lead o CPL &gt; +50% media</span>
    <span><span class="dot dot-nero"></span><b>Spenta</b> — nessuna spesa</span>
    <span style="opacity:.7">· Clicca un riquadro in alto per filtrare</span>
  </div>

  <div class="cards" id="cards">
{''.join(cards_html)}
  </div>
  <div class="empty-result" id="empty-result" style="display:none">Nessuna campagna corrisponde ai filtri attivi.</div>

  <div class="signature">© Francesco Maria Mosca 2026</div>
</div>
<script>
(function() {{
  "use strict";
  const SEM_FILTERS = new Set();
  let SEARCH_Q = "";
  const searchInput = document.getElementById("search-input");
  const clearBtn    = document.getElementById("search-clear");
  const semGrid     = document.getElementById("sem-grid");
  const cards       = Array.from(document.querySelectorAll("#cards .card-new, #cards .card"));
  const cntEl       = document.getElementById("filter-count");
  const emptyEl     = document.getElementById("empty-result");

  function applyFilters() {{
    const q = SEARCH_Q.toLowerCase().trim();
    let visible = 0;
    for (const c of cards) {{
      const name = (c.dataset.name || "").toLowerCase();
      const color = c.dataset.color || "";
      const matchName  = !q || name.indexOf(q) !== -1;
      const matchColor = SEM_FILTERS.size === 0 || SEM_FILTERS.has(color);
      const show = matchName && matchColor;
      c.style.display = show ? "" : "none";
      if (show) visible++;
    }}
    if (cntEl) {{
      if (q || SEM_FILTERS.size > 0) cntEl.textContent = visible + " su " + cards.length;
      else cntEl.textContent = "";
    }}
    if (emptyEl) emptyEl.style.display = (visible === 0) ? "" : "none";
  }}

  if (searchInput) {{
    searchInput.addEventListener("input", () => {{
      SEARCH_Q = searchInput.value;
      if (clearBtn) clearBtn.classList.toggle("hidden", !SEARCH_Q);
      applyFilters();
    }});
    searchInput.addEventListener("keydown", (e) => {{
      if (e.key === "Escape") {{ searchInput.value = ""; SEARCH_Q = ""; clearBtn.classList.add("hidden"); applyFilters(); }}
    }});
  }}
  if (clearBtn) {{
    clearBtn.addEventListener("click", () => {{
      searchInput.value = ""; SEARCH_Q = ""; clearBtn.classList.add("hidden");
      applyFilters(); searchInput.focus();
    }});
  }}

  if (semGrid) {{
    semGrid.querySelectorAll("[data-filter]").forEach(el => {{
      el.addEventListener("click", () => {{
        const c = el.dataset.filter;
        if (SEM_FILTERS.has(c)) SEM_FILTERS.delete(c);
        else SEM_FILTERS.add(c);
        el.classList.toggle("active-filter", SEM_FILTERS.has(c));
        semGrid.classList.toggle("has-active", SEM_FILTERS.size > 0);
        applyFilters();
      }});
    }});
  }}
}})();
</script>
</body>
</html>
"""

def render_index(items):
    """items: list of {date_iso, kpi} ordinate desc per data"""
    items_html = []
    for it in items:
        k = it["kpi"]
        items_html.append(f"""    <a class="report-item" href="cea-daily-{it['date']}.html">
      <span class="day-name">{fmt_date_long(it['date'])}</span>
      <span class="day-counts">
        <span class="c-rosso">{k.get('rosso',0)}R</span> ·
        <span class="c-giallo">{k.get('giallo',0)}G</span> ·
        <span class="c-verde">{k.get('verde',0)}V</span> ·
        <span class="c-nero">{k.get('nero',0)}N</span>
      </span>
      <span class="arrow">→</span>
    </a>""")
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>CEA — Archivio Daily Check</title>
<style>{CSS_BLOCK}</style>
</head>
<body>
<div class="wrap">
  <div class="brand-header">
    <h1>CEA — Archivio Daily Check</h1>
    <p class="subtitle">Snapshot giornalieri · semaforica su media 3gg</p>
  </div>
  <div class="section-label">Report disponibili</div>
  <div class="report-list">
{''.join(items_html) if items_html else '<div class="reason">Nessun report ancora disponibile.</div>'}
  </div>
  <div class="signature">© Francesco Maria Mosca 2026</div>
</div>
</body>
</html>
"""

def main():
    dates = sys.argv[1:]
    if not dates:
        # Auto: tutti gli snapshot che hanno cea entries
        idx = json.load(open(SNAP_DIR / "index.json"))
        dates = [d for d in idx.get("dates", [])]
    items = []
    for dt in dates:
        snap_file = SNAP_DIR / f"{dt}.json"
        if not snap_file.exists():
            print(f"  [skip] {dt}: snapshot non trovato")
            continue
        snap = json.load(open(snap_file))
        cea = snap.get("cea")
        if not cea or not cea.get("entries"):
            print(f"  [skip] {dt}: cea vuoto")
            continue
        # Genera pagina daily
        html = render_daily(dt, cea)
        out_file = ROOT / f"cea-daily-{dt}.html"
        out_file.write_text(html, encoding="utf-8")
        print(f"  [ok]   {out_file.name}  ({len(cea['entries'])} card, R{cea['kpi'].get('rosso',0)}/G{cea['kpi'].get('giallo',0)}/V{cea['kpi'].get('verde',0)}/N{cea['kpi'].get('nero',0)})")
        items.append({"date": dt, "kpi": cea["kpi"]})

    # Sort desc + render archivio
    items.sort(key=lambda x: x["date"], reverse=True)
    archive = render_index(items)
    (ROOT / "cea-daily-check.html").write_text(archive, encoding="utf-8")
    print(f"\nArchivio: cea-daily-check.html ({len(items)} report)")


if __name__ == "__main__":
    main()
