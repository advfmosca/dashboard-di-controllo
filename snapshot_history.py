#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Congela i KPI IG/FB (+TikTok) di un mese in history/AAAA-MM.json (banking per YoY)."""
import argparse, json, os
from aghc_report_lib import CLIENTS, load_raw, bucket, n

ap=argparse.ArgumentParser()
ap.add_argument("--workspace",default=".")
ap.add_argument("--month",required=True,help="AAAA-MM da congelare")
ap.add_argument("--acct",required=True); ap.add_argument("--camp",required=True); ap.add_argument("--tt",required=True)
a=ap.parse_args(); ws=a.workspace
ma=load_raw(ws,a.acct); ca=load_raw(ws,a.camp)
tt={str(r["account_id"]):r for r in load_raw(ws,a.tt)}
out={"month":a.month,"clients":{}}
for name,acct,camp,ttid in CLIENTS:
    src = ca if camp else ma
    b=bucket(src,acct,camp)
    rec={"meta":b}
    if ttid and ttid in tt:
        t=tt[ttid]; rec["tiktok"]={"reach":n(t.get("reach")),"impressions":n(t.get("impressions")),"clicks":n(t.get("clicks")),"spend":n(t.get("spend"))}
    out["clients"][name]=rec
os.makedirs(os.path.join(ws,"history"),exist_ok=True)
json.dump(out,open(os.path.join(ws,"history",a.month+".json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
print("snapshot -> history/%s.json (%d clienti)"%(a.month,len(out["clients"])))
