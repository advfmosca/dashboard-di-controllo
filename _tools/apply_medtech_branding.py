#!/usr/bin/env python3
"""
Applica branding + layout uniforme alla Dashboard di Controllo
a TUTTI i file HTML del repo med-tech-daily-check, in modo idempotente.

Modifiche applicate:
  1. CSS uniforme alla dashboard (palette --bg/--bg-soft/--red/--yellow/--green,
     wrap container, card r-12, brand-header)
  2. Wrap content dentro <div class="wrap">
  3. Wrap h1 + subtitle dentro <div class="brand-header"> (uguale alle pagine CEA)
  4. KPI tiles top (Campagne attive, Lead OGGI, Lead ieri, R/G/V/N semafori grid)
  5. Patch run_daily_pipeline.py per usare orario corrente al posto di 15:59 hardcoded
  6. Rimozione footer 'Snapshot generato...' e tagline
  7. Signature '© Francesco Maria Mosca 2026'

Idempotente: rilanciato non aggiunge duplicati (controlla marker).
"""
import re
import json
import sys
import glob
import os
from pathlib import Path

NEW_CSS = """
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
.subtitle { color: var(--text-muted); font-size: 12.5px; margin: 0 0 0; }

/* KPI tiles top */
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin-bottom: 14px; }
.kpi { background: var(--bg-soft); border: 1px solid var(--border); border-radius: 10px; padding: 13px 15px; min-width: 0; }
.kpi .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 6px; font-weight: 600; }
.kpi .value { font-size: 24px; font-weight: 700; line-height: 1.1; color: #0f0f10; font-variant-numeric: tabular-nums; }
.kpi.total { background: #1c1c1e; border-color: #1c1c1e; }
.kpi.total .label { color: #b8b8bf; }
.kpi.total .value { color: #fff; }

/* Semafori grid 4 colonne — CLICCABILI come filtro */
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
.dot-rosso  { background: var(--red); }
.dot-giallo { background: var(--yellow); }
.dot-verde  { background: var(--green); }
.dot-nero   { background: var(--black); }

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
.rationale { font-size: 13px; margin-top: 4px; }
.reading { font-size: 12.5px; color: #2c2c2c; margin-top: 8px; line-height: 1.55; padding: 9px 11px; background: var(--bg-soft); border-radius: 8px; }
.path { font-size: 12.5px; color: var(--text); margin-top: 6px; line-height: 1.55; background: var(--bg-soft); border-left: 3px solid #0b57d0; padding: 8px 12px; border-radius: 8px; }
.path b { color: #0b57d0; font-weight: 700; }
.path.urgent { border-left-color: var(--red); } .path.urgent b { color: var(--red); }
.path.soft   { border-left-color: var(--green); } .path.soft   b { color: var(--green); }
.freq-badge { display: inline-block; font-size: 10.5px; font-weight: 600; padding: 1px 7px; border-radius: 999px; margin-left: 4px; vertical-align: middle; }
.freq-healthy { background: #d1fadf; color: #14532d; }
.freq-monitor { background: var(--border); color: var(--text-muted); }
.freq-alta    { background: #ffedd5; color: #9a3412; }
.freq-critica { background: #fee2e2; color: #991b1b; }
.empty { color: var(--text-dim); font-style: italic; padding: 16px 0; }

/* Index list */
.section-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin: 0 0 10px; }
.report-list { display: flex; flex-direction: column; gap: 4px; list-style: none; padding: 0; }
.report-list a, .report-item a { display: flex; align-items: center; width: 100%; text-decoration: none; color: inherit; gap: 10px; }
.report-item { display: flex; align-items: center; gap: 10px; padding: 11px 14px; border-radius: 10px; text-decoration: none; color: var(--text); border: 1px solid var(--border); background: #fff; transition: background .15s, border-color .15s; }
.report-item:hover { background: var(--bg-soft); border-color: #d2d2d7; }
.report-item .day-name { font-weight: 600; font-size: 13.5px; }
.report-item .day-counts { font-size: 12.5px; color: var(--text-muted); margin-left: 12px; font-variant-numeric: tabular-nums; }
.report-item .day-counts .c-rosso  { color: var(--red);   font-weight: 700; }
.report-item .day-counts .c-giallo { color: #b88a00;      font-weight: 700; }
.report-item .day-counts .c-verde  { color: var(--green); font-weight: 700; }
.report-item .day-counts .c-nero   { color: #444;         font-weight: 700; }
.report-item .arrow { margin-left: auto; color: var(--text-dim); font-size: 18px; }

.signature { font-size: 11.5px; color: var(--text-dim); margin-top: 28px; padding-top: 14px; border-top: 1px solid var(--border-soft); text-align: center; letter-spacing: 0.02em; }
"""


def get_data_for(html_path: Path):
    """Cerca il file _data/data-YYYY-MM-DD.json corrispondente al daily HTML.
    Ritorna dict o None.
    """
    m = re.search(r"med-tech-daily-(\d{4}-\d{2}-\d{2})\.html$", html_path.name)
    if not m:
        return None
    data_file = html_path.parent / "_data" / f"data-{m.group(1)}.json"
    if data_file.exists():
        try:
            return json.load(open(data_file))
        except Exception:
            return None
    return None


def transform(html, data):
    # 1) Rimuovi prima il vecchio logo wrap (se ancora presente)
    html = re.sub(r'<div class="med-logo-wrap">[\s\S]*?</div>\s*', "", html, flags=re.IGNORECASE)

    # 2) Sostituisci CSS
    if "<style" in html:
        html = re.sub(r"<style[^>]*>[\s\S]*?</style>", f"<style>{NEW_CSS}</style>", html, count=1, flags=re.IGNORECASE)
    else:
        html = re.sub(r"(</head>)", f"<style>{NEW_CSS}</style>\\1", html, count=1)

    # 3) Wrap content in <div class="wrap"> se manca
    if 'class="wrap"' not in html:
        if "<body" in html and "</body>" in html:
            html = re.sub(r"(<body[^>]*>)", r"\1\n<div class=\"wrap\">", html, count=1)
            html = re.sub(r"</body>", "</div>\n</body>", html, count=1)
    # Rename old `container` to `wrap` (idempotente)
    html = re.sub(r'<div class="container">', '<div class="wrap">', html, count=1)

    # 4) Wrap h1 + subtitle in <div class="brand-header"> (idempotente: marker brand-header)
    if 'class="brand-header"' not in html:
        # cerca <h1>...</h1> seguito (con whitespace) da <div class="subtitle">...</div>
        # o <p class="subtitle">...</p>
        m = re.search(
            r'(<h1[^>]*>.*?</h1>)\s*((?:<div|<p)\s+class="subtitle"[^>]*>.*?(?:</div>|</p>))',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if m:
            h1_block = m.group(1)
            sub_block = m.group(2)
            # Normalizza eventuali <div class="subtitle"> in <p class="subtitle">
            sub_block_norm = re.sub(r'<div(\s+class="subtitle"[^>]*>)', r'<p\1', sub_block, count=1)
            sub_block_norm = re.sub(r'</div>\s*$', '</p>', sub_block_norm)
            new_block = f'<div class="brand-header">\n  {h1_block}\n  {sub_block_norm}\n</div>'
            html = html.replace(m.group(0), new_block, 1)
        else:
            # Cerca solo <h1>
            m2 = re.search(r'(<h1[^>]*>.*?</h1>)', html, flags=re.IGNORECASE | re.DOTALL)
            if m2:
                new_block = f'<div class="brand-header">\n  {m2.group(1)}\n</div>'
                html = html.replace(m2.group(0), new_block, 1)

    # 5) Inserisci KPI tiles + sem-grid PRIMA della .legend (se data disponibile)
    if data and 'class="kpis"' not in html and '<div class="legend"' in html:
        counts = data.get("counts", {})
        cards = data.get("cards", [])
        n_camp = len(cards)
        lead_oggi = sum(int(c.get("leads_oggi_so_far", 0) or 0) for c in cards)
        lead_ieri = sum(int(c.get("leads_ieri_so_far", 0) or 0) for c in cards)
        rosso = counts.get("rosso", 0); giallo = counts.get("giallo", 0)
        verde = counts.get("verde", 0); nero   = counts.get("nero", 0)
        total = rosso + giallo + verde + nero
        salute_pct = int(round(verde / total * 100)) if total > 0 else 0
        kpi_block = f"""
<div class="kpis">
  <div class="kpi"><div class="label">Campagne attive</div><div class="value">{n_camp}</div></div>
  <div class="kpi total"><div class="label">Contatti oggi</div><div class="value">{lead_oggi}</div></div>
  <div class="kpi"><div class="label">Contatti ieri (stesso orario)</div><div class="value">{lead_ieri}</div></div>
  <div class="kpi"><div class="label">Δ contatti</div><div class="value">{lead_oggi - lead_ieri:+d}</div></div>
</div>
<div class="smart-summary" id="sem-grid">
  <div class="ss-hero">
    <div class="lbl">Stato salute portafoglio</div>
    <div class="val">{salute_pct}%</div>
    <div class="sub">{verde} di {total} campagne in linea</div>
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
"""
        html = re.sub(r'(<div class="legend"[^>]*>)', kpi_block + r'\1', html, count=1)

    # 5b) Aggiungi data-name e data-color a ogni <div class="card rosso/giallo/verde/nero">
    #     che non ce l'abbia già (idempotente). Estrae il nome dal successivo <div class="camp-name">.
    pattern = re.compile(r'<div class="card\s+(rosso|giallo|verde|nero)([^"]*)">', re.IGNORECASE)
    offset = 0
    for m in list(pattern.finditer(html)):
        color = m.group(1)
        start = m.start() + offset
        end = m.end() + offset
        opening = html[start:end]
        if "data-name=" in opening:
            continue
        # Cerca il prossimo <div class="camp-name">...</div> dopo questa apertura
        camp_m = re.search(r'<div class="camp-name"[^>]*>([\s\S]*?)</div>', html[end:end+1500])
        name = ""
        if camp_m:
            name = re.sub(r'<[^>]+>', '', camp_m.group(1)).strip().lower().replace('"', '').replace('\n', ' ')
        new_open = opening[:-1] + f' data-name="{name}" data-color="{color}">'
        html = html[:start] + new_open + html[end:]
        offset += len(new_open) - len(opening)

    # 5c) Trasforma ogni <div class="card COLOR" ...> nella nuova struttura .card-new
    #     (idempotente: se ha già class="card-new" skippa)
    STATE_HUMAN = {
        "rosso":  ("Da rivedere",  "🔴"),
        "giallo": ("Da monitorare","🟡"),
        "verde":  ("In linea",     "🟢"),
        "nero":   ("Spenta",       "⚫"),
    }
    def _convert_medtech_card(match):
        full = match.group(0)
        if "card-new" in full:
            return full
        color = match.group(1)
        body  = match.group(2)
        human_label, icon = STATE_HUMAN.get(color, ("—", "·"))

        # Estrai i campi
        def grab(pattern, txt, default=""):
            mm = re.search(pattern, txt, re.IGNORECASE | re.DOTALL)
            return mm.group(1).strip() if mm else default

        name = grab(r'<div class="camp-name"[^>]*>([\s\S]*?)</div>', body)
        name = re.sub(r"<[^>]+>", "", name).strip()
        # data-name dal contenitore esterno (lower)
        name_lower = name.lower().replace('"', '')

        # meta_block: tutto il testo delle <div class="meta">
        meta_parts = re.findall(r'<div class="meta"[^>]*>([\s\S]*?)</div>', body, re.IGNORECASE)
        meta_combined = " · ".join(re.sub(r"<[^>]+>", "", x).strip() for x in meta_parts if x.strip())

        # Partita date + giorni rimanenti
        since_str = ""
        m_since = re.search(r"Partita:?\s*([0-9/]+)(?:\s*·\s*([^·]+))?", meta_combined)
        if m_since:
            partita = m_since.group(1)
            extra = (m_since.group(2) or "").strip()
            since_str = f"Partita {partita}" + (f" · {extra}" if extra else "")

        # Lead oggi vs ieri stesso orario
        m_lead = re.search(r"Lead OGGI alle\s*([0-9:]+):\s*<b>(\d+)</b>\s*\(ieri stesso orario\s*(\d+)\)", body)
        if not m_lead:
            m_lead = re.search(r"Lead OGGI alle\s*([0-9:]+):\s*(\d+)\s*\(ieri stesso orario\s*(\d+)\)", body)
        lead_oggi = m_lead.group(2) if m_lead else None
        lead_ieri = m_lead.group(3) if m_lead else None
        ora = m_lead.group(1) if m_lead else ""

        # CPL e delta dal "reading"
        reading = grab(r'<div class="reading"[^>]*>([\s\S]*?)</div>', body)
        reading_text = re.sub(r"<[^>]+>", "", reading).strip()
        m_cpl = re.search(r"CPL\s*([0-9.,]+)\s*€", reading_text)
        cpl_val = m_cpl.group(1) if m_cpl else None
        m_delta = re.search(r"([+\-]\d+(?:[.,]\d+)?)%", reading_text)
        delta_str = m_delta.group(1) if m_delta else None
        m_media = re.search(r"media\s*([0-9.,]+)\s*€", reading_text)
        media_cpl = m_media.group(1) if m_media else None

        # Trend lead/gg
        m_trend = re.search(r"Trend ultimi 3 giorni:\s*<b>([0-9.,]+)</b>", body)
        trend_lead = m_trend.group(1) if m_trend else None

        # Frequency
        m_freq = re.search(r"Frequency 7gg:\s*<b>([0-9.,]+)</b>", body)
        freq = m_freq.group(1) if m_freq else None

        # Cosa faremo (path)
        path = grab(r'<div class="path[^"]*"[^>]*>([\s\S]*?)</div>', body)
        path_text = re.sub(r"<[^>]+>", "", path)
        path_text = re.sub(r"^\s*Cosa faremo per migliorare le performance:\s*", "", path_text).strip()

        # Costruisci KPI cells: contatti oggi (highlight), Costo per contatto, Media contatti/gg, Costo medio
        kpis = []
        if lead_oggi is not None:
            sub = f"stesso ieri: {lead_ieri}" if lead_ieri is not None else ""
            kpis.append(f'<div class="nc-kpi highlight"><div class="lbl">Contatti oggi</div><div class="val">{lead_oggi}</div><div class="delta">{sub}</div></div>')
        if cpl_val is not None:
            delta_html = ""
            if delta_str:
                cls = "up" if delta_str.startswith("+") else "down"
                delta_html = f'<div class="delta {cls}">{delta_str}% vs media</div>'
            kpis.append(f'<div class="nc-kpi"><div class="lbl">Costo per contatto</div><div class="val">{cpl_val}&nbsp;€</div>{delta_html}</div>')
        if trend_lead is not None:
            kpis.append(f'<div class="nc-kpi"><div class="lbl">Contatti media/gg</div><div class="val">{trend_lead}</div><div class="delta">ultimi 3gg</div></div>')
        if media_cpl is not None:
            kpis.append(f'<div class="nc-kpi"><div class="lbl">Costo medio 3gg</div><div class="val">{media_cpl}&nbsp;€</div></div>')

        # "Cosa è successo" = il testo del reading senza il pezzo "Ieri CPL..." già nei KPI
        story_html = ""
        if reading_text:
            story_html = f'<div class="nc-body"><div class="nc-section-lbl">Cosa è successo</div><p class="nc-story">{reading_text}</p></div>'

        action_html = ""
        if path_text:
            action_html = f'<div class="nc-action"><div class="arrow">→</div><div class="text"><b>Cosa faremo.</b> {path_text}</div></div>'

        # Details: freq + meta tecnici
        details_inner = []
        if freq:
            details_inner.append(f'<b>Frequency 7gg:</b> {freq}')
        if meta_combined:
            details_inner.append(meta_combined)
        details_html = ""
        if details_inner:
            details_html = f'<details><summary>Dettaglio tecnico</summary><div class="det-content">{" · ".join(details_inner)}</div></details>'

        return f'''<div class="card-new {color}" data-name="{name_lower}" data-color="{color}">
  <div class="nc-hero">
    <div class="nc-status-row">
      <span class="nc-status"><span class="ico">{icon}</span> {human_label}</span>
      {f'<span class="nc-since">{since_str}</span>' if since_str else ''}
    </div>
    <div class="nc-name">{name}</div>
  </div>
  <div class="nc-kpis">
    {"".join(kpis)}
  </div>
  {story_html}
  {action_html}
  {details_html}
</div>'''

    html = re.sub(
        r'<div class="card\s+(rosso|giallo|verde|nero)[^"]*"[^>]*>([\s\S]*?)</div>\s*(?=<div class="card\s+(?:rosso|giallo|verde|nero)|</div>\s*</div>\s*(?:<div class="empty-result"|<div class="signature"|<script|</body>))',
        _convert_medtech_card,
        html,
    )

    # 6) Rimuovi footer 'Snapshot generato...' / tagline
    html = re.sub(r'<div class="footer">[\s\S]*?</div>\s*', "", html, flags=re.IGNORECASE)
    html = re.sub(r'<div class="footer-note">[\s\S]*?</div>\s*', "", html, flags=re.IGNORECASE)
    html = re.sub(r'<div class="tagline">[\s\S]*?</div>\s*', "", html, flags=re.IGNORECASE)
    # 6b) Rimuovi 'rationale' (CPL ieri X € contro media 3gg Y € (+Z%, ...)) sotto al titolo
    html = re.sub(r'<div class="rationale">[\s\S]*?</div>\s*', "", html, flags=re.IGNORECASE)

    # 7) Signature (idempotente)
    if 'class="signature"' not in html:
        html = re.sub(
            r"(</div>\s*</body>)",
            '<div class="signature">© Francesco Maria Mosca 2026</div>\n\\1',
            html,
            count=1,
        )

    # 7b) Empty-state placeholder (mostrato dal JS quando i filtri non producono risultati)
    if 'id="empty-result"' not in html and 'class="signature"' in html:
        html = html.replace(
            '<div class="signature">',
            '<div class="empty-result" id="empty-result" style="display:none">Nessuna campagna corrisponde ai filtri attivi.</div>\n<div class="signature">',
            1,
        )

    # 8) Script JS per search + filtro semafori cliccabili (idempotente con marker)
    JS_MARKER = "/* MEDTECH_FILTER_JS_INJECTED */"
    if JS_MARKER not in html:
        js_block = """
<script>
""" + JS_MARKER + """
(function() {
  "use strict";
  const SEM_FILTERS = new Set();
  let SEARCH_Q = "";
  const searchInput = document.getElementById("search-input");
  const clearBtn    = document.getElementById("search-clear");
  const semGrid     = document.getElementById("sem-grid");
  const cards       = Array.from(document.querySelectorAll(".cards .card-new, .cards .card"));
  const cntEl       = document.getElementById("filter-count");
  const emptyEl     = document.getElementById("empty-result");

  function applyFilters() {
    const q = SEARCH_Q.toLowerCase().trim();
    let visible = 0;
    for (const c of cards) {
      const name = (c.dataset.name || "").toLowerCase();
      const color = c.dataset.color || "";
      const matchName  = !q || name.indexOf(q) !== -1;
      const matchColor = SEM_FILTERS.size === 0 || SEM_FILTERS.has(color);
      const show = matchName && matchColor;
      c.style.display = show ? "" : "none";
      if (show) visible++;
    }
    if (cntEl) {
      if (q || SEM_FILTERS.size > 0) cntEl.textContent = visible + " su " + cards.length;
      else cntEl.textContent = "";
    }
    if (emptyEl) emptyEl.style.display = (visible === 0 && cards.length > 0) ? "" : "none";
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      SEARCH_Q = searchInput.value;
      if (clearBtn) clearBtn.classList.toggle("hidden", !SEARCH_Q);
      applyFilters();
    });
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { searchInput.value = ""; SEARCH_Q = ""; clearBtn.classList.add("hidden"); applyFilters(); }
    });
  }
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      searchInput.value = ""; SEARCH_Q = ""; clearBtn.classList.add("hidden");
      applyFilters(); searchInput.focus();
    });
  }

  if (semGrid) {
    semGrid.querySelectorAll("[data-filter]").forEach(el => {
      el.addEventListener("click", () => {
        const c = el.dataset.filter;
        if (SEM_FILTERS.has(c)) SEM_FILTERS.delete(c);
        else SEM_FILTERS.add(c);
        el.classList.toggle("active-filter", SEM_FILTERS.has(c));
        semGrid.classList.toggle("has-active", SEM_FILTERS.size > 0);
        applyFilters();
      });
    });
  }
})();
</script>
"""
        if "</body>" in html:
            html = html.replace("</body>", js_block + "\n</body>", 1)

    # 9) PULIZIA TERMINI cliente-friendly su HTML statico (sostituzioni testuali finali).
    # I testi della legenda colori, del titolo H1 e di alcune subtitle sono generati da
    # run_daily_pipeline.py (repo separato). Li riscriviamo qui in modo idempotente.
    text_replacements = [
        # Titolo/sottotitoli
        ("Med &amp; Tech — Daily Check",        "Med &amp; Tech — Andamento campagne"),
        ("Med & Tech — Daily Check",            "Med & Tech — Andamento campagne"),
        ("Med &amp; Tech — Archivio Daily Check",        "Med &amp; Tech — Archivio andamento campagne"),
        ("Med & Tech — Archivio Daily Check",            "Med & Tech — Archivio andamento campagne"),
        # Cutoff orario "15:59 Europe/Rome"  ->  rimosso
        ('alle <b>15:59</b> ora Europe/Rome', "in giornata"),
        ("alle 15:59 ora Europe/Rome",        "in giornata"),
        ("ora Europe/Rome",                    ""),
        # Legenda colori (etichette tecniche)
        ("0 lead o CPL &gt; 50% media",        "0 contatti o costo per contatto &gt; 50% vs media"),
        ("0 lead o CPL > 50% media",           "0 contatti o costo per contatto > 50% vs media"),
        ("CPL fino a +50% vs media",           "Costo per contatto fino a +50% vs media"),
        ("sotto o pari alla media 3gg",        "costo per contatto sotto o pari alla media 3 giorni"),
        # Subtitle del periodo
        ("soglia semaforica su media 3gg (campagne brevi)", "soglia semaforica calcolata sul costo per contatto medio 3 giorni (campagne brevi)"),
        ("Snapshot giornalieri · semaforica su media 3gg",  "Snapshot giornalieri · semaforica calcolata sul costo medio per contatto 3 giorni"),
    ]
    for old, new in text_replacements:
        if old in html:
            html = html.replace(old, new)

    return html


def patch_pipeline_script(root: Path):
    """Patcha _scripts/run_daily_pipeline.py per:
      A) usare orario corrente al posto di '{cutoff_hour}:59' hardcoded
      B) NON emettere più la riga <div class="rationale">...</div>
    Idempotente.
    """
    p = root / "_scripts" / "run_daily_pipeline.py"
    if not p.exists():
        return False
    src = p.read_text(encoding="utf-8")
    changed = False

    # A) Cutoff label da datetime.now()
    marker_a = "# CUTOFF_LABEL_NOW_PATCH"
    if marker_a not in src:
        new_src = src.replace(
            'CUTOFF_LABEL_FMT = "{:02d}:59"',
            f'CUTOFF_LABEL_FMT = "{{:02d}}:59"  {marker_a}',
        )
        inject = (
            "    # CUTOFF_LABEL_NOW_PATCH: override con orario reale di esecuzione\n"
            "    from datetime import datetime as _dt_now\n"
            "    _now = _dt_now.now()\n"
            "    cutoff_label = _now.strftime('%H:%M')\n"
        )
        new_src = re.sub(
            r'(cutoff_label = CUTOFF_LABEL_FMT\.format\(args\.cutoff_hour\)\n)',
            r'\1' + inject,
            new_src,
            count=1,
        )
        if new_src != src:
            src = new_src
            changed = True

    # B) Rimuove la riga rationale dal template di render
    marker_b = "# RATIONALE_REMOVED"
    if marker_b not in src:
        # Pattern: <div class="rationale">...</div> dentro render_card
        new_src = re.sub(
            r'<div class="rationale">\{[^}]+\}</div>\s*\n?',
            f'{{}}  # {marker_b}\n  ',
            src,
            count=1,
        )
        # Approccio alternativo se sopra non matcha: sostituisce la singola f-string
        # Più conservativo: usa indented multi-line f-string come nello script reale.
        if new_src == src:
            # Trova qualsiasi riga che inietti class="rationale" e neutralizzala
            new_src = re.sub(
                r'^(\s*)<div class="rationale">.*?</div>',
                f'\\1{{"" }}  # {marker_b}',
                src,
                count=1,
                flags=re.MULTILINE,
            )
        if new_src != src:
            src = new_src
            changed = True

    if changed:
        p.write_text(src, encoding="utf-8")
        return True
    return False


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    if not (root / ".git").exists():
        print(f"❌ {root} non è un repo git", file=sys.stderr)
        sys.exit(1)
    os.chdir(root)

    # File HTML
    files = sorted(set(
        glob.glob("med-tech-daily-*.html")
        + glob.glob("_template/*.html")
        + (["index.html"] if os.path.isfile("index.html") else [])
    ))
    changed = 0
    for f in files:
        fp = Path(f)
        data = get_data_for(fp) if "daily" in f else None
        original = fp.read_text(encoding="utf-8")
        new = transform(original, data)
        if new != original:
            fp.write_text(new, encoding="utf-8")
            changed += 1
            print(f"  [updated] {f}")
        else:
            print(f"  [skip]    {f}")

    # Patch run_daily_pipeline.py per orario reale
    if patch_pipeline_script(root):
        print(f"  [updated] _scripts/run_daily_pipeline.py (orario reale cutoff)")
        changed += 1
    else:
        print(f"  [skip]    _scripts/run_daily_pipeline.py (già patchato o non trovato)")

    print(f"\nFile aggiornati: {changed}")


if __name__ == "__main__":
    main()
