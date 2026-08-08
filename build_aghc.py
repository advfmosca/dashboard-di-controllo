#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_aghc.py - Genera aghc_data.json per la Dashboard AGHC unica (aghc.html).

PERIODO BLOCCATO MENSILE (reportistica mensile): confronta un MESE di calendario
corrente vs il mese di calendario precedente. Il mese corrente puo' essere "in
corso" (MTD): in tal caso e' marcato partial=true con la data di ultimo dato.
Per le strutture con TikTok tiene i due canali (Meta / TikTok) separati.

INPUT (cartella raw/), 4 estratti Windsor aggregati PER ACCOUNT (niente campo date):
  raw/aghc_meta_current.json   raw/aghc_meta_prev.json      (connector facebook: +reach)
  raw/aghc_tiktok_current.json raw/aghc_tiktok_prev.json    (connector tiktok)

USO:
  python3 build_aghc.py --current-month 2026-08 --prev-month 2026-07 \
      --current-through 2026-08-07 --workspace .
"""

import argparse, json, os, calendar
from datetime import datetime, date

MESI_IT = ["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio",
           "agosto","settembre","ottobre","novembre","dicembre"]

def load_roster(ws):
    p = os.path.join(ws, "aghc_roster.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))["structures"]
    raise SystemExit("aghc_roster.json mancante")

def url_meta(aid):   return "https://business.facebook.com/adsmanager/manage/campaigns?act=" + str(aid)
def url_tiktok(aid): return "https://ads.tiktok.com/i18n/dashboard?aadvid=" + str(aid)

def load_rows(path):
    if not os.path.exists(path): return {}
    d = json.load(open(path, encoding="utf-8"))
    rows = d.get("result", d) if isinstance(d, dict) else d
    return {str(r.get("account_id")): r for r in rows}

def num(x):
    try: return float(x) if x is not None else 0.0
    except (TypeError, ValueError): return 0.0

def delta_pct(cur, prev):
    if not prev: return None
    return (cur - prev) / prev * 100.0

def build_metrics(cur, prev, kind):
    c_spend, p_spend = num(cur.get("spend")), num(prev.get("spend"))
    c_clk,   p_clk   = num(cur.get("clicks")), num(prev.get("clicks"))
    c_imp,   p_imp   = num(cur.get("impressions")), num(prev.get("impressions"))
    c_reach, p_reach = num(cur.get("reach")), num(prev.get("reach"))
    c_eng,   p_eng   = num(cur.get("actions_page_engagement")), num(prev.get("actions_page_engagement"))
    def cpc(s,c): return (s/c) if c else None
    def cpm(s,i): return (s/i*1000.0) if i else None
    def ctr(c,i): return (c/i*100.0) if i else None
    m = {
        "spend":       {"cur": round(c_spend,2), "prev": round(p_spend,2), "delta": delta_pct(c_spend,p_spend)},
        "impressions": {"cur": int(c_imp), "prev": int(p_imp), "delta": delta_pct(c_imp,p_imp)},
        "clicks":      {"cur": int(c_clk), "prev": int(p_clk), "delta": delta_pct(c_clk,p_clk)},
        "cpc":         {"cur": cpc(c_spend,c_clk), "prev": cpc(p_spend,p_clk),
                        "delta": delta_pct(cpc(c_spend,c_clk) or 0, cpc(p_spend,p_clk) or 0) if (c_clk and p_clk) else None},
        "cpm":         {"cur": cpm(c_spend,c_imp), "prev": cpm(p_spend,p_imp),
                        "delta": delta_pct(cpm(c_spend,c_imp) or 0, cpm(p_spend,p_imp) or 0) if (c_imp and p_imp) else None},
    }
    if kind == "meta":
        m["reach"] = {"cur": int(c_reach), "prev": int(p_reach), "delta": delta_pct(c_reach,p_reach)}
        m["interazioni"] = {"cur": int(c_eng), "prev": int(p_eng), "delta": delta_pct(c_eng,p_eng)}
        m["ctr"]   = {"cur": ctr(c_clk,c_imp), "prev": ctr(p_clk,p_imp),
                      "delta": delta_pct(ctr(c_clk,c_imp) or 0, ctr(p_clk,p_imp) or 0) if (c_imp and p_imp) else None}
    return m

def has_activity(cur, prev):
    return (num(cur.get("spend"))+num(prev.get("spend"))+num(cur.get("impressions"))+num(prev.get("impressions"))) > 0

def month_label(ym):
    y, m = ym.split("-"); return "%s %s" % (MESI_IT[int(m)-1].capitalize(), y)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--current-month", required=True, help="YYYY-MM del mese corrente")
    ap.add_argument("--prev-month", required=True, help="YYYY-MM del mese precedente")
    ap.add_argument("--current-through", default=None, help="YYYY-MM-DD ultimo giorno con dati nel mese corrente (per MTD)")
    ap.add_argument("--meta-cur", default="raw/aghc_meta_current.json")
    ap.add_argument("--meta-prev", default="raw/aghc_meta_prev.json")
    ap.add_argument("--tt-cur", default="raw/aghc_tiktok_current.json")
    ap.add_argument("--tt-prev", default="raw/aghc_tiktok_prev.json")
    ap.add_argument("--out", default="aghc_data.json")
    args = ap.parse_args()
    ws = args.workspace

    cy, cm = map(int, args.current_month.split("-"))
    last_day = calendar.monthrange(cy, cm)[1]
    through = args.current_through
    partial = False
    through_label = ""
    if through:
        td = datetime.strptime(through, "%Y-%m-%d").date()
        if td.day < last_day or (td.year, td.month) != (cy, cm):
            partial = True
            through_label = " (al %d %s)" % (td.day, MESI_IT[cm-1])

    roster = load_roster(ws)
    raw = os.path.join(ws, "raw")
    meta_cur = load_rows(os.path.join(ws, args.meta_cur))
    meta_prev = load_rows(os.path.join(ws, args.meta_prev))
    tt_cur = load_rows(os.path.join(ws, args.tt_cur))
    tt_prev = load_rows(os.path.join(ws, args.tt_prev))

    structures = []
    tot = {"meta":{"c_spend":0,"p_spend":0,"c_imp":0,"p_imp":0,"c_clk":0,"p_clk":0,"c_reach":0,"p_reach":0,"c_eng":0,"p_eng":0},
           "tiktok":{"c_spend":0,"p_spend":0,"c_imp":0,"p_imp":0,"c_clk":0,"p_clk":0}}
    for s in roster:
        entry = {"name": s["name"], "channels": {}, "notes": []}
        mid = s["meta_id"]; mc, mp = meta_cur.get(mid,{}), meta_prev.get(mid,{})
        if mid not in meta_cur and mid not in meta_prev:
            entry["notes"].append("Account Meta non collegato a Windsor: dati non disponibili.")
            entry["channels"]["meta"] = {"available": False, "url": url_meta(mid)}
        elif not has_activity(mc, mp):
            entry["channels"]["meta"] = {"available": True, "active": False, "url": url_meta(mid), "metrics": build_metrics(mc,mp,"meta")}
            entry["notes"].append("Meta: nessuna erogazione nel periodo.")
        else:
            entry["channels"]["meta"] = {"available": True, "active": True, "url": url_meta(mid), "metrics": build_metrics(mc,mp,"meta")}
            tot["meta"]["c_spend"]+=num(mc.get("spend")); tot["meta"]["p_spend"]+=num(mp.get("spend"))
            tot["meta"]["c_imp"]+=num(mc.get("impressions")); tot["meta"]["p_imp"]+=num(mp.get("impressions"))
            tot["meta"]["c_clk"]+=num(mc.get("clicks")); tot["meta"]["p_clk"]+=num(mp.get("clicks"))
            tot["meta"]["c_reach"]+=num(mc.get("reach")); tot["meta"]["p_reach"]+=num(mp.get("reach"))
            tot["meta"]["c_eng"]+=num(mc.get("actions_page_engagement")); tot["meta"]["p_eng"]+=num(mp.get("actions_page_engagement"))
        tid = s.get("tiktok_id")
        if tid:
            tc, tp = tt_cur.get(tid,{}), tt_prev.get(tid,{})
            active = has_activity(tc, tp)
            entry["channels"]["tiktok"] = {"available": True, "active": active, "url": url_tiktok(tid), "metrics": build_metrics(tc,tp,"tiktok")}
            if not active:
                entry["notes"].append("TikTok: nessuna erogazione nel periodo.")
            else:
                tot["tiktok"]["c_spend"]+=num(tc.get("spend")); tot["tiktok"]["p_spend"]+=num(tp.get("spend"))
                tot["tiktok"]["c_imp"]+=num(tc.get("impressions")); tot["tiktok"]["p_imp"]+=num(tp.get("impressions"))
                tot["tiktok"]["c_clk"]+=num(tc.get("clicks")); tot["tiktok"]["p_clk"]+=num(tp.get("clicks"))
        structures.append(entry)

    def totals_block(t, kind):
        b = {"spend":{"cur":round(t["c_spend"],2),"prev":round(t["p_spend"],2),"delta":delta_pct(t["c_spend"],t["p_spend"])},
             "impressions":{"cur":int(t["c_imp"]),"prev":int(t["p_imp"]),"delta":delta_pct(t["c_imp"],t["p_imp"])},
             "clicks":{"cur":int(t["c_clk"]),"prev":int(t["p_clk"]),"delta":delta_pct(t["c_clk"],t["p_clk"])}}
        if kind=="meta":
            b["reach"]={"cur":int(t["c_reach"]),"prev":int(t["p_reach"]),"delta":delta_pct(t["c_reach"],t["p_reach"])}
            b["interazioni"]={"cur":int(t["c_eng"]),"prev":int(t["p_eng"]),"delta":delta_pct(t["c_eng"],t["p_eng"])}
        return b

    out = {
        "schema_version": 2,
        "period_mode": "month",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "current_window": {"month": args.current_month, "label": month_label(args.current_month),
                           "through": through, "partial": partial, "through_label": through_label},
        "previous_window": {"month": args.prev_month, "label": month_label(args.prev_month), "partial": False},
        "totals": {"meta": totals_block(tot["meta"],"meta"), "tiktok": totals_block(tot["tiktok"],"tiktok")},
        "structures": structures,
    }
    with open(os.path.join(ws,args.out),"w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    n_meta = sum(1 for s in structures if s["channels"].get("meta",{}).get("active"))
    n_tt = sum(1 for s in structures if s["channels"].get("tiktok",{}).get("active"))
    print("OK -> " + args.out)
    print("  corrente:", out["current_window"]["label"] + through_label, "| precedente:", out["previous_window"]["label"], "| partial:", partial)
    print("  strutture:", len(structures), "| Meta attivi:", n_meta, "| TikTok attivi:", n_tt)
    print("  Meta spesa %.2f (prec %.2f) | TikTok spesa %.2f (prec %.2f)" % (
        out["totals"]["meta"]["spend"]["cur"], out["totals"]["meta"]["spend"]["prev"],
        out["totals"]["tiktok"]["spend"]["cur"], out["totals"]["tiktok"]["spend"]["prev"]))

if __name__ == "__main__":
    main()
