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

/* Semafori grid 4 colonne */
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


def transform(html: str, data: dict | None) -> str:
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
        kpi_block = f"""
<div class="kpis">
  <div class="kpi"><div class="label">Campagne attive</div><div class="value">{n_camp}</div></div>
  <div class="kpi total"><div class="label">Lead OGGI</div><div class="value">{lead_oggi}</div></div>
  <div class="kpi"><div class="label">Lead IERI (stesso orario)</div><div class="value">{lead_ieri}</div></div>
  <div class="kpi"><div class="label">Δ Lead</div><div class="value">{lead_oggi - lead_ieri:+d}</div></div>
</div>
<div class="sem-grid">
  <div class="kpi rosso"><div class="label">ROSSO</div><div class="value">{rosso}</div></div>
  <div class="kpi giallo"><div class="label">GIALLO</div><div class="value">{giallo}</div></div>
  <div class="kpi verde"><div class="label">VERDE</div><div class="value">{verde}</div></div>
  <div class="kpi nero"><div class="label">NERO</div><div class="value">{nero}</div></div>
</div>
"""
        html = re.sub(r'(<div class="legend"[^>]*>)', kpi_block + r'\1', html, count=1)

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
