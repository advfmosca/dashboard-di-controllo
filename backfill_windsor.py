#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_windsor.py — Popola lo storico YoY da estratti Windsor con year_month + publisher_platform.
Funziona solo per mesi ENTRO ~13 mesi (limite Meta sul breakdown reach). Scrive history/AAAA-MM.json
nello stesso formato di snapshot_history.py (per-cliente IG/FB + TikTok), pronto per --comparison yoy.

Input raw/: hist2025_acct.json (account×ym×platform), hist2025_camp.json (campaign×ym×platform,
account condivisi), hist2025_tt.json (tiktok×ym).
Uso: python3 backfill_windsor.py --acct hist2025_acct.json --camp hist2025_camp.json --tt hist2025_tt.json --workspace .
"""
import argparse, json, os
from aghc_report_lib import CLIENTS, n, empty

def load(ws,p):
    d=json.load(open(os.path.join(ws,"raw",p),encoding="utf-8")); return d.get("result",d)
def ym2m(ym):
    y,m=str(ym).split("|"); return "%s-%02d"%(y,int(m))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",default="."); ap.add_argument("--acct",required=True)
    ap.add_argument("--camp",required=True); ap.add_argument("--tt",required=True)
    a=ap.parse_args(); ws=a.workspace
    acct=load(ws,a.acct); camp=load(ws,a.camp); tt=load(ws,a.tt)
    months=sorted(set(ym2m(r["year_month"]) for r in acct+camp))
    def bucket(rows,account,kw,month):
        agg={"ig":empty(),"fb":empty()}
        for r in rows:
            if str(r.get("account_id"))!=account or ym2m(r.get("year_month",""))!=month: continue
            if kw and kw.lower() not in str(r.get("campaign","")).lower(): continue
            b=agg["ig" if r.get("publisher_platform")=="instagram" else "fb"]
            b["reach"]+=n(r.get("reach")); b["impr"]+=n(r.get("impressions"))
            b["eng"]+=n(r.get("actions_page_engagement")); b["clk"]+=n(r.get("clicks")); b["spend"]+=n(r.get("spend"))
        return agg
    os.makedirs(os.path.join(ws,"history"),exist_ok=True)
    written=[]
    for month in months:
        clients={}
        for name,account,kw,ttid in CLIENTS:
            b=bucket(camp if kw else acct, account, kw, month)
            rec={"meta":b}
            if ttid:
                tr=[r for r in tt if str(r["account_id"])==ttid and ym2m(r["year_month"])==month and n(r.get("spend"))>0]
                if tr:
                    t=tr[0]; rec["tiktok"]={"impressions":n(t.get("impressions")),"clicks":n(t.get("clicks")),"spend":n(t.get("spend"))}
            has=(b["ig"]["impr"]+b["fb"]["impr"]+b["ig"]["spend"]+b["fb"]["spend"])>0 or ("tiktok" in rec)
            if has: clients[name]=rec
        out={"month":month,"source":"windsor_backfill","clients":clients}
        json.dump(out,open(os.path.join(ws,"history",month+".json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
        written.append((month,len(clients)))
    for m,c in written: print("history/%s.json -> %d clienti"%(m,c))

if __name__=="__main__": main()
