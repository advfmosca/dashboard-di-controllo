#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_actuals_monthly.py — speso reale mensile YTD per struttura (Meta+TikTok).
Input:  aghc_roster.json, raw/aghc_monthly_meta.json, raw/aghc_monthly_tiktok.json
Output: aghc_actuals_monthly.json  { year, updated, structures:[{name, meta_id, monthly:{meta:[12], tiktok:[12], total:[12]}, ytd:{...}}] }
"""
import json, os, sys
from datetime import datetime

WS = sys.argv[1] if len(sys.argv) > 1 else "."

def load(p):
    with open(os.path.join(WS, p), encoding="utf-8") as f:
        d = json.load(f)
    return d.get("result", d) if isinstance(d, dict) else d

roster = json.load(open(os.path.join(WS, "aghc_roster.json"), encoding="utf-8"))["structures"]
meta_rows = load("raw/aghc_monthly_meta.json")
tt_rows   = load("raw/aghc_monthly_tiktok.json")

def by_acct(rows):
    m = {}
    for r in rows:
        aid = str(r.get("account_id"))
        ym = r.get("year_month", "")
        try:
            mon = int(ym.split("|")[1])
        except (IndexError, ValueError):
            continue
        m.setdefault(aid, [0.0]*12)
        if 1 <= mon <= 12:
            m[aid][mon-1] += float(r.get("spend") or 0)
    return m

meta_m = by_acct(meta_rows)
tt_m   = by_acct(tt_rows)

out = {"year": 2026, "updated": datetime.now().strftime("%Y-%m-%d %H:%M"), "structures": []}
for s in roster:
    mm = meta_m.get(s["meta_id"], [0.0]*12)
    tm = tt_m.get(s["tiktok_id"], [0.0]*12) if s.get("tiktok_id") else [0.0]*12
    total = [round(mm[i]+tm[i], 2) for i in range(12)]
    out["structures"].append({
        "name": s["name"], "meta_id": s["meta_id"], "has_tiktok": bool(s.get("tiktok_id")),
        "budget_annuale": s["budget_annuale"],
        "monthly": {"meta": [round(x,2) for x in mm], "tiktok": [round(x,2) for x in tm], "total": total},
        "ytd_total": round(sum(total), 2), "ytd_meta": round(sum(mm), 2), "ytd_tiktok": round(sum(tm), 2),
    })

with open(os.path.join(WS, "aghc_actuals_monthly.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("OK -> aghc_actuals_monthly.json")
tot = sum(s["ytd_total"] for s in out["structures"])
print("  YTD totale portfolio (gen-ago): %.2f EUR" % tot)
for s in out["structures"][:3]:
    print("  ", s["name"], "YTD", s["ytd_total"], "€ | annuale", s["budget_annuale"])
