#!/usr/bin/env python3
"""
build_data.py — Aggregator per la Dashboard di Controllo FMM/AGHC.

Legge i 4 dataset Windsor raw (passati via --meta, --google, --tiktok, --medtech),
calcola KPI/alert/status/recap e scrive data.json nel path indicato da --out.

Usage:
  python3 build_data.py --meta meta.json --google google.json \
    --tiktok tiktok.json --medtech medtech.json --out data.json
"""

import json
import argparse
import re
from datetime import datetime, timedelta
import os
import sys

# ============================ CONFIG ============================

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

# ============================ HELPERS ============================

def parse_iso(s):
    return datetime.strptime(s, "%Y-%m-%d").date()

def iso(d):
    return d.strftime("%Y-%m-%d")

def fmt_eur(n):
    if n is None:
        return "—"
    s = f"{n:,.2f}"
    # convert from 1,234.56 to 1.234,56
    s = s.replace(",", "_TEMP_").replace(".", ",").replace("_TEMP_", ".")
    return s + " €"

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

def build_daily_map(rows):
    """
    From a list of {account_id, account_name, date, spend, [actions_onsite_conversion_lead_grouped]}
    build {account_id: {name, daily: {date: spend}, leads_daily: {date: leads}}}
    """
    m = {}
    for r in rows:
        aid = str(r.get("account_id"))
        if aid not in m:
            m[aid] = {"name": r.get("account_name") or aid, "daily": {}, "leads_daily": {}}
        e = m[aid]
        if r.get("account_name"):
            e["name"] = r["account_name"]
        d = r.get("date")
        spend = float(r.get("spend") or 0)
        e["daily"][d] = e["daily"].get(d, 0) + spend
        lead = int(r.get("actions_onsite_conversion_lead_grouped") or 0)
        if lead:
            e["leads_daily"][d] = e["leads_daily"].get(d, 0) + lead
    return m

def sum_prev7(daily, ref_iso):
    """Return {total, mean7} of the 7 days preceding ref_iso."""
    ref = parse_iso(ref_iso)
    total = 0.0
    n = 0
    for i in range(1, 8):
        d = ref - timedelta(days=i)
        v = daily.get(iso(d))
        if v is not None:
            total += v
            n += 1
    return total, (total / 7) if n else 0

# ============================ STATUS LOGIC ============================

def status_account(spend_y, leads_y, prev7_spend, prev7_leads, project_type="hotel"):
    """
    project_type:
      - 'hotel'   (BeeFamily, AGHC): hotel/brand traffic. Status driven by spending trend
                  vs media 7gg. Lead count is informational (la maggior parte degli account
                  hotel non genera "lead" via Meta onsite — la conversione è la prenotazione
                  sul booking engine).
      - 'leadgen' (Med & Tech): campagne lead-gen pure. Status driven by CPL ratio vs media 7gg.
    """
    mean7 = prev7_spend / 7 if prev7_spend else 0
    if spend_y == 0 and prev7_spend > 0:
        return {"color": "gray", "label": "Fermo ieri",
                "reason": f"Spending ieri 0 ma media 7gg {fmt_eur(mean7)}"}
    if spend_y == 0:
        return {"color": "gray", "label": "Inattivo",
                "reason": "Nessuna spesa rilevante negli ultimi 8 giorni"}

    if project_type == "leadgen":
        if leads_y == 0:
            return {"color": "red", "label": "0 lead",
                    "reason": f"Spesi {fmt_eur(spend_y)} ieri senza generare lead"}
        cpl_y = spend_y / leads_y if leads_y > 0 else None
        cpl_mean = prev7_spend / prev7_leads if prev7_leads > 0 else None
        if cpl_y is not None and cpl_mean is not None and cpl_mean > 0:
            ratio = cpl_y / cpl_mean
            delta_pct = (ratio - 1) * 100
            if ratio > 1.5:
                return {"color": "red", "label": "CPL critico",
                        "reason": f"CPL {fmt_eur(cpl_y)} vs media 7gg {fmt_eur(cpl_mean)} ({fmt_pct(delta_pct)})"}
            if ratio > 1.2:
                return {"color": "yellow", "label": "CPL in salita",
                        "reason": f"CPL {fmt_eur(cpl_y)} vs media 7gg {fmt_eur(cpl_mean)} ({fmt_pct(delta_pct)})"}
            return {"color": "green", "label": "In linea",
                    "reason": f"CPL {fmt_eur(cpl_y)} (media 7gg {fmt_eur(cpl_mean)}, {fmt_pct(delta_pct)})"}
        return {"color": "green", "label": "Attivo",
                "reason": f"Spesi {fmt_eur(spend_y)} con {leads_y} lead (CPL {fmt_eur(cpl_y) if cpl_y else '—'})"}

    # project_type == "hotel" — status driven by spending anomaly vs media 7gg
    info_lead = ""
    if leads_y > 0:
        cpl_y = spend_y / leads_y
        info_lead = f" · {leads_y} lead (CPL {fmt_eur(cpl_y)})"
    if mean7 > 0:
        ratio = spend_y / mean7
        delta_pct = (ratio - 1) * 100
        if ratio > 1.5:
            return {"color": "red", "label": "Spesa anomala alta",
                    "reason": f"Spesi {fmt_eur(spend_y)} vs media 7gg {fmt_eur(mean7)} ({fmt_pct(delta_pct)}){info_lead}"}
        if ratio > 1.3:
            return {"color": "yellow", "label": "Spesa in salita",
                    "reason": f"Spesi {fmt_eur(spend_y)} vs media 7gg {fmt_eur(mean7)} ({fmt_pct(delta_pct)}){info_lead}"}
        if ratio < 0.4:
            return {"color": "yellow", "label": "Spesa in calo",
                    "reason": f"Spesi {fmt_eur(spend_y)} vs media 7gg {fmt_eur(mean7)} ({fmt_pct(delta_pct)}){info_lead}"}
        return {"color": "green", "label": "In linea",
                "reason": f"Spesi {fmt_eur(spend_y)} (media 7gg {fmt_eur(mean7)}, {fmt_pct(delta_pct)}){info_lead}"}
    return {"color": "green", "label": "Attivo",
            "reason": f"Spesi {fmt_eur(spend_y)} (no storico per confronto){info_lead}"}

def compute_project(entries, project_type="hotel"):
    tot_spend = sum(e["spend_y"] for e in entries)
    tot_leads = sum(e["leads_y"] for e in entries)
    tot_prev_spend = sum(e["prev7_spend"] for e in entries)
    tot_prev_leads = sum(e["prev7_leads"] for e in entries)
    actives = sum(1 for e in entries if e["spend_y"] > 0)
    cpl_y = tot_spend / tot_leads if tot_leads > 0 else None
    cpl_mean = tot_prev_spend / tot_prev_leads if tot_prev_leads > 0 else None
    for e in entries:
        e["status"] = status_account(e["spend_y"], e["leads_y"], e["prev7_spend"], e["prev7_leads"], project_type=project_type)
    return {
        "total_spend": tot_spend,
        "total_leads": tot_leads,
        "cpl_y": cpl_y,
        "cpl_mean": cpl_mean,
        "actives": actives,
        "total": len(entries),
    }

def build_recap(project_name, kpi, entries, yesterday):
    reds = [e for e in entries if e.get("status", {}).get("color") == "red"]
    yellows = [e for e in entries if e.get("status", {}).get("color") == "yellow"]
    grays = [e for e in entries if e.get("status", {}).get("color") == "gray"]
    lines = []
    lines.append(f"📊 Recap {project_name} — {date_slash(yesterday)}")
    lines.append("")
    cpl_str = fmt_eur(kpi['cpl_y']) if kpi['cpl_y'] is not None else "—"
    lines.append(f"Spending: {fmt_eur(kpi['total_spend'])} · Lead: {kpi['total_leads']} · CPL: {cpl_str}")
    cpl_mean_str = ("  ·  CPL medio 7gg: " + fmt_eur(kpi['cpl_mean'])) if kpi['cpl_mean'] is not None else ""
    lines.append(f"Account attivi: {kpi['actives']}/{kpi['total']}{cpl_mean_str}")
    lines.append("")
    if not reds and not yellows:
        lines.append("🟢 Performance in linea — nessun alert da gestire")
    else:
        if reds:
            lines.append(f"🔴 Alert critici ({len(reds)}):")
            for r in reds[:6]:
                src = f" ({r['source']})" if r.get("source") else ""
                lines.append(f"  • {r['name']}{src} — {r['status']['label']}: {r['status']['reason']}")
            if len(reds) > 6:
                lines.append(f"  • …e altri {len(reds) - 6}")
        if yellows:
            if reds:
                lines.append("")
            lines.append(f"🟡 Da monitorare ({len(yellows)}):")
            for y in yellows[:6]:
                src = f" ({y['source']})" if y.get("source") else ""
                lines.append(f"  • {y['name']}{src} — {y['status']['reason']}")
            if len(yellows) > 6:
                lines.append(f"  • …e altri {len(yellows) - 6}")
    if grays:
        lines.append("")
        names = ", ".join(g["name"] for g in grays[:5])
        suffix = "…" if len(grays) > 5 else ""
        lines.append(f"⚫ Fermi/inattivi ({len(grays)}): {names}{suffix}")
    lines.append("")
    if reds:
        next_act = f"Next action: verificare i {len(reds)} alert critici e rilanciare creatività/budget dove serve."
    elif yellows:
        next_act = f"Next action: monitorare i {len(yellows)} account in lieve risalita di CPL."
    else:
        next_act = "Next action: nessuna — mantenere la rotta."
    lines.append(next_act)
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
        out.append({
            "platform": platform,
            "account_id": aid,
            "account_name": e["name"],
            "target": target,
            "mean7": mean7,
            "delta": delta,
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
    zero.sort(key=lambda r: -r["mean7"])
    high.sort(key=lambda r: -r["target"])
    return zero, high

# ============================ BUILD ============================

def build(meta_rows, google_rows, tiktok_rows, medtech_rows, now_dt=None):
    now = now_dt or datetime.now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    prev7 = [(yesterday - timedelta(days=i+1)) for i in range(7)]
    prev7_iso = {iso(d) for d in prev7}
    y_iso = iso(yesterday)

    out = {
        "schema_version": 1,
        "generated_at": now.isoformat(),
        "generated_at_label": f"{date_slash(today)} {now.strftime('%H:%M')}",
        "reference_date": y_iso,
        "reference_date_label": date_label_it(yesterday),
        "errors": [],
    }

    meta_map = build_daily_map(meta_rows)
    google_map = build_daily_map(google_rows)
    tiktok_map = build_daily_map(tiktok_rows)

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

    # ============= SPENDING (no "speso ieri") =============
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

    # ============= PROJECTS =============
    out["beefamily"] = _build_project_block("BeeFamily", BEEFAMILY, meta_map, google_map, None, y_iso, yesterday, source_a="Meta", source_b="Google")
    out["aghc"]      = _build_project_block("AGHC",      AGHC,      meta_map, None, tiktok_map, y_iso, yesterday, source_a="Meta", source_b="TikTok")
    out["medtech"]   = _build_medtech(medtech_rows, y_iso, yesterday)

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
    }

def _build_project_block(name, roster, meta_map, google_map, tiktok_map, y_iso, yesterday, source_a, source_b, project_type="hotel"):
    entries = []
    for c in roster:
        meta_id = c.get("meta_id")
        if meta_id:
            e = meta_map.get(meta_id) or {"daily": {}, "leads_daily": {}}
            prev_spend, _ = sum_prev7(e["daily"], y_iso)
            prev_leads, _ = sum_prev7(e["leads_daily"], y_iso)
            entries.append({
                "name": c["name"], "source": source_a,
                "spend_y": round(e["daily"].get(y_iso, 0), 2),
                "leads_y": int(e["leads_daily"].get(y_iso, 0)),
                "prev7_spend": prev_spend,
                "prev7_leads": prev_leads,
            })
        google_id = c.get("google_id")
        if google_id and google_map is not None and source_b == "Google":
            e = google_map.get(google_id) or {"daily": {}, "leads_daily": {}}
            prev_spend, _ = sum_prev7(e["daily"], y_iso)
            entries.append({
                "name": c["name"], "source": "Google",
                "spend_y": round(e["daily"].get(y_iso, 0), 2),
                "leads_y": 0,  # Google Ads spend non porta lead via il field meta-onsite
                "prev7_spend": prev_spend,
                "prev7_leads": 0,
            })
        tiktok_id = c.get("tiktok_id")
        if tiktok_id and tiktok_map is not None and source_b == "TikTok":
            e = tiktok_map.get(tiktok_id) or {"daily": {}, "leads_daily": {}}
            prev_spend, _ = sum_prev7(e["daily"], y_iso)
            entries.append({
                "name": c["name"], "source": "TikTok",
                "spend_y": round(e["daily"].get(y_iso, 0), 2),
                "leads_y": 0,
                "prev7_spend": prev_spend,
                "prev7_leads": 0,
            })

    kpi = compute_project(entries, project_type=project_type)
    recap = build_recap(name, kpi, entries, yesterday)
    # cleanup for JSON (round)
    for e in entries:
        e["prev7_spend"] = round(e["prev7_spend"], 2)
        e["prev7_leads"] = int(e["prev7_leads"])
    return {
        "kpi": {
            "actives": kpi["actives"],
            "total": kpi["total"],
            "total_spend": round(kpi["total_spend"], 2),
            "total_leads": kpi["total_leads"],
            "cpl_y": round(kpi["cpl_y"], 2) if kpi["cpl_y"] is not None else None,
            "cpl_mean": round(kpi["cpl_mean"], 2) if kpi["cpl_mean"] is not None else None,
        },
        "entries": entries,
        "recap": recap,
    }

def _build_medtech(rows, y_iso, yesterday):
    camp_map = {}
    for r in rows:
        camp = r.get("campaign")
        if not camp or not MEDTECH_FILTER.search(camp):
            continue
        if camp not in camp_map:
            camp_map[camp] = {"daily": {}, "leads_daily": {}, "status": r.get("campaign_effective_status")}
        e = camp_map[camp]
        d = r.get("date")
        e["daily"][d] = e["daily"].get(d, 0) + float(r.get("spend") or 0)
        ld = int(r.get("actions_onsite_conversion_lead_grouped") or 0)
        if ld:
            e["leads_daily"][d] = e["leads_daily"].get(d, 0) + ld
        if r.get("campaign_effective_status"):
            e["status"] = r["campaign_effective_status"]

    entries = []
    for k, e in camp_map.items():
        prev_spend, _ = sum_prev7(e["daily"], y_iso)
        prev_leads, _ = sum_prev7(e["leads_daily"], y_iso)
        entries.append({
            "name": k, "source": e.get("status") or "",
            "spend_y": round(e["daily"].get(y_iso, 0), 2),
            "leads_y": int(e["leads_daily"].get(y_iso, 0)),
            "prev7_spend": prev_spend,
            "prev7_leads": prev_leads,
        })
    kpi = compute_project(entries, project_type="leadgen")
    recap = build_recap("Med & Tech", kpi, entries, yesterday)
    for e in entries:
        e["prev7_spend"] = round(e["prev7_spend"], 2)
        e["prev7_leads"] = int(e["prev7_leads"])
    return {
        "kpi": {
            "actives": kpi["actives"],
            "total": kpi["total"],
            "total_spend": round(kpi["total_spend"], 2),
            "total_leads": kpi["total_leads"],
            "cpl_y": round(kpi["cpl_y"], 2) if kpi["cpl_y"] is not None else None,
            "cpl_mean": round(kpi["cpl_mean"], 2) if kpi["cpl_mean"] is not None else None,
        },
        "entries": entries,
        "recap": recap,
    }

# ============================ MAIN ============================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", required=True)
    ap.add_argument("--google", required=True)
    ap.add_argument("--tiktok", required=True)
    ap.add_argument("--medtech", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    def load(path):
        with open(path, "r", encoding="utf-8") as f:
            j = json.load(f)
        return j.get("result", j) if isinstance(j, dict) else j

    meta = load(args.meta)
    google = load(args.google)
    tiktok = load(args.tiktok)
    medtech = load(args.medtech)

    data = build(meta, google, tiktok, medtech)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ wrote {args.out} ({os.path.getsize(args.out)} bytes)")
    print(f"  overview total_spend = {data['overview']['total_spend']} €")
    print(f"  overview active_accounts = {data['overview']['active_accounts']}/{data['overview']['total_accounts']}")
    print(f"  spending zero = {len(data['spending']['zero'])}, high = {len(data['spending']['high'])}")
    print(f"  beefamily entries = {len(data['beefamily']['entries'])}, alerts = {sum(1 for e in data['beefamily']['entries'] if e['status']['color'] in ('red','yellow'))}")
    print(f"  aghc entries = {len(data['aghc']['entries'])}, alerts = {sum(1 for e in data['aghc']['entries'] if e['status']['color'] in ('red','yellow'))}")
    print(f"  medtech entries = {len(data['medtech']['entries'])}, alerts = {sum(1 for e in data['medtech']['entries'] if e['status']['color'] in ('red','yellow'))}")

if __name__ == "__main__":
    main()
