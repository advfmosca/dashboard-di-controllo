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
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

# Orario di esecuzione (= orario di lettura/processing dei CSV di Alfredo)
EXECUTION_DT = datetime.now()
EXECUTION_LABEL = EXECUTION_DT.strftime("%H:%M")
EXECUTION_DATE_LABEL = EXECUTION_DT.strftime("%d/%m/%Y")

ROOT = Path(__file__).resolve().parent.parent  # /Dashboard di Controllo
SNAP_DIR = ROOT / "snapshots"

# Meta overrides opzionali: file JSON per popolare target geo + grandezza pubblico
# per ogni cliente (chiave = nome cliente come estratto da extractMTCEAClient).
# Esempio: { "STUDIO DOTT. RICCIARDI LUMINA": {"target": "Via Manzoni 12 +8km", "audience_size": "120K"} }
META_OVERRIDES = {}
_meta_path = ROOT / "mtcea_clients_meta.json"
if _meta_path.exists():
    try:
        META_OVERRIDES = json.loads(_meta_path.read_text(encoding="utf-8"))
    except Exception:
        META_OVERRIDES = {}

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
.card-new .nc-chart-wrap { margin: 12px 16px; padding: 10px 12px; background: var(--bg-soft); border-radius: 10px; }
.card-new .nc-chart-title { display: flex; justify-content: space-between; align-items: center; font-size: 10.5px; font-weight: 600; letter-spacing: 0.04em; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px; flex-wrap: wrap; gap: 6px; }
.card-new .nc-chart-legend { font-size: 10px; display: flex; gap: 8px; }
.card-new .nc-chart-legend .lg-s { display: inline-flex; align-items: center; gap: 4px; text-transform: none; letter-spacing: 0; }
.card-new .nc-chart-legend .lg-sw { display: inline-block; width: 9px; height: 9px; border-radius: 2px; }
.card-new .nc-chart { background: #fff; border: 1px solid var(--border-soft); border-radius: 8px; padding: 6px; }
.card-new .nc-chart svg { width: 100%; height: auto; display: block; }
.card-new .nc-chart .nc-loading { padding: 14px; text-align: center; color: var(--text-dim); font-size: 12px; }
.card-new .nc-day-nav { display: flex; align-items: center; justify-content: center; gap: 10px; margin-top: 8px; padding: 6px 10px; background: #fff; border: 1px solid var(--border); border-radius: 8px; }
.card-new .nc-nav-btn { background: #fff; border: 1px solid var(--border); border-radius: 6px; padding: 3px 9px; font: inherit; font-size: 13px; cursor: pointer; color: var(--text); }
.card-new .nc-nav-btn:hover { background: var(--bg-soft); }
.card-new .nc-nav-btn:disabled { color: var(--text-dim); cursor: not-allowed; opacity: 0.5; }
.card-new .nc-day-label { font-weight: 600; font-size: 12.5px; text-align: center; }
.card-new .nc-day-label .small { display: block; font-weight: 500; font-size: 10.5px; color: var(--text-muted); margin-top: 1px; }
.card-new .nc-day-kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-top: 8px; }
.card-new .nc-day-kpis .dk-cell { background: #fff; border: 1px solid var(--border-soft); border-radius: 8px; padding: 7px 9px; text-align: center; }
.card-new .nc-day-kpis .dk-lbl { font-size: 9.5px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; }
.card-new .nc-day-kpis .dk-val { font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; margin-top: 2px; }

.card-new .nc-meta { margin: 8px 0 12px; padding: 10px 12px; background: var(--bg-soft); border-radius: 8px; }
.card-new .nc-meta dl { margin: 0; display: grid; grid-template-columns: 1fr; gap: 8px; }
@media (min-width: 640px) { .card-new .nc-meta dl { grid-template-columns: repeat(3, 1fr); gap: 12px; } }
.card-new .nc-meta dt { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); margin-bottom: 2px; }
.card-new .nc-meta dd { margin: 0; font-size: 12.5px; font-weight: 600; color: var(--text); }
.card-new .nc-meta dd.placeholder { color: var(--text-dim); font-weight: 500; font-style: italic; }

.card-new .nc-status-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
.card-new .client-btn { margin-left: auto; font-size: 11.5px; font-weight: 600; padding: 4px 10px; border-radius: 999px; background: #fff; border: 1px solid #d2d2d7; color: var(--text); text-decoration: none; transition: background .12s; }
.card-new .client-btn:hover { background: var(--bg-soft); }
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

/* === Visualizzazioni & Frequenza (introdotte 2026-05-22) === */
.card-new .nc-kpi .freq-pill { display: inline-block; padding: 1px 7px; border-radius: 999px; font-size: 9.5px; font-weight: 700; letter-spacing: 0.04em; margin-top: 4px; text-transform: uppercase; }
.card-new .nc-kpi .freq-pill.bassa     { background: #dbeafe; color: #1e3a8a; }
.card-new .nc-kpi .freq-pill.ottimale  { background: #d1fadf; color: #14532d; }
.card-new .nc-kpi .freq-pill.monitorare{ background: #ffedd5; color: #9a3412; }
.card-new .nc-kpi .freq-pill.alta      { background: #fee2e2; color: #991b1b; }
.card-new .nc-kpi .freq-pill.critica   { background: #1a1a1a; color: #fff; }
.card-new .nc-freq { padding: 12px 16px 0; border-top: 1px solid var(--border-soft); margin-top: 12px; }
.card-new .nc-freq .nc-story.rosso  { color: #991b1b; }
.card-new .nc-freq .nc-story.giallo { color: #9a3412; }
.card-new .nc-freq .nc-story.verde  { color: #14532d; }

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

def load_series_7gg(ref_date_iso, section="cea"):
    """Carica i 7 snapshot precedenti (incluso ref_date) e costruisce
    {entry_name: [{date, spend, lead}, ...]} cronologico ASC per la sezione
    indicata (cea o medtech)."""
    from datetime import timedelta
    ref_dt = datetime.strptime(ref_date_iso, "%Y-%m-%d")
    dates = [(ref_dt - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    series_by_name = {}
    for d in dates:
        p = SNAP_DIR / f"{d}.json"
        if not p.exists(): continue
        try:
            snap = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for e in (snap.get(section, {}) or {}).get("entries", []) or []:
            nm = e.get("name") or ""
            if not nm: continue
            series_by_name.setdefault(nm, []).append({
                "date": d,
                "spend": float(e.get("spend_y") or 0),
                "lead": float(e.get("contatti_y") or e.get("lead_y") or 0),
            })
    return series_by_name

def render_chart_placeholder(card_id):
    """Placeholder che verrà popolato da JS embedded a fine pagina con chart
    navigabile (linea spesa + linea contatti) + day-navigator + day-panel."""
    return f"""<div class="nc-chart-wrap" data-chart-id="{card_id}">
  <div class="nc-chart-title"><span>Andamento spesa &amp; contatti (7gg) — naviga con ← →</span>
    <span class="nc-chart-legend"><span class="lg-s"><span class="lg-sw" style="background:#1c1c1e"></span>Spesa</span> <span class="lg-s"><span class="lg-sw" style="background:#0866FF"></span>Contatti</span></span>
  </div>
  <div class="nc-chart" id="chart-{card_id}"><div class="nc-loading">Carico la serie storica…</div></div>
  <div class="nc-day-nav" id="daynav-{card_id}" style="display:none">
    <button type="button" class="nc-nav-btn" data-action="prev">←</button>
    <div class="nc-day-label" id="daylbl-{card_id}">—<span class="small">giorno selezionato</span></div>
    <button type="button" class="nc-nav-btn" data-action="next">→</button>
  </div>
  <div class="nc-day-kpis" id="daykpi-{card_id}" style="display:none"></div>
</div>"""


def render_mini_chart_LEGACY(series, w=560, h=160):
    """LEGACY (non più usata: sostituita da chart navigabile JS embedded).
    Mantenuta per safety. Verrà rimossa nel prossimo refactor."""
    if not series: return ""
    valid = [p for p in series if p.get("spend") is not None]
    if not valid: return ""
    n = len(valid)
    padL, padR, padT, padB = 36, 36, 12, 26
    iw = w - padL - padR
    ih = h - padT - padB
    spends = [p["spend"] for p in valid]
    leads  = [p["lead"] or 0 for p in valid]
    has_leads = any(l > 0 for l in leads)
    smax = max(spends) * 1.15 or 1
    lmax = (max(leads) * 1.15) if has_leads else 1
    def x_at(i): return padL + (iw / 2 if n <= 1 else (i * iw) / (n - 1))
    def y_s(v): return padT + ih - (v / smax) * ih
    def y_l(v): return padT + ih - (v / lmax) * ih
    def fmt_e(v): return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    grid = "".join(f'<line stroke="#ececef" stroke-dasharray="2,3" x1="{padL}" x2="{w-padR}" y1="{padT + ih*i/3:.1f}" y2="{padT + ih*i/3:.1f}"/>' for i in range(4))
    psp = " ".join(("M" if i==0 else "L") + f"{x_at(i):.1f},{y_s(v):.1f}" for i,v in enumerate(spends))
    # Dot Spesa con <title> tooltip (data + spesa + contatti)
    dots_s = ""
    for i in range(n):
        d_short = valid[i]["date"][-5:]
        tip = f"{d_short} · Spesa {fmt_e(spends[i])}"
        if has_leads: tip += f" · Contatti {int(leads[i])}"
        dots_s += f'<circle cx="{x_at(i):.1f}" cy="{y_s(spends[i]):.1f}" r="3" fill="#1c1c1e" stroke="#fff" stroke-width="1"><title>{tip}</title></circle>'
    pld = ""
    dots_l = ""
    if has_leads:
        pld = '<path fill="none" stroke="#0866FF" stroke-width="1.6" d="' + " ".join(("M" if i==0 else "L") + f"{x_at(i):.1f},{y_l(leads[i]):.1f}" for i in range(n)) + '"/>'
        for i in range(n):
            d_short = valid[i]["date"][-5:]
            tip = f"{d_short} · Contatti {int(leads[i])} · Spesa {fmt_e(spends[i])}"
            dots_l += f'<circle cx="{x_at(i):.1f}" cy="{y_l(leads[i]):.1f}" r="3" fill="#0866FF" stroke="#fff" stroke-width="1"><title>{tip}</title></circle>'
    # X labels: una etichetta per ogni giorno (7 punti ci stanno)
    xl = "".join(f'<text x="{x_at(i):.1f}" y="{h - padB + 14}" text-anchor="middle" font-size="10" fill="#6b6b70">{valid[i]["date"][-5:]}</text>' for i in range(n))
    legend = ('<span class="lg-s"><span class="lg-sw" style="background:#1c1c1e"></span>Spesa</span>'
              + ('<span class="lg-s" style="margin-left:8px"><span class="lg-sw" style="background:#0866FF"></span>Contatti</span>' if has_leads else "")
              + '<span class="lg-hint">Passa il mouse sui punti per il dettaglio del giorno</span>')
    return f"""<div class="nc-chart">
  <div class="nc-chart-legend">{legend}</div>
  <svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Andamento spesa e contatti 7 giorni">
    {grid}
    <line stroke="#d2d2d7" stroke-width="0.5" x1="{padL}" x2="{w-padR}" y1="{padT + ih:.1f}" y2="{padT + ih:.1f}"/>
    <path fill="none" stroke="#1c1c1e" stroke-width="1.6" d="{psp}"/>
    {pld}
    {dots_s}{dots_l}
    {xl}
  </svg>
</div>"""

def render_daily(date_iso, cea, project="cea"):
    """project: 'cea' o 'medtech'. Cambia titolo H1 + load_series source section.

    Se cea._meta.stale=True, render produce un banner giallo evidente in cima alla
    pagina con il messaggio "Dati al <stale_from> — CSV del <date_iso> non disponibile".
    Introdotto 2026-05-22 per coprire i giorni in cui la mail automatica
    project@cea.management non arriva.
    """
    kpi = cea.get("kpi", {})
    entries = cea.get("entries", [])
    title_date = fmt_date_long(date_iso)
    meta = cea.get("_meta") or {}
    is_stale = bool(meta.get("stale"))
    stale_from = meta.get("stale_from") or meta.get("reference_date") or ""
    stale_from_label = fmt_date_long(stale_from) if stale_from else ""
    stale_title_tag = ""  # rimosso 2026-05-22 — il banner stale appare solo in overview master
    series_by_name = load_series_7gg(date_iso, section=project)
    project_label_h1 = "MED & TECH" if project == "medtech" else "CEA"
    rosso = kpi.get("rosso", 0); giallo = kpi.get("giallo", 0)
    verde = kpi.get("verde", 0); nero   = kpi.get("nero", 0)
    total_camp = len(entries) if entries else (rosso + giallo + verde + nero)
    # Stato salute = verde / totale
    salute_pct = int(round(verde / total_camp * 100)) if total_camp > 0 else 0

    cards_html = []
    series_by_id = {}  # card_id -> list of {date, spend, lead}
    card_idx = 0
    for e in entries:
        card_idx += 1
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

        # KPI in evidenza: il primo box è "Contatti ieri" (sfondo nero) per tutte le card
        kpis_inner = [
            f'<div class="nc-kpi highlight"><div class="lbl">Contatti ieri</div><div class="val">{fmt_int(lead)}</div><div class="delta">su {fmt_eur(spend)} di spesa</div></div>',
            f'<div class="nc-kpi"><div class="lbl">Costo per contatto</div><div class="val">{fmt_eur(cpl)}</div>{delta_html}</div>',
            f'<div class="nc-kpi"><div class="lbl">Spesa</div><div class="val">{fmt_eur(spend)}</div></div>',
        ]
        if cpl_m3 is not None:
            kpis_inner.append(
                f'<div class="nc-kpi"><div class="lbl">Costo medio 3gg</div><div class="val">{fmt_eur(cpl_m3)}</div></div>'
            )

        # Visualizzazioni + Frequenza (introdotti 2026-05-22).
        # Pill colorata per bucket; se reach mancante, mostra "—" ma resta la cella per coerenza layout.
        impressions_v = e.get("impressions")
        reach_v       = e.get("reach")
        freq_v        = e.get("frequency")
        freq_code     = e.get("freq_bucket") or ""
        freq_label    = e.get("freq_bucket_label") or ""
        vis_delta = f'<div class="delta">Reach {fmt_int(reach_v)}</div>' if reach_v else ''
        kpis_inner.append(
            f'<div class="nc-kpi"><div class="lbl">Visualizzazioni</div>'
            f'<div class="val">{fmt_int(impressions_v) if impressions_v else "—"}</div>{vis_delta}</div>'
        )
        freq_pill_html = f'<span class="freq-pill {freq_code}">{escape_html(freq_label)}</span>' if freq_code else ''
        kpis_inner.append(
            f'<div class="nc-kpi"><div class="lbl">Frequenza</div>'
            f'<div class="val">{(f"{freq_v:.2f}").replace(".", ",") if freq_v is not None else "—"}</div>'
            f'{freq_pill_html}</div>'
        )

        # Storia + azione: usiamo cpl_narrative per "cosa è successo" e performance_eval per "cosa faremo"
        story_html = ""
        if narrative:
            story_html = f'<div class="nc-body"><div class="nc-section-lbl">Cosa è successo</div><p class="nc-story">{escape_html(narrative)}</p></div>'
        # NUOVA sezione: Analisi frequenza (tra "Cosa è successo" e "Cosa faremo")
        freq_html = ""
        freq_text  = e.get("freq_analysis") or ""
        freq_color = e.get("freq_analysis_color") or ""
        if freq_text:
            # ATTENZIONE: freq_text contiene tag <b> intenzionali → NON escape-arlo
            freq_html = (
                f'<div class="nc-freq"><div class="nc-section-lbl">Analisi frequenza</div>'
                f'<p class="nc-story {freq_color}">{freq_text}</p></div>'
            )
        action_html = ""
        if perf_eval:
            action_html = f'<div class="nc-action"><div class="arrow">→</div><div class="text"><b>Cosa faremo.</b> {escape_html(perf_eval)}</div></div>'

        # Reason in details (più tecnico)
        details_html = ""
        if reason:
            details_html = f'<details><summary>Dettaglio tecnico</summary><div class="det-content">{escape_html(reason)}</div></details>'

        # Bottone "Vista cliente" che apre la pagina pubblica cliente.html con il nome cliente
        # estratto dal nome campagna. Si apre in nuova scheda.
        name_parts = [p.strip() for p in name.split(" - ") if p.strip()]
        client_short = name_parts[-1] if len(name_parts) > 1 else name
        client_url = "cliente.html?name=" + urllib.parse.quote(client_short) + "&date=" + date_iso
        client_btn = f'<a class="client-btn" href="{client_url}" target="_blank" rel="noopener">👁 Vista cliente</a>'

        # Campagna attiva: per CEA il nome intero, per MT-style ('A - B - CLIENTE') la parte
        # iniziale escluso l'ultimo segmento. Target + audience: opzionali da meta_overrides.
        if len(name_parts) > 1:
            campaign_active = " - ".join(name_parts[:-1])
        else:
            campaign_active = name
        meta_overrides = META_OVERRIDES.get(client_short, {}) if META_OVERRIDES else {}
        # Priorità: dato dal CSV (entry.target_geo / audience_size); fallback su mapping manuale.
        target_val = e.get("target_geo") or meta_overrides.get("target", "")
        aud_val = e.get("audience_size") or meta_overrides.get("audience_size", "")
        target_html = f'<dd>{escape_html(target_val)}</dd>' if target_val else '<dd class="placeholder">Da configurare</dd>'
        aud_html = f'<dd>{escape_html(aud_val)}</dd>' if aud_val else '<dd class="placeholder">Da configurare</dd>'
        meta_block = f"""<div class="nc-meta"><dl>
  <div><dt>Campagna attiva</dt><dd>{escape_html(campaign_active)}</dd></div>
  <div><dt>Target</dt>{target_html}</div>
  <div><dt>Grandezza pubblico</dt>{aud_html}</div>
</dl></div>"""

        card_id = f"c{card_idx}"
        series_by_id[card_id] = series_by_name.get(name, [])

        cards_html.append(f"""
<div class="card-new {cls}" data-name="{escape_html(name).lower()}" data-color="{cls}">
  <div class="nc-hero">
    <div class="nc-status-row">
      <span class="nc-status"><span class="ico">{icon}</span> {human_label}</span>
      {client_btn}
    </div>
    <div class="nc-name">{escape_html(name)}</div>
  </div>
  {meta_block}
  <div class="nc-kpis">
    {''.join(kpis_inner)}
  </div>
  {render_chart_placeholder(card_id)}
  {story_html}
  {freq_html}
  {action_html}
  {details_html}
</div>""")

    if not cards_html:
        cards_html = ['<div class="reason">Nessuna campagna registrata in questo giorno.</div>']

    # Serializza la mappa series_by_id per JS embedded (chart navigabile)
    series_json = json.dumps(series_by_id, ensure_ascii=False, separators=(",", ":"))
    if is_stale:
        stale_banner = (
            '<div class="stale-banner" role="alert" style="'
            'margin: 0 0 14px; padding: 14px 18px; '
            'background: linear-gradient(135deg,#fff7e0 0%,#fff2c2 100%); '
            'border: 1.5px solid #e0b020; border-left: 6px solid #d48800; '
            'border-radius: 12px; color: #5a3c00; '
            'font-size: 14px; line-height: 1.5; font-weight: 500;">'
            '<div style="font-size: 16px; font-weight: 700; margin-bottom: 4px;">'
            '⚠ Dati al ' + (stale_from_label or stale_from) + ' — non aggiornati al ' + title_date + '</div>'
            '<div style="opacity:.92;">I numeri qui sotto sono dell\'ultimo giorno con dati validi. '
            'La fonte automatica (mail <code style="background:#fff;padding:1px 5px;border-radius:4px;">'
            'project@cea.management</code> → CSV su Drive) non ha pubblicato il file per il '
            + title_date + '. Tornerà fresca al prossimo invio.</div>'
            '</div>'
        )
    else:
        stale_banner = ""
    # Banner stale rimosso 2026-05-22 — la visibilità del flag stale è solo nell'overview
    # della dashboard master (https://advfmosca.github.io/dashboard-di-controllo/#overview).
    # Le pagine team daily mostrano i dati senza alcun banner anche se _meta.stale=true.
    stale_banner = ""
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#1c1c1e">
<title>{project_label_h1} — Andamento campagne {date_iso}</title>
<style>{CSS_BLOCK}</style>
</head>
<body>
<div class="wrap">
  {stale_banner}
  <div class="brand-header">
    <h1>{project_label_h1} — Andamento campagne</h1>
    <p class="subtitle">Snapshot del {title_date} · {len(entries)} clienti con investimento nel periodo · soglia semaforica calcolata sul costo per contatto medio 3gg (campagne brevi)</p>
    <p class="subtitle" style="margin-top:4px;font-size:11.5px;">Contatti aggiornati alle <b>{EXECUTION_LABEL}</b> del {EXECUTION_DATE_LABEL}</p>
  </div>

  <div class="kpis">
    <div class="kpi"><div class="label">Clienti attivi</div><div class="value">{kpi.get('actives', '–')}</div></div>
    <div class="kpi total"><div class="label">Spesa totale</div><div class="value">{fmt_eur(kpi.get('total_spend'))}</div></div>
    <div class="kpi"><div class="label">Contatti generati</div><div class="value">{fmt_int(kpi.get('total_lead'))}</div></div>
    <div class="kpi"><div class="label">Costo medio per contatto</div><div class="value">{fmt_eur(kpi.get('cpl_y'))}</div></div>
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
    <span><span class="dot dot-verde"></span><b>In linea</b> — costo per contatto sotto o pari alla media 3gg</span>
    <span><span class="dot dot-giallo"></span><b>Da monitorare</b> — costo per contatto fino a +50% vs media</span>
    <span><span class="dot dot-rosso"></span><b>Da rivedere</b> — 0 contatti o costo &gt; +50% vs media</span>
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
const ALL_SERIES = {series_json};
</script>
<script>
(function() {{
  "use strict";
  // ============================================================
  // Chart navigabile per ogni card: linea Spesa (nera) + Contatti (blu)
  // + day-navigator (← →) + day-panel coi 3 KPI del giorno selezionato.
  // ============================================================
  function fmtEUR(n) {{
    if (n == null || isNaN(n)) return "—";
    return Number(n).toLocaleString("it-IT", {{ style: "currency", currency: "EUR", minimumFractionDigits: 2, maximumFractionDigits: 2 }});
  }}
  function fmtInt(n) {{
    if (n == null || isNaN(n)) return "—";
    return Math.round(Number(n)).toLocaleString("it-IT");
  }}
  function dayLabelIT(iso) {{
    const m = String(iso || "").match(/^(\d{{4}})-(\d{{2}})-(\d{{2}})$/);
    if (!m) return iso || "—";
    const wd = ["Dom","Lun","Mar","Mer","Gio","Ven","Sab"];
    const mo = ["gen","feb","mar","apr","mag","giu","lug","ago","set","ott","nov","dic"];
    const dt = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    return wd[dt.getDay()] + " " + Number(m[3]) + " " + mo[dt.getMonth()];
  }}
  function shortDate(iso) {{
    const m = String(iso || "").match(/^(\d{{4}})-(\d{{2}})-(\d{{2}})$/);
    return m ? (m[3] + "/" + m[2]) : (iso || "");
  }}
  function drawChart(root, series, selectedIdx, onSelect) {{
    const valid = [];
    const validToOrig = [];
    for (let i = 0; i < series.length; i++) {{
      if (series[i].spend != null) {{ valid.push(series[i]); validToOrig.push(i); }}
    }}
    if (valid.length === 0) {{ root.innerHTML = '<div class="nc-loading">Nessun dato giornaliero disponibile</div>'; return; }}
    const W = 640, H = 220;
    const padL = 40, padR = 40, padT = 12, padB = 32;
    const innerW = W - padL - padR, innerH = H - padT - padB;
    const n = valid.length;
    const spends = valid.map(p => p.spend);
    const leads = valid.map(p => p.lead != null ? p.lead : 0);
    const hasLeads = valid.some(p => p.lead != null && p.lead > 0);
    const spendMax = Math.max(...spends) * 1.15 || 1;
    const leadMax = Math.max(...leads, 1) * 1.15;
    const xAt = i => padL + (n <= 1 ? innerW / 2 : (i * innerW) / (n - 1));
    const ySpend = v => padT + innerH - (v / spendMax) * innerH;
    const yLeads = v => padT + innerH - (v / leadMax) * innerH;
    let grid = "";
    for (let i = 0; i <= 3; i++) {{
      const y = padT + (innerH * i) / 3;
      grid += '<line stroke="#ececef" stroke-dasharray="2,3" x1="' + padL + '" x2="' + (W-padR) + '" y1="' + y + '" y2="' + y + '"/>';
    }}
    let xLabels = "";
    for (let i = 0; i < n; i++) {{
      xLabels += '<text x="' + xAt(i) + '" y="' + (H - padB + 14) + '" text-anchor="middle" font-size="10" fill="#6b6b70">' + shortDate(valid[i].date) + '</text>';
    }}
    const pathSpend = spends.map((v,i) => (i===0?"M":"L") + xAt(i) + "," + ySpend(v)).join(" ");
    const pathLeads = hasLeads ? leads.map((v,i) => (i===0?"M":"L") + xAt(i) + "," + yLeads(v)).join(" ") : "";
    let selValidIdx = validToOrig.indexOf(selectedIdx);
    if (selValidIdx < 0) selValidIdx = n - 1;
    const selX = xAt(selValidIdx);
    const dayMarker = '<line stroke="#8a8a90" stroke-dasharray="3,3" x1="' + selX + '" x2="' + selX + '" y1="' + padT + '" y2="' + (padT + innerH) + '"/>';
    let dots = "", interact = "";
    for (let i = 0; i < n; i++) {{
      const xs = xAt(i);
      const isSel = i === selValidIdx;
      dots += '<circle cx="' + xs + '" cy="' + ySpend(spends[i]) + '" r="' + (isSel?5:3) + '" fill="#1c1c1e" stroke="#fff" stroke-width="' + (isSel?2:1) + '"/>';
      if (hasLeads) dots += '<circle cx="' + xs + '" cy="' + yLeads(leads[i]) + '" r="' + (isSel?5:3) + '" fill="#0866FF" stroke="#fff" stroke-width="' + (isSel?2:1) + '"/>';
      interact += '<rect x="' + (xs - innerW/(n*2)) + '" y="' + padT + '" width="' + (innerW/n) + '" height="' + innerH + '" fill="transparent" style="cursor:pointer" data-orig-idx="' + validToOrig[i] + '"/>';
    }}
    const svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Andamento spesa e contatti 7 giorni">'
      + grid
      + '<line stroke="#d2d2d7" stroke-width="0.5" x1="' + padL + '" x2="' + (W-padR) + '" y1="' + (padT+innerH) + '" y2="' + (padT+innerH) + '"/>'
      + dayMarker
      + '<path fill="none" stroke="#1c1c1e" stroke-width="1.6" d="' + pathSpend + '"/>'
      + (pathLeads ? '<path fill="none" stroke="#0866FF" stroke-width="1.6" d="' + pathLeads + '"/>' : "")
      + dots + xLabels + interact
      + '</svg>';
    root.innerHTML = svg;
    if (onSelect) {{
      root.querySelectorAll("rect[data-orig-idx]").forEach(el => {{
        el.addEventListener("click", () => {{
          const i = Number(el.getAttribute("data-orig-idx"));
          if (!isNaN(i)) onSelect(i);
        }});
      }});
    }}
  }}
  function renderDayPanel(panelRoot, p) {{
    if (!panelRoot) return;
    const cells = [];
    const cell = (lbl, val) => '<div class="dk-cell"><div class="dk-lbl">' + lbl + '</div><div class="dk-val">' + val + '</div></div>';
    if (p && p.spend != null) cells.push(cell("Budget", fmtEUR(p.spend)));
    if (p && p.lead != null) cells.push(cell("Contatti", fmtInt(p.lead)));
    if (p && p.lead > 0 && p.spend != null) cells.push(cell("Costo per contatto", fmtEUR(p.spend / p.lead)));
    panelRoot.innerHTML = cells.length ? cells.join("") : '<div class="nc-loading">Nessun KPI disponibile</div>';
  }}
  function wireCard(cardId) {{
    const series = ALL_SERIES[cardId] || [];
    const chartRoot = document.getElementById("chart-" + cardId);
    const navRoot   = document.getElementById("daynav-" + cardId);
    const kpiRoot   = document.getElementById("daykpi-" + cardId);
    const labelEl   = document.getElementById("daylbl-" + cardId);
    if (!chartRoot) return;
    let selIdx = -1;
    for (let i = series.length - 1; i >= 0; i--) {{
      if (series[i].spend != null) {{ selIdx = i; break; }}
    }}
    if (selIdx < 0) selIdx = series.length - 1;
    const hasAnySpend = series.some(p => p.spend != null);
    if (!hasAnySpend) {{
      chartRoot.innerHTML = '<div class="nc-loading">Nessun dato giornaliero disponibile</div>';
      return;
    }}
    function update() {{
      drawChart(chartRoot, series, selIdx, (newIdx) => {{ selIdx = newIdx; update(); }});
      if (navRoot) navRoot.style.display = "";
      if (kpiRoot) kpiRoot.style.display = "";
      if (labelEl) {{
        const d = series[selIdx] && series[selIdx].date;
        labelEl.innerHTML = dayLabelIT(d) + '<span class="small">' + (d || "") + '</span>';
      }}
      if (kpiRoot) renderDayPanel(kpiRoot, series[selIdx]);
      const prev = document.querySelector('#daynav-' + cardId + ' [data-action="prev"]');
      const next = document.querySelector('#daynav-' + cardId + ' [data-action="next"]');
      if (prev) prev.disabled = selIdx <= 0;
      if (next) next.disabled = selIdx >= series.length - 1;
    }}
    update();
    const prevBtn = document.querySelector('#daynav-' + cardId + ' [data-action="prev"]');
    const nextBtn = document.querySelector('#daynav-' + cardId + ' [data-action="next"]');
    if (prevBtn) prevBtn.addEventListener("click", () => {{ if (selIdx > 0) {{ selIdx--; update(); }} }});
    if (nextBtn) nextBtn.addEventListener("click", () => {{ if (selIdx < series.length - 1) {{ selIdx++; update(); }} }});
  }}
  // Wire tutte le card al ready
  Object.keys(ALL_SERIES).forEach(wireCard);

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

def render_index(items, project="cea"):
    """items: list of {date_iso, kpi} ordinate desc per data.
    project: 'cea' o 'medtech' → cambia titolo + prefix link."""
    file_prefix = "med-tech-daily" if project == "medtech" else "cea-daily"
    title = "MED & TECH — Archivio andamento campagne" if project == "medtech" else "CEA — Archivio andamento campagne"
    items_html = []
    for it in items:
        k = it["kpi"]
        items_html.append(f"""    <a class="report-item" href="{file_prefix}-{it['date']}.html">
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
<title>{title}</title>
<style>{CSS_BLOCK}</style>
</head>
<body>
<div class="wrap">
  
  <div class="brand-header">
    <h1>{title}</h1>
    <p class="subtitle">Snapshot giornalieri · semaforica calcolata sul costo medio per contatto 3gg</p>
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
    # Parsing argv: supporta --project cea|medtech (default cea) e --output-dir <PATH>
    # (default = ROOT). Le date residue sono gli ISO-date da generare.
    args = list(sys.argv[1:])
    project = "cea"
    out_dir = ROOT
    dates = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--project" and i + 1 < len(args):
            project = args[i + 1].lower()
            i += 2
        elif a.startswith("--project="):
            project = a.split("=", 1)[1].lower()
            i += 1
        elif a == "--output-dir" and i + 1 < len(args):
            out_dir = Path(args[i + 1])
            i += 2
        elif a.startswith("--output-dir="):
            out_dir = Path(a.split("=", 1)[1])
            i += 1
        else:
            dates.append(a)
            i += 1
    if project not in ("cea", "medtech"):
        print(f"⚠ project='{project}' non valido. Uso 'cea'.")
        project = "cea"
    file_prefix = "med-tech-daily" if project == "medtech" else "cea-daily"
    archive_name = "med-tech-daily-check.html" if project == "medtech" else "cea-daily-check.html"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not dates:
        idx = json.load(open(SNAP_DIR / "index.json"))
        dates = [d for d in idx.get("dates", [])]
    items = []
    for dt in dates:
        snap_file = SNAP_DIR / f"{dt}.json"
        if not snap_file.exists():
            print(f"  [skip] {dt}: snapshot non trovato")
            continue
        snap = json.load(open(snap_file))
        section_data = snap.get(project)
        if not section_data or not section_data.get("entries"):
            print(f"  [skip] {dt}: {project} vuoto")
            continue
        if (section_data.get("_meta") or {}).get("stale"):
            sf = (section_data.get("_meta") or {}).get("stale_from", "?")
            print(f"  [stale] {dt}: rendering pagina con banner STALE (dati al {sf})")
        html = render_daily(dt, section_data, project=project)
        out_file = out_dir / f"{file_prefix}-{dt}.html"
        out_file.write_text(html, encoding="utf-8")
        kpi = section_data.get("kpi", {})
        print(f"  [ok]   {out_file.name}  ({len(section_data['entries'])} card, R{kpi.get('rosso',0)}/G{kpi.get('giallo',0)}/V{kpi.get('verde',0)}/N{kpi.get('nero',0)})")
        items.append({"date": dt, "kpi": kpi})

    # Archivio: scansiona TUTTI i file daily presenti in out_dir, non solo
    # quelli appena generati. Evita di sovrascrivere l'archivio del repo
    # con una lista parziale quando si rigenera un sottoinsieme di date
    # (es. solo 19 e 20). Per i giorni non rigenerati ora, leggiamo i kpi
    # direttamente dall'HTML esistente.
    existing_files = sorted([
        p for p in out_dir.glob(f"{file_prefix}-*.html")
        if re.match(rf"{re.escape(file_prefix)}-\d{{4}}-\d{{2}}-\d{{2}}\.html$", p.name)
    ])
    items_by_date = {it["date"]: it for it in items}
    for fp in existing_files:
        m = re.match(rf"{re.escape(file_prefix)}-(\d{{4}}-\d{{2}}-\d{{2}})\.html$", fp.name)
        if not m:
            continue
        dt = m.group(1)
        if dt in items_by_date:
            continue
        # Estrai kpi dai counts dell'HTML esistente (smart-summary cells)
        try:
            ftxt = fp.read_text(encoding="utf-8")
        except Exception:
            ftxt = ""
        def _grab(cls):
            mm = re.search(rf'<div class="ss-cell {cls}".*?<div class="val">(\d+)</div>', ftxt, re.DOTALL)
            return int(mm.group(1)) if mm else 0
        items_by_date[dt] = {
            "date": dt,
            "kpi": {
                "rosso": _grab("rosso"),
                "giallo": _grab("giallo"),
                "verde":  _grab("verde"),
                "nero":   _grab("nero"),
            },
        }

    all_items = list(items_by_date.values())
    all_items.sort(key=lambda x: x["date"], reverse=True)
    archive = render_index(all_items, project=project)

    # Safeguard anti-regression: se esiste già un archivio con PIÙ voci di
    # quello che stiamo per scrivere, c'è qualcosa che non va (out_dir non
    # contiene tutti i daily file → l'archivio risulterebbe monco e
    # sovrascriverebbe l'attuale, perdendo giorni). Abort con messaggio
    # esplicito. Per forzare lo scrive comunque: env DASHBOARD_FORCE_ARCHIVE=1.
    archive_path = out_dir / archive_name
    if archive_path.exists() and not os.environ.get("DASHBOARD_FORCE_ARCHIVE"):
        try:
            existing_archive = archive_path.read_text(encoding="utf-8")
            existing_dates = set(re.findall(
                rf"{re.escape(file_prefix)}-(\d{{4}}-\d{{2}}-\d{{2}})\.html",
                existing_archive,
            ))
        except Exception:
            existing_dates = set()
        new_dates = {it["date"] for it in all_items}
        lost_dates = existing_dates - new_dates
        if lost_dates:
            print(
                f"\n✗ ABORT: il nuovo archivio perderebbe {len(lost_dates)} "
                f"giorni rispetto a quello esistente ({sorted(lost_dates)})."
                f"\n  → out_dir={out_dir} non contiene tutti i file daily."
                f"\n  → Per forzare comunque: DASHBOARD_FORCE_ARCHIVE=1",
            )
            return  # NON scrivo l'archivio monco

    archive_path.write_text(archive, encoding="utf-8")
    print(f"\nArchivio: {archive_name} ({len(all_items)} report — di cui {len(items)} rigenerati ora) in {out_dir}")

    # MIRROR su index.html per il repo med-tech-daily-check.
    # GitHub Pages serve index.html alla root: la dashboard master fa fetch a
    # https://advfmosca.github.io/med-tech-daily-check/ per parsare la lista
    # report. Tenere allineati i 2 file evita che la lista visualizzata sia
    # outdated rispetto all'archivio reale (regression vista 2026-05-22).
    if project == "medtech":
        index_path = out_dir / "index.html"
        if index_path.exists():  # mirror solo se il file è già presente nel repo
            index_path.write_text(archive, encoding="utf-8")
            print(f"   Mirror: index.html aggiornato (homepage Pages) in {out_dir}")


if __name__ == "__main__":
    main()
