#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_report.py — Report mensile cliente AGHC (5 tabelle split IG/FB + TikTok + rational).

Confronto:
  --comparison mom  → mese chiuso vs mese precedente (raw rep_*_prev).
  --comparison yoy  → mese chiuso vs stesso mese anno prec. dallo STORICO (history/AAAA-MM.json).
                      Per i clienti senza snapshot YoY → fallback automatico a MoM (flag per-cliente).
Lo split IG/FB via API è disponibile solo entro 13 mesi: lo YoY funziona sui mesi "congelati"
in history/ dal banking mensile (snapshot_history.py).

Input raw/: rep_meta_acct_cur/prev.json, rep_meta_camp_cur/prev.json, aghc_report_tt_month/prev.json
Storico:    history/AAAA-MM.json (per --comparison yoy, via --history-prev)
Output:     aghc_report.json
"""
import argparse, json, os, datetime
from aghc_report_lib import CLIENTS, load_raw, bucket, n, dpct, cell

def fmt_int(v): return ("{:,}".format(int(round(v)))).replace(",",".")
def fmt_eur(v): return ("{:,.2f}".format(v)).replace(",","§").replace(".",",").replace("§",".")+" €"

def rational(cur, prev, tt_cur_imp, tt_prev_imp):
    tsc=cur["ig"]["spend"]+cur["fb"]["spend"]; tsp=prev["ig"]["spend"]+prev["fb"]["spend"]
    reach_c=cur["ig"]["reach"]+cur["fb"]["reach"]; reach_p=prev["ig"]["reach"]+prev["fb"]["reach"]
    eng_c=cur["ig"]["eng"]+cur["fb"]["eng"]; eng_p=prev["ig"]["eng"]+prev["fb"]["eng"]
    clk_c=cur["ig"]["clk"]+cur["fb"]["clk"]
    bd=dpct(tsc,tsp)
    if bd is None: op="Il mese si chiude con un presidio Meta costante"
    elif bd>=5: op="Il mese si apre con un budget in crescita (%+d%%)"%bd
    elif bd<=-5: op="Il mese registra una ricalibrazione del budget (%+d%%)"%bd
    else: op="Il mese si chiude con un budget sostanzialmente stabile (%+d%%)"%(bd or 0)
    parts=[op+" e una spesa complessiva di %s."%fmt_eur(tsc)]
    grown=[]; ed=dpct(eng_c,eng_p); rd=dpct(reach_c,reach_p)
    if ed is not None and ed>=5: grown.append("le interazioni su Meta crescono del %+d%% (%s)"%(ed,fmt_int(eng_c)))
    if rd is not None and rd>=5: grown.append("la copertura sale del %+d%%"%rd)
    if grown: parts.append("Sul fronte engagement "+" e ".join(grown)+", segnale di un pubblico sempre più coinvolto e in target.")
    else: parts.append("L'attività mantiene un presidio qualificato, con ampia efficienza per euro investito: con %s l'algoritmo Meta ha generato oltre %s clic verso le destinazioni del brand."%(fmt_eur(tsc),fmt_int(clk_c)))
    if (rd is not None and rd<0) or (ed is not None and ed<0):
        parts.append("Le variazioni in flessione si inseriscono in uno scenario di aumento generalizzato dei costi pubblicitari Meta e di crescente competitività nel comparto ricettivo, che ha reso più selettiva l'erogazione sui pubblici a maggior valore.")
    if tt_cur_imp:
        ttd=dpct(tt_cur_imp,tt_prev_imp or 0)
        parts.append("Il canale TikTok ha contribuito con %s visualizzazioni%s, ampliando la copertura su un pubblico più giovane e complementare."%(fmt_int(tt_cur_imp),(" (%+d%%)"%ttd if ttd is not None else "")))
    parts.append("Una base solida ed efficiente da cui costruire le prossime finestre ad alto peso del piano annuale.")
    return " ".join(parts)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",default=".")
    ap.add_argument("--month-label",required=True); ap.add_argument("--prev-label",required=True)
    ap.add_argument("--comparison",choices=["mom","yoy"],default="mom")
    ap.add_argument("--history-prev",default=None,help="path history/AAAA-MM.json per YoY")
    a=ap.parse_args(); ws=a.workspace
    ma=load_raw(ws,"rep_meta_acct_cur.json"); ca=load_raw(ws,"rep_meta_camp_cur.json")
    mp=load_raw(ws,"rep_meta_acct_prev.json"); cp=load_raw(ws,"rep_meta_camp_prev.json")
    tt_c={str(r["account_id"]):r for r in load_raw(ws,"aghc_report_tt_month.json")}
    tt_p={str(r["account_id"]):r for r in load_raw(ws,"aghc_report_tt_prev.json")}
    hist=None
    if a.comparison=="yoy" and a.history_prev and os.path.exists(os.path.join(ws,a.history_prev)):
        hist=json.load(open(os.path.join(ws,a.history_prev),encoding="utf-8")).get("clients",{})

    clients=[]; fell_back=0
    for name,acct,camp,ttid in CLIENTS:
        cur=bucket(ca if camp else ma, acct, camp)
        cmp_used=a.comparison
        if a.comparison=="yoy" and hist and name in hist and hist[name].get("meta"):
            prev=hist[name]["meta"]
            for k in ("ig","fb"):
                prev.setdefault(k,{}); 
                for f in ("reach","impr","eng","clk","spend"): prev[k].setdefault(f,0)
            tt_prev_imp=(hist[name].get("tiktok") or {}).get("impressions",0)
        else:
            if a.comparison=="yoy": cmp_used="mom"; fell_back+=1
            prev=bucket(cp if camp else mp, acct, camp)
            tt_prev_imp=n((tt_p.get(ttid) or {}).get("impressions")) if ttid else 0
        active=(cur["ig"]["spend"]+cur["fb"]["spend"]+cur["ig"]["impr"]+cur["fb"]["impr"])>0
        e={"name":name,"comparison_used":cmp_used}
        if not active: e["meta"]={"available":False}
        else:
            def tbl(k): return {"ig":cell(cur["ig"][k],prev["ig"][k]),"fb":cell(cur["fb"][k],prev["fb"][k])}
            tsc=cur["ig"]["spend"]+cur["fb"]["spend"]; tsp=prev["ig"]["spend"]+prev["fb"]["spend"]
            e["meta"]={"available":True,"reach":tbl("reach"),"impressions":tbl("impr"),
                       "engagement":tbl("eng"),"clicks":tbl("clk"),
                       "budget":{"cur":round(tsc,2),"prev":round(tsp,2),"delta":dpct(tsc,tsp)}}
        ttc=tt_c.get(ttid) if ttid else None
        if ttid:
            if ttc and (n(ttc.get("spend"))+n(ttc.get("impressions"))>0):
                e["tiktok"]={"available":True,
                    "impressions":cell(n(ttc.get("impressions")),tt_prev_imp),
                    "clicks":cell(n(ttc.get("clicks")), n((tt_p.get(ttid) or {}).get("clicks")) if a.comparison=="mom" else (hist.get(name,{}).get("tiktok",{}).get("clicks",0) if hist else 0)),
                    "budget":{"cur":round(n(ttc.get("spend")),2),
                              "prev":round((hist.get(name,{}).get("tiktok",{}).get("spend",0) if (a.comparison=="yoy" and hist) else n((tt_p.get(ttid) or {}).get("spend"))),2),
                              "delta":None}}
                b=e["tiktok"]["budget"]; b["delta"]=dpct(b["cur"],b["prev"])
            else: e["tiktok"]={"available":False}
        e["rational"]=rational(cur,prev, n(ttc.get("impressions")) if ttc else 0, tt_prev_imp) if active else ""
        clients.append(e)

    out={"schema_version":2,"generated_at":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
         "comparison":a.comparison.upper(),"month_label":a.month_label,"prev_label":a.prev_label,
         "yoy_fallbacks":fell_back,"clients":clients}
    json.dump(out,open(os.path.join(ws,"aghc_report.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    na=sum(1 for c in clients if c["meta"].get("available"))
    print("OK -> aghc_report.json | %s %s vs %s | attivi %d/%d | fallback MoM(su YoY): %d"%(
        out["comparison"],a.month_label,a.prev_label,na,len(clients),fell_back))

if __name__=="__main__": main()
