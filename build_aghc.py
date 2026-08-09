#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_aghc.py — aghc_data.json per la vista unica AGHC (aghc.html).

Confronto PER-STRUTTURA (anagrafica AGHC):
  Meta YoY  -> Della Piana, Hannah, Lunetta, Marcella+Terrazza, Accentodì+Adèsso
  Meta MoM  -> tutte le altre
  TikTok    -> sempre MoM (split confronto per Della Piana/Lunetta/Marcella)
Ogni card mostra il proprio mese di confronto. Totali portfolio = confronto MoM (coerente).

Input raw/: aghc_meta_current.json (mese corrente), aghc_meta_prev.json (mese prec.=MoM),
aghc_meta_yoy.json (stesso mese anno prec.=YoY), aghc_tiktok_current.json, aghc_tiktok_prev.json
Uso: python3 build_aghc.py --current-month 2026-08 --prev-month 2026-07 --yoy-month 2025-08 --workspace .
"""
import argparse, json, os
from datetime import datetime

MESI_IT = ["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio",
           "agosto","settembre","ottobre","novembre","dicembre"]

# Confronto Meta per struttura (default MoM). TikTok sempre MoM.
META_YOY = {"Hotel Della Piana","Hannah Hotels Collection","Hotel Lunetta",
            "Marcella Royal + Terrazza Flavia","Accentodì + Adèsso"}

def load_roster(ws):
    return json.load(open(os.path.join(ws,"aghc_roster.json"),encoding="utf-8"))["structures"]
def url_meta(a): return "https://business.facebook.com/adsmanager/manage/campaigns?act="+str(a)
def url_tiktok(a): return "https://ads.tiktok.com/i18n/dashboard?aadvid="+str(a)
def month_label(ym): y,m=ym.split("-"); return "%s %s"%(MESI_IT[int(m)-1].capitalize(),y)
def load_rows(path):
    if not os.path.exists(path): return {}
    d=json.load(open(path,encoding="utf-8")); rows=d.get("result",d) if isinstance(d,dict) else d
    return {str(r.get("account_id")):r for r in rows}
def num(x):
    try: return float(x) if x is not None else 0.0
    except (TypeError,ValueError): return 0.0
def delta_pct(c,p): return ((c-p)/p*100.0) if p else None

def build_metrics(cur, prev, kind):
    c_spend,p_spend=num(cur.get("spend")),num(prev.get("spend"))
    c_clk,p_clk=num(cur.get("clicks")),num(prev.get("clicks"))
    c_imp,p_imp=num(cur.get("impressions")),num(prev.get("impressions"))
    c_reach,p_reach=num(cur.get("reach")),num(prev.get("reach"))
    c_eng,p_eng=num(cur.get("actions_page_engagement")),num(prev.get("actions_page_engagement"))
    def cpc(s,c): return (s/c) if c else None
    def cpm(s,i): return (s/i*1000.0) if i else None
    m={"spend":{"cur":round(c_spend,2),"prev":round(p_spend,2),"delta":delta_pct(c_spend,p_spend)},
       "impressions":{"cur":int(c_imp),"prev":int(p_imp),"delta":delta_pct(c_imp,p_imp)},
       "clicks":{"cur":int(c_clk),"prev":int(p_clk),"delta":delta_pct(c_clk,p_clk)},
       "cpc":{"cur":cpc(c_spend,c_clk),"prev":cpc(p_spend,p_clk),
              "delta":delta_pct(cpc(c_spend,c_clk) or 0,cpc(p_spend,p_clk) or 0) if (c_clk and p_clk) else None},
       "cpm":{"cur":cpm(c_spend,c_imp),"prev":cpm(p_spend,p_imp),
              "delta":delta_pct(cpm(c_spend,c_imp) or 0,cpm(p_spend,p_imp) or 0) if (c_imp and p_imp) else None}}
    if kind=="meta":
        m["reach"]={"cur":int(c_reach),"prev":int(p_reach),"delta":delta_pct(c_reach,p_reach)}
        m["interazioni"]={"cur":int(c_eng),"prev":int(p_eng),"delta":delta_pct(c_eng,p_eng)}
    return m

def active(cur,prev): return (num(cur.get("spend"))+num(prev.get("spend"))+num(cur.get("impressions"))+num(prev.get("impressions")))>0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",default=".")
    ap.add_argument("--current-month",required=True)
    ap.add_argument("--prev-month",required=True)
    ap.add_argument("--yoy-month",required=True)
    ap.add_argument("--out",default="aghc_data.json")
    a=ap.parse_args(); ws=a.workspace
    cur_l=month_label(a.current_month); mom_l=month_label(a.prev_month); yoy_l=month_label(a.yoy_month)
    roster=load_roster(ws); raw=os.path.join(ws,"raw")
    mc_=load_rows(os.path.join(raw,"aghc_meta_current.json"))
    mp_=load_rows(os.path.join(raw,"aghc_meta_prev.json"))
    my_=load_rows(os.path.join(raw,"aghc_meta_yoy.json"))
    tc_=load_rows(os.path.join(raw,"aghc_tiktok_current.json"))
    tp_=load_rows(os.path.join(raw,"aghc_tiktok_prev.json"))
    structures=[]
    tot={"meta":{"cs":0,"ps":0,"ci":0,"pi":0,"cc":0,"pc":0,"cr":0,"pr":0,"ce":0,"pe":0},
         "tiktok":{"cs":0,"ps":0,"ci":0,"pi":0,"cc":0,"pc":0}}
    for s in roster:
        name=s["name"]; entry={"name":name,"channels":{},"notes":[]}
        mid=s["meta_id"]; mc=mc_.get(mid,{})
        yoy = name in META_YOY
        prev_src = my_ if yoy else mp_
        mp = prev_src.get(mid,{})
        cmp_label = yoy_l if yoy else mom_l
        if yoy and mid not in my_ and mid in mp_:  # YoY mancante -> fallback MoM
            mp = mp_.get(mid,{}); cmp_label = mom_l; yoy=False
        if mid not in mc_ and mid not in mp_ and mid not in my_:
            entry["channels"]["meta"]={"available":False,"url":url_meta(mid),"compare":("yoy" if name in META_YOY else "mom"),"compare_label":cmp_label}
            entry["notes"].append("Account Meta non collegato a Windsor.")
        elif not active(mc,mp):
            entry["channels"]["meta"]={"available":True,"active":False,"url":url_meta(mid),"compare":("yoy" if yoy else "mom"),"compare_label":cmp_label,"metrics":build_metrics(mc,mp,"meta")}
        else:
            entry["channels"]["meta"]={"available":True,"active":True,"url":url_meta(mid),"compare":("yoy" if yoy else "mom"),"compare_label":cmp_label,"metrics":build_metrics(mc,mp,"meta")}
        # totali portfolio: sempre MoM per coerenza
        mm=mp_.get(mid,{})
        if active(mc,mm) or active(mc,mp):
            t=tot["meta"]; t["cs"]+=num(mc.get("spend")); t["ps"]+=num(mm.get("spend"))
            t["ci"]+=num(mc.get("impressions")); t["pi"]+=num(mm.get("impressions"))
            t["cc"]+=num(mc.get("clicks")); t["pc"]+=num(mm.get("clicks"))
            t["cr"]+=num(mc.get("reach")); t["pr"]+=num(mm.get("reach"))
            t["ce"]+=num(mc.get("actions_page_engagement")); t["pe"]+=num(mm.get("actions_page_engagement"))
        tid=s.get("tiktok_id")
        if tid:
            tc=tc_.get(tid,{}); tp=tp_.get(tid,{}); act=active(tc,tp)
            entry["channels"]["tiktok"]={"available":True,"active":act,"url":url_tiktok(tid),"compare":"mom","compare_label":mom_l,"metrics":build_metrics(tc,tp,"tiktok")}
            if act:
                t=tot["tiktok"]; t["cs"]+=num(tc.get("spend")); t["ps"]+=num(tp.get("spend"))
                t["ci"]+=num(tc.get("impressions")); t["pi"]+=num(tp.get("impressions"))
                t["cc"]+=num(tc.get("clicks")); t["pc"]+=num(tp.get("clicks"))
        structures.append(entry)
    def tb(t,kind):
        b={"spend":{"cur":round(t["cs"],2),"prev":round(t["ps"],2),"delta":delta_pct(t["cs"],t["ps"])},
           "impressions":{"cur":int(t["ci"]),"prev":int(t["pi"]),"delta":delta_pct(t["ci"],t["pi"])},
           "clicks":{"cur":int(t["cc"]),"prev":int(t["pc"]),"delta":delta_pct(t["cc"],t["pc"])}}
        if kind=="meta":
            b["reach"]={"cur":int(t["cr"]),"prev":int(t["pr"]),"delta":delta_pct(t["cr"],t["pr"])}
            b["interazioni"]={"cur":int(t["ce"]),"prev":int(t["pe"]),"delta":delta_pct(t["ce"],t["pe"])}
        return b
    out={"schema_version":3,"period_mode":"month_per_structure","generated_at":datetime.now().strftime("%Y-%m-%d %H:%M"),
         "current_label":cur_l,"mom_label":mom_l,"yoy_label":yoy_l,
         "totals":{"meta":tb(tot["meta"],"meta"),"tiktok":tb(tot["tiktok"],"tiktok"),"compare_label":mom_l},
         "structures":structures}
    json.dump(out,open(os.path.join(ws,a.out),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    ny=sum(1 for s in structures if s["channels"].get("meta",{}).get("compare")=="yoy")
    print("OK -> %s | corrente %s | YoY strutture: %d | MoM: %d"%(a.out,cur_l,ny,len(structures)-ny))
    for s in structures:
        m=s["channels"].get("meta",{})
        if m.get("active"): print("  -",s["name"],"| Meta vs",m["compare_label"],"| spesa",m["metrics"]["spend"]["cur"])

if __name__=="__main__": main()
