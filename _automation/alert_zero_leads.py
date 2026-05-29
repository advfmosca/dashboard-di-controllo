#!/usr/bin/env python3
"""
Alert Zero-Leads — pipeline CEA / MED & TECH

Logica:
  Per ogni entry CEA + medtech: se oggi.lead_y == 0 AND ieri.lead_y == 0
  → genera alert con:
     · 2-day budget speso
     · CTR (oggi)
     · Audience (Target Geo + Audience Size)
     · Lead storici nei 14gg precedenti (data ultimo lead + count)
     · Analisi audience (perché non genera lead)
     · Consigli media-buyer (cosa cambiare)

Output: stampa il testo del messaggio Slack su stdout.

Uso:
  python3 alert_zero_leads.py <DATA_REPORT_YYYY-MM-DD>
"""
import json, sys, os
from pathlib import Path
from datetime import datetime, timedelta

REPO = Path("/tmp/dashboard-di-controllo")
SNAP = REPO / "snapshots"

DATA = sys.argv[1] if len(sys.argv) > 1 else "2026-05-28"
LOOKBACK_DAYS = 14  # finestra storica per "ha generato conversioni in passato"

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
    """'11.4M' -> 11_400_000 ; '257K' -> 257_000 ; '50' -> 50."""
    if not s: return None
    s = str(s).strip().upper().replace(" ", "")
    try:
        if s.endswith("M"): return int(float(s[:-1]) * 1_000_000)
        if s.endswith("K"): return int(float(s[:-1]) * 1_000)
        return int(float(s))
    except Exception:
        return None

def historical_leads(name, project, today_iso, days=LOOKBACK_DAYS, skip=2):
    """Cerca, nei `days` giorni precedenti (esclusi gli ultimi `skip` = oggi+ieri),
       quante volte l'entity ha generato leads e quando è stato l'ultimo lead."""
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
                    last_lead_date = d_iso  # primo trovato = il più recente (loop in ordine recente→vecchio)
                break
    return {
        "leads": leads_total,
        "last_lead_date": last_lead_date,
        "spend": round(spend_total, 2),
        "days_active": days_active,
    }

def build_reco(entry_today, entry_yest, hist, project):
    """Restituisce lista di 1–3 raccomandazioni media-buyer in base ai segnali."""
    ctr = entry_today.get("ctr") or 0
    freq = entry_today.get("frequency") or 0
    aud_size = parse_audience_size(entry_today.get("audience_size"))
    spend_2d = (entry_today.get("spend_y") or 0) + (entry_yest.get("spend_y") or 0)
    impr_today = entry_today.get("impressions") or 0
    clicks_today = entry_today.get("clicks") or 0

    recos = []

    # 1) Segnale CTR
    if ctr and ctr < 1.0 and spend_2d > 15:
        recos.append("📉 CTR < 1%: creative non aggancia. Rinnovare ad (nuovi hook, formato UGC, prima frase più diretta) — non toccare ancora il targeting.")
    elif ctr and ctr >= 1.5 and (entry_today.get("lead_y") or 0) == 0:
        recos.append("🎯 CTR sopra benchmark ma 0 lead: collo di bottiglia post-click. Audit modulo Meta (campi minimi), verifica pixel/CAPI, controllare offerta sulla landing.")

    # 2) Segnale audience
    if aud_size is not None:
        if aud_size < 50_000:
            recos.append(f"🔭 Audience stretta (≈{entry_today.get('audience_size')}): ampliare geo +10–15 km o aggiungere 2–3 interessi correlati per ridare ossigeno all'asta.")
        elif aud_size > 1_500_000 and spend_2d < 40:
            recos.append(f"🎚 Audience troppo ampia (≈{entry_today.get('audience_size')}) per il budget: restringere geo o aggiungere filtro interessi/comportamenti per concentrare il budget.")

    # 3) Segnale frequenza
    if freq and freq >= 2.5:
        recos.append(f"♻️ Frequenza {freq:.2f}: pubblico saturo. Rotazione creative obbligatoria o pausa 48h e ripartenza con nuova creative.")

    # 4) Segnale storico
    if hist["leads"] > 0:
        recos.append(f"🕐 Aveva generato {hist['leads']} lead negli ultimi {LOOKBACK_DAYS}gg (ultimo {hist['last_lead_date']}): probabile fatica creativa / saturazione recente. Refresh creative + nuovo angolo offerta.")
    elif hist["days_active"] >= 5:
        recos.append("🚧 Mai generato lead negli ultimi 14gg pur essendo attivo: ripensare offerta o landing/form. Considerare pausa per evitare consumo budget improduttivo.")
    elif hist["days_active"] <= 2:
        recos.append("⏱ Campagna giovane (<3gg attivi nello storico): serve ancora qualche giorno per stabilizzare l'apprendimento. Riconsiderare entro 48–72h.")

    # 5) Segnale click ma nessun lead
    if clicks_today >= 20 and (entry_today.get("lead_y") or 0) == 0:
        recos.append(f"🧪 {clicks_today} click oggi senza un solo contatto: A/B test modulo Meta vs landing esterna per capire dove cade il funnel.")

    if not recos:
        recos.append("🔍 Quadro misto, nessun segnale forte: monitorare altre 24h, poi se ancora 0 lead pausare creative principale e provare variazione offerta.")
    return recos[:4]

def build_audience_analysis(entry_today, hist):
    """Genera testo 'ANALISI AUDIENCE — perché non genera leads'."""
    ctr = entry_today.get("ctr") or 0
    freq = entry_today.get("frequency") or 0
    impr = entry_today.get("impressions") or 0
    reach = entry_today.get("reach") or 0
    aud_label = entry_today.get("audience_size") or "n.d."
    geo = entry_today.get("target_geo") or "non specificato"

    bits = []
    # CTR diagnosis
    if ctr < 1.0:
        bits.append(f"CTR {ctr:.2f}% sotto benchmark (≥1%): l'audience non sta rispondendo al messaggio — o creative debole o target sbagliato.")
    elif ctr < 1.5:
        bits.append(f"CTR {ctr:.2f}% in linea ma non brillante: l'audience clicca a fatica.")
    else:
        bits.append(f"CTR {ctr:.2f}% sopra benchmark: l'audience apre, ma non converte → problema post-click.")
    # Freq diagnosis
    if freq >= 2.5:
        bits.append(f"Frequenza {freq:.2f}: il pubblico è già stato esposto più volte, segnale di saturazione/fatigue.")
    elif freq <= 1.2:
        bits.append(f"Frequenza {freq:.2f}: pubblico fresco, c'è ancora margine.")
    # Geo
    bits.append(f"Geo: {geo} · audience size ≈ {aud_label}.")
    # Storico
    if hist["leads"] > 0:
        bits.append(f"Storico: {hist['leads']} lead nei {LOOKBACK_DAYS}gg precedenti (ultimo il {hist['last_lead_date']}) → in passato l'audience convertiva, qualcosa è cambiato di recente.")
    else:
        bits.append(f"Storico: 0 lead nei {LOOKBACK_DAYS}gg precedenti pur con {hist['days_active']}gg attivi → l'audience non ha mai convertito stabilmente.")
    return " ".join(bits)

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
        # 2 consecutive days of 0 leads
        spend_2d = round((t.get("spend_y") or 0) + (y.get("spend_y") or 0), 2)
        hist = historical_leads(name, project, today_iso)
        analysis = build_audience_analysis(t, hist)
        recos = build_reco(t, y, hist, project)
        alerts.append({
            "name": name,
            "project": project_label,
            "spend_2d": spend_2d,
            "ctr": t.get("ctr"),
            "geo": t.get("target_geo"),
            "audience_size": t.get("audience_size"),
            "freq": t.get("frequency"),
            "hist": hist,
            "analysis": analysis,
            "recos": recos,
        })
    # ordina per spend 2gg desc (priorità a chi sta bruciando di più)
    alerts.sort(key=lambda a: -a["spend_2d"])
    return alerts

def format_alert(a):
    hist = a["hist"]
    if hist["leads"] > 0:
        hist_line = f"📈 Storico {LOOKBACK_DAYS}gg: *{hist['leads']} lead* (ultimo {hist['last_lead_date']}) · spesa {fmt_eur(hist['spend'])} · {hist['days_active']}gg attivi"
    else:
        hist_line = f"📈 Storico {LOOKBACK_DAYS}gg: *0 lead* · spesa {fmt_eur(hist['spend'])} · {hist['days_active']}gg attivi"
    ctr_str = f"{a['ctr']:.2f}%" if a['ctr'] is not None else "—"
    freq_str = f"{a['freq']:.2f}" if a['freq'] else "—"
    reco_block = "\n".join(f"  • {r}" for r in a["recos"])
    return (
        f"🚨 *{a['name']}* ({a['project']}) — 2gg consecutivi a 0 lead\n"
        f"💸 Budget speso 2gg: *{fmt_eur(a['spend_2d'])}*  ·  CTR oggi: *{ctr_str}*  ·  Freq: {freq_str}\n"
        f"🎯 Audience: {a['geo'] or 'n.d.'} · size {a['audience_size'] or 'n.d.'}\n"
        f"{hist_line}\n"
        f"\n📊 *ANALISI AUDIENCE — PERCHÉ NON GENERA LEADS*\n{a['analysis']}\n"
        f"\n🛠 *Come media buyer cosa cambierei*\n{reco_block}\n"
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
            blocks.append(format_alert(a))
            blocks.append("\n")
    if mt_alerts:
        blocks.append("\n━━━━━━━━━━━━━━━━━━━━━\n*🩺 MED & TECH*\n━━━━━━━━━━━━━━━━━━━━━\n")
        for a in mt_alerts:
            blocks.append(format_alert(a))
            blocks.append("\n")
    if not cea_alerts and not mt_alerts:
        blocks.append("\n✅ Nessun cliente in stato 0-lead 2gg consecutivi.")

    full = "".join(blocks)
    # Path di default: auto-detect (sandbox Cowork → /sessions/*/mnt/outputs/work; altrimenti /tmp).
    def _default_out():
        import glob as _g
        cands = _g.glob("/sessions/*/mnt/outputs/work")
        if cands:
            return cands[0] + "/_zero_leads_alert.md"
        return "/tmp/_zero_leads_alert.md"
    out_path = Path(os.environ.get("ALERT_OUT", _default_out()))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(full, encoding="utf-8")
    # JSON strutturato per altri consumer
    json_path = out_path.with_suffix(".json")
    json_path.write_text(json.dumps({"date": today_iso, "cea": cea_alerts, "medtech": mt_alerts}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(full)
    print(f"\n📄 Salvato: {out_path}\n📄 JSON:    {json_path}")

if __name__ == "__main__":
    main()
