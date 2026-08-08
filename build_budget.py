#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_budget.py — Modulo budget AGHC.

PROGRAMMATO = budget annuale (aghc_roster.json, autorevole) ripartito sui mesi con i
PESI STAGIONALI UFFICIALI (doc AGHC_Report_Mensile_Istruzioni):
  Gen 3 · Feb 3 · Mar 5 · Apr 10 · Mag 15 · Giu 15 · Lug 12 · Ago 12 · Set 5 · Ott 5 · Nov 5 · Dic 10 (%)
Split canali 80% Meta / 20% TikTok per i clienti con entrambi i canali.

- monthly_plan[m]  = annuale * peso[m]        (programmato stagionale)
- monthly_real[m]  = speso reale (mesi chiusi bloccati)
- monthly_recal[m] = reale nei mesi chiusi + residuo (annuale − reale YTD) ridistribuito
                     sui mesi RIMANENTI secondo i pesi rimanenti rinormalizzati
                     (ricalibrazione: recupero/rientro per chiudere sull'annuale).
- pace vs plan-to-date (somma pesi fino ad as_of), proiezione a fine anno al ritmo YTD.

Input:  aghc_roster.json, aghc_actuals_monthly.json, [aghc_budget_ops.json]
Output: aghc_budget.json
Uso:    python3 build_budget.py --as-of-month 2026-07 --workspace .
"""
import argparse, json, os
from datetime import datetime

MESI = ["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]
WEIGHTS = [0.03,0.03,0.05,0.10,0.15,0.15,0.12,0.12,0.05,0.05,0.05,0.10]  # pesi ufficiali AGHC
META_SHARE, TT_SHARE = 0.80, 0.20

def load(ws,p,req=True):
    fp=os.path.join(ws,p)
    if not os.path.exists(fp):
        if req: raise SystemExit(p+" mancante")
        return None
    return json.load(open(fp,encoding="utf-8"))

def r2(x): return round(float(x)+0.0,2)
def delta_pct(c,p): return ((c-p)/p*100.0) if p else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",default=".")
    ap.add_argument("--as-of-month",required=True)
    ap.add_argument("--pace-tol",type=float,default=12.0)
    a=ap.parse_args(); ws=a.workspace
    roster={s["name"]:s for s in load(ws,"aghc_roster.json")["structures"]}
    actuals={s["name"]:s for s in load(ws,"aghc_actuals_monthly.json")["structures"]}
    ops=(load(ws,"aghc_budget_ops.json",req=False) or {})
    wmap=ops.get("weights",{}); annualmap=ops.get("annual",{})

    ay,am=map(int,a.as_of_month.split("-")); as_of=am
    rem=list(range(as_of,12))

    out={"schema_version":3,"year":ay,"generated_at":datetime.now().strftime("%Y-%m-%d %H:%M"),
         "as_of_month":a.as_of_month,"as_of_label":MESI[as_of-1]+" "+str(ay),
         "weights":WEIGHTS,"channel_split":{"meta":META_SHARE,"tiktok":TT_SHARE},
         "method":("Programmato = annuale (roster) × pesi stagionali ufficiali. Ricalibrazione = residuo verso l'annuale "
                   "ridistribuito sui mesi rimanenti secondo i pesi. Split canali 80% Meta / 20% TikTok."),
         "structures":[],"totals":{}}
    T={"annual":0.0,"ytd":0.0,"plan_td":0.0,"proj":0.0,"resid":0.0,
       "m_plan":[0.0]*12,"m_real":[0.0]*12,"m_recal":[0.0]*12,"q_plan":[0,0,0,0],"q_real":[0,0,0,0]}

    for name,s in roster.items():
        annual=float(annualmap.get(name, s["budget_annuale"]))
        w=wmap.get(name, WEIGHTS)
        if len(w)!=12 or abs(sum(w)-1.0)>0.001: w=WEIGHTS
        act=actuals.get(name,{})
        real=[float(x or 0) for x in (list(act.get("monthly",{}).get("total",[]))+[0.0]*12)[:12]]
        plan=[r2(annual*w[i]) for i in range(12)]
        ytd=sum(real[:as_of]); plan_td=sum(plan[:as_of])
        residual=max(annual-ytd,0.0)
        rw=[w[i] for i in rem]; srw=sum(rw) or 1.0
        recal=list(real)
        for i in rem: recal[i]=r2(residual*w[i]/srw)
        if rem:
            drift=r2(annual-(ytd+sum(recal[i] for i in rem))); recal[rem[-1]]=r2(max(recal[rem[-1]]+drift,0.0))
        pace=delta_pct(ytd,plan_td)
        proj=ytd/as_of*12.0 if as_of else 0.0
        fwd=r2(residual/len(rem)) if rem else 0.0
        has_tt=act.get("has_tiktok",False)
        status=("over" if (pace is not None and pace>a.pace_tol) else
                "under" if (pace is not None and pace<-a.pace_tol) else
                "on_track" if pace is not None else "na")
        if annual==0: status="inactive"
        def q(v,i): return r2(sum(v[i*3:i*3+3]))
        out["structures"].append({
            "name":name,"has_tiktok":has_tt,"annual":r2(annual),
            "channel_annual":{"meta":r2(annual*(META_SHARE if has_tt else 1.0)),
                               "tiktok":r2(annual*TT_SHARE) if has_tt else 0.0},
            "ytd_real":r2(ytd),"ytd_meta":r2(act.get("ytd_meta",0)),"ytd_tiktok":r2(act.get("ytd_tiktok",0)),
            "plan_to_date":r2(plan_td),"pace_delta":r2(ytd-plan_td),"pace_pct":(r2(pace) if pace is not None else None),
            "residual":r2(residual),"fwd_recal_monthly":fwd,"remaining_months":len(rem),
            "projection_year_end":r2(proj),"projection_delta":r2(proj-annual),"status":status,
            "monthly_plan":plan,"monthly_real":[r2(x) for x in real],"monthly_recal":recal,
            "quarter_plan":[q(plan,i) for i in range(4)],"quarter_real":[q(real,i) for i in range(4)],
        })
        T["annual"]+=annual;T["ytd"]+=ytd;T["plan_td"]+=plan_td;T["proj"]+=proj;T["resid"]+=residual
        for i in range(12): T["m_plan"][i]+=plan[i];T["m_real"][i]+=real[i];T["m_recal"][i]+=recal[i]
        for i in range(4): T["q_plan"][i]+=q(plan,i);T["q_real"][i]+=q(real,i)

    out["totals"]={"annual":r2(T["annual"]),"ytd_real":r2(T["ytd"]),"plan_to_date":r2(T["plan_td"]),
                   "residual":r2(T["resid"]),"projection_year_end":r2(T["proj"]),
                   "monthly_plan":[r2(x) for x in T["m_plan"]],"monthly_real":[r2(x) for x in T["m_real"]],
                   "monthly_recal":[r2(x) for x in T["m_recal"]],
                   "quarter_plan":[r2(x) for x in T["q_plan"]],"quarter_real":[r2(x) for x in T["q_real"]]}
    json.dump(out,open(os.path.join(ws,"aghc_budget.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    t=out["totals"]
    print("OK -> aghc_budget.json (pesi ufficiali, as_of %s)"%out["as_of_label"])
    print("  Portfolio annuale %.0f € | programmato a %s %.0f € | reale YTD %.0f € | proiezione %.0f €"%(
        t["annual"],out["as_of_label"],t["plan_to_date"],t["ytd_real"],t["projection_year_end"]))
    for s in out["structures"][:4]:
        print("  - %-30s ann %6.0f | plan-to-date %6.0f | YTD %6.0f | pace %s | recal/mese %5.0f"%(
            s["name"],s["annual"],s["plan_to_date"],s["ytd_real"],
            (("%+.0f%%"%s["pace_pct"]) if s["pace_pct"] is not None else "n/d"),s["fwd_recal_monthly"]))

if __name__=="__main__": main()
