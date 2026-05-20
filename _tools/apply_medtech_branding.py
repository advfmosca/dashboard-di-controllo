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
<div class="sem-grid" id="sem-grid">
  <div class="kpi rosso"  data-filter="rosso"><div class="label">ROSSO</div><div class="value">{rosso}</div></div>
  <div class="kpi giallo" data-filter="giallo"><div class="label">GIALLO</div><div class="value">{giallo}</div></div>
  <div class="kpi verde"  data-filter="verde"><div class="label">VERDE</div><div class="value">{verde}</div></div>
  <div class="kpi nero"   data-filter="nero"><div class="label">NERO</div><div class="value">{nero}</div></div>
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
  const cards       = Array.from(document.querySelectorAll(".cards .card"));
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
    semGrid.querySelectorAll(".kpi[data-filter]").forEach(el => {
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
