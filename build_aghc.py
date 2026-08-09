#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_aghc.py — aghc_data.json per la vista unica AGHC (aghc.html), card avanzata.

Per ogni struttura:
- KPI per canale (meta/tiktok/both=aggregato) con confronto MoM SEMPRE (cur/prev/delta),
  + blocco YoY sul Meta dove l'anagrafica lo prevede (Della Piana, Hannah, Lunetta,
  Marcella+Terrazza, Accentodì+Adèsso).
- Serie GIORNALIERA (ultimi ~30gg) per canale (spend/impressions/clicks) + aggregato.
- Conteggio giorni di NON attività (spend=0) nella finestra, per canale.
- ALERT automatici (canale fermo, giorni a zero, spesa/CPC/copertura anomali vs mese prec.).

Input raw/: aghc_meta_current|prev|yoy.json (account, mensile), aghc_tiktok_current|prev.json,
aghc_meta_daily.json, aghc_tiktok_daily.json (account×date).
Uso: python3 build_aghc.py --current-month 2026-08 --prev-month 2026-07 --yoy-month 2025-08 --workspace .
"""
import argparse, json, os
from datetime import datetime

MESI=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
META_YOY={"Hotel Della Piana","Hannah Hotels Collection","Hotel Lunetta","Marcella Royal + Terrazza Flavia","Accentodì + Adèsso"}

def roster(ws): return json.load(open(os.path.join(ws,"aghc_roster.json"),encoding="utf-8"))["structures"]
def url_meta(a): return "https://business.facebook.com/adsmanager/manage/campaigns?act="+str(a)
def url_tt(a): return "https://ads.tiktok.com/i18n/dashboard?aadvid="+str(a)
def mlabel(ym): y,m=ym.split("-"); return "%s %s"%(MESI[int(m)-1].capitalize(),y)
def rows_by_acct(path):
    if not os.path.exists(path): return {}
    d=json.load(open(path,encoding="utf-8")); rows=d.get("result",d) if isinstance(d,dict) else d
    return {str(r.get("account_id")):r for r in rows}
def daily_by_acct(path):
    if not os.path.exists(path): return {}
    d=json.load(open(path,encoding="utf-8")); rows=d.get("result",d) if isinstance(d,dict) else d
    out={}
    for r in rows: out.setdefault(str(r.get("account_id")),[]).append(r)
    for a in out: out[a].sort(key=lambda x:x.get("date",""))
    return out
def num(x):
    try: return float(x) if x is not None else 0.0
    except (TypeError,ValueError): return 0.0
def dpct(c,p): return ((c-p)/p*100.0) if p else None

def metrics(cur,prev,kind):
    cs,ps=num(cur.get("spend")),num(prev.get("spend"))
    cc,pc=num(cur.get("clicks")),num(prev.get("clicks"))
    ci,pi=num(cur.get("impressions")),num(prev.get("impressions"))
    cr,pr=num(cur.get("reach")),num(prev.get("reach"))
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
    """Solo prev+delta YoY per KPI (Meta)."""
    out={}
    for k in (["spend","impressions","clicks","reach","interazioni"] if kind=="meta" else ["spend","impressions","clicks"]):
        src={"spend":"spend","impressions":"impressions","clicks":"clicks","reach":"reach","interazioni":"actions_page_engagement"}[k]
        c,p=num(cur.get(src)),num(yoy.get(src))
        out[k]={"prev":round(p,2) if k=="spend" else int(p),"delta":dpct(c,p)}
    return out

def sum_dict(a,b,keys): return {k:num(a.get(k))+num(b.get(k)) for k in keys}

def daily_series(rows, meta=False):
    s={"spend":[round(num(r.get("spend")),2) for r in rows],
       "impressions":[int(num(r.get("impressions"))) for r in rows],
       "clicks":[int(num(r.get("clicks"))) for r in rows]}
    if meta:
        s["reach"]=[int(num(r.get("reach"))) for r in rows]
        s["interazioni"]=[int(num(r.get("actions_page_engagement"))) for r in rows]
    return s
def nonactivity(rows): return sum(1 for r in rows if num(r.get("spend"))==0)

def active(c,p): return (num(c.get("spend"))+num(p.get("spend"))+num(c.get("impressions"))+num(p.get("impressions")))>0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",default="."); ap.add_argument("--current-month",required=True)
    ap.add_argument("--prev-month",required=True); ap.add_argument("--yoy-month",required=True)
    ap.add_argument("--out",default="aghc_data.json")
    a=ap.parse_args(); ws=a.workspace; raw=os.path.join(ws,"raw")
    cur_l,mom_l,yoy_l=mlabel(a.current_month),mlabel(a.prev_month),mlabel(a.yoy_month)
    mc_=rows_by_acct(os.path.join(raw,"aghc_meta_current.json")); mp_=rows_by_acct(os.path.join(raw,"aghc_meta_prev.json"))
    my_=rows_by_acct(os.path.join(raw,"aghc_meta_yoy.json"))
    tc_=rows_by_acct(os.path.join(raw,"aghc_tiktok_current.json")); tp_=rows_by_acct(os.path.join(raw,"aghc_tiktok_prev.json"))
    md_=daily_by_acct(os.path.join(raw,"aghc_meta_daily.json")); td_=daily_by_acct(os.path.join(raw,"aghc_tiktok_daily.json"))
    ADD=["spend","impressions","clicks"]
    structures=[]; tmeta={"c":{},"p":{}}; ttik={"c":{},"p":{}}
    TM={"spend":0,"impressions":0,"clicks":0,"reach":0,"actions_page_engagement":0}
    TMp=dict(TM); TT={"spend":0,"impressions":0,"clicks":0}; TTp=dict(TT)
    for s in roster(ws):
        name=s["name"]; mid=s["meta_id"]; tid=s.get("tiktok_id")
        mc,mp,my=mc_.get(mid,{}),mp_.get(mid,{}),my_.get(mid,{})
        tc,tp=(tc_.get(tid,{}),tp_.get(tid,{})) if tid else ({},{})
        e={"name":name,"channels":{},"daily":{},"nonactivity":{},"alerts":[]}
        # META
        is_yoy = name in META_YOY and (mid in my_)
        if mid not in mc_ and mid not in mp_:
            e["channels"]["meta"]={"available":False,"url":url_meta(mid)}
        else:
            mm=metrics(mc,mp,"meta")
            blk={"available":True,"active":active(mc,mp),"url":url_meta(mid),"metrics":mm,"mom_label":mom_l}
            if is_yoy: blk["yoy"]=yoy_block(mc,my,"meta"); blk["yoy_label"]=yoy_l
            e["channels"]["meta"]=blk
            for k in TM: TM[k]+=num(mc.get(k)); TMp[k]+=num(mp.get(k))
        # TIKTOK
        if tid:
            tm=metrics(tc,tp,"tiktok")
            e["channels"]["tiktok"]={"available":True,"active":active(tc,tp),"url":url_tt(tid),"metrics":tm,"mom_label":mom_l}
            if active(tc,tp):
                for k in TT: TT[k]+=num(tc.get(k)); TTp[k]+=num(tp.get(k))
        # BOTH (aggregato MoM)
        cur_both=sum_dict(mc,tc,ADD); cur_both["reach"]=num(mc.get("reach")); cur_both["actions_page_engagement"]=num(mc.get("actions_page_engagement"))
        prev_both=sum_dict(mp,tp,ADD); prev_both["reach"]=num(mp.get("reach")); prev_both["actions_page_engagement"]=num(mp.get("actions_page_engagement"))
        e["channels"]["both"]={"metrics":metrics(cur_both,prev_both,"meta"),"mom_label":mom_l,"has_tiktok":bool(tid)}
        # DAILY
        mrows=md_.get(mid,[]); trows=td_.get(tid,[]) if tid else []
        dates=sorted(set([r["date"] for r in mrows]+[r["date"] for r in trows]))
        def align(rows):
            byd={r["date"]:r for r in rows}
            return [byd.get(d,{"date":d,"spend":0,"impressions":0,"clicks":0}) for d in dates]
        ma,ta=align(mrows),align(trows)
        both_rows=[{"date":dates[i],"spend":round(num(ma[i].get("spend"))+num(ta[i].get("spend")),2),
                    "impressions":int(num(ma[i].get("impressions"))+num(ta[i].get("impressions"))),
                    "clicks":int(num(ma[i].get("clicks"))+num(ta[i].get("clicks"))),
                    "reach":int(num(ma[i].get("reach"))),
                    "actions_page_engagement":int(num(ma[i].get("actions_page_engagement")))} for i in range(len(dates))]
        if dates:
            e["daily"]={"dates":dates,"meta":daily_series(ma,meta=True) if mrows else None,
                        "tiktok":daily_series(ta) if trows else None,"both":daily_series(both_rows,meta=True)}
            e["nonactivity"]={"meta":(nonactivity(mrows) if mrows else None),
                              "tiktok":(nonactivity(trows) if trows else None),"window":len(dates)}
        # ALERT
        al=[]
        mblk=e["channels"].get("meta",{})
        if mblk.get("available") and mrows:
            if num(mrows[-1].get("spend"))==0: al.append({"level":"red","text":"Meta fermo: nessuna erogazione il "+mrows[-1]["date"][8:]+"/"+mrows[-1]["date"][5:7]})
            nz=nonactivity(mrows)
            if nz>=3: al.append({"level":"amber","text":"Meta: %d giorni senza erogazione negli ultimi %d"%(nz,len(mrows))})
        if mblk.get("available"):
            sd=mblk.get("metrics",{}).get("spend",{}).get("delta")
            if sd is not None and sd<=-40: al.append({"level":"amber","text":"Spesa Meta %.0f%% vs %s"%(sd,mom_l)})
            rd=mblk.get("metrics",{}).get("reach",{}).get("delta")
            if rd is not None and rd<=-40: al.append({"level":"amber","text":"Copertura Meta %.0f%% vs %s"%(rd,mom_l)})
            cd=mblk.get("metrics",{}).get("cpc",{}).get("delta")
            if cd is not None and cd>=40: al.append({"level":"amber","text":"CPC Meta +%.0f%% vs %s"%(cd,mom_l)})
        tblk=e["channels"].get("tiktok",{})
        if tblk.get("available") and trows and num(trows[-1].get("spend"))==0:
            al.append({"level":"red","text":"TikTok fermo: nessuna erogazione il "+trows[-1]["date"][8:]+"/"+trows[-1]["date"][5:7]})
        e["alerts"]=al
        structures.append(e)
    def tb(c,p,kind): return metrics(c,p,kind)
    out={"schema_version":4,"generated_at":datetime.now().strftime("%Y-%m-%d %H:%M"),
         "current_label":cur_l,"mom_label":mom_l,"yoy_label":yoy_l,
         "totals":{"meta":tb(TM,TMp,"meta"),"tiktok":tb(TT,TTp,"tiktok"),"compare_label":mom_l},
         "structures":structures}
    json.dump(out,open(os.path.join(ws,a.out),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    ny=sum(1 for s in structures if s["channels"].get("meta",{}).get("yoy"))
    nd=sum(1 for s in structures if s.get("daily"))
    print("OK -> %s | %s | YoY meta: %d | con daily: %d | alert tot: %d"%(a.out,cur_l,ny,nd,sum(len(s["alerts"]) for s in structures)))

if __name__=="__main__": main()
