#!/usr/bin/env python3
"""
build_data.py — Aggregator per la Dashboard di Controllo FMM/AGHC.
v2 — supporto storico, card AGHC, recap stile Slack, contatti = lead+onsite.

Legge i 4 dataset Windsor raw e scrive:
- data.json (puntatore "latest")
- snapshots/<reference_date>.json (storico)

Usage:
  python3 build_data.py --meta meta.json --google google.json \
    --tiktok tiktok.json --medtech medtech.json \
    --workspace "/Users/francescomariamosca/Desktop/Dashboard di Controllo"
"""

import json
import argparse
import re
from datetime import datetime, timedelta
import os
import sys

# ============================ CONFIG ============================

PAGES_URL = "https://advfmosca.github.io/dashboard-di-controllo/"

BEEFAMILY = [
    {"name": "ALBATROS",      "meta_id": "630436088886762",   "google_id": "517-405-1660"},
    {"name": "ARIANNA",       "meta_id": "908982640845603",   "google_id": "752-894-5060"},
    {"name": "BONADIES",      "meta_id": None,                "google_id": "614-938-8109"},
    {"name": "BRORA",         "meta_id": "508414914703199",   "google_id": None},
    {"name": "CICCIO",        "meta_id": "421004342260012",   "google_id": None},
    {"name": "CIRILLO",       "meta_id": "432856047384850",   "google_id": None},
    {"name": "COLOR HOLIDAY", "meta_id": "1576344015714351",  "google_id": None},
    {"name": "CRISTALLO",     "meta_id": "733342015364558",   "google_id": "798-656-6211"},
    {"name": "DELTA BLU",     "meta_id": "236880885374018",   "google_id": "638-552-4256"},
    {"name": "EL CID",        "meta_id": "978507964180533",   "google_id": "343-383-9480"},
    {"name": "HELIOS",        "meta_id": "1515205043021222",  "google_id": "111-356-3903"},
    {"name": "H&V",           "meta_id": "343882111507930",   "google_id": "816-227-1235"},
    {"name": "HOY VILLAGE",   "meta_id": "1234016965549263",  "google_id": "690-064-1891"},
    {"name": "MAURITIUS",     "meta_id": "574208703469432",   "google_id": "678-286-7092"},
    {"name": "MALASPINA",     "meta_id": "900620849401028",   "google_id": "486-060-7017"},
    {"name": "OLIMPIC",       "meta_id": "2855621041150238",  "google_id": "881-991-7013"},
    {"name": "RIVAMARE",      "meta_id": "1240912661421243",  "google_id": "718-909-9456"},
    {"name": "SARDINIA",      "meta_id": "608324351982441",   "google_id": "705-314-5188"},
    {"name": "SOGNO",         "meta_id": "737254889441352",   "google_id": "344-188-9884"},
    {"name": "TETI",          "meta_id": "408911445156468",   "google_id": "277-207-6095"},
    {"name": "TRIESTE",       "meta_id": "692054874845160",   "google_id": "397-800-2496"},
    {"name": "BEEFAMILY 2",   "meta_id": "1506205527775161",  "google_id": None},
]

# AGHC roster — alcune voci condividono lo stesso meta_id (sub-brand dello stesso gruppo).
AGHC = [
    {"name": "ACCENTODI",       "meta_id": "1312718426033158",  "tiktok_id": None},
    {"name": "ADESSO",          "meta_id": "1312718426033158",  "tiktok_id": None},
    {"name": "ALTAFIUMARA",     "meta_id": "1201395876543423",  "tiktok_id": None},
    {"name": "CASTELLO",        "meta_id": "1489903155429629",  "tiktok_id": None},
    {"name": "DELLA PIANA",     "meta_id": "911357333863123",   "tiktok_id": "7504967007843319824"},
    {"name": "HANNAH",          "meta_id": "1528485957725509",  "tiktok_id": None},
    {"name": "HANNAH TERRACES", "meta_id": "1528485957725509",  "tiktok_id": None},
    {"name": "HEMANAIRE",       "meta_id": "217115315497718",   "tiktok_id": None},
    {"name": "LIVATA",          "meta_id": "4666471140299701",  "tiktok_id": None},
    {"name": "LUNETTA",         "meta_id": "687349689221880",   "tiktok_id": "7498330316248203280"},
    {"name": "MAGARI ESTATES",  "meta_id": "1372615496521110",  "tiktok_id": None},
    {"name": "MARCELLA ROYAL",  "meta_id": "821188209852436",   "tiktok_id": "7499093699838607377"},
    {"name": "MARE",            "meta_id": "1432341844596179",  "tiktok_id": "7498679494010667009"},
    {"name": "MONTEMAGNO",      "meta_id": "752450855779035",   "tiktok_id": None},
    {"name": "TERRAZZA FLAVIA", "meta_id": "821188209852436",   "tiktok_id": None},
    {"name": "VILLA ERMELLINA", "meta_id": "30233607946222961", "tiktok_id": "7612666695502118929"},
    {"name": "VILLA GIADA",     "meta_id": "1849759899186169",  "tiktok_id": "7626418949391351815"},
    {"name": "VILLA MILIANI",   "meta_id": "1353024533007038",  "tiktok_id": None},
]

MEDTECH_META_ACCOUNT = "533672775128363"
MEDTECH_FILTER = re.compile(r"Total Lift|Total Sculpt", re.IGNORECASE)

EXCLUDED_SPENDING = {"1576344015714351", "533672775128363"}

# CEA Meta ids — placeholder. CEA è alimentato dai CSV di Alfredo, non da Windsor.
# In linea generale gli account CEA NON compaiono nei rows Meta di Windsor (non sono connessi),
# quindi non finiscono in other_roster. Tenuto come set vuoto per esclusione esplicita.
CEA_META_IDS: set = set()

# Slack targets per le azioni slack auto-generate (assorbiti da fmm-dashboard legacy).
SLACK_CHANNEL_ANOMALIE_SPENDING = "C0B2RE5KSHG"  # #anomalie-spending
SLACK_DM_FRANCESCO = "U0B0P0N7A2U"               # DM Francesco (fallback)

MONTHS_IT = ["gen","feb","mar","apr","mag","giu","lug","ago","set","ott","nov","dic"]

# Ad account URLs
def url_meta(account_id):
    return f"https://business.facebook.com/adsmanager/manage/campaigns?act={account_id}"

def url_google(account_id):
    aid = str(account_id).replace("-", "")
    return f"https://ads.google.com/aw/campaigns?__c={aid}"

def url_tiktok(account_id):
    return f"https://ads.tiktok.com/i18n/dashboard?aadvid={account_id}"

# ============================ HELPERS ============================

def parse_iso(s):
    return datetime.strptime(s, "%Y-%m-%d").date()

def iso(d):
    return d.strftime("%Y-%m-%d")

def fmt_eur(n):
    if n is None:
        return "—"
    s = f"{n:,.2f}"
    s = s.replace(",", "_T_").replace(".", ",").replace("_T_", ".")
    return s + " €"

def fmt_eur_compact(n):
    if n is None: return "—"
    if abs(n) >= 1000:
        return f"{n/1000:.1f}".replace(".", ",") + "k €"
    return fmt_eur(n)

def fmt_pct(p):
    if p is None:
        return "—"
    sign = "+" if p >= 0 else ""
    s = f"{p:.1f}".replace(".", ",")
    return sign + s + "%"

def date_label_it(d):
    return f"{d.day} {MONTHS_IT[d.month-1]} {d.year}"

def date_slash(d):
    return f"{d.day:02d}/{d.month:02d}/{d.year}"

# ============================ DATA STRUCTURES ============================

def build_daily_map(rows, is_meta_with_leads=False):
    """
    From a list of {account_id, account_name, date, spend, [lead fields]}
    build {account_id: {name, daily: {date: spend}, contatti_daily: {date: contatti}}}
    "contatti" = actions_lead + actions_onsite_conversion_lead_grouped (per Meta)
    For Google/TikTok = 0 (no lead tracking in current dataset).
    """
    m = {}
    for r in rows:
        aid = str(r.get("account_id"))
        if aid not in m:
            m[aid] = {"name": r.get("account_name") or aid, "daily": {}, "contatti_daily": {}}
        e = m[aid]
        if r.get("account_name"):
            e["name"] = r["account_name"]
        d = r.get("date")
        spend = float(r.get("spend") or 0)
        e["daily"][d] = e["daily"].get(d, 0) + spend
        if is_meta_with_leads:
            # actions_lead è già il TOTALE di tutti gli eventi "Lead" (pixel website + onsite leadgen + offline).
            # Per gli hotel BF questo cattura i "Contatti acquisiti sul sito web" tracciati via Pixel/CAPI.
            # Per Med & Tech (Instant Forms) actions_lead coincide con actions_onsite_conversion_lead_grouped.
            contatti = int(r.get("actions_lead") or 0)
            if contatti:
                e["contatti_daily"][d] = e["contatti_daily"].get(d, 0) + contatti
    return m

def build_campaign_breakdown(rows, is_meta_with_leads=False, only_active=True):
    """
    Per ogni account_id ritorna lista campagne aggregate sulla finestra dei `rows`.
    Compatibile sia con dataset che hanno il campo `campaign` (nuovo, dal 2026-05-20)
    sia con quelli senza (vecchio: ritorna dict vuoto).

    Output: {account_id: [{name, spend, lead, cpl, active, status}, ...]}
    - active = True se campaign_effective_status (se presente) è ACTIVE oppure
               se non c'è status MA spend > 0
    - Se only_active=True filtra solo le attive
    """
    out = {}
    has_campaign = any(r.get("campaign") for r in rows[:50])
    if not has_campaign:
        return out  # raw "vecchi" senza campagna: niente breakdown
    by_account = {}
    for r in rows:
        camp = (r.get("campaign") or "").strip()
        if not camp:
            continue
        aid = str(r.get("account_id"))
        st  = r.get("campaign_effective_status")  # solo Meta
        key = (aid, camp)
        b = by_account.setdefault(key, {"name": camp, "spend": 0.0, "lead": 0, "status": st})
        b["spend"] += float(r.get("spend") or 0)
        if is_meta_with_leads:
            b["lead"] += int(r.get("actions_lead") or 0)
        # Se in righe successive cambia status (improbabile), prendi l'ultimo non null
        if r.get("campaign_effective_status"):
            b["status"] = r["campaign_effective_status"]
    # Aggrega per account
    for (aid, camp), b in by_account.items():
        cpl = (b["spend"] / b["lead"]) if b["lead"] > 0 else None
        status_active = (b["status"] == "ACTIVE") if b["status"] else (b["spend"] > 0)
        if only_active and not status_active:
            continue
        out.setdefault(aid, []).append({
            "name": b["name"],
            "spend": round(b["spend"], 2),
            "lead": b["lead"] if is_meta_with_leads else None,  # Google: lead non tracciati
            "cpl": round(cpl, 2) if cpl is not None else None,
            "active": status_active,
            "status": b["status"],
        })
    # Sort per ogni account: spend desc
    for aid in out:
        out[aid].sort(key=lambda c: -c["spend"])
    return out


def sum_prev_window(daily, ref_iso, days):
    """Return total over the `days` days preceding ref_iso."""
    ref = parse_iso(ref_iso)
    total = 0.0
    days_with_data = 0
    for i in range(1, days + 1):
        d = ref - timedelta(days=i)
        v = daily.get(iso(d))
        if v is not None:
            total += v
            days_with_data += 1
    return total, days_with_data

def daily_series(daily, ref_iso, days):
    """Return ordered list of (iso_date, spend) for `days` days up to ref_iso (inclusive)."""
    ref = parse_iso(ref_iso)
    out = []
    for i in range(days - 1, -1, -1):
        d = ref - timedelta(days=i)
        out.append((iso(d), daily.get(iso(d), 0)))
    return out

# ============================ STATUS LOGIC ============================

def status_account(spend_y, contatti_y, prev7_spend, prev7_contatti, project_type="hotel"):
    """
    project_type: 'hotel' (BF + AGHC) | 'leadgen' (Med & Tech)
    Hotel: status su anomalia spending; contatti informativi.
    Leadgen: status su CPL (Cost Per Contatto).
    """
    mean7 = prev7_spend / 7 if prev7_spend else 0
    if spend_y == 0 and prev7_spend > 0:
        return {"color": "gray", "label": "Fermo ieri",
                "reason": f"Spending ieri 0 ma media 7gg {fmt_eur(mean7)}"}
    if spend_y == 0:
        return {"color": "gray", "label": "Inattivo",
                "reason": "Nessuna spesa rilevante negli ultimi 8 giorni"}

    if project_type == "leadgen":
        if contatti_y == 0:
            return {"color": "red", "label": "0 contatti",
                    "reason": f"Spesi {fmt_eur(spend_y)} ieri senza generare contatti"}
        cpc_y = spend_y / contatti_y if contatti_y > 0 else None
        cpc_mean = prev7_spend / prev7_contatti if prev7_contatti > 0 else None
        if cpc_y is not None and cpc_mean is not None and cpc_mean > 0:
            ratio = cpc_y / cpc_mean
            delta_pct = (ratio - 1) * 100
            if ratio > 1.5:
                return {"color": "red", "label": "CPL critico",
                        "reason": f"CPL {fmt_eur(cpc_y)} vs media 7gg {fmt_eur(cpc_mean)} ({fmt_pct(delta_pct)})"}
            if ratio > 1.2:
                return {"color": "yellow", "label": "CPL in salita",
                        "reason": f"CPL {fmt_eur(cpc_y)} vs media 7gg {fmt_eur(cpc_mean)} ({fmt_pct(delta_pct)})"}
            return {"color": "green", "label": "In linea",
                    "reason": f"CPL {fmt_eur(cpc_y)} (media 7gg {fmt_eur(cpc_mean)}, {fmt_pct(delta_pct)})"}
        return {"color": "green", "label": "Attivo",
                "reason": f"Spesi {fmt_eur(spend_y)} con {contatti_y} contatti (CPL {fmt_eur(cpc_y) if cpc_y else '—'})"}

    # hotel — status su spending anomalo vs media 7gg
    info_c = ""
    if contatti_y > 0:
        cpc_y = spend_y / contatti_y
        info_c = f" · {contatti_y} contatti (CPL {fmt_eur(cpc_y)})"
    if mean7 > 0:
        ratio = spend_y / mean7
        delta_pct = (ratio - 1) * 100
        if ratio > 1.5:
            return {"color": "red", "label": "Spesa anomala alta",
                    "reason": f"Spesi {fmt_eur(spend_y)} vs media 7gg {fmt_eur(mean7)} ({fmt_pct(delta_pct)}){info_c}"}
        if ratio > 1.3:
            return {"color": "yellow", "label": "Spesa in salita",
                    "reason": f"Spesi {fmt_eur(spend_y)} vs media 7gg {fmt_eur(mean7)} ({fmt_pct(delta_pct)}){info_c}"}
        if ratio < 0.4:
            return {"color": "yellow", "label": "Spesa in calo",
                    "reason": f"Spesi {fmt_eur(spend_y)} vs media 7gg {fmt_eur(mean7)} ({fmt_pct(delta_pct)}){info_c}"}
        return {"color": "green", "label": "In linea",
                "reason": f"Spesi {fmt_eur(spend_y)} (media 7gg {fmt_eur(mean7)}, {fmt_pct(delta_pct)}){info_c}"}
    return {"color": "green", "label": "Attivo",
            "reason": f"Spesi {fmt_eur(spend_y)} (no storico per confronto){info_c}"}

def compute_project(entries, project_type="hotel"):
    tot_spend = sum(e["spend_y"] for e in entries)
    tot_contatti = sum(e["contatti_y"] for e in entries)
    tot_prev_spend = sum(e["prev7_spend"] for e in entries)
    tot_prev_contatti = sum(e["prev7_contatti"] for e in entries)
    actives = sum(1 for e in entries if e["spend_y"] > 0)
    cpc_y = tot_spend / tot_contatti if tot_contatti > 0 else None
    cpc_mean = tot_prev_spend / tot_prev_contatti if tot_prev_contatti > 0 else None
    for e in entries:
        e["status"] = status_account(e["spend_y"], e["contatti_y"], e["prev7_spend"], e["prev7_contatti"], project_type=project_type)
    return {
        "total_spend": tot_spend,
        "total_contatti": tot_contatti,
        "cpc_y": cpc_y,
        "cpc_mean": cpc_mean,
        "actives": actives,
        "total": len(entries),
    }

# ============================ RECAP STYLES ============================

def recap_beefamily_slack(kpi, entries, yesterday):
    reds   = sum(1 for e in entries if e.get("status", {}).get("color") == "red")
    yellows= sum(1 for e in entries if e.get("status", {}).get("color") == "yellow")
    greens = sum(1 for e in entries if e.get("status", {}).get("color") == "green")
    grays  = sum(1 for e in entries if e.get("status", {}).get("color") == "gray")
    lines = [
        f"Bee Family — Daily Check del {date_slash(yesterday)}",
        f"{kpi['actives']} account attivi su {kpi['total']} · {reds} ROSSO · {yellows} GIALLO · {greens} VERDE · {grays} NERO",
        f"Spending: {fmt_eur(kpi['total_spend'])} · Contatti: {kpi['total_contatti']} · CPL medio: {fmt_eur(kpi['cpc_y']) if kpi['cpc_y'] else '—'}",
        f"Dashboard cliente: {PAGES_URL}beefamily.html",
    ]
    return "\n".join(lines)

def recap_medtech_slack(kpi, entries, yesterday):
    """Replica del messaggio della scheduled task med-tech-daily-total-lift-sculpt.
    Niente emoji (inoltrato su WhatsApp), niente landing/copy esterno, solo moduli Lead Ad."""
    reds   = sum(1 for e in entries if e.get("status", {}).get("color") == "red")
    yellows= sum(1 for e in entries if e.get("status", {}).get("color") == "yellow")
    greens = sum(1 for e in entries if e.get("status", {}).get("color") == "green")
    # "NERO" della scheduled task = campagna ferma → mappato sul color "black" (fallback su "gray" per retro-compat)
    blacks = sum(1 for e in entries if e.get("status", {}).get("color") in ("black", "gray"))
    lines = [
        "Med & Tech —",
        f"Daily Check del {date_slash(yesterday)}",
        f"{kpi['actives']} campagne attive · {reds} ROSSO · {yellows} GIALLO · {greens} VERDE · {blacks} NERO",
        f"Apri Report Storico: https://advfmosca.github.io/med-tech-daily-check/",
        f"Apri dashboard: {PAGES_URL}#medtech",
    ]
    return "\n".join(lines)

def recap_aghc_slack(cards, yesterday):
    """Recap copia-incolla stile 'Ciao team' con KPI di visibilità (vanity)."""
    actives = sum(1 for c in cards if c["spend_y"] > 0)
    tot_spend_y = sum(c["spend_y"] for c in cards)
    tot_spend_w = sum(c["spend_window"] for c in cards)
    tot_impr_w = sum(c.get("vanity", {}).get("impressions_window", 0) for c in cards)
    tot_clicks_w = sum(c.get("vanity", {}).get("clicks_window", 0) for c in cards)
    tot_lpv_w = sum(c.get("vanity", {}).get("lpv_window", 0) for c in cards)
    reds = sum(1 for c in cards if c["status"]["color"] == "red")
    yellows = sum(1 for c in cards if c["status"]["color"] == "yellow")

    def fmt_int(n):
        return f"{int(n):,}".replace(",", ".")

    lines = [
        "Ciao a tutti,",
        f"ecco l'andamento delle campagne AGHC negli ultimi 15 giorni:",
        "",
        f"📊 Spending totale: {fmt_eur(tot_spend_w)} · {actives}/{len(cards)} clienti attivi ieri",
        f"👁  Visualizzazioni: {fmt_int(tot_impr_w)} · 🖱  Click: {fmt_int(tot_clicks_w)} · 🌐  Visite landing: {fmt_int(tot_lpv_w)}",
    ]
    if reds or yellows:
        lines.append(f"⚠️  Alert da analizzare: {reds} critici · {yellows} da monitorare (dettagli in dashboard)")
    lines.extend([
        "",
        f"Dashboard live: {PAGES_URL}#aghc",
        "",
        "Per qualsiasi info sono a disposizione! :)",
    ])
    return "\n".join(lines)

# ============================ SPENDING ALERT ============================

def aggregate_spending(rows, platform, target_day, prev7_set):
    agg = {}
    for r in rows:
        aid = str(r.get("account_id"))
        if aid in EXCLUDED_SPENDING:
            continue
        spend = float(r.get("spend") or 0)
        if aid not in agg:
            agg[aid] = {"name": r.get("account_name") or aid, "target": 0, "prev": {}}
        e = agg[aid]
        if r.get("account_name"):
            e["name"] = r["account_name"]
        if r.get("date") == target_day:
            e["target"] += spend
        elif r.get("date") in prev7_set:
            e["prev"][r["date"]] = e["prev"].get(r["date"], 0) + spend
    out = []
    for aid, e in agg.items():
        prev_vals = list(e["prev"].values())
        total_prev = sum(prev_vals)
        mean7 = total_prev / 7
        target = e["target"]
        delta = ((target / mean7) - 1) * 100 if mean7 > 0 else None
        # Ad URL
        if platform == "Meta":
            ad_url = url_meta(aid)
        elif platform == "Google":
            ad_url = url_google(aid)
        else:
            ad_url = url_tiktok(aid)
        out.append({
            "platform": platform,
            "account_id": aid,
            "account_name": e["name"],
            "target": target,
            "mean7": mean7,
            "delta": delta,
            "ad_url": ad_url,
        })
    return out

def classify_spending(results):
    zero = []
    high = []
    for r in results:
        if r["target"] == 0 and r["mean7"] > 0:
            zero.append(r)
            continue
        triggers = []
        if r["target"] > 50:
            triggers.append(">50€")
        if r["delta"] is not None and r["delta"] > 30:
            triggers.append(">30%")
        if triggers:
            r["triggers"] = triggers
            high.append(r)
    # Sort decrescente per spend (più alta in cima)
    zero.sort(key=lambda r: -r["mean7"])
    high.sort(key=lambda r: -r["target"])
    return zero, high

# ============================ AGHC CARDS ============================

def _pick(seed, pool):
    """Pick deterministico (stesso client → stessa variante)."""
    return pool[abs(hash(seed)) % len(pool)]

_WEEKDAYS_IT = ["lunedì","martedì","mercoledì","giovedì","venerdì","sabato","domenica"]

def _build_beefamily_rational(client_name, window_days, total_spend_window,
                               meta_spend_total, google_spend_total, has_google,
                               zero_days, active_days, trend_pct,
                               contatti_window, contatti_y, spend_y,
                               daily_series_data=None,
                               meta_contatti_window=None, google_contatti_window=None,
                               meta_campaigns=None, google_campaigns=None):
    """
    Rational BeeFamily analitico-consulenziale a 3 paragrafi:
    P1 Contesto periodo · P2 Lettura dei dati di acquisizione · P3 Prospettiva strategica.
    Tono professionale, KPI integrati nel testo (CPL + contatti + breakdown Meta/Google).
    """
    avg_daily = total_spend_window / max(window_days, 1)
    pct_zero = (zero_days / max(window_days, 1)) * 100

    # Peak day
    peak_iso, peak_spend = None, 0
    if daily_series_data:
        for d, s in daily_series_data:
            if s and s > peak_spend:
                peak_iso, peak_spend = d, s
    peak_wd = ""
    if peak_iso:
        try: peak_wd = _WEEKDAYS_IT[parse_iso(peak_iso).weekday()]
        except Exception: peak_wd = ""

    cn = client_name
    cpl_window = (total_spend_window / contatti_window) if contatti_window > 0 else None
    meta_contatti = meta_contatti_window if meta_contatti_window is not None else contatti_window
    google_contatti = google_contatti_window if google_contatti_window is not None else 0
    has_meta = meta_spend_total > 0 or meta_contatti > 0
    has_g    = has_google and (google_spend_total > 0 or google_contatti > 0)
    meta_cpl   = (meta_spend_total   / meta_contatti)   if meta_contatti   > 0 else None
    google_cpl = (google_spend_total / google_contatti) if google_contatti > 0 else None

    def fmt_int(n):
        if n is None or n == 0: return "0"
        return f"{int(n):,}".replace(",", ".")

    def wrap(p1, p2, p3):
        return f"<p>{p1}</p><p>{p2}</p><p>{p3}</p>"

    # =====================================================================
    # P1 — Contesto periodo
    # =====================================================================
    peak_clause = f", con la giornata di massima erogazione di {peak_wd or 'centro periodo'} a {fmt_eur(peak_spend)}" if peak_iso else ""
    if total_spend_window == 0:
        p1 = (f"Nelle ultime due settimane {cn} è rimasto fermo: nessuna spesa sull'account, "
              f"con la riserva di budget tenuta integra per i cicli successivi.")
    elif pct_zero > 30 and zero_days >= 3:
        avg_active = total_spend_window / max(active_days, 1)
        p1 = (f"Negli ultimi {window_days} giorni {cn} mostra un'erogazione frammentata: "
              f"l'account è rimasto fermo per {zero_days} giornate su {window_days} e i "
              f"{fmt_eur(total_spend_window)} di periodo si concentrano sui {active_days} "
              f"giorni effettivi, con una media a regime di {fmt_eur(avg_active)} al giorno.")
    elif trend_pct is not None and trend_pct > 25:
        p1 = (f"Negli ultimi {window_days} giorni {cn} accelera in modo netto: la spesa della "
              f"seconda metà del periodo cresce del {trend_pct:.0f}% rispetto alla prima, "
              f"portando il totale a {fmt_eur(total_spend_window)} con un ritmo medio di "
              f"{fmt_eur(avg_daily)} al giorno{peak_clause}.")
    elif trend_pct is not None and trend_pct < -25:
        p1 = (f"Negli ultimi {window_days} giorni {cn} attraversa una fase di raffreddamento: "
              f"la spesa della seconda metà scende del {abs(trend_pct):.0f}% rispetto alla prima, "
              f"chiudendo il periodo a {fmt_eur(total_spend_window)} totali con una media di "
              f"{fmt_eur(avg_daily)} al giorno{peak_clause}.")
    else:
        delta = f" ({trend_pct:+.0f}% tra prima e seconda metà del periodo)" if trend_pct is not None else ""
        p1 = (f"Negli ultimi {window_days} giorni {cn} mantiene una traiettoria di crociera"
              f"{delta}: {fmt_eur(total_spend_window)} di investimento distribuiti su "
              f"{active_days} giorni effettivi, a un ritmo medio di {fmt_eur(avg_daily)} "
              f"al giorno{peak_clause}.")

    # =====================================================================
    # P2 — Lettura dei dati: contatti, CPL, breakdown canale
    # =====================================================================
    if contatti_window > 0 and cpl_window is not None:
        # Lettura efficienza CPL
        if cpl_window < 5:
            cpl_qual = "molto efficiente"
        elif cpl_window < 15:
            cpl_qual = "in linea con il benchmark di settore"
        elif cpl_window < 30:
            cpl_qual = "leggermente sopra il benchmark"
        else:
            cpl_qual = "sopra il benchmark, da consolidare"

        opener = (f"Sul fronte conversioni il periodo restituisce <strong>{fmt_int(contatti_window)} "
                  f"contatti generati</strong> a un CPL medio di <strong>{fmt_eur(cpl_window)}</strong> "
                  f"— un costo per lead {cpl_qual} considerato l'investimento medio di "
                  f"{fmt_eur(avg_daily)} al giorno.")
    else:
        opener = (f"Sul fronte conversioni il periodo chiude a zero contatti diretti a fronte di "
                  f"{fmt_eur(total_spend_window)} di investimento, con una media di "
                  f"{fmt_eur(avg_daily)} al giorno.")

    # Mix canali
    mix_clause = ""
    if has_meta and has_g:
        bits = []
        if meta_cpl is not None:
            bits.append(f"<strong>Meta</strong> con {fmt_int(meta_contatti)} contatti a CPL {fmt_eur(meta_cpl)}")
        elif meta_spend_total > 0:
            bits.append(f"<strong>Meta</strong> con {fmt_eur(meta_spend_total)} di spesa ma nessun contatto attribuito")
        if google_cpl is not None:
            bits.append(f"<strong>Google</strong> con {fmt_int(google_contatti)} contatti a CPL {fmt_eur(google_cpl)}")
        elif google_spend_total > 0:
            bits.append(f"<strong>Google</strong> con {fmt_eur(google_spend_total)} di spesa senza contatti attribuiti")
        if bits:
            mix_clause = " Il mix di acquisizione si divide tra " + " e ".join(bits) + "."
    elif has_meta and meta_cpl is not None and contatti_window > 0:
        mix_clause = f" L'intero volume di contatti è stato lavorato sul canale <strong>Meta</strong> a CPL {fmt_eur(meta_cpl)}."
    elif has_g and google_cpl is not None and contatti_window > 0:
        mix_clause = f" <strong>Google</strong> ha lavorato come unico canale di lead generation, con CPL {fmt_eur(google_cpl)}."

    # Frase contatti di ieri
    yesterday_clause = ""
    if contatti_y > 50:
        yesterday_clause = f" L'ultimo giorno ha registrato <strong>{contatti_y} contatti</strong>, segnale che il messaggio attuale intercetta in modo efficace la domanda."
    elif contatti_y > 0:
        yesterday_clause = f" Tra le conversioni di ieri sono entrati {contatti_y} contatti, in linea con la media del periodo."

    p2 = opener + mix_clause + yesterday_clause

    # =====================================================================
    # P3 — Prospettiva strategica
    # =====================================================================
    no_contacts = contatti_window == 0

    if total_spend_window == 0:
        p3 = (f"Lo scenario è di attesa controllata: la riserva di budget intatta permetterà "
              f"di riaprire il canale con un assetto fresco quando la domanda tornerà sui livelli previsti.")
    elif pct_zero > 30 and zero_days >= 3:
        p3 = (f"La priorità è ripristinare una continuità di erogazione su 7 giorni: "
              f"l'attuale frammentazione costringe l'algoritmo a ricalibrarsi a ogni ripartenza, "
              f"impedendo di stabilizzare il CPL e di consolidare i bacini di pubblico già lavorati.")
    elif no_contacts and spend_y > 0:
        p3 = (f"Il segnale di zero contatti a fronte di spesa attiva richiede un'analisi tecnica: "
              f"si tratta verosimilmente di una rottura nel flusso di tracciamento o di un disallineamento "
              f"tra creatività e funnel, da verificare prima che la prossima settimana confermi il pattern.")
    elif trend_pct is not None and trend_pct > 25:
        p3 = (f"L'accelerazione in corso va sostenuta con un'attenta lettura della frequency e "
              f"del CPL giornaliero: in fase di pressione competitiva crescente, la sostenibilità "
              f"della curva dipende dalla rotazione tempestiva dell'asset creativo, prima che il "
              f"pubblico mostri segnali di saturazione.")
    elif trend_pct is not None and trend_pct < -25:
        p3 = (f"La contrazione dei volumi nella seconda metà del periodo evidenzia una perdita di "
              f"presenza che, se prolungata, rischia di erodere il bacino di pubblico già qualificato. "
              f"La lettura strategica suggerisce un rilancio controllato prima che l'algoritmo perda "
              f"la curva di apprendimento.")
    else:
        p3 = (f"In uno scenario competitivo che continua a comprimere i margini di efficienza, "
              f"mantenere questa cadenza significa difendere il CPL attuale senza forzare il sistema: "
              f"la base dati che stiamo costruendo nel periodo è coerente con il piano di acquisizione "
              f"concordato ed è la fondazione su cui si misurerà la stagione.")

    return wrap(p1, p2, p3)


def _build_aghc_rational(client_name, window_days, total_spend_window,
                          meta_spend_total, tt_spend_total, has_tiktok,
                          zero_days, active_days, trend_pct,
                          contatti_y, spend_y, daily_series_data=None,
                          vanity_window=None):
    """
    Rational AGHC analitico-consulenziale a 3 paragrafi:
    P1 Contesto periodo · P2 Lettura dei dati di visibilità · P3 Prospettiva strategica.
    Tono professionale, KPI integrati nel testo, niente bullet o label uppercase.
    """
    avg_daily = total_spend_window / max(window_days, 1)
    pct_zero = (zero_days / max(window_days, 1)) * 100

    # Peak day estratto dalla serie giornaliera
    peak_iso, peak_spend = None, 0
    if daily_series_data:
        for d, s in daily_series_data:
            if s and s > peak_spend:
                peak_iso, peak_spend = d, s
    peak_wd = ""
    if peak_iso:
        try: peak_wd = _WEEKDAYS_IT[parse_iso(peak_iso).weekday()]
        except Exception: peak_wd = ""

    cn = client_name
    tt_share = (tt_spend_total / total_spend_window * 100) if total_spend_window else 0

    # Vanity 15gg
    v = vanity_window or {}
    v_impr   = int(v.get("impressions", 0) or 0)
    v_reach  = int(v.get("reach", 0) or 0)
    v_clicks = int(v.get("clicks", 0) or 0)
    v_eng    = int(v.get("page_eng", 0) or 0)
    v_lpv    = int(v.get("lpv", 0) or 0)
    has_vanity = (v_impr + v_clicks + v_eng) > 0

    def fmt_int(n):
        if n is None or n == 0: return "0"
        return f"{int(n):,}".replace(",", ".")

    def wrap(p1, p2, p3):
        return f"<p>{p1}</p><p>{p2}</p><p>{p3}</p>"

    # =====================================================================
    # P1 — Contesto: andamento spesa e cadenza del periodo
    # =====================================================================
    peak_clause = f", con la giornata di massima erogazione di {peak_wd or 'centro periodo'} a {fmt_eur(peak_spend)}" if peak_iso else ""
    if total_spend_window == 0:
        p1 = (f"Nelle ultime due settimane {cn} è rimasto fermo: nessuna spesa sull'account, "
              f"con la riserva di budget tenuta integra per le finestre commerciali successive.")
    elif pct_zero > 30 and zero_days >= 3:
        avg_active = total_spend_window / max(active_days, 1)
        p1 = (f"Negli ultimi {window_days} giorni {cn} mostra un'erogazione frammentata: "
              f"l'account è rimasto fermo per {zero_days} giornate su {window_days} e i "
              f"{fmt_eur(total_spend_window)} di periodo si concentrano sui {active_days} "
              f"giorni effettivi, con una media a regime di {fmt_eur(avg_active)} al giorno.")
    elif trend_pct is not None and trend_pct > 25:
        p1 = (f"Negli ultimi {window_days} giorni {cn} accelera in modo netto: la spesa della "
              f"seconda metà del periodo cresce del {trend_pct:.0f}% rispetto alla prima, "
              f"portando il totale a {fmt_eur(total_spend_window)} con un ritmo medio di "
              f"{fmt_eur(avg_daily)} al giorno{peak_clause}.")
    elif trend_pct is not None and trend_pct < -25:
        p1 = (f"Negli ultimi {window_days} giorni {cn} attraversa una fase di raffreddamento: "
              f"la spesa della seconda metà scende del {abs(trend_pct):.0f}% rispetto alla prima, "
              f"chiudendo il periodo a {fmt_eur(total_spend_window)} totali con una media di "
              f"{fmt_eur(avg_daily)} al giorno{peak_clause}.")
    else:
        delta = f" ({trend_pct:+.0f}% tra prima e seconda metà del periodo)" if trend_pct is not None else ""
        p1 = (f"Negli ultimi {window_days} giorni {cn} mantiene una traiettoria di crociera"
              f"{delta}: {fmt_eur(total_spend_window)} di investimento distribuiti su "
              f"{active_days} giorni effettivi di erogazione, a un ritmo medio di "
              f"{fmt_eur(avg_daily)} al giorno{peak_clause}.")

    # =====================================================================
    # P2 — Lettura dei dati: visibilità, reach, engagement, mix canali
    # =====================================================================
    parts_p2 = []
    if has_vanity:
        # Bilancio aggregato visibilità
        vis_phrase = f"<strong>{fmt_int(v_impr)} impression</strong>"
        if v_reach > 0:
            vis_phrase += f" che hanno raggiunto <strong>{fmt_int(v_reach)} persone uniche</strong>"
        vis_phrase += f", <strong>{fmt_int(v_eng)} interazioni</strong> con la pagina e <strong>{fmt_int(v_clicks)} click</strong>"
        if v_lpv > 50:
            vis_phrase += f" — di cui {fmt_int(v_lpv)} con atterraggio sul sito"

        # Engagement rate (interazioni / impression)
        eng_rate = (v_eng / v_impr * 100) if v_impr > 0 else 0
        if eng_rate >= 20:
            bench_clause = f" Il rapporto interazioni/impression del {eng_rate:.1f}% colloca l'account <strong>sopra il benchmark di categoria</strong> per il segmento hospitality."
        elif eng_rate >= 10:
            bench_clause = f" Il rapporto interazioni/impression del {eng_rate:.1f}% si colloca <strong>in linea con il benchmark</strong> di settore."
        else:
            bench_clause = f" Il rapporto interazioni/impression del {eng_rate:.1f}% segnala <strong>spazio di miglioramento</strong> sull'efficacia del messaggio."

        parts_p2.append(f"L'analisi della visibilità del periodo restituisce {vis_phrase}.{bench_clause}")
    else:
        parts_p2.append(f"Sul piano dei volumi il periodo si è mosso su un ritmo medio di {fmt_eur(avg_daily)} giornalieri, senza picchi di esposizione fuori scala.")

    # Mix canali
    if has_tiktok and tt_spend_total > 0 and tt_share >= 8:
        parts_p2.append(
            f"Il mix di investimento vede <strong>TikTok al {tt_share:.0f}%</strong> "
            f"({fmt_eur(tt_spend_total)}) come secondo canale di presidio sul target sotto i "
            f"35 anni, mentre Meta lavora il pubblico storico del brand."
        )
    elif has_tiktok and tt_spend_total > 0:
        parts_p2.append(
            f"TikTok contribuisce in modo marginale ({fmt_eur(tt_spend_total)}, "
            f"{tt_share:.0f}% del mix) come supporto al canale Meta principale."
        )
    elif has_tiktok and tt_spend_total == 0:
        parts_p2.append("Nel periodo è stato presidiato il solo canale Meta, con TikTok in stand-by.")

    p2 = " ".join(parts_p2)

    # =====================================================================
    # P3 — Prospettiva strategica (sostituisce "prossima mossa interna")
    # =====================================================================
    if total_spend_window == 0:
        p3 = (f"Lo scenario è di attesa controllata: la riserva di budget intatta diventa la "
              f"leva per la prossima apertura stagionale, dove la concentrazione del fuoco su "
              f"finestre di domanda mirate permetterà di massimizzare il rendimento di ogni euro investito.")
    elif pct_zero > 30 and zero_days >= 3:
        p3 = (f"L'elemento da consolidare nel prossimo ciclo è la continuità quotidiana: "
              f"senza copertura su tutti i giorni della settimana l'algoritmo perde la curva di "
              f"apprendimento e la frequenza non si stabilizza, indebolendo la presenza nelle aste "
              f"competitive del segmento.")
    elif trend_pct is not None and trend_pct > 25:
        p3 = (f"L'accelerazione in corso va monitorata in chiave CPM e frequency: in questa fase "
              f"di pressione competitiva crescente, la sostenibilità della curva si misura sulla "
              f"capacità di rinnovare l'asset creativo prima che il pubblico si saturi e i costi "
              f"d'asta inizino a salire più rapidamente dei volumi.")
    elif trend_pct is not None and trend_pct < -25:
        p3 = (f"La contrazione dei volumi richiede un'analisi di scenario: il calo di "
              f"{abs(trend_pct):.0f}% nella seconda metà del periodo evidenzia una perdita di "
              f"presenza nelle aste che, se prolungata, rischia di erodere la visibilità organica "
              f"costruita nelle settimane precedenti.")
    else:
        p3 = (f"In uno scenario competitivo che continua a comprimere i margini di visibilità, "
              f"mantenere questa cadenza significa preservare il presidio sui canali principali "
              f"senza forzature: la base dati che stiamo costruendo nel periodo è quella su cui "
              f"si fonderà la lettura della stagione, ed è coerente con il piano media concordato.")

    return wrap(p1, p2, p3)


def _build_aghc_day_entry(date_iso, spend_combined, vanity_for_day):
    """Costruisce l'entry giornaliera per `aghc.cards[].series`.

    - `spend_combined` = spend Meta+TikTok aggregato del giorno (sempre presente).
    - `vanity_for_day` = dict da vanity_idx per (account_id, date) o None. Se presente,
      arricchisce con impressions/reach/page_engagement/clicks/lpv (solo Meta).
    Backward-compat: se vanity assente, l'entry resta {date, spend}.
    """
    entry = {"date": date_iso, "spend": round(spend_combined, 2)}
    if vanity_for_day:
        if vanity_for_day.get("impressions"):
            entry["impressions"] = vanity_for_day["impressions"]
        if vanity_for_day.get("reach"):
            entry["reach"] = vanity_for_day["reach"]
        if vanity_for_day.get("page_eng"):
            entry["page_engagement"] = vanity_for_day["page_eng"]
        if vanity_for_day.get("clicks"):
            entry["clicks"] = vanity_for_day["clicks"]
        if vanity_for_day.get("lpv"):
            entry["lpv"] = vanity_for_day["lpv"]
    return entry


def build_aghc_cards(meta_rows, tiktok_rows, y_iso, yesterday, window_days=15, vanity_rows=None, budgets_config=None):
    """
    Una card per cliente AGHC. Se più voci roster condividono lo stesso meta_id,
    le aggrego in UNA card con nomi merged (es. "ACCENTODI + ADESSO").
    vanity_rows: lista opzionale [{account_id, date, impressions, clicks, actions_landing_page_view}]
    da cui estraiamo le metriche vanity per le card.
    """
    meta_map = build_daily_map(meta_rows, is_meta_with_leads=True)
    tiktok_map = build_daily_map(tiktok_rows, is_meta_with_leads=False)

    # Budgets per meta_id
    budgets_year = None
    budgets_clients = {}
    if budgets_config:
        budgets_year = budgets_config.get("year")
        budgets_clients = budgets_config.get("clients", {})

    # YTD spending per meta_id e per tiktok_id sull'anno corrente del config (o anno yesterday se non specificato)
    target_year = budgets_year or yesterday.year
    target_year_prefix = str(target_year) + "-"
    ytd_by_account = {}  # account_id → sum spend in target year
    for r in meta_rows + tiktok_rows:
        d = r.get("date") or ""
        if not d.startswith(target_year_prefix):
            continue
        aid = str(r.get("account_id"))
        ytd_by_account[aid] = ytd_by_account.get(aid, 0) + float(r.get("spend") or 0)

    # Indice vanity (account_id, date) → {impressions, reach, clicks, lpv, page_eng}
    # `reach` è opzionale: il fetch Meta del refresh-dashboard-data lo include solo dal 2026-05-20.
    # Per i record precedenti il campo sarà 0 e gli aggregati `reach_window`/`reach_y` resteranno 0.
    # NOTA Meta: la riga ha più record per giorno (uno per campaign). Sommiamo impressions/clicks/lpv/page_eng
    # in modo additivo, ma `reach` di Meta è già deduplicato a livello account/giorno — quindi prendiamo
    # il MASSIMO osservato (proxy ragionevole della reach unica account-level).
    vanity_idx = {}
    if vanity_rows:
        for r in vanity_rows:
            key = (str(r.get("account_id")), r.get("date"))
            cur = vanity_idx.get(key) or {
                "impressions": 0, "reach": 0, "clicks": 0, "lpv": 0, "page_eng": 0,
            }
            cur["impressions"] += int(r.get("impressions") or 0)
            cur["clicks"] += int(r.get("clicks") or 0)
            cur["lpv"] += int(r.get("actions_landing_page_view") or 0)
            cur["page_eng"] += int(r.get("actions_page_engagement") or 0)
            cur["reach"] = max(cur["reach"], int(r.get("reach") or 0))
            vanity_idx[key] = cur

    # group AGHC voci per meta_id
    by_meta = {}
    for c in AGHC:
        mid = c.get("meta_id")
        if mid not in by_meta:
            by_meta[mid] = {"names": [], "tiktok_ids": set()}
        by_meta[mid]["names"].append(c["name"])
        if c.get("tiktok_id"):
            by_meta[mid]["tiktok_ids"].add(c["tiktok_id"])

    cards = []
    for mid, info in by_meta.items():
        if not mid:
            continue
        merged_name = " + ".join(info["names"])
        meta_e = meta_map.get(mid) or {"daily": {}, "contatti_daily": {}, "name": merged_name}
        # Aggregate metriche meta sul window
        meta_series = daily_series(meta_e["daily"], y_iso, window_days)
        meta_spend_total = sum(s for _, s in meta_series)
        meta_spend_y = meta_e["daily"].get(y_iso, 0)
        # Prev7 per status
        prev7_spend, _ = sum_prev_window(meta_e["daily"], y_iso, 7)
        prev7_contatti, _ = sum_prev_window(meta_e["contatti_daily"], y_iso, 7)
        contatti_y = int(meta_e["contatti_daily"].get(y_iso, 0))

        # TikTok aggregato (eventuali)
        tt_spend_total = 0
        tt_spend_y = 0
        tt_zero_days = 0
        tt_series = []
        for tt_id in info["tiktok_ids"]:
            tt_e = tiktok_map.get(tt_id) or {"daily": {}}
            tt_series_one = daily_series(tt_e["daily"], y_iso, window_days)
            for d, s in tt_series_one:
                pass
            tt_spend_total += sum(s for _, s in tt_series_one)
            tt_spend_y += tt_e["daily"].get(y_iso, 0)

        total_spend_window = meta_spend_total + tt_spend_total
        # Considera solo i giorni effettivamente coperti dal dataset.
        # zero_days = solo giorni con valore esplicito 0 (non missing).
        days_with_data = sum(1 for d, _ in meta_series if d in meta_e["daily"])
        zero_days_meta = sum(1 for d, s in meta_series if d in meta_e["daily"] and s == 0)
        active_days_meta = sum(1 for d, s in meta_series if d in meta_e["daily"] and s > 0)
        effective_window = days_with_data if days_with_data > 0 else window_days

        # Status
        st = status_account(meta_spend_y + tt_spend_y, contatti_y, prev7_spend, prev7_contatti, project_type="hotel")

        # Trend: confronta media prima metà vs seconda metà — solo sui giorni con dati
        actual_series = [(d, s) for d, s in meta_series if d in meta_e["daily"]]
        mid_idx = len(actual_series) // 2
        first_half = [s for _, s in actual_series[:mid_idx]]
        second_half = [s for _, s in actual_series[mid_idx:]]
        first_mean = sum(first_half) / len(first_half) if first_half else 0
        second_mean = sum(second_half) / len(second_half) if second_half else 0
        if first_mean > 0:
            trend_pct = ((second_mean / first_mean) - 1) * 100
        else:
            trend_pct = None
        if trend_pct is None:
            trend_arrow, trend_label = "—", "n/d"
        elif trend_pct > 10:
            trend_arrow, trend_label = "↑", "in crescita"
        elif trend_pct < -10:
            trend_arrow, trend_label = "↓", "in calo"
        else:
            trend_arrow, trend_label = "→", "stabile"

        # Vanity metrics aggregati sul window (impressions, reach, clicks, landing page views, page engagement)
        # CALCOLATI PRIMA del rational così possono essere passati come argomento.
        # Per `reach` la window NON è la somma giornaliera (over-count perché utenti unici si ripetono)
        # ma il MAX giornaliero osservato sulla finestra — proxy ragionevole della reach account-level.
        # Da rivedere appena disponibile l'endpoint Meta `reach` con time_increment=15.
        van_impr_w = 0
        van_reach_w = 0
        van_clicks_w = 0
        van_lpv_w = 0
        van_eng_w = 0
        van_impr_y = 0
        van_reach_y = 0
        van_clicks_y = 0
        van_lpv_y = 0
        van_eng_y = 0
        for d, _ in meta_series:
            v = vanity_idx.get((mid, d))
            if v:
                van_impr_w += v["impressions"]
                van_reach_w = max(van_reach_w, v.get("reach", 0))
                van_clicks_w += v["clicks"]
                van_lpv_w += v["lpv"]
                van_eng_w += v.get("page_eng", 0)
                if d == y_iso:
                    van_impr_y = v["impressions"]
                    van_reach_y = v.get("reach", 0)
                    van_clicks_y = v["clicks"]
                    van_lpv_y = v["lpv"]
                    van_eng_y = v.get("page_eng", 0)

        # ===== Budget approvato + Speso YTD =====
        budget_info = budgets_clients.get(mid, {}) if isinstance(budgets_clients, dict) else {}
        budget_annuale = budget_info.get("budget_annuale")
        ytd_seed = budget_info.get("ytd_seed") or 0
        ytd_spent_from_data = ytd_by_account.get(mid, 0)
        # Aggiungi anche eventuali TikTok ids dello stesso cliente
        for tt_id in info["tiktok_ids"]:
            ytd_spent_from_data += ytd_by_account.get(tt_id, 0)
        ytd_spent = round(ytd_seed + ytd_spent_from_data, 2)
        budget_pct = (ytd_spent / budget_annuale * 100) if budget_annuale and budget_annuale > 0 else None

        # ===== Rational descrittivo argomentato con vanity inline =====
        rational = _build_aghc_rational(
            client_name=merged_name,
            window_days=effective_window,
            daily_series_data=actual_series,
            vanity_window={"impressions": van_impr_w, "reach": van_reach_w, "clicks": van_clicks_w, "lpv": van_lpv_w, "page_eng": van_eng_w},
            total_spend_window=total_spend_window,
            meta_spend_total=meta_spend_total,
            tt_spend_total=tt_spend_total,
            has_tiktok=bool(info["tiktok_ids"]),
            zero_days=zero_days_meta,
            active_days=active_days_meta,
            trend_pct=trend_pct,
            contatti_y=contatti_y,
            spend_y=meta_spend_y + tt_spend_y,
        )

        card = {
            "id": mid,
            "name": merged_name,
            "ad_url_meta": url_meta(mid),
            "ad_url_tiktok": (url_tiktok(list(info["tiktok_ids"])[0]) if info["tiktok_ids"] else None),
            "has_tiktok": bool(info["tiktok_ids"]),
            "spend_y": round(meta_spend_y + tt_spend_y, 2),
            "spend_window": round(total_spend_window, 2),
            "spend_window_meta": round(meta_spend_total, 2),
            "spend_window_tiktok": round(tt_spend_total, 2),
            "contatti_y": contatti_y,
            "active_days": active_days_meta,
            "zero_days": zero_days_meta,
            "trend_pct": (round(trend_pct, 2) if trend_pct is not None else None),
            "trend_arrow": trend_arrow,
            "trend_label": trend_label,
            "status": st,
            "rational": rational,
            # Series giornaliera arricchita: oltre a `spend` (Meta+TikTok combinato), aggiungiamo
            # i KPI vanity per giorno (Meta-only finché TikTok non espone metriche analoghe).
            # I campi sono presenti solo se vanity_idx ha dati per quel (account_id, date),
            # altrimenti il giorno resta {date, spend} backward-compat.
            "series": [
                _build_aghc_day_entry(d, s, vanity_idx.get((mid, d)))
                for d, s in meta_series
            ],
            "window_days": window_days,
            "vanity": {
                "impressions_window": van_impr_w,
                "reach_window": van_reach_w,
                "clicks_window": van_clicks_w,
                "lpv_window": van_lpv_w,
                "page_eng_window": van_eng_w,
                "impressions_y": van_impr_y,
                "reach_y": van_reach_y,
                "clicks_y": van_clicks_y,
                "lpv_y": van_lpv_y,
                "page_eng_y": van_eng_y,
            },
            "budget": {
                "year": target_year,
                "budget_annuale": budget_annuale,
                "ytd_seed": ytd_seed if ytd_seed else None,
                "ytd_spent": ytd_spent,
                "budget_pct": round(budget_pct, 1) if budget_pct is not None else None,
            },
        }
        cards.append(card)

    # sort: rossi/gialli in cima, poi spending desc
    pri = lambda c: 0 if c["status"]["color"] == "red" else (1 if c["status"]["color"] == "yellow" else 2)
    cards.sort(key=lambda c: (pri(c), -c["spend_window"]))
    return cards

# ============================ BUILD ============================

def build(meta_rows, google_rows, tiktok_rows, medtech_rows, now_dt=None, ref_date=None, vanity_rows=None, budgets_config=None):
    now = now_dt or datetime.now()
    today = now.date()
    yesterday = ref_date if ref_date is not None else today - timedelta(days=1)
    prev7 = [(yesterday - timedelta(days=i+1)) for i in range(7)]
    prev7_iso = {iso(d) for d in prev7}
    y_iso = iso(yesterday)

    out = {
        "schema_version": 2,
        "generated_at": now.isoformat(),
        "generated_at_label": f"{date_slash(today)} {now.strftime('%H:%M')}",
        "reference_date": y_iso,
        "reference_date_label": date_label_it(yesterday),
        "pages_url": PAGES_URL,
        "errors": [],
    }

    meta_map = build_daily_map(meta_rows, is_meta_with_leads=True)
    google_map = build_daily_map(google_rows, is_meta_with_leads=False)
    tiktok_map = build_daily_map(tiktok_rows, is_meta_with_leads=False)

    # ============= OVERVIEW =============
    total_spend = 0.0
    active_accounts = set()
    all_accounts = set()
    by_platform = {"Meta": {"spend": 0.0, "accounts": set()},
                   "Google": {"spend": 0.0, "accounts": set()},
                   "TikTok": {"spend": 0.0, "accounts": set()}}

    def tally(rows, plat):
        nonlocal total_spend
        for r in rows:
            aid = str(r.get("account_id"))
            key = f"{plat}:{aid}"
            all_accounts.add(key)
            by_platform[plat]["accounts"].add(aid)
            if r.get("date") == y_iso:
                sp = float(r.get("spend") or 0)
                if sp > 0:
                    total_spend += sp
                    active_accounts.add(key)
                    by_platform[plat]["spend"] += sp

    tally(meta_rows, "Meta")
    tally(google_rows, "Google")
    tally(tiktok_rows, "TikTok")

    platforms_out = []
    for p in ["Meta", "Google", "TikTok"]:
        pct = (by_platform[p]["spend"] / total_spend * 100) if total_spend > 0 else 0
        platforms_out.append({
            "name": p,
            "accounts": len(by_platform[p]["accounts"]),
            "spend": round(by_platform[p]["spend"], 2),
            "pct": round(pct, 2),
        })

    # Project breakdown
    bf_meta_ids = {c["meta_id"] for c in BEEFAMILY if c["meta_id"]}
    bf_google_ids = {c["google_id"] for c in BEEFAMILY if c["google_id"]}
    aghc_meta_ids = {c["meta_id"] for c in AGHC if c["meta_id"]}
    aghc_tt_ids = {c["tiktok_id"] for c in AGHC if c["tiktok_id"]}

    def project_spend(rows, ids):
        s = 0
        n = set()
        for r in rows:
            if str(r.get("account_id")) not in ids:
                continue
            if r.get("date") != y_iso:
                continue
            sp = float(r.get("spend") or 0)
            s += sp
            if sp > 0:
                n.add(str(r.get("account_id")))
        return s, len(n)

    bf_meta_s, bf_meta_n = project_spend(meta_rows, bf_meta_ids)
    bf_google_s, bf_google_n = project_spend(google_rows, bf_google_ids)
    aghc_meta_s, aghc_meta_n = project_spend(meta_rows, aghc_meta_ids)
    aghc_tt_s, aghc_tt_n = project_spend(tiktok_rows, aghc_tt_ids)

    # NOTA: Med & Tech NON viene più calcolato da Windsor. La TAB Med & Tech è
    # alimentata esclusivamente dai CSV di Alfredo via _automation/build_dashboard_payload.py
    # che aggiunge anche "Med & Tech" e "CEA" a overview.projects quando popolato.

    proj_data = [
        {"name": "BeeFamily",   "spend": round(bf_meta_s + bf_google_s, 2), "accounts": bf_meta_n + bf_google_n},
        {"name": "AGHC",        "spend": round(aghc_meta_s + aghc_tt_s, 2), "accounts": aghc_meta_n + aghc_tt_n},
    ]
    tot_proj = sum(p["spend"] for p in proj_data) or 1
    for p in proj_data:
        p["pct"] = round(p["spend"] / tot_proj * 100, 2)

    out["overview"] = {
        "total_spend": round(total_spend, 2),
        "active_accounts": len(active_accounts),
        "total_accounts": len(all_accounts),
        "date_label": date_slash(yesterday),
        "platforms": platforms_out,
        "projects": proj_data,
    }

    # ============= SPENDING =============
    sp_all = (aggregate_spending(meta_rows, "Meta", y_iso, prev7_iso) +
              aggregate_spending(google_rows, "Google", y_iso, prev7_iso) +
              aggregate_spending(tiktok_rows, "TikTok", y_iso, prev7_iso))
    sp_zero, sp_high = classify_spending(sp_all)

    out["spending"] = {
        "target_day": y_iso,
        "totals": {
            "meta": sum(1 for r in sp_all if r["platform"] == "Meta"),
            "google": sum(1 for r in sp_all if r["platform"] == "Google"),
            "tiktok": sum(1 for r in sp_all if r["platform"] == "TikTok"),
            "total": len(sp_all),
        },
        "zero": [_clean_sp(r) for r in sp_zero],
        "high": [_clean_sp(r) for r in sp_high],
    }

    # ============= BEEFAMILY =============
    bf_entries = []
    for c in BEEFAMILY:
        if c["meta_id"]:
            e = meta_map.get(c["meta_id"]) or {"daily": {}, "contatti_daily": {}}
            prev_spend, _ = sum_prev_window(e["daily"], y_iso, 7)
            prev_contatti, _ = sum_prev_window(e["contatti_daily"], y_iso, 7)
            bf_entries.append({
                "name": c["name"], "source": "Meta",
                "spend_y": round(e["daily"].get(y_iso, 0), 2),
                "contatti_y": int(e["contatti_daily"].get(y_iso, 0)),
                "prev7_spend": prev_spend,
                "prev7_contatti": prev_contatti,
                "ad_url": url_meta(c["meta_id"]),
            })
        if c["google_id"]:
            e = google_map.get(c["google_id"]) or {"daily": {}, "contatti_daily": {}}
            prev_spend, _ = sum_prev_window(e["daily"], y_iso, 7)
            bf_entries.append({
                "name": c["name"], "source": "Google",
                "spend_y": round(e["daily"].get(y_iso, 0), 2),
                "contatti_y": 0,
                "prev7_spend": prev_spend,
                "prev7_contatti": 0,
                "ad_url": url_google(c["google_id"]),
            })
    bf_kpi = compute_project(bf_entries, project_type="hotel")
    # sort: rossi/gialli prima, poi spending desc
    pri = lambda e: 0 if e["status"]["color"] == "red" else (1 if e["status"]["color"] == "yellow" else (2 if e["status"]["color"] == "gray" else 3))
    bf_entries.sort(key=lambda e: (pri(e), -e["spend_y"]))
    for e in bf_entries:
        e["prev7_spend"] = round(e["prev7_spend"], 2)
        e["prev7_contatti"] = int(e["prev7_contatti"])

    # ---------- BeeFamily CARDS per cliente (raggruppa Meta + Google) ----------
    bf_window_days = 15
    # Breakdown campagne attive (popolato solo se raw Meta/Google hanno il campo `campaign`)
    bf_meta_camps_by_aid   = build_campaign_breakdown(meta_rows,   is_meta_with_leads=True,  only_active=True)
    bf_google_camps_by_aid = build_campaign_breakdown(google_rows, is_meta_with_leads=False, only_active=True)
    bf_cards = []
    for c in BEEFAMILY:
        meta_id = c.get("meta_id")
        google_id = c.get("google_id")
        meta_e = meta_map.get(meta_id) if meta_id else None
        google_e = google_map.get(google_id) if google_id else None
        if not meta_e and not google_e:
            continue

        meta_daily   = (meta_e or {}).get("daily", {})
        google_daily = (google_e or {}).get("daily", {})

        meta_series   = daily_series(meta_daily, y_iso, bf_window_days)
        google_series = daily_series(google_daily, y_iso, bf_window_days)
        spend_window  = sum(s for _, s in meta_series) + sum(s for _, s in google_series)
        spend_y       = (meta_daily.get(y_iso, 0) or 0) + (google_daily.get(y_iso, 0) or 0)

        # Trend confrontando media prima vs seconda metà del periodo (sommando Meta+Google giorno per giorno)
        merged_series = []
        dates_iso = [d for d, _ in meta_series] if meta_series else [d for d, _ in google_series]
        m_map = {d: s for d, s in meta_series}
        g_map = {d: s for d, s in google_series}
        for d in dates_iso:
            merged_series.append((d, m_map.get(d, 0) + g_map.get(d, 0)))
        mid_idx = len(merged_series) // 2
        first_half = [s for _, s in merged_series[:mid_idx]]
        second_half = [s for _, s in merged_series[mid_idx:]]
        first_mean = sum(first_half) / len(first_half) if first_half else 0
        second_mean = sum(second_half) / len(second_half) if second_half else 0
        if first_mean > 0:
            trend_pct = ((second_mean / first_mean) - 1) * 100
            if trend_pct > 10: trend_arrow, trend_label = "↑", "in crescita"
            elif trend_pct < -10: trend_arrow, trend_label = "↓", "in calo"
            else: trend_arrow, trend_label = "→", "stabile"
        else:
            trend_pct, trend_arrow, trend_label = None, "—", "n/d"

        # Status della card = peggiore status tra le entries Meta+Google di questo cliente
        related = [e for e in bf_entries if e["name"] == c["name"]]
        pri_color = {"red": 0, "yellow": 1, "gray": 2, "green": 3}
        if related:
            worst = sorted(related, key=lambda e: pri_color.get(e["status"]["color"], 4))[0]
            card_status = worst["status"]
        else:
            card_status = {"color": "gray", "label": "Inattivo", "reason": "Nessun dato"}

        # Contatti window/yesterday (solo Meta — Google su BeeFamily ha contatti_y=0 di default)
        meta_contatti_daily = (meta_e or {}).get("contatti_daily", {})
        google_contatti_daily = (google_e or {}).get("contatti_daily", {})
        meta_contatti_window = sum(
            int(meta_contatti_daily.get(d, 0))
            for d, _ in (meta_series if meta_series else [])
        )
        google_contatti_window = sum(
            int(google_contatti_daily.get(d, 0))
            for d, _ in (google_series if google_series else [])
        )
        contatti_window = meta_contatti_window + google_contatti_window
        contatti_y = int(meta_contatti_daily.get(y_iso, 0)) + int(google_contatti_daily.get(y_iso, 0))

        # zero_days / active_days sulla merged series (giorni con almeno un valore in qualsiasi map)
        days_with_data = sum(1 for d, _ in merged_series if (d in (meta_e or {}).get("daily", {}) or d in (google_e or {}).get("daily", {})))
        zero_days = sum(1 for d, s in merged_series if (d in (meta_e or {}).get("daily", {}) or d in (google_e or {}).get("daily", {})) and s == 0)
        active_days = sum(1 for d, s in merged_series if (d in (meta_e or {}).get("daily", {}) or d in (google_e or {}).get("daily", {})) and s > 0)

        rational_html = _build_beefamily_rational(
            client_name=c["name"],
            window_days=bf_window_days,
            total_spend_window=spend_window,
            meta_spend_total=sum(s for _, s in meta_series),
            google_spend_total=sum(s for _, s in google_series),
            has_google=(google_id is not None),
            zero_days=zero_days,
            active_days=active_days,
            trend_pct=trend_pct,
            contatti_window=contatti_window,
            contatti_y=contatti_y,
            spend_y=spend_y,
            daily_series_data=merged_series,
            meta_contatti_window=meta_contatti_window,
            google_contatti_window=google_contatti_window,
            meta_campaigns=bf_meta_camps_by_aid.get(meta_id, [])      if meta_id   else [],
            google_campaigns=bf_google_camps_by_aid.get(google_id, []) if google_id else [],
        )

        # Campagne attive per questo cliente (vuoto se raw senza campo `campaign`)
        meta_campaigns   = bf_meta_camps_by_aid.get(meta_id, [])     if meta_id   else []
        google_campaigns = bf_google_camps_by_aid.get(google_id, []) if google_id else []

        # CPL window (BF lavora a Contatti+CPL, non a vanity metrics)
        cpl_window = (spend_window / contatti_window) if contatti_window > 0 else None

        bf_cards.append({
            "id": c["name"].lower().replace(" ", "-").replace("&", "and"),
            "name": c["name"],
            "spend_window": round(spend_window, 2),
            "spend_y": round(spend_y, 2),
            "contatti_window": contatti_window,
            "contatti_y": contatti_y,
            "cpl_window": round(cpl_window, 2) if cpl_window is not None else None,
            "window_days": bf_window_days,
            "trend_arrow": trend_arrow,
            "trend_label": trend_label,
            "trend_pct": round(trend_pct, 1) if trend_pct is not None else None,
            "status": card_status,
            "rational": rational_html,
            "ad_url_meta":   url_meta(meta_id)     if meta_id   else None,
            "ad_url_google": url_google(google_id) if google_id else None,
            "meta_campaigns":   meta_campaigns,    # lista campagne Meta attive sulla window 15gg
            "google_campaigns": google_campaigns,  # lista campagne Google attive sulla window 15gg
        })

    # Sort card: rossi/gialli prima, poi spend_window desc
    pri_card = lambda c: {"red": 0, "yellow": 1, "gray": 2, "green": 3}.get(c["status"]["color"], 4)
    bf_cards.sort(key=lambda c: (pri_card(c), -c["spend_window"]))

    out["beefamily"] = {
        "kpi": {
            "actives": bf_kpi["actives"],
            "total": bf_kpi["total"],
            "total_spend": round(bf_kpi["total_spend"], 2),
            "total_contatti": bf_kpi["total_contatti"],
            "cpc_y": round(bf_kpi["cpc_y"], 2) if bf_kpi["cpc_y"] is not None else None,
            "cpc_mean": round(bf_kpi["cpc_mean"], 2) if bf_kpi["cpc_mean"] is not None else None,
        },
        "entries": bf_entries,
        "cards": bf_cards,
        "recap": recap_beefamily_slack(bf_kpi, bf_entries, yesterday),
    }

    # ============= AGHC =============
    aghc_cards = build_aghc_cards(meta_rows, tiktok_rows, y_iso, yesterday, window_days=15, vanity_rows=vanity_rows, budgets_config=budgets_config)
    aghc_tot_spend_y = sum(c["spend_y"] for c in aghc_cards)
    aghc_actives = sum(1 for c in aghc_cards if c["spend_y"] > 0)
    out["aghc"] = {
        "kpi": {
            "actives": aghc_actives,
            "total": len(aghc_cards),
            "total_spend_y": round(aghc_tot_spend_y, 2),
            "total_spend_window": round(sum(c["spend_window"] for c in aghc_cards), 2),
            "window_days": 15,
        },
        "cards": aghc_cards,
        "recap": recap_aghc_slack(aghc_cards, yesterday),
    }

    # NOTA: data["medtech"] e data["cea"] vengono popolati ESCLUSIVAMENTE dal
    # connettore _automation/build_dashboard_payload.py (CSV di Alfredo).
    # build_data.py non legge più raw/medtech.json. Tuttavia, se esistono già
    # nel data.json precedente, li PRESERVA (importante per evitare di
    # cancellarli accidentalmente quando si rilancia build_data.py).

    # ============= OTHER ROSTER (assorbe fmm-discover-other-accounts) =============
    # Account Meta visibili nel dataset Windsor che NON appartengono a BF/AGHC/medtech/CEA.
    exclude_other = set(bf_meta_ids) | set(aghc_meta_ids) | {MEDTECH_META_ACCOUNT} | set(CEA_META_IDS) | set(EXCLUDED_SPENDING)
    out["other_roster"] = _build_other_roster(
        meta_rows=meta_rows,
        meta_map=meta_map,
        exclude_ids=exclude_other,
        y_iso=y_iso,
        window_days=15,
    )

    return out


def _build_other_roster(meta_rows, meta_map, exclude_ids, y_iso, window_days=15):
    """Lista account Meta visibili in Windsor (meta_rows) che NON sono in
    BeeFamily / AGHC / Med&Tech / CEA / EXCLUDED. Per ciascuno calcola lo
    spend_window_15d (somma su `window_days` precedenti a y_iso incluso) e
    spend_y (spend di reference_date).

    Output:
      {
        "generated_at": "<iso>",
        "window_days": 15,
        "reference_date": "<y_iso>",
        "accounts": [
            {"account_id","account_name","spend_y","spend_window_15d","ad_url"}, ...
        ]
      }
    """
    exclude_set = {str(x) for x in (exclude_ids or set())}
    # Account_id distinti presenti nei rows meta
    seen = []
    seen_set = set()
    for r in meta_rows:
        aid = str(r.get("account_id") or "")
        if not aid or aid in seen_set or aid in exclude_set:
            continue
        seen.append(aid)
        seen_set.add(aid)
    accounts = []
    for aid in seen:
        e = meta_map.get(aid) or {"name": aid, "daily": {}}
        daily = e.get("daily", {})
        spend_y = float(daily.get(y_iso, 0) or 0)
        series = daily_series(daily, y_iso, window_days)
        spend_window = sum(s for _, s in series)
        accounts.append({
            "account_id": aid,
            "account_name": e.get("name") or aid,
            "spend_y": round(spend_y, 2),
            "spend_window_15d": round(spend_window, 2),
            "ad_url": url_meta(aid),
        })
    # Sort: prima spend_window desc, fallback nome
    accounts.sort(key=lambda a: (-a["spend_window_15d"], (a["account_name"] or "").lower()))
    return {
        "reference_date": y_iso,
        "window_days": window_days,
        "accounts": accounts,
        "total_count": len(accounts),
        "total_spend_window": round(sum(a["spend_window_15d"] for a in accounts), 2),
    }


def preserve_csv_sections(out, workspace):
    """Re-inietta in `out` le sezioni `cea`, `medtech` e overview.projects(CEA/Med&Tech)
    scritte da dashboard-csv-update / build_dashboard_payload.py, scegliendo la
    fonte FRESCA per la `reference_date` corrente.

    Sorgenti, in ordine di affidabilità decrescente:
      1. snapshots/<reference_date>.json  → scritto SOLO dallo script di sync,
         autoritativo per quel giorno specifico.
      2. data.json                        → fallback, ma considerato valido solo
         se _meta.reference_date (o reference_date top-level) coincide con
         l'output corrente.

    Una sezione cea/medtech viene presa solo se "fresca" (= il marker
    `_meta.reference_date` coincide con `out["reference_date"]`). Se nessuna
    fonte è fresca, la sezione resta vuota — meglio vuoto che valori del giorno
    sbagliato (regression osservata il 20/05/2026: rebuild Windsor + stash pop
    in daily-push.sh sovrascrivevano cea/medtech con dati del giorno precedente).
    """
    import os as _os
    ref_date = out.get("reference_date")

    # Costruisci candidati in ordine di priorità
    candidates = []
    if ref_date:
        snap_path = _os.path.join(workspace, "snapshots", f"{ref_date}.json")
        if _os.path.exists(snap_path):
            candidates.append(("snapshots/" + ref_date + ".json", snap_path))
    data_json = _os.path.join(workspace, "data.json")
    if _os.path.exists(data_json):
        candidates.append(("data.json", data_json))

    def _is_fresh(section, expected_ref, container_ref):
        """Una sezione cea/medtech è fresca se il suo `_meta.reference_date`
        coincide con `expected_ref`. Per backward-compat (file pre-fix che
        non hanno _meta), accetta anche match sul `reference_date` top-level
        del container."""
        if not isinstance(section, dict) or not expected_ref:
            return False
        meta_ref = (section.get("_meta") or {}).get("reference_date")
        if meta_ref == expected_ref:
            return True
        # Backward-compat fallback: nessun _meta, ma il container ha
        # reference_date corretto e la sezione ha entries → trustabile.
        if meta_ref is None and container_ref == expected_ref:
            return True
        return False

    cea_taken = False
    medtech_taken = False
    overview_src = None

    for label, path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                prev = json.load(f)
        except Exception:
            continue
        prev_ref = prev.get("reference_date")
        if not cea_taken:
            cea_sec = prev.get("cea") or {}
            if cea_sec.get("entries") and _is_fresh(cea_sec, ref_date, prev_ref):
                out["cea"] = cea_sec
                cea_taken = True
        if not medtech_taken:
            mt_sec = prev.get("medtech") or {}
            if mt_sec.get("entries") and _is_fresh(mt_sec, ref_date, prev_ref):
                out["medtech"] = mt_sec
                medtech_taken = True
        if overview_src is None and prev.get("overview", {}).get("projects") and prev_ref == ref_date:
            overview_src = prev
        if cea_taken and medtech_taken and overview_src is not None:
            break

    # Aggiungi Med & Tech + CEA in overview.projects (dal source più affidabile)
    if overview_src is not None and "overview" in out and "projects" in out["overview"]:
        prev_projects = overview_src.get("overview", {}).get("projects", [])
        existing_names = {p["name"] for p in out["overview"]["projects"]}
        for p in prev_projects:
            if p.get("name") in ("Med & Tech", "CEA") and p["name"] not in existing_names:
                out["overview"]["projects"].append(p)
        tot = sum(p.get("spend", 0) for p in out["overview"]["projects"]) or 1
        for p in out["overview"]["projects"]:
            p["pct"] = round((p.get("spend", 0) or 0) / tot * 100, 2)
    return out

def _clean_sp(r):
    return {
        "platform": r["platform"],
        "account_id": r["account_id"],
        "account_name": r["account_name"],
        "target": round(r["target"], 2),
        "mean7": round(r["mean7"], 2),
        "delta": (round(r["delta"], 2) if r["delta"] is not None else None),
        "triggers": r.get("triggers", []),
        "ad_url": r.get("ad_url"),
    }

def _medtech_status(spend_y, lead_y, cpl_mean_3d):
    """
    Med & Tech: campagne brevi (≈14 giorni) → ottimizzazione giornaliera, soglia media 3gg.
    - NERO: spend ieri == 0 (campagna ferma)
    - ROSSO: 0 lead pur con spending OPPURE CPL ieri > 1.5x media 3gg
    - GIALLO: CPL ieri tra 1.0x e 1.5x media 3gg
    - VERDE: CPL ieri ≤ media 3gg
    """
    if spend_y == 0:
        return {"color": "black", "label": "NERO",
                "reason": "Nessuna spesa ieri sulla campagna"}
    if lead_y == 0:
        return {"color": "red", "label": "ROSSO",
                "reason": f"Spesi {fmt_eur(spend_y)} ieri senza generare lead via modulo Lead Ad"}
    cpl_y = spend_y / lead_y
    if cpl_mean_3d is None or cpl_mean_3d == 0:
        return {"color": "green", "label": "VERDE",
                "reason": f"Spesi {fmt_eur(spend_y)} con {lead_y} lead (CPL {fmt_eur(cpl_y)})"}
    ratio = cpl_y / cpl_mean_3d
    delta_pct = (ratio - 1) * 100
    if ratio > 1.5:
        return {"color": "red", "label": "ROSSO",
                "reason": f"CPL ieri {fmt_eur(cpl_y)} contro media 3gg {fmt_eur(cpl_mean_3d)} ({fmt_pct(delta_pct)}, oltre la soglia +50%)"}
    if ratio > 1.0:
        return {"color": "yellow", "label": "GIALLO",
                "reason": f"CPL ieri {fmt_eur(cpl_y)} contro media 3gg {fmt_eur(cpl_mean_3d)} ({fmt_pct(delta_pct)}, lieve crescita)"}
    return {"color": "green", "label": "VERDE",
            "reason": f"CPL ieri {fmt_eur(cpl_y)} contro media 3gg {fmt_eur(cpl_mean_3d)} ({fmt_pct(delta_pct)}, in linea o sotto)"}


def _build_medtech(rows, y_iso, yesterday):
    """
    Tab Med & Tech allineata alla scheduled task med-tech-daily-total-lift-sculpt:
    - Solo moduli Lead Ad (Instant Forms) — niente landing page
    - Stati semaforici NERO/ROSSO/GIALLO/VERDE
    - Trend 3gg di CPL
    """
    camp_map = {}
    for r in rows:
        camp = r.get("campaign")
        if not camp or not MEDTECH_FILTER.search(camp):
            continue
        if camp not in camp_map:
            camp_map[camp] = {"daily": {}, "lead_daily": {}, "status": r.get("campaign_effective_status")}
        e = camp_map[camp]
        d = r.get("date")
        e["daily"][d] = e["daily"].get(d, 0) + float(r.get("spend") or 0)
        # Med & Tech usa SOLO Instant Forms → actions_onsite_conversion_lead_grouped è il dato canonico
        ld = int(r.get("actions_onsite_conversion_lead_grouped") or r.get("actions_lead") or 0)
        if ld:
            e["lead_daily"][d] = e["lead_daily"].get(d, 0) + ld
        if r.get("campaign_effective_status"):
            e["status"] = r["campaign_effective_status"]

    # Helper: media CPL ultimi 7gg per una campagna (esclude eventuali giorni a 0 lead)
    def cpl_mean_3d(daily, lead_daily, ref_iso):
        ref = parse_iso(ref_iso)
        cpls = []
        for i in range(1, 4):
            d = iso(ref - timedelta(days=i))
            s = daily.get(d, 0)
            l = lead_daily.get(d, 0)
            if l > 0 and s > 0:
                cpls.append(s / l)
        return sum(cpls) / len(cpls) if cpls else None

    # Helper: trend 3gg ultimi (CPL giornaliero degli ultimi 3 giorni esclusi vuoti)
    def cpl_trend_3d(daily, lead_daily, ref_iso):
        ref = parse_iso(ref_iso)
        series = []
        for i in range(2, -1, -1):
            d = iso(ref - timedelta(days=i))
            s = daily.get(d, 0)
            l = lead_daily.get(d, 0)
            cpl = (s / l) if l > 0 else None
            series.append({"date": d, "cpl": (round(cpl, 2) if cpl is not None else None)})
        return series

    entries = []
    for k, e in camp_map.items():
        spend_y = round(e["daily"].get(y_iso, 0), 2)
        lead_y = int(e["lead_daily"].get(y_iso, 0))
        cpl_y = (spend_y / lead_y) if lead_y > 0 else None
        cpl_mean = cpl_mean_3d(e["daily"], e["lead_daily"], y_iso)
        status = _medtech_status(spend_y, lead_y, cpl_mean)
        trend = cpl_trend_3d(e["daily"], e["lead_daily"], y_iso)
        prev7_spend, _ = sum_prev_window(e["daily"], y_iso, 7)
        prev7_lead, _ = sum_prev_window(e["lead_daily"], y_iso, 7)
        entries.append({
            "name": k,
            "source": e.get("status") or "",
            "spend_y": spend_y,
            "lead_y": lead_y,
            "contatti_y": lead_y,  # alias backward-compat con UI esistente
            "cpl_y": round(cpl_y, 2) if cpl_y is not None else None,
            "cpl_mean_3d": round(cpl_mean, 2) if cpl_mean is not None else None,
            "trend_3d": trend,
            "prev7_spend": round(prev7_spend, 2),
            "prev7_lead": int(prev7_lead),
            "prev7_contatti": int(prev7_lead),
            "status": status,
            "ad_url": url_meta(MEDTECH_META_ACCOUNT),
        })

    # Sort: ROSSO -> GIALLO -> VERDE -> NERO, entro stesso colore spend desc
    pri = lambda e: {"red": 0, "yellow": 1, "green": 2, "black": 3}.get(e["status"]["color"], 4)
    entries.sort(key=lambda e: (pri(e), -e["spend_y"]))

    # KPI aggregati: campagne attive (status != NERO) + totali del giorno
    actives = sum(1 for e in entries if e["status"]["color"] != "black")
    n_rosso = sum(1 for e in entries if e["status"]["color"] == "red")
    n_giallo = sum(1 for e in entries if e["status"]["color"] == "yellow")
    n_verde = sum(1 for e in entries if e["status"]["color"] == "green")
    n_nero = sum(1 for e in entries if e["status"]["color"] == "black")
    tot_spend = round(sum(e["spend_y"] for e in entries), 2)
    tot_lead = sum(e["lead_y"] for e in entries)
    cpl_agg = round(tot_spend / tot_lead, 2) if tot_lead > 0 else None

    return {
        "kpi": {
            "actives": actives,
            "total": len(entries),
            "total_spend": tot_spend,
            "total_contatti": tot_lead,
            "total_lead": tot_lead,
            "cpc_y": cpl_agg,
            "cpl_y": cpl_agg,
            "rosso": n_rosso,
            "giallo": n_giallo,
            "verde": n_verde,
            "nero": n_nero,
        },
        "entries": entries,
        "recap": recap_medtech_slack({"actives": actives, "total": len(entries),
                                       "total_spend": tot_spend, "total_contatti": tot_lead,
                                       "cpc_y": cpl_agg, "cpc_mean": None}, entries, yesterday),
    }

# ============================ MAIN ============================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", required=True)
    ap.add_argument("--google", required=True)
    ap.add_argument("--tiktok", required=True)
    ap.add_argument("--medtech", default=None, help="OPZIONALE: dal 2026-05-19 Med & Tech non passa più da Windsor, è popolato dal connettore CSV di Alfredo")
    ap.add_argument("--workspace", required=True, help="Path workspace (Dashboard di Controllo)")
    ap.add_argument("--aghc-vanity", default=None, help="Path opzionale a JSON con vanity metrics (impressions/clicks/landing_page_view) per AGHC")
    ap.add_argument("--aghc-budgets", default=None, help="Path opzionale a aghc_budgets.json con budget_annuale + ytd_seed per ogni meta_id")
    ap.add_argument("--owners", default=None, help="Path opzionale a owners.json (mapping meta_id → slack_user_id del referente) per popolare slack_target sulle azioni bf_fermo. Se assente, fallback DM Francesco.")
    ap.add_argument("--retention-days", type=int, default=90, help="Quanti snapshot/<date>.json tenere; più vecchi vengono cancellati")
    ap.add_argument("--ref-date", default=None, help="Override reference date (YYYY-MM-DD); default = ieri")
    args = ap.parse_args()

    def load(path):
        if not path or not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            j = json.load(f)
        return j.get("result", j) if isinstance(j, dict) else j

    meta = load(args.meta)
    google = load(args.google)
    tiktok = load(args.tiktok)
    medtech = load(args.medtech)  # Tollerato vuoto: Med & Tech ora viene da CSV di Alfredo

    ref_date = parse_iso(args.ref_date) if args.ref_date else None
    vanity_rows = load(args.aghc_vanity) if args.aghc_vanity and os.path.exists(args.aghc_vanity) else None
    budgets_config = None
    if args.aghc_budgets and os.path.exists(args.aghc_budgets):
        with open(args.aghc_budgets, "r", encoding="utf-8") as f:
            budgets_config = json.load(f)
    owners_map = {}
    if args.owners and os.path.exists(args.owners):
        try:
            with open(args.owners, "r", encoding="utf-8") as f:
                owners_raw = json.load(f)
            # owners.json formato atteso: {"meta_id_to_slack_user": {"<meta_id>": "<U...>"}}
            # oppure root-level {"<meta_id>": "<U...>"}; supporta entrambi.
            if isinstance(owners_raw, dict):
                owners_map = owners_raw.get("meta_id_to_slack_user") or owners_raw
        except Exception as _e:
            owners_map = {}
    data = build(meta, google, tiktok, medtech, ref_date=ref_date, vanity_rows=vanity_rows, budgets_config=budgets_config)

    workspace = args.workspace
    snap_dir = os.path.join(workspace, "snapshots")
    os.makedirs(snap_dir, exist_ok=True)

    # Preserve cea/medtech eventualmente popolati da dashboard-csv-update
    # (build_data.py non li costruisce, ma non deve nemmeno cancellarli)
    data = preserve_csv_sections(data, workspace)

    # Write latest
    latest_path = os.path.join(workspace, "data.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Write snapshot for reference_date
    snap_path = os.path.join(snap_dir, data["reference_date"] + ".json")
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Retention: remove snapshots older than retention-days
    today = datetime.now().date()
    cutoff = today - timedelta(days=args.retention_days)
    removed = 0
    for fn in os.listdir(snap_dir):
        if not fn.endswith(".json"):
            continue
        try:
            d = parse_iso(fn[:-5])
        except Exception:
            continue
        if d < cutoff:
            os.remove(os.path.join(snap_dir, fn))
            removed += 1

    # Build/update snapshots index (lista date disponibili, decrescente)
    available_dates = sorted([fn[:-5] for fn in os.listdir(snap_dir) if fn.endswith(".json") and re.match(r"\d{4}-\d{2}-\d{2}\.json", fn)], reverse=True)
    index_path = os.path.join(snap_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"dates": available_dates}, f, ensure_ascii=False, indent=2)

    # ============= ACTIONS.JSON per Calendar + Slack =============
    # Trigger:
    # - HIGH spending: account con BOTH triggers (>50€ + >30% vs media 7gg) — più critico
    # - NEW fermo: account in spending.zero oggi che NON era in spending.zero ieri (diff snapshot)
    # - SPENDING_ANOMALY: ogni zero + high per loop Slack #anomalie-spending (assorbe alert-spending-anomalie-windsor)
    # - BF_FERMO: account BeeFamily a spend_y=0 con prev7_spend>0, DM al referente cliente (assorbe daily-check-beefamily)
    actions = []
    ref_date_iso = data["reference_date"]
    ref_date_label = data["reference_date_label"]

    # Cerca lo snapshot del giorno PRECEDENTE (ieri rispetto a reference_date)
    prev_date = (parse_iso(ref_date_iso) - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_snap_path = os.path.join(snap_dir, prev_date + ".json")
    prev_zero_ids = set()
    prev_bf_fermo_ids = set()
    prev_snapshot_exists = os.path.exists(prev_snap_path)
    if prev_snapshot_exists:
        try:
            with open(prev_snap_path, "r", encoding="utf-8") as f:
                prev_data = json.load(f)
            prev_zero_ids = {f"{r['platform']}:{r['account_id']}" for r in prev_data.get("spending", {}).get("zero", [])}
            for e in prev_data.get("beefamily", {}).get("entries", []):
                if (e.get("spend_y") or 0) == 0 and (e.get("prev7_spend") or 0) > 0:
                    prev_bf_fermo_ids.add(f"{e.get('source')}:{e.get('name')}")
        except Exception:
            prev_snapshot_exists = False

    # 1) HIGH spending critici (entrambi trigger) — solo Calendar
    for r in data["spending"]["high"]:
        triggers = r.get("triggers", [])
        if ">50€" in triggers and ">30%" in triggers:
            actions.append({
                "type": "high_spending",
                "priority": "high",
                "title": f"🔴 {r['account_name']} · spesa anomala alta",
                "platform": r["platform"],
                "account_id": r["account_id"],
                "ad_url": r["ad_url"],
                "details": f"Spesa {fmt_eur(r['target'])} ieri vs media 7gg {fmt_eur(r['mean7'])} ({fmt_pct(r['delta'])})",
                "reference_date": ref_date_iso,
                "reference_date_label": ref_date_label,
            })

    # 2) NEW fermi (in zero oggi, non c'erano ieri) — Calendar
    if prev_snapshot_exists:
        new_fermi = []
        for r in data["spending"]["zero"]:
            key = f"{r['platform']}:{r['account_id']}"
            if key not in prev_zero_ids:
                new_fermi.append({
                    "type": "new_fermo",
                    "priority": "high",
                    "title": f"⚫ {r['account_name']} · nuovo account fermo",
                    "platform": r["platform"],
                    "account_id": r["account_id"],
                    "ad_url": r["ad_url"],
                    "details": f"Spending 0 ieri, media 7gg precedente {fmt_eur(r['mean7'])}. Da verificare.",
                    "reference_date": ref_date_iso,
                    "reference_date_label": ref_date_label,
                })
        new_fermi.sort(key=lambda a: -float(a['details'].split('precedente ')[1].split(' €')[0].replace('.','').replace(',','.')) if 'precedente' in a['details'] else 0)
        actions.extend(new_fermi[:10])  # max 10 new_fermi al giorno

    # ===== Cap Calendar a 15 (high_spending + new_fermo) =====
    cal_actions = [a for a in actions if a["type"] in ("high_spending", "new_fermo")]
    cal_actions = cal_actions[:15]
    actions = cal_actions  # ripartiamo con le sole calendar capped

    # 3) SPENDING_ANOMALY → Slack #anomalie-spending (assorbe alert-spending-anomalie-windsor)
    # Top alert già pre-formattato per il loop slack della SKILL refresh-dashboard-data.
    spending_zero = data["spending"]["zero"]
    spending_high = data["spending"]["high"]
    spending_total = len(spending_zero) + len(spending_high)
    if spending_total > 0:
        # Top 3: prima zero, poi high (per spend desc)
        top3_lines = []
        for r in sorted(spending_zero, key=lambda x: -x.get("mean7", 0))[:3]:
            top3_lines.append(f"• :zap: {r['account_name']} ({r['platform']}) — 0,00 € (storico {fmt_eur(r['mean7'])}) · _Causa da verificare_")
        remaining = 3 - len(top3_lines)
        if remaining > 0:
            for r in sorted(spending_high, key=lambda x: -x.get("target", 0))[:remaining]:
                delta = r.get("delta")
                delta_str = (fmt_pct(delta) if delta is not None else "n/d")
                top3_lines.append(f"• :fire: {r['account_name']} ({r['platform']}) — {fmt_eur(r['target'])} ({delta_str})")
        more = spending_total - len(top3_lines)
        more_line = f"\n_+ {more} altri alert sulla dashboard_" if more > 0 else ""
        date_slash_str = date_slash(parse_iso(ref_date_iso))
        slack_text = (
            f":rotating_light: *Check spending — {date_slash_str}*\n"
            f"*Top alert:*\n"
            + "\n".join(top3_lines)
            + more_line
            + f"\n\n<{PAGES_URL}?section=spending&date={ref_date_iso}|:link: Apri dashboard →>"
        )
        actions.append({
            "type": "spending_anomaly",
            "priority": "high",
            "title": f"Alert spending — {date_slash_str}",
            "details": f"{len(spending_zero)} zero + {len(spending_high)} high",
            "reference_date": ref_date_iso,
            "reference_date_label": ref_date_label,
            "slack_target": SLACK_CHANNEL_ANOMALIE_SPENDING,
            "slack_template": slack_text,
            "skip_if_quiet": False,
        })

    # 4) BF_FERMO → Slack DM al referente cliente (assorbe daily-check-beefamily)
    # Logica: account BeeFamily con spend_y=0 e prev7_spend>0 → DM al referente del cliente.
    # Distinguiamo "nuovo" (non era fermo ieri) vs "persistente" (era già fermo).
    bf_fermi_actions = []
    for e in data.get("beefamily", {}).get("entries", []):
        spend_y = e.get("spend_y") or 0
        prev7 = e.get("prev7_spend") or 0
        if spend_y == 0 and prev7 > 0:
            key = f"{e.get('source')}:{e.get('name')}"
            is_new = key not in prev_bf_fermo_ids
            # Risolvi slack_target: cerca per meta_id (se source=Meta) o google_id (se source=Google) in owners_map.
            # owners_map può essere keyed per meta_id OPPURE per name del cliente. Proviamo entrambe.
            slack_target = None
            # Trova meta_id/google_id dal roster BEEFAMILY
            roster_entry = next((c for c in BEEFAMILY if c["name"] == e.get("name")), None)
            if roster_entry:
                if e.get("source") == "Meta" and roster_entry.get("meta_id"):
                    slack_target = owners_map.get(str(roster_entry["meta_id"]))
                elif e.get("source") == "Google" and roster_entry.get("google_id"):
                    slack_target = owners_map.get(str(roster_entry["google_id"]))
            if not slack_target:
                slack_target = owners_map.get(e.get("name", ""))
            if not slack_target:
                slack_target = SLACK_DM_FRANCESCO  # fallback DM Francesco
            label = "nuovo fermo" if is_new else "fermo persistente"
            emoji = "⚫" if is_new else "⚠️"
            slack_text = (
                f"{emoji} *Bee Family — {e.get('name')} ({e.get('source')})*: {label}\n"
                f"Spending ieri: 0,00 € · Media 7gg precedente: {fmt_eur(prev7)}\n"
                f"<{e.get('ad_url', '')}|Apri account →>"
            )
            bf_fermi_actions.append({
                "type": "bf_fermo",
                "priority": "high" if is_new else "medium",
                "title": f"{emoji} Bee Family {e.get('name')} — {label}",
                "source": e.get("source"),
                "client_name": e.get("name"),
                "ad_url": e.get("ad_url"),
                "details": f"spend_y=0, prev7={fmt_eur(prev7)}",
                "reference_date": ref_date_iso,
                "reference_date_label": ref_date_label,
                "slack_target": slack_target,
                "slack_template": slack_text,
                "skip_if_quiet": (not is_new),  # se persistente → solo notifica se severity high
                "severity": "high" if is_new else "medium",
            })
    # priorità: nuovi prima
    bf_fermi_actions.sort(key=lambda a: 0 if a["priority"] == "high" else 1)
    actions.extend(bf_fermi_actions)

    actions_path = os.path.join(workspace, "actions.json")
    with open(actions_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": data["generated_at"],
            "reference_date": ref_date_iso,
            "actions": actions,
        }, f, ensure_ascii=False, indent=2)
    n_high = sum(1 for a in actions if a['type']=='high_spending')
    n_newf = sum(1 for a in actions if a['type']=='new_fermo')
    n_spa  = sum(1 for a in actions if a['type']=='spending_anomaly')
    n_bff  = sum(1 for a in actions if a['type']=='bf_fermo')
    print(f"✓ actions.json: {len(actions)} azioni (high={n_high}, new_fermo={n_newf}, spending_anomaly={n_spa}, bf_fermo={n_bff})")

    print(f"✓ data.json:   {latest_path} ({os.path.getsize(latest_path)} bytes)")
    print(f"✓ snapshot:    {snap_path}")
    print(f"✓ index.json:  {len(available_dates)} date disponibili")
    if removed:
        print(f"  (retention: rimossi {removed} snapshot vecchi oltre {args.retention_days}gg)")
    print(f"  overview total_spend = {data['overview']['total_spend']} €")
    print(f"  overview active_accounts = {data['overview']['active_accounts']}/{data['overview']['total_accounts']}")
    print(f"  spending zero = {len(data['spending']['zero'])}, high = {len(data['spending']['high'])}")
    bf_alerts = sum(1 for e in data['beefamily']['entries'] if e['status']['color'] in ('red','yellow'))
    print(f"  beefamily entries = {len(data['beefamily']['entries'])}, alerts = {bf_alerts}")
    aghc_alerts = sum(1 for c in data['aghc']['cards'] if c['status']['color'] in ('red','yellow'))
    print(f"  aghc cards = {len(data['aghc']['cards'])}, alerts = {aghc_alerts}")
    if 'medtech' in data:
        mt_alerts = sum(1 for e in data['medtech']['entries'] if e['status']['color'] in ('red','yellow'))
        print(f"  medtech entries = {len(data['medtech']['entries'])}, alerts = {mt_alerts}")
    else:
        print(f"  medtech: alimentato da CSV di Alfredo (build_data.py non lo gestisce più)")
    if 'other_roster' in data:
        otr = data['other_roster']
        print(f"  other_roster = {otr.get('total_count', 0)} account · spend_window_15d totale {otr.get('total_spend_window', 0)} €")

if __name__ == "__main__":
    main()
