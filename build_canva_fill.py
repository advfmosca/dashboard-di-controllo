#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_canva_fill.py — per ogni cliente AGHC produce il fill-map per il template Canva nativo
(DAHR1ubVbvk): token pagina Meta/TikTok/Budget + dati grafico budget (pag.6) + demografiche (pag.7).
Legge aghc_report.json (KPI IG/FB + TikTok + rational), aghc_data.json (budget mensile),
aghc_demographics_monthly.json. Output: canva_fill.json  (dict per cliente).
Uso: python3 build_canva_fill.py --workspace . [--month 2026-07]"""
import argparse, json, os
MESI=["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
MABBR=["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]
def grp(n):  # 1234567 -> 1.234.567
    return format(int(round(n)),",d").replace(",",".")
def eur(n): return grp(n)+" €"
def eurd(n): # 1234.5 -> 1.234,50 €
    s=format(float(n),",.2f"); s=s.replace(",","§").replace(".",",").replace("§","."); return s+" €"
def pct(d):
    if d is None: return "n/d"
    return ("+" if d>=0 else "")+str(int(round(d)))+"%"
def NV(x): return x if x is not None else 0
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workspace",default="."); ap.add_argument("--month",default=None); a=ap.parse_args()
    W=a.workspace; L=lambda n: json.load(open(os.path.join(W,n),encoding="utf-8"))
    rep=L("aghc_report.json"); data=L("aghc_data.json")
    demoM=L("aghc_demographics_monthly.json")
    month=a.month or data.get("as_of_month")
    ym=month; mm=int(ym.split("-")[1])
    bud={s["name"]:s.get("budget",{}) for s in data["structures"]}
    demo=demoM.get("by_month",{}).get(ym,{})
    mlabel=rep.get("month_label"); plabel=rep.get("prev_label")
    out={"schema_version":1,"month":ym,"month_label":mlabel,"clients":{}}
    for c in rep["clients"]:
        name=c["name"]; M=c.get("meta",{}); T=c.get("tiktok",{}); has_tt=bool(T.get("available"))
        tok={"NOME_CLIENTE":name,"MESE_META":(c.get("meta_period_label") or f"{mlabel} vs {plabel}"),"MESE_TT":(c.get("tt_period_label") or f"{mlabel} vs {plabel}"),
             "FOLL_IG_DELTA":"n/d","FOLL_IG_TOT":"n/d","FOLL_FB_DELTA":"n/d","FOLL_FB_TOT":"n/d","FOLL_TT_DELTA":"n/d","FOLL_TT_TOT":"n/d"}
        def trip(blk,pre,fmt=grp):
            tok[pre+"_ATT"]=fmt(NV(blk.get("cur"))); tok[pre+"_PRE"]=fmt(NV(blk.get("prev"))); tok[pre+"_CFR"]=pct(blk.get("delta"))
        if M.get("available"):
            for dim,pre in [("reach","REACH"),("impressions","VIEWS"),("engagement","INTER"),("clicks","CLICK")]:
                trip(M[dim]["ig"],pre+"_IG"); trip(M[dim]["fb"],pre+"_FB")
            b=M.get("budget",{}); tok["BUDGET_ATT"]=eurd(NV(b.get("cur"))); tok["BUDGET_PRE"]=eurd(NV(b.get("prev"))); tok["BUDGET_CFR"]=pct(b.get("delta"))
        tok["RATIONAL_META"]=c.get("rational","")
        if has_tt:
            tok["TT_REACH_ATT"]=tok["TT_REACH_PRE"]="n/d"; tok["TT_REACH_CFR"]="n/d"  # TikTok non espone reach
            trip(T["impressions"],"TT_VIEWS"); trip(T["clicks"],"TT_CLICK")
            tb=T.get("budget",{}); tok["TT_BUDGET_ATT"]=eurd(NV(tb.get("cur"))); tok["TT_BUDGET_PRE"]=eurd(NV(tb.get("prev"))); tok["TT_BUDGET_CFR"]=pct(tb.get("delta"))
            tok["RATIONAL_TT"]=f"Il canale TikTok ha generato {grp(NV(T['impressions'].get('cur')))} visualizzazioni e {grp(NV(T['clicks'].get('cur')))} click nel mese, ampliando la copertura su un pubblico complementare e più giovane."
        # budget totale periodo = meta.budget + tiktok.budget
        mb=NV(M.get("budget",{}).get("cur")) + (NV(T.get("budget",{}).get("cur")) if has_tt else 0)
        pb=NV(M.get("budget",{}).get("prev")) + (NV(T.get("budget",{}).get("prev")) if has_tt else 0)
        tok["BUDGET_TOT_ATT"]=eurd(mb); tok["BUDGET_TOT_PRE"]=eurd(pb); tok["BUDGET_TOT_CFR"]=pct(((mb-pb)/pb*100) if pb else None)
        # 12 totali mensili meta+tiktok (da budget.monthly_real del cliente)
        b=bud.get(name,{}); mr=b.get("monthly_real",[0]*12); plan=b.get("monthly_plan",[0]*12)
        for i in range(12): tok[f"TOT_{MABBR[i].upper()}"]=eurd(NV(mr[i]) if i<len(mr) else 0)
        # grafico budget pag.6: mesi chiusi (fino a mese report)
        chart={"labels":MABBR[:mm],"programmato":[round(NV(plan[i]),2) for i in range(mm)],"speso":[round(NV(mr[i]),2) for i in range(mm)]}
        # demografiche pag.7
        dblk=demo.get(name)
        out["clients"][name]={"has_tiktok":has_tt,"tokens":tok,"budget_chart":chart,"demographics":dblk}
    json.dump(out,open(os.path.join(W,"canva_fill.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=0)
    ntt=sum(1 for k,v in out["clients"].items() if v["has_tiktok"]); nd=sum(1 for v in out["clients"].values() if v["demographics"])
    print(f"OK canva_fill.json — clienti:{len(out['clients'])} con TikTok:{ntt} con demo:{nd} mese:{mlabel}")
if __name__=="__main__": main()
