#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_aghc.py — aghc_data.json per la vista unica AGHC (aghc.html), card avanzata.
Roster a livello STRUTTURA (account o campagna). Per ogni struttura: KPI Meta/TikTok/Entrambe
(MoM sempre + YoY Meta dove previsto), serie giornaliera (tutte le metriche), giorni non-attivita,
alert, e BUDGET (annuale x pesi stagionali vs speso, con ricalibrazione) incluso.
TikTok "clicks" = engagements (Clics all). Uso: python3 build_aghc.py --current-month 2026-08 --prev-month 2026-07 --yoy-month 2025-08 --as-of-month 2026-07 --workspace .
"""
import argparse, json, os
from datetime import datetime
MESI=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
WEIGHTS=[0.03,0.03,0.05,0.10,0.15,0.15,0.12,0.12,0.05,0.05,0.05,0.10]
# name, meta_acct, camp_inc, camp_exc(list), tt_acct, meta_cmp, annual
STRUCTS=[
 ("Altafiumara Resort","1201395876543423",None,[],None,"mom",23000),
 ("Hotel Castello","1489903155429629",None,[],None,"mom",8000),
 ("Hotel Della Piana","911357333863123",None,[],"7504967007843319824","yoy",17000),
 ("Hannah Hotels","1528485957725509","hannah",["terraces","puntebianche"],None,"yoy",9000),
 ("Puntebianche Resort","1528485957725509","puntebianche",[],None,"mom",11100),
 ("Hemanaire","217115315497718",None,[],None,"mom",15000),
 ("Livata","4666471140299701",None,[],None,"mom",20000),
 ("Hotel Lunetta","687349689221880",None,[],"7498330316248203280","yoy",18000),
 ("Magari Estates","1372615496521110",None,[],None,"mom",24600),
 ("Marcella Royal Hotel","821188209852436","marcella",[],"7499093699838607377","yoy",14400),
 ("Terrazza Flavia","821188209852436","terrazza",[],None,"yoy",7500),
 ("Mare Hotel","1432341844596179",None,[],"7498679494010667009","mom",14400),
 ("Tenuta Montemagno Relais","752450855779035",None,[],None,"mom",22000),
 ("Villa Ermellina","30233607946222961",None,[],"7612666695502118929","mom",18400),
 ("Villa Giada","1849759899186169",None,[],"7626418949391351815","mom",21600),
 ("Villa Miliani","1353024533007038",None,[],None,"mom",12000),
]
def url_meta(a): return "https://business.facebook.com/adsmanager/manage/campaigns?act="+str(a)
def url_tt(a): return "https://ads.tiktok.com/i18n/dashboard?aadvid="+str(a)
def mlabel(ym): y,m=ym.split("-"); return "%s %s"%(MESI[int(m)-1].capitalize(),y)
def load(path):
    if not os.path.exists(path): return []
    d=json.load(open(path,encoding="utf-8")); return d.get("result",d) if isinstance(d,dict) else d
def by_acct(path):
    return {str(r.get("account_id")):r for r in load(path)}
def daily_by_acct(path):
    out={}
    for r in load(path): out.setdefault(str(r.get("account_id")),[]).append(r)
    for a in out: out[a].sort(key=lambda x:x.get("date",""))
    return out
def num(x):
    try: return float(x) if x is not None else 0.0
    except (TypeError,ValueError): return 0.0
def dpct(c,p): return ((c-p)/p*100.0) if p else None
def campaign_sum(rows,acct,kw,exc):
    agg={"spend":0.0,"clicks":0,"impressions":0,"reach":0,"actions_page_engagement":0}
    for r in rows:
        if str(r.get("account_id"))!=acct: continue
        c=str(r.get("campaign","")).lower()
        if kw and kw not in c: continue
        if any(x in c for x in exc): continue
        for k in agg: agg[k]+=num(r.get(k))
    return agg
def meta_period(struct, acct_map, camp_rows):
    name,acct,kw,exc,tt,cmp_,ann=struct
    if kw is not None: return campaign_sum(camp_rows,acct,kw,exc)
    return acct_map.get(acct,{})
def metrics(cur,prev,kind):
    cs,ps=num(cur.get("spend")),num(prev.get("spend")); cc,pc=num(cur.get("clicks")),num(prev.get("clicks"))
    ci,pi=num(cur.get("impressions")),num(prev.get("impressions")); cr,pr=num(cur.get("reach")),num(prev.get("reach"))
    ce,pe=num(cur.get("actions_page_engagement")),num(prev.get("actions_page_engagement"))
    def cpc(s,c): return (s/c) if c else None
    def cpm(s,i): return (s/i*1000.0) if i else None
    m={"spend":{"cur":round(cs,2),"prev":round(ps,2),"delta":dpct(cs,ps)},
       "impressions":{"cur":int(ci),"prev":int(pi),"delta":dpct(ci,pi)},
       "clicks":{"cur":int(cc),"prev":int(pc),"delta":dpct(cc,pc)},
       "cpc":{"cur":cpc(cs,cc),"prev":cpc(ps,pc),"delta":dpct(cpc(cs,cc) or 0,cpc(ps,pc) or 0) if (cc and pc) else None},
       "cpm":{"cur":cpm(cs,ci),"prev":cpm(ps,pi),"delta":dpct(cpm(cs,ci) or 0,cpm(ps,pi) or 0) if (ci and pi) else None}}
    if kind=="meta":
        m["reach"]={"cur":int(cr),"prev":int(pr),"delta":dpct(cr,pr)}
        m["interazioni"]={"cur":int(ce),"prev":int(pe),"delta":dpct(ce,pe)}
    return m
def yoy_block(cur,yoy,kind):
    out={}
    ks=["spend","impressions","clicks","reach","interazioni"] if kind=="meta" else ["spend","impressions","clicks"]
    src={"spend":"spend","impressions":"impressions","clicks":"clicks","reach":"reach","interazioni":"actions_page_engagement"}
    for k in ks:
        c,p=num(cur.get(src[k])),num(yoy.get(src[k]))
        out[k]={"prev":round(p,2) if k=="spend" else int(p),"delta":dpct(c,p)}
    return out
def dser(rows, meta=False):
    s={"spend":[round(num(r.get("spend")),2) for r in rows],"impressions":[int(num(r.get("impressions"))) for r in rows],"clicks":[int(num(r.get("clicks"))) for r in rows]}
    if meta:
        s["reach"]=[int(num(r.get("reach"))) for r in rows]; s["interazioni"]=[int(num(r.get("actions_page_engagement"))) for r in rows]
    return s
def nonact(rows): return sum(1 for r in rows if num(r.get("spend"))==0)
def active(c,p): return (num(c.get("spend"))+num(p.get("spend"))+num(c.get("impressions"))+num(p.get("impressions")))>0
def meta_monthly(struct, acct_monthly, camp_monthly):
    name,acct,kw,exc,tt,cmp_,ann=struct; arr=[0.0]*12
    if kw is not None:
        for r in camp_monthly:
            if str(r.get("account_id"))!=acct: continue
            c=str(r.get("campaign","")).lower()
            if kw not in c or any(x in c for x in exc): continue
            try: mi=int(str(r.get("year_month","")).split("|")[1])-1
            except: continue
            if 0<=mi<12: arr[mi]+=num(r.get("spend"))
    else:
        for r in acct_monthly:
            if str(r.get("account_id"))!=acct: continue
            try: mi=int(str(r.get("year_month","")).split("|")[1])-1
            except: continue
            if 0<=mi<12: arr[mi]+=num(r.get("spend"))
    return arr
def tt_monthly(tt,rows):
    arr=[0.0]*12
    if not tt: return arr
    for r in rows:
        if str(r.get("account_id"))!=tt: continue
        try: mi=int(str(r.get("year_month","")).split("|")[1])-1
        except: continue
        if 0<=mi<12: arr[mi]+=num(r.get("spend"))
    return arr

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workspace",default=".")
    ap.add_argument("--current-month",required=True); ap.add_argument("--prev-month",required=True)
    ap.add_argument("--yoy-month",required=True); ap.add_argument("--as-of-month",default=None); ap.add_argument("--out",default="aghc_data.json")
    a=ap.parse_args(); ws=a.workspace; raw=os.path.join(ws,"raw")
    cur_l,mom_l,yoy_l=mlabel(a.current_month),mlabel(a.prev_month),mlabel(a.yoy_month)
    as_of=int((a.as_of_month or a.prev_month).split("-")[1])
    P=lambda f: os.path.join(raw,f)
    mac=by_acct(P("aghc_meta_current.json")); map_=by_acct(P("aghc_meta_prev.json")); may=by_acct(P("aghc_meta_yoy.json"))
    cac=load(P("aghc_meta_camp_current.json")); cap=load(P("aghc_meta_camp_prev.json")); cay=load(P("aghc_meta_camp_yoy.json"))
    tac=by_acct(P("aghc_tiktok_current.json")); tap=by_acct(P("aghc_tiktok_prev.json"))
    mdaily=daily_by_acct(P("aghc_meta_daily.json")); tdaily=daily_by_acct(P("aghc_tiktok_daily.json"))
    acct_monthly=load(P("aghc_monthly_meta.json")); camp_monthly=load(P("aghc_meta_camp_monthly.json")); tt_month_rows=load(P("aghc_monthly_tiktok.json"))
    structures=[]; TM={k:0 for k in ["spend","impressions","clicks","reach","actions_page_engagement"]}; TMp=dict(TM); TT={"spend":0,"impressions":0,"clicks":0}; TTp=dict(TT)
    for st in STRUCTS:
        name,acct,kw,exc,tt,cmp_,ann=st
        e={"name":name,"channels":{},"daily":{},"nonactivity":{},"alerts":[]}
        mc=meta_period(st,mac,cac); mp=meta_period(st,map_,cap); my=meta_period(st,may,cay)
        avail = bool(mc) or bool(mp)
        if not avail:
            e["channels"]["meta"]={"available":False,"url":url_meta(acct),"compare_label":mom_l}
        else:
            blk={"available":True,"active":active(mc,mp),"url":url_meta(acct),"metrics":metrics(mc,mp,"meta"),"mom_label":mom_l}
            if cmp_=="yoy" and (num(my.get("spend"))+num(my.get("impressions"))>0):
                blk["yoy"]=yoy_block(mc,my,"meta"); blk["yoy_label"]=yoy_l
            e["channels"]["meta"]=blk
            for k in TM: TM[k]+=num(mc.get(k)); TMp[k]+=num(mp.get(k))
        if tt:
            tc,tp=tac.get(tt,{}),tap.get(tt,{})
            e["channels"]["tiktok"]={"available":True,"active":active(tc,tp),"url":url_tt(tt),"metrics":metrics(tc,tp,"tiktok"),"mom_label":mom_l}
            if active(tc,tp):
                for k in TT: TT[k]+=num(tc.get(k)); TTp[k]+=num(tp.get(k))
        else: tc,tp={},{}
        cur_b={"spend":num(mc.get("spend"))+num(tc.get("spend")),"impressions":num(mc.get("impressions"))+num(tc.get("impressions")),"clicks":num(mc.get("clicks"))+num(tc.get("clicks")),"reach":num(mc.get("reach")),"actions_page_engagement":num(mc.get("actions_page_engagement"))}
        prev_b={"spend":num(mp.get("spend"))+num(tp.get("spend")),"impressions":num(mp.get("impressions"))+num(tp.get("impressions")),"clicks":num(mp.get("clicks"))+num(tp.get("clicks")),"reach":num(mp.get("reach")),"actions_page_engagement":num(mp.get("actions_page_engagement"))}
        e["channels"]["both"]={"metrics":metrics(cur_b,prev_b,"meta"),"mom_label":mom_l}
        # daily (solo account meta con daily disponibile; campagne: nessun daily)
        mrows=mdaily.get(acct,[]) if kw is None else []
        trows=tdaily.get(tt,[]) if tt else []
        dates=sorted(set([r["date"] for r in mrows]+[r["date"] for r in trows]))
        if dates:
            def al(rows):
                byd={r["date"]:r for r in rows}; return [byd.get(d,{"date":d,"spend":0,"impressions":0,"clicks":0}) for d in dates]
            ma,ta=al(mrows),al(trows)
            both=[{"date":dates[i],"spend":round(num(ma[i].get("spend"))+num(ta[i].get("spend")),2),"impressions":int(num(ma[i].get("impressions"))+num(ta[i].get("impressions"))),"clicks":int(num(ma[i].get("clicks"))+num(ta[i].get("clicks"))),"reach":int(num(ma[i].get("reach"))),"actions_page_engagement":int(num(ma[i].get("actions_page_engagement")))} for i in range(len(dates))]
            e["daily"]={"dates":dates,"meta":dser(ma,True) if mrows else None,"tiktok":dser(ta) if trows else None,"both":dser(both,True)}
            e["nonactivity"]={"meta":(nonact(mrows) if mrows else None),"tiktok":(nonact(trows) if trows else None),"window":len(dates)}
        # alert
        alr=[]; mb=e["channels"].get("meta",{})
        if mb.get("available") and mrows and num(mrows[-1].get("spend"))==0: alr.append({"level":"red","text":"Meta fermo: nessuna erogazione il "+mrows[-1]["date"][8:]+"/"+mrows[-1]["date"][5:7]})
        if mb.get("available") and mrows and nonact(mrows)>=3: alr.append({"level":"amber","text":"Meta: %d giorni senza erogazione (%dgg)"%(nonact(mrows),len(mrows))})
        if mb.get("available"):
            for key,lbl in [("spend","Spesa"),("reach","Copertura")]:
                dd=mb.get("metrics",{}).get(key,{}).get("delta")
                if dd is not None and dd<=-40: alr.append({"level":"amber","text":"%s Meta %.0f%% vs %s"%(lbl,dd,mom_l)})
            cd=mb.get("metrics",{}).get("cpc",{}).get("delta")
            if cd is not None and cd>=40: alr.append({"level":"amber","text":"CPC Meta +%.0f%% vs %s"%(cd,mom_l)})
        e["alerts"]=alr
        # BUDGET
        real=[round(meta_monthly(st,acct_monthly,camp_monthly)[i]+tt_monthly(tt,tt_month_rows)[i],2) for i in range(12)]
        plan=[round(ann*WEIGHTS[i],2) for i in range(12)]
        ytd=round(sum(real[:as_of]),2); plan_td=round(sum(plan[:as_of]),2); resid=round(max(ann-ytd,0),2)
        rem=list(range(as_of,12)); rw=[WEIGHTS[i] for i in rem]; srw=sum(rw) or 1
        recal=list(real)
        for i in rem: recal[i]=round(resid*WEIGHTS[i]/srw,2)
        proj=round(ytd/as_of*12,2) if as_of else 0
        ytd_meta=round(sum(meta_monthly(st,acct_monthly,camp_monthly)[:as_of]),2); ytd_tt=round(sum(tt_monthly(tt,tt_month_rows)[:as_of]),2)
        pace=dpct(ytd,plan_td); status=("under" if (pace is not None and pace<-10) else "over" if (pace is not None and pace>10) else "on_track" if pace is not None else "na")
        if ann==0: status="inactive"
        e["budget"]={"annual":ann,"monthly_plan":plan,"monthly_real":[round(x,2) for x in real],"monthly_recal":[round(x,2) for x in recal],
                     "ytd_real":ytd,"ytd_meta":ytd_meta,"ytd_tiktok":ytd_tt,"plan_to_date":plan_td,"residual":resid,
                     "projection_year_end":proj,"fwd_recal_monthly":round(resid/len(rem),2) if rem else 0,"pace_pct":(round(pace,1) if pace is not None else None),"status":status}
        structures.append(e)
    def tb(c,p,kind): return metrics(c,p,kind)
    out={"schema_version":5,"generated_at":datetime.now().strftime("%Y-%m-%d %H:%M"),"as_of_month":(a.as_of_month or a.prev_month),
         "current_label":cur_l,"mom_label":mom_l,"yoy_label":yoy_l,
         "totals":{"meta":tb(TM,TMp,"meta"),"tiktok":tb(TT,TTp,"tiktok"),"compare_label":mom_l},
         "structures":structures}
    json.dump(out,open(os.path.join(ws,a.out),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    ny=sum(1 for s in structures if s["channels"].get("meta",{}).get("yoy")); nd=sum(1 for s in structures if s.get("daily"))
    print("OK -> %s | %s | strutture: %d | YoY meta: %d | con daily: %d"%(a.out,cur_l,len(structures),ny,nd))
    for s in structures:
        if s["name"] in ("Hannah Hotels","Puntebianche Resort","Marcella Royal Hotel","Terrazza Flavia"):
            m=s["channels"]["meta"]["metrics"]; b=s["budget"]
            print("  -",s["name"],"| Meta spesa",m["spend"]["cur"],"click",m["clicks"]["cur"],"| budget annuo",b["annual"],"ytd",b["ytd_real"])

if __name__=="__main__": main()
