#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_aghc.py - Genera aghc_data.json per la Dashboard AGHC unica (aghc.html).

Confronta i KPI di una finestra corrente (default 30 giorni, fino a ieri) con la
finestra IMMEDIATAMENTE precedente della stessa ampiezza. Per le strutture con
TikTok tiene i due canali (Meta / TikTok) separati.

INPUT (cartella raw/), estratti da Windsor.ai per le due finestre:
  raw/aghc_meta_current.json   raw/aghc_meta_prev.json      (connector facebook)
  raw/aghc_tiktok_current.json raw/aghc_tiktok_prev.json    (connector tiktok)
Ogni file ha forma {"result": [ {account_id, account_name, spend, clicks,
impressions, [reach], ...}, ... ]} aggregato per account sull'intera finestra.

USO:
  python3 build_aghc.py --window-days 30 --ref-date 2026-08-07 --workspace .
"""

import argparse, json, os
from datetime import datetime, timedelta

MONTHS_IT = ["gen","feb","mar","apr","mag","giu","lug","ago","set","ott","nov","dic"]

ROSTER = [
    {"name": "Accentodì + Adèsso",       "meta_id": "1312718426033158",  "tiktok_id": None},
    {"name": "Altafiumara Resort",              "meta_id": "1201395876543423",  "tiktok_id": None},
    {"name": "Hotel Castello",                  "meta_id": "1489903155429629",  "tiktok_id": None},
    {"name": "Hotel Della Piana",               "meta_id": "911357333863123",   "tiktok_id": "7504967007843319824"},
    {"name": "Hannah Hotels Collection",        "meta_id": "1528485957725509",  "tiktok_id": None},
    {"name": "Hemanaire",                       "meta_id": "217115315497718",   "tiktok_id": None},
    {"name": "Livata",                          "meta_id": "4666471140299701",  "tiktok_id": None},
    {"name": "Hotel Lunetta",                   "meta_id": "687349689221880",   "tiktok_id": "7498330316248203280"},
    {"name": "Magari Estates",                  "meta_id": "1372615496521110",  "tiktok_id": None},
    {"name": "Marcella Royal + Terrazza Flavia","meta_id": "821188209852436",   "tiktok_id": "7499093699838607377"},
    {"name": "Mare Hotel",                      "meta_id": "1432341844596179",  "tiktok_id": "7498679494010667009"},
    {"name": "Tenuta Montemagno Relais",        "meta_id": "752450855779035",   "tiktok_id": None},
    {"name": "Villa Ermellina",                 "meta_id": "30233607946222961", "tiktok_id": "7612666695502118929"},
    {"name": "Villa Giada",                     "meta_id": "1849759899186169",  "tiktok_id": "7626418949391351815"},
    {"name": "Villa Miliani",                   "meta_id": "1353024533007038",  "tiktok_id": None},
]

def url_meta(aid):   return "https://business.facebook.com/adsmanager/manage/campaigns?act=" + str(aid)
def url_tiktok(aid): return "https://ads.tiktok.com/i18n/dashboard?aadvid=" + str(aid)
def date_label_it(d): return "%d %s %d" % (d.day, MONTHS_IT[d.month-1], d.year)

def load_rows(path):
    if not os.path.exists(path): return {}
    with open(path, encoding="utf-8") as f: payload = json.load(f)
    rows = payload.get("result", payload) if isinstance(payload, dict) else payload
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
        m["ctr"]   = {"cur": ctr(c_clk,c_imp), "prev": ctr(p_clk,p_imp),
                      "delta": delta_pct(ctr(c_clk,c_imp) or 0, ctr(p_clk,p_imp) or 0) if (c_imp and p_imp) else None}
    return m

def has_activity(cur, prev):
    return (num(cur.get("spend"))+num(prev.get("spend"))+num(cur.get("impressions"))+num(prev.get("impressions"))) > 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--ref-date", default=None)
    args = ap.parse_args()
    ws, wd = args.workspace, args.window_days
    ref = datetime.strptime(args.ref_date, "%Y-%m-%d").date() if args.ref_date else (datetime.now().date()-timedelta(days=1))
    cur_end = ref; cur_start = ref - timedelta(days=wd-1)
    prev_end = cur_start - timedelta(days=1); prev_start = prev_end - timedelta(days=wd-1)
    raw = os.path.join(ws, "raw")
    meta_cur = load_rows(os.path.join(raw,"aghc_meta_current.json"))
    meta_prev = load_rows(os.path.join(raw,"aghc_meta_prev.json"))
    tt_cur = load_rows(os.path.join(raw,"aghc_tiktok_current.json"))
    tt_prev = load_rows(os.path.join(raw,"aghc_tiktok_prev.json"))
    structures = []
    tot = {"meta":{"c_spend":0,"p_spend":0,"c_imp":0,"p_imp":0,"c_clk":0,"p_clk":0,"c_reach":0,"p_reach":0},
           "tiktok":{"c_spend":0,"p_spend":0,"c_imp":0,"p_imp":0,"c_clk":0,"p_clk":0}}
    for s in ROSTER:
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
        tid = s["tiktok_id"]
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
        if kind=="meta": b["reach"]={"cur":int(t["c_reach"]),"prev":int(t["p_reach"]),"delta":delta_pct(t["c_reach"],t["p_reach"])}
        return b
    out = {
        "schema_version": 1,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "window_days": wd,
        "current_window": {"start":cur_start.isoformat(),"end":cur_end.isoformat(),"label":date_label_it(cur_start)+" – "+date_label_it(cur_end)},
        "previous_window": {"start":prev_start.isoformat(),"end":prev_end.isoformat(),"label":date_label_it(prev_start)+" – "+date_label_it(prev_end)},
        "totals": {"meta": totals_block(tot["meta"],"meta"), "tiktok": totals_block(tot["tiktok"],"tiktok")},
        "structures": structures,
    }
    with open(os.path.join(ws,"aghc_data.json"),"w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    n_meta = sum(1 for s in structures if s["channels"].get("meta",{}).get("active"))
    n_tt = sum(1 for s in structures if s["channels"].get("tiktok",{}).get("active"))
    print("OK -> aghc_data.json")
    print("  finestra corrente:", out["current_window"]["label"], "(%dgg)" % wd)
    print("  finestra prec.:   ", out["previous_window"]["label"])
    print("  strutture:", len(structures), "| Meta attivi:", n_meta, "| TikTok attivi:", n_tt)
    print("  spesa Meta %.2f EUR (prec %.2f)" % (out["totals"]["meta"]["spend"]["cur"], out["totals"]["meta"]["spend"]["prev"]))
    print("  spesa TikTok %.2f EUR (prec %.2f)" % (out["totals"]["tiktok"]["spend"]["cur"], out["totals"]["tiktok"]["spend"]["prev"]))

if __name__ == "__main__":
    main()
