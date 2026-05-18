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

PAGES_URL = "https://moscadv.github.io/dashboard-di-controllo/"  # aggiornare dopo primo push

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
            onsite = int(r.get("actions_onsite_conversion_lead_grouped") or 0)
            lead_ad = int(r.get("actions_lead") or 0)
            contatti = onsite + lead_ad
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
                return {"color": "red", "label": "CPC critico",
                        "reason": f"CPC {fmt_eur(cpc_y)} vs media 7gg {fmt_eur(cpc_mean)} ({fmt_pct(delta_pct)})"}
            if ratio > 1.2:
                return {"color": "yellow", "label": "CPC in salita",
                        "reason": f"CPC {fmt_eur(cpc_y)} vs media 7gg {fmt_eur(cpc_mean)} ({fmt_pct(delta_pct)})"}
            return {"color": "green", "label": "In linea",
                    "reason": f"CPC {fmt_eur(cpc_y)} (media 7gg {fmt_eur(cpc_mean)}, {fmt_pct(delta_pct)})"}
        return {"color": "green", "label": "Attivo",
                "reason": f"Spesi {fmt_eur(spend_y)} con {contatti_y} contatti (CPC {fmt_eur(cpc_y) if cpc_y else '—'})"}

    # hotel — status su spending anomalo vs media 7gg
    info_c = ""
    if contatti_y > 0:
        cpc_y = spend_y / contatti_y
        info_c = f" · {contatti_y} contatti (CPC {fmt_eur(cpc_y)})"
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
        f"Spending: {fmt_eur(kpi['total_spend'])} · Contatti: {kpi['total_contatti']} · CPC medio: {fmt_eur(kpi['cpc_y']) if kpi['cpc_y'] else '—'}",
        f"Apri dashboard live: {PAGES_URL}",
    ]
    return "\n".join(lines)

def recap_medtech_slack(kpi, entries, yesterday):
    reds   = sum(1 for e in entries if e.get("status", {}).get("color") == "red")
    yellows= sum(1 for e in entries if e.get("status", {}).get("color") == "yellow")
    greens = sum(1 for e in entries if e.get("status", {}).get("color") == "green")
    grays  = sum(1 for e in entries if e.get("status", {}).get("color") == "gray")
    lines = [
        "Med & Tech —",
        f"Daily Check del {date_slash(yesterday)}",
        f"{kpi['actives']} campagne attive · {reds} ROSSO · {yellows} GIALLO · {greens} VERDE · {grays} NERO",
        f"Apri Report Storico: https://advfmosca.github.io/med-tech-daily-check/",
        f"Apri dashboard: {PAGES_URL}#medtech",
    ]
    return "\n".join(lines)

def recap_aghc_slack(cards, yesterday):
    actives = sum(1 for c in cards if c["spend_y"] > 0)
    tot_spend = sum(c["spend_y"] for c in cards)
    reds = sum(1 for c in cards if c["status"]["color"] == "red")
    yellows = sum(1 for c in cards if c["status"]["color"] == "yellow")
    lines = [
        f"AGHC — Daily Check del {date_slash(yesterday)}",
        f"{actives} clienti attivi su {len(cards)} · Spending {fmt_eur(tot_spend)}",
        f"{reds} alert critici · {yellows} da monitorare",
        f"Dashboard live: {PAGES_URL}#aghc",
    ]
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

def build_aghc_cards(meta_rows, tiktok_rows, y_iso, yesterday, window_days=15):
    """
    Una card per cliente AGHC. Se più voci roster condividono lo stesso meta_id,
    le aggrego in UNA card con nomi merged (es. "ACCENTODI + ADESSO").
    """
    meta_map = build_daily_map(meta_rows, is_meta_with_leads=True)
    tiktok_map = build_daily_map(tiktok_rows, is_meta_with_leads=False)

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
        # Zero days nel window (giorni con 0 spending Meta nel window)
        zero_days_meta = sum(1 for _, s in meta_series if s == 0)
        active_days_meta = len(meta_series) - zero_days_meta

        # Status
        st = status_account(meta_spend_y + tt_spend_y, contatti_y, prev7_spend, prev7_contatti, project_type="hotel")

        # Trend: confronta media prima metà vs seconda metà del window
        mid_idx = len(meta_series) // 2
        first_half = [s for _, s in meta_series[:mid_idx]]
        second_half = [s for _, s in meta_series[mid_idx:]]
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

        # Rational: 2-3 righe
        rat_lines = []
        rat_lines.append(
            f"Negli ultimi {window_days} giorni l'account ha investito {fmt_eur(total_spend_window)} "
            f"({fmt_eur(total_spend_window / window_days)} al giorno in media)."
        )
        if trend_pct is not None:
            rat_lines.append(
                f"Trend di spesa {trend_label} ({fmt_pct(trend_pct)} confrontando prima e seconda metà del periodo)."
            )
        if zero_days_meta > 0:
            rat_lines.append(
                f"In {zero_days_meta} giorni su {window_days} l'account non ha speso; verificare cause."
            )
        else:
            rat_lines.append("Erogazione costante senza giorni a zero spending.")
        rational = " ".join(rat_lines)

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
        }
        cards.append(card)

    # sort: rossi/gialli in cima, poi spending desc
    pri = lambda c: 0 if c["status"]["color"] == "red" else (1 if c["status"]["color"] == "yellow" else 2)
    cards.sort(key=lambda c: (pri(c), -c["spend_window"]))
    return cards

# ============================ BUILD ============================

def build(meta_rows, google_rows, tiktok_rows, medtech_rows, now_dt=None, ref_date=None):
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
        "recap": recap_beefamily_slack(bf_kpi, bf_entries, yesterday),
    }

    # ============= AGHC =============
    aghc_cards = build_aghc_cards(meta_rows, tiktok_rows, y_iso, yesterday, window_days=15)
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

def _build_medtech(rows, y_iso, yesterday):
    camp_map = {}
    for r in rows:
        camp = r.get("campaign")
        if not camp or not MEDTECH_FILTER.search(camp):
            continue
        if camp not in camp_map:
            camp_map[camp] = {"daily": {}, "contatti_daily": {}, "status": r.get("campaign_effective_status")}
        e = camp_map[camp]
        d = r.get("date")
        e["daily"][d] = e["daily"].get(d, 0) + float(r.get("spend") or 0)
        ld = int(r.get("actions_onsite_conversion_lead_grouped") or 0)
        if ld:
            e["contatti_daily"][d] = e["contatti_daily"].get(d, 0) + ld
        if r.get("campaign_effective_status"):
            e["status"] = r["campaign_effective_status"]

    entries = []
    for k, e in camp_map.items():
        prev_spend, _ = sum_prev_window(e["daily"], y_iso, 7)
        prev_contatti, _ = sum_prev_window(e["contatti_daily"], y_iso, 7)
        entries.append({
            "name": k, "source": e.get("status") or "",
            "spend_y": round(e["daily"].get(y_iso, 0), 2),
            "contatti_y": int(e["contatti_daily"].get(y_iso, 0)),
            "prev7_spend": prev_spend,
            "prev7_contatti": prev_contatti,
            "ad_url": url_meta(MEDTECH_META_ACCOUNT),
        })
    kpi = compute_project(entries, project_type="leadgen")
    # sort: rossi -> gialli -> verdi/grigi; entro stesso colore, spend desc
    pri = lambda e: 0 if e["status"]["color"] == "red" else (1 if e["status"]["color"] == "yellow" else (2 if e["status"]["color"] == "gray" else 3))
    entries.sort(key=lambda e: (pri(e), -e["spend_y"]))
    for e in entries:
        e["prev7_spend"] = round(e["prev7_spend"], 2)
        e["prev7_contatti"] = int(e["prev7_contatti"])
    return {
        "kpi": {
            "actives": kpi["actives"],
            "total": kpi["total"],
            "total_spend": round(kpi["total_spend"], 2),
            "total_contatti": kpi["total_contatti"],
            "cpc_y": round(kpi["cpc_y"], 2) if kpi["cpc_y"] is not None else None,
            "cpc_mean": round(kpi["cpc_mean"], 2) if kpi["cpc_mean"] is not None else None,
        },
        "entries": entries,
        "recap": recap_medtech_slack(kpi, entries, yesterday),
    }

# ============================ MAIN ============================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", required=True)
    ap.add_argument("--google", required=True)
    ap.add_argument("--tiktok", required=True)
    ap.add_argument("--medtech", required=True)
    ap.add_argument("--workspace", required=True, help="Path workspace (Dashboard di Controllo)")
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
    data = build(meta, google, tiktok, medtech, ref_date=ref_date)

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
