#!/usr/bin/env python3
"""
Alert Zero-Leads — pipeline CEA / MED & TECH (v3)

Logica:
  Per ogni entry CEA + medtech: se oggi.lead_y == 0 AND ieri.lead_y == 0
  → genera alert con:
     · 2-day budget speso
     · CTR (oggi), Freq, Audience, Geo
     · Storico 14gg precedenti la finestra (con ultimo lead)
     · DIAGNOSI: score 0-100 per ciascuna delle 3 cause
       (AD FATIGUE / GEO TROPPO RISTRETTA / OFFERTA NON PERTINENTE)
     · SOLUZIONE per la causa con score più alto: intro + 3 step concreti

Nota tecnica: FMM Consulting NON usa landing page esterne.
Tutte le campagne usano Meta Lead Form (modulo Meta nativo).
Le raccomandazioni NON devono mai citare landing, A/B test landing,
collo di bottiglia post-click su landing, ecc.

Uso:
  python3 alert_zero_leads.py <DATA_REPORT_YYYY-MM-DD>
"""
import json, sys, os
from pathlib import Path
from datetime import datetime, timedelta

REPO = Path("/tmp/dashboard-di-controllo")
SNAP = REPO / "snapshots"

DATA = sys.argv[1] if len(sys.argv) > 1 else "2026-05-28"
LOOKBACK_DAYS = 14

# ---------- helpers ----------
def load_snap(date_iso):
    p = SNAP / f"{date_iso}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))

def date_minus(d_iso, n):
    return (datetime.strptime(d_iso, "%Y-%m-%d") - timedelta(days=n)).strftime("%Y-%m-%d")

def fmt_eur(v):
    if v is None: return "—"
    return (f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")) + " €"

def parse_audience_size(s):
    if not s: return None
    s = str(s).strip().upper().replace(" ", "")
    try:
        if s.endswith("M"): return int(float(s[:-1]) * 1_000_000)
        if s.endswith("K"): return int(float(s[:-1]) * 1_000)
        return int(float(s))
    except Exception:
        return None

def historical_leads(name, project, today_iso, days=LOOKBACK_DAYS, skip=2):
    last_lead_date = None
    leads_total = 0
    spend_total = 0.0
    days_active = 0
    for n in range(skip, skip + days):
        d_iso = date_minus(today_iso, n)
        snap = load_snap(d_iso)
        if not snap: continue
        entries = (snap.get(project) or {}).get("entries") or []
        for e in entries:
            if e.get("name") == name:
                spend_total += e.get("spend_y") or 0.0
                if e.get("spend_y") and e["spend_y"] > 0:
                    days_active += 1
                l = e.get("lead_y") or 0
                leads_total += l
                if l > 0 and last_lead_date is None:
                    last_lead_date = d_iso
                break
    return {
        "leads": leads_total,
        "last_lead_date": last_lead_date,
        "spend": round(spend_total, 2),
        "days_active": days_active,
    }

# ---------- DIAGNOSI: 3 cause scorate ----------
def compute_causes(entry_today, entry_yest, hist):
    """Ritorna (scores_dict, top_cause).
       scores in 0..100 per ad_fatigue / geo_ristretta / offerta_non_pertinente."""
    ctr = entry_today.get("ctr") or 0
    freq = entry_today.get("frequency") or 0
    aud_size = parse_audience_size(entry_today.get("audience_size"))
    days_active = hist.get("days_active") or 0
    hist_leads = hist.get("leads") or 0
    clicks_today = entry_today.get("clicks") or 0
    leads_today = entry_today.get("lead_y") or 0

    # ---- AD FATIGUE ----
    fatigue = 0
    if freq >= 2.5: fatigue += 45
    elif freq >= 2.0: fatigue += 30
    elif freq >= 1.6: fatigue += 18
    if hist_leads >= 5 and days_active >= 5: fatigue += 25
    elif hist_leads >= 2 and days_active >= 4: fatigue += 12
    if days_active >= 7: fatigue += 10
    if ctr >= 1.0 and leads_today == 0 and hist_leads > 0:
        fatigue += 12  # ancora aggancia ma non converte più
    fatigue = min(fatigue, 100)

    # ---- GEO TROPPO RISTRETTA ----
    geo_score = 0
    if aud_size is not None:
        if aud_size < 50_000: geo_score += 55
        elif aud_size < 100_000: geo_score += 35
        elif aud_size < 200_000: geo_score += 18
        if freq >= 1.5 and aud_size < 200_000: geo_score += 20
        if freq >= 2.0 and aud_size < 500_000: geo_score += 15
    if days_active >= 7 and hist_leads >= 3 and aud_size is not None and aud_size < 250_000:
        geo_score += 15
    geo_score = min(geo_score, 100)

    # ---- OFFERTA NON PERTINENTE ----
    # NB: nessun riferimento a landing/modulo esterno.
    # CTR molto basso → messaggio+offerta non aggancia il target
    # CTR alto + 0 lead → l'audience apre ma l'offerta non chiude (promessa-realtà)
    # storico 0 lead pur attivi → offerta non risuona su questo target
    offerta = 0
    if ctr < 0.8 and clicks_today >= 5: offerta += 45
    elif ctr < 1.0 and clicks_today >= 5: offerta += 30
    if hist_leads == 0 and days_active >= 5: offerta += 35
    elif hist_leads == 0 and days_active >= 3: offerta += 18
    if ctr >= 1.5 and leads_today == 0 and clicks_today >= 15: offerta += 22
    if aud_size is not None and aud_size > 1_000_000 and leads_today == 0:
        offerta += 12
    offerta = min(offerta, 100)

    scores = {
        "ad_fatigue": fatigue,
        "geo_ristretta": geo_score,
        "offerta_non_pertinente": offerta,
    }
    # top_cause = max score; tie-breaker priorità ad_fatigue > offerta > geo
    priority = ["ad_fatigue", "offerta_non_pertinente", "geo_ristretta"]
    top = max(priority, key=lambda k: (scores[k], -priority.index(k)))
    return scores, top

# ---------- SOLUZIONE per la top cause ----------
def build_solution(top_cause, entry, hist):
    freq = entry.get("frequency")
    aud_size_str = entry.get("audience_size") or "n.d."
    aud_size = parse_audience_size(aud_size_str)
    ctr = entry.get("ctr") or 0
    hist_leads = hist.get("leads", 0) or 0
    last_lead = hist.get("last_lead_date")
    days_active = hist.get("days_active", 0) or 0

    if top_cause == "ad_fatigue":
        intro_parts = ["Il pubblico è stato esposto ripetutamente alla stessa creative"]
        if freq and freq >= 1.6:
            intro_parts.append(f"(frequenza {freq:.2f})")
        if hist_leads > 0 and last_lead:
            intro_parts.append(f"e ha smesso di rispondere dopo aver generato {hist_leads} lead nei 14gg precedenti (ultimo il {last_lead}). Segnale tipico di saturazione recente della creative attuale.")
        elif days_active >= 5:
            intro_parts.append("attiva ormai da diversi giorni senza più presa sull'audience.")
        else:
            intro_parts.append("e la creative non ha più presa sull'audience.")
        return {
            "label": "Ad Fatigue",
            "intro": " ".join(intro_parts),
            "steps": [
                "Pausare l'ad principale e attivare 2-3 varianti con hook iniziale diverso (problema vs prova sociale vs prima/dopo)",
                "Cambiare formato: se ora è statico passare a video UGC (o viceversa) per spezzare la pattern blindness",
                "Refresh copy: nuovo angolo dell'offerta in apertura, riscrivere primo benefit del testo principale",
            ],
        }

    if top_cause == "geo_ristretta":
        sat_note = ""
        if freq and freq >= 1.5 and aud_size and aud_size < 250_000:
            sat_note = f" e la frequenza è già {freq:.2f}: il bacino disponibile sta venendo saturato"
        elif aud_size and aud_size < 100_000:
            sat_note = ": il bacino è troppo piccolo per sostenere il budget allocato senza saturare in pochi giorni"
        else:
            sat_note = ""
        intro = f"L'audience size è ridotta (≈{aud_size_str}){sat_note}."
        if hist_leads > 0:
            intro += f" Quando convertiva ({hist_leads} lead nei 14gg precedenti) il pubblico era ancora 'fresco' — ora il bacino utile si è esaurito."
        return {
            "label": "Geo troppo ristretta",
            "intro": intro,
            "steps": [
                "Ampliare il raggio geo di +10-15 km o aggiungere 2-3 comuni limitrofi mantenendo il target ICP",
                "Aggiungere 2-3 interessi correlati al servizio per ampliare il pubblico totale senza perdere rilevanza",
                "Avviare in parallelo un lookalike 1-3% sui lead già acquisiti per scalare in modo simile al pubblico che convertiva",
            ],
        }

    # offerta_non_pertinente
    if ctr < 1.0:
        intro = f"CTR {ctr:.2f}% sotto benchmark: il messaggio non aggancia. Il pubblico non riconosce l'offerta come rilevante per sé."
    elif ctr >= 1.5:
        intro = f"CTR {ctr:.2f}% sopra benchmark — l'inserzione attira clic ma il Lead Form Meta non viene completato. La promessa nell'ad non viene percepita come abbastanza forte da chiudere."
    else:
        intro = f"Il pubblico non sta rispondendo: né con CTR (fermo a {ctr:.2f}%) né con conversioni."
    if hist_leads == 0 and days_active >= 5:
        intro += " Lo storico conferma che l'offerta non ha mai convertito stabilmente su questo pubblico."
    elif hist_leads == 0:
        intro += " L'offerta non ha ancora trovato un product-market fit con questo segmento."
    return {
        "label": "Offerta non pertinente",
        "intro": intro,
        "steps": [
            "Rivedere offerta: cambiare prezzo di ingresso, costruire bundle, aggiungere leva di urgenza (scadenza promo, ultimi posti)",
            "Testare 2-3 nuovi angoli del messaggio: emotional (problema-soluzione personale), razionale (numero/risultato), social proof (testimonianza con nome+città)",
            "Verificare allineamento offerta-stagione e segmento: lo stesso prodotto può funzionare diversamente in maggio rispetto a gennaio e su over-45 rispetto a under-35",
        ],
    }

# ---------- scan + format ----------
def scan_project(today_snap, yest_snap, project, project_label, today_iso):
    today_entries = {e["name"]: e for e in (today_snap.get(project) or {}).get("entries") or []}
    yest_entries = {e["name"]: e for e in (yest_snap.get(project) or {}).get("entries") or []}

    alerts = []
    for name, t in today_entries.items():
        if (t.get("lead_y") or 0) > 0:
            continue
        y = yest_entries.get(name)
        if not y:
            continue
        if (y.get("lead_y") or 0) > 0:
            continue
        spend_2d = round((t.get("spend_y") or 0) + (y.get("spend_y") or 0), 2)
        hist = historical_leads(name, project, today_iso)
        causes, top = compute_causes(t, y, hist)
        solution = build_solution(top, t, hist)
        alerts.append({
            "name": name,
            "project": project_label,
            "spend_2d": spend_2d,
            "ctr": t.get("ctr"),
            "geo": t.get("target_geo"),
            "audience_size": t.get("audience_size"),
            "freq": t.get("frequency"),
            "clicks_today": t.get("clicks"),
            "impressions_today": t.get("impressions"),
            "hist": hist,
            "causes": causes,
            "top_cause": top,
            "solution": solution,
        })
    alerts.sort(key=lambda a: -a["spend_2d"])
    return alerts

CAUSE_LABEL = {
    "ad_fatigue": "Ad Fatigue",
    "geo_ristretta": "Geo troppo ristretta",
    "offerta_non_pertinente": "Offerta non pertinente",
}

def format_alert_text(a):
    """Output testo per Slack/markdown."""
    hist = a["hist"]
    if hist["leads"] > 0:
        hist_line = f"📈 Storico {LOOKBACK_DAYS}gg: *{hist['leads']} lead* (ultimo {hist['last_lead_date']}) · {hist['days_active']}gg attivi · spesa {fmt_eur(hist['spend'])}"
    else:
        hist_line = f"📈 Storico {LOOKBACK_DAYS}gg: *0 lead* · {hist['days_active']}gg attivi · spesa {fmt_eur(hist['spend'])}"
    ctr_str = f"{a['ctr']:.2f}%" if a['ctr'] is not None else "—"
    freq_str = f"{a['freq']:.2f}" if a['freq'] else "—"
    causes = a["causes"]
    causes_block = "\n".join(
        f"  • {CAUSE_LABEL[k]}: *{v}%*" + ("  ← causa principale" if k == a["top_cause"] else "")
        for k, v in sorted(causes.items(), key=lambda x: -x[1])
    )
    sol = a["solution"]
    steps = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(sol["steps"]))
    return (
        f"🚨 *{a['name']}* ({a['project']}) — 2gg consecutivi a 0 lead\n"
        f"💸 Budget 2gg: *{fmt_eur(a['spend_2d'])}*  ·  CTR: *{ctr_str}*  ·  Freq: {freq_str}\n"
        f"🎯 Audience: {a['geo'] or 'n.d.'} · size {a['audience_size'] or 'n.d.'}\n"
        f"{hist_line}\n"
        f"\n📊 *DIAGNOSI PROBABILE*\n{causes_block}\n"
        f"\n💡 *SOLUZIONE CONSIGLIATA — {sol['label']}*\n{sol['intro']}\n{steps}\n"
    )

def main():
    today_iso = DATA
    yest_iso = date_minus(today_iso, 1)
    today_snap = load_snap(today_iso)
    yest_snap = load_snap(yest_iso)
    if not today_snap or not yest_snap:
        print(f"❌ Snapshot mancanti: today={bool(today_snap)} yesterday={bool(yest_snap)}")
        sys.exit(1)

    cea_alerts = scan_project(today_snap, yest_snap, "cea", "CEA", today_iso)
    mt_alerts  = scan_project(today_snap, yest_snap, "medtech", "MED & TECH", today_iso)

    header = (f"⚠️ *Alert Zero-Leads 2gg — snapshot {today_iso}*\n"
              f"Entità con 0 lead in {yest_iso} *e* {today_iso}\n"
              f"\n— *CEA*: {len(cea_alerts)} alert  ·  *MED & TECH*: {len(mt_alerts)} alert —\n")
    blocks = [header]
    if cea_alerts:
        blocks.append("\n━━━━━━━━━━━━━━━━━━━━━\n*🏥 CEA*\n━━━━━━━━━━━━━━━━━━━━━\n")
        for a in cea_alerts:
            blocks.append(format_alert_text(a))
            blocks.append("\n")
    if mt_alerts:
        blocks.append("\n━━━━━━━━━━━━━━━━━━━━━\n*🩺 MED & TECH*\n━━━━━━━━━━━━━━━━━━━━━\n")
        for a in mt_alerts:
            blocks.append(format_alert_text(a))
            blocks.append("\n")
    if not cea_alerts and not mt_alerts:
        blocks.append("\n✅ Nessun cliente in stato 0-lead 2gg consecutivi.")

    full = "".join(blocks)

    # ---- Output paths (auto-detect sandbox/local) ----
    def _default_out():
        import glob as _g
        cands = _g.glob("/sessions/*/mnt/outputs/work")
        if cands: return cands[0] + "/_zero_leads_alert.md"
        return "/tmp/_zero_leads_alert.md"
    out_path = Path(os.environ.get("ALERT_OUT", _default_out()))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(full, encoding="utf-8")
    json_path = out_path.with_suffix(".json")
    payload = {"date": today_iso, "cea": cea_alerts, "medtech": mt_alerts}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # alerts.json nel repo dashboard (se presente)
    repo_alerts = Path("/tmp/dashboard-di-controllo/alerts.json")
    if repo_alerts.parent.exists():
        repo_alerts.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(full)
    print(f"\n📄 Salvato: {out_path}\n📄 JSON:    {json_path}")
    if repo_alerts.parent.exists():
        print(f"📄 Repo alerts.json: {repo_alerts}")

if __name__ == "__main__":
    main()
