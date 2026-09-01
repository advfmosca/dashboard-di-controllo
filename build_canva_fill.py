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
    try: act={x["name"]:x for x in L("aghc_actuals_monthly.json")["structures"]}
    except Exception: act={}
    demoM=L("aghc_demographics_monthly.json")
    # il mese di riferimento è quello del REPORT (aghc_report.json), non quello di
    # aghc_data.json: quest'ultimo è scritto dal refresh quotidiano e può essere indietro,
    # facendo scivolare token di budget e demografiche sul mese sbagliato.
    def month_from_label(lbl):
        if not lbl: return None
        parts=str(lbl).split()
        if len(parts)!=2: return None
        try: return "%s-%02d"%(parts[1], MESI.index(parts[0].capitalize())+1)
        except ValueError: return None
    month=a.month or month_from_label(rep.get("month_label")) or data.get("as_of_month")
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
            if T.get("reach"): trip(T["reach"],"TT_REACH")
            else: tok["TT_REACH_ATT"]=tok["TT_REACH_PRE"]=tok["TT_REACH_CFR"]="n/d"
            trip(T["impressions"],"TT_VIEWS"); trip(T["clicks"],"TT_CLICK")
            tb=T.get("budget",{}); tok["TT_BUDGET_ATT"]=eurd(NV(tb.get("cur"))); tok["TT_BUDGET_PRE"]=eurd(NV(tb.get("prev"))); tok["TT_BUDGET_CFR"]=pct(tb.get("delta"))
            tok["RATIONAL_TT"]=f"Il canale TikTok ha generato {grp(NV(T['impressions'].get('cur')))} visualizzazioni e {grp(NV(T['clicks'].get('cur')))} click nel mese, ampliando la copertura su un pubblico complementare e più giovane."
        # budget totale periodo = meta.budget + tiktok.budget
        mb=NV(M.get("budget",{}).get("cur")) + (NV(T.get("budget",{}).get("cur")) if has_tt else 0)
        pb=NV(M.get("budget",{}).get("prev")) + (NV(T.get("budget",{}).get("prev")) if has_tt else 0)
        tok["BUDGET_TOT_ATT"]=eurd(mb); tok["BUDGET_TOT_PRE"]=eurd(pb); tok["BUDGET_TOT_CFR"]=pct(((mb-pb)/pb*100) if pb else None)
        # 12 totali mensili meta+tiktok (da budget.monthly_real del cliente)
        b=bud.get(name,{}); mr=list(b.get("monthly_real",[0]*12)); plan=b.get("monthly_plan",[0]*12)
        # split per canale dagli actuals; il MESE DI REPORT viene sovrascritto con i valori
        # autoritativi di aghc_report.json (gli actuals sono aggiornati dal refresh quotidiano
        # e possono mancare gli ultimi giorni del mese -> pagina Budget incoerente con Meta/TikTok)
        A=act.get(name,{}); mon=A.get("monthly",{})
        mmeta=list(mon.get("meta",[0]*12)); mtt=list(mon.get("tiktok",[0]*12))
        for L_ in (mr,mmeta,mtt):
            while len(L_)<12: L_.append(0.0)
        i0=mm-1
        if 0<=i0<12:
            mmeta[i0]=NV(M.get("budget",{}).get("cur"))
            mtt[i0]=NV(T.get("budget",{}).get("cur")) if has_tt else 0.0
            mr[i0]=mmeta[i0]+mtt[i0]
        for i in range(12):
            tok[f"TOT_{MABBR[i].upper()}"]=eurd(NV(mr[i]))
            tok[f"META_{MABBR[i].upper()}"]=eurd(NV(mmeta[i]))
            tok[f"TT_{MABBR[i].upper()}"]=eurd(NV(mtt[i])) if has_tt else "0,00 €"
        annuo=NV(A.get("budget_annuale")) or NV(b.get("budget_annuale"))
        speso=sum(NV(x) for x in mr)
        tok["BUD_ANNUO"]=eurd(annuo); tok["TOT_SPESO"]=eurd(speso)
        tok["TOT_RESIDUO"]=eurd(max(annuo-speso,0))
        # grafico budget pag.6: mesi chiusi (fino a mese report)
        chart={"labels":MABBR[:mm],"programmato":[round(NV(plan[i]),2) for i in range(mm)],"speso":[round(NV(mr[i]),2) for i in range(mm)]}
        # demografiche pag.7
        dblk=demo.get(name)
        out["clients"][name]={"has_tiktok":has_tt,"tokens":tok,"budget_chart":chart,"demographics":dblk}
    json.dump(out,open(os.path.join(W,"canva_fill.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=0)
    ntt=sum(1 for k,v in out["clients"].items() if v["has_tiktok"]); nd=sum(1 for v in out["clients"].values() if v["demographics"])
    print(f"OK canva_fill.json — clienti:{len(out['clients'])} con TikTok:{ntt} con demo:{nd} mese:{mlabel}")
if __name__=="__main__": main()
