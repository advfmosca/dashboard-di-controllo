#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_daily.py — aghc_daily.json: serie giornaliere per struttura, spezzate per mese.
Legge raw/daily_meta_full.json (account), raw/daily_meta_camp_full.json (campagne condivise),
raw/daily_tt_full.json (tiktok). Uso: python3 build_daily.py --workspace ."""
import argparse, json, os
from datetime import date
# name, meta_acct, camp_inc, camp_exc, tt_acct
STRUCTS=[
 ("Altafiumara Resort","1201395876543423",None,[],None),
 ("Hotel Castello","1489903155429629",None,[],None),
 ("Hotel Della Piana","911357333863123",None,[],"7504967007843319824"),
 ("Hannah Hotels","1528485957725509","hannah",["terraces","puntebianche"],None),
 ("Puntebianche Resort","1528485957725509","puntebianche",[],None),
 ("Hemanaire","217115315497718",None,[],None),
 ("Livata","4666471140299701",None,[],None),
 ("Hotel Lunetta","687349689221880",None,[],"7498330316248203280"),
 ("Magari Estates","1372615496521110",None,[],None),
 ("Marcella Royal Hotel","821188209852436","marcella",[],"7499093699838607377"),
 ("Terrazza Flavia","821188209852436","terrazza",[],None),
 ("Mare Hotel","1432341844596179",None,[],"7498679494010667009"),
 ("Tenuta Montemagno Relais","752450855779035",None,[],None),
 ("Villa Ermellina","30233607946222961",None,[],"7612666695502118929"),
 ("Villa Giada","1849759899186169",None,[],"7626418949391351815"),
 ("Villa Miliani","1353024533007038",None,[],None),
]
def num(x):
    try: return float(x) if x is not None else 0.0
    except (TypeError,ValueError): return 0.0
def load(p):
    if not os.path.exists(p): return []
    d=json.load(open(p,encoding="utf-8")); return d.get("result",d) if isinstance(d,dict) else d
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workspace",default="."); a=ap.parse_args()
    W=a.workspace; R=lambda n: os.path.join(W,"raw",n)
    hist=json.load(open(os.path.join(W,"aghc_history.json"),encoding="utf-8"))
    months=hist["months"]
    mrows=load(R("daily_meta_full.json")); crows=load(R("daily_meta_camp_full.json")); trows=load(R("daily_tt_full.json"))
    def meta_days(acct,kw,exc):
        agg={}
        src=mrows if kw is None else crows
        for r in src:
            if str(r.get("account_id"))!=acct: continue
            if kw is not None:
                c=str(r.get("campaign","")).lower()
                if kw not in c or any(x in c for x in exc): continue
            dt=r.get("date");
            if not dt: continue
            e=agg.setdefault(dt,{"spend":0.0,"reach":0.0,"impressions":0.0,"interazioni":0.0,"clicks":0.0})
            e["spend"]+=num(r.get("spend")); e["reach"]+=num(r.get("reach"))
            e["impressions"]+=num(r.get("impressions")); e["interazioni"]+=num(r.get("actions_page_engagement"))
            e["clicks"]+=num(r.get("clicks"))
        return agg
    def tt_days(acct):
        if not acct: return {}
        agg={}
        for r in trows:
            if str(r.get("account_id"))!=acct: continue
            dt=r.get("date")
            if not dt: continue
            e=agg.setdefault(dt,{"spend":0.0,"impressions":0.0,"clicks":0.0})
            e["spend"]+=num(r.get("spend")); e["impressions"]+=num(r.get("impressions")); e["clicks"]+=num(r.get("engagements"))
        return agg
    structs=[]
    for name,acct,kw,exc,tt in STRUCTS:
        md=meta_days(acct,kw,exc); td=tt_days(tt)
        days={}
        alldates=set(md)|set(td)
        bym={}
        for dt in alldates: bym.setdefault(dt[:7],[]).append(dt)
        for ym in months:
            ds=sorted(bym.get(ym,[]))
            if not ds: continue
            M={k:[] for k in ("spend","reach","impressions","interazioni","clicks")}
            T={k:[] for k in ("spend","impressions","clicks")}
            C={k:[] for k in ("spend","reach","impressions","interazioni","clicks")}
            for dt in ds:
                m=md.get(dt,{}); t=td.get(dt,{})
                for k in M: M[k].append(round(m.get(k,0.0),2) if k=="spend" else int(m.get(k,0)))
                for k in T: T[k].append(round(t.get(k,0.0),2) if k=="spend" else int(t.get(k,0)))
                C["spend"].append(round(m.get("spend",0.0)+t.get("spend",0.0),2))
                C["reach"].append(int(m.get("reach",0)))
                C["impressions"].append(int(m.get("impressions",0)+t.get("impressions",0)))
                C["interazioni"].append(int(m.get("interazioni",0)))
                C["clicks"].append(int(m.get("clicks",0)+t.get("clicks",0)))
            labels=[str(int(x.split("-")[2])) for x in ds]
            days[ym]={"labels":labels,"meta":M,"tiktok":(T if td and any(ym==x[:7] for x in td) else None),"combined":C}
        structs.append({"name":name,"has_tiktok":bool(tt),"days":days})
    out={"schema_version":1,"months":months,"structures":structs}
    json.dump(out,open(os.path.join(W,"aghc_daily.json"),"w",encoding="utf-8"),ensure_ascii=False,separators=(",",":"))
    nd=sum(1 for s in structs if s["days"]); print("OK aghc_daily.json strutture con daily:",nd,"/",len(structs))
if __name__=="__main__": main()
