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

/* Conteggi semafori 4 colonne */
.sem-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 18px; }
.sem-grid .kpi { padding: 11px 13px; }
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

def render_daily(date_iso, cea):
    kpi = cea.get("kpi", {})
    entries = cea.get("entries", [])
    title_date = fmt_date_long(date_iso)
    rosso = kpi.get("rosso", 0); giallo = kpi.get("giallo", 0)
    verde = kpi.get("verde", 0); nero   = kpi.get("nero", 0)

    cards_html = []
    for e in entries:
        col = e.get("status", {}).get("color", "gray")
        cls = COL2CLS.get(col, "nero")
        label = e.get("status", {}).get("label", "—")
        reason = e.get("status", {}).get("reason", "")
        name = e.get("name", "—")
        spend = e.get("spend_y", 0)
        lead = e.get("lead_y", 0)
        cpl = e.get("cpl_y")
        cpl_m3 = e.get("cpl_mean_3d")
        meta_bits = [f"Spesa <b>{fmt_eur(spend)}</b>", f"Lead <b>{lead}</b>"]
        if cpl is not None:
            meta_bits.append(f"CPL <b>{fmt_eur(cpl)}</b>")
        if cpl_m3 is not None:
            meta_bits.append(f"Media 3gg {fmt_eur(cpl_m3)}")
        narrative = e.get("cpl_narrative")
        perf_eval = e.get("performance_eval")
        narrative_html = f'<div class="r-cpl">{escape_html(narrative)}</div>' if narrative else ""
        perf_html = f'<div class="r-perf"><strong>Performance:</strong> {escape_html(perf_eval)}</div>' if perf_eval else ""
        cards_html.append(f"""
<div class="card {cls}">
  <div class="card-head">
    <span class="tag {cls}">{escape_html(label)}</span>
    <div class="camp-name">{escape_html(name)}</div>
  </div>
  <div class="meta">{' · '.join(meta_bits)}</div>
  <div class="reason">{escape_html(reason)}</div>
  {narrative_html}
  {perf_html}
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

  <div class="sem-grid">
    <div class="kpi rosso"><div class="label">ROSSO</div><div class="value">{rosso}</div></div>
    <div class="kpi giallo"><div class="label">GIALLO</div><div class="value">{giallo}</div></div>
    <div class="kpi verde"><div class="label">VERDE</div><div class="value">{verde}</div></div>
    <div class="kpi nero"><div class="label">NERO</div><div class="value">{nero}</div></div>
  </div>

  <div class="legend">
    <span><span class="dot dot-verde"></span><b>VERDE</b> — in linea o sotto media 3gg</span>
    <span><span class="dot dot-giallo"></span><b>GIALLO</b> — CPL fino a +50% vs media 3gg</span>
    <span><span class="dot dot-rosso"></span><b>ROSSO</b> — 0 lead o CPL &gt; +50% media 3gg</span>
    <span><span class="dot dot-nero"></span><b>NERO</b> — nessuna spesa</span>
  </div>

  <div class="cards">
{''.join(cards_html)}
  </div>

  <div class="signature">© Francesco Maria Mosca 2026</div>
</div>
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
