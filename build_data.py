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
    {"name": "VILLA GIADA",     "meta_id": "1849759899186169",  "tiktok_id": None},
    {"name": "VILLA MILIANI",   "meta_id": "1353024533007038",  "tiktok_id": None},
]

MEDTECH_META_ACCOUNT = "533672775128363"
MEDTECH_FILTER = re.compile(r"Total Lift|Total Sculpt", re.IGNORECASE)

EXCLUDED_SPENDING = {"1576344015714351", "533672775128363"}

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
    """Recap copia-incolla stile 'Ciao team' con KPI di gasazione (vanity)."""
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
                               meta_contatti_window=None, google_contatti_window=None):
    """
    Rational BeeFamily per uso INTERNO (team) — tono colloquiale, asciutto.
    Struttura: titolo periodo + breakdown per canale + prossima mossa.
    - Aggregato per investimento e lead totali
    - Sempre dettaglio Meta / Google se presenti (Investimento, Lead, CPL)
    - Niente prosa lunga: bullet-style con riga sintesi
    """
    avg_daily = total_spend_window / max(window_days, 1)
    pct_zero = (zero_days / max(window_days, 1)) * 100

    # Peak day estratto dalla serie giornaliera (Meta+Google sommati)
    peak_iso, peak_spend = None, 0
    if daily_series_data:
        for d, s in daily_series_data:
            if s and s > peak_spend:
                peak_iso, peak_spend = d, s
    peak_wd = ""
    if peak_iso:
        try:
            peak_wd = _WEEKDAYS_IT[parse_iso(peak_iso).weekday()]
        except Exception:
            peak_wd = ""

    google_share = (google_spend_total / total_spend_window * 100) if total_spend_window else 0
    cpl_window = (total_spend_window / contatti_window) if contatti_window > 0 else None
    cn = client_name
    meta_contatti = meta_contatti_window if meta_contatti_window is not None else contatti_window
    google_contatti = google_contatti_window if google_contatti_window is not None else 0
    has_meta = meta_spend_total > 0 or meta_contatti > 0
    has_g    = has_google and (google_spend_total > 0 or google_contatti > 0)
    meta_cpl   = (meta_spend_total   / meta_contatti)   if meta_contatti   > 0 else None
    google_cpl = (google_spend_total / google_contatti) if google_contatti > 0 else None

    def fmt_int(n):
        if n is None or n == 0: return "0"
        return f"{int(n):,}".replace(",", ".")

    def fmt_pct_short(p):
        if p is None: return ""
        sign = "+" if p >= 0 else ""
        return f"{sign}{p:.0f}%"

    def channel_line(label, spend, leads, cpl):
        bits = [f"<strong>{label}:</strong>"]
        bits.append(f"Investimento {fmt_eur(spend)}")
        if leads is not None and leads > 0:
            bits.append(f"Lead generati {fmt_int(leads)}")
            if cpl is not None:
                bits.append(f"CPL {fmt_eur(cpl)}")
        elif spend > 0:
            bits.append("Lead non tracciati lato canale")
        return " · ".join(bits)

    def wrap(headline, channels_html, action):
        # Tre blocchi: sintesi periodo, breakdown per canale, prossima mossa.
        chan_block = ("<ul class=\"r-channels\">" + "".join(f"<li>{c}</li>" for c in channels_html) + "</ul>") if channels_html else ""
        return (
            f"<p class=\"r-head\">{headline}</p>"
            + chan_block
            + f"<p class=\"r-action\"><strong>Prossima mossa.</strong> {action}</p>"
        )

    # ----- Sintesi periodo (1 frase) -----
    trend_str = fmt_pct_short(trend_pct) if trend_pct is not None else ""
    peak_str = f" · picco {peak_wd or 'centrale'} a {fmt_eur(peak_spend)}" if peak_iso else ""
    if total_spend_window == 0:
        headline = f"{cn}: in pausa nel periodo, zero spend{f' · giorni attivi {active_days}/{window_days}' if active_days else ''}."
    elif pct_zero > 30 and zero_days >= 3:
        avg_active = total_spend_window / max(active_days, 1)
        headline = (
            f"{cn}: erogazione a strappi ({zero_days} giorni a zero su {window_days}). "
            f"Totale {fmt_eur(total_spend_window)} · media giorni attivi {fmt_eur(avg_active)}{peak_str}."
        )
    elif trend_pct is not None and trend_pct > 25:
        headline = (
            f"{cn}: spinta in accelerazione ({trend_str} vs prima metà). "
            f"Totale {fmt_eur(total_spend_window)}{peak_str}."
        )
    elif trend_pct is not None and trend_pct < -25:
        headline = (
            f"{cn}: spinta in raffreddamento ({trend_str} vs prima metà). "
            f"Totale {fmt_eur(total_spend_window)}{peak_str}."
        )
    else:
        delta = f" · trend {trend_str}" if trend_str else ""
        headline = (
            f"{cn}: andamento regolare nel periodo. "
            f"Totale {fmt_eur(total_spend_window)} · {active_days} giorni attivi{delta}{peak_str}."
        )

    # ----- Breakdown per canale (sempre, se il canale è presente) -----
    channels = []
    if has_meta:
        channels.append(channel_line("META", meta_spend_total, meta_contatti, meta_cpl))
    if has_g:
        channels.append(channel_line("GOOGLE", google_spend_total, google_contatti, google_cpl))
    # Aggregato totale (sempre — utile come riassunto)
    total_leads = (meta_contatti or 0) + (google_contatti or 0)
    if total_leads > 0:
        total_cpl = total_spend_window / total_leads if total_leads > 0 else None
        channels.append(
            f"<strong>TOTALE:</strong> Investimento {fmt_eur(total_spend_window)} · Lead generati {fmt_int(total_leads)}"
            + (f" · CPL {fmt_eur(total_cpl)}" if total_cpl is not None else "")
        )
    else:
        channels.append(f"<strong>TOTALE:</strong> Investimento {fmt_eur(total_spend_window)} · 0 lead nel periodo")

    # ----- Prossima mossa (1 frase, da team interno) -----
    is_cooling   = trend_pct is not None and trend_pct < -25
    is_accel     = trend_pct is not None and trend_pct > 25
    no_contacts  = total_leads == 0
    yesterday_active = spend_y > 0

    if total_spend_window == 0:
        action = _pick(cn + "·BFe·act·pause", [
            "Asset pronti per quando si rialza lo switch, niente refresh oggi.",
            "Budget intatto: lo teniamo per la prossima finestra calda.",
        ])
    elif pct_zero > 30 and zero_days >= 3:
        action = _pick(cn + "·BFe·act·strappi", [
            "Priorità: riportare l'erogazione a 7/7 (check billing + pacing).",
            "Sistemare la continuità: senza copertura quotidiana l'algoritmo riparte ogni volta.",
        ])
    elif no_contacts and yesterday_active:
        action = _pick(cn + "·BFe·act·nolead", [
            "Audit veloce su creative + tracking: c'è spesa ma zero lead, qualcosa si rompe nel funnel.",
            "Refresh creative + verifica pixel/CAPI: stiamo spendendo a vuoto.",
        ])
    elif is_cooling:
        action = _pick(cn + "·BFe·act·cool", [
            "Rinfresco creative top + bid review per invertire la curva entro 7gg.",
            "Nuovo lotto creativo in coda: serve ripartire dalla seconda metà.",
        ])
    elif is_accel:
        action = _pick(cn + "·BFe·act·acc", [
            "Tenere il ritmo: secondo set creativo pronto a entrare prima della saturazione.",
            "Monitoriamo frequency: appena tocca 2,5 entriamo con nuovi creative.",
        ])
    else:
        action = _pick(cn + "·BFe·act·steady", [
            "Si tiene la rotta, mettiamo in coda un test creativo a basso budget.",
            "Confermare assetto + preparare refresh creativo successivo.",
        ])

    return wrap(headline, channels, action)




def _build_aghc_rational(client_name, window_days, total_spend_window,
                          meta_spend_total, tt_spend_total, has_tiktok,
                          zero_days, active_days, trend_pct,
                          contatti_y, spend_y, daily_series_data=None,
                          vanity_window=None):
    """
    Rational a 3 paragrafi (Cosa è successo / Perché conta / Cosa faremo ora).
    Variants pool deterministiche per client + dati specifici (peak day, weekday).
    """
    avg_daily = total_spend_window / max(window_days, 1)
    pct_zero = (zero_days / max(window_days, 1)) * 100

    # === Peak/low day estratti dalla serie giornaliera ===
    peak_iso, peak_spend = None, 0
    low_iso, low_spend = None, None
    if daily_series_data:
        for d, s in daily_series_data:
            if s and s > peak_spend:
                peak_iso, peak_spend = d, s
            if s and s > 0 and (low_spend is None or s < low_spend):
                low_iso, low_spend = d, s
    peak_wd = ""
    if peak_iso:
        try:
            peak_wd = _WEEKDAYS_IT[parse_iso(peak_iso).weekday()]
        except Exception:
            peak_wd = ""

    tt_share = (tt_spend_total / total_spend_window * 100) if total_spend_window else 0
    cn = client_name  # alias

    def fmt_int(n):
        if n is None or n == 0: return "0"
        return f"{int(n):,}".replace(",", ".")

    def wrap(p1, p2, p3):
        # Stile descrittivo argomentato: niente label uppercase, solo prosa
        return f"<p>{p1}</p><p>{p2}</p><p>{p3}</p>"

    # Vanity inline string (riga "gasazione" da incastonare nei paragrafi)
    v = vanity_window or {}
    v_impr = v.get("impressions", 0)
    v_clicks = v.get("clicks", 0)
    v_lpv = v.get("lpv", 0)
    v_eng = v.get("page_eng", 0)
    has_vanity = (v_impr + v_clicks + v_eng) > 0
    vanity_phrase = ""
    if has_vanity:
        parts = []
        if v_impr > 0:
            parts.append(f"{fmt_int(v_impr)} visualizzazioni")
        if v_clicks > 0:
            parts.append(f"{fmt_int(v_clicks)} click")
        if v_eng > 0:
            parts.append(f"{fmt_int(v_eng)} interazioni con la pagina")
        if v_lpv > 50:
            parts.append(f"{fmt_int(v_lpv)} visite landing")
        vanity_phrase = ", ".join(parts)

    # ============================================================
    # RAMO A — Pausa pulita (nessuno spending nel periodo)
    # ============================================================
    if total_spend_window == 0:
        p1 = _pick(cn + "·A·p1", [
            f"In queste due settimane {cn} è rimasto fermo: nessuna spesa, l'account ha tenuto la riserva di budget al sicuro.",
            f"Le ultime giornate per {cn} sono passate in silenzio pubblicitario, in linea con la stagionalità del piano.",
            f"Per {cn} il periodo è stato di stand-by programmato: zero erogazione e zero rumore.",
        ])
        p2 = _pick(cn + "·A·p2", [
            "Quello che non è speso adesso resta a disposizione per le finestre commerciali più calde, dove ogni euro pesa di più.",
            "La riserva di budget intatta diventa la nostra leva nella prossima apertura di stagione: meno disperso, più mirato.",
            "Nessun consumo a vuoto significa che possiamo concentrare il fuoco esattamente dove sappiamo che la domanda risponderà.",
        ])
        p3 = _pick(cn + "·A·p3", [
            "Quando rialzeremo lo switch ripartiamo con un set creativo nuovo e una distribuzione piena su tutta la settimana, così non perdiamo i primi giorni in start-up.",
            "Per la riapertura prepariamo un test creativo fresco e una cadenza distribuita: l'algoritmo deve poter scaldare l'apprendimento da subito.",
            "Alla ripresa lavoreremo su creatività rinnovate e copertura quotidiana: l'obiettivo è entrare nella seconda settimana già a regime.",
        ])
        return wrap(p1, p2, p3)

    # ============================================================
    # RAMO B — Erogazione frammentata (>30% giorni a zero)
    # ============================================================
    if pct_zero > 30 and zero_days >= 3:
        p1 = _pick(cn + "·B·p1", [
            f"L'erogazione di {cn} è andata a strappi: in {zero_days} giornate su {window_days} l'account è rimasto fermo, "
            f"e i {fmt_eur(total_spend_window)} totali si sono concentrati in pochi giorni di attività piena.",
            f"Quindici giornate spezzate per {cn}: {zero_days} a zero, le altre {active_days} che si sono divise tutto il "
            f"carico — {fmt_eur(total_spend_window)} bruciati senza una distribuzione regolare.",
            f"Per {cn} è stata una finestra a singhiozzo: solo {active_days} giorni effettivi di spinta, dove sono confluiti i "
            f"{fmt_eur(total_spend_window)} di periodo.",
        ])
        avg_active = total_spend_window / max(active_days, 1)
        p2 = _pick(cn + "·B·p2", [
            f"Sui giorni effettivamente attivi la media sale a {fmt_eur(avg_active)}, ma la discontinuità penalizza la "
            f"curva di apprendimento e la stabilità delle aste.",
            f"Quando l'account spinge, spinge forte ({fmt_eur(avg_active)} al giorno), ma le pause obbligano l'algoritmo a "
            f"ricominciare da capo ogni volta che torniamo live.",
            f"Il problema non è il quanto — sui giorni attivi si arriva a {fmt_eur(avg_active)} medi — ma il quando: senza "
            f"continuità il pubblico non si scalda e la frequenza non si stabilizza.",
        ])
        if contatti_y > 0:
            p3 = _pick(cn + "·B·p3a", [
                f"Per la prossima settimana l'obiettivo è uno solo: riportare l'erogazione a sette giorni su sette. Ieri "
                f"abbiamo già visto {contatti_y} contatti, segnale che il messaggio risponde — non manca la domanda, manca la presenza.",
                f"Riallineiamo la cadenza: l'ultimo giorno ha portato {contatti_y} contatti pur con erogazione interrotta, "
                f"quindi sappiamo che il pubblico c'è. La priorità è eliminare i buchi di copertura.",
            ])
        else:
            p3 = _pick(cn + "·B·p3b", [
                f"La prima mossa è ripristinare la continuità quotidiana — poi controlleremo bidding e creatività per "
                f"capire perché non stiamo intercettando contatti nemmeno nei giorni attivi.",
                f"Riattiviamo l'erogazione stabile e poi facciamo un audit veloce: senza contatti su {active_days} giorni di "
                f"spinta serve verificare offerta, audience e creative.",
            ])
        return wrap(p1, p2, p3)

    # ============================================================
    # RAMO C — Accelerazione forte (+25%)
    # ============================================================
    if trend_pct is not None and trend_pct > 25:
        peak_clause = f" con un picco {peak_wd or 'centrale'} a {fmt_eur(peak_spend)}" if peak_iso else ""
        p1 = _pick(cn + "·C·p1", [
            f"{cn} ha cambiato passo nelle ultime due settimane: la spesa nella seconda metà è {trend_pct:.0f}% sopra la prima, "
            f"portando il totale a {fmt_eur(total_spend_window)}{peak_clause}.",
            f"Per {cn} è stato un periodo in accelerazione netta: +{trend_pct:.0f}% di spesa tra prima e seconda settimana, "
            f"{fmt_eur(total_spend_window)} bruciati con una curva chiaramente in salita{peak_clause}.",
            f"Le ultime giornate di {cn} hanno alzato l'asticella: +{trend_pct:.0f}% nella seconda parte della finestra, "
            f"con il monte spese che chiude a {fmt_eur(total_spend_window)}{peak_clause}.",
        ])
    elif trend_pct is not None and trend_pct < -25:
        # ============================================================
        # RAMO D — Raffreddamento (-25%)
        # ============================================================
        p1 = _pick(cn + "·D·p1", [
            f"{cn} ha rallentato visibilmente: la spesa della seconda metà è {abs(trend_pct):.0f}% sotto la prima, "
            f"chiudendo il periodo a {fmt_eur(total_spend_window)} totali.",
            f"Per {cn} la curva si è raffreddata: −{abs(trend_pct):.0f}% nella seconda settimana, segno che qualcosa "
            f"nell'erogazione o nel bidding ha frenato.",
            f"Nelle ultime giornate {cn} ha ridotto la presenza: cala del {abs(trend_pct):.0f}% tra prima e seconda metà, "
            f"a fronte di un totale di {fmt_eur(total_spend_window)} sul periodo.",
        ])
    elif trend_pct is not None and trend_pct > 5:
        # ============================================================
        # RAMO E — Crescita misurata (+5 a +25%)
        # ============================================================
        peak_clause = f", con il picco {peak_wd} a {fmt_eur(peak_spend)}" if peak_iso else ""
        p1 = _pick(cn + "·E·p1", [
            f"Negli ultimi {window_days} giorni {cn} ha tenuto una traiettoria in lieve salita, con un +{trend_pct:.0f}% "
            f"tra la prima e la seconda metà del periodo: in totale sono stati investiti {fmt_eur(total_spend_window)}, "
            f"distribuiti con regolarità su tutta la finestra{peak_clause}.",
            f"Per {cn} la finestra appena chiusa è stata una crescita controllata (+{trend_pct:.0f}%): "
            f"{fmt_eur(total_spend_window)} di investimento spalmati su {window_days} giorni che hanno respirato bene"
            f"{peak_clause}.",
            f"Curva in lieve risalita per {cn} nelle ultime due settimane, con un +{trend_pct:.0f}% di spesa nella "
            f"seconda parte del periodo e {fmt_eur(total_spend_window)} totali messi a terra senza giorni fuori scala"
            f"{peak_clause}.",
        ])
    else:
        # ============================================================
        # RAMO F — Stabilità / leggero calo
        # ============================================================
        delta_str = f" ({trend_pct:+.0f}% tra prima e seconda metà del periodo)" if trend_pct is not None else ""
        peak_clause = f", con la giornata più importante {peak_wd} a {fmt_eur(peak_spend)}" if peak_iso else ""
        p1 = _pick(cn + "·F·p1", [
            f"Nelle ultime due settimane {cn} ha mantenuto la rotta che ci siamo dati: {fmt_eur(total_spend_window)} "
            f"investiti su {active_days} giorni effettivi di erogazione, senza scossoni rilevanti{delta_str}{peak_clause}.",
            f"Per {cn} il periodo è stato di crociera: {fmt_eur(total_spend_window)} spesi con una cadenza prevedibile "
            f"giorno per giorno{delta_str}{peak_clause}. È esattamente il ritmo che il piano media richiede in questa parte della stagione.",
            f"Andamento regolare per {cn} negli ultimi {window_days} giorni, con {fmt_eur(total_spend_window)} totali "
            f"distribuiti sui {active_days} giorni attivi e nessuna oscillazione meritevole di intervento{delta_str}{peak_clause}.",
        ])

    # ============================================================
    # P2 — Perché conta: VANITY metrics nel testo + composizione canali
    # ============================================================
    if has_vanity:
        # Frase principale: vanity in evidenza, poi media giornaliera come contesto.
        p2_opener = _pick(cn + "·p2·van", [
            f"Sul fronte della visibilità i numeri parlano da soli: le campagne hanno totalizzato {vanity_phrase}, "
            f"con una spesa media giornaliera di {fmt_eur(avg_daily)}",
            f"In termini di copertura il bilancio è solido — abbiamo portato a casa {vanity_phrase}, "
            f"a fronte di {fmt_eur(avg_daily)} di investimento medio al giorno",
            f"La fotografia di gasazione del periodo restituisce {vanity_phrase}, "
            f"con un ritmo giornaliero di {fmt_eur(avg_daily)} di spesa",
        ])
    else:
        p2_opener = _pick(cn + "·p2·noVan", [
            f"La media giornaliera nel periodo è {fmt_eur(avg_daily)}",
            f"Il ritmo è di {fmt_eur(avg_daily)} al giorno",
        ])

    # TikTok clause
    tk_clause = ""
    if has_tiktok and tt_spend_total > 0 and tt_share >= 8:
        tk_clause = _pick(cn + "·p2·tk", [
            f", con il canale TikTok che pesa per il {tt_share:.0f}% del mix ({fmt_eur(tt_spend_total)}) sul pubblico più giovane",
            f", con TikTok in affiancamento al {tt_share:.0f}% ({fmt_eur(tt_spend_total)}) come secondo canale di presidio",
            f" e con TikTok che porta il {tt_share:.0f}% del totale ({fmt_eur(tt_spend_total)}) a presidiare il target sotto i 35 anni",
        ])
    elif has_tiktok and tt_spend_total > 0:
        tk_clause = f", con TikTok in attivazione marginale ({fmt_eur(tt_spend_total)} di affiancamento)"
    elif has_tiktok and tt_spend_total == 0:
        tk_clause = _pick(cn + "·p2·tk0", [
            " — concentrati per ora sul solo canale Meta, mentre TikTok resta in stand-by",
            "; per la finestra appena chiusa TikTok è rimasto fermo, scelta che andrà rivalutata alla prossima apertura",
        ])

    p2 = p2_opener + tk_clause + "."

    # Contatti aggiunti come frase narrativa successiva
    if contatti_y > 50:
        p2 += _pick(cn + "·p2·c+", [
            f" Ieri sono entrati anche {contatti_y} contatti diretti, segnale che il messaggio attuale sta intercettando bene la domanda.",
            f" Sul fronte conversioni l'ultimo giorno ha portato {contatti_y} contatti, conferma che la creatività gira sul pubblico giusto.",
        ])
    elif contatti_y > 0:
        p2 += _pick(cn + "·p2·c-", [
            f" L'ultimo giorno ha portato anche {contatti_y} contatti diretti, dentro le aspettative del funnel.",
            f" Tra le conversioni dirette di ieri abbiamo {contatti_y} contatti, in linea con la media del periodo.",
        ])

    # ============================================================
    # P3 — Cosa faremo ora (concreto, niente cliché)
    # ============================================================
    if trend_pct is not None and trend_pct > 25:
        p3 = _pick(cn + "·p3·up", [
            f"Lasciamo correre la spinta ma teniamo l'occhio su CPL e frequenza: se la frequenza supera 2,5 entriamo "
            f"subito con un test creativo nuovo per non bruciare il pubblico.",
            f"La crescita la cavalchiamo, però la prossima settimana misuriamo CPL giornaliero e frequenza — se l'asta "
            f"si surriscalda alziamo il prezzo per evitare di pagare di più ogni nuovo utente.",
            f"Cavalchiamo il momentum senza forzare: alziamo i tetti budget solo se il CPL resta stabile, e ruotiamo "
            f"creatività appena la frequenza tocca 2,5.",
        ])
    elif trend_pct is not None and trend_pct < -25:
        p3 = _pick(cn + "·p3·down", [
            f"La prossima cosa da fare è capire se il calo è strategico o tecnico: controlliamo bidding, copertura del "
            f"pubblico e vivacità delle creatività, e poi decidiamo se rialzare la spinta.",
            f"Riapro le campagne lunedì per un audit veloce: CTR, copertura giornaliera e budget non spesi. Se il calo "
            f"non è voluto, riallineo bidding e creatività in giornata.",
            f"Programmo subito una revisione: vedo se è un raffreddamento naturale del pubblico (servono creatività nuove) "
            f"o un limite di bidding/copertura, e ti dico cosa muovere.",
        ])
    elif zero_days > 0 and zero_days <= 2:
        p3 = _pick(cn + "·p3·zd", [
            f"Da chiarire {zero_days} {'giorno' if zero_days == 1 else 'giorni'} a zero nel periodo: oggi verifico che "
            f"non sia un blocco budget o billing e ti aggiorno entro l'orario operativo.",
            f"Quei {zero_days} giorni a spending nullo me li guardo subito: controllo limiti carta, billing e "
            f"campaign status, così sappiamo se è stata una pausa voluta.",
        ])
    elif has_tiktok and tt_spend_total == 0:
        p3 = _pick(cn + "·p3·tk0", [
            f"Nella prossima finestra rimettiamo in moto TikTok: serve quel canale per non lasciare scoperto il pubblico "
            f"sotto i 30 anni, dove ormai la prima ricerca passa da lì.",
            f"La prima cosa da decidere è quando riattivare TikTok — il pubblico più giovane sta scivolando fuori dal "
            f"funnel solo Meta e dobbiamo ricaricarlo.",
        ])
    else:
        p3 = _pick(cn + "·p3·ok", [
            f"Nessuna mossa urgente: la prossima settimana facciamo solo refresh creativo sugli annunci più stanchi e "
            f"teniamo monitorato il CPL giorno per giorno.",
            f"Per ora si va così: rotazione creativa di routine, monitoraggio CPL giornaliero, niente intervento "
            f"strutturale fino al prossimo segnale.",
            f"Si naviga: nessuna correzione di rotta, solo refresh creativo se compaiono segnali di saturazione e "
            f"controllo del CPL sulla media settimanale.",
        ])

    return wrap(p1, p2, p3)


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

    # Indice vanity (account_id, date) → {impressions, clicks, lpv, page_eng}
    vanity_idx = {}
    if vanity_rows:
        for r in vanity_rows:
            key = (str(r.get("account_id")), r.get("date"))
            vanity_idx[key] = {
                "impressions": int(r.get("impressions") or 0),
                "clicks": int(r.get("clicks") or 0),
                "lpv": int(r.get("actions_landing_page_view") or 0),
                "page_eng": int(r.get("actions_page_engagement") or 0),
            }

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

        # Vanity metrics aggregati sul window (impressions, clicks, landing page views, page engagement)
        # CALCOLATI PRIMA del rational così possono essere passati come argomento
        van_impr_w = 0
        van_clicks_w = 0
        van_lpv_w = 0
        van_eng_w = 0
        van_impr_y = 0
        van_clicks_y = 0
        van_lpv_y = 0
        van_eng_y = 0
        for d, _ in meta_series:
            v = vanity_idx.get((mid, d))
            if v:
                van_impr_w += v["impressions"]
                van_clicks_w += v["clicks"]
                van_lpv_w += v["lpv"]
                van_eng_w += v.get("page_eng", 0)
                if d == y_iso:
                    van_impr_y = v["impressions"]
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
            vanity_window={"impressions": van_impr_w, "clicks": van_clicks_w, "lpv": van_lpv_w, "page_eng": van_eng_w},
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
            "series": [{"date": d, "spend": round(s, 2)} for d, s in meta_series],
            "window_days": window_days,
            "vanity": {
                "impressions_window": van_impr_w,
                "clicks_window": van_clicks_w,
                "lpv_window": van_lpv_w,
                "page_eng_window": van_eng_w,
                "impressions_y": van_impr_y,
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

    mt_spend = 0.0
    mt_camps = set()
    for r in medtech_rows:
        if r.get("date") != y_iso:
            continue
        camp = r.get("campaign", "")
        if not MEDTECH_FILTER.search(camp or ""):
            continue
        sp = float(r.get("spend") or 0)
        mt_spend += sp
        if sp > 0:
            mt_camps.add(camp)

    proj_data = [
        {"name": "BeeFamily",   "spend": round(bf_meta_s + bf_google_s, 2), "accounts": bf_meta_n + bf_google_n},
        {"name": "AGHC",        "spend": round(aghc_meta_s + aghc_tt_s, 2), "accounts": aghc_meta_n + aghc_tt_n},
        {"name": "Med & Tech",  "spend": round(mt_spend, 2),                "accounts": len(mt_camps)},
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
        )

        bf_cards.append({
            "id": c["name"].lower().replace(" ", "-").replace("&", "and"),
            "name": c["name"],
            "spend_window": round(spend_window, 2),
            "spend_y": round(spend_y, 2),
            "window_days": bf_window_days,
            "trend_arrow": trend_arrow,
            "trend_label": trend_label,
            "trend_pct": round(trend_pct, 1) if trend_pct is not None else None,
            "status": card_status,
            "rational": rational_html,
            "ad_url_meta":   url_meta(meta_id)     if meta_id   else None,
            "ad_url_google": url_google(google_id) if google_id else None,
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

    # ============= MED & TECH =============
    out["medtech"] = _build_medtech(medtech_rows, y_iso, yesterday)

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

def _medtech_status(spend_y, lead_y, cpl_mean_7d):
    """
    Stessa logica della scheduled task med-tech-daily-total-lift-sculpt:
    - NERO: spend ieri == 0 (campagna ferma)
    - ROSSO: 0 lead pur con spending OPPURE CPL ieri > 1.5x media 7gg
    - GIALLO: CPL ieri tra 1.0x e 1.5x media 7gg
    - VERDE: CPL ieri ≤ media 7gg
    """
    if spend_y == 0:
        return {"color": "black", "label": "NERO",
                "reason": "Nessuna spesa ieri sulla campagna"}
    if lead_y == 0:
        return {"color": "red", "label": "ROSSO",
                "reason": f"Spesi {fmt_eur(spend_y)} ieri senza generare lead via modulo Lead Ad"}
    cpl_y = spend_y / lead_y
    if cpl_mean_7d is None or cpl_mean_7d == 0:
        return {"color": "green", "label": "VERDE",
                "reason": f"Spesi {fmt_eur(spend_y)} con {lead_y} lead (CPL {fmt_eur(cpl_y)})"}
    ratio = cpl_y / cpl_mean_7d
    delta_pct = (ratio - 1) * 100
    if ratio > 1.5:
        return {"color": "red", "label": "ROSSO",
                "reason": f"CPL ieri {fmt_eur(cpl_y)} contro media 7gg {fmt_eur(cpl_mean_7d)} ({fmt_pct(delta_pct)}, oltre la soglia +50%)"}
    if ratio > 1.0:
        return {"color": "yellow", "label": "GIALLO",
                "reason": f"CPL ieri {fmt_eur(cpl_y)} contro media 7gg {fmt_eur(cpl_mean_7d)} ({fmt_pct(delta_pct)}, lieve crescita)"}
    return {"color": "green", "label": "VERDE",
            "reason": f"CPL ieri {fmt_eur(cpl_y)} contro media 7gg {fmt_eur(cpl_mean_7d)} ({fmt_pct(delta_pct)}, in linea o sotto)"}


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
    def cpl_mean_7d(daily, lead_daily, ref_iso):
        ref = parse_iso(ref_iso)
        cpls = []
        for i in range(1, 8):
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
        cpl_mean = cpl_mean_7d(e["daily"], e["lead_daily"], y_iso)
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
            "cpl_mean_7d": round(cpl_mean, 2) if cpl_mean is not None else None,
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
    ap.add_argument("--medtech", required=True)
    ap.add_argument("--workspace", required=True, help="Path workspace (Dashboard di Controllo)")
    ap.add_argument("--aghc-vanity", default=None, help="Path opzionale a JSON con vanity metrics (impressions/clicks/landing_page_view) per AGHC")
    ap.add_argument("--aghc-budgets", default=None, help="Path opzionale a aghc_budgets.json con budget_annuale + ytd_seed per ogni meta_id")
    ap.add_argument("--retention-days", type=int, default=90, help="Quanti snapshot/<date>.json tenere; più vecchi vengono cancellati")
    ap.add_argument("--ref-date", default=None, help="Override reference date (YYYY-MM-DD); default = ieri")
    args = ap.parse_args()

    def load(path):
        with open(path, "r", encoding="utf-8") as f:
            j = json.load(f)
        return j.get("result", j) if isinstance(j, dict) else j

    meta = load(args.meta)
    google = load(args.google)
    tiktok = load(args.tiktok)
    medtech = load(args.medtech)

    ref_date = parse_iso(args.ref_date) if args.ref_date else None
    vanity_rows = load(args.aghc_vanity) if args.aghc_vanity and os.path.exists(args.aghc_vanity) else None
    budgets_config = None
    if args.aghc_budgets and os.path.exists(args.aghc_budgets):
        with open(args.aghc_budgets, "r", encoding="utf-8") as f:
            budgets_config = json.load(f)
    data = build(meta, google, tiktok, medtech, ref_date=ref_date, vanity_rows=vanity_rows, budgets_config=budgets_config)

    workspace = args.workspace
    snap_dir = os.path.join(workspace, "snapshots")
    os.makedirs(snap_dir, exist_ok=True)

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

    # ============= ACTIONS.JSON per Calendar =============
    # Trigger:
    # - HIGH spending: account con BOTH triggers (>50€ + >30% vs media 7gg) — più critico
    # - NEW fermo: account in spending.zero oggi che NON era in spending.zero ieri (diff snapshot)
    actions = []
    ref_date_iso = data["reference_date"]
    ref_date_label = data["reference_date_label"]

    # Cerca lo snapshot del giorno PRECEDENTE (ieri rispetto a reference_date)
    prev_date = (parse_iso(ref_date_iso) - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_snap_path = os.path.join(snap_dir, prev_date + ".json")
    prev_zero_ids = set()
    prev_snapshot_exists = os.path.exists(prev_snap_path)
    if prev_snapshot_exists:
        try:
            with open(prev_snap_path, "r", encoding="utf-8") as f:
                prev_data = json.load(f)
            prev_zero_ids = {f"{r['platform']}:{r['account_id']}" for r in prev_data.get("spending", {}).get("zero", [])}
        except Exception:
            prev_snapshot_exists = False

    # 1) HIGH spending critici (entrambi trigger)
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

    # 2) NEW fermi (in zero oggi, non c'erano ieri)
    # Solo se abbiamo lo snapshot di ieri per fare il diff. Al primo run salta del tutto
    # (altrimenti tutti i fermi sarebbero "nuovi" e riempirebbe il calendar).
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
        # Sort by media7 desc — prima i più "importanti" (spendevano di più prima del fermo)
        new_fermi.sort(key=lambda a: -float(a['details'].split('precedente ')[1].split(' €')[0].replace('.','').replace(',','.')) if 'precedente' in a['details'] else 0)
        actions.extend(new_fermi[:10])  # max 10 new_fermi al giorno

    # Cap globale per non saturare il Calendar: max 15 azioni totali
    actions = actions[:15]

    actions_path = os.path.join(workspace, "actions.json")
    with open(actions_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": data["generated_at"],
            "reference_date": ref_date_iso,
            "actions": actions,
        }, f, ensure_ascii=False, indent=2)
    print(f"✓ actions.json: {len(actions)} azioni (high={sum(1 for a in actions if a['type']=='high_spending')}, new_fermo={sum(1 for a in actions if a['type']=='new_fermo')})")

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
    mt_alerts = sum(1 for e in data['medtech']['entries'] if e['status']['color'] in ('red','yellow'))
    print(f"  medtech entries = {len(data['medtech']['entries'])}, alerts = {mt_alerts}")

if __name__ == "__main__":
    main()
